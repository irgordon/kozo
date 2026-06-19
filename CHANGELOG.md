# Changelog

## v0.3.6 - 2026-06-19

**Status:** Bootable ISO generation blocked by missing local ISO tooling.

### Added

* Added a Limine/xorriso ISO generation path to `scripts/build_boot_image.sh`.
* Added v0.3.6 package metadata for either successful ISO generation or a blocked missing-tooling result.
* Updated `boot_image_packaging` validation to distinguish a real packaged ISO from an honest blocked ISO-generation attempt.

### Changed

* Narrowed the active boot blocker from `missing_bootable_iso_generation` to `missing_iso_generation_tooling` for this local environment.
* Updated boot, boot image, blocker, runtime evidence, release evidence, phase map, and roadmap docs to record that ISO generation is implemented but cannot complete until Limine artifacts and xorriso are available.

### Notes

* This change does not add a bootable ISO in the current environment.
* This change does not add QEMU boot evidence.
* This change does not add serial success evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change ABI contracts or syscall behavior.

## v0.3.5 - 2026-06-19

**Status:** Limine ISO tooling acquisition.

### Added

* Added `docs/BOOT_TOOLING.md` to define the Limine and xorriso acquisition path, local development path, CI installation path, provenance requirements, tool verification, and future ISO generation path.
* Added `boot_tooling` validation and focused negative coverage for missing Limine documentation, xorriso documentation, local install path, CI install path, provenance, blocker state, and diagnostic quality.

### Changed

* Narrowed the active boot blocker from `missing_limine_iso_tooling` to `missing_bootable_iso_generation`.
* Updated boot, boot image, boot blocker, runtime evidence, release evidence, phase map, and roadmap docs to record the tooling acquisition policy without claiming ISO generation.

### Notes

* This change does not add a bootable ISO.
* This change does not add QEMU boot evidence.
* This change does not add serial success evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change ABI contracts or syscall behavior.

## v0.3.4 - 2026-06-19

**Status:** Bootable ISO packaging blocked by missing Limine ISO tooling.

### Added

* Added boot image package metadata at `artifacts/runtime/boot_image/package_metadata.json`.
* Added `boot_image_packaging` validation for package metadata, blocker alignment, documentation references, non-goals, and diagnostic quality.
* Updated full verification to regenerate boot image packaging metadata through `scripts/build_boot_image.sh`.

### Changed

* Narrowed the active blocker from `missing_bootable_iso_packaging` to `missing_limine_iso_tooling`.
* Updated boot, runtime evidence, release evidence, phase map, and roadmap docs to record that ISO packaging prerequisites are now checked, but no bootable ISO is produced yet.

### Notes

* This change does not add a bootable ISO.
* This change does not add QEMU boot evidence.
* This change does not add serial success evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change ABI contracts or syscall behavior.

## v0.3.3 - 2026-06-19

**Status:** QEMU serial smoke blocked by missing bootable image packaging.

### Added

* Added `scripts/qemu_smoke.sh` as a bounded QEMU smoke command that fails closed when no bootable image exists.
* Added QEMU smoke blocker documentation across boot, runtime evidence, release evidence, release checklist, required checks, phase map, and roadmap documents.

### Changed

* Refined the active boot blocker from `missing_qemu_execution_evidence` to `missing_bootable_iso_packaging`.
* Updated `boot_blocker_report`, `boot_image_skeleton`, and `boot_protocol_decision` validation expectations to require the refined blocker state.

### Notes

* This change does not add QEMU boot evidence.
* This change does not add serial marker evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change ABI contracts or syscall behavior.

## v0.3.2 - 2026-06-19

**Status:** Boot image skeleton.

### Added

* Added `linker/kernel.ld` as the minimal x86_64 kernel linker script with `_start` entry and text, rodata, data, and bss layout.
* Added `boot/limine.conf` as the initial Limine configuration for the future QEMU serial smoke path.
* Added `scripts/build_boot_image.sh` to build and stage the boot image skeleton under `artifacts/runtime/boot_image/`.
* Added `docs/BOOT_IMAGE.md` as the authoritative boot image skeleton document.
* Added `boot_image_skeleton` validation and focused negative coverage for the linker script, Limine config, build script, boot image docs, blocker state, and diagnostic quality.

### Changed

* Reduced the active boot blocker from `missing_boot_protocol_and_image_packaging` to `missing_qemu_execution_evidence`.
* Updated boot, runtime evidence, release evidence, phase map, and roadmap docs for the boot image skeleton.

