import json
import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION_PATH = ROOT / "release" / "version.txt"
MANIFEST_PATH = ROOT / "release" / "release_files.v1.json"
SCRIPT_PATH = ROOT / "scripts" / "build_release_candidate.sh"
CI_PATH = ROOT / ".github" / "workflows" / "ci.yml"
LINT_PATH = ROOT / ".github" / "workflows" / "lint.yml"
SUMMARY_PATH = ROOT / "scripts" / "ci_evidence_summary.sh"


class ReleaseCandidateHardeningTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST_PATH.read_text())
        self.script = SCRIPT_PATH.read_text()

    def test_version_authority_is_canonical(self):
        self.assertEqual(VERSION_PATH.read_text(), "1.0.0-rc.1\n")

    def test_manifest_destinations_are_explicit_and_unique(self):
        destinations = [
            item["destination"]
            for key in ("required_files", "required_directories")
            for item in self.manifest[key]
        ]
        self.assertEqual(len(destinations), len(set(destinations)))
        self.assertFalse(any("*" in destination for destination in destinations))

    def test_manifest_includes_runtime_artifacts_and_licenses(self):
        sources = {item["source"] for item in self.manifest["required_files"]}
        required = {
            "LICENSE",
            "LICENSE-MIT",
            "LICENSE-APACHE",
            "artifacts/latest_verify.json",
            "artifacts/runtime/boot_image/kozo.iso",
            "artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf",
            "artifacts/runtime/qemu_smoke.metadata.json",
            "docs/releases/v1.0.0-rc.1.md",
        }
        self.assertTrue(required.issubset(sources))

    def test_manifest_excludes_repository_and_private_state(self):
        all_sources = [
            item["source"]
            for key in ("required_files", "required_directories")
            for item in self.manifest[key]
        ]
        self.assertNotIn(".git", all_sources)
        self.assertNotIn(".github", all_sources)
        self.assertNotIn("target", all_sources)
        self.assertNotIn(".env", all_sources)

    def test_script_has_no_publication_interface(self):
        self.assertNotRegex(self.script, r"gh\s+release\s+create")
        self.assertNotRegex(self.script, r"cargo\s+publish")
        self.assertNotIn("--publish", self.script)
        self.assertIn('"published": False', self.script)

    def test_script_requires_clean_commit_and_passing_evidence(self):
        required = (
            "ensure_clean_repository",
            "run_governed_verification",
            "ensure_verification_passed",
            '[[ "$verificationCheckCount" == "67" ]]',
            '[[ "$markerCount" == "41" ]]',
        )
        for value in required:
            self.assertIn(value, self.script)

    def test_script_canonicalizes_temporary_workspace(self):
        self.assertIn('workDir="$(cd "$workDir" && pwd -P)"', self.script)

    def test_script_main_reads_top_down(self):
        main = re.search(r"main\(\) \{(?P<body>.*?)\n\}", self.script, re.DOTALL)
        self.assertIsNotNone(main)
        body = main.group("body")
        calls = [
            "parse_arguments",
            "read_release_version",
            "ensure_clean_repository",
            "prepare_release_workspace",
            "run_governed_verification",
            "copy_release_files",
            "create_release_archive",
            "inspect_release_archive",
            "report_outputs",
        ]
        positions = [body.index(call) for call in calls]
        self.assertEqual(positions, sorted(positions))

    def test_ci_uses_node24_actions_and_authenticated_odin_setup(self):
        ci = CI_PATH.read_text()
        lint = LINT_PATH.read_text()
        for workflow in (ci, lint):
            self.assertIn("actions/checkout@v7", workflow)
            self.assertIn("token: ${{ secrets.GITHUB_TOKEN }}", workflow)
        self.assertIn("actions/upload-artifact@v7", ci)

    def test_ci_runs_release_security_and_bundle_gates(self):
        ci = CI_PATH.read_text()
        for required in (
            "cargo deny",
            "cargo audit",
            "scripts/build_release_candidate.sh",
            "SHA256SUMS",
            "release_metadata.json",
        ):
            self.assertIn(required, ci)

    def test_ci_summary_reads_release_evidence_without_source_mutation(self):
        ci = CI_PATH.read_text()
        summary = SUMMARY_PATH.read_text()
        self.assertIn(
            "KOZO_CI_EVIDENCE_ROOT: artifacts/release-candidate/evidence",
            ci,
        )
        self.assertIn('EVIDENCE_ROOT="${KOZO_CI_EVIDENCE_ROOT:-artifacts}"', summary)

    def test_ci_packages_clean_commit_before_workspace_preflight(self):
        ci = CI_PATH.read_text()
        package_step = ci.index("- name: Build and validate release candidate")
        preflight_step = ci.index("- name: Build governed boot image preflight")
        self.assertLess(package_step, preflight_step)


if __name__ == "__main__":
    unittest.main()
