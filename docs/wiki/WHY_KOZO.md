# Why KOZO

## The Problem KOZO Addresses

Operating-system code starts before most familiar tools are available. A bad
stack, page-table bit, CPU setting, or privilege transition can stop the
machine before a normal log or debugger can explain the failure.

Feature-rich kernels solve broader problems, but their size can make one early
assumption difficult to isolate. KOZO addresses a different need: a kernel
small enough to inspect, with narrow claims that can be connected to source,
the linked binary, and an observed QEMU run.

## Why a Small Governed Kernel Is Useful

KOZO adds one bounded behavior at a time. Each accepted behavior has an owner,
explicit limits, failure checks, and evidence from more than one layer. This
makes it easier to answer:

- what the kernel was supposed to do;
- whether the built kernel retained the required code;
- whether the path ran in QEMU;
- where execution stopped when a check failed.

The practical value is traceability, not feature count. Releases are tied to
one accepted commit and an immutable set of checksummed files.

## Why Evidence Matters

Source review can show intent, but it cannot prove that a compiler kept an
instruction or that QEMU reached a path. Serial progress markers show runtime
order, ELF inspection shows linked structure, and validators check both
against machine-readable rules.

KOZO stops when an expected condition is missing. This prevents a partial
result from being reported as a successful boot. That fail-closed approach
improves claim discipline; it does not by itself make the kernel secure.

## How KOZO Differs From a Feature-Complete OS

KOZO v1.0.0 demonstrates a governed kernel foundation. It initializes its
execution environment, enters one fixed user-mode program, completes one fixed
status transaction, executes two internal kernel operations, and halts.

It deliberately avoids the subsystem breadth of a feature-complete operating
system. The fixed path keeps the implementation and evidence reviewable.

## Who KOZO Is For

KOZO is for:

- learners studying boot, memory, privilege, and kernel boundaries;
- engineers experimenting with evidence-driven low-level development;
- maintainers who need a small, explicit change and verification workflow;
- reviewers who want release claims tied to inspectable evidence.

## Who KOZO Is Not Yet For

KOZO is not yet for someone who needs a desktop, shell, applications,
multi-process workload, hardware support, Linux or POSIX compatibility, or a
stable public ABI. It does not contain arbitrary user programs or prove
containment of hostile user code.

Continue with [Getting Started](GETTING_STARTED.md), the
[User Guide](USER_GUIDE.md), or the
[Engineering Overview](ENGINEERING_OVERVIEW.md).
