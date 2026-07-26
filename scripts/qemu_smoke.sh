#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/artifacts/runtime"
BOOT_IMAGE_DIR="$RUNTIME_DIR/boot_image"
DEFAULT_BOOT_ISO="$BOOT_IMAGE_DIR/kozo.iso"
BOOT_ISO="${KOZO_BOOT_ISO:-$DEFAULT_BOOT_ISO}"
PACKAGE_METADATA="$BOOT_IMAGE_DIR/package_metadata.json"
QEMU_LOG="$RUNTIME_DIR/qemu_smoke.log"
QEMU_METADATA="$RUNTIME_DIR/qemu_smoke.metadata.json"
QEMU_STDERR_LOG="$RUNTIME_DIR/qemu_smoke.stderr.log"
QEMU_SUMMARY="$RUNTIME_DIR/qemu_smoke.summary.txt"
BOOT_BLOCKER_REPORT="$RUNTIME_DIR/boot_blocker_report.json"
EXPECTED_MARKER="KOZO_RUNTIME_RETURN_OK"
EARLY_MARKERS=(
  "KOZO_EARLY_0_ENTRY"
  "KOZO_EARLY_1_SERIAL_INIT_START"
  "KOZO_EARLY_2_SERIAL_INIT_OK"
  "KOZO_BOOT_SMOKE_OK"
  "KOZO_STACK_INIT_OK"
  "KOZO_MEMORY_INIT_OK"
  "KOZO_CPU_EXT_STATE_INIT_START"
  "KOZO_CPU_EXT_STATE_INIT_OK"
  "KOZO_SIMD_PROBE_OK"
  "KOZO_USER_MAPPING_INIT_START"
  "KOZO_USER_MAPPING_TABLES_OK"
  "KOZO_USER_MAPPING_PERMISSIONS_OK"
  "KOZO_USER_MAPPING_ACTIVATE_OK"
  "KOZO_USER_MAPPING_SURVIVAL_OK"
  "KOZO_PRIVILEGE_TRANSITION_INIT_START"
  "KOZO_PRIVILEGE_TABLES_OK"
  "KOZO_RING3_ENTER"
  "KOZO_USER_REQUEST_COPY_IN_OK"
  "KOZO_USER_REQUEST_SERVICE_OK"
  "KOZO_USER_RESPONSE_COPY_OUT_OK"
  "KOZO_FIXED_USER_REQUEST_OK"
  "KOZO_RING3_PROBE_OK"
  "KOZO_RING0_RETURN_OK"
  "KOZO_RUNTIME_PROGRESS_ENTRY"
  "KOZO_RUNTIME_INIT_OK"
  "KOZO_RUNTIME_LOOP_ENTER"
  "KOZO_RUNTIME_LOOP_ITER_1"
  "KOZO_RUNTIME_LOOP_ITER_2"
  "KOZO_RUNTIME_LOOP_ITER_3"
  "KOZO_RUNTIME_LOOP_EXIT_OK"
  "KOZO_CAPABILITY_DISPATCH_ENTER"
  "KOZO_RUNTIME_STATUS_QUERY_OK"
  "KOZO_FIRST_CAPABILITY_OK"
  "KOZO_RUNTIME_STATE_UPDATE_ENTER"
  "KOZO_RUNTIME_STATE_UPDATE_OK"
  "KOZO_SECOND_CAPABILITY_OK"
  "$EXPECTED_MARKER"
)
QEMU_TIMEOUT_SECONDS="${KOZO_QEMU_TIMEOUT_SECONDS:-20}"
QEMU_EXIT_CODE=0
QEMU_BIN=""

main() {
  prepare_runtime_directory
  ensure_boot_image_available
  ensure_qemu_available
  run_qemu_and_record_evidence
}

prepare_runtime_directory() {
  mkdir -p "$RUNTIME_DIR"
  : >"$QEMU_LOG"
  : >"$QEMU_STDERR_LOG"
}

ensure_boot_image_available() {
  if [[ -n "${KOZO_BOOT_ISO:-}" ]]; then
    require_boot_image "$BOOT_ISO"
    return
  fi

  "$ROOT/scripts/build_boot_image.sh"
  require_boot_image "$BOOT_ISO"
}

