# 🗂️ OCR Environment Documentation

This directory contains setup instructions, scripts, and operational documentation for the **OCR generation system** used to create searchable PDF/A documents from scanned files.

---

## 🗁️ Directory Structure

```
/docs                      → This documentation folder  
/mnt/data/ocr_gen          → Working data directory  
  ├── in/                  → Drop original, unprocessed PDFs here  
  ├── out/                 → Searchable PDFs and sidecar text files are written here  
  └── logs/                → OCR run logs and status messages  

/mnt/AIStorage/venvs/ocr   → Dedicated Python virtual environment for OCR tools
```

---

## ⚙️ System Overview

The OCR pipeline uses **Tesseract** and **OCRmyPDF** to convert non-searchable (image-only) PDFs into **searchable PDF/A** files.  
The process preserves layout and formatting while embedding recognized text as a hidden layer for indexing, search, and compliance archiving.

### Core Components
| Component | Purpose |
|------------|----------|
| `tesseract-ocr` | OCR engine for text recognition (English only) |
| `ocrmypdf` | Workflow manager: deskews, rotates, and embeds OCR text |
| `ghostscript`, `qpdf` | Optimize and rebuild compliant PDFs |
| `poppler-utils` | Validation tools (`pdftotext`, `pdfinfo`) |
| Python libs | Programmatic support via virtual environment |

---

## 🚀 Setup Summary

### 1️⃣ System Install (Run once)
```bash
sudo apt update
sudo apt install -y \
  ocrmypdf \
  tesseract-ocr tesseract-ocr-eng tesseract-ocr-osd \
  qpdf ghostscript pngquant unpaper \
  poppler-utils
```

### 2️⃣ Virtual Environment
```bash
python3 -m venv /mnt/AIStorage/venvs/ocr
source /mnt/AIStorage/venvs/ocr/bin/activate
pip install --upgrade pip
pip install "ocrmypdf[full]" pikepdf pillow pdfminer.six
```

### 3️⃣ Working Directories
```bash
mkdir -p /mnt/data/ocr_gen/{in,out,logs}
```

---

## 🧠 Usage

### Single File
```bash
ocrmypdf \
  --skip-text \
  --rotate-pages --deskew --clean \
  --optimize 3 \
  --pdfa-2 \
  --jobs $(nproc) \
  --language eng \
  --sidecar "/mnt/data/ocr_gen/out/sample.txt" \
  "/mnt/data/ocr_gen/in/sample.pdf" \
  "/mnt/data/ocr_gen/out/sample (searchable).pdf"
```

### Batch Processing
Run the automation script to process all PDFs in `/in`:

```bash
/mnt/data/ocr_gen/ocr_batch.sh
```

Each file generates:
- `filename (searchable).pdf` → searchable PDF/A  
- `filename.txt` → extracted text  
- `filename.log` → process log  

---

## ✅ Verification

Check if a PDF contains selectable text:
```bash
pdftotext "/mnt/data/ocr_gen/out/file (searchable).pdf" - | head
```

View metadata or confirm PDF/A compliance:
```bash
pdfinfo "/mnt/data/ocr_gen/out/file (searchable).pdf"
```

---

## 🧮 Maintenance

- **Activate venv before running scripts**  
  ```bash
  source /mnt/AIStorage/venvs/ocr/bin/activate
  ```
- **Clean old logs and outputs periodically:**  
  ```bash
  find /mnt/data/ocr_gen/logs -type f -mtime +30 -delete
  find /mnt/data/ocr_gen/out -type f -mtime +180 -delete
  ```

---

## 📋 Notes

- This environment is optimized for **English-language OCR**.  
- Scans should be at least **300 DPI** for best accuracy.  
- The process automatically **skips pages that already contain live text**.  
- All outputs are **PDF/A-2 compliant**, suitable for archival.

---

**Maintainer:** Jeremy Heyer  
**Location:** DOH HVSU  
**Last Updated:** November 2025