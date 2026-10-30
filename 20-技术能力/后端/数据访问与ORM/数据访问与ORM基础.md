---
type: 基础能力
通用技能: 数据访问与ORM
域: 后端
证据: 学习中
---

# 数据访问与 ORM 基础

通用技能：[[数据访问与ORM]] · 定位：基础知识挂载页

**一句话**：数据访问基础题的分类索引。这里回答「应该会什么」，不冒充「我做过什么」；做过的事仍记在实践卡。

## 怎么用

- 自测：看每一块的「要能回答」，能用自己的话讲清楚才算过。
- 挂笔记：新写一篇八股文，在对应块的「笔记」后加 `笔记名`，笔记里链回本页。
- 分边界：原理和机制放这里；具体故障、排查过程、修复方案放场景/实践卡。

## 1. JDBC 与连接池

**一句话**：JDBC 是 Java 访问数据库的规范；连接池复用物理连接，核心参数是最大连接数、最小空闲、获取超时和存活检测。

要能回答：

- `DriverManager`、`DataSource`、`Connection` 的关系？
- 连接池为什么不能无限大？连接数和数据库线程、下游容量是什么关系？
- 连接泄漏怎么发现？`removeAbandoned` 之类的兜底有什么代价？
- 事务和连接是什么关系？一个事务能不能跨多个连接？

笔记：

- `DriverManager` 每次新建物理连接；`DataSource` 是连接工厂，连接池实现（HikariCP/Druid）在背后复用连接；`Connection` 是一次数据库会话，事务、会话变量、临时表都绑在它上面。
- 连接池不能无限大：数据库能承载的连接数有限，每个连接占数据库线程/内存；应用连接总数要 ≤ 数据库上限，还要给运维/其他应用留余量。池太大只会把压力推给数据库，表现为连接超时/数据库拒绝。
- 泄漏表现：活跃连接数持续上涨、获取连接超时、数据库连接被打满。`removeAbandoned` 能兜底关闭长时间未归还的连接，但会误杀长事务，且泄漏根因还在；先用 `leakDetectionThreshold` 定位借出栈。
- 一个事务绑定一个连接，不能跨多个连接；跨库/跨服务要么用分布式事务，要么放弃强一致（Outbox/补偿）。多数据源下 `@Transactional` 只对其中一个数据源生效。
- 连接池参数要和下游容量、线程池一起算：请求线程 > 连接数时，线程会等连接；连接数 > 数据库容量时，数据库先崩。

## 2. SQL 与 ORM 映射

**一句话**：ORM 把表行映射成对象，省掉手写 ResultSet；代价是隐藏 SQL、容易产生 N+1 和意外更新。

要能回答：

- 全自动 ORM（JPA/Hibernate）和半自动（MyBatis）各适合什么场景？
- 实体、DTO、VO 为什么要分开？直接返回实体有什么风险？
- 一对一、一对多、多对多怎么映射？懒加载在什么时候触发？
- N+1 问题怎么产生、怎么发现、怎么解决？
- 脏检查（dirty checking）和显式 update 的区别？

关联：[[数据访问与ORM]]

笔记：

- JPA/Hibernate 全自动：实体映射、脏检查、级联、JPQL，适合领域模型和标准 CRUD；MyBatis 半自动：自己写 SQL、自己控结果映射，适合复杂查询、性能敏感、SQL 可控的场景。项目用 MyBatis-Plus。
- 实体是表行，DTO 是接口入参/出参，VO 是展示模型。直接返回实体：暴露内部字段/敏感列、懒加载序列化报错、前端能传不该传的字段（mass assignment）、表结构变更直接破坏接口。
- 一对一/一对多用 `@OneToOne/@OneToMany` 或 MyBatis 的 `association/collection`；多对多用中间表。懒加载在「访问关联属性」时触发，Session 关闭后访问会 `LazyInitializationException`。
- N+1：查列表 1 条 SQL，再为每行查关联 N 条。开 SQL 日志能看到重复语句；解决用 join fetch、`@EntityGraph`、`batchSize`，或手写一次查询 + 内存组装。
- 脏检查：事务提交时 Hibernate 自动比对新旧值并发 update，方便但容易「改了一个字段，update 了整行」或意外更新；显式 update 可控，但要自己写。MyBatis 没有脏检查，都是显式 SQL。

## 3. MyBatis 执行链

**一句话**：`SqlSessionFactory` 创建 `SqlSession`，`Executor` 执行 SQL，`StatementHandler` 处理 JDBC，`ParameterHandler`/`ResultSetHandler` 负责参数和结果映射。

要能回答：

