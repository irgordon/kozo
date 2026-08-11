import json
from pathlib import Path
import tempfile
import unittest

from scripts.host_portability_contract import (
    ContractExecutionState,
    GOVERNED_RELEASE_INPUTS,
    OBJECT_FORM_PATTERN,
    PortabilityContractError,
    ReleaseInputSource,
    ROOT,
    build_failure_evidence,
    build_pending_evidence,
    expected_staged_files,
    portable_release_entries,
    sha256_bytes,
    stage_release_sources,
    validate_canonical_lf_bytes,
    validate_checksum_manifest,
    validate_destinations,
    validate_prohibited_entries,
    validate_release_input_attributes,
    validate_release_input_bytes,
    validate_staged_release_inputs,
    write_checksum_manifest,
)


class HostPortabilityContractTests(unittest.TestCase):
    def test_governed_license_attributes_require_lf(self):
        validate_release_input_attributes(ROOT)

    def test_governed_release_input_set_is_narrow(self):
        self.assertEqual(
            GOVERNED_RELEASE_INPUTS,
            ("LICENSE", "LICENSE-APACHE", "LICENSE-MIT"),
        )

    def test_accepts_canonical_lf_release_input(self):
        validate_canonical_lf_bytes(b"governed\nrelease input\n", "LICENSE")

    def test_rejects_crlf_release_input(self):
        with self.assertRaises(PortabilityContractError):
            validate_canonical_lf_bytes(b"governed\r\nrelease input\r\n", "LICENSE")

    def test_rejects_cr_release_input(self):
        with self.assertRaises(PortabilityContractError):
            validate_canonical_lf_bytes(b"governed\rrelease input\r", "LICENSE")

    def test_rejects_worktree_bytes_that_differ_from_blob(self):
        with self.assertRaises(PortabilityContractError):
            validate_release_input_bytes(
                b"governed\r\nlicense\r\n",
                b"governed\nlicense\n",
                "LICENSE",
            )

    def test_staged_release_input_remains_byte_exact(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "source"
            staging = Path(temporary_directory) / "staging"
            root.mkdir()
            content = b"governed\nlicense\n"
            (root / "LICENSE").write_bytes(content)
            source = ReleaseInputSource(
                "LICENSE", "blob", len(content), sha256_bytes(content)
            )
            stage_release_sources(
                root,
                staging,
                [{"source": "LICENSE", "destination": "LICENSE"}],
            )

            result = validate_staged_release_inputs(root, staging, (source,))

            self.assertEqual((staging / "LICENSE").read_bytes(), content)
            self.assertEqual(
                result["files"][0]["sha256"],
                result["files"][0]["staged_sha256"],
            )

    def test_staged_release_input_rejects_changed_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "source"
            staging = Path(temporary_directory) / "staging"
            root.mkdir()
            staging.mkdir()
            content = b"governed\nlicense\n"
            (root / "LICENSE").write_bytes(content)
            (staging / "LICENSE").write_bytes(b"changed\n")
            source = ReleaseInputSource(
                "LICENSE", "blob", len(content), sha256_bytes(content)
            )

            with self.assertRaises(PortabilityContractError):
                validate_staged_release_inputs(root, staging, (source,))

    def test_binary_staging_does_not_normalize_bytes(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "source"
            staging = Path(temporary_directory) / "staging"
            root.mkdir()
            content = b"\x00\r\n\xff"
            (root / "binary.bin").write_bytes(content)

            stage_release_sources(
                root,
                staging,
                [{"source": "binary.bin", "destination": "binary.bin"}],
            )

            self.assertEqual((staging / "binary.bin").read_bytes(), content)

    def test_pending_evidence_contains_host_tools_and_workflow(self):
        environment = sample_environment()
        state = ContractExecutionState(environment)

        evidence = build_pending_evidence(state)

        self.assertEqual(evidence["host"], environment["host"])
        self.assertEqual(evidence["tool_versions"], environment["tool_versions"])
        self.assertEqual(evidence["workflow"], environment["workflow"])
        self.assertEqual(evidence["contract_stage"], "environment_capture")
        self.assertEqual(evidence["build_contract"], "PENDING")

    def test_failure_evidence_retains_environment_and_stage(self):
        environment = sample_environment()
        state = ContractExecutionState(environment)
        state.enter("python_tests")

        evidence = build_failure_evidence(state, PortabilityContractError("failed"))

        self.assertEqual(evidence["host"], environment["host"])
        self.assertEqual(evidence["tool_versions"]["odin"], "odin test")
        self.assertEqual(evidence["workflow"]["run_id"], "123")
        self.assertEqual(evidence["contract_stage"], "python_tests")
        self.assertEqual(evidence["build_contract"], "FAIL")
        self.assertEqual(evidence["failure"], "failed")

    def test_failure_evidence_does_not_coerce_success(self):
        state = ContractExecutionState(sample_environment())

        evidence = build_failure_evidence(state, PortabilityContractError("failed"))

        self.assertNotEqual(evidence["build_contract"], "PASS")
        self.assertEqual(evidence["runtime_contract"], "NOT_EXECUTED")

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


def sample_environment() -> dict:
    return {
        "commit": "abc123",
        "host": {
            "runner_os": "Windows",
            "runner_arch": "X64",
            "shell_contract": "Git Bash",
        },
        "tool_versions": {
            "python": "3.13.14",
            "odin": "odin test",
            "rustc": "rustc test",
            "cargo": "cargo test",
            "git": "git test",
        },
        "workflow": {
            "name": "portability",
            "run_id": "123",
            "run_attempt": "1",
        },
    }


if __name__ == "__main__":
    unittest.main()
