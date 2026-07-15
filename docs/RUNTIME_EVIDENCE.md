# KOZO Runtime Evidence

Version: 1
Status: Authoritative
Scope: Runtime smoke evidence for the current governed KOZO runtime boundary

---

# 1. Purpose

This document defines KOZO's current runtime smoke evidence path.

The current evidence set includes a bounded runtime-adjacent object and symbol smoke check plus CI-proven QEMU serial smoke evidence. The runtime-adjacent check proves that the freestanding x86_64 kernel objects and assembly bridge objects can be built together with the current entry, dispatcher, syscall bridge, and serial marker surfaces present in binary evidence. The QEMU serial smoke check proves only that QEMU launched the KOZO ISO, Limine loaded the KOZO kernel ELF, serial output was captured, and the expected smoke marker sequence was observed.

The v0.3.0 boot baseline attempted to move beyond runtime-adjacent evidence. It is currently blocked by `missing_boot_protocol_and_image_packaging`.

v0.3.1 selected Limine as the planned x86_64 boot protocol, but QEMU smoke is planned and not yet proven.

v0.3.2 added a boot image skeleton, but QEMU smoke is still planned and not yet proven.

v0.3.3 added a bounded QEMU smoke command, but it currently fails closed because no bootable Limine ISO or disk image is produced.

v0.3.4 added boot image package metadata at `artifacts/runtime/boot_image/package_metadata.json`, recording the packaging blocker.

v0.3.5 added `docs/BOOT_TOOLING.md` to define the Limine and xorriso acquisition path.

v0.3.6 added the ISO generation command path, but local ISO generation is blocked by missing Limine artifacts and xorriso tooling.

v0.3.7 added full-CI installation of pinned Limine source tooling and xorriso so CI can attempt ISO generation and upload boot image artifacts.

v0.3.8 added QEMU serial smoke metadata, `qemu_smoke_evidence`, and the kernel-emitted `KOZO_BOOT_SMOKE_OK` marker. Local QEMU smoke remains blocked by missing ISO generation tooling unless the ISO is supplied.

v0.3.9 adds QEMU stderr log evidence at `artifacts/runtime/qemu_smoke.stderr.log` and records `qemu_timeout` as an exact blocked QEMU smoke outcome when the marker is absent after a bounded QEMU run.

v0.4.0 adds Limine serial/verbose diagnostics and early KOZO marker taxonomy so QEMU smoke can narrow timeout into `limine_not_reached`, `kernel_not_loaded`, `kernel_entry_not_reached`, `serial_not_initialized`, `marker_not_emitted`, or fallback `qemu_timeout`.

v0.4.1 fixes the Limine kernel executable path and classifies Limine executable-open failures as `kernel_not_loaded`.

v0.4.2 adds `artifacts/runtime/kernel_elf_report.json` and `kernel_loadability` validation so the staged kernel ELF can be inspected for architecture, entry point, `_start` alignment, program headers, and PT_LOAD segments before interpreting Limine load failures.

v0.4.4 updates Limine kernel load semantics to use `boot():/boot/kozo/kozo-kernel.elf` and adds ISO path visibility metadata for the configured kernel path.

v0.4.5 adds Limine ELF load-layout classification. The latest inspected CI QEMU evidence reached Limine, opened the configured kernel path, and failed with `PANIC: elf: Lower half PHDRs are not allowed`, so the evidence-backed blocker is `limine_lower_half_phdr`.

v0.4.7 adds the higher-half linker transition. Local kernel ELF evidence now records `_start` at `0xffffffff80200000`, higher-half PT_LOAD virtual addresses, low physical load addresses, and no lower-half PT_LOAD blocker. CI QEMU evidence must still prove whether Limine advances beyond the previous `limine_lower_half_phdr` blocker.

v0.4.8 adds the first entry marker emission directly to `_start`. The marker is written through assembly COM1 output before stack setup and before Odin code so QEMU smoke evidence can distinguish entry handoff from later serial initialization.

