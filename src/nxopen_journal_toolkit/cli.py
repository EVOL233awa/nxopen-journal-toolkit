"""nxjt: install the nxopen-journal skill and its API-retrieval MCP."""
from __future__ import annotations

import importlib.util
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

import typer

app = typer.Typer(
    help="Install the nxopen-journal skill and nxopen-mcp-enhanced.")
config_app = typer.Typer(help="Configure the MCP embedding backend.")
app.add_typer(config_app, name="config")

SKILL_NAME = "nxopen-journal"
SKILL_DIR = "nxopen_journal"
PKG = Path(__file__).resolve().parent
SKILL_SRC = PKG / "_skill" / SKILL_DIR
MANIFEST = PKG / "_skill" / "vendor-manifest.json"
HOSTS: dict[str, Path] = {
    "zcode": Path.home() / ".codex" / "skills",
    "codex": Path.home() / ".codex" / "skills",
    "claude": Path.home() / ".claude" / "skills",
}
ZCODE_CONFIG = Path.home() / ".zcode" / "cli" / "config.json"
MCP_SERVER = "nxopen"
MCP_EXE = "nxopen-mcp-enhanced"
DEFAULT_DB = Path.home() / ".nxopen-mcp-enhanced" / "index.db"
DEFAULT_NX = Path(r"D:\UG-NX12")
REMOTE_ENV = (
    "NXOPEN_MCP_EMBEDDER", "NXOPEN_MCP_EMBED_URL", "NXOPEN_MCP_EMBED_MODEL",
    "NXOPEN_MCP_EMBED_API_KEY", "NXOPEN_MCP_RERANK", "NXOPEN_MCP_RERANK_URL",
    "NXOPEN_MCP_RERANK_MODEL", "NXOPEN_MCP_RERANK_API_KEY",
)


def _bom() -> dict:
    if not MANIFEST.exists():
        return {}
    return json.loads(MANIFEST.read_text(encoding="utf-8")).get("skill", {})


def _mcp_command() -> str:
    """Resolve the MCP executable the installed config points at.

    A configured absolute command wins over PATH: ZCode may run the server from
    a venv that is not on PATH, and `nxjt index`/`verify` must use the same
    executable `serve` will read. A sibling of sys.executable only helps
    pipx/venv installs of this package.
    """
    configured = str(_server_entry().get("command") or "")
    if configured and (Path(configured).exists() or shutil.which(configured)):
        return configured
    found = shutil.which(MCP_EXE)
    if found:
        return found
    candidate = Path(sys.executable).with_name(MCP_EXE + (".exe" if os.name == "nt" else ""))
    return str(candidate)


def _read_zcode() -> dict:
    if not ZCODE_CONFIG.exists():
        return {}
    return json.loads(ZCODE_CONFIG.read_text(encoding="utf-8"))


def _server_entry() -> dict:
    cfg = _read_zcode()
    return (cfg.get("mcp", {}).get("servers", {}).get(MCP_SERVER) or {})


def _configured_db() -> Path:
    """The DB the configured MCP server actually opens, so index/verify/doctor
    operate on the same file serve will read."""
    args = _server_entry().get("args") or []
    for i, arg in enumerate(args):
        if arg == "--db" and i + 1 < len(args):
            return Path(args[i + 1])
    return DEFAULT_DB


def _configured_env() -> dict[str, str]:
    raw = _server_entry().get("env") or {}
    return {k: str(v) for k, v in raw.items()
            if k.startswith("NXOPEN_MCP_")}


def _write_zcode(cfg: dict) -> None:
    text = json.dumps(cfg, indent=2, ensure_ascii=False) + "\n"
    old = ZCODE_CONFIG.read_text(encoding="utf-8") if ZCODE_CONFIG.exists() else None
    if old == text:
        return
    ZCODE_CONFIG.parent.mkdir(parents=True, exist_ok=True)
    if old is not None:
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        ZCODE_CONFIG.with_name(ZCODE_CONFIG.name + f".bak-{stamp}").write_text(
            old, encoding="utf-8")
    ZCODE_CONFIG.write_text(text, encoding="utf-8")


