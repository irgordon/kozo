#!/usr/bin/env bash
set -euo pipefail

rootDir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
versionFile="$rootDir/release/version.txt"
canonicalVersionPattern='^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$'
verifiedReleaseManifest=""
requestedVersion=""
outputDir=""
workDir=""
verificationRoot=""
releaseStageDirectory=""
releaseBundleName=""
releaseArchivePath=""
releaseCommit=""
releaseBranch=""
buildTimeUtc=""
verificationStatus=""
verificationCheckCount=""
qemuOutcome=""
qemuBlocker=""
markerCount=""
checksumCommand=()

fail() {
  printf "FAIL: %s\n" "$*" >&2
  exit 1
}

parse_arguments() {
  while [[ "$#" -gt 0 ]]; do
    case "$1" in
      --version)
        [[ "$#" -ge 2 ]] || fail "--version requires a value"
        requestedVersion="$2"
        shift 2
        ;;
      --output)
        [[ "$#" -ge 2 ]] || fail "--output requires a value"
        outputDir="$2"
        shift 2
        ;;
      *) fail "Unknown argument: $1" ;;
    esac
  done

  [[ -n "$requestedVersion" ]] || fail "--version is required"
  [[ -n "$outputDir" ]] || fail "--output is required"
}

read_release_version() {
  [[ -f "$versionFile" ]] || fail "Version authority missing: $versionFile"
  releaseVersion="$(tr -d '[:space:]' <"$versionFile")"
  [[ "$releaseVersion" == "$requestedVersion" ]] || fail "Requested version does not match release/version.txt"
  [[ "$releaseVersion" =~ $canonicalVersionPattern ]] || fail "Release version is not canonical"
}

ensure_output_directory_empty() {
  mkdir -p "$outputDir"
  [[ -z "$(find "$outputDir" -mindepth 1 -print -quit)" ]] || fail "Output directory must be empty"
}

ensure_clean_repository() {
  local status
  status="$(git -C "$rootDir" status --porcelain --untracked-files=all)"
  [[ -z "$status" ]] || fail "Repository must be clean before release packaging"
}

prepare_release_workspace() {
  workDir="$(mktemp -d "${TMPDIR:-/tmp}/kozo-release-candidate.XXXXXX")"
  workDir="$(cd "$workDir" && pwd -P)"
  verificationRoot="$workDir/source"
  verifiedReleaseManifest="$verificationRoot/release/release_files.v1.json"
  releaseBundleName="kozo-v$releaseVersion"
  releaseStageDirectory="$workDir/stage/$releaseBundleName"
  mkdir -p "$verificationRoot" "$releaseStageDirectory"
  git -C "$rootDir" archive HEAD | tar -xf - -C "$verificationRoot"
}

run_governed_verification() {
  (
    cd "$verificationRoot"
    scripts/verify.sh
  )
}

read_verification_result() {
  local result
  result="$(python3 - "$verificationRoot" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
verify = json.loads((root / "artifacts/latest_verify.json").read_text())
qemu = json.loads((root / "artifacts/runtime/qemu_smoke.metadata.json").read_text())
blocker = qemu.get("blocker_category") or "none"
print(
    verify["status"],
    verify["summary"]["total_checks"],
    qemu["outcome"],
    blocker,
    len(qemu["observed_markers"]),
)
PY
)"
  read -r verificationStatus verificationCheckCount qemuOutcome qemuBlocker markerCount <<<"$result"
}

ensure_verification_passed() {
  [[ "$verificationStatus" == "pass" ]] || fail "Verification did not pass"
  [[ "$verificationCheckCount" == "67" ]] || fail "Expected 67 verification checks"
  [[ "$qemuOutcome" == "pass" ]] || fail "QEMU smoke did not pass"
  [[ "$qemuBlocker" == "none" ]] || fail "QEMU smoke reported a blocker"
  [[ "$markerCount" == "41" ]] || fail "Expected 41 runtime markers"
}

