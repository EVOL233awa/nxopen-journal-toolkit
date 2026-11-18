# nxopen-journal-toolkit

一条命令安装 **nxopen-journal 技能** 与 **nxopen-mcp-enhanced**（NXOpen API 检索 MCP）。

## 组成

| 组件 | 版本 | 作用 |
|---|---|---|
| skill `nxopen-journal` | 见 `nxopen-journal-toolkit doctor` | 生成/检查 NX 12 journal，覆盖建模、装配、Drafting、FEA、Motion |
| `nxopen-mcp-enhanced` | `1.0.x` | 对 NXOpen .NET API 做语义检索，供 agent 核实类/成员/签名 |

## 快速开始

```bash
pip install nxopen-journal-toolkit

nxjt install            # 复制技能到 ~/.zcode/skills，并写入 ZCode MCP 配置
nxjt index              # 用 NX_HOME（默认 D:\UG-NX12）建 API 索引
nxjt doctor             # 检查 NX、索引、MCP 配置与版本
```

云端嵌入（可选，不需要本地 2 GB 模型）：

```bash
nxjt config embed --provider remote
```

## 命令

| 命令 | 作用 |
|---|---|
| `nxjt install [--target zcode\|codex\|claude\|all] [--skill-only]` | 复制技能，写 ZCode MCP 配置（备份、幂等） |
| `nxjt doctor` | NX_HOME、run_journal.exe、managed XML、索引、MCP、BOM |
| `nxjt index [--nx-path ...] [--workers N]` | 构建 NXOpen API 索引 |
| `nxjt verify [--nx]` | 技能自检 + MCP 冒烟；`--nx` 跑 NX 回归套件 |
| `nxjt config embed --provider local\|remote` | 切换本地 BGE-M3 / OpenAI 兼容远程嵌入 |

## 来源与许可

- 技能：`nxopen-journal`（MIT），本包内为只读快照，源头仓库仍是技能仓库。
- MCP：`nxopen-mcp-enhanced`（MIT），fork 自 `mingfeng6684/nxopen-mcp`。
- 许可全文见 `LICENSES/`；来源与版本见 `NOTICE` 与 `vendor-manifest.json`。

技能与 MCP 也可单独安装：只要技能文件直接复制技能仓库；只要 API 检索用
`pip install nxopen-mcp-enhanced`。
