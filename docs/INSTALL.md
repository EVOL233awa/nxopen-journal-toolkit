# 安装说明

## 前置

| 项 | 要求 |
|---|---|
| Python | 3.11+（`nxjt` 与 MCP 用；NX journal 仍由 NX 内嵌 3.6.1 执行） |
| Siemens NX | 12.x；`NX_HOME` 指向安装根，默认 `D:\UG-NX12` |
| 磁盘 | 技能约 4 MB；索引约 400 MB（本机构建） |

## 安装

```bash
pip install nxopen-journal-toolkit
nxjt install --target zcode     # 复制技能 + 写 ZCode MCP 配置
nxjt index                      # 用 NX_HOME 建索引
nxjt doctor
```

`install` 会把技能复制到 `~/.codex/skills/nxopen-journal`（ZCode/Codex 共用），
并把 `nxopen` server 写入 `~/.zcode/cli/config.json`。写前自动备份，内容不变时跳过。

其他宿主：

```bash
nxjt install --target codex
nxjt install --target claude
```

## 嵌入后端

默认本地 BGE-M3：首次建索引/查询会下载约 2 GB 模型，建索引可能需要数小时。

远程模式（OpenAI 兼容）：

```bash
nxjt config embed --provider remote
```

会依次询问 base URL、嵌入模型、API key、rerank URL/模型，并写入 ZCode MCP 的 env。
切回本地：`nxjt config embed --provider local`。

## 复用已有索引

若已有上游 `nxopen-mcp` 的索引，可让配置直接指向它：

```bash
nxjt index --db C:\Users\<you>\.nxopen-mcp\index.db
```

或在 ZCode 的 `nxopen` server `args` 里把 `--db` 改成该路径。两者 schema 相同，
但 enhanced 不会修改索引结构。

## 自检

```bash
nxjt doctor                 # NX、XML、索引、MCP、BOM
nxjt verify                 # 已安装技能跑 check_repo.py + MCP 冒烟
nxjt verify --nx            # 追加 NX 回归套件（需真实 NX，耗时长）
```
