# Plain-Language Terms

Use the plain term first in user guidance. Add the engineering term in
parentheses when it helps a reader find the detailed documentation.

| Engineering term | Plain-language translation | Use in user documentation |
| --- | --- | --- |
| Governed evidence | A checked record that proves a step happened | Proof record |
| Runtime progression | The ordered steps the kernel completes while starting | Startup sequence |
| Runtime marker | A short serial message showing that a step completed | Progress marker |
| Blocker | The exact reason verification stopped | Failure reason |
| Contract | A machine-readable rule describing required behavior | Rule file |
| Validator | A check that compares evidence with a rule | Automated check |
| Fail closed | Stop safely instead of continuing with uncertain state | Stop safely |
| Deterministic | The same input produces the same result | Predictable |
| Controlled runtime loop | A fixed, bounded loop used to prove repeated runtime execution | Fixed runtime loop |
| Capability | A specific operation the kernel is allowed to perform | Kernel operation |
| Runtime-status capability | A kernel operation that reports proven runtime facts | Runtime status request |
| Fixed user boundary | The fixed path used to move a request and response between user and kernel mode | Fixed request path |
| Copy-in | Copy a fixed request from user memory into kernel-owned memory | Copy request into the kernel |
| Copy-out | Copy a fixed response from kernel memory into user memory | Copy response to the user |
| Snapshot | A fixed copy of the current runtime state | Status copy |
| Ring 0 | The CPU mode used by the kernel | Kernel mode |
| Ring 3 | The CPU mode used by user code | User mode |
| Privilege transition | A controlled switch between kernel mode and user mode | Mode switch |
| Page table | A table that maps virtual addresses to physical memory | Memory map |
| User mapping | Memory that user-mode code is allowed to access | User-accessible memory |
| Supervisor-only | Accessible only by kernel-mode code | Kernel-only |
| W^X | Memory may be writable or executable, but not both | Write-or-run protection |
| NX | A setting that prevents memory from being executed as code | Not executable |
| CR3 activation | Switching the CPU to KOZO's page tables | Activate KOZO's memory map |
| GDT | A table that defines kernel and user code modes | Mode table |
| IDT | A table that tells the CPU where interrupt handlers are | Interrupt table |
| TSS | CPU data used to select the kernel stack when returning from user mode | Kernel return-stack settings |
| RSP0 | The kernel stack address used during a user-to-kernel return | Kernel return stack |
| `iretq` | The CPU instruction used for a controlled mode change | Mode-switch instruction |
| `int 0x81` | KOZO's fixed software interrupt for the bounded user request | Fixed user-to-kernel call |
| SIMD | CPU instructions that process several values at once | Vector instructions |
| x87/SSE state | CPU state needed for floating-point and vector instructions | CPU math state |
| ELF | The built kernel file format | Kernel binary |
| ELF evidence | Facts read from the built kernel file | Kernel-binary proof |
| QEMU | A virtual computer used to boot and test KOZO | Virtual test computer |
| Halt loop | The final stopped state after KOZO completes or fails | Final safe stop |
| Generated proof | A report produced by governed scripts | Generated verification report |
| Hosted CI | Automated tests run in the repository's remote build system | Remote verification |
