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

`PHASEMAP.md` owns release phase sequencing.

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
* `PHASEMAP.md`
* `ROADMAP.md`
* CI run URLs or statuses when available
* release notes
* known non-goals list

Detailed evidence rules are owned by `docs/RELEASE_EVIDENCE.md`.

---

# 6. Phase Table

| Phase | Name | Purpose | Required Deliverables | Exit Criteria |
| --- | --- | --- | --- | --- |
| `v0.1.0` | Release governance baseline | Define v1.0.0 scope, release evidence requirements, required CI checks, release checklist, README claim cleanup, and generated report review inputs. | `PHASEMAP.md`, `ROADMAP.md`, `docs/RELEASE_EVIDENCE.md`, `docs/RELEASE_CHECKLIST.md`, `docs/REQUIRED_CHECKS.md`, README claim cleanup if needed. | Release checklist and required checks policy are merged, non-goals are preserved, verification passes, generated governance surfaces are refreshed as needed. |
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
| `v0.4.1` | ABI and syscall maturity | Stabilize current ABI/syscall governance and define expansion rules. | ABI version policy, syscall expansion checklist, generated binding compatibility expectations, regression evidence for all governed syscalls. | Current syscall surface is frozen unless changed through governed process. |
| `v0.5.0-rc.1` | Release candidate hardening | Freeze release scope and release gates, produce evidence bundle, confirm branch protection, and dry-run release notes. | Release evidence bundle, completed release checklist, current generated reports, changelog/release notes dry run, all required CI checks green. | Release candidate can be reviewed without adding new scope. |
| `v1.0.0` | Scoped production release | Release only the proven, scoped KOZO surface. | Final release evidence bundle, final changelog and release notes, passing required gates, explicit non-goals. | v1.0.0 claims only evidence-backed behavior and preserves all compatibility non-goals. |

---

# 7. v1.0.0 Constraints

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

# 8. Release Checklist

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
