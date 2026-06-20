from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path

from harness.codes import HOST_DEPENDENCY_PORTABILITY_INVALID, OK
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_CI_WORKFLOW_PATH = _ROOT / ".github" / "workflows" / "ci.yml"
_LINT_WORKFLOW_PATH = _ROOT / ".github" / "workflows" / "lint.yml"
_VERIFY_SCRIPT_PATH = _ROOT / "scripts" / "verify.sh"
_BUILD_BOOT_IMAGE_PATH = _ROOT / "scripts" / "build_boot_image.sh"
_QEMU_SMOKE_PATH = _ROOT / "scripts" / "qemu_smoke.sh"
_BOOT_TOOLING_DOC_PATH = _ROOT / "docs" / "BOOT_TOOLING.md"
_REQUIRED_CHECKS_DOC_PATH = _ROOT / "docs" / "REQUIRED_CHECKS.md"
_RELEASE_EVIDENCE_DOC_PATH = _ROOT / "docs" / "RELEASE_EVIDENCE.md"
_COMPATIBILITY_DOC_PATH = _ROOT / "docs" / "COMPATIBILITY.md"

_FORBIDDEN_HOST_TOKENS = (
    "/" + "Users/",
    "god" + "zilla",
    "stable-aarch64-" + "apple-darwin",
    "/opt/" + "homebrew",
)

_SCAN_SUFFIXES = (".py", ".sh", ".md", ".json", ".toml", ".yml", ".yaml", ".odin", ".rs", ".asm", ".ld", ".conf")
_SKIPPED_SCAN_PREFIXES = (
    "artifacts/",
    ".git/",
    "tests/",
)

_VERIFY_RUST_ANCHORS = (
    "rust-toolchain.toml",
    "rustup which --toolchain",
    "PINNED_RUSTC",
    "PINNED_CARGO",
    'RUSTC="$PINNED_RUSTC"',
    'run_pinned_cargo check --manifest-path "$ROOT/userspace/core_service/Cargo.toml"',
)

_CI_TOOLING_ANCHORS = (
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
    "make -C \"$limine_root\"",
    "LIMINE_DIR=$limine_root",
    "LIMINE=$limine_cmd",
    "XORRISO=$(command -v xorriso)",
    "scripts/build_boot_image.sh",
    "scripts/qemu_smoke.sh",
)

_LINT_TOOLING_ANCHORS = (
    "runs-on: ubuntu-latest",
    "nasm",
    "laytan/setup-odin",
    "rustup target add --toolchain",
    "x86_64-unknown-none",
)

_BUILD_SCRIPT_ENV_ANCHORS = (
    "${LIMINE:-}",
    "${LIMINE_DIR:-}",
    "${LIMINE_INSTALL:-}",
    "${XORRISO:-}",
    "find_cmd limine",
    "find_cmd xorriso",
)

_QEMU_FAIL_CLOSED_ANCHORS = (
    "command -v qemu-system-x86_64",
    'write_blocked_metadata "missing_qemu_tooling"',
    'print_blocker "missing_qemu_tooling"',
)

_DOC_POLICY_ANCHORS = (
    "CI/Linux is the authoritative portability proof",
    "Local macOS development is a convenience path",
    "No build or verification script may depend on user-specific absolute paths",
)


@dataclass(frozen=True)
class HostPortabilityIssue:
    reason: str
    contract_field: str
    detail: str


class HostDependencyPortabilityValidator(BaseValidator):
    name = "host_dependency_portability"
    subsystem = "host_dependency_portability"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _host_portability_issue()
        if issue is not None:
            return _failure(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Host dependency portability gate rejects local path assumptions and verifies declared CI tooling",
        )


def _host_portability_issue() -> HostPortabilityIssue | None:
    return _first_issue(
        _tracked_source_scan_issue(),
        _anchor_file_issue(_VERIFY_SCRIPT_PATH, _VERIFY_RUST_ANCHORS, "verify.rust_toolchain"),
        _anchor_file_issue(_CI_WORKFLOW_PATH, _CI_TOOLING_ANCHORS, "ci.tooling"),
        _anchor_file_issue(_LINT_WORKFLOW_PATH, _LINT_TOOLING_ANCHORS, "lint.tooling"),
        _anchor_file_issue(_BUILD_BOOT_IMAGE_PATH, _BUILD_SCRIPT_ENV_ANCHORS, "boot_image.env"),
        _anchor_file_issue(_QEMU_SMOKE_PATH, _QEMU_FAIL_CLOSED_ANCHORS, "qemu_smoke.fail_closed"),
        _documentation_policy_issue(),
    )


def _tracked_source_scan_issue() -> HostPortabilityIssue | None:
    for path in _tracked_scan_paths():
        if _allows_historical_host_reference(path):
            continue
        text = path.read_text(errors="replace")
        for token in _FORBIDDEN_HOST_TOKENS:
            if token in text:
                return _issue(
                    "host_specific_token",
                    f"host_dependency_portability.{_relative_path(path)}.{token}",
                    f"Tracked source contains host-specific token {token}: {_relative_path(path)}",
                )
    return None


def _allows_historical_host_reference(path: Path) -> bool:
    return _relative_path(path) == "CHANGELOG.md"


def _tracked_scan_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in _tracked_paths()
        if _should_scan_path(path)
    )


def _tracked_paths() -> tuple[Path, ...]:
    try:
        result = subprocess.run(
            ["git", "-C", str(_ROOT), "ls-files"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return ()
    return tuple(_ROOT / line for line in result.stdout.splitlines() if line)


def _should_scan_path(path: Path) -> bool:
    relative = _relative_path(path)
    return (
        path.is_file()
        and path.suffix in _SCAN_SUFFIXES
        and not any(relative.startswith(prefix) for prefix in _SKIPPED_SCAN_PREFIXES)
    )


def _anchor_file_issue(path: Path, anchors: tuple[str, ...], field_prefix: str) -> HostPortabilityIssue | None:
    if not path.is_file():
        return _issue("missing_file", f"host_dependency_portability.{field_prefix}", f"Missing portability input: {_relative_path(path)}")
    text = path.read_text(errors="replace")
    for anchor in anchors:
        if anchor not in text:
            return _issue(
                "missing_anchor",
                f"host_dependency_portability.{field_prefix}.{anchor}",
                f"Portability surface {_relative_path(path)} is missing required anchor: {anchor}",
            )
    return None


def _documentation_policy_issue() -> HostPortabilityIssue | None:
    for path in (
        _BOOT_TOOLING_DOC_PATH,
        _REQUIRED_CHECKS_DOC_PATH,
        _RELEASE_EVIDENCE_DOC_PATH,
        _COMPATIBILITY_DOC_PATH,
    ):
        issue = _anchor_file_issue(path, _DOC_POLICY_ANCHORS, _relative_path(path))
        if issue is not None:
            return issue
    return None


def _relative_path(path: Path) -> str:
    try:
        return str(path.relative_to(_ROOT))
    except ValueError:
        return str(path)


def _first_issue(*issues: HostPortabilityIssue | None) -> HostPortabilityIssue | None:
    for issue in issues:
        if issue is not None:
            return issue
    return None


def _issue(reason: str, contract_field: str, detail: str) -> HostPortabilityIssue:
    return HostPortabilityIssue(reason=reason, contract_field=contract_field, detail=detail)


def _failure(issue: HostPortabilityIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=HOST_DEPENDENCY_PORTABILITY_INVALID,
        detail=issue.detail,
        action="Remove host-specific assumptions or declare the dependency in CI and portability docs",
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
