#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/artifacts/runtime"
BOOT_IMAGE_DIR="$RUNTIME_DIR/boot_image"
WORK_DIR="$BOOT_IMAGE_DIR/work"
IMAGE_ROOT="$BOOT_IMAGE_DIR/image-root"
KERNEL_ELF="$IMAGE_ROOT/boot/kozo/kozo-kernel.elf"
MANIFEST="$BOOT_IMAGE_DIR/manifest.json"
PACKAGE_METADATA="$BOOT_IMAGE_DIR/package_metadata.json"
BOOT_ISO="$BOOT_IMAGE_DIR/kozo.iso"
BRIDGE_TARGET="freestanding_amd64_sysv"

fail() {
  printf "FAIL: %s\n" "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

need_file() {
  [[ -f "$1" ]] || fail "Required file missing: $1"
}

prepare_directories() {
  rm -rf "$BOOT_IMAGE_DIR"
  mkdir -p "$WORK_DIR" "$IMAGE_ROOT/boot/limine" "$IMAGE_ROOT/boot/kozo"
}

build_kernel_objects() {
  odin build "$ROOT/kernel" \
    "-target:$BRIDGE_TARGET" \
    -build-mode:obj \
    "-out:$WORK_DIR/kernel.o"
  nasm -f elf64 "$ROOT/kernel/arch/x86_64/boot.asm" -o "$WORK_DIR/boot.o"
  nasm -f elf64 "$ROOT/kernel/arch/x86_64/syscall.asm" -o "$WORK_DIR/syscall.o"
  nasm -f elf64 "$ROOT/kernel/arch/x86_64/memory.asm" -o "$WORK_DIR/memory.o"
}

link_kernel_elf() {
  lld -flavor gnu \
    -nostdlib \
    -T "$ROOT/linker/kernel.ld" \
    -o "$KERNEL_ELF" \
    "$WORK_DIR"/*.o
}

stage_limine_config() {
  cp "$ROOT/boot/limine.conf" "$IMAGE_ROOT/boot/limine/limine.conf"
}

write_manifest() {
  python3 - "$MANIFEST" <<'PY'
import json
import sys
from pathlib import Path

manifest = {
    "version": 0,
    "phase": "v0.3.2",
    "artifact_type": "boot-image-skeleton",
    "image_root": "artifacts/runtime/boot_image/image-root",
    "kernel_elf": "artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf",
    "limine_config": "artifacts/runtime/boot_image/image-root/boot/limine/limine.conf",
    "does_not_prove": [
        "QEMU boot",
        "hardware trap execution",
        "Linux compatibility",
        "POSIX compatibility",
        "userspace execution",
        "process model behavior",
        "VFS behavior",
        "scheduler maturity",
        "ELF loading",
        "file descriptor behavior",
        "production readiness"
    ]
}

Path(sys.argv[1]).write_text(json.dumps(manifest, indent=2) + "\n")
PY
}

write_package_metadata() {
  python3 - "$PACKAGE_METADATA" <<'PY'
import json
import sys
from pathlib import Path

metadata = {
    "version": 0,
    "phase": "v0.3.5",
    "outcome": "blocked",
    "blocker_category": "missing_bootable_iso_generation",
    "image_type": "iso",
    "boot_protocol": "Limine",
    "architecture": "x86_64",
    "image_path": "artifacts/runtime/boot_image/kozo.iso",
    "image_exists": False,
    "generated_by": "scripts/build_boot_image.sh",
    "missing_components": [
        "ISO generation command integration",
        "bootable ISO artifact"
    ],
    "proves": [
        "boot image skeleton packaging prerequisites were checked"
    ],
    "does_not_prove": [
        "boot image packaging completed",
        "QEMU boot",
        "serial output",
        "hardware trap execution",
        "Linux compatibility",
        "POSIX compatibility",
        "userspace execution",
        "process model behavior",
        "VFS behavior",
        "scheduler maturity",
        "ELF loading",
        "file descriptor behavior",
        "production readiness"
    ]
}

Path(sys.argv[1]).write_text(json.dumps(metadata, indent=2) + "\n")
PY
}

need_cmd odin
need_cmd nasm
need_cmd lld
need_cmd cp
need_cmd python3
need_file "$ROOT/linker/kernel.ld"
need_file "$ROOT/boot/limine.conf"

prepare_directories
build_kernel_objects
link_kernel_elf
stage_limine_config
write_manifest
write_package_metadata

printf "Boot image skeleton written to %s\n" "$BOOT_IMAGE_DIR"
printf "Kernel ELF written to %s\n" "$KERNEL_ELF"
printf "Boot image packaging metadata written to %s\n" "$PACKAGE_METADATA"
printf "Bootable ISO not produced: %s\n" "$BOOT_ISO"
printf "This phase does not prove QEMU boot.\n"
