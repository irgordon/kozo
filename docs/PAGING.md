# KOZO Fixed Paging Foundation

Version: 1
Status: Authoritative
Scope: The fixed v0.8.3 page-table ownership and permission boundary

---

# 1. Authority

`contracts/fixed_user_mapping_foundation.v0.json` owns the fixed paging
geometry, permissions, evidence markers, and claim boundary. This document
explains that contract; it does not redefine it. Generated ELF and QEMU
reports are evidence, not authority.

# 2. Paging Model

KOZO requires active x86_64 four-level paging, 4 KiB pages, CPU NX support,
and active `EFER.NXE`. Five-level paging is rejected. Limine's executable
address response supplies the loaded kernel physical and virtual bases used
to resolve fixed physical backing.

KOZO owns seven statically allocated, explicitly cleared, 4096-byte-aligned
table pages:

```text
governed_pml4
├── governed_kernel_pdpt -> governed_kernel_pd -> governed_kernel_pt
└── governed_user_pdpt   -> governed_user_pd   -> governed_user_pt
```

The kernel subtree remains supervisor-only. The dedicated user subtree sets
U/S at PML4E, PDPTE, PDE, and PTE levels.

# 3. Fixed Mappings

| Region | Virtual range | Size | Effective policy |
| --- | --- | ---: | --- |
| User probe code | `0x0000400000000000` to `0x0000400000001000` | 4096 | User, read-only, executable |
| User probe data | `0x0000400000001000` to `0x0000400000002000` | 4096 | User, writable, NX |
| User probe stack | `0x0000400000002000` to `0x0000400000003000` | 4096 | User, writable, NX |

The backing symbols are `user_probe_code_start`/`user_probe_code_end`,
`user_probe_data_start`/`user_probe_data_end`, and
`user_probe_stack`/`user_probe_stack_top`. These regions and all page tables
are fixed, page-aligned, non-overlapping loaded-image storage. No allocator or
general mapping API exists.

Kernel text is supervisor read-only executable. Kernel rodata is supervisor
read-only NX. Kernel data, bss, the boot stack and memory region contained in
bss, CPU-state buffers, runtime/capability state, and fixed page tables are
supervisor writable NX.

# 4. Policy Validation

The software walker combines present, writable, user, and NX state across all
four levels and resolves only the fixed table storage. Validation rejects
missing U/S propagation, user-accessible kernel leaves, wrong backing,
large-page leaves, writable executable mappings, and incorrect code/data/stack
permissions.

Ring 0 read/write survival does not prove Ring 3 access. Effective U/S and W^X
claims depend on the governed software walk and table construction evidence.

# 5. Activation And Survival

After construction and policy validation, KOZO loads the governed root
physical address into CR3. The CR3 page-frame address is read back under mask
`0x000ffffffffff000` and must match exactly.

After activation, KOZO proves continued kernel instruction, stack, and serial
execution; performs bounded write/read/restore probes through the fixed user
data and stack virtual addresses; and re-runs the software permission walk.
Only then is `KOZO_USER_MAPPING_SURVIVAL_OK` emitted.

The evidence sequence is:

```text
KOZO_USER_MAPPING_INIT_START
KOZO_USER_MAPPING_TABLES_OK
KOZO_USER_MAPPING_PERMISSIONS_OK
KOZO_USER_MAPPING_ACTIVATE_OK
KOZO_USER_MAPPING_SURVIVAL_OK
```

Any failure returns an exact mapping status to `_start`, suppresses later
success markers and Odin entry, and converges on the existing terminal halt.

# 6. Claim Boundary

This phase proves one fixed active KOZO-owned four-level hierarchy, three
user-accessible mappings with effective governed permissions, supervisor-only
kernel mappings, exact CR3 readback, and bounded kernel survival.

It does not prove Ring 3 execution, GDT/TSS/IDT setup, syscall MSRs, general
userspace, process or address-space isolation, dynamic mapping, unmapping,
frame allocation, page-fault recovery, scheduler behavior, compatibility, or
production readiness.

# 7. Bounded Privilege Consumer

v0.8.4 consumes only the three accepted fixed mappings. The user code page
contains the fixed `user_privilege_probe_start` target, the user data page
contains the fixed token cell, and the user stack page supplies the fixed CPL3
RSP. Before `iretq`, Ring 0 repeats effective-permission checks for all three
pages and confirms the supervisor-only privilege structures are not
user-accessible.

This use does not change the fixed page-table hierarchy, introduce dynamic
mapping, map arbitrary code, or establish per-process address spaces.

# 8. Fixed Request Consumer

v0.8.5 uses two non-overlapping spans in the existing user data page:
`0x0000400000001000..0x0000400000001028` for the 40-byte request and
`0x0000400000001080..0x00004000000010b0` for the 48-byte response. Before
either span is accessed in Ring0, the software walker validates both endpoints
against the same expected physical backing and exact effective user RW-NX
policy.

No mapping, permission, CR3, or page-table geometry changes in this phase.
The fixed page still does not provide process isolation, dynamic mapping,
page-fault recovery, or safe arbitrary user-pointer access.

# 9. Fixed Response-Consumption Spans

v0.8.6 adds no mapping. It uses the accepted user RW-NX data page for the
existing response and the fixed record at
`0x0000400000001100..0x0000400000001130`. Both endpoints are revalidated by
the software walker before Ring 0 access. The record does not overlap the
request, response, code page, user stack, or supervisor storage.
