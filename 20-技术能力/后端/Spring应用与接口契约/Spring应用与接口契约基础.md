---
type: 基础能力
通用技能: Spring应用与接口契约
域: 后端
证据: 学习中
---

# Spring 应用与接口契约基础

通用技能：[[Spring应用与接口契约]] · 定位：基础知识挂载页

**一句话**：Spring 应用与接口契约基础题的分类索引。这里回答「应该会什么」，不冒充「我做过什么」；做过的事仍记在实践卡。

## 怎么用

- 自测：看每一块的「要能回答」，能用自己的话讲清楚才算过。
- 挂笔记：新写一篇八股文，在对应块的「笔记」后加 `笔记名`，笔记里链回本页。
- 分边界：原理和机制放这里；具体故障、排查过程、修复方案放场景/实践卡。

## 1. IoC 与依赖注入

**一句话**：IoC 把对象创建和依赖装配交给容器；DI 是它的实现方式，Spring 用构造器、Setter、字段三种注入。

要能回答：

- IoC 和 DI 的区别？为什么推荐构造器注入？
- Bean 的作用域有哪些？单例 Bean 为什么要注意线程安全？
- Bean 的生命周期？`@PostConstruct`、`InitializingBean`、`BeanPostProcessor` 的执行顺序？
- 循环依赖怎么产生？Spring 怎么解决？为什么构造器循环依赖解决不了？
- `@Component`、`@Service`、`@Repository` 的区别？

**笔记**：

- IoC 是「控制权反转」：对象的创建、依赖装配、生命周期由容器管，不由业务代码 `new`。DI 是实现方式，构造器注入让依赖显式、可 `final`、易测试；字段注入隐藏依赖，单元测试要反射或起容器。构造器注入的代价是依赖多时构造器长，但这会暴露「这个类职责太多」。
- 作用域：`singleton`（默认，容器内一个实例）、`prototype`（每次获取新实例）、`request`/`session`/`application`/`websocket`（Web 环境）。单例 Bean 会被多线程共享，不能把请求级状态放在字段里；无状态 Service 安全，有状态要加锁或用 ThreadLocal/局部变量。
- 生命周期：实例化 → 属性填充 → Aware 回调 → `BeanPostProcessor.postProcessBeforeInitialization` → `@PostConstruct` / `afterPropertiesSet` / `init-method` → `BeanPostProcessor.postProcessAfterInitialization`（AOP 代理通常在这里生成）→ 使用 → `@PreDestroy` / `destroy`。
- 循环依赖：A 依赖 B、B 依赖 A。单例的字段/Setter 注入靠三级缓存提前暴露「早期引用」解决；构造器注入在对象还没造出来时就要对方，无法提前暴露，所以解决不了。`prototype` 也不支持循环依赖。正解是拆职责、用 `@Lazy` 延迟一个依赖，或改成事件/接口回调。
- `@Component`、`@Service`、`@Repository` 本质都是 `@Component`，区别是语义；`@Repository` 额外把持久层异常翻译成 Spring 的 `DataAccessException`。不要靠注解名字做逻辑判断。

## 2. AOP 与代理

**一句话**：AOP 把横切逻辑（事务、日志、权限）从业务代码里抽出来；Spring 用 JDK 动态代理或 CGLIB 生成代理对象。

要能回答：

- AOP 的切点、通知、切面分别是什么？五种通知的执行顺序？
- JDK 动态代理和 CGLIB 的区别？Spring Boot 默认用哪个？
- 为什么同类自调用会让 AOP 失效？
- `@Transactional`、`@Async`、自定义注解切面分别靠什么代理？
- AOP 能拦截 private 方法吗？为什么？

关联：[[Spring事务]]、[[事务失效]]

**笔记**：

