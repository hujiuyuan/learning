---
type: 项目证据
时间: 2026-10
技术栈: [Playwright, TypeScript, Node.js]
---

# e2e-hub

**定位**：多前端共用的 Playwright 测试台；统一 fixture 采集接口/console/i18n，自研 reporter 出单文件 HTML + `summary.json`。

**模块 → 相关节点**

| 模块 | 相关节点 |
| --- | --- |
| 多端配置 | [[测试与质量]]、[[Playwright]] |
| 接口采集与失败截图 | [[E2E报告]]、[[e2e-hub]] |
| 报告与历史对比 | [[E2E报告]] |
| muou 业务流 | [[muou]]、智能体（待建） |

**我在这里练到的技能**：[[测试与质量]]、[[Playwright]]、[[前端与Vue3]]

**源路径**：`/Users/hujiuyuan/studyspace/e2e-hub`

**规模**：2 个项目（demo/muou）；muou `flows` 下 21 个 `*.spec.ts`；2026-10-24 一次运行 69 条用例（48 passed / 21 skipped / 0 failed）。

**边界**：仓库 `main` 没有任何提交，文件未跟踪；没接 CI；只在 Chromium 上跑；数据依赖本机八个服务 + 网关 + 两个 dev server。
