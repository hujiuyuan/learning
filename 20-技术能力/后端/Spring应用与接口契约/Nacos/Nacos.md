---
type: 技能点
域: 后端
项目: [muou]
证据: 实战
---

# Nacos

所属通用技能：[[Spring应用与接口契约]]、[[中间件与异步任务]]

**一句话**：Nacos 在 muou 里同时做配置中心和服务注册；关键不是「连上」，而是命名空间、dataId、导入顺序和连不上时的启动行为。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/`。

## 方法总纲

1. **命名空间先隔离**：local/dev/prod 用不同 namespace，别让本地读到生产配置。
2. **dataId 有顺序**：`common.yaml` 放公共项，`<service>.yaml` 放服务项；后导入的同名 key 覆盖前者。
3. **启动必需项进镜像**：连 Nacos 之前就要用的配置（如网关模块门控 cache-ttl）写在仓内 `application.yml`，其余放 Nacos。
4. **`optional:` 是启动开关**：不加 `optional:`，Nacos 连不上直接起不来；加了也要知道 dataId 为空时只 WARN。
5. **服务发现和配置中心分开看**：注册发现解决「调谁」，配置中心解决「用什么配置」。
6. **配置要有 seed 脚本**：新 namespace 先跑 `seed-service-configs.sh`，否则客户端只打 WARN 照常启动。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 网关配置导入（common + gateway） | 实战 | muou | 2026-09 | [[Spring Cloud Gateway]] |
| 本地 namespace / 服务账号 | 实战 | muou | 2026-09 | — |
| Nacos 本地编排与配置 seed | 实战 | muou | 2026-09 | — |

## 选型与取舍

### 为什么用 Nacos，不用 Eureka + Apollo / Consul

- Nacos 一个组件同时做配置中心和服务注册，少一套部署/鉴权/客户端；Spring Cloud Alibaba 直接集成，版本对齐由 BOM 管。
- 代价：配置和注册耦合在同一个组件，Nacos 挂了既影响「调谁」也影响「用什么配置」；集群、持久化、鉴权要自己运维。Eureka + Apollo 把两件事拆开，故障面更小，但多一套组件和客户端。
- 项目服务数量/团队规模还没到「拆开更划算」的程度，选 Nacos 是减少组件数；如果配置和注册的可用性要求不同，拆开更合理。

### 为什么配置分「镜像内」和 Nacos 两层

- 连 Nacos 之前就要用的项（地址、应用名、网关门控 cache-ttl 等）必须在镜像/本地配置里，否则启动时没有 Nacos 地址；其余放 Nacos，改配置不用重新打镜像。
- 代价：配置来源多，排查要看导入顺序（`application.yml:7-15`：仓内 `module-gate-paths.yml` → `nacos:common.yaml` → `nacos:gateway.yaml`，后者覆盖前者）；配置漂移要靠启动日志/配置中心版本排查。
- 如果所有配置都进 Nacos，镜像更干净但启动强依赖 Nacos；项目选择「启动必需项本地化」，是可用性优先。

### 为什么用 `optional:` 导入

- 不加 `optional:`，Nacos 连不上直接起不来；加了之后 dataId 不存在只打 WARN，服务照常启动（`application.yml:8-9`）。
- 这是明确的取舍：开发/测试环境容忍配置缺失，避免本地没起 Nacos 就完全跑不了；代价是生产如果 dataId 漏配，服务可能带着默认值启动，问题延后暴露。
- 如果生产要求「配置缺失必须失败」，应该去掉 `optional:` 或加启动校验；当前没有做这个区分，是一个残余风险。

### 为什么按 namespace 隔离环境

- local/dev/prod 用不同 namespace，避免本地误读生产配置；代价是每个 namespace 都要跑 seed 脚本，新环境初始化多一步。
- 服务注册也按 namespace 隔离，跨 namespace 调用要显式配置；如果 namespace 规划不清，会出现「服务注册了但调不到」。

### 什么条件下会反悔

- 配置中心故障影响面不可接受 → 拆成独立配置中心/本地缓存兜底；当前 Nacos 同时承担注册和配置。
- 生产配置缺失导致带默认值启动 → 去掉 `optional:` 或加 dataId 必填校验；当前是开发便利优先。
- 多环境/多集群规模上升 → 补 Nacos 集群、持久化、鉴权；当前只有本地编排经验。

## 我会的部分

- **配置导入**：网关 `spring.config.import` 依次导入 `optional:classpath:module-gate-paths.yml`、`nacos:common.yaml`、`nacos:gateway.yaml`（`muou-backend/muou-server-gateway/src/main/resources/application.yml:7-15`）。
- **启动行为**：注释明确「不加 optional:，Nacos 连不上直接起不来」；dataId 不存在时只打 WARN（`application.yml:8-9`）。
- **本地 profile**：local profile 配 Nacos 地址、用户名/密码、namespace；部署时不激活，由编排环境变量给（`application.yml:25-40`）。
- **服务注册**：网关依赖 `spring-cloud-starter-alibaba-nacos-discovery`（`muou-backend/muou-server-gateway/pom.xml:67-71`）。
- **配置中心**：网关依赖 `spring-cloud-starter-alibaba-nacos-config`（`pom.xml:73-77`）。
- **本地编排**：`muou-app-ops/middleware/nacos/docker-compose.yml` 起 Nacos；`bootstrap.sh`、`seed-service-configs.sh` 负责初始化和配置导入。
- **排障脚本**：`check-dev-keypairs.sh`、`check-tenant-only-paths.sh`、`stress-test.sh` 分别查密钥、路径和压测。

## 边界

- 没有 Nacos 集群部署、持久化（MySQL）和鉴权体系运维经验。
- 没有做过配置历史回滚、灰度发布、监听器动态刷新。
- 没有做过 Nacos 服务发现的健康检查、权重、保护阈值调优。
- 没有做 Sentinel 集群流控/规则治理；单机流控/熔断规则由 Nacos 数据源订阅（`SentinelAutoConfiguration.java:221-226`，dataId `<app>-flow-rules` / `<app>-degrade-rules`），详见 [[Sentinel]]。muou 的 Boot 4 / Cloud / Alibaba 版本组合见 [[Spring Boot#Boot 4 版本组合（muou）]]。
- 没有处理过 Nacos 不可用时的完整降级方案（项目里只是启动失败或 WARN）。

## 相关技能

- [[Spring Cloud Gateway]]、[[Spring Boot]]、[[CI-CD与部署]]
- [[Redis]]（网关会话/缓存也依赖 Redis）
- 理论：[[服务发现与配置理论]]（注册/心跳、推拉、AP/CP、配置灰度与兜底）

## 用在哪些工程能力

- 多环境配置隔离
- 服务注册与发现
- 网关路由/模块门控配置
