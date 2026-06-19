#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TASKS_DIR="$ROOT/tasks"
ARTIFACTS_DIR="$ROOT/artifacts"
LOG_DIR="$ARTIFACTS_DIR/logs"

TODO_JSON="$TASKS_DIR/todo.json"
RUNTIME_JSON="$TASKS_DIR/runtime.json"
LESSONS_JSON="$TASKS_DIR/lessons.json"
VERIFY_JSON="$ARTIFACTS_DIR/latest_verify.json"
RUST_TOOLCHAIN_FILE="$ROOT/rust-toolchain.toml"
RUST_TARGET="x86_64-unknown-none"

EMPTY_TREE="4b825dc642cb6eb9a060e54bf8d69288fbee4904"
KERNEL_BUILD_CHECK="$ARTIFACTS_DIR/kernel-build-check"
RUNTIME_SMOKE_LOG="$ARTIFACTS_DIR/runtime/runtime_smoke.log"
RUNTIME_SMOKE_METADATA="$ARTIFACTS_DIR/runtime/runtime_smoke.metadata.json"
BOOT_BLOCKER_REPORT="$ARTIFACTS_DIR/runtime/boot_blocker_report.json"
BOOT_IMAGE_PACKAGE_METADATA="$ARTIFACTS_DIR/runtime/boot_image/package_metadata.json"
QEMU_SMOKE_LOG="$ARTIFACTS_DIR/runtime/qemu_smoke.log"
QEMU_SMOKE_STDERR_LOG="$ARTIFACTS_DIR/runtime/qemu_smoke.stderr.log"
QEMU_SMOKE_METADATA="$ARTIFACTS_DIR/runtime/qemu_smoke.metadata.json"
VERIFY_TMP=""

mkdir -p "$LOG_DIR" "$ARTIFACTS_DIR"

cleanup() {
  [[ -n "${VERIFY_TMP:-}" && -f "$VERIFY_TMP" ]] && rm -f "$VERIFY_TMP"
  rm -f "$KERNEL_BUILD_CHECK"
}

trap cleanup EXIT

fail() {
  printf "FAIL: %s\n" "$*" >&2
  exit 1
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "Missing command: $1"
}

need_file() {
  [[ -f "$1" ]] || fail "Required file missing: $1"
}

read_rust_toolchain() {
  python3 - "$RUST_TOOLCHAIN_FILE" <<'PY'
import sys
import tomllib
from pathlib import Path

data = tomllib.loads(Path(sys.argv[1]).read_text())
print(data["toolchain"]["channel"])
PY
}

require_pinned_rust_versions() {
  local expected_cargo_version="cargo $RUST_TOOLCHAIN"
  local expected_rustc_version="rustc $RUST_TOOLCHAIN"
  local cargo_version
  local rustc_version

  cargo_version="$("$PINNED_CARGO" --version)"
  rustc_version="$("$PINNED_RUSTC" --version)"

  [[ "$cargo_version" == "$expected_cargo_version"* ]] || fail "Expected $expected_cargo_version at $PINNED_CARGO, got: $cargo_version"
  [[ "$rustc_version" == "$expected_rustc_version"* ]] || fail "Expected $expected_rustc_version at $PINNED_RUSTC, got: $rustc_version"
}

require_pinned_rust_toolchain() {
  if ! PINNED_RUSTC="$(rustup which --toolchain "$RUST_TOOLCHAIN" rustc 2>/dev/null)"; then
    fail "Pinned Rust toolchain unavailable: $RUST_TOOLCHAIN. Install with: rustup toolchain install $RUST_TOOLCHAIN"
  fi
  if ! PINNED_CARGO="$(rustup which --toolchain "$RUST_TOOLCHAIN" cargo 2>/dev/null)"; then
    fail "Pinned Rust cargo unavailable: $RUST_TOOLCHAIN. Install with: rustup toolchain install $RUST_TOOLCHAIN"
  fi
}

