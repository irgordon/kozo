// KOZO Kernel - x86_64 Context Switch
// File Path: kernel/arch/x86_64/context.S
// Responsibility: Atomic Stack-Based Context Switching
// Scope: PURE 64 - Callee-saved registers and CR3 handling

.code64
.section .text

/**
 * switch_context(old_rsp_ptr, new_rsp, new_cr3)
 * * ABI Mapping:
 * RDI = *u64 (Pointer to the old TCB's stack_ptr field)
 * RSI = u64  (The stack_ptr of the new TCB)
 * RDX = u64  (The CR3/PML4 of the new address space)
 */
.global switch_context
switch_context:
    /* 1. Save Callee-saved registers of the OLD thread onto its current stack.
       The return address (RIP) is already at (%rsp) due to the 'call' instruction. */
    pushq %rbp
    pushq %rbx
    pushq %r12
    pushq %r13
    pushq %r14
    pushq %r15

    /* 2. Atomic Pointer Swap:
       Save the current %rsp into the memory location pointed to by RDI (the old TCB). */
    movq %rsp, (%rdi)

    /* 3. Address Space Transition:
       Only reload CR3 if the new CR3 (RDX) differs from the current one.
       This prevents unnecessary TLB flushes for threads sharing an address space. */
    movq %cr3, %rax
    cmpq %rax, %rdx
    je 1f
    movq %rdx, %cr3
1:

    /* 4. Restore Context:
       Switch %rsp to the new thread's stack. */
    movq %rsi, %rsp

    /* 5. Pop registers in EXACT reverse order of the initial pushes. */
    popq %r15
    popq %r14
    popq %r13
    popq %r12
    popq %rbx
    popq %rbp

    /* 6. Return to the RIP saved on the NEW thread's stack. */
    retq
