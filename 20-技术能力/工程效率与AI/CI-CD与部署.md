---
type: 技能点
域: 后端
项目: [smart WMS, muou]
证据: 实战/设计
---

# CI-CD与部署

所属通用技能：[[工程效率与AI]]

**一句话**：流水线只做三件事：构建、迁移、切换；构建与部署必须落在同一台 runner，迁移用一次性容器先跑，切换用蓝绿 + 健康检查；大多数事故不在 YAML 语法，而在变量为空、网络名不一致、端口没开。

## 方法总纲

1. **stages**：`guard → build → test → package → deploy`，服务仓只写差异，公共模板用 `include`（`muou-backend/muou-server-notify/.gitlab-ci.yml:6-11`）。
2. **runner 绑定**：build 与 deploy 用同一个 tag，deploy 直接用 build 产出的本地镜像，不经 Harbor；换机器就找不到镜像（`smart-server-wms3/.gitlab-ci.yml:10-13`、`:30-40`）。
3. **镜像标签**：`IMAGE_TAG=$CI_COMMIT_SHA`；同一提交只打一次镜像，避免标签被后来的流水线挪走（`smart-server-wms3/.gitlab-ci.yml:42-44`；`muou-backend/muou-server-notify/.gitlab-ci.yml:55-62`）。
4. **部署守卫**：先检查关键变量非空（Protected 变量在非保护分支上是空串）、本地镜像存在、`DOCKER_EXTRA_ARGS` 回显（`smart-server-wms3/.gitlab-ci.yml:116-154`）。
5. **迁移容器**：Liquibase 不随应用启动，部署前用同一镜像跑一次性容器；显式关 web 和调度，跑完退出，失败即中止（`smart-server-wms3/scripts/deploy/switch.sh:101-130`）。
6. **蓝绿**：起 staging → 健康检查（最多 60 次、间隔 3 秒）→ 切 active → 删旧；`resource_group` 串行化，`interruptible: false` 防止切一半被取消（`smart-server-wms3/.gitlab-ci.yml:106-110`；`smart-server-wms3/scripts/deploy/switch.sh:132-208`；`smart-server-wms3/scripts/deploy/health-check.sh:3-9`）。
7. **环境变量**：shell executor 自动把 CI/CD 变量导出为环境变量；空值变量被 `switch.sh` 跳过，由 `application.yml` 默认值兜底（`smart-server-wms3/.gitlab-ci.yml:14-18`；`smart-server-wms3/scripts/deploy/switch.sh:96-99`）。
8. **配置进仓库**：`KNIFE4J_ENABLE=true` 写进 yml 而不是 CI 变量，因为迁移时没人配、空值会被跳过，测试服文档接口静默 401（`smart-server-wms3/.gitlab-ci.yml:46-61`）。
9. **生产清单**：拓扑、内存限额、密钥轮换、nginx/TLS、Go-Live 检查单独维护；清单落笔时自述是「测试级部署」，不是生产级（`smart/docs/生产部署清单.md:11-19`、`:289-302`）。
10. **回滚**：保留旧镜像 tag，按 tag 重新起容器；蓝绿保留上一份 active 可快速切回（`smart/docs/测试环境CI-CD部署笔记.md:1081-1110`；`smart/docs/生产部署清单.md:312`）。

## 我用它干过什么

| 实践 | 类型 | 项目 | 时间 | 对应场景 |
| --- | --- | --- | --- | --- |
| smart wms3 测试环境 GitLab CI：build → 迁移 → 蓝绿 | 实战 | smart WMS | 2026-08 | — |
| muou-server-notify 接共享 Maven 流水线 + 3 个 guard | 实战 | muou | 2026-10 | — |
| Jenkins + Docker/Harbor + ssh 部署笔记 | 设计/方案 | smart WMS | 2026-05 | — |
| 生产部署清单：拓扑/限额/密钥/备份 | 设计/方案 | smart WMS | 2026-07 | — |

证据：
- smart CI：`smart-server-wms3/.gitlab-ci.yml:10-18`、`:100-167`；`smart-server-wms3/scripts/deploy/switch.sh:101-208`
- muou CI：`muou-backend/muou-server-notify/.gitlab-ci.yml:6-23`；`muou-backend/muou-build/ci/maven.gitlab-ci.yml:82-137`
- Jenkins 笔记：`smart/docs/测试环境CI-CD部署笔记.md:664-731`、`:758-808`
- 生产清单：`smart/docs/生产部署清单.md:11-19`、`:289-302`

## 我会的部分

- 写 GitLab CI：workflow rules、needs、resource_group、interruptible、environment（`smart-server-wms3/.gitlab-ci.yml:24-28`、`:100-114`）。
- Docker 构建：BuildKit、内存上限、失败重试 3 次、按 SHA 打 tag、保留最近 N 个镜像（`smart-server-wms3/.gitlab-ci.yml:71-99`、`:160-167`）。
- 部署脚本：网络探测与 `--add-host`、环境变量数组、迁移容器、staging 健康检查、active 切换（`smart-server-wms3/.gitlab-ci.yml:146-157`；`smart-server-wms3/scripts/deploy/switch.sh:56-99`）。
- 共享模板：`extends` 复用 `.guard:*`、`.compile`、`.test`、`.publish:api`（`muou-backend/muou-server-notify/.gitlab-ci.yml:13-43`）。
- 生产化检查：单机 OOM 教训、容器 mem_limit、MySQL buffer pool、nginx `/api` 重写、密钥轮换（`smart/docs/生产部署清单.md:11-19`、`:289-302`）。

