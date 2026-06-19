#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUNTIME_DIR="$ROOT/artifacts/runtime"
REPORT_PATH="$RUNTIME_DIR/boot_blocker_report.json"

mkdir -p "$RUNTIME_DIR"

python3 - "$ROOT" "$REPORT_PATH" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
report_path = Path(sys.argv[2])

report = {
    "version": 0,
    "phase": "v0.3.3",
    "outcome": "blocked",
    "evidence_type": "boot-blocker-report",
    "generated_by": "scripts/boot_blocker_report.sh",
    "validator": "boot_blocker_report",
    "blocker_category": "missing_bootable_iso_packaging",
    "missing_components": [
        "bootable Limine ISO or disk image",
        "Limine bootloader artifacts for image installation",
        "ISO tooling such as xorriso or an equivalent image builder",
        "validated QEMU serial smoke execution"
    ],
    "current_surfaces": [
        "kernel/arch/x86_64/boot.asm defines a 64-bit _start symbol",
        "kernel/main.odin exports kernel_entry",
        "kernel/arch/x86_64/serial.odin initializes COM1 serial output",
        "linker/kernel.ld defines the kernel ELF layout",
        "boot/limine.conf defines the Limine boot entry",
        "scripts/build_boot_image.sh stages the boot image skeleton",
        "scripts/qemu_smoke.sh fails closed when no bootable ISO is present",
        "scripts/runtime_smoke.sh proves runtime-adjacent object and symbol evidence"
    ],
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
    "next_required_fix": "Add bootable Limine ISO or disk packaging, then run scripts/qemu_smoke.sh to capture serial output and validate an expected kernel marker before claiming QEMU boot evidence.",
    "inspected_paths": [
        "kernel/arch/x86_64/boot.asm",
        "kernel/main.odin",
        "kernel/arch/x86_64/serial.odin",
        "linker/kernel.ld",
        "boot/limine.conf",
        "scripts/build_boot_image.sh",
        "scripts/qemu_smoke.sh",
        "scripts/runtime_smoke.sh",
        "docs/RUNTIME_EVIDENCE.md"
    ]
}

report_path.write_text(json.dumps(report, indent=2) + "\n")
print(f"Boot blocker report written to {report_path}")
PY