- `SqlSession`、`Executor`、`StatementHandler` 各自负责什么？
- 一级缓存和二级缓存的作用域？为什么一级缓存会踩坑？
- `#{}` 和 `${}` 的区别？为什么 `${}` 有 SQL 注入风险？
- 动态 SQL 的 `if`、`choose`、`foreach` 分别怎么用？
- 插件（Interceptor）能拦截哪些对象？多个插件的执行顺序？

关联：[[MyBatis-Plus]]、[[插件链]]

笔记：

- `SqlSessionFactory` 生产 `SqlSession`；`SqlSession` 是面向用户的会话（增删改查、事务提交）；`Executor` 负责执行、缓存、事务；`StatementHandler` 管 JDBC Statement；`ParameterHandler` 设参；`ResultSetHandler` 映射结果。
- 一级缓存是 `SqlSession` 级，默认开，同一会话内相同查询走缓存；更新/提交会清空。Spring 下会话绑定事务，事务内多次查询可能读到旧值；跨事务不复用。
- 二级缓存是 namespace 级、跨 `SqlSession`，要显式开启并实现序列化；多表关联/更新其他 namespace 时容易脏，生产一般不用或只读表用。
- `#{}` 是预编译占位符，参数走 `PreparedStatement`，安全；`${}` 是字符串替换，拼进 SQL，用户可控就有注入风险，只用于表名/列名/排序字段且必须白名单。
- 插件可拦截 `Executor`、`StatementHandler`、`ParameterHandler`、`ResultSetHandler`；多个插件形成代理链，后注册的先执行（包装顺序相反）。插件顺序会改变最终 SQL，租户/软删/分页的顺序要固定并测试。

## 4. MyBatis-Plus 增强

**一句话**：MyBatis-Plus 在 MyBatis 上提供通用 CRUD、条件构造器、分页、租户、软删除、乐观锁等插件；插件顺序会改变最终 SQL。

要能回答：

- `BaseMapper` 的通用方法有哪些？`Wrapper` 怎么用？
- 分页插件怎么工作？`maxLimit` 防的是什么？
- 逻辑删除怎么实现？查、改、删分别要注意什么？
- 乐观锁插件靠什么字段？更新失败怎么处理？
- 多租户插件在 SQL 的哪个阶段改写？哪些表要排除？

关联：[[MyBatis-Plus]]、[[MyBatis分页]]、[[租户插件落地]]、[[软删除]]、[[乐观锁]]

笔记：

- `BaseMapper` 提供 `insert/deleteById/updateById/selectById/selectList/selectPage` 等通用方法；`Wrapper`（`QueryWrapper/LambdaQueryWrapper`）拼条件，`Lambda` 版用方法引用避免字段名硬编码。
- 分页插件在 SQL 执行前改写：先查 count，再拼 `LIMIT offset, size`；`maxLimit` 限制单页最大条数，防止 `size=100000` 拖垮数据库/内存。
- 逻辑删除：查询自动加 `deleted = 0`，删除转成 `UPDATE ... SET deleted = 1`；更新也要带未删除条件。唯一索引要处理「删除后同编码能否复用」，否则逻辑删除的行仍占唯一键。
- 乐观锁插件靠 `version` 字段：更新时 `WHERE version = ?` 并 `SET version = version + 1`，影响 0 行说明并发冲突，要重试或报错，不能静默当成功。
- 多租户插件在 SQL 解析阶段改写（where/insert），全局表、字典表、平台表要显式排除；排除表清单要维护并测试，漏排会跨租户，多排会查不到数据。

## 5. 事务与会话

**一句话**：MyBatis 的 `SqlSession` 本身不提交事务，Spring 通过 `SqlSessionTemplate` 把它绑定到 Spring 事务；`@Transactional` 失效通常不是数据库问题。

要能回答：

- `SqlSessionTemplate` 和 `SqlSessionDaoSupport` 的区别？
- 为什么同一个类里方法自调用会让 `@Transactional` 失效？
- 只读事务有什么用？能提升性能吗？
- 事务回滚默认对哪些异常生效？`checked` 异常怎么办？
- 事务里调用远程接口有什么风险？

关联：[[Spring事务]]、[[事务失效]]

笔记：

