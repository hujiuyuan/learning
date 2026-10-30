# 后端技能证据扫描（smart-server-wms3）

## 扫描范围
- `/Users/hujiuyuan/workspace/voidtech/smart`：smart-server-wms3（9128 个 Java 文件、534 个测试类、4364 次提交）、docs 82 篇 plan/spec/报告、smart-web-wms 与 smart-web-omp 的 package.json 与 docs；覆盖 8 个候选技能，只读。

## 关键发现
1. 权限体系是「认证实战、授权未启用」：JWT 过滤器、keyVer 单端登录、代登录均已落地并有 E2E，但 `smart-server-wms3/src/main/resources/application.yml:183` 为 `api-perm-enabled: false`，代码注释自认全项目零 `@PreAuthorize`（`smart-server-wms3/src/main/java/com/track/wms/service/impl/ImpersonateServiceImpl.java:241`）。
2. MyBatis-Plus 实践最深：4 层拦截器链 + 租户插件 + `@TableLogic`，454 处条件构造，多组 `@MybatisPlusTest` + Testcontainers IT（`smart-server-wms3/src/main/java/com/track/wms/config/MybatisPlusConfig.java:33`、`smart-server-wms3/src/main/java/com/track/wms/config/WmsTenantLineHandler.java:86`）。
3. 时区治理已全量落地但与文档矛盾：`smart-server-wms3/src/main/java/com/track/wms/config/InstantNyTypeHandler.java:16` 全局注册、70 个响应 DTO 全 Instant，而计划仍写「待执行」（`docs/superpowers/plans/2026-06-17-wms-time-utc-unify-plan.md:3`）。
4. 定时任务的「自停守卫」只停留在方案：报告明确「待讨论，本次未实施」（`docs/2026-07-16-测试数据库卡顿排查报告.md:149-154`），`smart-server-wms3/src/main/java/com/track/wms/scheduler/OmpTenantBackfillJob.java:51` 仍每小时执行 9 条全表 UPDATE。
5. 异步导出与任务中心策略模式均为完整实战：虚拟线程 + Redisson 信号量（`smart-server-wms3/src/main/java/com/track/wms/config/ExportPoolConfig.java:28`），继承改 Context+Strategy（`smart-server-wms3/src/main/java/com/track/wms/service/impl/TaskFlowEngine.java:33`），均有对应测试。

## 证据缺口
- 所有 plan 复选框全程未勾选，不能据此判断完成度；`role-rebind` 计划标 Draft 但 `sys_role.scope`/`can_use` 已落库（`smart-server-wms3/src/main/resources/db/sql/update-init.sql:54,69-70`）。
- 事务与 i18n 缺独立设计文档；事务回滚仅有注解断言、无真实回滚 IT（`smart-server-wms3/src/test/java/com/track/wms/service/impl/WarehouseReserveLocationTest.java:366-368`）。
- 异步导出代码注释称 io_record 无 reaper，实际 `smart-server-wms3/src/main/java/com/track/wms/scheduler/IoReaperJob.java:42` 已补，注释滞后于实现。