require_pinned_rust_target() {
  if ! rustup target list --installed --toolchain "$RUST_TOOLCHAIN" | grep -Fx "$RUST_TARGET" >/dev/null; then
    fail "Pinned Rust target unavailable: $RUST_TARGET for $RUST_TOOLCHAIN. Install with: rustup target add --toolchain $RUST_TOOLCHAIN $RUST_TARGET"
  fi
}

run_pinned_cargo() {
  local rust_bin_dir

  rust_bin_dir="$(dirname "$PINNED_RUSTC")"

  env RUSTC="$PINNED_RUSTC" PATH="$rust_bin_dir:$PATH" "$PINNED_CARGO" "$@"
}

repo_head_ref() {
  if git -C "$ROOT" rev-parse --verify HEAD >/dev/null 2>&1; then
    printf "HEAD"
    return
  fi

  printf "%s" "$EMPTY_TREE"
}

filter_generated_changes() {
  local status=0

  grep -vE '(^|/)__pycache__/|\.pyc$|^artifacts/latest_verify\.json$|^artifacts/logs/|^artifacts/kernel.*\.o$|^artifacts/kernel-build-check$' || status=$?

  if [[ "$status" -eq 1 ]]; then
    return 0
  fi

  return "$status"
}

collect_changed_files() {
  local head_ref
  head_ref="$(repo_head_ref)"

  {
    git -C "$ROOT" diff --name-only --diff-filter=ACMRT -- . || true
    git -C "$ROOT" diff --name-only --cached --diff-filter=ACMRT "$head_ref" -- . || true
    git -C "$ROOT" ls-files --others --exclude-standard || true
  } | sed '/^$/d' | filter_generated_changes | sort -u
}

collect_evidence_files() {
  local files=(
    "$LOG_DIR/odin-check.log"
    "$LOG_DIR/odin-build.log"
    "$LOG_DIR/cargo-check.log"
    "$LOG_DIR/nm-kernel.log"
    "$RUNTIME_SMOKE_LOG"
    "$RUNTIME_SMOKE_METADATA"
    "$BOOT_BLOCKER_REPORT"
    "$BOOT_IMAGE_PACKAGE_METADATA"
    "$QEMU_SMOKE_LOG"
    "$QEMU_SMOKE_STDERR_LOG"
    "$QEMU_SMOKE_METADATA"
  )

  local file
  for file in "${files[@]}"; do
    [[ -f "$file" ]] && printf "%s\n" "${file#"$ROOT/"}"
  done
}

run_logged_command() {
  local log_file=$1
  shift

  if ! "$@" >"$log_file" 2>&1; then
    cat "$log_file" >&2
    fail "Command failed: $*"
  fi
}

build_kernel_object_artifact() {
  local log_file="$LOG_DIR/nm-kernel.log"
  local object_files=()

  find "$ARTIFACTS_DIR" -maxdepth 1 -type f -name 'kernel*.o' -delete

  if ! odin build "$ROOT/kernel" -build-mode:obj "-out:$ARTIFACTS_DIR/kernel.o" >"$log_file" 2>&1; then
    cat "$log_file" >&2
    fail "Command failed: odin build $ROOT/kernel -build-mode:obj -out:$ARTIFACTS_DIR/kernel.o"
  fi

  shopt -s nullglob
  object_files=("$ARTIFACTS_DIR"/kernel*.o)
  shopt -u nullglob

  if [[ "${#object_files[@]}" -eq 0 ]]; then
    cat "$log_file" >&2
    fail "Object build did not emit any kernel*.o files under $ARTIFACTS_DIR"
  fi

  if ! nm -g "${object_files[@]}" >>"$log_file" 2>&1; then
    cat "$log_file" >&2
    fail "Command failed: nm -g ${object_files[*]}"
  fi
}

validate_verify_artifact() {
  local verify_path=$1

  ROOT="$ROOT" python3 - "$verify_path" <<'PY'
import json
import sys
from pathlib import Path

from harness.validators_impl.schema import validate_named_document

verify_path = Path(sys.argv[1])
verify = json.loads(verify_path.read_text())

validate_named_document("latest_verify", verify)

print(verify["status"])
PY
}

