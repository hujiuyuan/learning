---
type: 技能点
域: 数据库
项目: [muou]
证据: 实战/设计
---

# PostgreSQL

所属通用技能：[[数据建模与迁移]]、[[多租户与数据隔离]]、[[查询性能优化]]

**一句话**：在 muou 里 PostgreSQL 不是「MySQL 换皮」：uuid 主键、`timestamptz`、`jsonb`、RLS、`SKIP LOCKED` 队列和按月分区，分别解决主键、时间、半结构化、租户隔离、并发抢占和历史归档。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/`。

## 方法总纲

1. **主键用 uuid，业务编号另存**：不暴露自增规模；跨服务生成不冲突。
2. **时刻用 `timestamptz`**：应用层传 UTC/`Instant`，不要用无时区的 `timestamp` 存时刻。
3. **半结构化放 `jsonb`，可筛选字段提列**：会被 where/order by 的字段留在 jsonb 里，等于放弃索引。
4. **租户隔离优先 RLS**：`ENABLE` + `FORCE` + 事务级 `set_config`，应用层过滤只做补充。
5. **队列抢占用 `FOR UPDATE SKIP LOCKED`**：先查后改在并发下会重复抢同一行。
6. **大表按时间分区，归档用 detach**：`DETACH PARTITION` 不删数据，删除是不可逆动作。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| uuid + `timestamptz` + `jsonb` 建模 | 实战 | muou | 2026-09~10 | [[数据建模]]、[[多仓迁移落地]] |
| 两张 notify 表启用 RLS | 实战 | muou | 2026-09 | [[RLS落地]] |
| Outbox 用 `SKIP LOCKED` 抢占 | 实战 | muou | 2026-09 | [[Outbox落地]] |
| 审计日志按月分区、到期 detach | 实战 | muou | 2026-10 | [[审计归档]] |
| 部分索引、GIN/trgm 索引 | 实战 | muou | 2026-09~10 | [[数据建模]] |
| 平台跨租户 `BYPASSRLS` 入口 | 设计 | muou | — | [[PostgreSQL RLS]] |

## 选型与取舍

### 为什么 muou 用 PostgreSQL，不是继续 MySQL

| 需求 | PostgreSQL 的做法 | 换 MySQL 要付的代价 |
| --- | --- | --- |
| 不暴露自增规模、跨服务生成主键 | `uuid` + `gen_random_uuid()` | 应用层生成 UUID 或号段；索引更大、随机写更散 |
| 时刻类型不丢时区 | `timestamptz` + `OffsetDateTime` | `datetime` + 应用层统一时区；跨时区仍要靠约定 |
| 半结构化字段 | `jsonb` + GIN 索引 | JSON 函数/生成列；复杂查询和索引能力弱 |
| 租户隔离兜底 | RLS（`ENABLE` + `FORCE` + 事务级 `set_config`） | 只能靠应用层每条 SQL 带租户条件；漏一条就泄漏 |
| 队列抢占 | `FOR UPDATE SKIP LOCKED` | 8.0 有 `SKIP LOCKED`，但旧版本/生态要另做 |
| 大表归档 | 按月分区 + `DETACH PARTITION` | 分区/归档要更多手工 DDL |

代价也要写清楚：团队原来以 MySQL 为主，PG 的 RLS、角色、`VACUUM`、连接池行为都要重新学；项目只在两张 notify 表启用 RLS，其他表仍然应用层过滤，说明 RLS 不是“开了就全库安全”，而是逐表设计。这个选择不是「PG 更先进」，是 muou 需要 uuid/jsonb/RLS/SKIP LOCKED 这些能力，并且愿意承担运维学习成本。

### 为什么租户隔离用 RLS，不只靠应用层

- 应用层过滤的失败模式是静默的：新写一条裸 SQL、DTO 投影、定时任务，忘了 `tenant_id = ?` 就跨租户泄漏；RLS 把兜底放在数据库，漏写条件时直接返回零行。
- 代价：连接池里每个事务都要 `set_config('app.tenant_id', ?, true)`，漏设就 fail-closed；平台跨租户入口要 `BYPASSRLS` 角色，不能和普通业务连接混用；排查时要先看当前 session 的租户变量。
- 项目只对两张 notify 表启用 RLS（`V202609231221__notify_rls_notify_type_and_template.sql:8-16`），不是全库；这正说明 RLS 的代价——每张表都要写策略、测越权、配平台 bypass，不能一键铺开。

### 为什么 jsonb 和固定列混用

- 纯 jsonb 的优点是 schema 灵活、半结构化数据不用频繁改表；缺点是约束、外键、类型检查都弱，`WHERE jsonb_col->>'x'` 没索引就全表扫。
- 项目的改判是：会被筛选/排序的字段提成固定列，剩下真正半结构化的内容才放 jsonb（`member_qual_type.grace_days` 的注释写明这个改判，`V202609231243__member_correction_and_columns.sql:91`）。
- 代价：同一个业务对象有「列 + jsonb」两套读取路径，写入时要保证两边一致；提列后旧 jsonb 数据要回填/兼容。

### 为什么主键用 uuid，不用 bigint

- uuid 不暴露数据量、跨服务可生成、合并/导入不撞号；代价是索引更大、随机写导致页分裂，范围查询/排序不如自增 ID。
- 项目接受这个代价，是因为多服务/多仓写入和外部不可枚举优先；如果只是单库单服务、追求写入密度，bigint 自增更合适。UUIDv7 的时间有序版本是另一条路，见 [[UUIDv7与业务编号]]。

### 什么条件下会反悔

- RLS 策略数量/连接池开销成为瓶颈 → 退回应用层过滤 + 关键表保留 RLS，但要做越权测试。
- jsonb 查询越来越多、GIN 索引撑不住 → 把字段提列或拆子表。
- uuid 随机写导致索引膨胀 → 评估 UUIDv7/雪花号段；不要直接换回自增，先看跨服务生成需求。

## 我会的部分

- **uuid 主键**：核心表主键、租户、操作人统一 `UUID`（`muou-backend/muou-app-ops/databases/migration/core/V202609112100__core_init.sql:3-28`）；种子数据用 `gen_random_uuid()`（`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202610262110__seed_cert_renew_application_type.sql:14`）。
- **时间类型**：`TIMESTAMPTZ` 存时刻（`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202610132200__member_create_membership_expiry_notice.sql:14-15`）；Java 侧用 `OffsetDateTime` 读写。
- **jsonb**：半结构化内容、文件 id 列表、导入批次行都放 `jsonb`（`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202610270900__member_followup_setting.sql:12`、`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202610252130__qualification_history_import_batch.sql:11`）；但会被筛选的字段提成固定列，`member_qual_type.grace_days` 的注释写明了这个改判（`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202609231243__member_correction_and_columns.sql:91`）。
- **部分索引**：软删除表用 `where deleted_at is null` 的部分索引（`muou-backend/muou-app-ops/databases/migration/core/V202609112100__core_init.sql:691`、`:832`）。
- **GIN/trgm**：姓名、证件号模糊查询用 `gin_trgm_ops`（`muou-backend/muou-server-iam/muou-iam-app/db/migration/core/V202609211813__iam_index_adjust.sql:51-52`）。
- **`ON CONFLICT`**：固定主键的种子数据用 `on conflict do nothing`，重复执行不报错也不覆盖（`muou-backend/muou-server-member/muou-member-app/db/migration/core/V202609291927__member_right_word_assembly_vote_preset.sql:9-16`）。
- **RLS**：`ENABLE` + `FORCE` + `USING` 策略；事务级 `set_config('app.tenant_id', ?, true)`（`muou-server/src/main/java/com/voidtech/muou/config/TenantAwareTransactionManager.java:30`、`muou-backend/muou-server-notify/muou-notify-app/db/migration/message/V202609231221__notify_rls_notify_type_and_template.sql:8-16`）。
- **`SKIP LOCKED`**：Outbox 投递器并发抢占，第二个人跳过已锁行（`muou-server/src/test/java/com/voidtech/muou/dao/OutboxEventDaoIT.java:240`）。
- **分区**：审计/访问日志按范围分区（`muou-backend/muou-app-ops/databases/migration/core/V202609112100__core_init.sql:1223`）；归档任务只 detach，不 DROP（`muou-backend/muou-server-notify/muou-notify-app/src/main/java/com/voidtech/muou/notify/service/logstore/AuditLogArchiveService.java:40,76-118`）。

## 边界

- 没有生产运维经验：没做过主从切换、备份恢复、VACUUM 调优、连接池压测。
- 没有用 `BYPASSRLS` 角色跑过平台跨租户入口，只读过设计分级。
- 没有做过分区表的在线扩容和跨分区迁移。
- 没有用过 PostgreSQL 的发布订阅、逻辑复制、FDW、扩展开发。
- 项目里的 SQL 以 MyBatis/JDBC 为主，没有使用 PostgreSQL 专属 ORM。

## 相关技能

- [[PostgreSQL RLS]]、[[RLS落地]]、[[租户隔离测试]]
- [[数据建模]]、[[Flyway与多仓迁移]]、[[多仓迁移落地]]
- [[Outbox]]、[[Outbox落地]]、[[任务幂等]]
- [[MySQL]]（对比：MySQL 没有 RLS，租户隔离靠应用层）

## 用在哪些工程能力

- 多租户数据隔离（RLS、事务级租户变量）
- 事务与状态一致性（Outbox 抢占、租约）
- 数据建模与迁移（uuid、jsonb、分区、多仓迁移）
- 安全与审计（审计日志分区归档）
