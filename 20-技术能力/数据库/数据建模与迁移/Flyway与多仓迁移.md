---
type: 技能点
域: 后端
项目: [muou]
证据: 实战/设计
---

# Flyway 与多仓迁移

所属通用技能：[[数据建模与迁移]]

**一句话**：一个库被多个仓库写时，版本号用时间戳、脚本用 `collect.sh` 收集整合；Flyway 只在开发/测试记账，生产执行人审过的纯 SQL。

## 方法总纲

1. **一个库一条版本序列**，但序列由多个仓库共同追加；版本号必须跨仓库不撞。
2. **时间戳版本号**：`V<yyyyMMddHHmm>__<说明>.sql`，排序即时间顺序。
3. **收集整合**：`collect.sh` 把各仓脚本按版本排序、校验、拼成 `build/<库>.sql` + `.manifest`。
4. **两种消费方式**：`build/<库>.sql` 给人执行；`--stage` 出 `build/stage/<库>/` 给 Flyway 当 locations。
5. **环境分工**：Flyway 只用于开发/测试；生产执行整合产物，谁跑、何时跑由人决定。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 时间戳版本号 + 跨仓撞号检查 | 实战 | muou | 2026-09 | [[多仓迁移落地]] |
| `collect.sh` 收集/排序/校验/拼接 | 实战 | muou | 2026-09~10 | [[多仓迁移落地]] |
| CI 静态校验 + 收集校验 + 手动迁移 job | 实战 | muou | 2026-10 | [[破坏性变更]] |

## 选型与取舍

### Flyway / Liquibase / golang-migrate

项目里三种迁移工具都出现过，不是统一选型：

| 工具 | 用法 | 优点 | 代价 | 项目证据 |
| --- | --- | --- | --- | --- |
| Flyway | 纯 SQL + `flyway_schema_history` 记账 | SQL 透明、版本顺序直观、CI 好接 | 没有 changelog 抽象/回滚/context；多仓收集要自己写 | muou ops CI、xxl-job `pom.xml:62-78` |
| [[Liquibase]] | changelog + changeset + rollback | 有回滚、context、跨库抽象；适合需要审计/回滚的库 | 文件多、抽象重、SQL 被拆成 changeset | smart wms3：59 个 changelog、`db/rollback/`、`pom.xml:283-287` |
| golang-migrate | `*.up.sql` / `*.down.sql` | Go 工具链、up/down 成对 | 没有多仓收集/Java CI 集成；本人无提交 | muou-dashboard `server/go.mod:8`、`server/migrations/` |

muou 选 Flyway 的直接原因在代码里能确认：ops 仓已经有 Flyway 的 `--stage` 产物和 CI job（`.gitlab-ci.yml:63-86`、`ci/migrate.sh`），迁移脚本本身就是纯 SQL。设计文档没有写完整的工具对比，所以「为什么不是 Liquibase」只能标推断：SQL-first、已有 CI、PostgreSQL 单库，Liquibase 的 changelog/rollback 能力在这个场景没有被需要。反过来说，wms3 需要 `db/rollback/` 和 59 个 changelog 的可回滚结构，所以它用 Liquibase；这不是谁更先进，是约束不同。

### 为什么版本号用时间戳，不用 V1/V2

- 一个 core 库由 7 个仓库共同追加脚本；各仓各自排 V23/V24 必然撞号，而且撞车要到整合时才暴露（`muou-backend/muou-app-ops/databases/迁移编写约定.md:49-52`）。
- 时间戳 `V<yyyyMMddHHmm>__说明.sql` 让「写完脚本的时刻」就是顺序，跨仓不需要中心协调；`collect.sh` 再按版本排序并检查重复（`collect.sh:142`、`:161-173`）。
- 代价是时钟：机器时间不准会让顺序错；所以版本号取「写完脚本那一刻」，不取 commit 时间，整合时仍要做撞号检查。项目实测 7 个服务/公共仓 446 份迁移全部是 12 位时间戳（`迁移编写约定.md:119-122`）。

### 为什么用 collect.sh + build.sql，不让各服务自己跑 Flyway

