# User Guide

## Current Prerelease

KOZO `v1.0.0-rc.1` is available as a
[GitHub prerelease](https://github.com/irgordon/kozo/releases/tag/v1.0.0-rc.1).
Download and checksum instructions are in
[Getting Started](GETTING_STARTED.md). The prerelease is intended for testing
the current kernel foundation; it is not the final v1.0.0 release.

## What Happens When KOZO Starts

KOZO starts under Limine in a virtual x86-64 computer. It prepares a controlled
stack and memory area, enables the CPU math state needed by compiled Odin code,
and activates its own memory map.

The kernel then prepares kernel mode and one fixed user-mode path. Odin runs a
small three-step loop. KOZO enters the fixed user program, accepts one fixed
runtime-status request, returns a fixed response, and checks that response in
both user mode and kernel mode. It then completes two internal kernel
operations and reaches its final safe stop.

## What Progress Markers Mean

A progress marker is a short serial message emitted only after a specific check
succeeds. Markers make a silent early-boot path observable.

The marker order is owned by
`contracts/runtime_evidence_taxonomy.v0.json`. To view the exact sequence from
the latest run:

```bash
jq -r '.observed_markers[]' artifacts/runtime/qemu_smoke.metadata.json
```

The sequence groups into boot, memory and CPU setup, page-table setup,
user-mode entry, fixed request handling, internal capabilities, and runtime
return. The final marker is `KOZO_RUNTIME_RETURN_OK`.

## How to Recognize Success

Run:

```bash
scripts/qemu_smoke.sh
cat artifacts/runtime/qemu_smoke.summary.txt
```

A successful summary reports:

```text
Outcome: pass
Blocker: none
Expected Marker: KOZO_RUNTIME_RETURN_OK
```

The accepted prerelease produces 41 ordered markers. Full repository
verification must also print `VERIFY: PASS`.

KOZO stops after the final marker. There is no prompt, shell, desktop, settings
screen, or other interactive application interface in this prerelease.

## What the Fixed User Program Does

The current user-mode code is linked into the kernel image at a fixed address.
It is not loaded from a file and cannot be replaced by a caller.

The program confirms that it is running in user mode, submits one fixed status
request through software interrupt `int 0x81`, checks every returned field,
records that it consumed the response, and returns through the same fixed gate.

## What the Runtime-Status Request Returns

The response contains only bounded facts already known by the kernel:

- the current proven startup stage;
- the proven-stage mask;
- the controlled boot-memory size;
- the fixed loop limit, final count, and final accumulator;
- a mask of the fixed runtime features proven by the current path.

The response contains no kernel pointer, physical address, variable length, or
caller-selected field.

## How Failures Are Reported

Before QEMU starts, tool or image failures are recorded as exact failure
reasons. During execution, the last observed progress marker identifies the
boundary that was reached. A failed runtime check stops before later success
markers and converges on a halt path.

Use [Troubleshooting](TROUBLESHOOTING.md) to interpret the last marker.

## Current Limits

This fixed path does not provide a process model, persistent user program,
general syscall interface, scheduler, files, devices, networking, memory-fault
recovery, hostile-code containment, compatibility promise, or production
readiness.
