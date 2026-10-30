---
type: 技能点
域: 工程效率与AI
项目: [smart WMS]
证据: 实战
---

# Docker 与容器

所属通用技能：[[工程效率与AI]]

**一句话**：Docker 用镜像分层和命名空间把应用连依赖一起交付；项目里真正有用的是两阶段构建、依赖缓存、非 root 运行和 CI 同机部署。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/smart/`。

## 方法总纲

1. **构建和运行分开**：builder 阶段装 Maven/JDK，runtime 阶段只留 JRE 和 jar，镜像更小、攻击面更少。
2. **依赖层放前面**：先拷 `pom.xml` 跑 `dependency:go-offline`，再拷 `src`；代码改动只重建后面的层。
3. **缓存挂载**：BuildKit `--mount=type=cache,target=/root/.m2` 让 Maven 依赖跨构建复用。
4. **非 root 运行**：runtime 阶段建普通用户，`ENTRYPOINT` 用 `su-exec` 降权；不要用 root 跑应用。
5. **配置外置**：镜像不写环境相关配置，用 env file / 环境变量注入。
6. **部署可回滚**：镜像打唯一 tag，部署前确认镜像存在，失败能回退到上一个 tag。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 后端两阶段 Dockerfile | 实战 | smart WMS | 2026-07 | [[CI-CD与部署]] |
| CI 构建 + 同机部署 + 旧镜像清理 | 实战 | smart WMS | 2026-07 | [[CI-CD与部署]] |
| docker-compose 起应用 + Loki/Promtail | 实战 | smart WMS | 2026-07 | [[CI-CD与部署]] |

## 选型与取舍

### 为什么用容器，不用裸机 jar / 虚拟机

- 容器把 JDK、时区、字体、启动脚本和应用打进同一个镜像，减少「我这能跑、服务器不行」；比虚拟机轻，启动快，CI 里能直接构建/运行。
- 代价：容器内是另一个文件系统/网络命名空间，时区、挂载、日志、资源限制都要显式配；Docker daemon 是单点，镜像仓库/清理也要运维。
- 项目只有单机/少量服务，Docker + compose 够用；Kubernetes 的调度/自愈/滚动发布收益在当前规模不明显，学习和运维成本更高。不是「K8s 更先进」，是规模没到。

### 为什么用两阶段构建，不用单阶段

- builder 阶段有 Maven/JDK/源码，runtime 阶段只留 JRE 和 jar；镜像更小、攻击面更少，也不会把源码/构建缓存带进生产。
- 代价：Dockerfile 更长，两个阶段的基础镜像要分别维护；调试构建失败要分清是 builder 还是 runtime。
- 如果只是本地临时跑，单阶段更快；生产镜像值得多这几行。

### 为什么依赖层放前面、挂 BuildKit cache

- Docker 层缓存按指令内容命中；`COPY src` 会让后面的层失效。先 `COPY pom.xml` + `go-offline`，代码改动只重建编译/打包层。
- BuildKit `--mount=type=cache,target=/root/.m2` 让 Maven 依赖跨构建复用，不受镜像层缓存失效影响。
- 代价：`go-offline` 可能漏掉动态解析的插件依赖；Cache mount 在 CI 上需要 BuildKit 和持久化 cache，否则收益有限。项目 CI 用 `DOCKER_BUILDKIT=1`，本地/runner 的 cache 行为要一致。

### 为什么非 root 运行

- 容器默认 root，应用被攻破就是容器内 root；虽然还有 namespace 隔离，但挂载卷、内核漏洞时风险更大。runtime 阶段建普通用户 + `su-exec` 降权，是低成本加固。
- 代价：文件权限/日志目录/端口（<1024）要提前处理；挂载卷的 UID 要匹配，否则应用写不了文件。
- 如果应用只读、无挂载，root 的风险小一些；项目要写日志/上传目录，所以非 root 有必要。

### 为什么 build 和 deploy 必须同一台 runner

- 镜像构建后只在当前 Docker daemon 本地，没推仓库；换一台 runner 部署会找不到镜像。项目用 `docker image inspect` 在部署前检查，失败时明确提示「build/deploy 不同机」（`.gitlab-ci.yml:139-141`）。
- 代价：部署被绑定到单台 runner，横向扩展/容灾弱；要跨机部署就得加镜像仓库（Harbor/registry），这会增加推送/拉取/认证成本。
- 当前选择是「简单但绑定」；如果 runner 故障频繁或多环境部署，应该补镜像仓库，而不是继续同机。

### 什么条件下会反悔

- 服务数量/发布频率上升 → 引入 Kubernetes 或至少镜像仓库 + 多 runner；当前同机部署会成为瓶颈。
- 镜像安全要求提高 → 加镜像扫描、签名、distroless；当前只做非 root。
- 构建缓存收益下降/CI 不稳定 → 改用远端构建缓存或预构建依赖镜像；当前 BuildKit cache 够用。

## 我会的部分

- **两阶段构建**：builder 用 `maven:3.9-eclipse-temurin-21-alpine`，runtime 用 `eclipse-temurin:21-jre-alpine`（`smart-server-wms3/Dockerfile:1-37`）。
- **依赖缓存**：`COPY pom.xml` + `mvn dependency:go-offline`，再 `COPY src` + `mvn package`；两段都挂 `--mount=type=cache,target=/root/.m2`（`Dockerfile:20-25`）。
- **非 root**：runtime 阶段 `addgroup/adduser`，`chown` 应用目录，`ENTRYPOINT` 走 `entrypoint.sh`（`Dockerfile:28-37`）。
- **镜像加速**：Dockerfile 内改 Maven `settings.xml` 使用阿里云镜像，不依赖宿主机配置（`Dockerfile:13-21`）。
- **CI 构建**：`DOCKER_BUILDKIT=1 docker build`，build 与 deploy 必须同一台 runner（`smart-server-wms3/.gitlab-ci.yml:71-99`）。
- **部署检查**：部署前 `docker image inspect` 确认镜像存在；失败时提示 build/deploy 不同机（`.gitlab-ci.yml:139-141`）。
- **清理旧镜像**：按镜像引用过滤后删除旧镜像，避免磁盘打满（`.gitlab-ci.yml:162-165`）。
- **compose**：应用 + Loki + Promtail 三个服务，独立网络、内存限制、日志目录挂载（`smart-server-wms3/docker/docker-compose.yml:1-40`）。

## 边界

- 没有 Kubernetes、Swarm、Nomad 实战。
- 没有做过多架构镜像（arm64/amd64）和镜像签名/扫描。
- 没有做过镜像体积的极致优化（distroless、jlink）。
- 没有处理过容器网络、存储卷迁移的复杂故障。

## 相关技能

- [[CI-CD与部署]]、[[Maven]]、[[Spring Boot]]
- [[Redis]]（compose 里的依赖服务）

## 用在哪些工程能力

- 后端镜像构建与分层缓存
- CI 构建、部署、回滚
- 本地 compose 环境
