---
type: 基础能力
通用技能: 查询性能优化
技能点: PostgreSQL
域: 数据库
证据: 学习中
---

# PostgreSQL 基础

技能点：[[PostgreSQL]] · 定位：基础知识挂载页

**一句话**：PostgreSQL 基础题的分类索引。这里回答「应该会什么」，不冒充「我做过什么」；做过的事仍记在实践卡。

## 怎么用

- 自测：看每一块的「要能回答」，能用自己的话讲清楚才算过。
- 挂笔记：新写一篇八股文，在对应块的「笔记」后加 `笔记名`，笔记里链回本页。
- 分边界：原理和机制放这里；具体故障、排查过程、修复方案放场景/实践卡。

## 1. 进程与存储

**一句话**：PostgreSQL 是进程模型，每个连接一个后端进程；数据按 8KB 页存放，MVCC 通过行版本和事务 ID 实现。

要能回答：

- PostgreSQL 为什么用多进程而不是多线程？连接数多了会怎样？
- 表、索引、TOAST 在磁盘上怎么组织？
- 死元组（dead tuple）怎么产生？VACUUM 做什么？
- `autovacuum` 什么时候触发？为什么它会跟不上？
- 事务 ID 回卷（wraparound）是什么？怎么监控？

笔记：

- PostgreSQL 用多进程：每个连接 fork 一个后端进程，共享 `shared_buffers`；进程隔离好、崩溃影响小，但每连接内存/上下文切换开销大，连接数上千要上连接池（PgBouncer）。
- 表是堆文件，按 8KB 页存行；大字段（>~2KB）压缩/拆到 TOAST 表；索引是独立文件，存指向堆行的 TID。
- MVCC 的 update/delete 不原地改，而是标记旧行并写新行；旧行成为死元组，占空间。VACUUM 标记空间可复用、更新可见性地图；普通 VACUUM 不还给操作系统，`VACUUM FULL` 会重写表并锁表。
- autovacuum 按「死元组数 > 阈值 + 比例」触发；长事务、长复制槽、大量更新会让它跟不上，导致表/索引膨胀。监控 `pg_stat_user_tables.n_dead_tup`、`last_autovacuum`。
- 事务 ID 是 32 位，约 40 亿后回卷；旧行会被当成「未来」而不可见。监控 `age(datfrozenxid)`，autovacuum 的 freeze 防止回卷，临近上限要手动 `VACUUM FREEZE`。

## 2. 数据类型

**一句话**：PostgreSQL 类型系统比 MySQL 丰富：`uuid`、`jsonb`、数组、范围、枚举、`timestamptz` 都是一等类型；选对类型比后面加索引更重要。

要能回答：

- `uuid`、`bigint`、自增 ID 怎么选？
- `json` 和 `jsonb` 的区别？什么时候不该用 jsonb？
- `timestamptz` 和 `timestamp` 的区别？底层怎么存？
- 数组类型适合什么？和关联表怎么选？
- 枚举类型怎么改？为什么改枚举要谨慎？
- `numeric` 和 `float8` 在金额场景怎么选？

关联：[[数据建模]]、[[UUIDv7与业务编号]]

笔记：

- `bigint` 自增：小、顺序写入、索引友好，适合单库；`uuid`：全局唯一、不可猜、适合分布式/对外暴露，但随机 UUIDv4 写入分散、索引膨胀；UUIDv7 带时间前缀，兼顾唯一和顺序。
- `json` 存原始文本、保留空格/键顺序，不索引；`jsonb` 存解析后的二进制、可建 GIN 索引、支持操作符。关系型字段不要塞 jsonb：更新整块、约束弱、查询难优化；jsonb 适合稀疏/可变扩展字段。
- `timestamptz` 存时刻（内部 UTC），`timestamp` 存墙钟；跨时区/绝对时间用前者，营业时间等墙钟语义用后者 + 时区字段。
- 数组适合「小、整体读写、不常按元素 join」的列表（标签、权限码）；多对多、需要按元素查询/统计/约束的用关联表。数组也能建 GIN 索引，但更新整列。
- 枚举加值可以 `ALTER TYPE ... ADD VALUE`（老版本不能在事务里），删值/改名要重建类型；枚举适合稳定小集合，频繁变更用 lookup 表或 `varchar + check`。
- 金额用 `numeric(19,4)` 精确十进制；`float8` 是二进制浮点，会有 0.1+0.2 问题，只适合科学计算/近似值。

