# Changelog

格式遵循 [Keep a Changelog 2.0.0](https://keepachangelog.com/zh-CN/2.0.0/)，版本号遵循
[Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

## [1.0.0] - 2026-11-21

首个版本，一条命令完成安装。

### Added

- `nxjt install`：放置技能快照，写入宿主 MCP 配置或打印可合入的片段。
- `nxjt doctor`：检查 NX、API XML、索引、嵌入后端、MCP 配置与 BOM。
- `nxjt index`：按配置的嵌入后端构建索引，写入 MCP 配置指向的同一路径。
- `nxjt verify`：仓库检查与真实 MCP 冒烟；`--nx` 追加 51 个 NX 回归用例。
- `nxjt config embed`：交互配置远程或本地嵌入后端。
- 内置 `nxopen-journal` 技能快照，记录逐文件 SHA-256 并支持 `--check` 校验。
- 提供 `nxopen-journal-toolkit` 与 `nxjt` 两个命令入口。
- 文档：新增中英双语 README 与安装说明。
