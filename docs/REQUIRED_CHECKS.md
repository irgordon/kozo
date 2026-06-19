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

---

# 4. Required Checks Table

| Check Name | Command or Workflow | Owner Document | Required for PR | Required for Release | Evidence Output |
| --- | --- | --- | --- | --- | --- |
| Full verification | `scripts/verify.sh` | `docs/VALIDATION.md` | Yes | Yes | `artifacts/latest_verify.json`, `artifacts/logs/*.log`, `artifacts/runtime/runtime_smoke.log`, `artifacts/runtime/runtime_smoke.metadata.json`, `artifacts/runtime/boot_blocker_report.json` |
| Unit discovery | `python3 -m unittest discover -s tests` | `docs/VALIDATION.md` | Yes | Yes | test output |
| Odin check | `odin check kernel` | `docs/VALIDATION.md` | Yes | Yes | CI output, `artifacts/logs/odin-check.log` through full verification |
| Pinned Rust cargo check | pinned cargo check for `userspace/core_service` | `docs/VALIDATION.md` | Yes | Yes | CI output, `artifacts/logs/cargo-check.log` through full verification |
| JSON validation | `python3 -m json.tool` for task/proof artifacts | `docs/VALIDATION.md` | Yes | Yes | CI output |
| Whitespace check | `git diff --check` | `docs/CODING_STYLE.md` | Yes | Yes | CI output |
| Runtime smoke evidence | `scripts/runtime_smoke.sh` | `docs/RUNTIME_EVIDENCE.md` | Yes, through full verification | Yes | `artifacts/runtime/runtime_smoke.log`, `artifacts/runtime/runtime_smoke.metadata.json` |
| Runtime evidence review | `runtime_evidence_review` through `scripts/verify.sh` | `docs/RUNTIME_EVIDENCE_REVIEW.md` | Yes, through full verification | Yes | release-only review gate over runtime evidence claims and documentation |
| Boot blocker report | `scripts/boot_blocker_report.sh` | `docs/BOOT.md` | Yes, through full verification while boot is blocked | Yes, while boot is blocked | `artifacts/runtime/boot_blocker_report.json` |
| QEMU smoke blocker review | `scripts/qemu_smoke.sh` | `docs/BOOT.md` | No | Yes, when the QEMU blocker is under direct review | `artifacts/runtime/qemu_smoke.log` |
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
| `.github/workflows/ci.yml` | `full verification` | system tools, pinned Rust toolchain, bare-metal target, Odin, JSON validation, unit tests, Rust check, Odin check, runtime smoke through full verification, boot blocker report through full verification while boot is blocked, proof artifact validation, transient artifact cleanup, whitespace check |
| `.github/workflows/lint.yml` | `static checks` | system tools, pinned Rust toolchain, bare-metal target, Odin, shell syntax, JSON syntax, unit tests, Rust check, Odin check, whitespace check |

The CI workflows must keep installing `nasm`, pinned Rust, `x86_64-unknown-none`, and Odin before running checks that depend on them.

Runtime smoke evidence is generated by full verification. Runtime evidence review is a release-only review gate enforced by `runtime_evidence_review` during full verification; it does not add a QEMU boot, hardware trap, compatibility, userspace, or production-readiness claim.

Full CI requires runtime smoke evidence because `.github/workflows/ci.yml` runs `scripts/verify.sh`.

The lint workflow does not require runtime smoke evidence because `.github/workflows/lint.yml` does not run full verification. If lint is changed to run `scripts/verify.sh`, runtime smoke evidence becomes required there through the same full-verification path.

QEMU smoke is not a required CI check while the active blocker is `missing_bootable_iso_packaging`. `scripts/qemu_smoke.sh` is a release-local blocker review command until bootable Limine image packaging exists and CI support is explicitly added.

CI should upload the runtime smoke log and metadata when full verification runs so release review can inspect the same runtime-adjacent evidence generated by the required check.

CI should upload the boot blocker report while boot is blocked so release review can inspect the exact missing boot components.

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
