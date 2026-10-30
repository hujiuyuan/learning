---
type: 技能点
域: 桌面端
项目: [NovelForge]
证据: 实战
---

# LanceDB与RAG

所属通用技能：[[桌面与本地AI]]

**一句话**：RAG 的可信度取决于三件事——分块文本有镜像、查询与索引用同一个嵌入函数、维度不符直接报错而不是静默返回「看起来合理」的距离。

## 方法总纲

1. **分账**：SQLite 存章节、真相文件、审计结果，以及每个分块的文本镜像；LanceDB 只存向量和检索所需的元数据。
2. **表设计**：每项目一张表 `chunks_<slug>`；列 = id / chapter_id / chapter_number / chunk_index / kind / text / vector。
3. **固定维度**：向量列是 `FixedSizeList<Float32, 384>`；写入前校验数量和维度，不符就拒绝。
4. **写路径**：整项目重建用 Overwrite；单章增量先删后加；空集合 drop 表，避免搜到已删除文本。
5. **检索**：`nearest_to(vector).limit(n)`；排除当前章在 Rust 侧后过滤，避免依赖 Lance 的谓词下推行为。
6. **嵌入身份**：另存 `rag_index_meta`（SQLite；`local:hash:384` 或 `remote:<model>:384`）；查询必须用同一个 embedder。
7. **并发**：同一项目的索引/删除/检索共用一把 `index_lock`，防止并发重建互相覆盖。
8. **规模取舍**：几千个分块时 flat scan 比维护 ANN 索引更快，也避免 IVF_PQ 的召回率调参。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 章节分块 → SQLite 镜像 → LanceDB 向量 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| 项目级重建 / 单章增量 / 删除清理 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| 本地哈希嵌入 + 远端嵌入回退 | 实战 | NovelForge | 2026-10 | [[本地优先]] |
| 索引一致性检查与重建 | 实战 | NovelForge | 2026-10 | [[本地优先]] |

**细节与证据**：

- 分工与无 ANN 的理由：`novelforge/src-tauri/src/vectorstore.rs:1-15`。
- 表结构：`novelforge/src-tauri/src/vectorstore.rs:39-56`；表名 slug：`:59-61`。
- 整项目覆盖写：`novelforge/src-tauri/src/vectorstore.rs:126-146`；增量追加：`:149-170`；按章删除：`:173-181`；删项目：`:183-189`。
- 检索与排除章：`novelforge/src-tauri/src/vectorstore.rs:222-318`。
- 分块：摘要一块 + 正文按 400 字、40 字重叠切（`novelforge/src-tauri/src/sample.rs:487-518`）。
- 本地嵌入：384 维字符 1–3 gram + 拉丁词，带符号哈希后 L2 归一（`novelforge/src-tauri/src/agents/provider.rs:842-881`）。
- 远端嵌入：OpenAI 兼容 `/embeddings`，请求 `dimensions: 384`；网络失败退回本地，维度不符硬报错（`novelforge/src-tauri/src/agents/provider.rs:900-940`）。
- 重建：镜像为空时回退扫描 chapters；重建后写 `rag_index_meta`（`novelforge/src-tauri/src/commands/memory.rs:126-211`）。
- 查询同一 embedder：`novelforge/src-tauri/src/commands/memory.rs:330-361`。
- 每项目索引锁：`novelforge/src-tauri/src/state.rs:62-71`。
- 测试：往返检索、排除章、删除清理、嵌入一致性、维度不符（`novelforge/src-tauri/src/integration_tests.rs:300-346`、`:1043-1074`、`:1754`、`:1766`）。

## 选型与取舍

### 为什么用 LanceDB，不用 pgvector / SQLite 向量扩展 / Chroma

| 方案 | 优点 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| LanceDB | 嵌入式、无服务、Arrow/Lance 列式、Rust 客户端 | 生态比 pgvector 小；ANN 索引/调参要自己学；多进程并发支持有限 | 主方案 |
| pgvector | 已在 PostgreSQL 里，事务/备份/权限复用 | 要起 PG 服务；桌面端多一个依赖；向量索引调参 | 未使用 |
| SQLite 向量扩展 | 单文件、和业务库同库 | 扩展兼容/性能/索引能力有限；生态不成熟 | 未使用 |
| Chroma | Python 生态、上手快 | 多一个服务/进程；Rust 集成不如 LanceDB 直接 | 未使用 |

