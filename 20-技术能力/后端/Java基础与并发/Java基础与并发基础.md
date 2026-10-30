---
type: 基础能力
通用技能: Java基础与并发
域: 后端
证据: 学习中
---

# Java 基础与并发基础

通用技能：[[Java基础与并发]] · 定位：基础知识挂载页

**一句话**：Java 基础与并发基础题的分类索引。这里回答「应该会什么」，不冒充「我做过什么」；做过的事仍记在实践卡。

## 怎么用

- 自测：看每一块的「要能回答」，能用自己的话讲清楚才算过。
- 挂笔记：新写一篇八股文，在对应块的「笔记」后加 `笔记名`，笔记里链回本页。
- 分边界：原理和机制放这里；具体故障、排查过程、修复方案放场景/实践卡。

## 1. JVM 与内存

**一句话**：JVM 把类加载到方法区，对象分配在堆，线程私有栈保存栈帧；GC 回收不可达对象，分代和收集器决定停顿特性。

要能回答：

- 堆、栈、方法区、程序计数器、本地方法栈分别存什么？
- 对象什么时候进入老年代？逃逸分析解决什么？
- 类加载过程？双亲委派模型是什么？
- GC Roots 有哪些？可达性分析怎么工作？
- 常见垃圾收集器（G1、ZGC、CMS）的区别？
- OOM 和 StackOverflow 分别怎么排查？

**笔记**：

- 堆：对象实例和数组，线程共享，GC 主战场；栈：每个线程私有，栈帧存局部变量表、操作数栈、动态链接、返回地址；方法区（JDK 8+ Metaspace）：类元数据、常量、静态变量；程序计数器：当前线程执行的字节码行号；本地方法栈：JNI 调用。
- 对象进入老年代：年龄达到阈值（默认 15，`-XX:MaxTenuringThreshold`）、大对象直接进老年代、Survivor 同年龄对象超过一半（动态年龄判定）、老年代空间担保。逃逸分析判断对象是否逃出方法/线程，不逃逸就可以标量替换/栈上分配，减少堆分配和 GC。
- 类加载：加载（读字节码、生成 Class 对象）→ 链接（验证、准备、解析）→ 初始化（执行 `<clinit>`）。双亲委派：类加载器先委托父加载器，父加载不到才自己加载；保证核心类不被篡改、类只加载一次。Java 9 后是 Bootstrap/Platform/System 三层。
- GC Roots：虚拟机栈中引用的对象、方法区静态属性/常量引用的对象、JNI 引用、活跃线程、锁对象等；从 Roots 做可达性分析，不可达才回收（不是引用计数）。
- 收集器：Serial（单线程、停顿长）、ParNew（多线程年轻代）、CMS（并发标记清除、停顿短、碎片多，已废弃）、G1（Region 分代、可预测停顿）、ZGC（着色指针、并发整理、停顿毫秒级）。选型看堆大小、停顿目标、JDK 版本。
- OOM：`-XX:+HeapDumpOnOutOfMemoryError` 拿 dump，用 MAT 看支配树/泄漏嫌疑；StackOverflow：栈深度超限，通常是递归没终止或栈帧过大，看异常栈。

## 2. 集合

**一句话**：`ArrayList` 基于数组，`LinkedList` 基于链表，`HashMap` 基于数组 + 链表/红黑树；按读写模式和有序性选容器。

要能回答：

- `ArrayList` 和 `LinkedList` 的区别？各自时间复杂度？
- `HashMap` 的底层结构？扩容、哈希冲突、树化条件？
- `HashMap` 为什么线程不安全？`ConcurrentHashMap` 怎么保证并发安全？
- `HashSet` 怎么去重？`equals` 和 `hashCode` 的契约？
- `TreeMap`、`LinkedHashMap` 的有序性怎么实现？
- 遍历集合时修改会怎样？fail-fast 和 fail-safe 的区别？

关联：[[Java集合与泛型]]

**笔记**：

