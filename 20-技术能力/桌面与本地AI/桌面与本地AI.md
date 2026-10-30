---
type: 通用技能
域: 桌面端
证据: 实战/设计
---

# 桌面与本地AI

**一句话**：桌面 AI 应用的核心不是「套个壳」，而是划清三条边界——数据留在本机、能力留在宿主进程、密钥留在系统凭据库；前端只拿 IPC 和流。

基础知识自测：[[桌面与本地AI基础]]

> 四层读法：理论 [[桌面与本地AI基础]]｜实践 本页「我用它干过什么」｜问题 [[本地优先]]｜方案 [[NovelForge 项目]]。总入口 [[四层读法]]。

## 一、理论：六条边界

1. **本地优先**：稿件、真相文件、索引、设置默认全部落在本机；云端只承担可选推理。断网、没 Key 时，非 AI 功能必须照常可用。
2. **进程边界**：WebView 只负责渲染与交互；文件、数据库、网络、密钥都在宿主进程（这里指 Rust）。前端不直接发模型请求，避免跨域和密钥暴露。
3. **IPC 三原语**：请求/响应用命令（invoke），高频流用通道（Channel），后端主动通知用事件（listen）。三者混用会让状态不可推理。
4. **密钥不进前端**：密钥写系统凭据库，数据库只存「有没有配」和掩码；前端只拿到前 4 后 4 的掩码。
5. **嵌入向量库**：桌面端不适合另起向量服务，通常用嵌入式库；固定维度 + 记录 embedder 身份 + 文本镜像，才能保证索引可重建、距离有意义。
6. **Provider 适配**：同一套界面背后可能是 OpenAI 兼容、Anthropic、Ollama、mock 四种线协议；差异收敛在一个 `stream_chat` 里，上层只认 `kind`。

## 二、实际使用：NovelForge 怎么落的

- **壳与版本**：Tauri 2 + React 19 + TypeScript + Vite。证据：`novelforge/package.json:17-23`、`novelforge/src-tauri/Cargo.toml:20-30`。
- **安全边界**：CSP 只允许 `'self'` 脚本，窗口能力走 capabilities 白名单。证据：`novelforge/src-tauri/tauri.conf.json:25-27`、`novelforge/src-tauri/capabilities/default.json:6-15`。
- **IPC 分层**：`commands/` 只做校验→委托→返回可序列化类型；前端只有 `lib/ipc.ts` 知道命令名。证据：`novelforge/CLAUDE.md:51-53`、`novelforge/src/lib/ipc.ts:1-16`。
- **命令注册**：命令表集中在 `generate_handler!`，前端 `api` 一一对应。证据：`novelforge/src-tauri/src/lib.rs:195-305`、`novelforge/src/lib/ipc.ts:68-340`。
- **流式生命周期**：`Channel<StreamEvent>` 承载 start/delta/done/error；provider 失败与用户取消都会发 `Error`，避免编辑器一直转圈。证据：`novelforge/src-tauri/src/stream.rs:70-90`、`novelforge/src-tauri/src/commands/agent.rs:669-685`。
- **后端主动通知**：审计完成、Agent 完成走 `app.emit` + 前端 `listen`。证据：`novelforge/src-tauri/src/commands/audit.rs:232-240`、`novelforge/src-tauri/src/commands/agent.rs:738-741`、`novelforge/src/lib/ipc.ts:422-434`。
- **密钥**：系统钥匙串默认，开发可切 `secrets.json`（0600）；前端只拿掩码。证据：`novelforge/src-tauri/src/keyring.rs:31-57`、`novelforge/src-tauri/src/keyring.rs:244-252`、`novelforge/src-tauri/src/commands/agent.rs:374-381`。
- **向量**：SQLite 存分块文本镜像，LanceDB 存 384 维向量，每项目一张表，无 ANN。证据：`novelforge/src-tauri/src/vectorstore.rs:1-15`、`novelforge/src-tauri/src/vectorstore.rs:39-56`。
- **Provider**：四种线协议 + 统一对话请求。证据：`novelforge/src-tauri/src/agents/provider.rs:49-75`、`novelforge/src-tauri/src/agents/provider.rs:331-542`。
- **离线**：mock 是一等公民，审计/RAG/导出/后端测试都能无 Key、无网络跑。证据：`novelforge/src-tauri/src/agents/provider.rs:355-373`、`novelforge/src-tauri/src/integration_tests.rs:1-8`、`novelforge/README.md:38`。
- **数据目录**：一个目录装下 db/WAL/lancedb/exports/snapshots，备份就是复制目录。证据：`novelforge/src-tauri/src/state.rs:1-17`。