### Notes

* This change does not add QEMU boot evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change ABI contracts or syscall behavior.

## v0.3.1 - 2026-06-19

**Status:** Boot protocol selection.

### Added

* Added `docs/decisions/0001-boot-protocol.md` as the accepted boot protocol decision record.
* Added `docs/BOOT_PROTOCOL.md` as the authoritative boot protocol plan.
* Added `boot_protocol_decision` as a registered validator for the selected boot protocol, alternatives, non-goals, boot blocker relationship, and next boot phase references.
* Added focused negative coverage for missing decision records, wrong protocol, missing alternatives, missing non-goals, missing active-blocker wording, missing v0.3.2 phase references, and diagnostic quality.

### Changed

* Selected Limine as the initial x86_64 boot protocol for the planned QEMU serial smoke path.
* Updated boot docs, runtime evidence docs, release evidence docs, phase map, and roadmap to keep the boot blocker active while recording the protocol decision.

### Notes

* The `missing_boot_protocol_and_image_packaging` blocker remains active until linker script, loader configuration, image packaging, and QEMU smoke execution exist.
* This change does not add QEMU boot evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change runtime behavior, ABI contracts, or syscall behavior.

## v0.3.0 - 2026-06-19

**Status:** Bootable runtime baseline blocked by missing boot protocol and image packaging.

### Added

* Added `docs/BOOT.md` and `docs/BOOT_BLOCKERS.md` to record the current boot baseline and exact blocker preventing an honest QEMU boot claim.
* Added `scripts/boot_blocker_report.sh` to generate `artifacts/runtime/boot_blocker_report.json`.
* Added `boot_blocker_report` as a registered validator for the v0.3.0 boot blocker report and documentation references.
* Added focused negative coverage for missing, malformed, incomplete, and diagnostically weak boot blocker reports.

### Changed

* Updated full verification, release evidence, release checklist, required checks, phase map, roadmap, and CI artifact upload policy to include the boot blocker report while boot remains blocked.

### Notes

* Boot feasibility result: blocked.
* Exact blocker: `missing_boot_protocol_and_image_packaging`.
* Missing components: linker script, boot protocol, loader configuration, and boot image packaging.
* This change does not add QEMU boot evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change runtime behavior, ABI contracts, or syscall behavior.

## v0.2.4 - 2026-06-19

**Status:** CI/runtime evidence policy alignment.

### Changed

* Aligned full CI, required checks, release checklist, release evidence policy, runtime evidence docs, and runtime evidence review docs around the runtime smoke evidence requirement.
* Updated full CI artifact upload to include `artifacts/runtime/runtime_smoke.log` and `artifacts/runtime/runtime_smoke.metadata.json`.
* Documented that runtime smoke evidence is required in full CI through `scripts/verify.sh`, required for release review, and not required in lint unless lint runs full verification.

### Notes

* Runtime evidence remains scoped as `runtime-adjacent-object-symbol-smoke`.
* This change does not add QEMU boot evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change runtime behavior, ABI contracts, or syscall behavior.

## v0.2.3 - 2026-06-19

**Status:** Runtime evidence review gate.

### Added

* Added `docs/RUNTIME_EVIDENCE_REVIEW.md` as the release-review gate for runtime evidence scope, paths, metadata, validators, non-goals, release blockers, and claim examples.
* Added `runtime_evidence_review` as a registered validator for runtime evidence review policy, release references, required non-goals, and metadata alignment.
* Added focused negative coverage for missing review policy fields, missing release gates, metadata non-goal drift, and diagnostic quality.

### Changed

* Updated release evidence, release checklist, required checks, phase map, and roadmap documents to require runtime evidence review before release.

### Notes

* Runtime evidence remains scoped as `runtime-adjacent-object-symbol-smoke`.
* This change does not add QEMU boot evidence.
* This change does not add hardware syscall/trap execution evidence.
* This change does not add Linux compatibility, POSIX compatibility, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change runtime behavior, ABI contracts, or syscall behavior.

## v0.2.2 - 2026-06-18

**Status:** Documentation clarity governance.

### Added

* Added `docs/DOCUMENTATION_STANDARD.md` as the authoritative standard for documentation clarity, audience separation, claim discipline, terminology consistency, onboarding structure, and documentation review.

### Changed

