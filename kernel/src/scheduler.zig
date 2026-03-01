//! KOZO Kernel - Minimal Scheduler
//! File Path: kernel/src/scheduler.zig
//! Responsibility: One run queue, one current thread, deterministic switch
//! Scope: NO preemption, NO fairness, NO IPC fast path - just switch on syscall return

const std = @import("std");
const thread = @import("thread.zig");

// External assembly function
extern fn context_switch(current: *thread.Context, next: *thread.Context) void;

/// Run queue - simple singly-linked list
/// Head is next to run, tail is where we append
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
        // Append to existing queue
        tail.next = tcb;
        runqueue_tail = tcb;
    } else {
        // First thread in queue
        runqueue_head = tcb;
        runqueue_tail = tcb;
    }
}

/// Remove and return next runnable thread
pub fn dequeue() ?*thread.TCB {
    const tcb = runqueue_head orelse return null;
    
    runqueue_head = tcb.next;
    if (runqueue_tail == tcb) {
        // Was the only thread
        runqueue_tail = null;
    }
    
    tcb.next = null;
    return tcb;
}

/// Get next thread to run (don't remove from queue)
pub fn peek() ?*thread.TCB {
    return runqueue_head;
}

/// Yield CPU to next runnable thread
/// Called on syscall return or explicit yield
pub fn yield() void {
    const current = thread.getCurrent();
    
    // Get next thread to run
    const next = dequeue();
    if (next == null) {
        // No other thread to run - continue with current
        return;
    }
    
    // If current exists and is runnable, put it back in queue
    if (current) |curr| {
        if (curr.state == .RUNNING or curr.state == .RUNNABLE) {
            curr.state = .RUNNABLE;
            enqueue(curr);
        }
    }
    
    // Switch to next thread
    switchTo(next.?);
}

/// Switch to specific thread (used by thread resume, IPC return)
pub fn switchTo(next: *thread.TCB) void {
    const current = thread.getCurrent();
    
    // Mark next as running
    next.state = .RUNNING;
    
    // Update current thread pointer
    const prev = current;
    thread.setCurrent(next);
    
    // If there's a previous thread, context switch
    // If not (first switch), we need different handling
    if (prev) |p| {
        // Save current state to prev's context, restore from next's context
        context_switch(&p.context, &next.context);
        // When we return here, it's because someone switched back to us
    } else {
        // First thread - just restore its context
        // This shouldn't happen in normal operation
        asm volatile (
            \\movq %[rsp], %rsp
            \\jmp *%[rip]
            :
            : [rsp] "r" (next.context.rsp),
              [rip] "r" (next.context.rip)
            : "memory"
        );
        unreachable;
    }
}

/// Block current thread (remove from run queue, mark BLOCKED)
pub fn block(tcb: *thread.TCB) void {
    // Remove from run queue if present
    // For now, just mark as blocked
    tcb.state = .BLOCKED;
    
    // If this is current thread, we MUST switch away
    if (thread.getCurrent() == tcb) {
        const next = dequeue();
        if (next) |n| {
            thread.setCurrent(n);
            n.state = .RUNNING;
            // Context switch to next
            context_switch(&tcb.context, &n.context);
        } else {
            // No other thread - this is a problem
            // For now, panic
            @panic("Blocked last thread");
        }
    }
}

/// Unblock thread (make runnable again)
pub fn unblock(tcb: *thread.TCB) void {
    if (tcb.state == .BLOCKED) {
        enqueue(tcb);
    }
}

/// Force suspend a running thread
pub fn forceSuspend(tcb: *thread.TCB) void {
    if (tcb.state == .RUNNING) {
        tcb.state = .SUSPENDED;
        // If it's current, we need to switch away
        if (thread.getCurrent() == tcb) {
            yield();
        }
    }
}

/// Remove from run queue (for priority changes)
pub fn removeFromQueue(tcb: *thread.TCB) void {
    // Simple removal - scan and unlink
    // Not efficient, but minimal
    
    if (runqueue_head == tcb) {
        runqueue_head = tcb.next;
        if (runqueue_tail == tcb) {
            runqueue_tail = null;
        }
        tcb.next = null;
        return;
    }
    
    // Scan for it
    var curr = runqueue_head;
    while (curr) |c| {
        if (c.next == tcb) {
            c.next = tcb.next;
            if (runqueue_tail == tcb) {
                runqueue_tail = c;
            }
            tcb.next = null;
            return;
        }
        curr = c.next;
    }
}

/// Reprioritize thread (after priority change)
pub fn reprioritize(tcb: *thread.TCB) void {
    // For now, just remove and re-add
    // In a real scheduler we'd use a proper priority queue
    if (tcb.state == .RUNNABLE) {
        removeFromQueue(tcb);
        enqueue(tcb);
    }
}

/// Check if scheduler has work to do
pub fn hasWork() bool {
    return runqueue_head != null;
}

/// Get count of runnable threads
pub fn runnableCount() usize {
    var count: usize = 0;
    var curr = runqueue_head;
    while (curr) |c| {
        count += 1;
        curr = c.next;
    }
    return count;
}
