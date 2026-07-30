# Getting Started

The fastest way to see KOZO work is to run the published ISO. Building from
source is a separate path for contributors and engineers.

## Path 1: Run the Published ISO

### 1. Open the Release

Open [KOZO v1.0.0](https://github.com/irgordon/kozo/releases/tag/v1.0.0).
Download `kozo.iso` and `SHA256SUMS`. The GitHub CLI can download the complete
six-file release set:

```bash
mkdir kozo-v1.0.0
gh release download v1.0.0 \
  --repo irgordon/kozo \
  --dir kozo-v1.0.0
```

### 2. Verify the Download

```bash
(
  cd kozo-v1.0.0
  shasum -a 256 -c SHA256SUMS
)
```

Every listed file must report `OK`. Stop if a checksum fails. Delete the
suspect download and download it again before running anything.

### 3. Run the Hosted ISO

Run this command from a KOZO source checkout so the bounded smoke script can
classify the serial output:

```bash
release_iso="$(cd kozo-v1.0.0 && pwd)/kozo.iso"
env \
  KOZO_BOOT_ISO="$release_iso" \
  KOZO_QEMU_BIN="$(command -v qemu-system-x86_64)" \
  scripts/qemu_smoke.sh
```

The QEMU lookup must return an executable path. If it is empty, install QEMU
or set `KOZO_QEMU_BIN` to the correct executable.

### 4. Recognize Success

A successful run reports:

```text
Outcome: pass
Blocker: none
Observed Markers: 41
Expected Marker: KOZO_RUNTIME_RETURN_OK
```

The ending serial sequence includes:

```text
KOZO_FIRST_CAPABILITY_OK
KOZO_RUNTIME_STATE_UPDATE_ENTER
KOZO_RUNTIME_STATE_UPDATE_OK
KOZO_SECOND_CAPABILITY_OK
KOZO_RUNTIME_RETURN_OK
```

KOZO then enters its terminal halt loop. The bounded smoke script may stop QEMU
at its timeout and observe exit status `124`. That is successful only when the
script already observed the complete ordered sequence through
`KOZO_RUNTIME_RETURN_OK`. An arbitrary timeout or empty serial log is a
failure.

See the [User Guide](USER_GUIDE.md) for what the output means and
[Troubleshooting](TROUBLESHOOTING.md) for failed checks.

## Path 2: Build KOZO From Source

### Requirements

The governed x86-64 path requires:

- Python 3;
- Odin;
- Rust and Cargo from `rust-toolchain.toml`;
- NASM and the LLVM linker executable `ld.lld`;
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

### Open the Repository

```bash
git clone https://github.com/irgordon/kozo.git
cd kozo
git status --short --branch
```

If you already have the repository, enter its root directory and confirm that
`git status` names the expected branch.

### Build the Boot Image

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

### Run KOZO in QEMU

```bash
env \
  KOZO_QEMU_BIN="$(command -v qemu-system-x86_64)" \
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

### Run Tests

```bash
python3 -m unittest discover -s tests
cargo check --manifest-path userspace/core_service/Cargo.toml
odin check kernel
```

### Run Full Verification

```bash
scripts/verify.sh
python3 -m json.tool artifacts/latest_verify.json
jq '{status, summary}' artifacts/latest_verify.json
git diff --check
```

Success prints `VERIFY: PASS`. The v1.0.0 release gate expects 67 checks, no
failures, QEMU outcome `pass`, and 41 ordered runtime markers.

### Build a Dry-Run Release Bundle

From a clean commit:

```bash
release_output="$(mktemp -d)"
scripts/build_release_candidate.sh \
  --version 1.0.0 \
  --output "$release_output"
```

The command runs governed verification against the committed tree, creates an
explicitly allowlisted archive, validates legal files and metadata, and writes
`SHA256SUMS`. It does not publish or tag anything. See the
[v1.0.0 release notes](../releases/v1.0.0.md) for the artifact list and limits.

### Inspect the Kernel Binary

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

## Expected Result

The source-built path must produce the same accepted runtime result: QEMU pass,
no blocker, 41 ordered markers, and final marker
`KOZO_RUNTIME_RETURN_OK`. Full verification must report 67 checks and no
failures.

## Common First-Run Problems

See [Troubleshooting](TROUBLESHOOTING.md) for missing QEMU, empty serial output,
Limine failures, stale generated reports, Taplo failures, and marker diagnosis.
