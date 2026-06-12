#!/bin/bash

cat <<'EOF'
The skills.sh script has been removed in favor of the cross-platform Python
implementation. Please run one of the following commands instead:

    python skills.py
    pixi run skills-sync

Refer to AGENTS.md for additional context.
EOF

exit 1
