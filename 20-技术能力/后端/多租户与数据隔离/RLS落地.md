---
type: 实践
技能点: PostgreSQL RLS
项目: [muou-client]
时间: 2026-09
证据: 实战
---

# RLS落地

技能点：[[PostgreSQL RLS]] · 项目：muou-client · 2026-09

场景：租户硬隔离（场景页待建）

## 我想干什么

让数据库在应用漏写租户条件时也返回零行；每个事务一开就带上当前租户，事务结束不残留。应用层拦截器作为第二道，负责在 SQL 里拼等值条件。

## 我干了什么

- 给 notify 两张表补 RLS：`ENABLE` + `FORCE` + policy，谓词用会话变量 `app.tenant_id`（`muou-backend/muou-server-notify/muou-notify-app/db/migration/message/V202609231221__notify_rls_notify_type_and_template.sql:8-16`）。
- `TenantAwareTransactionManager` 在 `prepareTransactionalConnection` 里执行 `set_config('app.tenant_id', ?, true)` 和 `app.org_scope`，事务级生效；没有租户时写空串（`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/tenant/TenantAwareTransactionManager.java:23-24,63-71`）。
- `MuouTenantLineHandler` 作为应用层第二道：有租户注入当前租户，没有租户注入查不到的哨兵 UUID，白名单表跳过（`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/persistence/MuouTenantLineHandler.java:20-30,43,63-66`）。
- 白名单检查：`TenantIgnoreTablesCheck` 断言「实体没有 `tenantId` ↔ 表在白名单」两个方向，各服务在自己的 arch 测试里调一行（`muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/arch/TenantIgnoreTablesCheck.java:20-31`；`muou-backend/muou-server-notify/muou-notify-app/src/test/java/com/voidtech/muou/notify/arch/NotifyArchTest.java:80` 等 6 个服务）。
- 测试：受限角色 + `TenantAwareTransactionManager` 跑 Mapper，断言只能读到本租户；事务外的新连接读同一张表为 0（`muou-backend/muou-server-member/muou-member-app/src/test/java/com/voidtech/muou/member/form/FormTemplateRlsTest.java:32-33,43-50`）。

## 犯了什么错 / 误判

1. **设计写「启」，生成脚本误判成「不启」**：基线建表脚本把同一行里「由不启改启」的沿革读反，两张表都没开 RLS；只能再写增量迁移补（`V202609231221__notify_rls_notify_type_and_template.sql:1-6`）。
2. **以为 `getTenantId()` 可以返回「恒假条件」**：返回 `EqualsTo('1','0')` 会被拦截器填进等号右边，拼出 `tenant_id = '1' = '0'`，PostgreSQL 报语法错；症状是 `BadSqlGrammarException`，完全看不出跟租户有关（`MuouTenantLineHandler.java:55-61`；回归测试 `MuouTenantLineHandlerTest.java:62-66`）。
3. **设计文档与代码不一致**：文档写「无租户返回 `1 = 0` 表达式」（`03-3-RLS与多租户数据隔离.md:118`），代码实际返回哨兵 UUID，因为表达式方案跑不通。落地以代码和测试为准。
4. **插入也补哨兵**：读/改查不到是安全，插入填哨兵会把行写进一个谁也看不见的租户；改为无上下文时不补列，让约束或 RLS 当场报错（`MuouTenantLineHandler.java:74-83`）。
5. **误以为事务管理器无所谓**：默认退化成 Boot 自带的事务管理器等于关掉 RLS，而且不报错；有测试断言默认装配必须是 `TenantAwareTransactionManager`（`TxAutoConfigurationTest.java:63-70`）。

## 怎么解决

- 策略统一用 A 型模板：`ENABLE` + `FORCE` + `nullif(current_setting('app.tenant_id', true), '')::uuid`，空串和未设置都走零行。
- 会话变量用事务级 `set_config(..., true)`，事务结束自动失效；连接回池不带脏值由测试兜住。
- 无租户上下文时：读/改注入哨兵，插入不补列。
- 白名单用架构测试锁住两个方向；有 `tenant_id` 但按设计免注入的表走 `extraIgnored` 明着登记。
- 测试用 `NOSUPERUSER NOBYPASSRLS` 且非表 owner 的受限角色，避免管理员连接让策略看起来生效（`RestrictedRoleAssertions.java:21,60`）。

## 现在的规矩

- 新私有表建表迁移末尾直接贴 A 型策略，不另起批次补。
- 表 owner 也必须受约束，所以 `FORCE` 不能省。
- 执行角色不能带 `BYPASSRLS`；真跨租户走独立平台入口，不走普通 DAO。
- 白名单变更必须同时过架构测试；过期登记和漏登记都会红。
- 不把设计文档里的伪代码当实现，策略以迁移脚本为准逐表核对。

## 证据

- `muou-backend/muou-server-notify/muou-notify-app/db/migration/message/V202609231221__notify_rls_notify_type_and_template.sql:1-16`
- `muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/tx/tenant/TenantAwareTransactionManager.java:18-24,62-71`
- `muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/persistence/MuouTenantLineHandler.java:20-30,38-43,55-66,74-83`
- `muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/arch/TenantIgnoreTablesCheck.java:20-31`
- `muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/persistence/MuouTenantLineHandlerTest.java:44-66`
- `muou-backend/muou-common/muou-common-app/src/test/java/com/voidtech/muou/common/tx/TxAutoConfigurationTest.java:63-70`
- `muou-backend/muou-server-member/muou-member-app/src/test/java/com/voidtech/muou/member/form/FormTemplateRlsTest.java:32-33,43-50`
- `muou-backend/muou-common/muou-common-test/src/main/java/com/voidtech/muou/common/test/RestrictedRoleAssertions.java:21,60`
