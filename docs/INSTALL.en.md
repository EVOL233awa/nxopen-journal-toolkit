# Installation

[中文](INSTALL.md) | English

Host-agnostic manual installation steps. The [Hand installation to an
agent](../README.en.md#hand-installation-to-an-agent-recommended) section of the README has a complete
prompt to copy to an agent; the agent checks the environment, installs, registers the MCP, builds the
index, and runs the self-check.

## Prerequisites

| Item | Requirement |
|---|---|
| Python | 3.11+ (for `nxjt` and the MCP; NX journals still run on NX embedded 3.6.1) |
| Siemens NX | 12.x; `NX_HOME` points to the install root, default `D:\UG-NX12` |
| Disk | Skill about 4 MB; index about 400 MB (local build) |

## Installation

### Toolkit and MCP

Neither is on PyPI yet, so both must be installed from source. The MCP is a dependency of the toolkit;
install the MCP first so that `pip` satisfies the dependency locally instead of looking for a
same-named package on PyPI:

```bash
git clone https://github.com/EVOL233awa/nxopen-mcp-enhanced
python -m pip install -e nxopen-mcp-enhanced
git clone https://github.com/EVOL233awa/nxopen-journal-toolkit
cd nxopen-journal-toolkit
python -m pip install -e .
```

### Skill

The bundled snapshot is at `src/nxopen_journal_toolkit/_skill/nxopen_journal`. Copy or link it into
the host's skill directory, keeping the directory name `nxopen-journal`; `nxjt install` can do it for
you:

| `--target` | Skill directory | MCP configuration |
|---|---|---|
| `codex` | `%USERPROFILE%\.codex\skills` | Prints a `config.toml` snippet |
| `claude` | `%USERPROFILE%\.claude\skills` | Prints a `.mcp.json` snippet |
| `all` | All built-in host directories | Writes the default MCP configuration entry and prints the other snippets |
| `auto` (default) | Detects existing built-in host directories; falls back to the default target | Same as the detection result |

Other target names and directories are listed by `nxjt install --help`.

```bash
nxjt install --target auto
```

An existing target is skipped by default; `--force` overwrites it, but a git repository is never
deleted. Directory conventions and write targets follow the `--target` table; for hosts not in the
table, place files manually and register the MCP yourself.

### MCP

The stdio command is `nxopen-mcp-enhanced serve --db <index path>`; the default index is
`%USERPROFILE%\.nxopen-mcp-enhanced\index.db`. Register it in the host's MCP configuration format.
Generic JSON:

```json
{"mcpServers":{"nxopen":{"command":"nxopen-mcp-enhanced","args":["serve","--db","<index path>"]}}}
```

If `nxjt install` supports your host, the matching `--target` writes the configuration or prints a
ready-to-merge snippet; other hosts register it per their own documentation. Switching hosts only
requires re-registering this entry; the skill directory and index can be reused.

## Embedding backend

The remote mode is recommended: SiliconFlow lists `BAAI/bge-m3` and `BAAI/bge-reranker-v2-m3` as free
models, the same models the toolkit uses by default, and no model is downloaded.

```bash
nxjt config embed --provider remote
```

The command interactively writes the base URL, embedding model, API key, and rerank URL/model to the
toolkit's default MCP configuration entry. If your host does not use that entry, set the
`NXOPEN_MCP_*` environment variables directly: set them in the shell before building the index and
put the same variables in the host MCP configuration's `env`; the full variable list is in the
README's agent install prompt. Switch back to local with `nxjt config embed --provider local`.

Local BGE-M3 is the offline alternative: install `pip install "nxopen-mcp-enhanced[embed]"` first;
the first index build or query downloads about 2 GB of models, and the build may take hours. With
neither path configured, `nxjt doctor` warns and `nxjt index` fails.

`nxjt index` writes the same file as `--db` in the MCP configuration and reuses the configured
`NXOPEN_MCP_*` environment variables—after `nxjt config embed --provider remote`, build the index
directly; it will not silently fall back to the local model. An existing index does not need a
rebuild.

## Reusing an existing index

If an upstream `nxopen-mcp` index already exists on the machine, point the configuration at it;
`nxjt index` writes the same path:

```bash
nxjt index --db C:\Users\<you>\.nxopen-mcp\index.db
```

Or change `--db` to that path in the `args` of the host MCP configuration's `nxopen` server. The
schemas are identical, and enhanced does not modify the index structure. Reuse requires the same
embedding model—vectors in the index come from the model used at build time, so changing models
requires a rebuild.

## Self-check

```bash
nxjt doctor                 # NX, XML, configured index, embedding backend, MCP, BOM
nxjt verify                 # check_repo.py + real MCP smoke (starts the server and calls get_member)
nxjt verify --nx            # adds the NX regression suite (needs real NX, slow)
```

`verify` returns nonzero if any check fails; the smoke test uses the configured `--db`, and a missing
index or a missing `Tag` member fails the check—it does not stop at `--help`. When the skill
directory is outside the CLI's probe paths `%USERPROFILE%\.codex\skills` and
`%USERPROFILE%\.claude\skills`, pass `--skill-dir <skill directory>`. `doctor`'s MCP configuration
check targets the toolkit's default write target; if the host does not use that target, the item
fails as expected—verify the host's own MCP configuration and a real `get_member` call instead. The
`verify` smoke test also reads the index path from the toolkit's default MCP configuration; if the
index is not at the default path, rely on the host call.
