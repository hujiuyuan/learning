---
type: 技能点
域: 前端
项目: [smart WMS]
证据: 实战/设计
---

# Vue3

所属通用技能：[[前端与Vue3]]

**一句话**：Vue 3 的日常是四件事——用 `script setup` 声明组件，用 `ref/computed` 描述状态，用 props/emit/slot 组合组件，用 Pinia + 路由守卫把跨页状态和权限串起来。

## 方法总纲

1. **组合式 API**：`<script setup>` 顶层声明即组件体；`defineProps`/`defineEmits` 声明接口；`defineOptions({ name })` 给 KeepAlive 用。
2. **响应式**：`ref` 包基本值，`reactive` 包对象，`computed` 派生，`watch`/`watchEffect` 做副作用；模板里 ref 自动解包。
3. **组件通信**：props 下行、emit 上行、slot 留结构；跨层用 provide/inject（MeCrud 用它把折叠状态给查询项）。
4. **生命周期**：`onMounted` 初始化；`onActivated/onDeactivated` 配合 KeepAlive 处理页签切换。
5. **路由**：`useRoute/useRouter` 取参数和跳转；全局守卫做登录态、动态路由、页签。
6. **Pinia**：`defineStore` 的 state/getters/actions；`pinia-plugin-persistedstate` 按字段持久化。
7. **权限**：路由 meta 带按钮码，自定义指令在 mounted 时移除无权限元素。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| 派送拼车弹窗按派送单粒度分组/排序 | 实战 | smart WMS（OMP） | 2026-08 | [[组件拆分]] |
| 出货任务展开区 Actions 列与 Delivery Info 弹窗 | 实战 | smart WMS（OMP） | 2026-08 | [[组件拆分]] |
| 列表勾选跨页记忆 | 实战（已回滚） | smart WMS | 2026-08 | [[组件拆分]] |
| 表格多行文本保留换行 | 实战（已回滚） | smart WMS | 2026-08 | [[组件拆分]] |
| 签到页展示多提顺序 | 实战（已回滚） | smart WMS | 2026-08 | [[组件拆分]] |

## 选型与取舍

### 为什么用 Vue 3，不用 Vue 2 / React

- 项目已有 Vue 2/3 代码和组件库（Naive UI/MeCrud），Vue 3 的组合式 API 更适合按业务拆分 composable；Vue 2 已停止维护，继续停留没有收益。
- 代价：Vue 生态在复杂状态/跨端/SSR 上不如 React/Next 丰富；团队要熟悉 `ref` 解包、响应式丢失、`script setup` 编译宏。项目没有 SSR/SEO 需求，Vue 的轻量和现有组件库更划算。
- 如果要做内容站/SEO/React 生态组件，Next.js 更合适；当前是后台管理系统，Vue 3 足够。

### 为什么用组合式 API，不用 Options API

- 组合式 API 把同一业务的状态/计算/副作用放在一起，逻辑可以抽成 composable 复用；TS 类型推导也比 Options 的 `this` 更直接。
- 代价：`ref`/`reactive` 的响应式规则、解包、生命周期要重新学；团队里仍有 Options API 代码（OMP 拼车弹窗），两套风格并存。
- 不是「Options 不能用」：简单组件用 Options 更直观；项目新代码统一组合式，旧代码不强制重写，避免无收益迁移。

### 为什么用 Pinia，不用 Vuex

- Pinia 的 store 是普通函数/对象，TS 推导好、模块不需要嵌套 `modules`，持久化插件也简单；Vuex 的 mutation/action 分层在中小项目里是额外样板。
- 代价：Pinia 的 store 可以互相引用，容易形成循环依赖；持久化字段要显式选，不能整个 store 无脑存。项目 auth store 只持久化 key（`auth.js:121-123`），app store 按字段存 sessionStorage（`app.js:65-68`）。
- 如果项目已经大量 Vuex 代码，迁移收益低；新项目/新模块用 Pinia。

