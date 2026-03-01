// File Path: kernel/src/thread.zig
// Last Modified: 2026-03-01, 10:15:22.402
// Note: Refined TCB - Implements O(1) Free List and Stack-based Context.

const std = @import("std");
const cap = @import("capability.zig");

/// Thread states
pub const ThreadState = enum {
    FREE,       // TCB available
    SUSPENDED,  // Created but not runnable
    RUNNABLE,   // Ready to run
    RUNNING,    // Currently executing
    BLOCKED,    // Waiting for event
};

/// Thread Control Block - minimal viable for 64-bit preemption
pub const TCB = struct {
    // Current stack pointer of the thread (pointing to its Context on the stack)
    stack_ptr: u64,
    
    // Virtual Memory Space (CR3)
    cr3: u64,
    
    // Capability Root (CNode)
    cspace: u64,

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
            .cr3 = 0,
            .cspace = 0,
            .state = .FREE,
            .tid = 0,
            .priority = 128,
            .next = null,
        };
    }

    /// Prepare a thread's stack for initial execution.
    /// This simulates a context switch save by pushing the entry point and registers.
    pub fn setupThread(self: *TCB, entry: u64, stack_top: u64) void {
        // ABI Alignment: Ensure stack_top is 16-byte aligned
        const aligned_stack = (stack_top & ~@as(u64, 15));
        
        // Return address (RIP)
        var sp = aligned_stack - 8;
        @as(*u64, @ptrFromInt(sp)).* = entry;

        // Pushed by switch_context: rbp, rbx, r12, r13, r14, r15
        // Total 6 registers (48 bytes)
        sp -= 8 * 6;
        const regs: [*]u64 = @ptrFromInt(sp);
        @memset(regs[0..6], 0); // Clear R15 through RBP
        
        self.stack_ptr = sp;
        self.state = .RUNNABLE;
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
    
    tcb.state = .SUSPENDED;
    tcb.next = null;
    return tcb;
}

/// Free a TCB back to the list in O(1) time.
pub fn freeTCB(tcb: *TCB) void {
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
