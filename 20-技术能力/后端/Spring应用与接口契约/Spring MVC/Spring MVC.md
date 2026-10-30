---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战
---

# Spring MVC

所属通用技能：[[Spring应用与接口契约]]

**一句话**：项目里的 MVC 用法固定成一套：薄 controller、注解校验、`Result<T>` 返回、异常全部向上抛给全局 advice。

## 方法总纲

1. Controller 只做三件事：绑定参数、调 service、返回 `Result`。
2. 参数校验用注解，不写 if；校验消息写 i18n key。
3. 返回值统一 `Result<T>`；只有导入这类历史接口返回裸 VO，交给 `ResponseBodyAdvice` 包。
4. 业务异常不在 controller catch，由 `CoreControllerAdvice` 统一映射。
5. 路径按模块一级前缀 `/api/v1/{module}`，动作放方法级注解。

## 我用它干过什么

时间说明：`smart` 目录不是 git 仓库，2026-08 按计划文档和文件 mtime 推断，不是提交记录。

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 全局异常与统一响应 | 实战 | [[smart WMS]] | 2026-08 | [[全局异常与统一响应]] |
| 三模块 controller 的参数校验 | 实战 | [[smart WMS]] | 2026-08 | [[参数校验]] |
| 39 个 controller 的注解式路由 | 实战 | [[smart WMS]] | 2026-08 | — |

## 选型与取舍

### 为什么统一 `Result<T>`，不直接返回 DTO / 用 HTTP 状态码表达业务错误

- 统一 `Result<T>` 让前端只写一个拦截器：`code=200` 成功，其他走错误提示；分页再套 `PageResponse`，前端不用按接口猜结构。
- 代价：HTTP 状态码长期是 200，网关/监控/日志无法按 4xx/5xx 统计业务失败；接口文档要额外说明 `code`；REST 语义被弱化。项目里 `Result` 还保留 `getError()/getReason()` 兼容旧前端字段（`Result.java:55-64`），说明这是历史契约，不是纯理论选择。
- 更标准的做法是「HTTP 状态码 + 错误体」；项目没改，是因为 39 个 controller、旧前端和网关都按 body code 写死了，迁移成本高于收益。如果新项目从零开始，应该优先用 HTTP 状态码；老项目继续统一 wrapper，至少保证一致。

### 为什么异常向上抛，不在 controller catch

- controller 只做参数绑定/调 service/返回，业务异常由 `CoreControllerAdvice` 统一映射成 `Result`；这样错误码、日志、i18n 只在一处，不会每个 controller 各写一套 try/catch。
- 代价：异常路径不直观，排查要看 advice；如果 advice 漏了某类异常，会落到默认 500/空响应。项目用统一异常测试和 `@OperationLog` 补可观测性。
- 如果某个接口需要特殊错误格式（文件下载、第三方回调），可以在方法内局部处理；项目选择「默认上抛，例外显式注释」，避免静默吞异常。

### 为什么用注解校验，不写 if

- `@Valid` + JSR-303 把「字段非空/长度/格式」声明在 DTO 上，错误消息走 i18n；39 个 controller 有 183 处 `@Valid`，统一口径。
- 代价：跨字段/业务校验（如「开始时间 < 结束时间」「租户内名称唯一」）注解表达不了，仍要 service/自定义 validator；类级 `@Validated` 只有 1 个 controller，`@RequestParam` 校验口径不统一。
- 这不是「注解万能」：简单字段用注解，业务规则下沉 service；项目边界里明确写了方法级校验不统一，是待补的债。

### 为什么 controller 要薄

- 薄 controller 让参数绑定/HTTP 细节和业务逻辑分离，service 可单测、可复用；权限/业务校验下沉，避免「同一个规则在多个 controller 各写一遍」。
- 代价：简单 CRUD 多一层转发；有些前置校验（文件大小、格式）放在 controller 更直接，项目也保留了例外（`WarehouseController.java:374-379`、`:408-416`）。
- 判断标准不是「controller 行数越少越好」，是「业务规则是否只在一处」；为了薄而薄、把逻辑硬塞 service 也会让 service 变成上帝类。

### 什么条件下会反悔

- 新项目/新网关要求按 HTTP 状态码监控 → 改成标准状态码 + 错误体，旧接口保留 wrapper 兼容。
- 跨字段校验大量增加 → 引入自定义 validator/规则引擎，而不是继续在 service 写 if。
- controller 继续膨胀/重复 → 抽基类或函数式路由；当前 39 个 controller 的重复还在可接受范围。

## 我会的部分

- **类级注解**：`@RestController` + `@RequestMapping("/api/v1/{module}")`（`CompanyController.java:41-42`、`LoginLogController.java:29-30`），方法级 `@GetMapping/@PostMapping/@PutMapping/@DeleteMapping`。
- **参数绑定**：`@Valid @RequestBody`（`CompanyController.java:53`）、GET query DTO（`WarehouseController.java:82`）、`@PathVariable`（`CompanyController.java:119`、`WarehouseController.java:428`）、`@RequestParam`（`WarehouseController.java:175`）、`MultipartFile`（`WarehouseController.java:407`）。
- **校验**：wms3 main 里 183 处 `@Valid`（精确匹配；controller 层 175 处、model/req 7 处，grep 2026-10-29）；类级 `@Validated` 只有 `WarehouseController.java:46`，用来让 `@RequestParam` 上的 `@NotNull` 生效（`:175`、`:212`、`:226`、`:240`、`:308`、`:322`）。
- **返回**：`Result<T>` + `PageResponse<T>`（`CompanyController.java:53`）；导入接口返回裸 `ImportResultVO`，由 advice 包装（`WarehouseController.java:367-379`）。
- **分层**：类注释写明「Controller 仅转发，权限/业务校验下沉到 Service」（`CompanyController.java:39`）；但也有例外，controller 里做文件大小等前置校验并抛 `BusinessException`（`WarehouseController.java:374-379`、`:408-416`）。
- **横切**：操作日志用 `@OperationLog` 注解（`CompanyController.java:58-59`、`WarehouseController.java:290-292`）；接口文档用 `@Tag`/`@Operation`/`@Parameter`（`CompanyController.java:44`、`:52`）。
- **响应兼容**：`Result` 提供 `getError()`/`getReason()`，把 `code`/`message` 映射成前端拦截器认识的字段（`Result.java:55-64`）。
- **异常**：controller 不 catch；`FilesController` 曾手写 catch，已移除并把异常上抛（`FilesController.java:117-124` 注释）。

## 边界

- 没写过自定义 `HandlerMethodArgumentResolver`、`Formatter`、`Converter`。
- 没写过 `@InitBinder`/`@ModelAttribute`；全局 advice 只做异常处理和响应包装。
- 没做过内容协商、多视图；导出走异步任务 + 文件 URL，不直接回二进制。
- 没做过函数式 `RouterFunction`。
- `@IgnoreResponse` 定义了但全仓零使用（`IgnoreResponse.java:8`、`CoreControllerAdvice.java:236-242`）。
- 方法级校验口径不统一：39 个 controller 只有 1 个类级 `@Validated`。
- `docs/wms-controller-api-inventory.md:3-15` 还写着 13 个 controller / 70 个端点（2026-05-10），已过期；当前是 39 个 controller。

## 相关技能

[[Spring Boot]]、[[全局异常与统一响应]]、[[参数校验]]、[[全局异常落地]]

## 用在哪些工程能力

接口契约与统一响应、参数校验与错误码（均未建卡，无页面）
