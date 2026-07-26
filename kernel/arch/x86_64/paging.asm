bits 64

%include "kernel/arch/x86_64/runtime_layout.inc"

global initialize_fixed_user_mapping_tables
global validate_fixed_user_mapping_policy
global activate_fixed_user_mapping_root
global run_fixed_user_mapping_survival_probe
global walk_page_mapping
global governed_pml4
global governed_kernel_pdpt
global governed_kernel_pd
global governed_kernel_pt
global governed_user_pdpt
global governed_user_pd
global governed_user_pt
global governed_page_tables_start
global governed_page_tables_end
global governed_page_table_root_physical
global observed_governed_cr3
global user_probe_data_start
global user_probe_data_end
global user_probe_stack
global user_probe_stack_top
global limine_executable_address_request

extern __kernel_image_start
extern __kernel_text_start
extern __kernel_text_end
extern __kernel_rodata_start
extern __kernel_rodata_end
extern __kernel_data_start
extern __kernel_data_end
extern __kernel_bss_start
extern __kernel_bss_end
extern __kernel_loaded_image_end
extern user_probe_code_start
extern user_probe_code_end

%define PAGE_SIZE KOZO_PAGE_SIZE
%define PAGE_QWORDS 512
%define GOVERNED_TABLE_PAGE_COUNT 7
%define GOVERNED_TABLE_BYTES (GOVERNED_TABLE_PAGE_COUNT * PAGE_SIZE)

%define PTE_PRESENT 0x001
%define PTE_WRITABLE 0x002
%define PTE_USER 0x004
%define PTE_LARGE 0x080
%define PTE_ADDRESS_MASK 0x000ffffffffff000
%define PTE_NX 0x8000000000000000

%define CR0_PAGING (1 << 31)
%define CR4_PAE (1 << 5)
%define CR4_LA57 (1 << 12)
%define EFER_MSR 0xc0000080
%define EFER_LME (1 << 8)
%define EFER_LMA (1 << 10)
%define EFER_NXE (1 << 11)
%define CPUID_EXTENDED_MAX 0x80000000
%define CPUID_EXTENDED_FEATURES 0x80000001
%define CPUID_NX_BIT (1 << 20)

%define KERNEL_PML4_INDEX 511
%define KERNEL_PDPT_INDEX 510
%define KERNEL_PD_INDEX 1
%define USER_PML4_INDEX 128
%define USER_PDPT_INDEX 0
%define USER_PD_INDEX 0

%define USER_MAPPING_OK 0
%define USER_MAPPING_PAGING_MODE_UNSUPPORTED 1
%define USER_MAPPING_NX_UNAVAILABLE 2
%define USER_MAPPING_PHYSICAL_BACKING_INVALID 3
%define USER_MAPPING_TABLE_GEOMETRY_INVALID 4
%define USER_MAPPING_OVERLAP 5
%define USER_MAPPING_PERMISSION_INVALID 6
%define USER_MAPPING_CR3_ACTIVATION_FAILED 7
%define USER_MAPPING_SURVIVAL_FAILED 8

%define SURVIVAL_KERNEL_SENTINEL 0x4b4f5a4f50414745
%define SURVIVAL_DATA_SENTINEL 0x4b4f5a4f44415441
%define SURVIVAL_STACK_SENTINEL 0x4b4f5a4f5553544b

section .limine_requests_start progbits alloc write align=8
limine_requests_start_marker:
    dq 0xf6b8f4b39de7d1ae
    dq 0xfab91a6940fcb9cf
    dq 0x785c6ed015d3e316
    dq 0x181e920a7852b9d9

section .limine_requests progbits alloc write align=8
limine_executable_address_request:
    dq 0xc7b1dd30df4c8b88
    dq 0x0a82e883a194f07b
    dq 0x71ba76863cc55f63
    dq 0xb2644a48c516a487
    dq 0
    dq 0

section .limine_requests_end progbits alloc write align=8
limine_requests_end_marker:
    dq 0xadc0e0531bb10d03
    dq 0x9572709f31764c62

