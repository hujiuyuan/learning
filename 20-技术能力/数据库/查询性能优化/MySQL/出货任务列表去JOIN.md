---
type: 实践
技能点: MySQL
项目: smart WMS
时间: 2026-06-02
证据: 设计/方案
---

# 出货任务列表去 JOIN

技能点：[[MySQL]] · 项目：[[smart WMS]] · 2026-06-02 · 通用技能：[[查询性能优化]]
场景：[[字段调整与冗余]]

## 我想干什么

出货任务列表原来要 `LEFT JOIN car/common` 再解析 `data` JSON，查询复杂、慢；要支持 5 个时间字段范围查询和多字段排序。

## 我做了什么

- 调研现有列表查询，写了一份实现计划。
- 把列表展示字段 `plan_no / bol / isa_pro / delivery_eta / loading_instruction` 冗余成 `shipping_task` 物理列。
- 新增 `load_at`（开装时间，状态 21→22 时盖）。
- OMP 创建/编辑来源单时 `refreshRedundant()` 刷新冗余列；WMS 列表去 JOIN、直读 `st` 列。
- 默认 `id DESC`；`sortField ∈ {id, code, deliveryEta, outboundDate, createdAt}`。
- 5 个时间字段各支持 start/end；DATETIME 的 end 只传日期时由前端补 `23:59:59`。
- 详情仍查来源单；列表不查。

## 方案里推翻 / 修正过什么

1. 一开始决定 `ACCT STATUS` 不冗余（只在详情用），后来列表要展示/筛选计划状态，推翻决定，改成冗余 + `PlanAggService` 双写。**列表字段的范围要一开始就按「列表要展示/筛选什么」定，不要按「详情用不用」定。**
2. `Car.php::save()` 编辑分支会回填 `goods_id`，然后再次 `create()`，导致重复生成 shipping_task。改成「该 source 下没有 shipping_task 才 create，否则 refreshRedundant」。
3. 冗余列不是加完就完：创建和编辑两个口子都要刷新。OMP 的 Car/Common 编辑要挂 `refreshRedundant`；WMS 侧核实没有写回，才不用挂钩子。
4. 曾计划给 `work_task` 加列同步开装时间；后来确认「领取=开装」，`work_task.claimed_at` 就是同口径，方案取消。

## 现在的规矩

- 列表字段全部冗余成物理列；列表查询不 JOIN、不解析 JSON。
- 冗余列必须有明确的刷新口子：创建 + 编辑。
- 详情才查来源单；列表不查。
- 幂等：生成前先查是否已存在。

## 证据

`smart/docs/superpowers/plans/2026-06-02-shipping-denormalize-query.md`

> 说明：计划里 57 个步骤未勾选，是否已落地待确认；这里记的是方案和决策，不当作已完成。