require_boot_image() {
  local image_path=$1

  if [[ -f "$image_path" ]]; then
    return
  fi

  if [[ -f "$PACKAGE_METADATA" ]]; then
    local package_blocker
    package_blocker="$(package_blocker_category)"
    write_blocked_metadata "$package_blocker"
    print_blocker "$package_blocker" "Expected boot image is missing: $image_path"
    return
  fi

  write_blocked_metadata "missing_boot_image"
  print_blocker "missing_boot_image" "Boot image and package metadata are missing"
}

package_blocker_category() {
  python3 - "$PACKAGE_METADATA" <<'PY'
import json
import sys
from pathlib import Path

try:
    metadata = json.loads(Path(sys.argv[1]).read_text())
except (OSError, json.JSONDecodeError):
    print("missing_boot_image")
    raise SystemExit(0)

blocker = metadata.get("blocker_category")
print(blocker if isinstance(blocker, str) else "missing_boot_image")
PY
}

ensure_qemu_available() {
  QEMU_BIN="$(resolve_qemu_bin)"
  if [[ -n "$QEMU_BIN" ]]; then
    return
  fi

  write_blocked_metadata "missing_qemu_tooling"
  print_blocker "missing_qemu_tooling" "Missing QEMU binary: set KOZO_QEMU_BIN or install qemu-system-x86_64"
}

resolve_qemu_bin() {
  local discovered

  if [[ -n "${KOZO_QEMU_BIN:-}" ]]; then
    [[ -x "$KOZO_QEMU_BIN" ]] && printf "%s\n" "$KOZO_QEMU_BIN"
    return
  fi
  if discovered="$(command -v qemu-system-x86_64 2>/dev/null)"; then
    printf "%s\n" "$discovered"
    return
  fi
  homebrew_qemu_bin
}

homebrew_qemu_bin() {
  local brew_prefix
  local candidate

  command -v brew >/dev/null 2>&1 || return
  brew_prefix="$(brew --prefix qemu 2>/dev/null || true)"
  candidate="$brew_prefix/bin/qemu-system-x86_64"
  [[ -x "$candidate" ]] && printf "%s\n" "$candidate"
}

run_qemu_and_record_evidence() {
  local qemu_status

  run_qemu_with_timeout || qemu_status=$?
  qemu_status="${qemu_status:-0}"
  QEMU_EXIT_CODE="$qemu_status"

  if serial_marker_was_observed; then
    write_pass_metadata
    printf "QEMU smoke evidence written to %s\n" "$QEMU_METADATA"
    return
  fi

  record_qemu_blocker "$qemu_status"
}

run_qemu_with_timeout() {
  python3 - "$QEMU_TIMEOUT_SECONDS" "$QEMU_STDERR_LOG" -- \
    "$QEMU_BIN" \
      -machine q35 \
      -accel tcg \
      -m 256M \
      -cpu qemu64 \
      -display none \
      -monitor none \
      -serial "file:$QEMU_LOG" \
      -no-reboot \
      -no-shutdown \
      -cdrom "$BOOT_ISO" <<'PY'
import subprocess
import sys
from pathlib import Path

timeout = float(sys.argv[1])
stdio_log = Path(sys.argv[2])
cmd = sys.argv[4:]

with stdio_log.open("wb") as output:
    process = subprocess.Popen(cmd, stdout=output, stderr=output)
    try:
        raise SystemExit(process.wait(timeout=timeout))
    except subprocess.TimeoutExpired:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise SystemExit(124)
PY
}

serial_marker_was_observed() {
  python3 - "$QEMU_LOG" "${EARLY_MARKERS[@]}" <<'PY'
import sys
from pathlib import Path

text = Path(sys.argv[1]).read_text(errors="replace")
position = -1
for marker in sys.argv[2:]:
    position = text.find(marker, position + 1)
    if position < 0:
        raise SystemExit(1)
PY
}

record_qemu_blocker() {
  local qemu_status=$1
  local blocker

  blocker="$(qemu_blocker_for_status "$qemu_status" "$QEMU_LOG" "$QEMU_STDERR_LOG")"
  write_blocked_metadata "$blocker"
  print_blocker "$blocker" "Expected marker not found: $EXPECTED_MARKER"
}

qemu_blocker_for_status() {
  local qemu_status=$1
  local serial_log=$2
  local stderr_log=$3

  if [[ "$qemu_status" -ne 0 ]]; then
    if [[ "$qemu_status" -eq 124 ]]; then
      classify_boot_blocker "$serial_log" "$stderr_log"
      return
    fi
    printf "qemu_launch_failed\n"
    return
  fi

  classify_boot_blocker "$serial_log" "$stderr_log"
}