section .user_probe_data nobits alloc noexec write align=4096
align 4096
user_probe_data_start:
    resb PAGE_SIZE
user_probe_data_end:

section .user_probe_stack nobits alloc noexec write align=4096
align 4096
user_probe_stack:
    resb PAGE_SIZE
user_probe_stack_top:

section .paging_tables nobits alloc noexec write align=4096
align 4096
governed_page_tables_start:
governed_pml4:
    resb PAGE_SIZE
governed_kernel_pdpt:
    resb PAGE_SIZE
governed_kernel_pd:
    resb PAGE_SIZE
governed_kernel_pt:
    resb PAGE_SIZE
governed_user_pdpt:
    resb PAGE_SIZE
governed_user_pd:
    resb PAGE_SIZE
governed_user_pt:
    resb PAGE_SIZE
governed_page_tables_end:

section .data
align 8
executable_physical_base:
    dq 0
executable_virtual_base:
    dq 0
governed_page_table_root_physical:
    dq 0
observed_governed_cr3:
    dq 0
mapping_kernel_survival_value:
    dq SURVIVAL_KERNEL_SENTINEL

section .note.GNU-stack
section .text

; Coordinates fixed table construction. Returns one exact USER_MAPPING status.
initialize_fixed_user_mapping_tables:
    call validate_paging_prerequisites
    test eax, eax
    jnz .done
    call capture_executable_address
    test eax, eax
    jnz .done
    call validate_fixed_mapping_geometry
    test eax, eax
    jnz .done
    call clear_fixed_mapping_storage
    call install_fixed_table_hierarchy
    call map_required_kernel_regions
    test eax, eax
    jnz .done
    call map_fixed_user_regions
.done:
    ret

; Rejects five-level paging and any CPU lacking active NX support.
validate_paging_prerequisites:
    mov rax, cr0
    bt rax, 31
    jnc .paging_unsupported
    mov rax, cr4
    test rax, CR4_PAE
    jz .paging_unsupported
    test rax, CR4_LA57
    jnz .paging_unsupported

    push rbx
    mov eax, CPUID_EXTENDED_MAX
    cpuid
    cmp eax, CPUID_EXTENDED_FEATURES
    jb .nx_unavailable
    mov eax, CPUID_EXTENDED_FEATURES
    cpuid
    test edx, CPUID_NX_BIT
    jz .nx_unavailable
    mov ecx, EFER_MSR
    rdmsr
    and eax, EFER_LME | EFER_LMA | EFER_NXE
    cmp eax, EFER_LME | EFER_LMA | EFER_NXE
    jne .nx_unavailable
    pop rbx
    xor eax, eax
    ret

.nx_unavailable:
    pop rbx
    mov eax, USER_MAPPING_NX_UNAVAILABLE
    ret
.paging_unsupported:
    mov eax, USER_MAPPING_PAGING_MODE_UNSUPPORTED
    ret

capture_executable_address:
    mov rax, [rel limine_executable_address_request + 40]
    test rax, rax
    jz .invalid
    mov rdx, [rax + 8]
    mov rcx, [rax + 16]
    test rdx, PAGE_SIZE - 1
    jnz .invalid
    lea r8, [rel __kernel_image_start]
    cmp rcx, r8
    jne .invalid
    mov [rel executable_physical_base], rdx
    mov [rel executable_virtual_base], rcx
    xor eax, eax
    ret
.invalid:
    mov eax, USER_MAPPING_PHYSICAL_BACKING_INVALID
    ret

