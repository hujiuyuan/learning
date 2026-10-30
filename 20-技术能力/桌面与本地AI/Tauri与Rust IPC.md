---
type: 技能点
域: 桌面端
项目: [NovelForge]
证据: 实战
---

# Tauri与Rust IPC

所属通用技能：[[桌面与本地AI]]

**一句话**：Tauri 的 UI 在系统 WebView、能力在 Rust；前端只能靠 `invoke`（请求响应）、`Channel`（流）、`listen`（事件）三种原语跨进程，网络和密钥都留在 Rust 侧。

## 方法总纲

1. **命令薄层**：`commands/*.rs` 只做参数校验、调用领域函数、返回可序列化类型，不写业务逻辑。
2. **注册链路**：新增命令 = 实现 → `lib.rs` 的 `generate_handler!` 注册 → `src/lib/ipc.ts` 加类型化封装 → `src/types.ts` 同步。
3. **三种原语各司其职**：CRUD/审计/配置走 invoke；逐 token 输出走 Channel；后端主动通知走 Event。
4. **跨边界类型**：结构体统一 `#[serde(rename_all = "camelCase")]`；错误实现 `Serialize`，前端收到的是中文 `Display` 字符串。
5. **流要有终止态**：`StreamEvent` 带 start/delta/done/error，失败也发事件。
6. **能力白名单**：窗口能调哪些插件命令写进 `capabilities/*.json`，不靠默认全开。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 三插件初始化 + 命令注册表 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| 十个 Agent 的流式生成与取消 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| 前端类型化 IPC 封装 + 边界 mock 测试 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| macOS/Windows/Linux 打包配置 | 设计/方案 | NovelForge | 2026-10 | [[本地优先]] |

**细节与证据**：

- 壳版本：Tauri 2 + React 19 + TS + Vite（`novelforge/package.json:17-23`、`novelforge/src-tauri/Cargo.toml:20-30`）。
- 插件与命令：`opener` / `dialog` / `keyring` 三个插件（`novelforge/src-tauri/src/lib.rs:178-181`），命令表在 `generate_handler!`（`novelforge/src-tauri/src/lib.rs:195-305`）。
- 通道：`Channel<StreamEvent>`；每次调用新建一个 Channel，因为 Tauri channel 单次绑定（`novelforge/src/lib/ipc.ts:346-363`）。
- 事件：`audit://completed`、`agent://finished`；前端用 `listen` 订阅并返回 unlisten（`novelforge/src/lib/ipc.ts:408-434`）。
- 后端流：`run_agent` 先发 Start，再把 provider delta 转发到 Channel，结束发 Done；取消走 watch channel（`novelforge/src-tauri/src/commands/agent.rs:567-578`、`:669-685`、`novelforge/src-tauri/src/state.rs:74-102`）。
- JSON 类 Agent 走非流式：一次拿完整文档，解析失败能报清楚（`novelforge/src-tauri/src/commands/agent.rs:687-724`）。
- 错误：`Error` 实现 `Serialize`，按 `Display` 输出中文（`novelforge/src-tauri/src/error.rs:1-5`、`:95-99`）。
- 网络不出前端：所有 LLM 请求由 Rust `reqwest` 发起（`novelforge/src-tauri/src/lib.rs:26-29`、`novelforge/src-tauri/src/stream.rs:1-4`）。
- 前端测试只 mock Tauri 边界，不启动 Rust（`novelforge/src/App.test.tsx:1-9`、`novelforge/vitest.config.ts:1-12`）。
- 打包：bundle targets = nsis/dmg/app（`novelforge/src-tauri/tauri.conf.json:29-31`）；CI 矩阵覆盖 macOS arm64/x64、Linux、Windows（`novelforge/.github/workflows/release.yml:33-46`）。

## 选型与取舍

### 为什么用 Tauri，不用 Electron

- Tauri 的 UI 用系统 WebView，二进制不打包 Chromium，体积/内存比 Electron 小；Rust 侧能做网络、密钥、文件访问，前端拿不到原始密钥。
- 代价：各平台 WebView 版本/行为不一致（macOS WKWebView、Windows WebView2、Linux WebKitGTK），CSS/JS 兼容要分别测；Rust 学习曲线、插件生态比 Electron 小；移动端支持还不成熟。
- Electron 的优点是 Chromium 一致、Node 生态/插件多、团队只写 JS；代价是包大、内存高、主进程/渲染进程安全边界要自己守。项目是本地优先的桌面写作工具，体积和密钥隔离优先，所以选 Tauri；如果团队只会 JS、或需要成熟的多窗口/托盘/自动更新生态，Electron 更稳。

### 为什么网络和密钥留在 Rust，不放前端

- 前端直连 LLM/对象存储会把 API key 暴露在 WebView/DevTools；Rust 侧持有 keyring、发请求、流式回传，前端只拿 token/结果。CSP 和 capabilities 再把前端能力收窄。
- 代价：所有请求都要过 IPC，命令/类型/错误映射要维护；流式输出要用 Channel，取消要 watch channel；前端不能直接用 fetch 的生态。
- 如果只是纯展示、没有密钥/本地文件，前端直连更简单；项目要保存 provider key、读写本地库，必须把敏感能力放 Rust。

### 为什么用 invoke / Channel / listen 三种原语

