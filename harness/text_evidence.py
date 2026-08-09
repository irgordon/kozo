from __future__ import annotations

from pathlib import Path


def canonical_text_bytes(text: str) -> bytes:
    canonical_text = text.replace("\r\n", "\n").replace("\r", "\n")
    return canonical_text.encode("utf-8")


def write_canonical_text(path: Path, text: str) -> None:
    path.write_bytes(canonical_text_bytes(text))


def raw_artifact_size(path: Path) -> int:
    return path.stat().st_size
