"""The README tells humans where the agent harness lives."""

from __future__ import annotations


def test_readme_describes_the_agent_harness(repo_root):
    text = (repo_root / "README.md").read_text(encoding="utf-8")
    assert "\n## AI Agents\n" in text
    section = text.split("\n## AI Agents\n", 1)[1].split("\n## ", 1)[0]
    for needle in (
        "AGENTS.md", ".agents/rules/", "CLAUDE.md", ".agents/skills/",
        ".claude/skills", "pixi run skills-sync", "knowledge/", "pixi run okf",
        "copilot-setup-steps.yml",
    ):
        assert needle in section, needle
