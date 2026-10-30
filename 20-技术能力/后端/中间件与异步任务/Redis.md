---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战
---

# Redis

所属通用技能：[[中间件与异步任务]]

**一句话**：Redis 在 smart 里干三件事：共享缓存、登录态/版本号、Redisson 分布式锁与信号量；缓存必须能降级，锁必须带租约。

路径说明：以下路径相对 `smart-server-wms3/src/main/java/com/track/wms/`；配置相对 `smart-server-wms3/src/main/resources/`。

## 方法总纲

1. **缓存是加速层，不是数据源**：GET/PUT/EVICT 失败只记 WARN，回源 DB，不让 Redis 抖动拖成 500。
2. **共享缓存优于本地缓存**：多副本本地缓存会长期分叉；改 Redis 共享 key，要么都旧要么都新。
3. **TTL 是收敛手段**：外部系统（PHP）写表、Java 感知不到时，用短 TTL 收敛脏读窗口，不做跨系统删 key。
4. **key 必须带租户/业务维度**：缓存 key 漏 tenant 会把 A 租户数据给 B。
5. **锁用看门狗，信号量用可过期许可**：节点崩溃后锁/配额要能自动释放。
6. **释放要防重复/过期**：已过期租约再 release 会抛异常，两次 release 各自兜住。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| fields/config 共享缓存 + 降级 | 实战 | smart WMS | 2026-07 | — |
| 登录态 keyVer、单端登录、刷新令牌轮换 | 实战 | smart WMS | 2026-05~07 | [[登录态与踢线]]、[[keyVer踢线校验]] |
| 导出/导入分布式信号量 | 实战 | smart WMS | 2026-06~08 | [[导出背压]]、[[异步导出落地]] |
| 定时任务多副本分布式锁 | 实战 | smart WMS | 2026-07 | [[定时任务多副本锁]] |

## 选型与取舍

### 为什么用 Redis 共享缓存，不用本地 Caffeine

- 多副本下本地缓存会长期分叉：A 副本改了配置，B 副本的 Caffeine 还在旧值，请求落到哪台结果不一样；Redis 共享 key 至少做到「要么都旧、要么都新」。
- 代价：每次读多一次网络往返，Redis 抖动会拖慢请求；项目用 `CacheErrorHandler` 降级——GET/PUT/EVICT 失败只记 WARN，GET 按未命中回源（`config/CacheConfig.java:109-131`）。
- 本地缓存不是被否定：如果数据允许分钟级不一致、且能接受副本间分叉，Caffeine 更快；项目选共享缓存，是因为配置/字段这类数据要求副本一致。

### 为什么用 cache-aside + 短 TTL，不做跨系统删 key

- 项目里 PHP 也会写表，Java 感知不到；跨系统删 key 需要可靠事件/双写，失败就长期脏。短 TTL（60 秒）把脏读窗口收敛到可接受范围，代价是短时间内可能读到旧值。
- cache-aside 的写路径是「先写 DB，再删 key」；删 key 失败只记 WARN，靠 TTL 兜底。代价是并发读写时仍可能把旧值写回缓存，需要短 TTL/版本号/延迟双删等补丁；项目没有做全套防击穿/穿透，边界里写明了。
- 结论：不是「缓存一致性 solved」，是「在跨系统写入约束下，选一个能收敛的窗口」。

### 为什么登录态放 Redis，不纯 JWT 无状态

- 纯 JWT 不能撤回：签发了就有效到过期；项目要单端登录、踢线、权限变更立即生效，所以用 keyVer/jti 把「撤销状态」放 Redis，JWT 只承载身份。
- 代价：Redis 成为登录链路依赖；项目按路径分开降级——单端登录/effective user 校验降级放过，actor keyVer 严格拒绝（`config/JwtSecurityFilter.java:136`、`:240-259`）。这是「可用性优先」和「安全优先」按操作分流，不是全局一个开关。
- 如果业务不需要撤回/单端登录，纯 JWT 更简单；项目需要，所以接受 Redis 依赖。

### 为什么锁/信号量用 Redisson

- 裸 `SET NX PX` 要自己写续租、可重入、释放校验；Redisson `RLock` 看门狗、`RPermitExpirableSemaphore` 租约自动归还，适合「任务可能跑几分钟、节点可能崩」的场景。
- 代价：多一个客户端依赖，集群/序列化行为要学；具体对比见 [[Redisson]]。

