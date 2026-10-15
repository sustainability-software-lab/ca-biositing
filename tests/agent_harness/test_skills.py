"""Project skills are portable, committed, discoverable, and safe from skills-sync."""

from __future__ import annotations

import json
import os
import re
import subprocess

import pytest
import yaml

PROJECT_SKILLS = {
    "clean-branches", "commit", "create-issue", "create-pr", "docs", "merge-pr",
    "okf-memory", "push",
}
SKILL_NAME_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")


def read_frontmatter(path) -> dict:
    text = path.read_text(encoding="utf-8")
    assert text.startswith("---\n"), f"{path} has no YAML frontmatter"
    return yaml.safe_load(text.split("---\n", 2)[1])


@pytest.fixture(scope="module")
def local_registry(repo_root) -> list[str]:
    manifest = json.loads((repo_root / "skills.json").read_text(encoding="utf-8"))
    return next(s for s in manifest["sources"] if s["registry"] == "local")["skills"]


@pytest.fixture(scope="module")
def synced_skill_names(repo_root) -> set[str]:
    lock = json.loads((repo_root / "skills-lock.json").read_text(encoding="utf-8"))
    return set(lock["skills"])


def test_project_skills_are_committable(project_skill_dirs):
    missing = PROJECT_SKILLS - {path.name for path in project_skill_dirs}
    assert not missing, (
        f"missing, or hidden by .gitignore (add `!.agents/skills/<name>/`): {sorted(missing)}"
    )


def test_skill_frontmatter_follows_the_agent_skills_spec(project_skill_dirs):
    for skill_dir in project_skill_dirs:
        meta = read_frontmatter(skill_dir / "SKILL.md")
        assert set(meta) == {"name", "description"}, f"{skill_dir.name}: {sorted(meta)}"
        assert meta["name"] == skill_dir.name
        assert SKILL_NAME_RE.fullmatch(meta["name"]) and len(meta["name"]) <= 64
        description = meta["description"]
        assert isinstance(description, str) and 0 < len(description) <= 1024
        assert description.startswith("Use "), f"{skill_dir.name}: say when to use it"


def test_claude_code_sees_skills_through_a_committed_symlink(repo_root):
    link = repo_root / ".claude" / "skills"
    assert link.is_symlink(), ".claude/skills must be a symlink (Windows: core.symlinks)"
    assert os.readlink(link) == "../.agents/skills"
    staged = subprocess.run(
        ["git", "ls-files", "-s", ".claude/skills"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout
    assert staged.startswith("120000 "), "stage .claude/skills as a symlink"


def test_synced_skills_and_local_agent_state_stay_ignored(is_git_ignored, synced_skill_names):
    for name in sorted(synced_skill_names):
        assert is_git_ignored(f".agents/skills/{name}/SKILL.md"), name
    for path in (".claude/settings.local.json", ".claude/worktrees/x/y", ".agents/state.json"):
        assert is_git_ignored(path), path


def test_no_registry_skill_shadows_a_project_skill(project_skill_dirs, synced_skill_names):
    clash = synced_skill_names & {path.name for path in project_skill_dirs}
    assert not clash, (
        f"`pixi run skills-sync` would delete and replace these project skills: {sorted(clash)}; "
        "filter them out of skills.json"
    )


def test_skills_json_declares_every_project_skill(project_skill_dirs, local_registry):
    undeclared = {path.name for path in project_skill_dirs} - set(local_registry)
    assert not undeclared, f"add to the 'local' registry in skills.json: {sorted(undeclared)}"


def test_declared_local_skills_on_disk_are_not_ignored(repo_root, local_registry, is_git_ignored):
    hidden = [
        name
        for name in local_registry
        if (repo_root / ".agents" / "skills" / name / "SKILL.md").exists()
        and is_git_ignored(f".agents/skills/{name}/SKILL.md")
    ]
    assert not hidden, "allowlist in .gitignore: " + ", ".join(
        f"!.agents/skills/{name}/" for name in hidden
    )


def test_merge_pr_is_safe_in_linked_worktrees(repo_root):
    text = (repo_root / ".agents/skills/merge-pr/SKILL.md").read_text(encoding="utf-8")
    text = " ".join(text.split())
    for required in (
        "git rev-parse --git-common-dir",
        'git stash push -u -m "merge-pr-<number>"',
        "git stash apply <sha>",
        "git worktree remove <path>",
    ):
        assert required in text, required
    for upstream_only in (
        "stash them before proceeding: `git stash`",
        "restore them: `git stash pop`",
    ):
        assert upstream_only not in text, upstream_only


def test_commit_and_pr_skills_follow_the_ai_policy(repo_root):
    for skill in ("commit", "create-pr"):
        text = (repo_root / ".agents/skills" / skill / "SKILL.md").read_text(encoding="utf-8")
        assert "Assisted-by: <harness>:<model>" in text, skill
