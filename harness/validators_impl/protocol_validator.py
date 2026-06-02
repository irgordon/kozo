from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness import abi_manifest
from harness.codes import OK, PROTOCOL_MISMATCH
from harness.validator import BaseValidator, ValidationResult
from harness.validators_impl.runtime_trap_path import runtime_trap_path_observations

_ROOT = Path(__file__).resolve().parents[2]
_ABI_MANIFEST_PATH = abi_manifest.MANIFEST_PATH
_KERNEL_PATH = _ROOT / "kernel" / "main.odin"
_SERVICE_PATH = _ROOT / "userspace" / "core_service" / "src" / "main.rs"

_RUST_SYSCALL_PATTERN = re.compile(r"\bpub\s+const\s+(K_SYSCALL_[A-Z0-9_]+)\s*:\s*K_SYSCALL_ID\s*=\s*(\d+)\s*;")
_ODIN_SYSCALL_PATTERN = re.compile(r"\b(K_SYSCALL_[A-Z0-9_]+)\s*:\s*K_SYSCALL_ID\s*:\s*(\d+)")


@dataclass(frozen=True)
class ProtocolConstant:
    name: str
    value: int


@dataclass(frozen=True)
class ProtocolSources:
    rust_bindings: str
    odin_bindings: str
    kernel: str
    service: str


@dataclass(frozen=True)
class ProtocolUsageAnchor:
    name: str
    needle: str
    detail: str
    source_path: Path


@dataclass(frozen=True)
class ForbiddenLocalConstant:
    name: str
    pattern: re.Pattern[str]
    detail: str
    source_path: Path


@dataclass(frozen=True)
class ProtocolIssue:
    reason: str
    contract_field: str
    detail: str
    action: str


_RUST_USAGE_ANCHORS = (
    ProtocolUsageAnchor(
        "rust_live_heartbeat_syscall_constant",
        "let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;",
        "Rust heartbeat_request must select the generated heartbeat syscall constant",
        _SERVICE_PATH,
    ),
    ProtocolUsageAnchor(
        "rust_live_status_syscall_constant",
        "let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_STATUS;",
        "Rust status_request must select the generated STATUS syscall constant",
        _SERVICE_PATH,
    ),
)

_ODIN_USAGE_ANCHORS = (
    ProtocolUsageAnchor(
        "odin_live_heartbeat_signal_constant",
        "syscall_dispatch(abi.K_SYSCALL_DEBUG_HEARTBEAT,",
        "Odin signal_kernel_heartbeat must call syscall_dispatch with the generated heartbeat syscall constant",
        _KERNEL_PATH,
    ),
    ProtocolUsageAnchor(
        "odin_live_heartbeat_dispatch_case",
        "case abi.K_SYSCALL_DEBUG_HEARTBEAT:",
        "Odin syscall_dispatch must dispatch the generated heartbeat syscall constant",
        _KERNEL_PATH,
    ),
)

class ProtocolContractValidator(BaseValidator):
    name = "protocol_contract_alignment"
    subsystem = "protocol_contract_alignment"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        issue = _protocol_validation_issue()
        if issue is not None:
            return _failure_result(issue)
        return ValidationResult.pass_(
            code=OK,
            detail="Kernel and Rust protocol contracts align across the assembly bridge boundary",
        )


def _protocol_validation_issue() -> ProtocolIssue | None:
    manifest = _load_protocol_manifest()
    if isinstance(manifest, ProtocolIssue):
        return manifest
    sources = _load_protocol_sources(manifest)
    if isinstance(sources, ProtocolIssue):
        return sources
    return _first_protocol_issue(manifest, sources)


def _first_protocol_issue(
    manifest: abi_manifest.AbiManifest,
    sources: ProtocolSources,
) -> ProtocolIssue | None:
    manifest_syscalls = _manifest_syscalls(manifest)
    return _first_issue(
        _manifest_syscall_issue(manifest_syscalls),
        _binding_alignment_issue(manifest_syscalls, sources),
        _kernel_dispatch_issue(manifest_syscalls, sources.kernel),
        _rust_live_usage_issue(manifest, sources.service),
        _odin_live_usage_issue(manifest, sources.kernel),
        _bridge_path_issue(sources.service),
    )


