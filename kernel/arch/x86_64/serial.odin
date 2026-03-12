package x86_64

import kozo_abi "../../../bindings/odin"

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

serial_init :: proc() -> kozo_abi.K_STATUS {
	disable_serial_interrupts()
	configure_serial_baud_rate()
	configure_serial_frame()
	return kozo_abi.K_OK
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

serial_write :: proc(s: string) -> kozo_abi.K_STATUS {
	for i in 0..<len(s) {
		write_serial_byte(s[i])
	}
	return kozo_abi.K_OK
}
