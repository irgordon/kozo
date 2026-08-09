from __future__ import annotations

from pathlib import PurePath


def canonical_repository_path(repository_root: PurePath, path: PurePath) -> str:
    _require_matching_path_flavors(repository_root, path)
    relative_path = path.relative_to(repository_root)
    if ".." in relative_path.parts:
        raise ValueError("repository path escapes its root")
    return relative_path.as_posix()


def canonical_repository_field(
    prefix: str,
    repository_root: PurePath,
    path: PurePath,
    suffix: str,
) -> str:
    repository_path = canonical_repository_path(repository_root, path)
    return f"{prefix}.{repository_path}.{suffix}"


def _require_matching_path_flavors(repository_root: PurePath, path: PurePath) -> None:
    if type(repository_root) is not type(path):
        raise ValueError("repository root and path use different path flavors")
