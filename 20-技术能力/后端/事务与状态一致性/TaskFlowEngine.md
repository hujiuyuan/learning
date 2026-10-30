---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战/设计
---

# TaskFlowEngine

所属通用技能：[[事务与状态一致性]]

**一句话**：把任务生命周期的固定骨架放进 Context 引擎，类型差异抽成 Strategy 接口，服务用组合实现；状态推进靠 CAS，骨架跑在 Redis 锁 + 数据库事务内。

## 方法总纲

1. **Context**：`TaskFlowEngine` 持有 `TaskInfra`，提供 `claim/complete/cancel/doAssign` 模板：锁 → 事务 → 加载校验 → 状态机流转 → CAS 落库 → 回调。
2. **Strategy**：`TaskFlow` 只留 `taskType()`、`bindClaimer()` 和三个 default 钩子（`onStatusChanged/afterComplete/afterCancel`），类型差异由各 Service 实现。
3. **组合替代继承**：三个任务 Service 不再 `extends AbstractTaskService`，改成 `implements TaskFlow` + 注入 `engine`；抽象基类已删除。
4. **锁内事务**：`inLockTx` 先拿单任务 Redis 锁，再用 `TransactionTemplate` 开事务，提交后释放锁。
5. **CAS**：`updateOnStatus(entity, fromStatus)` 的 WHERE 是 `id + status=fromStatus`；返回 0 行说明状态已变。
6. **幂等分流**：`startForShip/completeForShip` 在 CAS 0 行时重读；已是目标态就跳过，不是目标态才抛 `TASK_STATUS_INVALID`。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 任务中心继承 → 策略模式改造 | 实战 | smart WMS | 2026-05 | [[任务幂等]] |
| 任务状态 CAS 落库 + 幂等分支 | 实战 | smart WMS | 2026-07 | [[任务幂等]] |
| 锁 + 事务骨架复用 | 实战 | smart WMS | 2026-05 | [[事务失效]] |

## 我会的部分

- **接口**：`smart-server-wms3/src/main/java/com/track/wms/service/TaskFlow.java:11-30`。
- **引擎**：`smart-server-wms3/src/main/java/com/track/wms/service/impl/TaskFlowEngine.java:25-33` 类注释写明「策略模式 Context」；`:43-57` claim、`:60-74` complete、`:77-91` cancel、`:161-176` doAssign。
- **锁内事务**：同上文件 `:178-182`，注释是「锁→事务→提交→释放锁」。
- **CAS**：同上文件 `:52-54`、`:68-70`、`:115-124`；DAO 实现 `smart-server-wms3/src/main/java/com/track/wms/dao/impl/WorkTaskDaoImpl.java:18-24`。
- **幂等**：同上文件 `:104-127`、`:138-158`；测试 `smart-server-wms3/src/test/java/com/track/wms/service/impl/TaskFlowEngineTest.java:94-127`（CAS 竞态已达目标态则跳过、非目标态则抛）。
- **改造计划**：`smart/docs/superpowers/plans/2026-05-25-任务中心策略模式改造.md:5-12` 定义目标与架构；`:30-41` 给出继承→组合的机械替换规则；`:94` 说明骨架逐行搬移；`:1073` 以「总测试数 = 改造前 310」作为行为不变判据。**复选框未勾选**，代码与测试以仓库现状为准。
- **落地**：`smart-server-wms3/src/main/java/com/track/wms/service/impl/TaskMoveServiceImpl.java:67`、`smart-server-wms3/src/main/java/com/track/wms/service/impl/TaskPreloadServiceImpl.java:86`、`smart-server-wms3/src/main/java/com/track/wms/service/impl/TaskOnsiteServiceImpl.java:67` 均实现 `TaskFlow`；两个抽象基类文件已不存在。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| 组合 + Strategy 而不是继承抽象基类 | 三个任务 Service 骨架相同、类型差异有限；组合避免基类膨胀和强耦合 | 每个 Service 要注入 engine、实现接口；钩子多了接口会变宽 | 类型差异变大、钩子爆炸 → 拆更细的领域服务/状态机 |
| 手写状态机 + CAS 而不是引入 COLA/Flowable | 状态少、流转固定，手写可控、无框架依赖 | 状态/事件多了会散落；没有可视化/审计 | 流转复杂、需要编排/补偿 → 状态机引擎或工作流引擎 |
| Redis 锁 + 数据库事务 | 锁降低同一任务并发，事务保证状态和副作用原子 | 锁过期/Redis 故障仍有并发；锁内做 IO 会拉长持锁 | 单库 CAS 已够 → 去掉锁；跨服务 → 分布式事务/Outbox |
| CAS（`WHERE status=from`）而不是 `SELECT FOR UPDATE` | 无长事务、无悲观锁等待，冲突时影响 0 行可判断 | 冲突要重读/重试；0 行语义要区分「已到目标态」和「非法状态」 | 冲突率极高、重试成本大 → 悲观锁/排队 |
| 副作用同事务，不接 Outbox | 当前副作用是本地状态同步，回滚要一起回滚 | 外部 IO/消息在同一事务会拖长/不一致 | 出现跨服务/消息/HTTP → Outbox + 补偿 |

## 边界

- 计划文档的 `- [ ]` 未勾选，不能把计划当「已完成记录」；代码和测试已存在，但本次没有重跑全量测试。
- 只在 smart WMS 做过；没有在其他项目复用这套引擎。
- 锁是单任务粒度的 Redis 锁；没做过分区/批量任务的并发控制。
- 行为不变的计划判据是「逐行搬移 + 测试全绿 + 总数不变」；本次只核对了代码与测试文件存在，没有独立验证总数仍是 310，也没有自动化 diff。
- 状态变更后的副作用（同步 move_status 等）仍在同一事务内做；没有接 Outbox。
- 时间说明：`2026-05` 按改造计划日期，`2026-07` 按 `TaskFlowEngine.java` 文件修改时间；smart 不是 git 仓库，均非提交记录。

## 相关技能

- 通用技能：[[事务与状态一致性]]
- 技能点：[[Spring事务]]
- 场景：[[任务幂等]]、[[事务失效]]

## 用在哪些工程能力

- 多类型业务的模板骨架复用
- 继承→组合/策略模式重构
- 状态机 + CAS 并发控制
- 锁与事务的先后顺序设计
