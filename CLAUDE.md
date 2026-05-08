# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

`b81-claude` is BEAT81's internal [Claude Code plugin marketplace](https://docs.anthropic.com/en/docs/claude-code/plugins) — a catalog (`.claude-plugin/marketplace.json`) plus the plugin folders it references under `plugins/`. There is no application code; the only Python here is a structural validator that enforces the catalog's invariants.

End users add the marketplace once with `/plugin marketplace add GRITSpot/b81-claude`, then install individual plugins via `/plugin install <name>@b81-claude`. Claude Code's native `/plugin` UI handles browsing, enable/disable, and removal.

## Commands

Both commands run from the repo root and are exactly what CI runs (`.github/workflows/validate.yml`):

```bash
python3 scripts/validate_marketplace.py .          # structural validator
python3 -m unittest discover tests -v              # validator's unit tests
```

Run a single test:

```bash
python3 -m unittest tests.test_validate_marketplace.TestValidator.test_duplicate_name -v
```

There is no build step, no linter config, and no package manager — the validator uses only the standard library.

## Architecture

**Single source of truth: `.claude-plugin/marketplace.json`.** Every plugin must have an entry here; the catalog is what Claude Code reads when adding the marketplace. A plugin folder existing on disk is not enough — if it isn't listed here, the orphan check in the validator will fail CI.

**Plugin layout.** Each plugin lives at `plugins/<name>/` and must contain `.claude-plugin/plugin.json`. The catalog entry's `source.path` points at the folder; the validator resolves that path and confirms `plugin.json` exists and parses.

**Validator invariants** (`scripts/validate_marketplace.py`). These are the rules CI enforces — keep them in mind when editing the catalog or adding plugins:
- `marketplace.json` parses as JSON and `plugins` is a list
- Each plugin has a `name` (no duplicates) and a `source` object with a non-empty `path`
- Each `source.path` resolves to an existing directory containing a parseable `.claude-plugin/plugin.json`
- `description` is ≤ 80 characters (the `/plugin` UI truncates beyond that)
- Every folder under `plugins/` is referenced by some catalog entry (no orphans)

**Test fixtures.** `tests/fixtures/<case>/` directories are intentionally-broken (or valid) marketplace roots that the validator runs against. When adding a new validator rule, add a fixture for both the failing and passing case and a corresponding test method in `tests/test_validate_marketplace.py`.

**Pyright path shim.** `pyrightconfig.json` sets `extraPaths: ["scripts"]` so static analysis can resolve `import validate_marketplace` from the test file (which adds `scripts/` to `sys.path` at runtime).

## Versioning model (V1)

Every catalog entry pins `ref: "main"`. Fresh installs (`/plugin install <name>@b81-claude`) pull the latest commit on `main`; rollback is a revert PR. Don't introduce semver pinning in the catalog without discussion — it's a deliberate v1 simplification.

**But existing installs are gated by the `version` field in `plugins/<name>/.claude-plugin/plugin.json`.** Claude Code's `/plugin marketplace update` only re-fetches plugin contents when this version string changes; matching the previous version short-circuits with "already at the latest version (X.Y.Z)" even when new commits exist on `main`. So **every PR that changes a plugin's content (skill prompts, commands, agents, hooks) must bump the plugin's `version`** — patch for fixes/wording, minor for new behavioral guidance or features, major for breaking changes. The catalog itself stays unversioned; only `plugin.json` moves.

## Conventions for new plugins

- **Name:** kebab-case, verb-or-domain (`code-review`, `deploy-helper`, `data-pipeline-tools`), unique in the catalog.
- **Description:** ≤80 chars, understandable without context (it's the only thing the `/plugin` UI shows before install).
- **Category:** free-form, but established values are `engineering`, `ops`, `product`. New categories are fine — call out the rationale in the PR.
- **Catalog entry shape** (also in `README.md`):
  ```json
  {
    "name": "<plugin-name>",
    "description": "...",
    "category": "engineering",
    "source": {
      "source": "git-subdir",
      "url": "https://github.com/GRITSpot/b81-claude.git",
      "path": "plugins/<plugin-name>",
      "ref": "main"
    }
  }
  ```

## Notes

- `docs/superpowers/` is gitignored — it's a local-only working directory, not part of the marketplace.
- The repo's only language is Python 3 (stdlib only). CI uses `python-version: "3.x"`.
