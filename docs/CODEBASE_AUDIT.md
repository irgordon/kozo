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

---

# 13. v0.4.95 Code Quality and Style Audit

## 13.1 Date

2026-06-20

## 13.2 Scope

This audit reviewed:

* `harness/validators_impl/`
* `harness/validators.py`
* `harness/registry.py`
* `harness/codes.py`
* `scripts/`
* `tests/`
* `kernel/`
* `userspace/core_service/`
* `contracts/`
* `schemas/`
* `docs/`

The audit focused on stale code, dead code, brittle functions, god files, duplicated logic, and deviations from `docs/CODING_STYLE.md`.

## 13.3 Commands Run

```text
git status --short --branch
find harness scripts tests kernel userspace contracts schemas docs -type f | sort
python3 -m compileall harness scripts tests
python3 -m unittest discover -s tests
rg "TODO|FIXME|HACK|XXX|stub|placeholder|temporary|dead|unused|legacy|compat|shim|pass #|NotImplemented|raise NotImplementedError" harness scripts tests kernel userspace docs contracts schemas
rg "def .*\\(" harness scripts tests
rg "class .*" harness tests
rg "subprocess|shell=True|os.system|eval\\(|exec\\(" harness scripts tests
rg host-specific absolute paths, local user names, local package-manager paths, and platform-specific toolchain tokens
git ls-files "*__pycache__*" "userspace/core_service/target/*"
wc -l harness/validators_impl/validator_coverage.py scripts/qemu_smoke.sh scripts/build_boot_image.sh harness/validators_impl/qemu_smoke_evidence.py
```

## 13.4 Summary

The latest CI evidence before this audit captured:

* `KOZO_EARLY_0_ENTRY`
* `KOZO_EARLY_1_SERIAL_INIT_START`
* `KOZO_EARLY_2_SERIAL_INIT_OK`

It did not capture `KOZO_BOOT_SMOKE_OK`.

The current evidence-backed blocker is `marker_not_emitted`.

The audit did not find a P0 or P1 issue that blocks v0.5.0.

The audit found P2 maintainability risks that should be addressed after the final boot smoke marker phase, unless one directly blocks v0.5.0 implementation.

No safe cleanup was applied.

## 13.5 Findings

