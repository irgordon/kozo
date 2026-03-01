// KOZO Kernel - x86_64 IPC Fast Path (STUB)
// File Path: kernel/arch/x86_64/ipc.S
// Responsibility: Direct context switch IPC (NOT YET IMPLEMENTED)
// Scope: STUB - IPC will use scheduler for now

// IPC fast path requires:
// 1. Direct switch without scheduler involvement
// 2. Preserved message registers
// 3. Reply capability setup
// 
// This is optimization, not required for basic functionality.
// Current IPC uses: syscall -> kernel -> scheduler -> context_switch

.code64
.section .text

// Stub symbols to satisfy linker
.global ipc_fast_call_stub
ipc_fast_call_stub:
    // Not implemented - use slow path through scheduler
    ret

.global ipc_fast_reply_stub  
ipc_fast_reply_stub:
    // Not implemented - use slow path through scheduler
    ret
