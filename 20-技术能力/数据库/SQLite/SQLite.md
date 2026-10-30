---
type: 技能点
域: 数据库
项目: [NovelForge]
证据: 学习中
---

# SQLite

所属通用技能：[[数据建模与迁移]]、[[桌面与本地AI]]

**一句话**：桌面端用 SQLite 不是「放个文件当库」：WAL 让读不阻塞写，但 `Connection` 是 `Send` 不是 `Sync`，所有阻塞访问要进 `spawn_blocking`；`user_version` 做迁移，拒绝打开比自己新的库，备份就是复制整个数据目录。

路径说明：以下路径相对 `/Users/hujiuyuan/studyspace/noval/novelforge/`。

**归属说明**：novelforge 不是 git 仓库，不能证明这些代码是本人所写；本页只写「项目内使用、代码存在、作者待核」，不写「我做过」。

## 方法总纲

1. **一个文件一个库**：书稿、章节、真相文件、审计、RAG 分块都在同一个 SQLite 文件里，用 `project_id` 隔离不同书；备份 = 复制数据目录。
2. **WAL 是 pragma，不是编译 feature**：每个连接 open 时 `PRAGMA journal_mode=WAL`；读不阻塞写，写不阻塞读，但只有一个写者。
3. **连接不能跨线程共享**：`rusqlite::Connection` 是 `Send` 但不是 `Sync`，放在 `Mutex` 后面；所有阻塞 DB 访问走 `spawn_blocking`，不能阻塞 async runtime。
4. **迁移用 `user_version`**：`SCHEMA_VERSION=4`，迁移数组只追加；打开时执行未完成的迁移。
5. **拒绝未来版本**：`user_version > SCHEMA_VERSION` 直接报错，提示安装新版，不用旧版覆盖写。
6. **busy_timeout 兜并发**：后台 Agent 持写锁时，UI 等待 5 秒而不是立刻失败；同时 `foreign_keys=ON`、`synchronous=NORMAL`、`temp_store=MEMORY` 每连接设置。

## 我用它干过什么

| 能力 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| rusqlite 0.31 bundled + WAL + 连接管理 | 项目内使用 | NovelForge | 2026-10 | [[本地优先]] |
| `user_version` 版本化迁移（v1–v4） | 项目内使用 | NovelForge | 2026-10 | [[本地优先]] |
| 拒绝打开未来版本数据库 | 项目内使用 | NovelForge | 2026-10 | [[本地优先]] |
| 单根目录 + 复制目录备份 | 项目内使用 | NovelForge | 2026-10 | [[本地优先]] |

## 我会的部分

### WAL 与连接

- `rusqlite = { version = "0.31", features = ["bundled"] }`，bundled 自带 SQLite，不依赖系统库（`src-tauri/Cargo.toml:35`）。
- Cargo 注释明确：WAL 不是 cargo feature，是 `PRAGMA journal_mode=WAL`，在 `db.rs` 里每个连接 open 时设置（`Cargo.toml:32-35`）。
- `configure()` 设置 `journal_mode=WAL`、`foreign_keys=ON`、`synchronous=NORMAL`、`temp_store=MEMORY`、`cache_size=-16000`，并 `busy_timeout(5s)`（`src-tauri/src/db.rs:188-206`）。
- WAL 设置失败（例如网络文件系统）不致命，只打警告；读/写仍能工作，但并发行为退化（`db.rs:190-196`）。

### 连接不能跨线程

- `rusqlite::Connection` 是 `Send` 但不是 `Sync`；`Db` 用 `Mutex<Connection>` 包住，所有访问串行化（`db.rs:1-15`、`:72-80`）。
- 每个阻塞 DB 访问通过 `with_db` 走 `tauri::async_runtime::spawn_blocking`；async command 不能直接在 runtime 线程上做 SQLite I/O（`db.rs:1-10`、`:168-184`）。
- 事务入口也走 `spawn_blocking`：`transaction(f)` 在阻塞线程里执行，避免 UI 卡顿（`db.rs:180-184`）。

### 迁移与版本

- `SCHEMA_VERSION: i32 = 4`；`MIGRATIONS` 数组 index 0 把 `user_version 0 -> 1`，依次追加；v4 把 `rag_index_meta`、`audit_runs.meta_json`、`chapters.version` 一次打包（`db.rs:24-63`）。
- 为什么 v4 不拆成 v4/v5/v6：拆开会让用户连续迁移，旧二进制在每个中间版本都拒绝打开；打包一次减少升级摩擦（`db.rs:30-36`）。
- `ensure_not_from_future` 读 `user_version`，大于当前版本直接报错，提示「这份数据由更新版本创建，请安装新版，不要用旧版覆盖写」（`db.rs:208-232`）。
- 迁移只追加、不改历史；`user_version` 是唯一版本源，不另建 migrations 表。

### 数据布局与备份