- `ArrayList` 数组，随机访问 O(1)，尾部追加均摊 O(1)，中间插入/删除 O(n)，扩容 1.5 倍并复制；`LinkedList` 双向链表，头尾操作 O(1)，随机访问 O(n)，每个节点多两个指针、内存开销大。绝大多数业务用 `ArrayList`。
- `HashMap`：数组 + 链表 + 红黑树；默认容量 16、负载因子 0.75，超过阈值扩容 2 倍并 rehash；链表长度 ≥8 且容量 ≥64 才树化，树节点 ≤6 退化为链表；哈希用 `(h = key.hashCode()) ^ (h >>> 16)` 扰动，让高位参与索引。
- `HashMap` 线程不安全：并发 put 可能覆盖、丢数据，JDK 7 扩容还可能形成环；`ConcurrentHashMap` JDK 8 用 CAS + synchronized 锁桶头，读不加锁（volatile），扩容多线程协助。
- `HashSet` 内部是 `HashMap`，value 是固定对象；去重靠 `hashCode` 定位桶、`equals` 比较。契约：equals 相等则 hashCode 必须相等；反之不要求。违反会导致 HashSet/HashMap 去重失效。
- `TreeMap` 红黑树，按 key 排序，O(log n)；`LinkedHashMap` 在 HashMap 基础上加双向链表，默认插入顺序，`accessOrder=true` 可按访问顺序（可做 LRU）。
- 遍历时修改：`ArrayList/HashMap` 的迭代器用 `modCount` 做 fail-fast，抛 `ConcurrentModificationException`；`ConcurrentHashMap` 的迭代器是弱一致，不抛但可能看不到最新修改。遍历中删除用 `Iterator.remove` 或 `removeIf`。

## 3. 泛型与类型系统

**一句话**：Java 泛型在编译期做类型检查，运行时擦除；通配符 `? extends` 用于读，`? super` 用于写。

要能回答：

- 类型擦除是什么？擦除后泛型信息还在吗？
- `List<Object>` 和 `List<?>` 的区别？
- `? extends T` 和 `? super T` 分别适合读还是写？
- 泛型方法、泛型类、泛型接口怎么定义？
- 桥接方法是什么？
- 为什么不能 `new T[]`？

关联：[[Java集合与泛型]]

**笔记**：

- 类型擦除：泛型只存在于编译期，编译后变成原始类型 + 强制转换；运行时 `List<String>` 和 `List<Integer>` 都是 `List`。泛型信息在类文件签名/反射的 `ParameterizedType` 里还能看到一部分，但不能 `instanceof List<String>`。
- `List<Object>` 可以放任何对象；`List<?>` 是未知类型，只能读成 Object、不能写（除 null）。`List<? extends T>` 是 T 的子类型，适合读；`List<? super T>` 是 T 的父类型，适合写（PECS：Producer Extends, Consumer Super）。
- 泛型方法 `<T> T foo(T t)`、泛型类 `class Box<T>`、泛型接口 `interface Mapper<T>`；静态方法不能用类的类型参数，要自己声明。
- 桥接方法：子类覆盖泛型父类方法时，编译器生成一个擦除后的桥接方法，保证多态调用能转到子类方法；反射看到两个同名方法时要注意。
- 不能 `new T[]` 是因为擦除后不知道具体类型，无法分配数组；用 `Array.newInstance(componentType, size)` 或 `Object[]` + 强制转换，但会有类型安全警告。

## 4. 异常与资源管理

**一句话**：受检异常强制处理，非受检异常 runtime 抛出；`try-with-resources` 自动关闭资源，异常链保留根因。

要能回答：

- 受检异常和非受检异常的区别？怎么选？
- `throw` 和 `throws` 的区别？
- `finally` 一定会执行吗？哪些情况不执行？
- `try-with-resources` 的关闭顺序？抑制异常是什么？
- 异常包装为什么要保留 cause？
- 自定义异常应该继承什么？

**笔记**：

- 受检异常继承 `Exception` 但不是 `RuntimeException`，编译器强制 catch/throws；非受检继承 `RuntimeException`，不强制。业务可恢复/调用方应处理用受检；编程错误/不可恢复用非受检。项目里业务异常通常继承 `RuntimeException`，配合全局异常处理。
- `throw` 抛出一个异常对象；`throws` 在方法签名声明可能抛出的异常，交给调用方处理。
- `finally` 在正常/异常/return 前都会执行；`System.exit`、JVM 崩溃、死循环/线程被杀、`Runtime.halt` 不执行。finally 里 return 会覆盖 try 的返回值，不要这么写。
- try-with-resources 按「后打开先关闭」的顺序关闭；关闭时抛的异常作为 suppressed 挂在主异常上，不覆盖主异常。比手写 finally 更安全。
- 异常包装保留 cause，才能看到根因栈；只写 message 会丢根因。自定义异常继承 `RuntimeException`（业务）或 `Exception`（需要强制处理），带错误码和可执行 message。

## 5. 线程与 Java 内存模型

**一句话**：线程共享堆、私有栈；JMM 规定可见性、有序性和原子性，`volatile` 保证可见性和有序性，`synchronized` 三者都保证。

