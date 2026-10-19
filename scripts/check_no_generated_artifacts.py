#!/usr/bin/env python3
"""Pre-commit and CI guard forbidding generated dashboard/audit artifacts in git.

Checks both filenames passed via CLI arguments and tracked files in the git
index (`git ls-files`) against the forbidden generated-artifact paths documented
in `.agents/rules/generated-artifacts.md`.
"""

from __future__ import annotations

from pathlib import Path, PurePosixPath
import subprocess
import sys


def _normalize_rel_path(raw_path: str, repo_root: Path) -> str:
    """Normalize a raw path string into a repository-relative POSIX path."""
    path = Path(raw_path)
    if path.is_absolute():
        try:
            path = path.resolve().relative_to(repo_root.resolve())
        except ValueError:
            return path.as_posix()
    return PurePosixPath(path.as_posix()).as_posix().lstrip("./")


def is_forbidden_generated_artifact(rel_posix: str) -> str | None:
    """Return the matching forbidden pattern if `rel_posix` is a generated artifact."""
    pure = PurePosixPath(rel_posix)
    parts = pure.parts
    if len(parts) >= 2 and parts[:2] == ("exports", "plots"):
        return "exports/plots/**"
    if rel_posix == "data/insights/resource_ai_insights.json":
        return "data/insights/resource_ai_insights.json"
    if (
        len(parts) == 4
        and parts[:3] == ("audit", "output", "env_fingerprints")
        and parts[3].endswith(".json")
    ):
        return "audit/output/env_fingerprints/*.json"
    if rel_posix == "audit/output/drift_report.md":
        return "audit/output/drift_report.md"
    return None


def _git_tracked_files(repo_root: Path) -> list[str]:
    """Return tracked files from `git ls-files` if git index is accessible."""
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return []
    return [line.strip() for line in proc.stdout.splitlines() if line.strip()]


def main(argv: list[str] | None = None) -> int:
    """Entry point for the generated-artifact pre-commit and CI check."""
    args = sys.argv[1:] if argv is None else argv
    repo_root = Path(__file__).resolve().parents[1]

    candidates: set[str] = set()
    for raw in args:
        norm = _normalize_rel_path(raw, repo_root)
        if norm:
            candidates.add(norm)

    for tracked in _git_tracked_files(repo_root):
        norm = _normalize_rel_path(tracked, repo_root)
        if norm:
            candidates.add(norm)

    violations: list[tuple[str, str]] = []
    for candidate in sorted(candidates):
        matched_rule = is_forbidden_generated_artifact(candidate)
        if matched_rule is not None:
            violations.append((candidate, matched_rule))

    if violations:
        print(
            "ERROR: Generated HTML/JSON/MD artifacts must not be tracked in git:",
            file=sys.stderr,
        )
        for path_str, pattern in violations:
            print(f"  - {path_str} (matches forbidden pattern `{pattern}`)", file=sys.stderr)
        print(
            "\nTo fix, untrack the file(s) from the git index:\n"
            "  git rm --cached <file>\n"
            "See `.agents/rules/generated-artifacts.md` for the GCS artifact publishing workflow.",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
