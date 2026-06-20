# KOZO Release Evidence

Version: 1
Status: Authoritative
Scope: Required evidence for KOZO release review

---

# 1. Purpose

This document defines the evidence required before a KOZO release may be reviewed.

Release evidence must make claims reproducible, scoped, and auditable.

---

# 2. Authority

This document owns release evidence requirements.

It is subordinate to `docs/GOVERNANCE.md`, `docs/INVARIANTS.md`, `docs/ARCHITECTURE.md`, `docs/CONTRACTS.md`, and `docs/COMPATIBILITY.md`.

It does not define runtime behavior, ABI truth, syscall truth, compatibility claims, or validator implementation mechanics.

`docs/RELEASE_CHECKLIST.md` owns release approval checklist requirements.

`docs/REQUIRED_CHECKS.md` owns required CI/check policy.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim general userspace execution.

This document does not claim process model, VFS, scheduler, ELF loading, or file descriptor behavior.

This document does not make generated reports authoritative.

CI/Linux is the authoritative portability proof.

Local macOS development is a convenience path.

No build or verification script may depend on user-specific absolute paths.

---

# 4. Required Release Artifacts

Every release review must include:

* `artifacts/latest_verify.json`
* `artifacts/runtime/runtime_smoke.log`
* `artifacts/runtime/runtime_smoke.metadata.json`
* `artifacts/runtime/boot_blocker_report.json`
* `artifacts/runtime/kernel_elf_report.json`
* `artifacts/runtime/boot_image/package_metadata.json`
* `artifacts/runtime/boot_image/kozo.iso` when packaging succeeds
* `artifacts/runtime/qemu_smoke.log` when a QEMU smoke blocker or QEMU serial evidence is under review
* `artifacts/runtime/qemu_smoke.metadata.json` when a QEMU smoke blocker or QEMU serial evidence is under review
* `docs/BOOT_PROTOCOL.md`
* `docs/BOOT_IMAGE.md`
* `docs/BOOT_TOOLING.md`
* `docs/decisions/0001-boot-protocol.md`
* `CHANGELOG.md`
* `docs/PHASEMAP.md`
* `docs/ROADMAP.md`
* `docs/RELEASE_CHECKLIST.md`
* `docs/REQUIRED_CHECKS.md`
* `docs/RUNTIME_EVIDENCE_REVIEW.md`
* release notes
* known non-goals list
* checked-in contracts
* checked-in schemas

`artifacts/latest_verify.json` must be valid JSON and must report `pass`.

---

# 5. Required Generated Reports

Every release review must include current generated reports:

* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `docs/generated/governance_index.md`

Generated reports are review surfaces. They do not own contract, compatibility, architecture, or runtime truth.

---

# 6. Required Logs

Release review must include verification logs when generated:

* `artifacts/logs/odin-check.log`
* `artifacts/logs/odin-build.log`
* `artifacts/logs/cargo-check.log`
* `artifacts/logs/nm-kernel.log`
* `artifacts/runtime/runtime_smoke.log`
* `artifacts/runtime/runtime_smoke.metadata.json`
* `artifacts/runtime/boot_blocker_report.json`
* `artifacts/runtime/kernel_elf_report.json`
* `artifacts/runtime/boot_image/package_metadata.json`
* `artifacts/runtime/boot_image/kozo.iso` when packaging succeeds
* `artifacts/runtime/qemu_smoke.log` when generated during QEMU smoke blocker review
* `artifacts/runtime/qemu_smoke.stderr.log` when generated during QEMU smoke blocker review
* `artifacts/runtime/qemu_smoke.metadata.json` when generated during QEMU smoke blocker review

Future runtime smoke phases must add their runtime logs to this list before using them as release evidence.

Runtime evidence review is required for release review and is governed by `docs/RUNTIME_EVIDENCE_REVIEW.md`.

The boot blocker report is required while v0.3.0 remains blocked and is governed by `docs/BOOT.md`, `docs/BOOT_BLOCKERS.md`, `scripts/boot_blocker_report.sh`, and `boot_blocker_report`.

The current local boot blocker category is `missing_iso_generation_tooling`.

When CI produces `artifacts/runtime/boot_image/kozo.iso`, the generated boot blocker report may narrow to `missing_qemu_serial_evidence` for that run.

When CI then runs QEMU against that ISO but the kernel marker is absent before timeout, the generated boot blocker report may narrow further to `qemu_timeout`.

If Limine reaches the boot entry but fails to open or load the configured kernel executable, QEMU smoke evidence must report `kernel_not_loaded`.

For v0.4.2 and later, release review must include `artifacts/runtime/kernel_elf_report.json` when kernel loadability is under review. That report may prove ELF structure, entry, and PT_LOAD segment presence, but it does not prove Limine loaded the ELF or executed kernel code.

For v0.4.0 and later, QEMU smoke metadata must also include early marker diagnostics and may narrow timeout to one of:

* `limine_not_reached`
* `kernel_not_loaded`
* `kernel_entry_not_reached`
* `serial_not_initialized`
* `marker_not_emitted`
* `qemu_timeout`

The latest inspected post-v0.4.1 CI artifact narrowed to `kernel_not_loaded` because Limine reached the boot entry and failed to open the configured kernel executable before any KOZO marker appeared.