### 什么条件下会反悔

- 缓存一致性要求提高到「不能读到旧值」→ 改成事件驱动删 key/版本号，或不用缓存；当前 60 秒 TTL 不满足强一致。
- Redis 不可用导致登录/限流不可接受 → 把关键路径本地化或换多级缓存；当前按路径降级是明确的取舍。
- 本地缓存命中率极高、分叉可接受 → 引入 Caffeine 做一级缓存，Redis 做二级；当前没有做。

## 我会的部分

- **共享缓存**：`RedisCacheManager` + 60 秒 TTL + 不缓存 null（`config/CacheConfig.java:51-63`）；`@Cacheable` 13 处、`@CacheEvict` 1 处。
- **缓存 key 带租户**：`company:code` 的 key 用 `#tenantId`（`dao/impl/CompanyDaoImpl.java:93`）；`config:all` 是全平台配置，单独一个 key（`dao/impl/ConfigDaoImpl.java:38`）。
- **序列化安全**：缓存值用 Jackson JSON，注册 `JavaTimeModule`，开启默认类型信息但用包名白名单，避免 `LaissezFaireSubTypeValidator` 的 gadget chain 风险（`config/CacheConfig.java:87-97`）。
- **缓存降级**：实现 `CacheErrorHandler`，GET/PUT/EVICT/CLEAR 失败只记 WARN，GET 按未命中回源（`config/CacheConfig.java:109-131`）。
- **登录态**：`RedisUtil` 提供 get/set/del/atomicGet/atomicIncr 等原子操作（`common/util/RedisUtil.java:27-84`）；keyVer、单端登录 jti、踢线原因都走 Redis（`config/JwtSecurityFilter.java:112-136`）。
- **Redis 不可用时的取舍**：单端登录和 effective user 校验降级放过，actor keyVer 严格拒绝（`config/JwtSecurityFilter.java:136`、`:240-259`）。
- **分布式信号量**：导出/导入各两道闸门，`RPermitExpirableSemaphore` 带租约，节点崩溃自动归还（`config/ExportPoolConfig.java:49-55`）。
- **分布式锁**：`RedisLockUtil.withLock` 只传 waitTime，启用看门狗；抢不到抛 `SYS_BUSY`；`withLocks` 按 key 排序去重防死锁（`common/util/RedisLockUtil.java:18,29,39-56,66-107`）。
- **连接配置**：地址列表、密码、超时、重试都在 `application.yml:109-115`；客户端按地址数自动切单机/集群（`config/RedissonConfig.java:26-37`）。
- **Valkey 8（muou 编排）**：中间件用 `valkey/valkey:8-alpine`，开 AOF、强制 requirepass、端口只绑 `127.0.0.1`（`muou-app-ops/middleware/valkey/docker-compose.yml:23`、`:36-39`）。它和 Redis 协议兼容，应用侧仍走 Redisson；本人只读过编排，没有做过 Redis→Valkey 迁移、集群或故障转移验证。项目为什么选 Valkey 而不是 Redis 没有查到设计记录，不替它编理由。

## 边界

- 没做过 Redis 持久化（RDB/AOF）、主从切换、哨兵、Cluster 槽迁移的实战。
- 没做过内存淘汰策略调优、big key/hot key 排查、慢查询分析。
- 没写过 Lua 脚本；项目里的原子操作主要靠 `INCR`/`SET NX` 和 Redisson。
- 没做过 Redis 集群故障转移下的锁行为验证；只覆盖蓝绿部署的 180 秒共存窗口。
- 没做过缓存击穿/穿透/雪崩的专项防护；项目里靠短 TTL 和 null 不缓存兜底。

## 相关技能

- [[Redisson]]、[[导出背压]]、[[异步导出]]、[[异步导出落地]]
- [[登录态与踢线]]、[[keyVer踢线校验]]
- [[定时任务多副本锁]]
- [[中间件与异步任务]]
- 理论：[[缓存理论]]、[[复制与一致性理论]]

## 用在哪些工程能力

- 共享缓存与降级（fields/config）
- 登录态、单端登录、踢线（keyVer）
- 异步任务限流与背压（信号量）
- 多副本定时任务互斥（分布式锁）
