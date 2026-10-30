---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战/设计
---

# MyBatis-Plus

所属通用技能：[[数据访问与ORM]]

**一句话**：用 MyBatis-Plus 的插件链和 wrapper 管住租户、分页、软删和参数绑定，同时清楚哪些 SQL 它管不到。

## 方法总纲

- 先分清 SQL 来源：实体 CRUD / wrapper 受插件和实体注解约束；XML 裸 SQL、`@Select` 不受。
- 再按 [[插件链]] 的「租户 → 分页 → 乐观锁 → 防全表更新」核对顺序，租户必须在分页前。
- 最后用专项 IT 验证跨租户、软删行、count 口径，不靠读代码下结论。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| [[租户插件落地]] | 实战 | [[smart WMS]] | 2026-06 | [[多租户拦截]]、[[租户字段与查询过滤]] |
| 软删除专项 IT | 实战 | [[smart WMS]] | 2026-08 | [[软删除]] |
| 分页上限与 count 同口径 | 配置/设计 | [[smart WMS]] | 2026-06 | [[MyBatis分页]]、[[分页与排序]] |
| JSON path 绑定参数 | 实战 | [[smart WMS]] | 2026-08 | JSON 字段查询（待建） |
| 乐观锁 / 防全表更新 | 仅注册，未使用 | [[smart WMS]] | 2026-06 | [[乐观锁]] |

## 选型与取舍

### 为什么用 MyBatis-Plus，不是 JPA / 裸 MyBatis / JOOQ

| 方案 | 优点 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| 裸 MyBatis | SQL 完全可控、映射透明 | CRUD/分页/租户/软删都要手写；XML 多 | 仍有大量 XML，插件管不到 |
| MyBatis-Plus | 通用 CRUD、wrapper、分页/租户/软删插件 | 插件顺序和注解会“隐式改 SQL”；裸 SQL/投影不受保护 | 主方案 |
| JPA/Hibernate | 领域模型、自动脏检查、跨库抽象 | 复杂查询要 Criteria/JPQL；SQL 不透明；团队/旧库迁移成本高 | 未使用，学习中 |
| JOOQ | 类型安全 SQL、编译期校验 | 代码生成/构建链复杂；团队学习成本 | 未使用 |

项目选 MP 的直接约束是既有 MyBatis XML 和 MySQL 生态：MP 能在不改旧 SQL 的前提下加通用 CRUD、分页和租户插件。代价是「隐式 SQL」——插件顺序、实体注解、全局配置都会改变最终 SQL；所以页面反复强调「先分清 SQL 来源」，并用专项 IT 验证。JPA 不是“更高级”，是另一种取舍：领域模型更顺，但复杂列表查询和旧库迁移更重。

### 为什么租户过滤放插件，不靠每条 SQL 手写

- 手写 `tenant_id = ?` 的失败模式是静默的：新 DAO、XML、DTO 投影漏一条就跨租户；插件在 SQL 解析层统一加条件，漏写概率低。
- 代价：JSqlParser 解析失败时 `SafeTenantLineInnerInterceptor` 选择跳过租户过滤而不是中断请求（`:33-39`），这是可用性优先的取舍，也是隔离缺口；所以还要有 `TenantIgnore` 逃生舱、跨租户 IT 和平台账号分流。
- 结论：插件是兜底，不是“配了就安全”；裸 SQL 仍然要手写，且要测试。

### 为什么软删除有三种口径

- 实体 `@TableLogic`：自动过滤/自动写删除时间，适合新实体；代价是只保护 MP 生成的 SQL。
- 全局 `logic-delete-field: deleted`：适合 `deleted TINYINT` 的操作记录表，少写注解；代价是字段名/值固定，和 `deleted_at` 表混用时容易搞错。
- 手动 `isNull`：适合历史表/无注解表；代价是每个读口都要记得写，漏了就把已删行捞回来。
- 这不是“三种都行”，是历史表和全局配置混用的现状；新表按 [[软删除]] 的决策树选一种，不要求全库统一，但要求每张表写清楚用哪套。

### 什么条件下会反悔

- 复杂领域模型/多数据库成为主流 → 评估 JPA 或 MyBatis-Flex；当前旧 XML 和 MySQL 绑定太深，迁移收益低。
- 插件解析失败导致隔离事故 → 把 `SafeTenantLineInnerInterceptor` 改成 fail-closed，代价是合法复杂 SQL 会被拒绝。
- 裸 SQL 占比继续上升 → 插件价值下降，应该收口 SQL 入口或改用编译期检查，而不是继续加注解。

## 我会的部分

- **插件链注册与顺序**：租户 → 分页（`maxLimit=1000`）→ 乐观锁 → 防全表更新，`MybatisPlusConfig.java:33-51`。
- **租户处理器**：全局表清单、平台账号全量模式、反引号/大小写归一化，`WmsTenantLineHandler.java:35-107`。
- **跨租户逃生舱**：`TenantIgnore.call` 用 `InterceptorIgnoreHelper` 临时关租户、`finally` 恢复，`TenantIgnore.java:30-36`；全仓 38 处调用。
- **三种软删口径**：实体 `@TableLogic(value="NULL", delval="NOW()")`（如 `Dock.java:89`、`ShippingTask.java:241`）；全局 `logic-delete-field: deleted`（`application.yml:129-131`，对应 `IoRecord.java:94`、`MoveLog.java:106`）；无注解手动 `isNull`（`FilesDaoImpl.java:40-41`）。
- **分页**：DAO 创建 `Page`（`UserDaoImpl.java:29-33`），count 与列表同 wrapper；上限由 `PaginationInnerInterceptor.setMaxLimit(1000L)` 兜（`MybatisPlusConfig.java:40-42`）。
- **参数化 custom SQL**：`wrapper.apply("... {0} ...", jsonPathParam(mainField))`，key 不进 SQL 文本（`InfoDaoImpl.java:85-91`；测试断言 SQL 段不含 key、绑定表里有 path，`SelfSyncFieldGuardTest.java:76-112`）。

## 边界

- `OptimisticLockerInnerInterceptor` 只注册，仓库内没有 `@Version` 字段，没验证过乐观锁并发更新。
- `BlockAttackInnerInterceptor` 只注册，没找到依赖它的测试或用例。
- XML 裸 SQL 的租户/软删条件不受自动规则保护：27 个 mapper XML 中 16 个仍写 `tenant_id =` 过滤条件，`TrailerMapper.xml:109` 明确写「原生 XML 无 @TableLogic 自动软删过滤」。
- `SafeTenantLineInnerInterceptor` 在 JSqlParser 解析失败时跳过租户过滤而非中断请求（`:33-39`），这是有意的可用性取舍，也是隔离缺口。
- 没做过多数据源、分库分表、MP 代码生成器、复杂嵌套结果映射。

## 相关技能

[[MySQL]]、[[查询性能优化]]、[[插件链]]、[[MyBatis分页]]、[[乐观锁]]、[[分页与排序]]、[[租户字段与查询过滤]]、[[字段调整与冗余]]

## 用在哪些工程能力

多租户隔离、数据访问层规范、软删除一致性（以上均未建卡，无页面）。
