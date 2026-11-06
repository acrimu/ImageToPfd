#!/bin/sh

APP_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd) || exit 1

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    printf '%s\n' "Python was not found. Install Python 3.10 or newer to run Paperstack." >&2
    exit 1
fi

exec "$PYTHON" "$APP_DIR/image_to_pdf.py"
