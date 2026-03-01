/* kernel/arch/x86_64/boot.S */
/* Last Modified: 2026-02-28, 21:03:12.115 */

.section .note.Xen, "a"
.align 4
    .long 4, 8, 18
    .ascii "Xen\0"
    .long 0x201000, 0

.section .boot.text, "ax"
.global _start
.code32

_start:
    cli
    movl $0x4F314F31, 0xb8000  /* Pulse 1: Red '1' */
    movl $0x9000, %esp

    /* Clear 3 pages of tables */
    movl $boot_pml4, %edi
    xorl %eax, %eax
    movl $3072, %ecx
    rep stosl

    /* PML4 Setup: Shared Trunk */
    movl $boot_pdp, %eax
    orl $0x3, %eax
    movl %eax, (boot_pml4)
    movl %eax, (boot_pml4 + 4088)

    /* PDP Setup */
    movl $boot_pd, %eax
    orl $0x3, %eax
    movl %eax, (boot_pdp)
    movl %eax, (boot_pdp + 4080)

    /* PD Setup: The 4MB Physical Bridge
     * Identity map 0-4MB to physical 0-4MB so VGA (0xb8000) 
     * and current IP (0x201xxx) stay valid.
     */
    movl $0x000083, (boot_pd)      /* 0-2MB -> 0-2MB (VGA lives here) */
    movl $0x200083, (boot_pd + 8)  /* 2-4MB -> 2-4MB (IP lives here) */

    /* Enable Long Mode bits */
    movl $boot_pml4, %eax
    movl %eax, %cr3
    movl %cr4, %eax
    orl $0x20, %eax
    movl %eax, %cr4
    movl $0xC0000080, %ecx
    rdmsr
    orl $0x100, %eax
    wrmsr
    movl %cr0, %eax
    orl $0x80000001, %eax
    movl %eax, %cr0

    lgdt (gdt64_ptr_phys)
    ljmp $0x08, $long_mode_entry

.code64
long_mode_entry:
    movl $0x0E320E32, 0xb8004  /* Pulse 2: Yellow '2' */
    xorw %ax, %ax
    movw %ax, %ds
    movw %ax, %ss
    movabsq $stack_top, %rsp
    movl $0x0F2B0F2B, 0xb800c  /* Pulse 3: White '+' */

    movabsq $kozo_kernel_main, %rax
    jmp *%rax

.section .boot.data, "aw"
.align 4096
boot_pml4: .fill 4096, 1, 0
boot_pdp:  .fill 4096, 1, 0
boot_pd:   .fill 4096, 1, 0

.align 16
gdt64:
    .quad 0x0000000000000000
    .quad 0x00af9a000000ffff
    .quad 0x00cf92000000ffff
gdt64_end:
gdt64_ptr_phys:
    .word gdt64_end - gdt64 - 1
    .long gdt64 - 0xffffffff80000000 + 0x400000