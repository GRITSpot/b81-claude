## What this PR adds

<!-- One-line summary. -->

## Plugin checklist (skip if not adding/modifying a plugin)

- [ ] Plugin name is kebab-case and follows `<verb-or-domain>` convention (e.g. `code-review`, `deploy-helper`)
- [ ] `description` in `marketplace.json` is ≤80 chars and clear without context
- [ ] `category` set (`engineering`, `ops`, `product`, or new — note the choice)
- [ ] Plugin folder contains a valid `.claude-plugin/plugin.json`
- [ ] `marketplace.json` updated to reference the new folder
- [ ] Locally tested: `python3 scripts/validate_marketplace.py .` returns OK
- [ ] Locally installed in Claude Code via `/plugin install <name>@b81-claude` from a worktree of this branch

## Notes for reviewer

<!-- Anything specific to flag? Breaking changes? Migration steps? -->
