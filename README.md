# b81-claude

BEAT81's internal Claude Code plugin marketplace. One repo, every BEAT81-curated skill, agent, command, and hook for Claude Code.

## What this is

A standard [Claude Code plugin marketplace](https://docs.anthropic.com/en/docs/claude-code/plugins). Once you've added it once, every BEAT81 plugin shows up in Claude's native `/plugin` UI alongside any other marketplaces you have. Install, browse, enable/disable, and remove plugins from there — there are no custom commands to learn.

## Available plugins

| Plugin | Category | Description |
|---|---|---|
| [`b81-platform-buttler`](plugins/b81-platform-buttler/README.md) | engineering | BEAT81 platform expert spanning b81-platform, b81-workflows, b81-kubernetes |

Run `/plugin install <name>@b81-claude` to add any of them. Browse via `/plugin` after the marketplace is added.

## Get started

**Prerequisites:**
- [Claude Code](https://docs.anthropic.com/en/docs/claude-code) installed
- GitHub auth on this machine: `gh auth login`, or an SSH key with access to the GRITSpot org

**Add the marketplace (run once):**

Open Claude and run:

```
/plugin marketplace add GRITSpot/b81-claude
```

Then install whichever plugin you want:

```
/plugin install <plugin-name>@b81-claude
```

After that, just type `/plugin` anytime to browse, install, enable, disable, or remove BEAT81 plugins from the interactive menu.

## Adding a new plugin

1. Clone the repo (or open a worktree).
2. Create a folder under `plugins/<your-plugin-name>/` with at minimum:
   ```
   plugins/<your-plugin-name>/
   ├── .claude-plugin/
   │   └── plugin.json
   └── README.md
   ```
   plus whichever of `skills/`, `agents/`, `commands/`, `hooks/`, `scripts/` your plugin uses. The `README.md` is required — it's where users land from the catalog and where they read about features, install, and usage.
3. Append an entry to `.claude-plugin/marketplace.json`:
   ```json
   {
     "name": "<your-plugin-name>",
     "description": "≤80 chars, scannable in /plugin UI",
     "category": "engineering",
     "source": {
       "source": "git-subdir",
       "url": "https://github.com/GRITSpot/b81-claude.git",
       "path": "plugins/<your-plugin-name>",
       "ref": "main"
     }
   }
   ```
4. Add a row to the **Available plugins** table at the top of this README, with the plugin name linking to its `README.md` (e.g. `[\`<your-plugin-name>\`](plugins/<your-plugin-name>/README.md)`). Every plugin must appear in that index pointing at its own README.
5. Validate locally:
   ```
   python3 scripts/validate_marketplace.py .
   python3 -m unittest discover tests -v
   ```
6. Open a PR. CI runs the same two commands.

### Plugin name rules

- kebab-case
- describes a verb or a domain: `code-review`, `deploy-helper`, `data-pipeline-tools`
- unique within `marketplace.json`

### Description rules

- ≤80 characters
- understandable without context — it's all the `/plugin` UI shows

### Categories

Free-form. Established conventions: `engineering`, `ops`, `product`. Add new ones as needed; mention the rationale in your PR.

## Versioning

V1 pins every plugin to `ref: "main"` — installs always pull the latest commit on `main`. Rollback is a revert PR. If you need stable versions later, propose adding `ref: "v1.2.3"` in your plugin's catalog entry; we'll take it from there.

## Troubleshooting

**`/plugin marketplace add` fails with auth error**
Make sure `gh auth status` shows you're logged in to github.com with access to the GRITSpot org, or that an SSH key in your account has access. Then retry.

**`/plugin install` says the plugin doesn't exist**
The marketplace catalog might be stale. Run `/plugin marketplace update b81-claude` and try again.

**My plugin works locally but CI fails**
Run `python3 scripts/validate_marketplace.py .` locally — that's exactly what CI runs. The error messages will point at the broken file.

## Repo structure

```
.claude-plugin/marketplace.json   # the catalog read by /plugin marketplace add
plugins/<name>/                   # one folder per plugin
scripts/validate_marketplace.py   # structural validator (CI + local)
tests/                            # unittest cases for the validator
.github/workflows/validate.yml    # CI workflow
```

## License

Internal BEAT81 use. Do not redistribute outside the organization.
