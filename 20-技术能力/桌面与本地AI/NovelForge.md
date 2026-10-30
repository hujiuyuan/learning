---
type: 实践
技能点: Tauri与Rust IPC
项目: [NovelForge]
时间: 2026-10
证据: 实战
---

# NovelForge

技能点：[[Tauri与Rust IPC]]、[[LanceDB与RAG]]、[[keyring与Provider]] · 项目：NovelForge · 2026-10

场景：[[本地优先]]

## 我想干什么

做一个本地优先的长篇小说创作桌面应用：稿件、真相文件、向量索引、密钥都在本机；云端模型只是可选推理；没有 Key、没有网络时，审计、去 AI 味、RAG、导出仍能跑通。

## 我干了什么

- **壳**：Tauri 2 + React 19 + TypeScript + Vite；前端只通过 IPC 调 Rust（`novelforge/package.json:17-23`、`novelforge/src-tauri/Cargo.toml:20-30`、`novelforge/src/lib/ipc.ts:1-16`）。
- **分层**：`commands/` 薄 IPC 层；`repo.rs` 独占 SQL；`db.rs` 用 WAL + `with_db`/`with_db_tx`（`novelforge/CLAUDE.md:30-53`、`novelforge/src-tauri/src/db.rs:1-13`）。
- **十个 Agent / 十个阶段**：`AGENT_ROLES: [&str; 10]`、`PIPELINE_STAGES: [&str; 10]`（`novelforge/src-tauri/src/models.rs:12-37`）；每个角色独立提示词（`novelforge/src-tauri/src/agents/prompts/mod.rs:1-20`）。
- **33 维审计**：`DIMENSIONS: [DimensionDef; 33]`，21 个规则维度 + 12 个模型维度（`novelforge/src-tauri/src/audit_engine.rs:42-51`）。
- **密钥**：系统钥匙串默认，file 后端兜底；数据库只存标记；前端只拿掩码（`novelforge/src-tauri/src/keyring.rs:1-15`、`novelforge/src-tauri/src/commands/agent.rs:356-381`）。
- **模型服务**：OpenAI 兼容 / Anthropic / Ollama / mock 四协议，统一 `stream_chat`（`novelforge/src-tauri/src/agents/provider.rs:49-75`、`:331-542`）。
- **RAG**：SQLite 文本镜像 + LanceDB 每项目一张表，384 维，无 ANN（`novelforge/src-tauri/src/vectorstore.rs:1-15`、`:39-56`、`novelforge/src-tauri/src/commands/memory.rs:1-10`）。
- **导出**：Markdown / DOCX / EPUB 3，自写 stored-only ZIP（`novelforge/CLAUDE.md:46`）。
- **测试**：Rust 225 个带 test 属性（`src-tauri/src/` 全目录按 `#[test]`/`#[tokio::test]` 计数；1 个 `#[ignore]`，默认跑 224），其中 `integration_tests.rs` 64 个；前端 31 个（`App.test.tsx` 26 + `EditorPane.test.tsx` 5）。与 `README.md:382-384` 的 31 / 224 一致。
- **打包**：bundle targets = nsis/dmg/app；CI 矩阵覆盖 macOS arm64/x64、Linux、Windows（`novelforge/src-tauri/tauri.conf.json:29-31`、`novelforge/.github/workflows/release.yml:33-46`）。

## 犯了什么错 / 误判

