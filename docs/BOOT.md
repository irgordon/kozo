# KOZO Boot Baseline

Version: 1
Status: Authoritative
Scope: Current bootability status and boot baseline requirements

---

# 1. Purpose

This document records the current KOZO boot baseline.

The v0.3.0 bootable runtime baseline attempted to determine whether the current kernel output can honestly be booted under QEMU.

The result is blocked.

v0.3.1 selected Limine as the initial x86_64 boot protocol.

v0.3.2 added the boot image skeleton.

v0.3.3 added a bounded QEMU smoke command and attempted the first QEMU serial path.

v0.3.4 added deterministic boot image packaging metadata and confirmed that Limine ISO tooling was still missing.

v0.3.5 added `docs/BOOT_TOOLING.md` to define the Limine and xorriso acquisition path.

v0.3.6 added the ISO generation command path to `scripts/build_boot_image.sh`, but local generation remains blocked because Limine artifacts and xorriso are unavailable.

v0.3.7 added CI installation of pinned Limine tooling and xorriso so full CI can attempt `scripts/build_boot_image.sh` and upload boot image artifacts when produced.

v0.3.8 added QEMU serial smoke metadata, the `qemu_smoke_evidence` validator, and a kernel-emitted `KOZO_BOOT_SMOKE_OK` marker for future QEMU serial validation.

v0.3.9 records the CI-observed QEMU timeout path as an exact blocker, adds QEMU stderr log evidence at `artifacts/runtime/qemu_smoke.stderr.log`, and keeps the no-QEMU-boot claim unless the serial log contains `KOZO_BOOT_SMOKE_OK`.

v0.4.0 adds documented Limine serial and verbose diagnostics, early KOZO serial markers, and a reachability taxonomy that distinguishes `limine_not_reached`, `kernel_not_loaded`, `kernel_entry_not_reached`, `serial_not_initialized`, `marker_not_emitted`, and fallback `qemu_timeout`.

v0.4.1 updates the Limine kernel path to match the staged ISO layout and classifies Limine executable-open failures as `kernel_not_loaded`.

v0.4.2 adds deterministic kernel ELF loadability evidence at `artifacts/runtime/kernel_elf_report.json`, validates the staged kernel ELF architecture, entry point, `_start` alignment, program headers, and PT_LOAD segments, and keeps the no-QEMU-boot claim until serial evidence proves execution.

v0.4.4 updates the Limine kernel path to use explicit `boot():` resource semantics and records ISO path visibility metadata so the configured path can be checked against the staged ISO contents.

v0.4.5 records the next CI-observed Limine blocker: the configured kernel path is opened, but Limine rejects the current lower-half ELF program-header layout with `limine_lower_half_phdr`.

v0.4.7 moves the kernel ELF virtual load layout to the higher half while preserving low physical load addresses in the linker script. Local ELF evidence no longer reports lower-half PT_LOAD segments, but CI QEMU evidence must still prove whether Limine advances beyond the previous `limine_lower_half_phdr` blocker.

v0.4.8 adds an assembly-level `KOZO_EARLY_0_ENTRY` emission path at `_start`, before stack setup and before calling Odin code. Kernel entry remains unclaimed until CI QEMU serial output captures that marker.

v0.4.9 adds assembly-level `KOZO_EARLY_1_SERIAL_INIT_START` and `KOZO_EARLY_2_SERIAL_INIT_OK` emission at `_start`, before stack setup and before calling Odin code. Serial initialization remains unclaimed until CI QEMU serial output captures `KOZO_EARLY_2_SERIAL_INIT_OK`.

v0.5.0 adds assembly-level `KOZO_BOOT_SMOKE_OK` emission at `_start`, immediately after `KOZO_EARLY_2_SERIAL_INIT_OK` and before stack setup or Odin code. Passing QEMU serial smoke evidence remains unclaimed unless QEMU smoke metadata validates passing evidence and captured serial output contains the full ordered marker sequence.

v0.5.4 promotes the CI-proven QEMU serial smoke evidence after CI run `27894312430` captured the full ordered marker sequence and QEMU smoke metadata reported `outcome: pass` with `blocker_category: none`.

v0.6.0 adds a governed runtime halt contract for the immediate post-smoke path. After `_start` emits `KOZO_BOOT_SMOKE_OK`, the assembly path enters a deterministic terminal `cli`/`hlt` loop instead of falling through into unrelated bytes or continuing into ungoverned runtime work.