The v0.4.2 kernel ELF loadability validator is:

```text
kernel_loadability
```

The current packaging metadata records the missing ISO generation tooling blocker:

```text
artifacts/runtime/boot_image/package_metadata.json
```

The expected future ISO path is:

```text
artifacts/runtime/boot_image/kozo.iso
```

The boot tooling acquisition policy is:

```text
docs/BOOT_TOOLING.md
```

The blocked QEMU smoke command is:

```text
scripts/qemu_smoke.sh
```

The QEMU smoke evidence validator is:

```text
qemu_smoke_evidence
```

The expected QEMU smoke marker is:

```text
KOZO_BOOT_SMOKE_OK
```

The boot protocol decision, boot image skeleton, and blocked QEMU smoke command are release context only. They do not create a QEMU boot claim unless `qemu_smoke_evidence` validates passing metadata and serial output.

---

# 7. Required CI Evidence

Release review must record CI run URLs or statuses when available.

Required check policy is owned by `docs/REQUIRED_CHECKS.md`.

The minimum release evidence must record:

* full verification status
* lint/static-check status
* required target/toolchain setup
* runtime smoke log and metadata artifact availability from full CI when available
* boot blocker report artifact availability from full CI while boot is blocked
* CI run URL or status when available
* ISO tooling acquisition status from full CI
* boot image package metadata artifact availability from full CI
* boot image ISO artifact availability from full CI when produced
* QEMU smoke metadata and serial log availability from full CI when generated

Full CI runs `scripts/verify.sh`, so runtime smoke evidence is required there through full verification and should be uploaded as CI artifacts.

Full CI also runs the boot blocker report generator through `scripts/verify.sh` while boot remains blocked, and should upload `artifacts/runtime/boot_blocker_report.json`.

Full CI installs xorriso, acquires pinned Limine source tooling, runs `scripts/build_boot_image.sh`, and should upload `artifacts/runtime/boot_image/package_metadata.json` plus `artifacts/runtime/boot_image/kozo.iso` when the image exists.

Full CI installs QEMU, runs `scripts/qemu_smoke.sh`, and should upload `artifacts/runtime/qemu_smoke.log` plus `artifacts/runtime/qemu_smoke.metadata.json` whether the result is pass or an exact blocker.

Release review must treat CI/Linux as the authoritative portability proof for declared build and verification dependencies. Local macOS development may provide convenience evidence, but local host state must not replace CI dependency declarations or CI artifact review.

Release evidence must not depend on user-specific absolute paths. Required tools must be declared in documentation and supplied by CI, controlled environment variables, command discovery, or repository-relative paths.

The lint workflow is static-check only. It does not own runtime smoke evidence unless it is changed to run full verification.

---

# 8. Required Changelog and Release Notes

`CHANGELOG.md` must include the release version and must identify:

* added behavior
* changed behavior
* generated artifact changes
* validator or governance changes
* explicit non-goals

Release notes must describe only behavior backed by release evidence.

Release notes must not introduce compatibility or production-readiness claims that are not backed by authoritative documents and evidence.

---

# 9. Release Checklist

Release checklist authority is owned by `docs/RELEASE_CHECKLIST.md`.

Before release review, the checklist must confirm:

* repository state
* verification gates
* generated report gates
* contract gates
* CI gates
* compatibility gates
* security and governance gates
* release evidence bundle completeness
* release decision

---

# 10. Evidence Bundle Structure

A release evidence bundle should contain or reference:

```text
release-evidence/
  README.md
  latest_verify.json
  runtime/
    runtime_smoke.log
    runtime_smoke.metadata.json
    boot_blocker_report.json
    boot_image/
      package_metadata.json
      kozo.iso
    qemu_smoke.log
    qemu_smoke.metadata.json
  logs/
    odin-check.log
    odin-build.log
    cargo-check.log
    nm-kernel.log
  reports/
    syscall_surface.md
    abi_surface.md
    governance_index.md
  contracts/
  schemas/
  changelog.md
  release_notes.md
  phase_map.md
  roadmap.md
  release_checklist.md
  required_checks.md
  runtime_evidence_review.md
  boot_tooling.md
  ci_status.md
  non_goals.md
```

This is the minimum directory or archive shape for release review.

Runtime evidence is generated under `artifacts/runtime/`.

Release packaging should copy the runtime log and metadata to `artifacts/release/runtime/` when assembling a release evidence bundle.

The exact packaging command may be defined by a later release phase.

---

# 11. Retention Guidance

Keep the latest generated runtime evidence under `artifacts/runtime/` for local review.

Keep release-reviewed runtime evidence under `artifacts/release/runtime/` or an equivalent release archive.

Do not rely on stale runtime evidence after runtime, ABI binding, smoke script, or runtime evidence validator changes.

---

# 12. Release Blocker Categories

| Priority | Meaning |
| --- | --- |
| P0 | Correctness, security boundary, or release integrity blocker. |
| P1 | v1.0.0 credibility blocker. |
| P2 | Release candidate blocker. |
| P3 | Non-blocking cleanup or polish. |

P0 and P1 issues block v1.0.0 release.

P2 issues block release candidate promotion unless explicitly waived through governance.

P3 issues may be deferred when they do not weaken release claims or evidence.
