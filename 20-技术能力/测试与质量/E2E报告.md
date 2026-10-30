---
type: 场景
技能点: Playwright
方法: 自研 reporter 出单文件报告
证据: 实战
---

# E2E报告

技能点：[[Playwright]] · 方法：自研 reporter 出单文件报告（待建） · 通用技能：[[测试与质量]]

**什么时候会遇到**：多端 E2E 跑完，要让开发、产品、测试一起看结果；Playwright 自带的 HTML 报告要起服务、截图和接口信息分散，失败原因还要人工翻日志。

## 判断顺序

拿到一份报告，按这个顺序看：

1. **总览**：通过/失败/问题/慢接口各多少，和上一次比是变好还是变差。
2. **失败分类**：接口 5xx → 超时未返回 → 接口连不上 → 接口 4xx → 多语言 key → 控制台报错 → 页面显示不对 → 用例自身/环境。越靠前越像产品问题（`e2e-hub/reporter/hub-reporter.ts:93-107`）。
3. **用例步骤**：每一步调了哪些接口、状态码、耗时、请求/响应体；慢的标黄/标红。
4. **截图**：失败截图里报错提示有没有红框；接口报错但用例没失败时也有截图。
5. **trace**：需要回放时按报告给出的 `show-trace` 命令看。
6. **慢接口榜**：按接口聚合调用次数、平均、P95、最慢；只作为优化线索。
7. **summary.json**：机器可读，供下一次对比。

## 手段

- **单文件 HTML**：数据、样式、截图 base64 全内嵌，直接发给别人双击就能看（`e2e-hub/reporter/render.ts:3`；2026-10-24 那份文件 2.1 MB）。
- **接口四态**：成功、失败（4xx/5xx）、慢（超过 `slowMs`）、超时未返回/连不上；预期报错单独标蓝（`e2e-hub/reporter/render.ts:161`）。
- **失败分类**：按「越像产品坏了越靠前」排序，避免把环境问题排在第一（`e2e-hub/reporter/hub-reporter.ts:93-107`）。
- **红框**：把 `errorSelectors` 命中的报错提示框出来再截图（`e2e-hub/reporter/fixture.ts:217-234`）。
- **慢接口榜**：超过 `slowMs` 标红、`warnMs`～`slowMs` 标黄；只报警、不判用例失败（`e2e-hub/reporter/render.ts:225-238`）。
- **与上次对比**：新增失败、已修复、仍失败、失败连续次数；KPI 显示增减（`e2e-hub/reporter/hub-reporter.ts:193-201`、`e2e-hub/reporter/render.ts:123-131`）。
- **保留历史**：每个项目留最近 10 次报告（`e2e-hub/reporter/hub-reporter.ts:247`、`:393-399`）。

## 反例 / 边界

- **报告绿 ≠ 覆盖全**：2026-10-24 那次是 69 条用例、48 passed、21 skipped、0 failed；skipped 不算通过（`e2e-hub/reports/muou/20261024183327/summary.json:1`）。
- **慢接口不判失败**：慢只是线索，环境抖动也会慢；不能拿它卡发布（`e2e-hub/reporter/render.ts:231`）。
- **红框依赖选择器**：`errorSelectors` 没覆盖的提示不会画框，截图只能看到原页面（`e2e-hub/projects/muou/hub.config.ts:50-53`）。
- **trace 不内嵌**：报告只给路径和命令，换机器可能打不开（`e2e-hub/README.md:15`）。
- **报告好看依赖脚本规范**：没写说明头会在报告里标红「缺说明头」；没写 `test.step` 就按页面动作自动成步（`e2e-hub/README.md:34-44`）。
- **没有 CI**：报告是手动跑出来的，不能当「每次提交都验证过」（`e2e-hub/README.md:9-12`；仓库内无 CI 配置）。

## 现在的规矩

- 每次跑完发单文件 HTML，不发截图拼图、不发终端日志。
- 看失败先看分类，再看用例步骤和截图，最后才看 trace。
- flaky 单列，不混进稳定通过。
- 慢接口榜只用于排优化优先级，不当作发布门禁。
- 报告留最近 10 次，用 `summary.json` 做对比。

## 相关实践

[[e2e-hub]]

## 来源

- `e2e-hub/reporter/hub-reporter.ts`
- `e2e-hub/reporter/render.ts`
- `e2e-hub/reporter/fixture.ts`
- `e2e-hub/reports/muou/20261024183327/summary.json`
- `e2e-hub/README.md`
