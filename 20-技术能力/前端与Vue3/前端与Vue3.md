---
type: 通用技能
域: 前端
证据: 实战/设计
---

# 前端与Vue3

**一句话**：前端把页面拆成组件树，用状态存跨组件数据，用路由决定显示哪棵树，用请求层统一收口后端契约，用构建把源码变成可部署的静态文件；权限和 i18n 是横切所有层的两条规则。

**组内范围**：本组含 Vue 与 React/Next 两条并列栈；组名保留 `前端与Vue3` 是历史命名，不代表 React/Next 属于 Vue。React/Next 见 [[React与Next.js]]。

基础知识自测：[[前端与Vue3基础]]

> 四层读法：理论 [[前端与Vue3基础]]｜实践 本页「我用它干过什么」｜问题 [[组件拆分]]、[[前端i18n]]｜方案 [[smart WMS]]、[[muou]]。总入口 [[四层读法]]。

## 一、理论：六层

1. **组件化**：组件 = 模板 + 状态 + 事件；props 向下、emit 向上、slot 留空位。页面本身也是组件，布局只是包在外面的壳。
2. **状态**：只在本页用 → `ref`/`reactive`；跨页、跨组件 → Pinia/Vuex；要跨刷新保留才做持久化，且只挑字段。
3. **路由**：静态路由写在代码里；后端菜单驱动的动态路由要先拉权限、过滤本地路由表、再 `addRoute`。守卫负责登录态、标题、页签、404。
4. **请求层**：axios 实例 + 拦截器统一 baseURL、超时、token、错误提示、token 刷新；业务码和 HTTP 状态要分开判断。
5. **权限菜单**：后端返回 perm 集合，前端只做展示过滤；按钮级用指令或 `v-if`。前端权限不是授权。
6. **构建**：Vite 开发服务器 + 代理；环境变量按 mode 分文件；产物目录随 mode 变；镜像里校验产物存在。

## 二、实际使用：两个前端

### smart-web-wms（新前端）

- 技术栈：Vue 3.5 + Vite 6 + Pinia 3 + Naive UI + vue-router 4 + axios + UnoCSS（`smart-web-wms/package.json:18`、`:23`、`:24`、`:29`、`:31`、`:50`、`:53`）。
- 启动顺序：store → directives → router → mount（`smart-web-wms/src/main.js:14-21`）。
- 请求层：实例和超时分两处配（`src/utils/http/index.js:8-18`）；成功码是 `['OK', 0, '0', 200, '200']`，业务 401 走刷新（`src/utils/http/interceptors.js:8-32`）；请求前带 Bearer（`interceptors.js:62-66`）。
- 动态路由：无 token 先跳登录；有 token 拉 profile + 权限，过滤路由后 `addRoute`（`src/router/guards/permission-guard.js:5-50`）。
- 菜单：权限树按 `permName === route.code` 匹配（`src/store/helper.js:70-73`、`:126-129`），再生成 Naive UI menu（`src/store/modules/permission.js:12-19`）。
- 布局：`full` 布局 = 顶栏 + Logo + 侧栏 + 内容插槽（`src/layouts/full/index.vue:1-24`）；`App.vue` 按 `route.meta.layout` 动态加载布局（`src/App.vue:32-40`、`:87-91`）。
- 构建：代理 `/proxy` 转发到 `VITE_PROXY_TARGET`（`vite.config.js:45-67`）；产物目录取 `VITE_OUTDIR`（`vite.config.js:68-71`）。
- 我落地的构建链路：两阶段 Dockerfile + 容器内 nginx（`docker/Dockerfile:1-35`，commit `75a0e77`），GitLab CI 在 test 直发容器、main 推 Harbor（`.gitlab-ci.yml:35-66`，commit `85e8af4`）。

### smart-web-omp（OMP 前端，vue-cli 工程）

- 技术栈：Vue 3.2 + Element Plus + Vuex 4 + vue-i18n 9 + vue-cli 5（`smart-web-omp/package.json:22`、`:30`、`:33`、`:37`、`:46`）。
- hash 路由（`src/router/index.js:22-25`）；动态路由把本地路由和后端菜单合并后 `addRoute('layout', ...)`（`src/router/index.js:68-80`）。
- 权限：全局方法 `$AUTH`/`$ROLE`（`src/scui.js:43-44`），底层是 `PERMISSIONS.includes(code)`（`src/utils/permission.js:3-10`）。
- 请求层：全局 axios 拦截器，401 直接跳登录，没有刷新 token（`src/utils/request.js:12-28`、`:31-79`）。

## 三、归纳：前端检查清单

1. **数据从哪来**：URL 是否集中在 `api/`，页面里有没有散落 `fetch`。
2. **状态放哪**：本页 / 跨页 / 要持久化，三档选一。
3. **路由四件事**：登录态、权限过滤、404 与 403 区分、刷新后能重建。
4. **请求层统一**：baseURL、超时、token、错误提示、401 刷新只在一个地方写。
5. **错误去重**：同一个错误短时间只弹一次（wms 用 1.5 秒 TTL，`src/utils/http/helpers.js:5-36`）。
6. **权限前端过滤、后端校验**：菜单能藏，接口不能只靠藏。
7. **时间转换一次**：请求层统一转（`interceptors.js:41-44`），页面不再各自换算。
8. **组件边界**：页面壳、查询区、表格、弹窗分开；单文件过千行就是拆分信号。
9. **构建产物可验证**：Docker/CI 里检查 `index.html` 真的存在。
10. **i18n 要么全接要么不接**：半接的页面不算支持多语言。

## 四、回到理论

- 这六层换任何框架都在：React 用 props/hooks/context/router/axios，名字不同，职责一样。
- 动态路由的本质是「后端数据 → 前端路由表」；刷新后必须能重建，所以 `addRoute` 要放在守卫里可重复执行。
- 请求层是前端唯一看得见后端契约的地方；后端 HTTP 200 + body code 时，判断只能看 body（见 [[Spring应用与接口契约]]）。
- 前端权限只影响「看不看得见」，不影响「调不调得动」；真正的授权在后端（见 [[认证与授权]]）。

## 五、边界

- Vue 项目只做过 Vue 3；没做过 Vue 2 迁移、Nuxt/SSR、微前端。React/Next 项目有 SSR（muou-web），见 [[React与Next.js]]。
- 两个 Vue 仓库都零 `.ts`；TypeScript 只在另一个项目里读过，见 [[TypeScript与Vite]]。
- wms 没写过前端测试（`package.json` 没有 test script）；muou-admin/muou-web 有 702 个 Vitest/RTL 测试文件，另有 17 个 Playwright spec，但不是本页 Vue 3 的证据，见前端测试（待建）。
- 构建只做到「能出镜像」，没做过分包策略、CDN、性能预算；`rollup-plugin-visualizer` 装了但 `vite.config.js` 没引用。
- 前端权限是展示级；生产接口授权是否生效见 [[认证与授权]] 的边界。
- i18n 只在 omp 模板层，业务页没覆盖，见 [[前端i18n]]。

## 相关

- 技能点：[[Vue3]]、[[TypeScript与Vite]]
- 场景：[[组件拆分]]、[[前端i18n]]
- 实践：[[smart-web页面]]
- 项目：[[smart WMS]]
- 相邻通用技能：[[Spring应用与接口契约]]、[[认证与授权]]、[[时区与时间序列化]]
