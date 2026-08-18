# KOZO Roadmap

Version: 1.1.0
Status: Published final feature release
Release commit: a5226635be46c687299028b5244f808da67c0984
Scope: Product direction and release gates from the published KOZO v1.1.0 baseline

---

# 1. Purpose

This roadmap describes how KOZO moves from a governance-proven prototype to a release-gated, evidence-backed minimal operating-system substrate.

It defines direction, goals, deferred work, and release expectations.

---

# 2. Authority

`docs/ROADMAP.md` owns product direction and release goals.

It does not override:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/COMPATIBILITY.md`
* checked-in contracts
* schemas
* validators

Roadmap entries are planning commitments, not claims that behavior already exists.

---

# 3. Product Thesis

KOZO is a small, contract-backed operating-system substrate where every
claimed boundary is explicit, verified, and supported by reproducible release
evidence.

The v1.1.0 baseline proves bounded user execution through one fixed execution
context and exactly two sequential fixed sessions. Future work should add one
concrete capability at a time without broad compatibility, process, or
production-readiness claims that exceed the evidence.

---

# 4. Goals

* Preserve the immutable v1.1.0 release baseline and its downloadable evidence.
* Maintain strict contract-backed development.
* Extend usable runtime capability one bounded feature at a time.
* Keep compatibility claims narrow and evidence-tiered.
* Make release evidence reproducible from committed inputs and hosted assets.
* Keep generated reports current and non-authoritative.
* Preserve validator coverage, cross-host build portability, and release-input identity.

---

# 5. Non-Goals

The roadmap does not add or imply:

* Linux compatibility
* POSIX completeness
* general or persistent userspace execution
* third, arbitrary, or concurrent user sessions
* process lifecycle or scheduling
* physical-frame allocation, heap allocation, or general virtual memory
* VFS, filesystem, or file descriptor behavior
* executable loading
* device-driver or networking behavior
* a stable public ABI
* production readiness beyond the scoped release definition

---

# 6. Release Themes

| Theme | Goal |
| --- | --- |
| Governance | Keep authority, invariants, contracts, validation, compatibility, and generated artifact policy separated. |
| Evidence | Make every release claim reproducible from checked-in commands and artifacts. |
| Runtime | Add runtime execution evidence beyond source-shape proof. |
| Security | Move security model rules into minimal implementation-backed checks. |
| ABI and syscalls | Keep the current ABI/syscall surface stable unless expanded through governed process. |
| Compatibility | Preserve explicit non-goals until implementation and evidence justify scoped claims. |

---

# 7. Current Proven Capabilities

The current repository proves:

* governed ABI, syscall, runtime trap, return-path, layout, and protocol proof surfaces through the verification harness
* generated report governance for ABI, syscall, and governance surfaces
* host dependency portability through CI/Linux policy checks
* boot image skeleton, Limine configuration, ISO generation path, and QEMU smoke command existence
* higher-half kernel ELF loadability metadata with no local lower-half PHDR blocker
* assembly-level entry, serial initialization, and final smoke marker emission in source
* CI-proven QEMU serial smoke evidence with the full ordered marker sequence
* governed post-smoke terminal behavior through `contracts/runtime_halt_contract.v0.json`
* governed future halt-to-runtime transition planning through `contracts/runtime_progression_contract.v0.json`
* governed internal progression boundary through `contracts/runtime_progression_entry_contract.v0.json`, proven by hosted CI marker and validator evidence
* governed, acyclic runtime progression stage ordering and transition ownership through `contracts/runtime_progression_stages.v0.json`
* governed stack initialization evidence through `contracts/stack_initialization_evidence_contract.v0.json` and `stack_initialization_evidence`
* governed static-memory initialization evidence through `contracts/memory_initialization_evidence_contract.v0.json` and `memory_initialization_evidence`, accepted by the CI validator gate without manual artifact inspection
* hosted-CI-proven internal assembly-to-Odin progression boundary and bounded volatile Odin state probe
* hosted-CI-proven contract-backed three-iteration controlled Odin loop with linked-symbol, backward-edge, terminal-comparison, marker-order, and halt-continuation validation
* hosted-CI-proven versioned internal runtime status query with fixed request/response geometry, explicit dispatch, response validation, linked-symbol evidence, and governed capability markers
* hosted-CI-proven boot-CPU x87/SSE initialization with CPUID checks, CR0/CR4 readback, x87/MXCSR validation, and one bounded SSE2 probe before Odin entry
* hosted-CI-proven capability ID 2 path for one fixed boot-owned READY/0-to-ACTIVE/1 volatile state transition and validated response
* hosted-CI-proven fixed user-mapping foundation with supervisor-only kernel leaves, user RX/RW-NX pages, effective U/S propagation, W^X, exact CR3 readback, and bounded survival
* hosted-CI-proven fixed CPL0-to-CPL3 `iretq` probe, DPL3 `int 0x81` return through TSS.RSP0, saved-frame/token validation, fixed CPL0 continuation, and unchanged capability/halt suffix
* hosted-accepted exact fixed user request boundary with complete-span validation, supervisor-only shadows, deterministic service, response readback, verified request-side clearing, and unchanged privilege/capability/halt paths
* hosted-CI-accepted bounded response consumption with one sanitized Ring3 resume, complete response validation, fixed 48-byte record, second gate entry, Ring0 revalidation, verified clearing, and phase reset
* hosted-CI-accepted runtime-ordered user status service with one shared
  post-loop snapshot, fixed 88-byte response, complete Ring3/Ring0 validation,
  and unchanged internal capability ID 1 behavior
* accepted MIT metadata and cargo-deny policy for `core_service` with unchanged
  runtime evidence
* hosted-CI-accepted v0.8.9 documentation and adoption path with 67 checks,
  0 failures, QEMU pass, blocker none, and all 41 markers
* hosted-CI-accepted Fixed User Execution Context with one 128-byte
  supervisor-owned context and one separate 32-byte non-authoritative result,
  both in supervisor RW-NX static storage,
  lifecycle `UNINITIALIZED -> READY -> ACTIVE -> RETURNED -> CLEARED`, exact
  two-return phase/count coupling, verified cleanup, CI run `31563696881`, 67
  governed checks, and the then-authoritative 41-marker sequence
* hosted-CI-accepted Bounded Repeated User Session with exactly two sequential
  sessions, distinct nonzero opaque kernel identities, four total `int 0x81`
  returns, verified reset of result, transaction buffers, scratch storage, and
  user stack, fail-closed rejection of a third session or fifth return, and a
  repeated 11-marker transaction block that increased ordered occurrences from
  41 to 52; CI run `31899981058` passed 1,284 Python tests
* final v1.1.0 feature release from exact hosted-accepted commit
  `a5226635be46c687299028b5244f808da67c0984` with six assets, pre-upload
  SHA-256 values matching fresh GitHub downloads, and a downloaded ISO that
  booted with two completed sessions through 52 ordered markers ending at
  `KOZO_RUNTIME_RETURN_OK`

The final v1.1.0 release is the current published capability baseline. Detailed
release evidence is owned by `docs/RELEASE_EVIDENCE.md`.

---

# 8. Current Limitations

KOZO still does not prove:

* complete Odin runtime readiness or dynamic initialization
* general stack readiness beyond the controlled boot, user, and Ring 0 return stacks
* general memory management beyond the governed static regions and fixed mappings
* more than exactly two sequential fixed user sessions
* arbitrary, concurrent, persistent, or user-selected sessions
* general-purpose or persistent userspace beyond the fixed request/response transaction
* process identity, process lifecycle, scheduling, preemption, or concurrency
* physical-frame allocation, heap allocation, or dynamic virtual memory
* executable loading
* a public or general hardware syscall ABI beyond the fixed `int 0x81` path
* general interrupt handling or exception recovery
* AVX, XSAVE, extended-state context switching, or floating-point exception recovery
* filesystem, VFS, or file descriptor behavior
* device-driver or networking behavior
* Windows or macOS runtime validation
* Linux compatibility
* POSIX compatibility
* production readiness beyond the scoped v1.1.0 release evidence

---

# 9. Release Sequence

KOZO v1.1.0 is the current final release. It is published from exact
hosted-accepted commit `a5226635be46c687299028b5244f808da67c0984` and was
independently verified after download.

v1.0.2 was intentionally skipped. The Fixed User Execution Context and
Bounded Repeated User Session add runtime capability rather than correct only
a patch-level defect, so the governed release class is minor rather than
patch.

| Release | Purpose | Required Evidence | Explicit Non-Goals |
| --- | --- | --- | --- |
| `v1.0.0-rc.1` | Freeze and publish the first release candidate. | Annotated prerelease tag, six verified assets, checksum and downloaded-ISO validation. | Final-release claim or in-place mutation of tag, notes, or assets. |
| `v1.0.0` | Publish the governed kernel-foundation baseline. | Hosted CI/lint, 67 checks, QEMU pass, 41 markers, six assets, downloaded checksum and ISO proof. | General userspace, process model, scheduler, filesystem, drivers, or compatibility claims. |
| `v1.0.1` | Correct `KOZO-TRIAGE-001` at the Odin object-output boundary. | Focused exact/`.o`/`.obj` regressions, hosted release-bundle pass, 67 checks, 41 markers, and six verified assets. | Feature additions, runtime changes, ABI expansion, or in-place repair of v1.0.0. |
| `v1.1.0` | Publish the Fixed User Execution Context and Bounded Repeated User Session as one final feature release. | Exact commit `a5226635be46c687299028b5244f808da67c0984`; CI `31922319739`; lint `31922319746`; portability `31922319738`; 1,284 Python tests; 67 checks; Linux QEMU pass through 52 ordered markers; two sessions and four `int 0x81` returns; cross-host release-input identity; six assets; pre-upload/download SHA-256 match; downloaded ISO proof. | No process, scheduler, allocator, public ABI expansion, mapping change, interrupt-vector change, third or arbitrary session, Windows/macOS runtime claim, or in-place mutation of prior releases. |

No active release blocker is recorded. Any later capability, patch, or release
requires a separately scoped and evidenced task.

---

# 10. Current Runtime and Release Gates

Future work must preserve the accepted v1.1.0 boundary unless a separately
governed phase changes it:

1. Preserve exactly one fixed supervisor-owned execution context and its separate non-authoritative result.
2. Preserve exactly two sequential fixed sessions, distinct opaque identities, four total `int 0x81` returns, and verified inter-session reset.
3. Preserve fail-closed rejection of a third session, fifth return, stale authority, stale result, or stale transaction storage.
4. Preserve 67 governed checks and the 52-occurrence runtime sequence ending at `KOZO_RUNTIME_RETURN_OK` unless a separate evidence-governance phase authorizes a change.
5. Preserve Linux as `VALIDATED_RUNTIME`; preserve Windows 2025 under Git Bash and macOS 15 as `VALIDATED_BUILD` with runtime `NOT_EXECUTED`.
6. Preserve committed Git blobs as release-input authority and require cross-host release-input identity.
7. Require exact-commit hosted CI, lint, portability, package, checksum, metadata, and downloaded-artifact validation for every release.
8. Require the packaged and GitHub-downloaded ISO to reproduce the governed runtime result; a local rebuild is not a substitute for user artifact validation.
9. Preserve the six-asset release inventory unless a separately governed packaging change explains and validates a different set.
10. Preserve immutable prior tags, notes, classifications, and hosted assets.
11. Keep process, scheduler, allocator, loader, filesystem, drivers, networking, general public ABI, and broader runtime-host claims outside scope until separately implemented and proven.
12. Do not infer a next version or capability merely because v1.1.0 is complete.

---

# 11. Change Justification: v1.1.0 Instead of v1.0.2

v1.0.2 would have represented another patch-only correction to the v1.0.x
line. The accepted post-v1.0.1 work instead added two bounded runtime
capabilities:

* a Fixed User Execution Context with explicit identity, lifecycle, result, and cleanup;
* a Bounded Repeated User Session with exactly two sessions, fresh identity, verified reset, and four total user-to-kernel returns.

Those additions expand what KOZO can execute while preserving the existing
public and internal fixed transaction geometry. They therefore justify the
minor release `v1.1.0`, not a patch release `v1.0.2`.

No `v1.0.2` tag or GitHub release was created. This classification does not
claim a process model, scheduler, allocator, general userspace, or public ABI
expansion.

---

# 12. Deferred Work

Deferred until separately scoped and proven:

* a third, arbitrary, persistent, or concurrent user session
* process identity and process lifecycle
* scheduler, timer, preemption, and context switching
* physical-frame allocation, heap allocation, and dynamic virtual memory
* executable loading and general-purpose userspace
* public or expanded syscall ABI
* filesystem, VFS, and file descriptor behavior
* device drivers and networking
* Windows or macOS runtime validation
* Linux compatibility and POSIX completeness
* stable public ABI guarantees
* evidence-backed minimum CPU, RAM, and storage profiles
* production readiness beyond the scoped v1.1.0 release evidence

---

# 13. Roadmap Table

| Target | Theme | Goals | Non-Goals |
| --- | --- | --- | --- |
| `v0.1.0` | Release governance baseline | Define v1.0.0 scope, release evidence policy, `docs/RELEASE_CHECKLIST.md`, `docs/REQUIRED_CHECKS.md`, and generated report review inputs. | Runtime behavior changes, ABI changes, syscall changes, compatibility claims. |
| `v0.2.0` | Runtime execution evidence | Add governed runtime smoke evidence and logs using QEMU boot when feasible or a clearly labeled runtime-adjacent binary/symbol smoke path until boot packaging exists. | Broad userspace, Linux compatibility, process model, production readiness. |
| `v0.2.1` | Runtime evidence packaging | Add deterministic runtime evidence metadata, release bundle paths, review instructions, and retention guidance before attempting QEMU boot evidence. | QEMU boot claims, hardware trap claims, runtime feature expansion. |
| `v0.2.3` | Runtime evidence review gate | Add release-review claim discipline for runtime evidence paths, metadata, validators, release references, and overclaim blockers. | QEMU boot evidence, hardware trap execution evidence, compatibility claims, runtime feature expansion. |
| `v0.2.4` | CI/runtime evidence policy alignment | Make full CI, lint, required checks, release checklist, and release evidence policy agree on runtime smoke evidence requirements and artifact upload. | QEMU boot evidence, hardware trap execution evidence, compatibility claims, runtime feature expansion. |
| `v0.3.0` | Bootable runtime baseline | Attempt minimal QEMU boot evidence and, if blocked, record the concrete missing boot components as verified release evidence. | Linux compatibility, POSIX compatibility, userspace execution, runtime subsystem expansion, production readiness. |
| `v0.3.1` | Boot Protocol Selection | Select Limine as the initial x86_64 boot protocol and define the minimum implementation path toward QEMU serial smoke. | QEMU boot claim, hardware trap execution claim, runtime subsystem expansion. |
| `v0.3.2` | Boot Image Skeleton | Add linker script, Limine configuration, boot image staging, and a build path without claiming boot success. | QEMU boot claim, compatibility claims, userspace execution, production readiness. |
| `v0.3.3` | QEMU serial smoke evidence | Attempt QEMU serial smoke, add a fail-closed smoke command, and record the narrower bootable image packaging blocker when serial evidence cannot honestly be captured. | QEMU boot claim, Linux compatibility, POSIX compatibility, process model, VFS, scheduler, ELF loading, file descriptors. |
| `v0.3.4` | Bootable image packaging | Attempt bootable ISO packaging, generate package metadata, and record the missing Limine ISO tooling blocker without claiming an image exists. | QEMU boot claim, serial success claim, Linux compatibility, userspace execution, runtime subsystem expansion. |
| `v0.3.5` | Limine ISO Tooling Acquisition | Document Limine and xorriso acquisition, local install, CI install, provenance, and future version-pinning policy without vendoring opaque binaries. | Bootable ISO claim, QEMU boot claim, serial success claim, runtime subsystem expansion. |
| `v0.3.6` | Bootable ISO Generation | Implement the ISO generation command using the documented Limine and xorriso tooling path and record missing local ISO tooling if the image cannot be generated. | QEMU boot claim until serial evidence is captured, Linux compatibility, userspace execution, runtime subsystem expansion. |
| `v0.3.7` | CI ISO Tooling Install | Install xorriso and pinned Limine source tooling in full CI, run the boot image build path, and upload package metadata plus the ISO when produced. | QEMU boot claim, serial success claim, hardware trap claim, runtime subsystem expansion. |
| `v0.3.8` | QEMU Serial Smoke Evidence | Add QEMU smoke metadata, CI QEMU smoke execution, and validation for either a kernel-emitted `KOZO_BOOT_SMOKE_OK` serial marker or an exact blocked outcome. | Hardware trap execution claim, Linux compatibility, POSIX compatibility, process model, VFS, scheduler, ELF loading, file descriptors, production readiness. |
| `v0.3.9` | Fix QEMU Boot Path | Preserve the CI-observed `qemu_timeout` result as an exact blocker, add stderr log evidence, and reject any blocked record that already contains the kernel marker. | QEMU boot claim without captured marker, hardware trap execution claim, compatibility claims, runtime subsystem expansion. |
| `v0.3.10` | Security boundary foundation | Back pointer/null and authority-boundary rules with implementation evidence and negative tests. | Full formal verification, complete capability system. |
| `v0.4.0` | Kernel Entry Reachability | Add QEMU/Limine/kernel-entry diagnostics, early KOZO serial markers, and exact reachability blockers before making any QEMU boot claim. | QEMU boot claim without captured marker, hardware trap execution claim, compatibility claims, runtime subsystem expansion. |
| `v0.4.1` | Fix Limine Kernel Load | Fix the Limine kernel path or ISO layout and keep QEMU smoke blocker classification aligned with Limine load evidence. | QEMU boot claim without captured marker, kernel entry claim without `KOZO_EARLY_0_ENTRY`, compatibility claims, runtime subsystem expansion. |
| `v0.4.2` | Fix Kernel Binary Loadability | Add kernel ELF loadability evidence, validate entry/load segments, and narrow kernel-load blockers before further QEMU boot work. | QEMU boot claim, kernel entry claim without `KOZO_EARLY_0_ENTRY`, Limine ELF loading claim without evidence, compatibility claims, runtime subsystem expansion. |
| `v0.4.3` | Host Dependency Portability Gate | Add a harness gate proving build, verification, ISO, ELF, and QEMU smoke tooling use declared CI/Linux dependencies or controlled environment variables rather than local host paths. | Apple Silicon requirement, user-specific paths, QEMU boot claim, compatibility claims, production-readiness claim. |
| `v0.4.4` | Fix Limine ISO/kernel load semantics | Correct Limine kernel path resource semantics, record configured/normalized path metadata, and validate ISO path visibility before deeper boot debugging. | QEMU boot claim, kernel entry claim without `KOZO_EARLY_0_ENTRY`, serial initialization work, compatibility claims, runtime subsystem expansion. |
| `v0.4.5` | Limine ELF Load Layout | Classify Limine's lower-half PHDR rejection, record load-layout metadata, and keep the next boot fix focused on kernel ELF virtual-address layout. | QEMU boot claim, kernel entry claim without `KOZO_EARLY_0_ENTRY`, risky higher-half migration without explicit evidence, compatibility claims, runtime subsystem expansion. |
| `v0.4.6` | Codebase Structural Audit | Audit stale/dead/brittle/god-file risks and higher-half transition hazards before changing linker/runtime layout. | Runtime behavior changes, ABI changes, syscall changes, linker layout changes, QEMU boot claims, broad refactors. |
| `v0.4.7` | Higher-Half Linker and Entry Transition | Move the kernel ELF to higher-half virtual PT_LOAD addresses, preserve low physical load addresses, and wait for CI QEMU evidence to classify the next blocker or marker state. | Syscall behavior changes, serial fixes before kernel entry evidence, compatibility claims, runtime subsystem expansion, QEMU boot claims without `KOZO_BOOT_SMOKE_OK`. |
| `v0.4.8` | Kernel Entry Handoff | Emit `KOZO_EARLY_0_ENTRY` from `_start` before stack setup or Odin code and require QEMU metadata to distinguish entry handoff from later serial blockers. | QEMU boot claim without `KOZO_BOOT_SMOKE_OK`, kernel entry claim without captured `KOZO_EARLY_0_ENTRY`, ABI or syscall behavior changes, broad runtime subsystem expansion. |
| `v0.4.9` | Early Serial Initialization | Emit `KOZO_EARLY_1_SERIAL_INIT_START` and `KOZO_EARLY_2_SERIAL_INIT_OK` from `_start` before stack setup or Odin code and require QEMU metadata to distinguish serial initialization from final smoke marker emission. | QEMU boot claim without `KOZO_BOOT_SMOKE_OK`, serial initialization claim without captured `KOZO_EARLY_2_SERIAL_INIT_OK`, ABI or syscall behavior changes, broad runtime subsystem expansion. |
| `v0.4.95` | Code Quality and Style Audit | Audit stale/dead/brittle/god-file risks and coding-style drift before the final boot smoke marker phase. | Runtime behavior changes, ABI changes, syscall changes, linker layout changes, QEMU marker semantic changes, broad refactors. |
| `v0.4.96` | Smoke Evidence Observability | Add a deterministic QEMU smoke summary artifact so CI and release reviewers can classify the current smoke state without manually correlating multiple artifacts. | Runtime behavior changes, ABI changes, syscall changes, linker layout changes, QEMU marker semantic changes, QEMU boot or compatibility claims. |
| `v0.5.0` | Boot Smoke Marker Emission | Emit `KOZO_BOOT_SMOKE_OK` through the proven assembly serial path after early serial initialization and require ordered-marker QEMU smoke validation. | QEMU boot claim without the full ordered marker sequence, ABI or syscall behavior changes, broad runtime subsystem expansion. |
| `v0.5.1` | Governance Planning Alignment | Align governance, planning, audit, release, and evidence docs with the local v0.5.0 proof state and the failed pushed v0.5.0 CI run. | Runtime behavior changes, ABI changes, syscall changes, linker changes, QEMU smoke behavior changes, QEMU serial smoke promotion without CI proof. |
| `v0.5.2` | CI Evidence Access Hardening | Print verification, QEMU smoke, serial/stderr, and boot blocker summaries into full CI logs so first-level triage does not depend on authenticated artifact downloads or local `gh`. | Runtime behavior changes, ABI/syscall changes, linker changes, QEMU marker semantic changes, QEMU boot or compatibility claims. |
| `v0.5.3` | CI Smoke Evidence Triage | Inspect the failed v0.5.0/v0.5.2 CI evidence, classify the verification failure, and repair only the exact evidence-backed blocker. | ABI/syscall maturity work before CI smoke evidence is classified. |
| `v0.5.4` | QEMU Serial Smoke Evidence Promotion | Promote the CI-proven QEMU serial smoke evidence and realign stale validators, docs, audit state, and blocker wording. | Runtime behavior changes, ABI/syscall changes, linker changes, marker semantic changes, compatibility claims, production-readiness claims. |
| `v0.6.0` | Runtime Logic Baseline | Add a governed runtime halt contract so the post-smoke assembly path enters deterministic terminal behavior after `KOZO_BOOT_SMOKE_OK`. | ABI/syscall changes, hardware trap claims, interrupt handling claims, scheduler behavior, userspace execution, compatibility claims, production-readiness claims. |
| `v0.6.4` | Code Structure Remediation | Remove proven-unused zero-byte generator stubs and document oversized, stale, shim, and deferred cleanup decisions before runtime progression work. | Runtime behavior changes, ABI/syscall changes, linker changes, marker semantic changes, broad refactors, compatibility claims, production-readiness claims. |
| `v0.6.5` | Runtime Evidence Taxonomy Centralization | Add a governed runtime evidence taxonomy contract and migrate smoke/blocker validators to consume marker order, outcomes, and blocker allowlists from it. | Runtime behavior changes, marker string/order changes, QEMU pass-criteria changes, ABI/syscall changes, broad validator rewrites, compatibility claims, production-readiness claims. |
| `v0.6.6` | Runtime Progression Stages Contract | Add a governed runtime progression stages contract so future progression stages share one canonical ordering, evidence, and transition model. | Runtime behavior changes, halt replacement, stack/memory/runtime initialization, userspace, scheduler, VFS, compatibility claims, production-readiness claims. |
| `v0.6.7` | Stack Initialization Evidence Planning | Add a governed stack initialization evidence contract and reserve `KOZO_STACK_INIT_OK` as future evidence without implementing stack setup. | Runtime behavior changes, boot assembly changes, halt replacement, stack setup, memory initialization, Odin runtime execution, compatibility claims, production-readiness claims. |
| `v0.7.0` | Stack Initialization Evidence | Establish the controlled static boot stack, emit `KOZO_STACK_INIT_OK`, and validate the stack evidence boundary. | Memory initialization, Odin runtime execution, halt replacement, userspace, scheduler, VFS, compatibility claims, production-readiness claims. |
| `v0.7.1` | Memory Initialization Evidence Planning | Add a governed memory initialization evidence contract and reserve `KOZO_MEMORY_INIT_OK` as future evidence without implementing memory setup. | Runtime behavior changes, boot assembly changes, halt replacement, memory setup, allocator behavior, paging behavior, Odin runtime execution, compatibility claims, production-readiness claims. |
| `v0.7.2` | Runtime Progression Model Reconciliation | Make the canonical stage graph acyclic, monotonic, and single-owner while aligning contracts, validation, planning, and task state. | Runtime behavior changes, marker changes, halt replacement, memory implementation, validator weakening, compatibility claims, production-readiness claims. |
| `v0.7.3` | Memory Evidence Contract Hardening | Make the planned memory evidence boundary mechanically implementable before scheduling runtime changes. | Memory implementation, `KOZO_MEMORY_INIT_OK` emission, paging, allocator behavior, halt replacement, compatibility claims, production-readiness claims. |
| `v0.7.4` | Memory Initialization Evidence | Implement only the contract-defined static region initialization and survival probe, emit governed evidence, and retain the halt path. | Physical memory discovery, paging, virtual memory management, allocator or heap behavior, Odin runtime initialization, halt replacement, compatibility claims, production-readiness claims. |
| `v0.7.45` | Runtime Progression Entry and Minimal Runtime Initialization | Call a bounded Odin entry with a fixed validated context, prove one static-state operation, require exact return status, and retain the halt path. | Complete Odin runtime readiness, dynamic initialization, paging, allocation, interrupts, scheduling, userspace, hardware syscall boundaries, compatibility claims, production-readiness claims. |
| `v0.7.5` | Controlled Runtime Loop | Execute exactly three Odin-owned iterations with static volatile state, deterministic accumulation, fixed evidence markers, exact status handling, and the unchanged halt continuation. | Scheduler semantics, interrupts, concurrency, unbounded execution, allocation, userspace, process/VFS/fd behavior, compatibility claims, production-readiness claims. |
| `v0.8.0` | First Governed Runtime Capability | Validate and dispatch one internal versioned runtime status request, validate a deterministic response, and preserve governed return-to-halt behavior. | Userspace access, privilege separation, hardware syscall entry, scheduler/process/VFS/fd behavior, allocation, compatibility claims, production-readiness claims. |
| `v0.8.1` | CPU Extended-State Initialization | Detect and configure the boot CPU x87/SSE state, validate x87/MXCSR control state, and prove one bounded SIMD result before Odin. | AVX/XSAVE/XCR0, per-task extended-state ownership, context switching, exception recovery, complete CPU initialization, compatibility, production readiness. |
| `v0.8.2` | Governed Runtime State Transition Capability | Validate and dispatch one fixed internal READY/0-to-ACTIVE/1 state mutation, read it back through volatile accesses, validate its response, and preserve return-to-halt. | Arbitrary memory writes, general state machines, dynamic capability registration, concurrency, userspace access, authorization, persistence, compatibility, production readiness. |
| `v0.8.3` | Fixed User-Mapping Foundation | Own one fixed four-level hierarchy with supervisor-only kernel leaves and three W^X user pages, then verify CR3 activation and survival. | Ring 3, process isolation, general VM, dynamic mappings, allocators, page-fault recovery, compatibility, production readiness. |
| `v0.8.4` | Bounded Privilege-Transition Probe | Execute one fixed Ring 0 to Ring 3 probe and one governed return using the accepted fixed mappings. | General userspace, process model, scheduler, general syscall ABI, isolation, compatibility, production readiness. |
| `v0.8.5` | Fixed User Request Boundary | Execute one exact Ring3 request and Ring0 response transaction through the accepted fixed interrupt boundary. | Arbitrary pointers or lengths, generic copy API, public syscall ABI, persistent userspace, process isolation, compatibility, production readiness. |
| `v0.8.6` | Bounded User Response Consumption | Return one validated fixed response to a fixed Ring3 continuation for bounded consumption before final Ring0 convergence. | General request dispatch, repeated sessions, arbitrary user buffers, process model, isolation, compatibility, production readiness. |
| `v0.8.7` | Runtime-Ordered User Status Service | Collect one post-loop snapshot and expose it through the existing fixed transaction while preserving internal capability ID 1. | General dispatch, variable fields or messages, public syscall ABI, persistent userspace, process model, compatibility, production readiness. |
| `v0.8.8` | Core Service MIT License Metadata | Add exact MIT package metadata, pass cargo-deny, and inspect package contents without changing runtime behavior. | Publication, packaging frameworks, dependency changes, runtime changes, complete release readiness. |
| `v0.8.9` | Documentation and Adoption Readiness | Add a user-first wiki, maintainer path, engineering overview, terminology guide, documentation audit, and focused comment cleanup. | Runtime features, documentation frameworks, publication, compatibility, complete release readiness. |
| `v1.0.0-rc.1` | Published release candidate | Freeze scope and gates, publish the accepted immutable prerelease, and verify the distributed artifacts and user path. | In-place tag, note, or asset changes; new feature scope after RC. |
| `v1.0.0` | Final kernel-foundation release | Publish the accepted governed kernel foundation with final versioning, evidence, and immutable assets. | Any unimplemented compatibility or runtime subsystem claim; any in-place mutation of the final tag or assets. |
| `v1.0.1` | Odin object-output compatibility patch | Normalize supported exact, `.o`, and legacy `.obj` object outputs at one fail-closed compiler boundary and publish the verified correction. | Runtime capability additions, ABI changes, platform-specific exceptions, or in-place mutation of v1.0.0. |
| `post-Phase-0 definition` | Fixed User Execution Context | Define one supervisor-only identity and lifecycle that binds the accepted fixed user execution path without implementing it. | Runtime implementation, repeated sessions, processes, scheduling, dynamic memory, ABI expansion, version authorization, or release. |
| `post-Phase-0 prerequisites` | Fixed User Execution Context Governance | Adopt exact ownership, lifecycle, result, cleanup, transition-budget, progression, and evidence authority before runtime implementation. | Runtime implementation, marker/check-count changes, repeated sessions, public ABI, version authorization, or release. |
| `post-Phase-0 implementation` | Fixed User Execution Context Implementation | Add one static supervisor-owned lifecycle around the accepted fixed transaction and prove cleanup without changing markers or ABI. | Repeated sessions, processes, scheduling, dynamic allocation, marker/check-count changes, version authorization, or release. |
| `post-context implementation` | Bounded Repeated User Session | Reuse the one static context for exactly two independent fixed sessions after verified reset. | Third or arbitrary sessions, processes, scheduling, dynamic allocation, ABI expansion, version authorization, or release. |
| `v1.1.0` | Fixed-context and bounded-session feature release | Publish exact hosted-accepted commit `a5226635be46c687299028b5244f808da67c0984` with 1,284 tests, 67 governed checks, Linux QEMU through 52 markers, two sessions, four `int 0x81` returns, all pinned host build gates, cross-host release-input identity, six assets, pre-upload/download SHA-256 identity, and downloaded-ISO proof. | No process, scheduler, allocator, public ABI expansion, mapping changes, interrupt-vector changes, third or arbitrary session, Windows/macOS runtime claim, or mutation of prior releases. |

---

# 14. Release Gates

Required gates for any release after v1.1.0:

* `release/version.txt` and all current release metadata agree.
* `scripts/verify.sh` passes with the governed check count and expected runtime sequence.
* Unit discovery passes; v1.1.0 established a 1,284-test release baseline.
* Odin check/build, Cargo check, cargo-deny, and cargo-audit pass.
* The fixed execution context and exactly two repeated sessions validate, including four total `int 0x81` returns and fail-closed rejection of a third session or fifth return.
* Linux QEMU passes through 52 ordered marker occurrences ending at `KOZO_RUNTIME_RETURN_OK`, unless a separately governed release changes the evidence contract.
* The pinned Linux, Windows, and macOS build matrix passes; runtime claims remain evidence-tiered.
* Cross-host release-input identity passes using committed Git blobs as authority.
* Generated reports and `artifacts/latest_verify.json` are current, valid, and passing.
* The governed release bundle contains the expected asset inventory, licenses, metadata, and checksum manifest.
* Pre-upload and fresh GitHub-download SHA-256 values match for every asset.
* The GitHub-downloaded ISO reproduces the accepted runtime result on the governed runtime host.
* Prior release tags, notes, classifications, and assets remain immutable.
* Compatibility and product claims remain limited to demonstrated behavior.

---

# 15. Evidence Requirements

Release evidence must include:

* exact release version, annotated tag object, and target commit
* hosted CI, lint, and portability run identities
* full verification artifact and logs
* generated syscall, ABI, ELF, and governance reports required by the release
* checked-in contracts, schemas, changelog, phase map, and roadmap
* Fixed User Execution Context lifecycle, storage, cleanup, and result evidence where applicable
* Bounded Repeated User Session evidence for exactly two sessions, four returns, reset validation, and marker occurrence counts where applicable
* Linux runtime evidence and separate Windows/macOS build evidence
* cross-host release-input identity evidence
* release bundle inventory, license files, metadata, and `SHA256SUMS`
* pre-upload artifact digests
* fresh GitHub-download asset digests and checksum validation
* downloaded-ISO QEMU evidence
* known limits and explicit non-goals

Detailed evidence ownership is defined in `docs/RELEASE_EVIDENCE.md`.

---

# 16. Explicit Deferred Work

Deferred until separately scoped and proven:

* third, arbitrary, persistent, or concurrent user sessions
* process lifecycle and scheduling
* timer, preemption, and general context switching
* physical-frame allocation, heap allocation, and dynamic virtual memory
* executable loading and general userspace
* public syscall or interrupt-interface expansion
* filesystem, VFS, and file descriptor behavior
* device drivers and networking
* Windows and macOS runtime validation
* Linux compatibility and POSIX completeness
* stable public ABI guarantees
* evidence-backed minimum hardware profiles
* production readiness beyond scoped release evidence
