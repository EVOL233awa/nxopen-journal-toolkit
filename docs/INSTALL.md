# 安装说明

[English](INSTALL.en.md) | 中文

宿主无关的手动安装步骤。README 的[交给 agent 安装](../README.md#交给-agent-安装推荐)一节有可直接
复制给 agent 的完整提示词，由 agent 检查环境、安装、注册 MCP、建索引并自检。

## 前置

| 项 | 要求 |
|---|---|
| Python | 3.11+（`nxjt` 与 MCP 用；NX journal 仍由 NX 内嵌 3.6.1 执行） |
| Siemens NX | 12.x；`NX_HOME` 指向安装根，默认 `D:\UG-NX12` |
| 磁盘 | 技能约 4 MB；索引约 400 MB（本机构建） |

## 安装

### 工具包与 MCP

两者都未发布到 PyPI，安装包挂在 GitHub Release。MCP 是工具包的依赖，先装 MCP 再装工具包，
`pip` 才能在本机满足依赖，不会去 PyPI 找同名包：

```bash
python -m pip install https://github.com/EVOL233awa/nxopen-mcp-enhanced/releases/download/v1.0.0/nxopen_mcp_enhanced-1.0.0-py3-none-any.whl
python -m pip install https://github.com/EVOL233awa/nxopen-journal-toolkit/releases/download/v1.0.0/nxopen_journal_toolkit-1.0.0-py3-none-any.whl
```

开发或需要 extras 时改从源码安装（editable），顺序同样先 MCP 后工具包：

```bash
git clone https://github.com/EVOL233awa/nxopen-mcp-enhanced
python -m pip install -e "nxopen-mcp-enhanced[reflect]"
git clone https://github.com/EVOL233awa/nxopen-journal-toolkit
cd nxopen-journal-toolkit
python -m pip install -e .
```

### 技能

快照在已安装包的 `_skill/nxopen_journal` 下（源码树里是
`src/nxopen_journal_toolkit/_skill/nxopen_journal`）。复制或链接到宿主的技能目录，目录名保持
`nxopen-journal`；`nxjt install` 可代劳。取得快照绝对路径：

```bash
python -c "import nxopen_journal_toolkit, pathlib; print(pathlib.Path(nxopen_journal_toolkit.__file__).parent / '_skill' / 'nxopen_journal')"
```

`nxjt install` 的技能目录与 MCP 配置写入范围：

| `--target` | 技能目录 | MCP 配置 |
|---|---|---|
| `codex` | `%USERPROFILE%\.codex\skills` | 打印 `config.toml` 片段 |
| `claude` | `%USERPROFILE%\.claude\skills` | 打印 `.mcp.json` 片段 |
| `all` | 所有内置宿主目录 | 写入默认 MCP 配置入口并打印其余片段 |
| `auto`（默认） | 探测已存在的内置宿主目录，未探测到回退默认目标 | 同探测结果 |

其余目标名与目录以 `nxjt install --help` 为准。

```bash
nxjt install --target auto
```

目标已存在时默认跳过，`--force` 覆盖，但目标是 git 仓库时拒绝删除。目录约定与写入目标以
`--target` 表为准；宿主不在表内时手动放置并自行注册 MCP。

### MCP

stdio 命令为 `nxopen-mcp-enhanced serve --db <索引路径>`，默认索引
`%USERPROFILE%\.nxopen-mcp-enhanced\index.db`。按宿主的 MCP 配置格式注册，通用 JSON：

```json
{"mcpServers":{"nxopen":{"command":"nxopen-mcp-enhanced","args":["serve","--db","<索引路径>"]}}}
```

若宿主受 `nxjt install` 支持，对应 `--target` 会写入配置或打印可直接合入的片段；其他宿主按
自己的文档注册。换宿主只需重注册这一条，技能目录与索引可复用。

## 嵌入后端

推荐远程模式：硅基流动把 `BAAI/bge-m3` 与 `BAAI/bge-reranker-v2-m3` 标为免费模型，与工具包
默认模型相同，不下载任何模型。

```bash
nxjt config embed --provider remote
```

该命令交互写入 base URL、嵌入模型、API key、rerank URL/模型，落到工具包默认的 MCP 配置入口。
宿主不使用该入口时直接设置 `NXOPEN_MCP_*` 环境变量：建索引前在 shell 里设置，并把同一组变量
写入宿主 MCP 配置的 `env`；完整变量清单见 README 的 agent 安装提示词。切回本地：
`nxjt config embed --provider local`。

本地 BGE-M3 是离线备选：先装 `pip install FlagEmbedding`，首次建索引/查询会
下载约 2 GB 模型，建索引可能需要数小时。两条路都没配时 `nxjt doctor` 给 warn，`nxjt index` 失败。

`nxjt index` 写入 MCP 配置里 `--db` 指向的同一个文件，并沿用配置中的
`NXOPEN_MCP_*` 环境变量——`nxjt config embed --provider remote` 之后直接建索引即可，
不会退回本地模型；已有索引无需重建。

## 复用已有索引

若本机已有上游 `nxopen-mcp` 的索引，让配置直接指向它，`nxjt index` 会写同一路径：

```bash
nxjt index --db C:\Users\<you>\.nxopen-mcp\index.db
```

或在宿主 MCP 配置的 `nxopen` server `args` 里把 `--db` 改成该路径。两者 schema 相同，
但 enhanced 不会修改索引结构。复用的前提是嵌入模型一致——索引里的向量由建索引时的模型产生，
换模型要重建。

## 自检

```bash
nxjt doctor                 # NX、XML、配置的索引、嵌入后端、MCP、BOM
nxjt verify                 # check_repo.py + 真实 MCP 冒烟（启动 server 调 get_member）
nxjt verify --nx            # 追加 NX 回归套件（需真实 NX，耗时长）
```

`verify` 任一项失败即返回非零；冒烟使用配置里的 `--db`，索引缺失或没有 `Tag` 成员都会判失败，
不再只看 `--help`。技能目录不在 CLI 探测的 `%USERPROFILE%\.codex\skills`、
`%USERPROFILE%\.claude\skills` 时，需传 `--skill-dir <技能目录>`。`doctor` 的 MCP 配置检查
针对工具包默认的写入目标；宿主不使用该目标时该项会失败，属预期，以宿主自身的 MCP 配置和
`get_member` 实际调用为准。`verify` 冒烟读取的索引路径同样来自工具包默认的 MCP 配置，
索引不在默认路径时以宿主调用为准。
