---
type: 方法
技能点: Spring MVC
域: Spring应用与接口契约
证据: 实战
---

# Bean Validation 入参校验

技能点：[[Spring MVC]] · 通用技能：[[Spring应用与接口契约]]

**一句话**：校验要分三层——字段格式用 Bean Validation，跨字段/业务规则进 Service，失败统一由 `ControllerAdvice` 转成 body code；注解不加 `@Valid` 等于没写。

## 方法总纲

1. **按参数来源选入口**：body → `@Valid @RequestBody DTO`；query DTO → `@Valid DTO`；`@RequestParam`/`@PathVariable` 直接参数 → 类级 `@Validated` + 参数注解；路径变量格式用 `@Pattern` 或类型转换。
2. **字段注解只做格式**：`@NotNull/@NotBlank/@Size/@Pattern/@Min/@Max/@Email`；一个字段一个语义，别用 `@Pattern` 拼复杂业务规则。
3. **嵌套对象逐层 `@Valid`**：根对象加了 `@Valid` 不会自动校验嵌套对象，每层都要标；集合元素用 `@Valid` + `List<@Valid Item>`。
4. **跨字段规则进 Service**：时间先后、状态前置、枚举组合、唯一性查库，抛业务异常 + 具体 `ResultCode`；不要塞进自定义注解隐藏数据库访问。
5. **message 用 i18n key**：`@NotBlank(message = "COMPANY_CODE_REQUIRED")`，所有 locale 文件都补；缺翻译时降级返回 key 本身，前端会看到大写常量。
6. **异常统一映射**：body/query DTO → `MethodArgumentNotValidException`/`BindException`；直接参数 → `HandlerMethodValidationException` 或 `ConstraintViolationException`；`ControllerAdvice` 取第一条错误转 400 + message。
7. **测试断 body code**：不只断 HTTP status；项目统一 HTTP 200 + body code，只断 `isOk()` 锁不住错误类型。

## 参数来源与入口

| 参数位置 | 正确写法 | 不写会怎样 |
| --- | --- | --- |
| JSON body | `@Valid @RequestBody Dto` | 字段注解完全不触发 |
| query 绑定 DTO | `@Valid Dto` | 同上 |
| `@RequestParam` | 类级 `@Validated` + `@NotNull` 等 | 参数注解不生效 |
| 嵌套对象 | 每层 `@Valid` | 只校验第一层 |
| 集合元素 | `@Valid List<@Valid Item>` | 元素内部不校验 |

## 反例

- **只加注解不加 `@Valid`**：最常见，编译通过、运行不校验。
- **在 Controller 手写 if 返回 `Result.error`**：错误码语义混乱（项目里有 4 处返回固定 500），且散落在各接口。
- **把查库唯一性塞进自定义校验注解**：校验器里访问数据库，事务/连接/性能都失控；放 Service。
- **message 写字面量**：多语言环境无法翻译；前端拿不到稳定 key。
- **只回第一条错误且不带字段名**：项目当前就是只取 `findFirst()`，前端无法定位是哪个字段；要定位就把字段名放进 message 或扩展响应结构。
- **测试只断 HTTP status**：400 和 500 都可能是 4xx/5xx，锁不住具体校验分支。

## 证据

- [[参数校验]] — 项目里的四种入口、四个异常 handler、i18n key 与反例
- [[全局异常与统一响应]] — `ControllerAdvice` 的映射顺序
- `smart-server-wms3/src/main/java/com/track/wms/controller/WarehouseController.java:46,82,175-322` — 类级 `@Validated`、query DTO、6 处直接参数
- `smart-server-wms3/src/main/java/com/track/wms/controller/CompanyController.java:53` — body `@Valid`
- `smart-server-wms3/src/main/java/com/track/wms/model/req/company/CompanyCreateReq.java:17` — message 是 i18n key
- `smart-server-wms3/src/main/java/com/track/wms/model/req/auth/LoginLogPageReq.java:18-20` — 嵌套 `@Valid`
- `smart-server-wms3/src/main/java/com/track/wms/config/CoreControllerAdvice.java:108-160` — 四类校验异常到 body code
- `smart-server-wms3/src/main/java/com/track/wms/common/util/I18nUtil.java:37-51` — 缺翻译降级返回 key

## 边界

- `@RequestParam` 约束只在 `WarehouseController` 落地，其他 controller 未验证。
- 直接参数的 `HandlerMethodValidationException` vs `ConstraintViolationException` 取决于代理方式，项目未逐一验证。
- 校验失败只回第一条、不回字段名，前端定位能力有限。
