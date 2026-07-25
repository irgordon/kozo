# CPU Extended-State Initialization

## Purpose

KOZO initializes the boot CPU state required for x87 and SSE execution before
the first call into Odin. The authoritative requirements are defined by
`contracts/cpu_extended_state_initialization_contract.v0.json`.

This initialization protects the early Odin path from faults caused by
compiler-generated x87 or SSE instructions. It is not a general CPU subsystem.

## Execution Order

The governed pre-Odin sequence is:

```text
KOZO_MEMORY_INIT_OK
-> KOZO_CPU_EXT_STATE_INIT_START
-> CPUID feature validation
-> CR0 and CR4 configuration and readback
-> x87 and MXCSR initialization and readback
-> KOZO_CPU_EXT_STATE_INIT_OK
-> bounded SIMD survival probe
-> KOZO_SIMD_PROBE_OK
-> KOZO_RUNTIME_PROGRESS_ENTRY
```

Any failure before `KOZO_SIMD_PROBE_OK` converges on the existing non-fallthrough
`cli`/`hlt` loop. Odin is not entered on those failure paths.

## Required Features

The assembly path confirms that CPUID basic leaf 1 is available and requires
these leaf 1 EDX features:

| Feature | Bit | Purpose |
| --- | ---: | --- |
| FPU | 0 | x87 execution |
| FXSR | 24 | FXSAVE/FXRSTOR and SSE state support |
| SSE | 25 | SSE execution |
| SSE2 | 26 | SSE2 execution |

Unsupported feature sets return a bounded failure status and do not enter Odin.

## Control Policy

Unrelated control-register bits are preserved through read-modify-write
operations. Both registers are read back before initialization succeeds.

| Register | Bit | Required value | Purpose |
| --- | ---: | ---: | --- |
| CR0.MP | 1 | 1 | Governs WAIT/FWAIT behavior |
| CR0.EM | 2 | 0 | Allows x87/SSE execution |
| CR0.TS | 3 | 0 | Prevents device-not-available faults |
| CR0.NE | 5 | 1 | Uses native floating-point exceptions |
| CR4.OSFXSR | 9 | 1 | Enables FXSAVE/FXRSTOR and SSE state |
| CR4.OSXMMEXCPT | 10 | 1 | Enables SIMD exception handling semantics |
| CR4.OSXSAVE | 18 | 0 | Keeps AVX/XCR0-dependent execution prohibited |

Exception recovery remains outside this phase even though the architectural
control bits are configured.

## x87 And SSE State

The path executes `fninit`, stores the x87 control word with `fnstcw`, and
requires the architectural default `0x037F`.

It loads MXCSR with `0x00001F80`, stores the observed value, and requires an
exact match before emitting `KOZO_CPU_EXT_STATE_INIT_OK`.

## SIMD Survival Probe

The probe uses two fixed 128-bit values from read-only storage, executes one
SSE2 `pxor`, and stores the result in a 16-byte, 16-byte-aligned boot-owned
buffer. Scalar comparisons validate both 64-bit halves:

```text
low:  0xffee2233bbaa6677
high: 0x8796a5b4c3d2e1f0
```

The result buffer and the used XMM register are cleared on success and failure.
`KOZO_SIMD_PROBE_OK` is emitted only after both comparisons succeed.

## Evidence

Source and ELF validation require:

* the CPU initializer and probe symbols;
* CPUID, CR0, CR4, x87, MXCSR, and SSE2 instructions in the governed path;
* pre-Odin ordering;
* exact probe buffer geometry;
* no governed AVX, YMM, ZMM, or `xsetbv` use;
* failure convergence on the existing halt path.

QEMU evidence requires the three CPU-state markers in taxonomy order before
runtime progression. Generated metadata and reports summarize this evidence;
they do not define the policy.

## AVX Prohibition

`CR4.OSXSAVE` remains clear. KOZO does not execute `xsetbv`, use YMM or ZMM
registers, or permit VEX/EVEX AVX instructions in the governed pre-Odin path.

Future AVX enablement requires separate governance and evidence for CPUID
XSAVE/OSXSAVE/AVX support, XCR0 policy, XSAVE-area geometry and alignment,
save/restore behavior, context ownership, and failure handling.

## Claim Boundary

This phase proves only that the boot CPU exposed the required feature bits,
the required control state was configured and read back, x87 and MXCSR were
initialized, and one bounded SSE2 result was validated before Odin entry.

It does not prove AVX or XSAVE support, per-task extended-state ownership,
context switching, floating-point exception recovery, complete CPU
initialization, userspace execution, compatibility, isolation, or production
readiness.
