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
    let syscall: abi::K_SYSCALL_ID = abi::K_SYSCALL_DEBUG_HEARTBEAT;
    let _ = syscall;
    abi::K_OK
}

#[no_mangle]
pub extern "C" fn core_service_entry(handle: K_HANDLE) -> K_STATUS {
    let _ = handle;
    heartbeat_request()
}
