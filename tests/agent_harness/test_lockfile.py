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


def test_every_pixi_pin_is_the_same_release(repo_root):
    pins = pixi_pins(repo_root)
    assert len(set(pins.values())) == 1, (
        "pin one pixi release everywhere, so no sanctioned environment writes a "
        f"lock file another cannot read: {sorted(pins.items())}"
    )