* Updated `docs/GOVERNANCE.md` to place the documentation standard in the governance authority order and define its ownership boundary.
* Replaced a duplicated authority-order list in `docs/CODING_STYLE.md` with a pointer to `docs/GOVERNANCE.md`.
* Updated `docs/GENERATED_ARTIFACTS.md` to name the governed generator and validator for `docs/generated/governance_index.md`.

### Notes

* This change does not change runtime behavior.
* This change does not change ABI contracts.
* This change does not change syscall behavior.
* This change does not add Linux compatibility, POSIX completeness, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.

## v0.2.1 - 2026-06-18

**Status:** Runtime evidence packaging.

### Added

* Added deterministic runtime smoke metadata at `artifacts/runtime/runtime_smoke.metadata.json`.
* Added runtime evidence packaging, review, retention, and invalidation guidance.
* Added validator coverage for runtime metadata integrity and release evidence metadata references.

### Changed

* Updated `scripts/runtime_smoke.sh` to write both runtime smoke log and metadata artifacts.
* Updated `runtime_smoke_evidence` to validate runtime metadata fields, positive claims, non-goals, and release evidence references.
* Updated release evidence, checklist, required checks, phase map, and roadmap documents for runtime evidence packaging.

### Notes

* This change does not add QEMU boot evidence.
* This change does not add hardware trap execution evidence.
* This change does not add Linux compatibility, POSIX completeness, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change runtime behavior, ABI contracts, or syscall behavior.

## v0.2.0 - 2026-06-18

**Status:** Runtime execution evidence baseline.

### Added

* Added `scripts/runtime_smoke.sh` as the governed runtime smoke evidence command.
* Added `docs/RUNTIME_EVIDENCE.md` to document the runtime evidence target, command, artifact, validator, limitations, and non-goals.
* Added `runtime_smoke_evidence` as a registered validator for `artifacts/runtime/runtime_smoke.log`.
* Added focused negative coverage for missing, empty, malformed, failed, unreferenced, and diagnostically weak runtime smoke evidence.

### Changed

* Updated `scripts/verify.sh` to generate runtime smoke evidence during full verification.
* Updated release evidence, checklist, required checks, phase map, and roadmap documents to include the runtime smoke evidence path.

### Notes

* The v0.2.0 evidence target is runtime-adjacent object and symbol evidence, not QEMU boot evidence.
* This change does not add Linux compatibility, POSIX completeness, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.
* This change does not change ABI contracts or syscall behavior.

## v0.0.35 - 2026-06-18

**Status:** Release governance baseline execution.

### Added

* Added `docs/RELEASE_CHECKLIST.md` as the release approval checklist for repository state, verification gates, generated reports, contracts, CI, compatibility, security/governance review, evidence bundle completeness, and release decisions.
* Added `docs/REQUIRED_CHECKS.md` as the required CI/check policy for pull requests and releases.

### Changed

* Refined `docs/RELEASE_EVIDENCE.md` to link release evidence requirements to the checklist and required checks policy.
* Updated `PHASEMAP.md` and `ROADMAP.md` so the v0.1.0 release governance baseline has concrete checklist and required-check deliverables.

### Notes

* This change does not change runtime behavior.
* This change does not change ABI contracts.
* This change does not change syscall behavior.
* This change does not add Linux compatibility, POSIX completeness, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.

## v0.0.34 - 2026-06-18

**Status:** Release planning baseline.

### Added

* Added `PHASEMAP.md` to define release phase sequencing toward a scoped KOZO v1.0.0.
* Added `ROADMAP.md` to define release direction, goals, non-goals, gates, evidence requirements, and deferred work.
* Added `docs/RELEASE_EVIDENCE.md` to define required release artifacts, generated reports, logs, CI evidence, release checklist, evidence bundle structure, and blocker categories.

### Notes

* This change does not change runtime behavior.
* This change does not change ABI contracts.
* This change does not change syscall behavior.
* This change does not add Linux compatibility, POSIX completeness, general userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness claims.

## v0.0.33 - 2026-06-18

**Status:** ABI generator cleanup.

### Changed

* Documented `harness/validators_impl/abi.py` as a stable shim for the registered `abi` validator import path.
* Removed unused ABI generator helper functions that were not part of the binding generation path.

### Notes

* This change does not change ABI constants.
* This change does not change ABI layouts, generated bindings, runtime behavior, syscall behavior, or validator behavior.

## v0.0.32 - 2026-06-18

**Status:** Generated governance index.

### Added