copy_release_files() {
  python3 - "$verificationRoot" "$releaseStageDirectory" "$verifiedReleaseManifest" <<'PY'
import json
import shutil
import sys
from pathlib import Path, PurePosixPath

source_root = Path(sys.argv[1])
stage_root = Path(sys.argv[2])
manifest = json.loads(Path(sys.argv[3]).read_text())

def checked_destination(value):
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts:
        raise SystemExit(f"unsafe release destination: {value}")
    return stage_root.joinpath(*path.parts)

seen = set()
for item in manifest["required_files"]:
    source = source_root / item["source"]
    destination = checked_destination(item["destination"])
    if item["destination"] in seen or not source.is_file():
        raise SystemExit(f"invalid required release file: {item}")
    seen.add(item["destination"])
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)

for item in manifest["required_directories"]:
    source = source_root / item["source"]
    destination = checked_destination(item["destination"])
    if item["destination"] in seen or not source.is_dir():
        raise SystemExit(f"invalid required release directory: {item}")
    seen.add(item["destination"])
    shutil.copytree(source, destination)
PY
}

write_release_metadata() {
  python3 - "$releaseStageDirectory/release_metadata.json" <<PY
import json
from pathlib import Path

metadata = {
    "metadata_version": 1,
    "version": "$releaseVersion",
    "display_version": "v$releaseVersion",
    "commit": "$releaseCommit",
    "branch": "$releaseBranch",
    "build_time_utc": "$buildTimeUtc",
    "verification_status": "$verificationStatus",
    "verification_check_count": int("$verificationCheckCount"),
    "qemu_outcome": "$qemuOutcome",
    "qemu_blocker": "$qemuBlocker",
    "marker_count": int("$markerCount"),
    "license_set": ["MIT", "Apache-2.0"],
    "core_service_license": "MIT",
    "artifact_files": [
        "artifacts/kozo.iso",
        "artifacts/kozo-kernel.elf",
        "evidence/latest_verify.json",
    ],
    "checksum_algorithm": "SHA-256",
    "published": False,
}
Path("$releaseStageDirectory/release_metadata.json").write_text(
    json.dumps(metadata, indent=2) + "\n"
)
PY
}

select_checksum_command() {
  if command -v sha256sum >/dev/null 2>&1; then
    checksumCommand=(sha256sum)
  elif command -v shasum >/dev/null 2>&1; then
    checksumCommand=(shasum -a 256)
  else
    fail "No SHA-256 checksum command is available"
  fi
}

write_checksum_file() {
  local baseDir=$1
  local checksumPath=$2
  shift 2
  : >"$checksumPath"
  for relativePath in "$@"; do
    local digest
    digest="$("${checksumCommand[@]}" "$baseDir/$relativePath" | awk '{print $1}')"
    printf "%s  %s\n" "$digest" "$relativePath" >>"$checksumPath"
  done
}

write_internal_checksums() {
  write_checksum_file "$releaseStageDirectory" "$releaseStageDirectory/SHA256SUMS" \
    "artifacts/kozo.iso" \
    "artifacts/kozo-kernel.elf" \
    "evidence/latest_verify.json"
}

create_release_archive() {
  releaseArchivePath="$outputDir/$releaseBundleName.tar.xz"
  tar -cJf "$releaseArchivePath" -C "$workDir/stage" "$releaseBundleName"
}

write_output_artifacts() {
  cp "$releaseStageDirectory/artifacts/kozo.iso" "$outputDir/kozo.iso"
  cp "$releaseStageDirectory/artifacts/kozo-kernel.elf" "$outputDir/kozo-kernel.elf"
  cp "$releaseStageDirectory/evidence/latest_verify.json" "$outputDir/latest_verify.json"
  cp "$releaseStageDirectory/release_metadata.json" "$outputDir/release_metadata.json"
  cp -R "$releaseStageDirectory/evidence" "$outputDir/evidence"
  write_checksum_file "$outputDir" "$outputDir/SHA256SUMS" \
    "$(basename "$releaseArchivePath")" \
    "kozo.iso" \
    "kozo-kernel.elf" \
    "latest_verify.json" \
    "release_metadata.json"
}