要能回答：

- 进程和线程的区别？线程的生命周期？
- 并发三大问题：原子性、可见性、有序性分别是什么？
- `volatile` 能解决什么、不能解决什么？
- `synchronized` 的锁升级过程？
- happens-before 规则有哪些？
- 指令重排什么时候会发生？

关联：[[Java并发与虚拟线程]]

**笔记**：

- 进程有独立地址空间，线程共享进程堆/方法区、私有栈/PC；线程生命周期 NEW → RUNNABLE → BLOCKED/WAITING/TIMED_WAITING → TERMINATED。RUNNABLE 包含「正在跑」和「等 CPU」。
- 原子性：一个操作不可分割；可见性：一个线程的修改另一个线程能看到；有序性：程序顺序不被随意重排。`volatile` 保证可见性 + 禁止重排，不保证 `i++` 原子；`synchronized` 保证三者。
- `volatile` 适合状态标志、DCL 单例的引用；不适合计数、复合操作。`synchronized` 锁升级：无锁 → 偏向锁（JDK 15+ 默认禁用/移除）→ 轻量级锁（CAS 自旋）→ 重量级锁（OS 互斥量）。
- happens-before：程序顺序、监视器解锁→加锁、volatile 写→读、线程 start→线程内、线程内→join 返回、传递性。满足 happens-before 才保证可见/有序。
- 指令重排来自编译器、CPU、内存系统；单线程语义不变，多线程可能看到中间状态。用 volatile/synchronized/final 建立约束。

## 6. 锁与并发工具

**一句话**：`ReentrantLock` 基于 AQS，支持可中断、超时、公平锁；`CAS` 用乐观方式更新，`Atomic` 类基于它实现。

要能回答：

- `synchronized` 和 `ReentrantLock` 的区别？
- AQS 的原理？独占模式和共享模式？
- CAS 是什么？ABA 问题怎么解决？
- `CountDownLatch`、`CyclicBarrier`、`Semaphore` 分别适合什么？
- 死锁的四个必要条件？怎么排查和避免？
- `ThreadLocal` 的原理？内存泄漏怎么产生？

**笔记**：

- `synchronized` JVM 内置、自动释放、非公平；`ReentrantLock` API 级、可中断、可超时、可公平、可多条件队列，必须 finally unlock。简单同步用 synchronized，需要高级能力用 ReentrantLock。
- AQS：一个 `volatile int state` + CLH 双向队列；独占模式（ReentrantLock）state 表示重入次数，共享模式（Semaphore/CountDownLatch）state 表示许可数；抢不到入队 park，释放时 unpark 后继。
- CAS：比较内存值是否等于预期，相等才更新，否则重试；`AtomicInteger` 用 Unsafe CAS。ABA：值从 A→B→A，CAS 以为没变；用 `AtomicStampedReference` 加版本号。
- `CountDownLatch` 一次性，等 N 个任务完成；`CyclicBarrier` 可重用，N 个线程互相等；`Semaphore` 控制并发许可数。`CountDownLatch` 不能 reset，`CyclicBarrier` 可以。
- 死锁四条件：互斥、持有并等待、不可抢占、循环等待；破坏任一即可。排查 `jstack` 看 `Found one Java-level deadlock`；避免固定锁顺序、tryLock 超时、减少锁粒度。
- `ThreadLocal` 每个线程一个 `ThreadLocalMap`，key 是弱引用的 ThreadLocal，value 强引用；ThreadLocal 被回收后 key 为 null，value 还在，线程池长期存活就泄漏。用完 `remove()`。

## 7. 线程池与异步编排

**一句话**：线程池复用线程、控制并发；`CompletableFuture` 做异步编排，但异常处理和线程池选择容易踩坑。

要能回答：

- 线程池的核心参数和执行流程？
- 拒绝策略有哪些？怎么选？
- 线程池大小怎么估？CPU 密集和 IO 密集有什么区别？
- `CompletableFuture` 的 `thenApply`、`thenCompose`、`thenCombine` 有什么区别？
- 异步任务的异常怎么处理？
- 虚拟线程和线程池怎么选？

关联：[[线程池与CompletableFuture]]、[[Java并发与虚拟线程]]

**笔记**：

