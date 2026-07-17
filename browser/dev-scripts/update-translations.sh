#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/.."

mapfile -t PY_FILES < <(find . -name '*.py' -not -path './.venv/*' -not -path './__pycache__/*')

pyside6-lupdate -no-obsolete "${PY_FILES[@]}" -ts ts/de_DE.ts