| ID | Priority | Area | File(s) | Finding | Evidence | Risk | Recommendation | Fix now |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-095-001 | P2 | Boot marker taxonomy | `scripts/qemu_smoke.sh`, `harness/validators_impl/qemu_smoke_evidence.py`, `tests/test_qemu_smoke_evidence.py`, boot evidence docs | The ordered boot marker list is duplicated across script, validator, tests, and docs. | `KOZO_EARLY_0_ENTRY`, `KOZO_EARLY_1_SERIAL_INIT_START`, `KOZO_EARLY_2_SERIAL_INIT_OK`, and `KOZO_BOOT_SMOKE_OK` appear in multiple proof surfaces. | v0.5.0 marker emission work may require synchronized updates in several files. | Keep v0.5.0 narrowly scoped. After the marker is proven or a narrower blocker is found, centralize marker taxonomy in a small shared source or contract. | No |
| AUDIT-095-002 | P2 | Boot blocker taxonomy | `scripts/qemu_smoke.sh`, `scripts/boot_blocker_report.sh`, `harness/validators_impl/qemu_smoke_evidence.py`, `harness/validators_impl/boot_blocker_report.py`, tests, docs | Exact blocker categories remain duplicated between metadata generation, validation, tests, and release language. | Current categories include `marker_not_emitted`, `serial_not_initialized`, `kernel_entry_not_reached`, `kernel_not_loaded`, and `missing_iso_generation_tooling`. | A future blocker could pass locally but fail in CI or release review if one surface is missed. | Defer taxonomy centralization until after v0.5.0 unless v0.5.0 requires a new blocker category. | No |
| AUDIT-095-003 | P2 | Script size and mixed concerns | `scripts/qemu_smoke.sh`, `scripts/build_boot_image.sh` | Boot evidence scripts mix orchestration, tool checks, embedded Python classification, metadata rendering, and output writing. | `scripts/qemu_smoke.sh` is 360 lines; `scripts/build_boot_image.sh` is 366 lines. | The scripts are readable enough for current work but make future boot evidence changes more error-prone. | After v0.5.0, consider moving classification and metadata rendering into Python helpers while keeping shell scripts as orchestration layers. | No |
| AUDIT-095-004 | P2 | Validator size and abstraction | `harness/validators_impl/validator_coverage.py` | Validator coverage remains a god validator by size and responsibility. | File is 1086 lines and owns contracts, AST parsing, negative test behavior checks, marker metadata, and diagnostics. | Future coverage-governance edits carry high cognitive load and risk of abstraction mixing. | Split into coverage contracts, AST inspection, negative behavior rules, and diagnostics after runtime marker work stabilizes. | No |
| AUDIT-095-005 | P2 | QEMU validator/script policy duplication | `scripts/qemu_smoke.sh`, `harness/validators_impl/qemu_smoke_evidence.py` | Script-generated classification and validator-expected classification are separate implementations. | Both files encode marker/blocker ordering for `serial_not_initialized`, `marker_not_emitted`, and pass outcomes. | Script and validator drift could produce generated metadata that fails verification or, worse, misses a stale blocker. | Keep focused tests around each marker transition for v0.5.0. Extract a shared classifier only after the current marker path is proven. | No |
| AUDIT-095-006 | P2 | Fixture duplication | `tests/test_*contract*.py`, `tests/test_qemu_smoke_evidence.py`, `tests/test_kernel_loadability.py` | Large fixture builders duplicate manifest, contract, blocker, and metadata shapes. | Function scan shows many fixture factories and repeated JSON metadata construction. | ABI/syscall or boot metadata evolution requires multiple synchronized test fixture edits. | Do not refactor fixtures before v0.5.0. Add shared fixtures only when the next contract or marker change forces repeated edits. | No |
| AUDIT-095-007 | P3 | Scan noise | local ignored files | Local structural scans include ignored `__pycache__` and Cargo `target` files, but they are not tracked. | `find` sees generated local byproducts; `git ls-files "*__pycache__*" "userspace/core_service/target/*"` returns no tracked paths. | Audit output is noisy if future scans use raw `find` instead of source or tracked-file scopes. | Prefer `git ls-files` plus selected source roots for future stale/dead-code audits. | No |
| AUDIT-095-008 | P3 | Historical host/path references | `CHANGELOG.md`, `tests/test_host_dependency_portability.py`, `harness/validators_impl/host_dependency_portability.py` | Host-specific tokens remain in historical changelog text and negative tests by design. | The host-specific token scan reports only allowed historical or test-policy references. | Reviewers may mistake historical/test strings for active host dependencies. | Keep host dependency portability validator as the enforcement boundary; no cleanup needed. | No |

## 13.6 Safe Cleanup Applied

No safe cleanup was applied.

The audit found structural issues, not isolated unused imports or trivially removable dead helpers.

## 13.7 Deferred Fixes

Deferred intentionally:

* boot marker taxonomy centralization
* boot blocker taxonomy centralization
* QEMU smoke script split
* boot image script split
* `validator_coverage.py` module split
* shared test fixture extraction
* broad validator refactors

These are deferred because v0.5.0 should focus on the observed `marker_not_emitted` blocker.

## 13.8 v0.5.0 Risk Notes

v0.5.0 should start from the CI-proven marker sequence:

```text
KOZO_EARLY_0_ENTRY
KOZO_EARLY_1_SERIAL_INIT_START
KOZO_EARLY_2_SERIAL_INIT_OK
```

The next runtime question is why `KOZO_BOOT_SMOKE_OK` is absent.

Risk areas for v0.5.0:

* stack setup after early serial initialization
* call from `_start` into `kernel_entry`
* Odin runtime assumptions after higher-half entry
* final marker emission location and dependency chain
* QEMU timeout hiding a fault after serial initialization
* duplicated marker/blocker taxonomy while updating tests and docs

v0.5.0 must not claim QEMU boot unless `KOZO_BOOT_SMOKE_OK` appears in captured QEMU serial output.

---

# 14. v0.4.96 Smoke Evidence Observability Update

Date: 2026-06-20

Status: Completed.

## 14.1 Summary

The v0.4.95 audit noted that runtime smoke diagnosis required manual correlation across multiple CI artifacts. v0.4.96 addresses that observability gap by adding `artifacts/runtime/qemu_smoke.summary.txt`.

The summary is generated from existing QEMU smoke evidence:

* `artifacts/runtime/qemu_smoke.metadata.json`
* `artifacts/runtime/qemu_smoke.log`
* `artifacts/runtime/qemu_smoke.stderr.log`
* `artifacts/runtime/boot_blocker_report.json`

