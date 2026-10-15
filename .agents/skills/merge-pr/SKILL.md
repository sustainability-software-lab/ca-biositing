---
name: merge-pr
description:
  Use when a pull request is approved and ready to land, or when review has
  finished and the branch needs cleaning up afterward.
---

# Merge PR

Merge a pull request and clean up branches.

## Arguments

Optional: a PR number or URL. Defaults to the current branch's PR.

## Instructions

1. Determine the PR:

   - If a PR number or URL was passed, use it
   - If not, find the PR for the current branch:
     `gh pr view --json number,title,state,headRefName`

2. Check PR status:

   - `gh pr view <number> --json state,mergeable,mergeStateStatus,statusCheckRollup,title,headRefName`
   - If checks are failing, warn the user and ask whether to proceed
   - If there are merge conflicts, tell the user and stop

3. Check for local changes and for a linked worktree:

   - `git status`
   - Compare `git rev-parse --git-dir` with `git rev-parse --git-common-dir`. If
     they differ, this checkout is a linked worktree, and `main` is usually
     checked out in the main worktree.
   - If there are uncommitted changes, set them aside under a unique name. The
     stash stack is shared by every worktree of the repository, so never use a
     bare stash: run `git stash push -u -m "merge-pr-<number>"` and note the
     entry's SHA from `git stash list --format='%H %gs'`.

4. Merge the PR. Use `--squash` by default (consistent with this repo's
   history).

   - In the main checkout:

     ```bash
     gh pr merge <number> --squash --delete-branch
     ```

   - In a linked worktree, leave out `--delete-branch`, because it tries to
     check out `main` here and fails while another worktree has it. Delete the
     remote branch yourself:

     ```bash
     gh pr merge <number> --squash
     git push origin --delete <branch-name>
     ```

5. Clean up locally:

   - In the main checkout:
     - Switch to main if not already: `git checkout main`
     - Pull the merged changes: `git pull origin main`
     - Prune stale remote refs: `git fetch --prune`
     - Delete the local branch if it still exists: `git branch -d <branch-name>`
   - In a linked worktree:
     - Prune stale remote refs: `git fetch --prune`
     - Tell the user the worktree can now be removed from the main checkout with
       `git worktree remove <path>`, which also frees the branch for deletion.
       Do not check out `main` here.
   - If you stashed changes, restore them with `git stash apply <sha>`. Once
     they apply cleanly, find the entry's current `stash@{n}` in
     `git stash list` and drop it with `git stash drop stash@{n}`.

6. Verify cleanup:

   - `git branch -a | grep <branch-name>` to confirm the branch is gone. In a
     linked worktree the local branch remains until the worktree is removed.

7. Confirm: "PR #N merged into main. Branch `<name>` deleted locally and
   remotely." From a linked worktree: "PR #N merged into main. Branch `<name>`
   deleted remotely; remove the worktree to delete it locally."

## Rules

- Default merge strategy is `--squash` (produces clean linear history)
- If user asks for a merge commit, use `--merge` instead
- If user asks for rebase, use `--rebase` instead
- NEVER force-delete branches (`-D`), use `-d` which is safe
- Always restore stashed changes after merge, by SHA. Never pop a stash by
  position: another worktree's session may own the top entry
- If the merge fails, do NOT retry destructively — report the error