- 切点（Pointcut）定义「拦哪些方法」，通知（Advice）定义「拦到后做什么」，切面（Aspect）是切点 + 通知的组合。`@Around` 包住整个调用，`@Before` 在方法前，`@After` 在 finally，`@AfterReturning` 正常返回后，`@AfterThrowing` 异常后；多个切面用 `@Order` 控制顺序。
- JDK 动态代理要求目标类实现接口，代理对象实现同一接口；CGLIB 生成目标类的子类，不能代理 `final` 类/`final` 方法。Spring Boot 默认 `proxyTargetClass=true`，优先 CGLIB；接口注入时仍可能用 JDK 代理。
- 同类自调用 `this.method()` 不走代理对象，直接调目标对象，所以事务/异步/自定义切面都不生效。解决：拆到另一个 Bean、注入自己（`@Lazy` 避免循环依赖）、`AopContext.currentProxy()`（需 `exposeProxy=true`）。
- `@Transactional`、`@Async`、自定义注解切面都靠代理；代理没生成（private/final/同类调用/对象不是 Spring 管理的 Bean）就不生效。
- private 方法不能被 JDK 代理（接口没有）也不能被 CGLIB 覆盖（子类不能重写 private），所以拦截不到；需要事务就改成 public 入口或 `TransactionTemplate`。

## 3. Spring MVC 请求流程

**一句话**：请求先到 `DispatcherServlet`，经 `HandlerMapping` 找到处理器，`HandlerAdapter` 调用，参数解析、返回值处理、消息转换依次完成。

要能回答：

- `DispatcherServlet` 的职责？它和 `Filter`、`Interceptor` 的执行顺序？
- `HandlerMapping`、`HandlerAdapter`、`HandlerExceptionResolver` 分别解决什么？
- `@RequestParam`、`@PathVariable`、`@RequestBody`、`@ModelAttribute` 的绑定规则？
- `HttpMessageConverter` 什么时候生效？JSON 序列化在哪一步？
- `Filter` 和 `Interceptor` 的区别？各自能拿到什么？

关联：[[Spring MVC]]、[[Spring Boot]]

**笔记**：

- `DispatcherServlet` 是前端控制器：收请求、找 handler、调 adapter、处理返回值/异常、渲染响应。执行顺序：`Filter`（Servlet 容器）→ `DispatcherServlet` → `HandlerMapping` → `Interceptor.preHandle` → `HandlerAdapter` → 参数解析 → 方法 → 返回值处理 → `Interceptor.postHandle` → 视图/消息转换 → `Interceptor.afterCompletion`。
- `HandlerMapping` 把 URL 映射到 handler（`@RequestMapping`）；`HandlerAdapter` 负责调用 handler（参数解析、返回值处理）；`HandlerExceptionResolver` 把异常转成响应。404 找不到 handler 时可能由容器/`BasicErrorController` 处理，不一定进 `@ControllerAdvice`。
- `@RequestParam` 取 query/form 参数；`@PathVariable` 取 URI 模板变量；`@RequestBody` 用 `HttpMessageConverter` 读 body（JSON 用 Jackson）；`@ModelAttribute` 把 query/form 绑定到对象；`@RequestPart` 处理 multipart。
- `HttpMessageConverter` 在 `@RequestBody` 读入和 `@ResponseBody` 写出时生效；JSON 序列化在 converter 里，不在 Controller 里。`@RestController` = `@Controller` + `@ResponseBody`。
- `Filter` 属于 Servlet 规范，能拿 `HttpServletRequest/Response`，在 Spring 之外；`Interceptor` 属于 Spring MVC，能拿 handler、`ModelAndView`，拿不到原始 body（body 已被读）。AOP 更内层，拦 Bean 方法。

## 4. 参数校验

**一句话**：JSR-303/Jakarta Validation 用注解声明约束，`@Valid`/`@Validated` 触发校验；嵌套对象和分组校验是常见坑。

要能回答：

- `@Valid` 和 `@Validated` 的区别？
- `@NotNull`、`@NotEmpty`、`@NotBlank` 分别管什么？
- 嵌套对象校验为什么要加 `@Valid`？
- 分组校验怎么用？什么时候需要自定义校验注解？
- 校验失败应该返回 400 还是统一 200 + 业务码？

关联：[[参数校验]]

**笔记**：