classify_boot_blocker() {
  local serial_log=$1
  local stderr_log=$2

  python3 - "$serial_log" "$stderr_log" "${EARLY_MARKERS[@]}" <<'PY'
import sys
from pathlib import Path

serial_log = Path(sys.argv[1])
stderr_log = Path(sys.argv[2])
markers = sys.argv[3:]
serial_text = serial_log.read_text(errors="replace") if serial_log.is_file() else ""
stderr_text = stderr_log.read_text(errors="replace") if stderr_log.is_file() else ""
combined = f"{serial_text}\n{stderr_text}"
combined_lower = combined.lower()
observed = [marker for marker in markers if marker in combined]


def _has_kernel_load_evidence(text: str, observed_markers: list[str]) -> bool:
    return bool(observed_markers) or "entry point" in text or "handoff" in text or "starting kernel" in text


def _has_kernel_open_failure(text: str) -> bool:
    return "failed to open executable" in text or "failed to load executable" in text


def _has_lower_half_phdr_failure(text: str) -> bool:
    return "lower half phdrs are not allowed" in text


if not combined.strip():
    print("limine_not_reached")
elif "limine" not in combined_lower and not observed:
    print("limine_not_reached")
elif _has_lower_half_phdr_failure(combined_lower):
    print("limine_lower_half_phdr")
elif "limine" in combined_lower and _has_kernel_open_failure(combined_lower):
    print("kernel_not_loaded")
elif "limine" in combined_lower and not _has_kernel_load_evidence(combined_lower, observed):
    print("kernel_not_loaded")
elif markers[1] in observed and markers[2] not in observed:
    print("serial_not_initialized")
elif _has_kernel_load_evidence(combined_lower, observed) and markers[0] not in observed:
    print("kernel_entry_not_reached")
elif markers[0] in observed and markers[2] not in observed:
    print("serial_not_initialized")
elif markers[2] in observed and markers[3] not in observed:
    print("marker_not_emitted")
elif markers[3] in observed and markers[4] not in observed:
    print("stack_marker_not_emitted")
elif markers[4] in observed and markers[5] not in observed:
    print("memory_marker_not_emitted")
elif markers[5] in observed and markers[6] not in observed:
    print("cpu_extended_state_initialization_not_completed")
elif markers[6] in observed and markers[7] not in observed:
    print("cpu_extended_state_initialization_not_completed")
elif markers[7] in observed and markers[8] not in observed:
    print("simd_survival_probe_not_completed")
elif markers[8] in observed and markers[9] not in observed:
    print("user_mapping_initialization_not_reached")
elif markers[9] in observed and markers[10] not in observed:
    print("user_mapping_tables_not_validated")
elif markers[10] in observed and markers[11] not in observed:
    print("user_mapping_permissions_not_validated")
elif markers[11] in observed and markers[12] not in observed:
    print("user_mapping_activation_not_completed")
elif markers[12] in observed and markers[13] not in observed:
    print("user_mapping_survival_not_proven")
elif markers[13] in observed and markers[14] not in observed:
    print("privilege_transition_initialization_not_completed")
elif markers[14] in observed and markers[15] not in observed:
    print("privilege_transition_initialization_not_completed")
elif markers[15] in observed and markers[16] not in observed:
    print("ring3_entry_not_completed")
elif markers[16] in observed and markers[17] not in observed:
    print("fixed_user_request_copy_in_not_completed")
elif markers[17] in observed and markers[18] not in observed:
    print("fixed_user_request_service_not_completed")
elif markers[18] in observed and markers[19] not in observed:
    print("fixed_user_response_copy_out_not_completed")
elif markers[19] in observed and markers[20] not in observed:
    print("fixed_user_request_boundary_not_completed")
elif markers[20] in observed and markers[21] not in observed:
    print("ring3_probe_not_completed")
elif markers[21] in observed and markers[22] not in observed:
    print("ring0_return_not_completed")
elif markers[22] in observed and markers[23] not in observed:
    print("runtime_progression_entry_not_reached")
elif markers[23] in observed and markers[24] not in observed:
    print("runtime_initialization_not_proven")
elif markers[24] in observed and markers[25] not in observed:
    print("runtime_loop_entry_not_reached")
elif markers[25] in observed and markers[28] not in observed:
    print("runtime_loop_iteration_incomplete")
elif markers[28] in observed and markers[29] not in observed:
    print("runtime_loop_exit_not_reached")
elif markers[29] in observed and markers[30] not in observed:
    print("capability_dispatch_not_reached")
elif markers[30] in observed and markers[31] not in observed:
    print("runtime_status_query_not_completed")
elif markers[31] in observed and markers[32] not in observed:
    print("first_governed_capability_not_proven")
elif markers[32] in observed and markers[33] not in observed:
    print("runtime_state_update_not_reached")
elif markers[33] in observed and markers[34] not in observed:
    print("runtime_state_update_not_completed")
elif markers[34] in observed and markers[35] not in observed:
    print("second_governed_capability_not_proven")
elif markers[35] in observed and markers[36] not in observed:
    print("runtime_return_not_reached")
elif observed and observed[0] != markers[0]:
    print("qemu_timeout")
else:
    print("qemu_timeout")
PY
}

