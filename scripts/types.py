from __future__ import annotations

from typing import NotRequired, TypedDict


class ValidationCommandResult(TypedDict):
    """Structured outcome from running an external validation command."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


ValidationSummary = dict[str, ValidationCommandResult]


class OCRJobSummary(TypedDict):
    """Structured metadata about a single OCR processing job."""

    input: str
    output: str
    profile: str
    returncode: int
    stdout: NotRequired[str]
    stderr: NotRequired[str]
    validation: NotRequired[ValidationSummary]


class OCRBatchSummary(TypedDict):
    """Aggregated results for a batch OCR run."""

    profile: str
    input_dir: str
    output_dir: str
    results: list[OCRJobSummary]
    failed: int
    succeeded: int


__all__ = [
    "OCRBatchSummary",
    "OCRJobSummary",
    "ValidationCommandResult",
    "ValidationSummary",
]