* Added generated governance index for active contracts, schemas, validators, generated reports, latest verification artifact, current version, and current non-goals.
* Added deterministic governance index renderer and `governance_index_report` validator.
* Added focused negative coverage for stale indexes, manual edits, missing validators, missing contracts, missing schemas, missing report references, missing proof artifact references, missing non-goals, and diagnostic quality.

### Notes

* The governance index is generated and non-authoritative.
* The source of truth remains the checked-in contracts, schemas, validators, generated proof artifact, and changelog.
* This change does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, ABI changes, runtime behavior changes, or production readiness claims.

## v0.0.31 - 2026-06-18

**Status:** Rust verification selects the pinned toolchain deterministically.

### Changed

* Updated `scripts/verify.sh` to read the Rust channel from `rust-toolchain.toml` and invoke the pinned `cargo` and `rustc` binaries directly.
* Updated CI and lint workflows to install the pinned Rust toolchain from `rust-toolchain.toml`, install `x86_64-unknown-none` for that toolchain, and run Rust checks through the resolved pinned `cargo` binary.
* Preserved fail-closed checks for the pinned Rust version and bare-metal target availability.

### Notes

* This change does not change Rust source behavior.
* This change does not change ABI contracts, generated bindings, runtime behavior, or syscall behavior.
* Verification no longer depends on host `stable` being the desired Rust toolchain.

## v0.0.30 - 2026-06-17

**Status:** Rust toolchain version pinned.

### Changed

* Updated `rust-toolchain.toml` to pin Rust `1.96.0`.
* Updated `scripts/verify.sh` to prefer the pinned local Rust toolchain path and fail if `cargo` or `rustc` do not report version `1.96.0`.

### Notes

* This change does not change runtime behavior.
* This change does not change ABI contracts, syscall contracts, generated bindings, or validator logic.
* This change only makes Rust toolchain selection explicit for verification.

## v0.0.29 - 2026-06-17

**Status:** Governance document authority split.

### Added

* Added a documentation governance authority model covering precedence, conflict resolution, amendment rules, generated report authority, diagram authority, changelog authority, and README authority.
* Added non-negotiable technical invariants for runtime authority, contracts, syscalls, pointers, capability boundaries, validation, generated artifacts, documentation, compatibility, and review.
* Added KOZO coding style guidance for Python harness code, Odin kernel code, Rust userspace code, shell scripts, tests, generated files, diagnostics, and interface safety.
* Added contract, validation, generated artifact, compatibility, security model, and ADR policy governance documents.

### Changed

* Clarified that `docs/ARCHITECTURE.md` owns system structure only.
* Marked `docs/ARCHITECTURE_DIAGRAM.md` as descriptive and non-authoritative.

### Notes

* This change does not change runtime behavior.
* This change does not change ABI contracts, syscall contracts, generated bindings, or validator logic.
* This change does not add Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or production readiness.

## v0.0.28 - 2026-06-02

**Status:** Generated ABI surface report.

### Added

* Added generated ABI surface report for currently governed ABI constants, binding paths, heartbeat payload layout, and request/response sentinels.
* Added deterministic ABI surface report renderer and registered `abi_surface_report` validator.
* Added focused negative coverage for stale reports, manual edits, missing constants, missing binding paths, missing layout fields, missing sentinels, manifest-driven report drift, and diagnostic quality.

### Notes

* The ABI surface report is generated and non-authoritative.
* The source of truth remains the ABI manifest, checked-in ABI files, and validators.
* This change does not change ABI constants, ABI layouts, generated bindings, runtime behavior, syscall behavior, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, or file descriptor behavior.

## v0.0.27 - 2026-06-02

**Status:** Generated syscall surface report.

### Added

* Added generated syscall surface report for currently governed syscalls.
* Added deterministic report renderer and registered `syscall_surface_report` validator.
* Added focused negative coverage for stale reports, manual edits, missing syscalls, missing classes, missing source references, catalog-driven report drift, and diagnostic quality.

### Notes

* The syscall surface report is generated and non-authoritative.
* The source of truth remains the checked-in contracts and validators.
* This change does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or runtime behavior changes.

## v0.0.26 - 2026-06-02

**Status:** Syscall catalog governance.

### Added

* Added syscall catalog v0 for the currently governed syscall surface.
* Added a schema-backed syscall catalog loader and registered `syscall_catalog` validator.
* Cataloged `nop`, `status`, and `debug_heartbeat` with class, payload behavior, return behavior, mutation behavior, branch selector, proof validator, and runtime probe metadata.
* Added focused negative coverage for missing files, invalid JSON, schema violations, missing or unknown syscalls, field drift from table/class/ABI contracts, unknown proof validators, missing class proofs, runtime probe drift, and diagnostic quality.

