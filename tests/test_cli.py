"""CLI tests: no NX, no network, temporary HOME layout."""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from nxopen_journal_toolkit import cli

runner = CliRunner()


@pytest.fixture()
def sandbox(tmp_path, monkeypatch):
    hosts = {
        "zcode": tmp_path / "zcode" / "skills",
        "codex": tmp_path / "codex" / "skills",
    }
    monkeypatch.setattr(cli, "HOSTS", hosts)
    monkeypatch.setattr(cli, "ZCODE_CONFIG", tmp_path / "zcode" / "cli" / "config.json")
    monkeypatch.setattr(cli, "DEFAULT_DB", tmp_path / "index.db")
    return hosts


def test_bom_loaded():
    bom = cli._bom()
    assert bom["version"]
    assert len(bom["commit"]) >= 7
    assert bom["file_count"] > 100


def test_install_and_idempotent(sandbox):
    first = runner.invoke(cli.app, ["install", "--target", "zcode"])
    assert first.exit_code == 0, first.output
    dest = sandbox["zcode"] / cli.SKILL_NAME
    assert (dest / "SKILL.md").exists()
    assert (dest / "scripts" / "check_repo.py").exists()
    config = json.loads(cli.ZCODE_CONFIG.read_text(encoding="utf-8"))
    assert config["mcp"]["servers"]["nxopen"]["args"][:1] == ["serve"]

    second = runner.invoke(cli.app, ["install", "--target", "zcode"])
    assert second.exit_code == 0
    assert "[skip]" in second.output

    forced = runner.invoke(cli.app, ["install", "--target", "zcode", "--force"])
    assert forced.exit_code == 0
    assert "[ok] installed skill" in forced.output


def test_install_skill_only_skips_config(sandbox):
    result = runner.invoke(cli.app, ["install", "--target", "zcode",
                                     "--skill-only"])
    assert result.exit_code == 0
    assert not cli.ZCODE_CONFIG.exists()


def test_config_embed_local_removes_remote_env(sandbox):
    cli.ZCODE_CONFIG.parent.mkdir(parents=True)
    cli.ZCODE_CONFIG.write_text(json.dumps({
        "mcp": {"servers": {"nxopen": {
            "command": "x", "args": [], "env": {
                "NXOPEN_MCP_EMBEDDER": "remote",
                "NXOPEN_MCP_RERANK": "1",
                "KEEP": "1",
            }}}}
    }), encoding="utf-8")
    result = runner.invoke(cli.app, ["config", "embed", "--provider", "local"])
    assert result.exit_code == 0, result.output
    env = json.loads(cli.ZCODE_CONFIG.read_text(encoding="utf-8"))[
        "mcp"]["servers"]["nxopen"]["env"]
    assert "NXOPEN_MCP_EMBEDDER" not in env
    assert "NXOPEN_MCP_RERANK" not in env
    assert env["KEEP"] == "1"


def test_doctor_reports_missing_nx(sandbox, monkeypatch, tmp_path):
    monkeypatch.setenv("NX_HOME", str(tmp_path / "no-nx"))
    monkeypatch.setattr(cli, "DEFAULT_DB", tmp_path / "missing.db")
    result = runner.invoke(cli.app, ["doctor"])
    assert result.exit_code == 1
    assert "[fail] NX_HOME" in result.output


def test_verify_without_install_fails(sandbox):
    result = runner.invoke(cli.app, ["verify"])
    assert result.exit_code == 2


def test_install_prints_host_snippet_without_writing_config(sandbox):
    result = runner.invoke(cli.app, ["install", "--target", "codex"])
    assert result.exit_code == 0, result.output
    assert "mcp_servers.nxopen" in result.output
    assert not cli.ZCODE_CONFIG.exists()


def test_install_force_refuses_git_repository(sandbox):
    dest = sandbox["zcode"] / cli.SKILL_NAME
    (dest / ".git").mkdir(parents=True)
    result = runner.invoke(cli.app, ["install", "--target", "zcode", "--force"])
    assert result.exit_code == 2
    assert (dest / ".git").exists()


def test_verify_fails_when_smoke_fails(sandbox, monkeypatch):
    install = runner.invoke(cli.app, ["install", "--target", "zcode",
                                      "--skill-only"])
    assert install.exit_code == 0, install.output
    dest = sandbox["zcode"] / cli.SKILL_NAME

    class Ok:
        returncode = 0

    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: Ok())
    monkeypatch.setattr(cli, "_mcp_smoke", lambda db: (False, "boom"))
    result = runner.invoke(cli.app, ["verify", "--skill-dir", str(dest)])
    assert result.exit_code == 1
    assert "[fail] MCP smoke" in result.output


def test_verify_fails_when_check_repo_fails(sandbox, monkeypatch):
    install = runner.invoke(cli.app, ["install", "--target", "zcode",
                                      "--skill-only"])
    assert install.exit_code == 0, install.output
    dest = sandbox["zcode"] / cli.SKILL_NAME

    class Failed:
        returncode = 1

    monkeypatch.setattr(cli.subprocess, "run", lambda *a, **k: Failed())
    monkeypatch.setattr(cli, "_mcp_smoke", lambda db: (True, "ok"))
    result = runner.invoke(cli.app, ["verify", "--skill-dir", str(dest)])
    assert result.exit_code == 1


def test_index_uses_configured_db_and_embedding_env(sandbox, monkeypatch):
    cli.ZCODE_CONFIG.parent.mkdir(parents=True)
    cli.ZCODE_CONFIG.write_text(json.dumps({
        "mcp": {"servers": {"nxopen": {
            "command": "x",
            "args": ["serve", "--db", str(sandbox["zcode"] / "custom.db")],
            "env": {"NXOPEN_MCP_EMBEDDER": "remote",
                    "NXOPEN_MCP_EMBED_URL": "https://example.test"},
        }}}
    }), encoding="utf-8")
    captured = {}

    class Ok:
        returncode = 0

    def fake_run(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["env"] = kwargs.get("env") or {}
        return Ok()

    monkeypatch.setattr(cli.subprocess, "run", fake_run)
    result = runner.invoke(cli.app, ["index", "--nx-path", "D:/NX"])
    assert result.exit_code == 0, result.output
    assert str(sandbox["zcode"] / "custom.db") in captured["cmd"]
    assert captured["env"]["NXOPEN_MCP_EMBEDDER"] == "remote"
    assert captured["env"]["NXOPEN_MCP_EMBED_URL"] == "https://example.test"
