#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/artifacts/runtime"
REPORT_PATH="$RUNTIME_DIR/boot_blocker_report.json"
PACKAGE_METADATA_PATH="$RUNTIME_DIR/boot_image/package_metadata.json"
QEMU_METADATA_PATH="$RUNTIME_DIR/qemu_smoke.metadata.json"

mkdir -p "$RUNTIME_DIR"

python3 - "$ROOT" "$REPORT_PATH" "$PACKAGE_METADATA_PATH" "$QEMU_METADATA_PATH" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
report_path = Path(sys.argv[2])
package_metadata_path = Path(sys.argv[3])
qemu_metadata_path = Path(sys.argv[4])

allowed_qemu_blockers = {
    "limine_not_reached",
    "kernel_not_loaded",
    "kernel_entry_not_reached",
    "serial_not_initialized",
    "marker_not_emitted",
    "qemu_timeout",
    "missing_qemu_tooling",
    "missing_boot_image",
    "qemu_launch_failed",
    "missing_iso_generation_tooling",
}


def load_json(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text())
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


def qemu_passed(metadata: dict[str, object]) -> bool:
    return (
        metadata.get("outcome") == "pass"
        and metadata.get("evidence_type") == "qemu-serial-smoke"
    )


def qemu_blocker(metadata: dict[str, object]) -> str:
    if metadata.get("outcome") != "blocked":
        return ""
    blocker = metadata.get("blocker_category")
    if not isinstance(blocker, str):
        return ""
    if blocker not in allowed_qemu_blockers:
        return ""
    return blocker


def blocker_state() -> dict[str, object]:
    package_metadata = load_json(package_metadata_path)
    qemu_metadata = load_json(qemu_metadata_path)
    qemu_blocker_category = qemu_blocker(qemu_metadata)
    if qemu_blocker_category == "missing_iso_generation_tooling":
        qemu_blocker_category = ""
    if qemu_passed(qemu_metadata):
        return {
            "outcome": "pass",
            "blocker_category": "none",
            "missing_components": [],
            "current_surfaces": [
                "scripts/qemu_smoke.sh captured artifacts/runtime/qemu_smoke.log",
                "artifacts/runtime/qemu_smoke.metadata.json records passing QEMU serial smoke metadata",
            ],
            "next_required_fix": "Do not expand runtime claims beyond QEMU serial smoke until separate hardware trap, userspace, or subsystem evidence exists.",
        }
    if qemu_blocker_category:
        return {
            "outcome": "blocked",
            "blocker_category": qemu_blocker_category,
            "missing_components": [
                "validated QEMU serial smoke execution"
            ],
            "current_surfaces": [
                "scripts/qemu_smoke.sh records exact QEMU serial smoke blocker metadata",
                "artifacts/runtime/qemu_smoke.metadata.json records the current QEMU smoke blocker",
            ],
            "next_required_fix": "Resolve the exact QEMU smoke blocker recorded in artifacts/runtime/qemu_smoke.metadata.json before claiming QEMU boot evidence.",
        }
    if packaged_iso_exists(package_metadata):
        return {
            "outcome": "blocked",
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
        "outcome": "blocked",
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
    "phase": "v0.4.0",
    "outcome": state["outcome"],
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
        "artifacts/runtime/qemu_smoke.metadata.json",
        "artifacts/runtime/qemu_smoke.log",
        "artifacts/runtime/qemu_smoke.stderr.log",
        "scripts/qemu_smoke.sh",
        "scripts/runtime_smoke.sh",
        "docs/RUNTIME_EVIDENCE.md"
    ]
}

report_path.write_text(json.dumps(report, indent=2) + "\n")
print(f"Boot blocker report written to {report_path}")
PY
