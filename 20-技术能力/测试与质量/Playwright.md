---
type: 技能点
域: 测试与质量
项目: [muou]
证据: 实战
---

# Playwright

所属通用技能：[[测试与质量]]

**一句话**：Playwright 负责驱动真实浏览器；e2e-hub 在它上面补了统一 fixture 与自研 reporter，让脚本只写业务动作，接口、截图、失败分类交给框架。

## 方法总纲

1. **一个端一个 project**：`defineHubConfig` 把端配置展开成 Playwright projects，按文件名匹配脚本；有依赖的端挂 `dependencies`。
2. **共用服务就串行**：`workers: 1`，避免多个端同时改同一套测试库。
3. **失败重跑一次**：`retries` 默认 1；重跑才过记 flaky，和真失败分开。
4. **统一 fixture**：`test`/`expect` 从 `reporter/fixture` 引，自动监听每个 page 的请求、响应、console；多窗口、多 context 都挂上。
5. **失败留证据**：失败截图、接口报错截图、`trace: retain-on-failure`；截图里的报错提示画红框。
6. **报告与对比**：自研 reporter 汇总为单文件 HTML + `summary.json`，和上一次比新增失败/已修复/仍失败。
7. **反向验证**：`expectApiError` 声明「这里应该报错」，命中不算问题，没报出来算问题。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 多端跑测试（admin/web/cross） | 实战 | muou | 2026-10 | [[E2E报告]] |
| setup 先登录存 storageState | 实战 | muou | 2026-10 | [[E2E报告]] |
| 统一采集接口/console/i18n/截图 | 实战 | e2e-hub | 2026-10 | [[E2E报告]] |
| 自研 reporter 出单文件报告 | 实战 | e2e-hub | 2026-10 | [[E2E报告]] |

## 选型与取舍

### 为什么用 Playwright，不用 Cypress / Selenium

- Playwright 支持多浏览器/多 context、自动等待、trace、网络拦截和下载；一个脚本可以开多个窗口/租户，适合 muou 的 admin/web/cross 多端场景。
- 代价：生态/教程比 Selenium 少，CI 要装浏览器；多浏览器矩阵要自己配。项目目前只在 Chromium 上跑，跨浏览器仍未验证。
- Cypress 的开发体验好、时间旅行调试强，但多 tab/跨域/多浏览器能力弱；Selenium 生态最广但等待/稳定性要自己封装。项目选 Playwright，是多端/多 context 和 trace 的收益更大。

### 为什么在 Playwright 上再包一层 e2e-hub，不直接写原生脚本

- e2e-hub 把登录态、接口采集、console/pageerror、截图红框、trace、flaky 分类、HTML 报告统一到 fixture/reporter；业务脚本只写动作和断言，失败证据自动留。
- 代价：多一层自研框架要维护，Playwright 升级/配置变化要跟着改；新人要先学 hub 的 `defineHubConfig`/fixture，不能直接照搬网上示例。
- 如果只有少量一次性脚本，原生 Playwright 更快；项目多端、多环境、需要报告对比，包一层划算。

### 为什么 `workers: 1`、共用服务

- muou 的 E2E 要连本机八个服务 + 网关 + 两个 dev server，共用一套测试库；并行 worker 会互相改数据，失败难定位。串行换稳定。
- 代价：跑得慢；用例多了会成为瓶颈。项目当前 21 个 flow/69 条用例，串行可接受。
- 如果以后按租户/数据隔离出独立库，可以并行；当前没有做数据隔离，串行是明确取舍。

### 为什么失败重跑一次、flaky 单列

- 环境/网络抖动会造成的偶发失败，重跑一次能区分「真失败」和「不稳定」；但重跑才过不能算稳定通过，报告单独标 flaky。
- 代价：多跑一次增加时间；如果 flaky 率高，重跑会掩盖测试自身的时序/数据缺陷。项目用报告对比和红框截图追根因，不把 flaky 混进通过率。
- 如果 CI 时间敏感，可以减少 retries，但必须保留 flaky 统计；不能直接 `retries: 0` 把不稳定当失败/通过。

