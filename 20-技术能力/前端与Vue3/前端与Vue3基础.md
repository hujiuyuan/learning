---
type: 基础能力
通用技能: 前端与Vue3
域: 前端与Vue3
证据: 学习中
---

# 前端与 Vue3 基础

通用技能：[[前端与Vue3]] · 定位：基础知识挂载页

**一句话**：前端与 Vue3 基础题的分类索引。这里回答「应该会什么」，不冒充「我做过什么」；做过的事仍记在实践卡。**本组含 Vue 与 React/Next 两条并列栈**，基础题以通用前端为主，React/Next 专属内容见 [[React与Next.js]]。

## 怎么用

- 自测：看每一块的「要能回答」，能用自己的话讲清楚才算过。
- 挂笔记：新写一篇八股文，在对应块的「笔记」后加 `笔记名`，笔记里链回本页。
- 分边界：原理和机制放这里；具体故障、排查过程、修复方案放场景/实践卡。

## 1. HTML / CSS / JavaScript

**一句话**：HTML 定义结构，CSS 负责布局和样式，JavaScript 负责行为；盒模型、层叠、事件循环是前端基础中的基础。

要能回答：

- 盒模型是什么？`box-sizing: border-box` 改变了什么？
- 块级、行内、行内块元素的区别？
- Flex 和 Grid 分别适合什么布局？
- 事件冒泡、捕获、委托分别是什么？
- 事件循环里宏任务和微任务怎么执行？
- `var`、`let`、`const` 的区别？闭包是什么？

笔记：

- 盒模型：content + padding + border + margin；`box-sizing: border-box` 让设置的 `width` 包含 padding 和 border，布局按「最终占位」算，少算错尺寸。
- 块级独占一行、可设宽高；行内按内容排、宽高/上下 margin 受限；`inline-block` 行内排列但可设宽高。Flex 适合一维排列（行或列），Grid 适合二维网格。
- 事件捕获从外到内、冒泡从内到外；`addEventListener(type, fn, true)` 捕获。事件委托把监听放在父元素，靠冒泡处理子元素事件，减少监听器、支持动态子节点。
- 事件循环：同步代码 → 微任务（Promise、queueMicrotask）全部清空 → 宏任务（setTimeout、事件、I/O）取一个 → 再清微任务。微任务会饿死渲染。
- `var` 函数作用域、变量提升、可重复声明；`let/const` 块级作用域、暂时性死区；`const` 只保证绑定不变，对象内容可改。闭包是函数记住外层作用域变量，常用于私有状态/回调，也可能导致内存不释放。

## 2. Vue3 响应式

**一句话**：Vue3 用 `Proxy` 拦截对象读写，`ref` 包装基本类型，`reactive` 包装对象；依赖收集和触发更新构成响应式系统。

要能回答：

- Vue2 的 `Object.defineProperty` 和 Vue3 的 `Proxy` 有什么区别？
- `ref` 和 `reactive` 怎么选？为什么解构会丢响应式？
- `computed` 和 `watch` 的区别？什么时候用哪个？
- `watch` 的 `deep`、`immediate`、`flush` 分别控制什么？
- 响应式丢失的常见场景？怎么排查？
- `nextTick` 解决什么问题？

关联：[[Vue3]]

笔记：

- Vue2 用 `Object.defineProperty` 递归劫持每个属性，新增/删除属性、数组下标修改检测不到；Vue3 用 `Proxy` 代理整个对象，能拦截新增/删除/数组索引，且惰性递归（访问到才代理）。
- `ref` 适合基本类型和「需要整体替换」的值，模板/JS 里用 `.value`；`reactive` 适合对象/数组，直接访问属性。解构 `reactive` 对象会丢响应式（拿到的是普通值），用 `toRefs`/`storeToRefs`。
- `computed` 有缓存、依赖不变不重算，适合派生值；`watch` 监听变化执行副作用（请求、存储），不返回值。能用 computed 表达的就别用 watch。
- `watch` 的 `deep` 深度监听（性能差）、`immediate` 立即执行一次、`flush: 'pre'|'post'|'sync'` 控制执行时机（DOM 更新前/后/同步）。
- 响应式丢失常见：解构、把值当普通变量传参、`reactive` 整体替换、数组直接赋下标（Vue3 能检测但模板里仍要保证引用）、`Object.freeze`。排查看值是不是从响应式对象上读的。
- `nextTick` 等 DOM 更新完成后再读/操作 DOM；改数据后同步读 DOM 拿到的是旧值。

## 3. 组件与通信

**一句话**：组件是 Vue 的基本单元；props 向下、events 向上、slots 分发内容，`provide/inject` 跨层级，全局状态用 Pinia。

