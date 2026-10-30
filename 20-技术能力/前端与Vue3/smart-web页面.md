---
type: 实践
技能点: Vue3
项目: [smart WMS]
时间: 2026-06 ~ 2026-08
证据: 实战
---

# smart-web页面

技能点：[[Vue3]] · 项目：[[smart WMS]] · 2026-06 ~ 2026-08

场景：[[组件拆分]]

## 我想干什么

把老 PHP 前端的业务页迁到 Vue 3 新前端；同时维护 OMP 前端的派送拼车、出货任务页面。

## 我干了什么

**证据口径**：`smart` 目录本身不是 git 仓库，但两个前端各自是独立仓库；能证明归属的只有提交记录。下面分「提交仍在当前分支」和「提交被回滚」两类。

### 仍在当前分支

- **WMS 前端镜像 + CI**：两阶段 Dockerfile（node 22 构建、nginx 1.26 托管），CI 在 test 分支直接部署容器、main 推 Harbor；构建后断言 `index.html` 存在。证据：`smart-web-wms/docker/Dockerfile:1-35`、`smart-web-wms/.gitlab-ci.yml:35-66`、`docker/nginx.conf:1-28`；commit `75a0e77`、`8126248`、`85e8af4`。
- **OMP 派送拼车**：按派送单粒度重做分组与排序，提交时下发 `delivery_sort`，弹窗重开按 `group_seq` 还原。证据：`smart-web-omp/src/views/goods/deliveryCarpool.vue:173`、`:431-475`、`:709-852`；commit `0ff157a`、`77ab455`、`43d27a9`、`2b01e1d`、`6e97799`、`6968b94`。
- **OMP 出货任务**：展开区新增 Actions 列，按订单组看派送单；Delivery Info 弹窗改用 `planDeliveries`。证据：`src/views/car/index.vue:225-234`、`:975-1058`，`src/api/model/car.js:75-76`；commit `d642e3e`、`84e44ee`、`cd8bd2b`。
- **OMP 表格防空**：只读列 `data` 改可选链，避免 `data=null` 报错。证据：`src/views/common/showV2.vue:48`、`src/views/components/tableColumnFormat.vue:3-35`；commit `f166ff3`、`a5d728c`。

### 提交被回滚（做过，但当前分支没有）

- **列表勾选跨页记忆**：commit `d493fd8` 改 `src/views/wms/wms.vue`，被 `7057a51` 回滚。
- **多行文本保留换行**：commit `91e1da7` 改 `src/utils/common.js`，被 `023f088` 回滚。
- **签到页多提顺序**：commit `db6fbfb` 改 `src/views/shipping-task/shippingTask.vue`，被 `884446e` 回滚。

所以这三条只能算「我实现过」，不能算「现在生效」。

## 犯了什么错 / 误判

1. **把 WMS 当主战场**：三个业务修复都被 test 分支回滚，说明改动没通过验收或与 dev 分支冲突；当时只看了自己的提交，没跟分支流向。
2. **改提示只改了一个入口**：拼车错误提示先改了 `car/save.vue`，漏了 `goods/deliveryCarpool.vue` 和两个 `carSharing.vue`，第二次才补（`2da7a3b`）。
3. **默认后端字段一定有值**：表格列直接读 `row.data[column.label]`，`data=null` 就报错（`f166ff3`）。
4. **两套 row-key 混用**：勾选记忆按业务 `id` 合并，但表格 row-key 是 `id__index`，翻页后容易对不上。
5. **i18n 想当然**：以为 omp 接了 `vue-i18n` 就是全站多语言，实际只有登录页和设置页，业务页 0 处 `$t`。
6. **对接文档路径过期**：文档写 `GET /api/v1/wms-user/me`（`smart/docs/管理员账号切换-前端对接文档.md:77`），代码实际调 `/api/v1/me`（`smart-web-wms/src/api/admin.js:5`）；照着文档联调会 404。

## 怎么解决

- **回滚**：先确认 dev 上是否有等价实现，有就不在 test 重复提交；没有再把需求重新提出。
- **提示**：改提示前先 grep 所有 `$alert` 入口，统一 `replace(/\n/g, '<br>')` 再渲染。
- **表格**：只读场景 `data` 一律可选链；`v-model` 场景保持原样，避免改坏双向绑定（`a5d728c`）。
- **勾选**：`selectedRows` 按业务 `id` 跨页合并，`checkedRowKeys` 只反映当前页的渲染态。
- **i18n**：按页面统计 `$t` 覆盖率，写进 [[前端i18n]] 的边界。

## 现在的规矩

1. 改 UI 前先 grep 所有入口，不只改第一个看到的。
2. 渲染函数里对行字段一律可选链；数组/对象默认值写 `[]`/`{}`。
3. 提交后确认分支流向；被 revert 的改动不当已完成。
4. 前端改动至少本地跑 `pnpm dev` 和 `pnpm build:test`（wms 的 `package.json:8-10`）。
5. 说「我做过」必须能指到 commit 或当前代码行；只有代码存在就标「设计」。

## 证据

- 仓库：`/Users/hujiuyuan/workspace/voidtech/smart/smart-web-wms`（分支 `test`）、`/Users/hujiuyuan/workspace/voidtech/smart/smart-web-omp`（分支 `feature/pickup-delivery-orders`）
- 提交：`git log --author=hujiuyuan`；wms 11 条、omp 31 条
- 回滚：`git show 7057a51`、`git show 023f088`、`git show 884446e`
