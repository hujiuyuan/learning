---
type: 技能点
域: 前端
项目: [smart WMS, novelforge]
证据: 实战/学习
---

# TypeScript与Vite

所属通用技能：[[前端与Vue3]]

**一句话**：Vite 管开发服务器和构建，TypeScript 管编译前的类型检查；两者都不改运行时，只是把「打包」和「类型」问题提前到命令里暴露。

## 方法总纲

1. **TS 严格模式**：`strict: true` 打开空值与隐式 any 检查；再叠 `noUnusedLocals`、`noUnusedParameters`、`noFallthroughCasesInSwitch`。
2. **类型检查进构建**：`tsc --noEmit && vite build`，让类型错误直接挡住产物。
3. **Vite 配置**：`defineConfig(({ mode }) => ...)` 按模式返回配置；`loadEnv(mode, cwd)` 读环境变量。
4. **别名**：`@` 指 `src`，`~` 指项目根；`jsconfig`/`tsconfig` 的 paths 要与之一致。
5. **代理**：只在 dev server 生效；`changeOrigin` + `rewrite` 去掉前缀；生产靠 nginx。
6. **环境变量**：Vite 只暴露 `VITE_` 前缀；`.env.[mode]` 覆盖 `.env`；读取用 `import.meta.env`。
7. **产物目录**：`build.outDir` 跟 mode 走，不能写死 `dist`。
8. **UI 组件库**：`unplugin-vue-components` + resolver 做按需自动引入；主题用 CSS 变量或 config-provider 覆盖。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| WMS 前端镜像构建与 GitLab CI | 实战 | smart WMS | 2026-08 | — |
| TS 严格模式与类型定义 | 学习中 | novelforge（对照） | — | — |

## 选型与取舍

### 为什么用 Vite，不用 Webpack

- Vite 开发态用 esbuild 预构建 + 原生 ESM，冷启动和 HMR 比 Webpack 快；配置少，`defineConfig` + 插件即可。
- 代价：生产构建仍用 Rollup，复杂分包/老浏览器兼容/插件生态不如 Webpack 成熟；Vite 的 ESM 开发模式要求依赖预构建，遇到 CommonJS/动态导入要调 `optimizeDeps`。
- 项目是 Vue 3 + 现代浏览器后台系统，Vite 的速度收益明确；如果要兼容 IE/老浏览器或大量自定义 loader，Webpack 更稳。

### 为什么用 TypeScript 严格模式，不用 JS

- `strict: true` + `noUnusedLocals`/`noUnusedParameters` 把空值、隐式 any、未使用变量提前到构建期；类型定义集中在 `types.ts`，接口变更时编译能发现。
- 代价：类型体操/第三方类型缺失会拖慢开发；`tsc --noEmit && vite build` 让类型错误挡住产物，构建时间增加。Vue 项目目前零 `.ts`，TypeScript 只在 novelforge 里学习中，不能写成「Vue 项目已用 TS」。
- 如果团队/项目没有类型文化，强上 strict 会变成大量 `any`/`@ts-ignore`；类型收益要靠 review 和构建门禁，不是打开开关就自动获得。

### 为什么类型检查放构建，不只靠编辑器

- 编辑器只检查打开的文件，CI 要保证全量类型正确；`tsc --noEmit && vite build` 让类型错误直接失败，避免「本地没报错、CI 过了、运行时炸」。
- 代价：构建变慢；`vite build` 本身不做类型检查，漏掉 `tsc` 就等于没有门禁。项目在 novelforge 里把 `typecheck` 单独暴露，方便本地先跑。
- 如果构建时间敏感，可以把 typecheck 放独立 CI job 并行；但不能完全省略。

### 为什么代理只在 dev，生产用 nginx

