# 安装说明

## 前置

| 项 | 要求 |
|---|---|
| Python | 3.11+（`nxjt` 与 MCP 用；NX journal 仍由 NX 内嵌 3.6.1 执行） |
| Siemens NX | 12.x；`NX_HOME` 指向安装根，默认 `D:\UG-NX12` |
| 磁盘 | 技能约 4 MB；索引约 400 MB（本机构建） |

## 安装

当前未发布到 PyPI，先从源码安装：

```bash
cd nxopen-journal-toolkit
pip install -e .
nxjt install --target zcode     # 复制技能 + 写 ZCode MCP 配置
nxjt index                      # 用 NX_HOME 建索引
nxjt doctor
```

`install` 会把技能复制到 `~/.codex/skills/nxopen-journal`（ZCode/Codex 共用），
并把 `nxopen` server 写入 `~/.zcode/cli/config.json`。写前自动备份，内容不变时跳过。

其他宿主（只复制技能，并打印对应的 MCP 配置片段）：

```bash
nxjt install --target codex
nxjt install --target claude
```

## 嵌入后端

推荐远程模式：硅基流动把 `BAAI/bge-m3` 与 `BAAI/bge-reranker-v2-m3` 标为免费模型，与工具包
默认模型相同，不下载任何模型。

```bash
nxjt config embed --provider remote
```

会依次询问 base URL、嵌入模型、API key、rerank URL/模型，并写入 ZCode MCP 的 env。
切回本地：`nxjt config embed --provider local`。

本地 BGE-M3 是离线备选：先装 `pip install "nxopen-mcp-enhanced[embed]"`，首次建索引/查询会
下载约 2 GB 模型，建索引可能需要数小时。两条路都没配时 `nxjt doctor` 给 warn，`nxjt index` 失败。

`nxjt index` 写入 MCP 配置里 `--db` 指向的同一个文件，并沿用配置中的
`NXOPEN_MCP_*` 环境变量——`nxjt config embed --provider remote` 之后直接建索引即可，
不会退回本地模型；已有索引无需重建。

## 复用已有索引

若已有上游 `nxopen-mcp` 的索引，让配置直接指向它，`nxjt index` 会写同一路径：

```bash
nxjt index --db C:\Users\<you>\.nxopen-mcp\index.db
```

或在 ZCode 的 `nxopen` server `args` 里把 `--db` 改成该路径。两者 schema 相同，
但 enhanced 不会修改索引结构。

## 自检

```bash
nxjt doctor                 # NX、XML、配置的索引、嵌入后端、MCP、BOM
nxjt verify                 # check_repo.py + 真实 MCP 冒烟（启动 server 调 get_member）
nxjt verify --nx            # 追加 NX 回归套件（需真实 NX，耗时长）
```

`verify` 任一项失败即返回非零；冒烟使用配置里的 `--db`，索引缺失或没有 `Tag`
成员都会判失败，不再只看 `--help`。
