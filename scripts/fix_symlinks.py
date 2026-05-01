#!/usr/bin/env python3
"""
Script to fix broken symlinks in the ca-biositing repository.
This is often caused by Windows git clients not handling symlinks correctly.
"""

import os
from pathlib import Path

# Mapping of symlink path -> target path
SYMLINKS = {
    "datamodels": "src/ca_biositing/datamodels",
    "pipeline": "src/ca_biositing/pipeline",
    "webservice": "src/ca_biositing/webservice",
    "docs/CHANGELOG.md": "../CHANGELOG.md",
    "docs/CODE_OF_CONDUCT.md": "../CODE_OF_CONDUCT.md",
    "docs/CONTRIBUTING.md": "../CONTRIBUTING.md",
    "docs/LICENSE": "../LICENSE",
    "docs/README.md": "../README.md",
    "docs/SECURITY.md": "../SECURITY.md",
    "docs/deployment/README.md": "../../deployment/README.md",
    "docs/resources/README.md": "../../resources/README.md",
    "docs/datamodels/README.md": "../../src/ca_biositing/datamodels/README.md",
    "docs/pipeline/README.md": "../../src/ca_biositing/pipeline/README.md",
    "docs/webservice/README.md": "../../src/ca_biositing/webservice/README.md",
}

def fix_symlinks():
    repo_root = Path(__file__).parent.parent.resolve()
    os.chdir(repo_root)

    print(f"Checking symlinks in {repo_root}...")

    for link_path_str, target_path_str in SYMLINKS.items():
        link_path = Path(link_path_str)
        target_path = Path(target_path_str)

        # Check if it's already a valid symlink
        if link_path.is_symlink():
            current_target = os.readlink(link_path)
            if current_target == target_path_str:
                print(f"✅ {link_path_str} is already correct.")
                continue
            else:
                print(f"⚠️  {link_path_str} points to {current_target}, fixing...")
                link_path.unlink()
        elif link_path.exists():
            # If it exists but is not a symlink, it might be a text file containing the path (Windows behavior)
            print(f"🔄 {link_path_str} exists but is not a symlink, replacing...")
            link_path.unlink()

        # Ensure parent directory exists
        link_path.parent.mkdir(parents=True, exist_ok=True)

        # Create the symlink
        try:
            os.symlink(target_path_str, link_path)
            print(f"✨ Restored symlink: {link_path_str} -> {target_path_str}")
        except Exception as e:
            print(f"❌ Failed to create symlink {link_path_str}: {e}")

if __name__ == "__main__":
    fix_symlinks()
