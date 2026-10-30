---
type: 技能点
域: 后端
项目: [muou]
证据: 实战
---

# EasyCode与Velocity

所属通用技能：[[工程效率与AI]]

**一句话**：EasyCode 的产物由三层共同决定：模板组（17 个 .vm）、全局配置（muouDefine.vm 的宏和变量）、类型映射（muou-pg 38 条）；任何一层错，结果不是编译不过，就是运行期静默错。

## 方法总纲

- **模板组**：`template["muou-ms"]` 现在 17 个模板，覆盖契约、DTO、实体、Mapper、DAO、Service、Controller、转换器；其中 `apiKey.java.vm`、`apiVersioningConfig.java.vm` 是修模板时新增的（`easycode-sim/config/EasyCodeConfig.final.json:570-642`；`easycode-sim/report/修复与验证.md:32`）。
- **全局配置**：`globalConfig["muou-ms"]` 6 个，核心是 `muouDefine.vm`，约 1.4 万字符，负责算 `$pkCols`、`$hasCompositePk`、`$skipTable`、`$castCols`、`$dtoImports`、`$selfIdTables`（`easycode-sim/config/EasyCodeConfig.final.json:687-711`；`easycode-sim/report/复合主键.md:68-70`）。
- **类型映射**：`muou-pg` 38 条，匹配顺序是 ORDINARY 大小写不敏感、REGEX 全匹配、首个命中、未命中落 Object（`easycode-sim/config/EasyCodeConfig.final.json:115`；`easycode-sim/report/修复与验证.md:119-120`）。
- **渲染**：Velocity 2.3，与 IDEA 2026.1 插件运行时同一份；全局配置是纯字符串替换（`easycode-sim/report/修复与验证.md:115-118`）。
- **落盘**：app 模块路径由对话框选，api 模块由 `$modulePath.replace("-app","-api")` 推出（`easycode-sim/README.md:125-127`）。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 修 muou-ms 模板组与 muouDefine，使 5 个库生成可编译 | 实战 | muou | 2026-09 | [[模板补丁]] |
| 搭 easycode-sim 仿真台，复刻拼接/渲染/类型映射/落盘 | 实战 | muou | 2026-09 | [[模板补丁]] |
| 加复合主键守卫与产物守卫 | 实战 | muou | 2026-09 | [[模板补丁]] |
| 复合主键改成 Key 记录 + 走请求体 | 实战 | muou | 2026-09 | [[模板补丁]] |

证据：
- 模板修复范围与结果：`easycode-sim/report/修复与验证.md:3-21`
- 仿真台保真做法：`easycode-sim/report/修复与验证.md:113-125`
- 两道守卫：`easycode-sim/README.md:26-31`
- 复合主键契约：`easycode-sim/report/复合主键.md:8-14`

## 我会的部分

- 读配置结构：`template` / `globalConfig` / `typeMapper` 三块，模板取 `code`，全局取 `value`（`easycode-sim/sync-workspace-config.py:30-37`）。
- 写 Velocity 宏：`muouInit` 里做主键分叉、跳过表、cast 列、per-DTO import（`easycode-sim/report/修复与验证.md:29-36`）。
- 复刻插件行为：全局配置拼接、`ColumnInfoDTO.getJavaType`、`pg_catalog.format_type` 归一化（`easycode-sim/report/修复与验证.md:113-122`）。
- 跑验收：5 库灌库→生成→编译（`easycode-sim/verify-all.sh:33-37`）；message 225 文件 0 渲染错误、38 项运行期断言（`easycode-sim/report/修复与验证.md:16-19`）。
- 写守卫：复合主键按 A/B/C 三类扫产物，判据取 `pg_index`（`easycode-sim/guard-composite-pk.sh:4-13`、`:53-64`）；产物守卫扫四类 javac 不报的错（`easycode-sim/guard-generated-code.py:3-8`）。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| EasyCode + 自定义 Velocity 模板，而不是手写 CRUD | 产物直接符合项目分层/命名/契约；一次改模板，所有表受益 | 模板与 IDE 插件版本耦合；模板错会批量产出错误代码；调试靠仿真台 | 模板维护成本超过手写收益、或插件不兼容 → 换 OpenAPI Generator/自研 CLI |
| 模板组 + 全局宏分离 | 模板管结构，`muouDefine.vm` 管复合主键/类型/导入等公共逻辑，改一处全局生效 | 宏太复杂难读；全局变量污染；改宏影响所有模板 | 宏膨胀到不可维护 → 拆成多个 include/插件 |
| 类型映射表（38 条）而不是代码里判断 | 数据库类型 → Java 类型集中配置，新增类型只改表 | 匹配顺序/大小写/未命中落 Object，错了运行期才炸 | 类型少且稳定 → 代码内映射也可 |
| 生成一次后手改，而不是反复覆盖 | 生成物是起点，业务逻辑要手写；覆盖会丢修改 | 模板升级后无法自动同步；手改与模板分叉 | 生成物需要长期跟随模板 → 生成到独立目录 + 补丁链，不手改 |
| 仿真台 + 产物守卫，而不是只信 IDE | IDE 插件渲染不可编程复现；仿真台能跑模板/类型映射/落盘并做编译校验 | 仿真台本身要维护，可能与插件运行时仍有差异 | 插件提供稳定 CLI/API → 直接集成 |
| 不用低代码平台 | 产物是普通代码，可 review、可调试、可脱离平台；控制权在团队 | 没有可视化编排；重复劳动比低代码多 | 业务人员自助搭建、变化极快 → 评估低代码 |

## 边界

- EasyCode 是 IDEA 插件，配置靠导入生效（`easycode-sim/report/修复与验证.md:154-160`）；没有团队采用记录，不能写成「团队生产工具」。
- 只改 `muou-ms` 模板组和 `muouDefine`，没碰其他模板组，也没碰 Java 业务代码（`easycode-sim/report/修复与验证.md:3-4`）。
- 只做 PostgreSQL（muou-pg）；没做 MySQL 类型映射。
- 模板仍留 3 个已知坑：敏感列进 Resp/SaveReq、`is_` 前缀在契约层被去掉、`inet` 列不进等值查询（`easycode-sim/report/修复与验证.md:138-140`）。
- 复合主键的 `create` 仍只返回第一主键列（`easycode-sim/report/复合主键.md:87-89`）；分区子表的处理未做。
- 没有生成器级单测；仿真台是复刻，不是插件本体，IDEA 里仍可能不同。

## 相关技能

[[Claude Code与Agent]]、[[CI-CD与部署]]、[[数据访问与ORM]]

## 用在哪些工程能力

模板生成、代码生成验收、CI 门禁、数据访问层生成。
