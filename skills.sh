#!/bin/bash

# Ensure we are in the project root
cd "$(dirname "$0")"

if [ ! -f "skills.json" ]; then
    echo "Error: skills.json not found."
    exit 1
fi

# Parse skills.json and install each source
# Use a separate file descriptor to prevent stdin consumption by sub-commands
while read -r source <&3; do
    registry=$(echo "$source" | jq -r '.registry')

    # Check if there are specific skills listed
    has_skills=$(echo "$source" | jq -r 'has("skills")')

    if [ "$has_skills" == "true" ]; then
        # Install specific skills
        echo "$source" | jq -r '.skills[]' | while read -r skill; do
            echo "--- Installing specific skill: $skill from $registry ---"
            # Redirect stdin from /dev/null to ensure the loop continues
            pixi run npx skills add "$registry" --skill "$skill" -y < /dev/null
        done
    else
        # Install all skills from registry
        echo "--- Installing all skills from registry: $registry ---"
        pixi run npx skills add "$registry" -y < /dev/null
    fi
done 3< <(jq -c '.sources[]' skills.json)

echo "--- Updating all installed skills to latest versions ---"
pixi run npx skills update < /dev/null

echo "--- Skill synchronization complete ---"
