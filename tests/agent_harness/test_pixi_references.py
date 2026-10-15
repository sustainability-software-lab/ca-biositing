"""Every `pixi run <name>` in the harness names a real task or command."""

from __future__ import annotations

import re

# Commands the docs run through `pixi run` that are executables, not tasks.
COMMANDS_RUN_DIRECTLY = {"pre-commit", "pytest", "python", "which"}

PIXI_RUN_RE = re.compile(
    r"pixi run(?:\s+(?:-e|--environment)\s+\S+)?\s+([A-Za-z0-9_][A-Za-z0-9_.-]*)"
)


def test_pattern_skips_the_environment_flag():
    match = PIXI_RUN_RE.search("run `pixi run -e docs docs-build` first")
    assert match is not None and match.group(1) == "docs-build"
    assert PIXI_RUN_RE.search("pixi run <task>") is None


def test_pixi_run_references_name_real_tasks(harness_markdown_files, pixi_tasks, repo_root):
    unknown = sorted(
        {
            f"{path.relative_to(repo_root)}: pixi run {match.group(1)}"
            for path in harness_markdown_files
            for match in PIXI_RUN_RE.finditer(path.read_text(encoding="utf-8"))
            if match.group(1) not in pixi_tasks | COMMANDS_RUN_DIRECTLY
        }
    )
    assert not unknown, "no such Pixi task:\n" + "\n".join(unknown)