validate_fixed_mapping_geometry:
    lea rax, [rel governed_page_tables_start]
    test rax, PAGE_SIZE - 1
    jnz .invalid_table_geometry
    lea rdx, [rel governed_page_tables_end]
    sub rdx, rax
    cmp rdx, GOVERNED_TABLE_BYTES
    jne .invalid_table_geometry

    lea rax, [rel user_probe_code_start]
    lea rdx, [rel user_probe_code_end]
    call validate_one_page_region
    test eax, eax
    jnz .invalid_table_geometry
    lea rax, [rel user_probe_data_start]
    lea rdx, [rel user_probe_data_end]
    call validate_one_page_region
    test eax, eax
    jnz .invalid_table_geometry
    lea rax, [rel user_probe_stack]
    lea rdx, [rel user_probe_stack_top]
    call validate_one_page_region
    test eax, eax
    jnz .invalid_table_geometry

    lea rax, [rel __kernel_loaded_image_end]
    sub rax, [rel executable_virtual_base]
    add rax, [rel executable_physical_base]
    jc .invalid_backing
    mov rdx, PTE_ADDRESS_MASK
    not rdx
    test rax, rdx
    jnz .invalid_backing

    lea rdi, [rel governed_page_tables_start]
    call physical_for_kernel_virtual
    test rax, PAGE_SIZE - 1
    jnz .invalid_backing
    mov [rel governed_page_table_root_physical], rax
    xor eax, eax
    ret

.invalid_table_geometry:
    mov eax, USER_MAPPING_TABLE_GEOMETRY_INVALID
    ret
.invalid_backing:
    mov eax, USER_MAPPING_PHYSICAL_BACKING_INVALID
    ret

; Input: rax=start, rdx=end. Output: eax=0 when one aligned page is described.
validate_one_page_region:
    test rax, PAGE_SIZE - 1
    jnz .invalid
    sub rdx, rax
    cmp rdx, PAGE_SIZE
    jne .invalid
    xor eax, eax
    ret
.invalid:
    mov eax, 1
    ret

clear_fixed_mapping_storage:
    cld
    lea rdi, [rel governed_page_tables_start]
    xor eax, eax
    mov ecx, GOVERNED_TABLE_BYTES / 8
    rep stosq
    lea rdi, [rel user_probe_data_start]
    mov ecx, PAGE_QWORDS
    rep stosq
    lea rdi, [rel user_probe_stack]
    mov ecx, PAGE_QWORDS
    rep stosq
    ret

install_fixed_table_hierarchy:
    lea rdi, [rel governed_kernel_pdpt]
    call physical_for_kernel_virtual
    or rax, PTE_PRESENT | PTE_WRITABLE
    mov [rel governed_pml4 + KERNEL_PML4_INDEX * 8], rax

    lea rdi, [rel governed_kernel_pd]
    call physical_for_kernel_virtual
    or rax, PTE_PRESENT | PTE_WRITABLE
    mov [rel governed_kernel_pdpt + KERNEL_PDPT_INDEX * 8], rax

    lea rdi, [rel governed_kernel_pt]
    call physical_for_kernel_virtual
    or rax, PTE_PRESENT | PTE_WRITABLE
    mov [rel governed_kernel_pd + KERNEL_PD_INDEX * 8], rax

    lea rdi, [rel governed_user_pdpt]
    call physical_for_kernel_virtual
    or rax, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    mov [rel governed_pml4 + USER_PML4_INDEX * 8], rax

    lea rdi, [rel governed_user_pd]
    call physical_for_kernel_virtual
    or rax, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    mov [rel governed_user_pdpt + USER_PDPT_INDEX * 8], rax

    lea rdi, [rel governed_user_pt]
    call physical_for_kernel_virtual
    or rax, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    mov [rel governed_user_pd + USER_PD_INDEX * 8], rax
    ret

map_required_kernel_regions:
    lea rdi, [rel __kernel_text_start]
    lea rsi, [rel __kernel_text_end]
    mov rdx, PTE_PRESENT
    call map_fixed_kernel_range
    test eax, eax
    jnz .done

    lea rdi, [rel __kernel_rodata_start]
    lea rsi, [rel __kernel_rodata_end]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT
    call map_fixed_kernel_range
    test eax, eax
    jnz .done

    lea rdi, [rel __kernel_data_start]
    lea rsi, [rel __kernel_data_end]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE
    call map_fixed_kernel_range
    test eax, eax
    jnz .done

    lea rdi, [rel __kernel_bss_start]
    lea rsi, [rel __kernel_bss_end]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE
    call map_fixed_kernel_range
    test eax, eax
    jnz .done

    lea rdi, [rel governed_page_tables_start]
    lea rsi, [rel governed_page_tables_end]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE
    call map_fixed_kernel_range
