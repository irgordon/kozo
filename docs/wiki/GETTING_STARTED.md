# Getting Started

This guide first runs the published prerelease ISO, then shows how to build
KOZO from source.

## Run the Downloaded Prerelease ISO

Download all six assets for `v1.0.0-rc.1` into an empty directory:

```bash
mkdir kozo-v1.0.0-rc.1
cd kozo-v1.0.0-rc.1
gh release download v1.0.0-rc.1 \
  --repo irgordon/kozo \
  --dir .
```

Verify the downloaded files:

```bash
shasum -a 256 -c SHA256SUMS
```

Run the downloaded ISO from a KOZO source checkout so the existing bounded
smoke script can classify the result:

```bash
KOZO_BOOT_ISO="/absolute/path/to/download/kozo.iso" scripts/qemu_smoke.sh
```

Use the actual absolute download path for `KOZO_BOOT_ISO`. A successful run
reports `Outcome: pass`, `Blocker: none`, 41 ordered markers, and
`KOZO_RUNTIME_RETURN_OK` as the final marker. See the
[current release status](../releases/v1.0.0-rc.1-status.md) for the accepted
artifact hashes and limits.

## Build KOZO from Source

## Requirements

The governed x86-64 path requires:

- Python 3;
- Odin;
- Rust and Cargo from `rust-toolchain.toml`;
- NASM and LLVM `lld`;
- Limine 12.3.3 and its BIOS/UEFI image files;
- xorriso;
- `qemu-system-x86_64`;
- `jq`;
- GNU or LLVM `nm` and `objdump`;
- `aarch64-elf-readelf` for portable ELF metadata inspection on macOS.

Check the main tools:

```bash
python3 --version
odin version
cargo --version
nasm -v
ld.lld --version
xorriso -version
qemu-system-x86_64 --version
jq --version
```

See [Boot Tooling](../BOOT_TOOLING.md) for the pinned Limine source and
checksum. If a tool is outside `PATH`, set the supported `LIMINE_DIR`, `LIMINE`,
`XORRISO`, or `KOZO_QEMU_BIN` environment variable before running the scripts.

## Open the Repository

```bash
git clone https://github.com/irgordon/kozo.git
cd kozo
git status --short --branch
```

If you already have the repository, enter its root directory and confirm that
`git status` names the expected branch.

## Build the Boot Image

```bash
scripts/build_boot_image.sh
```

Success creates:

```text
artifacts/runtime/boot_image/kozo.iso
artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
artifacts/runtime/kernel_elf_report.json
```

If required ISO tools are missing, the script fails closed or records the exact
local tooling failure. Do not edit generated package metadata to bypass it.

## Run KOZO in QEMU

```bash
scripts/qemu_smoke.sh
```

The QEMU command resolves its binary in this order: `KOZO_QEMU_BIN`, `PATH`,
then the Homebrew package prefix when available. A successful run writes serial
evidence under `artifacts/runtime/`.

Inspect the result:

```bash
jq '{outcome, blocker_category, expected_marker, observed_markers}' artifacts/runtime/qemu_smoke.metadata.json
```

Expected values are `outcome: "pass"`, no blocker, and an ordered marker list
ending in `KOZO_RUNTIME_RETURN_OK`.

## Run Tests

```bash
python3 -m unittest discover -s tests
cargo check --manifest-path userspace/core_service/Cargo.toml
odin check kernel
```

## Run Full Verification

```bash
scripts/verify.sh
python3 -m json.tool artifacts/latest_verify.json
jq '{status, summary}' artifacts/latest_verify.json
git diff --check
```

Success prints `VERIFY: PASS`. The v0.8.9 acceptance gate expects 67 checks,
no failures, QEMU outcome `pass`, and 41 ordered runtime markers.

## Build a Dry-Run Release Bundle

From a clean commit:

```bash
scripts/build_release_candidate.sh \
  --version 1.0.0-rc.1 \
  --output /tmp/kozo-release-candidate
```

The command runs governed verification against the committed tree, creates an
explicitly allowlisted archive, validates legal files and metadata, and writes
`SHA256SUMS`. It does not publish or tag anything. It is not the command that
created the existing GitHub prerelease. See the
[release notes](../releases/v1.0.0-rc.1.md) for the artifact list and limits.

## Inspect the Kernel Binary

Use the AArch64-prefixed tool only for ELF metadata:

```bash
aarch64-elf-readelf -h -l -S -s artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
```

Use the host `nm` and `objdump` for x86-64 symbols and instructions:

```bash
nm -n artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
objdump -d artifacts/runtime/boot_image/image-root/boot/kozo/kozo-kernel.elf
```

Do not use AArch64-prefixed assemblers, linkers, `nm`, or `objdump` for the
x86-64 kernel.

## Common First-Run Problems

See [Troubleshooting](TROUBLESHOOTING.md) for missing QEMU, empty serial output,
Limine failures, stale generated reports, Taplo failures, and marker diagnosis.
