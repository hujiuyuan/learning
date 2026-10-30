---
type: 技能点
域: 数据库
项目: [smart WMS]
证据: 实战
---

# Liquibase

所属通用技能：[[数据建模与迁移]]

**一句话**：Liquibase 用 changelog + changeset 记录数据库版本，wms3 有 59 个 changelog 文件、50 份 rollback SQL；真正学到的不是 YAML 怎么写，而是「迁移不能跟应用启动绑死」——`DATABASECHANGELOGLOCK` 没有 TTL，持锁副本被杀一次，所有副本都会卡在等锁。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/smart/smart-server-wms3/`。

## 方法总纲

1. **一个 master 串所有 changeset**：`db.changelog-master.yaml` 按序号 include；新变更只追加文件，不改历史 changeset。
2. **changeset 要有 id/author/comment**：id 唯一，author 记录责任人，comment 写「为什么改」，不是「改了什么」。
3. **能回滚的写 rollback**：DDL 写反向 SQL；数据回填写独立 rollback 文件，和 forward SQL 分开。
4. **重复执行要幂等**：`preConditions: onFail: MARK_RAN` 用于「列/索引可能已存在」；`preConditions` 不参与 checksum，已跑过的环境不受影响。
5. **不可逆操作不要用 context 挡**：不指定 contexts 运行时，带 context 的 changeset 照样执行；失败方向是「开」，所以危险 changeset 直接注释掉 include，而不是加 context。
6. **生产迁移与启动分离**：部署流程先跑一次性迁移容器，应用容器 `LIQUIBASE_ENABLED=false`；迁移失败中止部署。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 59 个 changelog 的 master 编排 | 实战 | [[smart WMS]] | 2026-05~10 | [[多仓迁移落地]] |
| 50 份 rollback SQL + 回填/索引回滚 | 实战 | [[smart WMS]] | 2026-05~10 | [[破坏性变更]] |
| 迁移移出应用启动、部署期一次性容器 | 实战 | [[smart WMS]] | 2026-07 | [[CI-CD与部署]] |
| 锁残留事故的规避与开关 | 实战 | [[smart WMS]] | 2026-07 | — |

## 我会的部分

### changelog 编排

- master 文件按序号 `include`：`001-init.yaml` → `061-merge-file-ship-from.yaml`，每个文件一个主题（`db/changelog/db.changelog-master.yaml:1-178`）。
- 新变更只追加，不改旧 changeset；旧 changeset 的 checksum 变了，Liquibase 会在启动时直接报错，所有环境都过不去。
- 一个 changeset 可以走 `sqlFile`（外部 SQL）或内联 `sql`；项目两种都有，DDL 多的用 `sqlFile`，单条索引用内联（`029-omp-common-getlist-index.yaml`、`030-goods-created-at-index.yaml`）。

### 幂等与前置条件

- `preConditions: onFail: MARK_RAN` + `not: columnExists/indexExists`：全新库如果已把列并进 init 脚本，这里再 ADD 会 1060 Duplicate column；列不存在时照常执行（`059-user-notify-enabled.yaml:5-13`、`060-merge-tmpl-path.yaml:7-10`）。
- `preConditions` 不参与 checksum：已跑过的环境不会因为加了前置条件就重新执行（`059-user-notify-enabled.yaml:6-8`）。
- 这不是「所有变更都加 MARK_RAN」：只有「可能已存在」的加；真正要失败的变更（删列、改类型）不加，让它在不满足条件时中止。

### 回滚

- 50 份 `db/rollback/*.sql`，按 changeset 编号命名；`010/016/019/020/023/027/059/060` 等 changeset 的 `rollback` 指向对应文件（`db/rollback/`、`db/changelog/010-preload-forklift-name.yaml:12-14`）。
- 回滚不是「自动安全」：数据回填的回滚只能恢复结构，删掉的数据回不来；所以危险变更先备份/快照，再执行。
- `021-goods-multi-valued-index.yaml:14` 里还有 changeset 级 `rollback`，说明回滚可以内联也可以外置；项目偏外置，因为 SQL 长、要 review。

### 危险变更：注释掉 include，不用 context

- `050-clean-bonded-shells.yaml` 会软删 372 行 BONDED 存量占位壳；master 里这段 include 是**注释掉的**，并写明「刻意未启用，勿随手打开」（`db.changelog-master.yaml:140-154`）。
- 注释写清了原因：Liquibase 在应用启动时自动执行，一旦 include 就会在任何被部署到的环境立即清库；而这次改造要求清壳排在后端上线、前端切 commonId、灰度验证之后。注释 = 失败安全（忘了打开只是没清，不会误删）。
- 还写了一个关键坑：「Liquibase 的 context 属性挡不住这个场景——不指定 contexts 运行时，带 context 的 changeset 照样执行，失败方向是开，不适合用于不可逆的删数据操作」（`db.changelog-master.yaml:145-146`）。
- 这条比任何 YAML 语法都重要：**不可逆变更的默认状态必须是「不执行」**，不能依赖运行时参数。

### 生产：迁移容器 + 应用开关

- `application.yml` 的 `spring.liquibase.enabled: ${LIQUIBASE_ENABLED:true}`，默认 true 是 fail-safe：本地/测试靠自动建表，忘了设变量也不会静默不建表（`src/main/resources/application.yml:71-77`）。
- 注释写明事故模式：`DATABASECHANGELOGLOCK` 无 TTL 无心跳，持锁副本被杀后锁永久残留，之后所有副本启动无限等锁、全线起不来；所以迁移改由部署流程单独跑一次性容器。
- `switch.sh` 先跑迁移容器：`LIQUIBASE_ENABLED=true`、`SPRING_MAIN_WEB_APPLICATION_TYPE=none`、`WMS_SCHEDULING_ENABLED=false`，失败直接 `exit 1` 中止部署（`scripts/deploy/switch.sh:118-132`）。
- 应用容器启动时 `LIQUIBASE_ENABLED=false`，不再碰迁移锁（`scripts/deploy/switch.sh:140-148`、`:196-204`）。
- 蓝绿部署由 `scripts/deploy/switch.sh` 串起来：迁移 → staging → 健康检查 → 切流量（`.gitlab-ci.yml:150-160`）。

## 选型与取舍

### 为什么 wms3 用 Liquibase，不用 Flyway

| 方案 | 优点 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| Liquibase | changelog 抽象、changeset 级 rollback、preConditions、跨库 SQL 生成 | 文件多、YAML 抽象重、锁/context 行为要学 | wms3：59 个 changelog、50 份 rollback |
| Flyway | 纯 SQL、版本表直观、CI 好接 | 回滚/前置条件/跨库抽象弱；多仓收集要自己写 | muou/xxl-job 的 PostgreSQL |
| golang-migrate | up/down 成对、Go 工具链 | 无 Java/多仓集成，本人无提交 | muou-dashboard |

wms3 选 Liquibase 的直接约束是 MySQL + 需要 changeset 级回滚：50 份 rollback、`preConditions` 处理「列可能已存在」、`sqlFile` 把长 SQL 外置。Flyway 也能做 MySQL，但回滚要自己写 undo 脚本/付费版，项目已经有 Liquibase 的 rollback 目录，换 Flyway 等于重做一遍。代价是 YAML 文件多、抽象重、锁事故需要单独处理；这不是「Liquibase 更先进」，是 wms3 的迁移形态（大量 DDL + 回填 + 回滚）更贴合 changeset。

### 为什么把迁移移出应用启动

- 应用启动时跑 Liquibase，多个副本会同时抢 `DATABASECHANGELOGLOCK`；锁没有 TTL/心跳，持锁副本被 kill 后锁永久残留，其他副本无限等锁，表现为「服务起不来但日志没有明确错误」。
- 改成部署流程的一次性容器：迁移只跑一次，失败中止部署；应用容器 `LIQUIBASE_ENABLED=false`，启动不碰锁。代价是多一个部署步骤、迁移容器要能连库/拿配置；换来的是启动路径可预测。
- 这是「把一次性动作从长期进程里拿出来」的典型：迁移是部署阶段的事，不是每次启动的事。

### 为什么危险变更注释 include，不用 context

- context 的默认行为是「不指定 contexts 时照样执行」，失败方向是「开」；对删数据这种不可逆操作，默认必须是「关」。
- 注释 include 让「忘记打开」只导致没执行，不会导致误删；打开前要满足前端切换、预览 SQL、负责人确认三个前置条件（`db.changelog-master.yaml:148-153`）。
- 代价：需要人工记得打开/关闭；项目用注释 + 前置条件清单 + rollback 文件兜底，而不是靠工具开关。

### 什么条件下会反悔

- 多仓/多服务共写一个库 → Liquibase 的单 master 不适合，需要像 muou 那样做收集/整合，或换 Flyway + 时间戳版本。
- changeset 文件继续膨胀、review 成本过高 → 按领域拆 master/模块，或评估 Flyway 的纯 SQL；不要直接删历史 changeset。
- 锁事故再次发生 → 先确认迁移容器唯一性/超时/清理锁的 runbook；不要靠加 `context` 或重试掩盖。

## 边界

- 没有生产手工回滚演练；50 份 rollback 只做到「脚本存在」，没在生产验证过每一份。
- 没有用 Liquibase 的 `context`/`labels` 做多环境差异化；项目明确认为 context 不适合危险变更。
- 没有做过 Liquibase 多 master/多租户 schema 的拆分。
- 锁残留的恢复动作（清 `DATABASECHANGELOGLOCK`）只读代码/注释，没实际处理过生产锁。
- 没有评估 Liquibase 商业版/Pro 的能力；只用开源核心。

## 相关技能

- [[Flyway与多仓迁移]]、[[数据建模与迁移]]、[[破坏性变更]]、[[多仓迁移落地]]
- [[Spring Boot]]（`LIQUIBASE_ENABLED` 开关）、[[CI-CD与部署]]（迁移容器）

## 用在哪些工程能力

- 数据库迁移与兼容
- 部署流程与失败中止
- 破坏性变更的回滚/前置条件设计
