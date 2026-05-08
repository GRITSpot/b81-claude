"""Structural validator for the b81-claude marketplace.

Checks performed against a marketplace root directory:
  - .claude-plugin/marketplace.json exists and is valid JSON
  - No two plugins share a `name`
  - Each plugin's source.path resolves to an existing folder under the root
  - Each referenced plugin folder contains .claude-plugin/plugin.json
  - Each plugin's `description` is <= 80 characters
  - Every folder under plugins/ is referenced by some plugin entry (no orphans)

Usage:
  python3 scripts/validate_marketplace.py                 # validates the current repo
  python3 scripts/validate_marketplace.py path/to/repo    # validates a specific root

Exit codes:
  0 — no errors
  1 — one or more errors (printed to stderr)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

DESCRIPTION_MAX = 80


def validate(root: Path) -> list[str]:
    """Return a list of error strings. Empty list = valid."""
    root = Path(root)
    errors: list[str] = []

    catalog_path = root / ".claude-plugin" / "marketplace.json"
    if not catalog_path.is_file():
        return [f"marketplace.json not found at {catalog_path}"]

    try:
        catalog = json.loads(catalog_path.read_text())
    except json.JSONDecodeError as e:
        return [f"marketplace.json is not valid JSON: {e}"]

    plugins = catalog.get("plugins", [])
    if not isinstance(plugins, list):
        return ["marketplace.json: 'plugins' must be a list"]

    seen_names: set[str] = set()
    referenced_paths: set[Path] = set()

    for i, plugin in enumerate(plugins):
        # Type guard.
        if not isinstance(plugin, dict):
            errors.append(f"plugins[{i}] is not an object")
            continue

        # Required name.
        if "name" not in plugin:
            errors.append(f"plugins[{i}]: 'name' is required")
            continue
        name = plugin["name"]

        # Duplicate name check.
        if name in seen_names:
            errors.append(f"duplicate plugin name: {name}")
        seen_names.add(name)

        # Description length check.
        description = plugin.get("description", "")
        if len(description) > DESCRIPTION_MAX:
            errors.append(
                f"{name}: description is {len(description)} chars; max is {DESCRIPTION_MAX}"
            )

        # Source object checks.
        if "source" not in plugin:
            errors.append(f"{name}: source is required")
            continue
        source = plugin["source"]
        if not isinstance(source, dict):
            errors.append(f"{name}: source must be an object")
            continue

        # Source path checks.
        path_str = source.get("path", "")
        if not path_str:
            errors.append(f"{name}: source.path is required")
            continue

        plugin_dir = root / path_str
        referenced_paths.add(plugin_dir.resolve())

        if not plugin_dir.is_dir():
            errors.append(f"{name}: source.path '{path_str}' does not exist")
            continue

        plugin_json = plugin_dir / ".claude-plugin" / "plugin.json"
        if not plugin_json.is_file():
            errors.append(f"{name}: plugin.json not found at {plugin_json.relative_to(root)}")
            continue

        try:
            json.loads(plugin_json.read_text())
        except json.JSONDecodeError as e:
            errors.append(f"{name}: plugin.json is not valid JSON: {e}")

    # Orphan check: every folder under plugins/ should be referenced.
    plugins_dir = root / "plugins"
    if plugins_dir.is_dir():
        for entry in plugins_dir.iterdir():
            if not entry.is_dir():
                continue
            if entry.resolve() not in referenced_paths:
                errors.append(
                    f"orphan plugin folder: plugins/{entry.name} is not listed in marketplace.json"
                )

    return errors


def main(argv: list[str]) -> int:
    root = Path(argv[1]) if len(argv) > 1 else Path.cwd()
    errors = validate(root)
    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1
    print(f"OK ({root})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
