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
