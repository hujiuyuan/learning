---
type: 技能点
域: 后端
项目: [smart WMS]
证据: 实战（维护级）
---

# PHP 与 ThinkPHP

所属通用技能：[[Spring应用与接口契约]]

**一句话**：OMP 这套 PHP 是「维护级」不是「从零搭过」：ThinkPHP 5.1 跑在 PHP 8.0-FPM 上，请求走 nginx → FPM → `public/index.php` → 路由 → 中间件 → controller → service → model；我主要是在这套老系统上改业务、修导出队列、修 PHP 错误输出、把存储切到 OSS V4，并补齐容器化部署。

路径说明：以下路径相对 `/Users/hujiuyuan/workspace/voidtech/smart/smart-server-omp-legacy/`。

**归属说明**：这个仓库里本人提交 160 次（`git shortlog -sn` 当前值），主要集中 2026-08~09；框架与旧业务是历史代码，不能把整个系统算成个人从零实现。

## 方法总纲

1. **请求链路固定**：nginx 把 `.php` 交给 php-fpm；`public/index.php` 是唯一入口；`route/route.php` 与 `route/admin.php` 定义路由；`Api`/`ApiLogin`/`Admin` 中间件做入口校验；controller 只做参数与响应，业务在 service，表在 model。
2. **路由必须显式注册**：ThinkPHP 不会自动给所有 controller 方法挂鉴权；没注册的路由不会进中间件，等于绕过登录。曾有一个废弃接口 `planGoods` 未注册路由而绕过登录，已删除（commit `4b07ad2`）。
3. **会话登录，不是 JWT**：`ApiLogin` 从 `Session` 取 `user_api` 或 `user_api_view`，再查 `User` 确认没过期；后台走 `Admin` 中间件（`application/http/middleware/ApiLogin.php:9-31`、`route/route.php:78-85`、`route/admin.php:215`）。
4. **大任务用「命令 + 常驻 worker」**：导出/导入/同步是 4 个 `php think` 命令，每次只处理一页就退出，并把任务状态改回 0 重新入队；由 compose 里的 `worker` 容器每 5 秒串行跑一遍。
5. **队列只能单实例**：命令捞任务是「先 `select status=0` 再 `update status=1`」，并发多份有重复捞取窗口；所以 worker 只跑一份，四个命令串行（`docker-compose.yml:95-124`）。
6. **PHP 错误绝不进响应体**：`display_errors=Off`、`html_errors=Off`、`log_errors=On`，错误走 FPM 的 stderr 进 `docker logs`；否则 fatal 会粘在 JSON 后面，前端 `JSON.parse` 直接炸（`docker/php/Dockerfile:36-54`）。
7. **调试开关要用 `PHP_APP_DEBUG`**：ThinkPHP 5.1 的 `Env::get('app_debug')` 先查 `$_ENV['APP_DEBUG']`，字符串 `'false'` 在 PHP 里是真值；必须注入 `PHP_APP_DEBUG` 才会做 `'false' -> false` 转换（`docker-compose.yml:45-55`）。
8. **存储走门面**：业务只调 `Storage::upload`，`STORAGE_DRIVER=oss|s3` 决定落谁家；下载按 URL 域名路由，存量四个桶的文件都能拉（`application/common/tools/Storage.php:7-10`、`:67-100`）。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| OMP 出货/派送/拼车业务：按派送单聚合、装货序号、拼车排序 | 实战 | smart WMS | 2026-08 | [[组件拆分]] |
| 补齐导出队列 worker：此前三个分支都没拉起四个命令，11 条任务卡死 | 实战 | smart WMS | 2026-08 | [[中间件与异步任务]] |
| PHP 错误输出治理：`PHP_APP_DEBUG` 哑弹、`display_errors` 污染 JSON | 实战 | smart WMS | 2026-08~09 | [[安全与审计]] |
| 存储切阿里云 OSS V4 签名 + S3/OSS 门面与环境前缀 | 实战 | smart WMS | 2026-08~09 | [[S3与对象存储]] |
| PHP 后端 GitLab CI：构建/推 Harbor/部署，补 nginx reload 修 502 | 实战 | smart WMS | 2026-08~09 | [[CI-CD与部署]] |

