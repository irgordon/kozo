# User Guide

KOZO v1.0.0 runs one fixed governed runtime demonstration. Using KOZO currently
means booting its ISO in QEMU and observing serial evidence. It does not accept
keyboard commands and does not provide a shell or graphical interface.

## Current Release

KOZO `v1.0.0` is available as the
[final kernel-foundation release](https://github.com/irgordon/kozo/releases/tag/v1.0.0).
Download and checksum instructions are in [Getting Started](GETTING_STARTED.md).

## What Happens When KOZO Starts

Limine loads KOZO in a virtual x86-64 computer. The kernel prepares a controlled
stack and memory region, initializes required CPU state, and activates fixed
page tables.

It then prepares one fixed kernel-to-user path. Odin runs a three-iteration
loop. KOZO enters fixed user-mode code, handles one fixed runtime-status
request, returns a fixed response, and checks that response in both user mode
and kernel mode. It completes two internal kernel operations and reaches its
final safe stop.

## What the Runtime Proves

The accepted path proves that:

- the kernel reached its assembly entry;
- controlled stack, memory, CPU, and paging initialization succeeded;
- fixed descriptor and interrupt tables supported one user-mode transition;
- one fixed request and response crossed the privilege boundary;
- Odin completed a bounded loop and two governed kernel operations;
- all successful paths converged on the final halt loop.

This is a narrow demonstration. It does not prove a general application or
process environment.

## What the Output Means

The serial lines beginning with `KOZO_` are ordered evidence that each accepted
runtime stage completed. They are progress markers, not commands or an
interactive user interface.

The sequence groups into startup, memory and CPU setup, paging, user-mode
entry, fixed request handling, internal capabilities, runtime return, and halt.
The authoritative marker order is owned by the runtime evidence taxonomy
contract; the plain-language purpose is explained in
[Runtime Evidence](../RUNTIME_EVIDENCE.md).

## How to Recognize Success

A successful summary reports:

```text
Outcome: pass
Blocker: none
Observed Markers: 41
Expected Marker: KOZO_RUNTIME_RETURN_OK
```

The final serial marker must be:

```text
KOZO_RUNTIME_RETURN_OK
```

Do not treat an empty log, missing marker, or out-of-order sequence as success.

## Why QEMU Eventually Times Out

After the final marker, KOZO disables interrupts and repeatedly halts. There is
no shutdown service yet, so the bounded smoke script eventually terminates
QEMU. Exit status `124` can therefore accompany a successful run.

The timeout is successful only when the script first reports `Outcome: pass`,
no blocker, and the complete sequence through `KOZO_RUNTIME_RETURN_OK`.

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

## What Users Can Experiment With Safely

- Re-run the hosted ISO and compare the marker sequence.
- Inspect `qemu_smoke.summary.txt` and the generated metadata.
- Inspect the released kernel ELF with the documented read-only tools.
- Build a local copy and compare its governed evidence with the release.
- Change a local source checkout only after reading the maintainer workflow.

Do not modify the published tag or hosted assets. A local experiment is not the
published release and must not be described as such.

## Current Limits

KOZO does not provide a desktop, window manager, settings application,
interactive terminal, shell, scheduler, persistent processes, preemption,
general-purpose userspace, general system-call interface, filesystem, drivers,
networking, dynamic virtual memory, executable loader, Linux or POSIX
compatibility, hostile user-code containment, stable public ABI, or production
readiness.

## Where to Go Next

- [Getting Started](GETTING_STARTED.md) for commands.
- [Troubleshooting](TROUBLESHOOTING.md) for failed runs.
- [Why KOZO](WHY_KOZO.md) for project value and scope.
- [Engineering Overview](ENGINEERING_OVERVIEW.md) for implementation.
- [Maintainer Guide](MAINTAINER_GUIDE.md) before changing the repository.
