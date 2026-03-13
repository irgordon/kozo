package kernel

import abi "../bindings/odin"
import x86_64 "./arch/x86_64"

heartbeat_payload_from_handle :: proc(handle: abi.K_HANDLE) -> ^abi.Heartbeat_Payload {
	ptr := cast(rawptr)(uintptr(handle))
	return cast(^abi.Heartbeat_Payload)(ptr)
}

signal_kernel_heartbeat :: proc() -> abi.K_STATUS {
	status := x86_64.bootstrap()
	if status != abi.K_OK {
		return status
	}
	payload := abi.Heartbeat_Payload{
		sequence = 1,
		timestamp = 0,
		status_bits = u32(abi.K_INVALID),
	}
	handle := abi.K_HANDLE(uintptr(&payload))
	return syscall_dispatch(abi.K_SYSCALL_DEBUG_HEARTBEAT, handle)
}

syscall_dispatch :: proc(id: abi.K_SYSCALL_ID, payload_handle: abi.K_HANDLE) -> abi.K_STATUS {
	switch id {
	case abi.K_SYSCALL_NOP:
		return abi.K_OK
	case abi.K_SYSCALL_DEBUG_HEARTBEAT:
		payload := heartbeat_payload_from_handle(payload_handle)
		payload.timestamp = x86_64.read_timestamp()
		payload.status_bits = u32(abi.K_OK)
		return x86_64.log_heartbeat_payload(payload^)
	}
	return abi.K_INVALID
}

park_cpu_forever :: proc() {
	for {
		x86_64.halt()
	}
}

main :: proc() {
	status := signal_kernel_heartbeat()
	if status != abi.K_OK {
		park_cpu_forever()
	}
	park_cpu_forever()
}
