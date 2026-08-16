# Terms

Use the plain wording first. The technical term helps readers find the owning
engineering document.

| Plain wording | Technical term | Why it matters in KOZO |
| --- | --- | --- |
| Kernel mode | Ring 0 | The CPU mode that owns privileged state and validates the fixed user request |
| User mode | Ring 3 | The lower-privilege mode used by KOZO's one fixed user program |
| Memory map | Page table | Maps virtual addresses to physical pages and keeps kernel leaves supervisor-only |
| Kernel-only | Supervisor-only | Prevents the fixed user path from accessing kernel mappings through page permissions |
| Write-or-run protection | W^X | Prevents the fixed user pages from being writable and executable at the same time |
| Not executable | NX | Marks fixed data and stack pages as non-executable |
| Activate KOZO's memory map | CR3 activation | Switches the CPU to the validated KOZO-owned page-table root |
| Kernel operation | Capability | One explicit internal operation with fixed input, output, and failure rules |
| Progress marker | Runtime marker | A serial line emitted after one accepted runtime stage succeeds |
| Failure reason | Blocker | Identifies why governed verification could not accept a result |
| Stop safely | Fail closed | Prevents missing or uncertain state from being reported as success |
| Rule file | Contract | A machine-readable definition of one required boundary or behavior |
| Automated check | Validator | Compares contracts, source, ELF, runtime evidence, or generated reports |
| Generated verification report | Generated proof | Records a governed result but does not replace authoritative source or contracts |
| Published file | Release artifact | One immutable file attached to the GitHub release, such as the ISO or checksum list |
| Named Git record | Annotated tag | Stores the release name and message while pointing to one accepted commit |
| Application binary interface | ABI | Defines binary-facing constants or layouts; KOZO does not promise a stable public ABI |
| Fixed request path | Fixed user boundary | Moves one fixed request and response between user and kernel mode |
| Copy request into the kernel | Copy-in | Copies fixed user memory into kernel-owned memory before validation and service work |
| Copy response to the user | Copy-out | Copies a validated fixed kernel response to the user page |
| Status copy | Snapshot | Holds bounded proven runtime facts while the request is processed |
| Mode table | Global Descriptor Table (GDT) | Defines the fixed kernel and user code/data segments |
| Interrupt table | Interrupt Descriptor Table (IDT) | Routes the one fixed software interrupt and fail-closed fault sinks |
| Kernel return-stack settings | Task State Segment (TSS) | Supplies the Ring 0 stack when the fixed user path returns |
| Kernel return stack | RSP0 | The fixed stack pointer loaded for a user-to-kernel transition |
| Mode-switch instruction | `iretq` | Enters the fixed Ring 3 code using an explicit return frame |
| Fixed user-to-kernel call | `int 0x81` | Invokes the governed request/response gate twice per bounded v1.1.0 session |
| CPU math state | x87/SSE state | Must be initialized before Odin can safely execute compiler-generated instructions |
| Kernel binary | ELF | The linked file inspected for symbols, instructions, and geometry |
| Virtual test computer | QEMU | Boots the released ISO and captures its serial evidence |
| Final safe stop | Halt loop | The terminal successful or failed state; it is not a shutdown or interactive prompt |
