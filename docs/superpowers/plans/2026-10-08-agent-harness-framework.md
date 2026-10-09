# Agent Harness Framework Integration Implementation Plan

<!-- Steps copy and match the code blocks below byte for byte, so keep prettier from reformatting them. -->
<!-- prettier-ignore-start -->

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the UW SSEC project template's agent-harness framework — a short `AGENTS.md` entry point, on-demand rules in `.agents/rules/`, portable project skills in `.agents/skills/` exposed to Claude Code through `.claude/skills`, an AI-attribution policy, OKF project memory, and agent-ready dev environments — into ca-biositing, adapted to this repository and without changing `pixi.lock`.

**Architecture:** The existing `agent_docs/` guides move into `.agents/rules/` beside the template's behavioral rules, and the 272-line root `AGENTS.md` shrinks to an entry point with a rule index. Every `AGENTS.md` (root and six nested) gets a `CLAUDE.md` that imports it. Project skills are committed under `.agents/skills/` through a `.gitignore` allowlist, while third-party skills from `pixi run skills-sync` stay ignored. A pytest suite in `tests/agent_harness/`, run in CI, pins every invariant.

**Tech Stack:** Markdown (prettier `--prose-wrap=always`), pytest + PyYAML + `tomllib` + git (repository-invariant tests), Pixi tasks and `pixi exec`, the `okf` CLI (`okf-agent-memory` 0.5.x), GitHub Actions, Dev Containers.

