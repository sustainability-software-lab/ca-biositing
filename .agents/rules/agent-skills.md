# Agent Skills

**Load when:** adding, editing, or syncing an agent skill, editing
`skills.json`, or a skill is missing or behaving unexpectedly.

## Two Kinds of Skills

| Kind                                                                                                 | Lives in                                                      | Tracked in git                   | Declared in                                                 |
| ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- | -------------------------------- | ----------------------------------------------------------- |
| Project skills (`commit`, `push`, `create-pr`, `merge-pr`, `create-issue`, `clean-branches`, `docs`) | `.agents/skills/<name>/SKILL.md`                              | Yes, allowlisted in `.gitignore` | The `"local"` registry in `skills.json`                     |
| Third-party skills (`find-skills`, `github-issues`, `web-design-guidelines`, ...)                    | `.agents/skills/<name>/`, installed by `pixi run skills-sync` | No, ignored                      | Registries in `skills.json`; versions in `skills-lock.json` |

Every harness finds both kinds in one place. Codex, Copilot, Cursor, and
OpenCode read `.agents/skills/` natively. Claude Code reads `.claude/skills/`,
which is a committed symlink to `../.agents/skills`.

## Add a Project Skill

1. Create `.agents/skills/<name>/SKILL.md`. Its frontmatter holds only `name` —
   the directory name: lowercase letters, digits, and hyphens, at most 64
   characters — and `description`, at most 1024 characters, starting "Use when
   ...". Other frontmatter keys are Claude Code-specific and break portability.
2. Add `!.agents/skills/<name>/` to the "Agents Braindump" block of
   `.gitignore`. Without it, git silently ignores the new skill.
3. Add `<name>` to the `"local"` registry's `skills` list in `skills.json`.
4. Run `pixi run pytest tests/agent_harness -v`.

## Add or Update a Third-Party Skill

1. Add the registry, and optionally a `skills` filter, to `skills.json`.
2. Run `pixi run skills-sync`. It runs `npx skills add <registry> -y` for each
   source, then `npx skills update`.
3. Commit `skills.json` and `skills-lock.json` only; the installed skill
   directories stay ignored.

## Name Collisions

`skills-sync` installs a skill by deleting `.agents/skills/<name>/` and copying
the new one in, so a registry skill that shares a project skill's name
overwrites the committed one. Registries without a `skills` filter, such as
`vercel-labs/agent-skills`, install everything they publish. Git shows the
overwritten files as modified: restore them with
`git restore .agents/skills/<name>` and filter that skill out of `skills.json`.
`tests/agent_harness/test_skills.py` fails when `skills-lock.json` names a
project skill.

## Windows

`.claude/skills` is a symlink. On Windows, git checks a symlink out as a plain
text file unless Developer Mode is on and `core.symlinks` is enabled, and Claude
Code then finds no project skills. Enable Developer Mode, run
`git config core.symlinks true`, then `git checkout -- .claude/skills`.

## Verify

- In Claude Code, `/skills` lists the project skills.
- `claude plugin validate .agents/skills` checks their frontmatter. Point it at
  `.agents/skills`: the validator does not follow the `.claude/skills` symlink.
- `pixi run pytest tests/agent_harness -v` checks frontmatter, the symlink, the
  ignore rules, `skills.json`, and collisions.