write_pass_metadata() {
  write_metadata "pass" ""
}

write_blocked_metadata() {
  local blocker=$1
  write_metadata "blocked" "$blocker"
}

write_metadata() {
  local outcome=$1
  local blocker=$2

  python3 - \
    "$QEMU_METADATA" \
    "$outcome" \
    "$blocker" \
    "$EXPECTED_MARKER" \
    "${BOOT_ISO#"$ROOT/"}" \
    "$QEMU_EXIT_CODE" \
    "$QEMU_TIMEOUT_SECONDS" \
    "$QEMU_LOG" \
    "$QEMU_STDERR_LOG" \
    "${EARLY_MARKERS[@]}" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
outcome = sys.argv[2]
blocker = sys.argv[3]
expected_marker = sys.argv[4]
boot_image = sys.argv[5]
qemu_exit_code = int(sys.argv[6])
qemu_timeout_seconds = int(float(sys.argv[7]))
serial_log_file = Path(sys.argv[8])
stderr_log_file = Path(sys.argv[9])
early_markers = sys.argv[10:]
serial_log_path = Path("artifacts/runtime/qemu_smoke.log")
stderr_log_path = Path("artifacts/runtime/qemu_smoke.stderr.log")
serial_text = serial_log_file.read_text(errors="replace") if serial_log_file.is_file() else ""
stderr_text = stderr_log_file.read_text(errors="replace") if stderr_log_file.is_file() else ""
combined_text = f"{serial_text}\n{stderr_text}"
observed_markers = [marker for marker in early_markers if marker in combined_text]


def _limine_entry_point_observed(text: str) -> bool:
    return "elf entry point:" in text.lower()


def _entry_fault_signal(text: str) -> str:
    lowered = text.lower()
    if "triple fault" in lowered:
        return "triple_fault"
    if "page fault" in lowered:
        return "page_fault"
    if "general protection" in lowered:
        return "general_protection_fault"
    if "exception" in lowered:
        return "exception"
    return ""


def _proves(outcome: str) -> list[str]:
    if outcome == "pass":
        return [
            "QEMU launched the KOZO ISO",
            "serial output was captured",
            "the expected KOZO runtime return marker was observed",
        ]
    return [
        "QEMU serial smoke was attempted or checked",
        "QEMU boot evidence remains unclaimed",
    ]


metadata = {
    "version": 0,
    "phase": "v0.4.1",
    "evidence_type": "qemu-serial-smoke",
    "outcome": outcome,
    "boot_protocol": "Limine",
    "architecture": "x86_64",
    "generated_by": "scripts/qemu_smoke.sh",
    "boot_image": boot_image,
    "serial_log": str(serial_log_path),
    "stderr_log": str(stderr_log_path),
    "expected_marker": expected_marker,
    "early_markers": early_markers,
    "observed_markers": observed_markers,
    "earliest_observed_marker": observed_markers[0] if observed_markers else "",
    "limine_entry_point_observed": _limine_entry_point_observed(combined_text),
    "expected_entry_symbol": "_start",
    "entry_marker_expected": early_markers[0],
    "entry_marker_observed": early_markers[0] in observed_markers,
    "entry_fault_signal": _entry_fault_signal(combined_text),
    "qemu_exit_code": qemu_exit_code,
    "timed_out": qemu_exit_code == 124,
    "timeout_seconds": qemu_timeout_seconds,
    "serial_log_bytes": serial_log_file.stat().st_size if serial_log_file.is_file() else 0,
    "stderr_log_bytes": stderr_log_file.stat().st_size if stderr_log_file.is_file() else 0,
    "validator": "qemu_smoke_evidence",
    "proves": _proves(outcome),
    "does_not_prove": [
        "general hardware trap handling",
        "general interrupt handling",
        "complete Odin runtime readiness",
        "dynamic initialization",
        "general stack readiness",
        "general memory management",
        "arbitrary kernel memory writes",
        "concurrent execution",
        "persistent state",
        "authentication",
        "authorization",
        "process privilege isolation",
        "general virtual memory management",
        "dynamic mapping",
        "page-fault recovery",
        "syscall dispatch",
        "Linux compatibility",
        "POSIX compatibility",
        "general userspace execution",
        "process model behavior",
        "VFS behavior",
        "scheduler maturity",
        "ELF loading",
        "file descriptor behavior",
        "production readiness",
    ],
}

if outcome == "blocked":
    metadata["blocker_category"] = blocker

metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
PY
  write_smoke_summary
}

