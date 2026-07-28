# Why KOZO

## The Problem

Operating-system code runs before most familiar tools are available. If boot,
memory setup, a CPU mode switch, or a kernel request fails, the machine may
simply stop. A developer then has to infer which assumption was wrong.

Large kernels add another difficulty. Many subsystems start together, so one
successful output may depend on behavior that was never checked directly.

## Why Low-Level Systems Are Hard to Inspect

Early code controls CPU registers, memory maps, stacks, and privilege levels.
Small mistakes can stop execution before normal logs exist. The built binary
may also differ from the source because compilers and linkers choose exact
instructions and addresses.

Source review alone therefore cannot prove that a path executed.

## What KOZO Changes

KOZO builds one bounded step at a time. Each accepted step has:

- a clear rule file;
- source and kernel-binary checks;
- progress markers written to the serial port;
- QEMU evidence that the ordered path executed;
- a safe failure path that does not emit later success.

The product is not complexity. The value is clear behavior, visible proof,
predictable limits, and code that a maintainer can inspect.

## Who Benefits

KOZO is designed for learners, operating-system engineers, tool builders, and
reviewers who want to see how a small kernel boundary works. It is also useful
as a test bed for evidence-driven low-level development.

## What KOZO Proves Today

KOZO proves one x86-64 boot path, controlled initialization, a fixed user-mode
probe, a fixed status transaction, two internal kernel operations, and a final
safe stop. The user and kernel exchange only fixed data at fixed addresses.

See the [User Guide](USER_GUIDE.md) for the current behavior and the
[Engineering Overview](ENGINEERING_OVERVIEW.md) for the implementation path.

## What KOZO Does Not Do Yet

KOZO does not provide arbitrary user programs, processes, scheduling,
filesystems, drivers, networking, Linux or POSIX compatibility, or production
readiness. The fixed user-mode probe does not prove isolation from hostile
code.