## 我会的部分

### 请求链路与代码组织

- 依赖：`php >=7.4`、`topthink/framework 5.1.*`、`workerman/gateway-worker`、`aliyuncs/oss-sdk-php`、`aws/aws-sdk-php`、PhpSpreadsheet/PhpWord/PhpMailer；`autoload.psr-4` 把 `app\\` 映射到 `application/`（`composer.json:18-43`）。
- 运行时是 `php:8.0-fpm`，`composer.json` 的 `platform.php` 也是 8.0.30；不是本机 PHP 8.5（`docker/php/Dockerfile:3`、`composer.json:53-55`）。
- 规模：40 个 controller 文件、33 个 model、57 条 `Route::` 定义；controller 构造器注入 service，业务逻辑不堆在 controller（`application/api/controller/v1/User.php:11-18`）。
- 参数校验在基类：`filterParams` 检查必填键，缺了直接 `Response::error`；controller 里再按业务做类型/范围校验（`application/api/controller/v1/Base.php:49-55`）。
- 事务写法是显式 `Db::startTrans/commit/rollback`，异常往外抛，不吞（`application/api/controller/v1/User.php:20-46`）。

### 中间件、会话与路由安全

- API 路由分两层：`api/v1` 整体挂 `Api` 中间件；需要登录的子组再挂 `ApiLogin`；后台 `api/admin` 挂 `Admin`（`route/route.php:15-16`、`:78-85`、`route/admin.php:215`）。
- `ApiLogin` 支持两种会话：`login_type=1` 读 `user_api_view`（只读/查看态），否则读 `user_api`；再从 `User` 表确认用户存在且 `is_login != 1`，否则 401（`application/http/middleware/ApiLogin.php:13-30`）。
- 安全教训：路由没注册就不走中间件。一个已废弃的 `planGoods` 接口没注册路由、一直绕过登录校验，删除它而不是只删调用点（commit `4b07ad2`，2026-08-25）。
- 这套是「会话 + 服务端权限」，没有 JWT、没有 OAuth2 资源服务器；和 muou 的 IAM 不是一套。

### 队列与导出：命令 + worker

- 4 个命令：`taskExport`、`taskImport`、`taskExportFile`、`taskSync`，都是 `think\console\Command`，`execute()` 里查一条/一页任务、处理、改状态（`application/command/TaskExport.php:30-42`、`TaskImport.php:26-44`、`TaskSync.php:27-41`）。
- 为什么不能靠 cron 每分钟跑：命令跑一页就退出，10 页的导出要被调用 10 次；每分钟一次会让大导出慢到不可用（`docker-compose.yml:92-96`）。
- 2026-08-19 补建 worker 前，main/master/test 三个部署链路都没有拉起这四个命令，宿主机 crontab/宝塔/systemd 也没有；测试库最后成功任务停在 2026-07-02，之后 11 条全卡死，客户表现为「一键导出一直挂起」（`docker-compose.yml:97-103`）。
- worker 以 `www-data` 运行，循环里每条命令后加 `|| true`：单条脏任务不能打断整个队列；`sleep 5` 控制轮询间隔（`docker-compose.yml:104-124`）。
- 导出目录 `public/exportTask` 必须在镜像里预建：`TaskExport` 用 `exec('mkdir -m 0777 ...')` 没有 `-p`，父目录不存在时 `exec` 不抛异常，后面写 xlsx 才报错，日志里看不出真因（`docker/php/Dockerfile:56-70`）。

### 存储：OSS/S3 门面

- `Storage` 门面按 `STORAGE_DRIVER` 转发；上传走默认驱动，下载按 URL 域名精确匹配当前桶，认不出的一律当历史桶走公开读直拉（`application/common/tools/Storage.php:67-100`）。
- 为什么不能按 `.aliyuncs.com` 后缀路由：库里存着四个来源（storageadmin-us2 53 万条、wms-res、store-test-hk、AWS CloudFront），后缀匹配会拿当前桶名去请求别的桶，全部 404（`Storage.php:95-99`）。
- OSS V4 签名必须带 region；region 缺失时 SDK 仍会构造 SignerV4，但签出的凭证无效，首次请求才报签名错。所以只在 region 非空时启用 V4，否则回落 V1（`application/common/tools/Oss.php:33-42`）。
- 对象 key 统一加环境前缀（`test/omp/`、`pro/omp/`），两个驱动共用一处拼接；兼容漏尾斜杠/多前导斜杠的配置写法（`Storage.php:13-40`）。

