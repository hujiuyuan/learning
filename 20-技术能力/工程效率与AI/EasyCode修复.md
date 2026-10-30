---
type: 实践
技能点: EasyCode与Velocity
项目: [muou]
时间: 2026-09
证据: 实战
---

# EasyCode修复

技能点：[[EasyCode与Velocity]] · 项目：muou · 2026-09

场景：[[模板补丁]]

## 我想干什么

让 muou 的 EasyCode 模板对五个库生成可编译、能跑 CRUD 的代码；只改配置，不改 Java 业务代码（`easycode-sim/report/修复与验证.md:3-4`；`easycode-sim/verify-all.sh:33-37`）。

## 我干了什么

- 备份原始导出：`config/EasyCodeConfig.json.user-orig`，sha1 `fc07238c...`（`easycode-sim/report/修复与验证.md:5`）。
- 搭仿真台：复刻插件拼接、渲染、类型映射、落盘；运行时版本与 muou 的 pom 对齐（`easycode-sim/report/修复与验证.md:113-122`）。
- 写补丁链：fix1…fix7 共 58 处文本改动，后来补 fix8/fix9（`easycode-sim/report/修复与验证.md:27`；`easycode-sim/build-config.sh:13-21`）。
- 修十类问题：初始化宏被注释吃掉、`import byte[]`、非 UUID 主键硬套 UUID、NOT NULL、insert 送 null 挡默认值、复合主键 WHERE 少列、`inet` 写入、`jsonb` 等值过滤、`is_` 前缀撞关键字、主键名口径（`easycode-sim/report/修复与验证.md:40-109`）。
- 加两道守卫：复合主键守卫 + 产物守卫（`easycode-sim/README.md:26-31`）。
- 全链验证：message 225 文件 0 渲染错误、210 Java 全编译、38 项运行期断言；四个库 177 表 / 2518 Java 0 编译错误（`easycode-sim/report/修复与验证.md:16-19`）。
- 修 `tpl/` 手抄漂移：改成从配置导出，`--check` 拦不同步（`easycode-sim/export-tpl.js:1-9`）。

## 犯了什么错 / 误判

- 以为「生成成功 = 模板对」。修之前 225 个文件全部不可用：实体没字段、`where = #{row.${pkField}}`、`return row.get();`（`easycode-sim/report/修复与验证.md:21`）。
- 低估 import 问题：以为只有一两处，实际 762 处废 import（`easycode-sim/report/修复与验证.md:137`）。
- fix7 第一次改错：让开条件漏了 `$hasCompositePk`，把单主键表的 import 也删了，25 个类编译不过（`easycode-sim/report/修复与验证.md:147-148`）。
- 只拿 message 一个库当样本：20 处复合主键只覆盖 2 处（`easycode-sim/verify-all.sh:7-9`）。
- `verify-all.sh` 把 `gen.sh` 接进管道，退出码被 `grep` 盖掉，编译失败还打「全部通过」（`easycode-sim/report/修复与验证.md:149-150`）。

## 怎么解决

- 所有配置改动走补丁，每处断言命中 1 次；补丁链可重放（`easycode-sim/fix5.js:7`；`easycode-sim/build-config.sh:13-21`）。
- 仿真台先保证「桩和真文件逐字一致」，再谈生成结果（`easycode-sim/sync-stub.sh:1-6`）。
- 守卫判据取真实主键（`pg_index`）和配置白名单，不取 SQL 文本或模板注释（`easycode-sim/guard-composite-pk.sh:15`、`:38-42`）。
- 五个库全跑，不只跑 message（`easycode-sim/verify-all.sh:33-37`）。
- 编译/生成/验证三层都硬报错，管道不能再吞退出码（`easycode-sim/verify-all.sh:10`、`:57-62`）。

## 现在的规矩

1. 先跑仿真台，再导入 IDEA；IDEA 导入顺序是先导入后生成，先导出会覆盖配置（`easycode-sim/report/修复与验证.md:154-160`）。
2. 不手改最终配置；改 fix 脚本和补丁片段。
3. 改模板必须重跑两道守卫；改补丁必须重跑全链。
4. 已知坑写进边界，不装作修完。
5. 单库 `--quick` 只用于迭代，交付前跑五库。

## 证据

- `easycode-sim/report/修复与验证.md`：改动范围、十类问题、验证结果、待办
- `easycode-sim/report/配置改动.diff`：逐条配置改动
- `easycode-sim/report/复合主键.md`：复合主键设计与实测
- `easycode-sim/config/EasyCodeConfig.json.user-orig`：改动前备份
- `easycode-sim/guard-composite-pk.sh`、`easycode-sim/guard-generated-code.py`：两道守卫
- `easycode-sim/verify-all.sh`：全链入口