- `invoke` 适合请求-响应（CRUD、配置、审计）；`Channel` 适合逐 token 流（单次绑定，每次调用新建）；`listen` 适合后端主动通知（完成/审计事件）。用错原语会让流式/取消/事件难处理。
- 代价：三种 API 三套错误/生命周期；Channel 单次绑定、Event 要 unlisten、invoke 大 payload 要序列化。项目在 `ipc.ts` 统一封装，前端不直接散落调用。
- 如果只有简单 CRUD，`invoke` 足够；流式/后台任务多了，才需要 Channel/Event。

### 为什么用 capabilities 白名单，不默认全开

- Tauri 2 的窗口能力由 `capabilities/*.json` 声明，插件命令不默认全开；配合 CSP 限制脚本来源，减少 WebView 被 XSS 后的能力。
- 代价：新增插件/命令要同步改 capabilities，漏配就是运行时拒绝；项目没有对 capabilities 做测试，权限收紧是配置，不是被验证过的行为。
- 如果只是内部工具、不加载远程内容，默认权限的风险小；项目要存密钥/读文件，白名单值得。

### 为什么用 tokio/reqwest/Channel 做异步流式

- **依赖**：`reqwest 0.12` 开 `stream`/`json`，`tokio 1` 开 `full`，`futures-util 0.3`；`stream` feature 才能拿 `bytes_stream()`，把响应体当增量流而不是先收完整 body（`novelforge/src-tauri/Cargo.toml:44`、`:50-51`）。
- **SSE 解析是状态机**：`sse_events(resp)` 用 `unfold` 维护缓冲区、行缓冲、事件名和数据行，处理多行 `data:`、CRLF、注释行、末尾没有空行的最后一个事件（`novelforge/src-tauri/src/stream.rs:103-170`）。
- **UTF-8 不能按 chunk 解码**：中文一个字 3 字节，TCP 分包可能把它劈开；直接 `from_utf8_lossy` 会把半个字变成 `U+FFFD` 并写进正文。`decode_chunk` 用 `encoding_rs::Decoder` 保留不完整尾字节，下一块补齐（`stream.rs:31-48`）。
- **Channel 传生命周期事件**：`run_agent` 先发 `Start`，再把 provider 的增量经 `mpsc` 转发成 `Delta`，结束发 `Done`；失败也发 `Error`，否则编辑器会一直转圈（`novelforge/src-tauri/src/commands/agent.rs:671-682`、`:693-720`；`stream.rs:67-95`）。
- **取消**：`register_run(run_id)` 返回 `watch::Receiver<bool>`，`tokio::select!` 在流循环里同时等 provider 和取消信号；取消后发 `Error` 并 `finish_run` 清理注册表（`novelforge/src-tauri/src/state.rs:74-102`；`agent.rs:583`、`:707-712`、`:765-770`）。
- **背压边界（重要）**：转发用的是 `tokio::sync::mpsc::unbounded_channel`，没有容量上限，webview 消费慢时事件会在内存里堆着；没有做限流、丢弃策略或窗口控制（`agent.rs:677-682`、`:953-958`）。当前一次只跑一个生成、token 速率低，没出问题；这是未压测的缺口，不是「已解决背压」。

**为什么不用阻塞 IO/线程池**：每个生成是一条长连接，阻塞 IO 会占住线程；tokio 让一条任务在等待网络时让出执行器，`reqwest` 的 `bytes_stream` 直接给出增量块。**代价**：异步状态机、取消、错误传播都要手写；SSE 分包和 UTF-8 边界是两类容易静默出错的坑。**什么时候反悔**：并发生成/大流量导致无界队列内存上涨 → 换有界 channel + 背压/丢弃策略；需要多路复用/HTTP2 连接池调优 → 在 reqwest client 层统一配置，而不是每个 provider 各建一个。

### 什么条件下会反悔

- 多平台 WebView 兼容问题频发/需要成熟自动更新 → 评估 Electron；当前打包只保证能构建，不保证能安装。
- Rust 侧命令/插件继续膨胀 → 拆独立服务/进程，或把非敏感能力放前端；当前 IPC 还可控。
- 需要移动端 → Tauri 2 移动支持还不成熟，可能要换方案；当前只做桌面。

## 我会的部分

- 初始化 Tauri 2 Builder、注册插件与 `generate_handler!`。
- 写薄命令层，返回值统一 camelCase，错误转中文可执行文案。
- 用 Channel 做流式输出，用 Event 做完成通知，用 watch channel 做取消。
- 用 `capabilities` 收窄窗口权限，用 CSP 限制脚本来源。
- 配置 devUrl 固定端口、bundle targets、release profile。
- 为前端写「只验证点击有反应」的 jsdom 测试，Tauri 边界全 mock。

## 边界

- 没有移动端实现；`cfg_attr(mobile, ...)` 只是入口标记（`novelforge/src-tauri/src/lib.rs:163`）。
- 没有多窗口、托盘、自定义协议、文件拖放；`tray-icon` 只是开了 feature，没有代码。
- 没有对 capabilities 做测试；权限收紧是配置，不是被验证过的行为。
- 没有代码签名/公证产物；CI 只保证「能构建」，不保证「能安装」。
- 没做 IPC 压测；流式并发、长连接、背压都没验证。
- 没做过前端直连 HTTP 的对照方案；Electron 也没有可指的项目证据。

## 相关技能

[[keyring与Provider]]、[[LanceDB与RAG]]

## 用在哪些工程能力

桌面应用开发、进程边界设计、流式 UI、插件权限、跨平台打包
