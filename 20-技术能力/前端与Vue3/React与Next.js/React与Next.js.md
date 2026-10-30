---
type: 技能点
域: 前端
项目: [muou, NovelForge]
证据: 实战/项目内使用
---

# React 与 Next.js

所属通用技能：[[前端与Vue3]]

**一句话**：muou-web 用 Next 16 App Router 做多租户官网：默认服务端组件、只有 20 个客户端岛，页面与取数都在服务端，浏览器只走同源 `/api/v1` 转发；muou-admin 是 React 19 + Vite 的后台 SPA，用 antd、Zustand、TipTap 和路由级懒加载。两套工程解决的是两种问题，不是「同一套技术栈换了个框架」。

路径说明：muou 两个前端仓库相对 `/Users/hujiuyuan/workspace/voidtech/muou-client/muou-frontend/`；NovelForge 相对 `/Users/hujiuyuan/studyspace/noval/novelforge/`。

**归属说明**：muou-web 本人提交 423 次、muou-admin 496 次（项目证据页 `30-项目证据/muou.md` 记录，当前 shortlog 略有增长）；muou-dashboard 的代码作者里没有本人，只作项目内使用；NovelForge 不是 git 仓库，作者待核，本页不把它写成「我做的」。

## 方法总纲

1. **服务端优先**：App Router 的 `page.tsx`/`layout.tsx` 默认是服务端组件；只有需要事件、状态、浏览器 API 的叶子组件加 `"use client"`。当前 64 个页面文件，客户端组件 20 个。
2. **用路由组表达边界**：`(site)` 官网、`(workbench)` 会员/属会工作台、`(task)` 免登录收银台、`(preview)` 预览，各自有 layout；收银台不继承官网导航，也不让站点配置故障拖垮它。
3. **静态与按需混合**：`[locale]/layout.tsx` 用 `generateStaticParams` 预渲染三语；内容 catch-all 没有路径清单，按需渲染，取数层 `revalidate: 300` + tag 失效兜底。
4. **两条取数路径**：服务端用 `GATEWAY_BASE_URL` 内网直连并带租户头；浏览器用同源 `/api/v1/**` 转发，把访客域名带给后端，同时让 HttpOnly Cookie 自然生效。
5. **服务端状态不复制进全局 store**：muou-web 的会话、菜单、主题都在服务端取；muou-admin 的 Zustand 只存服务端下发的会话派生值，登录凭据在 HttpOnly Cookie 里，JS 读不到。
6. **客户端缓存按应用选**：后台的会话/菜单用 Zustand；dashboard 的接口数据用 TanStack Query 管加载、失效、重取；官网不用客户端查询库，数据在服务端取完再渲染。
7. **安全头在框架层统一发**：静态 CSP + `nosniff` + `Referrer-Policy` + `Permissions-Policy`，`poweredByHeader: false`；CSP 的每条放行都对应真实资源，不是模板。
8. **构建产物决定部署形态**：官网 `output: "standalone"`，运行时必须有 Node 进程；后台是 Vite 静态产物，交给 nginx。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| muou-web Next 16 App Router 多租户官网：64 个页面、20 个客户端岛 | 实战 | muou | 2026-08~10 | [[前端与Vue3]] |
| 服务端/浏览器两条取数出口，同源 `/api/v1` 转发与路径白名单 | 实战 | muou | 2026-09~10 | [[Spring应用与接口契约]] |
| 静态 CSP 与安全响应头（`next.config.ts`） | 实战 | muou | 2026-10 | [[安全与审计]] |
| muou-admin React 19 + antd + Zustand + TipTap + React Router 8 | 实战 | muou | 2026-08~10 | [[组件拆分]] |
| Vitest/RTL 测试：两个仓 702 个测试文件 | 实战 | muou | 2026-09~10 | [[测试与质量]] |
| Next standalone 两阶段镜像与构建期/运行期环境变量拆分 | 实战 | muou | 2026-10 | [[CI-CD与部署]] |

## 我会的部分

### Next App Router 与服务端组件

