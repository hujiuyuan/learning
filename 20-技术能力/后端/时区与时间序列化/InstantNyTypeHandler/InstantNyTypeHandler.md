---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战
---

# InstantNyTypeHandler

所属通用技能：[[时区与时间序列化]]

**一句话**：一个全局 MyBatis TypeHandler，把 Java 的 UTC `Instant` 与库里的纽约墙钟 `DATETIME` 在绑定/读取两个点显式互转，不让 JDBC 或 JVM 时区插手。

## 方法总纲

1. **只认 `Instant`**：继承 `BaseTypeHandler<Instant>`，`@MappedTypes(Instant.class)`（`InstantNyTypeHandler.java:21-22`）。别的类型不经过它。
2. **写库显式转墙钟**：`parameter.atZone(STORAGE_ZONE).toLocalDateTime()`，再用 `ps.setObject` 传 `LocalDateTime`（`:25-29`）。驱动把字面量原样写进 `DATETIME`，不做二次转换。
3. **读库显式还原时刻**：`rs.getObject(col, LocalDateTime.class)` 拿到纽约墙钟，再 `atZone(STORAGE_ZONE).toInstant()`（`:31-49`）。三个重载都走同一个 `toInstant`。
4. **全局注册**：`ConfigurationCustomizer` 把 `Instant.class` 注册到 `TypeHandlerRegistry`（`MybatisPlusConfig.java:68-72`）。mapper XML 的 `#{}`、Lambda wrapper 参数、列→实体映射自动生效，业务代码零改动。
5. **不依赖 JDBC `serverTimezone` / JVM 时区**：`DATETIME` 本身不带时区，JDBC 的 `serverTimezone` 只在驱动做 `TIMESTAMP`/字符串转换时介入；这里绑定的是 `LocalDateTime` 字面量，换算全在 handler 里（`InstantNyTypeHandler.java:16-20`）。
6. **配套两个时间源**：
   - `Clock` Bean 固定纽约（`MybatisPlusConfig.java:53-61`），业务日「今天」用它算。
   - `TimeFillHandler` 自动填审计时间：字段是 `Instant` 就填 `Instant.now()`，是 `LocalDateTime` 就填 `LocalDateTime.now(STORAGE_ZONE)`，落库都是纽约（`TimeFillHandler.java:61-76`）。

## 我用它干过什么

时间说明：`smart` 目录不是 git 仓库，2026-06/2026-07 按计划文档和文件 mtime 推断，不是提交记录。

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 登录日志按 UTC 区间查纽约 `DATETIME` | 实战/测试 | [[smart WMS]] | 2026-07 | [[UTC与业务时区]] |
| 验证会话时区变化不影响 handler 往返 | 实战/测试 | [[smart WMS]] | 2026-07 | [[会话时区无关]] |
| 全套时间契约改 UTC | 实战 | [[smart WMS]] | 2026-06 | [[WMS时区统一改造]] |

## 我会的部分

- 写：`Instant → atZone(STORAGE_ZONE) → LocalDateTime → ps.setObject`。
- 读：`ResultSet.getObject(col, LocalDateTime.class) → atZone(STORAGE_ZONE) → Instant`；`null` 原样返回。
- `CallableStatement` 重载也覆盖，三处读取不会漏。
- 用 `ZoneId.of("America/New_York")`，夏令时自动判 EDT-4 / EST-5，不写固定偏移。
- 判断什么时候它不管：`LocalDateTime` 参数和字段绕过它，MySQL 的 `DEFAULT CURRENT_TIMESTAMP` / `ON UPDATE` / `NOW()` 也绕过它。
- 用测试钉住：`LoginLogTzItTest.java:97-146` 用同一纽约 10:00 的 EDT/EST 两行，验证 UTC 区间换算；`SessionTzSafeItTest.java:110-125` 验证会话时区改成 `-09:00` 后往返仍是纽约。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| 全局 TypeHandler 显式互转，而不是靠 JDBC `serverTimezone` | 转换点唯一、可读可测；不依赖驱动/JVM/会话时区 | 全局注册影响所有 `Instant` 字段；漏注册/重复注册会双重转换 | 全库改用 `timestamptz` → 可去掉 handler，交给数据库 |
| 存纽约墙钟 `DATETIME`，而不是 UTC/epoch | 兼容 Legacy 数据和既有查询口径；业务日/报表按纽约自然日 | 不能直接跨时区比较；换时区要迁移；DST 边界要测 | 多时区租户/全球业务 → 存 UTC `timestamptz` + 展示层转换 |
| 应用侧 `Clock` 固定纽约，而不是 `LocalDateTime.now()` | 「今天」由业务时区决定，不随容器/JVM 时区漂移 | 所有取当前时间的地方都要用同一个 Clock；漏用会混 | 多时区业务 → 按租户/门店取 ZoneId |
| `TimeFillHandler` 应用侧填充，而不是数据库默认值 | 审计时间与业务时区一致；Java 侧可控、可测 | 绕过 MyBatis 的写入（裸 SQL/批量）不会自动填 | 无法保证所有写入走 MyBatis → 数据库默认值 + 触发器兜底 |
| `LocalDateTime` 绑定，而不是 `Timestamp` | 避免驱动按会话时区再转一次；字面量原样入库 | 读写的类型必须成对，混用会平移 | 驱动/数据库升级改变类型映射 → 回归测试必须覆盖 |

## 边界

- 只对 `Instant` 生效。实体里仍有 66 个 `LocalDateTime` 字段（grep 2026-10-29），它们依赖「库内就是纽约墙钟」这个约定，handler 不做任何保护。
- 只覆盖 MyBatis 路径。裸 JDBC、拼字符串 SQL、其他 ORM 都不经过它。
- `LocalDate` 不经过它，按纯日期逐字读写；日期边界由 `NyLocalDateDeser` 和业务代码处理。
- 只服务纽约一个时区，多时区租户要另做。
- 不处理 DST 秋季重复小时的歧义，`atZone` 用 JDK 默认规则。

## 相关技能

[[MyBatis-Plus]]、[[数据访问与ORM]]、[[MySQL]]

## 用在哪些工程能力

数据库迁移与兼容、接口契约与前后端联调（均未建卡，无页面）
