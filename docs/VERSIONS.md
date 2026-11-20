# 版本与物料清单

## toolkit 1.0.1

| 组件 | 版本 | 来源 |
|---|---|---|
| skill `nxopen-journal` | 1.7.0 | 技能仓库 commit `376041e`，115 文件 |
| `nxopen-mcp-enhanced` | 1.0.0 | fork 自 `mingfeng6684/nxopen-mcp` 0.2.0 |

技能快照的逐文件 SHA-256 记录在
`src/nxopen_journal_toolkit/_skill/vendor-manifest.json`，可用
`python tools/sync_skill.py --check` 校验。

## 更新规则

| 场景 | 动作 | toolkit 版本 |
|---|---|---|
| MCP 单独更新 | 改 `nxopen-mcp-enhanced`，发 1.x；toolkit 依赖范围允许则不必重发 | 不变 |
| 技能单独更新 | `python tools/sync_skill.py --ref <tag>`，更新本表 | patch |
| 两者一起更新 | 先同步两者，再更新本表 | minor |

发布说明固定三段：`Skill:`、`MCP:`、`Toolkit changes:`。未变化的写“不变”。