v0.4.9 adds the serial initialization start and OK markers directly to `_start`. The markers are written through assembly COM1 output before stack setup and before Odin code so QEMU smoke evidence can distinguish serial initialization from final smoke marker emission.

v0.5.0 adds the final `KOZO_BOOT_SMOKE_OK` marker directly to `_start` after assembly-level serial initialization. Passing QEMU smoke evidence requires the full ordered marker sequence in captured serial output.

v0.5.1 validates the pushed v0.5.0 outcome before further runtime work. Local verification passes, but the latest pushed CI run for commit `14fb015` failed in `scripts/verify.sh`. QEMU serial smoke evidence is not promoted until that CI failure is inspected and a passing CI run validates the full ordered marker sequence.

v0.5.2 adds CI evidence access hardening. Full CI prints a concise verification, QEMU smoke, serial/stderr, and boot blocker summary into the Actions log so first-level triage does not require authenticated artifact download or local `gh`.

v0.5.4 promotes QEMU serial smoke evidence after CI run `27894312430` captured the full ordered marker sequence and QEMU smoke metadata reported `outcome: pass` with `blocker_category: none`.

v0.6.0 adds the governed post-smoke runtime halt baseline. The runtime halt contract validates that the assembly path emits `KOZO_BOOT_SMOKE_OK` before entering a deterministic terminal halt loop and forbids structural fallthrough after the smoke marker.

v0.6.5 adds `contracts/runtime_evidence_taxonomy.v0.json` as the governed source for QEMU serial smoke marker names, marker order, smoke outcome names, blocker categories, pass condition, blocked condition, and taxonomy-level non-goals. The generated smoke metadata remains evidence, not taxonomy authority.

v0.6.6 adds `contracts/runtime_progression_stages.v0.json` as the governed source for future runtime progression stage order, prerequisites, evidence, contracts, validators, allowed next stages, and forbidden shortcuts. It is planning governance only and does not implement stack initialization, memory initialization, runtime progression, userspace execution, compatibility, or production behavior.

v0.7.0 implements the governed stack initialization evidence path. `_start` sets `rsp` to the static boot stack, performs a minimal stack-use probe, emits `KOZO_STACK_INIT_OK`, and then enters the governed halt loop. This proves controlled stack establishment and stack marker emission only.

v0.7.3 hardens `contracts/memory_initialization_evidence_contract.v0.json` into an implementation-ready boundary. v0.7.4 implements its static region, explicit zero fill, bounded sentinel write/read/compare/restore probe, `KOZO_MEMORY_INIT_OK` emission, and unchanged terminal halt path. The generated kernel ELF report records the region symbol addresses, computed size, and required-alignment result so validation does not depend on source structure alone. This does not prove physical memory discovery, paging, virtual memory management, allocation, Odin runtime execution, progression entry, userspace, compatibility, or production readiness.

v0.7.45 implements a bounded assembly-to-Odin call after memory evidence. Assembly emits `KOZO_RUNTIME_PROGRESS_ENTRY`, calls the exported Odin entry with a fixed versioned context, requires exact status zero, emits `KOZO_RUNTIME_RETURN_OK`, and enters the terminal halt path. Odin validates the context, performs a static-state write/read/restore probe, and causes `KOZO_RUNTIME_INIT_OK` to be emitted through a fixed assembly bridge. These stages remain implemented pending CI until QEMU captures the ordered sequence.

Current local boot blocker: `missing_iso_generation_tooling` when Limine and xorriso tooling are unavailable outside CI.

Current release blocker for QEMU serial smoke evidence: none.

When CI produces `artifacts/runtime/boot_image/kozo.iso` but QEMU serial evidence has not yet been captured, the generated blocker report may narrow to `missing_qemu_serial_evidence` for that run.

When CI runs QEMU against that ISO but does not capture `KOZO_BOOT_SMOKE_OK`, the generated blocker report may narrow further to `qemu_timeout`.

The latest inspected pre-v0.4.5 CI artifact reached Limine and opened the configured kernel executable path, but Limine rejected the kernel ELF lower-half program headers, so the evidence-backed diagnostic blocker is `limine_lower_half_phdr`.

