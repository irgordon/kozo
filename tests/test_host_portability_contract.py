import json
from pathlib import Path
import tempfile
import unittest

from scripts.host_portability_contract import (
    OBJECT_FORM_PATTERN,
    PortabilityContractError,
    expected_staged_files,
    portable_release_entries,
    validate_checksum_manifest,
    validate_destinations,
    validate_prohibited_entries,
    write_checksum_manifest,
)


class HostPortabilityContractTests(unittest.TestCase):
    def test_accepts_safe_relative_release_destinations(self):
        validate_destinations(["README.md", "docs/guide.md", "packages/core/Cargo.toml"])

    def test_rejects_absolute_release_destination(self):
        with self.assertRaises(PortabilityContractError):
            validate_destinations(["/private/file"])

    def test_rejects_parent_release_destination(self):
        with self.assertRaises(PortabilityContractError):
            validate_destinations(["docs/../private/file"])

    def test_rejects_wildcard_release_destination(self):
        with self.assertRaises(PortabilityContractError):
            validate_destinations(["docs/*.md"])

    def test_rejects_prohibited_release_path(self):
        manifest = {"prohibited_names": [".git"]}
        entries = [{"source": ".git/config", "destination": "config"}]
        with self.assertRaises(PortabilityContractError):
            validate_prohibited_entries(entries, manifest)

    def test_portable_staging_excludes_runtime_generated_sources(self):
        entries = [
            {"source": "README.md", "destination": "README.md"},
            {"source": "artifacts/latest_verify.json", "destination": "proof.json"},
        ]

        self.assertEqual(portable_release_entries(entries), entries[:1])

    def test_expected_staging_inventory_maps_directory_contents(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = root / "docs"
            source.mkdir()
            (source / "guide.md").write_text("guide\n")
            entries = [{"source": "docs", "destination": "manual"}]

            self.assertEqual(expected_staged_files(root, entries), {"manual/guide.md"})

    def test_checksum_round_trip_accepts_matching_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            checked_file = root / "file with spaces.txt"
            manifest_path = root / "SHA256SUMS"
            checked_file.write_text("portable\n")
            write_checksum_manifest(manifest_path, [checked_file])

            validate_checksum_manifest(manifest_path, root)

    def test_checksum_round_trip_rejects_modified_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            checked_file = root / "payload.txt"
            manifest_path = root / "SHA256SUMS"
            checked_file.write_text("accepted\n")
            write_checksum_manifest(manifest_path, [checked_file])
            checked_file.write_text("modified\n")

            with self.assertRaises(PortabilityContractError):
                validate_checksum_manifest(manifest_path, root)

    def test_object_form_pattern_accepts_only_supported_forms(self):
        for output_form in ("exact", "dot_o", "dot_obj"):
            with self.subTest(output_form=output_form):
                text = f"KOZO_ODIN_OBJECT_OUTPUT_FORM={output_form}\n"
                self.assertEqual(OBJECT_FORM_PATTERN.search(text).group(1), output_form)
        self.assertIsNone(OBJECT_FORM_PATTERN.search("KOZO_ODIN_OBJECT_OUTPUT_FORM=other\n"))

    def test_evidence_shape_remains_json_serializable(self):
        evidence = {
            "build_contract": "PASS",
            "runtime_contract": "NOT_EXECUTED",
            "host": {"runner_os": "Windows", "shell_contract": "Git Bash"},
        }
        self.assertEqual(json.loads(json.dumps(evidence)), evidence)


if __name__ == "__main__":
    unittest.main()