def _set_zcode_server(env: dict[str, str] | None = None) -> bool:
    cfg = _read_zcode()
    servers = cfg.setdefault("mcp", {}).setdefault("servers", {})
    current = servers.get(MCP_SERVER) or {}
    merged_env = dict(current.get("env") or {})
    if env is not None:
        merged_env = env
    entry = {
        "command": _mcp_command(),
        "args": ["serve", "--db", str(DEFAULT_DB)],
        "env": merged_env,
    }
    if current == entry:
        return False
    servers[MCP_SERVER] = entry
    _write_zcode(cfg)
    return True


def _targets(target: str) -> list[str]:
    if target != "auto":
        return [target]
    detected = [name for name, base in HOSTS.items()
                if base.exists() or base.parent.exists()]
    return detected or ["zcode"]


@app.command()
def install(
    target: str = typer.Option("auto", help="zcode, codex, claude, all or auto"),
    force: bool = typer.Option(False, help="overwrite an existing skill copy"),
    skill_only: bool = typer.Option(False, help="do not touch MCP configuration"),
) -> None:
    """Copy the bundled skill into host skill directories."""
    if not SKILL_SRC.exists():
        typer.echo(f"error: bundled skill missing at {SKILL_SRC}", err=True)
        raise typer.Exit(1)
    names = list(HOSTS) if target == "all" else _targets(target)
    seen: set[Path] = set()
    for name in names:
        if name not in HOSTS:
            typer.echo(f"error: unknown target {name}", err=True)
            raise typer.Exit(2)
        dest = HOSTS[name] / SKILL_NAME
        if dest in seen:
            continue
        seen.add(dest)
        if dest.exists() and not force:
            typer.echo(f"[skip] {dest} exists (use --force to overwrite)")
            continue
        if dest.exists():
            if (dest / ".git").exists():
                typer.echo(f"error: {dest} is a git repository; move it aside "
                           f"instead of using --force", err=True)
                raise typer.Exit(2)
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_SRC, dest)
        typer.echo(f"[ok] installed skill -> {dest}")
    if not skill_only and "zcode" in names:
        changed = _set_zcode_server()
        typer.echo(f"[{'ok' if changed else 'skip'}] ZCode MCP server "
                   f"'{MCP_SERVER}' -> {_mcp_command()}")
    if not skill_only:
        _print_host_snippet(names)
    typer.echo(f"skill version: {_bom().get('version', 'unknown')}")


def _print_host_snippet(names: list[str]) -> None:
    """Other hosts keep their MCP config outside ZCode; print the entry they
    need instead of writing config files we don't own."""
    exe = _mcp_command()
    for name in names:
        if name == "codex":
            typer.echo("\nCodex (~/.codex/config.toml):\n"
                       f'[mcp_servers.{MCP_SERVER}]\n'
                       f'command = "{exe}"\n'
                       f'args = ["serve", "--db", "{DEFAULT_DB}"]')
        elif name == "claude":
            typer.echo("\nClaude Code (.mcp.json):\n" + json.dumps({
                "mcpServers": {MCP_SERVER: {
                    "command": exe,
                    "args": ["serve", "--db", str(DEFAULT_DB)]}}},
                indent=2, ensure_ascii=False))


