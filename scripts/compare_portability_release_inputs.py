from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.text_evidence import write_canonical_text
from scripts.host_portability_contract import GOVERNED_RELEASE_INPUTS

HOSTS = ("linux", "macos", "windows")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class CrossHostIdentityError(RuntimeError):
    pass


def main() -> int:
    arguments = parse_arguments()
    evidence_paths = {host: getattr(arguments, host) for host in HOSTS}
    try:
        report = compare_evidence_files(evidence_paths)
    except Exception as error:
        write_report(arguments.output, {"result": "FAIL", "failure": str(error)})
        raise
    write_report(arguments.output, report)
    print(json.dumps(report, indent=2))
    return 0


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Compare governed release inputs across required hosts"
    )
    for host in HOSTS:
        parser.add_argument(f"--{host}", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def compare_evidence_files(evidence_paths: dict[str, Path]) -> dict:
    evidence = {host: load_json(path) for host, path in evidence_paths.items()}
    return compare_release_input_evidence(evidence)


def compare_release_input_evidence(evidence_by_host: dict[str, dict]) -> dict:
    require(set(evidence_by_host) == set(HOSTS), "required host evidence is incomplete")
    commits = {evidence["commit"] for evidence in evidence_by_host.values()}
    require(len(commits) == 1, "host evidence commits differ")
    records = {
        host: indexed_release_inputs(evidence)
        for host, evidence in evidence_by_host.items()
    }
    baseline = records[HOSTS[0]]
    for host in HOSTS[1:]:
        require(
            records[host] == baseline,
            f"cross-host release-input identity mismatch: {host}",
        )
    return {
        "artifact_version": "1",
        "evidence_class": "cross_host_release_input_identity",
        "commit": commits.pop(),
        "hosts": list(HOSTS),
        "governed_scope": list(GOVERNED_RELEASE_INPUTS),
        "comparison_dimensions": ["path", "size", "sha256"],
        "result": "PASS",
        "files": [
            {"path": path, "size": size, "sha256": digest}
            for path, (size, digest) in sorted(baseline.items())
        ],
    }


def indexed_release_inputs(evidence: dict) -> dict[str, tuple[int, str]]:
    require(evidence.get("build_contract") == "PASS", "host build contract did not pass")
    release_inputs = evidence.get("release_inputs", {})
    require(
        release_inputs.get("authority") == "git_blob",
        "release-input authority mismatch",
    )
    require(
        release_inputs.get("result") == "PASS",
        "release-input validation did not pass",
    )
    records: dict[str, tuple[int, str]] = {}
    for record in release_inputs.get("files", []):
        path = record.get("path")
        require(path not in records, f"duplicate governed release input: {path}")
        size = record.get("size")
        digest = record.get("sha256")
        require(
            isinstance(size, int) and size >= 0,
            f"invalid governed release-input size: {path}",
        )
        require(
            isinstance(digest, str)
            and SHA256_PATTERN.fullmatch(digest) is not None,
            f"invalid governed release-input hash: {path}",
        )
        require(
            record.get("staged_size") == size,
            f"source/staged release-input size mismatch: {path}",
        )
        require(
            record.get("staged_sha256") == digest,
            f"source/staged release-input hash mismatch: {path}",
        )
        records[path] = (size, digest)
    require(
        set(records) == set(GOVERNED_RELEASE_INPUTS),
        "governed release-input set mismatch",
    )
    return records


def load_json(path: Path) -> dict:
    return json.loads(path.read_text())


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    write_canonical_text(path, json.dumps(report, indent=2) + "\n")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CrossHostIdentityError(message)


if __name__ == "__main__":
    raise SystemExit(main())
