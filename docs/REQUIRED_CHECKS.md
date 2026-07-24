# KOZO Required Checks

Version: 1
Status: Authoritative
Scope: Required local and CI checks for KOZO pull requests and releases

---

# 1. Purpose

This document defines the checks required before KOZO changes may merge or release.

It maps local verification commands to GitHub Actions checks and release evidence outputs.

---

# 2. Authority

`docs/REQUIRED_CHECKS.md` owns required CI/check policy.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`
* checked-in contracts
* schemas
* validators

It does not define runtime behavior, ABI truth, syscall truth, compatibility claims, or validator internals.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim general userspace execution.

This document does not claim process model, VFS, scheduler, ELF loading, or file descriptor behavior.

This document does not replace `scripts/verify.sh` as the full verification entry point.

CI/Linux is the authoritative portability proof.

Local macOS development is a convenience path.

No build or verification script may depend on user-specific absolute paths.

---

# 4. Required Checks Table

| Check Name | Command or Workflow | Owner Document | Required for PR | Required for Release | Evidence Output |
| --- | --- | --- | --- | --- | --- |
| Full verification | `scripts/verify.sh` | `docs/VALIDATION.md` | Yes | Yes | `artifacts/latest_verify.json`, `artifacts/logs/*.log`, `artifacts/runtime/runtime_smoke.log`, `artifacts/runtime/runtime_smoke.metadata.json`, `artifacts/runtime/boot_blocker_report.json`, `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, `artifacts/runtime/qemu_smoke.metadata.json`, `artifacts/runtime/qemu_smoke.summary.txt` |
| Unit discovery | `python3 -m unittest discover -s tests` | `docs/VALIDATION.md` | Yes | Yes | test output |
| Odin check | `odin check kernel` | `docs/VALIDATION.md` | Yes | Yes | CI output, `artifacts/logs/odin-check.log` through full verification |
| Pinned Rust cargo check | pinned cargo check for `userspace/core_service` | `docs/VALIDATION.md` | Yes | Yes | CI output, `artifacts/logs/cargo-check.log` through full verification |
| JSON validation | `python3 -m json.tool` for task/proof artifacts | `docs/VALIDATION.md` | Yes | Yes | CI output |
| Whitespace check | `git diff --check` | `docs/CODING_STYLE.md` | Yes | Yes | CI output |
| Runtime smoke evidence | `scripts/runtime_smoke.sh` | `docs/RUNTIME_EVIDENCE.md` | Yes, through full verification | Yes | `artifacts/runtime/runtime_smoke.log`, `artifacts/runtime/runtime_smoke.metadata.json` |
| Runtime evidence review | `runtime_evidence_review` through `scripts/verify.sh` | `docs/RUNTIME_EVIDENCE_REVIEW.md` | Yes, through full verification | Yes | release-only review gate over runtime evidence claims and documentation |
| Boot blocker report | `scripts/boot_blocker_report.sh` | `docs/BOOT.md` | Yes, through full verification while boot is blocked | Yes, while boot is blocked | `artifacts/runtime/boot_blocker_report.json` |
| Boot image packaging metadata | `scripts/build_boot_image.sh` | `docs/BOOT_IMAGE.md` | Yes, through full verification while boot image packaging is blocked | Yes, while boot image packaging is blocked | `artifacts/runtime/boot_image/package_metadata.json` |
| CI ISO tooling install | GitHub Actions `ci / full verification` | `docs/BOOT_TOOLING.md` | Yes | Yes | CI output, `artifacts/runtime/boot_image/package_metadata.json`, `artifacts/runtime/boot_image/kozo.iso` when produced |
| QEMU smoke evidence | `scripts/qemu_smoke.sh` and `qemu_smoke_evidence` | `docs/BOOT.md` | Yes, through full verification | Yes, when the QEMU blocker is under direct review | `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, `artifacts/runtime/qemu_smoke.metadata.json`, `artifacts/runtime/qemu_smoke.summary.txt` |
| Runtime progression evidence | `runtime_progression_entry_contract` and `runtime_progression_evidence` through `scripts/verify.sh` | `docs/RUNTIME_EVIDENCE.md` | Yes, through full verification | Yes | contract, source, ELF report, QEMU metadata/log evidence |
| CI workflow | GitHub Actions `ci / full verification` | `docs/REQUIRED_CHECKS.md` | Yes | Yes | GitHub Actions status |
| Lint workflow | GitHub Actions `lint / static checks` | `docs/REQUIRED_CHECKS.md` | Yes | Yes | GitHub Actions status |

---

# 5. Branch Protection Recommendation

For `main`, branch protection should require:

* `ci / full verification`
* `lint / static checks`
* pull request review before merge
* branch up to date before merge when available
* prevention of force push when available

Bypass should not be allowed except for maintainers under a documented emergency process.

An emergency bypass must not create unsupported compatibility, runtime, security, or production-readiness claims.

---

# 6. Local Verification Command Set

Before release review, run:

```bash
python3 -m unittest discover -s tests
python3 -m json.tool tasks/todo.json
scripts/runtime_smoke.sh
scripts/verify.sh
python3 -m json.tool artifacts/latest_verify.json
python3 -m json.tool tasks/todo.json
git diff --check
```

When Rust behavior or Rust tooling is in scope, also run the pinned Rust cargo check used by CI.

When Odin behavior is in scope, also run `odin check kernel` before full verification.

---

# 7. CI Workflow Mapping

| Workflow | Job | Required Surface |
| --- | --- | --- |
| `.github/workflows/ci.yml` | `full verification` | system tools, pinned Rust toolchain, bare-metal target, Odin, pinned Limine source tooling, xorriso, QEMU, JSON validation, unit tests, Rust check, Odin check, ISO build attempt, QEMU smoke attempt, runtime smoke through full verification, boot blocker report through full verification while boot is blocked, proof artifact validation, transient artifact cleanup, whitespace check |
| `.github/workflows/lint.yml` | `static checks` | system tools, pinned Rust toolchain, bare-metal target, Odin, shell syntax, JSON syntax, unit tests, Rust check, Odin check, whitespace check |

The CI workflows must keep installing `nasm`, pinned Rust, `x86_64-unknown-none`, and Odin before running checks that depend on them.

Full CI must install xorriso and QEMU through apt, acquire the pinned Limine source release, verify the Limine source checksum, build Limine tooling, export `LIMINE_DIR`, `LIMINE`, and `XORRISO`, and run `scripts/build_boot_image.sh`.

CI/Linux is the authoritative portability proof for the full build, verification, ISO packaging, ELF inspection, and QEMU smoke tooling path. Local macOS development is a convenience path and must not weaken CI-required dependency declarations.

No build or verification script may depend on user-specific absolute paths; required tools must be found through CI installation, pinned toolchain resolution, controlled environment variables, command discovery, or repository-relative paths.

Runtime smoke evidence is generated by full verification. Runtime evidence review is a release-only review gate enforced by `runtime_evidence_review` during full verification; it does not add a QEMU boot, hardware trap, compatibility, userspace, or production-readiness claim.

Full CI requires runtime smoke evidence because `.github/workflows/ci.yml` runs `scripts/verify.sh`.

The lint workflow does not require runtime smoke evidence because `.github/workflows/lint.yml` does not run full verification. If lint is changed to run `scripts/verify.sh`, runtime smoke evidence becomes required there through the same full-verification path.

QEMU smoke evidence is required in full CI through `scripts/qemu_smoke.sh` and `qemu_smoke_evidence`. A blocked QEMU smoke result is acceptable only when metadata records an exact blocker and preserves narrow claims. Passing v0.7.5 controlled-loop evidence requires a green full CI run, passing metadata, and the full ordered marker sequence through `KOZO_RUNTIME_LOOP_EXIT_OK` and `KOZO_RUNTIME_RETURN_OK` in `artifacts/runtime/qemu_smoke.log`. That claim proves only the bounded assembly-to-Odin operation, three controlled iterations, exact return, and governed halt continuation; it does not prove a scheduler, interrupts, userspace, complete Odin runtime readiness, general stack or memory readiness, syscall dispatch, hardware trap execution, or broader lifecycle behavior.

If full CI fails after QEMU smoke runs, release review must treat the run as blocked even if uploaded artifacts appear promising. Passing progression evidence remains a narrow bounded-call claim and does not prove complete Odin runtime readiness, dynamic initialization, general stack readiness, general memory management, syscall dispatch, hardware trap execution, compatibility, userspace behavior, or production readiness.

Full CI must run `scripts/ci_evidence_summary.sh` with `if: always()` so failure evidence is visible in the Actions log even when verification, artifact authentication, API log download, or local `gh` access is unavailable.

The CI evidence summary is a first-level triage surface. It does not replace `artifacts/latest_verify.json`, QEMU smoke metadata, QEMU serial/stderr logs, or boot blocker reports as generated evidence.

The CI-observed timeout or runtime state must be narrowed when possible. QEMU smoke metadata blocker vocabulary is owned by `contracts/runtime_evidence_taxonomy.v0.json`, including the distinguishable capability states `capability_dispatch_not_reached`, `runtime_status_query_not_completed`, and `first_governed_capability_not_proven`; all blocked states remain evidence limitations and do not authorize a pass.

Full verification runs `scripts/build_boot_image.sh` to produce `artifacts/runtime/boot_image/package_metadata.json`; while packaging is blocked, that metadata is blocker evidence rather than boot evidence.

Full CI separately attempts `scripts/build_boot_image.sh` after installing ISO tooling so CI can surface tooling or image-generation failures before the aggregate verification step.

CI should upload the runtime smoke log and metadata when full verification runs so release review can inspect the same runtime-adjacent evidence generated by the required check.

CI should upload the boot blocker report while boot is blocked so release review can inspect the exact missing boot components.

CI should upload `artifacts/runtime/boot_image/package_metadata.json` and `artifacts/runtime/boot_image/kozo.iso` when the ISO is produced.

CI should upload `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, and `artifacts/runtime/qemu_smoke.metadata.json` when QEMU smoke runs.

CI should also upload `artifacts/runtime/qemu_smoke.summary.txt` when QEMU smoke runs. The summary is a non-authoritative reviewer convenience derived from the QEMU smoke metadata, serial log, stderr log, and boot blocker report.

---

# 8. Failure Handling

If a required check fails:

* stop release preparation
* classify the failure using `docs/RELEASE_CHECKLIST.md`
* inspect the failing evidence
* fix the source, generated artifact, task state, workflow, or documentation that owns the failure
* rerun focused checks before rerunning full verification
* refresh generated proof state only after source checks pass

Do not ignore a failing required check because generated reports look current.

Do not treat generated reports as source truth.

Do not downgrade required checks without a governance update.

For v0.8.0, full CI must run `first_governed_runtime_capability` and `first_governed_runtime_capability_evidence`. Passing capability evidence requires the full taxonomy marker sequence, matching metadata/logs, linked dispatcher/handler/bridge symbols, a recorded progression call edge, and the unchanged runtime halt contract. The check proves only one internal same-address-space status query.
