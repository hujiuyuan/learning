---
type: 技能点
域: 后端
项目: [muou-client]
证据: 实战
---

# Outbox

所属通用技能：[[事务与状态一致性]]

**一句话**：本地消息表把「业务写库 + 发消息」变成一个库里的一个事务，投递器再异步搬运；消息不会凭空消失，但会重复，消费端必须幂等。

## 方法总纲

1. **写**：`publish` 用当前事务的连接插一行 `pending`，业务回滚消息一起回滚；没有活动事务直接抛。
2. **抢**：投递器按 `state in (pending, failed) and next_run_at <= now() and 租约空闲` 批量捞，`FOR UPDATE SKIP LOCKED` 让多个实例不抢同一行。
3. **租**：捞到时写 `lease_until = now() + leaseSeconds`，并把 `attempts + 1`；租约期内别的实例看得见但捞不走。
4. **投**：先执行副作用（发邮件/发 MQ），成功后才标 `sent`；所以「副作用做完、标记没写」会重投。
5. **败**：没到上限写 `failed` + 退避时间；到上限写 `dead` 并回调死信处理器，不再自动重试。
6. **收尸**：定时扫描租约过期的行，清租约让别的实例重新捞。
7. **挡晚到**：`failed`/`dead` 写入要带「捞取时的租约」做条件，租约换过人就不许写；`sent` 不比对（确实送到了）。
8. **定时任务不是 Outbox**：`JobRunMarker` 是「条件 INSERT 占位 + 同事务副作用」，防的是任务重复执行；Outbox 的幂等靠租约，两者别混。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 本地消息表 `member_tx_message` + 公共库 `TxOutbox` | 实战 | muou-client | 2026-10 | [[任务幂等]] |
| 投递器租约抢占 / 退避 / 死信 | 实战 | muou-client | 2026-09 | [[任务幂等]] |
| 崩溃恢复与租约 fencing 测试 | 实战 | muou-client | 2026-09 | [[任务幂等]] |
| 定时任务 `JobRunMarker` 条件占位 | 实战 | muou-client | 2026-09 | [[任务幂等]] |

## 选型与取舍

### 为什么用 Outbox，不用 2PC / Seata XA

- 2PC/XA 在同一请求内强一致，但跨库/跨服务会持锁到全局提交，吞吐和可用性都受 TC/协调者影响；Outbox 把「业务写库 + 消息」放进一个本地事务，投递异步做，服务之间不互相锁。
- 代价：消息会重复（副作用做完、标记没写），消费端必须幂等；有投递延迟；死信/重试要自己做。项目用租约 + fencing + 死信状态机兜住重复和并发，但消费端幂等仍是前提。
- 如果业务要求「跨库写入当场一致、失败一起回滚」，XA 更合适；项目只在 11 个强一致入口用 Seata XA，其余异步事件/通知走 Outbox（见 [[Seata]]）。这不是二选一，是按链路选。

### 为什么用轮询投递器，不用 CDC / Debezium

- 轮询只依赖业务库和一张消息表，不需要 binlog 权限、Kafka Connect、额外组件；投递状态、退避、死信都在自己的表里，排查直接。
- 代价：有轮询延迟和空转查询；消息量大时会给 DB 增加压力；`SKIP LOCKED` 依赖数据库支持。项目用 `next_run_at` 索引、批量 `LIMIT`、租约减少空转。
- 如果消息量很大、要求低延迟，CDC 更合适；当前规模轮询更简单，运维面更小。

### 为什么用本地消息表，不用 RocketMQ 事务消息（半消息）

- 本地消息表和业务表同库同事务，业务回滚消息一定回滚；不依赖 MQ 的事务消息实现，换 MQ 不用改业务。
- 代价：要自己写投递器/重试/死信；消息会重复；项目没有做半消息，RocketMQ 通道是普通消息 + outbox 重试。
- 如果 MQ 原生事务消息成熟、且只用一个 MQ，半消息能少一张表；项目要支持多通道/邮件/通知，统一 outbox 更灵活。

### 为什么用租约 + fencing，不用简单状态更新