.done:
    ret

; Maps one governed supervisor range into the fixed kernel PT.
map_fixed_kernel_range:
    mov r8, rdi
    mov r9, rsi
    add r9, PAGE_SIZE - 1
    and r9, -PAGE_SIZE
    mov r10, rdx
.next_page:
    cmp r8, r9
    jae .success
    mov rax, r8
    shr rax, 39
    and eax, 0x1ff
    cmp eax, KERNEL_PML4_INDEX
    jne .invalid
    mov rax, r8
    shr rax, 30
    and eax, 0x1ff
    cmp eax, KERNEL_PDPT_INDEX
    jne .invalid
    mov rax, r8
    shr rax, 21
    and eax, 0x1ff
    cmp eax, KERNEL_PD_INDEX
    jne .invalid
    mov rdi, r8
    call physical_for_kernel_virtual
    or rax, r10
    mov rcx, r8
    shr rcx, 12
    and ecx, 0x1ff
    lea r11, [rel governed_kernel_pt]
    mov [r11 + rcx * 8], rax
    add r8, PAGE_SIZE
    jmp .next_page
.success:
    xor eax, eax
    ret
.invalid:
    mov eax, USER_MAPPING_TABLE_GEOMETRY_INVALID
    ret

map_fixed_user_regions:
    lea rdi, [rel user_probe_code_start]
    call physical_for_kernel_virtual
    or rax, PTE_PRESENT | PTE_USER
    mov [rel governed_user_pt], rax

    lea rdi, [rel user_probe_data_start]
    call physical_for_kernel_virtual
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    or rax, rdx
    mov [rel governed_user_pt + 8], rax

    lea rdi, [rel user_probe_stack]
    call physical_for_kernel_virtual
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    or rax, rdx
    mov [rel governed_user_pt + 16], rax
    xor eax, eax
    ret

; Validates effective permissions and physical backing through a software walk.
validate_fixed_user_mapping_policy:
    mov rdi, USER_PROBE_CODE_VA
    lea rsi, [rel user_probe_code_start]
    mov rdx, PTE_PRESENT | PTE_USER
    call mapping_matches
    test eax, eax
    jnz .invalid

    mov rdi, USER_PROBE_DATA_VA
    lea rsi, [rel user_probe_data_start]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    call mapping_matches
    test eax, eax
    jnz .invalid

    mov rdi, USER_PROBE_STACK_VA
    lea rsi, [rel user_probe_stack]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    call mapping_matches
    test eax, eax
    jnz .invalid

    lea rdi, [rel __kernel_text_start]
    lea rsi, [rel __kernel_text_start]
    mov rdx, PTE_PRESENT
    call mapping_matches
    test eax, eax
    jnz .invalid

    lea rdi, [rel __kernel_data_start]
    lea rsi, [rel __kernel_data_start]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE
    call mapping_matches
    test eax, eax
    jnz .invalid

    lea rdi, [rel governed_page_tables_start]
    lea rsi, [rel governed_page_tables_start]
    mov rdx, PTE_NX
    or rdx, PTE_PRESENT | PTE_WRITABLE
    call mapping_matches
    test eax, eax
    jnz .invalid

    xor eax, eax
    ret
.invalid:
    mov eax, USER_MAPPING_PERMISSION_INVALID
    ret

; Input: rdi=virtual, rsi=backing symbol, rdx=effective flags.
mapping_matches:
    push rbx
    push r12
    mov rbx, rsi
    mov r12, rdx
    call walk_page_mapping
    cmp rdx, r12
    jne .mismatch
    mov r12, rax
    mov rdi, rbx
    call physical_for_kernel_virtual
    cmp rax, r12
    jne .mismatch
    pop r12
    pop rbx
    xor eax, eax
    ret
.mismatch:
    pop r12
    pop rbx
    mov eax, 1
    ret

