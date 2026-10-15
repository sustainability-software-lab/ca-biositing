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

   - `gh pr view <number> --json state,mergeable,mergeStateStatus,statusCheckRollup,title,headRefName,isCrossRepository`
   - If checks are failing, warn the user and ask whether to proceed
   - If there are merge conflicts, tell the user and stop
   - If `isCrossRepository` is true, the head branch lives in a fork, not in
     `origin`: skip every remote-branch deletion below

3. Check for local changes and for a linked worktree:

   - `git status`
   - Compare `git rev-parse --git-dir` with `git rev-parse --git-common-dir`. If
     they differ, this checkout is a linked worktree, and `main` is usually
     checked out in the main worktree.
   - If there are uncommitted changes, stop and ask the user to commit them or
     set them aside first. Do not stash them yourself: the PR may belong to a
     different branch than the one checked out, so restoring the work after the
     switch to `main` would land it on the wrong branch, and the stash stack is
     shared by every worktree, so another session can renumber or drop entries
     between your commands.

4. Merge the PR. Use `--squash` by default (consistent with this repo's
   history).

   - In the main checkout:

     ```bash
     gh pr merge <number> --squash --delete-branch
     ```

   - In a linked worktree, leave out `--delete-branch`, because it tries to
     check out `main` here and fails while another worktree has it. Delete the
     remote branch yourself, unless the PR is from a fork:

     ```bash
     gh pr merge <number> --squash
     git push origin --delete <branch-name>  # same-repository PRs only
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

6. Verify cleanup:

   - `git branch -a | grep <branch-name>` to confirm the branch is gone. In a
     linked worktree the local branch remains until the worktree is removed.

7. Confirm, naming only the cleanup that actually happened: "PR #N merged into
   main. Branch `<name>` deleted locally and remotely." From a linked worktree:
   "PR #N merged into main. Branch `<name>` deleted remotely; remove the
   worktree to delete it locally." For a fork PR, say the remote branch was left
   in the contributor's fork.

## Rules

- Default merge strategy is `--squash` (produces clean linear history)
- If user asks for a merge commit, use `--merge` instead
- If user asks for rebase, use `--rebase` instead
- NEVER force-delete branches (`-D`), use `-d` which is safe
- Never stash on the user's behalf; stop on uncommitted changes instead
- Never delete a remote branch for a fork PR: `origin` does not own it
- If the merge fails, do NOT retry destructively — report the error
