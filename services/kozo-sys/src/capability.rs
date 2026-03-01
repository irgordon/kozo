//! KOZO-SYS: Capability Handle Types
//! File Path: services/kozo-sys/src/capability.rs
//! Responsibility: Type-safe capability handles preventing category errors
//! Security: Rust's type system ensures Thread capabilities aren't used as Memory Frames
//! Architecture: Zero-cost abstractions - compile-time checks only

use crate::abi::{CapType, Error, Rights};
use crate::syscall;
use core::marker::PhantomData;

/// Generic capability handle (slot index in CNode)
/// 
/// This is a bare index. Prefer typed handles (CNodeHandle, etc.) for safety.
#[derive(Debug, Clone, Copy, PartialEq, Eq, PartialOrd, Ord, Hash)]
pub struct CapHandle(pub usize);

impl CapHandle {
    /// Null/invalid capability handle
    pub const NULL: Self = CapHandle(0);

    /// Check if handle is null
    pub const fn is_null(&self) -> bool {
        self.0 == 0
    }

    /// Get raw slot index
    pub const fn raw(&self) -> usize {
        self.0
    }

    /// Create from raw index (unsafe - caller must ensure validity)
    pub const unsafe fn from_raw(slot: usize) -> Self {
        CapHandle(slot)
    }

    /// Delete this capability from current CNode
    pub fn delete(self) -> Result<(), Error> {
        syscall::sys_cap_delete(self.0)
    }

    /// Verify this capability is of expected type (runtime check)
    /// 
    /// Note: Kernel tracks types, but this requires a syscall to verify.
    /// Prefer static typing via typed handles when possible.
    pub fn verify_type(self, expected: CapType) -> Result<(), Error> {
        // In production: query kernel for type
        // Genesis: assume caller knows what they're doing
        let _ = expected;
        Ok(())
    }
}

impl Default for CapHandle {
    fn default() -> Self {
        CapHandle::NULL
    }

    /// Create new typed capability from untyped memory
    /// 
    /// # Type Parameters
    /// * `T` - The type of capability to create (determines return type)
    pub fn retype_from<T: TypedCapability>(
        untyped: UntypedHandle,
        size_bits: usize,
    ) -> Result<T, Error> {
        let slot = find_free_slot()?; // Would need actual implementation
        syscall::sys_retype(untyped.0 .0, T::cap_type(), slot, size_bits)?;
        T::from_handle(CapHandle(slot))
    }

    /// Find a free slot in current CNode
    fn find_free_slot() -> Result<usize, Error> {
        // Genesis: hardcoded slot allocation
        // Production: query kernel or manage free list
        Ok(10) // Placeholder
    }
}

// =============================================================================
// TYPED CAPABILITY TRAIT
// =============================================================================

/// Trait for type-safe capability handles
/// 
/// Implement this for each capability type to get typed constructors and methods.
pub trait TypedCapability: Sized + Copy {
    /// The kernel capability type enum variant
    fn cap_type() -> CapType;

    /// Create from generic handle (fails if type mismatch)
    fn from_handle(handle: CapHandle) -> Result<Self, Error>;

    /// Convert to generic handle (for syscalls expecting any capability)
    fn to_handle(self) -> CapHandle;
}

// =============================================================================
// SPECIALIZED HANDLE TYPES
// =============================================================================

/// CNode (Capability Node) handle - table of capabilities
/// 
/// CNodies are the only objects that can contain other capabilities.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct CNodeHandle(CapHandle);

impl TypedCapability for CNodeHandle {
    fn cap_type() -> CapType {
        CapType::Cnode
    }

    fn from_handle(handle: CapHandle) -> Result<Self, Error> {
        // In production: verify handle points to actual CNode
        Ok(CNodeHandle(handle))
    }

    fn to_handle(self) -> CapHandle {
        self.0
    }
}

impl CNodeHandle {
    /// Create new CNode from untyped memory
    /// 
    /// # Arguments
    /// * `untyped` - Source untyped capability
    /// * `size_bits` - log2(number of slots), e.g., 12 = 4096 slots
    pub fn create(untyped: UntypedHandle, size_bits: usize) -> Result<Self, Error> {
        let slot = Self::allocate_slot()?;
        syscall::sys_retype(untyped.0 .0, CapType::Cnode, slot, size_bits)?;
        Ok(CNodeHandle(CapHandle(slot)))
    }

    /// Insert capability into this CNode
    /// 
    /// # Safety
    /// Target slot must be empty (NULL)
    pub fn insert(&self, slot: usize, src: impl TypedCapability) -> Result<(), Error> {
        syscall::sys_cap_transfer(
            src.to_handle().raw(),
            self.0.raw() as u64, // CNode badge identifies target
            slot,
            Rights::RIGHT_READ | Rights::RIGHT_WRITE | Rights::RIGHT_GRANT,
        )
    }

    /// Remove capability from this CNode
    pub fn remove(&self, slot: usize) -> Result<CapHandle, Error> {
        // In production: need syscall to move out
        // Genesis: simplified
        Ok(CapHandle(slot))
    }

    fn allocate_slot() -> Result<usize, Error> {
        // Would query kernel for free slot
        Ok(5)
    }
}

/// Endpoint handle - IPC communication channel
/// 
/// Endpoints are unidirectional message queues used for service communication.
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct EndpointHandle(CapHandle);

impl TypedCapability for EndpointHandle {
    fn cap_type() -> CapType {
        CapType::Endpoint
    }

    fn from_handle(handle: CapHandle) -> Result<Self, Error> {
        Ok(EndpointHandle(handle))
    }

    fn to_handle(self) -> CapHandle {
        self.0
    }
}

impl EndpointHandle {
    /// Create new endpoint
    pub fn create(untyped: UntypedHandle) -> Result<Self