### Notes

* The catalog summarizes existing governed syscalls and is not the source of truth for ABI constants, table structure, class semantics, or runtime behavior.
* This change does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or runtime behavior changes.

## v0.0.25 - 2026-06-01

**Status:** STATUS is governed as the second no-payload syscall and exercised from Rust through the existing bridge.

### Added

* Added `K_SYSCALL_STATUS` to the canonical ABI header, generated Rust bindings, generated Odin bindings, and ABI manifest.
* Added STATUS as a `no_payload_status` syscall table entry that uses a null payload argument, returns `K_OK`, and declares no payload mutation.
* Added a live Odin `abi.K_SYSCALL_STATUS` dispatcher branch that returns `abi.K_OK` without reading or mutating payload state.
* Added a narrow Rust `status_request` probe that calls the existing `syscall_entry` bridge with `K_SYSCALL_STATUS` and a null payload pointer, then validates the `K_OK` return status.
* Hardened protocol, syscall table, syscall class, and runtime trap validators with focused negative coverage for missing STATUS constants, hardcoded IDs, payload use, payload mutation, missing dispatcher branches, missing Rust probes, and diagnostic quality.

### Notes

* STATUS uses the existing two-argument bridge convention with a null payload pointer.
* This change does not add Linux compatibility, userspace generalization, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or runtime subsystem behavior.

## v0.0.24 - 2026-06-01

**Status:** Syscall classes are governed as semantic categories for currently proven dispatcher entries.

### Added

* Added syscall class contract v0 for currently proven syscall classes: `no_payload_status` and `payload_mutating_status`.
* Added a schema-backed syscall class loader and registered `syscall_class_contract` validator.
* Extended syscall table contract v0 so each syscall entry keeps its structural `kind` and declares a semantic `class`.
* Added focused negative coverage for missing class contracts, malformed class semantics, unknown examples, missing or wrong syscall classes, kind/class drift, no-payload request/response metadata, no-payload mutation, payload metadata gaps, unknown mutation fields, and diagnostic quality.

### Notes

* This version classifies only currently proven syscall shapes: NOP as no-payload status and debug heartbeat as payload-mutating status.
* This change does not add new syscalls, userspace generalization, Linux compatibility, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or runtime subsystem behavior.

## v0.0.23 - 2026-06-01

**Status:** NOP is exercised from Rust through the existing bridge with a null payload argument.

### Added

* Added a narrow Rust `nop_request` probe that calls `syscall_entry` with `K_SYSCALL_NOP` and a null payload pointer.
* Added NOP return-status validation so the Rust probe requires `K_OK` without creating or mutating a payload.
* Extended syscall boundary contract v0 to record the NOP no-payload argument as `null` and keep NOP mutation behavior empty.
* Hardened `runtime_trap_path` with focused NOP anchors for the generated syscall constant, null payload handoff, status validation, and live entrypoint probe.
* Added focused negative coverage for NOP hardcoded IDs, non-null payloads, payload-layout usage, missing return validation, missing NOP path, missing entrypoint invocation, and boundary-contract drift.

### Notes

* This version proves the existing two-argument bridge can carry a no-payload syscall by using a null payload pointer for `K_SYSCALL_NOP`.
* This change does not generalize userspace syscalls and does not add Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or runtime subsystem behavior beyond the NOP probe.

## v0.0.22 - 2026-05-31

**Status:** NOP is governed as the first no-payload syscall table entry.

### Added

* Promoted `K_SYSCALL_NOP` from an allowed dispatcher branch into a first-class `no_payload` syscall entry in syscall table contract v0.
* Added schema and loader support for distinct payload and no-payload syscall table entries without leaking unchecked optional payload fields into validators.
* Hardened `syscall_table_contract` and `syscall_table_conformance` so NOP must use `abi.K_SYSCALL_NOP`, return `K_OK`, avoid payload mutation, and avoid heartbeat payload layout or sentinels.
* Added focused negative coverage for missing NOP manifest/binding/header constants, payload-layout references on no-payload entries, missing/wrong NOP return status, missing or hardcoded NOP dispatcher branches, NOP payload mutation, NOP heartbeat layout usage, and NOP diagnostics.

### Notes

