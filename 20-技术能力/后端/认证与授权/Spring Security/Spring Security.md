---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战/设计
---

# Spring Security

所属通用技能：[[认证与授权]]

**一句话**：用 Spring Security 6 的过滤器链做无状态 JWT 认证，把用户上下文塞进 `SecurityContextHolder`，并为 URL 级和方法级授权留好扩展点。

## 方法总纲

1. **配置一条链**：`SecurityFilterChain` 统一管 CORS、CSRF、Session 策略、公开路径和异常处理；纯 API 项目关闭 CSRF、设为 `STATELESS`。
2. **认证放在过滤器**：自定义 `OncePerRequestFilter` 解析 token、做业务校验（版本/单端/状态），构造 `Authentication` 写入 `SecurityContextHolder`；失败只写 request attribute，交给 `AuthenticationEntryPoint` 统一出 401。
3. **上下文只放快照**：principal 用 `LoginCtxDto`，权限同时放 `GrantedAuthority`（`menuPerms` + `ROLE_*`）；业务代码从 `LoginContext` 读，不直接依赖 Security 的 ThreadLocal。
4. **授权分两层**：URL 级用自定义 Filter 匹配权限码；方法级用 `@PreAuthorize("hasPermission(...)")` + 自定义 `PermissionEvaluator`。两层权限都来自同一批角色绑定数据：`apiPerms` 用于 URL，`menuPerms` 用于菜单和方法码。
5. **异常统一格式**：401 走 `AuthenticationEntryPoint`，403 走 `AccessDeniedHandler`，响应体保持项目统一的 `Result` 结构。
6. **CORS 显式配置**：`allowCredentials(true)` 与通配 `*` 互斥，配置成 `*` 在启动期直接失败。

## 我用它干过什么

时间说明：`smart` 目录不是 git 仓库，2026-05 按计划文档日期推断，不是提交记录。

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| `SecurityFilterChain` 迁移（自定义 Filter → Spring Security；`smart-server-wms3/src/main/java/com/track/wms/config/SecurityConfig.java:47-67`） | 实战 | [[smart WMS]] | 2026-05 | — |
| JWT 认证过滤器（`smart-server-wms3/src/main/java/com/track/wms/config/JwtSecurityFilter.java:73-188`） | 实战 | [[smart WMS]] | 2026-05 | [[登录态与踢线]]、[[keyVer踢线校验]] |
| 代登录 actor/effective 双 keyVer 校验（`smart-server-wms3/src/main/java/com/track/wms/service/impl/ImpersonateServiceImpl.java:70-143`、`smart-server-wms3/src/main/java/com/track/wms/config/JwtSecurityFilter.java:245-259`） | 实战 | [[smart WMS]] | 2026-05 | [[登录态与踢线]] |
| 角色 scope + `can_use/can_grant` 权限模型（`smart-server-wms3/src/main/resources/db/sql/update-init.sql:54,69-70`、`smart-server-wms3/src/main/java/com/track/wms/service/impl/SysRoleServiceImpl.java:305-329`） | 部分落地 | [[smart WMS]] | 2026-05 | [[权限模型]]、[[RBAC权限模型]]、[[权限模型迁移]] |
| `@PreAuthorize` + `PermEvaluator` 方法级授权（`smart-server-wms3/src/main/java/com/track/wms/config/PermEvaluator.java:16-29`，无调用方） | 设计/未接线 | [[smart WMS]] | 2026-05 | [[权限模型]] |

## 选型与取舍

### 为什么用 Spring Security，不用自写过滤器 / Shiro / Sa-Token

| 方案 | 优点 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| 自写 Filter | 逻辑透明、依赖少 | 认证入口、异常分流、CORS、方法级授权都要自己写；漏一个分支就是 401/403 不一致 | 2026-05 之前 |
| Spring Security | 过滤器链、EntryPoint/DeniedHandler、方法级授权、测试支持 | 学习曲线陡；配置错会静默放行/全拦；版本升级有 breaking change | 2026-05 迁移后 |
| Shiro | 轻量、API 直观 | 方法级/表达式能力弱；与 Spring Boot 3 生态整合不如 Security | 未使用 |
| Sa-Token | 国内生态、登录/踢线开箱即用 | 强绑定自己的会话模型；复杂授权要扩展 | 未使用 |

项目从自写 Filter 迁到 Spring Security，是为了统一认证入口、异常出口和方法级授权扩展点（`SecurityConfig.java:47-67`、`JwtSecurityFilter.java:73-188`）。代价是 Security 的过滤器顺序和上下文传播成为必须理解的部分；页面里的「先配置一条链」「认证放过滤器」就是这次迁移的产物。Shiro/Sa-Token 不是不能做，是项目已经有 Security 的迁移成果，再换一套不划算。

