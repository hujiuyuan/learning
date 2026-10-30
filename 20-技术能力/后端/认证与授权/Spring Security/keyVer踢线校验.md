---
type: 方法
技能点: Spring Security
域: 后端
证据: 实战/设计
---

# keyVer 踢线校验

技能点：[[Spring Security]] · 通用技能：[[认证与授权]]

**一句话**：token 里带签发时的版本号，Redis 里存当前版本；两者不等就失效。改密、禁用、他端登录只需改 Redis，不用等 token 过期。

## 方法总纲

1. **按端分版本**：`user:key:{userId}:{loginSys}`，WMS 和 PDA 各自独立，踢一端不影响另一端。
2. **签发时写版本**：登录/刷新把当前 keyVer 签进 token；刷新时对齐最新值。
3. **每次请求比对**：过滤器读 Redis 当前版本，与 token 里的版本比对；不等就按踢线原因返回。
4. **变更时 bump 或删**：他端登录、改密用自增；禁用/删除直接删 key，让所有已签发 token（含代登录 actor）一起失效。
5. **留原因**：同时写踢线原因，前端才能区分「账号被禁用」「密码已改」「他端登录」。

## 实际使用

- **校验入口**：`checkEffKey` 比对 `token.keyVer` 与 `redis.atomicGet(userKey)`；不一致时读踢线原因，映射成对应错误码（`JwtSecurityFilter.java:206-237`）。
- **按端隔离**：`sysOf(claim)` 取 token 的 `loginSys`，默认 WMS；同一用户跨端互不影响（`:200-203`）。
- **自增**：`bumpKeyVer` 用 `atomicIncr`，TTL 跟 refresh 有效期；同时写踢线原因，TTL 为 access+60 秒（`UserServiceImpl.java:853-870`）。
- **全端旋转**：`bumpKeyVerAll` 遍历所有登录端（`:872-879`）；改密还配合 `clearOwnRefresh` 清 refresh 槽（`:881-901`）。
- **永久作废**：`revokeAllTokens` 删各端 key、清 refresh、写墓碑，并踢掉正在 impersonate 该用户的管理员（`:903-945`）。
- **代登录**：effective user 用宽松规则（只被账号/租户撤销类原因踢）；actor 用严格比对，Redis 异常直接拒绝（`JwtSecurityFilter.java:111-119,239-259`）。

## 判断顺序

1. 这次变更是「踢一端」还是「踢全端」？选 `bumpKeyVer` 或 `bumpKeyVerAll` / `revokeAllTokens`。
2. 账号还在用吗？改密用 bump + 清 refresh；禁用/删除直接删 key。
3. 要不要留原因？要，前端和 refresh 都靠它给准确文案。
4. 代登录会不会被误伤？effective 的版本 churn 放行，actor 严格；撤销类原因才踢 impersonator。
5. Redis 挂了怎么办？校验降级放过、靠 DB 状态兜底；actor 校验 fail-closed。

## 反例

- 只设 token 过期，不做版本：改密、禁用后旧 token 还能用到过期。
- 所有端共用一个 key：踢 WMS 把 PDA 也踢了。
- bump 不写原因：前端只能显示「登录超时」，用户不知道被禁用还是被顶号。
- 代登录只看 effective keyVer：管理员自己被禁用/改密后，代登录 token 还能用。
- 把 `0==0` 当异常：imp target 从未登录过时两边都是 0，会误杀。

## 边界

- Redis 不可用时 keyVer 和单端登录校验会降级放过（`JwtSecurityFilter.java:233-235`）；这是可用性取舍，不是强一致。
- 代登录 actor 校验 Redis 异常时拒绝（`:252-258`），属于高敏操作宁严勿宽。
- 没做过 Redis 集群故障下的版本一致性专项。
- 没做过 refresh token 轮换的并发压测；60 秒宽限只有代码路径。

## 证据

- [[登录态与踢线]]
- [[代登录实现]]
- `smart-server-wms3/src/main/java/com/track/wms/config/JwtSecurityFilter.java:103-138,200-259`
- `smart-server-wms3/src/main/java/com/track/wms/service/impl/UserServiceImpl.java:853-945`
