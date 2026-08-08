# KOZO Roadmap

Version: 1
Status: Planning
Scope: Product direction and release goals for the path to a scoped KOZO v1.0.0

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

KOZO should become a small, contract-backed operating-system substrate where every claimed boundary is explicit, verified, and supported by reproducible release evidence.

The current repository is strong at governance and source-level proof. The roadmap focuses on adding runtime evidence and release discipline without broad compatibility claims.

---

# 4. Goals

* Define exact v1.0.0 scope.
* Maintain strict contract-backed development.
* Add runtime execution evidence.
* Keep compatibility claims narrow.
* Make release evidence reproducible.
* Keep generated reports current and non-authoritative.
* Preserve validator coverage depth.

---

# 5. Non-Goals

The roadmap does not add or imply:

* Linux compatibility
* POSIX completeness
* general userspace execution
* process model behavior
* VFS behavior
* scheduler maturity
* ELF loading
* file descriptor behavior
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

The latest local generated evidence may still report missing local Limine/xorriso tooling, but CI run `27894312430` proves the narrow QEMU serial smoke path.

---

# 8. Current Limitations

KOZO still does not prove:

* complete Odin runtime readiness or dynamic initialization
* general stack readiness beyond the controlled boot stack proof
* general memory management beyond the governed static region
* runtime progression beyond the bounded call and governed halt continuation
* general userspace planning and execution remain unproven beyond the fixed boot-time CPL3 probe
* AVX, XSAVE, extended-state context switching, and floating-point exception recovery remain unproven
* syscall dispatch during boot
* hardware halt instruction semantics
* interrupt handling
* hardware trap execution
* Linux compatibility
* POSIX compatibility
* userspace execution
* process model behavior
* VFS behavior
* scheduler maturity
* file descriptor behavior
* production readiness

---

# 9. Current Active Blocker

No active runtime blocker is recorded for the published v1.0.1
kernel-foundation scope.
Force pushes to `main` are blocked. No broader repository policy is required
by the final-release scope. The immutable `v1.0.0-rc.1` prerelease and
`v1.0.0` final release are published. The final hosted assets passed checksum,
metadata, and downloaded-ISO verification. No reproducible blocker was found
for the declared release scope.

Post-publication documentation on `main` now routes users, maintainers, and
engineers through separate paths while preserving the immutable release
records. This alignment changes no runtime or release artifact.

The v1.0.0 post-release issue triage reviewed all project-visible GitHub
issues, Actions runs after publication, repository issue records, the six
hosted assets, and the downloaded ISO. No user-filed report was present, but
hosted acceptance exposed `KOZO-TRIAGE-001`: current Odin emits `.o` for a
suffixless object output, while the accepted helper normalizes only the prior
path forms. Tagged-source and direct compiler reproductions classify the case
`BUILD_TOOLING`, `U2`, and `R3`. Current `main` implements the bounded
normalization correction and focused regression coverage. Local and hosted
governed verification pass, including the formerly failing release-bundle
stage. Patch preparation and release gates passed. v1.0.1 is published from
the exact hosted-accepted commit, and `KOZO-TRIAGE-001` is resolved.

The bounded v1.0.1 post-release observation is complete. It reviewed
all project-visible issues and post-publication Actions, revalidated the six
hosted assets, booted the downloaded ISO through all 41 markers, and observed
the accepted cross-host Odin output boundary against tagged source. No
qualifying defect was reproduced. v1.0.2 is not authorized, and the current
release remains v1.0.1.

v1.1.0 Phase 0 is now the active repository-development gate. It establishes
host portability as an evidence-backed invariant and requires pinned Linux,
Windows, and macOS build-contract results while keeping guest runtime evidence
separate. Hosted run `31270131685` passed Linux and macOS but exposed the
reproducible Windows evidence-normalization failure `KOZO-TRIAGE-002`. The
separate Linux runtime run `31270131715` remains green. Phase 0 is blocked,
and no v1.1.0 product capability work is authorized until the Windows boundary
is corrected and the full required matrix passes.

Future general-userspace releases must preserve a defined minimum usable
hardware profile. Additional CPU, memory, and storage should increase capacity
and performance without making core supported functionality depend on
high-end development hardware. KOZO does not yet define host or guest resource
minimums, and this tooling correction introduces none.

---

# 10. Near-Term Runtime Work

The next runtime work must preserve the narrow QEMU serial smoke claim boundary:

1. Keep CI evidence summaries and artifact uploads active.
2. Keep QEMU serial smoke evidence as marker-sequence evidence only.
3. Keep the v0.6.0 post-smoke terminal halt contract narrow and source-structural.
4. Use `contracts/runtime_progression_stages.v0.json` as the sole authority for stage order and allowed transitions.
5. Keep the v0.6.2 runtime progression contract as halt-preservation governance, not a second stage-order definition.
6. Treat v0.7.4 memory evidence as accepted by the CI validator gate, while preserving the manual-artifact-inspection limitation.
7. Preserve the accepted v0.7.45 progression/runtime-initialization evidence and the hosted-CI-proven v0.7.5 controlled loop.
8. Keep the terminal halt path authoritative after the bounded Odin call.
9. Keep physical memory discovery, general virtual memory management, allocators, heaps, dynamic Odin initialization, and userspace outside the current proof.
10. Preserve the hosted-accepted v0.8.1 CPU-state boundary before all Odin capability work.
11. Preserve the hosted-accepted v0.8.3 fixed-mapping boundary, both validators, effective U/S and W^X, and the unchanged runtime suffix.
12. Preserve the hosted-accepted v0.8.4 fixed `iretq` entry, CPL3 probe, `int 0x81` return, saved-frame validation, fixed continuation, and unchanged runtime suffix.
13. Preserve hosted-accepted v0.8.5 fixed request geometry, service behavior, and evidence.
14. Preserve hosted-accepted v0.8.6 response consumption, exact cleanup, and unchanged runtime suffix.
15. Preserve the hosted-accepted v0.8.7 complete 41-marker transaction and both status-service validators.
16. Preserve the accepted v0.8.8 package-license correction and v0.8.9 documentation path.
17. Preserve the accepted v1.0.0-rc.1 tag, hosted artifacts, checksums, runtime
    evidence, and immutable release record.
18. Preserve the published v1.0.0 version, documentation, bundle, hosted gate,
    immutable tag, and hosted asset evidence without in-place mutation.
19. Preserve the post-publication user, maintainer, and engineering entry paths
    without making the wiki authoritative over contracts or governance.
20. Preserve the accepted bounded v1.0.1 correction for `KOZO-TRIAGE-001` at
    one canonical object-build boundary with its focused failure coverage.
21. Preserve the immutable v1.0.1 tag, notes, six assets, checksums, and hosted
    ISO evidence; use a later patch version for any product correction.
22. Complete v1.1.0 Phase 0 by proving the governed build contract on pinned
    Linux, Windows, and macOS runners while retaining Linux as the required
    guest/runtime gate.
23. Keep v1.1.0 product capability work blocked until Phase 0 hosted evidence
    is accepted.
24. Keep arbitrary writes, concurrency, general userspace access, authorization, persistence, AVX/XSAVE context ownership, compatibility, and production readiness outside the current scope.

---

# 11. Post-Boot Roadmap

After CI QEMU serial smoke evidence is green, resume deferred maturity work:

* accept runtime progression entry evidence through CI
* accept bounded runtime initialization evidence through CI
* accept first governed runtime capability evidence through hosted CI
* split QEMU smoke script policy from metadata rendering
* split large validator coverage implementation layers
* define ABI/syscall expansion rules
* strengthen security boundary implementation evidence

---

# 12. Deferred Work

Deferred until separately scoped runtime or cleanup phases:

* ABI versioning expansion
* syscall expansion process changes
* new runtime subsystems
* hardware trap execution work
* broader boot lifecycle claims

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

---

# 14. Release Gates

Required gates:

* `scripts/verify.sh` passes.
* Unit discovery passes.
* Odin check/build passes.
* Pinned Rust cargo check passes.
* Generated reports are current.
* `artifacts/latest_verify.json` is valid and passing.
* Branch protection checks are green.
* Release checklist is complete.
* Required checks policy is satisfied.
* Release evidence bundle is present.
* Compatibility claims are scoped and accurate.

---

# 15. Evidence Requirements

Release evidence must include:

* verification artifact
* verification logs
* generated syscall surface report
* generated ABI surface report
* generated governance index
* checked-in contracts and schemas
* changelog and release notes
* phase map and roadmap
* CI status or run URLs when available
* known non-goals

Detailed evidence ownership is defined in `docs/RELEASE_EVIDENCE.md`.

---

# 16. Explicit Deferred Work

Deferred until separately scoped and proven:

* hardware syscall or interrupt transition path
* general userspace execution
* process lifecycle
* scheduler maturity
* VFS behavior
* file descriptor behavior
* ELF loading
* Linux compatibility
* POSIX completeness
* stable public ABI guarantee
* production readiness beyond scoped release evidence
