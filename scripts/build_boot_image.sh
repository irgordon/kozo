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
LIMINE_CMD=""
XORRISO_CMD=""
BLOCKER_CATEGORY=""
MISSING_COMPONENTS=()

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

find_cmd() {
  command -v "$1" 2>/dev/null || true
}

find_limine_cmd() {
  local cmd
  cmd="$(find_cmd limine)"
  if [[ -n "$cmd" ]]; then
    printf "%s\n" "$cmd"
    return
  fi
  find_cmd limine-deploy
}

find_limine_artifact() {
  local name="$1"
  local candidate
  for candidate in \
    "$ROOT/boot/limine/$name" \
    "/opt/homebrew/share/limine/$name" \
    "/usr/local/share/limine/$name" \
    "/usr/share/limine/$name"; do
    if [[ -f "$candidate" ]]; then
      printf "%s\n" "$candidate"
      return
    fi
  done
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

detect_iso_tooling() {
  LIMINE_CMD="$(find_limine_cmd)"
  XORRISO_CMD="$(find_cmd xorriso)"
  MISSING_COMPONENTS=()
  local missing_limine_artifact=0

  if [[ -z "$LIMINE_CMD" ]]; then
    MISSING_COMPONENTS+=("Limine executable")
  fi
  if [[ -z "$XORRISO_CMD" ]]; then
    MISSING_COMPONENTS+=("xorriso executable")
  fi
  if [[ -z "$(find_limine_artifact limine-bios-cd.bin)" ]]; then
    missing_limine_artifact=1
    MISSING_COMPONENTS+=("Limine BIOS CD artifact")
  fi
  if [[ -z "$(find_limine_artifact limine-bios.sys)" ]]; then
    missing_limine_artifact=1
    MISSING_COMPONENTS+=("Limine BIOS system artifact")
  fi
  if [[ -z "$(find_limine_artifact limine-uefi-cd.bin)" ]]; then
    missing_limine_artifact=1
    MISSING_COMPONENTS+=("Limine UEFI CD artifact")
  fi
  if (( missing_limine_artifact )); then
    MISSING_COMPONENTS=("Limine bootloader artifacts" "${MISSING_COMPONENTS[@]}")
  fi

  if (( ${#MISSING_COMPONENTS[@]} > 0 )); then
    BLOCKER_CATEGORY="missing_iso_generation_tooling"
  else
    BLOCKER_CATEGORY=""
  fi
}

stage_limine_artifacts() {
  cp "$(find_limine_artifact limine-bios-cd.bin)" "$IMAGE_ROOT/boot/limine/limine-bios-cd.bin"
  cp "$(find_limine_artifact limine-bios.sys)" "$IMAGE_ROOT/boot/limine/limine-bios.sys"
  cp "$(find_limine_artifact limine-uefi-cd.bin)" "$IMAGE_ROOT/boot/limine/limine-uefi-cd.bin"
}

create_bootable_iso() {
  "$XORRISO_CMD" -as mkisofs \
    -b boot/limine/limine-bios-cd.bin \
    -no-emul-boot \
    -boot-load-size 4 \
    -boot-info-table \
    --efi-boot boot/limine/limine-uefi-cd.bin \
    -efi-boot-part \
    --efi-boot-image \
    --protective-msdos-label \
    -o "$BOOT_ISO" \
    "$IMAGE_ROOT"
}

install_limine_bootloader() {
  if [[ "$(basename "$LIMINE_CMD")" == "limine-deploy" ]]; then
    "$LIMINE_CMD" "$BOOT_ISO"
  else
    "$LIMINE_CMD" bios-install "$BOOT_ISO"
  fi
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
  python3 - "$PACKAGE_METADATA" "$BLOCKER_CATEGORY" "$BOOT_ISO" "${MISSING_COMPONENTS[@]}" <<'PY'
import json
import sys
from pathlib import Path

metadata_path = Path(sys.argv[1])
blocker_category = sys.argv[2]
image_path = Path(sys.argv[3])
missing_components = sys.argv[4:]
relative_image_path = "artifacts/runtime/boot_image/kozo.iso"

metadata = {
    "version": 0,
    "phase": "v0.3.6",
    "image_type": "iso",
    "boot_protocol": "Limine",
    "architecture": "x86_64",
    "image_path": relative_image_path,
    "image_exists": image_path.is_file(),
    "generated_by": "scripts/build_boot_image.sh",
    "does_not_prove": [
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

if blocker_category:
    metadata.update(
        {
            "outcome": "blocked",
            "blocker_category": blocker_category,
            "missing_components": missing_components,
            "proves": [
                "bootable ISO generation prerequisites were checked"
            ],
        }
    )
else:
    metadata.update(
        {
            "outcome": "packaged",
            "blocker_category": "missing_qemu_serial_evidence",
            "proves": [
                "bootable ISO generation completed"
            ],
        }
    )

metadata_path.write_text(json.dumps(metadata, indent=2) + "\n")
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
detect_iso_tooling
if [[ -z "$BLOCKER_CATEGORY" ]]; then
  stage_limine_artifacts
  create_bootable_iso
  install_limine_bootloader
  need_file "$BOOT_ISO"
fi
write_manifest
write_package_metadata

printf "Boot image skeleton written to %s\n" "$BOOT_IMAGE_DIR"
printf "Kernel ELF written to %s\n" "$KERNEL_ELF"
printf "Boot image packaging metadata written to %s\n" "$PACKAGE_METADATA"
if [[ -f "$BOOT_ISO" ]]; then
  printf "Bootable ISO written to %s\n" "$BOOT_ISO"
else
  printf "Bootable ISO not produced: %s\n" "$BOOT_ISO"
  printf "Blocker: %s\n" "$BLOCKER_CATEGORY"
fi
printf "This phase does not prove QEMU boot.\n"
