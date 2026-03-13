package kozo_abi

KOZO_ABI_VERSION :: 1

K_HANDLE :: u64

K_STATUS :: u32
K_OK : K_STATUS : 0
K_INVALID : K_STATUS : 1
K_DENIED : K_STATUS : 2

K_SYSCALL_ID :: u32
K_SYSCALL_NOP : K_SYSCALL_ID : 0
K_SYSCALL_DEBUG_HEARTBEAT : K_SYSCALL_ID : 1

Heartbeat_Payload :: struct #align(8) {
	sequence: u64,
	timestamp: u64,
	status_bits: u32,
}