### GitHub Actions（NovelForge）

路径相对 `/Users/hujiuyuan/studyspace/noval/novelforge/`。

- **触发**：推送 `v*` tag 或手动 `workflow_dispatch`；`concurrency` 按 ref 串行，`cancel-in-progress: true`，同一版本不会并发出两套包（`.github/workflows/release.yml:17-27`）。
- **矩阵**：4 个产物——macOS arm64（`macos-latest`）、macOS x64（`macos-13`）、Linux x64（`ubuntu-22.04`）、Windows x64（`windows-latest`）；每个平台只带自己的 bundle 参数（`app,dmg` / `deb,appimage` / `nsis`），`runs-on` 跟着矩阵走（`release.yml:33-48`）。
- **发布动作**：`tauri-apps/tauri-action@v0` 负责构建、创建 GitHub Release、上传产物；`releaseDraft: true`，先出草稿再人工发布；签名/公证全部可选，secret 不存在时构建仍成功（`release.yml:128-160`）。
- **与 GitLab CI 的差异**：GitLab 那套是「同 runner build→deploy、迁移容器、蓝绿切换」，GHA 这套是「打 tag→多平台出安装包→草稿 Release」，没有部署环节；两者不是同一种流水线。

#### 为什么 novelforge 用 GHA，不用 GitLab CI

- **仓库在 GitHub**：代码、Release、issue 都在同一平台，`GITHUB_TOKEN` 能直接建 Release，`tauri-action` 就是为这个场景写的；搬去 GitLab 要多维护一套镜像/凭据和发布脚本。
- **代价**：CI 配置和 smart/muou 的 GitLab 模板不共享，团队要会两套 YAML；macOS runner 按分钟计费，矩阵四份产物构建成本高；Actions 的第三方 action 要跟版本和权限（`contents: write`）。
- **什么时候反悔**：仓库迁到 GitLab、或需要自建 runner/内网构建 → 把矩阵和 `tauri-action` 的步骤翻成 GitLab CI；当前 GHA 的 Release 集成没有等价替代。

## 选型与取舍

| 选择 | 为什么 | 代价/失败模式 | 什么时候反悔 |
| --- | --- | --- | --- |
| GitLab CI 而不是 Jenkins/GitHub Actions | 仓库、变量、runner、MR 一体；共享模板用 `include`，服务仓只写差异 | YAML 调试差、runner 与机器绑定、Protected 变量在非保护分支为空 | 多仓库/多平台、需要更强编排 → GitHub Actions/Jenkins；已有 Jenkins 资产 → 保留 |
| shell runner + 本地镜像，不走 Harbor | build 和 deploy 同一台机器，镜像不用推拉，快且少一层故障 | 换 runner 就找不到镜像；机器磁盘要清理；无法多机部署 | 多 runner/多环境 → 推镜像仓库；K8s → 镜像 + Deployment |
| 迁移用一次性容器，不随应用启动 | 迁移和应用生命周期解耦；失败即中止部署，不会半启动应用 | 多一步、要保证迁移镜像与代码版本一致；并发部署要锁 | 小应用/单实例 → 启动时迁移也可，但要加锁和备份 |
| 蓝绿而不是滚动/金丝雀 | 两套容器切换，回滚快；健康检查通过才切 | 资源翻倍；数据库变更要向前兼容；切换瞬间要处理连接 | 资源紧张 → 滚动；高风险变更 → 金丝雀 + 指标 |
| 镜像 tag 用 commit SHA，不用 latest | 同一提交唯一镜像，可追溯/可回滚 | 镜像数量增长，要保留策略；tag 不可变要纪律 | 频繁构建的临时环境 → 可用分支名 + SHA 后缀 |
| 非密钥配置进仓库 yml，密钥走 CI 变量 | 迁移/部署脚本不会因为空变量静默跳过；密钥不进仓库 | 配置变更要改代码/发版；环境差异要 profile | 多环境差异大 → 配置中心；密钥 → KMS/CI secret |

## 边界

- 生产部署没有落地证据：清单 2026-07-16 自述「当前是测试级部署」，生产化条目全是待办（`smart/docs/生产部署清单.md:11-19`、`:325-342`）；之后是否上线，本页没有证据。
- 备份恢复只有文档条目，没有实现代码，不建页（`smart/docs/生产部署清单.md:305-312`）。
- 只做过单机 Docker + shell runner；没做过 Kubernetes、Helm、多集群、多环境晋级。
- smart wms3 当前流程不经 Harbor；Harbor 只出现在 Jenkins 笔记和生产清单的方案里（`smart/docs/测试环境CI-CD部署笔记.md:664-731`）。
- 没有流水线自身的测试，也没有回滚演练记录；回滚步骤只是文档。
- muou 的共享模板只接过、用过，没有改核心模板。

## 相关技能

[[工程效率与AI]]、[[EasyCode与Velocity]]、[[Claude Code与Agent]]

## 用在哪些工程能力

发布流水线、环境治理、部署门禁、故障回滚。
