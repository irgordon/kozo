#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ARTIFACTS_DIR="$ROOT/artifacts"
RUNTIME_DIR="$ARTIFACTS_DIR/runtime"
LOG_FILE="$RUNTIME_DIR/runtime_smoke.log"
METADATA_FILE="$RUNTIME_DIR/runtime_smoke.metadata.json"
WORK_DIR="$RUNTIME_DIR/runtime-smoke-work"
BRIDGE_TARGET="freestanding_amd64_sysv"

mkdir -p "$RUNTIME_DIR"

cleanup() {
  rm -rf "$WORK_DIR"
}

trap cleanup EXIT

fail() {
  printf "FAIL: %s\n" "$*" >&2
  if [[ -f "$LOG_FILE" ]]; then
    cat "$LOG_FILE" >&2
  fi
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

start_log() {
  : >"$LOG_FILE"
  {
    printf "KOZO_RUNTIME_SMOKE_VERSION=1\n"
    printf "KOZO_RUNTIME_SMOKE_KIND=runtime-adjacent-object-symbol-smoke\n"
    printf "KOZO_RUNTIME_SMOKE_SCOPE=freestanding_amd64_sysv_object\n"
    printf "KOZO_RUNTIME_SMOKE_LIMITATION=not_boot_or_hardware_trap_execution\n"
  } >>"$LOG_FILE"
}

build_kernel_objects() {
  cleanup
  mkdir -p "$WORK_DIR"
  odin build "$ROOT/kernel" \
    "-target:$BRIDGE_TARGET" \
    -build-mode:obj \
    "-out:$WORK_DIR/kernel.o" >>"$LOG_FILE" 2>&1
  nasm -f elf64 "$ROOT/kernel/arch/x86_64/boot.asm" -o "$WORK_DIR/boot.o" >>"$LOG_FILE" 2>&1
  nasm -f elf64 "$ROOT/kernel/arch/x86_64/syscall.asm" -o "$WORK_DIR/syscall.o" >>"$LOG_FILE" 2>&1
}

append_evidence() {
  {
    printf "\n[files]\n"
    find "$WORK_DIR" -maxdepth 1 -type f | sort
    printf "\n[nm]\n"
    nm -g "$WORK_DIR"/*.o
    printf "\n[strings]\n"
    strings "$WORK_DIR"/*.o
  } >>"$LOG_FILE" 2>&1
}

require_log_marker() {
  local marker=$1
  if ! grep -F "$marker" "$LOG_FILE" >/dev/null; then
    fail "Runtime smoke evidence is missing marker: $marker"
  fi
  printf "KOZO_RUNTIME_SMOKE_MARKER=%s\n" "$marker" >>"$LOG_FILE"
}

write_result() {
  printf "KOZO_RUNTIME_SMOKE_RESULT=pass\n" >>"$LOG_FILE"
}

write_metadata() {
  cat >"$METADATA_FILE" <<'JSON'
{
  "version": 0,
  "evidence_type": "runtime-adjacent-object-symbol-smoke",
  "artifact": "artifacts/runtime/runtime_smoke.log",
  "generated_by": "scripts/runtime_smoke.sh",
  "validator": "runtime_smoke_evidence",
  "proves": [
    "freestanding x86_64 kernel object generation",
    "required entry symbol presence",
    "dispatcher symbol presence",
    "bridge symbol presence",
    "serial marker presence in binary evidence"
  ],
  "does_not_prove": [
    "QEMU boot",
    "hardware trap execution",
    "Linux compatibility",
    "userspace execution",
    "process model",
    "VFS behavior",
    "scheduler maturity",
    "ELF loading",
    "file descriptor behavior",
    "production readiness"
  ]
}
JSON
}

need_cmd odin
need_cmd nasm
need_cmd nm
need_cmd strings
need_cmd grep
need_cmd find

start_log
build_kernel_objects
append_evidence

require_log_marker "_start"
require_log_marker "kernel_entry"
require_log_marker "syscall_entry"
require_log_marker "syscall_dispatch"
require_log_marker "SYSCALL[DEBUG_HEARTBEAT] Recv Seq: 0x"
require_log_marker "SYSCALL[DEBUG_HEARTBEAT] New Time: 0x"

write_result
write_metadata
printf "Runtime smoke evidence written to %s\n" "$LOG_FILE"
printf "Runtime smoke metadata written to %s\n" "$METADATA_FILE"