v0.7.0 implements the governed stack initialization evidence path. `_start` loads `rsp` with the existing static `boot_stack_top`, performs a minimal push/pop stack-use probe, emits `KOZO_STACK_INIT_OK` through the proven assembly COM1 path, and then enters the existing halt loop.

v0.7.1 adds memory initialization evidence planning through `contracts/memory_initialization_evidence_contract.v0.json`. It reserves `KOZO_MEMORY_INIT_OK` as future evidence, but the marker is not emitted and memory initialization remains unimplemented.

v0.7.4 implements that governed boundary: `_start` explicitly zeroes a boot-owned 4096-byte, 4096-byte-aligned `.bss` region, performs the bounded 64-bit sentinel write/read/compare/restore probe, emits `KOZO_MEMORY_INIT_OK`, and then enters the existing halt loop.

v0.7.45 adds a bounded progression path after memory evidence. Assembly verifies call-site stack alignment, emits `KOZO_RUNTIME_PROGRESS_ENTRY`, calls the exported Odin `runtime_progression_entry` symbol with a fixed bootstrap context, requires exact status zero, emits `KOZO_RUNTIME_RETURN_OK`, and enters the existing halt loop. Odin validates the context, performs a static-state write/read/restore probe, and invokes a fixed assembly bridge that emits `KOZO_RUNTIME_INIT_OK` from the Odin execution path.

v0.7.5 extends that bounded Odin path with `controlled_runtime_loop`. After `KOZO_RUNTIME_INIT_OK`, Odin initializes static volatile loop state, executes exactly three iterations, accumulates `1 + 2 + 3`, validates the terminal count, accumulator, status, and reserved field, and causes fixed assembly bridges to emit `KOZO_RUNTIME_LOOP_ENTER`, three ordered iteration markers, and `KOZO_RUNTIME_LOOP_EXIT_OK`. Hosted CI run `30057826315` captured that ordered sequence and passed `controlled_runtime_loop_evidence`.

v0.8.0 executes one versioned internal `RUNTIME_STATUS_QUERY` after controlled-loop success. Odin validates a fixed 16-byte request and non-overlapping 64-byte response, clears the response, dispatches capability ID 1, reports only the accepted stage 0 through 5 baseline, validates every response field, and emits three fixed capability markers before exact status zero permits `KOZO_RUNTIME_RETURN_OK`. This remains same-address-space kernel execution and is accepted by hosted CI marker and validator evidence.

v0.8.3 constructs and validates a fixed KOZO-owned four-level page-table
hierarchy after SIMD evidence and before Odin entry. It preserves the loaded
kernel as supervisor-only, adds fixed user RX code and user RW-NX data/stack
mappings, verifies effective permissions through a software walk, activates
and reads back CR3, proves bounded kernel survival, and then continues through
the unchanged runtime and halt path. Hosted CI accepted this fixed-mapping
boundary with 59 checks and 0 failures.

v0.8.4 adds one fixed privilege-transition probe after mapping survival and
before Odin entry. Ring 0 validates fixed descriptor tables, fixed user and
return stacks, and the fixed `iretq` frame. The linked CPL3 stub validates its
privilege through CS, performs one bounded stack/token probe, and returns
through the DPL3 `int 0x81` gate. Ring 0 validates the saved frame and token,
restores one fixed continuation, and only then proceeds to Odin.

No active QEMU serial smoke blocker.

Local generated blocker: `missing_iso_generation_tooling` when Limine and xorriso tooling are unavailable outside CI.

If CI produces `artifacts/runtime/boot_image/kozo.iso`, the generated blocker report narrows to `missing_qemu_serial_evidence` for that run.

