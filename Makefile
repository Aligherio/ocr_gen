.PHONY: setup lint format batch single

VENV ?= .venv
PYTHON ?= python3
PIP ?= $(VENV)/bin/pip
RUFF ?= ruff

setup:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	mkdir -p /mnt/data/ocr_gen/in /mnt/data/ocr_gen/out /mnt/data/ocr_gen/logs

lint:
	$(RUFF) check .

format:
	$(RUFF) format .

batch:
	bash /mnt/data/ocr_gen/ocr_batch.sh

single:
	@if [ -z "$(INPUT)" ]; then \
		echo "Usage: make single INPUT=/path/to/input.pdf [OUTPUT=/path/to/output.pdf]"; \
		exit 1; \
	fi
	@output_path="$(OUTPUT)"; \
	if [ -z "$$output_path" ]; then \
		filename=$$(basename "$(INPUT)" .pdf); \
		output_path="/mnt/data/ocr_gen/out/$$filename (searchable).pdf"; \
	fi; \
	sidecar="$${output_path%.pdf}.txt"; \
	echo "Running OCRmyPDF for $(INPUT)"; \
	ocrmypdf --skip-text --rotate-pages --deskew --clean --optimize 3 --pdfa-2 --jobs $$(nproc) --language eng --sidecar "$$sidecar" "$(INPUT)" "$$output_path"
