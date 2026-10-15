"""Shared fixtures for the agent-harness invariant tests.

These tests check repository structure (instruction files, rules, skills,
ignore rules, and tool pins), not package code, so they need no database,
Docker services, or network access.
"""

from __future__ import annotations

import subprocess
import tomllib
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    """Run git in the repository root and capture its output."""
    return subprocess.run(
        ["git", *args], cwd=REPO_ROOT, check=False, capture_output=True, text=True
    )


def repo_files(*pathspecs: str) -> list[Path]:
    """Return tracked plus untracked-but-not-ignored files matching pathspecs.

    Ignored files, such as skills installed by ``pixi run skills-sync``, are
    left out, so the result is what a fresh clone would hold once the working
    tree is committed.
    """
    result = _git(
        "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", *pathspecs
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr)
    paths = {REPO_ROOT / name for name in result.stdout.split("\0") if name}
    return sorted(path for path in paths if path.exists() or path.is_symlink())


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Absolute path to the repository root."""
    return REPO_ROOT


@pytest.fixture(scope="session")
def agents_md_files() -> list[Path]:
    """Every AGENTS.md in the repository, root and nested."""
    return repo_files("AGENTS.md", "*/AGENTS.md")


@pytest.fixture(scope="session")
def rule_files() -> list[Path]:
    """Every rule under .agents/rules/ that git would commit."""
    return repo_files(".agents/rules/*.md")


@pytest.fixture(scope="session")
def harness_markdown_files(agents_md_files, rule_files) -> list[Path]:
    """Markdown files that make up the agent harness."""
    files = set(agents_md_files) | set(rule_files)
    files |= set(
        repo_files("CLAUDE.md", "*/CLAUDE.md", ".agents/skills/*/SKILL.md", "AI_POLICY.md")
    )
    return sorted(files)


@pytest.fixture(scope="session")
def is_git_ignored() -> Callable[[Path | str], bool]:
    """Return a function reporting whether .gitignore rules exclude a path."""

    def check(path: Path | str) -> bool:
        rel = Path(path)
        if rel.is_absolute():
            rel = rel.relative_to(REPO_ROOT)
        result = _git("check-ignore", "--no-index", "-q", rel.as_posix())
        if result.returncode not in (0, 1):
            raise RuntimeError(result.stderr)
        return result.returncode == 0

    return check


@pytest.fixture(scope="session")
def pixi_manifest() -> dict[str, Any]:
    """The parsed pixi.toml."""
    with (REPO_ROOT / "pixi.toml").open("rb") as handle:
        return tomllib.load(handle)


@pytest.fixture(scope="session")
def pixi_tasks(pixi_manifest) -> set[str]:
    """Names of every task in pixi.toml, top-level and per feature."""
    tasks = set(pixi_manifest.get("tasks", {}))
    for feature in pixi_manifest.get("feature", {}).values():
        tasks |= set(feature.get("tasks", {}))
    return tasks


@pytest.fixture(scope="session")
def project_skill_dirs() -> list[Path]:
    """Skill directories under .agents/skills/ that git would commit."""
    return sorted({path.parent for path in repo_files(".agents/skills/*/SKILL.md")})
