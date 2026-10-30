---
type: 技能点
域: 后端
项目: [claude-team]
证据: 实战/设计
---

# Claude Code与Agent

所属通用技能：[[工程效率与AI]]

**一句话**：Claude Code 的扩展点是 Skill、Agent、Plugin、Hook、MCP；我的用法是把「角色 = 提示词 + 预加载技能」打包成插件市场，用盲审 + 裁判降低单模型误判，用 ccds worker 干可验收的活，worktree 是并行时的隔离方案。

## 方法总纲

- **Skill**：可复用的流程、模板、清单；角色 frontmatter 的 `skills:` 在作为子代理启动时全文预加载（`claude-team/README.md:227-230`）。
- **Agent**：一个角色一个提示词文件，frontmatter 定 `name`、`description`、`tools`、`model`、`skills`（`claude-team/README.md:211-225`）。
- **Plugin / marketplace**：每个 `roles/<角色>` 是一个插件，仓库本身是插件市场；一条命令安装，跨电脑复用（`claude-team/README.md:26-50`）。
- **Hook**：插件可以注册钩子；我只在 ccds-panel 里见过注册（`claude-team/roles/ccds-panel/hooks/hooks.json:1`）。
- **MCP**：没有用过，仓库里也没有 MCP 配置；不把理论写进「我用过」。
- **角色分工**：team 核心管通用习惯、辩证裁决、组队、文档；architect 只读出方案；developer 实现；reviewer 只读评审；writer 写文档（`claude-team/README.md:13-24`）。
- **盲审 / 裁判**：L1 问题先跑 2 名盲审分析员，互看不到产出；裁判只按带出处的论据裁决；两人推荐不一致或涉及业务取舍时升辩论（`claude-team/roles/team/skills/deliberate/SKILL.md:29-41`、`:78-113`）。
- **ccds 派活**：官方会话拆任务、写 brief、验收；worker 读代码、改代码、跑验收命令；worker 被禁止 commit/push（`claude-team/roles/team/skills/ds-dispatch/SKILL.md:8-11`、`:30-65`）。
- **worktree**：改代码的 worker 一个一台 worktree，`--cwd` 指过去，验收后 merge 再删（`claude-team/roles/team/skills/ds-dispatch/SKILL.md:87-92`、`:117-119`）。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 建 claude-team 插件市场：5 个角色 + team 核心技能 | 实战 | claude-team | 2026-10 | 多 Agent 协作（待建） |
| 用盲审 + 裁判补技能图谱 | 实战 | learning | 2026-10 | 多 Agent 协作（待建） |
| 用 ccds worker 派可验收的编码任务 | 实战 | — | 2026-09 | 多 Agent 协作（待建） |
| 用 worktree 并行改代码 | 设计/方案 | — | 2026-09 | 多 Agent 协作（待建） |

证据：
- 插件市场与角色组成：`claude-team/README.md:1-3`、`:13-24`、`:211-230`
- 盲审 + 裁判实际运行：`~/.claude-team/runs/20261029-技能图谱补充/rounds/C1-1-甲.md:1-3`、`~/.claude-team/runs/20261029-技能图谱补充/rounds/C1-4-裁判.md:1-9`、`~/.claude-team/runs/20261029-技能图谱补充/verdicts.md:3`
- ccds 派活与实测：`claude-team/roles/team/skills/ds-dispatch/SKILL.md:69-82`
- worktree 流程：`claude-team/roles/team/skills/ds-dispatch/SKILL.md:87-92`

## 我会的部分

- 角色文件：frontmatter 最小工具集、只读角色去掉 Write/Edit/Agent、技能全名 `<插件>:<技能>`（`claude-team/CLAUDE.md:11-17`）。
- 主持辩证裁决：问题卡、盲审原文、T1/T2、裁判、决策日志、问题池（`claude-team/roles/team/skills/deliberate/SKILL.md:72-113`、`:194-208`）。
- 写裁决协议：原文落盘、逐字比对、写入范围核对（`claude-team/roles/team/skills/deliberate/SKILL.md:43-60`）。
- ccds brief：目标、背景、相关文件、约束、验收命令、最终汇报格式；验收命令必须能跑（`claude-team/roles/team/skills/ds-dispatch/SKILL.md:30-65`）。
- 验收 worker：看 `git status` / `git diff --stat`、读 diff、亲自重跑每条验收命令、结论写回面板（`claude-team/roles/team/skills/ds-dispatch/SKILL.md:109-121`）。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| Claude Code（CLI/Agent）而不是纯补全 | 能读多文件、跑命令、按验收标准改代码；适合有明确边界的中等任务 | token 成本高、需要 review、会自信地编造未验证结论 | 单行补全/强 IDE 上下文 → Copilot/Cursor；安全敏感改动 → 人工为主 |
| 插件市场 + 角色提示词，而不是复制粘贴 prompt | 跨电脑复用、可版本化、角色/技能一致 | 插件结构/加载规则要维护；升级可能破坏旧角色 | 只有一两个 prompt → 直接放全局配置更简单 |
| 盲审 2 人 + 裁判，而不是单模型自问自答 | 降低单模型偏见；裁判按出处裁决，分歧才升级辩论 | 3–4 倍调用成本、延迟高；裁判也可能被错误出处误导 | 问题小/答案可 L0 查证 → 直接查，不起流程 |
| ccds worker 干可验收的活 | 省官方额度、可并行；任务边界清楚时性价比高 | 质量参差，验收成本转移到主会话；禁止 commit/push 要守住 | 安全/架构关键改动 → 官方模型 + 人工 review |
| worktree 隔离并行 worker | 每个 worker 独立目录/分支，互不踩未提交改动 | 合并/清理成本；依赖/服务要各自启动 | 只读任务 → 不需要 worktree |
| 不用 MCP（当前） | 没有实际需求，不把理论写成能力 | 失去外部系统集成能力 | 需要连数据库/工单/浏览器等外部系统 → 再评估 MCP |

## 边界

- MCP 没用过；Hook 只见过 ccds-panel 的注册，没自己写过通用 Hook。
- 没有团队级权限、配额、审计治理；角色只在本机个人使用。
- Agent teams 是实验功能，队友不会自动预加载技能，token 消耗更高（`claude-team/README.md:140-153`）。
- 盲审 + 裁判只用于「需要判断」的问题，不替代代码测试；裁判也只看证据，不跑全量回归。
- ccds worker 的汇报不能当验收结论，必须由人重跑命令、读 diff（`claude-team/roles/team/skills/ds-dispatch/SKILL.md:109-111`）。
- 看图找错别字的活不派给 DeepSeek：会把错别字顺手改对（`claude-team/roles/team/skills/ds-dispatch/SKILL.md:78`）。
- worktree 只写在流程里，没有运行记录证明并行跑过；本页标「设计/方案」。
- 没有 prompt 评测集；`validate.py` 只校验结构，不校验提示词效果（`claude-team/README.md:234`）。

## 相关技能

[[工程效率与AI]]、[[EasyCode与Velocity]]、[[CI-CD与部署]]

## 用在哪些工程能力

自动化评审、多 Agent 决策、任务分派、文档生产。