## 三、归纳：桌面 AI 检查清单

1. **先定数据归属**：哪些必须本机、哪些允许出站、出站内容是否包含用户正文。
2. **再定进程边界**：网络、密钥、文件读写只放宿主；前端只做展示和意图。
3. **IPC 选型**：一次性调用 invoke，流式用 Channel，通知用 Event；每个 Channel 每次调用新建。
4. **密钥三件事**：系统凭据库、数据库只存标记、前端只拿掩码；删除要幂等。
5. **数据目录可备份**：一个根目录装结构化数据、向量、导出、快照；文档里写清楚「复制哪个文件夹」。
6. **索引当缓存**：文本镜像 + embedder 身份 + 固定维度；索引坏了能离线重建。
7. **Provider 收敛**：协议差异关在一个适配层；错误文案翻译成用户能照做的说明。
8. **离线路径**：mock/本地嵌入必须是一等公民，测试默认不联网。
9. **可恢复**：破坏性操作先快照；数据库迁移只追加、不修改；拒绝打开更高版本的数据。
10. **打包**：安装包目标、CSP、capabilities、签名状态都要在发布说明里写清楚。

## 四、回到理论

- 前端拿不到密钥的前提是**权限层也不给**。只靠「代码里没调用」不够——XSS 或供应链污染后，前端仍能调用任何被 capability 放开的命令。NovelForge 的 capabilities 放开了 keyring 的 `get_secret`（`novelforge/src-tauri/capabilities/default.json:10-15`），所以这条保证目前靠代码自律 + CSP，不是 ACL 强制。
- Channel 用 tagged enum 而不是 `String`，是因为**失败也是流的一部分**；没有终止事件，UI 只能靠超时猜。
- 向量索引必须可丢弃：嵌入函数、维度、分块策略任一变化，旧向量就失去意义；把文本留在 SQLite 才敢重建。
- mock 不是测试道具，是**离线可用性的验收装置**：没有它，所有测试都变成「有网有 Key 才能跑」。

## 五、边界

- 桌面经验只有 Tauri 2 + Rust 这一种组合；Electron、Flutter Desktop、Qt 没有可指的项目证据。
- 证据全部来自 macOS 语境（数据目录、钥匙串、ad-hoc 签名）；Windows/Linux 只有打包配置与 CI 矩阵，没有本机产物验证。
- 没做代码签名/公证；`release.yml` 明说无签名密钥也会产安装包，只是未签名（`novelforge/.github/workflows/release.yml:12-13`）。
- 没做自动更新、崩溃上报、多窗口、移动端；`tray-icon` feature 开了但代码里没有托盘实现（`novelforge/src-tauri/Cargo.toml:23`）。
- 没做过真正的语义嵌入：本地嵌入是字符 n-gram 哈希的词面检索，远端嵌入路径没有可查的真实服务实测记录。
- NovelForge 没有 git 提交、没有发布上线证据；本页只证明「代码与测试具备这些能力」。

## 相关

- 技能点：[[Tauri与Rust IPC]]、[[LanceDB与RAG]]、[[keyring与Provider]]
- 理论：[[检索与排序理论]]、[[复制与一致性理论]]
- 场景：[[本地优先]]
- 实践：[[NovelForge]]