### 为什么权限用路由 meta + 指令，不只靠后端

- 前端权限只决定「看不看得见」：路由 meta 的按钮码 + 自定义指令移除无权限元素，减少误操作；真正的授权仍在后端（见 [[认证与授权]]）。
- 代价：前端权限码和后端权限码要同步，漏一处会出现「按钮可见但接口 403」；指令在 mounted 时移除元素，动态新增的 DOM 不会自动处理。
- 这不是安全边界：隐藏按钮不等于阻止请求；后端必须独立校验。

### 什么条件下会反悔

- 需要 SSR/SEO/跨端 → 评估 Nuxt/Next；当前后台系统不需要。
- 组合式 composable 过多、逻辑分散 → 收敛领域 store/组合函数；当前按页面拆，尚未失控。
- 前端权限码频繁不同步 → 由后端下发菜单/按钮树，前端不再手写码；当前是静态 meta。

## 我会的部分

- **script setup + props/emit**：`smart-web-wms/src/components/me/crud/index.vue:89-116`；`MeModal` 的 props、slot、footer（`src/components/me/modal/index.vue:1-66`）。
- **defineOptions 与 KeepAlive**：组件名必须等于路由 code，否则缓存命中不了（`src/views/packing-list/packingList.vue:8-9`、`src/views/shipping-task/shippingTask.vue:2199`）。
- **computed 派生展示**：签到抽屉按 `pickupType` 和 `planTaskTotal` 决定是否显示提货顺序（commit `db6fbfb` 改 `src/views/shipping-task/shippingTask.vue`，已被 `884446e` 回滚，当前代码不含）。
- **ref 合并跨页选择**：`selectedRows` 按业务 `id` 保留其他页，`checkedRowKeys` 只反映当前页（commit `d493fd8` 改 `src/views/wms/wms.vue`，已被 `7057a51` 回滚，当前代码不含）。
- **渲染函数 h**：菜单图标用 `h('i', { class })` 生成（`src/store/modules/permission.js:32`）。
- **Pinia**：auth store 存 access/refresh 和代登录上下文（`src/store/modules/auth.js:5-15`）；persist 只留 key（`auth.js:121-123`）；app store 按字段持久化到 sessionStorage（`src/store/modules/app.js:65-68`）。
- **路由守卫**：`permission-guard.js:5-50` 串起白名单、拉权限、`addRoute`、404 兜底；页签守卫在 `afterEach` 里加 tab（`src/router/guards/tab-guard.js:5-15`）。
- **权限指令**：`src/directives/index.js:4-15` 按 `route.meta.btns` 移除元素；`setupDirectives` 在 `:210-211` 注册。
- **Options API**：omp 的拼车弹窗仍是 Options API（`smart-web-omp/src/views/goods/deliveryCarpool.vue:234-291`），我用 `computed/data/methods` 改功能。

## 边界

- 只写过 Vue 3；没做过 Vue 2 → 3 迁移。
- 没写过 `<script setup lang="ts">`；两个 Vue 仓库零 `.ts`。
- 没写过自定义响应式（`customRef`/`effectScope`），没发布过组件库。
- KeepAlive 只按 name 用；页签刷新靠 `reloadTab` 临时移出缓存（`src/store/modules/tab.js:39-63`），没做过更细的缓存失效。
- Vue 项目没做过 SSR、Teleport 复杂场景、Suspense；React/Next 的 SSR 见 [[React与Next.js]]。

## 相关技能

- [[TypeScript与Vite]]
- [[组件拆分]]
- [[前端i18n]]

## 用在哪些工程能力

- [[Spring应用与接口契约]]：前端按 `Result` 的 `code/message/data` 判断成败（`smart-web-wms/src/utils/http/interceptors.js:8-32`）。
- [[认证与授权]]：登录态、代登录、菜单权限的前端侧。
- [[时区与时间序列化]]：请求层统一转换时间字段（`interceptors.js:41-44`），展示层按用户时区。