The summary is non-authoritative. It exists to help reviewers quickly classify the current smoke state. Metadata, logs, contracts, validators, and docs remain the governed evidence.

## 14.2 Future Runtime Phase Guidance

Future runtime phases should inspect `artifacts/runtime/qemu_smoke.summary.txt` first, then confirm the summary against metadata and logs before selecting the next implementation target.

For v0.5.0, the expected starting point remains:

```text
KOZO_EARLY_0_ENTRY: present
KOZO_EARLY_1_SERIAL_INIT_START: present
KOZO_EARLY_2_SERIAL_INIT_OK: present
KOZO_BOOT_SMOKE_OK: absent
blocker_category: marker_not_emitted
```

v0.5.0 should still focus on final boot smoke marker emission and must not claim QEMU boot unless `KOZO_BOOT_SMOKE_OK` appears in captured QEMU serial output.

---

# 15. v0.5.1 Governance Planning Alignment

Date: 2026-06-21

Status: Completed.

## 15.1 Current Evidence Review

v0.5.1 reviewed the v0.5.0 local and pushed CI state before further runtime work.

Local evidence:

* `scripts/verify.sh` passes with 39 checks and 0 failures.
* Unit discovery passes with 451 tests.
* Local QEMU smoke metadata remains blocked by `missing_iso_generation_tooling`.

Pushed CI evidence:

* `lint` passed for commit `14fb015`.
* `ci` failed for commit `14fb015` in the `scripts/verify.sh` step.
* The failed run uploaded `kozo-verification-logs`, but this review environment could not authenticate artifact download.

QEMU serial smoke evidence is not promoted from the failed CI run.

## 15.2 Finding Status

| ID | Status | Rationale |
| --- | --- | --- |
| AUDIT-001 | Deferred | Boot blocker taxonomy remains duplicated. Do not centralize it until the v0.5.0 CI verification failure is classified. |
| AUDIT-002 | Resolved | v0.4.7 moved the kernel ELF PT_LOAD virtual addresses to the higher half and local loadability evidence reports no lower-half PHDR blocker. |
| AUDIT-003 | Resolved | Release checklist and required checks now include exact QEMU blocker wording and the v0.5.1 CI failure boundary. |
| AUDIT-004 | Deferred | `validator_coverage.py` remains large by design for now; splitting it is cleanup, not a runtime blocker. |
| AUDIT-005 | Deferred | ABI/syscall fixture duplication is deferred until ABI/syscall maturity work resumes. |
| AUDIT-006 | Deferred | Boot evidence scripts still mix orchestration and metadata rendering; this should wait until the CI smoke failure is classified. |
| AUDIT-007 | Deferred | Script/validator blocker policy duplication remains the highest cleanup risk after CI smoke evidence stabilizes. |
| AUDIT-008 | Resolved | Current-state sections now separate active release blocker, local generated blocker, and historical blockers. |
| AUDIT-009 | Deferred | Scan-noise cleanup remains a future audit-quality improvement. |
| AUDIT-010 | Open | Subprocess usage remains acceptable and should keep explicit argument vectors and bounded timeouts. |
| AUDIT-095-001 | Deferred | Boot marker taxonomy is still duplicated across script, validator, tests, and docs. |
| AUDIT-095-002 | Deferred | Boot blocker taxonomy remains duplicated and should be centralized after CI smoke evidence is green or precisely blocked. |
| AUDIT-095-003 | Deferred | QEMU/build script splitting remains post-triage cleanup. |
| AUDIT-095-004 | Deferred | Validator coverage splitting remains post-triage cleanup. |
| AUDIT-095-005 | Deferred | QEMU script/validator policy duplication remains relevant because the pushed v0.5.0 CI failed in verification. |
| AUDIT-095-006 | Deferred | Shared fixtures should wait until the next ABI/syscall or smoke metadata change forces repeated edits. |
| AUDIT-095-007 | Deferred | Prefer tracked-file scans in future audits. |
| AUDIT-095-008 | Open | Historical host/path references remain allowed when they are clearly historical or test-policy fixtures. |

## 15.3 Removed Drift

v0.5.1 removes these stale planning assumptions:

* `v0.5.1` is no longer ABI/syscall maturity.
* `marker_not_emitted` is no longer the active release blocker after the pushed v0.5.0 CI failure.
* QEMU serial smoke evidence is not promoted from failed CI.
* Local `missing_iso_generation_tooling` is a local generated blocker, not the CI/Linux release blocker.

## 15.4 Next Runtime Risk

