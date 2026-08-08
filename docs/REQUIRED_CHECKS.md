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
| Runtime state transition capability | `runtime_state_transition_capability` and `runtime_state_transition_capability_evidence` through `scripts/verify.sh` | `docs/RUNTIME_CAPABILITIES.md` | Yes, through full verification | Yes | contract, source, focused ELF report, QEMU metadata/log evidence |
| Cargo license policy | `cargo deny --manifest-path userspace/core_service/Cargo.toml check` | `docs/RELEASE_CHECKLIST.md` | No | Yes | CI and release-review output |
| Cargo advisory audit | `cargo audit --file userspace/core_service/Cargo.lock` | `docs/RELEASE_CHECKLIST.md` | No | Yes | CI and release-review output |
| Release bundle | `scripts/build_release_candidate.sh --version 1.0.0 --output <directory>` | `docs/RELEASE_EVIDENCE.md` | No | Yes | archive, release metadata, legal files, and `SHA256SUMS` |
| CI workflow | GitHub Actions `ci / full verification` | `docs/REQUIRED_CHECKS.md` | Yes | Yes | GitHub Actions status |
| Lint workflow | GitHub Actions `lint / static checks` | `docs/REQUIRED_CHECKS.md` | Yes | Yes | GitHub Actions status |
| Host portability workflow | GitHub Actions `portability / required build contract` on all pinned matrix hosts | `docs/VALIDATION.md`, `docs/COMPATIBILITY.md` | Yes | Yes | GitHub Actions status and `kozo-portability-<host>` artifacts |

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

The live 2026-07-29 GitHub API readback confirms that force pushes to `main`
are blocked. No required status checks, pull-request reviews, administrator
enforcement, conversation-resolution rule, deletion restriction, or repository
ruleset was added by the release work. Those broader settings are not required
for the declared v1.0.0 release scope.

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
| `.github/workflows/ci.yml` | `full verification` | system tools, pinned Rust toolchain, bare-metal target, authenticated Odin setup, pinned Limine source tooling, xorriso, QEMU, JSON validation, unit tests, Rust check, cargo-deny, cargo-audit, Odin check, governed full verification, release-bundle and checksum validation, evidence and dry-run artifact upload, proof artifact validation, transient artifact cleanup, whitespace check |
| `.github/workflows/lint.yml` | `static checks` | system tools, pinned Rust toolchain, bare-metal target, Odin, shell syntax, JSON syntax, unit tests, Rust check, Odin check, whitespace check |
| `.github/workflows/portability.yml` | `required build contract` | pinned Ubuntu, Windows, and macOS runners; task/schema validation; 34 Odin object regressions; full Python tests; real Odin object normalization; Rust and Odin checks; release inventory, license, prohibited-path, and portable checksum validation; per-host evidence upload |
| `.github/workflows/portability.yml` | `observation build contract` | non-blocking latest-runner observation on schedule or manual dispatch; no compatibility promotion |

The CI workflows must keep installing `nasm`, pinned Rust, `x86_64-unknown-none`, and Odin before running checks that depend on them.

Full CI must install xorriso and QEMU through apt, acquire the pinned Limine source release, verify the Limine source checksum, build Limine tooling, export `LIMINE_DIR`, `LIMINE`, and `XORRISO`, and run the release builder. The release builder invokes `scripts/verify.sh`, which performs the boot-image, QEMU, runtime, and aggregate verification path against the committed source snapshot.

The required portability matrix owns host build claims through
`VALIDATED_BUILD`; only a separately executed runtime contract can promote a
host to `VALIDATED_RUNTIME`. Linux hosted QEMU remains the authoritative
guest-runtime proof for full verification, ISO packaging, ELF inspection, and
QEMU smoke. Local macOS development is one validation environment and must not weaken hosted dependency declarations.

No build or verification script may depend on user-specific absolute paths; required tools must be found through CI installation, pinned toolchain resolution, controlled environment variables, command discovery, or repository-relative paths.

Runtime smoke evidence is generated by full verification. Runtime evidence review is a release-only review gate enforced by `runtime_evidence_review` during full verification; it does not add a QEMU boot, hardware trap, compatibility, userspace, or production-readiness claim.

Full CI requires runtime smoke evidence because `.github/workflows/ci.yml` runs `scripts/verify.sh`.

The lint workflow does not require runtime smoke evidence because `.github/workflows/lint.yml` does not run full verification. If lint is changed to run `scripts/verify.sh`, runtime smoke evidence becomes required there through the same full-verification path.

QEMU smoke evidence is required in full CI through `scripts/qemu_smoke.sh` and `qemu_smoke_evidence`. A blocked QEMU smoke result is acceptable only when metadata records an exact blocker and preserves narrow claims. Passing v0.7.5 controlled-loop evidence requires a green full CI run, passing metadata, and the full ordered marker sequence through `KOZO_RUNTIME_LOOP_EXIT_OK` and `KOZO_RUNTIME_RETURN_OK` in `artifacts/runtime/qemu_smoke.log`. That claim proves only the bounded assembly-to-Odin operation, three controlled iterations, exact return, and governed halt continuation; it does not prove a scheduler, interrupts, userspace, complete Odin runtime readiness, general stack or memory readiness, syscall dispatch, hardware trap execution, or broader lifecycle behavior.