- 服务仓没有配置 Flyway（`迁移编写约定.md:30-31`）；数据库由 ops 仓统一管，生产执行人审过的 `build/<库>.sql`，Flyway 只在开发/测试用（`迁移编写约定.md:4`、`:87-88`）。
- 这样做的代价：多一个收集步骤，产物可能过期；所以 CI 加 `validate:collected`，浅克隆 7 个仓跑 `collect.sh`，再 `git diff` 查 `build/` 是否过期（`.gitlab-ci.yml:47-59`、`ci/validate-collected.sh`）。
- 另一个代价：生产不自动记账，靠人执行；换来的是事务边界、执行窗口、回滚预案由人决定，而不是迁移工具在发布时自动跑。拼出来的 SQL 不含事务控制语句，分几个事务由执行方决定（`迁移编写约定.md:82`、`collect.sh:186`）。

### 什么条件下会反悔

- 服务仓需要自助迁移、不想经过 ops 收集 → 改成中央迁移服务/每仓 Flyway，但要先解决多仓版本协调和凭证隔离。
- 需要自动回滚/多数据库抽象 → 评估 Liquibase；代价是 changelog 维护和 SQL 透明性下降。
- 生产需要自动执行 → Flyway 可以接，但必须加审批、备份、失败中止和回滚预案；当前的人审流程不能直接删。

## 我会的部分

### 时间戳版本号

- 文件名一律 `V<yyyyMMddHHmm>__<说明>.sql`，取写完脚本那一刻的时间（`muou-backend/muou-app-ops/databases/迁移编写约定.md:41-47`）。
- 不能接着排 V23 / V24：core 由四个独立仓库共写，各排各的必然撞号，撞车要到整合时才暴露（`迁移编写约定.md:49-52`）。
- 实测：7 个服务/公共仓的 446 份迁移全部是 12 位时间戳；ops 基线里那批 V1–V22 单体脚本已退役到 `migration/_retired-2026-09-11/`，不再参与整合（`迁移编写约定.md:119-122`，目录实测）。

### collect.sh

- 来源三类：本仓基线、各服务仓 `app 模块/db/migration/<库>/`、公共库 `_all/`（`collect.sh:60-95`）。
- 排序 `sort -k1,1n -k2,2`；同一库同一版本号撞了直接失败，把两个文件都打出来（`collect.sh:142`、`:161-173`）。
- 文件名不合规、脚本写在仓库根下（旧形状）都收不下，整次整合失败，不许静默跳过（`collect.sh:70-88`、`:149-159`）。
- 产出 `build/<库>.sql` 与 `.manifest`；头部不写墙钟时间，保证产物可逐字比对（`collect.sh:178-188`）。
- 公共表 `_all/` 展开到 core / billing / message，日志库不展开（`collect.sh:90-95`）。

### CI 里的三件事

- `validate`：静态检查本仓迁移的版本号重复、`DROP COLUMN`、列注释（`.gitlab-ci.yml:36-43`）。
- `validate:collected`：浅克隆 7 个仓、跑 `collect.sh`，再 `git diff` 查 `build/` 是否过期（`.gitlab-ci.yml:47-59`、`ci/validate-collected.sh`）。
- `migrate:<库>:dev`：手动任务（test 分支自动），用 `--stage` 产物跑 Flyway，跑完补授权（`.gitlab-ci.yml:63-86`、`ci/migrate.sh`）。

### 生产不跑 Flyway

- 生产执行 `build/<库>.sql`，由人触发；Flyway 只用于开发与测试（`迁移编写约定.md:4`、`:87-88`）。
- 拼出来的 SQL 不含事务控制语句，分几个事务由执行方决定（`迁移编写约定.md:82`、`collect.sh:186`）。

## 边界

- 没有生产执行经验；只做到「整合产物 + 人审」的流程。
- `_all/` 目录当前只有 `.gitkeep`，公共表展开机制没有实际脚本可验证。
- 服务仓没有配置 Flyway（`迁移编写约定.md:30-31`），Flyway 只出现在 ops 仓的 CI。
- MySQL 侧没做过 Flyway；smart wms3 用 Liquibase（59 个 changelog、db/rollback、`switch.sh:126,144,200` 一次性迁移容器），见 Liquibase（待建）。Flyway 落地在 PostgreSQL（xxl-job `pom.xml:62-78`、`db/migration/`）。

## 相关技能

[[数据建模与迁移]]、[[数据建模]]、[[多仓迁移落地]]、[[破坏性变更]]、[[查询性能优化]]

## 用在哪些工程能力

数据库迁移与兼容（待建）。