* This version governs the existing NOP dispatcher branch as a no-payload syscall contract; it does not add a payload layout, request/response sentinels, or a new runtime behavior path.
* This change does not add Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, file descriptor behavior, or runtime expansion beyond NOP governance.

## v0.0.21 - 2026-05-31

- Added `syscall_table_conformance` as a source-level validator for the live Odin dispatcher implementation.
- Extended syscall table contract v0 with explicit `allowed_nonpayload_branches` so the existing `abi.K_SYSCALL_NOP` branch is allowed without broadening the payload syscall table.
- Added focused negative coverage for dispatcher source drift, signature drift, hardcoded selectors, wrong branch bodies, uncontracted branches, payload layout drift, unknown/default behavior drift, and diagnostic quality.
- Documented syscall table conformance as a source proof against syscall table contract v0 only; it does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, or runtime behavior changes.

## v0.0.20 - 2026-05-31

- Added syscall table contract v0 for the currently proven heartbeat/debug dispatcher behavior.
- Added a schema-backed syscall table loader and `syscall_table_contract` validator.
- Added focused negative coverage for dispatcher metadata, ABI references, branch selector mapping, unknown/default syscall behavior, no-mutation guarantees, and diagnostic quality.
- Documented syscall table contract v0 as a current heartbeat/debug dispatcher proof only; it does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, or runtime behavior changes.

## v0.0.19 - 2026-05-31

- Added `syscall_boundary_conformance` as a contract-driven validator for the currently proven x86_64 heartbeat/debug syscall implementation.
- Added focused negative coverage for assembly entry drift, dispatcher/register drift, Rust extern/request/return-validation drift, Odin dispatcher/branch/invalid-return/mutation drift, proof ownership drift, and diagnostic quality.
- Documented syscall boundary conformance as a source proof against syscall boundary contract v0 only; it does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, or runtime behavior changes.

## v0.0.18 - 2026-05-31

- Added syscall boundary contract v0 for the currently proven x86_64 heartbeat/debug syscall path.
- Added a schema-backed syscall boundary loader and `syscall_boundary_contract` validator.
- Added focused negative coverage for boundary contract failures, including register drift, missing ABI manifest references, sentinel mismatches, invalid payload retention, unknown mutable fields, and unknown proof validator references.
- Documented syscall boundary contract v0 as a current heartbeat/debug proof artifact only; it does not add new syscalls, Linux compatibility, userspace execution, process model behavior, VFS behavior, scheduler behavior, ELF loading, or runtime behavior changes.

## v0.0.17 - 2026-05-31

- Added ABI manifest v0 as the machine-readable contract for currently proven syscall constants, status constants, heartbeat payload layout, generated binding paths, and heartbeat request/response sentinels.
- Added an `abi_manifest` validator with schema-backed manifest loading and focused negative coverage for missing files, invalid JSON, schema violations, missing binding paths, constant drift, layout drift, and diagnostic quality.
- Rewired `protocol_contract_alignment` and `layout_parity` to read proven ABI values from the manifest instead of duplicating local validator constants.
- Documented ABI manifest v0 as a current proof artifact only; it does not declare a stable public ABI, Linux compatibility, additional syscalls, or runtime behavior changes.

## v0.0.16 - 2026-05-31

- Hardened `layout_parity` so it mechanically proves ABI data layout agreement across the canonical C header, generated Rust bindings, and generated Odin bindings.
- Added explicit immutable layout contracts and parsed language layouts for heartbeat payload field order, widths, offsets, struct size, alignment, and single-definition expectations.
- Added focused negative coverage for missing fields, manifest drift, wrong field order, width drift, offset drift, struct size drift, stale duplicate structs, and diagnostic quality.

## v0.0.15 - 2026-05-31

- Hardened `protocol_contract_alignment` so it proves canonical syscall protocol agreement across the ABI header, generated Rust bindings, generated Odin bindings, and live Rust/Odin heartbeat paths.
- Added checks for ABI-manifest-backed syscall constants, generated binding agreement, live ABI-prefixed constant usage, and rejection of local hardcoded syscall IDs.
- Added focused negative coverage for missing constants, mismatches, hardcoded IDs, stale/dead constants, and diagnostic quality.

## v0.0.14 - 2026-05-31

- Hardened verification artifact handling so generated verification state is refreshed without leaving transient kernel build artifacts or unsafe partial writes.
- Cleaned `scripts/verify.sh` transient outputs and refreshed proof state after script hardening.
- Preserved generated proof-state updates as separate verification commits from source changes.

