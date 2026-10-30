---
type: 方法
技能点: Spring Security
域: 后端
证据: 实战/设计
---

# RBAC 权限模型

技能点：[[Spring Security]] · 通用技能：[[认证与授权]]

**一句话**：用户绑角色、角色绑权限；再用 `scope` 管角色给谁看、`can_use/can_grant` 管「自己能用」和「能授出去」，最后用调用者的可授集合封顶。

## 方法总纲

1. **三层分离**：`user_role` 管归属，`role_permission` 管权限绑定，`permission` 管权限点；不要把权限直接挂用户。
2. **可见性单独一列**：`sys_role.scope` 用位图表示「平台可见 / 子公司可见 / 两侧通用」，不要拿 `type` 或 `tenant_id` 兼职。
3. **持有与分发拆开**：`can_use=1` 是能调接口，`can_grant=1` 是能分配给下游角色；自定义角色默认 `can_use=1, can_grant=0`，防止分发权传染。
4. **调用者封顶**：创建/更新角色、复制模板、权限树，都先算 caller 的 `can_grant=1` 集合，提交的权限必须是它的子集。
5. **数据范围另算**：RBAC 管功能权限，租户/行级范围靠查询条件或数据库策略；不要指望角色表达式解决数据隔离。

## 实际使用

- **7 个内置角色**：`SUPER_ADMIN`、`PLATFORM_ADMIN`、`SUBSIDIARY_ADMIN`、`PERMISSIONS_ADMIN`、`PDA_CLERK`、`FORKLIFT_OPERATOR`、`MULE_DRIVER`，见 `SysRoleEnum.java:15-34`。
- **scope 位图**：`PLATFORM=1`、`SUBSIDIARY=2`、`COMMON=3`，SQL 用 `(scope & 2) > 0` 过滤子公司可见角色（`SysScopeEnum.java:36-50`、`SysRoleMapper.xml:25-28`）。
- **can_use / can_grant**：列定义见 `update-init.sql:69-70`；`grantablePermIds` 只取 `can_grant=1` 的并集（`SysRolePermDaoImpl.java:62-72`）。
- **调用者封顶**：`assertGrantable` 校验提交的 `permIds` 全在 caller 的可授集合内（`SysRoleServiceImpl.java:304-314`）；`listCopyable` 过滤掉超出天花板的角色（`:236-264`）；`roleTemplate` 取交集裁剪（`:275-302`）。
- **权限树按 caller**：只查 `can_grant=1` 的权限，再在内存里按 `parentId` 组树（`SysPermServiceImpl.java:30-48`）。
- **种子数据**：所有角色（含 `SUPER_ADMIN`）都通过 `sys_role_permission` 显式绑定，没有 bypass；超管只绑平台集（`seed_permissions.sql:9-13,250-268`）。

## 判断顺序

1. 这个动作是「能用」还是「能授」？分别查 `can_use` / `can_grant`。
2. 这个角色该给谁看？查 `scope` 位，不查 `type`。
3. 调用者是谁？平台账号 tenant 为空、子公司账号非空，SQL 分支不同。
4. 提交的权限有没有超 ceiling？在写库前校验，失败不要留下半条角色。
5. 数据范围有没有单独做？没有就明说，不要宣称「权限模型已完成」。

## 反例

- 只加角色不给 `can_grant`：权限管理员自己不能用业务，却也不能把业务权限分给下游。
- 自定义角色顺手给 `can_grant=1`：下游可以继续扩散，权限失控。
- 复制角色不裁剪：平台账号复制子公司角色时，把平台权限带过去。
- 用 `scope` 当租户隔离：scope 只决定角色可见性，不决定数据行可见性。

## 边界

- smart WMS 的接口级授权开关是 `false`（`application.yml:183`），全项目零 `@PreAuthorize`；本页是模型能力，不是线上已生效的授权。
- 没做过 ABAC 规则引擎、行级 RLS、权限缓存一致性专项。
- `SysRoleMapper.xml` 的 SQL 只有 mock DAO 单测，没有真实 MySQL 集成测试（`SysRoleMapper.xml:49` 自注）。

## 证据

- [[权限模型]]
- [[权限模型迁移]]
- `smart-server-wms3/src/main/java/com/track/wms/common/enums/SysScopeEnum.java:36-50`
- `smart-server-wms3/src/main/java/com/track/wms/service/impl/SysRoleServiceImpl.java:236-314`
- `smart-server-wms3/src/main/resources/db/sql/seed_permissions.sql:9-13,250-268`