- Vite dev server 的 `server.proxy` 只用于本地跨域；生产静态文件由 nginx 托管，`/api` 反向代理到后端，行为和 dev 不完全一样。
- 代价：dev/prod 两套代理配置，容易出现「本地正常、生产 404」；项目用 `VITE_AXIOS_BASE_URL` 和环境变量区分，nginx 单独配置。
- 如果团队用统一网关/BFF，dev 也走真实网关，代理可以省；当前本地开发不想依赖后端网关，保留 Vite 代理。

### 什么条件下会反悔

- 需要兼容老浏览器/复杂构建 → 回 Webpack 或加 legacy 插件；当前只支持现代浏览器。
- 类型错误长期靠 `any` 绕过 → 收紧 ESLint/tsc 规则或放弃 strict；当前 novelforge 是学习项目，尚未到这一步。
- 前端工程多到代理/环境变量难维护 → 抽统一配置包/BFF；当前两个 Vue 仓 + 一个 React 仓，手工配置还可控。

## 我会的部分

### Vite（实战）

- **多环境变量**：`.env.development`、`.env.test`、`.env.production` 各自定义 `VITE_AXIOS_BASE_URL`、`VITE_OUTDIR`（`smart-web-wms/.env.development:11`、`.env.test:11-14`、`.env.production:11-14`）。
- **代理**：`/proxy` → `VITE_PROXY_TARGET`，`rewrite` 去掉前缀，dev 下把真实地址写回响应头（`vite.config.js:45-67`）。
- **自动引入**：`AutoImport({ imports: ['vue', 'vue-router'] })` + `Components({ resolvers: [NaiveUiResolver()] })`（`vite.config.js:24-31`）。
- **UnoCSS**：presetWind3 + presetAttributify + presetIcons，自定义 `fe`/`me`/`ep` 图标集（`uno.config.js:10-32`）。
- **产物目录**：`outDir: VITE_OUTDIR`（`vite.config.js:68-71`）；test 出 `smart-wms-test`，prod 出 `smart-wms-production`。
- **镜像与 CI**：两阶段 Dockerfile，node 22 构建 + nginx 1.26 托管，构建后断言 `index.html` 存在（`docker/Dockerfile:1-35`，commit `75a0e77`）；CI 里再跑一次镜像内检查（`.gitlab-ci.yml:61-66`，commit `85e8af4`）。

### TypeScript（学习中）

- 严格模式：`strict`、`noUnusedLocals`、`noUnusedParameters`、`noFallthroughCasesInSwitch`（`novelforge/tsconfig.json:17-21`）。
- 类型检查进构建：`"build": "tsc --noEmit && vite build"`、`"typecheck": "tsc --noEmit"`（`novelforge/package.json:10-13`）。
- 类型定义集中在 `src/types.ts`：联合类型 + interface（`novelforge/src/types.ts:12-94`）。
- React + Vite 配置（`novelforge/package.json:21-34`）。
- **证据等级**：novelforge 不是 git 仓库，没有提交记录，只能证明「代码这样写」，不能证明是我写的，所以标学习中。

## 边界

- 没在 Vue 项目里用过 TS：`smart-web-wms` 和 `smart-web-omp` 的 `src` 都是 0 个 `.ts`，只有 `jsconfig.json`。
- 没写过 `.d.ts` 声明、泛型组件、类型体操。
- 没配过 Vite 的 `build.rollupOptions` 分包、SSR、库模式；`rollup-plugin-visualizer` 装了但没接进配置。
- Vue 项目没配过 vitest/playwright；React 项目（muou、novelforge）有 Vitest/RTL 和 Playwright，见前端测试（待建）。
- 生产环境不经过 Vite 代理，nginx 是另一套配置（`docker/nginx.conf:1-28`）。

## 相关技能

- [[Vue3]]
- [[组件拆分]]

## 用在哪些工程能力

- [[Spring应用与接口契约]]：前端 baseURL/代理决定请求打到哪个环境。
- [[认证与授权]]：token 存在 store、由请求拦截器带出。
