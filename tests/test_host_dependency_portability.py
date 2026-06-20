from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from harness.codes import HOST_DEPENDENCY_PORTABILITY_INVALID, OK
from harness.validators_impl import host_dependency_portability as validator_module
from harness.validators_impl.host_dependency_portability import HostDependencyPortabilityValidator

KOZO_NEGATIVE_COVERAGE = {
    "host_dependency_portability": {
        "hardcoded_users_path": "test_fails_when_tracked_source_contains_users_path",
        "hardcoded_user_name": "test_fails_when_tracked_source_contains_user_name",
        "hardcoded_apple_toolchain": "test_fails_when_tracked_source_contains_apple_toolchain",
        "missing_ci_xorriso_install": "test_fails_when_ci_xorriso_install_is_missing",
        "missing_ci_limine_acquisition": "test_fails_when_ci_limine_acquisition_is_missing",
        "missing_ci_qemu_install": "test_fails_when_ci_qemu_install_is_missing",
        "missing_rust_toolchain_selection": "test_fails_when_verify_script_does_not_select_rust_toolchain",
        "diagnostic_names_field": "test_failure_diagnostic_names_field",
    }
}


class HostDependencyPortabilityValidatorTests(unittest.TestCase):
    def test_passes_when_portability_inputs_are_complete(self):
        result = self.validate_fixture()

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_fails_when_tracked_source_contains_users_path(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(extra_file=("scripts/local.sh", "/Users/example/tool"))

        self.assertEqual(result.status, "fail")
        self.assert_portability_failure(result, "host_specific_token", "host_dependency_portability.scripts/local.sh./Users/")

    def test_fails_when_tracked_source_contains_user_name(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(extra_file=("docs/local.md", "hello godzilla"))

        self.assertEqual(result.status, "fail")
        self.assert_portability_failure(result, "host_specific_token", "host_dependency_portability.docs/local.md.godzilla")

    def test_fails_when_tracked_source_contains_apple_toolchain(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(extra_file=("scripts/rust.sh", "stable-aarch64-apple-darwin"))

        self.assertEqual(result.status, "fail")
        self.assert_portability_failure(result, "host_specific_token", "host_dependency_portability.scripts/rust.sh.stable-aarch64-apple-darwin")

    def test_fails_when_ci_xorriso_install_is_missing(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(mutate_ci=lambda text: text.replace("xorriso", "missing-iso-tool"))

        self.assertEqual(result.status, "fail")
        self.assert_portability_failure(result, "missing_anchor", "host_dependency_portability.ci.tooling.xorriso")

    def test_fails_when_ci_limine_acquisition_is_missing(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(mutate_ci=lambda text: text.replace("LIMINE_TARBALL_SHA256", "LIMINE_HASH"))

        self.assertEqual(result.status, "fail")
        self.assert_portability_failure(result, "missing_anchor", "host_dependency_portability.ci.tooling.LIMINE_TARBALL_SHA256")

    def test_fails_when_ci_qemu_install_is_missing(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(mutate_ci=lambda text: text.replace("qemu-system-x86", "missing-qemu"))

        self.assertEqual(result.status, "fail")
        self.assert_portability_failure(result, "missing_anchor", "host_dependency_portability.ci.tooling.qemu-system-x86")

    def test_fails_when_verify_script_does_not_select_rust_toolchain(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(mutate_verify=lambda text: text.replace("rustup which --toolchain", "rustup which"))

        self.assertEqual(result.status, "fail")
        self.assert_portability_failure(result, "missing_anchor", "host_dependency_portability.verify.rust_toolchain.rustup which --toolchain")

    def test_does_not_fail_when_changelog_contains_historical_host_reference(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(extra_file=("CHANGELOG.md", "Historical /Users/godzilla/local note"))

        self.assertEqual(result.status, "pass")
        self.assertEqual(result.code, OK)

    def test_failure_diagnostic_names_field(self):
        self.assertEqual("host_dependency_portability", HostDependencyPortabilityValidator.name)
        result = self.validate_fixture(mutate_build=lambda text: text.replace("${XORRISO:-}", "${ISO_TOOL:-}"))

        self.assertEqual(result.status, "fail")
        self.assertEqual(result.code, HOST_DEPENDENCY_PORTABILITY_INVALID)
        self.assertEqual(result.meta["reason"], "missing_anchor")
        self.assertEqual(result.meta["contract_field"], "host_dependency_portability.boot_image.env.${XORRISO:-}")

    def validate_fixture(
        self,
        *,
        mutate_ci=None,
        mutate_verify=None,
        mutate_build=None,
        extra_file: tuple[str, str] | None = None,
    ):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            paths = write_fixture_files(root)

            if mutate_ci is not None:
                paths["ci"].write_text(mutate_ci(paths["ci"].read_text()))
            if mutate_verify is not None:
                paths["verify"].write_text(mutate_verify(paths["verify"].read_text()))
            if mutate_build is not None:
                paths["build"].write_text(mutate_build(paths["build"].read_text()))
            if extra_file is not None:
                path = root / extra_file[0]
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(extra_file[1])
                paths["tracked"].append(path)

            old_paths = patch_validator_paths(paths)
            try:
                return HostDependencyPortabilityValidator().validate({})
            finally:
                restore_validator_paths(old_paths)

    def assert_portability_failure(self, result, reason: str, contract_field: str):
        self.assertEqual(result.code, HOST_DEPENDENCY_PORTABILITY_INVALID)
        self.assertEqual(result.meta["reason"], reason)
        self.assertEqual(result.meta["contract_field"], contract_field)


def write_fixture_files(root: Path) -> dict[str, object]:
    paths = {
        "ci": root / ".github" / "workflows" / "ci.yml",
        "lint": root / ".github" / "workflows" / "lint.yml",
        "verify": root / "scripts" / "verify.sh",
        "build": root / "scripts" / "build_boot_image.sh",
        "qemu": root / "scripts" / "qemu_smoke.sh",
        "boot_tooling": root / "docs" / "BOOT_TOOLING.md",
        "required_checks": root / "docs" / "REQUIRED_CHECKS.md",
        "release_evidence": root / "docs" / "RELEASE_EVIDENCE.md",
        "compatibility": root / "docs" / "COMPATIBILITY.md",
        "tracked": [],
    }
    for key, path in paths.items():
        if key == "tracked":
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
    paths["ci"].write_text(valid_ci_text())
    paths["lint"].write_text(valid_lint_text())
    paths["verify"].write_text(valid_verify_text())
    paths["build"].write_text(valid_build_text())
    paths["qemu"].write_text(valid_qemu_text())
    for key in ("boot_tooling", "required_checks", "release_evidence", "compatibility"):
        paths[key].write_text(valid_doc_text())
    paths["tracked"].extend(path for key, path in paths.items() if key != "tracked")
    return paths


def valid_ci_text() -> str:
    return "\n".join(
        (
            "runs-on: ubuntu-latest",
            "xorriso",
            "qemu-system-x86",
            "nasm",
            "lld",
            "laytan/setup-odin",
            "rustup target add --toolchain",
            "x86_64-unknown-none",
            "LIMINE_VERSION: v12.3.3",
            "LIMINE_TARBALL_SHA256",
            "curl -fsSL",
            "sha256sum -c -",
            'make -C "$limine_root"',
            "LIMINE_DIR=$limine_root",
            "LIMINE=$limine_cmd",
            "XORRISO=$(command -v xorriso)",
            "scripts/build_boot_image.sh",
            "scripts/qemu_smoke.sh",
        )
    )


def valid_lint_text() -> str:
    return "\n".join(
        (
            "runs-on: ubuntu-latest",
            "nasm",
            "laytan/setup-odin",
            "rustup target add --toolchain",
            "x86_64-unknown-none",
        )
    )


def valid_verify_text() -> str:
    return "\n".join(
        (
            "rust-toolchain.toml",
            "rustup which --toolchain",
            "PINNED_RUSTC",
            "PINNED_CARGO",
            'RUSTC="$PINNED_RUSTC"',
            'run_pinned_cargo check --manifest-path "$ROOT/userspace/core_service/Cargo.toml"',
        )
    )


def valid_build_text() -> str:
    return "\n".join(
        (
            "${LIMINE:-}",
            "${LIMINE_DIR:-}",
            "${LIMINE_INSTALL:-}",
            "${XORRISO:-}",
            "find_cmd limine",
            "find_cmd xorriso",
        )
    )


def valid_qemu_text() -> str:
    return "\n".join(
        (
            "command -v qemu-system-x86_64",
            'write_blocked_metadata "missing_qemu_tooling"',
            'print_blocker "missing_qemu_tooling"',
        )
    )


def valid_doc_text() -> str:
    return "\n".join(
        (
            "CI/Linux is the authoritative portability proof",
            "Local macOS development is a convenience path",
            "No build or verification script may depend on user-specific absolute paths",
        )
    )


def patch_validator_paths(paths: dict[str, object]):
    old_paths = (
        validator_module._ROOT,
        validator_module._CI_WORKFLOW_PATH,
        validator_module._LINT_WORKFLOW_PATH,
        validator_module._VERIFY_SCRIPT_PATH,
        validator_module._BUILD_BOOT_IMAGE_PATH,
        validator_module._QEMU_SMOKE_PATH,
        validator_module._BOOT_TOOLING_DOC_PATH,
        validator_module._REQUIRED_CHECKS_DOC_PATH,
        validator_module._RELEASE_EVIDENCE_DOC_PATH,
        validator_module._COMPATIBILITY_DOC_PATH,
        validator_module._tracked_paths,
    )
    validator_module._ROOT = paths["ci"].parents[2]
    validator_module._CI_WORKFLOW_PATH = paths["ci"]
    validator_module._LINT_WORKFLOW_PATH = paths["lint"]
    validator_module._VERIFY_SCRIPT_PATH = paths["verify"]
    validator_module._BUILD_BOOT_IMAGE_PATH = paths["build"]
    validator_module._QEMU_SMOKE_PATH = paths["qemu"]
    validator_module._BOOT_TOOLING_DOC_PATH = paths["boot_tooling"]
    validator_module._REQUIRED_CHECKS_DOC_PATH = paths["required_checks"]
    validator_module._RELEASE_EVIDENCE_DOC_PATH = paths["release_evidence"]
    validator_module._COMPATIBILITY_DOC_PATH = paths["compatibility"]
    validator_module._tracked_paths = lambda: tuple(paths["tracked"])
    return old_paths


def restore_validator_paths(old_paths) -> None:
    (
        validator_module._ROOT,
        validator_module._CI_WORKFLOW_PATH,
        validator_module._LINT_WORKFLOW_PATH,
        validator_module._VERIFY_SCRIPT_PATH,
        validator_module._BUILD_BOOT_IMAGE_PATH,
        validator_module._QEMU_SMOKE_PATH,
        validator_module._BOOT_TOOLING_DOC_PATH,
        validator_module._REQUIRED_CHECKS_DOC_PATH,
        validator_module._RELEASE_EVIDENCE_DOC_PATH,
        validator_module._COMPATIBILITY_DOC_PATH,
        validator_module._tracked_paths,
    ) = old_paths


if __name__ == "__main__":
    unittest.main()
