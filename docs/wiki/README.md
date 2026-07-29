# KOZO Wiki

KOZO is a small operating-system kernel that makes early system behavior
visible and testable. It shows each important startup step, checks the result,
and stops safely when a required condition is not proven.

## Why KOZO Exists

Kernel failures often happen before a screen, filesystem, or normal debugger is
available. Large systems can also make it hard to identify which assumption
failed. KOZO keeps its current runtime path small and records progress so a
reader can connect the code, built kernel, and QEMU output.

Read [Why KOZO](WHY_KOZO.md) for the problem, the project approach, and who
benefits.

## Current Release

[KOZO v1.0.0](https://github.com/irgordon/kozo/releases/tag/v1.0.0) is the
current final kernel-foundation release. The accepted `v1.0.0-rc.1`
prerelease remains available as an immutable historical candidate.

KOZO currently exposes its result through serial progress markers. It does not
provide an interactive shell, desktop, or general application environment.

## Who Should Use KOZO

KOZO is useful to:

- learners studying how a kernel reaches user mode;
- engineers testing low-level boot and privilege boundaries;
- maintainers who need exact, reproducible proof for a small system;
- reviewers who want claims tied to source and runtime evidence.

It is not yet a general-purpose operating system.

## What KOZO Proves Today

The accepted x86-64 QEMU path proves a controlled startup sequence through:

- boot, stack, memory, and CPU-state preparation;
- fixed page tables with separate kernel and user permissions;
- one fixed switch to user mode and back;
- one fixed runtime-status request and response;
- two fixed internal kernel operations;
- a final safe stop.

The current accepted run has 41 ordered progress markers and 67 passing
verification checks. Generated reports support review, but contracts and source
files remain authoritative.

## Quick Links

- [Getting Started](GETTING_STARTED.md)
- [User Guide](USER_GUIDE.md)
- [Maintainer Guide](MAINTAINER_GUIDE.md)
- [Troubleshooting](TROUBLESHOOTING.md)
- [Plain-Language Terms](TERMS.md)
- [Engineering Overview](ENGINEERING_OVERVIEW.md)
- [v1.0.0-rc.1 current status](../releases/v1.0.0-rc.1-status.md)
- [v1.0.0-rc.1 release notes](../releases/v1.0.0-rc.1.md)
- [v1.0.0 release notes](../releases/v1.0.0.md)
- [v1.0.0 release evidence](../releases/v1.0.0-evidence.md)

## Current Limits

KOZO does not prove general userspace, process isolation, scheduling, files,
devices, networking, Linux compatibility, POSIX compatibility, or production
readiness. Its current user-mode code is one fixed boot-time probe, not an
arbitrary program.

## Recommended Reading Order

1. [Why KOZO](WHY_KOZO.md)
2. [Getting Started](GETTING_STARTED.md)
3. [User Guide](USER_GUIDE.md)
4. [Maintainer Guide](MAINTAINER_GUIDE.md)
5. [Engineering Overview](ENGINEERING_OVERVIEW.md)
6. Detailed [architecture](../ARCHITECTURE.md), [security](../SECURITY_MODEL.md),
   and [evidence](../RUNTIME_EVIDENCE.md) documents
