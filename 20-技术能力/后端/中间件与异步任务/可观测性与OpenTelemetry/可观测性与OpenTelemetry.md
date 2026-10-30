---
type: 技能点
域: 后端
项目: [muou, smart WMS]
证据: 实战
---

# 可观测性与 OpenTelemetry

所属通用技能：[[中间件与异步任务]]

**一句话**：可观测不是「装个 Grafana」，而是先把三种信号接成一条链：应用侧用 OTel starter 出 OTLP，traceId 进日志的每一行，日志经 logback appender 送采集端；采集端再分发给 Tempo（链路）、Loki（日志）、Prometheus（指标），Grafana 里从一条日志点进对应 trace。换后端只改编排，不改业务代码。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/muou-backend/`。简称：`00-16...` = `muou-app-doc/design/00-技术选型（selection）/00-16-日志与链路追踪技术选型.md`；`observability/` = `muou-app-ops/middleware/observability/`；`观测包/` = `muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/observability/`；`wms3/docker/` = `/Users/hujiuyuan/workspace/voidtech/smart/smart-server-wms3/docker/`。

**归属说明**：muou 的应用侧接线、日志脱敏、采集端编排与 Grafana 数据源由本人提交；smart WMS 的 Loki/Promtail/Grafana 栈最初由同事搭建，本人只做过日志标签、内存上限等运维调整，不把整套算成个人从零实现。

## 方法总纲

1. **三种信号各管一段**：trace 回答「一次请求经过哪些服务、每段多久」；metrics 回答「总量/分位/趋势」；log 回答「那一刻发生了什么」。三者靠 traceId 串起来，缺一个就只能各看各的。
2. **应用侧只认 OTLP**：`spring-boot-starter-opentelemetry` 出 traces/metrics，logback appender 出 logs；协议厂商中立，后端可换。
3. **traceId 必须进日志行**：`MuouTraceResolver` 统一从业务上下文、当前 span、MDC、`X-Muou-Trace-Id`、W3C `traceparent` 取号，取不到就生成，绝不为空。
4. **异步入口要显式搬上下文**：定时任务、手工补跑、outbox 投递/消费没有入站请求，用 `TraceScope.open/callAsSystemTask` 把 traceId 挂到当前线程，close 时还原。
5. **日志先脱敏再出进程**：`PiiMaskingConverter` 对正文/异常按邮箱、HKID、手机号正则打码；`PiiMaskingOtelAppender` 复制事件、只换正文再送 OTLP，原事件不动。
6. **采集端是唯一出口**：八个服务只认识 `otelcol:4317/4318`；换 Tempo/Loki/Prometheus 或换云，只改 `otelcol.yaml` 的 exporters/pipelines。
7. **采样率全链路一致**：当前 `probability: 1.0`；中间某一跳不同会导致链路缺一段且不报错。
8. **观测组件自己也会撑爆机器**：collector 有 `memory_limiter`，Go 组件要设 `GOMEMLIMIT`，容器 `mem_limit` 按实测用量给，不按拍脑袋。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 公共库接 OTel starter + `MuouTraceResolver`，traceId 进日志/上下文/出站头 | 实战 | muou | 2026-09 | 链路追踪（待建） |
| JSON 日志编码器 + PII 正则脱敏 + OTLP logback appender | 实战 | muou | 2026-10 | [[安全与审计]] |
| OTel Collector + Tempo/Loki/Prometheus/Grafana 五件套编排 | 实战 | muou | 2026-09 | [[CI-CD与部署]] |
| Grafana 数据源与 Loki→Tempo 的 traceId 跳转 | 实战 | muou | 2026-09 | — |
| smart WMS 的 Loki/Promtail 日志标签、保留期与内存上限调整 | 实战（运维） | smart WMS | 2026-07 | — |

## 我会的部分

### 应用侧接线：starter 与日志桥

- 公共库引 `spring-boot-starter-opentelemetry`（版本由 Boot BOM 管）和 `opentelemetry-logback-appender-1.0`（版本钉在父 POM，2.28.0-alpha，须与 Boot 管的 OTel 版本对齐）（`muou-common/muou-common-app/pom.xml:185-195`；`muou-build/pom.xml:65-66`、`:314-316`）。
- Boot 4 的自动装配拆成了独立模块；照 Boot 3 教程手拼桥接包+导出包会**静默失效**：应用正常启动、接口正常返回、日志正常打印，只是 traceId 槽位永远为空，没有任何警告。实测换成官方 starter 后一行配置没改就生效（`00-16...:75-86`）。
- 日志的 OTLP 通道要单独接：Boot 4 starter 只带日志 SDK，不带 logback 桥接。`OtlpLogbackBridge` 在容器就绪后 `OpenTelemetryAppender.install(openTelemetry)`；拿不到实例只 WARN，不拦启动。接线前 logback 比 Spring 容器早起，appender 默认缓存 1000 条，接上后补发，超出的丢掉（`观测包/OtlpLogbackBridge.java:9-32`）。
- 自动配置类名必须是 ASCII、且排在 OTel SDK 自动配置之后；`@ConditionalOnClass` 只看 logback appender 在不在，`ObjectProvider` 拿不到实例时给明确告警，而不是被条件静默跳过（`观测包/MuouObservabilityAutoConfiguration.java:10-23`）。

### traceId：一处取号，四个入口共用

- 优先级：业务上下文 → 当前 span → 日志上下文 → `X-Muou-Trace-Id` → W3C `traceparent` → 新生成；业务上下文排第一，因为审计表、发件箱表、出站头用的是同一个值（`观测包/MuouTraceResolver.java:10-18`、`:29-37`）。
- 入站请求先看「本请求已解析过的属性」，避免入站过滤器、签发过滤器、出站拦截器各问一次就各生成一个新号；没有合法值才生成（`MuouTraceResolver.java:54-82`）。
- 没有 Tracer 时降级为「只生成号」：不抛、不拦启动，但要清楚代价——日志里的号与链路后端的号对不上，跨服务父子关系也没有（`观测包/MuouTraceAutoConfiguration.java:18-32`）。
- 异步入口：`TraceScope.open(traceId)` 把号挂到当前线程 MDC，close 还原；`callAsSystemTask` 给定时任务/手工补跑用，已有上下文就沿用（手工补跑要串回触发它的请求），没有才造 system 上下文（`观测包/TraceScope.java:12-17`、`:36-67`）。
- outbox 投递/消费都用 `TraceScope` 续链路：投递时 `TraceScope.open(message.traceId())`，消费侧先用消息头的 traceId 开 scope 再进事务；消息头里的 traceId 为空时现造一个，不让日志断链（`muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcher.java:138`；`muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxMessageConsumerSupport.java:52-60`）。

### 日志：固定字段 + 脱敏 + 一行一条

- JSON 编码器不是 logback 自带 `JsonEncoder` 的原样：它写 `timestamp/threadName/loggerName/message` 和 `mdc` 子对象，项目要的是 `ts/thread/logger/msg` 且 `traceId/tenantId/operatorId` 平铺顶层；字段名写死在父类里、时间格式不可配，所以继承后关掉内置字段、自己写（`观测包/MuouJsonEncoder.java:14-31`）。
- 固定字段：`ts`（东八区 ISO-8601，不跟随机器时区）、`service`、`traceId`、`tenantId`、`operatorId`、`logger`、`thread`、`msg`；取不到的字段写空串，不省略——Loki 按字段取列，少一个字段会让后面所有列错位，而错位在查询结果里看不出来（`MuouJsonEncoder.java:38-52`、`:98-120`）。
- MDC 取事件自带的快照，不读当前线程：异步出口下两者会不一样，读当前线程会让这行带上「写出去那一刻」的租户，而不是这条日志真正属于的租户（`MuouJsonEncoder.java:102-104`）。
- 脱敏两道防线：第一道是 `@Pii` 注解管对象序列化；第二道是 `PiiMaskingConverter` 对整条正文按正则扫邮箱/HKID/手机号，管 `log.info("用户 " + phone)` 这种拼接。宁可误伤（八位订单号被当手机号打码），不能泄露（`观测包/PiiMaskingConverter.java:9-21`、`:54-61`）。
- 异常也在射程内：OTel 日志管线会把原始异常写成 `exception.message`/`exception.stacktrace`，绕开正文打码；`PiiMaskingOtelAppender` 复制事件、不带走 `ThrowableProxy`，把异常渲染成文本、打码后接在正文后面，栈与类型一行不少（`观测包/PiiMaskingOtelAppender.java:12-23`、`:55-61`）。
- 脱敏正则带长度上界并用 possessive 量词：日志里常有 JWT/base64/整段 JSON，没有上界的量词会从每个起点重试，对几千字节 token 是平方级耗时，而这个 converter 挂在每条日志的同步路径上（`PiiMaskingConverter.java:25-35`）。

### 采集端与后端

- Collector 收 OTLP gRPC/HTTP（4317/4318），`batch` 批量发送，`memory_limiter` 1 秒检查、75% 上限、15% spike；三条 pipeline 分别把 traces 送 Tempo、logs 送 Loki、metrics 送 Prometheus（`observability/config/otelcol.yaml:1-43`）。
- 为什么中间放 collector：八个服务只认识一个地址，换后端只改 exporters/pipelines；没有它，每换一次后端要改九份应用配置（`observability/docker-compose.yml:22-25`）。
- Grafana 数据源自动配置：Tempo、Loki、Prometheus；Loki 的 `derivedFields` 用正则从日志里抓 32 位 traceId，点一下跳到 Tempo。没有这一段就只是三个各看各的面板（`observability/config/grafana-datasources.yaml:14-21`）。
- 资源上限按实测：空载/偏低负载下 collector 36MB、Grafana 98MB、Tempo 63MB、Loki 71MB、Prometheus 38MB，合计 305MB；上限按 3~6 倍给到 1.6GB（原 4GB，超配十三倍）。测试服务器不到 8GB，还要跑八个服务加网关（`observability/docker-compose.yml:12-18`）。
- Go 组件必须设 `GOMEMLIMIT`：Go 的 GC 默认按 GOGC=100 走，不读 cgroup 内存上限，不设就一路涨到 `mem_limit` 被内核杀掉；Tempo 在测试服务器上实测每 20~30 分钟一轮、7 天杀了 20 次。JVM 服务配 `-XX:MaxRAMPercentage=70` 会读容器上限，所以稳在 35%（`observability/docker-compose.yml:71-80`）。
- 端口一律绑 `127.0.0.1`：里面有全部服务日志与链路，Grafana 默认口令又是弱口令，挂公网等于把内部调用关系和日志正文一起交出去（`observability/docker-compose.yml:12-13`）。

### smart WMS：只有日志栈，没有链路/指标

- wms3 的栈是 Loki 3.4.2 + Promtail 3.4.2 + Grafana 11.6.0；Promtail 读挂载的 `app.log`，按 JSON 解析 `level/logger/message/thread/stackTrace/timestamp`，`host` 标签取容器名，多副本才分得清来源（`wms3/docker/docker-compose.yml:22-66`；`wms3/docker/promtail-config.yaml:11-38`）。
- Promtail 启动必须带 `-config.expand-env=true`，否则 `${HOSTNAME}` 不展开，原样写成字面量落进 Loki 标签（`wms3/docker/docker-compose.yml:42-44`）。
- Loki 保留期 744 小时（31 天），单查询最多 5000 行，拒绝 168 小时前的旧样本；文件系统存储 + TSDB 索引（`wms3/docker/loki-config.yaml:33-41`）。
- Grafana 只配了 Loki 数据源，没有 Tempo/Prometheus；这套的定位是「能按字段查日志」，不是全链路可观测。为什么不做全栈：wms3 是单体，链路收益低，日志已经能定位；加 Tempo/Prometheus 要多两个组件和内存，测试服务器扛不住。
- Grafana 在这个编排里匿名 Admin（`GF_AUTH_ANONYMOUS_ORG_ROLE=Admin`），只适合内网/本机；muou 那套已改成默认关闭匿名、口令必填。

## 选型与取舍

### 为什么应用侧选 Boot 4 官方 OTel starter

| 方案 | 加权分 | 优势 | 代价 | 项目里的位置 |
| --- | ---: | --- | --- | --- |
| Boot 4 官方 OTel starter | 5.00 | OTLP 厂商中立、版本由 Boot BOM 管、业务零改动、定时任务也覆盖 | 日志要另加 logback 桥接 | 选定 |
| Boot 3 手拼桥接包+导出包 | 3.90 | 构件相同 | 在 Boot 4.1.1 上静默失效，traceId 永远为空 | 未选 |
| Zipkin starter | 3.65 | 机制同 OTel | 协议生态窄，云托管入口基本是 OTLP | 未选 |
| OTel Java Agent | 4.05 | 不改代码/依赖 | 自己一条版本线，对新运行时适配滞后 | 未选 |
| SkyWalking Agent | 2.85 | 功能全 | 私有协议，换后端等于换 agent | 未选 |
| 只做 MDC | 2.00 | 最轻 | 定时任务覆盖不到，跨服务串不起来 | 未选 |

真正的单向门是「协议」不是「产品」：选 OTLP，后端可以换；选 SkyWalking 私有协议，换后端要重接。Agent 看起来更省事，但它自己一条版本线，项目用 Boot 4.1.1 + Java 21 这种新组合，适配滞后风险高（`00-16...:34-67`）。

### 为什么开发测试用 Grafana 系，生产不定

- 开发测试要自建、轻量、能看三种信号：Grafana 系收 OTLP、组件齐、许可可接受（AGPL v3）；ELK 最重、Jaeger 只有链路、SigNoz 部分功能商业授权。
- 生产按「买哪朵云」再定：云托管基本都提供 OTLP 入口，应用侧不用改；现在定死反而绑住采购。
- 代价：开发测试要维护四个组件（Tempo/Loki/Prometheus/Grafana）+ collector；生产迁移时日志/指标/链路的保留期、权限、告警要重新配（`00-16...:90-118`）。

### 为什么中间放 collector，不让应用直连后端

- 应用只认识一个 OTLP 端点；换 Tempo/Loki/Prometheus/云，只改 collector 配置，八个服务一个字不动。
- 采集端还能做批量、内存兜底、统一加资源属性/采样（当前没做采样）；应用侧保持简单。
- 代价：多一个组件、多一跳网络、多一份内存；collector 挂了虽然应用照常返回 200（实测），但观测数据会丢。当前接受这个代价（`00-16...:100-102`；`observability/config/otelcol.yaml:1-3`）。

### 为什么 muou 用 OTLP 日志，smart 用 Promtail 读文件

- muou 是新栈，应用侧已经接 OTel，日志走 OTLP 能和 trace 共用一套上下文、字段固定、不用在宿主机挂日志目录；代价是应用要加 appender/桥接，日志在进程内先脱敏。
- smart 是已有单体，日志已经写 JSON 文件，Promtail 直接读文件、零应用改动；代价是日志与 trace 不共享上下文（这套也没有 trace），字段靠文件格式约定，脱敏只能在应用日志格式里做。
- 两条路没有绝对优劣：新项目、要多信号关联 → OTLP；老项目、只要日志检索 → Promtail 更省事。muou 的 OTLP 方案也能被 Promtail 替代，但会丢掉 traceId 自动关联。

### 为什么采样率先设 1.0

- 采样率必须全链路一致，最简单的一致取法就是都设 1.0；中间某一跳不同会导致链路缺一段且不报错。
- 代价：流量上来后存储/带宽成本线性增长；没有 tail sampling，错误请求可能被采样掉（当前全采不会）。
- 现在没有量的实测，定不了比例；等有生产流量再按错误率/延迟分位做尾部采样（`seed-service-configs.sh:1449-1454`；`00-16...` 待办第 3 条）。

### 为什么脱敏在应用侧，不在 collector

- 日志在离开进程前就必须脱敏：collector 可能被绕过（本地直接看文件、临时加一个 exporter）、也可能配错；应用侧是最后一道能保证的关口。
- 代价：每条日志多一次正则扫描，长 token 可能拖慢同步路径；所以正则带上界、possessive、无 `@` 早退。
- 如果只在自己可控的 collector 里脱敏，应用侧更轻；但 PII 泄露的代价更高，当前选应用侧（`观测包/PiiMaskingConverter.java:9-35`）。

### 什么条件下会反悔

- 生产买了云托管、且只收 OTLP → 删掉自建 Tempo/Loki/Prometheus，只留 collector 指向云；应用不改。
- 日志量/成本超出全采承受 → 上尾部采样/分级保留；当前全采。
- 需要 profiling/持续剖析 → 加 Pyroscope/OTel profiling，当前没有。
- smart WMS 也要链路 → 加 Tempo/OTel agent 或 SDK，当前只有日志。
- collector 成为瓶颈/单点 → 多副本 + 负载均衡；当前单实例。

## 边界

- 生产可观测后端未定：开发测试自建，生产跟云采购一起定；没有生产环境的保留期/告警/值班配置。
- 没有告警规则/SLO/错误预算；Grafana 只有看板和数据源，没有 Alertmanager/PagerDuty 接入。
- 没有采样调优/尾部采样；`probability: 1.0` 全采，没有流量/成本数据。
- 没有 profiling、没有 exemplars、没有日志派生指标、没有 RUM/前端监控。
- smart WMS 只有日志栈，没有 trace/metrics；Grafana 匿名 Admin 只适合内网。
- 没有 collector 高可用/多副本；没有跨机房/跨云链路。
- 没有长期存储/冷归档；Loki 保留 31 天（smart）或按环境配（muou），Tempo 没有长期后端。
- OTel logback appender 是 2.28.0-alpha，升级要跟 Boot 管的 OTel 版本对齐；没有做过跨版本升级演练。

## 相关技能

- [[中间件与异步任务]]、链路追踪（待建）
- [[安全与审计]]（PII 脱敏、日志合规）
- [[CI-CD与部署]]（collector/后端编排、内存上限）
- [[Sentinel]]（限流/熔断指标）
- [[Spring Boot]]（自动装配、Actuator）

## 用在哪些工程能力

- 分布式链路追踪与日志关联
- 结构化日志与 PII 脱敏
- 指标采集与看板
- 可观测后端选型与运维
