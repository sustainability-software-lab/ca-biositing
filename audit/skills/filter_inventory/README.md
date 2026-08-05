# filter-inventory skill

Inventories every rule in the BioCirv codebase that decides whether a record
reaches stored or user-facing outputs, and publishes it as a reviewable table.

**This directory is the canonical, git-tracked copy.** Edit `SKILL.md` here,
commit it, and everyone gets the change. Do not edit copies under `.claude/`
or `.agents/` — both are gitignored (`.gitignore:76-77`), so edits there reach
nobody and are silently overwritten on the next sync.

```
audit/skills/filter_inventory/     <- canonical, tracked, edit here
├── SKILL.md                       the skill itself
├── README.md                      this file
└── scripts/sync_skill.py          installs it into .claude/ for Claude Code

audit/filter_inventory/            <- the deliverables it produces
├── filter-inventory-report-N.md   narrative report, N increments per audit
├── build_inventory.py             source of truth for the rows
├── filter-inventory.csv           generated (gitignored: global *.csv rule)
└── push_to_sheet.py               publishes to the shared Google Sheet
```

## Using it with Claude Code

Claude Code only discovers skills under `.claude/skills/<name>/SKILL.md`, which
cannot be committed. Generate your local copy once:

```bash
pixi run -e auditor python audit/skills/filter_inventory/scripts/sync_skill.py --apply
```

Then ask for a filter audit in plain language — "where are we filtering data",
"why isn't resource X in the portal", "update the filter inventory" — and the
skill triggers on its own.

**After every `git pull`,** check whether a colleague changed the skill:

```bash
pixi run -e auditor python audit/skills/filter_inventory/scripts/sync_skill.py --check
```

Exit 0 means in sync. Exit 1 reports which direction drifted:

- **upstream** — the tracked file changed and your copy is stale. Run `--apply`.
- **local** — someone edited the generated `.claude` copy directly. That edit is
  gitignored and exists nowhere else. Port it into `SKILL.md` here *before*
  running `--apply`, or it is lost.

The generated copy carries the check as its own first instruction, so an agent
following the skill re-verifies currency before acting on possibly-superseded
guidance. That is a backstop, not a substitute for running `--check` yourself
after a pull.

## Using it with other agent tools

`SKILL.md` is a plain markdown file with YAML frontmatter and no tool-specific
syntax. Any agent that reads skill files can use it directly at its canonical
path. For the `.agents/` convention driven by `skills.json`, note that `"local"`
registry entries are declarative — `skills.py` skips installing them, so the
tracked path is the install path.

## Modes

**Full inventory** — no prior inventory exists, or scope changed enough to
restart. The complete workflow in `SKILL.md`.

**Delta re-audit** — the common case. An inventory already exists, so this is
reconciliation, not a rescan: match by rule ID, preserve the reviewer's
`Priority` / `Review status` / `Reviewer notes`, and never delete a row for a
rule that disappeared — mark it removed instead. A silently vanished rule looks
exactly like one the audit failed to find.

Rule IDs (`F-01`, `F-02`, …) are permanent. Reviewer judgements are anchored to
them; renumbering destroys that work.

## Reviewer workflow

Three columns in the Google Sheet belong to humans and are never written by the
build: `Priority`, `Review status`, `Reviewer notes`. `push_to_sheet.py` reads
them off the live sheet before clearing it and re-applies them matched by ID, so
rows can be reordered, added or removed without scrambling anyone's edits. If a
rated rule no longer exists, the push names it in the output rather than
dropping it quietly.

Track remediation in `Review status` rather than re-running the full audit —
that is what the column is for.

## Dependencies

`sync_skill.py` is stdlib-only and runs under any Python. The inventory scripts
need `gspread` (present in the `auditor` pixi env) and a service-account
`credentials.json` at the repo root with Editor access to the target sheet.

Note that `python` is not on PATH in some shells here; prefer
`pixi run -e auditor python`.
