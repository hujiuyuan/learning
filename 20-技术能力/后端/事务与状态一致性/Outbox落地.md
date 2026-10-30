---
type: 实践
技能点: Outbox
项目: [muou-client]
时间: 2026-10
证据: 实战
---

# Outbox落地

技能点：[[Outbox]] · 项目：muou-client · 2026-10

场景：[[任务幂等]]

## 我想干什么

业务事务提交后可靠地发出事件/邮件：业务失败不能把消息发出去，业务成功不能把消息弄丢；下游短暂不可用要能重试，重试不能把整轮投递拖垮。

## 我干了什么

- **建表**：`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202610091735__member_create_tx_message.sql:8-37`。`state`（pending/sent/failed/dead）、`attempts`、`next_run_at`、`lease_until` 四列支撑投递状态机；没有数据库默认值，写入方落初值；`attempts` 在捞到时加一（`:30`）。
- **写入口**：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/JdbcTxOutbox.java:21-24` 插入 `pending` 行；`:46-48` 没有活动事务直接抛；`:66-68` 检查连接是否自动提交，防止跨数据源误判。
- **投递器**：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcher.java:29-42` 用 `FOR UPDATE SKIP LOCKED` 抢批并写租约；`:52-68` 三条状态写回；`:134-148` 先投后标；`:173-199` 退避/死信。
- **调度入口**：`muou-server/src/main/java/com/voidtech/muou/job/OutboxDispatchJob.java:10-31` 说明为什么单独一个 Job 类（实现可注入、可确定性驱动），`:39-48` 每轮回收租约 + 投一批。
- **参数**：`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxOutboxProperties.java:10-55`，表名白名单、批量大小、租约秒数、最大尝试次数、退避基数/上限。
- **测试**：`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxTransactionTest.java:65-83` 回滚两边都不留；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxCrashRecoveryTest.java:92-166` 崩溃恢复/重投/死信；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxLeaseConcurrencyTest.java:82-88` 两实例并发只送一次；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxLeaseFencingTest.java:60-117` 旧持有者晚到写入作废；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcherFallbackTest.java:66-148` 退避、死信回调失败；`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxSchedulerTest.java:76-114` 轮询线程随容器停、失败不停轮询。

## 犯了什么错 / 误判

1. **把「占位先提交」当成通用规则**：定时任务的 `JobRunMarker` 占位是永久标记，先提交再做事会留下「标记已写、事情没做」的永久空洞，所以它必须和副作用同事务（`muou-server/src/main/java/com/voidtech/muou/service/JobRunMarker.java:27-32`）。Outbox 的 `claim` 也先提交，但它写的是会过期的 `lease_until`，崩溃后租约到期会被回收重投；两者像，但一个靠同事务、一个靠租约，不能照搬。
2. **以为消息只会投一次**：`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxCrashRecoveryTest.java:117-139` 证明「副作用做完、sent 没标」会重投；消费端不幂等就会重复建单。
3. **租约过期后旧持有者还能写**：旧实例晚到的 `failed` 会清掉新持有者的租约，第三个实例再捞到同一行，两个实例同时投；现在 `failed`/`dead` 比对捞取时的 `lease_until`，`sent` 不比对，见 `muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcher.java:44-51`。
4. **死信回调自己抛异常**：不能让整轮投递崩掉；`onFailure` 里 catch 住并打 ERROR，见 `:184-188`；测试 `muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcherFallbackTest.java:110-148` 连 `Error` 都覆盖。
5. **`attempts` 失败时才加**：反复「投到一半就崩」永远走不到失败分支，次数不涨，消息无限重试；迁移注释 `:30` 明确改成捞到就加一。

## 怎么解决

- 状态机：`pending/failed → sent` 成功；`pending/failed → failed` 退避；`failed → dead` 到上限。
- 抢占：`SKIP LOCKED` + `lease_until`，多实例并发不重复捞；过期租约由 `recoverExpiredLeases` 回收。
- 投递顺序：先副作用、后标 `sent`；接受至少一次，消费端幂等。
- 失败处理：指数退避封顶；死信必须回调，不能只留日志。
- 入口防御：`publish` 拒绝事务外调用；表名走白名单，不拼用户输入。

## 现在的规矩

- 业务表和消息表同库同事务；跨库不发消息。
- `publish` 只能在事务内；topic/payload 非空。
- 消费端必须按业务键幂等；不假设只投一次。
- 死信要回调处理器，不只打日志。
- 表名只能来自白名单配置，不能来自用户输入。

## 证据

- `muou-backend/muou-server-member/muou-member-app/db/migration/core/V202610091735__member_create_tx_message.sql`
- `muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/JdbcTxOutbox.java`
- `muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxOutboxDispatcher.java`
- `muou-server/src/main/java/com/voidtech/muou/job/OutboxDispatchJob.java`
- `muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxCrashRecoveryTest.java`
- `muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/TxOutboxTransactionTest.java`
- 时间说明：muou-client 的 git 分支没有提交记录，`2026-10` 按迁移文件日期 `V202610091735` 与文件修改时间推断，不是提交记录。
