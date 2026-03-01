//! KOZO Kernel - Thread Control Blocks
//! File Path: kernel/src/thread.zig
//! Responsibility: Thread state management, minimal viable TCB
//! Scope: One run queue, one current thread, deterministic switch

const std = @import("std");
const cap = @import("capability.zig");

/// Callee-saved register context (System V AMD64 ABI)
/// Layout must match context.S
pub const Context = extern struct {
    r15: u64,
    r14: u64,
    r13: u64,
    r12: u64,
    rbp: u64,
    rbx: u64,
    rsp: u64,  // Stack pointer
    rip: u64,  // Instruction pointer
    
    pub fn init() Context {
        return std.mem.zeroes(Context);
    }
};

/// Thread states
pub const ThreadState = enum {
    FREE,       // TCB available
    SUSPENDED,  // Created but not runnable
    RUNNABLE,   // Ready to run
    RUNNING,    // Currently executing
    BLOCKED,    // Waiting for event
};

/// Thread queue (for IPC endpoints, scheduler, etc.)
pub const ThreadQueue = struct {
    head: ?*TCB,
    tail: ?*TCB,
    
    pub fn init() ThreadQueue {
        return .{ .head = null, .tail = null };
    }
    
    pub fn enqueue(self: *ThreadQueue, tcb: *TCB) void {
        tcb.next = null;
        if (self.tail) |tail| {
            tail.next = tcb;
        } else {
            self.head = tcb;
        }
        self.tail = tcb;
    }
    
    pub fn dequeue(self: *ThreadQueue) ?*TCB {
        const tcb = self.head orelse return null;
        self.head = tcb.next;
        if (self.head == null) {
            self.tail = null;
        }
        return tcb;
    }
};

/// IPC state
pub const IpcState = enum {
    IDLE,
    WAITING_CALL,
    WAITING_REPLY,
    RECEIVED_CALL,
    RECEIVED_ASYNC,
    ERROR,
};

/// Thread Control Block - minimal viable
pub const TCB = struct {
    // Execution context (callee-saved registers)
    context: Context,
    
    // State
    state: ThreadState,
    ipc_state: IpcState,
    
    // Scheduling
    tid: u32,
    priority: u8,
    
    // Links for run queue
    next: ?*TCB,
    prev: ?*TCB,
    
    // Capability context
    root_cnode: cap.CNode,
    vspace: cap.CapSlot,
    
    // IPC
    ipc_buffer: [512]u8,
    ipc_msg_len: usize,
    ipc_endpoint: usize,
    ipc_caller: ?*TCB,
    ipc_badge: u64,
    
    /// Initialize a TCB to FREE state
    pub fn init(self: *TCB) void {
        self.* = .{
            .context = Context.init(),
            .state = .FREE,
            .ipc_state = .IDLE,
            .tid = 0,
            .priority = 128,
            .next = null,
            .prev = null,
            .root_cnode = undefined,
            .vspace = undefined,
            .ipc_buffer = undefined,
            .ipc_msg_len = 0,
            .ipc_endpoint = 0,
            .ipc_caller = null,
            .ipc_badge = 0,
        };
    }
};

// Static pool of TCBs (no heap allocation in kernel)
const MAX_THREADS = 256;
var tcb_pool: [MAX_THREADS]TCB = undefined;
var tcb_initialized = false;

/// Initialize TCB pool
pub fn init() void {
    if (tcb_initialized) return;
    
    for (&tcb_pool) |*tcb| {
        tcb.init();
    }
    tcb_initialized = true;
}

/// Allocate a free TCB
pub fn allocTCB() ?*TCB {
    for (&tcb_pool, 0..) |*tcb, i| {
        if (tcb.state == .FREE) {
            tcb.init();
            tcb.tid = @intCast(i);
            return tcb;
        }
    }
    return null;
}

/// Free a TCB back to pool
pub fn freeTCB(tcb: *TCB) void {
    tcb.state = .FREE;
    tcb.next = null;
    tcb.prev = null;
}

/// Get TCB by TID
pub fn getTCB(tid: u32) ?*TCB {
    if (tid >= MAX_THREADS) return null;
    const tcb = &tcb_pool[tid];
    if (tcb.state == .FREE) return null;
    return tcb;
}

/// Current thread (set by scheduler)
var current_thread: ?*TCB = null;

/// Get currently executing thread
pub fn getCurrent() ?*TCB {
    return current_thread;
}

/// Set current thread (called by scheduler during switch)
pub fn setCurrent(tcb: ?*TCB) void {
    current_thread = tcb;
}

/// Idle thread context (for when no other thread runs)
var idle_context: Context = undefined;

/// Get idle context for initial setup
pub fn getIdleContext() *Context {
    return &idle_context;
}