The next runtime phase must inspect the failed v0.5.0 CI artifact.

If the full ordered marker sequence appears, the risk is verification or metadata drift.

If the full ordered marker sequence is absent, the risk is the next evidence-backed runtime blocker.

---

# 16. v0.5.2 CI Evidence Access Hardening

Date: 2026-06-21

Status: Completed.

## 16.1 Observability Finding

v0.5.1 exposed an operational gap: GitHub Actions run status was visible, but public log download returned `403`, artifact download returned `401`, and local `gh` tooling was unavailable. That left the active QEMU/verification blocker harder to classify even though CI uploaded evidence artifacts.

## 16.2 Fix Applied

v0.5.2 adds `scripts/ci_evidence_summary.sh` and requires full CI to run it with `if: always()`.

The summary prints:

* latest verification status and failed checks
* QEMU smoke outcome, blocker, observed markers, expected marker, timeout, and byte counts
* QEMU smoke summary text
* last 80 serial log lines
* last 80 stderr log lines
* boot blocker report summary

The summary is non-authoritative and derived from generated artifacts. It does not replace metadata, logs, or validators.

## 16.3 Resolved Risk

Authenticated artifact download remains useful, but first-level triage no longer depends on artifact download, API log access, or local `gh`.

## 16.4 Remaining Risk

The next runtime phase still must classify the actual CI smoke evidence. v0.5.2 only makes that evidence visible in CI logs; it does not alter runtime behavior, marker semantics, QEMU behavior, or blocker taxonomy.

---

# 17. v0.5.4 QEMU Serial Smoke Evidence Promotion

Date: 2026-06-21

Status: Completed.

## 17.1 Evidence Review

CI run `27894312430` captured the full ordered QEMU serial smoke marker sequence:

```text
KOZO_EARLY_0_ENTRY
KOZO_EARLY_1_SERIAL_INIT_START
KOZO_EARLY_2_SERIAL_INIT_OK
KOZO_BOOT_SMOKE_OK
```

The matching QEMU smoke metadata reported `outcome: pass` and `blocker_category: none`.

## 17.2 Resolved Findings

The following boot-path blockers are resolved for the QEMU serial smoke path:

* `limine_lower_half_phdr`
* `kernel_entry_not_reached`
* `serial_not_initialized`
* `marker_not_emitted`

## 17.3 Remaining Findings

`AUDIT-095-001`, `AUDIT-095-002`, and `AUDIT-095-005` remain deferred cleanup risks. The marker and blocker taxonomy is still duplicated across scripts, validators, tests, and docs. v0.5.4 realigns stale validators only; it does not centralize taxonomy or refactor QEMU smoke policy.

## 17.4 Claim Boundary

The promoted evidence proves QEMU serial smoke only. It does not prove Odin runtime execution, stack setup, memory initialization, syscall dispatch, hardware trap execution, Linux compatibility, POSIX compatibility, userspace execution, process model behavior, VFS behavior, scheduler maturity, file descriptor behavior, or production readiness.

---

# 18. v0.6.4 Structural Remediation

Date: 2026-06-21

Status: Completed.

## 18.1 Scope

This remediation reviewed:

* `harness/`
* `scripts/`
* `tests/`
* `kernel/`
* `userspace/`
* `contracts/`
* `schemas/`
* `docs/`

The remediation was limited to mechanical, test-backed cleanup. It did not change runtime behavior, ABI contracts, syscall behavior, linker layout, QEMU smoke behavior, marker semantics, runtime halt behavior, runtime progression contracts, compatibility claims, or production-readiness claims.

## 18.2 Commands Run

```text
git status --short --branch
find harness scripts tests kernel userspace -type f \( -name "*.py" -o -name "*.odin" -o -name "*.asm" -o -name "*.sh" \) -exec wc -l {} +
rg "TODO|FIXME|HACK|XXX|stub|placeholder|temporary|legacy|compat|shim|unused|dead" harness scripts tests kernel userspace contracts schemas docs
rg "pass #|NotImplemented|raise NotImplementedError" harness scripts tests
rg "schema_gen|schema_gen_agent_context" harness scripts tests kernel userspace contracts schemas docs
rg "validators_impl\\.abi|from harness\\.validators_impl import abi|AbiValidator" harness tests docs scripts
python3 -m compileall harness scripts tests
python3 -m unittest discover -s tests
python3 -m json.tool tasks/todo.json
git diff --check
scripts/verify.sh
python3 -m json.tool artifacts/latest_verify.json
```

