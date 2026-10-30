---
type: 技能点
域: 后端
项目: [muou]
证据: 实战
---

# Spring Cloud Gateway

所属通用技能：[[Spring应用与接口契约]]、[[中间件与异步任务]]

**一句话**：muou 的网关是 **Spring Cloud Gateway Server WebMVC（Servlet 栈）**，不是 WebFlux 版；它在转发前做登录态、租户入口、模块门控、内部路径拦截和 TraceId。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/muou-backend/muou-server-gateway/`。

## 方法总纲

1. **先确认栈**：`spring-cloud-starter-gateway-server-webmvc` 是 Servlet 栈，过滤器是 `OncePerRequestFilter`，不是 WebFlux 的 `GlobalFilter`。
2. **过滤器排序即安全边界**：认证、租户、模块门控、内部路径拒绝各有 order，顺序错了会绕过检查。
3. **配置分两层**：镜像内只放「连 Nacos 前就要用」的项；其余放 Nacos，避免改配置要重新打镜像。
4. **门控按最长前缀匹配**：路径归属模块，再问 platform 该租户有没有开通；表里没有的路径放行，所以只登记能确定归属的路径。
5. **网关不落盘模块状态**：按租户在内存缓存模块清单，TTL 默认 30 秒。
6. **转发前改请求要有边界**：剥路径、加头、藏头、缓存 body 都是包装请求，不能让下游看到网关内部头。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 网关登录态/会话解析 | 实战 | muou | 2026-09 | — |
| 租户入口（域名/路径）识别 | 实战 | muou | 2026-09 | [[多租户与数据隔离]] |
| 模块门控（按租户查模块开通） | 实战 | muou | 2026-09~10 | — |
| 内部路径拒绝、TraceId、上传代理 | 实战 | muou | 2026-09~10 | — |

## 选型与取舍

### 为什么用 Servlet 栈网关，不用 WebFlux 版

- 项目后端是 Spring MVC/Servlet 栈，Servlet 网关的过滤器就是 `OncePerRequestFilter`，和业务服务的过滤器模型一致；排查、测试、线程上下文（`LoginCtxDto`/`ScopedValue`）都复用现有经验。
- WebFlux 版的优势是高并发/流式、非阻塞；代价是整条链路要避免阻塞调用，Redis/JDBC 客户端、线程上下文传播都要重新验证。muou 的网关还要做登录态、租户、模块门控，这些都是短请求，Servlet 栈够用。
- 代价：吞吐上限不如 WebFlux，长连接/流式代理能力弱；如果以后要接 WebSocket/SSE 或高并发 API 网关，再评估 WebFlux。

### 为什么认证/租户/门控放网关，不放每个服务

- 放网关：统一入口、统一顺序（认证 → 租户 → 模块门控 → 内部路径拒绝），服务不用各写一套；新增服务只要注册路由。
- 代价：网关成为单点/瓶颈，过滤器顺序错会绕过检查；服务侧不能假设「网关一定拦住了」，内部调用/直连仍需自己的校验。项目用 `InternalPathDenyFilter` 挡 `/internal`，但这不是服务侧授权的替代。
- 如果团队/服务数量少、网关维护成本高于收益，可以把认证下沉到服务；当前服务多、入口统一，网关集中更划算。

### 为什么模块门控用「路径表 + 30 秒缓存」，不是每请求查库

- 每请求查库会把网关变成 DB 依赖，延迟和故障面都放大；路径表 + 按租户缓存 30 秒，把大部分请求挡在内存里。
- 代价：模块开通/关闭有最多 30 秒延迟；表外路径默认放行（`module-gate-paths.yml:1-20`），是 fail-open 的取舍——只登记能确定归属的路径，未登记的不误杀，但也可能漏拦。
- 如果要严格门控，应该改成「默认拒绝 + 显式放行」，代价是新路径上线必须登记，漏登记会 403；当前选择的是可用性优先。

### 为什么配置分「镜像内」和 Nacos 两层

- 连 Nacos 之前就要用的配置（Nacos 地址、应用名）必须在镜像/本地配置里；其余放 Nacos，改配置不用重新打镜像。
- 代价：配置来源多，排查要看导入顺序（`application.yml:9-16`：仓内 `module-gate-paths.yml` → Nacos `common.yaml` → `gateway.yaml`，后者覆盖前者）；配置漂移要靠启动日志/配置中心版本排查。

### 什么条件下会反悔

- 需要 WebSocket/SSE/高并发流式 → 评估 WebFlux 网关，或把长连接拆到独立入口。
- 模块门控漏拦造成越权 → 改成默认拒绝 + 路径注册校验；当前 fail-open 不满足严格隔离。
- 网关过滤器继续变多、顺序难维护 → 拆成独立网关服务/责任链配置化，或把部分职责下沉到服务。

## 我会的部分

- **Servlet 网关**：依赖 `spring-cloud-starter-gateway-server-webmvc`，不是 `spring-cloud-starter-gateway`（`pom.xml:23`）。
- **过滤器顺序**：`GatewayAuthConfig` 给认证、租户、模块门控等过滤器设 `Ordered.HIGHEST_PRECEDENCE + n`（`src/main/java/com/voidtech/muou/gateway/config/GatewayAuthConfig.java:114-205`）。
- **登录态**：`SessionResolver` 有 Redis 和 DenyAll 两种实现；匿名路径由 `AnonymousPathMatcher` 判断（`src/main/java/com/voidtech/muou/gateway/auth/`）。
- **租户入口**：`TenantHostDirectory` + `TenantPathEntryFilter` 从域名/路径识别租户（`src/main/java/com/voidtech/muou/gateway/tenant/`）。
- **模块门控**：`ModuleGateFilter` 是 `OncePerRequestFilter`（`modulegate/ModuleGateFilter.java:39`）；路径表按最长前缀匹配，表外路径放行（`src/main/resources/module-gate-paths.yml:1-20`）。
- **门控缓存**：按租户缓存模块清单，默认 30 秒（`modulegate/ModuleGateStatusResolver.java:28,45,54`、`application.yml:20-23`）。
- **内部路径拒绝**：`InternalPathDenyFilter` 挡 `/internal` 等入口（`auth/InternalPathDenyFilter.java`）。
- **TraceId**：`TraceIdFilter` 生成/透传 trace id（`trace/TraceIdFilter.java`）。
- **上传代理**：`UploadProxyController` 处理上传转发（`upload/UploadProxyController.java`）。
- **配置导入顺序**：仓内 `module-gate-paths.yml` → Nacos `common.yaml` → Nacos `gateway.yaml`；后者同名 key 覆盖前者（`src/main/resources/application.yml:9-16`）。

## 边界

- 没有做过网关限流、熔断、重试、灰度发布。
- 没有写自定义路由断言/过滤器工厂；只用现成 MVC 网关 + Servlet 过滤器。
- 没有做过多副本网关的会话一致性验证。
- 没有处理过 WebSocket 代理。
- 没有做过网关层的 TLS 终止和证书轮换。

## 相关技能

- [[Nacos]]、[[Redis]]、[[Spring Boot]]、[[Spring MVC]]
- [[多租户与数据隔离]]、[[认证与授权]]
- 理论：[[服务发现与配置理论]]（路由/门控配置的传播延迟与兜底）
- 网关层没有限流/熔断；服务侧限流熔断见 [[Sentinel]]，Boot 4 / Cloud / Alibaba 版本组合见 [[Spring Boot#Boot 4 版本组合（muou）]]

## 用在哪些工程能力

- 统一入口、登录态校验、租户识别
- 模块开通门控
- 内部接口隔离与 TraceId 透传
