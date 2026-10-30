---
type: 场景
技能点: InstantNyTypeHandler
方法: 三层时间模型
证据: 实战
---

# UTC 与业务时区

技能点：[[InstantNyTypeHandler]] · 方法：三层时间模型（待建） · 通用技能：[[时区与时间序列化]]

**什么时候会遇到**：查询区间跨夏令时；同一个「业务日」在不同季节对应不同 UTC；纯日期（出库日、预约日）被当成时刻传；前端只肯发 UTC ISO；MySQL 默认值或软删时间跟会话时区走；看板要算「纽约的今天」。

## 判断顺序

1. **先判字段语义**：这是时间轴上的时刻，还是一个业务日/纯时间？时刻用 `Instant`，日期用 `LocalDate`，时刻的部分用 `LocalTime`。
2. **再看列类型**：`DATETIME` 是裸墙钟，必须知道基准；`DATE` 按业务日，不换算；`TIMESTAMP` 由数据库按会话时区换算，是另一套。
3. **确认库内基准**：smart WMS 是纽约（`TimeConstant.java:15-16`），OMP 还在写同库，不能单方面改 UTC。
4. **确认方向**：入口 UTC→纽约墙钟（TypeHandler 绑定），出口纽约墙钟→UTC（`DateTimeUtil.nyToUtc`，`DateTimeUtil.java:177-183`）。
5. **找 MySQL 生成值**：`CURRENT_TIMESTAMP`、`ON UPDATE`、`@TableLogic` 的 `delval = NOW()` 不经过 TypeHandler，看连接会话时区。
6. **最后验 DST**：同一纽约墙钟在冬夏对应两个 UTC，测试要各来一次。

## 手段

- 常量：`STORAGE_ZONE = America/New_York`（`TimeConstant.java:16`）。
- DB 边界：`InstantNyTypeHandler` 全局注册（`MybatisPlusConfig.java:68-72`）。
- 业务日：注入 `Clock.system(STORAGE_ZONE)`（`MybatisPlusConfig.java:58-61`），`DashboardServiceImpl.java:44,119` 用它算今天/昨天。
- 日期入参：`NyLocalDateDeser` 同时接受 `yyyy-MM-dd` 和 UTC ISO，后者转纽约业务日（`NyLocalDateDeser.java:33-36`）。
- 工具：`DateTimeUtil.now()` 固定纽约（`:149-151`）、`nyToUtc`（`:177-183`）、`utcToNy`（`:229-233`）、`nyDayEnd`（`:216-221`）。
- 测试：`LoginLogTzItTest.java:97-146` 用 EDT/EST 两行证明换算方向。

## 反例 / 边界

- **假 UTC**：`LocalDateTime.ofInstant(x, ZoneOffset.UTC)` 把纽约墙钟当 UTC，稳定偏 4–5 小时；计划文档把它列为原有 bug（`docs/superpowers/plans/2026-06-17-wms-time-utc-unify-plan.md:11,109-110`）。
- **`ZoneId.systemDefault()`**：开发机 CST、容器 UTC，结果随部署环境变。改造后的硬规则是主代码 0 处（grep 2026-10-29）。
- **固定偏移**：写死 `-04:00` 到冬天就错一小时，必须用 `ZoneId`。
- **纯日期转 `Instant`**：把 `2026-07-15` 当 `00:00Z` 会导致纽约业务日落到前一天；日期就按 `LocalDate` 绑 `DATE` 列。
- **秋季重复小时**：纽约回拨当天 01:00–02:00 出现两次，`atZone` 默认取较早偏移；订单算哪一次没有业务规则。
- 只覆盖纽约单时区；多时区用户各自业务日没有做过。

## 现在的规矩

- 实体时间字段保持 `LocalDateTime`（纽约墙钟），不改成 `Instant`。
- 对外时间戳用 `Instant`，纯日期用 `LocalDate`，时间字段不写 `@JsonFormat`。
- 所有 NY↔UTC 换算显式用 `STORAGE_ZONE`；禁止 `ZoneId.systemDefault()`、无参 `now()`、固定偏移。
- DB 进出 `Instant` 只走 `InstantNyTypeHandler`；MySQL 生成值靠连接级 `time_zone` 兜底。
- 新增时间字段或查询必须带 DST 用例（EDT + EST 各一次）。

## 相关实践

[[WMS时区统一改造]]、[[InstantNyTypeHandler]]、[[会话时区无关]]

## 来源

- `smart-server-wms3/src/main/java/com/track/wms/common/constant/TimeConstant.java:15-16`
- `smart-server-wms3/src/main/java/com/track/wms/config/MybatisPlusConfig.java:53-72`
- `smart-server-wms3/src/main/java/com/track/wms/common/util/DateTimeUtil.java:149-233`
- `smart-server-wms3/src/main/java/com/track/wms/common/serializer/NyLocalDateDeser.java:23-37`
- `smart-server-wms3/src/test/java/com/track/wms/dao/mapper/LoginLogTzItTest.java:97-146`
- `docs/superpowers/plans/2026-06-17-wms-time-utc-unify-plan.md:11,109-110`
