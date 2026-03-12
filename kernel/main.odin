package kernel

import abi "../bindings/odin"
import x86_64 "./arch/x86_64"

signal_kernel_heartbeat :: proc() -> abi.K_STATUS {
	status := x86_64.bootstrap()
	if status != abi.K_OK {
		return status
	}
	return syscall_dispatch(abi.K_SYSCALL_DEBUG_HEARTBEAT)
}

syscall_dispatch :: proc(id: abi.K_SYSCALL_ID) -> abi.K_STATUS {
	switch id {
	case abi.K_SYSCALL_NOP:
		return abi.K_OK
	case abi.K_SYSCALL_DEBUG_HEARTBEAT:
		return x86_64.serial_write("KOZO")
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
