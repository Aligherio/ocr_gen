# OCR Generation Toolkit

## Overview
The OCR Generation Toolkit bundles a thin command-line wrapper around
[OCRmyPDF](https://ocrmypdf.readthedocs.io/en/latest/) to streamline single-file and
batch PDF processing. It provides typed profile management, structured logging, and
Makefile automation so new operators can get productive quickly.

## Dependencies
- **Python 3.12** (used for the CLI utilities and validation helpers)
- **OCRmyPDF 16.4.5** with the `full` extras (pulled in by `requirements.txt`)
- **System libraries** required by OCRmyPDF (Ghostscript, Leptonica, Tesseract, etc.)
- **PyYAML 6.0.2**, **pikepdf 9.2.0**, **Pillow 10.4.0**, **pdfminer.six 20240706**
- **Ruff 0.6.9** for linting and formatting checks

All Python packages are pinned in `requirements.txt`. Install the system-level OCRmyPDF
dependencies before running the setup routine.

## Installation
1. Clone the repository and move into the project root.
2. Provision a local virtual environment and install dependencies:

   ```bash
   make setup
   source .venv/bin/activate
   ```

   The `setup` target creates `.venv/`, installs the pinned Python packages, and ensures
   `/mnt/data/ocr_gen/{in,out,logs}` exist for batch processing.

3. (Optional) Add the repository `scripts/` directory to your `$PATH` or create a shell
   alias so the `ocr` entry point resolves to `python scripts/ocr_cli.py`:

   ```bash
   alias ocr="python scripts/ocr_cli.py"
   ```

   This alias is assumed in the usage examples below.

## CLI Usage
The CLI exposes two primary commands. Profiles default to `balanced` unless overridden
with `--profile <name>`.

### Single-file OCR
```bash
ocr file.pdf
```

- Processes `file.pdf` in place and writes `file.ocr.pdf` beside the input unless
  `--output` is supplied.
- Accepts repeated `--ocrmypdf-arg` overrides that append directly to the underlying
  `ocrmypdf` invocation.

### Batch OCR
```bash
ocr batch --input-dir /mnt/data/ocr_gen/in --output-dir /mnt/data/ocr_gen/out
```

- Iterates through all PDFs in the input directory, writing results to the output
  directory (existing files are overwritten).
- Add `--validate` to run `scripts/validate_pdf.py` after each successful OCR pass.
- Additional `--ocrmypdf-arg` values are passed through to every job.

### Alternative Invocation
If you prefer not to create the `ocr` alias, call the CLI explicitly:

```bash
python scripts/ocr_cli.py file path/to/input.pdf --output path/to/output.pdf
python scripts/ocr_cli.py batch --input-dir in_dir --output-dir out_dir
```

## Profiles and Configuration
Profiles live in `config/ocr_profiles.yaml`. Each entry defines:

```yaml
<profile-name>:
  description: Friendly text for help output
  ocrmypdf_args:
    - "--skip-text"
    - "--optimize=2"
```

Use `--profiles /path/to/custom.yaml` to load alternate profile sets. The CLI validates
that every profile supplies an iterable `ocrmypdf_args` list before execution.

## Outputs and Logs
- **Output PDFs**: Default to `<input>.ocr.pdf` for single-file runs or the configured
  `--output-dir` for batch runs. The directory `/mnt/data/ocr_gen/out` is created during
  `make setup` and used by default.
- **Sidecar text**: When using `make single` (Makefile target), a `.txt` sidecar is
  emitted next to the generated PDF. Direct CLI usage does not add sidecars unless you
  pass `--ocrmypdf-arg "--sidecar=/desired/path"`.
- **Structured logs**: The CLI emits JSON-formatted messages to stdout. Redirect stdout
  to `/mnt/data/ocr_gen/logs/` for persistent storage, e.g.:

  ```bash
  ocr batch > /mnt/data/ocr_gen/logs/$(date +%Y%m%dT%H%M%S)_batch.jsonl
  ```

  The setup step prepares `/mnt/data/ocr_gen/logs` for this purpose.

## Maintenance Commands
- `make lint` – Run Ruff static analysis across the repository.
- `make format` – Apply Ruff formatting to normalize style.
- `make batch` – Execute `scripts/ocr_batch.sh` against the default in/out directories.
- `make single INPUT=/path/to/input.pdf [OUTPUT=/path/to/output.pdf]` – Wrapper that runs
  a single OCRmyPDF invocation with sensible defaults and sidecar generation.

## Troubleshooting
- **Missing profiles**: Confirm `config/ocr_profiles.yaml` exists or pass
  `--profiles /path/to/file`.
- **OCRmyPDF failures**: Check the JSON log output for stderr/stdout fields.
- **Permission issues**: Ensure the executing user can read from `in/` and write to
  `out/` and `logs/` directories under `/mnt/data/ocr_gen/`.