## 3. 索引

**一句话**：B-tree 是默认索引；GIN 适合 jsonb/数组/全文，GiST 适合几何/范围，BRIN 适合大表按物理顺序的列；部分索引和表达式索引能显著减小体积。

要能回答：

- B-tree、GIN、GiST、BRIN、Hash 索引分别适合什么？
- 部分索引（`where`）什么时候有用？
- 表达式索引怎么匹配查询？
- 联合索引的列顺序怎么定？最左前缀在 PG 里怎么体现？
- 索引膨胀怎么发现？`REINDEX` 和 `VACUUM` 的区别？
- 模糊查询 `like '%x%'` 怎么用 `pg_trgm` 加速？

关联：[[索引失效]]、[[慢查询定位]]

笔记：

- B-tree：等值、范围、排序，默认；GIN：jsonb/数组/全文/trgm 的倒排索引，适合「包含/存在」；GiST：几何、范围、最近邻；BRIN：大表按物理顺序存储的列（时间序列），索引极小但只适合相关性高的数据；Hash：只支持等值。
- 部分索引：`WHERE status = 'PENDING'` 只索引热子集，体积小、写少；查询条件必须包含该谓词才能用。
- 表达式索引：`CREATE INDEX ON t (lower(email))`，查询要写同样的表达式 `lower(email) = ...` 才匹配；否则不生效。
- 联合索引列顺序：等值条件列在前，范围/排序列在后；PG 没有 MySQL 的「最左前缀」说法，但 B-tree 仍按列顺序匹配，跳过前导列通常不能用（除非有独立索引/位图组合）。
- 索引膨胀：大量 update/delete 后索引页空洞，`pg_stat_user_indexes` 看大小；`REINDEX` 重建索引，`VACUUM` 主要回收堆空间，不能消除索引膨胀。
- `pg_trgm`：`CREATE EXTENSION pg_trgm; CREATE INDEX ... USING gin (col gin_trgm_ops);` 让 `LIKE '%x%'`、相似度查询走 GIN；短模式/中文分词效果有限，必要时上全文检索。

## 4. 查询与执行计划

**一句话**：`EXPLAIN (ANALYZE, BUFFERS)` 看真实执行；重点看扫描方式、连接方式、预估行数与实际行数的偏差、缓冲区读写。

要能回答：

- `EXPLAIN` 和 `EXPLAIN ANALYZE` 的区别？
- Seq Scan、Index Scan、Bitmap Heap Scan、Index Only Scan 分别适合什么？
- Nested Loop、Hash Join、Merge Join 怎么选？
- 预估行数偏差大说明什么？统计信息怎么更新？
- `BUFFERS` 里的 shared hit/read 说明什么？
- 为什么加了索引还是走全表扫描？

关联：[[慢查询定位]]、[[SQL 优化]]

笔记：

- `EXPLAIN` 只显示预估计划和成本，不执行；`EXPLAIN ANALYZE` 真执行并给实际时间/行数（会执行写语句，注意事务回滚）；`BUFFERS` 加缓冲区命中/读盘。
- Seq Scan：小表或取大部分行时更快；Index Scan：高选择性、需要排序；Bitmap Heap Scan：中等选择性、先建位图再批量回表；Index Only Scan：只读索引，需要 visibility map（VACUUM 后）。
- Nested Loop：外表小、内表有索引；Hash Join：大表等值连接、无排序；Merge Join：两边已排序/有索引。优化器按成本选，统计信息不准会选错。
- 预估行数与实际差几个数量级：统计信息过期、列相关性、表达式/函数、参数化查询。跑 `ANALYZE`、调 `default_statistics_target`、建扩展统计（`CREATE STATISTICS`）。
- `shared hit` 是内存命中，`read` 是磁盘读；读多说明缓存不足或扫描量大，不代表 SQL 一定慢。
- 加了索引不走：列上有函数/类型转换、`LIKE '%x'`、低选择性、统计信息过期、表太小、索引膨胀/失效；用 `EXPLAIN` 看实际过滤条件和行数。

## 5. 事务、MVCC 与锁

