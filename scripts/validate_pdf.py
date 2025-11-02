from __future__ import annotations

import argparse
import json
import logging
import subprocess
from pathlib import Path
from typing import Sequence

from scripts.types import ValidationCommandResult, ValidationSummary

LOGGER = logging.getLogger("validate_pdf")
LOGGER.propagate = False


def configure_logging(verbose: bool) -> None:
    """Configure structured logging for validation."""
    LOGGER.handlers.clear()
    handler = logging.StreamHandler()
    formatter = logging.Formatter("%(levelname)s %(message)s")
    handler.setFormatter(formatter)
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)


def run_command(command: Sequence[str]) -> ValidationCommandResult:
    """Run an external command and return structured results."""
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    max_preview = 4096  # Prevent log spam by limiting collected output.
    return {
        "command": list(command),
        "returncode": completed.returncode,
        "stdout": completed.stdout[:max_preview],
        "stderr": completed.stderr[:max_preview],
    }


def validate_pdf(pdf_path: Path) -> ValidationSummary:
    """Validate a PDF by calling pdfinfo and pdftotext."""
    commands = {
        "pdfinfo": ["pdfinfo", str(pdf_path)],
        "pdftotext": ["pdftotext", "-q", str(pdf_path), "-"],
    }
    results: ValidationSummary = {}
    for name, command in commands.items():
        outcome = run_command(command)
        results[name] = outcome
        level = logging.INFO if outcome["returncode"] == 0 else logging.ERROR
        LOGGER.log(level, "%s completed with code %s", name, outcome["returncode"])
    return results


def build_parser() -> argparse.ArgumentParser:
    """Create a CLI parser for PDF validation."""
    parser = argparse.ArgumentParser(description="Validate OCR outputs with pdfinfo/pdftotext")
    parser.add_argument("pdf", type=Path, help="PDF file to validate")
    parser.add_argument("--verbose", action="store_true", help="Enable debug logging")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.verbose)
    pdf_path = args.pdf.expanduser().resolve()
    if not pdf_path.exists():
        LOGGER.error("PDF does not exist: %s", pdf_path)
        return 2
    results = validate_pdf(pdf_path)
    print(json.dumps(results))
    return 0 if all(value["returncode"] == 0 for value in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
