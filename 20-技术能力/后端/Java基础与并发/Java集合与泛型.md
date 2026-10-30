---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战/设计
---

# Java集合与泛型

所属通用技能：[[Java基础与并发]]

**一句话**：集合解决「数据放哪」，泛型解决「编译期别放错」；在项目里我用它们定义导出任务契约、做批量转换，但没有做过集合性能调优。

路径约定：以下 `路径:行号` 相对 `smart-server-wms3/src/main/java/com/track/wms/`；测试相对 `smart-server-wms3/src/test/java/com/track/wms/`。

## 方法总纲

1. 先定元素类型与是否可空，再选容器：要顺序用 List，要按 key 查用 Map，要去重用 Set。
2. 能用上界就不用裸类型：`P extends PageReq<?>` 让编排层既能翻页又不丢具体请求类型。
3. 泛型方法保留元素类型：`PageResponse.of(IPage<T>, Function<T,U>)` 返回 `PageResponse<U>`，调用方不用 cast。
4. Stream 只在「转换/过滤/分组」时用；带事务、IO、ThreadLocal 的循环不要塞进 parallelStream。
5. 返回值不可变就返回 `List.of`；调用方可能要改就返回 `new ArrayList<>`。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 导出任务泛型契约 | 实战 | smart WMS | 2026-07 | [[异步导出中的并发]] |
| 分页响应泛型映射 | 实战 | smart WMS | 2026-06 | [[异步导出中的并发]] |
| 导入批次与错误排序 | 实战 | smart WMS | 2026-08 | [[异步导出中的并发]] |
| 角色分组与类型去重 | 实战 | smart WMS | 2026-08 | — |

## 我会的部分

- **泛型边界**：`ExportTask<E, P extends PageReq<?>>`（`model/dto/io/ExportTask.java:16`）把行类型和请求类型绑定；`Function<P, PageResponse<E>>` 是取页函数（`:25`）。`ExportDynTask<P>` 固定行类型为 `List<Object>`（`model/dto/io/ExportDynTask.java:19`）。调用侧只写 `ExportTask<?, ?>`（`service/impl/ExportServiceImpl.java:85`）。
- **泛型静态工厂**：`PageResponse.of(IPage<? extends T>)`、`of(IPage<T>, Function<? super T, ? extends U>)`、实例 `map`（`common/result/PageResponse.java:65-97`），`? super`/`? extends` 让入参和返回值都放宽。
- **集合选择**：导入批用 `new ArrayList<>(batchSize)` 预分配（`service/impl/ImportServiceImpl.java:227-231`）；错误列表排序用 `Comparator.comparingInt`（`:355`）；角色用 `groupingBy` + `mapping` 生成 `Map<Long, List<Long>>`（`dao/impl/UserRoleDaoImpl.java:59-67`）；挂车类型用 `map→flatMap→distinct→toList`（`dao/impl/TrailerDaoImpl.java:130-139`）。
- **不可变集合**：操作日志的 `Map.of("count", ...)`（`service/impl/ExportServiceImpl.java:192`）、导入的 `Map.of("total", ...)`（`service/impl/ImportServiceImpl.java:392`）只读传参，不修改。
- **Optional**：项目里主要用 `findFirst().orElse(null)`（`dao/impl/DockDaoImpl.java:54`）和外部响应 `getRejectionReason().orElse("unknown")`（`service/impl/IOSPushServiceImpl.java:269`）；没有把 Optional 当字段/入参用。
- **record**：只用于不可变 DTO（如 `model/dto/warehouse/LocRef.java:10`、`model/dto/logs/LogActor.java:9`），没有当实体用。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| `ArrayList` 而不是 `LinkedList` | 随机访问 O(1)、内存连续、缓存友好；尾部追加均摊 O(1) | 中间插入/删除 O(n)；扩容复制 | 频繁头插/中间删且已持有节点 → `LinkedList`/`ArrayDeque` |
| `HashMap` 而不是 `TreeMap` | O(1) 查找，满足大多数按 key 取 | 无序；哈希冲突多时退化 | 需要按 key 排序/范围查询 → `TreeMap`/`ConcurrentSkipListMap` |
| `ConcurrentHashMap` 而不是 `Collections.synchronizedMap` | 分段/CAS + 桶锁，读不加锁，并发吞吐高 | 弱一致迭代；复合操作要用 `compute` | 需要强一致快照/全表锁 → 加锁或复制 |
| `List.of`/`Map.of` 返回不可变 | 只读契约清晰，防调用方误改 | 不允许 null，改会抛异常 | 调用方需要修改 → `new ArrayList<>` |
| Stream 而不是 for 循环 | 转换/过滤/分组表达清晰、可组合 | 调试难、有装箱/lambda 开销；副作用难控 | 带 IO/事务/ThreadLocal/复杂控制流 → 普通循环 |
| `record` 而不是普通类 | 不可变 DTO 少样板，equals/hashCode 自动 | 不能继承、字段不可变 | 需要可变/框架反射赋值 → 普通类 |

泛型取舍：参数用 `? extends T`（只读）、写入用 `? super T`（PECS）；返回 `List<T>` 而不是 `List<? extends T>`，让调用方能放；不要用裸类型，`@SuppressWarnings` 要写清原因。

## 边界

- 没有写自定义泛型集合、通配符捕获（capture）或 `TypeToken` 反序列化。
- 没有用 `parallelStream`；唯一并行是 BCrypt 的 `IntStream.parallel()`（`service/impl/AdminAccountImportHandler.java:180-184`），属于 CPU 计算，不是集合流。
- 集合容量/数据结构没有 benchmark；`ArrayList` vs `LinkedList` 等项目里没有对比数据。
- Optional 不是项目约定：DAO/Service 大量直接返回 null，不能把「用 Optional 包装」当成团队规范。
- 没做过泛型与 Jackson 多态反序列化的组合（`@JsonTypeInfo` 等）。

## 相关技能

- [[Java基础与并发]]、[[Java并发与虚拟线程]]、[[线程池与CompletableFuture]]
- 相邻：[[数据访问与ORM]]、[[Spring应用与接口契约]]

## 用在哪些工程能力

- 异步导出/导入的任务契约与分页转换（[[异步导出中的并发]]）
- DAO 批量查询结果的组装（分组、去重、排序）
- 统一响应的泛型包装（[[Spring应用与接口契约]]）
