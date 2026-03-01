// KOZO Kernel - x86_64 Trap and Syscall Entry
// File Path: kernel/arch/x86_64/trap.S
// Responsibility: IDT installation, exception handling, syscall entry
// Scope: MINIMAL - Just handle traps and syscall, no fancy features

.code64
.section .text

// ============================================================================
// IDT - Interrupt Descriptor Table
// ============================================================================

// IDT entry structure (16 bytes) - we'll fill this at runtime
// For now, just declare the handlers

// Simple interrupt handler macro
.macro TRAP_STUB name num
    .global \name
    \name:
        // Save all registers (System V AMD64 ABI)
        pushq %rax
        pushq %rcx
        pushq %rdx
        pushq %rsi
        pushq %rdi
        pushq %r8
        pushq %r9
        pushq %r10
        pushq %r11
        
        // Call C handler with trap number
        movq $\num, %rdi
        call trap_dispatch
        
        // Restore registers
        popq %r11
        popq %r10
        popq %r9
        popq %r8
        popq %rdi
        popq %rsi
        popq %rdx
        popq %rcx
        popq %rax
        
        iretq
.endm

// Generate stub handlers for all 32 exceptions
TRAP_STUB trap_divide_error 0
TRAP_STUB trap_debug 1
TRAP_STUB trap_nmi 2
TRAP_STUB trap_breakpoint 3
TRAP_STUB trap_overflow 4
// Vector 5: Formerly BOUND, now Reserved in 64-bit
TRAP_STUB trap_invalid_opcode 6
TRAP_STUB trap_device_not_avail 7
TRAP_STUB trap_double_fault 8
TRAP_STUB trap_invalid_tss 10
TRAP_STUB trap_segment_not_present 11
TRAP_STUB trap_stack_segment 12
TRAP_STUB trap_general_protection 13
TRAP_STUB trap_page_fault 14
TRAP_STUB trap_x87_exception 16
TRAP_STUB trap_alignment_check 17
TRAP_STUB trap_machine_check 18
TRAP_STUB trap_simd_exception 19
TRAP_STUB trap_virtualization 20
TRAP_STUB trap_security 30

// Default handler for unimplemented interrupts
.global trap_default
trap_default:
    pushq %rax
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    
    movq $0xFF, %rdi
    call trap_dispatch
    
    popq %r11
    popq %r10
    popq %r9
    popq %r8
    popq %rdi
    popq %rsi
    popq %rdx
    popq %rcx
    popq %rax
    iretq

// ============================================================================
// Syscall Entry Point
// ============================================================================

.global syscall_entry
syscall_entry:
    // On syscall entry:
    // RAX = syscall number
    // RDI, RSI, RDX, R10, R8, R9 = args (System V AMD64 ABI)
    // RCX = user RIP (CPU sets this)
    // R11 = user RFLAGS (CPU sets this)
    
    // Save user state
    pushq %r11                    // User RFLAGS
    pushq %rcx                    // User RIP
    
    // Save argument registers
    pushq %rdi
    pushq %rsi
    pushq %rdx
    pushq %r10
    pushq %r8
    pushq %r9
    
    // Save callee-saved registers
    pushq %rbx
    pushq %rbp
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15
    
    // Arguments are in place, but R10 needs to move to RCX for C
    movq %r10, %rcx
    
    // Call the Zig syscall handler
    call kozo_syscall_handler
    
    // RAX now contains return value
    
    // Restore callee-saved registers
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbp
    popq %rbx
    
    // Restore argument registers
    popq %r9
    popq %r8
    popq %r10
    popq %rdx
    popq %rsi
    popq %rdi
    
    // Restore user RIP, RFLAGS
    popq %rcx
    popq %r11
    
    // Return to user mode
    sysretq

// ============================================================================
// IDT Installation
// ============================================================================

.global idt_install
idt_install:
    lidt idt_descriptor(%rip)
    ret