If full CI fails after QEMU smoke runs, release review must treat the run as blocked even if uploaded artifacts appear promising. Passing progression evidence remains a narrow bounded-call claim and does not prove complete Odin runtime readiness, dynamic initialization, general stack readiness, general memory management, syscall dispatch, hardware trap execution, compatibility, userspace behavior, or production readiness.

Full CI must run `scripts/ci_evidence_summary.sh` with `if: always()` so failure evidence is visible in the Actions log even when verification, artifact authentication, API log download, or local `gh` access is unavailable.

The CI evidence summary is a first-level triage surface. It does not replace `artifacts/latest_verify.json`, QEMU smoke metadata, QEMU serial/stderr logs, or boot blocker reports as generated evidence.

The CI-observed timeout or runtime state must be narrowed when possible. QEMU
smoke metadata blocker vocabulary is owned by
`contracts/runtime_evidence_taxonomy.v0.json`, including
`capability_dispatch_not_reached`, `runtime_status_query_not_completed`,
`first_governed_capability_not_proven`, `runtime_state_update_not_reached`,
`runtime_state_update_not_completed`, and
`second_governed_capability_not_proven`; all blocked states remain evidence
limitations and do not authorize a pass.

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

For v0.8.1, full CI must also run
`cpu_extended_state_initialization_contract` and
`cpu_extended_state_initialization_evidence`. Passing evidence requires CPUID
feature checks, preserved and read-back CR0/CR4 policy, x87/MXCSR validation,
the bounded SIMD probe, no prohibited AVX state or instructions, complete
metadata/log agreement, the unchanged runtime suffix, and the halt contract.

For v0.8.2, full CI must also run
`runtime_state_transition_capability` and
`runtime_state_transition_capability_evidence`. Passing evidence requires
fixed geometry, exact direct dispatch, volatile READY/0-to-ACTIVE/1 mutation
and readback, response validation before success, complete metadata/log
agreement, the unchanged first capability, exact return, and halt convergence.

For v0.8.3, full CI must also run `fixed_user_mapping_foundation` and
`fixed_user_mapping_foundation_evidence`. Passing evidence requires fixed
four-level geometry, page-aligned symbols, explicitly cleared tables,
effective U/S propagation, supervisor-only kernel policy, W^X, NX support,
pre-activation software walks, exact masked CR3 readback, post-activation
survival checks, complete QEMU metadata/log agreement, and the unchanged
runtime return and halt path.

# 9. v0.8.4 Privilege-Transition Checks

Full CI must run `bounded_privilege_transition_probe_contract` and
`bounded_privilege_transition_probe_evidence`. Passing evidence requires:

* contract-valid fixed selectors, descriptor tables, stacks, entry, return,
  token, statuses, markers, and non-goals;
* source and ELF evidence for `iretq`, `int 0x81`, TSS.RSP0, saved-frame
  validation, fixed continuation, and fault-to-halt convergence;
* exact QEMU metadata/log agreement for all privilege markers;
* preserved fixed-mapping, CPU-state, progression, capability, return, and
  halt validators;
* no public syscall, arbitrary target, return-to-user, or general userspace
  path.

# 10. v0.8.5 Fixed User Request Boundary Checks

Full CI must run `fixed_user_request_boundary_contract` and
`fixed_user_request_boundary_evidence`. Passing evidence requires:

* contract-valid exact request/response geometry, service semantics, copy
  policy, clearing, marker order, failures, and non-goals;
* source and ELF evidence for fixed Ring3 request construction, hardware-frame
  and full-span validation, supervisor shadows, exact copy/service/readback
  order, zero validation, and fixed continuation;
* exact QEMU metadata/log agreement for all four boundary markers;
* preserved fixed mapping, privilege transition, CPU state, progression,
  capability, runtime return, and halt validators;
* no arbitrary pointer, arbitrary length, generic copy API, broad syscall
  dispatch, return-to-user, or persistent-userspace path.

# 11. v0.8.6 Bounded User Response Consumption Checks

`bounded_user_response_consumption_contract` and
`bounded_user_response_consumption_evidence` are required. Full verification
must also pass the fixed request, privilege transition, user mapping,
CPU-state, runtime capability, QEMU smoke, schema, and halt checks. Missing,
duplicated, reordered, or metadata-only response markers are blocking.

# 12. v0.8.7 Runtime Status Service Checks

`fixed_user_runtime_status_service_contract` and
`fixed_user_runtime_status_service_evidence` are required. Full verification
must prove post-loop collection, one shared status source, fixed response
geometry, complete Ring 3 and Ring 0 validation, digest validation, snapshot
cleanup, exact QEMU metadata/log agreement, unchanged internal capability ID
1 behavior, capability ID 2 continuation, and terminal halt.
