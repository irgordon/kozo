# Engineering Overview

This page connects the user-visible startup path to the detailed engineering
documents. Exact addresses, bit fields, structure layouts, and instruction
sequences remain in those documents and the authoritative contracts.

## Boot

**What it does:** Limine loads the x86-64 kernel and transfers control to the
assembly entry path.

**Why it matters:** no later claim is meaningful until the kernel entry and
serial path execute.

**Read:** [Boot Baseline](../BOOT.md) and [Boot Tooling](../BOOT_TOOLING.md).

## Stack and Memory

**What it does:** assembly establishes a fixed stack, zeros a controlled memory
region, and proves bounded write/read/restore behavior.

**Why it matters:** compiled code needs known stack and memory state.

**Read:** [Runtime Evidence](../RUNTIME_EVIDENCE.md) and
[Contracts](../CONTRACTS.md).

## CPU State

**What it does:** KOZO checks CPU features and initializes x87 and SSE state
before Odin can execute compiler-generated vector instructions.

**Why it matters:** entering compiled code with unknown math state can fault.

**Read:** [CPU Extended State](../CPU_EXTENDED_STATE.md).

## Page Tables

**What it does:** KOZO builds and activates a fixed four-level memory map with
kernel-only pages and three user-accessible pages.

**Why it matters:** the user-mode probe needs explicit code, data, and stack
permissions without exposing kernel pages.

**Read:** [Paging](../PAGING.md).

## Kernel and User Mode

**What it does:** fixed descriptor and interrupt tables support one controlled
switch to user mode and one governed return to kernel mode.

**Why it matters:** the CPU must prove the privilege boundary, not merely follow
a source-level call.

**Read:** [Privilege Transition](../PRIVILEGE_TRANSITION.md).

## Fixed User Request

**What it does:** user mode sends one fixed request through `int 0x81`; kernel
mode validates and copies it before running the service.

**Why it matters:** kernel code must not trust user-controlled memory directly.

**Read:** [User Request Boundary](../USER_REQUEST_BOUNDARY.md) and
[User Response Consumption](../USER_RESPONSE_CONSUMPTION.md).

## Runtime Status

**What it does:** Odin collects one status copy after the fixed loop. The kernel
formats it for the fixed user response, and both modes validate every field.

**Why it matters:** the user result and internal capability share one source of
runtime truth.

**Read:** [User Runtime Status Service](../USER_RUNTIME_STATUS_SERVICE.md).

## Internal Capabilities

**What it does:** Odin executes one read-only status query and one fixed state
transition after the user transaction completes.

**Why it matters:** each kernel operation has explicit input, output, and
failure rules.

**Read:** [Runtime Capabilities](../RUNTIME_CAPABILITIES.md).

## Failure Behavior

**What it does:** failed checks stop before later success markers and converge
on fixed halt paths.

**Why it matters:** KOZO does not continue from uncertain CPU, memory, or
boundary state.

**Read:** [Security Model](../SECURITY_MODEL.md) and
[Runtime Evidence](../RUNTIME_EVIDENCE.md).

## Evidence and Verification

**What it does:** validators compare contracts, source, the linked kernel, QEMU
logs, generated reports, and task state.

**Why it matters:** no single evidence source can prove the whole path.

**Read:** [Validation](../VALIDATION.md), [Generated Artifacts](../GENERATED_ARTIFACTS.md),
and [Release Evidence](../RELEASE_EVIDENCE.md).

## Where to Read Exact Details

- Architecture authority: [ARCHITECTURE.md](../ARCHITECTURE.md)
- Technical invariants: [INVARIANTS.md](../INVARIANTS.md)
- Contract authority: [CONTRACTS.md](../CONTRACTS.md)
- Compatibility limits: [COMPATIBILITY.md](../COMPATIBILITY.md)
- Current release gates: [RELEASE_CHECKLIST.md](../RELEASE_CHECKLIST.md)
