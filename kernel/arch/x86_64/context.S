// KOZO Kernel - x86_64 Context Switch
// File Path: kernel/arch/x86_64/context.S
// Responsibility: Save/restore callee-saved registers only
// Scope: MINIMAL - Just what the C ABI requires, no FPU/MMX/SSE

.code64
.section .text

// System V AMD64 ABI Callee-saved registers:
// RBX, RBP, R12, R13, R14, R15, RSP (implicit)
// Plus: RIP (instruction pointer)

// Context structure layout (64 bytes):
// [0:7]   - R15
// [8:15]  - R14
// [16:23] - R13
// [24:31] - R12
// [32:39] - RBP
// [40:47] - RBX
// [48:55] - RSP (stack pointer)
// [56:63] - RIP (instruction pointer)

// ============================================================================
// Context Save
// ============================================================================

// void context_save(Context* ctx)
// Saves current callee-saved registers to context structure
.global context_save
context_save:
    // Argument: RDI = pointer to context structure
    
    // Save callee-saved registers
    movq %r15, 0(%rdi)
    movq %r14, 8(%rdi)
    movq %r13, 16(%rdi)
    movq %r12, 24(%rdi)
    movq %rbp, 32(%rdi)
    movq %rbx, 40(%rdi)
    
    // Save stack pointer
    movq %rsp, 48(%rdi)
    
    // Return address is at top of stack
    movq (%rsp), %rax
    movq %rax, 56(%rdi)
    
    ret

// ============================================================================
// Context Restore
// ============================================================================

// void context_restore(Context* ctx)
// Restores callee-saved registers from context structure
// DOES NOT RETURN - transfers control to saved RIP
.global context_restore
context_restore:
    // Argument: RDI = pointer to context structure
    
    // Restore callee-saved registers
    movq 0(%rdi), %r15
    movq 8(%rdi), %r14
    movq 16(%rdi), %r13
    movq 24(%rdi), %r12
    movq 32(%rdi), %rbp
    movq 40(%rdi), %rbx
    
    // Restore stack pointer
    movq 48(%rdi), %rsp
    
    // Jump to saved RIP
    movq 56(%rdi), %rax
    jmp *%rax
    
    // context_restore does not return - it transfers control

// ============================================================================
// Context Setup (for new threads)
// ============================================================================

// void context_setup(Context* ctx, void* entry, void* stack)
// Sets up a new context that will start executing at entry point
.global context_setup
context_setup:
    // Arguments:
    // RDI = pointer to context structure
    // RSI = entry point (RIP)
    // RDX = stack pointer (RSP)
    
    // Zero all callee-saved registers (clean state)
    movq $0, 0(%rdi)      // R15
    movq $0, 8(%rdi)      // R14
    movq $0, 16(%rdi)     // R13
    movq $0, 24(%rdi)     // R12
    movq $0, 32(%rdi)     // RBP
    movq $0, 40(%rdi)     // RBX
    
    // Set up stack pointer
    movq %rdx, 48(%rdi)
    
    // Set up entry point
    movq %rsi, 56(%rdi)
    
    ret

// ============================================================================
// Switch Context (save current, restore new)
// ============================================================================

// ============================================================================
// Switch Context (stack-based, Pure 64)
// ============================================================================

// void switch_context(uint64_t* old_stack, uint64_t new_stack, uint64_t new_cr3)
// RDI = *u64 (pointer to old TCB's stack_ptr)
// RSI = u64  (new TCB's stack_ptr)
// RDX = u64  (new TCB's CR3)
.global switch_context
switch_context:
    /* 1. Save Callee-saved registers of the OLD thread onto its stack */
    pushq %rbp
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15

    /* 2. Save the current stack pointer into the OLD TCB */
    movq %rsp, (%rdi)

    /* 3. Switch Address Space if necessary (CR3) */
    movq %cr3, %rax
    cmpq %rax, %rdx
    je 1f
    movq %rdx, %cr3
1:

    /* 4. Load the NEW thread's stack pointer */
    movq %rsi, %rsp

    /* 5. Restore Callee-saved registers from the NEW thread's stack */
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbx
    popq %rbp

    retq
