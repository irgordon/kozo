//! Boot Information Frame parsing for the Init Service.

#[repr(C)]
#[derive(Debug)]
pub struct BootInfo {
    /// Memory base for the initial Untyped pool
    pub untyped_base: usize,
    /// Total size of available physical memory handed to Init
    pub untyped_size: usize,
    /// Pointer to the root CNode slots (initially in-place)
    pub root_cnode_ptr: usize,
}

impl BootInfo {
    /// SLA Principle: Provide a clean interface to the hardware-provided boot data.
    pub fn print_summary(&self) {
        // This would use a debug syscall to print to the serial console
    }
}