- `muou-web/package.json:29-33`：`next 16.3.4`、`react 19.2.4`、`react-dom 19.2.4`；`muou-admin/package.json:37-40`：React 19.2.8 + React Router 8.3 + Zustand 5。
- 页面结构：`src/app/[locale]` 下分 `(site)`、`(workbench)`、`(task)`、`(preview)` 四个路由组；`find src/app -name 'page.tsx' | wc -l` = 64；`grep -rl '"use client"' src --include='*.tsx' | wc -l` = 20。绝大多数页面在服务端渲染，客户端组件只负责交互叶子。
- 服务端 layout 不碰浏览器 API：`[locale]/layout.tsx` 只做 locale 校验、`metadataBase`、设计令牌与 children 包裹，没有 `useState`/`useEffect`；`generateStaticParams` 预渲染三语（`src/app/[locale]/layout.tsx:25-35`）。
- 为什么不按「已启用语言」收窄：启用语言是运行期事实，构建期少预渲染一门已启用语言，会让那门语言所有页面退化成按需渲染；多渲染一条没有入口的语言只是产物大一点（`[locale]/layout.tsx:25-31`）。
- 内容页 catch-all 没有 `generateStaticParams`：后端没有「列全站页面」的端点，构建期拿不到路径清单，所以按需渲染；取数层 `revalidate: 300` + `site-config` tag，后台改完走 `/api/revalidate` 即时失效（`src/app/[locale]/(site)/(content)/[...slug]/page.tsx:31-36`）。
- `(site)/layout.tsx` 显式 `revalidate = 0`：故障视图只供本次请求，避免一次短暂接口失败被整段路由缓存（`src/app/[locale]/(site)/layout.tsx:23-24`）。
- 静态渲染遇到 `useSearchParams` 必须包 `Suspense`，否则构建直接失败；项目在登录闪条与主题动效两处按这个边界包（`src/app/[locale]/(site)/layout.tsx:194-203`、`src/site/theme/motion.tsx:91-99`）。

### 服务端取数与浏览器同源转发

- 服务端取数只在 `src/lib/api/client.ts`：读 `GATEWAY_BASE_URL`/`API_TIMEOUT_MS`，带租户头，`apiGet` 默认 `revalidate: 300`，带 Cookie 的请求 `revalidate: 0`；`cache: 'no-store'` 只给显式要求的调用（`src/lib/api/client.ts:187`、`:231-263`、`:317`）。
- 浏览器侧不直连 API 域名：`/api/v1/**` Route Handler 同源转发，把 `Host` 写成 `X-Muou-Site-Host`，后端才能按访客域名判租户；同时 Cookie 同源生效、不需要 CORS（`src/app/api/v1/[...path]/route.ts:16-24`、`:145`）。
- 转发有路径白名单：只放行 `site/member/club` 三个入口，后台 `admin` 不转发；每段先按 `^[A-Za-z0-9._~-]+$` 校验、再排除 `.`/`..`，最后才拼路径（`route.ts:60`、`:77-81`、`:204-209`）。不合法一律 404，不回「禁止转发」，避免暴露代理存在。
- 浏览器取数在 `src/lib/api/browser.ts`：`NEXT_PUBLIC_API_BASE_URL` 必须是相对 `/api/v1`；绝对地址会同时坏两件事——后端认不出官网租户、Cookie 跨站不发送，而且都不报错（`src/lib/api/browser.ts:12-36`）。

### 后台 SPA：状态、编辑器、路由

- 登录态在 Zustand：`create` 出来的 auth store 只存 `status/accountName/tenantName/menus/superAdmin/permissions/scope`，凭据在 HttpOnly Cookie，JS 读不到也写不了，所以启动必须问服务端（`muou-admin/src/store/auth.ts:15-45`）。
- 权限不在前端推导：菜单是服务端 `reachableRoutes` 与前端 `menuCatalog` 的交集，按钮动作码也由服务端下发；超管通配只认服务端布尔，不认邮箱/pageCount（`store/auth.ts:38-56`）。
- 富文本用 TipTap：`useEditor` 装 `richTextExtensions`，`onUpdate` 回传 HTML，`transformPastedHTML` 清洗粘贴内容，受控 `value` 变化时 `setContent(..., { emitUpdate: false })` 避免回环（`muou-admin/src/components/RichTextEditor.tsx:40-78`）。
- 路由级懒加载：`react-router` 的 route-level `lazy` 而不是 `React.lazy + Suspense`，导航先等 chunk 再提交，不会出现 URL 变了组件没到的空窗；菜单悬停用 `prefetch` 提前拉，实测一页首访约 870ms 花在 chunk 下载+执行+首次渲染（`muou-admin/src/router/index.tsx:16-32`）。
- 换版后旧 chunk 404：入口处装 `installChunkRecovery()`，拦 Vite 的 `preloadError` 刷新到新版本，避免用户停在报错页（`muou-admin/src/main.tsx:12-15`）。

### 另一个 React 工程：dashboard

