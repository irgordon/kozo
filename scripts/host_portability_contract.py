from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.text_evidence import write_canonical_text


EXPECTED_FOCUSED_TESTS = 34
GOVERNED_RELEASE_INPUTS = ("LICENSE", "LICENSE-APACHE", "LICENSE-MIT")
REQUIRED_LICENSES = set(GOVERNED_RELEASE_INPUTS)
PROHIBITED_NAMES = {".git", ".env", "target", "__pycache__"}
OBJECT_FORM_PATTERN = re.compile(
    r"^KOZO_ODIN_OBJECT_OUTPUT_FORM=(exact|dot_o|dot_obj)$", re.MULTILINE
)


class PortabilityContractError(RuntimeError):
    pass


@dataclass
class ContractExecutionState:
    environment: dict
    stage: str = "environment_capture"

    def enter(self, stage: str) -> None:
        self.stage = stage
        print(f"KOZO_PORTABILITY_STAGE={stage} RESULT=START")

    def finish(self) -> None:
        self.stage = "complete"


@dataclass(frozen=True)
class ReleaseInputSource:
    path: str
    blob_id: str
    size: int
    sha256: str


def main() -> int:
    arguments = parse_arguments()
    output_path = arguments.output.resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    state = begin_contract_evidence(output_path)
    try:
        with tempfile.TemporaryDirectory(
            prefix="kozo portability ", dir=output_path.parent
        ) as temporary_directory:
            evidence = execute_build_contract(ROOT, Path(temporary_directory), state)
    except Exception as error:
        evidence = build_failure_evidence(state, error)
        write_evidence(output_path, evidence)
        raise
    write_evidence(output_path, evidence)
    print(json.dumps(evidence, indent=2))
    return 0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the governed host build contract")
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def begin_contract_evidence(output_path: Path) -> ContractExecutionState:
    state = ContractExecutionState(capture_environment_evidence())
    write_evidence(output_path, build_pending_evidence(state))
    return state


def execute_build_contract(
    root: Path,
    work_directory: Path,
    state: ContractExecutionState,
) -> dict:
    state.enter("required_tools")
    validate_required_tools()
    state.enter("task_schema")
    validate_json_and_task_documents(root)
    state.enter("python_tests")
    focused_count, full_count = run_python_contract(root)
    state.enter("build_checks")
    run_build_checks(root)
    state.enter("release_inputs")
    release_sources = validate_release_input_sources(root)
    state.enter("release_inventory")
    inventory, release_inputs = validate_release_inventory(
        root,
        work_directory,
        release_sources,
    )
    state.enter("checksums")
    checksums = validate_checksum_round_trip(root, work_directory)
    state.enter("odin_object")
    object_result = build_real_odin_object(root, work_directory)
    state.finish()
    return build_evidence(
        state,
        focused_count,
        full_count,
        inventory,
        release_inputs,
        checksums,
        object_result,
    )


def validate_required_tools() -> None:
    for command in ("bash", "odin", "rustc", "cargo", "git"):
        require_command(command)
    report_step("required_tools")


def validate_json_and_task_documents(root: Path) -> None:
    documents = (
        "tasks/todo.json",
        "tasks/runtime.json",
        "tasks/lessons.json",
        "release/release_files.v1.json",
        "schemas/latest_verify.schema.json",
        "schemas/agent_context.schema.json",
    )
    for relative_path in documents:
        json.loads((root / relative_path).read_text())
    validate_task_schemas(root)
    report_step("task_schema")


def validate_task_schemas(root: Path) -> None:
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))
    from harness.validators_impl.schema import validate_named_document

    validate_named_document("todo", load_json(root / "tasks/todo.json"))
    validate_named_document("runtime", load_json(root / "tasks/runtime.json"))


def run_python_contract(root: Path) -> tuple[int, int]:
    focused_count = count_named_tests("tests.test_odin_object_build")
    require(focused_count == EXPECTED_FOCUSED_TESTS, "focused test count changed")
    run_command([sys.executable, "-m", "unittest", "tests.test_odin_object_build"], root)
    full_count = count_discovered_tests(root / "tests")
    run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"], root)
    report_step("python_tests")
    return focused_count, full_count


