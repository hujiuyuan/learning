---
type: 技能点
域: 后端
项目: [smart WMS, muou-client]
证据: 实战/设计
---

# Spring事务

所属通用技能：[[事务与状态一致性]]

**一句话**：`@Transactional` 只是给代理看的标记；调用不经过代理、异常没抛出去、传播级别不对，三者任一发生，注解在也不生效。

## 方法总纲

1. **代理入口**：只有 Spring 代理拦截到的 public 方法才开事务；同类 `this` 调用、private/final 方法、`@Async` 线程都不经过代理。
2. **传播**：`REQUIRED` 加入当前事务；`REQUIRES_NEW` 挂起当前事务、开一条新物理事务；`MANDATORY` 没有事务就抛。
3. **回滚规则**：默认只对 `RuntimeException`/`Error` 回滚；checked exception 必须 `rollbackFor = Exception.class`。
4. **只读**：`readOnly = true` 是给驱动/ORM 的优化提示，不是「禁止写」的保险。
5. **代码内边界**：`TransactionTemplate` 适合 private 方法、循环按批提交、需要显式控制传播的场景。
6. **提交后**：`afterCommit` 只在外层事务真正提交后触发；回调里写库必须 `REQUIRES_NEW`。
7. **验证**：注解断言只能证明「声明了边界」，真回滚要靠真库 + 中途失败。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| `reserveLocation` 补事务边界，懒建行与后续写入同事务 | 实战 | smart WMS | 2026-08 | [[事务失效]] |
| 签到后 PDF 归档：`afterCommit` + `REQUIRES_NEW` | 实战 | smart WMS | 2026-09 | [[事务失效]] |
| `mergeSave` 先删后插真回滚 E2E | 实战 | smart WMS | 2026-09 | [[事务失效]] |
| 定时任务 `claim` 用 `MANDATORY` 强制同事务 | 实战 | muou-client | 2026-09 | [[任务幂等]] |
| Outbox `publish` 拒绝事务外写入 | 实战 | muou-client | 2026-09 | [[Outbox]] |

## 选型与取舍

### 为什么用声明式 `@Transactional`，不全部写 `TransactionTemplate`

- 声明式注解让事务边界贴着 Service 方法，代码短、评审容易看出「这个方法是一个事务」；大多数单数据源 CRUD 用注解足够。
- 代价：代理失效（自调用/private/final/异步线程）、异常类型、传播级别都会让注解「在但不生效」；排查要懂 Spring AOP。项目因此保留 `TransactionTemplate` 处理 private 方法、循环分批、`REQUIRES_NEW` 等注解表达不了的场景。
- 结论：默认注解，边界复杂/需要显式控制时用编程式；不是「注解更高级」，是两种工具各管一段。

### 为什么本地事务 + Outbox/XA，不全部用一个全局事务

- 单库写入用本地事务最简单、最快；跨库强一致才上 XA，异步解耦用 Outbox。全部套全局事务会把不需要强一致的链路也拖进锁/TC 依赖。
- 代价：本地事务不能跨服务回滚；Outbox 有延迟/重复；XA 有阻塞/TC 单点。项目按链路选，不追求「全站一个事务」。
- 如果业务边界清晰、最终一致可接受，本地事务 + Outbox 是默认；只有必须当场一致的入口才用 XA。

### 为什么 `rollbackFor = Exception.class`，不只用默认 RuntimeException

- Spring 默认只对 RuntimeException/Error 回滚，checked exception 不回滚；业务里如果抛 checked 异常，会出现「异常抛了但数据已提交」。
- 代价：`rollbackFor = Exception.class` 会把所有异常都回滚，包括一些「可恢复/应继续」的异常；要确保异常分类和补偿逻辑清楚。
- 项目多数写方法用默认，只有明确需要的用 `rollbackFor`；这不是全库统一，而是按异常语义选。

### 为什么 `afterCommit` 里写库要 `REQUIRES_NEW`