### 为什么用无状态 JWT，不用 Session

- JWT 的优点是服务端不存会话、横向扩展不用共享 Session；代价是不能撤回，所以项目把 keyVer/jti 放 Redis，做单端登录、踢线和权限变更生效（`JwtSecurityFilter.java:112-136`）。
- 这不是「纯无状态」：身份在 JWT，撤销状态在 Redis；Redis 不可用时按路径分流——单端登录/effective user 降级放过，actor keyVer 严格拒绝（`:136`、`:240-259`）。
- 如果业务能接受 Session + Redis 共享，Session 更简单；项目选 JWT，是为了网关/多服务横向扩展和跨端携带。

### 为什么 URL 级和方法级两层授权

- URL 级 `ApiPermFilter` 集中管接口权限，适合「一个 URL 一个权限码」的粗粒度；方法级 `@PreAuthorize` 适合服务内部复用、细粒度判断。两层共用角色绑定数据，避免两套权限来源。
- 现状要看清：`api-perm-enabled: false`，全项目零 `@PreAuthorize`，方法级只有装配没有调用方（`application.yml:183`、`PermEvaluator.java:16-29`）。所以这是「代码具备的能力」，不是线上已生效的授权；页面边界必须这么写。
- 代价：两层都开时，权限码要同时维护 URL 和菜单/方法映射；漏一处就会出现「菜单看得见、接口调不动」或相反。

### 为什么关 CSRF、不用 OAuth2/OIDC

- 纯 API + Bearer token，不靠 Cookie 自动携带，CSRF 不适用；如果改成 Cookie/Session 认证，必须重新打开 CSRF，否则是漏洞。
- OAuth2/OIDC/SSO 没做，是因为当前是自有账号体系，没有第三方身份提供方需求；接入的代价是授权服务器/客户端注册/token 校验链路，不是加一个依赖。如果要做 B2B SSO 或开放平台，再评估。

### 什么条件下会反悔

- 需要第三方登录/SSO → 引入 OAuth2/OIDC，现有 JWT 过滤器要改成资源服务器校验。
- 需要更强的方法级授权 → 打开 `api-perm-enabled`、补 `@PreAuthorize` 调用和权限码测试；当前是未接线状态。
- Redis 不可用不可接受 → 把 keyVer 校验改成 fail-closed，或本地缓存 + 短 TTL；当前是按路径降级。

## 我会的部分

- 写 `SecurityFilterChain`：公开路径、`STATELESS`、CSRF 关闭、Filter 顺序、EntryPoint/DeniedHandler。
- 写 JWT 过滤器：解析 Bearer、异常分流（过期/非法）、认证成功后构造 `UsernamePasswordAuthenticationToken` 和 authorities。
- 把业务登录上下文（租户、角色、权限码、actor）放进 principal，同时保留请求级上下文给业务代码。
- 用 `PermissionEvaluator` 接 `hasPermission`，知道它读的是 principal 里的权限集合。
- CORS 与凭据的组合限制，以及启动期 fail-fast。
- 用 Mockito 单测覆盖过滤器分支；用 Testcontainers E2E 打开权限开关验证 403/200。

## 边界

- 全项目零 `@PreAuthorize`：方法级授权只有装配，没有实际使用。
- `auth.api-perm-enabled` 在仓库配置里是 `false`（`smart-server-wms3/src/main/resources/application.yml:183`），`ApiPermFilter` 直接放行；只有 E2E 测试把它设为 `true`（`smart-server-wms3/src/test/java/com/track/wms/controller/AuthPermissionE2eTest.java:44`）。所以「接口级权限」当前是代码能力，不是线上行为。
- 没做过 OAuth2 / OIDC / SSO、表单登录、CSRF 防护、Remember-Me、分布式 Session。
- Redis 不可用时，keyVer 和单端登录校验会降级放过（靠 DB 状态兜底）；代登录 actor 校验则 fail-closed。这是取舍，不是强一致。
- 没做过 Spring Security 的异步上下文传播专项；异步导出用 `ScopedValue` 另注入 `LoginCtxDto`（`smart-server-wms3/src/main/java/com/track/wms/common/context/LoginContext.java:19-35`）。

## 相关技能

[[RBAC权限模型]]、[[keyVer踢线校验]]、JWT（待建）、Redis（待建）、多租户数据隔离（待建）
- 理论：[[安全工程理论]]

## 用在哪些工程能力

权限模型设计与落地（部分落地，工程能力卡未建）；登录态与踢线、代登录是本项目实践，不另建工程能力卡