def run_build_checks(root: Path) -> None:
    bash = require_command("bash")
    run_command([bash, "-n", "scripts/build_odin_object.sh"], root)
    run_command([bash, "-n", "scripts/build_release_candidate.sh"], root)
    run_command(["odin", "check", "kernel"], root)
    run_command(
        [
            "cargo",
            "check",
            "--manifest-path",
            "userspace/core_service/Cargo.toml",
            "--target",
            "x86_64-unknown-none",
        ],
        root,
    )
    report_step("build_checks")


def validate_release_inventory(
    root: Path,
    work_directory: Path,
    release_sources: tuple[ReleaseInputSource, ...],
) -> tuple[dict, dict]:
    manifest = load_json(root / "release/release_files.v1.json")
    entries = manifest_entries(manifest)
    destinations = [entry["destination"] for entry in entries]
    require(len(destinations) == len(set(destinations)), "duplicate release destination")
    validate_destinations(destinations)
    validate_license_entries(root, entries)
    validate_prohibited_entries(entries, manifest)
    portable_entries = portable_release_entries(entries)
    staging = work_directory / "release staging with spaces"
    stage_release_sources(root, staging, portable_entries)
    release_inputs = validate_staged_release_inputs(root, staging, release_sources)
    write_host_release_metadata(root, staging)
    staged_file_count = validate_staged_inventory(root, staging, portable_entries)
    validate_staged_paths(staging, manifest)
    validate_host_release_metadata(root, staging)
    report_step("release_inventory")
    inventory = {
        "entry_count": len(entries),
        "portable_entry_count": len(portable_entries),
        "runtime_generated_entry_count": len(entries) - len(portable_entries),
        "staged_file_count": staged_file_count,
        "required_file_count": len(manifest["required_files"]),
        "required_directory_count": len(manifest["required_directories"]),
        "metadata_result": "PASS",
        "final_archive_contract": "NOT_EXECUTED",
    }
    return inventory, release_inputs


def validate_release_input_sources(root: Path) -> tuple[ReleaseInputSource, ...]:
    validate_release_input_attributes(root)
    sources = tuple(load_release_input_source(root, path) for path in GOVERNED_RELEASE_INPUTS)
    report_step("release_inputs")
    return sources


def validate_release_input_attributes(root: Path) -> None:
    attributes = read_release_input_attributes(root)
    for path in GOVERNED_RELEASE_INPUTS:
        require(
            attributes.get((path, "text")) == "set",
            f"release input text attribute missing: {path}",
        )
        require(
            attributes.get((path, "eol")) == "lf",
            f"release input LF attribute missing: {path}",
        )


def read_release_input_attributes(root: Path) -> dict[tuple[str, str], str]:
    result = run_command(
        ["git", "check-attr", "text", "eol", "--", *GOVERNED_RELEASE_INPUTS],
        root,
    )
    attributes: dict[tuple[str, str], str] = {}
    for line in result.stdout.splitlines():
        path, name, value = line.split(": ", 2)
        attributes[(path, name)] = value
    return attributes


def load_release_input_source(root: Path, relative_path: str) -> ReleaseInputSource:
    source = root / relative_path
    require(
        source.is_file() and not source.is_symlink(),
        f"invalid release input: {relative_path}",
    )
    source_bytes = source.read_bytes()
    blob_bytes = git_blob_bytes(root, relative_path)
    validate_release_input_bytes(source_bytes, blob_bytes, relative_path)
    return ReleaseInputSource(
        path=relative_path,
        blob_id=git_blob_id(root, relative_path),
        size=len(source_bytes),
        sha256=sha256_bytes(source_bytes),
    )


def validate_release_input_bytes(
    source_bytes: bytes,
    blob_bytes: bytes,
    relative_path: str,
) -> None:
    validate_canonical_lf_bytes(blob_bytes, relative_path)
    require(
        source_bytes == blob_bytes,
        f"release input differs from HEAD blob: {relative_path}",
    )


def validate_canonical_lf_bytes(content: bytes, relative_path: str) -> None:
    require(content, f"empty governed release input: {relative_path}")
    require(b"\r" not in content, f"non-LF governed release input: {relative_path}")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise PortabilityContractError(f"non-UTF-8 governed release input: {relative_path}") from error


