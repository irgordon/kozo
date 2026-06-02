from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from harness import abi_manifest, syscall_catalog, syscall_class_contract, syscall_table_contract

REPORT_PATH = abi_manifest.ROOT / "docs" / "generated" / "syscall_surface.md"
SOURCE_REFERENCES = (
    "contracts/syscall_catalog.v0.json",
    "contracts/syscall_table_contract.v0.json",
    "contracts/syscall_class_contract.v0.json",
    "contracts/kozo_abi_manifest.json",
)


@dataclass(frozen=True)
class SyscallSurfaceInputs:
    catalog: syscall_catalog.SyscallCatalog
    table: syscall_table_contract.SyscallTableContract
    classes: syscall_class_contract.SyscallClassContract
    manifest: abi_manifest.AbiManifest


def load_report_inputs(root: Path = abi_manifest.ROOT) -> SyscallSurfaceInputs:
    return SyscallSurfaceInputs(
        syscall_catalog.load_syscall_catalog(root / SOURCE_REFERENCES[0]),
        syscall_table_contract.load_syscall_table_contract(root / SOURCE_REFERENCES[1]),
        syscall_class_contract.load_syscall_class_contract(root / SOURCE_REFERENCES[2]),
        abi_manifest.load_abi_manifest(root / SOURCE_REFERENCES[3]),
    )


def render_syscall_surface_report(inputs: SyscallSurfaceInputs) -> str:
    lines = [
        "# KOZO syscall surface",
        "",
        "Generated from:",
        "",
        *_source_reference_lines(),
        "",
        "This document is generated. Do not edit manually.",
        "",
        "## Scope",
        "",
        "This report summarizes currently governed KOZO syscalls only. It does not declare Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness.",
        "",
        "## Summary",
        "",
        *_summary_table_lines(inputs),
        "",
        "## Syscalls",
        "",
        *_syscall_detail_lines(inputs),
        "## Syscall classes",
        "",
        *_class_lines(inputs),
        "",
        "## Notes",
        "",
        "* This report is generated from contracts.",
        "* The catalog summarizes existing governed syscalls and is not the source of truth.",
        "* Runtime behavior is validated by source-level validators.",
        "* No Linux compatibility is claimed.",
        "",
    ]
    return "\n".join(lines)


def expected_report_text(root: Path = abi_manifest.ROOT) -> str:
    return render_syscall_surface_report(load_report_inputs(root))


def write_report(root: Path = abi_manifest.ROOT, output_path: Path = REPORT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(expected_report_text(root))


def _source_reference_lines() -> list[str]:
    return [f"* `{reference}`" for reference in SOURCE_REFERENCES]


def _summary_table_lines(inputs: SyscallSurfaceInputs) -> list[str]:
    rows = [_summary_row(syscall) for syscall in inputs.catalog.syscalls]
    return [
        "| Syscall | Constant | ID | Kind | Class | Payload | Return | Mutates payload | Runtime probe |",
        "| --- | ---: | -: | --- | --- | --- | --- | --- | --- |",
        *rows,
    ]


def _summary_row(syscall: syscall_catalog.CatalogSyscall) -> str:
    return " | ".join(
        (
            f"| {syscall.name}",
            syscall.constant,
            str(syscall.numeric_id),
            syscall.kind,
            syscall.syscall_class,
            _payload_summary(syscall),
            syscall.return_status,
            _mutation_summary(syscall),
            f"{_yes_no(syscall.runtime_probe_present)} |",
        )
    )


def _syscall_detail_lines(inputs: SyscallSurfaceInputs) -> list[str]:
    lines: list[str] = []
    for syscall in inputs.catalog.syscalls:
        lines.extend(_single_syscall_lines(syscall))
    return lines


def _single_syscall_lines(syscall: syscall_catalog.CatalogSyscall) -> list[str]:
    return [
        f"### {syscall.name}",
        "",
        f"* Constant: `{syscall.constant}`",
        f"* Numeric ID: `{syscall.numeric_id}`",
        f"* Kind: `{syscall.kind}`",
        f"* Class: `{syscall.syscall_class}`",
        f"* Payload behavior: {_payload_behavior_text(syscall)}",
        f"* Return status: `{syscall.return_status}`",
        f"* Mutates payload: {_mutation_behavior_text(syscall)}",
        f"* Branch selector: `{syscall.source_branch_selector}`",
        f"* Runtime probe: {_runtime_probe_text(syscall)}",
        "* Proof validators:",
        "",
        *[f"  * `{validator}`" for validator in syscall.proof_validators],
        "",
    ]


def _class_lines(inputs: SyscallSurfaceInputs) -> list[str]:
    return [
        _class_line(syscall_class)
        for syscall_class in inputs.classes.classes
    ]


def _class_line(syscall_class: syscall_class_contract.SyscallClass) -> str:
    examples = ", ".join(syscall_class.valid_examples)
    return (
        f"* `{syscall_class.name}`: payload argument `{syscall_class.payload_argument}`, "
        f"payload layout required `{_yes_no(syscall_class.payload_layout_required)}`, "
        f"request required `{_yes_no(syscall_class.request_required)}`, "
        f"response required `{_yes_no(syscall_class.response_required)}`, "
        f"payload mutation `{syscall_class.mutates_payload}`, "
        f"return status required `{_yes_no(syscall_class.return_status_required)}`, "
        f"examples `{examples}`."
    )


def _payload_summary(syscall: syscall_catalog.CatalogSyscall) -> str:
    layout = syscall.payload_behavior.layout
    return layout if layout is not None else syscall.payload_behavior.argument


def _mutation_summary(syscall: syscall_catalog.CatalogSyscall) -> str:
    if not syscall.mutation_behavior.mutates_payload:
        return "no"
    return ", ".join(syscall.mutation_behavior.fields)


def _payload_behavior_text(syscall: syscall_catalog.CatalogSyscall) -> str:
    layout = syscall.payload_behavior.layout
    if layout is None:
        return f"{syscall.payload_behavior.argument} payload, no layout"
    return f"{syscall.payload_behavior.argument} payload, `{layout}` layout"


def _mutation_behavior_text(syscall: syscall_catalog.CatalogSyscall) -> str:
    if not syscall.mutation_behavior.mutates_payload:
        return "no"
    fields = ", ".join(f"`{field}`" for field in syscall.mutation_behavior.fields)
    return f"yes ({fields})"


def _runtime_probe_text(syscall: syscall_catalog.CatalogSyscall) -> str:
    return "present" if syscall.runtime_probe_present else "absent"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"