要能回答：

- props、emit、slot、provide/inject 分别适合什么场景？
- `v-model` 在组件上怎么实现？
- 动态组件、异步组件怎么用？
- 组件命名和目录怎么组织？
- 什么时候该拆组件？拆得太碎有什么问题？
- 父子组件生命周期执行顺序？

关联：[[组件拆分]]

笔记：

- props 向下传数据、emit 向上通知、slot 分发内容、`provide/inject` 跨层级（避免 prop drilling）、Pinia 管全局跨页面状态。按「数据流向和距离」选。
- 组件上的 `v-model` 展开为 `:modelValue` + `@update:modelValue`；多个 v-model 用 `v-model:foo`，对应 `foo` prop + `update:foo` 事件。
- 动态组件用 `<component :is="...">`；异步组件用 `defineAsyncComponent(() => import(...))`，配合 Suspense/加载态。
- 命名用多单词 PascalCase（模板/kebab-case），目录按功能/页面组织，通用组件放 `components/`，页面私有组件就近放。
- 拆分时机：复用、职责过多、状态/副作用混杂、测试困难；拆太碎会导致 props/emit 链过长、上下文割裂，先拆「有独立职责」的，不为行数拆。
- 父子生命周期：父 setup → 子 setup → 子 mounted → 父 mounted；卸载时父 beforeUnmount → 子 beforeUnmount → 子 unmounted → 父 unmounted。

## 4. 生命周期与渲染

**一句话**：Vue3 组合式 API 用 `onMounted`、`onUpdated`、`onUnmounted` 注册生命周期；渲染是声明式的，数据变→重新渲染。

要能回答：

- Vue3 生命周期钩子有哪些？执行顺序？
- `onMounted` 里能拿到 DOM 吗？`ref` 怎么绑定 DOM？
- `v-if` 和 `v-show` 的区别？
- `v-for` 为什么需要 `key`？用 index 做 key 有什么问题？
- 虚拟 DOM 和 diff 算法解决什么问题？
- 什么时候会触发重新渲染？

笔记：

- Vue3 钩子：`setup` → `onBeforeMount` → `onMounted` → `onBeforeUpdate` → `onUpdated` → `onBeforeUnmount` → `onUnmounted`；`onActivated/onDeactivated` 用于 KeepAlive。
- `onMounted` 时组件已挂载，能拿到 DOM；模板里 `ref="el"`，setup 里同名 `ref(null)` 绑定，挂载后 `.value` 才是元素。
- `v-if` 真正销毁/重建（切换开销大、可触发子组件生命周期）；`v-show` 只切 `display`（首次渲染开销大、频繁切换便宜）。
- `v-for` 的 `key` 帮 diff 识别节点；用 index 做 key，在插入/删除/排序时会复用错节点，导致状态错位（输入框内容、组件内部状态）。
- 虚拟 DOM 是 JS 对象描述 UI，diff 比较新旧树只更新差异；它避免直接全量操作 DOM，但不是「比原生快」，而是可预测、易维护。
- 重新渲染触发：响应式数据变化、父组件重渲染、`key` 变化、路由/状态变化；`computed` 缓存不变不触发。避免大对象深层监听和无意义子组件更新。

## 5. 路由与状态

**一句话**：Vue Router 管理页面切换和守卫，Pinia 管理跨组件状态；路由参数、查询参数、状态持久化要分清。

要能回答：

- `createWebHistory` 和 `createWebHashHistory` 的区别？
- 路由守卫有哪些？登录鉴权应该放哪？
- `params` 和 `query` 的区别？
- 路由懒加载怎么实现？
- Pinia 的 state、getters、actions 怎么组织？
- 刷新页面后状态怎么保留？

笔记：

- `createWebHistory` 用真实路径（`/user/1`），需要服务端 fallback 到 `index.html`；`createWebHashHistory` 用 `#/user/1`，不需要服务端配置，但 URL 丑、SEO 差。
- 守卫：`beforeEach`（全局前置，鉴权常用）、`beforeResolve`、`afterEach`（无 next，不能改导航）、组件内 `beforeRouteEnter/Update/Leave`。登录鉴权放 `beforeEach` + 路由 `meta.requiresAuth`，接口 401 也要兜底。
- `params` 是路径的一部分（`/user/:id`），刷新保留；`query` 是 `?key=value`，适合筛选/分页，可分享。`params` 不匹配路由会丢失。
- 路由懒加载：`component: () => import('./Page.vue')`，按路由拆 chunk；首屏只加载当前路由。
- Pinia：`state` 存数据、`getters` 派生、`actions` 改状态/异步；一个模块一个 store，跨模块用 store 互相调用，不直接改别的 store 的 state。
- 刷新保留：登录态/token 放 localStorage/cookie，筛选条件放 URL query，临时状态可不保留；用 pinia-plugin-persistedstate 要选白名单字段，避免把敏感/过期数据持久化。