项目是本地优先桌面应用，不能要求用户装 PostgreSQL/Chroma 服务；LanceDB 嵌入式、Rust 客户端直接可用，是主要理由。代价是它不像 pgvector 那样能复用 PG 的事务/备份，索引目录要自己管理；项目用「SQLite 存文本镜像 + LanceDB 只存向量」来补一致性。

### 为什么 SQLite 和 LanceDB 双写，不只存一份

- SQLite 是真相源：章节、审计、分块文本镜像都在 SQLite；LanceDB 只存向量和检索元数据。索引坏了可以从 SQLite 重建，不会丢原文。
- 代价：双写一致性要自己保证；重建/增量/删除要同步两边；查询结果要回 SQLite 取文本。项目用 `rag_index_meta` 记录 embedder 身份、每项目 `index_lock` 串行化写/检索，测试覆盖删除清理和维度不符。
- 如果只做简单全文检索，SQLite FTS 就够；引入向量是因为要语义召回，双写是代价。

### 为什么几千块用 flat scan，不建 ANN 索引

- 几千个分块时 flat scan 的延迟可接受，且没有 IVF_PQ 的召回率调参/训练成本；建 ANN 反而增加复杂度和「索引没训练好」的故障。
- 代价：数据量上去后延迟线性增长；项目没有压测，这是设计判断，不是实测结论。边界里明确写了「没建 ANN、没测大数据量」。
- 如果分块到十万级，应该建 ANN 并做召回率评估；当前规模不需要。

### 为什么本地哈希嵌入 + 远端回退

- 本地哈希嵌入不联网、无模型依赖，离线可用；远端嵌入质量更好，但需要 API key/网络，失败退回本地。
- 代价：本地嵌入是词面检索，同义改写/跨语言召回差；远端模型必须支持 `dimensions: 384`，否则固定维度会拒绝。项目把 embedder 身份写进 `rag_index_meta`，查询必须用同一个 embedder，避免「索引和查询不同模型」的静默错误。
- 如果要求语义质量，应该统一用远端嵌入并接受联网依赖；当前本地优先，接受词面召回的短板。

### 什么条件下会反悔

- 分块到十万级/召回质量要求提高 → 建 ANN、评估 rerank/混合检索；当前 flat scan。
- 多进程/多实例访问同一索引 → 需要跨进程锁/服务化；当前 `index_lock` 只是进程内。
- 远端嵌入成为默认 → 要处理离线降级、模型版本/维度迁移；当前本地嵌入是默认。

## 我会的部分

- 用 Arrow `RecordBatch` + `FixedSizeList` 建 Lance 表，做 Overwrite/Add/Delete/Count。
- 设计「文本镜像 + 向量表」的可重建结构，并记录 embedder 身份。
- 用 SQLite 镜像回填索引，处理「导入的书搜不到」这类空镜像场景。
- 用每项目锁串行化索引写与检索。
- 写离线测试：不联网、不调模型，用本地哈希嵌入验证检索结果。

## 边界

- 没建 ANN 索引，也没测过大数据量；「几千块 flat scan 够用」是设计判断，不是压测结论。
- 本地嵌入是**词面**检索，不是语义检索；同义改写、跨语言查询召回差，注释里已写明（`novelforge/src-tauri/src/agents/provider.rs:831-841`）。
- 远端嵌入只写在代码路径里，没有真实服务跑通的记录；且模型必须支持 `dimensions` 参数，否则固定 384 维会拒绝。
- 没有混合检索（BM25 + 向量）、没有 rerank、没有查询改写。
- 没有跨进程/多实例并发控制；`index_lock` 只是进程内。
- 没有备份/压缩/迁移 Lance 目录的专门工具；索引按设计可丢弃，所以没做。

## 相关技能

[[Tauri与Rust IPC]]、[[keyring与Provider]]

## 用在哪些工程能力

RAG、本地检索、向量数据库、嵌入服务适配、离线可用性
