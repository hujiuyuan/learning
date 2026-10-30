---
type: 实践
技能点: InstantNyTypeHandler
项目: [smart WMS]
时间: 2026-06
证据: 实战
---

# WMS 时区统一改造

技能点：[[InstantNyTypeHandler]] · 项目：[[smart WMS]] · 2026-06

场景：[[UTC与业务时区]]、[[会话时区无关]]

## 我想干什么

把 WMS 对前端的时间契约统一成 UTC ISO，同时不动数据库里的纽约 `DATETIME`，也不影响仍在写同库的 OMP 老系统。目标是不再出现「同一个接口，有的时间字段偏 4–5 小时，有的格式还不一样」。

## 我干了什么

- 立常量：`STORAGE_ZONE = America/New_York`，所有换算只认它（`TimeConstant.java:15-16`）。
- 立 DB 边界：新写 `InstantNyTypeHandler`，全局注册；`Instant` 进出库都显式做纽约↔UTC（`InstantNyTypeHandler.java:25-49`、`MybatisPlusConfig.java:68-72`）。
- 立 JSON 边界：`MsInstantSerializer` + `JacksonConfig`，`Instant` 出参固定 `yyyy-MM-dd'T'HH:mm:ss.SSS'Z'`（`JacksonConfig.java:29-35`、`MsInstantSerializer.java:20-23`）。
- 改响应外壳：`Result.timestamp` 从 `Long` 改成 `Instant`（`Result.java:44`）。
- 补工具：`DateTimeUtil.now()` 固定纽约，新增 `nyToUtc` / `utcToNy` / `nyDayEnd`（`DateTimeUtil.java:149-233`）。
- 补自动填充与业务时钟：`TimeFillHandler` 按字段类型填 `Instant` 或纽约 `LocalDateTime`（`TimeFillHandler.java:61-76`）；`Clock` Bean 固定纽约（`MybatisPlusConfig.java:58-61`）。
- 补会话时区：连接池初始化执行 `SET time_zone`，生产注入 `America/New_York`，默认 `+00:00` 供测试（`application.yml:41-43`、`docs/生产部署清单.md:133`）。
- 迁移 DTO：`model/resp` 下 70 个文件使用 `Instant`、0 个使用 `LocalDateTime`；`model/req` 24 个文件使用 `Instant`、0 个使用 `LocalDateTime`（grep 2026-10-29）。
- 清残留：主代码 `@JsonFormat` 0 处、`service` 下 `ZoneOffset.UTC` 0 处、`ZoneId.systemDefault()` 0 处（grep 2026-10-29）。
- 补测试：`LoginLogTzItTest.java:97-146` 验 EDT/EST 换算；`SessionTzSafeItTest.java:110-142` 验会话时区不影响 handler 往返。

## 犯了什么错 / 误判

1. **假 UTC**：原代码用 `LocalDateTime.ofInstant(x, ZoneOffset.UTC)` 把纽约墙钟当 UTC，查询稳定偏 4–5 小时（计划文档 `:11,109-110`）。这是「类型对、方向错」的典型。
2. **以为 TypeHandler 就够了**：它只管 Java 绑定的 `Instant`；MySQL 自己生成的 `CURRENT_TIMESTAMP`、`ON UPDATE`、`@TableLogic` 的 `NOW()`（`model/entity/Company.java:135`）完全绕过它。后来又补连接级 `time_zone`（`application.yml:41-43`、`SessionTzSafeItTest.java:38-47`）。
3. **计划文档与代码脱节**：计划首行写「状态：待执行」（`docs/superpowers/plans/2026-06-17-wms-time-utc-unify-plan.md:3`），但核心类文件 mtime 是 2026-06-24，代码已落地。文档状态不能当事实。
4. **计划内部口径也不一致**：§2.1 写「TypeHandler + `serverTimezone=NY` 自动换算」（计划 `:32`），§3.1 又写「不依赖 `serverTimezone`」（计划 `:41-48`）；最终代码选后者。照计划前半段抄会写出两套机制。
5. **「70 个 DTO 全量迁移」这个说法不准确**：70 是 `model/resp` 下使用 `Instant` 的文件数；`model/dto` 仍有 5 个文件用 `LocalDateTime`，`model/entity` 仍有 66 个 `LocalDateTime` 字段（grep 2026-10-29）。不能写「全项目零 LocalDateTime」。

## 怎么解决

- 先止血再改类型：先修「假 UTC」的 4 处查询，再迁 DTO（计划执行顺序 `:146`）。
- 两道闸分开：JSON 边界管出参格式，DB 边界管时区换算，互不依赖。
- 破坏性变更前后端同步发版：出参从纽约朴素时间变成 UTC ISO，值和格式同时变（`docs/2026-06-17-wms-time-utc-affected-apis.md:5,11-13,22-23`）。
- 用测试钉方向：EDT/EST 各一条，避免只测夏天。
- 用 grep 收尾：`@JsonFormat`、`ZoneOffset.UTC` 套裸 `LocalDateTime`、`systemDefault` 三项清零。

## 现在的规矩

- 实体时间字段保持 `LocalDateTime`（纽约墙钟），不跟着迁 `Instant`。
- 对外时间戳一律 `Instant`，纯日期一律 `LocalDate`，时间字段不写 `@JsonFormat`。
- 所有换算显式用 `STORAGE_ZONE`；禁止 `ZoneId.systemDefault()`、无参 `now()`、固定偏移。
- DB 进出 `Instant` 只经 `InstantNyTypeHandler`；MySQL 生成时间靠连接会话时区。
- 新增时间字段/查询必须带 DST 测试；改时间契约必须同步前端。

## 证据

- 计划：`docs/superpowers/plans/2026-06-17-wms-time-utc-unify-plan.md:3,9-13,32,41-51,109-110,146`
- 代码：`TimeConstant.java:15-16`、`InstantNyTypeHandler.java:25-49`、`MybatisPlusConfig.java:58-72`、`JacksonConfig.java:29-35`、`MsInstantSerializer.java:20-23`、`Result.java:44`、`TimeFillHandler.java:61-76`、`DateTimeUtil.java:149-233`、`application.yml:41-43`
- 测试：`LoginLogTzItTest.java:97-146`、`SessionTzSafeItTest.java:38-47,83-84,110-142`
- 联调文档：`docs/2026-06-17-wms-time-utc-affected-apis.md:5,11-13,22-24,130`
- 部署：`docs/生产部署清单.md:133`
- 日期口径：`smart` 目录不是 git 仓库，日期按计划文档和文件 mtime 推断（计划 2026-06-17、核心类 2026-06-24、会话时区测试 2026-07-15），不是提交记录。