- 单根目录：db + WAL + lancedb + exports + snapshots 全在一个目录，备份 = 复制目录（`src-tauri/src/state.rs:1-17`；[[本地优先]]）。
- 所有书在同一个 SQLite 库，通过 `project_id` 隔离；删一本书级联清章节/真相/角色/伏笔/账本/审计/RAG 分块，不碰别的书（`README.md:44-48`）。
- 破坏性操作（删除项目、清空内容、重导、重跑设定师/大纲师）先写 JSON 快照，每项目保留 5 份；快照不覆盖向量索引，因为索引可重建（`src-tauri/src/snapshot.rs:1-10`、`:28`、`:82`）。
- 没有数据库加密：SQLite 明文，没做 SQLCipher；密钥只在系统 keyring/0600 文件里（[[本地优先]]）。

## 选型与取舍

### 为什么桌面端用 SQLite，不用服务端数据库/纯文件

| 方案 | 优点 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| SQLite | 单文件、零服务、事务/索引/SQL 齐全、跨平台 | 单写者；多进程/网络盘并发弱；加密要 SQLCipher | 主方案 |
| 服务端库（PG/MySQL） | 多写者、并发/复制/权限成熟 | 要用户装/起服务；桌面应用不能假设有服务端 | 未使用 |
| 纯文件（JSON/Markdown） | 简单、可读、易备份 | 无事务/索引/并发控制；查询要全量加载 | 只用于导出/快照 |
| SQLCipher | 文件加密 | 额外依赖/密钥管理；性能和兼容性要验证 | 未使用 |

桌面应用不能要求用户装 PostgreSQL；纯文件又撑不住章节、审计、RAG 分块的关联查询和事务。SQLite 在「零运维 + 事务/索引」之间取平衡，是主方案。代价是单写者：后台 Agent 写库时 UI 要等，项目用 WAL + `busy_timeout(5s)` + `Mutex` 串行化，接受短等待而不是引入服务端。

### 为什么用 WAL

- WAL 让读不阻塞写、写不阻塞读；没有 WAL 时，一个长写事务会挡住所有读，UI 会卡。
- 代价：WAL 文件与主库一起存在，备份必须复制目录而不是只复制 `.db`；网络文件系统可能不支持 WAL，失败只警告；检查点/大事务会让 WAL 膨胀。
- 如果只读/单线程，WAL 收益小；项目有后台 Agent 与 UI 并发读写，WAL 是必要的。

### 为什么用 `user_version`，不用迁移表

- SQLite 没有独立的迁移工具链依赖；`PRAGMA user_version` 是文件内建版本号，打开时读一次，不需要建表/查表。
- 代价：没有迁移历史/checksum/作者记录；只能靠代码里的 `MIGRATIONS` 数组和注释。项目用「只追加 + 版本号 + 拒绝未来版本」补足，但没有回滚/审计。
- 如果迁移复杂/多人协作，应该用表记录每次迁移；单机桌面、迁移由应用自身执行，`user_version` 足够。

### 为什么拒绝打开未来版本

- 旧版应用遇到新版 schema，如果继续写会损坏数据；直接报错并提示安装新版，是失败安全。
- 代价：用户降级应用会被挡住；错误信息必须说清「数据目录在哪、升级不动稿件」，否则用户以为数据丢了（`db.rs:220-230`）。
- 这是「宁可打不开，也不要写坏」的取舍；桌面数据是用户手稿，损坏不可接受。

### 什么条件下会反悔

- 多写者/多进程并发成为常态 → 换服务端库或加单实例锁；当前 `Mutex` 只能管进程内。
- 需要加密/合规 → 评估 SQLCipher，代价是密钥管理和性能；当前明文。
- 数据量大到 WAL/单文件备份不可接受 → 分库/归档/导出；当前单库 + 复制目录。
- 需要多设备同步 → 现在没有版本向量/CRDT，必须另做同步层；不要直接把 SQLite 文件放网盘。

## 边界

- 没有多进程/多窗口并发测试；`Mutex` 只覆盖单进程，`busy_timeout` 只缓解锁等待。
- 没有加密（SQLCipher）、没有损坏恢复工具、没有异地备份/恢复演练。
- 没有大数据量压测；WAL 检查点/大事务膨胀没测过。
- 没有迁移回滚；`user_version` 只向前，旧版会被拒绝。
- 没有多设备冲突合并；同一份数据两台机器同时改会互相覆盖。
- 代码归属待核：novelforge 不是 git 仓库，不能证明作者。

## 相关技能

- [[本地优先]]、[[桌面与本地AI基础]]、[[LanceDB与RAG]]、[[Tauri与Rust IPC]]
- [[数据建模与迁移]]、[[Flyway与多仓迁移]]（服务端迁移对比）

## 用在哪些工程能力

- 桌面端本地存储
- 本地优先的数据布局/备份
- 版本化 schema 迁移