- `afterCommit` 触发时外层事务已提交，原事务连接/上下文可能已结束；直接写库可能没有事务或复用已关闭的连接。`REQUIRES_NEW` 明确开一条新物理事务。
- 代价：新事务和外层事务不是原子的；外层成功、内层失败要补偿/告警。项目在 PDF 归档等场景用这个模式，并接受「归档失败不回滚主业务」。
- 如果副作用必须和主业务同成败，应该放主事务内（但可能拖长事务）；`afterCommit` 适合「主业务成功后再做、失败可重试」的副作用。

### 什么条件下会反悔

- 跨服务强一致入口增多 → 评估 Seata XA/事务消息；当前只有少数入口。
- 注解失效反复出事故 → 收紧规范/静态检查，关键路径改编程式；当前靠评审 + 真库测试。
- `afterCommit` 副作用失败影响业务 → 改成 Outbox/消息表，保证可重试；当前部分场景只告警。

## 我会的部分

- **回滚范围**：`smart-server-wms3/src/main/java/com/track/wms/service/impl/WarehouseServiceImpl.java:1004`、`:1343` 用 `@Transactional(rollbackFor = Exception.class)`；仓内多数写方法沿用默认 `@Transactional`。
- **提交后 + 新事务**：`smart-server-wms3/src/main/java/com/track/wms/service/impl/SafetyAckServiceImpl.java:106-125` 用独立 `TransactionTemplate` 设 `PROPAGATION_REQUIRES_NEW`，不污染共享模板；`smart-server-wms3/src/main/java/com/track/wms/service/impl/ShippingTaskServiceImpl.java:524-539` 注册 `afterCommit`。
- **private 方法**：`smart-server-wms3/src/main/java/com/track/wms/service/impl/InfoServiceImpl.java:8924-8930`、`smart-server-wms3/src/main/java/com/track/wms/service/impl/OperationLogArchiveServiceImpl.java:112-123` 明确写「private 方法上的 `@Transactional` 不生效，故用 `TransactionTemplate`」。
- **自调用**：`muou-server/src/main/java/com/voidtech/muou/job/AuthReloadTenantStep.java:19-23` 把「一个租户一步」拆成独立 bean，因为同类调用不过代理、事务根本不开，而 `claim` 是 `MANDATORY` 会当场抛。
- **只读**：`smart-server-wms3/src/main/java/com/track/wms/service/impl/TrailerDemandServiceImpl.java:83`、`:105` 两处查询用 `readOnly = true`。
- **真回滚**：`smart-server-wms3/src/test/java/com/track/wms/service/impl/MergeSaveTxE2eTest.java:36-49` 说明为什么必须真库；`:190-214` 注入第 3 条插入失败，断言旧规则还在、新规则一条不写。
- **注解断言的局限**：`smart-server-wms3/src/test/java/com/track/wms/service/impl/WarehouseReserveLocationTest.java:363-376` 自认「Mockito 无法驱动真实事务回滚，退而求其次做反射断言」。

## 边界

- `reserveLocation` 没有真实回滚 IT；不能把 `:371-376` 的反射断言写成「回滚已验证」。
- 都是单数据源本地事务；没做过 JTA、多数据源事务、跨库事务。
- 没验证过 `readOnly = true` 下写库会怎样；仓内只用于查询。
- 没做过隔离级别、事务超时的专项配置与验证。
- `@Async` 与 `@Transactional` 同方法没做过；异步日志与业务事务的原子性明确不保证，见 `smart-server-wms3/src/main/java/com/track/wms/service/impl/InfoServiceImpl.java:873-875`。
- 没做过响应式（WebFlux）事务。
- 时间说明：smart 不是 git 仓库，表里的 `2026-08`/`2026-09` 按测试与实现文件的修改时间推断，不是提交记录。

## 相关技能

- 通用技能：[[事务与状态一致性]]
- 场景：[[事务失效]]、[[任务幂等]]
- 技能点：[[Outbox]]、[[TaskFlowEngine]]

## 用在哪些工程能力

- 业务 Service 的事务边界设计与评审
- 排查「注解在但不回滚 / 提交后写库没生效」
- 定时任务、消息消费、提交后副作用的事务前提
- 为事务写可证伪的真库测试