- 多实例投递时，「捞到 → 投递 → 标 sent」不是原子的；没有租约，两个实例会同时投；没有 fencing，晚到的失败写回会覆盖别人已经成功的状态。项目用 `lease_until` + 捞取时租约条件写回，保证同一行只有一个有效持有者。
- 代价：状态机/条件更新复杂，测试要覆盖崩溃恢复、租约过期、并发抢占、晚到写入；项目有对应 IT。
- 如果单实例投递，简单状态更新就够；项目的多副本部署要求租约。

### 什么条件下会反悔

- 消息量/延迟要求超出轮询能力 → 上 CDC/专用 MQ；当前轮询 + 索引够用。
- 消费端幂等成本高于强一致成本 → 把该链路改回 XA/同步调用；当前异步链路更看重解耦。
- Outbox 表膨胀 → 补归档/清理策略；当前没有做，是已知边界。

## 我会的部分

- **写入口**：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/JdbcTxOutbox.java:46-48` 检查「线程有事务且是本数据源上的非自动提交连接」；`:66-68` 直接问连接 `getAutoCommit()`，防止别的数据源事务里碰过本库导致误判。
- **表结构**：`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202610091735__member_create_tx_message.sql:8-37`，`state`、`attempts`、`next_run_at`、`lease_until` 四列是投递器的状态机；`attempts` 在捞到时加一，不是失败时才加（`:30`）。
- **抢批**：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcher.java:29-42` 的 `CLAIM`，`ORDER BY next_run_at, message_id` + `LIMIT` + `FOR UPDATE SKIP LOCKED`。
- **状态写回**：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcher.java:52-68` 三条 UPDATE 都带 `state in ('pending','failed')`；`failed`/`dead` 另带 `lease_until = ?`，`sent` 不比对。
- **投递顺序**：同上文件 `:134-148` 先 `transport.deliver`，再 `markSent`；失败走 `onFailure`。
- **退避/死信**：同上文件 `:173-199` 到 `maxAttempts` 转 `dead` 并回调；`:201-206` 指数退避封顶。
- **调度入口**：`muou-server/src/main/java/com/voidtech/muou/job/OutboxDispatchJob.java:24-31` 明确「幂等是租约机制，不是 `job_run_marker` 的 CAS」；`:39-48` 每轮先回收过期租约再投。
- **定时任务占位**：`muou-server/src/main/java/com/voidtech/muou/service/JobRunMarker.java:34-61` 定义复合键 `(jobId, targetType, targetKey, windowKey)`；`muou-server/src/main/java/com/voidtech/muou/service/impl/JobRunMarkerImpl.java:32-38` 用 `MANDATORY` 把「占位必须与副作用同事务」机器化；`muou-server/src/main/resources/db/migration/V14__job_run_marker.sql:19-31` 复合主键。
- **验证**：`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxTransactionTest.java:65-83` 回滚时业务和消息都不留；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxCrashRecoveryTest.java:92-115` 租约过期重投；`:117-139` 副作用做完没标 sent 会重投；`:141-166` 死信；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxLeaseConcurrencyTest.java:82-88` 两实例并发只送一次；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxLeaseFencingTest.java:60-117` 晚到写入作废。

## 边界

- 只在 PostgreSQL 上落地；`SKIP LOCKED` 依赖数据库支持，MySQL 8 可用，老版本不行。
- 业务表和消息表必须同库；跨库写入没有做过。
- 死信只做到 `state='dead'` + 回调；没有自动重放/人工修复工具。
- `JobRunMarker` 目前只有 `AuthReloadTenantStep` 一个真实调用点；其余任务有的走租约/终态抢占，有的还没落地，不能写成 11 个任务都用了占位表。接口/实现注释里仍写着「11 个任务一个都还没实现」，以实际调用点为准。
- 没做过 RocketMQ 事务消息（半消息）；RocketMQ 通道是普通消息 + outbox 重试，见 `muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/RocketMqRetryAndDeadLetterTest.java:20-30`。
- 没做过 outbox 表的归档/清理策略。
- 时间说明：`2026-09`/`2026-10` 按代码、测试与迁移文件的修改时间推断；muou-client 的 git 分支没有提交记录，均非提交记录。

## 相关技能

- 通用技能：[[事务与状态一致性]]
- 场景：[[任务幂等]]
- 实践：[[Outbox落地]]
- 技能点：[[Spring事务]]

## 用在哪些工程能力

- 异步事件/邮件/通知的可靠投递
- 定时任务重复执行防护
- 消费者幂等与死信处理
- 崩溃恢复与并发抢占设计