def _load_protocol_manifest() -> abi_manifest.AbiManifest | ProtocolIssue:
    try:
        return abi_manifest.load_abi_manifest(_ABI_MANIFEST_PATH)
    except (KeyError, OSError, TypeError, ValueError) as exc:
        return _issue("manifest_unavailable", "abi_manifest", f"Protocol mismatch: ABI manifest could not be loaded: {exc}")


def _load_protocol_sources(manifest: abi_manifest.AbiManifest) -> ProtocolSources | ProtocolIssue:
    try:
        return ProtocolSources(
            abi_manifest.manifest_repo_path(manifest.generated_bindings.rust).read_text(),
            abi_manifest.manifest_repo_path(manifest.generated_bindings.odin).read_text(),
            _KERNEL_PATH.read_text(),
            _SERVICE_PATH.read_text(),
        )
    except OSError as exc:
        return _issue("manifest_source_unavailable", "abi_manifest.generated_bindings", f"Protocol mismatch: ABI manifest source path could not be read: {exc}")


def _manifest_syscalls(manifest: abi_manifest.AbiManifest) -> tuple[ProtocolConstant, ...]:
    return tuple(
        ProtocolConstant(name, value)
        for name, value in manifest.constants.syscalls.items()
    )


def _manifest_syscall_issue(constants: tuple[ProtocolConstant, ...]) -> ProtocolIssue | None:
    for name in ("K_SYSCALL_NOP", "K_SYSCALL_DEBUG_HEARTBEAT", "K_SYSCALL_STATUS"):
        if _constant_named(constants, name) is None:
            return _issue(
                "missing_manifest_syscall_constant",
                f"constants.syscalls.{name}",
                f"Protocol mismatch: ABI manifest is missing {name}",
            )
    return None


def _binding_alignment_issue(
    canonical_syscalls: tuple[ProtocolConstant, ...],
    sources: ProtocolSources,
) -> ProtocolIssue | None:
    rust_syscalls = _parse_rust_syscalls(sources.rust_bindings)
    odin_syscalls = _parse_odin_syscalls(sources.odin_bindings)
    return _first_issue(
        _missing_binding_issue("rust", canonical_syscalls, rust_syscalls),
        _missing_binding_issue("odin", canonical_syscalls, odin_syscalls),
        _mismatched_binding_issue(canonical_syscalls, rust_syscalls, odin_syscalls),
    )


def _parse_rust_syscalls(source: str) -> tuple[ProtocolConstant, ...]:
    return tuple(
        ProtocolConstant(name, int(value))
        for name, value in _RUST_SYSCALL_PATTERN.findall(source)
    )


def _parse_odin_syscalls(source: str) -> tuple[ProtocolConstant, ...]:
    return tuple(
        ProtocolConstant(name, int(value))
        for name, value in _ODIN_SYSCALL_PATTERN.findall(source)
    )


def _missing_binding_issue(
    language: str,
    canonical_syscalls: tuple[ProtocolConstant, ...],
    binding_syscalls: tuple[ProtocolConstant, ...],
) -> ProtocolIssue | None:
    for syscall in canonical_syscalls:
        if _constant_named(binding_syscalls, syscall.name) is None:
            return _binding_issue(language, syscall.name, "missing_generated_syscall_constant")
    return None


def _mismatched_binding_issue(
    canonical_syscalls: tuple[ProtocolConstant, ...],
    rust_syscalls: tuple[ProtocolConstant, ...],
    odin_syscalls: tuple[ProtocolConstant, ...],
) -> ProtocolIssue | None:
    for syscall in canonical_syscalls:
        issue = _constant_value_issue(syscall, rust_syscalls, "rust")
        if issue is not None:
            return issue
        issue = _constant_value_issue(syscall, odin_syscalls, "odin")
        if issue is not None:
            return issue
    return None


def _constant_value_issue(
    canonical: ProtocolConstant,
    bindings: tuple[ProtocolConstant, ...],
    language: str,
) -> ProtocolIssue | None:
    binding = _constant_named(bindings, canonical.name)
    if binding is None or binding.value == canonical.value:
        return None
    return _binding_issue(language, canonical.name, "mismatched_generated_syscall_constant")


