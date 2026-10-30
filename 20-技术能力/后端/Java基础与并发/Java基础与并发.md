---
type: 通用技能
域: 后端
证据: 实战/设计
---

# Java基础与并发

**一句话**：Java 基础真正决定业务代码对不对的，不是语法，而是四件事：泛型把类型约束留在编译期、集合/Stream 把批量处理写成一条链、异常带码才能被上层翻译、并发只有在任务边界/上下文/资源上限/生命周期都明确时才安全。

基础知识自测：[[Java基础与并发基础]]

> 四层读法：理论 [[Java基础与并发基础]]｜实践 本页「我用它干过什么」｜问题 [[线程池与CompletableFuture]]、[[ScopedValue上下文]]｜方案 [[smart WMS]]。总入口 [[四层读法]]。

路径约定：以下 `路径:行号` 相对 `smart-server-wms3/src/main/java/com/track/wms/`；测试相对 `smart-server-wms3/src/test/java/com/track/wms/`；配置文件相对 `smart-server-wms3/src/main/resources/`。

## 一、理论：一条异步业务链路上的 Java 机制

1. **泛型**：只在编译期检查，运行时擦除。接口用 `<E, P extends PageReq<?>>` 把「行类型」和「请求类型」绑定在一起，调用方不再 cast；上界 `extends` 决定编排层能安全调用哪些方法。
2. **集合与 Stream**：List 保序、Map 做索引、Set 去重；`stream()` 是惰性链，`map/flatMap/groupingBy/sorted` 决定结果形态。批量导入还要关心初始容量和批次大小。
3. **异常**：`RuntimeException` + 错误码 + i18n key 才是可翻译、可上报的异常；catch 的粒度决定「一行坏」还是「整批坏」。`finally`/try-with-resources 管资源，不管业务。
4. **并发四问**：任务边界（谁提交、谁执行）、上下文（登录/租户/语言怎么过去）、资源上限（下游只能承受多少）、生命周期（关机时在途任务怎么办）。缺一个，代码就会在某个非功能场景下坏掉。
5. **虚拟线程改变的是线程成本，不是下游容量**：阻塞变便宜后，限流要从「池大小」挪到「信号量/配额」。

## 二、实际使用：smart WMS 里的 Java

- **泛型契约**：导出任务接口 `ExportTask<E, P extends PageReq<?>>`（`model/dto/io/ExportTask.java:16`），动态表头实现 `ExportDynTask<P>`（`model/dto/io/ExportDynTask.java:19`），编排层只认 `ExportTask<?, ?>`（`service/impl/ExportServiceImpl.java:85`）。分页响应用泛型静态工厂和 `map` 保类型（`common/result/PageResponse.java:65-97`）。
- **集合/Stream**：导入批次按 `handler.batchSize()` 预分配（`service/impl/ImportServiceImpl.java:227-231`）；错误按 Excel 行号排序（`:355`）；角色按用户分组（`dao/impl/UserRoleDaoImpl.java:59-67`）；挂车类型 `map→flatMap→distinct→toList`（`dao/impl/TrailerDaoImpl.java:130-139`）。
- **异常**：`BusinessException` 同时带数字码、messageCode、args（`common/exception/BusinessException.java:25-55`）；导入逐行 catch 业务异常记行号，其他异常也记成行级错误（`service/impl/ImportServiceImpl.java:248-261`）；整批 `batchSave` 抛异常时逐行记同一条错（`:330-335`）。
- **线程池**：导出/导入各一个 `newVirtualThreadPerTaskExecutor()`（`config/ExportPoolConfig.java:41-44`、`config/ImportPoolConfig.java:31-34`）；`@Async` 用的 `ThreadPoolTaskExecutor` 由 `AsyncConfig` 显式声明（`config/AsyncConfig.java:33-36`），参数在 `application.yml:57-70`。
- **上下文**：`LoginContext.SCOPED` 是 `ScopedValue<LoginCtxDto>`（`common/context/LoginContext.java:20-21`），异步线程里用 `ScopedValue.where(...).run(...)` 注入（`service/impl/ExportServiceImpl.java:118`、`service/impl/ImportServiceImpl.java:157`）。
- **资源上限**：Redisson 可过期信号量做「并发 + 排队」配额（`config/ExportPoolConfig.java:57-71`），拿不到就过载拒绝（`service/impl/ExportServiceImpl.java:97-112`）。
- **生命周期**：执行器 `destroyMethod = "shutdown"`，避免 Spring 推断 `close()` 无界等待（`config/ExportPoolConfig.java:31-44`）；停机预算 Tomcat 15s + @Async 10s（`application.yml:47-70`）。
- **测试**：过载拒绝和 ScopedValue 作用域（`service/impl/ExportServiceImplTest.java:121-125`、`:173-187`）；@Async 落在哪个池、destroy 是否等任务（`config/GracefulShutdownTest.java:73-147`）；执行器销毁不阻塞（`config/PoolShutdownTest.java:41-94`）；上下文优先级（`common/context/LoginContextTest.java:61-75`）。

