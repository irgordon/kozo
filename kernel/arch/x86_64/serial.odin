package x86_64

import abi "../../../bindings/odin"

COM1 :: u16(0x03f8)

divisor_latch_low_offset  :: u16(0)
divisor_latch_high_offset :: u16(1)
interrupt_enable_offset   :: u16(1)
fifo_control_offset       :: u16(2)
line_control_offset       :: u16(3)
modem_control_offset      :: u16(4)
line_status_offset        :: u16(5)

line_control_dlab :: u8(0x80)
line_control_8n1  :: u8(0x03)
fifo_enable_clear :: u8(0xC7)
modem_ready       :: u8(0x03)
transmit_ready    :: u8(0x20)

outb :: proc "contextless" (port: u16, value: u8) {
	asm(u16, u8) #side_effects #intel {
		"out dx, al",
		"N{dx},a"
	}(port, value)
}

inb :: proc "contextless" (port: u16) -> u8 {
	return asm(u16) -> u8 #side_effects #intel {
		"in al, dx",
		"={al},N{dx}"
	}(port)
}

disable_serial_interrupts :: proc() {
	outb(COM1 + interrupt_enable_offset, 0)
}

configure_serial_baud_rate :: proc() {
	outb(COM1 + line_control_offset, line_control_dlab)
	outb(COM1 + divisor_latch_low_offset, 3)
	outb(COM1 + divisor_latch_high_offset, 0)
}

configure_serial_frame :: proc() {
	outb(COM1 + line_control_offset, line_control_8n1)
	outb(COM1 + fifo_control_offset, fifo_enable_clear)
	outb(COM1 + modem_control_offset, modem_ready)
}

serial_init :: proc() -> abi.K_STATUS {
	disable_serial_interrupts()
	configure_serial_baud_rate()
	configure_serial_frame()
	return abi.K_OK
}

serial_transmitter_ready :: proc() -> bool {
	return (inb(COM1 + line_status_offset) & transmit_ready) != 0
}

wait_for_serial_transmitter :: proc() {
	for !serial_transmitter_ready() {
	}
}

write_serial_byte :: proc(value: u8) {
	wait_for_serial_transmitter()
	outb(COM1, value)
}

serial_write :: proc(s: string) -> abi.K_STATUS {
	for i in 0..<len(s) {
		write_serial_byte(s[i])
	}
	return abi.K_OK
}

write_serial_newline :: proc() {
	write_serial_byte('\r')
	write_serial_byte('\n')
}

write_serial_hex_digit :: proc(value: u8) {
	hex_digits := "0123456789ABCDEF"
	write_serial_byte(hex_digits[value])
}

write_serial_hex_u64 :: proc(value: u64) {
	for shift in 0..<16 {
		bit_shift := u64(60 - shift*4)
		nibble := u8((value >> bit_shift) & 0xF)
		write_serial_hex_digit(nibble)
	}
}

write_serial_hex_u32 :: proc(value: u32) {
	for shift in 0..<8 {
		bit_shift := u32(28 - shift*4)
		nibble := u8((value >> bit_shift) & 0xF)
		write_serial_hex_digit(nibble)
	}
}

log_heartbeat_payload :: proc(payload: abi.Heartbeat_Payload) -> abi.K_STATUS {
	serial_write("HB seq=")
	write_serial_hex_u64(payload.sequence)
	serial_write(" ts=")
	write_serial_hex_u64(payload.timestamp)
	serial_write(" status=")
	write_serial_hex_u32(payload.status_bits)
	write_serial_newline()
	return abi.K_OK
}

serial_log_debug_heartbeat_recv :: proc(sequence: u64) -> abi.K_STATUS {
	serial_write("SYSCALL[DEBUG_HEARTBEAT] Recv Seq: 0x")
	write_serial_hex_u64(sequence)
	write_serial_newline()
	return abi.K_OK
}

serial_log_debug_heartbeat_time :: proc(timestamp: u64) -> abi.K_STATUS {
	serial_write("SYSCALL[DEBUG_HEARTBEAT] New Time: 0x")
	write_serial_hex_u64(timestamp)
	write_serial_newline()
	return abi.K_OK
}
