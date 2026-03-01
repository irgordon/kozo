// File Path: kernel/src/memory/cpio.zig
// Last Modified: 2026-03-01, 13:15:10.202
// Note: Minimal CPIO (newc format) Parser.

const std = @import("std");

pub const CpioHeader = extern struct {
    magic: [6]u8,
    ino: [8]u8,
    mode: [8]u8,
    uid: [8]u8,
    gid: [8]u8,
    nlink: [8]u8,
    mtime: [8]u8,
    filesize: [8]u8,
    devmajor: [8]u8,
    devminor: [8]u8,
    rdevmajor: [8]u8,
    rdevminor: [8]u8,
    namesize: [8]u8,
    check: [8]u8,
};

/// Find a file by name in the CPIO archive.
pub fn findFile(cpio_data: []const u8, name: []const u8) ?[]const u8 {
    var offset: usize = 0;
    while (offset + @sizeOf(CpioHeader) <= cpio_data.len) {
        const header = @as(*const CpioHeader, @ptrCast(cpio_data[offset..].ptr));
        if (!std.mem.eql(u8, header.magic[0..6], "070701")) break;

        const namesize = hexToU32(header.namesize) catch 0;
        const filesize = hexToU32(header.filesize) catch 0;

        // Safety: Ensure namesize is sane (including null terminator)
        if (namesize < 2) {
            offset = (offset + @sizeOf(CpioHeader) + namesize + 3) & ~@as(usize, 3);
            continue;
        }

        // Ensure we don't overflow
        if (offset + @sizeOf(CpioHeader) + namesize > cpio_data.len) break;

        const current_name = cpio_data[offset + @sizeOf(CpioHeader) .. offset + @sizeOf(CpioHeader) + namesize - 1];
        
        const next_offset_init = (offset + @sizeOf(CpioHeader) + namesize + 3) & ~@as(usize, 3);
        
        if (std.mem.eql(u8, current_name, name)) {
            if (next_offset_init + filesize > cpio_data.len) return null;
            return cpio_data[next_offset_init .. next_offset_init + filesize];
        }

        if (std.mem.eql(u8, current_name, "TRAILER!!!")) break;

        offset = next_offset_init;
        offset = (offset + filesize + 3) & ~@as(usize, 3);
    }
    return null;
}

fn hexToU32(hex: [8]u8) !u32 {
    // CPIO hex is exactly 8 characters, no leading 0x
    return std.fmt.parseInt(u32, &hex, 16);
}