- `@Valid` 是 JSR-303 标准，标在参数/字段上触发级联校验；`@Validated` 是 Spring 的扩展，支持分组、方法级校验，标在类上可让方法参数校验生效。两者都能触发，但分组/方法校验用 `@Validated`。
- `@NotNull` 只判非 null；`@NotEmpty` 判非 null 且长度/集合大小 >0；`@NotBlank` 判字符串非 null 且 `trim()` 后长度 >0。字符串用 `@NotBlank`，集合用 `@NotEmpty`，对象用 `@NotNull`。
- 嵌套对象默认不级联，字段上要再加 `@Valid`；否则外层通过、内层约束不执行。集合元素校验用 `List<@Valid Item>` 或 `@Valid` + 容器元素约束。
- 分组用接口标记（`Create.class`、`Update.class`），`@Validated(Create.class)` 只校验该组；自定义校验实现 `ConstraintValidator`，跨字段校验用类级注解。
- 校验失败返回 400 还是 200+code 是契约选择：项目统一 HTTP 200 + body code，调用方只看 code；对外 REST/网关可能更希望 400。关键是全站一致，并在文档里写清。

## 5. 异常与统一响应

**一句话**：`@ControllerAdvice` + `@ExceptionHandler` 把异常转成统一响应；HTTP 状态码和 body 里的业务码是两套语义，要明确约定。

要能回答：

- `@ControllerAdvice` 能捕获哪些异常？404 为什么有时捕获不到？
- `@ExceptionHandler` 的匹配优先级？
- 统一响应体应该包含哪些字段？业务码怎么设计？
- HTTP 200 + body code 和 HTTP 语义状态码各有什么利弊？
- 异常堆栈要不要返回给前端？日志怎么记？

关联：[[全局异常与统一响应]]、[[全局异常落地]]

**笔记**：

- `@ControllerAdvice` 捕获 Controller 方法抛出的异常；404 是「没找到 handler」，在进入 Controller 前就由容器/`BasicErrorController` 处理，所以 `@ExceptionHandler(Exception.class)` 不一定能抓到。要统一 404 就配置 `spring.mvc.throw-exception-if-no-handler-found` 或自定义 `ErrorController`。
- `@ExceptionHandler` 按「最具体优先」匹配：先找异常类型完全匹配，再找父类；同一异常有多个 handler 会报歧义。全局 advice 和 Controller 内 handler 同时存在时，Controller 内优先。
- 统一响应体至少包含 `code`、`message`、`data`、`traceId`；`code` 是稳定业务码，不随文案变；`message` 是给人看的，不能当程序判断依据。业务码分段（模块+错误类型），并维护唯一性测试。
- HTTP 200 + body code：网关/前端统一处理，避免代理把 4xx/5xx 当故障；代价是监控/日志按状态码统计会失真。HTTP 语义状态码：符合 REST，监控直观；代价是业务码和 HTTP 码要映射两套。项目选前者，就要在网关/监控里按 body code 补统计。
- 堆栈不返回前端，只记服务端日志；日志带 traceId、用户/租户、参数摘要，敏感字段脱敏。前端拿到的 `message` 要可执行，不能是 `NullPointerException`。

## 6. REST 与 HTTP 契约

**一句话**：REST 用资源和方法表达操作；GET/POST/PUT/PATCH/DELETE 的语义、幂等性和状态码是接口契约的一部分。

要能回答：

- GET、POST、PUT、PATCH、DELETE 的语义和幂等性？
- 201、204、400、401、403、404、409、422、500 分别什么时候用？
- 幂等键应该放在哪？重复请求怎么处理？
- 版本化接口有哪几种做法？各自代价？
- 分页、排序、过滤参数怎么设计才稳定？

**笔记**：