def _kernel_dispatch_issue(
    canonical_syscalls: tuple[ProtocolConstant, ...],
    kernel_source: str,
) -> ProtocolIssue | None:
    dispatch_block = _extract_odin_proc_block(kernel_source, "syscall_dispatch")
    if dispatch_block is None:
        return _issue("missing_odin_dispatcher", "syscall_dispatch", "Protocol mismatch: kernel/main.odin is missing syscall_dispatch")
    return _missing_kernel_case_issue(canonical_syscalls, dispatch_block)


def _missing_kernel_case_issue(
    canonical_syscalls: tuple[ProtocolConstant, ...],
    dispatch_block: str,
) -> ProtocolIssue | None:
    for syscall in canonical_syscalls:
        if f"case abi.{syscall.name}:" not in dispatch_block:
            return _issue("missing_odin_syscall_case", syscall.name, f"Protocol mismatch: syscall_dispatch is missing abi.{syscall.name}")
    return None


def _rust_live_usage_issue(
    manifest: abi_manifest.AbiManifest,
    service_source: str,
) -> ProtocolIssue | None:
    heartbeat_block = _extract_rust_function_block(service_source, "heartbeat_request")
    status_block = _extract_rust_function_block(service_source, "status_request")
    if heartbeat_block is None:
        return _issue("missing_rust_heartbeat_path", "heartbeat_request", "Protocol mismatch: Rust heartbeat_request is missing")
    if status_block is None:
        return _issue("missing_rust_status_path", "status_request", "Protocol mismatch: Rust status_request is missing")
    return _first_issue(
        _forbidden_constant_issue(f"{heartbeat_block}\n{status_block}", _rust_forbidden_constants(manifest)),
        _missing_anchor_issue(heartbeat_block, (_RUST_USAGE_ANCHORS[0],)),
        _missing_anchor_issue(status_block, (_RUST_USAGE_ANCHORS[1],)),
    )


def _odin_live_usage_issue(
    manifest: abi_manifest.AbiManifest,
    kernel_source: str,
) -> ProtocolIssue | None:
    signal_block = _extract_odin_proc_block(kernel_source, "signal_kernel_heartbeat")
    dispatch_block = _extract_odin_proc_block(kernel_source, "syscall_dispatch")
    if signal_block is None or dispatch_block is None:
        return None
    return _first_issue(
        _forbidden_constant_issue(f"{signal_block}\n{dispatch_block}", _odin_forbidden_constants(manifest)),
        _missing_anchor_issue(signal_block, (_ODIN_USAGE_ANCHORS[0],)),
        _missing_anchor_issue(dispatch_block, (_ODIN_USAGE_ANCHORS[1],)),
    )


def _bridge_path_issue(service_source: str) -> ProtocolIssue | None:
    trap_path = runtime_trap_path_observations(service_source)
    if trap_path["has_local_stub"]:
        return _issue("local_rust_syscall_stub", "invoke_heartbeat_stub", "Protocol mismatch: core_service still defines a local syscall stub")
    if trap_path["has_extern_decl"] and trap_path["has_extern_call"]:
        return None
    return _issue("missing_extern_syscall_bridge", "syscall_entry", "Protocol mismatch: core_service does not declare and call extern syscall_entry")


def _forbidden_constant_issue(
    source: str,
    forbidden_constants: tuple[ForbiddenLocalConstant, ...],
) -> ProtocolIssue | None:
    for forbidden in forbidden_constants:
        if forbidden.pattern.search(source):
            return _issue("hardcoded_syscall_id", forbidden.name, f"Protocol mismatch: {forbidden.detail}")
    return None


def _missing_anchor_issue(
    source: str,
    anchors: tuple[ProtocolUsageAnchor, ...],
) -> ProtocolIssue | None:
    for anchor in anchors:
        if anchor.needle not in source:
            return _issue("missing_live_protocol_usage", anchor.name, f"Protocol mismatch: {anchor.detail}")
    return None


