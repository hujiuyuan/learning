---
type: 技能点
域: 测试与质量
项目: [smart WMS]
证据: 实战
---

# JUnit与Testcontainers

所属通用技能：[[测试与质量]]

**一句话**：JUnit 决定测试怎么写，切面决定测试装多少，Testcontainers 决定依赖真不真；三者组合的目标是「让这条测试证明它声称证明的那一层」。

## 方法总纲

1. **先选切面**：纯逻辑用 Mockito；MVC 契约用 `@WebMvcTest`；DAO/插件用 `@MybatisPlusTest`；全栈用 `@SpringBootTest(RANDOM_PORT)`。
2. **容器只起需要的**：MySQL 用 `MySQLContainer`，Redis 用 `GenericContainer`，S3 用 localstack；静态 `@Container` + `@Testcontainers(disabledWithoutDocker = true)`。
3. **把容器接进 Spring**：`ApplicationContextInitializer` 里把 JDBC URL/账号写进 `MapPropertySource` 并 `addFirst`；配合 `@AutoConfigureTestDatabase(replace = NONE)`。
4. **数据自己造、自己收**：DAO `save` 或 `init.sql`；断言完整集合，不用 `contains` 掩盖多算/少算。
5. **注解守不住行为**：反射只能证明注解存在，不能证明 AOP 代理、事务回滚、拦截器生效；这类地方要么起真容器，要么明确写「未验证」。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| `FilesSoftDeleteItTest` | 集成（@MybatisPlusTest + MySQL） | smart WMS | 2026-08 | [[单测与集成测试]] |
| `SessionTzSafeItTest` | 集成（会话时区 + 真库） | smart WMS | 2026-07 | [[单测与集成测试]] |
| `TenantIsolationIT` | 集成（租户插件 + 真库） | smart WMS | 2026-07 | [[单测与集成测试]] |
| `TaskFlowEngineTest` | 单测（Mockito） | smart WMS | 2026-07 | [[单测与集成测试]] |
| `AuthPermissionE2eTest` | 全栈（HTTP + 3 容器） | smart WMS | 2026-07 | [[单测与集成测试]] |

## 我会的部分

- **`@MybatisPlusTest` + 容器**：`FilesSoftDeleteItTest.java:48-53` 同时开切片、`Replace.NONE`、导入 `MybatisPlusConfig` 和目标 DAO；`FilesSoftDeleteItTest.java:56-72` 把容器地址注入环境。
- **会话级 SQL**：`SessionTzSafeItTest.java:83-87` 用 `hikari.connection-init-sql` 在每个连接上 `SET time_zone`；`SessionTzSafeItTest.java:110-125` 用夸张偏移验证 handler 免疫会话时区、默认值跟随会话时区。
- **三容器全栈**：`AuthPermissionE2eTest.java:80-83` 起 MySQL、Redis、localstack；`AuthPermissionE2eTest.java:91-104` 跑 `init.sql` 并建 S3 bucket。
- **Mockito**：`TaskFlowEngineTest.java:36-54` 用 `@ExtendWith(MockitoExtension.class)` + `@Mock` + `lenient()` 固定协作方；`TaskFlowEngineTest.java:70-79` 用 `when/verify` 断言分支。
- **正反成对**：`FilesSoftDeleteItTest.java:103-120` 一条测试里同时断「活着回来」「删掉不回」「恰好剩一条」；`FilesSoftDeleteItTest.java:142-147` 用完整集合 `equals` 抓多算和少算。
- **元测试**：`ResultCodeUniquenessTest.java:36-56` 遍历枚举，把业务码撞号变成红灯。

## 选型与取舍

### 为什么用 Testcontainers 真容器，不用 H2/Mock

| 方案 | 能证明什么 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| Mockito 单测 | 分支、协作方调用、异常路径 | 证明不了 SQL、事务、插件、序列化 | 纯逻辑层 |
| H2/内存库 | 部分 SQL、快速 | 方言/约束/函数/隔离级别与 MySQL 不一致，容易「H2 过、MySQL 挂」 | 未作为集成库 |
| Testcontainers 真 MySQL/Redis/S3 | 真实 SQL、事务、插件、时区、对象存储契约 | Docker 启动慢、占资源、无 Docker 就 skip、可能 flaky | DAO/全栈集成 |
| 切片测试（`@WebMvcTest`/`@MybatisPlusTest`） | 单层与真实框架的交互 | 不证明跨层契约 | 按层选 |

选真容器是因为项目踩过「SQL 文本对、真库行为不对」的坑：软删除过滤、租户插件、会话时区、事务回滚都只能在真库证明。H2 的方言和 MySQL 不同，Mock 连 SQL 都没发出去，二者都不能替代。

### 为什么还保留 Mockito 和切片

全栈测试慢、依赖多、失败定位差；能用 Mockito 证明的分支不要起容器，能用 `@WebMvcTest` 证明的 MVC 契约不要起全栈。测试金字塔不是教条，是「每层只证明它能证明的事」：单测证分支，切片证一层契约，容器证真实 SQL/事务，E2E 证用户路径。

### 代价与反悔条件

- 无 Docker 时 `disabledWithoutDocker=true` 整类 skip，绿灯可能是没跑；`*IT.java` 不在 surefire 默认匹配里，`mvn test` 不会跑；56 个 `*CloudE2eTest` 被显式排除。
- 容器启动/数据初始化让反馈变慢；容器复用、并行、测试库模板都能优化，但会增加隔离复杂度。
- 如果集成测试成为 CI 瓶颈 → 用 Testcontainers Cloud/复用容器/只跑受影响模块；如果团队没有 Docker → H2 只用于单测，集成测试明确标「未跑」，不能把 skip 当通过。

## 边界

- **无 Docker 就跳过**：`@Testcontainers(disabledWithoutDocker = true)`（`FilesSoftDeleteItTest.java:51`、`AuthPermissionE2eTest.java:47`）让集成测试在没 Docker 时整类 skip；绿灯可能是跳过，不是通过。
- **`*IT.java` 默认不跑**：`pom.xml:345-355` 是 surefire 配置，全文没有 failsafe；`TenantIsolationIT.java` 不在 `mvn test` 的默认匹配里，`FilesSoftDeleteItTest.java` 因为以 `Test` 结尾才会跑。
- **有 56 个云 E2E 被排除**：surefire 显式 exclude `**/*CloudE2eTest.java`（`pom.xml:351-353`），默认构建不覆盖这条链路。
- **反射守注解只是下限**：`WarehouseReserveLocationTest.java:363-376` 和 `WarehouseUploadPhotoTest.java:265-278` 自己注明「Mockito 无法驱动真实事务回滚，退而求其次做反射断言」；反射证明不了代理是否生效、事务是否真的回滚。
- **没做过**：容器复用/并行、PostgreSQL 容器、真实事务回滚验证；jacoco 只出报告、没有阈值（`pom.xml:356-370`）。

## 相关技能

[[Playwright]]、[[Spring Boot]]、[[MyBatis-Plus]]

## 用在哪些工程能力

数据访问与 ORM、多租户隔离、接口契约、时区与时间序列化、认证与授权。