**一句话**：PostgreSQL 默认 Read Committed；MVCC 让读写不互相阻塞，但会留下死元组；`SELECT ... FOR UPDATE` 加行锁，`SKIP LOCKED` 用于队列抢占。

要能回答：

- PostgreSQL 的四种隔离级别？默认哪个？
- Read Committed 和 Repeatable Read 在 PG 里怎么实现？
- 为什么 PostgreSQL 的 Repeatable Read 不会出现幻读？
- 行锁、表锁、 advisory lock 分别适合什么？
- `FOR UPDATE`、`FOR NO KEY UPDATE`、`FOR SHARE` 的区别？
- `SKIP LOCKED` 适合什么场景？有什么风险？
- 死锁怎么排查？

关联：[[Outbox]]、[[任务幂等]]、[[Spring事务]]

笔记：

- 隔离级别：Read Uncommitted（PG 实际等同 RC）、Read Committed（默认）、Repeatable Read、Serializable。RC 每条语句取新快照；RR 整个事务一个快照。
- PG 的 Repeatable Read 不会出现幻读：同一事务内快照不变，看不到新插入的行；代价是写冲突时可能 `could not serialize access`，要重试。Serializable 用 SSI 检测危险结构，冲突时 abort。
- 行锁：`SELECT ... FOR UPDATE` 锁行、阻止其他写；`FOR NO KEY UPDATE` 弱一点，不阻塞外键检查；`FOR SHARE` 共享锁，阻止写但允许其他共享。表锁（`LOCK TABLE`）粒度大，慎用；advisory lock 是应用自定义的整数锁，适合跨会话互斥。
- `SKIP LOCKED` 让队列消费者跳过已被锁的行，实现并发抢占；风险是可能跳过「正在处理」的行导致顺序乱、事务快照看不到刚提交的数据，适合「任务可并行、不要求严格顺序」。
- 死锁排查：`pg_locks` 看等待链，`pg_stat_activity` 看阻塞会话，日志里 `deadlock detected` 有两条语句；预防是固定加锁顺序、缩短事务、用 `NOWAIT/SKIP LOCKED`。

## 6. RLS 与多租户

**一句话**：RLS 由数据库强制加策略；`ENABLE` 只对普通用户生效，`FORCE` 让表 owner 也受约束，`USING` 管读、`WITH CHECK` 管写。

要能回答：

- RLS 的 `ENABLE`、`FORCE`、`POLICY` 分别是什么？
- `USING` 和 `WITH CHECK` 的区别？
- 租户 ID 怎么传给数据库？`set_config` 的事务级参数怎么用？
- 为什么表 owner 默认绕过 RLS？`FORCE` 解决什么？
- 连接池复用连接时怎么清理租户上下文？
- `BYPASSRLS` 角色应该怎么管？

关联：[[PostgreSQL RLS]]、[[RLS落地]]、[[多租户与数据隔离]]

笔记：

- `ENABLE ROW LEVEL SECURITY` 开启策略检查；`FORCE` 让表 owner 也受策略约束（默认 owner 绕过）；`POLICY` 定义 `USING`（读/可见行）和 `WITH CHECK`（写入后的行）。
- `USING` 管 select/update/delete 能看到哪些行；`WITH CHECK` 管 insert/update 后的新行是否允许。只写 `USING`，插入可能写到别的租户。
- 租户 ID 用事务级 `set_config('app.tenant_id', '...', true)` 或 `SET LOCAL`，事务结束自动失效；会话级变量要在连接归还前重置。
- 表 owner 默认绕过 RLS（防止自己锁死自己）；应用连接不能用 owner，用受限角色 + `FORCE`，否则策略不生效。
- 连接池：事务池（PgBouncer transaction）下 `SET LOCAL` 安全；会话级设置在连接复用时必须清理，否则串租户。
- `BYPASSRLS` 角色只给运维/迁移账号，单独凭证、单独审计、禁止应用使用；应用账号显式 `NOBYPASSRLS`。

## 7. 分区与归档

**一句话**：声明式分区按范围/列表/哈希拆分大表；查询裁剪只扫描相关分区，归档用 `DETACH PARTITION` 保留数据。

要能回答：

- 范围、列表、哈希分区分别适合什么？
- 分区键怎么选？为什么分区键要进主键/唯一索引？
- 分区裁剪（partition pruning）什么时候生效？
- 分区表上建索引和普通表有什么不同？
- `DETACH PARTITION` 和 `DROP PARTITION` 的区别？
- 分区太多有什么问题？

