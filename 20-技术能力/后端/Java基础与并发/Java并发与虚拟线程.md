---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战/设计
---

# Java并发与虚拟线程

所属通用技能：[[Java基础与并发]]

**一句话**：我把虚拟线程当「便宜的阻塞载体」用，把限流交给 Redisson 信号量，把 @Async 固定到显式线程池；没有用 CompletableFuture 做编排。

路径约定：以下 `路径:行号` 相对 `smart-server-wms3/src/main/java/com/track/wms/`；测试相对 `smart-server-wms3/src/test/java/com/track/wms/`；配置文件相对 `smart-server-wms3/src/main/resources/`。

## 方法总纲

1. 先分任务类型：IO 密集用虚拟线程，CPU 密集用固定大小池/ForkJoin。
2. 再定上限：线程数不等于下游容量，用信号量/连接池限制真正并发。
3. 再定上下文：跨线程前在主线程抓快照，工作任务内重新绑定 ScopedValue。
4. 再定失败：Runnable 内部 catch 并写状态表；不要指望被丢弃的 Future 报错。
5. 最后定停机：shutdown / shutdownNow / close 语义不同，Spring Bean 必须显式 destroyMethod。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 导出虚拟线程池 + 双信号量 | 实战 | smart WMS | 2026-07 | [[异步导出中的并发]] |
| 导入虚拟线程池 + 双信号量 | 实战 | smart WMS | 2026-08 | [[异步导出中的并发]] |
| @Async 默认池接管 | 实战 | smart WMS | 2026-07 | [[线程池与CompletableFuture]] |
| 执行器停机语义 | 实战 | smart WMS | 2026-07 | [[线程池与CompletableFuture]] |
| PDF 上传超时（虚拟线程 + Future.get） | 实战 | smart WMS | 2026-09 | [[线程池与CompletableFuture]] |

## 我会的部分

- **线程池参数**：`@Async` 池 core 8 / max 16 / queue 200（`application.yml:57-63`），在 `AsyncConfig` 里用 Boot 的 `ThreadPoolTaskExecutorBuilder` 构建（`config/AsyncConfig.java:33-36`）。有界队列是重点：无界队列下 max-size 永远不会生效。
- **虚拟线程**：导出/导入各一个 `Executors.newVirtualThreadPerTaskExecutor()`（`config/ExportPoolConfig.java:41-44`、`config/ImportPoolConfig.java:31-34`）；不池化，每个任务一条虚拟线程。
- **ExecutorService 生命周期**：Bean 上写 `destroyMethod = "shutdown"`（`config/ExportPoolConfig.java:41`、`config/ImportPoolConfig.java:31`），避开 Java 21 `close()` 的 `awaitTermination(1, DAYS)` 无界等待（注释 `config/ExportPoolConfig.java:31-39`）。
- **@Async 退避**：两个 `ExecutorService` Bean 会让 Boot 的 `applicationTaskExecutor` 自动配置整体退避，`@Async` 落到无界 `SimpleAsyncTaskExecutor` 或调度线程；`AsyncConfig` 显式声明 `applicationTaskExecutor` + `taskExecutor` 两个名字（`config/AsyncConfig.java:8-36`）。
- **超时**：安全声明 PDF 上传另起虚拟线程，用 `Future.get(timeout)` 卡上限，超时 `cancel(true)`，`finally` 用 `shutdownNow()`（`service/impl/SafetyAckServiceImpl.java:287-312`）。
- **CPU 并行**：BCrypt 哈希用 `IntStream.range(...).parallel()`，只并行纯 CPU 段，不碰事务和登录上下文（`service/impl/AdminAccountImportHandler.java:166-184`）。
- **测试**：`@Async` 实际线程名前缀 `task-`（`config/GracefulShutdownTest.java:88-104`）；执行器 destroy 快速返回（`config/PoolShutdownTest.java:41-94`）；过载拒绝（`service/impl/ExportServiceImplTest.java:121-125`）。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| IO 密集用虚拟线程，不用平台线程池 | 阻塞时让出载体，少量载体扛大量并发；不用为每个下游估算池大小 | 不池化，创建/调度有开销；`synchronized` 长临界区会 pinning；ThreadLocal 数量大占内存 | CPU 密集/需要限流的任务 → 固定平台线程池；响应式流/背压 → Reactor |
| 并发上限用信号量，不用无界队列 | 队列只是等待，不限制真正并发；信号量直接卡住下游压力 | 信号量满要阻塞/拒绝，调用方要处理；租约信号量要防止不归还 | 允许排队且下游能扛 → 有界队列；需要速率限制 → 令牌桶 |
| `@Async` 显式线程池，不用默认执行器 | 两个 `ExecutorService` Bean 会让 Boot 自动配置退避到无界 `SimpleAsyncTaskExecutor`；显式命名可控 | 要自己配 core/max/queue/reject；池名冲突会启动失败 | 任务量小、无并发风险 → 默认也可，但要确认类型 |
| `CompletableFuture` 只在需要组合时用 | 并行合并、异常链、超时组合表达清楚 | 不传 executor 会用 commonPool；异常不处理会静默丢 | 只是「丢后台跑」→ 虚拟线程/`@Async` 更简单 |
| `destroyMethod="shutdown"` 而不是 `close()` | Java 21 `ExecutorService.close()` 会 `awaitTermination(1, DAYS)`，停机可能挂住 | `shutdown()` 不等待任务完成，未完成任务要自己兜底 | 需要优雅等待 → `shutdown` + 有界 `awaitTermination` |
| ScopedValue 而不是 ThreadLocal | 请求快照只读、生命周期嵌套、退出自动解绑 | Java 21 preview，三处都要 `--enable-preview`；不自动跨线程 | 需要长期存活/动态修改 → ThreadLocal + `remove` |

## 边界

- 仓里没有 `CompletableFuture`、`StructuredTaskScope`、`Thread.ofVirtual()`、自定义 `ThreadFactory`。
- 没有测过虚拟线程的 pinning（`synchronized`/native 调用）；项目里也没有这类代码，属于未知区。
- 导出/导入测试把 `ExecutorService` mock 成同步执行（`ExportServiceImplTest.java:116`、`ImportServiceImplTest.java:177-180`），真实虚拟线程的调度、上下文传播和并发行为没有集成测试证明。
- 没有为导出/导入虚拟线程池单独接指标；@Async 池的监控采集未验证。参数是按要求留余量定的，不是压测出来的。
- 没用过自建 `ThreadLocal` 上下文；`LoginContext` 用请求属性 + ScopedValue。
- 没做过 `synchronized`/`ConcurrentHashMap`/`ReentrantLock` 的实际并发容器选型；锁都在 Redis 侧（分布式锁/信号量）。
- ScopedValue 是 Java 21 preview，编译/测试/运行都靠 `--enable-preview`（`pom.xml:320`、`:333`、`:350`），没评估升级到正式版的迁移成本。

## 相关技能

- [[Java基础与并发]]、[[Java集合与泛型]]
- 场景：[[线程池与CompletableFuture]]、[[ScopedValue上下文]]
- 实践：[[异步导出中的并发]]

## 用在哪些工程能力

- 异步导出/导入的并发控制与停机（[[异步导出中的并发]]）
- 日志/邮件类轻量任务的 @Async 线程池（[[线程池与CompletableFuture]]）
- 带超时的外部 IO 调用（S3 上传）
