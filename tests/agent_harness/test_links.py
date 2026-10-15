"""Relative links in the agent harness point at files that exist."""

from __future__ import annotations

import re
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
SKIPPED_PREFIXES = ("http://", "https://", "mailto:", "#")


def _strip_code(text: str) -> str:
    """Blank out fenced blocks and inline code, keeping line numbers intact."""
    lines, in_fence = [], False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            lines.append("")
        elif in_fence:
            lines.append("")
        else:
            lines.append(INLINE_CODE_RE.sub(lambda m: " " * len(m.group(0)), line))
    return "\n".join(lines)


def broken_links(path: Path, root: Path) -> list[str]:
    """Return ``file:line -> target`` for each relative link that resolves nowhere."""
    text = _strip_code(path.read_text(encoding="utf-8"))
    broken = []
    for match in LINK_RE.finditer(text):
        target = match.group(1)
        if target.startswith(SKIPPED_PREFIXES):
            continue
        resolved = path.parent / target.split("#", 1)[0]
        if not (resolved.exists() or resolved.is_symlink()):
            line = text.count("\n", 0, match.start()) + 1
            broken.append(f"{path.relative_to(root)}:{line} -> {target}")
    return broken


def test_broken_links_ignores_code_and_urls(tmp_path):
    (tmp_path / "real.md").write_text("x\n", encoding="utf-8")
    doc = tmp_path / "doc.md"
    doc.write_text(
        "[ok](real.md) [gone](missing.md) `[code](ignored.md)`\n"
        "```\n[fenced](also-ignored.md)\n```\n"
        "[web](https://example.com) [anchor](#top) [multi\nline](real.md#part)\n",
        encoding="utf-8",
    )
    assert broken_links(doc, tmp_path) == ["doc.md:1 -> missing.md"]


def test_harness_links_resolve(harness_markdown_files, repo_root):
    broken = [
        item for path in harness_markdown_files for item in broken_links(path, repo_root)
    ]
    assert not broken, "broken relative links:\n" + "\n".join(broken)
