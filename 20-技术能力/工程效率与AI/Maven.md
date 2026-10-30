---
type: 技能点
域: 工程效率与AI
项目: [smart WMS, muou]
证据: 实战
---

# Maven

所属通用技能：[[工程效率与AI]]

**一句话**：Maven 用「约定目录 + 生命周期 + 插件」把源码变成可部署产物；真正影响交付的是依赖仲裁、仓库镜像、测试跳过和 Docker 层缓存。

## 方法总纲

1. **坐标先定**：`groupId:artifactId:version` 唯一标识一个构件；父 POM 管版本，子模块只声明依赖。
2. **生命周期不是命令**：`clean/validate/compile/test/package/verify/install/deploy` 是阶段，插件 goal 绑定在阶段上。
3. **依赖冲突用 `dependency:tree` 看**：Maven 按「最近路径优先、先声明优先」仲裁，不显式管理就会随机。
4. **测试分 surefire/failsafe**：单测在 `test`，集成测试在 `verify`；`-DskipTests` 只跳过执行，`-Dmaven.test.skip` 连编译都跳。
5. **构建要可缓存**：Docker 里先拷 `pom.xml` 跑 `dependency:go-offline`，再拷 `src`，依赖层才能复用。
6. **仓库和镜像写进 settings**：`settings.xml` 管镜像、认证、私服；不要写进项目 POM。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| Spring Boot 单模块打包 | 实战 | smart WMS | 2026-05~09 | [[CI-CD与部署]] |
| Docker 两阶段构建 + 依赖缓存 | 实战 | smart WMS | 2026-07 | [[CI-CD与部署]] |
| 多仓迁移项目的构建/收集脚本 | 实战 | muou | 2026-09~10 | [[多仓迁移落地]] |

## 选型与取舍

### 为什么用 Maven，不用 Gradle

- Maven 的优势是约定强、生命周期固定、POM 可读；多仓/多团队时，构建脚本不容易各写一套。代价是 XML 冗长、复杂构建逻辑要写插件，增量构建/缓存不如 Gradle 灵活。
- 项目都是 Spring Boot + 单模块/少量模块，Maven 的约定足够；没有 Gradle 实战，换 Gradle 的收益（增量、Kotlin DSL、构建缓存）在当前规模不明显。
- 如果模块数量、构建时间继续增长，或者需要复杂条件构建，再评估 Gradle；当前不是「Maven 更先进」，是约定和团队熟悉度更划算。

### 为什么用父 POM/BOM 管版本，不在子模块到处写版本

- 父 POM `spring-boot-starter-parent` + 项目 BOM 把 Spring/Jackson/测试依赖的版本收在一处，子模块只声明 `groupId:artifactId`；升级时改一处，避免「A 模块 Jackson 2、B 模块 Jackson 3」。
- 代价：父 POM 变成隐性契约，子模块覆盖版本会绕过统一管理；排查冲突要用 `dependency:tree`/`effective-pom`，不能只看子模块 POM。
- 项目 muou 用 `muou-build` 统一 Spring Boot 4/Spring Cloud/Alibaba/Jackson 版本（`muou-backend/muou-build/pom.xml:9-12,32-35,88-114`）；smart 用 `spring-boot-starter-parent`（`smart-server-wms3/pom.xml:9-15`）。两种都是「版本集中」，不是谁更高级。

### 为什么用 Enforcer 守依赖收敛，不靠人工约束

- **它守什么**：`muou-build` 在 `validate` 阶段跑 `maven-enforcer-plugin`，两条规则——`requireUpperBoundDeps`（传递依赖版本打架就红）和 `bannedDependencies`（禁止 `com.alibaba:fastjson:[,2.0.0)`，含间接依赖）（`muou-client/muou-backend/muou-build/pom.xml:410-431`）。
- **为什么需要**：版本冲突常常「编译通过、运行期 `NoSuchMethodError`」，靠人看 `dependency:tree` 只能抽查；把冲突变成构建失败，才在合并前暴露。禁 fastjson 1.x 是因为 1.2.83 有远程代码执行公告，而 Sentinel 的传输包又必需 fastjson，所以父 POM 把它钉成第二代兼容包 2.0.65，并用 Enforcer 挡住任何路径把 1.x 拖回来（`muou-build/pom.xml:71-72`、`:352-359`、`:426-430`）。
- **代价**：任何新增依赖只要带进版本冲突或 1.x fastjson，构建直接失败，必须在父 POM 收敛或写 exclusion；规则误报时要用 `dependency:tree` 定位，不能直接关规则。`validate` 阶段多跑一次解析，构建时间略增。
- **与 BOM 的分工**：BOM 决定「应该用哪个版本」，Enforcer 验证「实际解析出来的版本有没有按 BOM 走」；只有 BOM 没有 Enforcer，间接依赖仍可能把版本顶上去。
- **什么时候反悔**：规则误报频繁、或构建时间成为瓶颈 → 收窄到 CI profile 而不是本地每次跑；需要放行某个冲突 → 先在父 POM 显式钉版本，不要加全局豁免。当前规则少、命中明确，收益大于成本。

