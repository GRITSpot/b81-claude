"""Tests for scripts/validate_marketplace.py.

Each test invokes validate_marketplace.validate(root) against a fixture
directory under tests/fixtures/ and asserts the expected outcome.

The validator returns a list of error strings. An empty list means valid.
"""

import sys
import unittest
from pathlib import Path

# Make the validator importable.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import validate_marketplace  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


class TestValidator(unittest.TestCase):
    def test_valid_empty(self):
        errors = validate_marketplace.validate(FIXTURES / "valid_empty")
        self.assertEqual(errors, [])

    def test_valid_one_plugin(self):
        errors = validate_marketplace.validate(FIXTURES / "valid_one_plugin")
        self.assertEqual(errors, [])

    def test_duplicate_name(self):
        errors = validate_marketplace.validate(FIXTURES / "duplicate_name")
        self.assertTrue(any("duplicate" in e.lower() for e in errors), errors)

    def test_missing_plugin_folder(self):
        errors = validate_marketplace.validate(FIXTURES / "missing_plugin_folder")
        self.assertTrue(any("does not exist" in e.lower() for e in errors), errors)

    def test_orphan_plugin_folder(self):
        errors = validate_marketplace.validate(FIXTURES / "orphan_plugin_folder")
        self.assertTrue(any("orphan" in e.lower() for e in errors), errors)

    def test_description_too_long(self):
        errors = validate_marketplace.validate(FIXTURES / "long_description")
        self.assertTrue(any("description" in e.lower() and "80" in e for e in errors), errors)

    def test_missing_plugin_json(self):
        errors = validate_marketplace.validate(FIXTURES / "missing_plugin_json")
        self.assertTrue(any("plugin.json" in e for e in errors), errors)

    def test_invalid_json(self):
        errors = validate_marketplace.validate(FIXTURES / "invalid_json")
        self.assertTrue(any("json" in e.lower() for e in errors), errors)

    def test_non_dict_plugin(self):
        errors = validate_marketplace.validate(FIXTURES / "non_dict_plugin")
        self.assertTrue(any("not an object" in e for e in errors), errors)

    def test_missing_name(self):
        errors = validate_marketplace.validate(FIXTURES / "missing_name")
        self.assertTrue(any("'name' is required" in e for e in errors), errors)

    def test_missing_source(self):
        errors = validate_marketplace.validate(FIXTURES / "missing_source")
        self.assertTrue(any("source is required" in e for e in errors), errors)


if __name__ == "__main__":
    unittest.main()
