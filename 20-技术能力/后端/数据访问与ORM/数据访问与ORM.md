---
type: 通用技能
域: 后端
证据: 实战/设计
---

# 数据访问与 ORM

**一句话**：ORM 只替我省掉「对象转 SQL」这部分；过滤、分页、软删、并发、租户这些自动行为，只在它生成的 SQL 上生效，绕开实体的查询必须自己补。

基础知识自测：[[数据访问与ORM基础]]

> 四层读法：理论 [[数据访问与ORM基础]]｜实践 本页「我用它干过什么」｜问题 [[软删除]]、[[MyBatis分页]]｜方案 [[smart WMS]]。总入口 [[四层读法]]。

## 一、理论：ORM 在链路上做了什么

1. **映射与 CRUD**：实体映射表/列，`save/getById/updateById/removeById` 由框架生成 SQL；手写 XML/`@Select` 不在自动规则内。
2. **插件链**：多个 `InnerInterceptor` 按注册顺序改写同一条 SQL。顺序错，语义就错——租户插件必须在分页之前，分页自动生成的 count 才会带租户条件。
3. **分页**：分页插件拼 `LIMIT` 并生成 count SQL；`maxLimit` 是服务端最后一道上限，业务参数校验通常只兜下限。
4. **软删除**：`@TableLogic` 或全局 `logic-delete-field` 让实体 CRUD 自动补 `deleted_at IS NULL`；裸 SQL、DTO/Map 投影不会。
5. **乐观锁**：靠实体 `@Version` 字段 + `update ... where version=?`；只注册插件、不加字段，等于没启用。
6. **多租户**：在 SQL 改写层统一追加 `tenant_id = ?`；跳过清单、平台账号、跨租户读取、解析失败都是缺口。
7. **共同边界**：框架按「实体/语句」生效，不按「表」生效；同一张表换个写法就可能绕过全部规则。

## 二、实际使用：smart WMS 的 MyBatis-Plus

- **插件链**：租户 → 分页（`maxLimit=1000`）→ 乐观锁 → 防全表更新，见 `MybatisPlusConfig.java:36-48`；注释写明租户必须在分页前，保证 count 同口径。
- **租户**：`WmsTenantLineHandler` 维护全局表清单、平台账号全量模式、表名归一化；跨租户读取走 `TenantIgnore`。详见 [[多租户拦截]]、[[租户插件落地]]。
- **软删除**：`@TableLogic(value="NULL", delval="NOW()")`、全局 `deleted` 字段、无注解手动过滤三种口径并存。详见 [[软删除]]。
- **分页**：DAO 里 `new Page<>(pageNum, pageSize)`（`UserDaoImpl.java:29-33`），count 与列表共用同一 wrapper；`maxLimit=1000` 兜底，`PageInfo` 只校验 `@Min(1)`（`PageInfo.java:22-30`）。
- **参数绑定**：JSON path 作为绑定参数传给 `wrapper.apply`，不拼 SQL 文本（`InfoDaoImpl.java:85-91`，回归测试 `SelfSyncFieldGuardTest.java:76-112`）。
- **只注册未使用**：`OptimisticLockerInnerInterceptor`、`BlockAttackInnerInterceptor`（`MybatisPlusConfig.java:44-48`）；仓库里没检索到 `@Version` 字段，也没找到依赖 BlockAttack 的测试。

## 三、归纳：数据访问检查清单

拿到一个 DAO 方法，按顺序问：

1. **SQL 谁生成的**：实体 CRUD / wrapper / XML 裸 SQL / `@Select`。后两种不吃实体注解。
2. **租户**：调用方 tenant 是否为空？表在跳过清单吗？跨租户是否 `TenantIgnore` + 上游归属校验？
3. **软删**：实体有 `@TableLogic` 吗？裸 SQL 写 `deleted_at IS NULL` 了吗？返回 DTO/Map 的查询呢？
4. **分页**：pageSize 上限谁兜？count 和列表是否同一套 where？租户/软删条件是否也进了 count？
5. **并发**：有 `@Version` 吗？没有就确认是不是靠条件更新（`where status=...`）保证原子性。
6. **注入**：用户输入进 SQL 文本，还是绑定参数？
7. **验证**：跨租户、软删行、count 口径各有一条测试吗？

### 三条红线

- 不要假设「表上有 tenant_id 就自动隔离」：裸 SQL 和跳过清单都能绕开。
- 不要只断言「删掉的不回」：要同时断言「活着的照回」，否则过度过滤也能绿灯。
- 不要只注册插件就算启用：乐观锁没有 `@Version`、防全表更新没有用例，都只是配置。

## 四、回到理论：为什么这些规则成立

- 插件链是**语句级改写**：它在 SQL 执行前动文本，所以顺序决定语义，也决定 count 是否被覆盖。
- 自动软删/租户依赖**实体元数据**：没有注解、没有字段、没有走实体映射，框架就没有改写依据。
- 所有自动化都有**逃生舱**（`TenantIgnore`、裸 SQL、自定义 XML）。逃生舱是必要的，但每次使用都等于把保障从框架挪回人。
- 软删除和租户是「每条查询都要带」的条件，适合放拦截层；但拦截层失效是静默的，必须用专项 IT 补。
- 这些原则换到 JPA/Hibernate 也成立：自动行为只覆盖框架生成的访问路径。

## 五、边界

- 只做过 MyBatis-Plus + MySQL；没做过 JPA/Hibernate、MyBatis 原生插件、多数据源、分库分表。
- 乐观锁只注册未使用；没验证过 `@Version` 并发更新。
- 防全表更新只注册；没找到依赖它的测试或用例。
- 租户插件覆盖不全：27 个 mapper XML 里有 16 个仍写 `tenant_id =` 过滤条件，类注释也承认存量 DAO 有大量手动 `eq("tenant_id")`；不能写「全仓租户隔离已完成」。
- 软删除在无注解实体、裸 SQL、投影查询上都要人工补条件，没做到「配置即生效」。

## 相关

- 技能点：[[MyBatis-Plus]]
- 方法：[[插件链]]、[[软删除过滤]]
- 场景：[[多租户拦截]]、[[软删除]]、[[MyBatis分页]]、[[乐观锁]]、[[分页与排序]]、[[租户字段与查询过滤]]
- 实践：[[租户插件落地]]
- 数据库：[[MySQL]]、[[查询性能优化]]
- 相邻通用技能：[[Spring应用与接口契约]]、[[时区与时间序列化]]
