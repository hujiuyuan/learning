---
type: 技能点
域: 后端
项目: [smart WMS, muou]
证据: 实战/设计
---

# Spring Boot

所属通用技能：[[Spring应用与接口契约]]

**一句话**：Boot 帮我把依赖、自动配置、启动和异步/定时/安全这些总开关装配好；我要做的是知道每个开关在哪、为什么开或关，以及非 web 场景怎么让进程正常退出。

## 方法总纲

1. 先看依赖：`pom.xml` 引了哪些 starter，就决定了 classpath 上有什么、自动配置会装配什么。
2. 再看入口：`@SpringBootApplication` 的扫描范围和 `exclude` 列表；总开关（`@EnableAsync`、`@EnableScheduling`）放哪。
3. 再看配置来源：`application.yml` + `${ENV}` 占位符；本项目不用 Profile。
4. 再看非功能：线程池、优雅停机、健康探针、迁移开关。
5. 最后看退出：web 正常停；非 web（迁移容器）要主动 `System.exit`。

## 我用它干过什么

时间说明：`smart` 目录不是 git 仓库，2026-07/2026-08 按计划文档和文件 mtime 推断，不是提交记录。

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 启动类与自动配置裁剪 | 实战 | [[smart WMS]] | 2026-07 | — |
| 显式接管 `@Async` 线程池 | 实战 | [[smart WMS]] | 2026-07 | — |
| 定时任务开关条件化 | 实战 | [[smart WMS]] | 2026-07 | — |
| 迁移模式主动退出 | 实战 | [[smart WMS]] | 2026-07 | — |
| starter 组合与版本管理 | 实战 | [[smart WMS]] | 2026-08 | — |

## 我会的部分

- **版本与 starter**：Boot 3.3.13（`pom.xml:10`）、Java 21（`:22`）；web、actuator、validation、mail、thymeleaf、aop、cache、security 都是 `spring-boot-starter-*`（`:41-140`），测试用 `spring-boot-starter-test`（`:210-214`）；第三方 starter 有 MyBatis-Plus（`:88-93`）、Redisson（`:189-193`）、Knife4j（`:102-107`）、spring-dotenv（`:195-200`）。
- **启动类**：`@SpringBootApplication(exclude = {UserDetailsServiceAutoConfiguration.class})`（`WmsTrackApplication.java:19`）；`@EnableAsync` 也在启动类上（`:18`），是全项目异步的总开关。
- **排除 `UserDetailsServiceAutoConfiguration` 的原因**：项目用 JWT 过滤器自己建 `SecurityContext`，全仓没有 `UserDetailsService`、`AuthenticationProvider`、`AuthenticationManager` Bean。不排除的话，Boot 会自动注册一个 in-memory 默认用户，并在启动日志里打印随机密码。代码没写这条排除的注释，原因是从「没有任何 UserDetailsService 相关 Bean」推断的。
- **`@EnableAsync` 的位置与配套**：注解在 `WmsTrackApplication.java:18`；默认执行器由 `AsyncConfig.java:33-36` 显式声明，Bean 名同时叫 `applicationTaskExecutor` 和 `taskExecutor`。原因：`ExportPoolConfig`/`ImportPoolConfig` 声明了 `ExecutorService` Bean，Boot 的 `TaskExecutorConfiguration` 会因 `@ConditionalOnMissingBean(Executor.class)` 整体退避，`@Async` 会悄悄落到无界的 `SimpleAsyncTaskExecutor`（`AsyncConfig.java:9-26`）。
- **异步池参数**：核心 8 / 最大 16 / 有界队列 200，关机等待 10s（`application.yml:52-70`）；与 Tomcat 的 15s 排空共享 30s 停机预算（`:44-51`）。
- **Profile**：本项目不用 Spring Profile，`resources` 下没有 `application-*.yml`；环境差异全走 `${DB_URL}`、`${REDIS_PASSWORD}`、`${KNIFE4J_ENABLE}` 这类环境变量（`application.yml:30-32`、`:142`、`:160`）。取舍是：少一层 profile 组合，多一层「部署时必须传对变量」。
- **条件化总开关**：`@EnableScheduling` 从启动类挪到 `SchedulingEnabler`，用 `@ConditionalOnProperty(prefix="wms.scheduling", name="enabled", matchIfMissing=true)` 控制（`SchedulingEnabler.java:24-26`），测试可用真实属性彻底关掉 `@Scheduled`。
- **迁移模式退出**：`main` 里读 `spring.main.web-application-type`，等于 `none` 时执行 `System.exit(SpringApplication.exit(ctx))`（`WmsTrackApplication.java:22-32`）。背景是迁移容器只跑一次 Liquibase，Redisson/Netty 的非守护线程会阻止 JVM 自然退出；Liquibase 也已从应用启动路径移到部署流程单独执行（`application.yml:71-77`）。
- **可观测**：actuator 只暴露 health，readiness 含 db/redis，liveness 只含进程状态，mail 指示器关闭（`application.yml:289-310`）。

## Boot 4 版本组合（muou）

muou 是另一组版本，不和上面的 smart WMS 3.3.13 混着记：父 POM `spring-boot-starter-parent 4.1.1`、Java 21、Jackson 3.1.5、`spring-cloud 2025.1.3` + `spring-cloud-alibaba 2025.1.0.0`（`muou-client/muou-backend/muou-build/pom.xml:8-22`、`:32-35`、`:87-89`）。

