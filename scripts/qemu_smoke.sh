#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/artifacts/runtime"
BOOT_IMAGE_DIR="$RUNTIME_DIR/boot_image"
BOOT_ISO="$BOOT_IMAGE_DIR/kozo.iso"
QEMU_LOG="$RUNTIME_DIR/qemu_smoke.log"
EXPECTED_MARKER="KOZO_KERNEL_ENTRY"

fail() {
  printf "FAIL: %s\n" "$*" >&2
  printf "FAIL: %s\n" "$*" >>"$QEMU_LOG"
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "missing_qemu_tooling: Missing command: $1"
}

need_file() {
  [[ -f "$1" ]] || fail "missing_bootable_iso_packaging: Required file missing: $1"
}

prepare_log() {
  mkdir -p "$RUNTIME_DIR"
  {
    printf "KOZO_QEMU_SMOKE_VERSION=0\n"
    printf "KOZO_QEMU_SMOKE_RESULT=blocked\n"
    printf "KOZO_QEMU_SMOKE_EXPECTED_MARKER=%s\n" "$EXPECTED_MARKER"
    printf "KOZO_QEMU_SMOKE_LOG=%s\n" "artifacts/runtime/qemu_smoke.log"
  } >"$QEMU_LOG"
}

build_boot_skeleton() {
  "$ROOT/scripts/build_boot_image.sh" >>"$QEMU_LOG" 2>&1
}

require_bootable_image() {
  if [[ ! -f "$BOOT_ISO" ]]; then
    fail "missing_bootable_iso_packaging: scripts/build_boot_image.sh stages image-root and kernel ELF but does not create artifacts/runtime/boot_image/kozo.iso"
  fi
}

run_qemu_smoke() {
  qemu-system-x86_64 \
    -machine q35 \
    -accel tcg \
    -m 256M \
    -cpu qemu64 \
    -nographic \
    -monitor none \
    -serial file:"$QEMU_LOG" \
    -no-reboot \
    -cdrom "$BOOT_ISO"
}

validate_serial_marker() {
  grep -F "$EXPECTED_MARKER" "$QEMU_LOG" >/dev/null || fail "qemu_smoke_failed: expected marker not found: $EXPECTED_MARKER"
}

prepare_log
need_cmd qemu-system-x86_64
need_file "$ROOT/scripts/build_boot_image.sh"
build_boot_skeleton
require_bootable_image
run_qemu_smoke
validate_serial_marker

printf "KOZO_QEMU_SMOKE_RESULT=pass\n" >>"$QEMU_LOG"
printf "QEMU smoke evidence written to %s\n" "$QEMU_LOG"
