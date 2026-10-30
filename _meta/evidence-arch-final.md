# 架构与中间件技能证据 · 完成报告

## 扫描范围
muou_arch（17 ADR + docs/7 篇）、muou-backend 8 个服务仓、muou-server、muou-frontend（web/admin/dashboard）、xxl-job、e2e-hub、easycode-sim、novelforge。只读，未改任何源码。

## 关键发现
1. muou_arch 的 32 次提交作者是 dodo，不是用户；用户证据在代码仓（member 582、common 144、muou-server 283 次提交）。
2. 租户隔离已落地：`muou-common-app/src/main/java/com/voidtech/muou/common/tx/tenant/TenantAwareTransactionManager.java:23-24` 每事务 set_config；`muou-server-notify/muou-notify-app/db/migration/message/V202609231221__notify_rls_notify_type_and_template.sql:8-16` 逐表 ENABLE+FORCE+POLICY；配套设计文档 `muou-server/docs/03-3-RLS与多租户数据隔离.md:1-5`。
3. 异步一致性已落地：`muou-server/src/main/java/com/voidtech/muou/service/JobRunMarker.java:10-34` 把占位与副作用同事务；`muou-server/src/main/java/com/voidtech/muou/job/OutboxDispatchJob.java:24-39` 用 SKIP LOCKED + 租约；`muou-common-app/.../tx/outbox` 下 18 个专项测试。
4. 迁移体系成型：`muou-app-ops/databases/迁移编写约定.md:1-30` 定时间戳版本号与不建外键/列注释门禁/改列名分三次发；`muou-app-ops/databases/collect.sh:1-20` 跨 4 仓收集拼 SQL；实测 446 个迁移文件。
5. 中间件改造实绩：`xxl-job/doc/db/tables_xxl_job_pgsql.sql:1-12` 与提交 `061ea238`，把上游调度中心从 MySQL 改到 PostgreSQL（7 类 157 处方言 + 驱动 + 时区）；业务侧 `muou-server/src/main/java/com/voidtech/muou/config/XxlJobConfig.java:23-52`。

路径前缀：muou 相关为 `/Users/hujiuyuan/workspace/voidtech/muou-client/`，xxl-job 为 `/Users/hujiuyuan/studyspace/xxl-job/`。

## 证据缺口
- ADR-0008/0010/0011 均 Blocked：真实支付、部署供应商、备份恢复无实现代码。
- e2e-hub、novelforge、easycode-sim 无有效 git 提交，只能靠文件与报告佐证。
- 全栈 PostgreSQL，无实际 MySQL 迁移案例；现有 MySQL 组只能借建模与迁移纪律，不能借 RLS。