If `scripts/qemu_smoke.sh` can run against a generated ISO, it writes `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, `artifacts/runtime/qemu_smoke.metadata.json`, and `artifacts/runtime/qemu_smoke.summary.txt`. Passing current QEMU runtime evidence requires the serial log to contain the full ordered marker sequence ending in `KOZO_RUNTIME_RETURN_OK`; blocked metadata preserves the narrow evidence boundary. The summary is non-authoritative reviewer convenience derived from the metadata and logs.

---

# 2. Current Result

Boot feasibility result: QEMU serial smoke evidence proven.

Active release blocker: none for QEMU serial smoke evidence.

Local generated blocker category: `missing_iso_generation_tooling`.

No active QEMU serial smoke blocker.

CI packaged-image blocker category, when the ISO exists: `missing_qemu_serial_evidence`.

CI observed QEMU execution blocker category, when QEMU runs the ISO but no marker is captured before the bounded timeout: `qemu_timeout`.

Latest inspected post-v0.4.3 CI artifact diagnosis: `kernel_not_loaded`. QEMU launched the ISO, Limine was reached, and Limine failed to open the configured kernel executable path before any KOZO marker appeared.

Latest inspected pre-v0.4.5 CI artifact diagnosis: `limine_lower_half_phdr`. QEMU launched the ISO, Limine was reached, Limine opened the configured kernel path, and Limine rejected the kernel ELF with `PANIC: elf: Lower half PHDRs are not allowed` before any KOZO marker appeared.

Latest inspected v0.4.7 CI artifact diagnosis: `kernel_entry_not_reached`. QEMU launched the ISO, Limine loaded the higher-half ELF, and Limine reported `ELF entry point: 0xffffffff80200000`, but no KOZO marker appeared.

Latest inspected v0.4.8 CI artifact diagnosis: `serial_not_initialized`. QEMU launched the ISO, Limine loaded the higher-half ELF, and captured `KOZO_EARLY_0_ENTRY`, but did not capture `KOZO_EARLY_2_SERIAL_INIT_OK` or `KOZO_BOOT_SMOKE_OK`.

Current v0.4.7 kernel ELF diagnosis: structurally parseable by local ELF inspection, with `_start` and all PT_LOAD virtual addresses in the higher half. The staged kernel ELF is an x86_64 executable, `_start` matches the ELF entry point, PT_LOAD segments are present, and physical load addresses remain low through linker `AT(...)` placement. This does not prove Limine loaded or executed the kernel.

Current v0.4.8 entry handoff change: `_start` writes `KOZO_EARLY_0_ENTRY` directly to COM1 before stack setup, before `kernel_entry`, and before any Odin runtime dependency. This does not prove kernel entry until captured in QEMU serial output.

Current v0.4.9 serial initialization change: `_start` writes the entry marker, the serial initialization start marker, performs minimal COM1 initialization in assembly, and writes the serial initialization OK marker before stack setup. This does not prove QEMU boot until `KOZO_BOOT_SMOKE_OK` appears in captured QEMU serial output.

Current v0.5.0 marker emission change: `_start` writes `KOZO_BOOT_SMOKE_OK` through the same assembly COM1 path after `KOZO_EARLY_2_SERIAL_INIT_OK`. This supports only QEMU serial smoke evidence when QEMU smoke validation observes the full ordered marker sequence in captured serial output; it does not prove Odin runtime execution, stack setup, memory initialization, syscall dispatch, hardware trap execution, or broader boot lifecycle behavior.

Latest inspected v0.5.4 CI smoke status: CI run `27894312430` produced passing QEMU smoke metadata and captured `KOZO_EARLY_0_ENTRY`, `KOZO_EARLY_1_SERIAL_INIT_START`, `KOZO_EARLY_2_SERIAL_INIT_OK`, and `KOZO_BOOT_SMOKE_OK` in the serial log.

Current v0.6.0 runtime halt baseline: `contracts/runtime_halt_contract.v0.json` and `runtime_halt_contract` validate that `kernel/arch/x86_64/boot.asm` emits `KOZO_BOOT_SMOKE_OK` before entering a deterministic `cli`/`hlt` loop with no structural fallthrough.

Current runtime progression governance: `contracts/runtime_progression_stages.v0.json` owns the canonical order and allowed transitions, while `contracts/runtime_progression_contract.v0.json` owns halt-preservation requirements. Stack, controlled-memory, progression-entry, and minimal runtime-initialization evidence are proven by hosted CI run `29459278491`. The halt loop remains authoritative after the bounded call.

Current v0.7.45 runtime progression entry: `contracts/runtime_progression_entry_contract.v0.json` governs the assembly-to-Odin boundary, bootstrap context, marker ownership, exact success status, and return continuation. Hosted CI captured the ordered runtime markers and passed the progression validator. This proves only the bounded governed path described by the contract.

Current v0.6.6 runtime progression stage governance: `contracts/runtime_progression_stages.v0.json` is the authoritative model for the planned progression from `BOOT_SMOKE` to `USERSPACE_PLANNING`. It defines stage ordering, prerequisites, evidence, transition rules, and forbidden shortcuts. It does not implement runtime progression or replace the halt behavior.

Current v0.7.0 stack initialization evidence: `contracts/stack_initialization_evidence_contract.v0.json` defines the controlled boot stack proof. `_start` sets `rsp` to `boot_stack_top`, performs a bounded push/pop probe, emits `KOZO_STACK_INIT_OK`, and then enters the governed halt loop. This proves only controlled stack establishment and marker emission.

Current v0.7.4 memory initialization evidence: `boot_memory_region` through `boot_memory_region_end` defines a boot-owned 4096-byte, 4096-byte-aligned static `.bss` region. Assembly explicitly zeroes the region, verifies and restores a bounded 64-bit sentinel probe at offset zero, and emits `KOZO_MEMORY_INIT_OK`. v0.7.4 is accepted by the CI validator gate; manual artifact inspection was not completed.

Current v0.7.45 local progression implementation: the call-site stack is checked for 16-byte alignment, the red zone is disabled in freestanding builds, `rdi` carries a fixed 64-byte context, and `eax` carries the exact internal status. Odin validates version, size, zero fields, stack geometry, and memory geometry; performs a bounded static-state probe; causes `KOZO_RUNTIME_INIT_OK` to be emitted through a fixed assembly bridge; and returns to the assembly continuation. This does not prove complete Odin runtime readiness, dynamic initialization, allocation, paging, interrupts, scheduling, userspace, hardware syscall isolation, compatibility, or production readiness.

Selected boot protocol: Limine.

The current repository has a 64-bit `_start` symbol, an exported `kernel_entry`, early serial initialization, early KOZO marker strings, and runtime-adjacent object/symbol smoke evidence.

The boot protocol decision, boot image skeleton, boot tooling acquisition policy, ISO generation command path, CI ISO tooling install path, and kernel entry reachability diagnostic path are complete.

`scripts/build_boot_image.sh` writes `artifacts/runtime/boot_image/package_metadata.json`.

`scripts/build_boot_image.sh` writes `artifacts/runtime/kernel_elf_report.json`.

`scripts/qemu_smoke.sh` writes `artifacts/runtime/qemu_smoke.metadata.json`, `artifacts/runtime/qemu_smoke.log`, `artifacts/runtime/qemu_smoke.stderr.log`, and `artifacts/runtime/qemu_smoke.summary.txt`.

The expected ISO path is `artifacts/runtime/boot_image/kozo.iso`.

The configured Limine kernel path is `boot():/boot/kozo/kozo-kernel.elf`, using Limine's boot-resource path semantics for the boot drive partition containing the configuration file.

The normalized ISO path is `boot/kozo/kozo-kernel.elf`.

`scripts/build_boot_image.sh` writes `artifacts/runtime/boot_image/iso_contents.txt` when an ISO is produced so packaging validation can confirm the configured Limine path is visible in the image.

The ISO generation command includes Rock Ridge and Joliet metadata so the lower-case Limine path remains visible to the loader when ISO tooling is available.

GitHub Actions full CI installs xorriso, acquires Limine v12.3.3 from a pinned source release, builds Limine, and attempts ISO generation.

The current local tooling does not yet provide the Limine artifacts and xorriso executable required to produce that image, so local verification continues to report blocked packaging metadata.

KOZO has CI-proven QEMU serial smoke evidence. Local execution may still record `missing_iso_generation_tooling` when Limine and xorriso are unavailable outside CI.

The early marker sequence is:

```text
KOZO_EARLY_0_ENTRY
KOZO_EARLY_1_SERIAL_INIT_START
KOZO_EARLY_2_SERIAL_INIT_OK
KOZO_BOOT_SMOKE_OK
KOZO_STACK_INIT_OK
KOZO_MEMORY_INIT_OK
```

---

# 3. Missing Components

The concrete remaining local-only missing components are:

* local Limine executable
* local xorriso executable
* local Limine bootloader artifacts
* bootable ISO artifact when not produced by CI
Validated QEMU serial smoke execution is no longer missing in CI evidence.

This still does not authorize a broad QEMU boot, hardware trap, compatibility, userspace, subsystem, or production-readiness claim.

---

# 4. Current Surfaces

The current source surfaces relevant to future boot work are:

* `kernel/arch/x86_64/boot.asm`
* `kernel/main.odin`
* `kernel/arch/x86_64/serial.odin`
* `scripts/runtime_smoke.sh`
* `scripts/build_boot_image.sh`
* `scripts/kernel_elf_report.py`
* `scripts/qemu_smoke.sh`
* `docs/BOOT_TOOLING.md`
* `artifacts/runtime/kernel_elf_report.json`
* `artifacts/runtime/qemu_smoke.metadata.json`
* `artifacts/runtime/qemu_smoke.log`
* `artifacts/runtime/qemu_smoke.summary.txt`

`kernel/arch/x86_64/boot.asm` defines `_start`, and `scripts/build_boot_image.sh` links a kernel ELF for the Limine image skeleton.

`artifacts/runtime/kernel_elf_report.json` records that the staged kernel ELF has an x86_64 executable format, `_start` entry alignment, PT_LOAD segments, PT_LOAD virtual and physical addresses, higher-half layout summary, and the current load-layout blocker. That report does not prove Limine has loaded the ELF or transferred control to `_start`.

`kernel/arch/x86_64/boot.asm` emits `KOZO_BOOT_SMOKE_OK` after assembly-level serial initialization, establishes the controlled boot stack, initializes and probes the governed static region, and emits `KOZO_STACK_INIT_OK` followed by `KOZO_MEMORY_INIT_OK`. It then emits `KOZO_RUNTIME_PROGRESS_ENTRY`, calls the bounded Odin entry, receives Odin-owned runtime, loop, and capability evidence through fixed bridges, requires exact status zero, emits `KOZO_RUNTIME_RETURN_OK`, and enters the terminal halt path. Passing current QEMU evidence requires the captured serial log to contain the full expected sequence.

After the Odin path returns exact status zero and assembly emits `KOZO_RUNTIME_RETURN_OK`, `kernel/arch/x86_64/boot.asm` enters the governed terminal halt loop. That source-level terminal behavior is validated by `runtime_halt_contract` and does not prove hardware halt instruction semantics, interrupt handling, scheduler behavior, general stack readiness, general memory management, userspace execution, syscall dispatch, or production readiness.

`kernel/arch/x86_64/serial.odin` initializes COM1 serial output for the later Odin path. The v0.5.0 smoke marker is owned by the assembly entry path and is not Odin runtime, stack, memory, syscall, or hardware-trap evidence.

`kernel/arch/x86_64/serial.odin` also owns the v0.4.0 early markers. Those markers are diagnostic evidence only; they do not prove hardware trap execution, userspace execution, or subsystem maturity.

---

# 5. Required Next Fix

The previous `missing_bootable_iso_packaging` blocker was refined to `missing_limine_iso_tooling`.

The previous `missing_limine_iso_tooling` blocker is refined by `docs/BOOT_TOOLING.md`.

The QEMU serial smoke, stack evidence, controlled-memory evidence, bounded
progression entry, minimal Odin initialization, controlled runtime loop, first
governed internal capability, and v0.8.1 CPU extended-state paths are proven.
v0.8.2 locally adds one bounded second capability that transitions a boot-owned
state cell from READY/0 to ACTIVE/1. Hosted marker and validator evidence is
required before v0.8.2 acceptance.

The existing QEMU smoke command writes blocked or passing metadata to `artifacts/runtime/qemu_smoke.metadata.json` and serial output to `artifacts/runtime/qemu_smoke.log`.

The selected protocol and implementation plan are owned by `docs/BOOT_PROTOCOL.md`.

The boot image skeleton is owned by `docs/BOOT_IMAGE.md`.

---

# 6. Non-Goals

This document does not claim QEMU boot.

This document does not claim hardware syscall/trap execution.

This document does not claim Linux compatibility.

This document does not claim POSIX compatibility.

This document does not claim general userspace execution.

This document does not claim process model behavior.

This document does not claim VFS behavior.

This document does not claim scheduler maturity.

This document does not claim ELF loading.

This document does not claim file descriptor behavior.

This document does not claim production readiness.

---

# 7. Evidence

The current blocker evidence artifact is:

```text
artifacts/runtime/boot_blocker_report.json
```

It is generated by:

```text
scripts/boot_blocker_report.sh
```

It is validated by:

```text
boot_blocker_report
```

The current boot image packaging metadata is:

```text
artifacts/runtime/boot_image/package_metadata.json
```

The current QEMU smoke metadata is:

```text
artifacts/runtime/qemu_smoke.metadata.json
```

The QEMU smoke evidence validator is:

```text
qemu_smoke_evidence
```

The current kernel ELF loadability report is:

```text
artifacts/runtime/kernel_elf_report.json
```

The kernel ELF loadability validator is:

```text
kernel_loadability
```

## CPU Extended-State Gate

After `KOZO_MEMORY_INIT_OK` and before the first Odin call, assembly validates
CPUID leaf 1 FPU/FXSR/SSE/SSE2 support, configures and reads back the required
CR0/CR4 bits, initializes x87 and MXCSR, and validates one bounded SSE2 result.
The resulting markers are:

```text
KOZO_CPU_EXT_STATE_INIT_START
KOZO_CPU_EXT_STATE_INIT_OK
KOZO_SIMD_PROBE_OK
```

Only the successful path continues to `KOZO_RUNTIME_PROGRESS_ENTRY`. Every
failure converges on the existing `cli`/`hlt` loop without CPU, SIMD, or
runtime-success markers. `docs/CPU_EXTENDED_STATE.md` owns the detailed
descriptive boundary; the contract under `contracts/` is authoritative.

This gate does not enable AVX/XSAVE, context switching, exception recovery,
userspace, or production behavior.

## Governed State Transition

After `KOZO_FIRST_CAPABILITY_OK`, executed Odin code constructs the fixed
capability ID 2 request, validates exact pointer and field constraints, and
transitions only `runtime_state_transition_cell`. The local ordered suffix is:

```text
KOZO_FIRST_CAPABILITY_OK
KOZO_RUNTIME_STATE_UPDATE_ENTER
KOZO_RUNTIME_STATE_UPDATE_OK
KOZO_SECOND_CAPABILITY_OK
KOZO_RUNTIME_RETURN_OK
```

The transition uses volatile write/readback, restores the prior state and
generation on readback failure, validates the fixed response before success,
and preserves the assembly terminal halt path. It is not userspace access,
general memory management, concurrency, authorization, or production
readiness.

## Bounded Privilege-Transition Probe

The local ordered transition boundary is:

```text
KOZO_USER_MAPPING_SURVIVAL_OK
KOZO_PRIVILEGE_TRANSITION_INIT_START
KOZO_PRIVILEGE_TABLES_OK
KOZO_RING3_ENTER
KOZO_USER_REQUEST_COPY_IN_OK
KOZO_USER_REQUEST_SERVICE_OK
KOZO_USER_RESPONSE_COPY_OUT_OK
KOZO_FIXED_USER_REQUEST_OK
KOZO_RING3_PROBE_OK
KOZO_RING0_RETURN_OK
KOZO_RUNTIME_PROGRESS_ENTRY
```

The v0.8.5 markers between Ring3 entry and probe completion follow exact
copy-in, fixed-service, copy-out/readback, and buffer-clear validation.
`KOZO_RING3_PROBE_OK` still follows validation of the hardware-saved CPL3
frame and the complete fixed request transaction. Any descriptor, stack,
frame, request, response, clear, or continuation failure suppresses later
success markers and converges on
`boot_terminal_halt`. The final assembly `cli`/`hlt` loop remains the only
terminal runtime state.

This proves one fixed lower-privilege excursion, one exact boot-time request
and response, and a fixed return. It does not prove general userspace, process
isolation, a public syscall ABI, arbitrary user-pointer handling, general copy
helpers, return to Ring 3, general interrupt handling, exception recovery, or
production readiness.

# 11. Bounded Response-Consumption Path

v0.8.6 preserves the accepted boot, mapping, CPU-state, and privilege setup.
After response copy-out, Ring 0 preserves the response, sets
`RESPONSE_READY`, and performs one sanitized `iretq` to the fixed consumer.
The consumer validates CPL3, its fixed stack, and every response field before
writing one fixed record and invoking `int 0x81` again.

Ring 0 validates the second saved frame, revalidates the response, copies and
validates exactly 48 record bytes, clears every remaining transaction buffer,
and resumes only the fixed continuation. Failure returns nonzero to `_start`,
which converges on the existing terminal halt.

# 12. Runtime-Ordered Status Transaction

v0.8.7 preserves all boot, mapping, CPU-state, and privilege setup but does not
enter Ring 3 from `_start`. Assembly setup completes, Odin enters, and the
controlled loop reaches `KOZO_RUNTIME_LOOP_EXIT_OK` before Odin collects the
runtime snapshot and invokes the fixed Ring 3 transaction.

After Ring 0 accepts the response-consumption record, control returns to Odin.
The unchanged internal status capability and state-transition capability run
before `KOZO_RUNTIME_RETURN_OK` and the authoritative `cli`/`hlt` loop.