1. **Base URL 拼两次**：中转站给的是完整端点，代码再拼 `/chat/completions`，变成 `.../chat/completions/chat/completions` → 404，用户读成「连不通」。修复：`endpoint()` 先判断 base 是否已以该路径结尾（`novelforge/src-tauri/src/agents/provider.rs:312-325`），并补测试 `:1255-1292`。
2. **给中转站发 `stream_options`**：这是 OpenAI 扩展，很多中转站直接 400。修复：不请求 usage（`novelforge/src-tauri/src/agents/provider.rs:375-378`）。
3. **推理模型正文为空**：预算全花在 reasoning 上，界面看起来像网络失败。修复：检测 `reasoning_content` 并提示调大 maxTokens 或换非推理模型（`novelforge/src-tauri/src/agents/provider.rs:660-675`）。
4. **每个 Agent 的 base_url 盖过 provider 地址**：请求被悄悄发到官方 DeepSeek，界面却显示中转站。修复：地址只认 provider 行，迁移清空旧列（`novelforge/src-tauri/src/commands/mod.rs:61-65`、`novelforge/src-tauri/src/db.rs:38-46`）。
5. **渲染一次读一次钥匙串**：macOS 每次读都弹授权。修复：进程内缓存，每 provider 最多读一次（`novelforge/src-tauri/src/keyring.rs:116-130`）。
6. **启动 schema 不匹配静默崩溃**：Finder 启动时 stderr 无处可看。修复：写 `novelforge-error.log` + 原生对话框；`setup()` 不返回 `Err`（`novelforge/src-tauri/src/lib.rs:136-161`、`:182-185`）。
7. **删掉的示例重启复活**：启动时自动 seed。修复：首启不写任何项目（`novelforge/src-tauri/src/lib.rs:126-128`）。
8. **导入的书搜不到**：RAG 镜像为空，重建永远返回 0 块。修复：镜像空时回扫 chapters 重建（`novelforge/src-tauri/src/commands/memory.rs:138-149`）。
9. **中文被切成 U+FFFD**：按 chunk 做 `from_utf8_lossy`，多字节字符跨 TCP 包就坏。修复：用增量 `Decoder` 保留未完成字节（`novelforge/src-tauri/src/stream.rs:24-38`）。
10. **点击按钮没反应**：state 更新了，但渲染在另一个 return 分支，`tsc` 看不见。修复：jsdom 渲染真实 `<App/>`，Tauri 边界全 mock（`novelforge/src/App.test.tsx:1-9`、`novelforge/vitest.config.ts:1-12`）。

## 怎么解决

不是逐条打补丁，而是把同类问题变成机制：URL/协议收敛到 `ProviderHandle` + 错误提示表 + 单测；配置只认一个来源，迁移只追加；密钥双后端 + 缓存 + 掩码 + 幂等删除；数据用镜像 + 可重建 + 快照 + 事务；界面只测「点击有没有反应」。

## 现在的规矩

1. `commands/` 只校验与委托，SQL 只出现在 `repo.rs`。
2. 新增命令四步：实现 → `generate_handler!` → `ipc.ts` → `types.ts`。
3. 跨 IPC 结构 camelCase；错误必须是作者能照做的中文。
4. 密钥不进数据库/日志/前端；前端只拿掩码。
5. 33 维声明表是唯一来源；`skipped` 不算 `pass`。
6. 索引是缓存，必须能离线重建；查询与索引必须同一 embedder。
7. 破坏性操作先快照；迁移只追加。
8. 测试默认不联网；mock 是一等公民。

## 证据

- 架构与约束：`novelforge/CLAUDE.md:7`、`:30-73`。
- 角色与阶段：`novelforge/src-tauri/src/models.rs:12-37`；33 维：`novelforge/src-tauri/src/audit_engine.rs:51`。
- 密钥与 Provider：`novelforge/src-tauri/src/keyring.rs`、`novelforge/src-tauri/src/agents/provider.rs`。
- RAG：`novelforge/src-tauri/src/vectorstore.rs`、`novelforge/src-tauri/src/commands/memory.rs`。
- 测试：`novelforge/src-tauri/src/integration_tests.rs`（64 个）、`novelforge/src/App.test.tsx`（26 个）、`novelforge/src/components/EditorPane.test.tsx`（5 个）。
- 缺口：仓库没有 `.git`，没有提交历史；没有发布上线证据；Windows/Linux 安装包没有本机验证；真实 provider 没有自动化测试。