**Spec:** No separate design doc. The spec is upstream [`uw-ssec/project-template`](https://github.com/uw-ssec/project-template) at commit `fc00b39` (PRs #28–#32 and #34–#39), adapted per the **Decisions** section below. That section records every deviation from upstream and the evidence behind it, and it is the spec of record for reviewers.

## Global Constraints

- Upstream source: `uw-ssec/project-template` at `fc00b39`. "Copy from upstream" means `git -C "$UPSTREAM" show fc00b39:<path>`. A ported file may differ from upstream only by the edits listed in its task, plus prettier reflow.
- Base commit for extraction: `c5a592e`. Every `sed -n` line range in this plan reads `git show c5a592e:<file>`, never the working tree.
- Pixi is the only package manager. Run `pixi install` before other Pixi commands. Never call `pip`, `conda`, or `venv`.
- `pixi.lock` must stay byte-identical to `main`: never run `pixi add`, `pixi remove`, `pixi update`, or `pixi lock` in this branch. Run `export PIXI_FROZEN=true` in every shell you use, so `pixi install` and `pixi run` use the lock as-is and never re-solve it. After every task, `git diff --exit-code origin/main -- pixi.lock` must exit 0.
- `pixi.toml` channels stay `["conda-forge"]`. The only `pixi.toml` change in this plan is one new task (Task 6).
- Every file in `.agents/rules/`: line 1 `# Title`, line 2 blank, line 3 starts with `**Load when:**`. Names are kebab-case.
- Skill frontmatter holds only `name` and `description`. `name` equals the directory name, matches `^[a-z0-9]+(-[a-z0-9]+)*$`, and is at most 64 characters. `description` is 1–1024 characters and starts with `Use ` (Agent Skills spec, <https://agentskills.io/specification>).
- From Task 3 on, every `AGENTS.md` has a sibling `CLAUDE.md` whose entire content is `@AGENTS.md` plus a trailing newline.
- **The gate** that ends every task: stage the task's files, format only those with `pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true`, stage the fixes with `git add -u`, then run `pixi run pre-commit-all`. It must pass without modifying anything. `pre-commit-all` checks only tracked files, so stage new files first. If it modifies a file this plan never touched, the base was not clean: `git restore` that file and mention it to your human partner instead of committing it.
- Do not touch package code under `src/` (only `AGENTS.md`/`CLAUDE.md` files there), the `frontend` submodule, or `skills.py`.
- Commits follow Conventional Commits. AI-assisted commits end with an `Assisted-by: <harness>:<model>` trailer, never an AI `Co-authored-by:` and never an agent `Signed-off-by:` (the policy Task 4 introduces). The examples use `Assisted-by: claude-code:claude-opus-5-5`; substitute your own harness and model. If your harness is configured to add a different attribution line, ask your human partner which to use before the first commit.

## Review Focus

Five conditions the spec implies that the per-task feature tests would not otherwise exercise, most likely first. Each one has a dedicated test in its owning task.

1. **A newer pixi rewrites `pixi.lock` as format v7.** Pixi ≥0.68.0 writes v7 on any re-solve (this plan was written on pixi 0.81.0), and every pin in CI, Docker, the devcontainer, and Copilot is older and cannot read it. Expected: CI's harness step fails, names each pin that cannot read the lock, and says how to recover. Owner: Task 6, `test_every_pinned_pixi_can_read_pixi_lock`.
2. **A new project skill is created under `.agents/skills/` but not allowlisted in `.gitignore`.** Git silently ignores it and teammates never get it; this already happened to the two local skills declared in #442. Expected: a test names the missing `!.agents/skills/<name>/` line. Owner: Task 5, `test_project_skills_are_committable` and `test_declared_local_skills_on_disk_are_not_ignored`.
3. **`pixi run skills-sync` installs a registry skill with a project skill's name.** The `skills` CLI deletes `.agents/skills/<name>/` and copies the registry skill in its place, and `vercel-labs/agent-skills` installs everything it publishes. Expected: a test fails when `skills-lock.json` names a project skill. Owner: Task 5, `test_no_registry_skill_shadows_a_project_skill`.
4. **An `AGENTS.md` without a sibling `CLAUDE.md`** (a future package guide, or a deleted shim). Once a root `CLAUDE.md` exists, Claude Code ≥2.1.277 stops reading `AGENTS.md` files natively, so that guide silently disappears. Expected: a test names the missing shim. Owner: Task 3, `test_every_agents_md_has_a_claude_md_import`.
5. **`merge-pr` run from a linked worktree**, which is how this team works. Upstream's `git checkout main` fails there, and upstream's bare `git stash pop` can grab another session's stash. Expected: the skill detects the worktree and uses a named stash restored by SHA. Owner: Task 5, `test_merge_pr_is_safe_in_linked_worktrees`.

## Decisions (spec of record)

- **D1 Scope.** Port the template's harness: AGENTS.md progressive disclosure and rules (#29), skills plus the `.claude/skills` symlink (#30), the optional mkdocs+OKF rule (#31), devcontainer agent CLIs and Copilot setup (#32), the AI policy and `Assisted-by` trailer (#35), the PR template's AI disclosure (#28), OKF memory (#34–#38), and the README AI section (#39).
- **D2 Rules location.** `agent_docs/*.md` moves with `git mv` to `.agents/rules/` under kebab-case names and gains `**Load when:**` lines. `agent_docs/README.md` is deleted; the AGENTS.md Rule Index replaces it. The local `code_quality.md` and `troubleshooting.md` are supersets of the template's `pre-commit-and-quality.md` and `troubleshooting.md`, so those two template rules are merged in rather than copied.
- **D3 One `CLAUDE.md` per `AGENTS.md`.** Claude Code ≥2.1.277 reads `AGENTS.md` natively only when no `CLAUDE.md` exists at or above the working directory; a subdirectory `AGENTS.md` loads on Read only in that mode. The template's root `CLAUDE.md` would therefore switch off the six nested guides, so each gets its own `@AGENTS.md` import, whose CLAUDE.md trigger (Read/Write/Edit) is also broader. Source: <https://code.claude.com/docs/en/memory#agents-md>.
- **D4 Skills layout.** `.claude/skills -> ../.agents/skills`, committed as in the template; the Claude Code changelog fixed a bug for exactly this setup. Verified against `skills` CLI 1.7.1 source: its `createSymlink` compares real paths, so `skills-sync` leaves this symlink alone, but `cleanAndCreateDirectory` does `rm -rf .agents/skills/<name>` before copying, hence Review Focus #3. `.gitignore` changes from ignoring `.agents/` and `.claude/` wholesale to an allowlist, checked with `git check-ignore` in a scratch repository.
- **D5 AI policy.** Adopt `AI_POLICY.md` verbatim. **This changes team practice:** recent commits credit AI with `Co-authored-by: Claude …`, which the policy replaces with `Assisted-by:`. Task 4 is a separate PR so the team can review the policy on its own; Task 5's `commit` and `create-pr` skills depend on it.
- **D6 No dependency changes.** CI, the deploy workflows, and both Docker images pin pixi 0.63.2, which cannot read lock format v7 ([pixi 0.68.0 release](https://github.com/prefix-dev/pixi/releases/tag/v0.68.0)). On a v7 lock it re-solves, or fails under `--locked` ([prefix-dev/pixi#4897](https://github.com/prefix-dev/pixi/pull/4897)). Re-locking with pixi 0.81 to add `gh` + `okf-agent-memory` changed no package versions, but rewrote 40,159/40,041 lines into v7. Re-locking with pixi 0.63.2 failed twice while fetching the conda→PyPI mapping. So `okf` ships as a Pixi **task** that runs the CLI through `pixi exec`; a test project showed that pixi 0.81 leaves a v6 lock untouched when a task is added and run. `gh` is a documented prerequisite. Moving both into Pixi features waits for a separate pixi-upgrade PR.
- **D7 Pixi pins.** The devcontainer (0.55.0) and Copilot setup (0.56.0) move to the CI pin, 0.63.2, with checksum-verified installs. Anything newer would let an agent there write a v7 lock.
- **D8 Sixth non-negotiable.** The old root AGENTS.md marks schema management CRITICAL, so the entry point adds "change the schema only through SQLModel and Alembic" to the template's five.
- **D9 Tests.** Repository-invariant tests in `tests/agent_harness/` use only stdlib, PyYAML, and git. Task 1 adds a step to `.github/workflows/ci.yml` because CI otherwise runs only package tests under `src/`.
- **D10 Adapted skills.** `merge-pr` handles linked worktrees and shared stashes. `docs` uses this repo's `docs/` layout and `pixi run -e docs docs-build`. `okf-memory` describes the `okf` task. `commit`, `push`, `create-pr`, `create-issue`, and `clean-branches` are verbatim.

## Not Ported, and Why

- `release` skill: semver plus `plugins/` zip assets; this repo uses CalVer, has no `plugins/`, and its `CHANGELOG.md` has no released sections.
- `onboard` environment, `ssec-cli`, `onboarded.md`, onboard issue template: SSEC onboarding, not harness. Open upstream PR #41 is not on `main`.
- `zizmor.yml` (#25) and `detect-secrets` + `.secrets.baseline` (#33): CI/security hardening that predates or sits beside the harness. Each deserves its own PR, and detect-secrets needs an audit of the dev credentials already in `pixi.toml` and `.env.example`.
- The `https://prefix.dev/conda-forge` channel switch (#34/#37): it re-solves the whole lock file.
- `gh-cli` and `okf` Pixi features: deferred by D6.

## Noticed, Not Fixed (mention to your human partner, don't fix here)

- README links `datamodels/CONTRIBUTING.md`, `pipeline/CONTRIBUTING.md`, and `webservice/CONTRIBUTING.md` don't resolve on GitHub; they exist only under `docs/`.
- `agent_docs/code_quality.md` says formatting is handled by "prettier, autopep8, ruff" hooks, but `.pre-commit-config.yaml` has no autopep8 or ruff hook.
- `skills.json` declares local skills `database-query` and `data-visualization` (#442) that were never committed, because `.agents/` was ignored. They exist only on their author's machine.
- `skills-lock.json` lists `documentation-writer` (github/awesome-copilot), which `skills.json` does not request.
- In a re-solve test, pixi 0.63.2 (the CI pin) failed twice to fetch the conda→PyPI mapping, while 0.81.0 succeeded on the same machine. Until the pins are upgraded, any dependency change is blocked.

## File Map

| Path | Task | Responsibility |
| --- | --- | --- |
| `tests/agent_harness/{__init__,conftest}.py` | 1 (+2, 5) | Shared fixtures: repo files, rules, harness markdown, git-ignore probe, pixi manifest |
| `tests/agent_harness/test_rules.py`, `test_links.py` | 1 (+2) | Rule shape and names; relative links resolve |
| `.agents/rules/{code-quality,docker-workflow,namespace-packages,testing-patterns,troubleshooting}.md` | 1 (+2) | Former `agent_docs/` guides |
| `.github/workflows/ci.yml` | 1 | Runs the harness tests in CI |
| `.agents/rules/{working-agreement,contribution-discipline,pixi-environments,repository-map,onboarding,schema-and-migrations}.md` | 2 | Template behavior rules and the content leaving the root AGENTS.md |
| `tests/agent_harness/test_pixi_references.py` | 2 | Every `pixi run X` names a real task |
| `AGENTS.md`, `CLAUDE.md` ×7 | 3 | Entry point; Claude Code imports |
| `tests/agent_harness/test_entrypoint.py` | 3 | Shims, index ↔ rules, nothing lost |
| `AI_POLICY.md`, `docs/AI_POLICY.md`, `.github/pull_request_template.md`, `mkdocs.yml`, `CONTRIBUTING.md`, `README.md` | 4 | AI attribution policy |
| `tests/agent_harness/test_ai_policy.py` | 4 | Policy, PR template, docs-site link |
| `.agents/skills/{clean-branches,commit,create-issue,create-pr,docs,merge-pr,push}/SKILL.md`, `.claude/skills`, `.gitignore`, `skills.json`, `.agents/rules/agent-skills.md` | 5 | Project skills |
| `tests/agent_harness/test_skills.py` | 5 | Spec frontmatter, symlink, ignore rules, collisions, worktree safety |
| `pixi.toml` (`okf` task), `knowledge/`, `.agents/skills/okf-memory/`, `.agents/rules/mkdocs-okf-knowledge-bundle.md`, `.pre-commit-config.yaml` | 6 | OKF project memory |
| `tests/agent_harness/test_okf.py`, `test_lockfile.py` | 6 (+7) | okf wiring; lock readable by every pixi pin |
| `.devcontainer/{Dockerfile,devcontainer.json,install-agents.sh}`, `.github/workflows/copilot-setup-steps.yml` | 7 | Agent-ready environments |
| `tests/agent_harness/test_agent_environments.py` | 7 | SHA-pinned actions, locked install, executable script |
| `README.md` (AI Agents section), `tests/agent_harness/test_readme.py` | 8 | Human-facing summary; final verification |

## Before You Start

- [ ] **Step 1: Confirm the base is unchanged where this plan quotes it**

```bash
git fetch origin
git diff --stat c5a592e origin/main -- AGENTS.md agent_docs resources/AGENTS.md alembic/AGENTS.md audit/AGENTS.md 'src/ca_biositing/*/AGENTS.md' .gitignore skills.json skills-lock.json pixi.toml .pre-commit-config.yaml .github/pull_request_template.md .github/workflows/ci.yml .github/workflows/copilot-setup-steps.yml .devcontainer README.md CONTRIBUTING.md mkdocs.yml docs/pipeline/USDA/ANALYTICS_HANDOFF.md
```

Expected: no output. If a file changed after `c5a592e`, re-check every line number and old/new string this plan quotes for that file before editing it.

- [ ] **Step 2: Work on a branch from current `main`** (use superpowers:using-git-worktrees if you want isolation), then install the environment:

```bash
pixi --version          # record it: at 0.68.0 or later, any re-solve would rewrite pixi.lock as v7
export PIXI_FROZEN=true # repeat in every new shell
pixi install
git diff --exit-code -- pixi.lock && head -1 pixi.lock
```

Expected: no diff, then `version: 6`.

- [ ] **Step 3: Fetch the upstream template.** Use this same path in every later step that reads upstream.

```bash
UPSTREAM="${TMPDIR:-/tmp}/ssec-project-template"
[ -d "$UPSTREAM" ] || git clone --quiet https://github.com/uw-ssec/project-template.git "$UPSTREAM"
git -C "$UPSTREAM" log -1 --format='%h %s' fc00b39
```

Expected: `fc00b39 docs(readme): document the okf feature and the AI agent setup (#39)`

## Suggested PR Split

One problem per PR, per the contribution rules being introduced:

1. **PR A** — Tasks 1–3: `docs(agents): adopt the SSEC progressive-disclosure agent harness`
2. **PR B** — Tasks 4–5: `docs(agents): add the AI policy and portable project skills` (team review of D5)
3. **PR C** — Task 6: `feat(memory): add OKF project memory` (on merge, the `pixi.toml` edit triggers `docker-build.yml`, then a staging deploy and a production Pulumi *preview*, like any `src/` merge; coordinate with whoever watches staging)
4. **PR D** — Tasks 7–8: `build(agents): agent-ready devcontainer and Copilot setup`

---

### Task 1: Move `agent_docs/` into `.agents/rules/` and add the harness test suite

**Files:**
- Create: `tests/agent_harness/__init__.py` (empty), `tests/agent_harness/conftest.py`, `tests/agent_harness/test_rules.py`, `tests/agent_harness/test_links.py`
- Move: `agent_docs/{code_quality,docker_workflow,namespace_packages,testing_patterns,troubleshooting}.md` → `.agents/rules/{code-quality,docker-workflow,namespace-packages,testing-patterns,troubleshooting}.md`
- Delete: `agent_docs/README.md`
- Modify: `.gitignore:75-79` (the "Agents Braindump" block)
- Modify: `AGENTS.md:37-45`, `resources/AGENTS.md:28-29,421`, `src/ca_biositing/datamodels/AGENTS.md:30-33`, `src/ca_biositing/webservice/AGENTS.md:29-32`, `src/ca_biositing/pipeline/AGENTS.md:27`, `docs/pipeline/USDA/ANALYTICS_HANDOFF.md:9-14`
- Modify: `.github/workflows/ci.yml` (new step after "Print pixi version")

**Interfaces:**
- Consumes: nothing.
- Produces: in `tests/agent_harness/conftest.py`, fixtures `repo_root() -> Path`, `agents_md_files() -> list[Path]`, `rule_files() -> list[Path]`, `harness_markdown_files() -> list[Path]` (every `AGENTS.md`, every `CLAUDE.md`, `.agents/rules/*.md`, non-ignored `.agents/skills/*/SKILL.md`, and `AI_POLICY.md`), and `is_git_ignored() -> Callable[[Path | str], bool]`; plus module helpers `_git(*args: str) -> subprocess.CompletedProcess[str]` and `repo_files(*pathspecs: str) -> list[Path]`, which later tasks extend inside `conftest.py`. Also the constant `MOVED_FROM_AGENT_DOCS: set[str]` in `test_rules.py`, and the CI step named "Check agent harness invariants".

- [ ] **Step 1: Write the fixtures**

Create `tests/agent_harness/__init__.py` as an empty file, then create `tests/agent_harness/conftest.py`:

```python
"""Shared fixtures for the agent-harness invariant tests.

These tests check repository structure (instruction files, rules, skills,
ignore rules, and tool pins), not package code, so they need no database,
Docker services, or network access.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

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
```

- [ ] **Step 2: Write the failing rule and link tests**

Create `tests/agent_harness/test_rules.py`:

```python
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
```

Create `tests/agent_harness/test_links.py`:

```python
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
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run pytest tests/agent_harness -v`
Expected: FAIL `test_agent_docs_directory_is_retired`, `test_moved_rules_are_present_and_committable`, and `test_every_rule_opens_with_title_and_load_when` (the last with "no rule files found"). The two link tests PASS.

- [ ] **Step 4: Let git track `.agents/rules/`**

In `.gitignore`, replace these lines:

```gitignore
# Agents Braindump
.agents/
.claude/
.cline/
.roo/
```

with:

```gitignore
# Agents Braindump
# .agents/ and .claude/ hold machine-local agent state and the third-party
# skills that `pixi run skills-sync` installs. Only the committed harness is
# tracked: .agents/rules/ (see AGENTS.md).
.agents/*
!.agents/rules/
.claude/
.cline/
.roo/
```

- [ ] **Step 5: Move the guides and retire `agent_docs/`**

```bash
mkdir -p .agents/rules
git mv agent_docs/code_quality.md .agents/rules/code-quality.md
git mv agent_docs/docker_workflow.md .agents/rules/docker-workflow.md
git mv agent_docs/namespace_packages.md .agents/rules/namespace-packages.md
git mv agent_docs/testing_patterns.md .agents/rules/testing-patterns.md
git mv agent_docs/troubleshooting.md .agents/rules/troubleshooting.md
git rm agent_docs/README.md
```

- [ ] **Step 6: Add a `Load when` line under each moved file's title**

```bash
add_trigger() {  # $1 = file, $2 = trigger text inserted after the H1 and its blank line
  TRIGGER="$2" perl -0pi -e 's/\A(# [^\n]*\n\n)/$1**Load when:** $ENV{TRIGGER}\n\n/' "$1"
}
add_trigger .agents/rules/code-quality.md 'writing or reviewing Python code (style, type hints, docstrings, imports), committing, preparing a PR, or claiming that checks pass.'
add_trigger .agents/rules/docker-workflow.md 'starting, stopping, rebuilding, or inspecting the Docker services (PostgreSQL, Prefect server and worker), or deploying and running ETL flows.'
add_trigger .agents/rules/namespace-packages.md 'adding a module or package under `src/ca_biositing/`, fixing an import error, or changing package structure or a `pyproject.toml`.'
add_trigger .agents/rules/testing-patterns.md 'writing, fixing, or running tests: pytest fixtures, Prefect task tests, and FastAPI TestClient tests.'
add_trigger .agents/rules/troubleshooting.md 'a documented command fails or behaves unexpectedly: environment, namespace import, Docker, database, Prefect, or Google credential problems.'
head -3 .agents/rules/*.md
```

Expected: each file prints `# <title>`, a blank line, and a `**Load when:** …` line.

- [ ] **Step 7: Re-point links inside the moved files**

These relative links break when the files move one level deeper and get kebab-case names:

```bash
perl -pi -e 's#\]\(\.\./resources/AGENTS\.md\)#](../../resources/AGENTS.md)#' .agents/rules/docker-workflow.md
perl -pi -e 's#\[namespace_packages\.md\]\(namespace_packages\.md\)#[namespace-packages.md](namespace-packages.md)#; s#\[testing_patterns\.md\]\(testing_patterns\.md\)#[testing-patterns.md](testing-patterns.md)#; s#\]\(\.\./AGENTS\.md\)#](../../AGENTS.md)#' .agents/rules/troubleshooting.md
```

- [ ] **Step 8: Re-point every reference to `agent_docs/`**

```bash
perl -pi -e '
  s#agent_docs/namespace_packages\.md#.agents/rules/namespace-packages.md#g;
  s#agent_docs/testing_patterns\.md#.agents/rules/testing-patterns.md#g;
  s#agent_docs/code_quality\.md#.agents/rules/code-quality.md#g;
  s#agent_docs/troubleshooting\.md#.agents/rules/troubleshooting.md#g;
  s#agent_docs/docker_workflow\.md#.agents/rules/docker-workflow.md#g;
  s#\[namespace_packages\.md\]#[namespace-packages.md]#g;
  s#\[testing_patterns\.md\]#[testing-patterns.md]#g;
  s#\[code_quality\.md\]#[code-quality.md]#g;
  s#\[docker_workflow\.md\]#[docker-workflow.md]#g;
  s#agent_docs/#.agents/rules/#g;
' AGENTS.md resources/AGENTS.md src/ca_biositing/datamodels/AGENTS.md src/ca_biositing/webservice/AGENTS.md docs/pipeline/USDA/ANALYTICS_HANDOFF.md
# ANALYTICS_HANDOFF.md lives three levels down; its links were already broken relative paths.
perl -pi -e 's#\]\(\.agents/rules/#](../../../.agents/rules/#g; s#\]\(AGENTS\.md\)#](../../../AGENTS.md)#g' docs/pipeline/USDA/ANALYTICS_HANDOFF.md
git add -A .agents/rules
git grep -n -E "agent_docs|code_quality\.md|docker_workflow\.md|namespace_packages\.md|testing_patterns\.md" || echo "no stale references"
for t in AGENTS.md .agents/rules/namespace-packages.md .agents/rules/docker-workflow.md .agents/rules/troubleshooting.md; do ls "docs/pipeline/USDA/../../../$t" >/dev/null && echo "ok $t"; done
```

Expected: `no stale references`, then four `ok` lines.

- [ ] **Step 9: Restore the pipeline guide's missing cross-cutting table**

`src/ca_biositing/pipeline/AGENTS.md` says "This package follows project-wide patterns documented in:" and then has no table; its siblings carry one. Replace:

````markdown
This package follows project-wide patterns documented in:

```text
````

with:

````markdown
This package follows project-wide patterns documented in:

| Topic              | Document                                                              | When to Reference                          |
| ------------------ | --------------------------------------------------------------------- | ------------------------------------------ |
| Namespace Packages | [namespace-packages.md](../../../.agents/rules/namespace-packages.md) | Import errors, package structure questions |
| Testing Patterns   | [testing-patterns.md](../../../.agents/rules/testing-patterns.md)     | Writing tests, Prefect task tests          |
| Code Quality       | [code-quality.md](../../../.agents/rules/code-quality.md)             | Pre-commit, style, imports                 |
| Docker Workflow    | [docker-workflow.md](../../../.agents/rules/docker-workflow.md)       | Running flows in the Docker services       |
| Troubleshooting    | [troubleshooting.md](../../../.agents/rules/troubleshooting.md)       | Common errors and solutions                |

```text
````

- [ ] **Step 10: Run the harness tests in CI**

In `.github/workflows/ci.yml`, replace:

```yaml
      - name: Print pixi version
        run: pixi --version

```

with:

```yaml
      - name: Print pixi version
        run: pixi --version

      - name: Check agent harness invariants
        run: pixi run pytest tests/agent_harness -v

```

- [ ] **Step 11: Run the tests to verify they pass**

Run: `pixi run pytest tests/agent_harness -v`
Expected: 6 passed.

- [ ] **Step 12: Run the gate**

```bash
git add .gitignore .agents/rules tests/agent_harness AGENTS.md resources/AGENTS.md src/ca_biositing/datamodels/AGENTS.md src/ca_biositing/webservice/AGENTS.md src/ca_biositing/pipeline/AGENTS.md docs/pipeline/USDA/ANALYTICS_HANDOFF.md .github/workflows/ci.yml
pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
git diff --exit-code origin/main -- pixi.lock && git status --short
```

Expected: every hook "Passed" or "Skipped" with no files modified, 6 tests passed, `pixi.lock` unchanged, and only the files above staged (renames show as `R`).

- [ ] **Step 13: Commit**

```bash
git commit -m "docs(agents): move agent_docs into on-demand .agents/rules" -m "Assisted-by: claude-code:claude-opus-5-5"
```

---

### Task 2: Add the template's behavior rules and the rules carved out of the root AGENTS.md

**Files:**
- Create: `.agents/rules/working-agreement.md`, `.agents/rules/contribution-discipline.md` (upstream plus edits)
- Create: `.agents/rules/pixi-environments.md`, `.agents/rules/repository-map.md`, `.agents/rules/onboarding.md`, `.agents/rules/schema-and-migrations.md`
- Modify: `.agents/rules/troubleshooting.md` (insert "Common Pitfalls"), `.agents/rules/code-quality.md` (append a section)
- Modify: `tests/agent_harness/conftest.py`, `tests/agent_harness/test_rules.py`
- Create: `tests/agent_harness/test_pixi_references.py`

**Interfaces:**
- Consumes: Task 1 fixtures `rule_files`, `harness_markdown_files`, `repo_root`.
- Produces: fixtures `pixi_manifest() -> dict[str, Any]` and `pixi_tasks() -> set[str]` in `conftest.py`; constant `ADDED_IN_TASK_2: set[str]` in `test_rules.py`; and the section headings Task 3 relies on (`## Common Pitfalls` in `troubleshooting.md`, `## Before Committing or Opening a PR` in `code-quality.md`, `## Agent Harness` in `repository-map.md`).

- [ ] **Step 1: Add the Pixi fixtures**

Append to `tests/agent_harness/conftest.py`, and add `import tomllib` plus `from typing import Any` to its imports:

```python
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
```

- [ ] **Step 2: Write the failing tests**

In `tests/agent_harness/test_rules.py`, add after `MOVED_FROM_AGENT_DOCS`:

```python
ADDED_IN_TASK_2 = {
    "contribution-discipline.md",
    "onboarding.md",
    "pixi-environments.md",
    "repository-map.md",
    "schema-and-migrations.md",
    "working-agreement.md",
}

# Upstream wording that only makes sense inside the template repository.
TEMPLATE_ONLY_PHRASES = (
    "general-purpose project template",
    "does not belong in the template",
    "This template is deliberately minimal",
    "pre-commit-and-quality.md",
)
```

Replace `test_moved_rules_are_present_and_committable` with:

```python
def test_core_rules_are_present_and_committable(rule_files):
    expected = MOVED_FROM_AGENT_DOCS | ADDED_IN_TASK_2
    missing = expected - {path.name for path in rule_files}
    assert not missing, f"missing, or hidden by .gitignore: {sorted(missing)}"
```

and append:

```python
def test_rules_carry_no_template_only_wording(rule_files):
    hits = [
        f"{path.name}: {phrase!r}"
        for path in rule_files
        for phrase in TEMPLATE_ONLY_PHRASES
        if phrase in " ".join(path.read_text(encoding="utf-8").split())
    ]
    assert not hits, "adapt these upstream phrases for this repository:\n" + "\n".join(hits)
```

Create `tests/agent_harness/test_pixi_references.py`:

```python
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
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run pytest tests/agent_harness -v`
Expected: FAIL `test_core_rules_are_present_and_committable` (six files missing). Everything else PASS.

- [ ] **Step 4: Port `working-agreement.md`**

```bash
UPSTREAM="${TMPDIR:-/tmp}/ssec-project-template"
git -C "$UPSTREAM" show fc00b39:.agents/rules/working-agreement.md > .agents/rules/working-agreement.md
```

Then replace:

```markdown
For this repository the minimum verification is `pixi run pre-commit-all` — see
[pre-commit-and-quality.md](pre-commit-and-quality.md).
```

with:

```markdown
For this repository the minimum verification is `pixi run pre-commit-all` plus
the tests for every package you changed — see [code-quality.md](code-quality.md)
and [testing-patterns.md](testing-patterns.md).
```

- [ ] **Step 5: Port `contribution-discipline.md` with five edits**

```bash
git -C "$UPSTREAM" show fc00b39:.agents/rules/contribution-discipline.md > .agents/rules/contribution-discipline.md
```

Edit 1 — replace:

```markdown
   open another duplicate. Use
   `pixi run gh pr list --state all --search "<terms>"`.
```

with:

```markdown
   open another duplicate. Use `gh pr list --state all --search "<terms>"` and
   `gh issue list --state all --search "<terms>"`.
```

Edit 2 — replace:

```markdown
4. **Confirm the change belongs here.** This is a general-purpose project
   template. If a change is specific to one downstream project, team, or
   workflow, it does not belong in the template — say so.
```

with:

```markdown
4. **Confirm the change belongs here.** Frontend changes belong in the
   `frontend` submodule's repository
   (`sustainability-software-lab/cal-bioscape-frontend`), and general
   improvements to the agent harness (the `AGENTS.md` layout, the behavior
   rules, the shared skills, `AI_POLICY.md`) usually belong upstream in
   `uw-ssec/project-template` first. If the change belongs elsewhere, say so.
```

Edit 3 — replace:

```markdown
This template is deliberately minimal — pre-commit, the GitHub CLI, and the
onboarding tooling. Adding a dependency requires justifying it against that
baseline, and every dependency must be added through Pixi (see
[pixi-environments.md](pixi-environments.md)), never through `pip`, `conda`, or
`venv` directly.
```

with:

```markdown
Every new dependency must be justified, added to the narrowest Pixi feature that
needs it, and locked without changing the lock-file format (see
[pixi-environments.md](pixi-environments.md)) — never through `pip`, `conda`, or
`venv` directly.
```

Edit 4 — replace:

```markdown
### Project-specific or personal configuration

Configuration, hooks, or tooling that only benefits a specific project, team, or
personal workflow does not belong in the template. It belongs in the downstream
repository that needs it.
```

with:

```markdown
### Personal configuration

Editor settings, personal agent skills, `.claude/settings.local.json`, and
`CLAUDE.local.md` are personal configuration. Keep them in your user-level
configuration or in ignored files; do not commit them here.
```

Edit 5 — replace:

```markdown
The guidance in `AGENTS.md` and `.agents/rules/`, the issue and PR templates,
and the pre-commit configuration are deliberately worded. Do not restructure,
```

with:

```markdown
The guidance in `AGENTS.md`, `.agents/rules/`, `.agents/skills/`, and
`AI_POLICY.md`, the issue and PR templates, and the pre-commit configuration are
deliberately worded. Do not restructure,
```

- [ ] **Step 6: Create `schema-and-migrations.md` from the old AGENTS.md**

```bash
{
  printf '%s\n' '# Schema & Migrations' '' \
    '**Load when:** changing SQLModel models, writing or reviewing Alembic' \
    'migrations, editing materialized views in `data_portal_views/`, or validating' \
    'the schema with pgschema.' ''
  git show c5a592e:AGENTS.md | sed -n '112,164p'
  cat <<'EOF'
## Related Guides

- [`alembic/AGENTS.md`](../../alembic/AGENTS.md) — migration templates and the
  raw-SQL snapshot pattern for materialized views
- [`src/ca_biositing/datamodels/AGENTS.md`](../../src/ca_biositing/datamodels/AGENTS.md)
  — SQLModel model and view patterns
- [`docs/datamodels/SQL_FIRST_WORKFLOW.md`](../../docs/datamodels/SQL_FIRST_WORKFLOW.md)
  — the SQL-first path for rapid schema iteration
EOF
} > .agents/rules/schema-and-migrations.md
sed -n '7p;$p' .agents/rules/schema-and-migrations.md
```

Expected: `## Schema Management & Migrations (CRITICAL)`, then the SQL-first link line.

- [ ] **Step 7: Create `repository-map.md` from the old AGENTS.md**

````bash
{
  printf '%s\n' '# Repository Map' '' \
    '**Load when:** you need to know what this repository is, where a file lives,' \
    'or what CI runs against it.' ''
  git show c5a592e:AGENTS.md | sed -n '5,34p'
  git show c5a592e:AGENTS.md | sed -n '165,197p' | sed -E 's#\]\((src|docs)/#](../../\1/#g'
  cat <<'EOF'
## Agent Harness

```text
.
├── AGENTS.md              # Agent entry point: non-negotiables and the rule index
├── .agents/
│   └── rules/             # On-demand rules indexed by AGENTS.md
├── skills.json            # Third-party agent skills synced by `pixi run skills-sync`
├── skills.py              # The sync script behind `pixi run skills-sync`
└── tests/agent_harness/   # Invariant tests for the harness (run in CI)
```

## Continuous Integration & Validation

| Workflow | Runs on | What it does |
| --- | --- | --- |
| `ci.yml` | PRs, pushes to `main` | Tests datamodels, pipeline, and webservice (Python 3.12/3.13 on Ubuntu and macOS) and the agent-harness invariants |
| `cd.yml` | PRs and pushes touching the three packages, releases | Builds the package distributions and publishes them to TestPyPI |
| `docker-build.yml` | Pushes to `main` touching `src/`, `deployment/`, `resources/docker/`, `pixi.toml`, or `pixi.lock`; releases; PRs | Builds and pushes the Docker images |
| `deploy-staging.yml` | A successful image build on `main`; PRs (preview) | Deploys to GCP staging |
| `deploy-production.yml` | An image build triggered by a release; pushes touching infrastructure or `pixi.toml` (Pulumi preview only) | Deploys to GCP production |
| `migrations.yml` | PRs touching `alembic/`, the datamodels package, or Pixi files | Tests the Alembic migrations |
| `trigger-etl.yml`, `trigger-etl-production.yml` | A completed deploy | Triggers the ETL pipeline when ETL code changed |
| `gh-pages.yml` | Changes to the resource-info assets | Validates them and publishes to GitHub Pages |
| `copilot-setup-steps.yml` | Changes to itself | Prepares the GitHub Copilot cloud agent's environment |

[pre-commit.ci](https://pre-commit.ci) runs the pre-commit hooks on pull requests
(see the badge in `README.md`), and Dependabot updates GitHub Actions weekly.

## Further Reading

For more information on SSEC best practices, see:
<https://rse-guidelines.readthedocs.io/en/latest/llms-full.txt>
EOF
} > .agents/rules/repository-map.md
````

- [ ] **Step 8: Create `pixi-environments.md`**

````bash
{
  cat <<'EOF'
# Pixi Environments & Dependencies

**Load when:** setting up the repository, running any command, adding or
changing a dependency, editing `pixi.toml`, or touching `pixi.lock`.

## Pixi Overview

This project uses **Pixi** for local development environment and dependency
management. Pixi handles both Conda and PyPI dependencies. See
<https://pixi.sh/latest/llms-full.txt> for details.

**ALWAYS use Pixi commands — never use conda, pip, or venv directly for local
development.**

The ETL pipeline runs in Docker containers orchestrated by Pixi tasks. Pixi is
used for:

- Managing Docker services (start, stop, logs, status)
- Running code quality tools (pre-commit)
- Running tests (pytest)
- Running QGIS for geospatial analysis
- Deploying and running Prefect workflows
- Starting the FastAPI web service
- Managing agent skills (installing, syncing, updating)

## Environment Setup (ALWAYS RUN FIRST)

```bash
# Install the default environment (required before any other commands)
pixi install
```

**CRITICAL:** Always run `pixi install` before any other Pixi commands. It is
idempotent and safe to repeat.

## Available Environments

| Environment | Features | Use for |
| --- | --- | --- |
| `default` | `datamodels`, `pipeline`, `webservice`, `kernel`, `gis` | Main development: the three packages, notebooks, tests |
| `py312`, `py313` | The three packages on Python 3.12 or 3.13 | The CI test matrix |
| `gis` | `qgis`, `raster`, `vector`, `kernel` | Geospatial analysis (QGIS, rasterio, xarray, shapely, pyproj) |
| `etl` | `datamodels`, `pipeline` | The ETL pipeline; the pipeline Docker image installs it |
| `webservice` | `datamodels`, `webservice` | The FastAPI service; the web service Docker image installs it |
| `frontend` | `frontend` | Frontend development (Node.js, npm) |
| `docs` | `datamodels`, `pipeline`, `docs` | The MkDocs site |
| `deployment` | `cloud` | Cloud infrastructure (Pulumi, gcloud) |
| `viz` | `datamodels`, `visualization`, `kernel` | The visualization gallery and plots |

## Channels

Conda packages resolve from the `conda-forge` channel only. Do not add channels.
The SSEC project template has moved to the `https://prefix.dev/conda-forge`
mirror; switching here would re-solve the whole lock file, so it is a separate
change.

## Lock File Compatibility (CRITICAL)

`pixi.lock` uses lock-file format **v6**. CI, the deploy workflows, both Docker
images (`resources/docker/*.dockerfile`), the devcontainer, and the Copilot setup
workflow pin pixi releases older than 0.68.0, which cannot read the v7 format
that pixi 0.68.0 and later write. A newer pixi rewrites `pixi.lock` as v7
whenever it re-solves — `pixi add`, `pixi remove`, `pixi update`, or
`pixi lock` — and CI and the Docker builds then fail or silently re-solve.

- Check `pixi --version` before any command that changes dependencies.
- With pixi 0.68.0 or later, do not run `pixi add`, `pixi remove`,
  `pixi update`, or `pixi lock`. A dependency change first needs every pinned
  pixi upgraded to the same release and the lock migrated to v7, in its own pull
  request.
- `pixi install` and `pixi run` leave an up-to-date `pixi.lock` alone, and adding
  or editing a task in `pixi.toml` does not change it.

## Adding Dependencies

Only with a pixi that every pin can follow (see above):

```bash
pixi add <package-name>                         # conda package
pixi add --pypi <package-name>                  # PyPI package
pixi add --feature <feature-name> <package-name>  # into one feature
pixi install                                    # after manual pixi.toml edits
```

Every new dependency needs a justification — see
[contribution-discipline.md](contribution-discipline.md).

## GitHub CLI

The GitHub CLI (`gh`) is not a Pixi dependency in this repository. Install it
from <https://cli.github.com> and run `gh auth login` once.

EOF
  git show c5a592e:AGENTS.md | sed -n '102,111p' | sed 's/^### /## /'
  git show c5a592e:AGENTS.md | sed -n '198,221p'
} > .agents/rules/pixi-environments.md
````

The two extracted blocks become `## Jupyter Notebooks` and `## Validated Commands`, the latter with its `### Docker Operations`, `### Development & Quality`, and `### ETL Flow Management` subsections.

- [ ] **Step 9: Create `onboarding.md`**

Create `.agents/rules/onboarding.md`:

````markdown
# Onboarding

**Load when:** setting up this repository for the first time, or helping a new
contributor get started.

The human-facing guide is
[`docs/ca_biositing_local_setup.md`](../../docs/ca_biositing_local_setup.md),
and the README's Quick Start covers the ETL pipeline and web service. The
agent-relevant first steps:

```bash
pixi install                                              # default environment
pixi run pre-commit-install                               # git hooks
cp resources/docker/.env.example resources/docker/.env    # then fill in values
pixi run start-services                                   # PostgreSQL + Prefect; Docker must be running
pixi run submodule-frontend-init                          # only for frontend work
pixi run skills-sync                                      # optional: third-party agent skills
```

- Google Sheets ETL needs a service-account key at `credentials.json` in the
  repository root — see
  [`docs/pipeline/GCP_SETUP.md`](../../docs/pipeline/GCP_SETUP.md). Never commit
  it.
- Commands run on the host that reach the Docker database (for example
  `pixi run migrate`) need `DATABASE_URL` pointing at `localhost`, as the setup
  guide shows.
- Install the GitHub CLI and run `gh auth login`; see
  [pixi-environments.md](pixi-environments.md#github-cli).
````

- [ ] **Step 10: Move the old AGENTS.md pitfalls into `troubleshooting.md`**

```bash
git show c5a592e:AGENTS.md | sed -n '246,270p' | sed -E 's#\]\((src|docs)/#](../../\1/#g' > "${TMPDIR:-/tmp}/pitfalls.md"
cat > "${TMPDIR:-/tmp}/insert_pitfalls.py" <<'EOF'
import sys
from pathlib import Path

rule = Path(".agents/rules/troubleshooting.md")
text = rule.read_text(encoding="utf-8")
marker = "## Environment Issues\n"
assert text.count(marker) == 1, "expected exactly one '## Environment Issues' heading"
pitfalls = Path(sys.argv[1]).read_text(encoding="utf-8")
rule.write_text(text.replace(marker, pitfalls + marker), encoding="utf-8")
EOF
pixi run python "${TMPDIR:-/tmp}/insert_pitfalls.py" "${TMPDIR:-/tmp}/pitfalls.md"
grep -n -E "^## (Common Pitfalls|Environment Issues)" .agents/rules/troubleshooting.md
```

Expected: `## Common Pitfalls` appears directly before `## Environment Issues`.

- [ ] **Step 11: Append the pre-PR workflow to `code-quality.md`**

```bash
cat >> .agents/rules/code-quality.md <<'EOF'

## Before Committing or Opening a PR

1. Stage new files first: `pixi run pre-commit-all` checks only tracked files, so
   run `git add <files>` before relying on it.
2. While you work, run `pixi run pre-commit` on staged changes. If a hook reports
   "files were modified by this hook", re-stage and run it again.
3. Run the tests for every package you changed (see
   [testing-patterns.md](testing-patterns.md)).
4. Before opening a PR, run `pixi run pre-commit-all`, confirm every hook shows
   "Passed" or "Skipped", and then work through
   [contribution-discipline.md](contribution-discipline.md).
EOF
```

- [ ] **Step 12: Run the tests to verify they pass**

Run: `pixi run pytest tests/agent_harness -v`
Expected: 9 passed. If `test_harness_links_resolve` fails, the link is in a file you created in this task; fix its relative path. If `test_pixi_run_references_name_real_tasks` fails, the quoted task is a typo or an upstream leftover.

- [ ] **Step 13: Run the gate and commit**

```bash
git add .agents/rules tests/agent_harness
pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
git diff --exit-code origin/main -- pixi.lock
git commit -m "docs(agents): add behavior rules and split repo guidance into rules" -m "Assisted-by: claude-code:claude-opus-5-5"
```

---

### Task 3: Shrink the root AGENTS.md to an entry point and add the CLAUDE.md imports

**Files:**
- Modify: `AGENTS.md` (full rewrite)
- Create: `CLAUDE.md`, `alembic/CLAUDE.md`, `audit/CLAUDE.md`, `resources/CLAUDE.md`, `src/ca_biositing/datamodels/CLAUDE.md`, `src/ca_biositing/pipeline/CLAUDE.md`, `src/ca_biositing/webservice/CLAUDE.md`
- Modify: `.agents/rules/repository-map.md` (one tree line)
- Create: `tests/agent_harness/test_entrypoint.py`

**Interfaces:**
- Consumes: fixtures `agents_md_files`, `rule_files`, `repo_root`; the Task 2 rule files.
- Produces: `AGENTS.md` sections `## Non-negotiables`, `## Rule Index` (rows of the form `| [<name>.md](.agents/rules/<name>.md) | <trigger> |`), `## Package Guides`, `## Provenance`, and `## Trust These Instructions`. Tasks 5 and 6 add Rule Index rows.

- [ ] **Step 1: Write the failing tests**

Create `tests/agent_harness/test_entrypoint.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run pytest tests/agent_harness/test_entrypoint.py -v`
Expected: FAIL the shim test (no `CLAUDE.md`), `test_entry_point_is_short` (272 lines), `test_entry_point_sections`, `test_rule_index_lists_exactly_the_rule_files`, and `test_package_guides_list_every_nested_agents_md`. PASS `test_old_agents_md_content_survives`, which is the regression guard for Step 3.

- [ ] **Step 3: Rewrite `AGENTS.md`**

Replace the entire file with:

```markdown
# AGENTS.md

Guidance for AI assistants (Claude Code, Codex, Cursor, Copilot, Gemini CLI, and
any other agent harness) working with **ca-biositing**: ETL pipelines that load
Google Sheets and public data into PostgreSQL, a FastAPI service, and geospatial
analysis for bioeconomy siting in California.

**This file is the entry point and is deliberately short.** It carries only what
every agent needs before doing anything. Detailed rules and conventions live as
separate files under [`.agents/rules/`](.agents/rules/) and are loaded on demand
— read the one whose trigger matches your current task, not all of them.
Package directories carry their own `AGENTS.md`; read it before changing code
there (see [Package Guides](#package-guides)).

## Non-negotiables

These apply to every task, in every session:

1. **Pixi is the only package manager.** Never invoke `pip`, `conda`, or `venv`
   directly. Run `pixi install` before any other Pixi command, and never let a
   newer pixi rewrite `pixi.lock` (see
   [pixi-environments.md](.agents/rules/pixi-environments.md)).
2. **Verify before you claim.** Never report work as complete, fixed, or passing
   without having run the check and read its output. The minimum gate here is
   `pixi run pre-commit-all` plus the tests for every package you changed.
3. **Change surgically.** Every changed line must trace directly to the request.
   Don't refactor, reformat, or "improve" adjacent code you weren't asked to
   touch.
4. **Ask instead of assuming.** If the request has multiple readings or
   something is unclear, stop and name it — before implementing, not after.
5. **Change the schema only through SQLModel models and Alembic migrations.**
   Never alter tables or views by hand; follow
   [schema-and-migrations.md](.agents/rules/schema-and-migrations.md).
6. **Never open a PR** without working through
   [`.agents/rules/contribution-discipline.md`](.agents/rules/contribution-discipline.md)
   in full, including human review of the complete diff.

## Rule Index

Load the rule file whose trigger matches what you are about to do.

| Rule file | Load when |
| --- | --- |
| [working-agreement.md](.agents/rules/working-agreement.md) | Starting any implementation, refactor, or bugfix — the behavioral baseline |
| [contribution-discipline.md](.agents/rules/contribution-discipline.md) | About to commit, open a PR, or asked to "contribute" / "fix some issues" |
| [pixi-environments.md](.agents/rules/pixi-environments.md) | Running any command, adding a dependency, editing `pixi.toml`, or touching `pixi.lock` |
| [code-quality.md](.agents/rules/code-quality.md) | Writing Python, committing, preparing a PR, or claiming checks pass |
| [testing-patterns.md](.agents/rules/testing-patterns.md) | Writing, fixing, or running tests |
| [repository-map.md](.agents/rules/repository-map.md) | You need to know what this repo is, where a file lives, or what CI runs |
| [namespace-packages.md](.agents/rules/namespace-packages.md) | Adding modules under `src/ca_biositing/` or fixing import errors |
| [schema-and-migrations.md](.agents/rules/schema-and-migrations.md) | Changing SQLModel models, Alembic migrations, or materialized views |
| [docker-workflow.md](.agents/rules/docker-workflow.md) | Starting, inspecting, or rebuilding the Docker services, or running ETL flows |
| [onboarding.md](.agents/rules/onboarding.md) | First-time setup, or helping a new contributor get started |
| [troubleshooting.md](.agents/rules/troubleshooting.md) | A documented command fails or behaves unexpectedly |

## Package Guides

| Directory | Guide | Covers |
| --- | --- | --- |
| `src/ca_biositing/datamodels/` | [AGENTS.md](src/ca_biositing/datamodels/AGENTS.md) | SQLModel models, views, and database sessions |
| `src/ca_biositing/pipeline/` | [AGENTS.md](src/ca_biositing/pipeline/AGENTS.md) | Prefect ETL tasks and flows |
| `src/ca_biositing/webservice/` | [AGENTS.md](src/ca_biositing/webservice/AGENTS.md) | The FastAPI application and endpoints |
| `alembic/` | [AGENTS.md](alembic/AGENTS.md) | Migration patterns and materialized-view SQL snapshots |
| `resources/` | [AGENTS.md](resources/AGENTS.md) | Docker Compose services and Prefect deployments |
| `audit/` | [AGENTS.md](audit/AGENTS.md) | Running and interpreting the database audit |

## Provenance

This harness — the short entry point, the on-demand rules under
`.agents/rules/`, and the `CLAUDE.md` imports — is adapted from the UW SSEC
[project template](https://github.com/uw-ssec/project-template) at commit
`fc00b39`. Its behavioral rules in turn adapt two upstream sources:

- [obra/superpowers](https://github.com/obra/superpowers) `CLAUDE.md` — agent
  contribution discipline (`contribution-discipline.md`).
- [multica-ai/andrej-karpathy-skills](https://github.com/multica-ai/andrej-karpathy-skills)
  `CLAUDE.md` — behavioral guidelines that reduce common LLM coding mistakes
  (`working-agreement.md`).

## Trust These Instructions

These instructions were generated through comprehensive exploration and testing
of the repository. Commands have been validated to work correctly. **Only
perform additional searches if:**

- You need information not covered by `AGENTS.md` or `.agents/rules/`
- Instructions appear outdated or produce errors
- You're implementing functionality that changes the build system

For routine tasks (adding files, making code changes, running checks), follow
these instructions directly without additional exploration.
```

- [ ] **Step 4: Add a `CLAUDE.md` import beside every `AGENTS.md`**

```bash
for dir in . alembic audit resources src/ca_biositing/datamodels src/ca_biositing/pipeline src/ca_biositing/webservice; do
  printf '@AGENTS.md\n' > "$dir/CLAUDE.md"
done
git ls-files --others --exclude-standard -- 'CLAUDE.md' '*/CLAUDE.md'
```

Expected: seven paths.

- [ ] **Step 5: Record the import in the repository map**

In `.agents/rules/repository-map.md`, replace:

```text
├── AGENTS.md              # Agent entry point: non-negotiables and the rule index
```

with:

```text
├── AGENTS.md              # Agent entry point: non-negotiables and the rule index
├── CLAUDE.md              # `@AGENTS.md` import; every package AGENTS.md has one too
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `pixi run pytest tests/agent_harness -v`
Expected: 15 passed.

- [ ] **Step 7: Verify Claude Code loads the files**

This needs Claude Code v2.1.277 or later.

1. Start `claude` in the repository root and run `/memory`. Expected: `CLAUDE.md` is listed, with `AGENTS.md` loaded through its import.
2. Ask Claude to read `alembic/env.py`, then run `/memory` again. Expected: `alembic/CLAUDE.md` is listed.

Record what you saw in the commit body. If step 2 shows no nested file, stop and report it rather than continuing: D3 depends on it.

- [ ] **Step 8: Run the gate and commit**

```bash
git add AGENTS.md CLAUDE.md alembic/CLAUDE.md audit/CLAUDE.md resources/CLAUDE.md src/ca_biositing/*/CLAUDE.md .agents/rules/repository-map.md tests/agent_harness/test_entrypoint.py
pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
git diff --exit-code origin/main -- pixi.lock
git commit -m "docs(agents): shrink AGENTS.md to an entry point and import it for Claude" -m "Assisted-by: claude-code:claude-opus-5-5"
```

---

### Task 4: Adopt the AI attribution policy and the AI-aware PR template

**Files:**
- Create: `AI_POLICY.md` (verbatim upstream), `docs/AI_POLICY.md` (symlink to `../AI_POLICY.md`)
- Modify: `.github/pull_request_template.md` (replace with verbatim upstream)
- Modify: `mkdocs.yml` (nav entry), `CONTRIBUTING.md` (one bullet), `README.md` (Contributing paragraph)
- Create: `tests/agent_harness/test_ai_policy.py`

**Interfaces:**
- Consumes: fixture `repo_root`.
- Produces: `AI_POLICY.md`, which defines the `Assisted-by: <harness>:<model>` trailer used by Task 5's `commit`/`create-pr` skills and Task 6's `okf --actor`; and the PR template sections `## 🤖 AI assistance disclosure` and `## 🔍 Author verification`.

- [ ] **Step 1: Write the failing tests**

Create `tests/agent_harness/test_ai_policy.py`:

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run pytest tests/agent_harness/test_ai_policy.py -v`
Expected: 3 failed (`AI_POLICY.md` missing, PR template sections missing, link and nav missing).

- [ ] **Step 3: Copy the policy and PR template from upstream**

```bash
UPSTREAM="${TMPDIR:-/tmp}/ssec-project-template"
git -C "$UPSTREAM" show fc00b39:AI_POLICY.md > AI_POLICY.md
git -C "$UPSTREAM" show fc00b39:.github/pull_request_template.md > .github/pull_request_template.md
ln -s ../AI_POLICY.md docs/AI_POLICY.md
```

- [ ] **Step 4: Publish and point to the policy**

In `mkdocs.yml`, replace `  - Contributing: CONTRIBUTING.md` with:

```yaml
  - Contributing: CONTRIBUTING.md
  - AI Policy: AI_POLICY.md
```

In `CONTRIBUTING.md`, replace:

```markdown
- Please follow the
  [Conventional Commits](https://github.com/uw-ssec/rse-guidelines/blob/main/conventional-commits.md)
  naming for pull request titles.
```

with:

```markdown
- Please follow the
  [Conventional Commits](https://github.com/uw-ssec/rse-guidelines/blob/main/conventional-commits.md)
  naming for pull request titles.

- If you use AI tools while contributing, read the [AI Policy](AI_POLICY.md)
  first: it covers disclosure, review responsibility, and how to credit AI
  assistance in commits.
```

In `README.md`, replace:

```markdown
See [CONTRIBUTING.md](CONTRIBUTING.md) for general contribution guidelines
(branching, PRs, commit style, pre-commit setup).
```

with:

```markdown
See [CONTRIBUTING.md](CONTRIBUTING.md) for general contribution guidelines
(branching, PRs, commit style, pre-commit setup). If you use AI tools while
contributing, read the [AI Policy](AI_POLICY.md) first: it covers disclosure,
review responsibility, and how to credit AI assistance in commits.
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `pixi run pytest tests/agent_harness -v`
Expected: 18 passed.

- [ ] **Step 6: Check the docs site build**

Run: `pixi run -e docs docs-build 2>&1 | grep -E "ERROR|AI_POLICY" ; test -f site/AI_POLICY/index.html && echo "AI Policy page built"`
Expected: no `ERROR` lines, no warning that mentions `AI_POLICY`, and `AI Policy page built`. `site/` is gitignored.

- [ ] **Step 7: Run the gate and commit**

```bash
git add AI_POLICY.md docs/AI_POLICY.md .github/pull_request_template.md mkdocs.yml CONTRIBUTING.md README.md tests/agent_harness/test_ai_policy.py
pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
git diff --exit-code origin/main -- pixi.lock
git commit -m "docs(policy): adopt the SSEC AI policy and AI-aware PR template" -m "Assisted-by: claude-code:claude-opus-5-5"
```

- [ ] **Step 8 (needs your human partner's go-ahead — this changes GitHub): create the label the policy names**

```bash
gh label create ai-assisted --description "Pull request made with AI assistance" --color 8250df
```

---

### Task 5: Commit portable project skills and wire them into every harness

**Files:**
- Create: `.agents/skills/{clean-branches,commit,create-issue,create-pr,push}/SKILL.md` (verbatim upstream)
- Create: `.agents/skills/merge-pr/SKILL.md`, `.agents/skills/docs/SKILL.md` (adapted, full content below)
- Create: `.claude/skills` (symlink to `../.agents/skills`), `.agents/rules/agent-skills.md`
- Modify: `.gitignore` (Agents Braindump block), `skills.json` (local registry), `AGENTS.md` (one Rule Index row), `.agents/rules/repository-map.md` (tree), `tests/agent_harness/conftest.py`
- Create: `tests/agent_harness/test_skills.py`

**Interfaces:**
- Consumes: fixtures `repo_root`, `is_git_ignored`, `rule_files`; helper `repo_files`; Task 4's `AI_POLICY.md`.
- Produces: fixture `project_skill_dirs() -> list[Path]`; constant `PROJECT_SKILLS: set[str]` in `test_skills.py`, which Task 6 extends with `okf-memory`; and the `.gitignore` allowlist block that Task 6 extends.

- [ ] **Step 1: Add the fixture**

Append to `tests/agent_harness/conftest.py`:

```python
@pytest.fixture(scope="session")
def project_skill_dirs() -> list[Path]:
    """Skill directories under .agents/skills/ that git would commit."""
    return sorted({path.parent for path in repo_files(".agents/skills/*/SKILL.md")})
```

- [ ] **Step 2: Write the failing tests**

Create `tests/agent_harness/test_skills.py`:

```python
"""Project skills are portable, committed, discoverable, and safe from skills-sync."""

from __future__ import annotations

import json
import os
import re
import subprocess

import pytest
import yaml

PROJECT_SKILLS = {
    "clean-branches", "commit", "create-issue", "create-pr", "docs", "merge-pr", "push",
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
```

- [ ] **Step 3: Run the tests to verify they fail**

Run: `pixi run pytest tests/agent_harness/test_skills.py -v`
Expected: FAIL `test_project_skills_are_committable`, `test_claude_code_sees_skills_through_a_committed_symlink`, `test_merge_pr_is_safe_in_linked_worktrees` (file not found), and `test_commit_and_pr_skills_follow_the_ai_policy`. The rest PASS: no skills exist yet, and `.agents/*` already ignores synced skills.

- [ ] **Step 4: Allowlist the project skills and the symlink**

In `.gitignore`, replace the block from Task 1:

```gitignore
# Agents Braindump
# .agents/ and .claude/ hold machine-local agent state and the third-party
# skills that `pixi run skills-sync` installs. Only the committed harness is
# tracked: .agents/rules/ (see AGENTS.md).
.agents/*
!.agents/rules/
.claude/
.cline/
.roo/
```

with:

```gitignore
# Agents Braindump
# .agents/ and .claude/ hold machine-local agent state and the third-party
# skills that `pixi run skills-sync` installs. Only the committed harness is
# tracked: .agents/rules/, the project skills allowlisted below, and the
# .claude/skills symlink. Allowlist each new project skill here (see
# .agents/rules/agent-skills.md).
.agents/*
!.agents/rules/
!.agents/skills/
.agents/skills/*
!.agents/skills/clean-branches/
!.agents/skills/commit/
!.agents/skills/create-issue/
!.agents/skills/create-pr/
!.agents/skills/docs/
!.agents/skills/merge-pr/
!.agents/skills/push/
.claude/*
!.claude/skills
.cline/
.roo/
```

- [ ] **Step 5: Copy the verbatim skills and link `.claude/skills`**

```bash
UPSTREAM="${TMPDIR:-/tmp}/ssec-project-template"
for skill in clean-branches commit create-issue create-pr push; do
  mkdir -p ".agents/skills/$skill"
  git -C "$UPSTREAM" show "fc00b39:.agents/skills/$skill/SKILL.md" > ".agents/skills/$skill/SKILL.md"
done
mkdir -p .agents/skills/merge-pr .agents/skills/docs .claude
ln -s ../.agents/skills .claude/skills
```

- [ ] **Step 6: Write the worktree-safe `merge-pr` skill**

Create `.agents/skills/merge-pr/SKILL.md`. Steps 1–2 and most rules are upstream verbatim; steps 3–7 are adapted for linked worktrees and the shared stash stack.

````markdown
---
name: merge-pr
description:
  Use when a pull request is approved and ready to land, or when review has
  finished and the branch needs cleaning up afterward.
---

# Merge PR

Merge a pull request and clean up branches.

## Arguments

Optional: a PR number or URL. Defaults to the current branch's PR.

## Instructions

1. Determine the PR:

   - If a PR number or URL was passed, use it
   - If not, find the PR for the current branch:
     `gh pr view --json number,title,state,headRefName`

2. Check PR status:

   - `gh pr view <number> --json state,mergeable,mergeStateStatus,statusCheckRollup,title,headRefName`
   - If checks are failing, warn the user and ask whether to proceed
   - If there are merge conflicts, tell the user and stop

3. Check for local changes and for a linked worktree:

   - `git status`
   - Compare `git rev-parse --git-dir` with `git rev-parse --git-common-dir`.
     If they differ, this checkout is a linked worktree, and `main` is usually
     checked out in the main worktree.
   - If there are uncommitted changes, set them aside under a unique name. The
     stash stack is shared by every worktree of the repository, so never use a
     bare stash: run `git stash push -u -m "merge-pr-<number>"` and note the
     entry's SHA from `git stash list --format='%H %gs'`.

4. Merge the PR. Use `--squash` by default (consistent with this repo's
   history).

   - In the main checkout:

     ```bash
     gh pr merge <number> --squash --delete-branch
     ```

   - In a linked worktree, leave out `--delete-branch`, because it tries to
     check out `main` here and fails while another worktree has it. Delete the
     remote branch yourself:

     ```bash
     gh pr merge <number> --squash
     git push origin --delete <branch-name>
     ```

5. Clean up locally:

   - In the main checkout:
     - Switch to main if not already: `git checkout main`
     - Pull the merged changes: `git pull origin main`
     - Prune stale remote refs: `git fetch --prune`
     - Delete the local branch if it still exists: `git branch -d <branch-name>`
   - In a linked worktree:
     - Prune stale remote refs: `git fetch --prune`
     - Tell the user the worktree can now be removed from the main checkout
       with `git worktree remove <path>`, which also frees the branch for
       deletion. Do not check out `main` here.
   - If you stashed changes, restore them with `git stash apply <sha>`. Once
     they apply cleanly, find the entry's current `stash@{n}` in
     `git stash list` and drop it with `git stash drop stash@{n}`.

6. Verify cleanup:

   - `git branch -a | grep <branch-name>` to confirm the branch is gone. In a
     linked worktree the local branch remains until the worktree is removed.

7. Confirm: "PR #N merged into main. Branch `<name>` deleted locally and
   remotely." From a linked worktree: "PR #N merged into main. Branch `<name>`
   deleted remotely; remove the worktree to delete it locally."

## Rules

- Default merge strategy is `--squash` (produces clean linear history)
- If user asks for a merge commit, use `--merge` instead
- If user asks for rebase, use `--rebase` instead
- NEVER force-delete branches (`-D`), use `-d` which is safe
- Always restore stashed changes after merge, by SHA. Never pop a stash by
  position: another worktree's session may own the top entry
- If the merge fails, do NOT retry destructively — report the error
````

- [ ] **Step 7: Write the repo-specific `docs` skill**

Create `.agents/skills/docs/SKILL.md`:

````markdown
---
name: docs
description:
  Use when work completed in this session needs writing up in the MkDocs site
  under docs/ — new pipelines, schema or API changes, deployment changes, or
  gotchas that readers of the site need to know.
---

# Docs

Write or update the MkDocs documentation in `docs/` for recent work in this
session.

## Arguments

Optional: a topic, a section, or "all" to cover everything from this session.

## Instructions

1. **Gather context** — run these in parallel to understand what changed:

   - `git log --oneline -20` (recent commits)
   - `git diff main...HEAD --stat` (if on a feature branch)
   - `git log --oneline --since="8 hours ago"` (today's work)
   - Read `mkdocs.yml`, whose `nav:` is explicit, and `docs/README.md`, a
     symlink to the repository `README.md` that serves as the site's home page

2. **Determine scope** — based on the argument and recent changes, decide which
   docs need writing or updating:

   - If the argument is a specific topic (e.g., "landiq", "auth",
     "materialized views"), focus there
   - If the argument is a section (e.g., "pipeline", "datamodels",
     "deployment"), update that section
   - If the argument is "all" or empty, document everything from the current
     session
   - Always check existing docs first — update rather than duplicate

3. **Write documentation** covering these categories as relevant:

   ### Technical Details

   - What was built, changed, or fixed
   - Schema changes (SQLModel models, Alembic migrations, materialized views),
     API endpoints, and ETL flows
   - Configuration changes, environment variables, Pixi tasks, or dependencies
     added

   ### Technical Architecture

   - System design and component relationships
   - Data flow diagrams (use Mermaid syntax)
   - Integration points: Google Sheets and external sources → Prefect ETL →
     PostgreSQL → materialized views → FastAPI → frontend
   - Infrastructure decisions (Docker Compose locally; GCP and Pulumi for
     deployment)

4. **Place documentation correctly** — follow the existing layout:

   - System architecture → `docs/architecture.md`
   - ETL pipeline and flows → `docs/pipeline/`
   - Data models, schema, and the SQL-first workflow → `docs/datamodels/`
   - Web service and API → `docs/webservice/` and `docs/api/`
   - Docker and Prefect resources → `docs/resources/`
   - Cloud deployment → `docs/deployment/`
   - Operational runbooks → `docs/operations/`
   - Implementation plans are not docs: keep them in the gitignored `plans/`
     directory

5. **Update mkdocs.yml nav** — if you created a new file, add it to the `nav:`
   section in `mkdocs.yml` under the correct heading. Match existing
   indentation and naming style.

6. **Verify** — run `pixi run -e docs docs-build` to confirm MkDocs builds
   without errors.

7. **Report** — show the user:
   - Files created or updated (with paths)
   - New nav entries added
   - Build status (pass/fail)

## Documentation Style

- Use MkDocs Material features: admonitions (`!!! note`, `!!! warning`,
  `!!! tip`), tabs, Mermaid diagrams, code blocks with language tags
- Start every doc with a level-1 heading and a 1-2 sentence summary
- Use tables for structured data (configs, env vars, field mappings)
- Keep headings hierarchical (h1 → h2 → h3, never skip levels)
- Use imperative voice for guides ("Run the migration", not "You should run the
  migration")
- Architecture decisions follow the pattern:

```markdown
### YYYY-MM-DD: Decision Title (Status)

- **Decision:** What was decided
- **Why:** The reasoning and constraints
- **Result:** What was implemented and any notable outcomes
```

## Mermaid Diagram Conventions

- Use `graph TD` for top-down architecture diagrams
- Use `sequenceDiagram` for request/response flows
- Use `erDiagram` for database relationships
- Keep diagrams focused — split complex systems into multiple diagrams
- Label edges with the protocol or mechanism (e.g., `-->|JWT|`, `-->|REST|`,
  `-->|Queue|`)

## Rules

- Never delete existing documentation — update or extend it
- Always read existing docs before writing to avoid duplication
- Every new doc must appear in `mkdocs.yml` nav
- Date-stamp architecture decisions
- Use relative links between docs (e.g., `../pipeline/ETL_WORKFLOW.md`)
- Build must pass before considering the task done
- If `pixi run -e docs docs-build` fails, fix the issue (usually a nav mismatch
  or broken link)
- NEVER include sensitive information in documentation (credentials, internal
  processes, etc.)
````

- [ ] **Step 8: Declare the project skills in `skills.json`**

Replace the first source:

```json
    {
      "registry": "local",
      "skills": ["database-query", "data-visualization"]
    },
```

with:

```json
    {
      "registry": "local",
      "skills": [
        "clean-branches",
        "commit",
        "create-issue",
        "create-pr",
        "data-visualization",
        "database-query",
        "docs",
        "merge-pr",
        "push"
      ]
    },
```

Keep `database-query` and `data-visualization`: they belong to the author of #442 (see Noticed, Not Fixed).

- [ ] **Step 9: Write the `agent-skills.md` rule and index it**

Add this row to the `AGENTS.md` Rule Index, directly after the `onboarding.md` row:

```markdown
| [agent-skills.md](.agents/rules/agent-skills.md) | Adding, editing, or syncing an agent skill, or editing `skills.json` |
```

Run `pixi run pytest tests/agent_harness/test_entrypoint.py -v`. Expected: FAIL `test_rule_index_lists_exactly_the_rule_files`, because the rule doesn't exist yet.

Create `.agents/rules/agent-skills.md`:

```markdown
# Agent Skills

**Load when:** adding, editing, or syncing an agent skill, editing `skills.json`,
or a skill is missing or behaving unexpectedly.

## Two Kinds of Skills

| Kind | Lives in | Tracked in git | Declared in |
| --- | --- | --- | --- |
| Project skills (`commit`, `push`, `create-pr`, `merge-pr`, `create-issue`, `clean-branches`, `docs`) | `.agents/skills/<name>/SKILL.md` | Yes, allowlisted in `.gitignore` | The `"local"` registry in `skills.json` |
| Third-party skills (`find-skills`, `github-issues`, `web-design-guidelines`, ...) | `.agents/skills/<name>/`, installed by `pixi run skills-sync` | No, ignored | Registries in `skills.json`; versions in `skills-lock.json` |

Every harness finds both kinds in one place. Codex, Copilot, Cursor, and OpenCode
read `.agents/skills/` natively. Claude Code reads `.claude/skills/`, which is a
committed symlink to `../.agents/skills`.

## Add a Project Skill

1. Create `.agents/skills/<name>/SKILL.md`. Its frontmatter holds only `name` —
   the directory name: lowercase letters, digits, and hyphens, at most 64
   characters — and `description`, at most 1024 characters, starting "Use when
   ...". Other frontmatter keys are Claude Code-specific and break portability.
2. Add `!.agents/skills/<name>/` to the "Agents Braindump" block of
   `.gitignore`. Without it, git silently ignores the new skill.
3. Add `<name>` to the `"local"` registry's `skills` list in `skills.json`.
4. Run `pixi run pytest tests/agent_harness -v`.

## Add or Update a Third-Party Skill

1. Add the registry, and optionally a `skills` filter, to `skills.json`.
2. Run `pixi run skills-sync`. It runs `npx skills add <registry> -y` for each
   source, then `npx skills update`.
3. Commit `skills.json` and `skills-lock.json` only; the installed skill
   directories stay ignored.

## Name Collisions

`skills-sync` installs a skill by deleting `.agents/skills/<name>/` and copying
the new one in, so a registry skill that shares a project skill's name
overwrites the committed one. Registries without a `skills` filter, such as
`vercel-labs/agent-skills`, install everything they publish. Git shows the
overwritten files as modified: restore them with
`git restore .agents/skills/<name>` and filter that skill out of `skills.json`.
`tests/agent_harness/test_skills.py` fails when `skills-lock.json` names a
project skill.

## Windows

`.claude/skills` is a symlink. On Windows, git checks a symlink out as a plain
text file unless Developer Mode is on and `core.symlinks` is enabled, and Claude
Code then finds no project skills. Enable Developer Mode, run
`git config core.symlinks true`, then `git checkout -- .claude/skills`.

## Verify

- In Claude Code, `/skills` lists the project skills, and
  `claude plugin validate .claude/skills` checks their frontmatter.
- `pixi run pytest tests/agent_harness -v` checks frontmatter, the symlink, the
  ignore rules, `skills.json`, and collisions.
```

- [ ] **Step 10: Record the skills in the repository map**

In `.agents/rules/repository-map.md`, replace:

```text
├── .agents/
│   └── rules/             # On-demand rules indexed by AGENTS.md
```

with:

```text
├── .agents/
│   ├── rules/             # On-demand rules indexed by AGENTS.md
│   └── skills/            # Project skills (committed) and synced third-party skills (ignored)
├── .claude/
│   └── skills -> ../.agents/skills   # Symlink so Claude Code discovers the skills
```

- [ ] **Step 11: Run the tests to verify they pass**

```bash
git add .gitignore .claude/skills .agents/skills .agents/rules skills.json AGENTS.md tests/agent_harness
pixi run pytest tests/agent_harness -v
```

Expected: 27 passed. `git add` comes first because two tests read the git index.

- [ ] **Step 12: Prove `skills-sync` leaves the project skills alone**

Run the real sync in a throwaway worktree built from a snapshot of the index, which leaves your branch and the shared stash untouched. It needs the network.

```bash
SYNC_DIR="${TMPDIR:-/tmp}/harness-sync-check"
SNAPSHOT=$(git commit-tree "$(git write-tree)" -p HEAD -m "skills-sync check")
git worktree add --detach "$SYNC_DIR" "$SNAPSHOT"
(
  cd "$SYNC_DIR"
  pixi exec --spec "python=3.12" --spec "nodejs>=18" -- python skills.py > "${TMPDIR:-/tmp}/harness-sync.log" 2>&1
  git status --porcelain --untracked-files=all
  git diff --exit-code -- .agents .claude && echo "project skills untouched"
  readlink .claude/skills
  ls .agents/skills | tr '\n' ' '; echo
)
git worktree remove --force "$SYNC_DIR"
```

Expected: `git status` shows at most ` M skills-lock.json`, then `project skills untouched`, then `../.agents/skills`, then a listing with both the project skills and synced ones such as `find-skills` and `github-issues`. Anything under `.agents/` or `.claude/` in the status output means the allowlist leaks: fix `.gitignore` before continuing. If the sync itself fails, read `${TMPDIR:-/tmp}/harness-sync.log`.

- [ ] **Step 13: Verify Claude Code discovers the skills**

Start `claude` in the repository root and run `/skills`. Expected: `clean-branches`, `commit`, `create-issue`, `create-pr`, `docs`, `merge-pr`, and `push` are listed as project skills. Then run `claude plugin validate .claude/skills`; expected: no errors (needs Claude Code v2.1.233 or later).

- [ ] **Step 14: Run the gate and commit**

```bash
pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
git diff --exit-code origin/main -- pixi.lock
git commit -m "feat(skills): add portable project skills for every agent harness" -m "Assisted-by: claude-code:claude-opus-5-5"
```

---

### Task 6: Add OKF project memory without touching `pixi.lock`

**Files:**
- Modify: `pixi.toml` (one `[tasks]` entry after `skills-sync`)
- Create: `knowledge/index.md`, `knowledge/log.md` (via `okf init`)
- Create: `.agents/skills/okf-memory/SKILL.md` (upstream plus one edit), `.agents/rules/mkdocs-okf-knowledge-bundle.md` (upstream plus four edits)
- Modify: `.pre-commit-config.yaml` (prettier `exclude`), `.gitignore` (one allowlist line), `skills.json` (one name), `AGENTS.md` (one Rule Index row), `.agents/rules/pixi-environments.md` (two additions), `.agents/rules/repository-map.md` (one tree line), `.agents/skills/docs/SKILL.md` (one subsection), `tests/agent_harness/test_skills.py` (`PROJECT_SKILLS`)
- Create: `tests/agent_harness/test_okf.py`, `tests/agent_harness/test_lockfile.py`

**Interfaces:**
- Consumes: fixtures `pixi_manifest`, `repo_root`; Task 5's `PROJECT_SKILLS`, `.gitignore` block, and `skills.json` local list; Task 4's `Assisted-by` token (for `okf --actor`).
- Produces: the Pixi task `okf` (`pixi run okf <args>` runs from the repository root); in `test_lockfile.py`, the functions `lock_format(lock_path: Path) -> int`, `pixi_pins(root: Path) -> dict[str, tuple[int, int, int]]`, and `pins_that_cannot_read(lock_version: int, pins: dict[str, tuple[int, int, int]]) -> list[str]`, which Task 7 reuses in the same module.

- [ ] **Step 1: Write the failing tests**

Create `tests/agent_harness/test_okf.py`:

```python
"""Project memory: the okf task, the knowledge/ bundle, and its prettier carve-out."""

from __future__ import annotations

import re

import yaml

OKF_TASK = 'pixi exec --spec "okf-agent-memory>=0.5.0,<0.6" -- okf'


def test_okf_task_runs_the_pinned_cli(pixi_manifest):
    assert pixi_manifest["tasks"]["okf"]["cmd"] == OKF_TASK


def test_knowledge_bundle_is_initialized(repo_root):
    index = (repo_root / "knowledge" / "index.md").read_text(encoding="utf-8")
    assert index.startswith('---\nokf_version: "0.2"\n---\n')
    assert (repo_root / "knowledge" / "log.md").is_file()


def test_prettier_skips_the_knowledge_bundle(repo_root):
    config = yaml.safe_load((repo_root / ".pre-commit-config.yaml").read_text(encoding="utf-8"))
    prettier = next(
        hook for repo in config["repos"] for hook in repo["hooks"] if hook["id"] == "prettier"
    )
    assert re.search(prettier["exclude"], "knowledge/decisions/use-okf.md")
    assert not re.search(prettier["exclude"], ".agents/rules/working-agreement.md")
```

Create `tests/agent_harness/test_lockfile.py`:

```python
"""pixi.lock stays readable by every pixi release this repository pins."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

Version = tuple[int, int, int]

# Oldest pixi that reads each lock-file format. The workspace already requires
# pixi >= 0.55 (`requires-pixi`), which reads v6; pixi 0.68.0 introduced v7
# (https://github.com/prefix-dev/pixi/releases/tag/v0.68.0).
MIN_PIXI_FOR_LOCK_FORMAT: dict[int, Version] = {6: (0, 55, 0), 7: (0, 68, 0)}

PIN_PATTERNS = {
    ".github/workflows/*.yml": re.compile(r"pixi-version:\s*v?(\d+)\.(\d+)\.(\d+)"),
    "resources/docker/*.dockerfile": re.compile(r"ghcr\.io/prefix-dev/pixi:(\d+)\.(\d+)\.(\d+)"),
    ".devcontainer/Dockerfile": re.compile(r"ARG PIXI_VERSION=v?(\d+)\.(\d+)\.(\d+)"),
}


def lock_format(lock_path: Path) -> int:
    """Return the lock-file format version from pixi.lock's first line."""
    with lock_path.open(encoding="utf-8") as handle:
        first = handle.readline().strip()
    match = re.fullmatch(r"version: (\d+)", first)
    if match is None:
        raise ValueError(f"unexpected first line in {lock_path}: {first!r}")
    return int(match.group(1))


def pixi_pins(root: Path) -> dict[str, Version]:
    """Map ``file:line`` to each pixi version pinned in CI, Docker, and the devcontainer."""
    pins: dict[str, Version] = {}
    for pattern, regex in PIN_PATTERNS.items():
        for path in sorted(root.glob(pattern)):
            lines = path.read_text(encoding="utf-8").splitlines()
            for lineno, line in enumerate(lines, start=1):
                for match in regex.finditer(line):
                    major, minor, patch = (int(group) for group in match.groups())
                    pins[f"{path.relative_to(root).as_posix()}:{lineno}"] = (major, minor, patch)
    return pins


def pins_that_cannot_read(lock_version: int, pins: dict[str, Version]) -> list[str]:
    """Return the pins too old to read a lock file of ``lock_version``."""
    if lock_version not in MIN_PIXI_FOR_LOCK_FORMAT:
        raise ValueError(
            f"lock-file format v{lock_version} is unknown; add its first pixi release"
        )
    minimum = MIN_PIXI_FOR_LOCK_FORMAT[lock_version]
    return sorted(
        f"{where} (pixi {'.'.join(map(str, version))})"
        for where, version in pins.items()
        if version < minimum
    )


def test_old_pins_cannot_read_v7():
    pins = {"ci.yml:38": (0, 63, 2), "devcontainer:3": (0, 68, 0)}
    assert pins_that_cannot_read(7, pins) == ["ci.yml:38 (pixi 0.63.2)"]
    assert pins_that_cannot_read(6, pins) == []


def test_unknown_lock_format_is_an_error():
    with pytest.raises(ValueError, match="v8"):
        pins_that_cannot_read(8, {})


def test_lock_format_reads_the_header(tmp_path):
    lock = tmp_path / "pixi.lock"
    lock.write_text("version: 7\nenvironments:\n", encoding="utf-8")
    assert lock_format(lock) == 7


def test_every_pinned_pixi_can_read_pixi_lock(repo_root):
    pins = pixi_pins(repo_root)
    assert len(pins) >= 10, f"expected pins in workflows, Dockerfiles, devcontainer: {pins}"
    unreadable = pins_that_cannot_read(lock_format(repo_root / "pixi.lock"), pins)
    assert not unreadable, (
        "pixi.lock is in a format these pinned pixi releases cannot read: "
        + ", ".join(unreadable)
        + ". Revert pixi.lock (`git checkout origin/main -- pixi.lock`) unless this "
        "pull request upgrades every pin; see .agents/rules/pixi-environments.md."
    )
```

In `tests/agent_harness/test_skills.py`, add `"okf-memory"` to `PROJECT_SKILLS`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run pytest tests/agent_harness -v`
Expected: FAIL `test_okf_task_runs_the_pinned_cli` (KeyError `okf`), `test_knowledge_bundle_is_initialized`, `test_prettier_skips_the_knowledge_bundle`, and `test_project_skills_are_committable` (`okf-memory` missing). The four lockfile tests PASS: they guard the current state.

- [ ] **Step 3: Add the `okf` task**

In `pixi.toml`, replace:

```toml
skills-sync = "python skills.py"
```

with:

```toml
skills-sync = "python skills.py"
okf = { cmd = "pixi exec --spec \"okf-agent-memory>=0.5.0,<0.6\" -- okf", description = "Run the okf agent-memory CLI on knowledge/ (fetched with pixi exec; adds nothing to pixi.lock)." }
```

Then confirm the lock file is untouched:

```bash
pixi run okf version
git diff --exit-code origin/main -- pixi.lock && head -1 pixi.lock
```

Expected: `okf version 0.5.x (OKF v0.2 specification)`, then `version: 6`.

- [ ] **Step 4: Initialize the bundle and exclude it from prettier**

```bash
pixi run okf init knowledge
pixi run okf validate --strict --drift
```

Expected: `Initialized OKF v0.2 bundle in 'knowledge'`, then a report ending `Conformant.` with 0 errors and 0 warnings.

In `.pre-commit-config.yaml`, replace:

```yaml
        exclude: ^(docs/api/|readthedocs\.yaml|exports/plots/)
```

with:

```yaml
        exclude: ^(docs/api/|readthedocs\.yaml|exports/plots/|knowledge/) # okf owns knowledge/; prettier folds its frontmatter
```

- [ ] **Step 5: Port the `okf-memory` skill**

```bash
UPSTREAM="${TMPDIR:-/tmp}/ssec-project-template"
mkdir -p .agents/skills/okf-memory
git -C "$UPSTREAM" show fc00b39:.agents/skills/okf-memory/SKILL.md > .agents/skills/okf-memory/SKILL.md
```

Replace:

```markdown
Project memory is the OKF v0.2 bundle at `knowledge/` in the repository root.
Read it and write it only through the `okf` CLI, run as `pixi run okf` (the
binary from the pixi environment; there is no pixi task). Run it from the
repository root, where the bundle path defaults to `knowledge` and can be
omitted; from any other directory okf treats that directory as the bundle.
```

with:

```markdown
Project memory is the OKF v0.2 bundle at `knowledge/` in the repository root.
Read it and write it only through the `okf` CLI, run as `pixi run okf`: a Pixi
task that fetches `okf-agent-memory>=0.5.0,<0.6` with `pixi exec`, so it adds
nothing to `pixi.lock`. Pixi runs the task from the repository root, where the
bundle path defaults to `knowledge` and can be omitted.
```

Then add `!.agents/skills/okf-memory/` to `.gitignore` between the `merge-pr` and `push` lines, and add `"okf-memory"` to the `"local"` list in `skills.json` between `"merge-pr"` and `"push"`.

- [ ] **Step 6: Port the optional mkdocs + OKF rule and index it**

Add this row to the `AGENTS.md` Rule Index, as its last row:

```markdown
| [mkdocs-okf-knowledge-bundle.md](.agents/rules/mkdocs-okf-knowledge-bundle.md) | Rendering `knowledge/` with mkdocs (optional pattern), or debugging wikilink or frontmatter clashes |
```

```bash
git -C "$UPSTREAM" show fc00b39:.agents/rules/mkdocs-okf-knowledge-bundle.md > .agents/rules/mkdocs-okf-knowledge-bundle.md
```

Edit 1 — replace:

```markdown
This is **not part of the template's default setup.** It is an optional pattern
for projects that adopt both:
```

with:

```markdown
This is **not part of this repository's default setup**: the docs site does not
render `knowledge/`. It is an optional pattern for a project that adopts both:
```

Edit 2 — replace:

```markdown
simultaneously live data for OKF tooling and static-site input for mkdocs. It
adds two new dependencies (`mkdocs`, `mkdocs-material`) and is only worth adding
if the project actually wants a rendered, browsable view of its knowledge bundle
— read
[contribution-discipline.md](contribution-discipline.md#unnecessary-third-party-dependencies)
before wiring this into `pixi.toml`.
```

with:

```markdown
simultaneously live data for OKF tooling and static-site input for mkdocs. Here
the `docs` Pixi feature already provides `mkdocs` and `mkdocs-material`, so it
needs no new dependency, but it is only worth doing if the project actually
wants a rendered, browsable view of `knowledge/`.
```

Edit 3 — replace this block, from the heading through the closing fence of the TOML example:

````markdown
## Example Wiring (Add Only If Adopting)

```toml
[environments]
docs = { features = ["docs"], solve-group = "default" }

[feature.docs.dependencies]
mkdocs = "*"
mkdocs-material = "*"

[feature.docs.tasks]
docs-build = { cmd = "mkdocs build", description = "Build the knowledge-bundle docs site" }
docs-serve = { cmd = "mkdocs serve", description = "Serve the knowledge-bundle docs site locally" }
```
````

with:

```markdown
## Example Wiring (Add Only If Adopting)

This repository's `docs` environment and its `docs-build` and `docs-serve` tasks
already exist; only mkdocs configuration changes. The bundle lives at
`knowledge/`, outside `docs/`, so either expose it with a relative symlink
(`docs/knowledge -> ../knowledge`, the way `docs/` already exposes root files)
or build it with a separate configuration like this one:
```

Edit 4 — replace:

```markdown
- [contribution-discipline.md](contribution-discipline.md) — read before adding
  the `docs` feature to `pixi.toml`; new dependencies need justification.
```

with:

```markdown
- [contribution-discipline.md](contribution-discipline.md) — read before adding
  any dependency for this pattern; new dependencies need justification.
```

- [ ] **Step 7: Document memory in the rules and the `docs` skill**

Insert into `.agents/rules/pixi-environments.md`, directly after the `## GitHub CLI` section's paragraph and before `## Jupyter Notebooks`:

````markdown
## OKF Agent Memory

Project memory lives in the OKF bundle at `knowledge/`; the `okf-memory` skill
says how to read and write it. The `okf` CLI is not a Pixi dependency here: the
`okf` task runs it through `pixi exec`, which fetches
`okf-agent-memory>=0.5.0,<0.6` into a cached temporary environment, so
`pixi.lock` stays unchanged. Once every pinned pixi is upgraded (see Lock File
Compatibility), move it into a Pixi feature, as the SSEC template does.

```bash
pixi run okf version   # okf version 0.5.x (OKF v0.2 specification)
pixi run okf --help
```

````

In the same file's `## Lock File Compatibility (CRITICAL)` list, add a final bullet:

```markdown
- `tests/agent_harness/test_lockfile.py` fails when the lock-file format
  outgrows a pinned pixi.
```

In `.agents/skills/docs/SKILL.md`, insert a blank line and then this subsection directly after the last `### Technical Architecture` bullet (still inside step 3, before `4. **Place documentation correctly**`):

```markdown
   ### Decisions and Learnings

   - Record decisions, rejected alternatives, and non-obvious gotchas in project
     memory with the `okf-memory` skill, not in `docs/`. Link the concept to the
     relevant docs page when that helps.
```

In `.agents/rules/repository-map.md`, add this tree line directly after the `.claude/` lines:

```text
├── knowledge/             # OKF project memory, read and written with `pixi run okf` (okf-memory skill)
```

- [ ] **Step 8: Run the tests to verify they pass**

```bash
git add pixi.toml knowledge .agents .gitignore skills.json AGENTS.md .pre-commit-config.yaml tests/agent_harness
pixi run pytest tests/agent_harness -v
```

Expected: 34 passed.

- [ ] **Step 9: Exercise the skill end to end, then discard the practice concept**

```bash
pixi run okf create decisions/harness-smoke-test --type Decision --title "Harness smoke test" --desc "Temporary concept proving okf create and search work through the pixi task" --tags "harness" --body "Delete me." --actor claude-code:claude-opus-5-5
(cd src && pixi run okf search "smoke test" --limit 1)
pixi run okf validate --strict --drift
git restore --staged knowledge 2>/dev/null; rm -rf knowledge && pixi run okf init knowledge && git add knowledge
```

Expected: `Created concept 'decisions/harness-smoke-test.md'`, a search hit even though the command ran from `src/` (the task runs from the root), `Conformant.`, and finally a fresh, empty bundle staged again.

- [ ] **Step 10: Run the gate and commit**

```bash
pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
pixi run okf validate --strict --drift
git diff --exit-code origin/main -- pixi.lock
git commit -m "feat(memory): add OKF project memory through a pixi exec task" -m "Assisted-by: claude-code:claude-opus-5-5"
```

On merge to `main`, the `pixi.toml` change runs `docker-build.yml` and the staging deploy, plus a read-only production Pulumi preview, like any `src/` change. Say so in the PR description.

---

### Task 7: Give the devcontainer and Copilot the repository's agent toolchain

**Files:**
- Modify: `.devcontainer/Dockerfile` (full rewrite), `.devcontainer/devcontainer.json` (one feature)
- Create: `.devcontainer/install-agents.sh` (verbatim upstream, mode 100755)
- Modify: `.github/workflows/copilot-setup-steps.yml` (full rewrite)
- Modify: `tests/agent_harness/test_lockfile.py` (one test), `.agents/rules/repository-map.md` (tree lines)
- Create: `tests/agent_harness/test_agent_environments.py`

**Interfaces:**
- Consumes: `pixi_pins(root: Path) -> dict[str, tuple[int, int, int]]` from `test_lockfile.py` (Task 6, same module); fixture `repo_root`.
- Produces: one pixi version (0.63.2) across CI, Docker, the devcontainer, and Copilot.

- [ ] **Step 1: Write the failing tests**

Append to `tests/agent_harness/test_lockfile.py`:

```python
def test_every_pixi_pin_is_the_same_release(repo_root):
    pins = pixi_pins(repo_root)
    assert len(set(pins.values())) == 1, (
        "pin one pixi release everywhere, so no sanctioned environment writes a "
        f"lock file another cannot read: {sorted(pins.items())}"
    )
```

Create `tests/agent_harness/test_agent_environments.py`:

```python
"""The devcontainer and Copilot setup give agents the repository's toolchain."""

from __future__ import annotations

import json
import re
import subprocess

import yaml


def _copilot_workflow(repo_root):
    path = repo_root / ".github" / "workflows" / "copilot-setup-steps.yml"
    workflow = yaml.safe_load(path.read_text(encoding="utf-8"))
    return workflow, workflow["jobs"]["copilot-setup-steps"]["steps"]


def test_copilot_setup_pins_actions_by_commit_sha(repo_root):
    _, steps = _copilot_workflow(repo_root)
    uses = [step["uses"] for step in steps if "uses" in step]
    assert uses
    unpinned = [u for u in uses if not re.fullmatch(r"[\w.-]+/[\w.-]+@[0-9a-f]{40}", u)]
    assert not unpinned, unpinned


def test_copilot_setup_installs_the_locked_environment(repo_root):
    workflow, steps = _copilot_workflow(repo_root)
    assert workflow["permissions"] == {}
    setup = next(s for s in steps if s.get("uses", "").startswith("prefix-dev/setup-pixi@"))
    assert setup["with"]["locked"] is True
    assert any(step.get("run") == "pre-commit install-hooks" for step in steps)


def test_devcontainer_installs_agent_clis_and_gh(repo_root):
    dockerfile = (repo_root / ".devcontainer" / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY --chown=vscode:vscode .devcontainer/install-agents.sh" in dockerfile
    assert 'sha256sum -c -' in dockerfile, "verify the pixi download"
    config = json.loads((repo_root / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8"))
    assert "ghcr.io/devcontainers/features/github-cli:1" in config["features"]


def test_install_agents_script_is_executable_in_git(repo_root):
    staged = subprocess.run(
        ["git", "ls-files", "-s", ".devcontainer/install-agents.sh"],
        cwd=repo_root, capture_output=True, text=True, check=True,
    ).stdout
    assert staged.startswith("100755 "), staged or "install-agents.sh is not staged"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `pixi run pytest tests/agent_harness -v`
Expected: FAIL `test_every_pixi_pin_is_the_same_release` (0.55.0, 0.56.0, and 0.63.2 pinned), plus all four tests in `test_agent_environments.py`.

- [ ] **Step 3: Rewrite `.devcontainer/Dockerfile`**

Replace the entire file with the following. The checksums are the published SHA-256 sums of the v0.63.2 release assets; both tarballs hold a single top-level `pixi` binary.

```dockerfile
FROM mcr.microsoft.com/devcontainers/base:jammy

# Use bash for RUN so pipefail is supported.
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

# Keep in step with every other pixi pin (CI workflows, resources/docker/*.dockerfile,
# copilot-setup-steps.yml); tests/agent_harness/test_lockfile.py checks this.
ARG PIXI_VERSION=v0.63.2
ARG PIXI_SHA256_X86_64=b2a9e26bb6c80fe00618a02e7198dec222e1fbcec61e04c11b6e6538089ab100
ARG PIXI_SHA256_AARCH64=dbde6dbc2806602171e17305ce005e1aed519f2f2461a7cafd0093e92b7e7681

# Install pixi, verifying the download against the pinned SHA256 above.
RUN set -eu \
    && ARCH="$(uname -m)" \
    && case "${ARCH}" in \
        x86_64) PIXI_ARCH="x86_64"; PIXI_SHA256="${PIXI_SHA256_X86_64}" ;; \
        aarch64|arm64) PIXI_ARCH="aarch64"; PIXI_SHA256="${PIXI_SHA256_AARCH64}" ;; \
        *) echo "Unsupported architecture: ${ARCH}" >&2; exit 1 ;; \
       esac \
    && PIXI_ASSET="pixi-${PIXI_ARCH}-unknown-linux-musl.tar.gz" \
    && PIXI_BASE_URL="https://github.com/prefix-dev/pixi/releases/download/${PIXI_VERSION}" \
    && curl -fsSL --compressed -o /tmp/pixi.tar.gz "${PIXI_BASE_URL}/${PIXI_ASSET}" \
    && echo "${PIXI_SHA256}  /tmp/pixi.tar.gz" | sha256sum -c - \
    && tar -xzf /tmp/pixi.tar.gz -C /tmp pixi \
    && install -m 0755 /tmp/pixi /usr/local/bin/pixi \
    && rm -f /tmp/pixi /tmp/pixi.tar.gz \
    && pixi info

# set some user and workdir settings to work nicely with vscode
ENV VSCODE_HOME=/home/vscode \
    VSCODE_USER=vscode \
    SHELL=/bin/bash \
    PATH=/home/vscode/.local/bin:/home/vscode/.opencode/bin:${PATH}
USER ${VSCODE_USER}
WORKDIR ${VSCODE_HOME}

RUN echo 'eval "$(pixi completion -s bash)"' >> ${VSCODE_HOME}/.bashrc

# Pre-install the coding agent CLIs (Claude Code, Codex, Copilot CLI, OpenCode)
# so the devcontainer is ready on attach. The build context is the repository
# root (devcontainer.json sets "context": ".."), hence the .devcontainer/ prefix.
COPY --chown=vscode:vscode .devcontainer/install-agents.sh /tmp/install-agents.sh
RUN bash /tmp/install-agents.sh && rm -f /tmp/install-agents.sh
```

- [ ] **Step 4: Add the agent installer and the GitHub CLI**

```bash
UPSTREAM="${TMPDIR:-/tmp}/ssec-project-template"
git -C "$UPSTREAM" show fc00b39:.devcontainer/install-agents.sh > .devcontainer/install-agents.sh
chmod +x .devcontainer/install-agents.sh
git add .devcontainer/install-agents.sh
git ls-files -s .devcontainer/install-agents.sh
```

Expected: a line starting `100755`.

In `.devcontainer/devcontainer.json`, replace:

```json
    "ghcr.io/devcontainers/features/sshd:1": {
      "version": "latest"
    }
  },
```

with:

```json
    "ghcr.io/devcontainers/features/sshd:1": {
      "version": "latest"
    },
    "ghcr.io/devcontainers/features/github-cli:1": {}
  },
```

- [ ] **Step 5: Rewrite `.github/workflows/copilot-setup-steps.yml`**

The action SHAs below were checked against their tags (`actions/checkout` v7.0.1, `prefix-dev/setup-pixi` v0.10.2). Replace the entire file with:

```yaml
# Environment setup for the GitHub Copilot cloud coding agent.
#
# Copilot runs the `copilot-setup-steps` job below before it starts working on
# a task, so the agent lands in a repo where pixi is installed, the default
# environment is solved from pixi.lock, and the pre-commit hook environments
# are already warm. That makes the required quality gate
# (`pixi run pre-commit-all`) work without further setup.
#
# Copilot discovers AGENTS.md and the skills under .agents/skills/ on its own;
# nothing here needs to point at them.
#
# Constraints from GitHub: the job must be named exactly `copilot-setup-steps`,
# the file must live on the default branch, and only `steps`, `permissions`,
# `runs-on`, `services`, `snapshot`, and `timeout-minutes` are honored.

name: Copilot setup steps

on:
  workflow_dispatch:
  push:
    branches: [main]
    paths:
      - ".github/workflows/copilot-setup-steps.yml"
  pull_request:
    branches: [main]
    paths:
      - ".github/workflows/copilot-setup-steps.yml"

permissions: {}

jobs:
  copilot-setup-steps:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    permissions:
      contents: read

    steps:
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
        with:
          persist-credentials: false

      # Keep pixi-version in step with every other pixi pin; see
      # tests/agent_harness/test_lockfile.py.
      - name: Install pixi and the default environment
        uses: prefix-dev/setup-pixi@d3f436a425481402e6a95a1d1fc10331c708cd9e # v0.10.2
        with:
          pixi-version: v0.63.2
          cache: true
          locked: true
          activate-environment: true

      - name: Pre-warm pre-commit hook environments
        run: pre-commit install-hooks
```

- [ ] **Step 6: Record the environments in the repository map**

In `.agents/rules/repository-map.md`, add these tree lines directly after the `knowledge/` line:

```text
├── .devcontainer/         # Codespaces image: pixi (checksum-verified) + Claude Code, Codex, Copilot CLI, OpenCode, gh
├── .github/workflows/copilot-setup-steps.yml   # Copilot cloud agent setup: locked pixi env, warm pre-commit hooks
```

- [ ] **Step 7: Run the tests to verify they pass**

```bash
git add .devcontainer .github/workflows/copilot-setup-steps.yml .agents/rules/repository-map.md tests/agent_harness
pixi run pytest tests/agent_harness -v
```

Expected: 39 passed.

- [ ] **Step 8 (optional; needs Docker and about 10 minutes): Build the devcontainer image**

Run: `docker build -f .devcontainer/Dockerfile -t ca-biositing-devcontainer-check .`
Expected: the build succeeds; its log shows `/tmp/pixi.tar.gz: OK` and the four agents' versions under `==> [install-agents] Installed versions`. Remove the image afterwards with `docker image rm ca-biositing-devcontainer-check`.

- [ ] **Step 9: Run the gate and commit**

```bash
pixi run pre-commit run --files $(git diff --cached --name-only --diff-filter=d) || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
git diff --exit-code origin/main -- pixi.lock
git commit -m "build(agents): agent-ready devcontainer and Copilot setup on the CI pixi" -m "Assisted-by: claude-code:claude-opus-5-5"
```

The pull request runs `copilot-setup-steps.yml` itself (it triggers on its own path). Its success is the real check of Step 5.

---

### Task 8: Describe the harness in the README and verify the whole branch

**Files:**
- Modify: `README.md` (new `## AI Agents` section before `## Contributing`)
- Create: `tests/agent_harness/test_readme.py`

**Interfaces:**
- Consumes: everything above.
- Produces: the human-facing summary of the harness.

- [ ] **Step 1: Write the failing test**

Create `tests/agent_harness/test_readme.py`:

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `pixi run pytest tests/agent_harness/test_readme.py -v`
Expected: FAIL at the `## AI Agents` assertion.

- [ ] **Step 3: Add the README section**

In `README.md`, insert directly above `## Contributing`:

```markdown
## AI Agents

The repository is set up for AI coding agents such as Claude Code, Codex,
Copilot, Cursor, and Gemini CLI, following the
[UW SSEC project template](https://github.com/uw-ssec/project-template):

- `AGENTS.md` is the agent entry point. It lists the non-negotiables and points
  to the rules in `.agents/rules/`, which agents load on demand. Package
  directories carry their own `AGENTS.md`, and every `AGENTS.md` has a
  `CLAUDE.md` beside it that imports it for Claude Code.
- `.agents/skills/` holds project skills such as `commit`, `push`, `create-pr`,
  `merge-pr`, `docs`, and `okf-memory`; `.claude/skills` links there so Claude
  Code finds them. `pixi run skills-sync` adds the third-party skills listed in
  `skills.json`.
- `knowledge/` is project memory: an OKF bundle that agents read and write with
  `pixi run okf`, as the `okf-memory` skill describes.
- The devcontainer installs Claude Code, Codex, Copilot CLI, and OpenCode, and
  `.github/workflows/copilot-setup-steps.yml` prepares the Copilot cloud agent.

```

The section links only to an external URL, because `docs/README.md` is a symlink to this file and relative links to harness paths would break on the docs site.

- [ ] **Step 4: Run the test to verify it passes**

Run: `pixi run pytest tests/agent_harness -v`
Expected: 40 passed.

- [ ] **Step 5: Verify the whole branch**

```bash
git add README.md tests/agent_harness/test_readme.py
pixi run pre-commit run --files README.md tests/agent_harness/test_readme.py || true
git add -u
pixi run pre-commit-all
pixi run pytest tests/agent_harness -v
pixi run okf validate --strict --drift
pixi run -e docs docs-build 2>&1 | grep -E "ERROR" || echo "docs build: no errors"
git diff --exit-code origin/main -- pixi.lock && head -1 pixi.lock
git diff --stat origin/main...HEAD -- src/ | grep -v -E "(AGENTS|CLAUDE)\.md" || true
```

Expected: every hook "Passed" or "Skipped"; 40 passed; `Conformant.`; `docs build: no errors`; `version: 6`; and the last command prints only the `files changed` summary line, meaning nothing under `src/` changed except `AGENTS.md`/`CLAUDE.md` files.

- [ ] **Step 6: Final Claude Code smoke test**

In a fresh `claude` session at the repository root:

1. `/memory`: `CLAUDE.md` and `AGENTS.md` are loaded.
2. `/skills`: the eight project skills (`clean-branches`, `commit`, `create-issue`, `create-pr`, `docs`, `merge-pr`, `okf-memory`, `push`) are listed.
3. Ask: "Which rule do you load before writing an Alembic migration?" Expected: an answer naming `.agents/rules/schema-and-migrations.md`.

- [ ] **Step 7: Commit**

```bash
git commit -m "docs(readme): describe the agent harness" -m "Assisted-by: claude-code:claude-opus-5-5"
```

Then use superpowers:finishing-a-development-branch. Fill in every section of the new PR template, including the AI disclosure and the Author verification, and split the branch into the PRs from **Suggested PR Split**.

## Follow-ups for Your Human Partner (outside this plan)

- Agree the AI policy (D5) with the team before PR B merges, then create the `ai-assisted` label (Task 4, Step 8).
- Open an issue to upgrade every pinned pixi to one release ≥0.68.0, migrate `pixi.lock` to v7, and then move `okf-agent-memory` and `gh` into Pixi features as upstream does. The v6→v7 diff is format-only: the 0.81.0 re-lock changed no package versions.
- Ask the author of #442 to commit `database-query` and `data-visualization` with the new allowlist, or to remove them from `skills.json`.
- Consider upstreaming the worktree-safe `merge-pr` and the per-`AGENTS.md` `CLAUDE.md` pattern to `uw-ssec/project-template`.

<!-- prettier-ignore-end -->