write_smoke_summary() {
  python3 - \
    "$QEMU_SUMMARY" \
    "$QEMU_METADATA" \
    "$QEMU_LOG" \
    "$QEMU_STDERR_LOG" \
    "$BOOT_BLOCKER_REPORT" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
metadata_path = Path(sys.argv[2])
serial_log_path = Path(sys.argv[3])
stderr_log_path = Path(sys.argv[4])
blocker_report_path = Path(sys.argv[5])


def _read_metadata(path: Path) -> dict[str, object]:
    try:
        value = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _read_tail(path: Path, limit: int = 50) -> list[str]:
    if not path.is_file():
        return []
    return path.read_text(errors="replace").splitlines()[-limit:]


def _display_path(path: Path) -> str:
    try:
        return str(path.relative_to(Path.cwd()))
    except ValueError:
        return str(path)


def _blocker(metadata: dict[str, object]) -> str:
    if metadata.get("outcome") == "pass":
        return "none"
    value = metadata.get("blocker_category")
    return value if isinstance(value, str) and value else "unknown"


def _observed_markers(metadata: dict[str, object]) -> list[str]:
    value = metadata.get("observed_markers")
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def _append_marker_lines(lines: list[str], markers: list[str]) -> None:
    if not markers:
        lines.append("  - none")
        return
    for marker in markers:
        lines.append(f"  - {marker}")


def _append_tail(lines: list[str], title: str, tail: list[str]) -> None:
    lines.append("")
    lines.append(title)
    if not tail:
        lines.append("(empty)")
        return
    lines.extend(tail)


metadata = _read_metadata(metadata_path)
summary_lines = [
    "QEMU Smoke Summary",
    "",
    "Outcome",
    f"Outcome: {metadata.get('outcome', 'unknown')}",
    "",
    "Blocker Category",
    f"Blocker: {_blocker(metadata)}",
    "",
    "Observed Markers",
]
_append_marker_lines(summary_lines, _observed_markers(metadata))
summary_lines.extend(
    [
        "",
        "Expected Marker",
        f"Expected Marker: {metadata.get('expected_marker', '')}",
        "",
        "Verifier Result",
        f"Validator: {metadata.get('validator', '')}",
        "",
        "Metadata",
        f"QEMU exit code: {metadata.get('qemu_exit_code', '')}",
        f"Timed out: {metadata.get('timed_out', '')}",
        f"Serial log bytes: {metadata.get('serial_log_bytes', '')}",
        f"Stderr log bytes: {metadata.get('stderr_log_bytes', '')}",
        "",
        "Evidence References",
        _display_path(serial_log_path),
        _display_path(stderr_log_path),
        _display_path(metadata_path),
        _display_path(blocker_report_path),
    ]
)
_append_tail(summary_lines, "Last 50 serial lines", _read_tail(serial_log_path))
_append_tail(summary_lines, "Last 50 stderr lines", _read_tail(stderr_log_path))
summary_path.write_text("\n".join(summary_lines) + "\n")
PY
}

print_blocker() {
  local blocker=$1
  local detail=$2

  printf "BLOCKED: %s\n%s\n" "$blocker" "$detail" >&2
  exit 0
}

main "$@"
