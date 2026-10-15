"""AGENTS.md is a short entry point, and every AGENTS.md reaches Claude Code."""

from __future__ import annotations

import re

MAX_ENTRY_POINT_LINES = 130

# Every task the pre-harness root AGENTS.md (commit c5a592e) told agents to run.
TASKS_FROM_OLD_AGENTS_MD = (
    "compile-mv-fixes", "list-flows", "migrate", "migrate-autogenerate",
    "pre-commit-all", "rebuild-services", "refresh-views", "run-single-flow",
    "schema-analytics-list", "schema-analytics-plan", "schema-dump",
    "schema-plan", "service-logs", "service-status", "skills-sync",
    "start-services", "start-webservice", "test", "update-static-resource-info",
)

# Facts from its setup, schema, and pitfalls sections that must survive the move.
FACTS_FROM_OLD_AGENTS_MD = (
    "PROJ_LIB",
    "credentials.json",
    "at the module level",
    "use the `db` hostname",
    "pixi-kernel",
    "Nine materialized views",
)


def _entry_point(repo_root) -> str:
    return (repo_root / "AGENTS.md").read_text(encoding="utf-8")


def _section(text: str, heading: str) -> str:
    assert heading in text, f"AGENTS.md is missing {heading!r}"
    return text.split(heading, 1)[1].split("\n## ", 1)[0]


def test_every_agents_md_has_a_claude_md_import(agents_md_files):
    assert len(agents_md_files) >= 7, "expected the root and six package AGENTS.md files"
    bad = [
        str(path.with_name("CLAUDE.md"))
        for path in agents_md_files
        if path.with_name("CLAUDE.md").is_symlink()
        or not path.with_name("CLAUDE.md").is_file()
        or path.with_name("CLAUDE.md").read_text(encoding="utf-8") != "@AGENTS.md\n"
    ]
    assert not bad, "each needs exactly '@AGENTS.md' (no symlink): " + ", ".join(bad)


def test_entry_point_is_short(repo_root):
    count = len(_entry_point(repo_root).splitlines())
    assert count <= MAX_ENTRY_POINT_LINES, (
        f"AGENTS.md has {count} lines; move detail into .agents/rules/"
    )


def test_entry_point_sections(repo_root):
    text = _entry_point(repo_root)
    for heading in (
        "## Non-negotiables", "## Rule Index", "## Package Guides",
        "## Provenance", "## Trust These Instructions",
    ):
        assert heading in text, heading


def test_rule_index_lists_exactly_the_rule_files(repo_root, rule_files):
    index = _section(_entry_point(repo_root), "## Rule Index")
    indexed = set(re.findall(r"\]\(\.agents/rules/([a-z0-9-]+\.md)\)", index))
    assert indexed == {path.name for path in rule_files}


def test_package_guides_list_every_nested_agents_md(repo_root, agents_md_files):
    guides = _section(_entry_point(repo_root), "## Package Guides")
    linked = set(re.findall(r"\]\(([\w./-]+/AGENTS\.md)\)", guides))
    nested = {path.relative_to(repo_root).as_posix() for path in agents_md_files}
    assert linked == nested - {"AGENTS.md"}


def test_old_agents_md_content_survives(repo_root, rule_files):
    corpus = " ".join(
        " ".join(path.read_text(encoding="utf-8").split())
        for path in [repo_root / "AGENTS.md", *rule_files]
    )
    missing = [
        f"pixi run {task}"
        for task in TASKS_FROM_OLD_AGENTS_MD
        if not re.search(rf"pixi run {re.escape(task)}(?![\w-])", corpus)
    ]
    missing += [fact for fact in FACTS_FROM_OLD_AGENTS_MD if fact not in corpus]
    assert not missing, f"dropped from the harness: {missing}"