def validate_staged_release_inputs(
    root: Path,
    staging: Path,
    sources: tuple[ReleaseInputSource, ...],
) -> dict:
    files = [validate_staged_release_input(root, staging, source) for source in sources]
    return {
        "authority": "git_blob",
        "checkout_policy": "text eol=lf",
        "comparison_scope": "governed_license_inputs",
        "comparison_dimensions": ["path", "size", "sha256"],
        "result": "PASS",
        "files": files,
    }


def validate_staged_release_input(
    root: Path,
    staging: Path,
    source: ReleaseInputSource,
) -> dict:
    staged = staging / source.path
    require(
        staged.is_file() and not staged.is_symlink(),
        f"missing staged release input: {source.path}",
    )
    source_bytes = (root / source.path).read_bytes()
    staged_bytes = staged.read_bytes()
    require(
        len(staged_bytes) == source.size,
        f"staged release input size mismatch: {source.path}",
    )
    require(
        staged_bytes == source_bytes,
        f"staged release input bytes mismatch: {source.path}",
    )
    staged_sha256 = sha256_bytes(staged_bytes)
    require(
        staged_sha256 == source.sha256,
        f"staged release input hash mismatch: {source.path}",
    )
    return {
        "path": source.path,
        "blob_id": source.blob_id,
        "size": source.size,
        "sha256": source.sha256,
        "staged_size": len(staged_bytes),
        "staged_sha256": staged_sha256,
    }


def manifest_entries(manifest: dict) -> list[dict]:
    return [*manifest["required_files"], *manifest["required_directories"]]


def portable_release_entries(entries: list[dict]) -> list[dict]:
    return [
        entry
        for entry in entries
        if PurePosixPath(entry["source"]).parts[0] != "artifacts"
    ]


def stage_release_sources(root: Path, staging: Path, entries: list[dict]) -> None:
    staging.mkdir()
    for entry in entries:
        source = root.joinpath(*PurePosixPath(entry["source"]).parts)
        destination = staging.joinpath(*PurePosixPath(entry["destination"]).parts)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_file():
            shutil.copy2(source, destination)
        else:
            require(source.is_dir(), f"missing release source: {entry['source']}")
            shutil.copytree(source, destination)


def write_host_release_metadata(root: Path, staging: Path) -> None:
    metadata = {
        "metadata_version": 1,
        "evidence_class": "host_portability",
        "version": (root / "release/version.txt").read_text().strip(),
        "commit": os.environ.get("GITHUB_SHA", git_head()),
        "published": False,
        "final_archive_contract": "NOT_EXECUTED",
    }
    (staging / "host_build_metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n"
    )


def validate_staged_inventory(
    root: Path,
    staging: Path,
    entries: list[dict],
) -> int:
    expected = expected_staged_files(root, entries)
    actual = {
        path.relative_to(staging).as_posix()
        for path in staging.rglob("*")
        if path.is_file()
    }
    expected.add("host_build_metadata.json")
    require(actual == expected, "release staging inventory mismatch")
    return len(actual)


def validate_host_release_metadata(root: Path, staging: Path) -> None:
    metadata = load_json(staging / "host_build_metadata.json")
    expected_version = (root / "release/version.txt").read_text().strip()
    require(metadata["version"] == expected_version, "release metadata version mismatch")
    require(metadata["published"] is False, "host build metadata must remain unpublished")


def expected_staged_files(root: Path, entries: list[dict]) -> set[str]:
    expected: set[str] = set()
    for entry in entries:
        source = root.joinpath(*PurePosixPath(entry["source"]).parts)
        destination = PurePosixPath(entry["destination"])
        if source.is_file():
            expected.add(destination.as_posix())
            continue
        require(source.is_dir(), f"missing release source: {entry['source']}")
        for path in source.rglob("*"):
            if path.is_file():
                expected.add((destination / path.relative_to(source).as_posix()).as_posix())
    return expected