## 18.3 Summary

No tracked source file exceeded 1200 LOC.

The largest files were:

| File | LOC | Decision |
| --- | ---: | --- |
| `harness/validators_impl/validator_coverage.py` | 1142 | Deferred. Near threshold, but below the split trigger and high risk because it owns validator coverage policy, AST inspection, marker metadata, and diagnostics. |
| `tests/test_qemu_smoke_evidence.py` | 699 | Deferred. Large but fixture-heavy and directly protects QEMU smoke evidence behavior. |
| `tests/test_syscall_table_contract.py` | 586 | Deferred. Large but fixture-heavy and tied to syscall contract coverage. |
| `harness/validators_impl/syscall_table_contract.py` | 549 | Deferred. Below threshold and active validator logic. |
| `tests/test_syscall_table_conformance.py` | 504 | Deferred. Large but active negative coverage. |

The scan found one clearly safe cleanup: two tracked zero-byte generator stubs with no active references.

## 18.4 Findings

| ID | Priority | Area | File(s) | Finding | Evidence | Risk | Fix Applied | Deferred |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| AUDIT-064-001 | P3 | Dead code | `harness/schema_gen.py`, `harness/schema_gen_agent_context.py` | Two tracked Python files were zero-byte generator stubs with no active references. | `wc -l` reported 0 lines; `rg "schema_gen|schema_gen_agent_context" harness scripts tests kernel userspace contracts schemas docs` returned no references. | Leaving empty tracked stubs creates scan noise and suggests generator surfaces that do not exist. | Removed both files. | No |
| AUDIT-064-002 | P2 | Validator size | `harness/validators_impl/validator_coverage.py` | Validator coverage remains the largest source file and is close to the 1200 LOC threshold. | LOC report: 1142 lines. | Splitting it now risks changing validator governance behavior before runtime progression work. | No code change. | Split into contract metadata, AST inspection, behavior checks, and diagnostics only in a dedicated test-backed phase. |
| AUDIT-064-003 | P2 | Test size | `tests/test_qemu_smoke_evidence.py` | QEMU smoke tests are large but active and behavior-protecting. | LOC report: 699 lines. | Fixture extraction could hide behavior changes if done casually. | No code change. | Extract shared smoke metadata fixtures only when a future QEMU evidence change forces repeated edits. |
| AUDIT-064-004 | P3 | Compatibility shim | `harness/validators_impl/abi.py` | ABI validator shim is compatibility-only but active. | `harness/validators.py` and `tests/test_abi.py` import `harness.validators_impl.abi.AbiValidator`. | Removing the shim would cause registry/import churn for no behavior benefit. | No code change. | Keep as a documented stable shim. |
| AUDIT-064-005 | P2 | Scan markers | tests and docs | `dead`, `placeholder`, `stub`, and `compat` matches are mostly intentional negative-test fixtures or non-goal policy text. | `rg` results are concentrated in validator tests, compatibility docs, and non-goal metadata. | Blind cleanup would weaken negative coverage or remove necessary claim-boundary wording. | No code change. | Continue using focused reference checks before deleting any marker-bearing code. |

## 18.5 Remediation Applied

Removed:

```text
harness/schema_gen.py
harness/schema_gen_agent_context.py
```

Proof of non-use:

```text
rg "schema_gen|schema_gen_agent_context" harness scripts tests kernel userspace contracts schemas docs
```

The reference scan returned no active source, script, test, contract, schema, or documentation references.

## 18.6 Deferred Cleanup

Deferred intentionally:

* splitting `harness/validators_impl/validator_coverage.py`
* splitting `tests/test_qemu_smoke_evidence.py`
* centralizing marker and blocker taxonomy
* removing the `abi.py` compatibility shim
* extracting shared ABI/syscall fixture helpers

These are deferred because each requires a dedicated behavior-preserving phase with focused tests.

## 18.7 Verification Result

The cleanup is behavior-preserving:

* Python compileall passes.
* Unit discovery passes.
* Full verification passes.
* JSON task and verification artifacts are valid.
* Whitespace diff check passes.

---

# 19. v0.6.5 Runtime Evidence Taxonomy Centralization

Date: 2026-06-21

Status: Completed.

## 19.1 Scope

This remediation addressed duplicated QEMU serial smoke marker and blocker vocabulary in validators. It added `contracts/runtime_evidence_taxonomy.v0.json` as the governed taxonomy source and migrated `qemu_smoke_evidence` and `boot_blocker_report` to consume taxonomy helper functions.

