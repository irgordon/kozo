# KOZO Release Checklist

Version: 1
Status: Authoritative
Scope: Release approval checklist for scoped KOZO releases

---

# 1. Purpose

This document defines the checklist used to decide whether a KOZO release is allowed, blocked, or deferred.

It converts release planning into reviewable release gates.

---

# 2. Authority

`docs/RELEASE_CHECKLIST.md` owns release approval checklist requirements.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`
* checked-in contracts
* schemas
* validators

It does not define runtime behavior, ABI truth, syscall truth, compatibility claims, validator logic, or generated artifact policy.

---

# 3. Non-Goals

This document does not claim production readiness.

This document does not claim Linux compatibility.

This document does not claim POSIX completeness.

This document does not claim general userspace execution.

This document does not claim process model, VFS, scheduler, ELF loading, or file descriptor behavior.

This document does not authorize bypassing governance, invariants, compatibility policy, or validation policy.

---

# 4. Blocker Categories

| Priority | Meaning | Release Effect |
| --- | --- | --- |
| P0 | Correctness, security boundary, or release integrity blocker. | Blocks release. |
| P1 | v1.0.0 credibility blocker. | Blocks v1.0.0 release. |
| P2 | Release candidate blocker. | Blocks release candidate promotion unless explicitly waived through governance. |
| P3 | Non-blocking cleanup or polish. | May be deferred when release claims and evidence remain accurate. |

---

# 5. Approval Rules

A release is allowed only when:

* every required checklist item is complete or explicitly marked not applicable with evidence
* every P0 and P1 blocker is resolved
* every P2 blocker is resolved or waived through governance
* release notes describe only evidence-backed behavior
* compatibility non-goals remain explicit
* required checks are green
* release evidence is complete

Emergency bypass of required checks is not allowed by this document.

Maintainer emergency action, if ever needed, must be documented in a release decision record and must not create unsupported compatibility or production-readiness claims.

---

# 6. Repository State

Required checklist:

* Release branch is correct.
* Working tree is clean.
* Release commit is identified.
* Tag candidate is identified.
* `CHANGELOG.md` is current.
* Release notes are present when required by the phase.
* `docs/PHASEMAP.md` and `docs/ROADMAP.md` match the intended release scope.

Evidence references:

* `git status --short --branch`
* `git log --oneline --decorate -n 5`
* `CHANGELOG.md`
* `docs/PHASEMAP.md`
* `docs/ROADMAP.md`

---

# 7. Verification Gates

Required checklist:

* `scripts/verify.sh` passes.
* `artifacts/latest_verify.json` status is `pass`.
* `artifacts/latest_verify.json` failed check count is `0`.
* `artifacts/runtime/runtime_smoke.log` is present.
* `artifacts/runtime/runtime_smoke.metadata.json` is present.
* `artifacts/runtime/boot_blocker_report.json` is present while boot is blocked.
* `artifacts/runtime/boot_image/package_metadata.json` is present while boot image packaging is blocked.
* `runtime_smoke_evidence` passes.
* `runtime_evidence_review` passes.
* `boot_blocker_report` passes while boot is blocked.
* `boot_image_packaging` passes while boot image packaging is blocked.
* `qemu_smoke_evidence` passes when QEMU smoke metadata is generated.
* Runtime evidence review is complete.
* Runtime metadata non-goals are reviewed.
* Full CI uploaded `artifacts/runtime/runtime_smoke.log` when available.
* Full CI uploaded `artifacts/runtime/runtime_smoke.metadata.json` when available.
* Full CI uploaded `artifacts/runtime/boot_blocker_report.json` while boot is blocked.
* `artifacts/runtime/qemu_smoke.log` is reviewed when the QEMU blocker is under direct review.
* `artifacts/runtime/qemu_smoke.stderr.log` is reviewed when the QEMU blocker is under direct review.
* `artifacts/runtime/qemu_smoke.metadata.json` is reviewed when the QEMU blocker is under direct review.
* QEMU smoke metadata outcome may use only a blocker governed by `contracts/runtime_evidence_taxonomy.v0.json`; capability blockers do not authorize a pass or broaden runtime claims.
* QEMU smoke metadata early markers, observed markers, earliest marker, timeout state, and byte counts are reviewed when the QEMU blocker is under direct review.
* QEMU smoke metadata outcome is `pass` before any QEMU boot claim is made.
* Passing QEMU smoke metadata includes `KOZO_RUNTIME_RETURN_OK` as the expected marker.
* Passing QEMU smoke serial output includes the taxonomy-owned sequence through `KOZO_RUNTIME_LOOP_EXIT_OK`, `KOZO_CAPABILITY_DISPATCH_ENTER`, `KOZO_RUNTIME_STATUS_QUERY_OK`, `KOZO_FIRST_CAPABILITY_OK`, and `KOZO_RUNTIME_RETURN_OK` in order.
* `runtime_progression_entry_contract` and `runtime_progression_evidence` pass.
* The kernel ELF report records the progression entry, bootstrap context, static state, and fixed serial bridge symbols.
* Memory evidence review includes the contract-owned region geometry, full zero fill, bounded sentinel probe, restoration, marker order, and unchanged halt path.
* QEMU serial smoke evidence is promoted only from a green CI run with passing metadata and the full ordered marker sequence.
* Passing QEMU serial smoke evidence is reviewed as a narrow smoke claim, not as hardware trap, userspace, subsystem, compatibility, or production-readiness evidence.
* Release is blocked if runtime evidence is overclaimed or missing required non-goals.
* No QEMU or boot claim is made unless separately implemented and proven.
* Python unit tests pass.
* Odin check/build passes through verification.
* Pinned Rust cargo check passes.
* `git diff --check` passes.

Evidence references:

* `artifacts/latest_verify.json`
* `artifacts/runtime/runtime_smoke.log`
* `artifacts/runtime/runtime_smoke.metadata.json`
* `artifacts/logs/odin-check.log`
* `artifacts/logs/odin-build.log`
* `artifacts/logs/cargo-check.log`
* `artifacts/logs/nm-kernel.log`
* `docs/RUNTIME_EVIDENCE.md`
* `docs/RUNTIME_EVIDENCE_REVIEW.md`

---

# 8. Generated Report Gates

Required checklist:

* `docs/generated/governance_index.md` is current.
* `docs/generated/syscall_surface.md` is current.
* `docs/generated/abi_surface.md` is current.
* Generated ABI bindings self-identify as generated files.
* Generated reports state their non-authoritative status.
* Generated artifacts were produced by their governed generator or verification path.

Evidence references:

* `docs/generated/governance_index.md`
* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* `bindings/rust/kozo_abi.rs`
* `bindings/odin/kozo_abi.odin`

---

# 9. Contract Gates

Required checklist:

* ABI manifest is valid.
* Syscall boundary contract is valid.
* Syscall table contract is valid.
* Syscall class contract is valid.
* Syscall catalog is valid.
* Schemas are valid.
* Contract-backed claims match generated reports and release notes.

Evidence references:

* `contracts/kozo_abi_manifest.json`
* `contracts/syscall_boundary_contract.v0.json`
* `contracts/syscall_table_contract.v0.json`
* `contracts/syscall_class_contract.v0.json`
* `contracts/syscall_catalog.v0.json`
* `schemas/`

---

# 10. CI Gates

Required checklist:

* Required GitHub Actions checks pass.
* `ci / full verification` passes.
* `lint / static checks` passes.
* Required target/toolchain setup is confirmed.
* Runtime smoke evidence is generated by `ci / full verification`.
* Boot blocker report is generated by `ci / full verification` while boot is blocked.
* QEMU smoke log and metadata are uploaded by `ci / full verification` when generated.
* Runtime smoke evidence is not required from `lint / static checks` unless lint runs full verification.
* CI evidence is recorded by URL or status when available.

Evidence references:

* GitHub Actions `ci` workflow status.
* GitHub Actions `lint` workflow status.
* `docs/REQUIRED_CHECKS.md`.

---

# 11. Compatibility Gates

Required checklist:

* No broad Linux compatibility claim is present.
* No POSIX completeness claim is present.
* No general userspace execution claim is present unless scoped and evidence-backed.
* No process model, VFS, scheduler, ELF loading, or file descriptor claim is present unless scoped and evidence-backed.
* No production-readiness claim is present outside the scoped release statement.
* Release notes include known non-goals.

Evidence references:

* `docs/COMPATIBILITY.md`
* `docs/generated/syscall_surface.md`
* `docs/generated/abi_surface.md`
* release notes

---

# 12. Security and Governance Gates

Required checklist:

* Invariants are reviewed.
* Security model is reviewed.
* Generated artifact policy is reviewed.
* Validation policy is reviewed.
* Release evidence bundle is complete.
* Release scope does not conflict with authoritative governance.

Evidence references:

* `docs/INVARIANTS.md`
* `docs/SECURITY_MODEL.md`
* `docs/GENERATED_ARTIFACTS.md`
* `docs/VALIDATION.md`
* `docs/RELEASE_EVIDENCE.md`

---

# 13. Release Evidence Bundle

Required checklist:

* `artifacts/latest_verify.json` is included.
* Verification logs are included.
* Generated reports are included.
* Contracts are included.
* Schemas are included.
* Changelog is included.
* Release notes are included when available.
* CI run references are included when available.
* Runtime smoke evidence is included for v0.2.0 and later.
* Runtime smoke metadata is included for v0.2.1 and later.
* Runtime evidence review is included for v0.2.3 and later.
* CI/runtime evidence policy alignment is included for v0.2.4 and later.
* Boot blocker report is included for v0.3.0 until QEMU boot evidence replaces it.

The release evidence bundle shape is owned by `docs/RELEASE_EVIDENCE.md`.

For v0.7.5 and later, confirm the controlled runtime loop contract and evidence validators pass, the ELF report records the linked loop symbols and backward branch, hosted QEMU evidence contains the ordered loop markers, exact return evidence follows loop exit, and the halt contract still passes. Do not promote the loop stage from local source or ELF evidence alone.

For v0.8.0 and later, confirm the first capability contract and evidence validators pass, request and response validation remain explicit, the ELF report records dispatcher/handler/bridge symbols and the progression call edge, hosted QEMU evidence contains all three capability markers before runtime return, and failure paths cannot emit success markers. Do not promote the capability from local source or ELF evidence alone.

For v0.8.1 and later, confirm the CPU extended-state contract and evidence
validators pass, the ELF report records CPU-state symbols and required
instructions, no governed AVX/YMM/ZMM/`xsetbv` use exists, hosted QEMU contains
the three CPU-state markers before runtime progression, the full capability
suffix remains present, and the terminal halt contract still passes.

For v0.8.2 and later, confirm both state-transition validators pass, capability
ID 1 behavior remains unchanged, ELF evidence records the state cell, direct
ID 2 route, handler, accessors, and fixed bridges, and hosted QEMU contains the
ordered update-entry, update-success, second-capability, return, and halt
evidence. Reject any release evidence that implies arbitrary memory writes,
concurrency, userspace access, authorization, persistence, or isolation.

For v0.8.3 and later, confirm both fixed user-mapping validators pass; ELF
evidence records seven aligned table pages and three aligned backing pages;
effective U/S propagates across PML4E/PDPTE/PDE/PTE; kernel leaves remain
supervisor-only; code is RX and data/stack are RW-NX; CR3 readback matches;
QEMU captures all five mapping markers before runtime entry; and the existing
capability, return, and halt evidence remains present. Do not infer Ring 3 or
isolation from Ring 0 survival probes.

---

# 14. Release Decision

Every release review must record one decision:

* release allowed
* release blocked
* release deferred

The decision record must include:

* release candidate version
* release commit
* tag candidate
* checklist result
* blocker category, if any
* required follow-up
* reviewer or maintainer approval

Release decision records may be stored in release notes, issue trackers, or a later governed release record file.

---

# 15. v0.8.4 Privilege-Transition Gate

For v0.8.4 and later, confirm:

* both bounded privilege-transition validators pass;
* the accepted fixed user-mapping validators remain green;
* ELF evidence records fixed GDT, TSS, IDT, stack, user-target, return-handler, continuation, `iretq`, and `int 0x81` paths;
* hosted QEMU captures all five privilege markers between mapping survival and Odin entry;
* the complete capability suffix and terminal halt remain present;
* no known failure path emits Ring3-probe, Ring0-return, or runtime-return success.

Reject any release claim that treats this fixed boot-time probe as general
userspace, process isolation, public syscall handling, exception recovery, or
production readiness.

---

# 16. v0.8.5 Fixed User Request Boundary Gate

For v0.8.5 and later, confirm:

* `fixed_user_request_boundary_contract` and
  `fixed_user_request_boundary_evidence` pass;
* ELF evidence records exact request, response, and verification-shadow
  geometry and the ordered handler call chain;
* hosted QEMU captures all four fixed-boundary markers between Ring3 entry and
  the existing Ring3-probe marker;
* request and response spans remain fixed within the governed user data page;
* all boundary buffers are cleared and verified zero before continuation;
* the accepted privilege, capability, runtime-return, and halt evidence remains
  green.

Reject any release claim that generalizes this transaction into arbitrary
user pointers, a public syscall ABI, persistent userspace, process isolation,
hostile-code safety, compatibility, or production readiness.

# 17. v0.8.6 Bounded User Response Consumption Gate

Confirm:

* v0.8.5 remains accepted;
* both response-consumption validators pass;
* QEMU reports `pass`, blocker `none`, and all 40 markers exactly once;
* the three new markers occur between response copy-out and fixed-request
  completion;
* ELF evidence proves fixed phase/shadow geometry, two entries, response
  revalidation, exact record copy, clearing, and the fixed continuation;
* no later success marker exists on a failed response path;
* existing paging, privilege, CPU-state, capability, return, and halt evidence
  remains green;
* no persistent Ring 3 runtime, general syscall ABI, arbitrary pointer,
  process, compatibility, or production claim was added.

# 18. v0.8.7 Runtime Status Service Gate

Confirm:

* `fixed_user_runtime_status_service_contract` and
  `fixed_user_runtime_status_service_evidence` pass;
* hosted QEMU reports `pass`, blocker `none`, and all 41 markers exactly once;
* the controlled-loop exit precedes Ring 3 entry;
* service entry follows request copy-in and service success precedes copy-out;
* the 64-byte snapshot and 88-byte response geometry match source and ELF;
* Ring 3 and Ring 0 validate every response field and the record digest;
* the snapshot and all transaction buffers clear before capability ID 2;
* both existing internal capability validators and terminal halt remain green;
* no general dispatcher, public ABI, persistent userspace, compatibility, or
  production claim was added.

# 19. v0.8.8 Core Service License Gate

The `core_service` package selects the MIT option provided by the KOZO
repository license set. Cargo records this selection as:

```toml
license = "MIT"
```

The root `LICENSE-MIT` file is the authoritative MIT license text. Confirm:

* Cargo metadata reports package name `core_service`, license `MIT`, and no
  package-specific license file;
* the root `deny.toml` allows the exact `MIT` SPDX value without a crate
  exception;
* `cargo deny check licenses` passes without an exception;
* the full `cargo deny check` passes without weakening license policy;
* `cargo package --manifest-path userspace/core_service/Cargo.toml --list`
  contains only the expected manifest, lockfile, Cargo metadata, and source;
* the package version, edition, dependencies, target, and runtime behavior are
  unchanged;
* full KOZO verification and QEMU evidence remain green.

This gate removes one package-metadata blocker. It does not publish the
package or establish complete v1.0.0 release readiness.

# 20. v0.8.9 Documentation and Adoption Gate

Confirm:

* the root README explains purpose, current behavior, quick start, expected
  result, limits, and documentation paths before implementation detail;
* `docs/wiki` contains the required user, maintainer, troubleshooting,
  terminology, and engineering pages;
* `docs/DOCUMENTATION_AUDIT.md` records document and source-comment review;
* current-facing version, check, marker, and hosted-acceptance claims match the
  accepted baseline;
* local Markdown links resolve;
* every executable wiki command was run and failures were recorded honestly;
* redundant comments were removed without deleting hardware, ABI, security,
  fail-closed, compiler, or toolchain constraints;
* full verification and QEMU preserve all 67 checks and 41 markers.

This gate improves understanding and adoption readiness. It does not add a
runtime feature or complete release-candidate hardening.

# 21. v1.0.0-rc.1 Pre-Promotion Hardening Gate

The candidate version is owned by `release/version.txt`. The display and tag
form is `v1.0.0-rc.1`; the archive and metadata form is `1.0.0-rc.1`.

This section records the gate before promotion. Current post-promotion status
is recorded in section 22.

| Item | Status | Evidence | Follow-up |
| --- | --- | --- | --- |
| Correct branch and clean source commit | Complete locally | `git status --short --branch`; release builder clean-tree gate | Reconfirm before final approval. |
| Version consistency | Complete locally | `release/version.txt`, archive name, release metadata, release notes | Hosted bundle must report the same version. |
| Changelog and release notes | Complete locally | `CHANGELOG.md`, `docs/releases/v1.0.0-rc.1.md` | Maintainer approval remains required. |
| Phase map and roadmap alignment | Complete locally | `docs/PHASEMAP.md`, `docs/ROADMAP.md` | No runtime scope added. |
| Full verification | Complete locally | `artifacts/latest_verify.json` | Hosted run must pass 67 checks with zero failures. |
| QEMU evidence | Complete locally | QEMU log, metadata, and summary | Hosted run must pass with blocker none and 41 markers. |
| Python, Odin, and Rust checks | Complete locally | local command output | Hosted checks remain required. |
| Cargo license and advisory policy | Complete locally | `cargo deny check`, `cargo audit` | Hosted CI must reproduce both. |
| Generated reports | Complete locally | governed generators and verification | Commit generated proof separately. |
| Contract and schema gates | Complete locally | verification report | Hosted verification must preserve all 67 checks. |
| Compatibility and security claim review | Complete locally | release notes and security policy | Keep fixed-probe limits explicit. |
| Explicit artifact manifest | Complete locally | `release/release_files.v1.json` | No wildcard or whole-repository packaging. |
| Boot image and kernel ELF | Complete locally | two dry-run outputs, direct extraction, and checksums | Hosted bundle must preserve both files. |
| Runtime and verification evidence | Complete locally | archive `evidence/` tree from both dry runs | Missing required evidence blocks packaging. |
| MIT and Apache-2.0 legal files | Complete locally | byte-for-byte archive checks | `NOTICE` is not present or required. |
| SHA-256 checksums | Complete locally | internal and external `SHA256SUMS` from both dry runs | Hosted entries must also validate. |
| Prohibited-file scan | Complete locally | direct extraction inspection from both dry runs | Any match blocks the candidate. |
| Packaging-level repeatability | Complete locally | two 104-file bundles with stable file lists and legal/release-note bytes | Generated timestamps differ; no bit-for-bit claim is authorized. |
| Hosted checks | Complete | CI run `30409678216`; lint run `30409678072` | No required-check branch policy is authorized by this phase. |
| Pull-request review | Not required by this phase | live REST and GraphQL protection readback | No review policy was added. |
| Force-push prevention | Complete | `allow_force_pushes.enabled: false`; `allowsForcePushes: false` | Branch deletion remains allowed. |
| Administrator enforcement | Not required by this phase | `enforce_admins.enabled: false`; `isAdminEnforced: false` | No administrator policy was added. |
| CI deprecation warnings | Complete | hosted Node 24 action and authenticated Odin setup runs | Hosted logs contain no matching warning. |
| Publication | Not applicable | metadata records `published: false` | Do not tag, publish, or create a release in this phase. |

Final promotion readiness requires only the force-push block authorized for
this phase, a fresh directly inspected dry-run bundle, preserved runtime
evidence, and separate authorization before tag or prerelease publication.

# 22. v1.0.0-rc.1 Post-Promotion Gate

| Item | Status | Evidence | Follow-up |
| --- | --- | --- | --- |
| Annotated tag | Complete | local Git, remote Git, and GitHub tag readback | Treat the tag as immutable. |
| GitHub prerelease | Complete | live release API; prerelease true and draft false | Do not edit the hosted record in place. |
| Approved asset set | Complete | exactly six hosted assets | A correction requires a new candidate. |
| Hosted checksums | Complete | downloaded `SHA256SUMS`; accepted archive hash | Preserve the accepted files. |
| Distributed ISO boot | Complete | hosted ISO QEMU smoke | 41 ordered markers; final marker `KOZO_RUNTIME_RETURN_OK`. |
| Hosted ELF and JSON | Complete | direct ELF inspection and JSON validation | Architecture, symbols, metadata, and proof match the candidate. |
| Clean user path | Complete | clean tagged clone and extracted hosted archive | `ld.lld --version` is the portable linker check used by the guide. |
| Technical gate | Accepted | 67 checks, zero failures, QEMU pass, blocker none | Runtime behavior remains unchanged. |
| RC promotion | Complete | [current status](releases/v1.0.0-rc.1-status.md) | Observe the candidate; do not repair it in place. |
| Final v1.0.0 release | Not created | no `v1.0.0` promotion record | Requires separate explicit authorization. |

No reproducible final-release blocker was found during post-promotion
verification. General cleanup wishes and unimplemented out-of-scope features
are not blockers for the declared release scope.

# 23. v1.0.0 Final Release Gate

Final release authorization is complete. The `v1.0.0` tag and GitHub release
are immutable publication records for accepted commit
`1586089415a98a11d2024d606ce6301f568b7d6e`.

| Item | Status | Evidence | Follow-up |
| --- | --- | --- | --- |
| Version authority | Complete locally | `release/version.txt` contains `1.0.0` | Hosted metadata must match. |
| Final notes and evidence | Complete locally | `docs/releases/v1.0.0.md`, `docs/releases/v1.0.0-evidence.md` | Fill hosted fields after publication. |
| Runtime behavior | Unchanged | no kernel, ABI, contract, request, marker, mapping, capability, or halt edits | Reconfirm in local and hosted verification. |
| Full local gate | Complete | 1,050 Python tests; Odin, Rust, cargo policy; verification run `verify-20260729T201733Z`; QEMU pass | Preserve the result in the generated proof commit. |
| Final bundle | Complete | Two 104-file bundle inventories; direct extraction; internal/external checksums | Approved archive SHA-256 `bb74de23e62a87ae26f21252388007822b4764f2cf98626c157f28422dd41897`. |
| Hosted final-commit gate | Complete | CI run `30495209451`; lint run `30495209186` | Both passed before tagging. |
| Annotated final tag | Complete | object `059fe90572db46185c219e8b38bbd190faa40e60`; target `1586089415a98a11d2024d606ce6301f568b7d6e` | Treat as immutable. |
| Final GitHub release | Complete | <https://github.com/irgordon/kozo/releases/tag/v1.0.0> | Non-draft and non-prerelease. |
| Hosted asset verification | Complete | six fresh downloads; checksum and byte comparison | All hosted files match approved local files. |
| RC preservation | Complete after promotion | tag, notes, classification, six asset names/sizes/digests | Before/after records match. |
| Package publication | Not authorized | `core_service` remains unpublished | Do not run `cargo publish`. |

This post-promotion record is the one authorized documentation/proof-only
commit on `main`. It does not alter the final tag, release notes, assets,
runtime, ABI, contracts, or marker sequence.

# 24. v1.0.1 Patch Release Gate

Patch release authorization was limited to `KOZO-TRIAGE-001`. Publication and
independent hosted-asset verification are complete; `v1.0.1` is the current
published release.

| Item | Status | Evidence | Follow-up |
| --- | --- | --- | --- |
| Version authority | Complete | `release/version.txt` and hosted metadata contain `1.0.1` | Advance only through a later authorized release. |
| Patch notes and evidence | Complete | `docs/releases/v1.0.1.md`, `docs/releases/v1.0.1-evidence.md` | Treat hosted notes as immutable. |
| Authorized correction | Complete on `main` | exact, `.o`, and legacy `.obj` outputs normalize through one fail-closed helper | Preserve the accepted implementation. |
| Runtime behavior | Unchanged | no kernel, userspace runtime, ABI, contract, schema, marker, mapping, capability, or halt edits | Reconfirm locally and in hosted CI. |
| Full local gate | Complete | 27 focused tests; 1,058 full tests; Odin, Rust, and cargo policy pass; verification `verify-20260807T214144Z`; QEMU pass with 41 markers | Runtime behavior remains unchanged. |
| Final bundle | Complete | 104-file archive plus five supporting assets; direct metadata, license, checksum, and prohibited-path inspection | Hosted CI bundle selected as publication source. |
| Hosted release-commit gate | Complete | CI `31223062540`; lint `31223061928` at `02f1b0113458b988562b7e03362ec9ae716cebd0` | Both passed before tagging. |
| Annotated patch tag | Complete | object `7896c767376a666ad7f7d8f294beadb473b0290c`; exact hosted-approved target | Treat as immutable. |
| Final GitHub release | Complete | <https://github.com/irgordon/kozo/releases/tag/v1.0.1>; six approved assets | Non-draft and non-prerelease. |
| Hosted asset verification | Complete | fresh download, `SHA256SUMS`, byte comparison, JSON validation, hosted ISO QEMU | 41 markers; final marker `KOZO_RUNTIME_RETURN_OK`. |
| Prior release preservation | Complete | v1.0.0 and v1.0.0-rc.1 tag objects, classifications, and asset digests | Records remain unchanged. |
| Package publication | Not authorized | `core_service` remains unpublished | Do not run `cargo publish`. |

# 25. v1.1.0 Feature Release Gate

v1.1.0 is authorized because the accepted Fixed User Execution Context and
Bounded Repeated User Session add runtime capability. v1.0.2 is skipped.

| Item | Status | Evidence | Follow-up |
| --- | --- | --- | --- |
| Version authority | Prepared | `release/version.txt` contains `1.1.0` | Hosted metadata must match. |
| Notes and evidence | Prepared | `docs/releases/v1.1.0.md`, `docs/releases/v1.1.0-evidence.md` | Complete immutable hosted fields after publication. |
| Runtime capability | Accepted on `main` | fixed context, two sessions, four returns, verified reset | Preserve exact two-session scope. |
| Full local gate | Complete | 337 focused and 1,284 full Python tests; Odin, Rust, cargo policy; 67/0 verification | Reproduce at exact target in hosted CI. |
| Runtime evidence | Complete locally | QEMU pass, blocker none, 52 ordered markers | Test the exact packaged and downloaded ISO. |
| Host portability | Pending fresh target run | pinned Linux, Windows, and macOS build contracts | Linux runtime and aggregate input identity remain required. |
| Final bundle | Pending exact commit | established six-asset output | Validate checksums, metadata, inventory, and licenses. |
| Annotated tag | Not created | `v1.1.0` absent before hosted acceptance | Target only the exact accepted proof commit. |
| Final GitHub release | Not created | authorized after tag verification | Final, non-draft, non-prerelease. |
| Hosted download | Pending publication | fresh six-asset download and QEMU run required | Do not substitute local bytes. |
| Prior releases | Preserved | v1.0.1, v1.0.0, and v1.0.0-rc.1 readback | Never replace their tags, notes, or assets. |
| Package publication | Not authorized | `core_service` remains unpublished | Do not run `cargo publish`. |