; Returns rax=physical page and rdx=effective P/W/U/NX flags, or zeros.
walk_page_mapping:
    push rbx
    push r12
    push r13
    push r14
    mov rbx, rdi
    lea r12, [rel governed_pml4]
    mov r13, PTE_PRESENT | PTE_WRITABLE | PTE_USER
    mov r14d, 39
.walk_level:
    mov ecx, r14d
    mov rax, rbx
    shr rax, cl
    and eax, 0x1ff
    mov r8, [r12 + rax * 8]
    test r8, PTE_PRESENT
    jz .missing
    test r8, PTE_WRITABLE
    jnz .writable
    and r13, ~PTE_WRITABLE
.writable:
    test r8, PTE_USER
    jnz .user
    and r13, ~PTE_USER
.user:
    bt r8, 63
    jnc .nx_done
    mov rax, PTE_NX
    or r13, rax
.nx_done:
    cmp r14d, 12
    je .leaf
    test r8, PTE_LARGE
    jnz .missing
    mov rdi, r8
    mov rax, PTE_ADDRESS_MASK
    and rdi, rax
    call fixed_table_virtual_address
    test rax, rax
    jz .missing
    mov r12, rax
    sub r14d, 9
    jmp .walk_level
.leaf:
    mov rax, r8
    mov rdx, PTE_ADDRESS_MASK
    and rax, rdx
    mov rdx, r13
    pop r14
    pop r13
    pop r12
    pop rbx
    ret
.missing:
    xor eax, eax
    xor edx, edx
    pop r14
    pop r13
    pop r12
    pop rbx
    ret

; Resolves only physical pages owned by the fixed table region.
fixed_table_virtual_address:
    mov r8, rdi
    test r8, PAGE_SIZE - 1
    jnz .invalid
    lea rdi, [rel governed_page_tables_start]
    call physical_for_kernel_virtual
    mov r9, rax
    lea rdi, [rel governed_page_tables_end]
    call physical_for_kernel_virtual
    cmp r8, r9
    jb .invalid
    cmp r8, rax
    jae .invalid
    sub r8, r9
    lea rax, [rel governed_page_tables_start]
    add rax, r8
    ret
.invalid:
    xor eax, eax
    ret

; Converts a loaded-image virtual address using Limine's uniform load offset.
physical_for_kernel_virtual:
    mov rax, rdi
    sub rax, [rel executable_virtual_base]
    add rax, [rel executable_physical_base]
    ret

activate_fixed_user_mapping_root:
    mov rax, [rel governed_page_table_root_physical]
    test rax, PAGE_SIZE - 1
    jnz .failed
    mov cr3, rax
    mov rdx, cr3
    mov [rel observed_governed_cr3], rdx
    mov rcx, PTE_ADDRESS_MASK
    and rax, rcx
    and rdx, rcx
    cmp rdx, rax
    jne .failed
    xor eax, eax
    ret
.failed:
    mov eax, USER_MAPPING_CR3_ACTIVATION_FAILED
    ret

run_fixed_user_mapping_survival_probe:
    mov rax, SURVIVAL_KERNEL_SENTINEL
    cmp qword [rel mapping_kernel_survival_value], rax
    jne .failed
    push rax
    pop rdx
    cmp rdx, rax
    jne .failed

    mov rdi, USER_PROBE_DATA_VA
    cmp qword [rdi], 0
    jne .failed
    mov rax, SURVIVAL_DATA_SENTINEL
    mov [rdi], rax
    cmp [rdi], rax
    jne .failed
    mov qword [rdi], 0
    cmp qword [rdi], 0
    jne .failed

    mov rdi, USER_PROBE_STACK_VA + PAGE_SIZE - 8
    cmp qword [rdi], 0
    jne .failed
    mov rax, SURVIVAL_STACK_SENTINEL
    mov [rdi], rax
    cmp [rdi], rax
    jne .failed
    mov qword [rdi], 0
    cmp qword [rdi], 0
    jne .failed

    call validate_fixed_user_mapping_policy
    test eax, eax
    jnz .failed
    xor eax, eax
    ret
.failed:
    mov eax, USER_MAPPING_SURVIVAL_FAILED
    ret
