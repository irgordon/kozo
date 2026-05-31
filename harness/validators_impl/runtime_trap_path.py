from __future__ import annotations

from dataclasses import dataclass
import re
from pathlib import Path

from harness.codes import OK, RUNTIME_TRAP_PATH_INVALID
from harness.validator import BaseValidator, ValidationResult

_ROOT = Path(__file__).resolve().parents[2]
_SERVICE_PATH = _ROOT / "userspace" / "core_service" / "src" / "main.rs"

_LOCAL_STUB_SIGNATURE = "fn invoke_heartbeat_stub("
_STUB_MODE_MARKER = "STUB MODE"
_EXTERN_BLOCK = re.compile(r'extern\s*"C"\s*\{(?P<body>.*?)\}', re.DOTALL)
_EXTERN_SYSCALL_FN = re.compile(
    r"fn\s+syscall_entry\s*\(\s*id\s*:\s*u64\s*,\s*payload\s*:\s*\*mut\s+abi::HeartbeatPayload\s*\)\s*->\s*u64\s*;",
)
_EXTERN_SYSCALL_CALL = re.compile(r"syscall_entry\s*\(")
_FUNCTION_PATTERN_TEMPLATE = r"fn\s+{name}\s*\([^)]*\)(?:\s*->\s*[^\s{{]+)?\s*\{{"


@dataclass(frozen=True)
class RuntimePathAnchor:
    name: str
    needle: str
    detail: str


@dataclass(frozen=True)
class OrderedRuntimeAnchor:
    name: str
    needle: str
    detail: str


_HEARTBEAT_REQUEST_ANCHORS = (
    OrderedRuntimeAnchor(
        "payload_initialization",
        "let mut payload = abi::HeartbeatPayload {",
        "heartbeat_request must construct the heartbeat payload on the live path",
    ),
    OrderedRuntimeAnchor(
        "request_sequence_sentinel",
        "sequence: 0xCAFEFEED",
        "heartbeat_request must initialize sequence to 0xCAFEFEED",
    ),
    OrderedRuntimeAnchor(
        "request_timestamp_sentinel",
        "timestamp: 0",
        "heartbeat_request must initialize timestamp to 0",
    ),
    OrderedRuntimeAnchor(
        "request_status_bits_initialization",
        "status_bits: abi::K_INVALID",
        "heartbeat_request must initialize status_bits to abi::K_INVALID",
    ),
    OrderedRuntimeAnchor(
        "heartbeat_syscall_constant",
        "let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;",
        "heartbeat_request must select the generated heartbeat syscall id",
    ),
    OrderedRuntimeAnchor(
        "bridge_helper_call",
        "let status = invoke_heartbeat_bridge(syscall, &mut payload);",
        "heartbeat_request must call invoke_heartbeat_bridge with the live payload",
    ),
    OrderedRuntimeAnchor(
        "return_path_validation",
        "return validate_heartbeat_return_path(status, &payload);",
        "heartbeat_request must pass returned status and payload to return-path validation",
    ),
)

_BRIDGE_HELPER_ANCHORS = (
    RuntimePathAnchor(
        "extern_bridge_call",
        "syscall_entry(u64::from(syscall), payload as *mut abi::HeartbeatPayload)",
        "invoke_heartbeat_bridge must call extern syscall_entry with the syscall id and payload pointer",
    ),
    RuntimePathAnchor(
        "bridge_status_cast",
        "as abi::K_STATUS",
        "invoke_heartbeat_bridge must return the bridge result as abi::K_STATUS",
    ),
)


def runtime_trap_path_observations(rust_source: str, asm_source: str | None = None) -> dict[str, bool]:
    _ = asm_source
    extern_block = _EXTERN_BLOCK.search(rust_source)
    has_extern_decl = extern_block is not None and _EXTERN_SYSCALL_FN.search(extern_block.group("body")) is not None
    call_count = len(_EXTERN_SYSCALL_CALL.findall(rust_source))
    heartbeat_block = _extract_rust_function_block(rust_source, "heartbeat_request")
    bridge_block = _extract_rust_function_block(rust_source, "invoke_heartbeat_bridge")
    return {
        "has_local_stub": _LOCAL_STUB_SIGNATURE in rust_source,
        "has_stub_marker": _STUB_MODE_MARKER in rust_source,
        "has_extern_decl": has_extern_decl,
        "has_extern_call": call_count > (1 if has_extern_decl else 0),
        "has_live_heartbeat_block": heartbeat_block is not None,
        "has_live_bridge_call": (
            bridge_block is not None
            and _BRIDGE_HELPER_ANCHORS[0].needle in bridge_block
        ),
    }


