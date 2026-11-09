"""config.schema.json must match the schema generated from the config classes."""

from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import dataclass
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "nosarch"))
sys.path.insert(0, str(_REPO_ROOT))

from user_config import UserConfigReader, flag, read_into  # noqa: E402

from utils.config_schema_generator import config_schema_text, object_schema, schema_file_path  # noqa: E402


class ConfigSchemaSyncTest(unittest.TestCase):
    def test_schema_file_matches_classes(self) -> None:
        generated = config_schema_text()
        committed = schema_file_path().read_text(encoding="utf-8")
        self.assertEqual(
            committed,
            generated,
            "config.schema.json is generated from nosarch/user_config.py. "
            "Run `python utils/config_schema_generator.py` to refresh it.",
        )


class UserConfigReaderTest(unittest.TestCase):
    def test_reads_values_and_uses_field_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "user": {"username": "ada", "fullname": "Ada Lovelace"},
                        "setups": {"dev": {"enabled": True, "languages": ["python", "rust"]}},
                        "packaging": {"snap": {"install-snaps": {"code": "stable"}}},
                        "system": {"enable_lts_kernel": True},
                    }
                ),
                encoding="utf-8",
            )
            config = UserConfigReader.load(config_path)

            self.assertEqual(config.user.username, "ada")
            self.assertEqual(config.user.fullname, "Ada Lovelace")
            self.assertEqual(config.user.git_email, "")
            self.assertTrue(config.setups.dev.enabled)
            self.assertEqual(config.setups.dev.languages, ["python", "rust"])
            self.assertEqual(config.setups.dev.editors, [])
            self.assertFalse(config.setups.basic.enable_virtualization)
            self.assertEqual(config.packaging.snap.install_snaps, {"code": "stable"})
            self.assertEqual(config.packaging.snap.install_classic_snaps, {})
            self.assertTrue(config.system.enable_lts_kernel)
            self.assertFalse(config.advanced.enable_nosarch_works)
            self.assertFalse(config.advanced.enable_swapfile)

            config.save()
            saved = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["packaging"]["arch"]["install-packages"], [])
            self.assertEqual(saved["user"]["git_email"], "")

    def test_true_default_is_used_when_the_setting_is_missing(self) -> None:
        @dataclass
        class Sample:
            enabled: bool = flag("Starts on", default=True)

        self.assertTrue(read_into(Sample, {}).enabled)
        self.assertFalse(read_into(Sample, {"enabled": False}).enabled)
        self.assertIs(object_schema(Sample)["properties"]["enabled"]["default"], True)

    def test_wrong_json_type_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(
                json.dumps({"user": {"username": "ada", "fullname": "Ada"}, "system": {"enable_lts_kernel": "yes"}}),
                encoding="utf-8",
            )
            with self.assertRaises(TypeError):
                _ = UserConfigReader.load(config_path)

    def test_unknown_choice_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(
                json.dumps(
                    {"user": {"username": "ada", "fullname": "Ada"}, "setups": {"dev": {"languages": ["pascal"]}}}
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                _ = UserConfigReader.load(config_path)

    def test_missing_required_value_raises(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config_path = Path(directory) / "config.json"
            config_path.write_text(json.dumps({"user": {"username": "ada"}}), encoding="utf-8")
            with self.assertRaises(ValueError):
                _ = UserConfigReader.load(config_path)


if __name__ == "__main__":
    unittest.main()
