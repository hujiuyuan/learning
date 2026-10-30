---
type: 方法
技能点: JUnit与Testcontainers
域: 测试与质量
证据: 实战
---

# Mock 与真实容器的取舍

技能点：[[JUnit与Testcontainers]] · 通用技能：[[测试与质量]]

**一句话**：选替身还是真容器，不看「快不快」，看「这条测试要证明的行为，依赖不依赖真实框架」；替身只能证明「我调了它」，证明不了「它真的这么干」。

路径约定：以下 `路径:行号` 相对 `smart-server-wms3/src/test/java/com/track/wms/` 与 `smart-server-wms3/pom.xml`。

## 方法总纲

1. **先写「这条测试声称证明什么」**：分支/状态机、一层框架契约、真实 SQL/事务、整条用户路径。一句话写不出，就先别写测试。
2. **按依赖选切面**：只依赖返回值和调用次数的 → Mockito；依赖 SQL 方言/事务/插件/时区 → 真库；依赖 MVC 序列化/错误处理 → `@WebMvcTest`；依赖认证链路 + 多存储 → `@SpringBootTest(RANDOM_PORT)` + 容器。
3. **检查替身有没有替掉被测行为**：mock 掉 DAO 还断言「软删过滤生效」，等于自己实现一遍再自己通过；mock 掉的就是要证明的规则时，必须换真容器。
4. **检查框架行为是否被切片关掉**：`@WebMvcTest(addFilters = false)` 关掉 Security，认证行为就证明不了；`@MybatisPlusTest` 不导插件配置，租户/软删插件就不生效。
5. **检查默认构建会不会跑**：`*IT.java` 不在 surefire 默认匹配、`disabledWithoutDocker = true` 无 Docker 整类 skip、`*CloudE2eTest` 被显式 exclude——三种「绿」都可能是没跑。
6. **断言写业务后果**：断完整集合、断 body code，不断 SQL 文本；正反成对（该回来的回来、不该回来的不回）。
7. **测试类注释写一句「为什么用这个替身/容器」**：半年后的人靠这句话判断测试还有没有效。

## 决策表

| 要证明的行为 | 该用的手段 | 不该用的手段 | 原因 |
| --- | --- | --- | --- |
| 状态机分支、幂等判断 | Mockito | 起容器 | 分支不依赖外部，容器只增加慢和 flaky |
| 软删过滤、租户插件、SQL 改写 | `@MybatisPlusTest` + 真 MySQL | Mock DAO、H2 | Mock 连 SQL 都没发；H2 方言/插件行为不同 |
| 会话时区、SQL 函数、默认值 | 真库 + `connection-init-sql` | 单测 + 推算 | 时区行为在连接初始化时才体现 |
| 404/405 的 body code | `@WebMvcTest` + `MockMvc` | 手写 Controller 单测 | 要证明的是 `ControllerAdvice` 链路 |
| 认证 + 权限 + 多存储 | `@SpringBootTest` + MySQL/Redis/localstack | 单层切片 | 跨层契约只有全栈能证明 |
| 浏览器可点 | Playwright | HTTP 测试 | HTTP 过了不代表页面能点 |

## 判断顺序

1. **问「失败时我最想知道什么」**：想知道是 SQL 写错还是逻辑错 → 真库；只想锁定分支 → Mockito。
2. **问「mock 掉的是不是被测对象依赖的框架行为」**：是（事务、插件、拦截器、序列化）→ 不能用 mock。
3. **问「这条测试在 CI 默认命令里跑吗」**：不跑就改命名、接 failsafe、或明确标注「未跑」，不能算通过。
4. **问「断言能不能区分对错实现」**：只断 `contains`、只断 SQL 文本、只断注解存在，都不算。
5. **最后问「代价能不能接受」**：容器启动慢 → 只给必须真库的类起，纯逻辑测试保持无容器。

## 反例

- **Mock 掉 DAO 断言软删**：SQL 根本没发出去，过滤逻辑没被执行，测试只证明 mock 被调用。
- **用 H2 跑 MySQL 业务**：方言、`ON DUPLICATE KEY`、隔离级别、JSON 函数不一致，「H2 绿、上线挂」。
- **只断 SQL 文本**：条件写了但值错、过度过滤照样绿（`FilesSoftDeleteItTest.java:41-44` 作者自己标注了这个局限）。
- **反射断言 `@Transactional`**：只证明注解存在，证明不了代理生效、事务真回滚（`WarehouseReserveLocationTest.java:363-376`、`WarehouseUploadPhotoTest.java:265-278`）。
- **`@WebMvcTest(addFilters = false)` 断认证**：Security 过滤器没参与，认证行为恒过（`CoreControllerAdviceNotFoundTest.java:28-31`）。
- **无 Docker 的绿灯**：`disabledWithoutDocker = true` 整类 skip（`FilesSoftDeleteItTest.java:51`、`AuthPermissionE2eTest.java:47`）。
- **`*IT.java` 以为会跑**：surefire 只匹配 `*Test`，`TenantIsolationIT` 不在 `mvn test` 里（`pom.xml:345-355`，无 failsafe）。
- **容器起了但数据没隔离**：用例互相污染，顺序一变就红；每个类独立 `databaseName`、每个用例自造行。

## 证据

- [[单测与集成测试]] — 项目里的切面选择、测试数据隔离、断言规矩
- [[JUnit与Testcontainers]] — 工具用法与配置细节
- `FilesSoftDeleteItTest.java:48-53,56-72,103-120,142-147` — 切片 + `Replace.NONE` + 容器注入 + 正反成对 + 完整集合断言
- `TenantIsolationIT.java:74-77,103-140` — 租户插件必须真库
- `SessionTzSafeItTest.java:83-87,110-125` — 会话时区只能真库证明
- `AuthPermissionE2eTest.java:47,80-83` — 三容器全栈 + 无 Docker skip
- `TaskFlowEngineTest.java:36-54,70-79` — 纯分支用 Mockito
- `CoreControllerAdviceNotFoundTest.java:28-31,61-65` — MVC 切片断 body code
- `ResultCodeUniquenessTest.java:36-56` — 元测试：遍历枚举把撞号变成红灯
- `pom.xml:345-355,351-353` — surefire 匹配与 `*CloudE2eTest` 排除

## 边界

- 没做过容器复用/并行、PostgreSQL 容器、真实事务回滚验证；jacoco 只出报告无阈值（`pom.xml:356-370`）。
- 56 个 `*CloudE2eTest` 默认构建不跑，云链路没有被 CI 覆盖。
- 没有测试分层比例的数据（单测/切片/集成各多少），测试金字塔是原则不是本项目实测。
