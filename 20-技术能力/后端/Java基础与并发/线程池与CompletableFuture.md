---
type: 场景
技能点: Java并发与虚拟线程
方法: 线程池参数与异步编排
证据: 实战/学习
---

# 线程池与CompletableFuture

技能点：[[Java并发与虚拟线程]] · 方法：[[线程池参数与异步编排]] · 通用技能：[[Java基础与并发]]

**什么时候会遇到**：接口里要并行做几件事、批量任务变慢、`@Async` 写了却没异步、服务一关机就丢任务、下游 DB/S3 被打满。

路径约定：以下 `路径:行号` 相对 `smart-server-wms3/src/main/java/com/track/wms/`；测试相对 `smart-server-wms3/src/test/java/com/track/wms/`；配置文件相对 `smart-server-wms3/src/main/resources/`。

## 判断顺序

1. **任务是 IO 还是 CPU**：IO 用虚拟线程或较大池；CPU 用 `CPU 核数` 左右的固定池/ForkJoin。
2. **下游能承受多少并发**：先定配额，再定线程数；虚拟线程不提供背压。
3. **用 @Async 还是直接 submit**：@Async 依赖代理调用和线程池 Bean，异常不会回到调用方；submit 返回 Future，但项目里 Future 被丢弃。
4. **需要组合多个结果吗**：需要 `thenCombine/allOf/exceptionally` 才上 CompletableFuture；只需要「提交后就不管」用 ExecutorService 就够。
5. **关机时怎么办**：明确 shutdown / shutdownNow / close 的差别，以及停机预算。
6. **失败怎么被看见**：Runnable 内 catch + 状态表，或 Future 被检查；两者都没有就是静默丢任务。

## 手段

- **@Async 池**：core 8 / max 16 / queue 200，启用 await-termination 10s（`application.yml:57-70`）；Bean 名同时注册 `applicationTaskExecutor` 和 `taskExecutor`（`config/AsyncConfig.java:33-36`）。
- **虚拟线程执行器**：`newVirtualThreadPerTaskExecutor()`，每个任务一条虚拟线程，不排队（`config/ExportPoolConfig.java:41-44`）。
- **背压**：Redisson `RPermitExpirableSemaphore`，admit = 并发+排队，running = 并发；`tryAcquire(0, 30min)` 拿不到就拒绝（`config/ExportPoolConfig.java:57-71`、`service/impl/ExportServiceImpl.java:97-112`）。
- **超时**：`Future.get(timeout)` + `cancel(true)` + `shutdownNow()`（`service/impl/SafetyAckServiceImpl.java:290-311`）。
- **停机**：`server.shutdown=graceful`、Tomcat 15s、@Async 10s（`application.yml:3-5`、`:51`、`:70`）；执行器 `destroyMethod=shutdown`（`config/ExportPoolConfig.java:41`）。

## 反例 / 边界

- **无界队列 + max-size**：队列无界时线程池永远扩不到 max，任务无限积压；项目明确用 200 有界队列（`application.yml:60-63`）。
- **@Async 退化**：`ExecutorService` Bean 会让 Boot 的 `TaskExecutorConfiguration` 退避，`@Async` 落到 `SimpleAsyncTaskExecutor` 或单个调度线程（`config/AsyncConfig.java:8-28`、`config/GracefulShutdownTest.java:88-104`）。
- **close() 停机**：Spring 对 `AutoCloseable` Bean 默认推断 `close()`，Java 21 的 `ExecutorService.close()` 会 `awaitTermination(1, DAYS)`（`config/ExportPoolConfig.java:31-39`、`config/PoolShutdownTest.java:23-33`）。
- **Future 丢弃**：`exportExecutor.submit(...)` 的返回值没人接（`service/impl/ExportServiceImpl.java:114-131`），Runnable 内必须自己 catch，否则异常只在日志里（`:197-199`）。
- **CompletableFuture 在本仓库没有实际用法**：无 `thenCombine`/`allOf`/`exceptionally` 代码；本页只把它当「需要组合结果时的选项」，不算我做过（学习中）。

## 现在的规矩

- 先定下游配额，再定线程数；虚拟线程只解决「线程不够」，不解决「下游扛不住」。
- `@Async` 必须有显式 `applicationTaskExecutor`/`taskExecutor` Bean，否则不写。
- 执行器关闭语义写死：共享池用 `shutdown` + await-termination 预算；一次性超时任务用 `shutdownNow`。
- 组合多个异步结果才考虑 CompletableFuture；只是「提交后台跑」就用 ExecutorService + 状态表。

## 相关实践

- [[异步导出中的并发]]
- [[ScopedValue上下文]]

## 来源

- `config/AsyncConfig.java`、`config/ExportPoolConfig.java`、`config/ImportPoolConfig.java`
- `src/main/resources/application.yml`
- `config/GracefulShutdownTest.java`、`config/PoolShutdownTest.java`
- `service/impl/SafetyAckServiceImpl.java`