## v0.0.13 - 2026-05-31

- Extended `validator_coverage` with marker-depth governance so each validator declares required negative coverage markers that must map to behavioral negative tests.
- Added `KOZO_NEGATIVE_COVERAGE` metadata to focused validator tests.
- Added regression coverage for missing metadata, missing required markers, unknown markers, missing mapped functions, and mapped tests without validator behavior.

## v0.0.12 - 2026-05-31

- Added `validator_coverage` governance so every registered validator must declare a focused test file with behavioral negative-path coverage.
- Added AST-based coverage checks that reject placeholder negative tests unless they invoke the validator or approved harness/helper path, assert failure behavior, and tie the negative test body to the configured validator token.
- Added focused negative tests for previously uncovered validators and regression coverage for missing files, missing mappings, missing validator invocation, missing failure assertions, and token-only false passes.

## v0.0.11 - 2026-05-31

- Hardened `execution_proof` as the high-level observable heartbeat execution proof by validating the live Odin `DEBUG_HEARTBEAT` branch and stable serial observation strings.
- Added focused `execution_proof` tests for missing nil guards, missing heartbeat branch, dead mutation snippets, out-of-order mutations, missing `status_bits` mutation, and missing serial observations.
- Regenerated proof state so `latest_verify.json` records the hardened execution proof details.

## v0.0.10 - 2026-05-31

- Hardened `runtime_trap_path` so the harness validates the live Rust `heartbeat_request` path and bridge helper instead of accepting unrelated extern bridge snippets.
- Added focused `runtime_trap_path` tests for missing live anchors, wrong request sentinels, out-of-order request construction, dead extern calls, and missing heartbeat request diagnostics.
- Regenerated proof state so `latest_verify.json` records the hardened runtime trap path details.

## v0.0.9 - 2026-05-30

- Hardened `bridge_alignment` so the harness validates the ordered live `syscall_entry` block instead of accepting bridge snippets that merely appear somewhere in `syscall.asm`.
- Added named immutable bridge contracts for the assembly symbols, Odin dispatcher signature, ordered register moves, stack alignment, dispatcher handoff, restore path, and return instruction.
- Added focused negative tests for dead snippets outside `syscall_entry`, out-of-order anchors, missing dispatcher handoff, missing Odin dispatcher signature, and missing entry block diagnostics.
- Regenerated proof state so `latest_verify.json` records the hardened bridge alignment details.

## v0.0.8 - 2026-05-30

- Replaced Rust-side debug assertions with explicit post-call return-path validation so the caller checks `abi::K_OK`, `payload.sequence == 0xCAFEFEEE`, `payload.timestamp == 0xDEADBEEF`, and `payload.status_bits == abi::K_OK` after `syscall_entry` returns.
- Added a heavy failure helper on the Rust side so return-path contract violations fail closed instead of relying on debug-only assertions.
- Added `return_path_proof` validation so the harness fails if Rust stops inspecting the returned payload, checks the wrong constants, removes sequence/timestamp/status-bits checks, reintroduces a local stub, or if Odin stops writing the full response through the payload pointer.
- Added focused negative tests so the proof fails when the Rust status-bits check or Odin status-bits success write is removed, including cases where `status_bits` appears only in unrelated text.
- Regenerated the verification artifact so `latest_verify.json` records `return_path_proof: pass` as part of the current proof surface.

## v0.0.7 - 2026-03-19

- Replaced the Rust heartbeat local stub with an extern `syscall_entry` bridge call so the implemented request path becomes `Rust -> syscall_entry (asm) -> syscall_dispatch (Odin)`.
- Updated `kernel/arch/x86_64/syscall.asm` to accept the normal function-call ABI, map ingress values into the bridge registers, preserve `rbx`, and then forward the request into the unchanged Odin dispatcher contract.
- Added `runtime_trap_path` validation so the harness fails closed if a local stub reappears, the extern bridge call is missing, or the syscall bridge symbol/mapping drifts.
- Updated repository status, task metadata, and verification artifacts to describe the boundary as an exercised assembly bridge rather than a simulated stub path.

## v0.0.6 - 2026-03-19