## 三、归纳：Java 代码检查清单

1. **泛型**：类型参数有没有上界？运行时需要类型吗？需要就显式传 `Class<T>`，别指望擦除后的泛型。
2. **集合**：这个 List 会被改吗？返回 `List.of` 后还有人 add 吗？Map 的 key 是否可变对象？
3. **Stream**：链里有没有副作用？`parallelStream` 是否碰 IO/事务/ThreadLocal？
4. **异常**：抛出的是业务码还是裸字符串？catch 粒度是不是「一行错拖垮整批」？`Error` 需不需要兜？
5. **任务边界**：提交后谁负责异常？Future 被丢弃时，Runnable 内部有没有 try/catch？
6. **上下文**：异步线程读得到登录/租户/语言吗？主线程是否已抓快照？
7. **资源上限**：并发数由谁定？虚拟线程是否被当成了无限配额？
8. **生命周期**：执行器关闭用 shutdown/shutdownNow/close 哪个？会不会阻塞停机？
9. **测试**：边界（过载、空页、中断、超时）有断言吗？还是只测了 happy path？
10. **preview 特性**：编译、测试、运行三处都加了 `--enable-preview` 吗？

### 三条红线

- 不要把虚拟线程当限流：线程便宜，数据库连接和下游配额不便宜。
- 不要在线程池任务里直接读 `RequestContextHolder`：它绑在请求线程上，读到的多半是 null。
- 不要让 `Future` 无人检查、异常只在 Runnable 里打一行日志：失败必须落到状态表或监控。

## 四、回到理论：为什么这些规则成立

- 泛型擦除决定了「运行时没有 T」：要拿类型就必须显式传 `Class`，要避免 cast 就把约束写成上界。
- 请求上下文是线程绑定的：`RequestContextHolder`/`ThreadLocal` 不跨线程；`ScopedValue` 也不自动传播，必须在目标任务内重新绑定作用域。
- 虚拟线程把「线程不够」换成「下游被打满」：所以项目用信号量而不是池大小保护 DB/S3。
- Spring 的销毁是顺序执行链：一个 Bean 的 `close()` 阻塞，会拖住后面所有 Bean 的停机。
- 异常粒度就是数据粒度：逐行导入必须逐行 catch，否则一行脏数据会回滚整批。

## 五、边界

- 仓里**零 `CompletableFuture`**：异步编排用 `ExecutorService.submit` + 状态表 + 轮询，不是 CF 组合式编排；本页不把 CF 写成「我做过」。
- 没用过结构化并发（`StructuredTaskScope`）、`Thread.ofVirtual()` 直接建线程、自定义 `ThreadFactory`。
- 没写过 `synchronized`、`ConcurrentHashMap`、`ReentrantLock`；并发安全主要靠请求内快照 + Redis 分布式锁/信号量。
- Java 21 的 preview 只是跟着项目用（`pom.xml:320`、`:333`、`:350`），没独立评估升级/移除 preview 的风险，也没做压测或 JFR 观测。
- 集合选型没有 benchmark；Optional 不是项目主约定（DAO 大量返回 null）。
- 只做过 Java 21 + Spring Boot 3.3；没做过 Java 8/11/17 的兼容或迁移。

## 相关

- 技能点：[[Java集合与泛型]]、[[Java并发与虚拟线程]]
- 理论：[[排队与限流理论]]
- 方法：[[线程池参数与异步编排]]、[[跨线程传递登录上下文]]
- 场景：[[线程池与CompletableFuture]]、[[ScopedValue上下文]]
- 实践：[[异步导出中的并发]]
- 相邻通用技能：[[Spring应用与接口契约]]、[[数据访问与ORM]]、[[时区与时间序列化]]
- 项目：[[smart WMS]]
