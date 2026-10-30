---
type: 技能点
域: 桌面端
项目: [NovelForge]
证据: 实战
---

# keyring与Provider

所属通用技能：[[桌面与本地AI]]

**一句话**：密钥只进系统凭据库（或 0600 的开发文件），数据库只存「有没有配」和掩码；所有模型服务收敛成一个 `stream_chat`，按 `kind` 分 OpenAI 兼容 / Anthropic / Ollama / mock 四种线协议。

## 方法总纲

1. **命名空间**：一个 service + 每个 provider 一个 account（`provider/<id>/api_key`），避免不同服务的 key 互相覆盖。
2. **默认系统库**：Windows 凭据管理器 / macOS 钥匙串 / Linux Secret Service。
3. **开发逃生舱**：macOS ad-hoc 签名每次重编都变，钥匙串会反复弹授权；可切 `file` 后端（`secrets.json`，0600）。
4. **读要缓存**：钥匙串读取是用户可见操作；每进程最多读一次，不在渲染路径读。
5. **前端只见掩码**：只返回前 4 后 4；「是否有 key」查标记，不读原值。
6. **删除幂等**：条目不存在也算成功，否则 UI 会被「删一个不存在的 key」卡住。
7. **协议适配**：OpenAI 兼容走 SSE `choices[0].delta.content`；Anthropic 走具名 SSE `content_block_delta`；Ollama 走 NDJSON；mock 合成并切片流式输出。
8. **错误翻译**：401/403/404/405/415/422/429 各自给可执行提示；返回 HTML 时提示「地址可能指向网页」。
9. **URL 防重复**：base 已经是完整端点时不再追加路径。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 密钥入库、掩码预览、幂等删除 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| keychain / file 双后端与迁移 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| 四协议 Provider 适配与流式解析 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| 模型列表拉取 + 非流式连通性测试 | 实战 | NovelForge | 2026-10 | [[本地优先]] |

**细节与证据**：

- 存储策略与命名：`novelforge/src-tauri/src/keyring.rs:1-15`、`novelforge/src-tauri/src/agents/provider.rs:164-170`。
- 后端选择：`novelforge/src-tauri/src/keyring.rs:31-57`；设置项 `secrets.backend`：`:59-73`。
- 文件后端 0600：`novelforge/src-tauri/src/keyring.rs:90-103`；测试断言权限位：`:313-318`。
- 读缓存与理由：`novelforge/src-tauri/src/keyring.rs:116-130`、`:218-229`。
- 掩码：`novelforge/src-tauri/src/keyring.rs:244-252`；测试：`:283-296`。
- 幂等删除：`novelforge/src-tauri/src/keyring.rs:255-277`。
- 前端只拿掩码：`provider_key_preview` 读掩码标记而非密钥（`novelforge/src-tauri/src/commands/agent.rs:374-381`）；`has_provider_api_key` 查标记（`:383-389`）。
- 保存密钥：写入后同时写「存在」与掩码标记（`novelforge/src-tauri/src/commands/agent.rs:356-372`）。
- Provider 目录：DeepSeek / Moonshot / OpenAI / Anthropic / Ollama / 自定义 / mock（`novelforge/src-tauri/src/agents/provider.rs:89-158`）。
- 四协议流式：`novelforge/src-tauri/src/agents/provider.rs:331-542`；非流式探测：`:625-755`。
- 错误提示与 HTML 识别：`novelforge/src-tauri/src/agents/provider.rs:790-824`。
- endpoint 防重复 + 测试：`novelforge/src-tauri/src/agents/provider.rs:312-325`、`:1255-1292`。
- 构建 provider：数据库行决定 kind/地址，key 从当前后端取（`novelforge/src-tauri/src/commands/mod.rs:44-79`）。
- 前端：密码框录入，展示「已配置/未配置」与掩码（`novelforge/src/components/SettingsPanel.tsx:345`、`:269`、`:1203`）。

## 选型与取舍

### 为什么用系统 keyring，不用加密文件/环境变量

- 系统凭据库由 OS 保护（Windows Credential Manager / macOS Keychain / Linux Secret Service），不会把明文 key 写进项目目录/数据库；前端只拿掩码，密钥只在 Rust 侧读。
- 代价：macOS ad-hoc 签名每次重编都变，钥匙串会反复弹授权；Linux 无 Secret Service 时不可用；读取是用户可见操作，不能放渲染路径。项目做进程内缓存 + `file` 逃生舱。
- 环境变量在桌面应用里不可控（用户双击启动没有 shell env），加密文件要自己管密钥；系统 keyring 是更合适的默认，但不是无代价。

### 为什么保留 `file` 后端

- macOS 开发期 ad-hoc 签名变化会导致 keychain 反复授权，`file` 后端（`secrets.json`，0600）让开发能继续；它不是生产推荐，是逃生舱。
- 代价：明文 JSON，只是文件权限保护；备份/同步/误提交都会泄漏。项目在页面上明确写「不是加密存储」，生产应使用系统 keyring。
- 如果没有开发期签名问题，不需要 file 后端；项目保留它是为了可调试。