## 6. 构建与 TypeScript

**一句话**：Vite 开发时用原生 ESM + esbuild 预构建，生产用 Rollup 打包；TypeScript 在编译期做类型检查，不改变运行时。

要能回答：

- Vite 为什么比 Webpack 快？开发和生产构建分别用什么？
- 环境变量怎么注入？`import.meta.env` 怎么用？
- 路径别名怎么配？
- TypeScript 的接口、类型别名、泛型、联合类型怎么用？
- `any`、`unknown`、`never` 的区别？
- 类型检查和构建要不要分开跑？

关联：[[TypeScript与Vite]]

笔记：

- Vite 开发时用浏览器原生 ESM 按需加载，依赖用 esbuild 预构建（把 CommonJS 转 ESM、合并请求）；生产用 Rollup 打包（tree-shaking、chunk 拆分）。Webpack 开发要先把整个依赖图打包，启动慢。
- 环境变量用 `.env` 文件，只有 `VITE_` 前缀会注入客户端，通过 `import.meta.env.VITE_API_URL` 读；不要放密钥。
- 路径别名在 `vite.config.ts` 的 `resolve.alias` 配，同时要在 `tsconfig.json` 的 `paths` 配一份，否则编辑器/类型检查找不到。
- TS：`interface` 适合对象契约/可扩展，`type` 适合联合/交叉/别名；泛型约束用 `extends`；联合类型配收窄（`typeof/in/instanceof`）。
- `any` 关掉类型检查，`unknown` 是安全的未知（用前必须收窄），`never` 表示不可能的值（穷尽检查、抛错函数）。
- 类型检查用 `vue-tsc --noEmit` 单独跑，构建用 Vite；`vite build` 默认不做类型检查（esbuild 只转译），CI 要单独加类型检查步骤。

## 7. 国际化与工程规范

**一句话**：i18n 用 key 查文案，按 locale 切换；文案覆盖率、日期/货币格式、RTL 都要单独考虑。

要能回答：

- vue-i18n 的基本用法？`$t` 和 `useI18n` 的区别？
- 文案 key 怎么设计？嵌套还是扁平？
- 缺失翻译怎么发现？
- 日期、数字、货币怎么按 locale 格式化？
- 语言切换怎么持久化？
- 哪些内容不应该走 i18n？

关联：[[前端i18n]]

笔记：

- vue-i18n：模板里 `$t('key')`，组合式 API 用 `useI18n()` 拿 `t`；`$t` 是全局注入，`useI18n` 更利于类型/局部作用域。
- key 设计：按页面/模块嵌套（`user.form.name`），公共文案放 `common.*`；避免把整句当 key，也别用中文当 key（改文案就失效）。
- 缺失翻译：开发时开 `missingWarn`/`fallbackWarn`，构建时扫描 key 和 locale 文件对比，CI 卡「有 key 没翻译」。
- 日期/数字/货币用 `Intl.DateTimeFormat`/`NumberFormat` 按 locale 格式化，不要手写 `yyyy-MM-dd`；时区另算，见 [[时区与时间序列化]]。
- 语言切换存 localStorage/cookie + 用户偏好，刷新后恢复；切换时同步 `document.lang` 和路由/请求头（后端返回对应语言文案）。
- 不走 i18n：品牌名、代码/错误码、日志、用户输入内容、法律条款原文（需专业翻译流程）。

## 常见对比题

- `ref` vs `reactive`
- `computed` vs `watch`
- `v-if` vs `v-show`
- `params` vs `query`
- Vue2 vs Vue3 响应式
- Vite vs Webpack
- Pinia vs Vuex

## 我现在到哪

| 块 | 现状 | 依据 |
| --- | --- | --- |
| Vue3 组件、路由、表格页面 | 项目里落地过 | [[Vue3]]、[[smart-web页面]] |
| 组件拆分、i18n 边界 | 项目里做过局部改造 | [[组件拆分]]、[[前端i18n]] |
| TypeScript / Vite 构建 | 项目里使用过 | [[TypeScript与Vite]] |
| 复杂状态管理、性能优化、SSR | 学习和面试准备，未在项目落地 | 本页 |

## 边界

- 本页是索引，不是教材：每个问题只留一行，展开写到独立笔记。
- Vue 项目以 Vue3 业务页面为主，没有 SSR/Nuxt、微前端实战；React/Next 项目有 SSR（muou-web），见 [[React与Next.js]]。
- 没有做过完整的前端性能优化和可视化埋点体系。