### 运行时错误与日志

- 官方 `php:8.0-fpm` 镜像不带 `php.ini`，`display_errors`/`html_errors` 默认 On；任何未捕获 fatal 会被引擎直接打进响应体，此时响应头已发出，只能在正常 JSON 后面粘一段 `<b>Fatal error</b>...`，前端解析必炸（`docker/php/Dockerfile:36-44`）。
- 2026-08-31 实际发生过：`runtime/log` 月份目录被 root 建走，php-fpm（www-data）写不进日志，ThinkPHP 在 shutdown 刷日志失败抛异常（PHP 8.0 不交给 `set_exception_handler`），登录接口 JSON 后面多了一坨 HTML（`docker/php/Dockerfile:42-46`）。
- 修法两层：`zz-omp-errors.ini` 强制 `display_errors=Off/html_errors=Off/log_errors=On`；`entrypoint.sh` 把 ThinkPHP 单文件日志转发到容器 stdout，`log_errors=On` 让 FPM 错误进 `docker logs`（`docker/php/Dockerfile:48-54`）。
- `APP_DEBUG=false` 是哑弹：`Env::get` 先查 `$_ENV`，字符串 `'false'` 是真值；改用 `PHP_APP_DEBUG` 后 `App.php:220` 的 `ini_set('display_errors','Off')` 才执行，异常响应也不再带绝对路径和调用栈（`docker-compose.yml:45-55`）。

### 部署与 CI

- 服务器只拉 Harbor 镜像，不在服务器构建；compose 四个服务：`php`（FPM）、`gateway`（Workerman Gateway/Register/BusinessWorker）、`worker`（队列消费者）、`nginx`（静态前端 + FastCGI）（`docker-compose.yml:1-15`、`:61-143`）。
- 镜像 `php:8.0-fpm`，装 pdo_mysql/mysqli/mbstring/zip/bcmath/sockets/gd/pcntl + redis 扩展；时区固定 `America/New_York`，与业务方约定一致（`docker/php/Dockerfile:1-30`）。
- CI 的硬约束：build 与 deploy 必须同一台 runner（deploy 直接用本地镜像，不经 Harbor）；deploy 禁止 `docker compose pull`，否则会把刚构建的本地镜像覆盖掉（`.gitlab-ci.yml:9-15`）。
- 后端发版只重建 php/gateway/worker，不动 nginx；php 容器换 IP 后，nginx 的 `fastcgi_pass php:9000` 仍缓存旧 IP，所有 `/api/admin/*` 502。修法是在部署末尾 `docker exec omp_test_nginx nginx -s reload`，只重载不中断连接（`.gitlab-ci.yml:143-155`）。
- `PHP_TAG`/`NGINX_TAG` 拆开，支持前后端分开发版；`TAG` 保留兜底，老 `.env` 未迁移也能启动（commit `7413b62`）。

## 选型与取舍

### 为什么维护这套 ThinkPHP 5.1，不重写/不新建 PHP 项目

| 方案 | 优势 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| 继续维护 ThinkPHP 5.1 | 业务知识都在代码里；改一个字段/接口当天能上线；PHP-FPM 部署简单 | 框架/PHP 8.0 已老；无类型、无现代测试/静态分析；安全补丁要自己盯 | 主方案，维护级 |
| 用 Laravel/Symfony 重写 | 现代框架、生态、测试工具 | 重写全部业务 + 数据迁移 + 回归；停业务风险高 | 未采用 |
| 用 Java/Go 重写 | 与 muou/WMS 新栈统一、类型与并发更好 | 同样重写；团队要同时维护两套 | 未落地 |

