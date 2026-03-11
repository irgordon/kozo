from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class ValidationResult:
    status: str
    code: str
    detail: str
    action: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def pass_(code: str, detail: str) -> "ValidationResult":
        return ValidationResult(status="pass", code=code, detail=detail)

    @staticmethod
    def fail(
        code: str,
        detail: str,
        action: Optional[str] = None,
        meta: Optional[Dict[str, Any]] = None,
    ) -> "ValidationResult":
        return ValidationResult(
            status="fail",
            code=code,
            detail=detail,
            action=action,
            meta={} if meta is None else dict(meta),
        )


class BaseValidator:
    name: str
    subsystem: str

    def validate(self, artifact_bundle: Dict[str, Any]) -> ValidationResult:
        raise NotImplementedError