- muou-dashboard 是 React 19 + Vite + shadcn/Base UI + TanStack Query：`QueryClientProvider` 包根，页面用 `useQuery/useMutation` 管服务端状态（`muou-dashboard/web/src/main.tsx:4`、`:42-46`；`package.json:16-25`）。
- 这个仓库的 git 作者里没有本人，只能算「项目内使用」；本页不把它写成个人实战。

### 安全头与部署

- 静态 CSP：`script-src 'self' 'unsafe-inline'`，生产不加 `unsafe-eval`，dev 才加；`frame-ancestors 'none'`、`object-src 'none'`、`form-action 'self'`；`img-src` 放 `https:`/`http:` 是因为租户自填图床域名无法枚举（`next.config.ts:4-47`）。
- 为什么不用 nonce：Next 官方要求 nonce 必须配动态渲染；整站预渲染的页面为了 nonce 退化成按请求渲染，代价大于收益。代价是 CSP 挡不住内联脚本注入，只挡外部脚本源、`<base>` 改写、插件对象、iframe 套壳、表单劫持（`next.config.ts:8-19`）。
- 其他头：`poweredByHeader: false`、`X-Content-Type-Options: nosniff`、`Referrer-Policy: strict-origin-when-cross-origin`、`Permissions-Policy` 默认拒绝摄像头/麦克风/定位/支付（`next.config.ts:49-77`）。
- 官网镜像两阶段：构建期注入 `API_BASE_URL`/`NEXT_PUBLIC_API_BASE_URL`/`SITE_URL`/`GATEWAY_BASE_URL`/`IMAGE_REMOTE_HOSTS`，运行期才给 `REVALIDATE_SECRET`/`DEFAULT_THEME_CODE`；`output: "standalone"` 后只拷 `.next/standalone` + `.next/static` + `public`，构建后单独检查 `server.js` 存在（`next.config.ts:79-84`；`muou-web/Dockerfile:1-100`）。
- 后台是 Vite 静态产物，不需要 Node 运行时；两套部署形态不同，不能互相照抄。

## 选型与取舍

### 为什么官网用 Next/React，不用 Vue/Nuxt 或纯 SPA

| 方案 | 优势 | 代价 | 项目里的位置 |
| --- | --- | --- | --- |
| Next 16 App Router + React 19 | SSR/预渲染、SEO、服务端取数、路由组、standalone 部署 | 服务端/客户端边界、缓存语义、Node 运行时 | muou-web 官网 |
| Vue 3 + Nuxt | 团队已有 Vue 经验，Nuxt 也能 SSR | 现有官网组件/主题/契约已在 React 侧；换栈等于重做 | 未用于 muou-web |
| 纯 SPA（Vite + React） | 部署简单、静态托管 | 首屏空壳、SEO 差、服务端取数拿不到 | muou-admin 后台 |

官网要 SEO、三语、多租户主题、服务端取数，纯 SPA 直接出局；Vue/Nuxt 能力上可行，但 muou 的官网组件、主题渲染、契约类型已经在 React/Next 侧，换栈是重做而不是升级。后台不需要 SEO，用 Vite SPA + antd 更直接，构建产物交给 nginx 即可。这是「按场景选形态」，不是「React 一定比 Vue 好」。

### 为什么用 App Router，不用 Pages Router

- App Router 的 layout 跨路由不重渲染、路由组能表达官网/工作台/收银台边界、服务端组件默认不把取数逻辑打进浏览器包；Pages Router 的 `_app/_document` 要自己拼这些边界。
- 代价：RSC 与客户端组件的边界要学（`"use client"` 只能放在叶子）、缓存有 `revalidate`/`staleTimes`/tag 多层、`useSearchParams` 在静态渲染下必须包 `Suspense`。项目用 20 个客户端岛把边界压住，没有把整页标成客户端。
- 如果团队不熟 RSC、或页面全是重交互后台，Pages Router/纯 SPA 更省心；官网的内容型页面更适合 App Router。

### 为什么静态 CSP，不用 nonce

- nonce 要求逐请求动态渲染；官网的首页、业务页、sitemap 依赖预渲染，为 CSP 把整站退化成按请求渲染，是拿架构换一条安全头。
- 代价：`script-src` 必须带 `unsafe-inline`，挡不住内联脚本注入；能挡的是外部脚本源、`<base>` 改写、插件对象、iframe 套壳、表单劫持。
- 如果站点改成全动态渲染、或安全要求必须去掉 `unsafe-inline`，再上 nonce；当前预渲染的收益更大（`next.config.ts:8-19`）。

### 为什么后台用 antd，官网用 Tailwind/shadcn

