// File Path: kernel/src/scheduler.zig
// Last Modified: 2026-03-01, 10:20:15.110
// Note: Refined Scheduler - Implements stack-based context switching and CR3 handling.

const std = @import("std");
const thread = @import("thread.zig");

// External assembly function
// void switch_context(uint64_t* old_stack, uint64_t new_stack, uint64_t new_cr3)
extern fn switch_context(current_stack: *u64, next_stack: u64, next_cr3: u64) void;

/// Run queue - simple singly-linked list via TCB.next
var runqueue_head: ?*thread.TCB = null;
var runqueue_tail: ?*thread.TCB = null;

/// Initialize scheduler
pub fn init() void {
    runqueue_head = null;
    runqueue_tail = null;
    thread.init();  // Initialize TCB pool
}

/// Add thread to run queue (append to tail)
pub fn enqueue(tcb: *thread.TCB) void {
    tcb.state = .RUNNABLE;
    tcb.next = null;
    
    if (runqueue_tail) |tail| {
        tail.next = tcb;
    } else {
        runqueue_head = tcb;
    }
    runqueue_tail = tcb;
}

/// Remove and return next runnable thread
pub fn dequeue() ?*thread.TCB {
    const tcb = runqueue_head orelse return null;
    
    runqueue_head = tcb.next;
    if (runqueue_head == null) {
        runqueue_tail = null;
    }
    
    tcb.next = null;
    return tcb;
}

/// Helper to create and enqueue a new thread
pub fn spawnThread(entry: u64, stack_top: u64, cr3: u64, priority: u8) !*thread.TCB {
    const tcb = thread.allocTCB() orelse return error.NoTCB;
    tcb.cr3 = cr3;
    tcb.priority = priority;
    tcb.setupThread(entry, stack_top);
    enqueue(tcb);
    return tcb;
}

/// Yield CPU to next runnable thread
pub fn yield() void {
    const current = thread.getCurrent() orelse return;
    const next = dequeue() orelse return; // Stay on current if nothing else is ready

    current.state = .RUNNABLE;
    enqueue(current);

    next.state = .RUNNING;
    thread.setCurrent(next);

    // Perform the stack-based swap and CR3 update
    switch_context(&current.stack_ptr, next.stack_ptr, next.cr3);
}

/// Switch to specific thread (e.g., for IPC return or first bootstrap)
pub fn switchTo(next: *thread.TCB) void {
    const current = thread.getCurrent();
    
    next.state = .RUNNING;
    thread.setCurrent(next);

    if (current) |p| {
        switch_context(&p.stack_ptr, next.stack_ptr, next.cr3);
    } else {
        // Bootstrap: First thread execution
        // We manually switch address space and stack
        if (next.cr3 != 0) {
            asm volatile ("mov %[cr3], %%cr3" : : [cr3] "r" (next.cr3) : "memory");
        }
        
        asm volatile (
            \\movq %[rsp], %%rsp
            \\popq %%r15
            \\popq %%r14
            \\popq %%r13
            \\popq %%r12
            \\popq %%rbx
            \\popq %%rbp
            \\retq
            :
            : [rsp] "r" (next.stack_ptr)
            : "memory"
        );
        unreachable;
    }
}

/// Block current thread (mark BLOCKED and switch away)
pub fn block() void {
    const current = thread.getCurrent() orelse return;
    current.state = .BLOCKED;
    
    const next = dequeue() orelse @panic("Blocked last thread");
    next.state = .RUNNING;
    thread.setCurrent(next);
    
    switch_context(&current.stack_ptr, next.stack_ptr, next.cr3);
}

/// Unblock thread
pub fn unblock(tcb: *thread.TCB) void {
    if (tcb.state == .BLOCKED) {
        enqueue(tcb);
    }
}
