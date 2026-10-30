---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战
---

# Redisson

所属通用技能：[[中间件与异步任务]]

**一句话**：用 Redis 做跨副本的并发控制——分布式信号量限总量、分布式锁防重复执行；关键是租约和自动归还，否则节点一挂配额或锁就永久丢失。

## 方法总纲

- 限流用 `RPermitExpirableSemaphore`：许可带租约，节点崩溃后自动归还；`RSemaphore` 没有归还机制，会越用越少。
- 锁用 `RLock` + 看门狗：`tryLock(waitTime)` 不传 leaseTime，持锁线程活着就自动续租，崩溃则到期释放。
- 抢锁失败是预期分支，不是故障：识别 `SYS_BUSY` 后静默跳过。
- 客户端按地址数自动切单机/集群（`RedissonConfig.java:26-37`）。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 导出/导入限流 | 实战 | [[smart WMS]] | 2026-06 | [[导出背压]] |
| 定时任务多副本锁 | 实战 | [[smart WMS]] | 2026-07 | [[定时任务多副本锁]] |

## 选型与取舍

### 为什么用 Redis 锁，不用数据库行锁/唯一约束

- 数据库行锁/唯一约束能保证强一致，但锁持有时间受事务长度限制；导出/回填这类任务要跑几分钟，把事务开着等任务结束会占连接、放大回滚段，不适合。
- Redis 锁的代价是「租约」：Redis 挂了、网络分区、GC 停顿都可能让锁提前释放；所以它只能防重复执行，不能代替幂等。项目里抢锁失败是预期分支（`SYS_BUSY` 静默跳过），真正的一致性仍靠数据库状态/唯一约束/Outbox。
- 结论：Redis 锁适合「短临界区 + 可重入 + 失败可跳过」；强一致、不可重复的写入仍要数据库约束兜底。

### 为什么用 Redisson，不用裸 `SET NX PX` + Lua

| 方案 | 优点 | 代价 |
| --- | --- | --- |
| 裸 `SET NX PX` | 无依赖、行为透明 | 续租、可重入、释放校验、信号量都要自己写 Lua；续租失败/误删别人的锁是常见事故 |
| Redisson `RLock` | 看门狗自动续租、可重入、锁释放校验 | 多一个客户端依赖；序列化/配置/集群行为要学 |
| Redisson `RPermitExpirableSemaphore` | 许可带租约，节点崩溃自动归还 | 许可数写在 Redis key 上，扩缩容要改配置；过期释放会抛异常，要 try/catch |

项目早期 `NotificationScheduler` 直接 `getLock + tryLock(0, 300, SECONDS)`，固定 300s 租约，任务跑超 5 分钟锁就自动释放；新代码统一 `RedisLockUtil.withLock`，不传 leaseTime，启用看门狗（`RedisLockUtil.java:18`、`:29`、`:39-56`）。这是一次具体的反悔：固定租约看似可控，实际上把「任务可能跑多久」硬编码进了锁。

### 为什么信号量用 `RPermitExpirableSemaphore`，不用 `RSemaphore`

- `RSemaphore` 没有自动归还：节点被杀后已拿到的 permit 永久消失，配额越用越少，最后限流变成“永久拒绝”。
- `RPermitExpirableSemaphore` 的 permit 带 lease，节点崩溃后到期自动归还；代价是 release 已过期 permit 会抛异常，两次 release 要各自 try/catch，避免 running 的异常连累 admit（`ExportServiceImpl.java:123-130`、`:136-142`）。
- 这不是「Redisson 的功能介绍」，是故障模式决定的：限流器必须假设持有点会崩溃。

### 什么条件下会反悔

- 临界区变成秒级以上、锁竞争激烈 → 改用数据库状态机/队列，不要把长任务塞进 Redis 锁。
- Redis 集群故障转移频繁、锁误释放不可接受 → 评估 ZooKeeper/etcd 或数据库租约；当前没有做过集群故障转移下的锁行为验证。
- 许可数需要动态扩缩 → 把配额从写死 key 改成配置中心下发，或改用令牌桶；当前扩缩容要改配置并重启。

## 我会的部分

- **分布式信号量 vs JVM Semaphore**：JVM 内 `Semaphore` 在多副本下等于 N×配额，下游 DB/S3 保护失效，且拒绝不均（A 副本满载、B 空闲，成败取决于负载均衡落点）（`ExportPoolConfig.java:49-52`）。
- **可过期许可**：`RPermitExpirableSemaphore.tryAcquire(wait, lease, unit)` 带租约；节点被杀后到期自动归还。`RSemaphore` 无自动归还，配额会逐次缩水直到耗尽（`ExportPoolConfig.java:53-55`）。
- **两道闸门**：接纳 = 并发 + 排队（`trySetPermits(15)`），执行 = 并发（`trySetPermits(5)`）；配置在 `application.yml:276-278`。
- **释放要防租约过期**：Redisson 对已过期租约的 permit 调 `release` 会抛异常；两次 release 各自 try/catch，避免 running 抛异常连累 admit（`ExportServiceImpl.java:123-130`、`:136-142`）。
- **分布式锁**：`RedisLockUtil.withLock` 只传 waitTime=3s，启用看门狗；抢不到抛 `SYS_BUSY`（`RedisLockUtil.java:18`、`:29`、`:39-56`）。
- **抢锁失败静默跳过**：任务里捕获 `SYS_BUSY` 记 info 后 return，其余异常照常传播（`OmpTenantBackfillJob.java:53-62`、`IoReaperJob.java:44-52`）。
- **两把锁的写法**：早期 `NotificationScheduler` 直接 `getLock` + `tryLock(0, 300, SECONDS)`（`NotificationScheduler.java:58-62`）；新代码统一走 `RedisLockUtil`。
- **多锁顺序**：`withLocks` 按 key 排序去重逐层加锁，避免死锁（`RedisLockUtil.java:66-107`）。
- **测试**：抢锁成功执行 9 条 UPDATE（`OmpTenantBackfillJobTest.java:64-70`）；抢锁失败不碰 DB（`:80-84`）。

## 边界

- 没做过 Redisson 的读写锁、公平锁、联锁（`RedissonMultiLock`）、限流器（`RRateLimiter`）。
- 没做过 Redis 集群故障转移下的锁行为验证；配置支持单机/集群，实战只覆盖蓝绿部署的 180 秒共存窗口，没覆盖常态多副本。
- 没有实现锁等待可观测（谁持锁、等多久）；只靠 `SYS_BUSY` 和日志。
- 信号量配额写死在 Redis key 上，扩缩容要改配置并重启。
- `NotificationScheduler` 用固定 300s 租约，任务跑超 5 分钟锁会自动释放；`RedisLockUtil` 用看门狗没有这个问题。

## 相关技能

[[异步导出]]、[[XXL-Job]]、[[Spring应用与接口契约]]
- 理论：[[调度与协调理论]]

## 用在哪些工程能力

异步任务与后台作业、并发与限流（未建卡）、集群化部署（未建卡）
