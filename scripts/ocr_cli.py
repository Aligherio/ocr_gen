from __future__ import annotations

import argparse
import json
import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError as exc:  # pragma: no cover - import guard
    raise SystemExit(
        "PyYAML is required to load OCR profiles. Install it with `pip install pyyaml`."
    ) from exc

LOGGER = logging.getLogger("ocr_cli")
LOGGER.propagate = False


class JsonLogFormatter(logging.Formatter):
    """Simple JSON formatter to keep log output structured."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname,
            "event": record.getMessage(),
            "logger": record.name,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        for key, value in getattr(record, "structured_data", {}).items():
            payload[key] = value
        return json.dumps(payload)


def configure_logging(verbose: bool) -> None:
    """Configure structured logging for the CLI."""
    LOGGER.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    LOGGER.addHandler(handler)
    LOGGER.setLevel(logging.DEBUG if verbose else logging.INFO)


@dataclass(frozen=True)
class OCRProfile:
    name: str
    description: str
    ocrmypdf_args: tuple[str, ...]


def load_profiles(profile_path: Path) -> dict[str, OCRProfile]:
    """Load OCR profiles from a YAML file."""
    with profile_path.open("r", encoding="utf-8") as stream:
        raw_profiles = yaml.safe_load(stream) or {}
    if not isinstance(raw_profiles, dict):
        raise ValueError("Profile configuration must be a mapping of profile names.")
    profiles: dict[str, OCRProfile] = {}
    for name, data in raw_profiles.items():
        if not isinstance(data, dict):
            raise ValueError(f"Profile '{name}' must be a mapping.")
        description = str(data.get("description", ""))
        raw_args = data.get("ocrmypdf_args", [])
        if isinstance(raw_args, (str, bytes)) or not isinstance(raw_args, Iterable):
            raise ValueError(f"Profile '{name}' must define iterable 'ocrmypdf_args'.")
        args = tuple(str(arg) for arg in raw_args)
        profiles[name] = OCRProfile(name=name, description=description, ocrmypdf_args=args)
    return profiles


def resolve_profile(name: str, profiles: dict[str, OCRProfile]) -> OCRProfile:
    """Resolve a profile name to a concrete ``OCRProfile`` instance."""
    try:
        return profiles[name]
    except KeyError as exc:
        raise KeyError(f"Unknown profile '{name}'. Available profiles: {', '.join(sorted(profiles))}") from exc


def run_ocr_job(
    input_path: Path,
    output_path: Path,
    profile: OCRProfile,
    extra_args: tuple[str, ...],
) -> dict[str, Any]:
    """Execute an ``ocrmypdf`` invocation and capture structured metadata."""
    command = [
        "ocrmypdf",
        *profile.ocrmypdf_args,
        *extra_args,
        str(input_path),
        str(output_path),
    ]
    LOGGER.info(
        "Running ocrmypdf",
        extra={
            "structured_data": {
                "input": str(input_path),
                "output": str(output_path),
                "profile": profile.name,
                "command": command,
            }
        },
    )
    completed = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
    )
    summary: dict[str, Any] = {
        "input": str(input_path),
        "output": str(output_path),
        "profile": profile.name,
        "returncode": completed.returncode,
    }
    if completed.stdout:
        summary["stdout"] = completed.stdout
    if completed.stderr:
        summary["stderr"] = completed.stderr
    if completed.returncode == 0:
        LOGGER.info(
            "ocrmypdf succeeded",
            extra={"structured_data": {"input": str(input_path), "output": str(output_path)}},
        )
    else:
        LOGGER.error(
            "ocrmypdf failed",
            extra={
                "structured_data": {
                    "input": str(input_path),
                    "output": str(output_path),
                    "returncode": completed.returncode,
                }
            },
        )
    return summary


def handle_file_command(args: argparse.Namespace, profiles: dict[str, OCRProfile]) -> int:
    """Handle the ``file`` subcommand."""
    input_path = Path(args.input).expanduser().resolve()
    if not input_path.exists():
        LOGGER.error(
            "Input file does not exist",
            extra={"structured_data": {"input": str(input_path)}},
        )
        return 2
    output_path = Path(args.output).expanduser().resolve() if args.output else input_path.with_suffix(".ocr.pdf")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        profile = resolve_profile(args.profile, profiles)
    except KeyError as error:
        LOGGER.error("Profile resolution failed", extra={"structured_data": {"profile": args.profile}})
        raise SystemExit(str(error)) from error
    extra_args = tuple(args.ocrmypdf_arg or [])
    summary = run_ocr_job(input_path=input_path, output_path=output_path, profile=profile, extra_args=extra_args)
    print(json.dumps(summary))
    return int(summary["returncode"])


def iter_pdfs(root: Path) -> Iterable[Path]:
    """Yield PDF files under ``root`` ordered for deterministic processing."""
    if not root.exists():
        LOGGER.warning(
            "Input directory does not exist",
            extra={"structured_data": {"input_dir": str(root)}},
        )
        return
    for path in sorted(root.glob("*.pdf")):
        if path.is_file():
            yield path


def handle_batch_command(args: argparse.Namespace, profiles: dict[str, OCRProfile]) -> int:
    """Handle the ``batch`` subcommand."""
    input_dir = Path(args.input_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    try:
        profile = resolve_profile(args.profile, profiles)
    except KeyError as error:
        LOGGER.error("Profile resolution failed", extra={"structured_data": {"profile": args.profile}})
        raise SystemExit(str(error)) from error
    extra_args = tuple(args.ocrmypdf_arg or [])
    summaries: list[dict[str, Any]] = []
    exit_codes: list[int] = []
    for pdf_path in iter_pdfs(input_dir):
        target_path = output_dir / pdf_path.name
        summary = run_ocr_job(pdf_path, target_path, profile, extra_args)
        summaries.append(summary)
        exit_codes.append(int(summary["returncode"]))
        if args.validate and summary["returncode"] == 0:
            from scripts.validate_pdf import validate_pdf  # Local import to avoid circular runtime dependency

            validation = validate_pdf(target_path)
            summaries[-1]["validation"] = validation
    batch_summary = {
        "profile": profile.name,
        "input_dir": str(input_dir),
        "output_dir": str(output_dir),
        "results": summaries,
        "failed": sum(code != 0 for code in exit_codes),
        "succeeded": sum(code == 0 for code in exit_codes),
    }
    print(json.dumps(batch_summary))
    return 0 if all(code == 0 for code in exit_codes) else 1


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(description="CLI wrapper around ocrmypdf with profile support")
    parser.add_argument(
        "--profiles",
        default=Path("config/ocr_profiles.yaml"),
        type=Path,
        help="Path to the YAML profile configuration file.",
    )
    parser.add_argument(
        "--profile",
        default="balanced",
        help="Profile name to use. Defaults to 'balanced'.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable debug logging.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    file_parser = subparsers.add_parser("file", help="Process a single PDF file")
    file_parser.add_argument("input", help="Input PDF file path")
    file_parser.add_argument("--output", help="Output PDF file path (defaults to <input>.ocr.pdf)")
    file_parser.add_argument(
        "--ocrmypdf-arg",
        action="append",
        dest="ocrmypdf_arg",
        help="Additional arguments to pass to ocrmypdf. Can be used multiple times.",
    )
    file_parser.set_defaults(handler=handle_file_command)

    batch_parser = subparsers.add_parser("batch", help="Process all PDFs in a directory")
    batch_parser.add_argument(
        "--input-dir",
        type=Path,
        default=Path("/mnt/data/ocr_gen/in"),
        help="Directory containing PDF files to process.",
    )
    batch_parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/mnt/data/ocr_gen/out"),
        help="Directory where processed PDFs will be written.",
    )
    batch_parser.add_argument(
        "--validate",
        action="store_true",
        help="Run post-processing validation on the generated PDFs.",
    )
    batch_parser.add_argument(
        "--ocrmypdf-arg",
        action="append",
        dest="ocrmypdf_arg",
        help="Additional arguments to pass to ocrmypdf. Can be used multiple times.",
    )
    batch_parser.set_defaults(handler=handle_batch_command)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Entrypoint for the CLI."""
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(verbose=args.verbose)
    profiles = load_profiles(Path(args.profiles))
    try:
        handler = args.handler
    except AttributeError:
        parser.error("No command provided.")
        return 1
    return handler(args, profiles)


if __name__ == "__main__":
    raise SystemExit(main())