The v0.4.7 kernel ELF report records PT_LOAD virtual addresses, physical load addresses, virtual base, physical load base, higher-half segment summary, entry address class, and the load-layout blocker. This does not prove QEMU boot, Limine ELF loading, kernel entry, or serial initialization.

The v0.4.8 QEMU smoke metadata records Limine entry-point evidence, expected entry symbol, expected entry marker, entry-marker observation, and entry fault signal. These fields do not prove kernel entry unless `KOZO_EARLY_0_ENTRY` is present in captured QEMU serial output.

The latest inspected v0.4.8 CI artifact captured `KOZO_EARLY_0_ENTRY`, so kernel entry handoff is proven for that artifact. It did not capture `KOZO_EARLY_2_SERIAL_INIT_OK`, so serial initialization remains unproven until that marker appears in captured QEMU serial output.

The expected v0.7.45 QEMU serial sequence is `KOZO_EARLY_0_ENTRY`, `KOZO_EARLY_1_SERIAL_INIT_START`, `KOZO_EARLY_2_SERIAL_INIT_OK`, `KOZO_BOOT_SMOKE_OK`, `KOZO_STACK_INIT_OK`, `KOZO_MEMORY_INIT_OK`, `KOZO_RUNTIME_PROGRESS_ENTRY`, `KOZO_RUNTIME_INIT_OK`, and `KOZO_RUNTIME_RETURN_OK`.

In v0.7.1 and v0.7.3, `KOZO_MEMORY_INIT_OK` was reserved planning vocabulary and was not runtime evidence. v0.7.4 replaces that planning state: runtime assembly now emits the marker only after completing the contract-defined initialization and probe, and the governed QEMU pass sequence includes it as the final expected marker.

The implemented memory proof remains bounded to one static 4096-byte `.bss` region. Runtime code zeroes the entire region, writes the contract sentinel at the declared offset, reads and compares it exactly, restores the zero fill value, and only then emits `KOZO_MEMORY_INIT_OK` before entering the existing halt path. This evidence does not prove physical memory discovery, paging, virtual memory management, allocator or heap behavior, general memory safety, or Odin runtime initialization.

The v0.4.4 ISO path metadata may prove that the configured Limine path is present in packaged ISO contents. It does not prove Limine loaded the ELF, entered the kernel, initialized serial output, or reached `KOZO_BOOT_SMOKE_OK`.

---

# 2. Authority

This document owns runtime smoke evidence requirements.

It is subordinate to:

* `docs/GOVERNANCE.md`
* `docs/INVARIANTS.md`
* `docs/ARCHITECTURE.md`
* `docs/CONTRACTS.md`
* `docs/COMPATIBILITY.md`
* `docs/VALIDATION.md`

It does not define runtime behavior, ABI truth, syscall truth, compatibility claims, or production-readiness claims.

---

# 3. Non-Goals

This evidence does not prove Linux compatibility.

This evidence does not prove POSIX compatibility.

This evidence does not prove general userspace execution.

This evidence does not prove a process model.

This evidence does not prove VFS behavior.

This evidence does not prove scheduler maturity.

This evidence does not prove ELF loading.

This evidence does not prove file descriptor behavior.

This evidence does not prove production readiness.

This evidence does not prove QEMU boot execution, hardware syscall execution, interrupt handling, or privilege transition behavior.

The current boot blocker report also does not prove QEMU boot.

The boot protocol decision also does not prove QEMU boot.

The boot image skeleton also does not prove QEMU boot.

---

# 4. Runtime Evidence Target

The current target is:

```text
runtime-adjacent-object-symbol-smoke
```

The smoke path builds freestanding x86_64 Odin kernel objects, assembles the current x86_64 boot and syscall bridge objects, records `nm` and `strings` evidence, and verifies required entry, dispatcher, bridge, and serial marker surfaces.