// ============================================================================
// Syscall MSRs Setup
// ============================================================================

.global syscall_init
syscall_init:
    // EFER.SCE = 1 (Enable syscall/sysret)
    movl $0xC0000080, %ecx        // EFER MSR
    rdmsr
    orl $0x01, %eax               // SCE bit
    wrmsr
    
    // STAR (0xC0000081): Segment selectors
    movl $0xC0000081, %ecx
    movl $0x001B0008, %edx        // User CS=0x1B, Kernel CS=0x08
    xorl %eax, %eax
    wrmsr
    
    // LSTAR (0xC0000082): SYSCALL entry point
    movl $0xC0000082, %ecx
    movabsq $syscall_entry, %rax
    movq %rax, %rdx
    shrq $32, %rdx
    wrmsr
    
    // SFMASK (0xC0000084): RFLAGS mask
    movl $0xC0000084, %ecx
    movl $0x00000200, %eax        // IF bit
    xorl %edx, %edx
    wrmsr
    
    ret

// ============================================================================
// IDT Setup Helper - called from Zig to fill IDT entries
// ============================================================================

// void idt_set_gate(uint8_t vector, uint64_t handler, uint16_t selector, uint8_t type)
.global idt_set_gate
idt_set_gate:
    // RDI = vector, RSI = handler, RDX = selector, RCX = type
    movq %rdi, %rax
    shlq $4, %rax                 // vector * 16 (sizeof IDT entry)
    leaq idt(%rip), %r8
    addq %r8, %rax                // &idt[vector]
    
    // Set offset[0:15]
    movw %si, (%rax)              // Low 16 bits of handler
    
    // Set selector
    movw %dx, 2(%rax)
    
    // Set IST (0) and reserved
    movb $0, 4(%rax)
    
    // Set type and attributes
    movb %cl, 5(%rax)
    
    // Set offset[16:31]
    shrq $16, %rsi
    movw %si, 6(%rax)
    
    // Set offset[32:63]
    shrq $16, %rsi
    movl %esi, 8(%rax)
    
    // Zero reserved
    movl $0, 12(%rax)
    
    ret

// ============================================================================
// Data Section - IDT & Trap Table
// ============================================================================

.section .data
.align 16

idt:
    .space 256 * 16               // 256 entries * 16 bytes
idt_end:

idt_descriptor:
    .word idt_end - idt - 1       // Limit
    .quad idt                     // Base

.align 8
.global trap_table
trap_table:
    .quad trap_divide_error      /* 0 */
    .quad trap_debug             /* 1 */
    .quad trap_nmi               /* 2 */
    .quad trap_breakpoint        /* 3 */
    .quad trap_overflow          /* 4 */
    .quad trap_default           /* 5: Formerly BOUND, now Reserved in 64-bit */
    .quad trap_invalid_opcode    /* 6 */
    .quad trap_device_not_avail  /* 7 */
    .quad trap_double_fault      /* 8 */
    .quad 0                       // 9: Reserved
    .quad trap_invalid_tss       /* 10 */
    .quad trap_segment_not_present /* 11 */
    .quad trap_stack_segment     /* 12 */
    .quad trap_general_protection /* 13 */
    .quad trap_page_fault        /* 14 */
    .quad 0                       // 15: Reserved
    .quad trap_x87_exception     /* 16 */
    .quad trap_alignment_check   /* 17 */
    .quad trap_machine_check     /* 18 */
    .quad trap_simd_exception    /* 19 */
    .quad trap_virtualization    /* 20 */
    .quad 0, 0, 0                 // 21-23: Reserved
    .quad 0, 0, 0                 // 24-26: Reserved
    .quad 0, 0, 0                 // 27-29: Reserved
    .quad trap_security          /* 30 */
    .quad 0                       // 31: Reserved
    // 32-255: default handler
    .rept 224
    .quad trap_default
    .endr
