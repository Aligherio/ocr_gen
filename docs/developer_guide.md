# Developer Guide

This guide documents the CLI architecture, configuration schema, logging strategy, and
extension practices that keep the OCR Generation Toolkit maintainable.

## Architecture Overview
The entry point `scripts/ocr_cli.py` wraps OCRmyPDF with three core layers:

1. **Argument parsing** – `argparse` constructs a top-level parser with `file` and
   `batch` subcommands (`build_parser`). Subcommands attach handler functions that manage
   orchestration.
2. **Profile management** – `load_profiles` reads YAML data from
   `config/ocr_profiles.yaml`, normalizes it into immutable `OCRProfile` dataclasses, and
   validates schema expectations (`description` text and an iterable `ocrmypdf_args`).
3. **Job execution** – `run_ocr_job` composes the OCRmyPDF command, logs structured
   metadata, and returns a JSON-serializable summary used by both subcommands. Batch
   processing reuses this helper inside `handle_batch_command`, aggregating per-file
   results.

Supporting modules include:
- `scripts/ocr_batch.sh` – Thin Bash wrapper that iterates over a directory and invokes
  the Python CLI for each PDF (used by `make batch`).
- `scripts/validate_pdf.py` – Optional validator called when the `--validate` flag is set
  during batch runs.

## Profile Schema
Profiles are keyed dictionaries with the following fields:

| Field            | Type             | Required | Notes                                                     |
| ---------------- | ---------------- | -------- | --------------------------------------------------------- |
| `description`    | string           | No       | Display text in docs/help; defaults to empty string.      |
| `ocrmypdf_args`  | list of strings  | Yes      | Appended verbatim to the OCRmyPDF command line.          |

Developers adding new profiles should ensure arguments are compatible with OCRmyPDF 16
and keep descriptions concise. Reuse existing arguments whenever possible to simplify
operator training. Custom profile files can be loaded at runtime with `--profiles`.

## Logging Patterns
- Logging is centralized through the module-level `LOGGER` configured by
  `configure_logging`.
- Output uses the custom `JsonLogFormatter`, emitting newline-delimited JSON records to
  stdout. Attach contextual metadata via the `extra={"structured_data": {...}}` pattern
  already present in `run_ocr_job` and its callers.
- Set `--verbose` to raise the log level to `DEBUG`. Default runs operate at `INFO`.
- Persist logs by redirecting stdout to files under `/mnt/data/ocr_gen/logs/`. The
  `make setup` target scaffolds this directory.

## JSON Summary Schema
The CLI returns JSON summaries for both single-file and batch executions. Downstream
automation relies on these payloads, so treat the field layout as a stable contract and
ensure any schema updates are reflected in this section.

### Single-file summaries
`run_ocr_job` emits one object per processed file with the following keys:

- `input` – Absolute or relative path to the source PDF.
- `output` – Destination path for the generated artifact (PDF or text sidecar).
- `profile` – Name of the OCR profile applied to the run.
- `returncode` – Integer exit status from the OCRmyPDF subprocess.
- `stdout` *(optional)* – Captured stdout from OCRmyPDF when available.
- `stderr` *(optional)* – Captured stderr from OCRmyPDF when available.

### Batch summaries
`handle_batch_command` wraps multiple single-file runs and aggregates their results into a
single JSON document:

- `profile` – Profile applied to every file in the batch.
- `input_dir` – Source directory that was scanned for input PDFs.
- `output_dir` – Directory receiving the processed outputs.
- `results` – Array of single-file summary objects (see schema above).
- `failed` – Count of single-file runs whose `returncode` was non-zero.
- `succeeded` – Count of successful single-file runs.
- `validation` *(optional)* – Object emitted when `--validate` is enabled; captures any
  validator-specific details (e.g., `status`, `messages`).

Example batch summary:

```json
{
  "profile": "default",
  "input_dir": "./samples",
  "output_dir": "./outputs",
  "results": [
    {
      "input": "./samples/doc1.pdf",
      "output": "./outputs/doc1.pdf",
      "profile": "default",
      "returncode": 0
    }
  ],
  "failed": 0,
  "succeeded": 1
}
```

## Retry and Idempotency Practices
- Both the `file` and `batch` handlers overwrite existing output files, making reruns
  idempotent as long as callers accept last-writer-wins behavior.
- `run_ocr_job` propagates non-zero return codes through the printed JSON summary. When
  implementing retries, wrap calls to `run_ocr_job` and re-execute based on the
  `returncode` field.
- Batch mode tracks failures via the `failed` count in its aggregate summary. Retry
  orchestration can read the JSON output and requeue specific PDFs.
- Avoid destructive cleanup between retries so partially processed directories can be
  inspected.

## Extension Guidelines
- **New subcommands**: Extend `build_parser` with additional subparsers and corresponding
  handler functions. Reuse helper utilities rather than duplicating subprocess logic.
- **Additional validation**: When importing extra validators, prefer local imports inside
  handlers (as done for `validate_pdf`) to avoid circular dependencies and keep optional
  dependencies off the hot path.
- **Profile evolution**: Ensure new YAML keys are backward compatible. If additional
  metadata is required, update `load_profiles` with strict type checks and document the
  change in `docs/README.md`.
- **Testing**: Add targeted unit tests around new helper functions. Keep manual checks
  convenient by expanding Makefile targets rather than inventing bespoke scripts.

## Makefile Touchpoints
- `make setup` – Bootstraps the environment and data directories. Run after cloning or
  when dependencies change.
- `make batch` – Executes `scripts/ocr_batch.sh`, useful for exercising the Bash wrapper
  during development.
- `make single` – Invokes OCRmyPDF for a single file while generating a sidecar text file
  (logic is contained in the Makefile to keep the CLI vendor-neutral).
- `make lint` / `make format` – Provide the shared Ruff-based quality gates; update docs
  if you change linting expectations.

## Logging and Metrics Destinations
- Redirect CLI stdout to `/mnt/data/ocr_gen/logs/*.jsonl` for structured historical logs.
- Capture stderr separately when debugging OCRmyPDF itself (the CLI preserves stderr in
  the printed JSON payloads).
- When integrating with external monitoring, parse the JSON output and forward the fields
  most relevant to your pipeline (e.g., `returncode`, `profile`, `input`).

## Development Workflow Checklist
1. Run `make setup` if dependencies or virtual environments have changed.
2. Activate the virtual environment: `source .venv/bin/activate`.
3. Execute targeted OCR runs with either `ocr file.pdf` or `ocr batch ...` to reproduce
   behavior.
4. Use `make lint` before submitting changes.
5. Update both `docs/README.md` and `docs/developer_guide.md` whenever the CLI interface
   or profile schema changes to keep operator and developer documentation in sync.

