#!/usr/bin/env python3
"""Sync the git-tracked filter-inventory skill into Claude Code's skill directory.

Why this exists
---------------
`.claude/` and `.agents/` are both gitignored (.gitignore:76-77), so nothing in
them reaches colleagues. The canonical, reviewable, git-tracked copy of this
skill is:

    audit/skills/filter_inventory/SKILL.md

But Claude Code only discovers skills under `.claude/skills/<name>/SKILL.md`.
That directory cannot be committed, so it has to be generated from the tracked
copy -- and regenerated whenever a colleague edits the tracked copy and you
pull their change.

This script is that bridge. It is stdlib-only so any Python can run it.

Usage
-----
    python audit/skills/filter_inventory/scripts/sync_skill.py --check
    python audit/skills/filter_inventory/scripts/sync_skill.py --apply

--check  Report whether the local Claude Code copy matches the tracked source.
         Exit 0 = in sync. Exit 1 = drift or missing. Read-only.
--apply  (Re)generate the local copy from the tracked source.

Drift is reported in both directions:
  * upstream  - the tracked SKILL.md changed (usually a colleague's commit).
                Your local copy is stale; --apply to pick it up.
  * local     - someone edited .claude/skills/... directly. That edit is not
                tracked and will be lost on --apply. Port it to the canonical
                file first.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent      # audit/skills/filter_inventory
REPO_ROOT = SKILL_DIR.parent.parent.parent              # repo root
SOURCE = SKILL_DIR / "SKILL.md"

TARGET_DIR = REPO_ROOT / ".claude" / "skills" / "filter-inventory"
TARGET = TARGET_DIR / "SKILL.md"
STATE = TARGET_DIR / "SYNC.json"

SOURCE_REL = SOURCE.relative_to(REPO_ROOT).as_posix()
SCRIPT_REL = Path(__file__).resolve().relative_to(REPO_ROOT).as_posix()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_commit_for(path: Path) -> str:
    """Last commit touching the canonical file, for legible drift reporting."""
    try:
        out = subprocess.run(
            ["git", "log", "-1", "--format=%h %ad %an", "--date=short", "--", str(path)],
            cwd=REPO_ROOT, capture_output=True, text=True, timeout=10,
        )
        return out.stdout.strip() or "(uncommitted)"
    except Exception:
        return "(git unavailable)"


# NOTE: the banner must go AFTER the YAML frontmatter, never before it.
# Frontmatter has to start at byte 0 or the skill loader does not see it and
# the skill silently fails to register. (Verified: a leading HTML comment makes
# skill-creator's quick_validate.py report "No YAML frontmatter found".)
BANNER = f"""
<!--
  GENERATED FILE - DO NOT EDIT HERE.

  Canonical source (git-tracked, shared with colleagues):
      {SOURCE_REL}

  `.claude/` is gitignored, so edits made here are invisible to everyone else
  and will be overwritten. Edit the canonical file, commit it, then run:
      python {SCRIPT_REL} --apply
-->
"""

SYNC_CHECK_BLOCK = f"""
## Before you start: confirm this skill is current

This file is a generated copy. The shared, git-tracked original lives at
`{SOURCE_REL}` and colleagues edit *that* one. If someone improved the audit
method and you pull their commit, this copy goes stale without any visible
signal.

So before following the workflow below, run:

```bash
python {SCRIPT_REL} --check
```

If it reports upstream drift, run `--apply`, then re-read this file — you were
about to follow superseded instructions. If it reports *local* drift, someone
edited this generated copy directly; tell the user before overwriting, because
that edit exists nowhere else and is not in git.

If the script is missing entirely, you are outside the repo or the checkout is
incomplete. Say so rather than proceeding on possibly-stale guidance.

---
"""


def build_target_text() -> str:
    """Canonical body with the banner and the self-check block spliced in.

    The check block goes after the frontmatter and title so the YAML stays
    valid and the description (which drives triggering) is untouched.
    """
    text = SOURCE.read_text(encoding="utf-8")

    if not text.startswith("---"):
        sys.exit(f"ERROR: {SOURCE_REL} has no YAML frontmatter")
    end = text.index("---", 3) + 3
    frontmatter, body = text[:end], text[end:]

    # Insert the check block after the first markdown H1, if present.
    lines = body.split("\n")
    insert_at = next((i + 1 for i, l in enumerate(lines) if l.startswith("# ")), 0)
    body = "\n".join(lines[:insert_at]) + "\n" + SYNC_CHECK_BLOCK + "\n".join(lines[insert_at:])

    return frontmatter + BANNER + body


def check(verbose: bool = True) -> int:
    if not SOURCE.exists():
        print(f"ERROR: canonical source missing: {SOURCE_REL}")
        return 1

    src_hash = sha(SOURCE)

    if not TARGET.exists() or not STATE.exists():
        if verbose:
            print("NOT INSTALLED - Claude Code copy does not exist yet.")
            print(f"  source:  {SOURCE_REL}  [{git_commit_for(SOURCE)}]")
            print(f"  target:  {TARGET.relative_to(REPO_ROOT).as_posix()}")
            print(f"\n  Run: python {SCRIPT_REL} --apply")
        return 1

    state = json.loads(STATE.read_text(encoding="utf-8"))
    upstream = state.get("source_sha256") != src_hash
    local = state.get("generated_sha256") != sha(TARGET)

    if not upstream and not local:
        if verbose:
            print("IN SYNC")
            print(f"  source: {SOURCE_REL}  [{git_commit_for(SOURCE)}]")
            print(f"  synced: {state.get('synced_from_commit', 'unknown')}")
        return 0

    if verbose:
        if upstream:
            print("UPSTREAM DRIFT - the tracked skill changed; your copy is stale.")
            print(f"  synced from: {state.get('synced_from_commit', 'unknown')}")
            print(f"  now at:      {git_commit_for(SOURCE)}")
        if local:
            print("LOCAL DRIFT - .claude copy was edited directly.")
            print("  That edit is gitignored and invisible to colleagues.")
            print(f"  Port it into {SOURCE_REL} before running --apply, or it is lost.")
        print(f"\n  Run: python {SCRIPT_REL} --apply")
    return 1


def apply() -> int:
    if not SOURCE.exists():
        sys.exit(f"ERROR: canonical source missing: {SOURCE_REL}")

    had_local_drift = False
    if TARGET.exists() and STATE.exists():
        state = json.loads(STATE.read_text(encoding="utf-8"))
        had_local_drift = state.get("generated_sha256") != sha(TARGET)

    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    text = build_target_text()
    TARGET.write_text(text, encoding="utf-8", newline="\n")

    STATE.write_text(json.dumps({
        "_comment": "Written by sync_skill.py. Do not hand-edit.",
        "source_path": SOURCE_REL,
        "source_sha256": sha(SOURCE),
        "generated_sha256": sha(TARGET),
        "synced_from_commit": git_commit_for(SOURCE),
    }, indent=2) + "\n", encoding="utf-8", newline="\n")

    print(f"SYNCED  {SOURCE_REL}")
    print(f"     -> {TARGET.relative_to(REPO_ROOT).as_posix()}")
    print(f"        [{git_commit_for(SOURCE)}]")
    if had_local_drift:
        print("\n  NOTE: a direct edit to the generated copy was overwritten.")
        print("        If it was intentional, it is gone - redo it in the canonical file.")
    return 0


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--check", action="store_true", help="report sync state; read-only")
    g.add_argument("--apply", action="store_true", help="regenerate the Claude Code copy")
    a = p.parse_args()
    sys.exit(check() if a.check else apply())
