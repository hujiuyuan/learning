---
type: 通用技能
域: 后端
证据: 实战/设计
---

# Spring应用与接口契约

**一句话**：一个 HTTP 接口的契约由五件事定死：路径与方法、参数怎么绑、校验在哪层、成功和失败响应长什么样、异常从哪出去；框架只给机制，契约是项目自己定的。

基础知识自测：[[Spring应用与接口契约基础]]

> 四层读法：理论 [[Spring应用与接口契约基础]]｜实践 本页「我用它干过什么」｜问题 [[全局异常与统一响应]]、[[参数校验]]｜方案 [[smart WMS]]。总入口 [[四层读法]]。

## 一、理论：一条请求在 Spring 应用里的固定路线

1. **自动配置**：Boot 按 classpath 上的 starter 装配 Bean；启动类负责组件扫描、排除不需要的自动配置、开总开关。
2. **路由**：DispatcherServlet 让 HandlerMapping 按 path + method 找方法；路径不存在抛 `NoHandlerFoundException`，方法不匹配抛 `HttpRequestMethodNotSupportedException`。
3. **参数绑定**：`@RequestBody` 走 HttpMessageConverter；query/form 走 WebDataBinder；`@PathVariable`、`@RequestParam`、`MultipartFile` 各有解析器。
4. **校验**：`@Valid`/`@Validated` 触发 Bean Validation，失败按参数位置抛不同异常，见 [[参数校验]]。
5. **返回**：返回对象由 HttpMessageConverter 序列化；`ResponseBodyAdvice` 可在写回前统一包装。
6. **异常出口**：`@RestControllerAdvice` 按异常类型选 handler；没有匹配就落到 `Exception.class` 兜底。
7. **两层契约**：HTTP 层（status/header/content-type）和 body 层（code/message/data）。两层可以一致，也可以故意不一致；不一致就是取舍，必须写清楚。

## 二、实际使用：smart WMS 的接口契约

- **应用**：Spring Boot 3.3.13 + Java 21（`smart-server-wms3/pom.xml:10`、`:22`），启动类 `WmsTrackApplication.java:19`。
- **路由**：39 个 `@RestController`，统一 `/api/v1/{模块}` 前缀（`CompanyController.java:41-42`、`LoginLogController.java:29-30`）。
- **参数绑定**：`@Valid @RequestBody`（`CompanyController.java:53`）、query DTO（`WarehouseController.java:82`）、`@PathVariable`（`WarehouseController.java:428`）、multipart（`WarehouseController.java:407`）。
- **校验**：DTO 的 `message` 直接写 i18n key（`CompanyCreateReq.java:17`），由全局 handler 再翻译。
- **统一响应**：`Result<T>`（`Result.java:22-50`）；未包装的返回值由 `CoreControllerAdvice.beforeBodyWrite` 兜底包成 `Result.success`（`CoreControllerAdvice.java:201-245`）。
- **异常**：12 个 handler 在 `CoreControllerAdvice.java`；错误码枚举 `ResultCode.java`；业务异常同时带数字码和 messageCode（`BusinessException.java:25-37`）。
- **HTTP 状态**：404/405/参数错误/业务错误都返回 HTTP 200，body 的 `code` 区分（`CoreControllerAdvice.java:72-97`、`:119-160`）。这是现状取舍，不是 REST 最佳实践。
- **接口文档**：Knife4j + springdoc 默认全关，靠 `KNIFE4J_ENABLE` 同开同关（`application.yml:133-162`）。

## 三、归纳：接口契约检查清单

1. **路径与方法**：前端调的 path/method 和 controller 注解一致吗？前缀是否叠了 `server.servlet.context-path`。
2. **参数载体**：body、query、path、multipart 分别对应哪种绑定，必填项谁兜。
3. **校验位置**：DTO 注解还是 service 业务规则；`@Valid` 有没有漏。
4. **校验失败响应**：返回哪个 code、哪条 message、带不带字段名。
5. **成功响应**：统一 `Result` 还是裸对象；分页是不是同一形态。
6. **失败响应**：code 来自 `ResultCode` 还是手写字符串。
7. **HTTP 状态**：统一 200 还是真状态码；网关和监控是否按状态码告警。
8. **异常出口**：controller 里有没有 `catch` 把异常压平。
9. **i18n**：messageCode 在四个语言文件里都有吗；缺 key 时降级成什么。
10. **测试**：404、405、参数错误、业务错误、未知异常各有断言吗。

### 三条红线

- 不要在 controller 手写 `Result.error(String)`：code 会固定成 500，文案绕过 i18n。
- 不要把内部异常文本直接回给前端：只回 messageCode 翻译后的文案，细节进日志。
- 不要照抄「HTTP 200 + body code」到新项目：这是兼容老系统的取舍，不是通用最佳实践。

## 四、回到理论：为什么这些规则成立

- `ResponseBodyAdvice` 是出参统一机制，不是契约本身；它能包 `Result`，也会漏掉 String、Resource、actuator，代码里必须逐类放行。
- HTTP 200 + body code 的本质是把状态语义从协议层搬到应用层：前端只需一套拦截器，代价是网关、监控、重试、缓存看到的永远是 200。
- 参数校验抛哪种异常取决于参数位置和是否走 AOP 代理；handler 分得细，才能给出不同 message。
- 前端消息用 messageCode 而不是字符串，是因为响应语言由请求决定（`?lang=`），文案不能写死在业务代码里。
- 换到任何 MVC 框架，这五段（路由、绑定、校验、序列化、异常）都存在，只是名字不同。

## 五、边界

- 只做过 Servlet MVC；没做过 WebFlux、函数式端点、内容协商多视图。
- 没做过声明式 HTTP 客户端：仓里零 `@HttpExchange`、零 `RestClient`/`WebClient`，服务间调用不在本页。
- 没做过 API 版本演进：只有 `/api/v1`，没有 v2 或兼容层。
- 没做过 OpenAPI 契约先行/代码生成；springdoc 只是运行时扫描注解。
- 老系统 WebSocket 编辑锁只看过分析文档（`docs/老系统WebSocket与编辑锁机制分析.md`），当前 wms3 没有实现，未迁移。
- HTTP 200 + body code 没有做过网关/监控侧的适配验证。

## 相关

- 技能点：[[Spring Boot]]、[[Spring MVC]]
- 方法：[[Bean Validation 入参校验]]
- 场景：[[全局异常与统一响应]]、[[参数校验]]
- 实践：[[全局异常落地]]
- 项目：[[smart WMS]]