- `SqlSessionTemplate` 是线程安全的，内部把 `SqlSession` 绑定到 Spring 事务/线程；`SqlSessionDaoSupport` 是给 DAO 基类注入 `SqlSessionTemplate` 的辅助类。业务代码不要自己 open/close `SqlSession`。
- 同类自调用 `this.method()` 不经过 Spring 代理，`@Transactional` 不生效；private/final 方法、`@Async` 线程也一样。改用 `TransactionTemplate` 或拆到另一个 Bean。
- 只读事务是提示：可能跳过脏检查/flush、设置连接 read-only，优化有限；不能当「禁止写」的保证。
- 默认只对 `RuntimeException`/`Error` 回滚；checked 异常要 `rollbackFor = Exception.class`。catch 后不抛也不会回滚。
- 事务里调远程接口：远程超时/失败会让本地事务长时间持锁/占连接；远程成功、本地回滚则数据不一致。远程调用放事务外，必须一致就用 Outbox/补偿。

## 6. 批处理与大数据量

**一句话**：批处理减少网络往返，但一次提交太大也会撑爆内存和锁；要分批、控制事务大小、必要时用流式查询。

要能回答：

- JDBC `addBatch`/`executeBatch` 和 MyBatis `foreach` 拼接的区别？
- 批量插入为什么可能很慢？`rewriteBatchedStatements` 解决什么？
- 流式查询/游标查询适合什么场景？和分页的区别？
- 大事务有什么危害？怎么拆分？

笔记：

- JDBC `addBatch/executeBatch` 把多条语句攒起来一次发送，减少网络往返；MyBatis `foreach` 拼成一条大 SQL（多 values 或 `IN`），解析/包大小受限。
- 批量插入慢的常见原因：每条 autocommit、网络往返、索引/唯一约束逐条检查。`rewriteBatchedStatements=true` 让 MySQL 驱动把 batch insert 改写成多 values 一条语句。
- 流式/游标查询适合「读大结果集但不想全加载内存」，保持连接/事务打开逐行处理；分页适合页面展示，但深分页 offset 大有性能问题。导出大表用游标 + 分批写文件。
- 大事务危害：锁持有久、undo/redo 大、回滚慢、连接占用久、主从延迟。拆成小批（每批独立事务）+ 幂等 + 断点续跑；不能简单按 1000 条切，要考虑业务原子性。
- 批处理失败要能定位到批/行；部分成功要有补偿或重跑机制，不能整批重来造成重复。

## 7. SQL 注入与安全

**一句话**：预编译参数化查询是防注入的根本；拼接 SQL、动态表名/排序字段是例外，必须白名单校验。

要能回答：

- 预编译为什么能防 SQL 注入？它和转义的区别？
- `ORDER BY`、表名、列名为什么不能用 `#{}`？怎么防？
- 最小权限数据库账号能降低什么风险？
- 慢查询、全表扫描和注入攻击之间有什么关联？

笔记：

- 预编译把 SQL 结构和参数分开：SQL 先编译成计划，参数只作为值绑定，不能改变语法结构；转义是「把特殊字符替换掉」，规则复杂、容易漏，不能作为主防线。
- `ORDER BY`、表名、列名不能参数化（占位符只能替换值），只能字符串拼接；必须用白名单映射（前端传 `sort=name` → 映射到 `name` 列），不能直接拼用户输入。
- 最小权限账号：应用账号只给需要的库/表/CRUD，禁止 DDL/文件/多库；即使注入成功，能做的事也有限。
- 慢查询与注入的关联：注入常通过拼接条件实现，攻击者可用 `OR 1=1`、子查询、`SLEEP()` 制造全表扫描/拒绝服务；监控慢查询和异常 SQL 模式能发现部分攻击。
- 防注入还要：输入校验（类型/长度/枚举）、错误信息不回显 SQL、ORM 参数绑定、代码扫描（SAST）检查字符串拼接 SQL。

## 常见对比题

- JDBC vs MyBatis vs JPA
- `#{}` vs `${}`
- 一级缓存 vs 二级缓存
- 逻辑删除 vs 物理删除
- 悲观锁 vs 乐观锁
- 分页查询 vs 流式查询

## 我现在到哪

| 块 | 现状 | 依据 |
| --- | --- | --- |
| MyBatis-Plus 通用 CRUD、条件构造器 | 项目里大量使用 | [[MyBatis-Plus]] |
| 分页、租户、软删除、乐观锁插件 | 项目里落地过 | [[插件链]]、[[租户插件落地]] |
| 事务与 `SqlSession` 绑定 | 项目里排查过事务失效 | [[事务失效]] |
| JPA/Hibernate、二级缓存、流式查询 | 学习和面试准备，未在项目落地 | 本页 |

## 边界

- 本页是索引，不是教材：每个问题只留一行，展开写到独立笔记。
- 项目以 MyBatis-Plus 为主，没有 JPA/Hibernate 实战。
- 没做过分库分表、读写分离和多数据源事务。