关联：[[审计归档]]

笔记：

- 范围分区适合时间/数值区间（按月、按年）；列表分区适合枚举/租户；哈希分区适合均匀打散、无自然范围。分区键要进主键/唯一索引（PG 要求唯一约束包含分区键）。
- 分区裁剪：查询条件能推导出分区键范围时只扫相关分区；用常量/参数化条件，函数包住分区键会失效；`EXPLAIN` 看是否只扫目标分区。
- 分区表上建索引：父表 `CREATE INDEX` 会递归到各分区（分区索引），也可以单独给热分区建；索引本身也按分区存在。
- `DETACH PARTITION` 把分区摘成独立表，数据保留、可归档/迁移；`DROP PARTITION` 直接删数据和分区。归档用 DETACH 再导出/压缩。
- 分区太多（成百上千）：规划时间变长、锁/DDL 变慢、连接/元数据开销大；按数据量和保留期控制分区数，定期归档旧分区。

## 8. 扩展与运维

**一句话**：PostgreSQL 用扩展加能力：`pg_trgm` 做模糊搜索、`pgcrypto` 做加密、`uuid-ossp`/`pgcrypto` 生成 uuid；运维重点是备份、复制、连接池和监控。

要能回答：

- 常用扩展有哪些？怎么安装？
- `pg_trgm` 的 GIN 索引怎么用？
- 逻辑复制和物理复制的区别？
- 流复制延迟怎么监控？
- PgBouncer 的会话池和事务池有什么区别？
- 备份方式有哪些？PITR 怎么工作？
- 连接数、锁等待、慢查询怎么监控？

笔记：

- 常用扩展：`pg_trgm`（模糊匹配）、`pgcrypto`（加密/摘要/uuid）、`uuid-ossp`（uuid 生成）、`postgis`（地理）、`hstore`（键值）；`CREATE EXTENSION` 安装，需要权限和对应包。
- `pg_trgm`：GIN/GiST 索引 + `%`/`similarity`/`LIKE '%x%'`，适合姓名/地址模糊搜索；中文按字符切 trigram，效果一般。
- 逻辑复制：发布/订阅表级、可跨版本/跨平台、可只复制部分表；物理复制：流式 WAL、整实例、备库只读。逻辑复制延迟看 `pg_stat_subscription`，物理看 `pg_stat_replication`。
- PgBouncer：会话池（连接绑定会话，兼容性好、复用低）、事务池（事务结束归还，复用高，但不支持会话级状态/部分 prepared statement）；应用要按池模式调整。
- 备份：`pg_dump` 逻辑备份（单库、可跨版本）、`pg_basebackup` 物理备份；PITR 靠基础备份 + 归档 WAL 回放到目标时间点。
- 监控：连接数（`pg_stat_activity`）、锁等待（`pg_locks` + `pg_blocking_pids`）、慢查询（`pg_stat_statements`）、复制延迟、死元组/膨胀、磁盘/IO。

## 常见对比题

- PostgreSQL vs MySQL
- `json` vs `jsonb`
- `timestamp` vs `timestamptz`
- B-tree vs GIN vs BRIN
- `ENABLE ROW LEVEL SECURITY` vs `FORCE ROW LEVEL SECURITY`
- `DETACH PARTITION` vs `DROP`
- 物理复制 vs 逻辑复制

## 我现在到哪

| 块 | 现状 | 依据 |
| --- | --- | --- |
| uuid、timestamptz、jsonb 建模 | 项目里落地过 | [[PostgreSQL]]、[[数据建模]] |
| RLS、事务级租户变量 | 项目里落地过 | [[PostgreSQL RLS]]、[[RLS落地]] |
| `SKIP LOCKED`、Outbox 抢占 | 项目里落地过 | [[Outbox落地]] |
| 分区、审计归档 | 项目里落地过 | [[审计归档]] |
| 复制、备份、PITR、连接池调优 | 学习和面试准备，未在项目落地 | 本页 |

## 边界

- 本页是索引，不是教材：每个问题只留一行，展开写到独立笔记。
- 项目里没有生产 DBA 经验，复制/备份/调优只是知识准备。
- 没有用过 PostgreSQL 的逻辑复制、FDW 和扩展开发。