@app.command()
def doctor() -> None:
    """Check NX, the index, the MCP install and the bundled skill version."""
    failures = 0

    def report(ok: bool, label: str, detail: str = "") -> None:
        nonlocal failures
        mark = "[ok]" if ok else "[fail]"
        failures += 0 if ok else 1
        typer.echo(f"{mark} {label}{(': ' + detail) if detail else ''}")

    report(sys.version_info >= (3, 11), "Python >= 3.11", sys.version.split()[0])
    nx_home = Path(os.environ.get("NX_HOME", DEFAULT_NX))
    report(nx_home.exists(), "NX_HOME", str(nx_home))
    run_journal = nx_home / "NXBIN" / "run_journal.exe"
    report(run_journal.exists(), "run_journal.exe", str(run_journal))
    xml_dir = None
    for candidate in (nx_home / "NXBIN" / "managed",
                      nx_home / "UGII" / "managed",
                      nx_home):
        if candidate.exists() and list(candidate.glob("NXOpen*.xml")):
            xml_dir = candidate
            break
    report(xml_dir is not None, "NXOpen XML docs",
           str(xml_dir) if xml_dir else
           f"no NXOpen*.xml under {nx_home}")
    db_path = _configured_db()
    report(db_path.exists(), "API index", f"{db_path} "
           f"({db_path.stat().st_size // (1 << 20)} MB)"
           if db_path.exists() else str(db_path))
    upstream_db = Path.home() / ".nxopen-mcp" / "index.db"
    if not db_path.exists() and upstream_db.exists():
        typer.echo(f"[info] upstream index found at {upstream_db}; rebuild "
                   f"with `nxjt index`, or point the config there with --db")
    backend = _configured_env().get("NXOPEN_MCP_EMBEDDER", "").lower()
    if backend in ("remote", "llama", "llama-server", "llamacpp", "openai"):
        required = ("NXOPEN_MCP_EMBED_URL", "NXOPEN_MCP_EMBED_MODEL",
                    "NXOPEN_MCP_EMBED_API_KEY")
        missing = [k for k in required if not _configured_env().get(k)]
        report(not missing, "embedding service config",
               ", ".join(missing) if missing else backend)
    elif importlib.util.find_spec("FlagEmbedding") is None:
        typer.echo("[warn] FlagEmbedding is not installed; local semantic "
                   "search will fail. Install the [embed] extra or configure "
                   "a remote service with `nxjt config embed --provider remote`.")
    exe = _mcp_command()
    report(Path(exe).exists() or shutil.which(exe) is not None,
           "nxopen-mcp-enhanced", exe)
    cfg = _read_zcode()
    entry = cfg.get("mcp", {}).get("servers", {}).get(MCP_SERVER)
    report(bool(entry), f"ZCode MCP server '{MCP_SERVER}'",
           (entry or {}).get("command", "not configured"))
    skill = _bom()
    report(bool(skill), "bundled skill", f"{skill.get('version', '?')} "
           f"({str(skill.get('commit', ''))[:12]})")
    if importlib.util.find_spec("nxopen_mcp") is not None:
        typer.echo("[warn] upstream module nxopen_mcp is installed too; "
                   "this package uses nxopen_mcp_enhanced and does not "
                   "share its index")
    if failures:
        raise typer.Exit(1)


@app.command()
def index(
    nx_path: str = typer.Option("", help="NX install root (default NX_HOME)"),
    db: str = typer.Option("", help="index path (default from MCP config)"),
    workers: int = typer.Option(1, help="parallel embedding workers"),
) -> None:
    """Build the NXOpen API index with the bundled MCP."""
    root = nx_path or os.environ.get("NX_HOME", str(DEFAULT_NX))
    db_path = Path(db) if db else _configured_db()
    cmd = [_mcp_command(), "index", "--nx-path", root, "--db", str(db_path)]
    if workers > 1:
        cmd += ["--workers", str(workers)]
    # serve gets its embedding settings from the MCP config; index runs as a
    # child process, so pass the same NXOPEN_* variables explicitly or a
    # remote-mode user would silently build with the local model.
    env = dict(os.environ)
    env.update(_configured_env())
    raise typer.Exit(subprocess.run(cmd, env=env).returncode)


