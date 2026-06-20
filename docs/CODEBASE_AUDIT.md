# KOZO Codebase Structural Audit

Version: 1
Status: Authoritative
Scope: Structural risks in source, scripts, validators, tests, contracts, schemas, and governance documents before the higher-half boot layout transition

---

# 1. Purpose

This document records the v0.4.6 codebase structural audit.

The audit exists to reduce risk before changing the kernel linker and entry layout for the next boot phase.

It identifies stale code, dead code, god files, brittle functions, duplicated logic, boundary risks, and boot-path risks.

---

# 2. Authority

This document is an audit report.

It records findings and recommendations.

It does not override:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/CODING_STYLE.md`
* `docs/VALIDATION.md`
* `docs/GENERATED_ARTIFACTS.md`
* `docs/COMPATIBILITY.md`
* `docs/SECURITY_MODEL.md`

Generated reports remain non-authoritative.

---

# 3. Non-Goals

This audit does not change runtime behavior.

This audit does not change ABI contracts.

This audit does not change syscall behavior.

This audit does not change linker layout.

This audit does not attempt the higher-half transition.

This audit does not claim QEMU boot.

This audit does not claim kernel entry.

This audit does not claim serial initialization.

This audit does not claim hardware trap execution.

This audit does not claim Linux compatibility, POSIX compatibility, userspace execution, process model behavior, VFS behavior, scheduler maturity, ELF loading, file descriptor behavior, or production readiness.

---

# 4. Audit Date

2026-06-20

---

# 5. Commands Run

```text
git status --short --branch
find . -type f | sort
find harness scripts tests kernel userspace contracts schemas docs -type f | sort
python3 -m compileall harness scripts tests
python3 -m unittest discover -s tests
rg "TODO|FIXME|HACK|XXX|stub|placeholder|temporary|dead|unused|legacy|compat|shim|pass #|NotImplemented|raise NotImplementedError" harness scripts tests kernel userspace docs contracts schemas
rg "def .*\\(" harness scripts tests
rg "class .*" harness tests
rg "subprocess|shell=True|os.system|eval\\(|exec\\(" harness scripts tests
rg host-specific absolute paths, local user names, local package-manager paths, and platform-specific toolchain tokens
rg "\\bPHASEMAP.md\\b|\\bROADMAP.md\\b" .
rg "missing_boot_protocol_and_image_packaging|missing_bootable_iso_packaging|missing_limine_iso_tooling|missing_bootable_iso_generation|kernel_not_loaded|limine_lower_half_phdr|qemu_timeout" docs harness scripts tests tasks CHANGELOG.md
odin check kernel
pinned Rust cargo check for userspace/core_service against x86_64-unknown-none
python3 -m json.tool tasks/todo.json
git diff --check
scripts/verify.sh
python3 -m json.tool artifacts/latest_verify.json
python3 -m json.tool artifacts/runtime/kernel_elf_report.json
python3 -m json.tool artifacts/runtime/qemu_smoke.metadata.json
python3 -m json.tool artifacts/runtime/boot_blocker_report.json
```

---

# 6. Summary

The repository is structurally strong in these areas:

* registered validators have marker-level negative coverage
* generated reports are validated against deterministic renderers
* host-specific path assumptions are mechanically checked
* runtime, ABI, syscall, and boot evidence claims are separated from compatibility claims
* the pre-v0.4.7 CI boot failure was classified as `limine_lower_half_phdr`
* v0.4.7 local ELF evidence clears the lower-half PHDR report and now requires CI QEMU evidence to classify the next blocker

The audit did not find a P0 blocker.

The audit found P1 risks that should be addressed before or during the higher-half linker/entry transition:

* boot blocker taxonomy is duplicated across shell scripts, validators, tests, and release docs
* release checklist and required-check wording had not yet been updated for the v0.4.5 `limine_lower_half_phdr` blocker
* the next higher-half transition crosses linker, assembly entry, Odin entry, serial output, and Limine assumptions

No cleanup was applied in this phase. The findings are recorded for targeted follow-up.

---

# 7. Risk Categories

| Priority | Meaning |
| --- | --- |
| P0 | Correctness, security, or release blocker |
| P1 | Likely to break higher-half transition or CI |
| P2 | Maintainability problem |
| P3 | Cleanup or documentation polish |

---

# 8. Findings

| ID | Priority | Area | File(s) | Finding | Evidence | Risk | Recommendation | Fix now |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-001 | P1 | Boot taxonomy | `scripts/qemu_smoke.sh`, `scripts/boot_blocker_report.sh`, `harness/validators_impl/qemu_smoke_evidence.py`, `harness/validators_impl/boot_blocker_report.py`, `harness/validators_impl/boot_image_packaging.py`, `harness/validators_impl/boot_image_skeleton.py`, `harness/validators_impl/boot_tooling.py`, tests, docs | Boot blocker names are duplicated across scripts, validators, tests, and docs. | `rg` found 152 references to active boot blocker names and reachability states. | Higher-half work may add another blocker or state transition; duplicated lists increase drift risk. | Define a narrow boot blocker taxonomy source or contract before expanding the boot state machine further. Keep validators deterministic and update tests around the taxonomy source. | No |
| AUDIT-002 | P1 | Boot layout | `linker/kernel.ld`, `kernel/arch/x86_64/boot.asm`, `kernel/main.odin`, `kernel/arch/x86_64/serial.odin`, `scripts/kernel_elf_report.py` | The pre-v0.4.7 ELF entry and PT_LOAD virtual addresses were lower-half, while Limine rejects lower-half PHDRs. | Pre-v0.4.7 `artifacts/runtime/kernel_elf_report.json` recorded `_start` and entry at `0x200000`, PT_LOAD virtual addresses starting at `0x200000`, and `limine_lower_half_phdr`; v0.4.7 moved local ELF virtual addresses higher-half and preserved low physical load addresses. | Higher-half layout changes may still break entry assumptions, early serial access, and the kernel handoff path until CI QEMU evidence advances beyond the load-layout blocker. | Inspect the next CI QEMU artifact before touching serial or syscall logic. If Limine reaches entry, continue with the observed marker state; otherwise classify the next loader/handoff blocker. | No |
| AUDIT-003 | P1 | Release gate wording | `docs/RELEASE_CHECKLIST.md`, `docs/REQUIRED_CHECKS.md` | Pre-v0.4.7 release/check wording listed earlier QEMU blockers without `limine_lower_half_phdr`. | v0.4.7 updated release checklist and required-check wording to include `limine_lower_half_phdr` as an exact no-boot-claim blocker. | Release review now has the latest exact blocker vocabulary, but future boot blockers still risk drift while taxonomy remains duplicated. | Keep blocker wording aligned until a centralized taxonomy source is introduced after the higher-half transition. | No |
| AUDIT-004 | P2 | Validator size | `harness/validators_impl/validator_coverage.py` | Validator coverage is a god file by size and responsibility. | File is about 1085 lines and owns contracts, AST scanning, behavioral-negative detection, marker metadata, and diagnostics. | Future validator governance changes are more likely to be error-prone. | Split into contract definitions, AST inspection, negative-test behavior rules, and diagnostics after the boot layout transition. | No |
| AUDIT-005 | P2 | Fixture duplication | `tests/test_syscall_table_contract.py`, `tests/test_syscall_table_conformance.py`, `tests/test_syscall_class_contract.py`, `tests/test_syscall_boundary_contract.py`, `tests/test_protocol_contract_alignment.py`, `tests/test_layout_parity.py`, `tests/test_abi_manifest.py` | Large JSON/manifest fixture builders are duplicated across tests. | Function-size scan found fixture builders up to 72 lines and repeated manifest/table construction patterns. | Test updates for ABI/syscall expansion may require many synchronized fixture edits. | Add shared test fixture helpers only when the next ABI/syscall expansion requires them. Avoid preemptive refactor. | No |
| AUDIT-006 | P2 | Script scope | `scripts/build_boot_image.sh`, `scripts/qemu_smoke.sh`, `scripts/boot_blocker_report.sh`, `scripts/verify.sh` | Runtime evidence scripts mix tool probing, build orchestration, metadata generation, blocker classification, and output writing. | Script sizes are about 366, 336, 233, and 321 lines respectively. | Higher-half changes may require carefully preserving metadata behavior while changing build/link details. | Keep higher-half changes localized to linker/build inputs first. Defer script splitting until after QEMU reaches or fails the new handoff path. | No |
| AUDIT-007 | P2 | Boundary between scripts and validators | `scripts/qemu_smoke.sh`, `harness/validators_impl/qemu_smoke_evidence.py`, `scripts/boot_blocker_report.sh`, `harness/validators_impl/boot_blocker_report.py` | Scripts and validators both encode blocker classification policy. | QEMU classification logic exists in shell-embedded Python and Python validators. | The script may generate metadata a validator later rejects if the two copies drift. | Centralize classification into a Python helper callable by scripts and validators, but only after the higher-half transition reveals the next blocker shape. | No |
| AUDIT-008 | P2 | Historical blocker wording | `docs/BOOT.md`, `docs/BOOT_BLOCKERS.md`, `docs/RUNTIME_EVIDENCE.md`, `docs/PHASEMAP.md`, `docs/ROADMAP.md`, `CHANGELOG.md`, `tasks/todo.json` | Historical blockers are retained alongside current blocker language. | `rg` finds old blockers such as `missing_boot_protocol_and_image_packaging`, `missing_bootable_iso_packaging`, and `missing_limine_iso_tooling`. | Historical wording is useful but can be mistaken for active state during review. | Keep historical wording where it is explicitly marked previous, but ensure current-state sections name the active local and CI blockers first. | No |
| AUDIT-009 | P3 | Local generated byproducts | working tree, ignored files | Local `find` output includes `__pycache__` and Cargo `target` files. | `find` sees these files, while `git ls-files` reports no tracked `__pycache__` or `userspace/core_service/target` files. | Review scans can be noisy if they are not scoped to tracked files or source roots. | Prefer `git ls-files` or ignore-aware scans for future structural audits. No repository cleanup is needed. | No |
| AUDIT-010 | P3 | Subprocess use | `scripts/qemu_smoke.sh`, `scripts/kernel_elf_report.py`, `harness/validators_impl/entrypoint_validator.py`, `harness/validators_impl/host_dependency_portability.py` | Subprocess usage is present but bounded. | `rg` found direct `subprocess.run`/`Popen` usage and no `shell=True`, `os.system`, `eval`, or `exec` calls in source paths. | Subprocess use is expected for tool invocation but should remain explicit and shell-free. | Keep current pattern. If adding new subprocess calls for higher-half evidence, preserve explicit argument vectors and bounded timeouts. | No |

---

# 9. Recommended Fixes

Recommended before or during v0.4.7:

1. Keep v0.4.7 focused on higher-half linker and entry layout only.
2. Keep release/check docs aligned with the next CI-observed blocker after v0.4.7.
3. Avoid adding new boot blocker names without updating QEMU metadata, boot blocker report generation, validators, tests, release evidence, release checklist, and required checks together.
4. Re-run full CI and inspect `qemu_smoke.log`, `qemu_smoke.stderr.log`, `qemu_smoke.metadata.json`, `kernel_elf_report.json`, and `boot_blocker_report.json` before selecting the next runtime fix.

Recommended after the higher-half transition stabilizes:

1. Centralize boot blocker taxonomy.
2. Split `validator_coverage.py` into smaller policy, AST-inspection, and diagnostic modules.
3. Extract shared test fixture builders for ABI/syscall contracts.
4. Consider moving script-embedded metadata rendering into Python helpers that scripts call.

---

# 10. Deferred Fixes

Deferred intentionally:

* higher-half linker layout
* `_start` or `kernel_entry` behavior changes
* serial initialization changes
* QEMU smoke pass promotion
* validator architecture refactors
* boot blocker taxonomy centralization
* fixture deduplication
* release/check blocker wording cleanup

These are deferred to avoid combining broad cleanup with the audit.

---

# 11. Higher-Half Transition Risk Notes

The next runtime phase should treat the higher-half transition as an architectural boot change.

Risks to review explicitly:

* `linker/kernel.ld` currently starts sections at `2M`
* `_start` currently equals `0x200000`
* PT_LOAD virtual addresses are lower-half
* physical load addresses need explicit reasoning if virtual addresses move higher-half
* assembly entry may assume identity-addressed code or data
* Odin code and serial output may rely on addresses being valid immediately after Limine handoff
* QEMU evidence must prove each transition step before later serial or marker fixes are attempted

Minimum expected evidence for the higher-half phase:

* regenerated `artifacts/runtime/kernel_elf_report.json`
* PT_LOAD virtual addresses no longer lower-half, if the transition succeeds
* QEMU smoke metadata that either reaches `KOZO_EARLY_0_ENTRY` or records a narrower blocker
* no QEMU boot claim unless `KOZO_BOOT_SMOKE_OK` appears in captured serial output

---

# 12. Safe Cleanup Applied

No cleanup was applied in this phase.

The audit intentionally avoids broad refactoring before the higher-half transition.
