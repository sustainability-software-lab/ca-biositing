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