- GET 安全且幂等，只读；POST 非幂等，创建/提交；PUT 幂等，整体替换；PATCH 部分更新，通常非幂等（取决于实现）；DELETE 幂等，重复删同一资源结果一致（第二次可能 404，但状态不变）。
- 201 创建成功（Location 指向新资源）；204 成功无 body；400 参数/语义错误；401 未认证；403 已认证无权限；404 资源不存在；409 冲突（唯一键/状态冲突）；422 语义校验失败；500 服务端异常。项目统一 200+code 时，HTTP 码只表达传输层，业务码表达结果，要在契约里写清。
- 幂等键放请求头（`Idempotency-Key`）或 body 的业务唯一号；服务端用唯一索引/去重表占位，重复请求返回第一次结果或 409。不能只靠「先查后写」，并发下会同时通过。
- 版本化：URI 版本（`/v1/`）直观、缓存友好，但 URL 变；Header 版本（`Accept: application/vnd.x.v1+json`）URL 稳定，但调试/网关配置复杂；媒体类型/参数版本类似。小项目 URI 版本够用，别同时上多套。
- 分页参数用 `page`/`pageSize` 或 `cursor`/`limit`；排序字段要白名单，避免 SQL 注入和任意索引扫描；过滤参数用明确字段，不要传原始 SQL/JSON。分页要有稳定排序键，否则翻页会重复/漏行。

## 7. 国际化与配置

**一句话**：`MessageSource` 按 Locale 取文案，Locale 从请求头或会话解析；配置外置用 `@ConfigurationProperties` 绑定。

要能回答：

- `MessageSource` 怎么加载资源文件？找不到 key 时怎么办？
- `LocaleResolver` 有哪些实现？怎么和用户设置联动？
- `@ConfigurationProperties` 和 `@Value` 的区别？
- 配置的优先级顺序？本地配置、环境变量、命令行谁覆盖谁？
- 敏感配置怎么管理？

关联：[[Spring Boot]]

**笔记**：

- `MessageSource` 按 `basename` 加载 `messages.properties`/`messages_zh_CN.properties`，用 `MessageSource.getMessage(code, args, locale)` 取文案；找不到 key 默认抛 `NoSuchMessageException`，可配 `useCodeAsDefaultMessage=true` 或默认文案兜底。
- `LocaleResolver`：`AcceptHeaderLocaleResolver` 看 `Accept-Language`；`SessionLocaleResolver` 存会话；`CookieLocaleResolver` 存 cookie；`FixedLocaleResolver` 固定。用户设置优先于请求头时，先读用户偏好再解析。
- `@ConfigurationProperties` 批量绑定前缀下的配置，支持类型转换、校验、嵌套对象、relaxed binding；`@Value` 只取单个 key，支持 SpEL，但类型转换/默认值/重构都不如前者。配置多时用 `@ConfigurationProperties`。
- Spring Boot 优先级大致：命令行参数 > `SPRING_APPLICATION_JSON` > Servlet 参数 > JNDI > 系统属性 > 环境变量 > `application-{profile}.properties/yml` > `application.properties/yml`。后加载的覆盖先加载的；测试里 `@TestPropertySource` 又高于默认文件。
- 敏感配置走环境变量/密钥管理，不进 git；`@ConfigurationProperties` 里不要 `toString()` 打印密码；配置中心要有权限和审计。

## 常见对比题

- IoC vs DI
- BeanFactory vs ApplicationContext
- Filter vs Interceptor vs AOP
- `@Valid` vs `@Validated`
- HTTP 状态码 vs 业务码
- PUT vs PATCH
- `@ConfigurationProperties` vs `@Value`

## 我现在到哪

| 块 | 现状 | 依据 |
| --- | --- | --- |
| Spring MVC 请求链、参数绑定 | 项目里落地过 | [[Spring MVC]] |
| 参数校验、统一异常、统一响应 | 项目里落地过 | [[参数校验]]、[[全局异常落地]] |
| AOP、事务代理 | 项目里排查过失效场景 | [[事务失效]] |
| WebFlux、响应式编程 | 未接触 | 本页 |

## 边界

- 本页是索引，不是教材：每个问题只留一行，展开写到独立笔记。
- 项目以 Spring MVC 为主，没有 WebFlux/响应式实战。
- 接口契约以项目约定为准，不等于 REST 规范的全部。