The QEMU serial smoke target is proven in CI. v0.7.4 extends its expected sequence through controlled stack and static-region evidence. It remains a narrow target and does not replace separate evidence for Odin runtime execution, general stack readiness, general memory management, syscall dispatch, hardware trap execution, userspace execution, or subsystem behavior.

The marker order and blocker vocabulary for QEMU serial smoke are owned by `contracts/runtime_evidence_taxonomy.v0.json` and enforced by `runtime_evidence_taxonomy`, `qemu_smoke_evidence`, and `boot_blocker_report`.

Stack initialization evidence is governed by `contracts/stack_initialization_evidence_contract.v0.json` and validated by `stack_initialization_evidence`. It proves only that the assembly boot path selects the controlled static boot stack, performs a bounded stack-use probe, and emits `KOZO_STACK_INIT_OK`.

---

# 5. Required Tools

Required tools:

* `odin`
* `nasm`
* `nm`
* `strings`
* `grep`
* `find`

No network access is required.

---

# 6. Evidence Command

Generate runtime smoke evidence with:

```bash
scripts/runtime_smoke.sh
```

Full verification runs this command through `scripts/verify.sh`.

Full CI runs `scripts/verify.sh`, so runtime smoke evidence is required in full CI through the full-verification path.

The lint workflow does not run runtime smoke evidence unless it is changed to run full verification.

---

# 7. Artifact Path

The runtime smoke artifact is:

```text
artifacts/runtime/runtime_smoke.log
```

The runtime smoke metadata artifact is:

```text
artifacts/runtime/runtime_smoke.metadata.json
```

The boot blocker artifact is:

```text
artifacts/runtime/boot_blocker_report.json
```

The QEMU smoke log path is:

```text
artifacts/runtime/qemu_smoke.log
```

The QEMU smoke metadata path is:

```text
artifacts/runtime/qemu_smoke.metadata.json
```

The QEMU smoke summary path is:

```text
artifacts/runtime/qemu_smoke.summary.txt
```

The boot image package metadata path is:

```text
artifacts/runtime/boot_image/package_metadata.json
```

The expected boot image path is:

```text
artifacts/runtime/boot_image/kozo.iso
```

The ISO contents report is:

```text
artifacts/runtime/boot_image/iso_contents.txt
```

The boot tooling policy path is:

```text
docs/BOOT_TOOLING.md
```

The QEMU smoke log is passing current runtime evidence only when `qemu_smoke_evidence` validates metadata with outcome `pass` and finds the full ordered marker sequence ending in `KOZO_RUNTIME_RETURN_OK` in the serial log. Blocked metadata remains blocker evidence only.

The QEMU smoke summary is a reviewer convenience artifact. It is generated from the QEMU smoke metadata, serial log, stderr log, and boot blocker report. It is not authoritative and must not replace metadata or log validation.

The CI evidence summary printed by `scripts/ci_evidence_summary.sh` is also reviewer convenience output. It reads local generated artifacts and log tails, does not require network access, and must not redefine runtime evidence or QEMU smoke pass criteria.

The runtime halt contract is:

```text
contracts/runtime_halt_contract.v0.json
```

The runtime halt contract validator is:

```text
runtime_halt_contract
```

It validates source structure for the post-smoke terminal path. It does not prove hardware halt instruction execution, interrupt handling, scheduler behavior, userspace execution, process model behavior, VFS behavior, file descriptor behavior, or production readiness.

The runtime progression contract is:

```text
contracts/runtime_progression_contract.v0.json
```

The runtime progression contract validator is:

```text
runtime_progression_contract
```

It validates halt-preservation governance for a future halt-to-runtime transition. It requires stack initialization evidence, memory initialization evidence, and progression path evidence before the halt loop can be removed, replaced, bypassed, or jumped around. It does not define stage order or prove Odin runtime execution, userspace execution, interrupt handling, scheduler behavior, VFS behavior, process model behavior, syscall dispatch during boot, memory manager behavior, hardware trap handling, device driver behavior, compatibility, or production readiness.

The runtime progression entry contract is:

```text
contracts/runtime_progression_entry_contract.v0.json
```

The runtime progression entry validator is:

```text
runtime_progression_entry_contract
```

It governs the implemented internal assembly-to-Odin boundary. `KOZO_RUNTIME_PROGRESS_ENTRY` is emitted by assembly immediately before the call, `KOZO_RUNTIME_INIT_OK` depends on executed Odin code invoking a fixed bridge after its bounded volatile state probe, and `KOZO_RUNTIME_RETURN_OK` is emitted by assembly only after exact status zero. Volatile accesses preserve the sentinel write, readback, zero restoration, and restored-value check in the linked kernel. Source and ELF validation do not promote the stages; QEMU serial evidence must capture the ordered markers. The halt loop remains authoritative after return.

The runtime progression stages contract is:

```text
contracts/runtime_progression_stages.v0.json
```

The runtime progression stages validator is:

```text
runtime_progression_stages
```

It owns the canonical planned progression sequence:

```text
BOOT_SMOKE
STACK_INITIALIZATION_EVIDENCE
MEMORY_INITIALIZATION_EVIDENCE
RUNTIME_PROGRESSION_ENTRY
RUNTIME_INITIALIZATION_EVIDENCE
CONTROLLED_RUNTIME_LOOP
FIRST_GOVERNED_RUNTIME_CAPABILITY
USERSPACE_PLANNING
```

This stage model is not runtime evidence. It is the sole authority for stage order and allowed transitions, requires each mandatory prerequisite to be an earlier proven stage before promotion, and assigns one proof-boundary owner to every transition. The current status is boot, stack, and memory evidence proven; progression entry and runtime initialization implemented pending CI; and later stages planned.

The selected boot protocol is documented in:

```text
docs/BOOT_PROTOCOL.md
docs/decisions/0001-boot-protocol.md
```

The boot image skeleton is documented in:

```text
docs/BOOT_IMAGE.md
```

The log is generated evidence. It must be reproduced by the smoke script before it is used in release review.

The metadata is deterministic generated evidence. It identifies the evidence type, source log, generator, validator, positive claims, and explicit non-goals.

Full CI should upload both runtime smoke artifacts when full verification runs.

Full CI should also upload the boot blocker report while v0.3.0 remains blocked.

Full CI should upload boot image package metadata and `artifacts/runtime/boot_image/kozo.iso` when ISO generation succeeds.

Full CI should upload QEMU smoke log, stderr log, metadata, and summary when `scripts/qemu_smoke.sh` runs.

Full CI should print the CI evidence summary after verification attempts with `if: always()` so a failed run still exposes the active blocker in the Actions log when artifact download is unavailable.

---

# 8. Packaging

Runtime evidence is generated under:

```text
artifacts/runtime/
```

The boot blocker report is generated under the same directory.

For release review, package or copy it under:

```text
artifacts/release/runtime/
  runtime_smoke.log
  runtime_smoke.metadata.json
```

`artifacts/runtime/runtime_smoke.log` is the live generated output.

`artifacts/release/runtime/runtime_smoke.log` is the release bundle copy.

Do not treat the release bundle copy as source truth. Regenerate the live artifact with `scripts/runtime_smoke.sh` when reviewing or refreshing evidence.

---

# 9. Review Instructions

Before release review:

* Run `scripts/runtime_smoke.sh`.
* Run `scripts/boot_blocker_report.sh` while v0.3.0 remains blocked.
* Run `scripts/qemu_smoke.sh` only when reviewing the current QEMU blocker directly; it is expected to fail closed until bootable image packaging exists.
* Confirm `artifacts/runtime/qemu_smoke.metadata.json` is valid JSON when QEMU smoke is in scope.
* Confirm `artifacts/runtime/qemu_smoke.summary.txt` exists when QEMU smoke is in scope.
* Confirm `qemu_smoke_evidence` passes when QEMU smoke metadata is generated.
* Confirm `artifacts/runtime/runtime_smoke.log` exists and is non-empty.
* Confirm `artifacts/runtime/runtime_smoke.metadata.json` is valid JSON.
* Confirm `artifacts/runtime/boot_blocker_report.json` is valid JSON while boot is blocked.
* Confirm metadata `evidence_type` is `runtime-adjacent-object-symbol-smoke`.
* Confirm metadata positive claims match the current smoke target.
* Confirm metadata non-goals still include QEMU boot, hardware trap execution, Linux compatibility, userspace execution, process model, VFS behavior, scheduler maturity, ELF loading, file descriptor behavior, and production readiness.
* Confirm `runtime_smoke_evidence` passes.
* Copy or archive the log and metadata into the release evidence bundle.
* Copy or archive the boot blocker report into the release evidence bundle while boot is blocked.

