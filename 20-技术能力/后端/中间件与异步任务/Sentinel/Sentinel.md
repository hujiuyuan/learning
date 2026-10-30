---
type: 技能点
域: 后端
项目: [muou]
证据: 实战
---

# Sentinel

所属通用技能：[[中间件与异步任务]]

**一句话**：Sentinel 在这套系统里不是「加个注解」，而是公共库里的一段自动装配：Servlet 服务默认装上拦截器，资源名按路由模式归一，来源按 IP（IPv6 归 /64）分桶，规则从 Nacos 的 `<应用名>-flow-rules` / `<应用名>-degrade-rules` 热更新；没有 Nacos 地址时它**完全不生效**，不是「用默认规则」。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/muou-backend/`。简称：`SentinelAutoConfiguration.java` = `muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/ratelimit/SentinelAutoConfiguration.java`；`00-15...` = `muou-app-doc/design/00-技术选型（selection）/00-15-限流熔断组件技术选型.md`；`README.md` = `muou-app-ops/middleware/sentinel/README.md`；`seed-service-configs.sh` = `muou-app-ops/middleware/nacos/seed-service-configs.sh`。

**归属说明**：`SentinelAutoConfiguration`、规则解析/来源分桶与主要测试由本人提交；规则种子脚本与 Sentinel 控制台运维文档也由本人维护，个别测试后续被同事改过。

## 方法总纲

1. **规则源只有一个**：Nacos 分组 `SENTINEL_GROUP`，dataId `<应用名>-flow-rules` 与 `<应用名>-degrade-rules`，内容是 Sentinel 规则对象的 JSON 数组；控制台与八个服务共用这一份契约。
2. **热更新靠订阅**：`NacosDataSource` 注册到 `FlowRuleManager` / `DegradeRuleManager`，Nacos 推新规则就生效，不重启、不发版。
3. **没规则源 = 完全不生效**：没有 Nacos 地址或没有应用名时只打 WARN，不装「默认规则」；这是失败方向，必须能从日志看出来。
4. **规则写坏保留上一版**：解析异常直接抛，Sentinel 的 Nacos 数据源不会用坏内容覆盖旧规则；返回「空规则」会清空限流，违背「宁可误拒，不能放空」。
5. **资源名按路由模式归一**：用 `HandlerMapping.BEST_MATCHING_PATTERN_ATTRIBUTE` 取 `/api/v1/persons/{personId}`，不按具体 URL；否则资源数随数据量膨胀，规则没法写。
6. **来源按 IP 分桶**：优先 `X-Real-IP`，IPv6 归到 /64；不归的话一个访客随手换地址就等于没限过。
7. **拦截器排最前**：`Ordered.HIGHEST_PRECEDENCE`，在会话解析之前；垃圾请求先被限流挡掉，不用先付一次查会话的代价。
8. **429 走统一返回体**：`Retry-After: 1`，body 是公共库的 `RATE_LIMITED`（`99429000`），不暴露是哪一层挡的。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 公共库 Sentinel 自动装配：Servlet 默认装、拦截器、429 返回体 | 实战 | muou | 2026-09 | 限流熔断（待建） |
| Nacos 规则订阅、启动主动读一次、坏规则保留旧版 | 实战 | muou | 2026-09 | 限流熔断（待建） |
| 来源分桶：`X-Real-IP` + IPv6 /64 | 实战 | muou | 2026-09 | 限流熔断（待建） |
| 流控/熔断规则种子：公开端点、登录接口、服务间慢调用/异常比例 | 实战 | muou | 2026-09~10 | 限流熔断（待建） |
| 控制台改造与运维：规则写 Nacos、命名空间/端口/鉴权 | 实战 | muou | 2026-09 | — |

## 我会的部分

### 自动装配与拦截器

- 只对 Servlet Web 应用生效，`muou.sentinel.enabled` 默认 true；定时任务那类非 Web 进程不装（`muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/ratelimit/SentinelAutoConfiguration.java:51-54`；`SentinelAutoConfigurationTest.java:30-58`）。
- 系统属性必须在构造函数里设：`project.name`、`csp.sentinel.api.port`、`csp.sentinel.dashboard.server`、日志目录；挪到 `@Bean` 里就晚了，Sentinel 的 `SentinelConfig` 类加载时已定型（`SentinelAutoConfiguration.java:80-100`；`README.md:149-151`）。
- 启动时显式 `InitExecutor.doInit()`：Sentinel 默认懒初始化，要等第一个请求穿过拦截器才连控制台；actuator 不走这个拦截器，健康检查打再多也不触发，控制台应用列表里就没有它（`SentinelAutoConfiguration.java:267-272`；`README.md:140-147`）。
- 拦截器装在 `/**`，`order(HIGHEST_PRECEDENCE)`；`setHttpMethodSpecify(false)`，同一路径的 POST/GET 共用一个资源，免登录路径上新加的 POST 也照样被限（`SentinelAutoConfiguration.java:104-124`）。
- 429 出口：`Retry-After: 1` + `ApiResponseWriter.write(RATE_LIMITED)`，形状与其他接口一致；不返回配额头、不说明哪一层挡的（`SentinelAutoConfiguration.java:115-119`）。

### 资源名与来源

- 资源名重写：`RoutePatternInterceptor` 取 `BEST_MATCHING_PATTERN_ATTRIBUTE`，拿不到才回退父类；用 10 个不同 id 打同一路径变量接口，控制台只出现一个资源（`SentinelAutoConfiguration.java:130-143`；`README.md` 资源名归一实测段）。
- 来源：优先 `X-Real-IP`，否则 `remoteAddr`；IPv6 只接受十六进制/冒号/点/百分号的字面量，去掉 zone 后缀后归到前 4 个 16 位分组（`/64`），IPv4 映射地址按 IPv4 处理（`SentinelAutoConfiguration.java:146-199`）。
- 为什么必须归一 IPv6：一段 /64 里有 2^64 个地址，照原样当来源等于没限过；归到 /64 后来源节点数才跟真实访客数走。

### Nacos 规则源

- dataId 约定：`appName + "-flow-rules"`、`appName + "-degrade-rules"`；`appName` 取 `muou.sentinel.app-name`，留空回退 `spring.application.name`（`SentinelAutoConfiguration.java:220-228`；`SentinelProperties.java:23-33`）。
- 没有 Nacos 地址：只 WARN「限流熔断此时是**完全不生效**的，不是用默认规则」，然后 return；没有应用名同理（`SentinelAutoConfiguration.java:204-214`；`SentinelRuleAndBlockTest.java:100-120`）。
- 订阅后主动 `loadConfig()` 读一次：Nacos 连不上时客户端不抛异常、只读回空，订阅本身照样「成功」；不读这一次，日志里只有「已订阅」，看不出一条规则都没拿到。读回空/抛异常都 WARN（`SentinelAutoConfiguration.java:250-265`；`SentinelRuleAndBlockTest.java:191-223`）。
- 解析失败：抛异常并保留上一版；同一份坏原文只打一次 ERROR，因为 Nacos 客户端会约每 5 秒重投同一版。空内容/null 按「没有规则」处理（`SentinelAutoConfiguration.java:274-302`；`SentinelRuleAndBlockTest.java:153-189`）。
- 规则解析用 Jackson 3，不用 fastjson；fastjson 只允许作为 Sentinel 的传递依赖存在（`SentinelAutoConfiguration.java:68-71`；`00-15-限流熔断组件技术选型.md:90-94`）。

### 规则内容

- 流控：五个公开端点 + 两条登录接口，来源 `limitApp=other`（按 IP 各分各的桶），阈值 1~2 次/秒/来源/实例；`resource` 必须是网关 StripPrefix 之后服务实际收到的路由模式（`muou-app-ops/middleware/nacos/seed-service-configs.sh:2054-2071`）。
- 为什么按 IP 分桶：登录/注册/邀请接口要防单来源刷；按全局 QPS 限会把正常用户一起挡。
- 熔断：每个服务对每个远程组两条规则——慢调用比例（超过 `slow_call_ms` 算慢、占 80%）与异常比例（50%），统计窗 60 秒、最少 10 次、熔断 30 秒；网关也在熔断名单里（`seed-service-configs.sh:2032-2051`）。
- 种子写入策略：local 每次覆盖；其余命名空间只在配置不存在或内容是 `[]` 时写，避免冲掉控制台调过的阈值；查询失败不能当成「不存在」去写（`seed-service-configs.sh:2074-2121`）。

### 控制台与运维

- 上游控制台改规则只推某实例内存，实例重启就没了，也不写 Nacos；服务侧从 Nacos 读规则，两边会分叉且不报错。项目改造源码重新打包成 `sentinel-dashboard-nacos:1.8.9-muou.2`，只覆盖流控/熔断两类，热点/系统/授权/集群流控页面摘掉（`muou-app-ops/middleware/sentinel/README.md:35-55`）。
- 改造镜像的源码不在本仓库、也没推远端，目前由 hjy 保管；丢了就无法重建、上游安全补丁也无法跟进（`00-15...:96-100`）。
- 端口：控制台 8858；客户端 api-port 同机必须错开，iam 8711、member 8712、billing 8713、flow 8714、content 8715、notify 8716、platform 8717；端口被占 Sentinel 自己 +1 且不提示，控制台就连错端口、实时监控为空（`README.md:135-138`）。
- `nacos-client` 必须显式钉 3.1.1：`sentinel-datasource-nacos:1.8.9` 会把它钉在 1.4.2，而 1.4.2 走 Nacos v1 HTTP 配置接口，在 Nacos 3.2.4 上已 404（`GET /nacos/v1/cs/configs`）（`muou-build/pom.xml:78-79`；`README.md:153-163`）。
- fastjson 是连控制台躲不掉的传递依赖，`sentinel-transport-simple-http` 的八个命令处理类编译期用它；排掉会导致控制台点「簇点链路」`NoClassDefFoundError`。父 POM 的禁令收窄为「只禁第一代 1.2.x」，版本钉 2.0.65（`00-15...:90-94`；`muou-build/pom.xml:71-72`）。

## 选型与取舍

### 为什么选 Sentinel，不选 Resilience4j/自研

| 方案 | 加权分 | 优势 | 代价 | 项目里的位置 |
| --- | ---: | --- | --- | --- |
| Sentinel 1.8.9 | 4.00 | 规则放 Nacos 热更新；MVC/Dubbo/gRPC 适配器齐；控制台看实时 QPS | 多一个自维护控制台镜像；fastjson 传递依赖；要自己写拦截器 | 选定 |
| Resilience4j | 2.85 | 轻、无额外部署件、无 fastjson | 规则在代码/配置文件，改完必须重启 | 未选 |
| 自研 | 2.85 | 无外部依赖、无供应链风险 | 热更新、指标、控制台三样都要自己造 | 未选 |

决策驱动因素里「规则热更新」占 35%，因为业务痛点就是「接口被刷时要在不发版的前提下立刻调阈值」。Resilience4j 在运维复杂度、供应链上更好，但它做不到热更新，直接出局；自研能实现，但三样基础设施的成本远高于引一个组件。这不是「Sentinel 更先进」，是「这次要的能力它独有」（`00-15...:25-32`、`:50-66`）。

### 为什么不走 Spring Cloud Alibaba

- Spring Cloud Alibaba 当前版本写死只接受 Spring Boot 4.0.x，项目是 Boot 4.1.1；用它就要被它的版本节奏绑住。
- 直接引 `sentinel-core` + `sentinel-spring-webmvc-v6x-adapter` + `sentinel-transport-simple-http` + `sentinel-datasource-nacos`，自己写几十行拦截器注册，版本与 Boot 解耦。
- 代价：适配器/自动装配要自己维护；好处是升级 Boot 不用等 SCA 发版（`00-15...:8-10`、`:54`、`:64-66`；`muou-build/pom.xml:287-311`）。

### 为什么改控制台源码，不直接用原版

- 原版控制台把规则推进某个实例内存，不写 Nacos；服务侧从 Nacos 读规则，控制台上看到的和实际生效的分叉，两边都不报错。直接部署原版比不部署更糟。
- 改造后控制台写 Nacos，规则持久化、重启不丢、多实例一致；代价是多一个自维护镜像、要跟上游打安全补丁、源码目前没进远端仓库。
- 如果不需要控制台、只手工写 Nacos，可以省掉这个镜像；但运营改阈值需要界面，当前保留（`README.md:35-55`；`00-15...:84-100`）。

### 为什么限流点在服务侧，不在网关

- 规则只下发给七个业务服务（`seed_flow_rules` 的 `SERVICES`），网关只配服务间调用的熔断规则（`seed_degrade_rules` 包含 `gateway`）。服务侧限流覆盖所有调用方：外部走网关、内部服务直连也照样被限；只靠网关会漏掉内网直连。
- 代价：每个服务都要装拦截器、规则要按服务分别配；网关层没有统一的全局限流视图。
- 如果只需要挡公网流量、内部调用可信，网关限流更集中；当前内部调用也走同一套服务，选服务侧（`seed-service-configs.sh:2032-2071`；`00-15...:80`）。

### 为什么接受 fastjson 传递依赖

- `sentinel-transport-simple-http` 的命令处理类编译期依赖 fastjson，排掉会在控制台「簇点链路」处 `NoClassDefFoundError`，坏得比不接更隐蔽。
- 父 POM 原禁令是「fastjson 一律不许进来」，为 Sentinel 收窄成「只禁第一代 1.2.x」，钉无已知漏洞的 2.0.65（fastjson2 兼容包）；规则解析仍用 Jackson，自己的代码一行不 import fastjson。
- 代价：类路径多一棵要盯的依赖树；如果哪天 Sentinel 换掉 fastjson 或提供无 fastjson 的传输构件，应该收回这条妥协（`00-15...:90-94`；`muou-build/pom.xml:71-72`）。

### 什么条件下会反悔

- 不需要热更新、规则可以跟发版走 → 换 Resilience4j，少一个控制台和 fastjson；改造成本约两人日。
- 改造镜像源码丢失/无法跟进上游安全补丁 → 要么找回源码建远端仓库，要么放弃控制台、只保留 Nacos 手工规则。
- 需要集群流控/热点参数/系统规则 → 当前改造只覆盖流控与熔断，另外四类页面已摘掉；要用得先补改造。
- 规则规模/服务数继续增长 → 评估规则分组、按命名空间隔离；当前八个服务各自 dataId。

## 边界

- 没有生产压测/阈值调优：规则阈值来自设计（99-01），不是压测结果；没有 QPS/延迟基线。
- 没有集群流控、热点参数、系统规则、授权规则的实战；控制台这几页被摘掉。
- 没有 Sentinel 控制台的高可用/多副本；本地与测试各一个实例。
- 没有改过 Sentinel 核心源码；只改控制台（源码不在本仓库）。
- 没有做过网关全局限流；限流点在服务侧，网关只有服务间熔断。
- 没有做过规则灰度/回滚演练；规则写坏靠「保留上一版」兜底，没有自动回滚。
- 没有真实故障注入验证熔断恢复；只有单测里的规则解析/保留旧版验证。
- 429 返回体是 muou 八位码；档案服务单独接了一份，字符串码，契约只在 Nacos 规则位置一致。

## 相关技能

- [[中间件与异步任务]]、限流熔断（待建）
- [[Nacos]]（配置源、命名空间、鉴权）
- [[Spring Cloud Gateway]]（网关与服务侧限流的分工）
- [[可观测性与OpenTelemetry]]（限流/熔断指标与控制台）
- [[Spring Boot]]（自动装配、Servlet 条件）

## 用在哪些工程能力

- 接口限流与熔断降级
- 规则热更新与配置中心
- 多租户/多服务入口保护
- 控制台运维与供应链权衡
