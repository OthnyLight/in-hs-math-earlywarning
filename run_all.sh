#!/usr/bin/env bash
# Run the full pipeline. Pass --final only after docs/VERIFY_CHECKLIST.md is complete.
set -euo pipefail
cd "$(dirname "$0")"
FLAG="${1:-}"
python code/02_build.py
python code/03_model.py > data/processed/model_log.txt
python code/04_figures.py $FLAG
python code/05_map.py $FLAG
node code/06_document.js $FLAG
(cd paper && soffice --headless --convert-to pdf manuscript.docx >/dev/null 2>&1 || echo "LibreOffice not found: PDF not rebuilt")
python code/07_model_card.py $FLAG
echo "done"