- Fixed `scripts/verify.sh` so an empty changed-file set no longer aborts the run under `set -euo pipefail`, and updated the script to emit the generated verification artifact JSON directly.
- Added fresh verification evidence generation for `odin check`, `odin build`, `cargo check`, and host object inspection so `artifacts/latest_verify.json` is reproducible from the current tree.
- Replaced the broken default serial port inline assembly path with a build-safe stub and gated architecture-specific kernel behavior so `odin build kernel` and `odin build kernel -build-mode:obj -out:artifacts/kernel.o` succeed on the host.
- Marked the Rust heartbeat path as explicit `STUB MODE`, documented that the syscall boundary is still simulated, and renamed `protocol_alignment` to `protocol_contract_alignment` so the harness reports the current system truthfully.
- Hardened protocol validation to reject unlabeled local syscall stubs and strengthened execution-foundation proof by checking freestanding amd64 bridge symbols and NASM-assembled trap objects.

## v0.0.5 - 2026-03-15

- Added source-level execution proof validation for the heartbeat syscall path across Odin, Rust, and the verification harness.
- Implemented the ordered Odin arbiter sequence with nil guard, magic-value guard, stable ingress/egress trace strings, ordered pointer mutation, and ABI-backed return values.
- Updated the Rust core service to initialize the normative magic payload, branch explicitly on `abi::K_OK`, assert postconditions, and enter a heavy failure path on error.
- Extended the verify artifact format to carry granular `sub_results` for `execution_proof`, making field-level proof status visible in `latest_verify.json`.
- Verified the negative proof by changing the Rust-side magic value and confirming `execution_proof` fails before restoring the correct contract.

## v0.0.4 - 2026-03-14

- Added the x86_64 boot foundation bridge with `_start`, a 16KB aligned bootstrap stack, and exported Odin `kernel_entry` / `syscall_dispatch` entry symbols.
- Added ADR-0016 to document the assembly-to-Odin entry flow, trap ingress registers, preservation rules, and stack alignment expectations.
- Added execution foundation validation so the harness proves the presence of the required boot and syscall bridge symbols even when full object-symbol inspection is environment-dependent.
- Added semantic trap-path validation so the harness proves the normative `rax -> rdi` and `rbx -> rsi` register bridge into the exported Odin dispatcher signature.
- Verified the negative proof for trap drift by swapping the ingress register moves and confirming `bridge_alignment` fails before restoring the correct mapping.
- Regenerated `latest_verify.json` and `agent_context.json` from the passing boot/trap verification flow.

## v0.0.3 - 2026-03-13

- Added ABI-backed protocol alignment between the Odin kernel dispatcher and the Rust core service heartbeat request path.
- Added semantic harness validation for protocol alignment so missing syscall cases or missing Rust syscall usage fail closed.
- Extended the ABI with `k_heartbeat_payload_t` and projected the struct deterministically into Odin and Rust bindings.
- Added full layout parity validation for the heartbeat payload, covering size, alignment, and field offsets across the generated projections.
- Updated the kernel heartbeat path to populate and log the structured payload, and updated the Rust service to initialize and pass the same typed payload.
- Verified the current state with `python3 scripts/gen_abi.py`, `odin check kernel/`, `cargo check --manifest-path userspace/core_service/Cargo.toml --target x86_64-unknown-none`, `./scripts/verify.sh`, and `./scripts/agent_context.sh`.

## v0.0.2 - 2026-03-12

- Completed the harness bootstrap and aligned the verify/control-plane loop with active task packets.
- Added the first Odin kernel heartbeat slice in `kernel/main.odin`, `kernel/arch/x86_64/serial.odin`, and `kernel/arch/x86_64/arch.odin`.
- Established KOZO ABI V1 in `contracts/kozo_abi.h` with deterministic generated bindings for Odin and Rust.
- Added `scripts/gen_abi.py` and checked in generated projections under `bindings/odin/` and `bindings/rust/`.
- Integrated the generated ABI into the Odin kernel heartbeat path and a `no_std` Rust service scaffold at `userspace/core_service/`.
- Added ABI sync validation so `verify.sh` fails closed if checked-in bindings drift from the normative header.
- Verified the current state with `odin check kernel/`, `cargo check --manifest-path userspace/core_service/Cargo.toml --target x86_64-unknown-none`, `./scripts/verify.sh`, and `./scripts/agent_context.sh`.

## v0.0.1 - 2026-03-11

- Bootstrap the minimum KOZO harness and control-plane loop.
- Add canonical registry-ordered validators and schema-backed artifacts.
- Add `verify.sh` and `agent_context.sh` to generate the first working verification outputs.
- Harden `aggregator.py` and `summarize.py` so verification runs in canonical order and agent context resolves the next required commands.
