# KOZO Wiki

## What KOZO Is

KOZO is a small x86-64 kernel for people who want to study or extend low-level
software whose claims are tied to explicit tests and runtime evidence. The
v1.1.0 release boots in QEMU, runs two sequential fixed user sessions,
and stops in a known halt state.

KOZO is useful as an auditable kernel foundation and as a learning environment
for evidence-driven operating-system engineering. It is not a desktop or a
general-purpose operating system.

## Current Release

Current final release:
[v1.1.0](https://github.com/irgordon/kozo/releases/tag/v1.1.0)

Previous final release:
[v1.0.1](https://github.com/irgordon/kozo/releases/tag/v1.0.1)

Previous prerelease:
[v1.0.0-rc.1](https://github.com/irgordon/kozo/releases/tag/v1.0.0-rc.1)

The current release provides six immutable hosted assets. Read the
[v1.1.0 release notes](../releases/v1.1.0.md), the
[release evidence](../releases/v1.1.0-evidence.md), or the
[documentation audit](../releases/v1.0.0-documentation-audit.md).

## Choose Your Path

| I want to... | Start here |
| --- | --- |
| Download and run KOZO | [Getting Started](GETTING_STARTED.md) |
| Understand why KOZO exists | [Why KOZO](WHY_KOZO.md) |
| Understand the output | [User Guide](USER_GUIDE.md) |
| Diagnose a problem | [Troubleshooting](TROUBLESHOOTING.md) |
| Maintain or change KOZO | [Maintainer Guide](MAINTAINER_GUIDE.md) |
| Study the architecture | [Engineering Overview](ENGINEERING_OVERVIEW.md) |
| Look up a term | [Terms](TERMS.md) |

## For Users

Start with the downloaded `kozo.iso`. KOZO reports progress over the QEMU
serial console. The v1.1.0 accepted runtime reaches 52 ordered markers ending in
`KOZO_RUNTIME_RETURN_OK`; it does not open a prompt or graphical interface.

## For Maintainers

Read the authority and generated-file rules before editing. A safe change
updates the owning source, runs focused checks and full verification, and keeps
generated proof separate. Published tags, notes, and assets are immutable.

## For Engineers

The engineering path connects boot, memory, CPU state, paging, privilege
transition, the fixed request boundary, Odin runtime operations, evidence, and
halt behavior to their source files and authoritative documents.

## Current Limits

KOZO v1.1.0 does not provide a desktop, window manager, settings application,
interactive terminal, shell, scheduler, persistent processes, general-purpose
userspace, general system-call interface, filesystem, drivers, networking,
dynamic virtual memory, executable loader, Linux or POSIX compatibility,
hostile user-code containment, stable public ABI, or production readiness.

## Where to Report a Problem

First use [Troubleshooting](TROUBLESHOOTING.md) to capture the checksum result,
QEMU outcome, last marker, and exact command. Then open a focused issue in the
[KOZO repository](https://github.com/irgordon/kozo/issues). Do not work around a
failed checksum or weaken a validator.
