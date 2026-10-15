"""Rules under .agents/rules/ are committable, kebab-case, and self-describing."""

from __future__ import annotations

import re

MOVED_FROM_AGENT_DOCS = {
    "code-quality.md",
    "docker-workflow.md",
    "namespace-packages.md",
    "testing-patterns.md",
    "troubleshooting.md",
}


def test_agent_docs_directory_is_retired(repo_root):
    assert not (repo_root / "agent_docs").exists(), (
        "agent_docs/ moved to .agents/rules/; delete the old directory"
    )


def test_moved_rules_are_present_and_committable(rule_files):
    missing = MOVED_FROM_AGENT_DOCS - {path.name for path in rule_files}
    assert not missing, f"missing, or hidden by .gitignore: {sorted(missing)}"


def test_rule_file_names_are_kebab_case(rule_files):
    bad = [
        path.name
        for path in rule_files
        if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*\.md", path.name)
    ]
    assert not bad, f"rename to kebab-case: {bad}"


def test_every_rule_opens_with_title_and_load_when(rule_files):
    assert rule_files, "no rule files found under .agents/rules/"
    bad = []
    for path in rule_files:
        lines = path.read_text(encoding="utf-8").splitlines()
        if (
            len(lines) < 3
            or not lines[0].startswith("# ")
            or lines[1] != ""
            or not lines[2].startswith("**Load when:**")
        ):
            bad.append(path.name)
    assert not bad, (
        "each rule must open with '# Title', a blank line, then "
        f"'**Load when:** ...': {bad}"
    )