It did not change runtime behavior, marker strings, marker order, QEMU smoke pass criteria, ABI contracts, syscall behavior, linker layout, runtime halt behavior, runtime progression contracts, compatibility claims, or production-readiness claims.

## 19.2 Finding Status

| ID | Status | Rationale |
| --- | --- | --- |
| AUDIT-001 | Partially resolved | The governed taxonomy now owns blocker category vocabulary and boot blocker validators consume it. Shell scripts, tests, and historical docs still contain literals for metadata generation, fixtures, and review history. |
| AUDIT-095-001 | Partially resolved | The governed taxonomy now owns QEMU smoke marker order and the QEMU smoke validator consumes it. Shell scripts and tests still contain marker literals where they emit or fixture evidence. |
| AUDIT-095-002 | Partially resolved | QEMU smoke and boot blocker validators now consume centralized blocker allowlists from the taxonomy helper. Metadata generators still emit blocker names directly and should be migrated only in a separate low-risk phase. |
| AUDIT-095-005 | Partially resolved | Validator-side policy no longer carries independent marker order or blocker allowlists. Script-side classification remains separate and is intentionally deferred to avoid broad shell rewrites. |

## 19.3 Remediation Applied

Added:

```text
contracts/runtime_evidence_taxonomy.v0.json
schemas/runtime_evidence_taxonomy.schema.json
harness/runtime_evidence_taxonomy.py
harness/validators_impl/runtime_evidence_taxonomy.py
tests/test_runtime_evidence_taxonomy.py
```

Migrated:

* `harness/validators_impl/qemu_smoke_evidence.py` now reads marker order, expected smoke marker, smoke outcomes, and QEMU blocker allowlist from `harness/runtime_evidence_taxonomy.py`.
* `harness/validators_impl/boot_blocker_report.py` now reads boot blocker and kernel ELF blocker categories from `harness/runtime_evidence_taxonomy.py`.

## 19.4 Deferred Cleanup

Deferred intentionally:

* migrating `scripts/qemu_smoke.sh` to consume the taxonomy contract
* migrating `scripts/boot_blocker_report.sh` to consume the taxonomy contract
* extracting shared QEMU smoke test fixtures
* removing historical marker and blocker names from audit/changelog history

These remain deferred because this phase avoided shell rewrites, broad test rewrites, and historical documentation rewrites.

## 19.5 Verification Result

The centralization is behavior-preserving:

* Runtime evidence taxonomy focused tests pass.
* QEMU smoke evidence focused tests pass.
* Boot blocker report focused tests pass.
* Validator coverage focused tests pass.
* Full unit discovery passes.
* Full verification passes.

---

# 20. v0.6.6 Runtime Progression Stage Centralization

Date: 2026-06-21

Status: Completed.

## 20.1 Scope

This remediation addressed progression-state fragmentation risk before stack, memory, runtime, loop, capability, or userspace progression evidence work begins.

It did not change runtime behavior, halt behavior, ABI contracts, syscall behavior, linker layout, QEMU smoke behavior, runtime progression behavior, compatibility claims, or production-readiness claims.

## 20.2 Finding Status

| ID | Status | Rationale |
| --- | --- | --- |
| AUDIT-066-001 | Resolved | `contracts/runtime_progression_stages.v0.json` now owns the canonical future runtime progression stage model. Planning docs describe the model instead of defining independent stage authority. |

## 20.3 Remediation Applied

Added:

```text
contracts/runtime_progression_stages.v0.json
schemas/runtime_progression_stages.schema.json
harness/runtime_progression_stages.py
harness/validators_impl/runtime_progression_stages.py
tests/test_runtime_progression_stages.py
```

The validator checks stage order, unique stage identifiers, prerequisites, evidence requirements, required contracts, required validators, allowed transitions, forbidden shortcuts, and non-goals.

## 20.4 Deferred Cleanup

Deferred intentionally:

* `runtime_progression_contract` and `runtime_progression_entry_contract` still contain historical stage summaries for review context.
* Future stack, memory, runtime, controlled-loop, capability, and userspace planning phases should extend the stage model only through governed contract updates.

These remain deferred because this phase centralizes stage authority without rewriting existing historical planning contracts.

## 20.5 Verification Result

The centralization is behavior-preserving:

* Runtime progression stages focused tests pass.
* Validator coverage focused tests pass.
* Full unit discovery passes.
* Full verification passes.
