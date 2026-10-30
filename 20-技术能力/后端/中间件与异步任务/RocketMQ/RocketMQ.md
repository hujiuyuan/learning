---
type: 技能点
域: 后端
项目: [muou]
证据: 实战
---

# RocketMQ

所属通用技能：[[中间件与异步任务]]

**一句话**：RocketMQ 在这套系统里只负责「把消息送到 Broker」，可靠投递由本地消息表负责；生产侧只允许同步发送并检查 `SEND_OK`，消费侧先还原租户再开事务、异常一律外抛，重试用尽后进 `%DLQ%` 死信主题——实测首投 + 2 次重试，间隔约 20 秒、30 秒。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/muou-backend/`；各模块是独立 git 仓库，行号以当前工作区为准。简称：`99-13...` = `muou-app-doc/design/99-公共（common）/99-13-消息队列使用与可靠性设计.md`；`00-12...` = `muou-app-doc/design/00-技术选型（selection）/00-12-消息中间件技术选型.md`；`broker.conf` 与 `docker-compose.yml` = `muou-app-ops/middleware/rocketmq/` 下同名文件。

**归属说明**：公共投递器、消费入口、死信实测、compose/运维文档、主题目录脚本由本人提交（`git log` 作者 hujiuyuan）。42 个监听器类里 24 个文件的最后一次提交人是本人、18 个是团队其他成员；末次提交不等于每行归属，本页不按模块提交数给 RocketMQ 加权。

## 方法总纲

1. **可靠投递归 Outbox，队列只管传输**：业务写库和 `tx_message` 同事务；投递器发成功才标 `sent`，失败退避重投，到上限标 `dead`。队列不承担「业务成功」这件事。
2. **只同步发送**：`syncSend` 等回执，只有 `SEND_OK` 算送达；异步、单向发送拿不到回执，等于放弃这一段保证。
3. **消息头带三样**：`message_id`（消费端幂等键）、`tenant_id`（行级安全上下文）、`trace_id`（日志链路）；空值不写空串，RocketMQ 的 `putUserProperty` 拒绝空串。
4. **消费先还原租户，再开事务**：`TxMessageConsumerSupport` 把租户放进 `ContextHolder`，再执行 `TransactionTemplate`；顺序反了，RLS 会 fail-closed 查不到数据。
5. **业务异常外抛，不许吞**：吞掉再返回成功等于告诉队列「处理完了」，消息不会再投，业务静默丢失。
6. **重试分两层，职责不同**：客户端发送重试（默认 2 次，换 Broker）只管一次投递；Outbox 投递器的重试（默认最多 8 次、指数退避封顶 600 秒）才是持久化、重启不丢的那一层。
7. **死信只记录，不自动重放**：`%DLQ%<消费组>` 没有消费者，消息不会消失；本地消息表侧的 `dead` 行保留 `last_error`，处理动作在线下。
8. **命名先于发送**：主题 `<领域>_<事件过去式>`、消费组 `<服务名>-<主题名>`，只允许 `^[%|a-zA-Z0-9_-]+$`；点号非法，且主题名到第一次发送才校验。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 公共投递通道 `RocketMqTxMessageTransport`：同步发送、回执校验、消息头 | 实战 | muou | 2026-09 | [[任务幂等]] |
| 消费侧统一入口 `TxMessageConsumerSupport`：租户上下文 + 事务 + 异常外抛 | 实战 | muou | 2026-09 | [[任务幂等]] |
| 死信/重试实测：3 次投递、20.0/30.1 秒间隔、最终进 `%DLQ%` | 实战 | muou | 2026-09~10 | [[任务幂等]] |
| NameServer/Broker/控制台 compose、`broker.conf`、端口与卷的运维口径 | 实战 | muou | 2026-09~10 | — |
| 主题/消费组清单生成 `mqcatalog.py`，从源码生成 `topics.tsv`/`groups.tsv` | 实战 | muou | 2026-10 | — |
| 消息中间件选型：四方案加权评分与改判记录 | 实战（设计） | muou | 2026-09 | — |

## 我会的部分

### 生产侧：Outbox 发，RocketMQ 送

- `RocketMqTxMessageTransport.deliver` 只调 `template.syncSend(topic, payload, timeout)`；返回 `null` 或状态不是 `SEND_OK` 一律抛 `TX_ROCKETMQ_NOT_ACKNOWLEDGED`，让投递器记失败，不把「可能到了」当成功（`muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/RocketMqTxMessageTransport.java:44-66`）。
- 发送超时取租约的一半、下限 1 秒；超时不短于租约，租约到期后第二个实例会接管同一行、重复发送，启动直接报 `TX_ROCKETMQ_SEND_TIMEOUT_NOT_SHORTER_THAN_LEASE`（`RocketMqTxMessageTransport.java:38-42`；`muou-app-doc/design/99-公共（common）/99-13-消息队列使用与可靠性设计.md:74-77`）。
- 消息头 `message_id` 永远写；`tenant_id`/`trace_id` 为空时不写头，不写空串（`RocketMqTxMessageTransport.java:50-59`）。
- `transport` 默认 `local`，投递器默认关；跨服务要在 Nacos 配 `transport: rocketmq` + `dispatcher-enabled: true`，否则消息只落表、永远不投（`TxOutboxProperties.java:22-29`；`muou-app-ops/middleware/nacos/seed-service-configs.sh:418-425`）。
- 两层重试不叠加放大：客户端发送重试保持默认 2 次，真正的重试在 Outbox 投递器（`99-13...:66-72`）。

### 消费侧：先租户、后事务、异常外抛

- 主代码里有 42 个带 `@RocketMQMessageListener` 的监听器类：在 `muou-backend/` 下执行 `grep -rl '@RocketMQMessageListener' --include='*.java' */muou-*-app/src/main | wc -l` = 42。
- 监听器实现 `RocketMQListener<MessageExt>`，先校验 `tenant_id`/`message_id` 头，缺了直接拒绝，再交给公共入口；载荷不能替代可信头（`muou-server-billing/muou-billing-app/src/main/java/com/voidtech/muou/billing/mq/consumer/OrderEffectReceiptListener.java:17-37`）。
- `TxMessageConsumerSupport.handle` 的顺序固定：反序列化 → 打开 `TraceScope` → `ContextHolder.callAs(租户)` → `TransactionTemplate` 执行业务；不 catch 业务异常（`muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxMessageConsumerSupport.java:40-61`）。
- 跨服务消费必须自建 `@RocketMQMessageListener`；`@TxListener` 只对进程内通道有效，配成 `rocketmq` 后它一次都不会被调用，监听器注释里写明了这个坑（`muou-server-iam/muou-iam-app/src/main/java/com/voidtech/muou/iam/mq/consumer/spaceaccess/IamMembershipFrozenListener.java:20-25`）。
- `TxListenerTransportGuard` 在启动时拦两种静默失效：配了 `rocketmq` 却没引依赖（`TX_OUTBOX_ROCKETMQ_ABSENT`）；配了跨进程通道却还留着 `@TxListener`（`TX_LISTENER_ORPHANED`）。它按配置判断，不看实际装上的通道（`muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/outbox/TxListenerTransportGuard.java:11-51`）。
- 消费默认并发；项目里没有 `consumeMode=ORDERLY`。顺序消费会阻塞整个队列，只在「同一对象的多条消息必须按序」时用，当前链路不需要（`99-13...:173-180`）。

### 重试与死信：实测不是照抄文档

- 测试真连本机 Broker：消费组每次运行带时间戳，主题带 `muou-verify` 前缀，消费方法故意返回 `RECONSUME_LATER`，然后量投递次数、间隔和死信主题是否「从无到有」（`muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/outbox/RocketMqRetryAndDeadLetterTest.java:26-49`、`:95-140`）。
- 实测结果：首投 1 次 + 重试 2 次；第一次间隔 20.0 秒、第二次 30.1 秒；次数用尽后进 `%DLQ%` 主题，不是消失。两次独立运行数字一致（`99-13...:195-213`）。
- 官方文档写第一次重试 10 秒，本项目实测 20 秒；上限没采用官方默认 16 次，因为退避会拉到 2 小时，一次实测跑不完。真实服务用多少次由各服务自己定（`99-13...:211-213`）。
- 死信没有消费者：不建人工工单，只保留记录；消息躺在 `%DLQ%<消费组>`，本地消息表侧 `dead` 行留 `last_error`（`99-13...:219-228`）。
- 幂等不在公共库射程内：公共库只把 `message_id` 放进消息头，重复消费会不会重复扣款、用什么键判重，由业务表/唯一键/状态 CAS 决定（`99-13...:215-217`）。

### 运维：单节点、同步刷盘、无鉴权

- 服务端与客户端版本对齐：`rocketmq-spring-boot-starter 2.3.6` 绑 `rocketmq-client 5.3.2`，镜像也用 5.3.2；跨版本的症状往往是超时而不是报错（`muou-build/pom.xml:75-76`、`:333-346`；`muou-app-ops/middleware/rocketmq/docker-compose.yml:21-24`）。
- 刷盘用 `SYNC_FLUSH`：消息真正落盘才返回成功；异步刷盘断电会丢，而发送方以为已送达，Outbox 不会重投，只有对账能发现（`muou-app-ops/middleware/rocketmq/broker.conf:23-28`）。
- 只有单节点 `ASYNC_MASTER`，没有从节点：`SYNC_MASTER` 没有从节点是空转；单节点挡不住磁盘坏/整机报废，这是已知残余风险（`broker.conf:20-21`；`99-13...:94-123`）。
- 数据卷声明为 `external`，`docker compose down` 不删消息；容器重建不丢消费位点（`docker-compose.yml:97-100`、`:226-227`）。
- 生产必须关自动建主题/消费组：主题名打错一个字母会静默建出新主题，消息发进去没人消费且不报错；本机才开（`docker-compose.yml:91-96`；`broker.conf:51-55`）。
- 端口一律绑 `127.0.0.1`：NameServer/Broker/控制台都没有鉴权，谁连上谁能读写任意主题、删主题、重置位点；控制台挂公网前必须开登录并换真口令（`docker-compose.yml:37-40`、`:161-167`；`README.md` 端口与安全段）。
- `brokerIP1` 写错的表现是「发送超时」而不是连接失败：Broker 把该地址注册到 NameServer，客户端拿到后连不上。宿主进程填 `127.0.0.1`，容器内必须填容器名（`broker.conf:8-13`；`README.md` 三个坑）。
- 空数据卷属主是 root、Broker 进程是 uid 3000，不 `chown` 会初始化失败，且 shutdown 的空指针把真原因盖掉；compose 用 root 进容器 chown 后 `setpriv` 降权（`docker-compose.yml:101-120`）。

### 主题目录：从源码生成，不手写

- `mqcatalog.py` 从三类来源收主题：契约模块的 `*Topics.java`、`@RocketMQMessageListener` 的 topic/group、`outbox.publish(...)` 的常量；解析不出订阅处的主题/组直接报错，宁可生成失败也不静默漏消费者（`muou-app-ops/middleware/rocketmq/mqcatalog.py:1-16`）。
- 产出 `topics.tsv` / `groups.tsv`，`--check` 与 `env-diff.sh` 核对代码和清单是否一致；`seed-topics.sh` 按清单预建主题（`topics.tsv:1-2`；`mqcatalog.py:12-16`）。
- 命名规则：主题 `<领域>_<事件过去式>` 全小写下划线，消费组 `<服务名>-<主题名>` 横线；点号是非法字符。消费组名在消费者启动时校验，主题名到第一次发送才校验（`99-13...:232-250`）。

## 选型与取舍

### 为什么选 RocketMQ，不选评分更高的 RabbitMQ

| 方案 | 加权分 | 优势 | 代价 | 项目里的位置 |
| --- | ---: | --- | --- | --- |
| RocketMQ | 3.85 | Java 栈可排障、任意精度定时消息、磁盘堆积强、已有 Seata 运维 | 两类有状态组件；集成包拖 fastjson 1.x 要排 | 选定，服务端/客户端 5.3.2 |
| RabbitMQ | 3.90 | 路由模型贴合多订阅方、死信开箱、接入最省事 | Erlang 栈对 Java 团队是黑盒 | 未选 |
| Kafka | 2.60 | 流处理/事件溯源最强 | 没有延迟消息、没有死信概念、没有单条重试 | 未选 |
| Valkey Streams | 2.90 | 零新增依赖、有消费组/确认 | 与会话、缓存、分布式锁挤同一实例，堆积会触发淘汰 | 未选 |

评分上 RabbitMQ 高 0.05，但决策看的是权重最高的「排障可及性」：RocketMQ 5 分、RabbitMQ 2 分。RabbitMQ 赢的项目都有替代手段——路由模型差距可以在应用侧补一层，接入成本是一次性的；排障能力出事时补不回来。这不是「RabbitMQ 报错看不懂」，两边当天都因同一类原因启动失败过，报错都不提权限（`00-12-消息中间件技术选型.md:54-90`）。

### 为什么不用 RocketMQ 事务消息（半消息）

- 本地消息表和事务消息是同一个问题的两个解：都为了让「业务写库」和「发消息」同生共死。项目已经有 Outbox（还要覆盖邮件、通知等多通道），再上半消息就是重复建设。
- 代价：消息会重复（副作用做完、标记没写）、有投递延迟、重试/死信要自己写；消费端必须幂等。换来的是换 MQ 不用改业务、所有通道统一走一张消息表。
- 如果只用一个 MQ、且只发 MQ 一种副作用，半消息能少一张表；当前不是这个形态（`99-13...:58-64`；`00-12...:110-114`）。

### 为什么只同步发送，不用异步/单向

- 投递器要靠返回值决定「标已送达还是标失败」；异步发送和 `sendOneway` 都拿不到回执，等于把「确保送达 Broker」这一段扔了。
- 代价：每条消息同步等 Broker，吞吐受限于单条往返；项目用批量逐条发、租约控制并发，接受这个延迟。
- 如果业务能接受丢消息/只做日志采集，单向发送更便宜；这里的消息会触发业务动作，不能丢（`RocketMqTxMessageTransport.java:44-66`；`99-13...:60-64`）。

### 为什么单节点 + 同步刷盘，不做从节点

- 同步刷盘是一行配置加一次重启，堵的是进程被杀、断电、内核崩溃这类最常见故障；加从节点要多一台机器和一套复制配置，堵的是磁盘坏/整机报废，当前阶段不值这笔成本。
- 代价：每条消息等写盘，吞吐下降、发送延迟上升（没实测降多少）；单节点仍然扛不住磁盘/整机故障，这段时间也发不进去、消费不了。
- 如果消息重要到不能接受「整机没了就全没」，必须加从节点；当前先把落盘做对（`broker.conf:20-28`；`99-13...` 存储阶段）。

### 为什么没有 ACL、只绑回环

- 现在只有我方服务连 Broker，访问控制的收益有限；端口全部绑 `127.0.0.1`，测试服务器走反向代理，控制台不挂公网。
- 代价：任何能连上端口的人都能读写任意主题、删主题、重置位点；控制台免登录时更是把删主题按钮放在页面上。这是已知且暂不修的风险。
- 一旦队列要对外、或控制台要挂公网，必须先开 ACL + 控制台登录并换真口令；当前不满足这个前提（`99-13...` 安全现状；`README.md` 控制台段）。

### 什么条件下会反悔

- 买不到阿里云、改成自建或别家云 → 选型文档明确要回头重看（`00-12...:125-126`）。
- 消费失败/死信处理成为主要故障源 → 补死信消费者、告警、重放工具；当前只记录。
- 消息量/延迟超出单节点同步刷盘 → 加从节点、评估异步刷盘或换存储；当前没压测。
- 跨服务链路大量增加、`@TxListener`/监听器混用频繁出错 → 统一消费基类/代码生成；当前靠守卫 + 注释。

## 边界

- 42 个监听器类里 24 个文件最后一次提交人是本人、18 个是团队，不能证明每一行都是本人所写；本人证据集中在公共投递器、消费入口、死信测试、compose/运维、主题目录脚本、选型文档。
- 没做过生产流量验证：已验的是单条端到端收发、重试/死信机制；没有消费者堆积、消费延迟、吞吐/压测数据。
- 没做过幂等实现：公共库只提供 `message_id`，业务判重键和唯一约束没有统一落地。
- 没做过顺序消费；没有 `ORDERLY` 的实战。
- 没做过 RocketMQ 事务消息（半消息）、延迟消息、消息轨迹、ACL。
- 没有从节点/主从切换演练；单节点是明确取舍。
- 没有死信消费者/自动重放；死信只保证「不消失」。
- 控制台本机看不到 Broker 是 `brokerIP1=127.0.0.1` 的预期结果，不是故障；要看数据用 `mqadmin` 或临时改容器名。
- 版本升级未验证：5.3.2 是客户端/服务端对齐的结果，升 5.5 要两边一起升。

## 相关技能

- [[中间件与异步任务]]、[[Outbox]]、[[Spring Boot]]
- [[可观测性与OpenTelemetry]]（trace_id 进消息头，消费侧续链路）
- [[CI-CD与部署]]（compose、外置卷、端口绑定）
- [[Nacos]]（`transport`/`dispatcher-enabled` 配置源）
- 理论：[[消息系统理论]]、[[分布式系统理论]]、[[序列化与Schema演进理论]]

## 用在哪些工程能力

- 跨服务异步事件/通知
- 可靠投递与消费幂等
- 重试、死信与故障恢复
- 中间件部署与运维