inspect_release_archive() {
  local inspectRoot="$workDir/inspect"
  mkdir -p "$inspectRoot"
  tar -tf "$releaseArchivePath" >"$workDir/archive-files.txt"
  tar -xf "$releaseArchivePath" -C "$inspectRoot"
  python3 - \
    "$inspectRoot/$releaseBundleName" \
    "$verifiedReleaseManifest" \
    "$releaseVersion" \
    "$releaseCommit" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
manifest = json.loads(Path(sys.argv[2]).read_text())
release_version = sys.argv[3]
release_commit = sys.argv[4]
paths = [path for path in root.rglob("*") if path.is_file()]
for path in paths:
    if any(part in manifest["prohibited_names"] for part in path.parts):
        raise SystemExit(f"prohibited release path: {path}")
    if any(path.name.startswith(prefix) for prefix in manifest["prohibited_prefixes"]):
        raise SystemExit(f"prohibited release file: {path}")
    if any(path.name.endswith(suffix) for suffix in manifest["prohibited_suffixes"]):
        raise SystemExit(f"prohibited release file: {path}")
for item in manifest["required_files"]:
    if not (root / item["destination"]).is_file():
        raise SystemExit(f"missing release file: {item['destination']}")
for item in manifest["required_directories"]:
    if not (root / item["destination"]).is_dir():
        raise SystemExit(f"missing release directory: {item['destination']}")
metadata = json.loads((root / "release_metadata.json").read_text())
expected = {
    "version": release_version,
    "display_version": f"v{release_version}",
    "commit": release_commit,
    "verification_status": "pass",
    "verification_check_count": 67,
    "qemu_outcome": "pass",
    "qemu_blocker": "none",
    "marker_count": 41,
    "published": False,
}
for field, value in expected.items():
    if metadata.get(field) != value:
        raise SystemExit(f"invalid release metadata field: {field}")
PY
  cmp "$verificationRoot/LICENSE" "$inspectRoot/$releaseBundleName/LICENSE"
  cmp "$verificationRoot/LICENSE-MIT" "$inspectRoot/$releaseBundleName/LICENSE-MIT"
  cmp "$verificationRoot/LICENSE-APACHE" "$inspectRoot/$releaseBundleName/LICENSE-APACHE"
}

validate_checksum_file() {
  local baseDir=$1
  local checksumPath=$2
  while read -r expected relativePath; do
    local actual
    actual="$("${checksumCommand[@]}" "$baseDir/$relativePath" | awk '{print $1}')"
    [[ "$actual" == "$expected" ]] || fail "Checksum mismatch: $relativePath"
  done <"$checksumPath"
}

report_outputs() {
  printf "Release bundle: v%s\n" "$releaseVersion"
  printf "Commit: %s\n" "$releaseCommit"
  printf "Verification: %s (%s checks)\n" "$verificationStatus" "$verificationCheckCount"
  printf "QEMU: %s (blocker: %s, markers: %s)\n" "$qemuOutcome" "$qemuBlocker" "$markerCount"
  printf "Archive: %s\n" "$releaseArchivePath"
  printf "Checksums: %s/SHA256SUMS\n" "$outputDir"
  printf "Published: false\n"
}

cleanup() {
  if [[ -n "$workDir" && -d "$workDir" ]]; then
    rm -rf "$workDir"
  fi
}

main() {
  parse_arguments "$@"
  read_release_version
  ensure_output_directory_empty
  ensure_clean_repository
  prepare_release_workspace
  run_governed_verification
  read_verification_result
  ensure_verification_passed
  copy_release_files
  write_release_metadata
  select_checksum_command
  write_internal_checksums
  create_release_archive
  write_output_artifacts
  inspect_release_archive
  validate_checksum_file "$releaseStageDirectory" "$releaseStageDirectory/SHA256SUMS"
  validate_checksum_file "$outputDir" "$outputDir/SHA256SUMS"
  report_outputs
}

trap cleanup EXIT
releaseCommit="$(git -C "$rootDir" rev-parse HEAD)"
releaseBranch="$(git -C "$rootDir" branch --show-current)"
buildTimeUtc="$(date -u +"%Y-%m-%dT%H:%M:%SZ")"
main "$@"