def _extract_rust_function_block(source: str, function_name: str) -> str | None:
    pattern = re.compile(_FUNCTION_PATTERN_TEMPLATE.format(name=re.escape(function_name)))
    match = pattern.search(source)
    if match is None:
        return None
    block_end = _matching_brace_index(source, match.end() - 1)
    if block_end < 0:
        return None
    return source[match.start():block_end + 1]


def _matching_brace_index(source: str, open_brace_index: int) -> int:
    depth = 0
    for index in range(open_brace_index, len(source)):
        if source[index] == "{":
            depth += 1
        if source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _validate_extern_contract(rust_source: str) -> ValidationResult | None:
    observations = runtime_trap_path_observations(rust_source)
    if observations["has_local_stub"]:
        return _failure_result(
            "local_stub_present",
            "rust_local_stub",
            "core_service still defines a local heartbeat syscall stub",
        )
    if observations["has_stub_marker"]:
        return _failure_result(
            "stub_marker_present",
            "rust_stub_marker",
            "core_service still advertises STUB MODE after the runtime trap path phase",
        )
    if not observations["has_extern_decl"]:
        return _failure_result(
            "missing_extern_bridge_declaration",
            "extern_syscall_entry",
            "core_service must declare extern syscall_entry(id, payload) -> u64",
        )
    return None


def _validate_live_heartbeat_block(rust_source: str) -> ValidationResult | None:
    heartbeat_block = _extract_rust_function_block(rust_source, "heartbeat_request")
    if heartbeat_block is None:
        return _failure_result(
            "missing_live_heartbeat_block",
            "heartbeat_request",
            "core_service must define the live heartbeat_request path",
        )
    return _ordered_anchor_result(heartbeat_block, rust_source, _HEARTBEAT_REQUEST_ANCHORS)


def _validate_bridge_helper_block(rust_source: str) -> ValidationResult | None:
    bridge_block = _extract_rust_function_block(rust_source, "invoke_heartbeat_bridge")
    if bridge_block is None:
        return _failure_result(
            "missing_bridge_helper_block",
            "invoke_heartbeat_bridge",
            "core_service must define the live bridge helper",
        )
    return _required_anchor_result(bridge_block, rust_source, _BRIDGE_HELPER_ANCHORS)


def _ordered_anchor_result(
    block: str,
    source: str,
    anchors: tuple[OrderedRuntimeAnchor, ...],
) -> ValidationResult | None:
    cursor = 0
    for anchor in anchors:
        index = block.find(anchor.needle, cursor)
        if index < 0:
            return _runtime_anchor_failure(block, source, anchor)
        cursor = index + len(anchor.needle)
    return None


def _required_anchor_result(
    block: str,
    source: str,
    anchors: tuple[RuntimePathAnchor, ...],
) -> ValidationResult | None:
    for anchor in anchors:
        if anchor.needle not in block:
            return _runtime_anchor_failure(block, source, anchor)
    return None


def _runtime_anchor_failure(
    block: str,
    source: str,
    anchor: RuntimePathAnchor | OrderedRuntimeAnchor,
) -> ValidationResult:
    if anchor.needle in block:
        return _failure_result("out_of_order_runtime_anchor", anchor.name, anchor.detail)
    if anchor.needle in source:
        return _failure_result("dead_snippet_outside_live_path", anchor.name, anchor.detail)
    return _failure_result("missing_runtime_anchor", anchor.name, anchor.detail)


def _failure_result(reason: str, contract_field: str, detail: str) -> ValidationResult:
    return ValidationResult.fail(
        code=RUNTIME_TRAP_PATH_INVALID,
        detail=f"Runtime trap path invalid: {reason}: {contract_field}: {detail}",
        action="Keep the live heartbeat_request path routed through the extern syscall_entry bridge",
        meta={"reason": reason, "contract_field": contract_field},
    )


class RuntimeTrapPathValidator(BaseValidator):
    name = "runtime_trap_path"
    subsystem = "runtime_trap_path"

    def validate(self, artifact_bundle):
        _ = artifact_bundle
        rust_source = _SERVICE_PATH.read_text()

        for result in (
            _validate_extern_contract(rust_source),
            _validate_bridge_helper_block(rust_source),
            _validate_live_heartbeat_block(rust_source),
        ):
            if result is not None:
                return result

        return ValidationResult.pass_(
            code=OK,
            detail="Rust heartbeat_request constructs the request payload and reaches the extern syscall_entry bridge",
        )
