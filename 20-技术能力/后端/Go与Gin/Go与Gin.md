---
type: 技能点
域: 后端
项目: [muou]
证据: 项目内使用（学习中）
---

# Go 与 Gin

所属通用技能：[[Spring应用与接口契约]]

**一句话**：muou-dashboard 是一个小型 Go 服务：`go 1.26.4` + Gin 1.12 + GORM 1.31 + pgx，单模块 `mcm/server`，Gin 路由组挂 JWT/PAT 认证、角色门禁与审计，复杂查询写原生 SQL，表结构由 golang-migrate 的 22 组 up/down 管；容器启动先 `migrate up` 再起服务。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/muou-frontend/muou-dashboard/`。

**归属说明**：**本人在这套 Go 代码里 0 提交**。`git shortlog` 的作者是 jiangjin、huyanglin、jianjun.lu，没有 hujiuyuan；本页只记录我读过、能讲清的项目实现与取舍，不算个人实战，也不能写成「我做过」。

## 方法总纲

1. **单模块、单二进制**：`module mcm/server`，`cmd/server`、`cmd/migrate`、`cmd/seed` 三个入口分别编译成三个静态二进制；部署镜像里只放二进制 + migrations，不装 Go 工具链。
2. **Gin 路由组表达权限边界**：`/api/v1` → `/admin`（内部角色）→ 更细的角色组；`client` 完全隔离在 `/admin` 之外，另有 `/dashboard` 给客户角色。
3. **中间件做入口校验**：`AuthRequired` 同时接受真人 JWT access token 与脚本 PAT；`RequireRoles` 做角色门禁；`AuditLog` 记写操作。
4. **GORM 管 CRUD，原生 SQL 管复杂查询**：简单增删改查用 GORM；任务列表这种多表 join/派生字段用 `RawPage` 写 SQL，避免 ORM 生成难读的查询。
5. **表结构只认迁移**：`golang-migrate` 的 `migrations/*.up.sql` / `*.down.sql` 是唯一来源，GORM 不开 `AutoMigrate`；容器启动先跑 `migrate up`，失败就不启动服务。
6. **错误显式返回**：Go 没有异常，函数返回 `error`，调用方 `if err != nil` 处理；handler 用 `httpapi.Fail` 统一错误体，main 里启动失败 `log.Fatal`。
7. **后台任务用 goroutine**：到期/滞后提醒用一个 `go func()` 每小时跑一次，启动即执行首轮；没有 cron/队列依赖。
8. **测试连真 PostgreSQL**：`testutil.SetupTestDB` 跑迁移、用 `pg_advisory_lock` 串行化多个包的集成测试、`TRUNCATE ... RESTART IDENTITY CASCADE` 清表；没有 `TEST_DATABASE_URL` 就 skip。

## 项目里怎么用（本人 0 提交）

| 代码事实 | 类型 | 项目 | 时间 | 说明 |
| --- | --- | --- | --- | --- |
| Go 1.26.4 + Gin 1.12 + GORM 1.31 + pgx 5.10 | 项目内使用 | muou-dashboard | 2026-07~10 | 读代码/README，不是本人实现 |
| Gin 路由组 + JWT/PAT + 角色门禁 + 审计 | 项目内使用 | muou-dashboard | 2026-07~10 | 同上 |
| golang-migrate 22 组 up/down + 容器启动迁移 | 项目内使用 | muou-dashboard | 2026-07~10 | 同上 |
| 36 个 `_test.go`，集成测试用 advisory lock 串行 | 项目内使用 | muou-dashboard | 2026-07~10 | 同上 |

## 这套代码怎么工作（读代码所得）

### 模块、入口与部署

- `go.mod`：`module mcm/server`、`go 1.26.4`，直接依赖 Gin 1.12.0、`golang-jwt/jwt/v5` 5.3.1、`golang-migrate/migrate/v4` 4.19.1、`pgx/v5` 5.10.0、`gorm.io/driver/postgres` 1.6.0、`gorm.io/gorm` 1.31.2（`server/go.mod:1-13`）。
- 三个入口：`cmd/server` 起 HTTP；`cmd/migrate` 执行 up/down；`cmd/seed` 幂等建项目与首个 admin（`server/cmd/server/main.go:15-45`、`cmd/migrate/main.go:1-34`、`cmd/seed/main.go:1-50`）。
- 镜像多阶段构建：`golang:1.26-alpine` 里 `CGO_ENABLED=0` 编出 server/migrate/seed，运行层只放二进制 + migrations；`CMD` 是 `/app/migrate up && exec /app/server`，迁移失败容器直接退出，不会带旧 schema 起服务（`deploy/server.Dockerfile:1-26`）。
- 生产三容器：postgres + server + nginx（前端静态 + 反代 `/api`）；`dc.sh` 固定 compose 项目名 `dashboard`，避免在 `deploy/` 目录执行时另起一套空库（`deploy/docker-compose.yml:1-70`；`deploy/dc.sh:1-15`）。

### Gin：路由组与中间件

- 入口 `router.New(deps)` 是 HTTP 层唯一组装点：`gin.New()` + `gin.Logger()` + `gin.Recovery()`；`/api/v1` 下分 `/admin`、`/dashboard`、`/notifications`（`server/internal/router/router.go:1-28`）。
- `/admin` 外层挂 `AuthRequired` + `RequireRoles(Internal...)` + `AuditLog`；用户管理、API Token 管理再收窄到 `role.Admin`；规划类写操作收窄到 Admin/PM；任务/评论/反馈等执行类操作对全部内部角色开放（`router.go:26-120`）。
- `/dashboard` 给客户：读接口挂 `AuthRequired`，写接口（附件、评论、变更请求、反馈）挂 `RequireRoles(role.Client)` + `AuditLog`；客户看不到任务明细与负责人，字段裁剪在 handler 里做（`router.go` 末尾段）。
- 认证中间件同时接受两类凭证：`Authorization: Bearer` 且 `apitoken.Is(tok)` 走 PAT 分支，否则按 JWT 解析；两条分支写入完全相同的 `userId/projectId/role` 上下文 key，下游 handler 不用区分凭证来源（`internal/middleware/auth.go:26-50`）。
- PAT 校验：哈希命中 → 未吊销 → 未过期 → 归属账号仍启用；角色实时取自 `users` 表而不是 token 快照，改角色/停用账号立刻生效（`auth.go:53-76`）。
- `last_used_at` 按 5 分钟节流：Go 侧先用已读到的旧值挡掉绝大多数请求（零 SQL），越阈值才发一条带同样阈值条件的 UPDATE，让并发越阈只有一个请求真正落库；写失败只记日志，不影响鉴权（`auth.go:19-24`、`:78-92`）。
- handler 是「返回 `gin.HandlerFunc` 的工厂」：`handler.TaskList(d)` 注入依赖，闭包里解析分页/筛选、查库、写统一响应；不是全局变量/单例（`internal/handler/tasks.go:70-130`）。

### GORM + pgx + 原生 SQL

- 打开连接：`gorm.Open(postgres.Open(url), &gorm.Config{Logger: logger.Default.LogMode(logger.Silent)})`；SQL 日志静默，查询错误返回给调用方由 handler 显式响应；`Ping` 失败先 `sqlDB.Close()` 再返回错误，避免连接池泄漏（`internal/db/db.go:10-27`）。
- 简单 CRUD 用 GORM：`d.DB.Where(...).First/Create/Update`；复杂列表用 `httpapi.RawPage` 拼原生 SQL，例如任务列表要 join 工作包/里程碑/用户、派生 `coalesce(t.assignee_id, w.owner_id)`，用 ORM 反而难读（`internal/handler/tasks.go:70-125`）。
- 为什么不用 `AutoMigrate`：表结构唯一来源是 migrations，模型只做映射；AutoMigrate 会按结构体推表，和迁移文件变成两个真源（`README.md:11-16`；`internal/model/models.go:1`）。
- 分页/列表返回统一：`ParsePage` 解析 page/page_size，`WriteList` 固定 `{items,total,page,page_size}`，handler 不各写一套（`internal/httpapi/pagination.go:37-75`）。

### golang-migrate

- 22 组 up/down（`find migrations -name '*.up.sql' | wc -l` = 22）；`cmd/migrate` 支持 `up` 与 `down`（`down` 走 `m.Steps(-1)`，只回退一步）；`ErrNoChange` 不算失败（`cmd/migrate/main.go:15-34`）。
- 生产容器启动先迁移：`/app/migrate up && exec /app/server`；迁移失败容器退出，由 compose `restart` 策略重试或人工处理（`deploy/server.Dockerfile:25-26`）。
- 测试也跑同一套迁移：`testutil.SetupTestDB` 用 `file://../../migrations` 跑 `m.Up()`，再清表；没有 `TEST_DATABASE_URL` 就 `t.Skip`，本地没库不会把测试判失败（`internal/testutil/testutil.go:25-42`）。
- 多包并行测试共用一个 `mcm_test` 库：用会话级 `pg_advisory_lock(823542)` 串行化 TRUNCATE/读写，锁必须固定在同一条连接上（不能经连接池随机分配），测试结束 unlock + close（`testutil.go:20-60`）。

### goroutine、错误与缺口

- 后台提醒：main 里 `go func(){ for { RunDueReminders; time.Sleep(time.Hour) } }()`，启动即跑首轮；没有 context/cancel、没有 leader election，多副本会各跑一遍（`cmd/server/main.go:28-38`）。
- 错误处理：没有 panic/异常传播；`db.Open` 返回 error，main `log.Fatal`；handler 用 `httpapi.Fail(c, status, code, message)` 统一错误体，业务错误不靠中间件猜（`internal/httpapi/response.go:1-20`；`internal/handler/auth.go:47-95`）。
- 缺口（读代码可见，不是「已做」）：
  - 没有 graceful shutdown：`r.Run(":"+port)` 阻塞，没监听 SIGTERM、没 `http.Server.Shutdown`；发版时在途请求会被直接切断（`cmd/server/main.go:40-44`）。
  - 没有把 `c.Request.Context()` 传进 GORM：查询不随请求取消而取消，客户端断开后 SQL 还会跑完（`grep -rn "WithContext" server/internal` 无结果）。
  - 计时 goroutine 没有退出信号，测试/重启时只能靠进程结束。
  - 没有 pprof、没有 OpenTelemetry/结构化日志；日志是标准 `log` 文本。

## 选型与取舍

> 以下是**项目为什么这么选**的整理（据 README 与代码，本人未参与决策，不冒充决策者）。

### 为什么 dashboard 用 Go，不用 Java/PHP/Node

| 方案 | 优势 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| Go + Gin + GORM | 单静态二进制、启动快、内存小、部署只需一个容器；goroutine 写后台任务简单 | 生态比 Java 小；GORM 的隐式行为要学；团队要会 Go | dashboard 后端 |
| Java + Spring Boot | 生态成熟、事务/安全/可观测齐 | 对这个小系统偏重：JVM 内存、启动、构建链 | muou 主系统用，dashboard 不用 |
| PHP + ThinkPHP | 现有 OMP 遗留栈，改起来快 | 老框架/PHP 8.0、无类型、部署要 FPM+nginx | 遗留系统维护，不新建 |
| Node/TypeScript | 与前端同语言 | 运行时依赖、构建产物带 node_modules；单二进制不如 Go | 未用 |

dashboard 是内部交付协同系统：单服务、表不多、并发不高、部署要简单。Go 的单二进制 + 低资源刚好匹配；Java 的能力过剩，PHP 是遗留栈不宜新建，Node 的部署形态不如 Go 干净。代价是团队要接受 Go 的显式错误处理、GORM 的隐式行为，以及生态比 Java 小。

### 为什么用 Gin，不用 net/http/chi/echo

- Gin 自带路由组、中间件链、`ShouldBindJSON` 参数绑定、`Recovery`，这个项目的权限分层正好用 group + middleware 表达；chi 更贴标准库但绑定/校验要自己补，echo 生态比 Gin 小。
- 代价：Gin 的 `c *gin.Context` 渗透到 handler，换框架要改一层；`gin.Context` 不是标准 `context.Context`，项目里也没把它传进 DB。
- 如果追求零框架/标准库，chi/net/http 更合适；当前 Gin 的组/中间件效率更高。

### 为什么 GORM + 原生 SQL 混用

- 简单 CRUD 用 GORM 省掉扫描/拼 SQL；复杂 join/派生字段用原生 SQL，避免 ORM 生成难读的查询、也避免 N+1。
- 代价：两套查询风格、两套调试方式；GORM 的 `Logger` 被设为 Silent，慢查询/错误 SQL 不会自动打日志，只能靠 handler 返回和手工排查。
- 如果团队更熟 SQL，可以全用 sqlc/sqlx；当前 GORM 的 CRUD 效率更高。

### 为什么用 golang-migrate，不用 AutoMigrate

- 迁移文件是显式 SQL，能写索引、约束、数据回填、down；AutoMigrate 只按结构体加列，不能表达数据迁移，也会和迁移文件变成两个真源。
- 代价：模型与表结构要手工保持一致；迁移顺序/回滚要人工管理；22 组 up/down 没有在 CI 里做「全量 up 再 down」的自动验证（至少本页没看到）。
- 如果只是原型、表结构频繁变，AutoMigrate 更快；这个项目要长期维护，显式迁移更稳。

### 为什么后台任务用 goroutine + Sleep，不用 cron/队列

- 只有一个每小时提醒任务，起一个 goroutine 最省事，不用额外部署 cron/队列。
- 代价：没有 context/cancel、没有 leader election，多副本会重复发送；进程重启会丢当前轮；sleep 期间不能优雅退出。
- 如果任务变多/多副本/要重试，应该换 `time.Ticker` + context、或引调度中心/队列；当前是单副本内部的简单任务。

### 什么条件下会反悔

- 服务变多、需要强事务/消息/可观测 → 评估回 Java 生态或补 Go 中间件；当前单服务。
- 多副本部署 → 提醒任务必须加 leader election/分布式锁，否则重复发邮件。
- 查询复杂到 GORM/原生 SQL 难维护 → 上 sqlc/sqlx 或重划服务边界。
- 团队 Go 经验不足、维护成本高于收益 → 迁回 Java/Node；当前代码量小（83 个 `.go` 文件、36 个测试文件），迁移成本可控。

## 边界

- **本人 0 提交**：没有写过这套 Go 代码、没有参与选型/部署；本页是阅读理解，不是实战。
- 没有用 Go 写过生产服务；goroutine/channel/context/接口组合这些语言能力只到「读得懂」，没有个人项目验证。
- 没有做过 Go 性能调优/pprof/逃逸分析/GC 调优；代码里也没有 pprof。
- 没有 graceful shutdown、没有请求 context 传递、没有结构化日志/链路追踪；这些是代码缺口，不是「项目已做」。
- 没有多副本/leader election；提醒任务在多副本下会重复。
- 没有 CI 里跑全量迁移 up/down；测试依赖外部 PostgreSQL，没设 `TEST_DATABASE_URL` 会 skip。
- 没有用过 sqlc/sqlx/ent、没有写过 gRPC、没有写过 Go 的泛型/反射库。
- 没有参与 dashboard 的部署/运维；只读了 Dockerfile/compose。

## 相关技能

- [[Spring应用与接口契约]]（另一套后端契约，对照看）
- [[PHP与ThinkPHP]]（遗留栈，和 Go 新栈对比）
- [[数据建模与迁移]]、[[Flyway与多仓迁移]]（迁移工具对照）
- [[测试与质量]]（集成测试/advisory lock）
- [[CI-CD与部署]]（单二进制/多阶段镜像）

## 用在哪些工程能力

- 小型 REST 服务的分层与权限
- Go 模块/错误处理/goroutine 基础
- GORM + 原生 SQL 的取舍
- 版本化迁移与集成测试
