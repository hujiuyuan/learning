---
type: 技能点
域: 后端
项目: [muou, xxl-job]
证据: 实战/设计
---

# XXL-Job

所属通用技能：[[中间件与异步任务]]

**一句话**：调度中心管 cron、路由和日志，执行器只管接收并执行 `@XxlJob`；本项目做的是执行器接入和调度中心 PostgreSQL 适配，没有改调度算法。

## 方法总纲

- **角色分工**：`xxl-job-admin` 是独立 Web 应用，任务定义、cron、调度日志都在它自己的库；执行器启动时注册地址、接收调度、回传执行日志，不连调度中心的库（`XxlJobConfig.java:11-17`）。
- **执行器装配**：`XxlJobSpringExecutor` + 一组 `@Value` 透传；`enabled` 默认关，fail-closed（`XxlJobConfig.java:52-53`、`:79-96`）。
- **分片**：调度中心下发 `(分片序号, 分片总数)`，执行器用 `XxlJobHelper.getShardIndex/Total` 自己切数据；框架不管怎么切（`ExecutorProbeJob.java:19-22`、`:34-35`）。
- **日志**：`XxlJobHelper.log` 回传调度中心；slf4j 只留本机（`ExecutorProbeJob.java:45-49`）。
- **PG 适配**：上游 3.4.2 只支持 MySQL；这个 fork 改 7 类 157 处方言，核心调度锁 `SELECT ... FOR UPDATE` 不用改（`deploy/README.md:9-19`、`:32`）。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 执行器接入 + 4 个 handler | 实战 | muou | 2026-08 | [[定时任务多副本锁]] |
| 调度中心 PostgreSQL 适配 | 实战 | xxl-job 3.4.2 | 2026-08 | 调度中心选型（待建） |
| 执行器开关默认关 | 实战 | muou | 2026-08 | 配置安全（待建） |

## 选型与取舍

### 为什么用 XXL-Job，不用 Spring `@Scheduled` / Quartz

- `@Scheduled` 只在单进程内有效，多副本会重复执行；Quartz 能持久化/集群，但没有现成的调度中心 UI、执行日志、分片和失败重试。XXL-Job 把这些做成独立 admin + 执行器，业务只写 handler。
- 代价：多一个 admin 服务和一套库；执行器要注册、配地址/token；调度中心单实例挂了任务不触发。项目接受这个运维成本，换集中管理和可观测性。
- 如果只有单实例、几个简单定时任务，`@Scheduled` 更轻；项目有 outbox 投递、权限巡检等多任务、多副本需求，XXL-Job 更合适。

### 为什么 fork 做 PostgreSQL 适配，不换调度器

- 上游 3.4.2 只支持 MySQL；项目数据库是 PostgreSQL。改 7 类 157 处方言（反引号、`LIMIT`、`IFNULL`、`DATE_FORMAT`、`DATE_ADD`、`ON DUPLICATE KEY`、`WHERE !(...)`）比换一套调度器/重写任务管理成本低，且核心调度锁 `SELECT ... FOR UPDATE` 不用改。
- 代价：fork 要跟上游升级，改动面大、回归成本高；`MAINTAINING.md` 写了流程但没实际演练过。这不是「改完就完了」，是一个长期维护分支。
- 如果上游以后支持 PG，应优先回退 fork；如果改动继续扩大，评估换 Quartz/自研调度。

### 为什么执行器默认关

- `enabled` 默认 false，环境没部署调度中心时不会悄悄接活/注册，属于 fail-closed（`XxlJobConfig.java:52-53`）。
- 代价：每个环境要显式打开，漏配就不执行；排查先看开关和注册日志。
- 如果所有环境都保证有调度中心，可以默认开；项目多环境/本地开发经常不起 admin，默认关更安全。

### 为什么幂等靠数据库占位/租约，不只靠 XXL-Job 重试

- XXL-Job 只保证触发，不保证「同一业务只执行一次」；重试、人工补跑、多副本都可能重复。项目用 `JobRunMarker.claim` 条件 UPDATE、outbox 的 `SKIP LOCKED` + 租约，把幂等放在业务/DB 层。
- 代价：每个任务要设计幂等键/占位表；占位与副作用必须同事务，否则仍会重复。
- 如果任务本身是幂等的（如全量刷新），可以不加占位；项目对副作用任务统一要求占位。

### 什么条件下会反悔

- 任务量/调度中心高可用要求上升 → 部署 admin 集群、补故障转移；当前单实例。
- fork 维护成本超过收益 → 回退上游/换 Quartz；当前 PG 适配是硬需求。
- 任务简单、无需 UI/分片 → 改用 `@Scheduled` + 分布式锁；当前任务复杂度和可观测性要求更高。

## 我会的部分

- **执行器**：`XxlJobConfig` 装配执行器参数；`enabled` 默认 false，避免环境没部署调度中心时悄悄接活（`XxlJobConfig.java:23-26`、`:52-53`）。
- **logPath 必须可写**：默认 `/data/applogs/xxl-job/jobhandler` 在 macOS 和非 root 容器里建不出来，必须显式配（`XxlJobConfig.java:28-32`、`:72`）。
- **handler 拆分**：`@XxlJob` 入口类只注入业务接口，方便测试直接驱动业务实现（`OutboxDispatchJob.java:17-21`）。
- **幂等**：默认条件 UPDATE 占位 `JobRunMarker.claim`，由架构测试机器检查（`JobIdempotencyArchTest.java:29-58`）；outbox 用 `FOR UPDATE SKIP LOCKED` + 租约（`OutboxDispatchJob.java:23-26`）；权限巡检用 `claim` + 逐租户上下文（`AuthReloadTenantStep.java:60-62`）。
- **PG 适配 7 类**：反引号 144、`LIMIT 偏移,行数` 4、`IFNULL` 3、`DATE_FORMAT` 1、`DATE_ADD` 2、`ON DUPLICATE KEY` 2、`WHERE !(...)` 1（`deploy/README.md:11-19`）。
- **时区坑**：上游 Dockerfile `TZ=PRC`，PG JDBC 驱动透传后直接拒连（`FATAL: invalid value for parameter "TimeZone": "PRC"`）；改成 IANA 名 `Asia/Shanghai`（`xxl-job-admin/Dockerfile:11-16`）。
- **PG 建表**：8 张表 + 初始数据；容器首次启动由 Flyway 自动建表（`doc/db/tables_xxl_job_pgsql.sql:1`、`deploy/README.md:61`）。

## 边界

- 只做 PG 适配，没有改调度算法、路由策略、分片算法、失败重试策略。
- 没有自建调度中心高可用；单实例部署，调度中心挂了任务不触发。
- 分片只在校验探针里打印过，没有真正按分片切业务数据。
- 代码里没有用过 GLUE 模式、子任务、任务依赖；报警邮件没配过（调度中心侧配置，代码里看不到）。
- 没有做过调度中心升级演练；`MAINTAINING.md` 写了流程，但没实际执行过。
- 官方文档与个人改动分开看：7 类 157 处是本仓库 fork 的改动，不是上游能力。

## 相关技能

[[Redisson]]、[[异步导出]]、[[Spring应用与接口契约]]
- 理论：[[调度与协调理论]]

## 用在哪些工程能力

定时调度与后台作业、中间件选型与部署（未建卡）、数据库兼容性改造（未建卡）
