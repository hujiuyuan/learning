---
type: 技能点
域: 后端
项目: [muou-client]
证据: 实战/设计
---

# PostgreSQL RLS

所属通用技能：[[多租户与数据隔离]]

**一句话**：RLS 把租户条件写在表策略上，由事务级会话变量驱动；应用漏过滤时它仍返回零行，前提是启用 `FORCE`、执行角色不带 `BYPASSRLS`、且会话变量确实写进去了。

## 方法总纲

1. **三层隔离**：L1 租户硬隔离进数据库谓词；L2 协同可见性、L3 岗位数据范围留在应用层。RLS 只做 L1，避免策略谓词里塞角色和例外清单（`muou-server/docs/03-3-RLS与多租户数据隔离.md:56-64`）。
2. **A 型私有表策略**：`ENABLE` + `FORCE ROW LEVEL SECURITY`，策略 `USING (tenant_id = nullif(current_setting('app.tenant_id', true), '')::uuid)`。`current_setting(..., true)` 不报错返回 NULL，`NULLIF` 把空串折成 NULL，等值比较不为真 → 零行，fail-closed（同上 `:72-80`）。
3. **只写 USING**：PostgreSQL 会把同一表达式当 `WITH CHECK`，越权写入同被拦（同上 `:82`）。
4. **会话变量**：`set_config('app.tenant_id', ?, true)` 的第三参 `true` 是事务级，事务结束自动失效，连接回池不带脏值（`TenantAwareTransactionManager.java:23-24,63-71`）。
5. **白名单/忽略表**：没有 `tenant_id` 列或按设计跨租户的表不注入应用层条件；RLS 策略只贴在私有表上。清单靠架构测试和实体对齐（`TenantIgnoreTablesCheck.java:20-31`）。
6. **平台跨租户**：跳数据库层要用独立 `BYPASSRLS` 角色 + 受控入口 + 审计；`BYPASSRLS` 是角色属性，不是应用层注解（设计见 `03-3-RLS与多租户数据隔离.md:133-139`）。
7. **架构测试**：白名单漏登记会让拦截器拼出 42703；过期登记会让表悄悄少一道条件。两个方向都要测（`TenantIgnoreTablesCheck.java:20-26`）。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| notify 两张表启 RLS（ENABLE + FORCE + policy） | 实战 | muou-client | 2026-09 | [[RLS落地]] |
| `TenantAwareTransactionManager` 事务开头写 `app.tenant_id` / `app.org_scope` | 实战 | muou-client | 2026-09 | [[RLS落地]] |
| 白名单与实体对齐的架构测试（6 个服务各调一行） | 实战 | muou-client | 2026-09 | [[租户隔离测试]] |
| 受限角色下跨租户不可见、事务结束不残留租户 | 实战 | muou-client | 2026-09 | [[租户隔离测试]] |
| B 型共享表策略（`visible_tenants` + `org_scope`） | 设计 | muou-client | 2026-09 | — |
| `BYPASSRLS` 平台入口 | 设计 | muou-client | — | — |

## 我会的部分

- 写 A 型策略：`ENABLE`、`FORCE`、`USING`、`nullif(current_setting(...), '')::uuid`。
- 用事务管理器在 `prepareTransactionalConnection` 里写会话变量；没有租户时写空串而不是跳过。
- 用 `FORCE` 让表 owner 也受策略约束。
- 用受限角色（`NOSUPERUSER NOBYPASSRLS`、非表 owner）跑测试，避免管理员连接掩盖策略失效（`RestrictedRoleAssertions.java:21,60`）。
- 用架构测试检查「实体没有 `tenantId` ↔ 表在白名单」两个方向。

## 选型与取舍

### 为什么用 RLS，不只靠应用层过滤

| 方案 | 隔离强度 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| 应用层 `WHERE tenant_id = ?` | 依赖每条 SQL 都写对 | 手写 SQL/解析失败/新 DAO 漏写就裸奔 | smart WMS 的做法（MySQL 无 RLS） |
| PostgreSQL RLS（当前） | 数据库兜底；漏写也返回零行 | 会话变量、角色、策略、迁移都要维护；调试看到零行不易定位 | muou 私有表 |
| schema/独立库 | 物理隔离 | 迁移 × N、连接路由、跨租户查询难 | 未选 |

RLS 的价值是「fail-closed」：应用忘了带条件，数据库策略仍把行过滤掉。它不能替代应用层授权（L2/L3 的角色、岗位范围仍在应用层），但能兜住 L1 租户隔离。

### 为什么必须 `FORCE` + 受限角色 + 事务级会话变量

- `ENABLE ROW LEVEL SECURITY` 默认对表 owner 不生效；不加 `FORCE`，迁移/运维连接（owner）能绕过策略，测试也会假绿。
- 应用连接角色必须是 `NOSUPERUSER NOBYPASSRLS`、非 owner；超级用户/BYPASSRLS 角色绕过所有策略，拿管理员连接测 RLS 等于没测。
- `set_config('app.tenant_id', ?, true)` 第三参 `true` 是事务级，事务结束自动失效，连接回池不带脏值；如果设成会话级，连接池复用会把上一个租户的 ID 带进下一个请求，这是最危险的泄漏。
- 没有租户时写空串而不是跳过：`current_setting(..., true)` 返回 NULL/空串，`NULLIF` 折成 NULL，等值比较不为真 → 零行，fail-closed；跳过设置会保留上一个事务的值。

### 为什么只做 A 型私有表，B 型共享表只留模板

A 型表每行只属于一个租户，策略最简单；B 型共享表（`visible_tenants` + `org_scope`）策略谓词复杂、性能/可维护性差，当前没有建表和写入服务，只留设计模板。RLS 不是「所有表都贴上策略」；没有 `tenant_id` 或按设计跨租户的表进白名单，白名单靠架构测试双向校验。

### 代价与反悔条件

- 策略变更/大批量回填/锁表没有生产运维经验；策略写错的表现是「查不到数据」，不是报错，排查成本高。
- `BYPASSRLS` 平台入口只读过设计，没实际跑过；平台跨租户要用独立角色 + 受控入口 + 审计，不能给应用主角色加 `BYPASSRLS`。
- 如果迁到 MySQL → 只能回应用层过滤；如果 B 型共享表变多、策略难维护 → 把 L2/L3 收回应用层，只保留 L1；如果 RLS 查询性能成为瓶颈 → 检查 `tenant_id` 索引和策略谓词，必要时物化/分区。

## 边界

- 只落过 A 型私有表；B 型共享表没有建表和写入服务，策略只是模板（`03-3-RLS与多租户数据隔离.md:84-102`）。
- 没有生产运维经验：没处理过策略变更、大批量回填、锁表。
- 没有实际用 `BYPASSRLS` 角色跑过平台跨租户入口，只读过设计分级。
- RLS 是 PostgreSQL 专有；MySQL 不能照搬，smart 只有应用层过滤。
- 迁移基线出过「设计写启、生成脚本误判成不启」的漏开，说明是否启用必须以迁移为准逐表核对（`V202609231221__notify_rls_notify_type_and_template.sql:1-6`）。

## 相关技能

- [[MySQL租户字段]] — 没有 RLS 时，隔离全靠应用层
- [[多租户拦截]] — MyBatis-Plus 侧的注入与逃生舱
- [[数据访问与ORM]] — 拦截器只覆盖它改写得到的 SQL

## 用在哪些工程能力

- 数据访问与 ORM：租户条件是「每条查询都要带」的条件，RLS 是数据库层兜底。
- 认证与授权：平台账号、跨租户入口属于授权边界，RLS 只是最后一道。