### 什么条件下会反悔

- 需要跨浏览器/移动端 → 配 webkit/firefox/设备矩阵；当前只跑 Chromium，是已知缺口。
- 用例多到串行跑不完 → 做数据隔离/分片并行；当前共用库，不能直接加 worker。
- e2e-hub 维护成本高于收益 → 回退原生 Playwright + 现成 reporter；当前多端报告需求还在。

## 我会的部分

- **多项目多端**：`e2e-hub/reporter/define.ts:9-31` 把每个端展开成 project，支持 `HUB_ENDS` 过滤、`dependencies`、按端覆盖 timeout/locale；`e2e-hub/projects/muou/hub.config.ts:19-32` 定义 admin/web/cross 三端。
- **setup 依赖**：`e2e-hub/projects/muou/playwright.config.ts:28-45` 先跑 `support/baseline/*.setup.ts` 建基线、存登录态，再让 admin/web 依赖它。
- **fixture 采集**：`e2e-hub/reporter/fixture.ts:62-215` 自动挂 `request/response/requestfailed/console/pageerror`；`e2e-hub/reporter/fixture.ts:132-153` 记录状态码、耗时、请求/响应体、traceId，敏感字段打码、超长截断。
- **截图与红框**：`e2e-hub/reporter/fixture.ts:95-110` 接口报错后在页面上画红框再截图；`e2e-hub/reporter/fixture.ts:217-234` 用 `#dc2626` 边框标出 `errorSelectors` 命中的元素；`e2e-hub/reporter/fixture.ts:203-209` 失败时最多截 3 个窗口。
- **trace**：`e2e-hub/reporter/define.ts:22` 配 `retain-on-failure`；`e2e-hub/reporter/hub-reporter.ts:290-291` 把 trace 路径写进报告。
- **反向验证**：`e2e-hub/reporter/fixture.ts:14-16` 把 `expectApiError` 写成 annotation；`e2e-hub/reporter/fixture.ts:197-198` 检查声明了却没报错的用例。
- **flaky 判定**：`e2e-hub/reporter/hub-reporter.ts:254` 把 Playwright 的 `flaky` outcome 单列；`e2e-hub/reporter/render.ts:176` 显示「第 N 次才过」；`e2e-hub/reporter/hub-reporter.ts:238-245` 的 summary 把 flaky 计入通过但报告里单独标注。
- **muou 仓内还有一套 spec**：`muou-web/e2e` 10 个 + `muou-admin/e2e` 7 个 = 17 个提交过的 e2e spec，另有 20 个 `e2e-dev` 开发态 spec；这些和 e2e-hub 的 21 条 flow 是两套，不要混成一个数字。两套都没有接 CI，仍是手动跑。

## 边界

- **只在 Chromium 上跑**：配置里没有 `browserName`，也没配 webkit/firefox 矩阵（`e2e-hub/reporter/define.ts:12-31`），跨浏览器未验证。
- **数据靠真服务**：muou 要本机八个服务 + 网关 + 两个 dev server（`e2e-hub/README.md:54`）；环境不稳时报告里的失败要先排除环境。
- **报告不内嵌 trace**：只给 `show-trace` 命令（`e2e-hub/README.md:15`）。
- **没接 CI**：仓里没有 `.github/`、`.gitlab-ci.yml`、`Jenkinsfile`，仍是手动 `node bin/run.mjs`（`e2e-hub/README.md:9-12`）。
- **没写过**：组件测试（Playwright CT）、视觉回归、API-only 测试、多浏览器矩阵、并行 worker。
- **慢接口只报警**：`e2e-hub/reporter/render.ts:231` 明确「只报警、不判用例失败」，慢不等于功能坏。

## 相关技能

[[JUnit与Testcontainers]]、[[E2E报告]]

## 用在哪些工程能力

端到端回归、前后端联调、发布前验收、线上问题复现。
