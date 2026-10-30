---
type: 项目证据
时间: 2026-08 ~ 2026-10
技术栈: [Java, Spring Boot, PostgreSQL, MyBatis-Plus, XXL-Job, Seata, Flyway]
---

# muou

**定位**：多租户会员/会籍管理 SaaS，按服务拆成 iam、member、platform、content、billing、notify 等模块，共用一个 PostgreSQL core 库，多仓写迁移。

**业务模块 → 相关节点（技能点/场景/实践）**

| 模块 | 相关节点 |
| --- | --- |
| 租户与 RLS | [[多租户与数据隔离]]、[[PostgreSQL]]、[[PostgreSQL RLS]]、[[RLS落地]]、[[租户隔离测试]] |
| 网关与配置 | [[Spring Cloud Gateway]]、[[Nacos]]、[[Spring应用与接口契约]] |
| 事务与 Outbox | [[事务与状态一致性]]、[[Outbox]]、[[Outbox落地]]、[[任务幂等]] |
| 分布式事务 | [[事务与状态一致性]]、[[Seata]]（5 个服务、11 个入口用 XA） |
| 定时任务 | [[XXL-Job]]、[[中间件与异步任务]]、[[定时任务多副本锁]] |
| 审计与 PII | [[安全与审计]]、[[PII加密]]、[[审计日志]]、[[PII加密落地]]、[[审计归档]] |
| 数据建模 | [[数据建模与迁移]]、[[数据建模]]、[[UUIDv7与业务编号]]、[[破坏性变更]] |
| 迁移体系 | [[Flyway与多仓迁移]]、[[多仓迁移落地]] |
| 支付回调 | [[任务幂等]]（回调幂等；真实渠道未接） |

## 项目级方案取舍

> 说明：muou 的选型文档比 smart 完整（`muou-app-doc/design/00-技术选型/`）；下面只整理项目级、跨模块的取舍，单技术细节见各技能页。

### 为什么多仓 + 共享 PostgreSQL core 库，不做微服务独立库

- **现状**：iam、member、platform、content、billing、notify 等按服务拆仓，共用一个 PostgreSQL core 库；迁移由 ops 仓 `collect.sh` 收集 7 个仓的脚本、按时间戳排序、拼 `build.sql` 人审执行（[[Flyway与多仓迁移]]、[[多仓迁移落地]]）。
- **候选**：单仓 monorepo；每服务独立库；共享库 + 多仓。选多仓是团队并行/权限边界，选共享库是跨服务查询/报表/事务简单；代价是迁移版本冲突、收集步骤、跨仓变更协调。
- **不选独立库**：跨服务 JOIN、报表、分布式事务会立刻变复杂；当前服务边界还没细到「每个服务独立数据」。反悔条件：服务/团队继续膨胀、共享库成为发布瓶颈 → 按领域拆库，先拆无跨服务 JOIN 的模块。

### 为什么 Outbox + RocketMQ 普通消息，不用 RocketMQ 事务消息

- **现状**：业务写和 outbox 记录同库同事务，投递器用 `FOR UPDATE SKIP LOCKED` + 租约抢批，发 RocketMQ 普通消息；消费者用 `TxMessageConsumerSupport` 做租户/事务/异常边界（[[RocketMQ]]、[[Outbox]]）。
- **候选**：RocketMQ 事务消息（半消息 + 回查）；本地消息表/Outbox；纯 Seata XA；Saga。选 Outbox 是因为「可靠投递」由自己掌控：消息表可查、可重放、可 dead，不依赖 MQ 的事务回查实现；RocketMQ 只做传输。
- **代价**：投递延迟（轮询）、outbox 表膨胀/清理、消费端必须幂等；没有用事务消息的「半消息」语义，也没做过 RocketMQ 事务消息生产落地。反悔条件：投递延迟成为业务问题、或 MQ 事务消息运维成熟 → 评估事务消息；但消费端幂等不能省。

### 为什么 Seata XA 只上 11 个入口，不全量

- **现状**：iam/member/billing/platform/content 五个服务开 XA，生产 11 处 `@MuouGlobalTx`（member 7、iam 3、content 1）；其余用本地事务 + Outbox 最终一致（[[Seata]]）。
- **取舍**：XA 强一致但同步阻塞、锁资源、TC 单点/性能成本；只给「钱/名额/状态必须一起成」的入口用，其余接受最终一致。没有上 AT/TCC/Saga 生产。
- **代价**：XA 入口要单独压测/故障演练（当前没做 TC 故障演练）；跨服务一致性有两套模型，排查要知道走哪套。反悔条件：XA 成为瓶颈/TC 不稳定 → 收缩到 Outbox/Saga；新增强一致入口要先评估是否真的需要 XA。

### 为什么 RLS + 应用层，不只靠应用过滤

- PostgreSQL RLS 做 L1 租户兜底（`FORCE` + 受限角色 + 事务级 `app.tenant_id`），L2 协同可见性/L3 岗位范围仍在应用层；应用漏过滤时数据库返回零行（[[PostgreSQL RLS]]）。
- 代价：会话变量、角色、策略、迁移都要维护；策略写错表现为「查不到数据」，排查成本高。反悔条件：B 型共享表策略复杂到难维护 → 收回应用层；迁 MySQL → 只能应用层。

### 为什么 Casbin 域内 RBAC，不用 Spring Security 方法级授权

- 需要四元判定（sub/dom/obj/act）、域隔离、策略表只读投影；jCasbin 把路径通配/主体分组/域比对做完，Spring Security 只给挂载点（[[认证与授权]]）。
- 代价：策略行数线性劣化、适配器/失效广播自己写；没有 ABAC。反悔条件：策略规模压不住 → OPA/自写哈希判定；需要 ABAC → 换模型。

### 什么条件下整体反悔

共享库成为发布瓶颈 → 拆库；Outbox 延迟/表膨胀不可接受 → 事务消息/分区归档；XA 入口故障 → 收缩最终一致；RLS 策略维护失控 → 应用层 + 测试；Casbin 策略规模/模型不匹配 → 换判定组件。

**我在这里练到的技能**：[[多租户与数据隔离]]、[[事务与状态一致性]]、[[Seata]]、[[安全与审计]]、[[数据建模与迁移]]、[[中间件与异步任务]]、[[Spring事务]]、[[测试与质量]]

**源路径**：`/Users/hujiuyuan/workspace/voidtech/muou-client`

**主要文档**：`muou-server/docs/`（表设计、RLS、迁移约定）、`muou-backend/muou-app-ops/databases/`

**边界**：顶层 `muou-client` 是空 git 仓库（0 次提交），但各服务仓是独立 git 仓库，我的提交可查：`muou-server` 283、`member` 583、`iam` 707、`content` 537、`platform` 299、`notify` 395、`billing` 321、`common` 144、`gateway` 82、`app-ops` 507、`admin` 496、`web` 423（`git log --author=hujiuyuan`）；`muou_arch` 的 32 次提交作者是 dodo。支付只做到离线渠道/桩网关；生产部署没有落地记录。