def _mcp_smoke(db: Path) -> tuple[bool, str]:
    """Start the configured MCP server and call get_member('Tag') over stdio.

    `--help` only proves the executable exists; this proves the configured
    index opens, the handshake completes and a tool answers. stdin stays open
    until the reply arrives: closing it early can end the server loop before
    the tool call is served.
    """
    try:
        proc = subprocess.Popen(
            [_mcp_command(), "serve", "--db", str(db)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, encoding="utf-8",
            errors="replace", bufsize=1,
            env={**os.environ, **_configured_env()})
    except OSError as exc:
        return False, str(exc)
    lines: queue.Queue[str] = queue.Queue()

    def _reader() -> None:
        for line in proc.stdout:
            lines.put(line)

    threading.Thread(target=_reader, daemon=True).start()

    def send(msg: dict) -> None:
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def wait_for(mid: int, timeout: float) -> dict:
        deadline = time.monotonic() + timeout
        while True:
            remain = deadline - time.monotonic()
            if remain <= 0:
                raise TimeoutError(f"no reply for request {mid}")
            line = lines.get(timeout=remain)
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue
            if msg.get("id") == mid:
                return msg

    try:
        send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "nxjt-verify", "version": "0"}}})
        wait_for(1, 20)
        send({"jsonrpc": "2.0", "method": "notifications/initialized"})
        send({"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {
            "name": "get_member", "arguments": {"member_name": "Tag"}}})
        result = wait_for(2, 40).get("result") or {}
    except (TimeoutError, queue.Empty, OSError, ValueError) as exc:
        return False, str(exc)
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    text = "\n".join(c.get("text", "") for c in result.get("content") or [])
    if result.get("isError") or not text.startswith("### "):
        return False, text.splitlines()[0][:120] if text else "empty result"
    return True, text.splitlines()[0][:80]


@app.command()
def verify(
    nx: bool = typer.Option(False, help="also run the NX regression suite"),
    skill_dir: str = typer.Option("", help="installed skill directory"),
) -> None:
    """Run the skill self-check and an MCP smoke test."""
    root = Path(skill_dir) if skill_dir else None
    if root is None:
        for name in ("zcode", "codex", "claude"):
            base = HOSTS.get(name)
            if base is not None and (base / SKILL_NAME).exists():
                root = base / SKILL_NAME
                break
    if root is None or not root.exists():
        typer.echo("error: skill not installed; run `nxjt install` first",
                   err=True)
        raise typer.Exit(2)
    check = root / "scripts" / "check_repo.py"
    check_rc = subprocess.run([sys.executable, str(check), str(root)],
                              check=False).returncode
    db = _configured_db()
    ok, detail = _mcp_smoke(db)
    typer.echo(f"[{'ok' if ok else 'fail'}] MCP smoke ({db}): {detail}")
    if nx:
        suite = root / "scripts" / "tests" / "RUN_TESTS.bat"
        suite_rc = subprocess.run([str(suite)], cwd=str(suite.parent)).returncode
        if suite_rc:
            raise typer.Exit(suite_rc)
    if check_rc or not ok:
        raise typer.Exit(1)


@config_app.command("embed")
def config_embed(
    provider: str = typer.Option("local", help="local or remote"),
) -> None:
    """Switch the MCP between local BGE-M3 and an OpenAI-compatible service."""
    cfg = _read_zcode()
    servers = cfg.setdefault("mcp", {}).setdefault("servers", {})
    entry = servers.setdefault(MCP_SERVER, {
        "command": _mcp_command(),
        "args": ["serve", "--db", str(DEFAULT_DB)],
        "env": {},
    })
    env = dict(entry.get("env") or {})
    if provider == "local":
        for key in REMOTE_ENV:
            env.pop(key, None)
    elif provider == "remote":
        url = typer.prompt("Embedding base URL",
                           default="https://api.siliconflow.cn")
        model = typer.prompt("Embedding model", default="BAAI/bge-m3")
        key = typer.prompt("API key", hide_input=True)
        rerank_url = typer.prompt("Rerank URL",
                                  default=url.rstrip("/") + "/v1/rerank")
        rerank_model = typer.prompt("Rerank model",
                                    default="BAAI/bge-reranker-v2-m3")
        env.update({
            "NXOPEN_MCP_EMBEDDER": "remote",
            "NXOPEN_MCP_EMBED_URL": url,
            "NXOPEN_MCP_EMBED_MODEL": model,
            "NXOPEN_MCP_EMBED_API_KEY": key,
            "NXOPEN_MCP_RERANK": "1",
            "NXOPEN_MCP_RERANK_URL": rerank_url,
            "NXOPEN_MCP_RERANK_MODEL": rerank_model,
            "NXOPEN_MCP_RERANK_API_KEY": key,
        })
    else:
        typer.echo("error: provider must be local or remote", err=True)
        raise typer.Exit(2)
    entry["env"] = env
    _write_zcode(cfg)
    typer.echo(f"[ok] embedding provider set to {provider}")


if __name__ == "__main__":
    app()
