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

`ROADMAP.md` owns product direction and release goals.

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

# 7. Roadmap Table

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
| `v0.4.1` | ABI and syscall maturity | Define ABI versioning, syscall expansion process, generated binding compatibility expectations, and regression evidence. | New syscall expansion without governed process. |
| `v0.5.0-rc.1` | Release candidate hardening | Freeze scope, freeze gates, produce evidence bundle, confirm branch protection, and dry-run release notes. | New feature scope after RC. |
| `v1.0.0` | Scoped release | Release only evidence-backed behavior with explicit non-goals. | Any unimplemented compatibility or runtime subsystem claim. |

---

# 8. Release Gates

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

# 9. Evidence Requirements

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

# 10. Explicit Deferred Work

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