### 为什么手写 HTTP 协议适配，不用各家 SDK

- 桌面端要同时支持 OpenAI 兼容、Anthropic、Ollama、mock；手写 `stream_chat` 可以统一流式/取消/错误映射，避免引入多套 SDK 和它们的依赖/版本冲突。
- 代价：协议漂移要自己跟（SSE 字段、NDJSON、错误码）；Anthropic 没走官方 SDK；Azure/Vertex/Bedrock 等专有协议没做。项目用非流式探测 + 错误翻译降低排障成本。
- 如果只接一家、且 SDK 稳定，官方 SDK 更省事；项目要接多家中转/本地模型，统一适配层更划算。

### 为什么所有 Provider 收敛成 `stream_chat`

- 上层 Agent 只依赖一个接口，按 `kind` 分协议；新增 provider 不改业务调用点，流式/非流式/取消行为一致。
- 代价：接口会泄漏差异（有的支持 `dimensions`、有的不支持；有的返回 HTML 错误页），要在适配层做能力标记/错误翻译；否则「统一接口」会把差异藏到运行时。
- 如果每个 provider 的能力差异很大，硬统一会变成大量 if；项目当前四类协议差异可控。

### 为什么前端只拿掩码/存在标记

- 密钥一旦进 WebView，就可能被 XSS/DevTools/日志拿到；前端只需要「有没有配」「前 4 后 4」，真正的 key 留在 Rust。
- 代价：前端不能做「显示完整 key」「复制 key」这类功能；保存/删除要走命令，错误映射要多一层。
- 如果只是本地单人工具、没有 XSS 面，暴露 key 的风险小；项目仍按最小暴露设计。

### 更新器/签名密钥（学习中）

- **现状**：`tauri.conf.json` 里没有 `plugins.updater`、没有 `pubkey`，应用没有接自动更新（`novelforge/src-tauri/tauri.conf.json:1-58`）。发布工作流已经预留 `TAURI_SIGNING_PRIVATE_KEY` / `TAURI_SIGNING_PRIVATE_KEY_PASSWORD` 以及 macOS 公证 secret，但 secret 不存在时构建照样成功（`novelforge/.github/workflows/release.yml:128-138`）。
- **密钥该放哪**：更新器的签名私钥属于发布方，应留在 CI secret/发布机，不能进客户端 keyring；客户端只需要内置公钥验签。keyring 是给「用户自己的 provider API key」用的，两者不要混。
- **为什么现在不接**：没有 updater 配置就没有更新清单、签名产物和回滚策略，接了也只是半套；当前安装包靠 GitHub Release 手动下载。**反悔条件**：`tauri.conf.json` 出现 updater 配置、发布流程开始产出签名更新包时，再把这一句升级成一节，并补「私钥不进客户端、公钥怎么轮换」。

### 什么条件下会反悔

- 需要 OAuth/短期令牌/多账号 → 现有 API Key 模型不够，要引入令牌刷新/租户隔离；当前只有单 key。
- 协议差异继续扩大 → 引入官方 SDK 或按 provider 拆适配器；当前手写四类还可控。
- file 后端被误用于生产 → 去掉逃生舱或加启动警告；当前靠文档/页面提示，不是强制。

## 我会的部分

- 用 `tauri-plugin-keyring` + `keyring` crate 做系统凭据存取。
- 设计 keychain/file 双后端、迁移、进程内缓存、掩码、幂等删除。
- 适配 OpenAI 兼容、Anthropic、Ollama 的流式与非流式请求。
- 把 HTTP 状态码翻译成用户能照做的错误文案。
- 用非流式请求做连通性探测，避免中转站不支持 SSE 时误判。
- mock provider 的确定性输出，用于离线测试。

## 边界

- 真实 provider 的调用没有被自动化测试覆盖；仓库里的测试全部走 mock，没有联网用例。
- Anthropic 是手写 HTTP，不是官方 SDK；没做 Azure OpenAI、Vertex、Bedrock 等专有协议。
- 只有 API Key 一种认证；没做 OAuth、短期令牌、密钥轮换/过期、配额管理。
- 缓存没有 TTL；外部换了 key，进程内还会用到重启。
- `file` 后端是明文 JSON，只是 0600；不是加密存储。
- **权限层没收紧**：capabilities 放开了 keyring 的 `get_secret`/`set_secret`/`delete_secret`（含 password 变体），前端理论上可以直接调插件读密钥。当前靠代码不调用 + CSP，尚不是 ACL 保证（`novelforge/src-tauri/capabilities/default.json:10-15`）。
- 没做多账号/多租户隔离；provider id 是全局的。

## 相关技能

[[Tauri与Rust IPC]]、[[LanceDB与RAG]]

## 用在哪些工程能力

密钥管理、模型服务接入、流式协议解析、错误可观测性、桌面安全边界
