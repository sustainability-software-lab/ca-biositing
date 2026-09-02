"""Register a stable Jupyter kernel for the active Pixi environment."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ipykernel.kernelspec import install


DEFAULT_KERNEL_NAME = "ca-biositing-pixi"
DEFAULT_DISPLAY_NAME = "ca-biositing (Pixi)"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Install a Jupyter kernelspec that launches the current Pixi "
            "Python executable directly."
        )
    )
    parser.add_argument("--name", default=DEFAULT_KERNEL_NAME)
    parser.add_argument("--display-name", default=DEFAULT_DISPLAY_NAME)
    parser.add_argument(
        "--prefix",
        help=(
            "Install into a Jupyter prefix instead of the current user's "
            "Jupyter data directory."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    ipython_dir = repo_root / ".pixi" / "ipython"
    ipython_dir.mkdir(parents=True, exist_ok=True)

    kernelspec_path = install(
        user=args.prefix is None,
        prefix=args.prefix,
        kernel_name=args.name,
        display_name=args.display_name,
        env={
            "CA_BIOSITING_PROJECT_ROOT": str(repo_root),
            "IPYTHONDIR": str(ipython_dir),
        },
        frozen_modules=False,
    )

    print(f"Installed kernel: {args.display_name}")
    print(f"Kernel name: {args.name}")
    print(f"Python executable: {sys.executable}")
    print(f"Kernelspec path: {kernelspec_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
