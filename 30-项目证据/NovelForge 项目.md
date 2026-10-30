---
type: 项目证据
时间: 2026-10
技术栈: [Tauri 2, Rust, React 19, TypeScript, SQLite, LanceDB]
---

# NovelForge

**定位**：本地优先的长篇小说创作桌面应用；稿件、真相文件、向量索引、密钥都在本机，云端模型只是可选推理。

**模块 → 相关节点**

| 模块 | 相关节点 |
| --- | --- |
| 壳与 IPC | [[桌面与本地AI]]、[[Tauri与Rust IPC]]、[[本地优先]] |
| RAG | [[LanceDB与RAG]]、[[本地优先]] |
| 密钥与模型服务 | [[keyring与Provider]]、local-first（待建） |
| 审计/导出/Agent | [[NovelForge]]、[[本地优先]] |
| 前端 | [[TypeScript与Vite]]、[[前端与Vue3]]（仅对照） |

## 项目级方案取舍

> 说明：NovelForge 没有 git 历史，决策以代码/配置和页面里的「选型与取舍」为准；下面只整理项目级、跨模块的取舍。

### 为什么本地优先 + SQLite，不做云端账号/服务端库

- **现状**：稿件、真相文件、审计、向量索引、密钥都在本机；SQLite WAL + `user_version` 迁移，LanceDB 存向量，keyring 存 provider key（[[SQLite]]、[[本地优先]]）。
- **候选**：纯云端 SaaS；本地文件（JSON/Markdown）；本地 SQLite；服务端库 + 本地缓存。选本地优先是产品定位：作者要离线、数据主权、不依赖账号；SQLite 单文件、事务、迁移、备份（复制目录）都比自管文件可靠。
- **代价**：没有多设备同步/协作；SQLite 单写者、`Send` 非 `Sync`、要 `spawn_blocking`；备份/损坏恢复要自己教用户；密钥/加密没做（SQLite 明文）。
- **反悔条件**：要多设备同步/协作 → 加同步层/CRDT 或服务端库；要合规加密 → SQLCipher/字段加密；单机写入成为瓶颈 → 分区/拆库（当前单用户，不紧迫）。

### 为什么 Tauri 2 + Rust，不用 Electron

- Tauri 用系统 WebView，包体/内存小；Rust 侧持有 keyring、发 LLM 请求、读写 SQLite/LanceDB，前端只拿 IPC/流（[[Tauri与Rust IPC]]）。
- 代价：各平台 WebView 行为不一致、Rust 学习曲线、插件生态小；打包只保证能构建，不保证安装/签名。
- 反悔条件：多平台 WebView 兼容问题频发、需要成熟自动更新/多窗口 → 评估 Electron；团队只会 JS 且不碰密钥/本地库 → Electron 更稳。

### 为什么 LanceDB，不用 pgvector/Chroma

- 嵌入式、Rust 客户端直接可用，不需要用户装 PostgreSQL/Chroma 服务；向量和 SQLite 文本镜像分账，索引坏了可从 SQLite 重建（[[LanceDB与RAG]]）。
- 代价：没有 ANN（当前暴力检索）、不具备 PG 的事务/备份能力、索引目录要自己管理；双写一致性靠 `rag_index_meta` + `index_lock`。
- 反悔条件：书库规模大到暴力检索不可接受 → 上 ANN/专用向量库；需要多用户/服务端检索 → pgvector/Qdrant。

### 为什么 keyring + 手写 Provider 适配

- 密钥进系统凭据库，前端只拿掩码；`stream_chat` 统一 OpenAI 兼容/Anthropic/Ollama/mock 四类协议（[[keyring与Provider]]）。
- 代价：macOS ad-hoc 签名反复弹授权、Linux 无 Secret Service 不可用；手写协议要跟 SSE/NDJSON 漂移；没有 OAuth/短期令牌/轮换。
- 反悔条件：接 OAuth/多账号 → 引入令牌刷新/租户隔离；协议差异扩大 → 官方 SDK/按 provider 拆适配器；file 后端被误用于生产 → 去掉逃生舱/加启动警告。

### 什么条件下整体反悔

要多设备/协作 → 本地优先 + 同步层或转服务端；要移动端 → Tauri 2 移动支持不成熟，评估其他壳；要自动更新/签名 → 接 updater + CI 签名，当前 `tauri.conf.json` 没有 updater；要合规加密 → SQLCipher/字段加密，当前 SQLite 明文。

**我在这里练到的技能**：[[桌面与本地AI]]、[[Tauri与Rust IPC]]、[[LanceDB与RAG]]、[[keyring与Provider]]、[[TypeScript与Vite]]

**源路径**：`/Users/hujiuyuan/studyspace/noval/novelforge`

**规模**：10 个 Agent / 10 个阶段；33 维审计（21 规则 + 12 模型）；Rust 225 个测试属性（1 个 `#[ignore]`，默认 224）、前端 31 个测试；LanceDB 384 维、每项目一张表、无 ANN。

**边界**：仓库没有 `.git`，没有发布上线证据；真实 provider 没有自动化测试；capabilities 放开了 keyring 的 `get_secret`，密钥边界目前靠代码自律 + CSP，不是 ACL 强制。