def validate_staged_paths(staging: Path, manifest: dict) -> None:
    prohibited_names = PROHIBITED_NAMES | set(manifest["prohibited_names"])
    for path in staging.rglob("*"):
        relative = path.relative_to(staging)
        require(
            not prohibited_names.intersection(relative.parts),
            f"prohibited staged path: {relative}",
        )
        require(
            not any(
                path.name.startswith(prefix)
                for prefix in manifest["prohibited_prefixes"]
            ),
            f"prohibited staged prefix: {relative}",
        )
        require(
            not any(
                path.name.endswith(suffix)
                for suffix in manifest["prohibited_suffixes"]
            ),
            f"prohibited staged suffix: {relative}",
        )


def validate_destinations(destinations: list[str]) -> None:
    for destination in destinations:
        path = PurePosixPath(destination)
        require(not path.is_absolute(), f"absolute release destination: {destination}")
        require(".." not in path.parts, f"unsafe release destination: {destination}")
        require("*" not in destination, f"wildcard release destination: {destination}")


def validate_license_entries(root: Path, entries: list[dict]) -> None:
    sources = {entry["source"] for entry in entries}
    require(REQUIRED_LICENSES.issubset(sources), "release licenses are incomplete")
    for license_name in REQUIRED_LICENSES:
        path = root / license_name
        require(path.is_file() and path.stat().st_size > 0, f"invalid {license_name}")


def validate_prohibited_entries(entries: list[dict], manifest: dict) -> None:
    prohibited = PROHIBITED_NAMES | set(manifest["prohibited_names"])
    for entry in entries:
        for value in (entry["source"], entry["destination"]):
            parts = PurePosixPath(value).parts
            require(not prohibited.intersection(parts), f"prohibited release path: {value}")


def validate_checksum_round_trip(root: Path, work_directory: Path) -> dict:
    staging = work_directory / "checksum path with spaces"
    staging.mkdir()
    copied_files = copy_checksum_inputs(root, staging)
    manifest_path = staging / "SHA256SUMS"
    write_checksum_manifest(manifest_path, copied_files)
    validate_checksum_manifest(manifest_path, staging)
    report_step("checksums")
    return {path.name: sha256(path) for path in copied_files}


def copy_checksum_inputs(root: Path, staging: Path) -> list[Path]:
    copied = []
    for name in sorted(REQUIRED_LICENSES):
        destination = staging / name
        shutil.copy2(root / name, destination)
        copied.append(destination)
    return copied


def write_checksum_manifest(manifest_path: Path, files: list[Path]) -> None:
    lines = [f"{sha256(path)}  {path.name}" for path in files]
    manifest_path.write_text("\n".join(lines) + "\n")


def validate_checksum_manifest(manifest_path: Path, root: Path) -> None:
    for line in manifest_path.read_text().splitlines():
        expected, name = line.split("  ", 1)
        require(sha256(root / name) == expected, f"checksum mismatch: {name}")


def build_real_odin_object(root: Path, work_directory: Path) -> dict:
    bash = require_command("bash")
    require_command("odin")
    output_path = work_directory / "object output" / "kernel build check.o"
    output_path.parent.mkdir()
    command = [
        bash,
        "scripts/build_odin_object.sh",
        str(output_path),
        "kernel",
        "-target:freestanding_amd64_sysv",
    ]
    result = run_command(command, root)
    match = OBJECT_FORM_PATTERN.search(result.stdout)
    require(match is not None, "Odin object output form was not reported")
    require(
        output_path.is_file() and output_path.stat().st_size > 0,
        "canonical Odin object missing",
    )
    report_step("odin_object")
    return {
        "requested_output": output_path.name,
        "observed_form": match.group(1),
        "canonical_output": output_path.name,
    }


def build_evidence(
    state: ContractExecutionState,
    focused_count: int,
    full_count: int,
    inventory: dict,
    release_inputs: dict,
    checksums: dict,
    object_result: dict,
) -> dict:
    return build_environment_evidence(
        state,
        "PASS",
    ) | {
        "tests": {"odin_object_build": focused_count, "full_python": full_count},
        "odin_object": object_result,
        "release_inventory": {**inventory, "result": "PASS"},
        "release_inputs": release_inputs,
        "checksums": {"algorithm": "SHA-256", "result": "PASS", "files": checksums},
    }


def build_pending_evidence(state: ContractExecutionState) -> dict:
    return build_environment_evidence(state, "PENDING")


