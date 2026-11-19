"""Snapshot the nxopen-journal skill into the toolkit package.

The skill repo stays the single source of truth; this script exports one git
ref into src/nxopen_journal_toolkit/_skill/nxopen_journal and records hashes in
vendor-manifest.json so CI and `--check` can detect hand edits.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = Path.home() / ".codex" / "skills" / "nxopen-journal"
DEST = ROOT / "src" / "nxopen_journal_toolkit" / "_skill" / "nxopen_journal"
MANIFEST = DEST.parent / "vendor-manifest.json"
EXCLUDE_TOP = {".github", ".gitignore"}
BAT_SUFFIXES = {".bat", ".cmd"}


def git(source: Path, *args: str) -> str:
    out = subprocess.run(
        ["git", "-C", str(source), *args],
        check=True, capture_output=True, text=True)
    return out.stdout.strip()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export(source: Path, ref: str, dest: Path) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        archive = Path(tmp) / "skill.tar"
        subprocess.run(
            ["git", "-C", str(source), "archive", "--format=tar",
             "-o", str(archive), ref],
            check=True, capture_output=True)
        with tarfile.open(archive) as tar:
            tar.extractall(Path(tmp) / "tree")
        tree = Path(tmp) / "tree"
        if dest.exists():
            shutil.rmtree(dest)
        dest.mkdir(parents=True)
        for item in tree.iterdir():
            if item.name in EXCLUDE_TOP:
                continue
            target = dest / item.name
            if item.is_dir():
                shutil.copytree(item, target)
            else:
                shutil.copy2(item, target)
    for path in dest.rglob("*"):
        if path.is_file() and path.suffix.lower() in BAT_SUFFIXES:
            data = path.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            path.write_bytes(data)


def snapshot(dest: Path) -> dict[str, str]:
    return {str(p.relative_to(dest)).replace("\\", "/"): sha256_file(p)
            for p in sorted(dest.rglob("*")) if p.is_file()}


def tree_hash(files: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name in sorted(files):
        digest.update(f"{name}:{files[name]}\n".encode("utf-8"))
    return digest.hexdigest()


def write_manifest(source: Path, ref: str, files: dict[str, str]) -> dict:
    try:
        version = git(source, "describe", "--tags", "--abbrev=0", "--match", "v*")
    except subprocess.CalledProcessError:
        version = "unversioned"
    manifest = {
        "skill": {
            "version": version,
            "commit": git(source, "rev-parse", f"{ref}^{{commit}}"),
            "file_count": len(files),
            "tree_sha256": tree_hash(files),
            "files": files,
        }
    }
    MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8")
    return manifest


def check() -> int:
    if not MANIFEST.exists():
        print("manifest missing", file=sys.stderr)
        return 2
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    recorded = manifest["skill"]["files"]
    current = snapshot(DEST)
    added = sorted(set(current) - set(recorded))
    missing = sorted(set(recorded) - set(current))
    changed = sorted(n for n in set(current) & set(recorded)
                     if current[n] != recorded[n])
    if not (added or missing or changed):
        print(f"manifest OK: {len(current)} files, "
              f"skill {manifest['skill']['version']} "
              f"({manifest['skill']['commit'][:12]})")
        return 0
    print(f"manifest MISMATCH: added={added} missing={missing} "
          f"changed={changed}", file=sys.stderr)
    return 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    ap.add_argument("--ref", default="HEAD")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()

    if args.check:
        return check()
    if not (args.source / ".git").exists():
        print(f"not a git repository: {args.source}", file=sys.stderr)
        return 2
    export(args.source, args.ref, DEST)
    files = snapshot(DEST)
    manifest = write_manifest(args.source, args.ref, files)
    print(f"synced {manifest['skill']['file_count']} files from "
          f"{manifest['skill']['version']} ({manifest['skill']['commit'][:12]})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
