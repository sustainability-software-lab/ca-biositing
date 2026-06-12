#!/usr/bin/env python3
"""
skills.py - Cross-platform skill synchronization script.

Reads skills.json and installs/updates agent skills using the `npx skills` CLI.
Replaces skills.sh for portability across macOS, Linux, and Windows.
"""

import json
import subprocess
import sys
from pathlib import Path

# On Windows, npx/npm are .cmd files and require shell=True to be found.
_SHELL = sys.platform == "win32"


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command, streaming output to stdout/stderr."""
    print(f"$ {' '.join(cmd)}", flush=True)
    result = subprocess.run(cmd, check=False, shell=_SHELL)
    if check and result.returncode != 0:
        print(
            f"Warning: command exited with code {result.returncode}: {' '.join(cmd)}",
            file=sys.stderr,
            flush=True,
        )
    return result


def main() -> int:
    root = Path(__file__).parent
    skills_json = root / "skills.json"

    if not skills_json.exists():
        print("Error: skills.json not found.", file=sys.stderr)
        return 1

    manifest = json.loads(skills_json.read_text(encoding="utf-8"))
    sources = manifest.get("sources", [])

    for source in sources:
        registry = source["registry"]
        skills = source.get("skills")

        if skills:
            for skill in skills:
                print(f"--- Installing specific skill: {skill} from {registry} ---", flush=True)
                run(["npx", "skills", "add", registry, "--skill", skill, "-y"])
        else:
            print(f"--- Installing all skills from registry: {registry} ---", flush=True)
            run(["npx", "skills", "add", registry, "-y"])

    print("--- Updating all installed skills to latest versions ---", flush=True)
    run(["npx", "skills", "update"])

    print("--- Skill synchronization complete ---", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
