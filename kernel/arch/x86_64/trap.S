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

// Simple interrupt handler macro (No Error Code)
.macro TRAP_STUB name num
    .global \name
    \name:
        pushq %rax
        pushq %rcx
        pushq %rdx
        pushq %rsi
        pushq %rdi
        pushq %r8
        pushq %r9
        pushq %r10
        pushq %r11
        
        // Smart swapgs: CS is at 80(%rsp)
        testb $3, 80(%rsp)
        jz 1f
        swapgs
    1:
        movq $\num, %rdi
        call trap_dispatch
        
        testb $3, 80(%rsp)
        jz 2f
        swapgs
    2:
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

// Interrupt handler macro (With Error Code)
.macro TRAP_STUB_ERR name num
    .global \name
    \name:
        // Error code is already on stack. We swap it with rax to preserve registers.
        xchgq %rax, (%rsp) 
        pushq %rcx
        pushq %rdx
        pushq %rsi
        pushq %rdi
        pushq %r8
        pushq %r9
        pushq %r10
        pushq %r11
        
        // Smart swapgs: CS is at 80(%rsp)
        // RAX push (via swap) + 8 more pushes = 9 pushes.
        // Stack: SS, RSP, RFLAGS, CS, RIP, ERR, R11...
        // CS is at 80(%rsp)
        testb $3, 80(%rsp)
        jz 1f
        swapgs
    1:
        movq $\num, %rdi
        // RSI gets the error code from rax
        movq %rax, %rsi 
        call trap_dispatch
        
        testb $3, 80(%rsp)
        jz 2f
        swapgs
    2:
        popq %r11
        popq %r10
        popq %r9
        popq %r8
        popq %rdi
        popq %rsi
        popq %rdx
        popq %rcx
        popq %rax // Error code was here, now rax is restored
        iretq
.endm

// Generate stub handlers
TRAP_STUB trap_divide_error 0
TRAP_STUB trap_debug 1
TRAP_STUB trap_nmi 2
TRAP_STUB trap_breakpoint 3
TRAP_STUB trap_overflow 4
TRAP_STUB trap_invalid_opcode 6
TRAP_STUB trap_device_not_avail 7
TRAP_STUB_ERR trap_double_fault 8
TRAP_STUB_ERR trap_invalid_tss 10
TRAP_STUB_ERR trap_segment_not_present 11
TRAP_STUB_ERR trap_stack_segment 12
TRAP_STUB_ERR trap_general_protection 13
TRAP_STUB_ERR trap_page_fault 14
TRAP_STUB trap_x87_exception 16
TRAP_STUB_ERR trap_alignment_check 17
TRAP_STUB trap_machine_check 18
TRAP_STUB trap_simd_exception 19
TRAP_STUB trap_virtualization 20
TRAP_STUB_ERR trap_security 30
TRAP_STUB trap_timer 32

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
    
    testb $3, 80(%rsp)
    jz 1f
    swapgs
1:
    movq $0xFF, %rdi
    call trap_dispatch
    
    testb $3, 80(%rsp)
    jz 2f
    swapgs
2:
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
    // 1. Swap from User GS to Kernel GS
    swapgs

    // Save User RSP and load Kernel RSP
    movq %rsp, user_rsp_scratch(%rip)
    movq kernel_rsp_scratch(%rip), %rsp
    
    // 2. Save User State (Match iretq frame for consistency)
    pushq $0x1B                      // SS (User Data)
    pushq user_rsp_scratch(%rip)     // RSP
    pushq %r11                       // RFLAGS (saved in R11 by syscall)
    pushq $0x23                      // CS (User Code)
    pushq %rcx                       // RIP (saved in RCX by syscall)

    // 3. Push Genearl Purpose Registers (Matches SyscallFrame order)
    pushq %rax
    pushq %rbx
    pushq %rcx
    pushq %rdx
    pushq %rsi
    pushq %rdi
    pushq %rbp
    pushq %r8
    pushq %r9
    pushq %r10
    pushq %r11
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15

    // 4. Call Zig dispatcher
    // RDI = SyscallFrame*
    movq %rsp, %rdi
    call syscall_dispatch

    // 5. Restore registers
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %r11
    popq %r10
    popq %r9
    popq %r8
    popq %rbp
    popq %rdi
    popq %rsi
    popq %rdx
    popq %rcx
    popq %rbx
    popq %rax

    // 6. Setup for sysretq
    // RCX = RIP, R11 = RFLAGS (Retrieved from frame)
    movq 120(%rsp), %rcx    // RIP
    movq 136(%rsp), %r11    // RFLAGS
    
    // Restore User RSP
    movq 144(%rsp), %rsp    // RSP
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

// void idt_set_ist(uint8_t vector, uint8_t ist_index)
.global idt_set_ist
idt_set_ist:
    // RDI = vector, RSI = ist_index
    movq %rdi, %rax
    shlq $4, %rax                 // vector * 16 (sizeof IDT entry)
    leaq idt(%rip), %r8
    addq %r8, %rax                // &idt[vector]
    
    movb %sil, 4(%rax)            // Set IST field (byte 4 of the entry)
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
    .quad trap_timer             /* 32 */
    // 33-255: default handler
    .rept 223
    .quad trap_default
    .endr

.global user_rsp_scratch
.global kernel_rsp_scratch
user_rsp_scratch:   .quad 0
kernel_rsp_scratch: .quad 0
