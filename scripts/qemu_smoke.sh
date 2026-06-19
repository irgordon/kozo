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
QEMU_STDIO_LOG="$RUNTIME_DIR/qemu_smoke.qemu.log"
EXPECTED_MARKER="KOZO_BOOT_SMOKE_OK"
QEMU_TIMEOUT_SECONDS="${KOZO_QEMU_TIMEOUT_SECONDS:-20}"

main() {
  prepare_runtime_directory
  ensure_boot_image_available
  ensure_qemu_available
  run_qemu_and_record_evidence
}

prepare_runtime_directory() {
  mkdir -p "$RUNTIME_DIR"
  : >"$QEMU_LOG"
  : >"$QEMU_STDIO_LOG"
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
  if command -v qemu-system-x86_64 >/dev/null 2>&1; then
    return
  fi

  write_blocked_metadata "missing_qemu_tooling"
  print_blocker "missing_qemu_tooling" "Missing command: qemu-system-x86_64"
}

run_qemu_and_record_evidence() {
  local qemu_status

  run_qemu_with_timeout || qemu_status=$?
  qemu_status="${qemu_status:-0}"

  if serial_marker_was_observed; then
    write_pass_metadata
    printf "QEMU smoke evidence written to %s\n" "$QEMU_METADATA"
    return
  fi

  record_qemu_blocker "$qemu_status"
}

run_qemu_with_timeout() {
  python3 - "$QEMU_TIMEOUT_SECONDS" "$QEMU_STDIO_LOG" -- \
    qemu-system-x86_64 \
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
  grep -F "$EXPECTED_MARKER" "$QEMU_LOG" >/dev/null 2>&1
}

record_qemu_blocker() {
  local qemu_status=$1
  local blocker

  blocker="$(qemu_blocker_for_status "$qemu_status")"
  write_blocked_metadata "$blocker"
  print_blocker "$blocker" "Expected marker not found: $EXPECTED_MARKER"
}

qemu_blocker_for_status() {
  local qemu_status=$1

  if [[ "$qemu_status" -eq 124 ]]; then
    printf "qemu_timeout\n"
    return
  fi
  if [[ "$qemu_status" -ne 0 ]]; then
    printf "qemu_launch_failed\n"
    return
  fi

  printf "missing_serial_marker\n"
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

  python3 - "$QEMU_METADATA" "$outcome" "$blocker" "$EXPECTED_MARKER" "${BOOT_ISO#"$ROOT/"}" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
outcome = sys.argv[2]
blocker = sys.argv[3]
expected_marker = sys.argv[4]
boot_image = sys.argv[5]


def _proves(outcome: str) -> list[str]:
    if outcome == "pass":
        return [
            "QEMU launched the KOZO ISO",
            "serial output was captured",
            "the expected KOZO boot smoke marker was observed",
        ]
    return [
        "QEMU serial smoke was attempted or checked",
        "QEMU boot evidence remains unclaimed",
    ]


metadata = {
    "version": 0,
    "phase": "v0.3.8",
    "evidence_type": "qemu-serial-smoke",
    "outcome": outcome,
    "boot_protocol": "Limine",
    "architecture": "x86_64",
    "generated_by": "scripts/qemu_smoke.sh",
    "boot_image": boot_image,
    "serial_log": "artifacts/runtime/qemu_smoke.log",
    "expected_marker": expected_marker,
    "validator": "qemu_smoke_evidence",
    "proves": _proves(outcome),
    "does_not_prove": [
        "hardware trap execution",
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
}

print_blocker() {
  local blocker=$1
  local detail=$2

  printf "BLOCKED: %s\n%s\n" "$blocker" "$detail" >&2
  printf "BLOCKED: %s\n%s\n" "$blocker" "$detail" >>"$QEMU_STDIO_LOG"
  exit 0
}

main "$@"
