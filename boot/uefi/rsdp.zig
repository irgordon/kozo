// File Path: boot/uefi/rsdp.zig
// Last Modified: 2026-02-28, 21:40:12.882
const std = @import("std");
const uefi = std.os.uefi;

/// GUID for ACPI 2.0 Table (RSDP)
const ACPI_20_TABLE_GUID = uefi.Guid{
    .time_low = 0x8868e871,
    .time_mid = 0xe4f1,
    .time_high_and_version = 0x11d3,
    .clock_seq_high_and_reserved = 0xbc,
    .clock_seq_low = 0x22,
    .node = .{ 0x00, 0x80, 0xc7, 0x3c, 0x88, 0x81 },
};

pub fn findRsdp(st: *uefi.tables.SystemTable) ?u64 {
    var i: usize = 0;
    while (i < st.number_of_table_entries) : (i += 1) {
        const entry = st.configuration_table[i];
        if (std.mem.eql(u8, std.mem.asBytes(&entry.vendor_guid), std.mem.asBytes(&ACPI_20_TABLE_GUID))) {
            return @intFromPtr(entry.vendor_table);
        }
    }
    return null;
}