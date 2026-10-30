---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战/设计
---

# MySQL租户字段

所属通用技能：[[多租户与数据隔离]]

**一句话**：MySQL 没有 RLS，租户隔离只能靠应用层；`tenant_id` 的可空性、平台账号的 NULL 语义、索引首列、以及拦截器覆盖不到的手写 SQL，决定隔离是真还是形同虚设。

## 方法总纲

1. **先定可空性**：`tenant_id NOT NULL` 表示「每条数据必属一个租户」；可空表示存在平台级/全局行。NULL 表示什么必须能说清。
2. **平台账号**：`tenant_id IS NULL` 的账号看全量；普通账号只匹配自己的 `tenant_id`。可见范围在 SQL 里显式写，不靠「没传租户」。
3. **索引打头**：高频查询建 `(tenant_id, ...)` 联合索引；但 `tenant_id` 选择性极低、或查询本来就走别的索引时，别机械加。
4. **拦截器分工**：实体 CRUD / wrapper / mapper XML 交给 `TenantLineInnerInterceptor` 尝试改写；`JdbcTemplate` 完全不经过它；复杂 JOIN 和解析失败的语句要自己写条件并核对。
5. **忽略清单**：没有 `tenant_id` 列、确需跨租户、已有显式过滤（避免 JOIN 歧义）三类才进；理由要能写出来。
6. **NULL 行**：历史未回填、平台保留数据会被严格 `tenant_id = ?` 打空；要用 `= ? OR tenant_id IS NULL`，或先回填。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 全局表清单 + 平台账号全量模式 + 表名归一化 | 实战 | smart WMS | 2026-06 | [[多租户拦截]] |
| 租户插件排在分页前，保证 count 同口径 | 实战 | smart WMS | 2026-06 | [[租户插件落地]] |
| `goods` 99.98% NULL：`TenantIgnore` + 手写 `(tenant_id = ? OR IS NULL)` | 实战 | smart WMS | 2026-07 | [[平台账号与NULL]] |
| `login_log` 加 `tenant_id`、按 caller 分流过滤 | 设计 | smart WMS | 2026-05 | [[登录日志租户隔离]] |
| `requireTenantId()` 写侧守卫 | 设计 | smart WMS | 2026-06 | [[租户字段与查询过滤]] |
| `tenant_id` 打头的联合索引 | 设计 | smart WMS | 2026-05 | — |

## 我会的部分

- 用 `TenantLineHandler` 控制「给谁注入、注入什么值、插入补不补列」（`WmsTenantLineHandler.java:85-108`）。
- 平台账号 `tenantId == null` 时整表跳过，普通账号只跳过全局表（`WmsTenantLineHandler.java:97-107`）。
- 表名匹配前剥离反引号并小写，避免 JSqlParser 保留原始写法导致清单失配（`WmsTenantLineHandler.java:100-107`）。
- 对 NULL 比例极高的表，关掉自动注入后手写 `= ? OR IS NULL`（`GoodsMapper.xml:14-27`）。
- 用 IT 验证跨租户 count 为 0、平台账号能看到全量（`TenantIsolationIT.java:104-140,172-195`）。

## 选型与取舍

### 为什么用共享表 + `tenant_id`，不做 schema/独立库

| 方案 | 隔离强度 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| 共享表 + `tenant_id` + 拦截器（当前） | 应用层；数据库不兜底 | 每条 SQL 都要带条件；解析失败/手写 SQL 会漏；租户多时索引选择性低 | 选定 |
| schema-per-tenant | 中；连接/迁移按 schema 切 | 租户多了迁移 × N、连接路由、跨租户报表难 | 未选 |
| database-per-tenant | 高；故障/备份隔离 | 运维成本最高、跨租户统计要汇总、小租户浪费 | 未选 |
| PostgreSQL RLS | 高；数据库兜底 | MySQL 没有；会话变量/角色/策略要维护 | MySQL 不可用 |

选共享表是因为租户数量多、单租户数据量不大、需要跨租户运营报表；schema/独立库会让迁移和连接路由变成 N 倍成本。代价是隔离靠应用层，必须用拦截器 + 手写条件 + 测试三重保证。

### 为什么拦截器 + 手写条件并存

- 拦截器（`TenantLineInnerInterceptor`）覆盖实体 CRUD、wrapper、大部分 mapper XML，减少重复；但它靠 JSqlParser 改写，解析失败会 warn 后跳过，复杂 JOIN/子查询可能改不对。
- 手写条件（`tenant_id = ?`）显式、可 review，但 27 个 mapper XML 里仍有 16 个手写，插件不能当全覆盖证明。
- 两类都要：拦截器兜底常规路径，手写/测试覆盖复杂 SQL 和逃生舱；只靠任一方都会漏。

### 为什么 `tenant_id` 不总是索引首列

`tenant_id` 选择性低（一个租户可能占大部分行），单独当首列不一定能缩小范围；但多租户查询通常先按租户过滤，联合索引 `(tenant_id, status, ...)` 能让每个租户的查询走同一索引。要按真实查询和选择性决定，不能机械「所有索引都加 tenant_id」。

### 代价与反悔条件

- 解析失败跳过过滤、子表靠父表间接隔离、NULL 行语义，都是已知漏点；靠 IT 和代码 review 守。
- 如果租户数量少、单租户数据大、合规要求物理隔离 → 评估 schema/独立库；如果迁到 PostgreSQL → 评估 RLS 做数据库兜底；如果跨租户报表成为主查询 → 单独走数仓/只读库，不要在业务库上放开过滤。

## 边界

- MySQL 没有 RLS；数据库层不会兜底，拦截器漏掉的语句就是裸奔。
- 解析失败会跳过过滤：`SafeTenantLineInnerInterceptor` 捕获 `ParseException` 后只记 warn（`SafeTenantLineInnerInterceptor.java:33-39`）。
- 存量手写过滤仍在：27 个 mapper XML 里 16 个仍写 `tenant_id =`，插件只是多一层，不能当全覆盖证明（`多租户拦截.md:35`）。
- 子表靠父表间接隔离，父表过滤漏了子表就漏（`WmsTenantLineHandler.java:54-58`）。
- 没做过分库分表、独立库/schema 的多租户；`tenant_id` 索引设计只有方案，没有压测数据。

## 相关技能

- [[PostgreSQL RLS]] — 数据库层兜底的另一条路
- [[多租户拦截]] — MyBatis-Plus 插件链与逃生舱
- [[SQL 优化]] — 联合索引与选择性

## 用在哪些工程能力

- 数据访问与 ORM：租户条件收在数据访问层，调用方不传 `tenant_id`。
- 查询性能优化：`tenant_id` 打头的索引是否命中，决定多租户查询的成本。
