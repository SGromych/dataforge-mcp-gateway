"""The distribution must contain every module the server imports.

This file exists because of a real outage: a `cache/` line in `.gitignore` — meant for
the runtime cache directory — also matched `src/dataforge_mcp/cache/`, so two modules
were never committed. hatchling honours VCS ignore files, so the wheel shipped without
them and every way of starting the server died with ModuleNotFoundError while
`pip install` reported success. Both halves of that failure are checked here.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "src" / "dataforge_mcp"


def _git(*args: str) -> str:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError) as exc:  # pragma: no cover - env-specific
        pytest.skip(f"git unavailable: {exc}")
    if result.returncode not in (0, 1):  # 1 = "nothing matched", a valid answer
        pytest.skip(f"not a usable git checkout: {result.stderr.strip()}")
    return result.stdout


def _source_modules() -> list[Path]:
    return sorted(
        path
        for path in PACKAGE_ROOT.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def test_every_source_module_is_tracked_by_git() -> None:
    tracked = {
        (REPO_ROOT / line).resolve()
        for line in _git("ls-files", "src/dataforge_mcp").splitlines()
        if line
    }
    if not tracked:  # pragma: no cover - environment without a checkout
        pytest.skip("no tracked files reported")

    untracked = [p for p in _source_modules() if p.resolve() not in tracked]
    assert untracked == [], (
        "these modules exist on disk but are not committed, so they will be missing "
        f"from the distribution: {[str(p.relative_to(REPO_ROOT)) for p in untracked]}"
    )


def test_no_source_module_is_ignored() -> None:
    """`git check-ignore` lists the paths a future `.gitignore` rule would swallow."""
    modules = [str(p.relative_to(REPO_ROOT)) for p in _source_modules()]
    ignored = [line for line in _git("check-ignore", "--", *modules).splitlines() if line]
    assert ignored == [], f".gitignore matches source modules: {ignored}"


def test_build_does_not_consult_vcs_ignore_files() -> None:
    """Belt and braces: even a bad ignore rule must not reach the build."""
    config = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert config["tool"]["hatch"]["build"]["ignore-vcs"] is True


def test_cache_package_is_importable_from_the_installed_package() -> None:
    from dataforge_mcp.cache.file_store import FileCacheStore
    from dataforge_mcp.cache.store import CacheStore

    assert issubclass(FileCacheStore, CacheStore)