这套系统还在承载出货/派送/拼车等真实业务，重写不是「换个框架」而是「把业务规则重新实现一遍」。维护的代价明确：框架老、PHP 8.0 已停止安全支持、没有 PHPUnit/静态分析；换来的是改动小、上线快、不打断业务。所以定位是维护级：只修 bug、加必要功能，不从零新建 PHP 项目。退出条件是业务迁到新栈/功能冻结，而不是「哪天想学 Laravel」。

### 为什么用 PHP-FPM，不用 Swoole/RoadRunner

- FPM 是「每请求一个进程」的经典模型：请求之间不共享内存，一个请求的致命错误不会污染下一个；opcache 只管字节码，部署/回滚简单。
- 代价：每个请求都要 bootstrap 框架、重建容器，吞吐不如常驻内存；长连接/WebSocket 不能靠 FPM。
- 项目只在实时消息用 Workerman Gateway（`gateway/start.php`），HTTP 仍走 FPM；没有为了性能把整站改成 Swoole。如果 QPS 高到 FPM 撑不住，再评估 RoadRunner/Swoole，代价是常驻内存的状态污染和更难的重载。

### 为什么队列用「命令 + 常驻 worker」，不用 cron

- 命令是「跑一页就退出、把状态改回 0 再入队」的模型；cron 每分钟只能推进一步，10 页导出要 10 分钟，大任务不可用。
- worker 每 5 秒串行跑四个命令，单实例避免「select status=0 → update status=1」的重复捞取窗口；`|| true` 保证一条脏任务不拖垮整个循环。
- 代价：没有并发、吞吐有限；单实例是单点，worker 挂了任务会停（容器 `restart: unless-stopped` 兜底）。如果任务量上来，要改成带租约/原子领取的多实例队列，而不是简单加副本。

### 为什么存储走门面，不直接调 OSS SDK

- 业务只依赖 `Storage::upload`，切 OSS/S3 只改配置；下载按 URL 域名路由，存量四个桶的历史文件不用迁移也能读。
- 代价：两套 SDK、两套签名/错误形态；V4 的 region、桶域名、环境前缀都要自己处理，配错往往首次请求才报错。
- 如果只用一家云、且没有历史桶，直接调 SDK 更简单；当前有历史数据和迁移需求，门面值得。

### 什么条件下会反悔

- 业务迁到 Java/Go 新栈、PHP 只做只读过渡 → 冻结功能，只修安全/数据问题；不再投入框架升级。
- PHP 8.0 出现无法绕过的安全漏洞 → 评估升 8.1/8.2 或容器隔离，不能一直拖。
- 队列任务量/并发要求超出单 worker → 改成带原子领取/租约的多实例消费者，或迁到统一 MQ。
- 存储只剩一家云、历史桶清空 → 去掉门面，直接调 SDK，减少一层抽象。

## 边界

- 维护级，不是从零搭建：没有从零建过 ThinkPHP 项目、没有做过框架升级/迁移。
- 没有 PHPUnit/ Pest、没有 PHPStan/ Psalm、没有 CI 单测；验证靠接口回归、日志和线上观察。
- 没有升级 PHP 8.0 → 8.1/8.2，也没有升级 ThinkPHP 5.1 → 6.x；老版本的安全支持是已知风险。
- 没有做过 Swoole/RoadRunner、没有做过 PHP 常驻内存框架。
- 没有做过 Laravel/Symfony；本页的「替代框架」只到选型比较，不是实战。
- 会话登录只覆盖现有后台/API；没有 JWT/OAuth2、没有多因素认证。
- 没有做过 PHP 性能压测/opcache/JIT 调优；FPM 参数按默认和现网观察。
- 没有做过代码静态分析/安全扫描；路由绕过登录这类问题靠人工审查和事故发现。

## 相关技能

- [[Spring应用与接口契约]]（新栈的接口契约对照）
- [[中间件与异步任务]]（命令 + worker 的队列模型）
- [[S3与对象存储]]（OSS/S3 门面、V4 签名）
- [[CI-CD与部署]]（Harbor、compose、nginx reload）
- [[安全与审计]]（错误输出、路由鉴权）

## 用在哪些工程能力

- 遗留系统维护与渐进改造
- PHP-FPM 请求链路与中间件
- 后台任务/导出队列
- 对象存储迁移与多云门面
- 容器化部署与发布故障处理
