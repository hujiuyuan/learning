---
type: 项目证据
时间: 2026-09
技术栈: [EasyCode, Velocity, Java, PostgreSQL, Shell]
---

# easycode-sim

**定位**：EasyCode 模板的仿真与验证台；复刻插件的配置拼接、Velocity 渲染、类型映射和落盘，再用多库生成/编译/守卫证明模板可用。

**模块 → 相关节点**

| 模块 | 相关节点 |
| --- | --- |
| 模板与全局配置 | [[工程效率与AI]]、[[EasyCode与Velocity]] |
| 补丁链 | [[模板补丁]]、[[EasyCode修复]] |
| 仿真台与守卫 | [[EasyCode修复]]、[[数据访问与ORM]] |
| 五库生成 | [[数据建模与迁移]]、[[MySQL]]（仅对照） |

**我在这里练到的技能**：[[工程效率与AI]]、[[EasyCode与Velocity]]、[[数据访问与ORM]]

**源路径**：`/Users/hujiuyuan/studyspace/easycode-sim`

**规模**：message 15 表 × 15 模板 = 225 文件；四库基准 177 表 / 2518 Java 源码 0 编译错误；加入 archive 后 180 表 / 2536 Java（README 口径）；补丁链 fix1–fix9，58 处文本改动。

**边界**：EasyCode 是 IDEA 插件，不是团队生产工具；仿真台不在 muou 仓库；没有接 CI；没有生成器级单测。
