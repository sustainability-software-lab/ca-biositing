"""The AI policy is defined once and reachable from GitHub and the docs site."""

from __future__ import annotations

import os


def test_ai_policy_defines_the_assisted_by_trailer(repo_root):
    text = " ".join((repo_root / "AI_POLICY.md").read_text(encoding="utf-8").split())
    assert "Assisted-by: <harness>:<model>" in text
    assert "AI can _never_ sign off on a commit" in text


def test_pr_template_asks_for_disclosure_and_verification(repo_root):
    text = (repo_root / ".github" / "pull_request_template.md").read_text(encoding="utf-8")
    assert "## 🤖 AI assistance disclosure" in text
    assert "## 🔍 Author verification" in text
    assert "`<harness>:<model>`" in text


def test_ai_policy_link_resolves_on_github_and_docs_site(repo_root):
    for name in ("README.md", "CONTRIBUTING.md"):
        assert "](AI_POLICY.md)" in (repo_root / name).read_text(encoding="utf-8"), name
    link = repo_root / "docs" / "AI_POLICY.md"
    assert link.is_symlink() and os.readlink(link) == "../AI_POLICY.md"
    assert link.is_file(), "docs/AI_POLICY.md must resolve"
    nav = (repo_root / "mkdocs.yml").read_text(encoding="utf-8")
    assert "  - AI Policy: AI_POLICY.md\n" in nav
