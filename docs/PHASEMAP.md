# KOZO Phase Map

Version: 1
Status: Planning
Scope: Release phase sequencing for the path to a scoped KOZO v1.0.0

---

# 1. Purpose

This document defines the release phase sequence from the current governed prototype toward a scoped KOZO v1.0.0 release.

It exists to make release planning explicit, reviewable, and evidence-driven.

---

# 2. Authority

`docs/PHASEMAP.md` owns release phase sequencing.

It does not override:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/COMPATIBILITY.md`
* checked-in contracts
* schemas
* validators

If this document conflicts with an authoritative governance document, the authoritative document wins.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim general userspace execution.

This document does not claim process model, VFS, scheduler, ELF loading, or file descriptor behavior.

This document does not define ABI truth, syscall truth, or runtime behavior.

---

# 4. Release Gates

Every release phase must preserve these gates unless a later governance amendment makes a narrower gate explicit:

* `scripts/verify.sh` passes.
* Python unit discovery passes.
* Odin check/build passes through verification.
* Pinned Rust cargo check passes.
* Generated reports are current.
* `artifacts/latest_verify.json` is valid JSON and reports `pass`.
* Branch protection checks are green for release branches.
* Compatibility claims are scoped and accurate.
* Release evidence is present for the phase being released.

---

# 5. Evidence Required

Release review must include:

* `artifacts/latest_verify.json`
* `artifacts/logs/*.log`
* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `docs/generated/governance_index.md`
* checked-in contracts
* checked-in schemas
* `CHANGELOG.md`
* `docs/PHASEMAP.md`
* `docs/ROADMAP.md`
* CI run URLs or statuses when available
* release notes
* known non-goals list

Detailed evidence rules are owned by `docs/RELEASE_EVIDENCE.md`.

---

# 6. Current Planning State

## Current Proven State

The current local generated evidence proves:

* `scripts/verify.sh` passes locally with 49 checks and 0 failures.
* Unit discovery passes locally with 603 tests after the v0.7.45 probe-hardening coverage expansion.
* The kernel ELF uses higher-half PT_LOAD virtual addresses.
* Local kernel ELF loadability reports no lower-half PHDR blocker.
* The repository source defines the ordered evidence path through `KOZO_RUNTIME_PROGRESS_ENTRY`, Odin-dependent `KOZO_RUNTIME_INIT_OK`, and `KOZO_RUNTIME_RETURN_OK` after the existing boot, stack, and memory markers.
* CI run `27894312430` captured the full ordered marker sequence in QEMU serial output.
* QEMU smoke metadata from that run reports `outcome: pass` and `blocker_category: none`.
* QEMU serial smoke evidence is proven for the narrow smoke path.
* The post-smoke path in `kernel/arch/x86_64/boot.asm` is governed by `contracts/runtime_halt_contract.v0.json`.
* After `KOZO_MEMORY_INIT_OK`, the assembly path enters a deterministic terminal `cli`/`hlt` loop with structural fallthrough forbidden.
* `contracts/runtime_progression_contract.v0.json` governs future halt-to-runtime transition prerequisites and forbids deleting, replacing, bypassing, or jumping around the halt loop without separate progression evidence.
* `contracts/runtime_progression_entry_contract.v0.json` governs the implemented internal assembly-to-Odin boundary, fixed bootstrap context, bounded state probe, exact return status, and terminal continuation.
* `contracts/runtime_evidence_taxonomy.v0.json` governs QEMU serial smoke marker order, smoke outcomes, blocker categories, pass condition, blocked condition, and taxonomy non-goals.
* `contracts/runtime_progression_stages.v0.json` is the sole authority for the acyclic runtime progression order, allowed transitions, and transition ownership from `BOOT_SMOKE` through `USERSPACE_PLANNING`.
* `contracts/stack_initialization_evidence_contract.v0.json` governs controlled stack initialization evidence, and `stack_initialization_evidence` validates the source and marker evidence boundary.
* `contracts/memory_initialization_evidence_contract.v0.json` governs the implemented static-region proof boundary with fixed geometry, explicit zero-fill semantics, a bounded survival probe, and pre-halt marker placement.
* `memory_initialization_evidence` validates the runtime source path and correlates passing QEMU metadata/log evidence or an allowed local tooling blocker.
* v0.7.4 memory evidence is accepted by the CI validator gate; manual artifact inspection was not completed.
* v0.7.45 is accepted by hosted CI run `29459278491`; `RUNTIME_PROGRESSION_ENTRY` and `RUNTIME_INITIALIZATION_EVIDENCE` are proven. `CONTROLLED_RUNTIME_LOOP` remains planned.
* Local QEMU smoke evidence remains blocked by `missing_iso_generation_tooling` because the local environment does not provide the CI Limine/xorriso tooling path.

## Current Active Blocker

There is no active QEMU serial smoke blocker.

The active local generated blocker remains `missing_iso_generation_tooling`.

Historical runtime blockers such as `kernel_not_loaded`, `limine_lower_half_phdr`, `kernel_entry_not_reached`, `serial_not_initialized`, and `marker_not_emitted` are retained only as resolved historical evidence states unless a future CI artifact reintroduces one.

## Next Runtime Phase

The next runtime phase is `v0.7.5 Controlled Runtime Loop`. It must replace neither evidence authority nor security boundaries and must remain separately governed.

---

# 7. Phase Table

| Phase | Name | Purpose | Required Deliverables | Exit Criteria |
| --- | --- | --- | --- | --- |
| `v0.1.0` | Release governance baseline | Define v1.0.0 scope, release evidence requirements, required CI checks, release checklist, README claim cleanup, and generated report review inputs. | `docs/PHASEMAP.md`, `docs/ROADMAP.md`, `docs/RELEASE_EVIDENCE.md`, `docs/RELEASE_CHECKLIST.md`, `docs/REQUIRED_CHECKS.md`, README claim cleanup if needed. | Release checklist and required checks policy are merged, non-goals are preserved, verification passes, generated governance surfaces are refreshed as needed. |
| `v0.2.0` | Runtime execution evidence | Add runtime evidence beyond source-shape proof using the narrowest honest smoke target available. | `docs/RUNTIME_EVIDENCE.md`, runtime smoke command, runtime evidence artifact, validator for runtime evidence, release evidence logs. | Runtime smoke evidence is reproducible, governed, included in release evidence, and clearly states whether it is boot execution or runtime-adjacent object evidence. |
| `v0.2.1` | Runtime evidence packaging | Make runtime evidence reviewable, named, retained, and packageable for release review. | Runtime smoke metadata, runtime evidence packaging instructions, retention policy, release checklist updates. | Runtime smoke log and metadata have a documented live path, release bundle path, validator coverage, and retention guidance. |
| `v0.2.3` | Runtime evidence review gate | Require release reviewers to inspect runtime evidence claims, limits, metadata, release references, and overclaim blockers. | `docs/RUNTIME_EVIDENCE_REVIEW.md`, `runtime_evidence_review` validator, release checklist/evidence/check policy updates. | Runtime evidence review blocks missing, stale, misunderstood, or overclaimed runtime evidence without adding QEMU boot or hardware trap claims. |
| `v0.2.4` | CI/runtime evidence policy alignment | Align full CI, lint, required checks, release checklist, and release evidence policy for runtime smoke evidence. | CI runtime smoke artifact upload, required-check wording, release checklist/evidence policy updates. | Full CI requires runtime smoke through `scripts/verify.sh`, lint stays static unless it runs full verification, release review requires runtime smoke evidence, and no QEMU boot or hardware trap claim is added. |
| `v0.3.0` | Bootable runtime baseline | Attempt a minimal QEMU boot baseline or record the exact blocker preventing an honest boot claim. | `docs/BOOT.md`, `docs/BOOT_BLOCKERS.md`, `artifacts/runtime/boot_blocker_report.json`, `boot_blocker_report` validator. | Boot remains blocked by `missing_boot_protocol_and_image_packaging`; the next fix must add a governed boot protocol, linker script, loader configuration, and boot image packaging before QEMU boot can be claimed. |
| `v0.3.1` | Boot Protocol Selection | Select the initial x86_64 boot protocol and define the minimum implementation plan for resolving the boot blocker. | `docs/decisions/0001-boot-protocol.md`, `docs/BOOT_PROTOCOL.md`, `boot_protocol_decision` validator. | Limine is selected for the initial x86_64 QEMU serial smoke path, and the blocker remains active until linker script, loader configuration, image packaging, and QEMU smoke execution exist. |
| `v0.3.2` | Boot Image Skeleton | Add the minimum Limine image skeleton without claiming boot success until serial output is captured. | `linker/kernel.ld`, `boot/limine.conf`, `scripts/build_boot_image.sh`, `docs/BOOT_IMAGE.md`, `boot_image_skeleton` validator. | A boot image skeleton exists, `missing_boot_protocol_and_image_packaging` is reduced to `missing_qemu_execution_evidence`, and any QEMU claim remains blocked until serial evidence is captured and validated. |
| `v0.3.3` | QEMU serial smoke evidence | Attempt bounded QEMU serial output from the kernel entry path and record the exact blocker if serial evidence cannot honestly be captured. | `scripts/qemu_smoke.sh`, `artifacts/runtime/qemu_smoke.log`, updated boot blocker report. | QEMU serial evidence remains blocked by `missing_bootable_iso_packaging`; the next fix must produce a bootable Limine ISO or disk image before a QEMU boot claim can be made. |
| `v0.3.4` | Bootable image packaging | Attempt bootable Limine ISO packaging and record deterministic package metadata. | `artifacts/runtime/boot_image/package_metadata.json`, `boot_image_packaging` validator, updated blocker state. | Bootable ISO packaging remains blocked by `missing_limine_iso_tooling`; no QEMU boot, serial, compatibility, userspace, or production-readiness claim is added. |
| `v0.3.5` | Limine ISO Tooling Acquisition | Define Limine and xorriso acquisition, provenance, local install, and CI install policy without vendoring opaque binaries. | `docs/BOOT_TOOLING.md`, `boot_tooling` validator, updated blocker state. | Tooling acquisition requirements are documented and validated; blocker narrows to `missing_bootable_iso_generation` without claiming a bootable ISO. |
| `v0.3.6` | Bootable ISO Generation | Implement the ISO generation command using the documented Limine and xorriso tooling path. | Deterministic image packaging command, package metadata, updated blocker state. | ISO generation is implemented but blocked locally by `missing_iso_generation_tooling`; no QEMU boot, serial, compatibility, userspace, or production-readiness claim is added. |
| `v0.3.7` | CI ISO Tooling Install | Install xorriso and pinned Limine source tooling in full CI, run the boot image build path, and upload package metadata plus the ISO when produced. | CI workflow ISO tooling install, `scripts/build_boot_image.sh` env hooks, boot tooling documentation updates. | Full CI attempts ISO generation with reproducible tooling without claiming QEMU boot, serial success, hardware trap execution, compatibility, userspace, subsystem, or production readiness. |
| `v0.3.8` | QEMU Serial Smoke Evidence | Run the generated boot image under QEMU and validate serial evidence if ISO generation is available. | `scripts/qemu_smoke.sh`, `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.metadata.json`, `qemu_smoke_evidence` validator, CI QEMU smoke artifact upload. | QEMU serial smoke records passing marker evidence or an exact blocker without hardware trap, compatibility, userspace, subsystem, or production-readiness claims. |
| `v0.3.9` | Fix QEMU Boot Path | Record the CI-observed QEMU timeout path as an exact blocker and harden QEMU smoke metadata/log validation. | `scripts/qemu_smoke.sh`, `artifacts/runtime/qemu_smoke.stderr.log`, `boot_blocker_report`, `boot_image_packaging`, `qemu_smoke_evidence`, CI QEMU smoke artifact upload. | QEMU smoke accepts a passing kernel-emitted marker or an exact timeout blocker, without claiming QEMU boot until `KOZO_BOOT_SMOKE_OK` appears in captured serial output. |
| `v0.3.10` | Security boundary foundation | Convert security model from policy-only to minimal implementation-backed checks. | Pointer/null boundary enforcement evidence, capability/handle placeholder policy or initial implementation, fault containment expectations, negative tests for unsafe boundary cases. | Security boundary claims are backed by implementation evidence and negative tests. |
| `v0.4.0` | Kernel Entry Reachability | Instrument QEMU, Limine, and KOZO early serial markers to narrow the QEMU timeout blocker. | Documented Limine serial/verbose config, early KOZO markers, v0.4.0 QEMU metadata, reachability blocker taxonomy, QEMU smoke validator coverage. | QEMU smoke records a passing marker or one exact reachability blocker without claiming QEMU boot until `KOZO_BOOT_SMOKE_OK` appears in captured serial output. |
| `v0.4.1` | Fix Limine Kernel Load | Fix the Limine kernel path or ISO layout so Limine can load the staged KOZO kernel ELF without claiming QEMU boot until the marker is captured. | Limine config path fix, QEMU smoke kernel-load blocker classification, focused qemu smoke tests, boot/runtime/release evidence docs. | Limine open failures classify as `kernel_not_loaded`, the configured kernel path matches the ISO layout, and QEMU boot remains unclaimed until `KOZO_BOOT_SMOKE_OK` appears in captured serial output. |
| `v0.4.2` | Fix Kernel Binary Loadability | Inspect the staged kernel ELF and narrow `kernel_not_loaded` without claiming QEMU boot or kernel entry. | `scripts/kernel_elf_report.py`, `artifacts/runtime/kernel_elf_report.json`, `kernel_loadability` validator, ISO filename metadata adjustment, boot/runtime/release evidence docs. | Kernel ELF structure is validated for x86_64 executable format, entry point, `_start` alignment, and PT_LOAD segments; any remaining kernel load failure stays evidence-backed and no QEMU boot claim is added. |
| `v0.4.3` | Host Dependency Portability Gate | Prevent local host paths, Apple-specific assumptions, and undeclared tooling from entering build, verification, ISO, ELF, or QEMU evidence paths. | `host_dependency_portability` validator, focused portability tests, CI/Linux tooling policy docs, boot tooling docs, required checks and release evidence updates. | CI/Linux remains the authoritative portability proof, local macOS stays convenience-only, scripts avoid user-specific absolute paths, and no QEMU boot or compatibility claim is added. |
| `v0.4.4` | Fix Limine ISO/kernel load semantics | Use explicit Limine boot-resource path semantics and validate that the configured kernel path is visible in packaged ISO contents. | `boot/limine.conf`, package metadata path fields, ISO contents report, boot image packaging validator/tests, boot/runtime/release evidence docs. | Limine path visibility is mechanically checked, `kernel_not_loaded` remains active until CI serial evidence proves otherwise, and no QEMU boot claim is added. |
| `v0.4.5` | Limine ELF Load Layout | Classify the CI-observed Limine lower-half PHDR rejection and keep the next boot fix focused on ELF load layout. | Kernel ELF load-layout metadata, `limine_lower_half_phdr` blocker taxonomy, kernel loadability and QEMU smoke validator coverage, boot/runtime/release evidence docs. | Limine path visibility is no longer the active CI blocker; the current blocker is lower-half PT_LOAD layout, with no QEMU boot, kernel entry, or serial initialization claim added. |
| `v0.4.6` | Codebase Structural Audit | Audit stale code, dead code, god files, brittle functions, duplicated logic, boundary violations, and higher-half transition risks before changing linker/runtime layout. | `docs/CODEBASE_AUDIT.md`, structural scan commands, compile/unit/toolchain validation, updated boot-transition findings. | Structural risks are documented without runtime behavior, ABI, syscall, linker, QEMU boot, kernel entry, serial initialization, compatibility, or production-readiness claims. |
| `v0.4.7` | Higher-Half Linker and Entry Transition | Move the kernel ELF PT_LOAD virtual addresses to the higher half while preserving low physical load addresses for the staged Limine kernel image. | Focused linker script changes, regenerated kernel ELF report with VMA/LMA fields, kernel loadability validator coverage, QEMU smoke blocker evidence. | Local ELF evidence no longer reports `limine_lower_half_phdr`; CI QEMU evidence must still determine whether Limine advances to entry/handoff evidence, and no QEMU boot claim is added. |
| `v0.4.8` | Kernel Entry Handoff | Emit the first entry marker from `_start` before stack setup or Odin code so CI QEMU evidence can distinguish entry handoff from later serial initialization. | Assembly-level entry marker, QEMU smoke entry metadata, qemu smoke validator coverage, boot/runtime/release evidence docs. | Kernel entry remains unclaimed until `KOZO_EARLY_0_ENTRY` appears in captured QEMU serial output, and no QEMU boot claim is added. |
| `v0.4.9` | Early Serial Initialization | Emit serial initialization start and OK markers from `_start` before stack setup or Odin code so CI QEMU evidence can distinguish serial initialization from final marker emission. | Assembly-level serial initialization markers, QEMU smoke blocker classification, qemu smoke validator tests, boot/runtime/release evidence docs. | Serial initialization remains unclaimed until `KOZO_EARLY_2_SERIAL_INIT_OK` appears in captured QEMU serial output, and no QEMU boot claim is added. |
| `v0.4.95` | Code Quality and Style Audit | Audit stale code, dead code, brittle functions, god files, duplicated logic, and coding-style drift before fixing final boot smoke marker emission. | `docs/CODEBASE_AUDIT.md`, structural scan commands, compile/unit/toolchain validation, updated v0.5.0 risk notes. | Structural risks are documented without runtime behavior, ABI, syscall, linker, QEMU marker semantic, compatibility, or production-readiness changes. |
| `v0.4.96` | Smoke Evidence Observability | Add a deterministic QEMU smoke summary artifact so CI artifacts expose the current smoke outcome and blocker without manual log correlation. | `artifacts/runtime/qemu_smoke.summary.txt`, QEMU smoke validator coverage, CI upload updates, runtime/release evidence docs. | The summary is non-authoritative and derived from metadata/log evidence; no runtime behavior, marker semantics, compatibility, or production-readiness claim is changed. |
| `v0.5.0` | Boot Smoke Marker Emission | Emit `KOZO_BOOT_SMOKE_OK` after the proven assembly serial initialization marker and require QEMU smoke validation to observe the full ordered marker sequence before pass evidence can support a QEMU smoke claim. | Assembly-level final marker, ordered marker validation, focused QEMU smoke tests, boot/runtime/release evidence docs. | QEMU boot remains unclaimed unless QEMU smoke validation captures `KOZO_EARLY_0_ENTRY`, `KOZO_EARLY_1_SERIAL_INIT_START`, `KOZO_EARLY_2_SERIAL_INIT_OK`, and `KOZO_BOOT_SMOKE_OK` in order. |
| `v0.5.1` | Governance Planning Alignment | Reconcile phase map, roadmap, audit, release evidence, boot blockers, and task state with the actual v0.5.0 local and CI outcomes. | Updated planning/evidence docs, changelog entry, task state update, regenerated governance index. | Local verification remains green, latest pushed CI failure is recorded without promoting QEMU serial smoke evidence, stale ABI/syscall-maturity next-step wording is removed, and the next runtime phase is evidence-driven. |
| `v0.5.2` | CI Evidence Access Hardening | Surface verification, QEMU smoke, serial/stderr, and boot blocker summaries directly in full CI logs so first-level diagnosis does not depend on authenticated artifact download. | `scripts/ci_evidence_summary.sh`, CI `if: always()` summary step, release/evidence/check policy docs, changelog and task state updates. | Failed CI runs print enough smoke evidence to classify the active blocker without `gh` or artifact download, while uploaded artifacts remain enabled and authoritative metadata/logs remain unchanged. |
| `v0.5.3` | CI Smoke Evidence Triage | Inspect the failed v0.5.0/v0.5.2 CI evidence now visible in logs and repair the exact verification or QEMU smoke evidence blocker. | CI evidence diagnosis, updated smoke evidence docs if needed, focused fix only if the CI failure is mechanically identified. | Either CI passes with full ordered QEMU serial smoke evidence, or a narrower evidence-backed runtime blocker is recorded without overclaiming. |
| `v0.5.4` | QEMU Serial Smoke Evidence Promotion | Promote the CI-proven QEMU serial smoke evidence and realign stale validators/docs that still require old boot blockers. | Boot validator realignment, runtime/release/boot docs, audit status update, changelog and task state update. | QEMU serial smoke evidence is proven only as a narrow marker-sequence smoke claim; stale blocker assumptions are removed without runtime, ABI, syscall, compatibility, or production-readiness changes. |
| `v0.6.0` | Runtime Logic Baseline | Govern the immediate post-smoke terminal behavior so the kernel does not fall through after `KOZO_BOOT_SMOKE_OK`. | `contracts/runtime_halt_contract.v0.json`, runtime halt schema/loader/validator/tests, post-smoke assembly halt loop, runtime/release/contract docs. | The final smoke marker is followed by a deterministic terminal halt loop with no structural fallthrough, without ABI/syscall changes or hardware trap, interrupt, scheduler, userspace, compatibility, or production-readiness claims. |
| `v0.6.2` | Runtime Progression Contract Planning | Define governance for any future transition beyond the current boot-smoke halt path without changing runtime behavior. | `contracts/runtime_progression_contract.v0.json`, runtime progression schema/loader/validator/tests, runtime/release/contract docs. | The halt loop remains authoritative until stack initialization evidence, memory initialization evidence, and progression-path evidence are added and validated; no runtime progression, ABI/syscall, compatibility, or production-readiness claim is added. |
| `v0.6.3` | Runtime Progression Entry Design | Reserve the first future runtime progression marker and define readiness requirements without changing runtime behavior. | `contracts/runtime_progression_entry_contract.v0.json`, runtime progression entry schema/loader/validator/tests, runtime/release/contract docs. | `KOZO_RUNTIME_PROGRESS_ENTRY` is documented as reserved and not emitted; the halt loop remains authoritative until stack, memory, and progression-path evidence exists. |
| `v0.6.4` | Code Structure Remediation | Reduce structural debt mechanically before runtime progression behavior work. | `docs/CODEBASE_AUDIT.md` v0.6.4 section, removal of proven-unused zero-byte generator stubs, updated planning/changelog/task state. | No source file exceeds 1200 LOC, dead-code cleanup is proven by reference scans and validation, deferred cleanup is documented, and no runtime, ABI, syscall, linker, marker, compatibility, or production-readiness behavior changes. |
| `v0.6.5` | Runtime Evidence Taxonomy Centralization | Centralize QEMU serial smoke marker and blocker vocabulary before more runtime evidence changes. | `contracts/runtime_evidence_taxonomy.v0.json`, runtime evidence taxonomy schema/loader/validator/tests, migrated QEMU smoke and boot blocker validators, updated evidence/contract/audit docs. | Marker strings, marker order, QEMU smoke pass criteria, runtime behavior, ABI, syscall, linker, halt, and progression contracts remain unchanged while validators consume the governed taxonomy. |
| `v0.6.6` | Runtime Progression Stages Contract | Centralize future runtime progression stage definitions before stack, memory, runtime, or capability evidence work. | `contracts/runtime_progression_stages.v0.json`, runtime progression stages schema/loader/validator/tests, planning/evidence/contract docs. | Stage ordering, prerequisites, evidence, ownership, allowed transitions, forbidden shortcuts, and non-goals are governed without changing runtime behavior, halt behavior, ABI, syscall behavior, QEMU smoke, compatibility, or production-readiness claims. |
| `v0.6.7` | Stack Initialization Evidence Planning | Define the future evidence boundary for stack initialization before runtime progression implementation. | `contracts/stack_initialization_evidence_contract.v0.json`, stack initialization evidence schema/loader/validator/tests, progression contract alignment, planning/evidence/contract docs. | `KOZO_STACK_INIT_OK` is reserved but not emitted, stack setup remains unimplemented, and no runtime behavior, ABI, syscall, linker, QEMU smoke, compatibility, or production-readiness claim changes. |
| `v0.7.0` | Stack Initialization Evidence | Implement the controlled boot stack proof and extend the governed marker sequence to `KOZO_STACK_INIT_OK`. | Static boot stack setup in `_start`, `stack_initialization_evidence`, runtime evidence taxonomy update, progression contract alignment, runtime/release/contract docs. | Controlled stack establishment and marker emission are proven without memory initialization, Odin runtime execution, halt replacement, userspace, compatibility, or production-readiness claims. |
| `v0.7.1` | Memory Initialization Evidence Planning | Define the future evidence boundary for controlled memory initialization before any memory setup implementation. | `contracts/memory_initialization_evidence_contract.v0.json`, memory initialization evidence schema/loader/validator/tests, progression contract alignment, planning/evidence/contract docs. | `KOZO_MEMORY_INIT_OK` is reserved but not emitted, memory initialization remains unimplemented, and no runtime behavior, ABI, syscall, linker, QEMU smoke, compatibility, or production-readiness claim changes. |
| `v0.7.2` | Runtime Progression Model Reconciliation | Remove the stack/entry dependency cycle and enforce an acyclic, monotonic, authority-backed progression graph without changing runtime behavior. | Reconciled progression contracts, graph-level stage validation, focused negative tests, aligned planning/audit/task state. | `STACK_INITIALIZATION_EVIDENCE` is proven, `MEMORY_INITIALIZATION_EVIDENCE` and `RUNTIME_PROGRESSION_ENTRY` remain planned, every prerequisite points backward, and every transition has one owner. |
| `v0.7.3` | Memory Evidence Contract Hardening | Strengthen the planned memory evidence boundary before implementation work begins. | Hardened memory evidence contract, implementability requirements, focused validator tests, planning alignment. | Memory evidence remains planning-only, `KOZO_MEMORY_INIT_OK` remains unclaimed, and implementation is not scheduled until the proof boundary is mechanically complete. |
| `v0.7.4` | Memory Initialization Evidence | Implement the hardened minimal controlled-memory proof without expanding into memory management. | Static controlled region, full-region zero fill, bounded sentinel probe, runtime marker emission, governed memory evidence validator. | `KOZO_MEMORY_INIT_OK` is captured after the contract-defined proof and before the unchanged halt loop; no paging, allocator, virtual-memory, Odin-runtime, userspace, compatibility, or production claim is added. |
| `v0.7.45` | Runtime Progression Entry and Minimal Runtime Initialization | Add a bounded internal assembly-to-Odin call after memory evidence and return to the authoritative halt path. | Calling-convention contract, fixed bootstrap context, bounded Odin state probe, fixed serial bridge, progression evidence validator, ordered CI markers. | CI captures `KOZO_RUNTIME_PROGRESS_ENTRY`, Odin-dependent `KOZO_RUNTIME_INIT_OK`, and `KOZO_RUNTIME_RETURN_OK`; exact status zero returns to the terminal halt path without allocator, scheduler, userspace, interrupt, compatibility, or production claims. |
| `v1.0.0-rc.1` | Release candidate hardening | Freeze release scope and release gates, produce evidence bundle, confirm branch protection, and dry-run release notes. | Release evidence bundle, completed release checklist, current generated reports, changelog/release notes dry run, all required CI checks green. | Release candidate can be reviewed without adding new scope. |
| `v1.0.0` | Scoped production release | Release only the proven, scoped KOZO surface. | Final release evidence bundle, final changelog and release notes, passing required gates, explicit non-goals. | v1.0.0 claims only evidence-backed behavior and preserves all compatibility non-goals. |

---

# 8. v1.0.0 Constraints

`v1.0.0` must remain scoped to proven behavior.

It must not claim:

* Linux compatibility unless separately implemented and proven
* POSIX completeness
* general userspace execution
* process model behavior
* VFS behavior
* scheduler maturity
* ELF loading
* file descriptor behavior
* production readiness beyond the scoped release definition

---

# 9. Release Checklist

Before release:

* Confirm phase exit criteria are satisfied.
* Complete `docs/RELEASE_CHECKLIST.md`.
* Confirm `docs/REQUIRED_CHECKS.md` required checks pass.
* Confirm release gates pass.
* Confirm generated reports are current.
* Confirm release evidence bundle is present.
* Confirm changelog and release notes describe only evidence-backed behavior.
* Confirm compatibility non-goals are present.
* Confirm no generated artifact was manually edited.
* Confirm branch protection checks are green.
