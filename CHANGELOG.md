# Changelog

`nxopen-journal-toolkit` 的版本变更记录。

格式遵循 [Keep a Changelog 2.0.0](https://keepachangelog.com/zh-CN/2.0.0/)，版本号遵循 [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### Changed

- 许可：`LICENSE` 版权行补仓库地址，新增 `NOTICE` 与 `TRADEMARK.md`（MIT 条款不变）。
- 源码归档与克隆统一为 LF 换行，`*.bat` 保持 CRLF。
- 内部：`pyproject.toml` 补 `authors` 与 `[project.urls]`，`pip show` 显示作者与仓库。

## [1.0.0] - 2026-11-21

首个版本，一条命令完成安装。

### Added

- `nxjt install`：放置技能快照，写入宿主 MCP 配置或打印可合入的片段。
- `nxjt doctor`：检查 NX、API XML、索引、嵌入后端、MCP 配置与 BOM。
- `nxjt index`：按配置的嵌入后端构建索引，写入 MCP 配置指向的同一路径。
- `nxjt verify`：仓库检查与真实 MCP 冒烟；`--nx` 追加 54 个 NX 回归用例（51 个带判定）。
- `nxjt config embed`：交互配置远程或本地嵌入后端。
- 内置 `nxopen-journal` 技能快照，`--check` 可校验完整性。
- 提供 `nxopen-journal-toolkit` 与 `nxjt` 两个命令入口。
- 文档：新增中英双语 README 与安装说明。

[1.0.0]: https://github.com/EVOL233awa/nxopen-journal-toolkit/releases/tag/v1.0.0
