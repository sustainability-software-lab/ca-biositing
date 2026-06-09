#!/bin/bash

# Ensure we are in the project root
cd "$(dirname "$0")" || exit 1

if [ ! -f "skills.json" ]; then
    echo "Error: skills.json not found."
    exit 1
fi

# Parse skills.json and install each source
# Use a temp file instead of process substitution for portability (no bash 4+ required)
tmp_sources=$(mktemp)
jq -c '.sources[]' skills.json > "$tmp_sources"

while IFS= read -r source; do
    registry=$(echo "$source" | jq -r '.registry')

    # Check if there are specific skills listed
    has_skills=$(echo "$source" | jq -r 'has("skills")')

    if [ "$has_skills" = "true" ]; then
        # Install specific skills
        tmp_skills=$(mktemp)
        echo "$source" | jq -r '.skills[]' > "$tmp_skills"
        while IFS= read -r skill; do
            echo "--- Installing specific skill: $skill from $registry ---"
            npx skills add "$registry" --skill "$skill" -y < /dev/null
        done < "$tmp_skills"
        rm -f "$tmp_skills"
    else
        # Install all skills from registry
        echo "--- Installing all skills from registry: $registry ---"
        npx skills add "$registry" -y < /dev/null
    fi
done < "$tmp_sources"

rm -f "$tmp_sources"

echo "--- Updating all installed skills to latest versions ---"
npx skills update < /dev/null

echo "--- Skill synchronization complete ---"
