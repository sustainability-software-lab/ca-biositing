---
name: create-pr
description:
  Use when a branch's work is complete and ready to be proposed for review
  against main, or when the user asks to open a pull request.
---

# Create PR

Create a pull request for the current branch.

## Instructions

1. Run these commands in parallel to understand the current state:

   - `git status` (never use `-uall`)
   - `git diff --stat` (check for uncommitted changes)
   - `git branch --show-current` (current branch)
   - `git log --oneline main..HEAD` (all commits being PR'd)
   - `git diff main...HEAD --stat` (full diff summary against main)

2. If there are uncommitted changes, ask whether to commit first.

3. If the branch hasn't been pushed, push with `git push -u origin <branch>`.

4. Analyze ALL commits in the branch (not just the latest) to draft:

   - **Title**: Use conventional commit format: `type(scope): short description`
     (under 70 chars)
   - **Body**: Start from `.github/pull_request_template.md` and fill in every
     section with real, specific answers, including "How to test"

5. On an AI-assisted PR, the "Author verification" section must come from the
   human author: ask them what they personally verified, what they are less
   certain about, and whether they can tick the two ownership boxes. Do not
   answer those on their behalf.

6. Complete the checklist in `.agents/rules/contribution-discipline.md`: show
   the user the complete diff and the drafted body, and get explicit approval
   before submitting.

7. Write the filled-in body to a temporary file and create the PR:

```bash
gh pr create --title "type(scope): description" --body-file <path-to-body.md>
```

8. If there's a related issue, put `Resolves #N` in the "Related Issues"
   section.
9. Return the PR URL to the user.

## Title Convention

Use the same conventional commit types as the `commit` skill:

- `feat(scope):` for new features
- `fix(scope):` for bug fixes
- `refactor(scope):` for restructuring
- `docs(scope):` for documentation
- `chore(scope):` for maintenance

## Rules

- Keep title under 70 characters
- Always fill the template's "How to test" section with specific steps
- Never bypass the template with a hand-written `--body`
- Never create a PR from `main` to `main`
- If the branch name contains a hint (e.g., `feat/`, `fix/`), use that as the
  commit type
- On an AI-assisted PR, disclose it: fill the "AI assistance disclosure" section
  of `.github/pull_request_template.md`, and/or apply the `ai-assisted` label.
  AI-assisted commits carry an `Assisted-by: <harness>:<model>` trailer and
  never an agent-added `Signed-off-by:` — see the `commit` skill for the format
- NEVER add "Generated with" or similar marketing lines to PR titles or bodies.
  This is attribution, not promotion
- If the PR is large or complex, consider breaking it into smaller PRs with
  focused scope and clear dependencies
