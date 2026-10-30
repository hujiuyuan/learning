---
type: 场景
技能点: MyBatis-Plus
方法: 插件链
证据: 实战/设计
---

# MyBatis 分页

技能点：[[MyBatis-Plus]] · 方法：[[插件链]] · 通用技能：[[数据访问与ORM]]

**什么时候会遇到**：列表接口要分页，但 total 和列表对不上、深页越翻越慢、前端传了超大 pageSize，或者租户/软删条件只进了列表没进 count。

## 判断顺序

1. **分页对象谁创建**：DAO 里 `new Page<>(pageNum, pageSize)`，还是 XML 自己拼 `LIMIT`。后者不吃分页插件。
2. **count 和列表是不是同一个 wrapper**：同一条件才同口径；两边各写一套，租户、软删、筛选迟早漂移。
3. **租户插件在不在分页前**：租户必须先改写 SQL，分页插件再生成 count；顺序反了，count 可能漏租户条件。
4. **pageSize 上限谁兜**：参数校验只包下限时，服务端 `maxLimit` 是最后一道；但它只截行数，不省 count。
5. **要不要精确 total**：大表每次 `COUNT(*)` 本身贵；产品能接受估算/缓存时，别默认 `searchCount=true`。

## 手段

- 统一入口：`PageInfo` 只放 `pageNum/pageSize`，DAO 用 `Page` 透传给 mapper；列表和 count 共用同一个查询条件。
- 插件顺序：租户 → 分页，见 `MybatisPlusConfig.java:36-42`；分页插件注册 `DbType.MYSQL` 并设 `maxLimit=1000L`。
- 参数兜底：`PageInfo` 用 `@NotNull + @Min(1)` 挡住 0、负数、null（`PageInfo.java:22-30`）；上限交给插件，不在每个 DTO 重复写。
- 大表 count：先问「是否每次都要精确值」；不需要就关 `searchCount` 或走缓存/统计表。
- 深分页：没有实测证据，不写成已优化；有需求时再比较延迟关联/游标。

## 反例 / 边界

- 只写 `@Min(1)` 不写 `@Max`：前端传 `pageSize=100000` 时，靠 `maxLimit` 截到 1000；这是兜底，不是参数校验。
- count 与列表各写一套 where：列表带 `tenant_id`、count 没带，total 偏大。
- 分页插件排在租户插件前：分页插件生成的 count SQL 可能没经过租户改写。
- `maxLimit` 只限返回行数，不限 `COUNT(*)` 的成本；大表照样慢。
- XML 手写 `LIMIT`：不经过分页插件，`maxLimit` 也管不到。

## 现在的规矩

- 分页统一用 `Page`，列表和 count 共用条件。
- 租户插件必须在分页插件之前。
- 参数校验管下限，服务端 `maxLimit` 管上限。
- 大表先判断要不要精确 total，再谈优化。
- 深分页没有证据不展开。

## 相关实践

- [[租户插件落地]]
- [[软删除]]

## 来源

- `smart-server-wms3/src/main/java/com/track/wms/config/MybatisPlusConfig.java:36-42`
- `smart-server-wms3/src/main/java/com/track/wms/model/req/PageInfo.java:22-30`
- `smart-server-wms3/src/main/java/com/track/wms/dao/impl/UserDaoImpl.java:29-34`
- `smart-server-wms3/src/main/java/com/track/wms/service/impl/SysRoleServiceImpl.java:71-94`（`Page` + 批量预查，避免 N+1）
