#![no_std]
#![no_main]

#[path = "../../../bindings/rust/kozo_abi.rs"]
mod abi;

use abi::{K_HANDLE, K_OK, K_STATUS};

#[panic_handler]
fn panic(_info: &core::panic::PanicInfo) -> ! {
    loop {}
}

pub fn heartbeat_request() -> abi::K_STATUS {
    let mut payload = abi::HeartbeatPayload {
        sequence: 1,
        timestamp: 0,
        status_bits: abi::K_INVALID,
    };
    payload.sequence = payload.sequence.wrapping_add(1);

    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;
    let payload_handle = (&mut payload as *mut abi::HeartbeatPayload as usize) as abi::K_HANDLE;
    let _ = payload_handle;
    let _ = syscall;
    K_OK
}

#[no_mangle]
pub extern "C" fn core_service_entry(handle: K_HANDLE) -> K_STATUS {
    let _ = handle;
    heartbeat_request()
}