write_verify_artifact_atomically() {
  local verify_output=$1

  VERIFY_TMP="$(mktemp "$ARTIFACTS_DIR/latest_verify.XXXXXX.tmp")"
  printf "%s\n" "$verify_output" >"$VERIFY_TMP"

  local status
  status="$(validate_verify_artifact "$VERIFY_TMP")"

  mv "$VERIFY_TMP" "$VERIFY_JSON"
  VERIFY_TMP=""

  printf "%s\n" "$status"
}

need_cmd python3
need_cmd git
need_cmd odin
need_cmd rustup
need_cmd nm
need_file "$RUST_TOOLCHAIN_FILE"
RUST_TOOLCHAIN="$(read_rust_toolchain)"
require_pinned_rust_toolchain
require_pinned_rust_versions
require_pinned_rust_target

need_file "$TODO_JSON"
need_file "$RUNTIME_JSON"
need_file "$LESSONS_JSON"

RUN_ID="verify-$(date -u +"%Y%m%dT%H%M%SZ")"
GENERATED_AT="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"

CHANGED_FILES_TEXT="$(collect_changed_files)"

run_logged_command "$LOG_DIR/odin-check.log" \
  odin check "$ROOT/kernel"

run_logged_command "$LOG_DIR/odin-build.log" \
  odin build "$ROOT/kernel" -target:freestanding_amd64_sysv -build-mode:obj "-out:$KERNEL_BUILD_CHECK"

run_logged_command "$LOG_DIR/cargo-check.log" \
  run_pinned_cargo check --manifest-path "$ROOT/userspace/core_service/Cargo.toml" --target "$RUST_TARGET"

build_kernel_object_artifact

"$ROOT/scripts/runtime_smoke.sh"
"$ROOT/scripts/build_boot_image.sh"
"$ROOT/scripts/qemu_smoke.sh"
"$ROOT/scripts/boot_blocker_report.sh"

EVIDENCE_FILES_TEXT="$(collect_evidence_files)"

VERIFY_OUTPUT="$(
ROOT="$ROOT" \
CHANGED_FILES_TEXT="$CHANGED_FILES_TEXT" \
EVIDENCE_FILES_TEXT="$EVIDENCE_FILES_TEXT" \
RUN_ID="$RUN_ID" \
GENERATED_AT="$GENERATED_AT" \
python3 - <<'PY'
import json
import os
from pathlib import Path

from harness.aggregator import run_aggregator

root = Path(os.environ["ROOT"])
changed_files = [
    line
    for line in os.environ.get("CHANGED_FILES_TEXT", "").splitlines()
    if line
]
evidence_files = [
    line
    for line in os.environ.get("EVIDENCE_FILES_TEXT", "").splitlines()
    if line
]

todo = json.loads((root / "tasks" / "todo.json").read_text())
runtime = json.loads((root / "tasks" / "runtime.json").read_text())
lessons = json.loads((root / "tasks" / "lessons.json").read_text())

bundle = {
    "todo": todo,
    "runtime": runtime,
    "lessons": lessons,
    "root_dir": str(root),
}

artifact = run_aggregator(
    artifact_bundle=bundle,
    changed_files=changed_files,
    evidence_files=evidence_files,
    run_id=os.environ["RUN_ID"],
    generated_at=os.environ["GENERATED_AT"],
)

print(json.dumps(artifact, indent=2))
PY
)"

STATUS="$(write_verify_artifact_atomically "$VERIFY_OUTPUT")"

printf "%s\n" "$VERIFY_OUTPUT"

if [[ "$STATUS" == "fail" ]]; then
  echo "VERIFY: FAIL"
  exit 1
fi

if [[ "$STATUS" != "pass" ]]; then
  fail "Unexpected verification status: $STATUS"
fi

echo "VERIFY: PASS"
exit 0
