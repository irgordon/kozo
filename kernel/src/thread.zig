// File Path: kernel/src/thread.zig
// Last Modified: 2026-03-01, 10:15:22.402
// Note: Refined TCB - Implements O(1) Free List and Stack-based Context.

const std = @import("std");
const cap = @import("capability.zig");

/// Thread states
pub const ThreadState = enum {
    FREE,           // TCB available
    SUSPENDED,      // Created but not runnable
    RUNNABLE,       // Ready to run
    RUNNING,        // Currently executing
    BLOCKED,        // Waiting for event
    BLOCKED_SEND,   // Waiting for receiver
    BLOCKED_RECV,   // Waiting for sender
    BLOCKED_REPLY,  // Waiting for reply
};

pub const ThreadQueue = struct {
    head: ?*TCB = null,
    tail: ?*TCB = null,

    pub fn init() ThreadQueue {
        return .{};
    }

    pub fn enqueue(self: *ThreadQueue, tcb: *TCB) void {
        tcb.next = null;
        if (self.tail) |t| {
            t.next = tcb;
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
        tcb.next = null;
        return tcb;
    }
};

/// Thread Control Block - minimal viable for 64-bit preemption
pub const TCB = struct {
    // Current saved stack pointer (pointing to its Context on the kernel stack)
    stack_ptr: u64,

    // Top of the kernel stack (for TSS.rsp0)
    stack_top: u64,
    
    // Virtual Memory Space (CR3)
    cr3: u64,
    
    // Capability Root (CNode)
    cspace: u64,
    root_cnode: ?*cap.CNode,

    // State management
    state: ThreadState,
    tid: u32,
    priority: u8,
    
    // Links for run queue and free list
    next: ?*TCB,
    
    /// Initialize a TCB to FREE state
    pub fn init(self: *TCB) void {
        self.* = .{
            .stack_ptr = 0,
            .stack_top = 0,
            .cr3 = 0,
            .cspace = 0,
            .root_cnode = null,
            .state = .FREE,
            .tid = 0,
            .priority = 128,
            .next = null,
        };
    }

    /// Prepare a thread's stack for initial execution.
    /// @param entry: Entry point (RIP)
    /// @param user_stack: User stack top (RSP)
    /// @param kernel_stack: Kernel stack top (for exceptions/syscalls)
    /// @param is_user: Whether to use Ring 3 segments
    pub fn setupThread(self: *TCB, entry: u64, user_stack: u64, kernel_stack: u64, is_user: bool) void {
        self.stack_top = kernel_stack;
        
        const cs: u64 = if (is_user) 0x23 else 0x08;
        const ss: u64 = if (is_user) 0x1B else 0x10;
        
        // ABI Alignment: Ensure kernel stack is 16-byte aligned
        var sp = kernel_stack & ~@as(u64, 15);
        
        // --- Part A: The 'iretq' Frame (Pushed by us to prime the return) ---
        // RIP, CS, RFLAGS, RSP, SS
        sp -= 8; @as(*u64, @ptrFromInt(sp)).* = ss;
        sp -= 8; @as(*u64, @ptrFromInt(sp)).* = user_stack;
        sp -= 8; @as(*u64, @ptrFromInt(sp)).* = 0x0202;        // RFLAGS (Interrupts enabled)
        sp -= 8; @as(*u64, @ptrFromInt(sp)).* = cs;
        sp -= 8; @as(*u64, @ptrFromInt(sp)).* = entry;

        // --- Part B: The 'switch_context' Frame (Matches assembly pop sequence) ---
        sp -= 8 * 6;
        const regs: [*]u64 = @ptrFromInt(sp);
        @memset(regs[0..6], 0); // Clear R15 through RBP
        
        self.stack_ptr = sp;
        self.state = .RUNNABLE;
    }

    pub fn getCapability(self: *TCB, index: usize) ?*cap.CapSlot {
        if (self.root_cnode) |cnode| {
            return cnode.get(index) catch null;
        }
        return null;
    }
};

// --- TCB Pool and O(1) Allocation ---
const MAX_THREADS = 256;
var tcb_pool: [MAX_THREADS]TCB = undefined;
var free_list_head: ?*TCB = null;
var tcb_initialized = false;

/// Initialize TCB pool and build the Free List.
pub fn init() void {
    if (tcb_initialized) return;
    
    // Build the initial free list O(1) chained
    for (0..MAX_THREADS) |i| {
        const tcb = &tcb_pool[i];
        tcb.init();
        tcb.tid = @intCast(i);
        
        if (i < MAX_THREADS - 1) {
            tcb.next = &tcb_pool[i + 1];
        } else {
            tcb.next = null;
        }
    }
    free_list_head = &tcb_pool[0];
    tcb_initialized = true;
}

/// Allocate a free TCB in O(1) time.
pub fn allocTCB() ?*TCB {
    const tcb = free_list_head orelse return null;
    free_list_head = tcb.next;
    
    const tid = tcb.tid;
    tcb.init();
    tcb.tid = tid;
    tcb.state = .SUSPENDED;
    return tcb;
}

/// Return a TCB to the free list.
pub fn freeTCB(tcb: *TCB) void {
    // Safety: Zero critical fields to prevent zombie scheduling
    tcb.stack_ptr = 0;
    tcb.cr3 = 0;
    tcb.root_cnode = null;
    tcb.state = .FREE;
    
    tcb.next = free_list_head;
    free_list_head = tcb;
}

// --- Current Thread Tracking ---
var current_thread: ?*TCB = null;

pub fn getCurrent() ?*TCB {
    return current_thread;
}

pub fn setCurrent(tcb: ?*TCB) void {
    current_thread = tcb;
}

pub fn getTCBByTid(tid: u32) ?*TCB {
    if (tid >= MAX_THREADS) return null;
    const tcb = &tcb_pool[tid];
    if (tcb.state == .FREE) return null;
    return tcb;
}

/// Helper to get the SyscallFrame of a blocked thread.
/// Assumes the thread was blocked via a syscall or interrupt.
pub fn getSyscallFrame(self: *TCB) *const anyopaque {
    // switch_context context is 6 regs (48 bytes)
    return @as(*anyopaque, @ptrFromInt(self.stack_ptr + 48));
}