def build_failure_evidence(
    state: ContractExecutionState,
    error: Exception,
) -> dict:
    return build_environment_evidence(state, "FAIL") | {"failure": str(error)}


def build_environment_evidence(
    state: ContractExecutionState,
    contract_result: str,
) -> dict:
    return {
        "artifact_version": "1",
        "evidence_class": "host_portability",
        "commit": state.environment["commit"],
        "host": state.environment["host"],
        "tool_versions": state.environment["tool_versions"],
        "workflow": state.environment["workflow"],
        "contract_stage": state.stage,
        "build_contract": contract_result,
        "runtime_contract": "NOT_EXECUTED",
    }


def capture_environment_evidence() -> dict:
    return {
        "commit": capture_commit(),
        "host": host_details(),
        "tool_versions": tool_versions(),
        "workflow": workflow_details(),
    }


def host_details() -> dict:
    return {
        "runner_os": os.environ.get("RUNNER_OS", platform.system()),
        "runner_arch": os.environ.get("RUNNER_ARCH", platform.machine()),
        "runner_image": os.environ.get("ImageOS", "local"),
        "runner_image_version": os.environ.get("ImageVersion", "local"),
        "platform": platform.platform(),
        "shell_contract": "Git Bash" if platform.system() == "Windows" else "Bash",
        "shell_path": os.environ.get("SHELL", os.environ.get("COMSPEC", "unknown")),
    }


def tool_versions() -> dict:
    return {
        "python": platform.python_version(),
        "odin": available_command_version(["odin", "version"]),
        "rustc": available_command_version(["rustc", "--version"]),
        "cargo": available_command_version(["cargo", "--version"]),
        "git": available_command_version(["git", "--version"]),
    }


def workflow_details() -> dict:
    return {
        "name": os.environ.get("GITHUB_WORKFLOW", "local"),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT", "local"),
        "job": os.environ.get("GITHUB_JOB", "local"),
    }


def capture_commit() -> str:
    return os.environ.get("GITHUB_SHA") or available_command_version(
        ["git", "rev-parse", "HEAD"]
    )


def available_command_version(command: list[str]) -> str:
    executable = shutil.which(command[0])
    if executable is None:
        return "NOT_AVAILABLE"
    result = subprocess.run(
        [executable, *command[1:]],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return f"ERROR({result.returncode})"
    return first_output_line(result)


def first_output_line(result: subprocess.CompletedProcess[str]) -> str:
    lines = (result.stdout or result.stderr).strip().splitlines()
    return lines[0] if lines else "unknown"


def command_version(command: list[str]) -> str:
    result = run_command(command, ROOT)
    lines = (result.stdout or result.stderr).strip().splitlines()
    return lines[0] if lines else "unknown"


def count_named_tests(name: str) -> int:
    return unittest.defaultTestLoader.loadTestsFromName(name).countTestCases()


def count_discovered_tests(test_directory: Path) -> int:
    return unittest.defaultTestLoader.discover(str(test_directory)).countTestCases()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file_handle:
        for block in iter(lambda: file_handle.read(65536), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def git_blob_bytes(root: Path, relative_path: str) -> bytes:
    result = subprocess.run(
        ["git", "cat-file", "blob", f"HEAD:{relative_path}"],
        cwd=root,
        capture_output=True,
    )
    require(result.returncode == 0, f"missing release input blob: {relative_path}")
    return result.stdout


def git_blob_id(root: Path, relative_path: str) -> str:
    result = run_command(["git", "rev-parse", f"HEAD:{relative_path}"], root)
    return result.stdout.strip()


def git_head() -> str:
    return command_version(["git", "rev-parse", "HEAD"])


def require_command(name: str) -> str:
    path = shutil.which(name)
    require(path is not None, f"required command missing: {name}")
    return path


def run_command(command: list[str], root: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise PortabilityContractError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"{result.stdout}{result.stderr}"
        )
    return result


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PortabilityContractError(message)


def report_step(name: str) -> None:
    print(f"KOZO_PORTABILITY_STEP={name} RESULT=PASS")


def write_evidence(path: Path, evidence: dict) -> None:
    write_canonical_text(path, json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