- 后台是密集表格、表单、弹窗、权限页，antd 的组件完整度和交互规范省大量实现；官网是内容展示 + 主题定制，Tailwind 的原子类和 shadcn 的「复制进仓库的组件」更容易按租户主题改样式，不会被组件库主题变量绑死。
- 代价：两套设计体系、两套组件习惯，人员切换有成本；两套样式还要显式隔离。后台的做法是不引 Tailwind preflight（base reset 会重置 button/img/border，和 antd 打架），只引 theme/utilities 两层；`StyleProvider layer` + `@layer antd, theme, base, components, utilities` 让同优先级时 utilities 胜出；颜色统一桥接到 antd 的 CSS variables，切主题色/暗色时两边一起变（`muou-admin/src/global.css:1-14`；`src/providers/AppProvider.tsx:160-167`）。
- 如果后台也追求高度定制品牌，shadcn 更灵活；如果官网要快速堆复杂表单，antd 更省事。当前按「后台重交互、官网重展示」分工。

### 为什么 Zustand + TanStack Query，不用一个全局 store 管所有状态

- 服务端状态（接口数据）和客户端状态（登录态、菜单、UI）生命周期不同：TanStack Query 负责缓存、失效、重取、并发去重；Zustand 只存跨组件共享的客户端状态。混在一个 store 里会手写缓存失效和请求去重。
- muou-web 更彻底：数据在服务端取，浏览器不建全局查询缓存，避免「服务端渲染的和客户端缓存的两份数据打架」。
- 代价：两套心智模型、调试入口不统一；如果应用很小，一个 store 就够，不值得拆。

### 为什么富文本用 TipTap，不用 textarea/Markdown/Quill

- 后台需要表格、图片、链接、对齐、占位符、粘贴清洗，TipTap 的 headless + 扩展体系能按需装；textarea 表达不了富文本，Markdown 对非技术运营不可见即所得，Quill 的定制和 React 集成不如 TipTap 直接。
- 代价：扩展矩阵要自己维护，HTML 粘贴必须清洗（项目用 `cleanPastedRichText`），受控值与编辑器内部状态要做回环保护；产物体积也比纯 textarea 大。
- 如果只是短文本/评论，textarea 更简单；需要结构化富文本才上 TipTap。

### 什么条件下会反悔

- 官网从内容站变成重交互应用 → 客户端岛会越来越多，考虑拆成 SPA/独立应用；当前 20 个客户端组件还算可控。
- 预渲染收益消失、全站必须动态 → 重新评估 nonce CSP；当前静态 CSP 是预渲染的配套选择。
- 后台表格/表单需求下降、品牌定制上升 → 评估 shadcn 替换 antd；当前 antd 的密集组件仍是效率来源。
- 多租户主题/语言继续膨胀 → 把主题渲染抽成独立包/服务；当前在 Next 应用内。
- 团队不熟 RSC、客户端边界频繁出错 → 退回 Pages Router/SPA；当前用目录约定和客户端岛数量控制。

## 边界

- React 19 只用了运行时与新 JSX，没有用 `useActionState`/`useOptimistic`/`useFormStatus` 等新 hooks；服务端能力主要通过 Next 提供。
- 没写过 React Server Actions；表单提交走 API Route/后端接口。
- 没做过 React 状态库迁移（Redux/MobX/Jotai），只用过 Zustand 与 TanStack Query。
- 没做过 Next 的 middleware 级鉴权；官网会话由后端/Route Handler 处理，后台由 `AuthGuard` + 服务端权限。
- 没做过 Next 的 ISR 大规模调优；只用了 `revalidate`、tag 失效、`staleTimes` 这几档。
- 没做过 React 性能剖析（Profiler/火焰图）；后台只做了路由级分包和 chunk 预取。
- muou-dashboard 本人无提交；NovelForge 不是 git 仓库、作者待核，只能算项目内使用/学习中。
- 没做过 React Native/跨端；NovelForge 是 Tauri 桌面端，不是移动端。

## 相关技能

- [[前端与Vue3]]、[[Vue3]]（另一条并列栈，别把 React 的 SSR 经验写成 Vue 的）
- [[TypeScript与Vite]]、[[组件拆分]]、[[前端i18n]]
- [[Spring应用与接口契约]]（Result 信封、同源转发）
- [[安全与审计]]（CSP、安全头）
- [[测试与质量]]（Vitest/RTL）

## 用在哪些工程能力

- 多租户官网的服务端渲染与 SEO
- 后台管理系统的组件化与权限
- 前后端契约与同源转发
- 前端安全头与构建部署
