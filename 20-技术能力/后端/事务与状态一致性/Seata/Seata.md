---
type: 技能点
域: 后端
项目: [muou]
证据: 实战/设计
---

# Seata

所属通用技能：[[事务与状态一致性]]

**一句话**：Seata 2.6.0 在 muou 是「按服务选择性开启」：默认关，只有 5 个服务用 XA，业务只写 `@MuouGlobalTx`；不是全量分布式事务，也不是裸 `@GlobalTransactional`。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/`。

## 方法总纲

1. **默认关**：`common.yaml` 里 `seata.enabled: false`；只有真需要跨库强一致的服务在自己的 dataId 打开。
2. **只给跨服务写入用**：单库能解决的不开全局事务；Outbox 最终一致仍是默认方案。
3. **业务不直接碰 Seata**：统一写 `@MuouGlobalTx`，由公共层决定接 Seata 还是降级本地事务。
4. **新路径显式拒绝降级**：`requireDistributed = true`，没接上 Seata 时直接抛错，不悄悄退成本地事务。
5. **模式必须和数据源代理一致**：注解写 XA，`seata.data-source-proxy-mode` 也必须是 XA；不一致在进入事务前就抛。
6. **客户端和服务端版本一致**：`muou-build` 钉 2.6.0，TC 镜像也用 2.6.0。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 5 个服务开启 Seata XA | 实战 | muou | 2026-09 | [[Outbox落地]] |
| 11 个跨库写入入口加 `@MuouGlobalTx` | 实战 | muou | 2026-09~10 | [[事务与状态一致性]] |
| `@MuouGlobalTx` 注解 + 自动装配 + 本地降级 | 实战 | muou | 2026-09 | — |
| Seata TC 2.6.0 本地编排 | 实战 | muou | 2026-09 | — |
| AT/TCC 模式与测试骨架 | 设计/测试 | muou | 2026-09 | — |

## 选型与取舍

项目里跨服务一致性有三条路：本地事务/Outbox、Seata XA、Seata AT/TCC。生产只把 XA 用在 11 个跨库写入入口，其余走 Outbox；AT/TCC 只有测试骨架。

| 方案 | 一致性 | 业务侵入 | 主要代价 | 项目里的位置 |
| --- | --- | --- | --- | --- |
| 本地事务 + Outbox | 最终一致 | 低：业务只写本地事务 + 消息表 | 有延迟；消费端必须幂等；死信/重试要自己做 | 默认方案，见 [[Outbox]] |
| Seata XA | 强一致（数据库 XA） | 低：加 `@MuouGlobalTx` | 全局锁/阻塞；TC 成为关键依赖；性能随跨库写入下降 | 5 个服务、11 个生产入口 |
| Seata AT | 强一致（undo_log 补偿） | 低：SQL 基本不改 | 需要 undo_log、SQL 解析兼容；全局锁/脏读边界；回滚依赖 undo | 只有测试骨架 |
| Seata TCC | 强一致（业务补偿） | 高：每个入口写 Try/Confirm/Cancel | 补偿逻辑、空回滚/悬挂/幂等都要业务处理 | 只有测试骨架 |
| Saga | 最终一致 | 中：每步补偿 | 中间状态可见；补偿失败要人工 | 未使用 |

### 为什么生产是 XA，不是 AT/TCC

从代码能确认的事实：生产 11 个 `@MuouGlobalTx` 全部是 XA；AT/TCC 只在测试里（`SeataGlobalTxExecutor.java:70-120`、`muou-build/pom.xml:69`）。设计文档没有写「为什么 AT/TCC 不上生产」的完整对比，下面是按模式代价做的推断，标「推断」：

- **XA 的侵入最小**：业务只加一个注解，不写 Confirm/Cancel，也不依赖 undo_log 的 SQL 解析；对 11 个已经存在的跨库写入入口，改造成本最低。
- **XA 的代价是阻塞和 TC 依赖**：跨库事务持有数据库锁到全局提交，吞吐会降；TC 挂了事务无法推进。项目因此默认关 Seata，只给真需要强一致的 5 个服务开，没有把全站写入都套进来。
- **AT 不是「免费」**：要保证每个库都有 undo_log、SQL 都能被解析，回滚依赖 undo 记录；项目虽然建了 undo_log，但没有生产入口，说明没有把握把它当默认模式。
- **TCC 要求业务写三段**：11 个入口每个都要 Try/Confirm/Cancel，还要处理空回滚、悬挂、幂等；在没有强需求时，收益不抵改造量。
- **Saga 只适合可补偿的长流程**：项目没有生产使用；跨库强一致写入仍然走 XA。

### 为什么默认关、只开 5 个服务

- 公共库把 Seata starter 传给八个服务和网关，但 `common.yaml` 默认 `seata.enabled: false`（`seed-service-configs.sh:1592-1593`）；只有 `seata_xa_block` 生成的 5 个服务打开（`:182-193`）。
- 原因：每个服务都连 TC 会增加启动依赖和故障面；不需要跨库强一致的服务，开 Seata 只会多一个可能挂掉的组件。
- 代价：同一个代码库里有「开」和「关」两种运行态，排查时要先确认服务 dataId；`@MuouGlobalTx` 的自动装配和模式校验就是为这个复杂度兜底（`SeataGlobalTxAutoConfiguration.java:1-80`、`SeataGlobalTxExecutor.java:70-120`）。

### 为什么业务不直接写 `@GlobalTransactional`

- 直接写 Seata 注解会把业务代码绑死在 Seata 上；`@MuouGlobalTx` 由公共层决定接 Seata 还是本地降级，还能在进入事务前校验 mode 和数据源代理是否一致（`MuouGlobalTx.java:1-30`）。
- 降级不是静默的：`requireDistributed = true` 时没接上 Seata 直接抛 `TX_GLOBAL_MODE_PROXY_DISABLED`；普通模式才退本地事务并打 WARN（`LocalFallbackGlobalTxExecutor.java:1-90`）。这是「可用性优先」和「一致性优先」按入口分开，而不是全局一个开关。

### 什么条件下会反悔

- 跨库写入并发升高、XA 全局锁成为瓶颈 → 把非核心链路改成 Outbox/Saga，只保留必须强一致的入口。
- TC 高可用/故障转移成为生产要求 → 先补 TC 集群、事务恢复演练，再扩大 XA 范围；当前没有做过这些演练。
- 业务需要可补偿的长流程 → 评估 Saga/TCC，但不能直接替换 XA：补偿语义要按业务重新设计。

## 我会的部分

- **版本**：`muou-backend/muou-build/pom.xml:69` 钉 `seata.version=2.6.0`，`:320-322` 引 `seata-spring-boot-starter`。
- **默认关**：`common.yaml` 里 `seata.enabled: false`，公共库把 starter 传给八个服务和网关，默认关避免每个服务都去连 TC（`muou-backend/muou-app-ops/middleware/nacos/seed-service-configs.sh:1592-1593`）。
- **五个服务开 XA**：`seata_xa_block` 生成 `seata.enabled: true`、`data-source-proxy-mode: XA`（`seed-service-configs.sh:182-193`），调用点只有 iam、member、billing、platform、content（`:568`、`:760`、`:903`、`:963`、`:1237`）。
- **业务注解**：生产代码 11 处 `@MuouGlobalTx`，全部 XA：member 7、iam 3、content 1。例子：`muou-backend/muou-server-member/muou-member-app/src/main/java/com/voidtech/muou/member/application/proxy/service/ProxyFirstAcceptanceCommit.java:62`、`muou-backend/muou-server-iam/muou-iam-app/src/main/java/com/voidtech/muou/iam/service/binding/IamClaimManagedPersonTx.java:25`、`muou-backend/muou-server-content/muou-content-app/src/main/java/com/voidtech/muou/content/service/impl/ApplicationCorrectionService.java:37`。
- **统一入口**：`@MuouGlobalTx` 故意不给 `mode` 默认值，漏写编译不过；业务代码写不出 Seata 类型（`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/globaltx/MuouGlobalTx.java:1-30`）。
- **自动装配**：`SeataGlobalTxAutoConfiguration` 只在类路径有 Seata、且 `seata.enabled` 与 `muou.tx.global.seata-enabled` 两个开关都开时装配（`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/seata/SeataGlobalTxAutoConfiguration.java:1-80`）。
- **本地降级**：没有 Seata 时 `LocalFallbackGlobalTxExecutor` 把方法包进本地事务并打 WARN，同一个方法 5 分钟只告警一次；跨库那一半不会回滚（`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/globaltx/LocalFallbackGlobalTxExecutor.java:1-90`）。
- **拒绝静默降级**：`requireDistributed = true` 时，没有接上 Seata 直接抛 `TX_GLOBAL_MODE_PROXY_DISABLED`（同文件 `:37-40`）。
- **模式校验**：`SeataGlobalTxExecutor` 进入事务前比对注解 mode 和 `seata.data-source-proxy-mode`，不一致抛 `TX_GLOBAL_MODE_MISMATCH`；TCC 不走数据源代理（`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/seata/SeataGlobalTxExecutor.java:70-120`）。
- **TC 与 undo_log**：`muou-backend/muou-app-ops/middleware/seata/docker-compose.yml:23-32` 用 `apache/seata-server:2.6.0.jdk21`；core/billing/message 初始化脚本都建 `undo_log`（`muou-backend/muou-app-ops/databases/migration/core/V202609112100__core_init.sql:8995`、`muou-backend/muou-app-ops/databases/migration/billing/V202609112100__billing_init.sql:1374`、`muou-backend/muou-app-ops/databases/migration/message/V202609112100__message_init.sql:1266`）。

## 边界

- 不是全量：notify、log、message、archive、flow、gateway 都保持关闭；只有 5 个服务开。
- 生产只用 XA；AT/TCC 只有测试骨架，没有生产业务入口。
- 没有做过 TC 高可用、故障转移、事务恢复的生产演练。
- 没有做过 Seata 控制台运维、事务补偿、超时/回滚告警。
- 没有用 Saga 模式；TCC 的 Cancel/Confirm 只在测试里。
- 没有验证过跨库 XA 在最大并发下的性能代价。

## 相关技能

- [[事务与状态一致性]]、[[Spring事务]]、[[Outbox]]、[[Outbox落地]]、[[任务幂等]]
- [[PostgreSQL]]、[[Nacos]]
- 理论：[[分布式系统理论]]、[[事务与隔离理论]]

## 用在哪些工程能力

- 跨服务/跨库强一致写入
- 全局事务降级与告警
- 分布式事务模式选择（XA/AT/TCC）