- 核心参数：corePoolSize、maximumPoolSize、workQueue、keepAliveTime、threadFactory、handler。执行流程：核心线程未满 → 建核心线程；核心满 → 入队；队列满 → 扩到 max；max 满 → 拒绝。无界队列会让 max 永远用不上。
- 拒绝策略：AbortPolicy 抛异常（默认）、CallerRunsPolicy 调用线程执行（降速）、DiscardPolicy 静默丢、DiscardOldestPolicy 丢最旧。业务任务一般用 Abort/CallerRuns，不能静默丢。
- CPU 密集约 N+1；IO 密集约 2N 或按「等待时间/计算时间」比例放大；最终要压测和监控。线程太多会增加上下文切换和内存，队列太长会掩盖过载。
- `thenApply` 是 map（同步转换结果）；`thenCompose` 是 flatMap（返回新的 CompletableFuture）；`thenCombine` 合并两个独立 future。默认用 `ForkJoinPool.commonPool()`，IO 任务要传自己的 executor，否则可能饿死公共池。
- 异常：`exceptionally`/`handle`/`whenComplete`；`thenApply` 里抛异常会变成 failed future，不处理就静默丢。异步任务要有人看结果/日志，不能只 `submit` 不看 Future。
- 虚拟线程适合高并发 IO、阻塞调用；CPU 密集仍用固定线程池。虚拟线程不要池化，每个任务一个；用 `Executors.newVirtualThreadPerTaskExecutor()`。

## 8. 虚拟线程

**一句话**：虚拟线程由 JVM 调度、阻塞时释放载体线程；适合高并发 IO，不适合 CPU 密集和长时间 pinning。

要能回答：

- 虚拟线程和平台线程的区别？
- 虚拟线程为什么不能池化？
- pinning 是什么？哪些操作会导致 pinning？
- 虚拟线程下 `ThreadLocal` 有什么问题？
- 虚拟线程和响应式编程怎么选？
- 怎么观测虚拟线程的数量和阻塞？

关联：[[Java并发与虚拟线程]]、[[ScopedValue上下文]]

**笔记**：

- 平台线程是 OS 线程的一对一封装，创建/切换成本高；虚拟线程是 JVM 管理的轻量线程，挂载到少量载体线程（ForkJoinPool）上，阻塞时卸载，载体去跑别的虚拟线程。
- 虚拟线程不能池化：它们很便宜，池化会限制并发、失去「一个任务一个虚拟线程」的模型；用 `newVirtualThreadPerTaskExecutor` 或直接 `Thread.ofVirtual().start()`。
- pinning：虚拟线程在 `synchronized` 块/JNI/某些 native 调用里阻塞时，不能卸载载体线程，载体被占住；大量 pinning 会退化。JDK 21+ 对 `synchronized` 的 pinning 有改进，但仍要避免长临界区；用 `ReentrantLock` 替代。
- 虚拟线程的 `ThreadLocal` 每个虚拟线程一份，数量巨大时内存开销大；用 `ScopedValue`（预览）或显式传参。项目里用 `ScopedValue` 传登录上下文，见 [[ScopedValue上下文]]。
- 响应式编程（WebFlux/Reactor）用事件循环、非阻塞 API，学习曲线陡；虚拟线程让阻塞代码也能高并发，适合迁移现有 MVC。CPU 密集、需要背压/流式处理时响应式仍更合适。
- 观测：JFR 的 `jdk.VirtualThreadStart/End/Pinned` 事件，`jcmd <pid> Thread.dump_to_file -format=json`，Micrometer 的虚拟线程指标；不要只数线程数。

## 常见对比题

- 进程 vs 线程
- `ArrayList` vs `LinkedList`
- `HashMap` vs `ConcurrentHashMap`
- `volatile` vs `synchronized`
- `synchronized` vs `ReentrantLock`
- 平台线程 vs 虚拟线程
- `CompletableFuture` vs 虚拟线程

## 我现在到哪

| 块 | 现状 | 依据 |
| --- | --- | --- |
| 集合、泛型、异常 | 项目里日常使用 | [[Java集合与泛型]] |
| 线程池、`@Async`、虚拟线程 | 项目里落地过 | [[线程池与CompletableFuture]]、[[Java并发与虚拟线程]] |
| ScopedValue 上下文传播 | 项目里落地过 | [[ScopedValue上下文]] |
| JVM 调优、GC 排查、AQS 源码 | 学习和面试准备，未在项目落地 | 本页 |

## 边界

- 本页是索引，不是教材：每个问题只留一行，展开写到独立笔记。
- 项目里以业务并发和虚拟线程为主，没有 JVM 调优和 GC 专项实战。
- 没有自建 `ThreadLocal` 上下文，锁主要在 Redis 侧。
