---
type: 场景
技能点: Java并发与虚拟线程
方法: 跨线程传递登录上下文
证据: 实战
---

# ScopedValue上下文

技能点：[[Java并发与虚拟线程]] · 方法：[[跨线程传递登录上下文]] · 通用技能：[[Java基础与并发]]

**什么时候会遇到**：把任务丢进线程池后，`LoginContext.current()` 变成 null；多租户查询突然少了 `tenant_id`；`@Async` 方法拿不到当前用户。

路径约定：以下 `路径:行号` 相对 `smart-server-wms3/src/main/java/com/track/wms/`；测试相对 `smart-server-wms3/src/test/java/com/track/wms/`。

## 判断顺序

1. **当前线程有请求吗**：有就 `RequestContextHolder` + 请求属性（`common/context/LoginContext.java:34-39`）。
2. **要跨线程吗**：要就在主线程抓 `LoginCtxDto` 快照，不要把 `HttpServletRequest` 传过去。
3. **生命周期是否严格嵌套**：是就用 ScopedValue；需要长期存活/动态修改才考虑 ThreadLocal（项目没用自建 ThreadLocal）。
4. **作用域内谁优先**：`SCOPED.isBound()` 优先于请求属性（`common/context/LoginContext.java:34-40`）。
5. **结束是否自动释放**：ScopedValue 随 `run()` 退出自动解绑；请求属性随请求销毁，不手动清理。

## 手段

- **定义**：`public static final ScopedValue<LoginCtxDto> SCOPED`（`common/context/LoginContext.java:20-21`）。
- **读取**：`current()` 先看 `SCOPED.isBound()`，再回落到 `RequestContextHolder`（`:34-40`）；所有 `currentUserId/currentTenantId/...` 都走它。
- **写入（请求线程）**：Filter/Interceptor 调 `populate(request, dto)` 写请求属性（`:28-31`）。
- **写入（异步线程）**：主线程先 `jwtTokenUtil.current()` 抓快照（`service/impl/ExportServiceImpl.java:86`、`service/impl/ImportServiceImpl.java:118`），worker 里 `ScopedValue.where(LoginContext.SCOPED, loginCtx).run(...)`（`service/impl/ExportServiceImpl.java:118`、`service/impl/ImportServiceImpl.java:157`）。
- **测试**：作用域内读得到、作用域外回落 null（`common/context/LoginContextTest.java:61-75`）；导出 pageFetcher 在作用域内读到 tenant 42（`service/impl/ExportServiceImplTest.java:173-187`）。

## 反例 / 边界

- **不要在线程池任务里直接读 `RequestContextHolder`**：它是线程绑定的，异步线程没有请求就返回 null（`LoginContext` 的回落分支就是为这种情况准备的）。
- **ScopedValue 不会自动传播**：即使父线程绑定了，提交到另一个线程也不会继承；必须在目标任务内部重新 `where(...).run(...)`。项目正是在 worker 内部绑定（`service/impl/ExportServiceImpl.java:118`）。
- **作用域只覆盖 `run()` 内**：`run()` 返回后 `SCOPED` 解绑，后续再读回落请求态/ null（`common/context/LoginContextTest.java:73-74`）。
- **不要把可变对象放进作用域**：`LoginCtxDto` 是快照，但项目没有做深拷贝；作用域内改它等于改共享对象。
- **preview 限制**：ScopedValue 是 Java 21 preview，编译、测试、运行三处都需要 `--enable-preview`（`pom.xml:320`、`:333`、`:350`）；换 JDK 或升级版本要先验证。
- **测试是同步 mock**：导出/导入测试把 `ExecutorService` 换成同步执行（`ExportServiceImplTest.java:116`、`ImportServiceImplTest.java:177-180`），所以「真实虚拟线程上 ScopedValue 能传播」没有被测试证明；测试覆盖的是作用域绑定本身。
- **没覆盖的场景**：`@Async` 的日志/邮件任务没有走 ScopedValue，而是调用方预取参数传入（`service/LoginLogService.java:18`、`:49-56`）；这说明不是所有异步路径都适合作用域注入。

## 现在的规矩

- 异步任务需要登录上下文时：主线程抓快照 → worker 内 `ScopedValue.where(...).run(...)` → 业务代码只读 `LoginContext`。
- 不在异步线程里重新解析 JWT、不把 `HttpServletRequest` 传进线程池。
- 作用域内不修改 `LoginCtxDto`；要改就在快照上新建对象。
- 新异步入口必须有一个「作用域内能读到租户」的测试。

## 相关实践

- [[异步导出中的并发]]

## 来源

- `common/context/LoginContext.java`
- `service/impl/ExportServiceImpl.java`、`service/impl/ImportServiceImpl.java`
- `common/context/LoginContextTest.java`、`service/impl/ExportServiceImplTest.java`
