"""nxjt: install the nxopen-journal skill and its API-retrieval MCP."""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
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
    found = shutil.which(MCP_EXE)
    if found:
        return found
    candidate = Path(sys.executable).with_name(MCP_EXE + (".exe" if os.name == "nt" else ""))
    return str(candidate)


def _read_zcode() -> dict:
    if not ZCODE_CONFIG.exists():
        return {}
    return json.loads(ZCODE_CONFIG.read_text(encoding="utf-8"))


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
            shutil.rmtree(dest)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SKILL_SRC, dest)
        typer.echo(f"[ok] installed skill -> {dest}")
    if not skill_only and "zcode" in names:
        changed = _set_zcode_server()
        typer.echo(f"[{'ok' if changed else 'skip'}] ZCode MCP server "
                   f"'{MCP_SERVER}' -> {_mcp_command()}")
    typer.echo(f"skill version: {_bom().get('version', 'unknown')}")


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
    report(DEFAULT_DB.exists(), "API index", f"{DEFAULT_DB} "
           f"({DEFAULT_DB.stat().st_size // (1 << 20)} MB)"
           if DEFAULT_DB.exists() else str(DEFAULT_DB))
    upstream_db = Path.home() / ".nxopen-mcp" / "index.db"
    if not DEFAULT_DB.exists() and upstream_db.exists():
        typer.echo(f"[info] upstream index found at {upstream_db}; rebuild "
                   f"with `nxjt index`, or point the config there with --db")
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
    db: str = typer.Option("", help="index path (default ~/.nxopen-mcp-enhanced)"),
    workers: int = typer.Option(1, help="parallel embedding workers"),
) -> None:
    """Build the NXOpen API index with the bundled MCP."""
    root = nx_path or os.environ.get("NX_HOME", str(DEFAULT_NX))
    cmd = [_mcp_command(), "index", "--nx-path", root]
    if db:
        cmd += ["--db", db]
    if workers > 1:
        cmd += ["--workers", str(workers)]
    raise typer.Exit(subprocess.run(cmd).returncode)


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
    subprocess.run([sys.executable, str(check), str(root)], check=False)
    smoke = subprocess.run([_mcp_command(), "--help"],
                           capture_output=True, text=True)
    typer.echo(f"[{'ok' if smoke.returncode == 0 else 'fail'}] MCP smoke")
    if nx:
        suite = root / "scripts" / "tests" / "RUN_TESTS.bat"
        raise typer.Exit(subprocess.run([str(suite)], cwd=str(suite.parent)).returncode)


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
