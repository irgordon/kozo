<p align="center">
  <a href="https://kozo.page"><img src="kozo-logo.svg" width="240" alt="KOZO"></a>
</p>

# KOZO

KOZO is a small x86-64 operating-system kernel built to make low-level behavior
easy to inspect and verify. It is for people who want to study or extend a
kernel whose claimed behavior is tied to explicit tests and runtime evidence.

Low-level software can fail before normal debugging tools exist. KOZO addresses
that problem by keeping each runtime feature bounded, recording progress over
the serial port, and checking source, kernel-binary, and QEMU evidence against
machine-readable rules.

**Current release:** [v1.0.1](https://github.com/irgordon/kozo/releases/tag/v1.0.1)

**Previous release:** [v1.0.0](https://github.com/irgordon/kozo/releases/tag/v1.0.0)

v1.0.1 fixes cross-host Odin object-output normalization. Its kernel runtime,
ABI, marker sequence, and terminal halt behavior are unchanged from v1.0.0.

Start with the [wiki](docs/wiki/README.md), which routes users, maintainers,
and engineers to the right level of detail. The
[v1.0.1 release notes](docs/releases/v1.0.1.md) and
[release evidence](docs/releases/v1.0.1-evidence.md) describe the current
published product and its immutable artifacts.

## What Works Today

KOZO currently boots on the governed x86-64 QEMU path, prepares a controlled
stack and memory region, initializes required CPU math state, activates
KOZO-owned page tables, enters one fixed user-mode probe, completes one fixed
runtime-status request, executes two internal kernel operations, and stops in
a deterministic halt loop.

The accepted run contains 41 ordered progress markers and passes 67 verification
checks. These are narrow proof claims. KOZO does not yet provide general
userspace, processes, a scheduler, a filesystem, Linux or POSIX compatibility,
or production readiness.

## Start Here

| I want to... | Start here |
| --- | --- |
| Download and run KOZO | [Getting Started](docs/wiki/GETTING_STARTED.md) |
| Understand why KOZO exists | [Why KOZO](docs/wiki/WHY_KOZO.md) |
| Understand the serial result | [User Guide](docs/wiki/USER_GUIDE.md) |
| Maintain or change KOZO | [Maintainer Guide](docs/wiki/MAINTAINER_GUIDE.md) |
| Study the implementation | [Engineering Overview](docs/wiki/ENGINEERING_OVERVIEW.md) |

From a configured development environment:

```bash
scripts/build_boot_image.sh
scripts/qemu_smoke.sh
python3 -m unittest discover -s tests
scripts/verify.sh
```

A successful QEMU run ends with `KOZO_RUNTIME_RETURN_OK`. Full verification
writes `artifacts/latest_verify.json` and reports `VERIFY: PASS`.

## Documentation

- [User and maintainer wiki](docs/wiki/README.md)
- [Detailed architecture](docs/ARCHITECTURE.md)
- [Runtime evidence](docs/RUNTIME_EVIDENCE.md)
- [Security boundaries](docs/SECURITY_MODEL.md)
- [Release checklist](docs/RELEASE_CHECKLIST.md)
- [Documentation audit](docs/DOCUMENTATION_AUDIT.md)
- [v1.0.0 documentation audit](docs/releases/v1.0.0-documentation-audit.md)

User, maintainer, and engineering entry paths start in `docs/wiki`. Detailed
architecture, contract, security, validation, and historical authority remains
under `docs`.

## Release Status

`v1.0.0` is published as the
[final kernel-foundation release](https://github.com/irgordon/kozo/releases/tag/v1.0.0).
Its [release evidence](docs/releases/v1.0.0-evidence.md) records the immutable
tag, hosted asset hashes, and accepted runtime result.

The earlier `v1.0.0-rc.1` prerelease remains immutable. KOZO v1.0.0 is not a
production desktop operating system.

The [v1.0.1 release evidence](docs/releases/v1.0.1-evidence.md) records the
bounded Odin build correction and the gates required before publication.

## Maintaining KOZO

Read the [Maintainer Guide](docs/wiki/MAINTAINER_GUIDE.md) before changing a
contract, validator, runtime marker, or generated report. Generated files are
review surfaces, not sources of truth, and must be refreshed through their
governed generators.

## License

KOZO is available under the MIT or Apache-2.0 license. See [LICENSE](LICENSE),
[LICENSE-MIT](LICENSE-MIT), and [LICENSE-APACHE](LICENSE-APACHE).