---

# 10. Retention Policy

The latest live runtime smoke log and metadata live under `artifacts/runtime/`.

Release bundle copies live under `artifacts/release/runtime/` when a release evidence bundle is assembled.

Transient object files created while generating evidence must be cleaned by `scripts/runtime_smoke.sh`.

Historical release evidence may be retained outside the live artifacts directory by release tooling or GitHub release assets.

---

# 11. Invalidating Changes

Runtime evidence is invalidated by:

* changes to `kernel/`
* changes to `kernel/arch/`
* changes to the ABI bindings used by the kernel
* changes to `scripts/runtime_smoke.sh`
* changes to `docs/RUNTIME_EVIDENCE.md`
* changes to `harness/validators_impl/runtime_smoke_evidence.py`
* changes to `scripts/boot_blocker_report.sh`
* changes to `scripts/qemu_smoke.sh`
* changes to `harness/validators_impl/boot_blocker_report.py`
* changes to `contracts/runtime_halt_contract.v0.json`
* changes to `harness/validators_impl/runtime_halt_contract.py`
* stale, missing, malformed, or failed runtime smoke artifacts
* stale, missing, malformed, or failed boot blocker artifacts while boot is blocked

When invalidated, regenerate evidence and rerun full verification.

---

# 12. Validator

The registered validator is:

```text
runtime_smoke_evidence
```

It checks:

* runtime smoke artifact exists
* runtime smoke metadata exists
* runtime smoke metadata is valid JSON
* runtime smoke metadata fields match the governed evidence target
* runtime smoke metadata declares required positive claims
* runtime smoke metadata declares required non-goals
* artifact is non-empty
* runtime metadata is structurally valid
* expected runtime-adjacent markers are present
* failure markers are absent
* release evidence policy references the artifact
* release evidence policy references the metadata
* diagnostics name the failed runtime evidence field

The runtime halt contract validator is:

```text
runtime_halt_contract
```

It checks:

* runtime halt contract exists
* runtime halt contract is valid JSON
* runtime halt contract matches its schema
* the declared final smoke marker is present in `kernel/arch/x86_64/boot.asm`
* the final smoke marker is emitted before the terminal halt loop
* the terminal halt loop contains the required `cli`, `hlt`, and loop-back instructions
* structural fallthrough after the loop is forbidden
* diagnostics name the failed contract field

---

# 13. What This Evidence Proves

This evidence proves:

* the freestanding x86_64 kernel object build path succeeds
* x86_64 boot and syscall assembly objects can be assembled
* runtime entry and dispatcher symbols are present in binary evidence
* syscall bridge symbols are present in binary evidence
* current serial heartbeat marker strings are present in binary evidence
* the generated runtime smoke artifact is available for release review
* the source-level post-smoke path is governed by a runtime halt contract

---

# 14. What This Evidence Does Not Prove

This evidence does not prove:

* QEMU boot
* hardware syscall or interrupt transition
* privilege transition
* Rust userspace execution in a kernel-managed process
* scheduler behavior
* memory isolation
* hardware halt instruction semantics
* interrupt handling
* Odin runtime execution
* stack setup
* memory initialization
* syscall dispatch during boot
* production readiness

Those surfaces require later phase work.

---

# 15. Known Limitations

The current runtime smoke path is not a boot smoke test.

It is a deterministic runtime-adjacent evidence step until the repository has enough boot packaging to run a bounded emulator smoke path honestly.
