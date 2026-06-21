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
* governed future progression entry marker reservation through `contracts/runtime_progression_entry_contract.v0.json`

The latest local generated evidence may still report missing local Limine/xorriso tooling, but CI run `27894312430` proves the narrow QEMU serial smoke path.

---

# 8. Current Limitations

KOZO still does not prove:

* Odin runtime execution after the assembly marker sequence
* stack setup
* memory initialization
* runtime progression past the governed halt loop
* `KOZO_RUNTIME_PROGRESS_ENTRY` emission
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

Current QEMU serial smoke blocker: none.

Local generated evidence still reports `missing_iso_generation_tooling`, which is a local environment blocker and not the CI/Linux portability state.

---

# 10. Near-Term Runtime Work

The next runtime work must preserve the narrow QEMU serial smoke claim boundary:

1. Keep CI evidence summaries and artifact uploads active.
2. Keep QEMU serial smoke evidence as marker-sequence evidence only.
3. Keep the v0.6.0 post-smoke terminal halt contract narrow and source-structural.
4. Keep the v0.6.2 runtime progression contract as the gate for any future halt-to-runtime transition.
5. Keep the v0.6.3 runtime progression entry contract as a marker reservation, not runtime evidence.
6. Plan stack initialization evidence before implementing progression entry or replacing the halt loop.

---

# 11. Post-Boot Roadmap

After CI QEMU serial smoke evidence is green, resume deferred maturity work:

* add stack initialization evidence
* add runtime progression entry evidence
* add runtime initialization evidence
* add controlled runtime loop evidence
* centralize boot marker and blocker taxonomy
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
| `v0.6.0-rc.1` | Release candidate hardening | Freeze scope, freeze gates, produce evidence bundle, confirm branch protection, and dry-run release notes. | New feature scope after RC. |
| `v1.0.0` | Scoped release | Release only evidence-backed behavior with explicit non-goals. | Any unimplemented compatibility or runtime subsystem claim. |

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
