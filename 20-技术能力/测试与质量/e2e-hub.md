---
type: 实践
技能点: Playwright
项目: [muou]
时间: 2026-10
证据: 实战
---

# e2e-hub

技能点：[[Playwright]] · 项目：[[muou]] · 2026-10

场景：[[E2E报告]]

## 我想干什么

把多个前端（运营后台 admin、官网 web、跨端主线）的 Playwright 脚本放进一个仓，一次跑多端，出一份非技术同事能直接打开的单文件报告：每一步调了哪些接口、哪里失败、慢在哪、和上次比有没有变差。

## 我干了什么

- **目录分层**：`reporter/` 放通用采集与报告，`projects/<项目>/` 放端配置与脚本，`reports/` 放产物，`bin/run.mjs` 是入口（`e2e-hub/README.md:19-29`）。
- **多端配置**：每个端一个 Playwright project，支持 `HUB_ENDS` 过滤、`dependencies`、按端覆盖超时和 locale（`e2e-hub/reporter/define.ts:9-31`）；muou 定义 admin/web/cross 三端（`e2e-hub/projects/muou/hub.config.ts:19-32`）。
- **setup 先行**：先跑 `support/baseline/*.setup.ts` 建基线、经真实登录页存 storageState，admin/web 依赖它（`e2e-hub/projects/muou/playwright.config.ts:28-45`）。
- **统一采集**：从 `reporter/fixture` 引 `test/expect`，自动记录接口、状态码、耗时、请求/响应体、console、i18n key（`e2e-hub/reporter/fixture.ts:62-215`）。
- **失败证据**：失败截图最多 3 个窗口，接口报错也截图，报错提示画红框（`e2e-hub/reporter/fixture.ts:95-110`、`:203-209`、`:217-234`）。
- **自研 reporter**：汇总用例、分类、问题清单、慢接口、与上次对比，写 `summary.json` 和单文件 HTML（`e2e-hub/reporter/hub-reporter.ts:147-249`）；渲染层把数据与截图内嵌（`e2e-hub/reporter/render.ts:3`）。

## 犯了什么错 / 误判

- **把「有脚本」当成「都跑了」**：69 条总数看起来像全覆盖，实际 21 条是 skipped（`e2e-hub/reports/muou/20261024183327/summary.json:1`）。
- **把浏览器取消的请求当接口故障**：页面导航、组件卸载会取消请求；不排除的话一次导航刷出几十条「接口连不上」，真故障被淹掉。后来显式忽略 `net::ERR_ABORTED`（`e2e-hub/reporter/hub-reporter.ts:85-90`）。
- **把页面关闭时在飞的请求当超时**：用例收尾关窗口，响应还没回来；后来给窗口关闭打 `closed` 标记，并给收尾 5 秒宽限（`e2e-hub/reporter/fixture.ts:126-131`、`:181-188`）。
- **只在失败时截图**：接口报错但用例没失败时没有证据；后来接口一报错就截，2 秒内同一窗口只截一张（`e2e-hub/reporter/fixture.ts:90-110`）。
- **把重跑才过算通过**：重跑能过其实是不稳定；后来单列 flaky，报告写「第 N 次才过」（`e2e-hub/reporter/hub-reporter.ts:254`、`e2e-hub/reporter/render.ts:176`）。

## 怎么解决

- 失败分类按「越像产品坏了越靠前」排序，先看接口 5xx/超时/连不上，再看页面和用例自身（`e2e-hub/reporter/hub-reporter.ts:93-107`）。
- 慢接口只报警、不判失败，避免环境抖动把用例染红（`e2e-hub/reporter/render.ts:231`）。
- 脚本没写 `test.step` 时，把每个页面动作自动成步并带上源码行，报告仍然可读（`e2e-hub/reporter/hub-reporter.ts:312-353`）。
- 脚本没写说明头，报告里标红「缺说明头」，逼着补（`e2e-hub/reporter/hub-reporter.ts:109-136`）。
- 报告与上一次对比，标出新增失败、已修复、仍失败和连续失败次数（`e2e-hub/reporter/hub-reporter.ts:193-201`）。

## 现在的规矩

- 脚本必须从 `reporter/fixture` 引 `test/expect`，否则接口不会被记录（`e2e-hub/README.md:33`）。
- 每个脚本写说明头（`@名称`/`@流程`），业务动作包 `test.step`（`e2e-hub/README.md:34-44`）。
- 反向验证用 `expectApiError` 声明，不要靠注释说明（`e2e-hub/README.md:46`）。
- 失败先看分类，再看截图/接口记录，最后看 trace。
- flaky 单列；报告留最近 10 次。
- 不写「已纳入 CI」：仓里没有 CI 配置，跑法仍是手动 `node bin/run.mjs`（`e2e-hub/README.md:9-12`）。

## 证据

- 代码：`e2e-hub/reporter/fixture.ts`、`hub-reporter.ts`、`render.ts`、`define.ts`；`e2e-hub/projects/muou/playwright.config.ts`、`hub.config.ts`。
- 文档：`e2e-hub/README.md:1-54`。
- 报告：`e2e-hub/reports/muou/20261024183327/summary.json:1`（69 条：48 passed / 21 skipped / 0 failed；2 个问题；85 次慢请求）；同目录 `20261024183327-muou.html`（2.1 MB，截图 base64 内嵌）。
- 规模：`projects` 下 2 个项目（demo/muou）；muou 的 `flows` 下 21 个 `*.spec.ts`（`find projects/muou/flows -name '*.spec.ts' | wc -l`）。
- **版本证据**：`e2e-hub` 的 git 仓库在 `main` 分支上没有任何提交，所有文件未跟踪；这份实践只能靠文件与报告证明，不能靠 commit 证明。