### 为什么 Docker 里先拷 `pom.xml` 再拷 `src`

- Docker 层按指令缓存；`COPY src` 会让后面的层全部失效。先把 `pom.xml` 单独拷进去跑 `dependency:go-offline`，依赖层只在 POM 变化时重建，代码改动命中缓存。
- 代价：`go-offline` 不是万能的，某些插件/动态依赖仍可能在线解析；镜像内要配镜像源，避免构建时依赖宿主机 `settings.xml`（`smart-server-wms3/Dockerfile:1-22`）。
- 如果构建时间不是瓶颈，这层优化可以不做；项目镜像构建频繁，缓存收益明确。

### 为什么 CI 用 `-DskipTests`，不默认 `-Dmaven.test.skip`

- `-DskipTests` 只跳过测试执行，仍然编译测试代码，能提前发现测试编译错误；`-Dmaven.test.skip=true` 连测试编译都跳过，构建更快但可能把坏测试带到后面。
- 代价：`-DskipTests` 仍然花测试编译时间；如果 CI 分阶段（build 阶段只打包、test 阶段单独跑），可以接受。项目在构建阶段用前者，测试阶段单独跑。
- 这不是「跳过测试」的借口：跳过执行的前提是后面有独立测试 job；没有的话，等于没测。

### 什么条件下会反悔

- 构建时间成为瓶颈、模块增多 → 评估 Gradle/Bazel 或 Maven 构建缓存；当前 `-T 1C` 和 Docker 层缓存够用。
- 多模块/BOM 发布复杂到父 POM 难以维护 → 拆 BOM 仓/用 dependencyManagement 平台；当前规模还不需要。
- 私服/镜像认证复杂化 → 把 settings 抽成 CI secret/模板，不写进项目 POM；当前 Dockerfile 内置镜像源是简化做法。

## 我会的部分

- **POM 继承**：`spring-boot-starter-parent` 管依赖版本和插件版本（`smart-server-wms3/pom.xml:9-15`）。
- **依赖 scope**：`compile`、`provided`、`runtime`、`test` 的边界；测试依赖不会进生产包。
- **打包插件**：`spring-boot-maven-plugin` 生成可执行 jar；`maven-compiler-plugin` 管 Java 版本和注解处理器。
- **测试跳过**：CI 构建阶段用 `-DskipTests` 只跳过执行；需要连测试编译都跳时用 `-Dmaven.test.skip=true`。
- **Docker 构建缓存**：先 `COPY pom.xml` + `mvn dependency:go-offline`，再 `COPY src`，代码改动不会让依赖层失效（`smart-server-wms3/Dockerfile:1-22`）。
- **镜像加速**：Dockerfile 里给 Maven 配阿里云镜像，构建阶段不依赖宿主机 `settings.xml`（`smart-server-wms3/Dockerfile:13-21`）。
- **多线程构建**：`-T 1C` 按 CPU 核数并行构建模块；单模块项目收益有限。
- **常见排查**：`mvn dependency:tree -Dincludes=...` 查冲突；`mvn help:effective-pom` 看最终 POM；`mvn -X` 看插件实际参数。

## 边界

- 没有 Gradle 实战。
- 没有做过复杂多模块聚合、BOM 发布、私服 Nexus/Artifactory 运维。
- 没有写过 Maven 插件；只配置过现成插件。
- 没有做过增量构建/构建缓存服务（如 Build Cache）的深度优化。

## 相关技能

- [[CI-CD与部署]]、[[Spring Boot]]、[[Docker与容器]]
- [[EasyCode与Velocity]]（代码生成后的构建）

## 用在哪些工程能力

- 本地/CI 构建与打包
- Docker 镜像分层与缓存
- 多仓项目的构建与收集