def _rust_forbidden_constants(
    manifest: abi_manifest.AbiManifest,
) -> tuple[ForbiddenLocalConstant, ...]:
    heartbeat_id = _heartbeat_syscall_value(manifest)
    status_id = _status_syscall_value(manifest)
    return (
        ForbiddenLocalConstant(
            "rust_hardcoded_heartbeat_syscall_id",
            re.compile(rf"\blet\s+syscall\s*:\s*abi::K_SYSCALL_ID\s*=\s*{heartbeat_id}\s*;|\binvoke_heartbeat_bridge\s*\(\s*{heartbeat_id}\s*,"),
            "Rust heartbeat_request must not hardcode the DEBUG_HEARTBEAT syscall id",
            _SERVICE_PATH,
        ),
        ForbiddenLocalConstant(
            "rust_hardcoded_status_syscall_id",
            re.compile(rf"\blet\s+syscall\s*:\s*abi::K_SYSCALL_ID\s*=\s*{status_id}\s*;|\binvoke_no_payload_bridge\s*\(\s*{status_id}\s*\)"),
            "Rust status_request must not hardcode the STATUS syscall id",
            _SERVICE_PATH,
        ),
    )


def _odin_forbidden_constants(
    manifest: abi_manifest.AbiManifest,
) -> tuple[ForbiddenLocalConstant, ...]:
    heartbeat_id = _heartbeat_syscall_value(manifest)
    return (
        ForbiddenLocalConstant(
            "odin_hardcoded_heartbeat_syscall_id",
            re.compile(rf"\bsyscall_dispatch\s*\(\s*{heartbeat_id}\s*,|case\s+{heartbeat_id}\s*:"),
            "Odin heartbeat paths must not hardcode the DEBUG_HEARTBEAT syscall id",
            _KERNEL_PATH,
        ),
    )


def _heartbeat_syscall_value(manifest: abi_manifest.AbiManifest) -> int:
    return manifest.constants.syscalls.get("K_SYSCALL_DEBUG_HEARTBEAT", 0)


def _status_syscall_value(manifest: abi_manifest.AbiManifest) -> int:
    return manifest.constants.syscalls.get("K_SYSCALL_STATUS", 0)


def _constant_named(
    constants: tuple[ProtocolConstant, ...],
    name: str,
) -> ProtocolConstant | None:
    return next((constant for constant in constants if constant.name == name), None)


def _extract_rust_function_block(source: str, function_name: str) -> str | None:
    return _extract_braced_block(source, rf"\bfn\s+{re.escape(function_name)}\s*\(")


def _extract_odin_proc_block(source: str, proc_name: str) -> str | None:
    return _extract_braced_block(source, rf"\b{re.escape(proc_name)}\s*::\s*proc\b")


def _extract_braced_block(source: str, start_pattern: str) -> str | None:
    match = re.search(start_pattern, source)
    if match is None:
        return None
    opening_brace = source.find("{", match.end())
    if opening_brace == -1:
        return None
    return _balanced_block(source, opening_brace)


def _balanced_block(source: str, opening_brace: int) -> str | None:
    depth = 0
    for index in range(opening_brace, len(source)):
        depth += source[index] == "{"
        depth -= source[index] == "}"
        if depth == 0:
            return source[opening_brace : index + 1]
    return None


def _first_issue(*issues: ProtocolIssue | None) -> ProtocolIssue | None:
    return next((issue for issue in issues if issue is not None), None)


def _binding_issue(language: str, constant_name: str, reason: str) -> ProtocolIssue:
    return _issue(
        f"{language}_{reason}",
        f"{language}_{constant_name}",
        f"Protocol mismatch: generated {language} binding for {constant_name} is missing or mismatched",
    )


def _issue(reason: str, contract_field: str, detail: str) -> ProtocolIssue:
    return ProtocolIssue(
        reason,
        contract_field,
        detail,
        "Keep canonical syscall ids generated from contracts/kozo_abi.h and used through abi-prefixed constants",
    )


def _failure_result(issue: ProtocolIssue) -> ValidationResult:
    return ValidationResult.fail(
        code=PROTOCOL_MISMATCH,
        detail=issue.detail,
        action=issue.action,
        meta={
            "reason": issue.reason,
            "contract_field": issue.contract_field,
        },
    )