- **Jackson 3 是主 JSON 栈**：核心包是 `tools.jackson`（`ObjectMapper`/`JsonMapper`/`JsonNode`），不是 Jackson 2 的 `com.fasterxml.jackson.databind`；注解仍用 `com.fasterxml.jackson.annotation`（Jackson 3 保留这组注解），Jackson 2 databind 2.22.2 只作为传递依赖存在（`muou-client/muou-backend/muou-build/pom.xml:32-35`；`muou-client/muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/pii/PiiValue.java:9`、`muou-client/muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/audit/ChangeOp.java:3`）。
- **两个 BOM 都要、顺序不能反**：先 import `spring-cloud-dependencies`，再 import `spring-cloud-alibaba-dependencies`。Alibaba BOM 里对 Spring Cloud 构件的版本管理依赖前者先就位；顺序反了，Maven 的 dependencyManagement 解析会把两者的版本覆盖关系弄反，症状是编译/启动时的版本冲突，不是一条明确报错（`pom.xml:87-89`、`:101-117`）。
- **Security 7 的 401/403 出口**：公共库只提供 `MuouAuthenticationEntryPoint` 与 `MuouAccessDeniedHandler` 两个 Bean，把未认证/无权限的响应接成统一返回体；它们不会自动生效，服务自己的 `SecurityFilterChain` 必须把这两个出口挂上（`muou-client/muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/security/MuouSecurityWebAutoConfiguration.java:14-34`）。
- **Boot 4 的自动装配拆分了**：OTel、Jackson、Security 的自动配置类名/条件都变了；照 Boot 3 教程抄会「应用正常启动、功能静默不生效」，链路追踪就是实例（见 [[可观测性与OpenTelemetry]]）。
- **升级检查点（没做过 Boot 3→4 升级，只在新项目起始版本上踩过）**：Jackson 2→3 的包名/模块注册、Security 6→7 的配置 API、OTel 属性名与 starter 拆分、`spring-cloud-alibaba` 与 Boot 4.1.x 的版本对应。每一条都要用「起服务 + 真调一次 + 看输出」验证，不能只看编译通过。

### 选型与取舍：为什么 muou 用这组版本

- **Boot 4.1.1 而不是 3.x**：新项目从零起，直接用当前主线，避免一上线就背一次大版本升级；代价是新版本生态还在追（SCA 只接受 Boot 4.0.x、部分教程还是 Boot 3 写法），所以版本全部由父 POM 钉死，服务 POM 不许写 version。
- **Cloud 2025.1.3 + Alibaba 2025.1.0.0**：注册/配置用 Nacos，网关用 Spring Cloud Gateway Servlet 版，需要这两套 BOM 的现状版本；Alibaba 的版本线比 Boot 慢，只能选它支持的组合。代价是升级要等 Alibaba 发版，不能单独升 Boot。
- **Jackson 3 而不是留在 Jackson 2**：Boot 4 的主线 JSON 栈就是 Jackson 3，新代码没有历史包袱；代价是大量第三方库还在 Jackson 2，类路径上会同时出现两代，注解包相同但 databind 不同，排障时要看清是哪一个 `ObjectMapper`。
- **什么条件下反悔**：SCA 长期不支持 Boot 4.1.x 或关键组件（Nacos/Sentinel/Seata）出现版本死角 → 降到 Boot 4.0.x 或改用不依赖 SCA 的接法；Jackson 3 的第三方兼容问题大面积爆 → 评估把边界服务留在 Jackson 2，但公共库不能两套混用。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| starter + BOM，而不是逐个手写依赖 | starter 带自动配置和一套兼容版本；BOM 统一版本，减少冲突 | 传递依赖多、启动慢；自动配置可能装配不需要的 Bean | 需要极致裁剪/排除冲突 → 显式依赖 + `exclude` |
| 自动配置为主，关键项显式声明 | 默认值覆盖大多数场景；线程池、迁移开关等关键项显式写，避免「魔法」 | 自动配置条件复杂，排查要看 `ConditionEvaluationReport`；升级可能改默认值 | 行为被默认值坑过 → 全部显式配置 |
| 环境变量占位符，不用 Profile | 部署时用 CI 变量注入，一套镜像多环境；减少 profile 文件组合 | 变量为空会静默用默认值；配置项散落，难审计 | 环境差异大/配置多 → 配置中心或 profile |
| 内嵌容器打 fat jar | 产物自包含、启动一致、部署简单 | 容器调优受限；镜像层大；JVM 参数要显式传 | 需要精细调优/多应用共用容器 → 外置 Tomcat |
| Boot 4 + Jackson 3 + Security 7（muou） | 跟 Java 21/新生态，长期维护；新项目无历史包袱 | 生态兼容滞后、第三方库未适配、迁移成本 | 关键依赖不兼容 → 留在 Boot 3；升级前先跑集成测试 |
| 迁移模式主动 `System.exit` | 非 web 进程没有请求线程，迁移完不退出会挂住流水线 | 退出码要正确；异常路径也要退出 | 改为独立迁移 Job → 由 Job 自身管理生命周期 |

## 边界

- 没写过自定义 starter、`AutoConfiguration.imports`、`@ConfigurationProperties` 校验。
- 没做过配置中心（Nacos/Apollo）、profile 分组、配置加密。
- 没做过 Boot 2→3 升级迁移；项目一开始就是 3.3.13。
- Java 21 的 `--enable-preview`（`pom.xml:320`、`:331-335`）只是跟着项目用，没独立评估过 preview 特性的升级风险。
- 迁移容器退出逻辑只读了代码和注释，没实际跑过迁移容器验证退出耗时。
- 排除 `UserDetailsServiceAutoConfiguration` 没有注释，原因属于推断，不是文档记录。

## 相关技能

[[Spring MVC]]、[[Spring Security]]、Java 线程池与异步（待建）、[[Liquibase]]（实战：smart wms3）

## 用在哪些工程能力

接口契约与统一响应、部署与优雅停机、异步任务（均未建卡，无页面）
