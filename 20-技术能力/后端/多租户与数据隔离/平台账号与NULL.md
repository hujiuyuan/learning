---
type: 场景
技能点: MySQL租户字段
证据: 实战
---

# 平台账号与 NULL

技能点：[[MySQL租户字段]] · 通用技能：[[多租户与数据隔离]]

**什么时候会遇到**：平台/超管账号的 `tenant_id` 为空，要跨租户看数据；表里又有一批 `tenant_id IS NULL` 的历史行或平台行。严格等值过滤会把它们一起打空。

## 判断顺序

1. **caller 是谁**：平台账号、租户账号、定时任务。平台账号的 `tenantId == null` 是「看全量」还是「只看平台行」，先问清楚。
2. **NULL 行的语义**：平台保留数据、历史未回填、还是「不属于任何租户」。不同语义决定它该不该被租户账号看见。
3. **当前 SQL 会不会被自动注入**：走拦截器时 `tenant_id = ?` 由插件追加；平台账号在 smart 里是整表跳过。
4. **严格等值会不会打空**：表里 NULL 占比高（`goods` 99.98%），`= ?` 会把本该可见的行全滤掉。
5. **跨租户要不要闸**：`TenantIgnore` / `@InterceptorIgnore` 之外，上游有没有归属校验或平台入口审计。

## 手段

- **平台模式整表跳过**：smart 的 `WmsTenantLineHandler` 在 `currentTenantId() == null` 时对所有表返回 `ignoreTable=true`（`WmsTenantLineHandler.java:97-99`）。
- **SQL 里显式分流**：通知查询对租户账号写 `tenant_id = ? OR tenant_id IS NULL`，平台账号只写 `tenant_id IS NULL`（`NotificationMapper.xml:44-47`）。
- **关注入后手写范围**：`goods` 用 `TenantIgnore` 关掉自动条件，再显式放行「本租户 + 未标记」两类行（`GoodsMapper.xml:14-27`）。
- **平台账号查询显式 `IS NULL`**：`pageOperatorUsers` 直接 `WHERE u.tenant_id IS NULL` 并限定平台角色（`UserMapper.xml:50-58`）。
- **fail-closed 哨兵**：muou 在没有租户上下文时注入查不到的 UUID，而不是放行（`MuouTenantLineHandler.java:43,63-66`）；插入不补哨兵，交给非空约束或 RLS 报错（`:74-83`）。

## 反例 / 边界

- **严格 `eq` 打空 NULL 行**：`goods.tenant_id` 99.98% 为 NULL，插件注入 `tenant_id = ?` 会把结果清零（`GoodsMapper.xml:14-27`）。
- **拿全 0 当哨兵**：全 0 是 muou 的平台保留租户，库里真有挂在它名下的行；拿它当「查不到」会让没设租户的请求看见整个平台层（`MuouTenantLineHandler.java:38-43`）。
- **插入补哨兵**：读/改查不到是安全，插入填哨兵会把一行写进谁也看不见的租户，不报错也找不回（`MuouTenantLineHandler.java:74-83`）。
- **平台账号写租户级资源**：`tenant_id IS NULL` 的账号写需要租户的数据会撞非空约束；写侧要有 `requireTenantId()` 之类的守卫（设计，见 [[租户字段与查询过滤]]）。
- **NULL 行对所有租户可见**：`= ? OR IS NULL` 是业务决定，不是通用写法；如果 NULL 表示「平台私有」，租户账号不该看到。

## 现在的规矩

- 平台账号的可见范围在 SQL 或服务层显式写，不靠「没传租户」。
- 表里存在 NULL 租户行时，先定义语义，再决定 `= ?` 还是 `= ? OR IS NULL`。
- 关掉自动注入的查询，必须在同一条 SQL 里把可见范围写回来。
- 写侧不靠哨兵兜底：没有租户就报错或拒绝。

## 相关实践

- [[租户插件落地]]
- [[登录日志租户隔离]]
- [[租户字段与查询过滤]]

## 来源

`smart-server-wms3/src/main/java/com/track/wms/config/WmsTenantLineHandler.java:97-99`
`smart-server-wms3/src/main/resources/mapper/NotificationMapper.xml:44-47`
`smart-server-wms3/src/main/resources/mapper/GoodsMapper.xml:14-27`
`smart-server-wms3/src/main/resources/mapper/UserMapper.xml:50-58`
`muou-backend/muou-common/muou-common-app/src/main/java/com/voidtech/muou/common/persistence/MuouTenantLineHandler.java:38-43,63-66,74-83`
