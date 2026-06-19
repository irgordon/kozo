#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/artifacts/runtime"
REPORT_PATH="$RUNTIME_DIR/boot_blocker_report.json"
PACKAGE_METADATA_PATH="$RUNTIME_DIR/boot_image/package_metadata.json"

mkdir -p "$RUNTIME_DIR"

python3 - "$ROOT" "$REPORT_PATH" "$PACKAGE_METADATA_PATH" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
report_path = Path(sys.argv[2])
package_metadata_path = Path(sys.argv[3])


def package_metadata() -> dict[str, object]:
    if not package_metadata_path.is_file():
        return {}
    try:
        value = json.loads(package_metadata_path.read_text())
    except json.JSONDecodeError:
        return {}
    if not isinstance(value, dict):
        return {}
    return value


def packaged_iso_exists(metadata: dict[str, object]) -> bool:
    return (
        metadata.get("outcome") == "packaged"
        and metadata.get("blocker_category") == "missing_qemu_serial_evidence"
        and (root / "artifacts" / "runtime" / "boot_image" / "kozo.iso").is_file()
    )


def blocker_state() -> dict[str, object]:
    metadata = package_metadata()
    if packaged_iso_exists(metadata):
        return {
            "blocker_category": "missing_qemu_serial_evidence",
            "missing_components": [
                "validated QEMU serial smoke execution"
            ],
            "current_surfaces": [
                "scripts/build_boot_image.sh produced artifacts/runtime/boot_image/kozo.iso",
                "artifacts/runtime/boot_image/package_metadata.json records packaged ISO metadata",
            ],
            "next_required_fix": "Run scripts/qemu_smoke.sh with QEMU available, capture serial output, and validate the expected KOZO marker before claiming QEMU boot evidence.",
        }
    return {
        "blocker_category": "missing_iso_generation_tooling",
        "missing_components": [
            "Limine executable",
            "xorriso executable",
            "Limine bootloader artifacts",
            "bootable ISO artifact",
            "validated QEMU serial smoke execution"
        ],
        "current_surfaces": [
            "scripts/build_boot_image.sh writes package metadata for the blocked ISO tooling attempt",
        ],
        "next_required_fix": "Install or provide the documented Limine executable, Limine bootloader artifacts, and xorriso executable so scripts/build_boot_image.sh can create artifacts/runtime/boot_image/kozo.iso, then run scripts/qemu_smoke.sh to capture serial output before claiming QEMU boot evidence.",
    }


state = blocker_state()

report = {
    "version": 0,
    "phase": "v0.3.6",
    "outcome": "blocked",
    "evidence_type": "boot-blocker-report",
    "generated_by": "scripts/boot_blocker_report.sh",
    "validator": "boot_blocker_report",
    "blocker_category": state["blocker_category"],
    "missing_components": state["missing_components"],
    "current_surfaces": [
        "kernel/arch/x86_64/boot.asm defines a 64-bit _start symbol",
        "kernel/main.odin exports kernel_entry",
        "kernel/arch/x86_64/serial.odin initializes COM1 serial output",
        "linker/kernel.ld defines the kernel ELF layout",
        "boot/limine.conf defines the Limine boot entry",
        "scripts/build_boot_image.sh stages the boot image skeleton",
        "docs/BOOT_TOOLING.md documents Limine and xorriso acquisition paths",
        "scripts/build_boot_image.sh implements the Limine and xorriso ISO generation path",
        "scripts/qemu_smoke.sh fails closed until kozo.iso exists",
        "scripts/runtime_smoke.sh proves runtime-adjacent object and symbol evidence"
    ] + state["current_surfaces"],
    "cannot_claim": [
        "QEMU boot",
        "hardware trap execution",
        "Linux compatibility",
        "POSIX compatibility",
        "general userspace execution",
        "process model behavior",
        "VFS behavior",
        "scheduler maturity",
        "ELF loading",
        "file descriptor behavior",
        "production readiness"
    ],
    "next_required_fix": state["next_required_fix"],
    "inspected_paths": [
        "kernel/arch/x86_64/boot.asm",
        "kernel/main.odin",
        "kernel/arch/x86_64/serial.odin",
        "linker/kernel.ld",
        "boot/limine.conf",
        "docs/BOOT_TOOLING.md",
        "scripts/build_boot_image.sh",
        "artifacts/runtime/boot_image/package_metadata.json",
        "scripts/qemu_smoke.sh",
        "scripts/runtime_smoke.sh",
        "docs/RUNTIME_EVIDENCE.md"
    ]
}

report_path.write_text(json.dumps(report, indent=2) + "\n")
print(f"Boot blocker report written to {report_path}")
PY
