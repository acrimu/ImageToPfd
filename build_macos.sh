#!/bin/sh
set -eu

APP_DIR=$(CDPATH= cd "$(dirname "$0")" && pwd)
cd "$APP_DIR"

if [ "$(uname -s)" != "Darwin" ]; then
    printf '%s\n' "This script must be run on macOS." >&2
    exit 1
fi

if command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
elif command -v python >/dev/null 2>&1; then
    PYTHON=python
else
    printf '%s\n' "Python was not found. Install Python 3.10 or newer." >&2
    exit 1
fi

if ! "$PYTHON" -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
    printf '%s\n' "Python 3.10 or newer is required to build Paperstack." >&2
    exit 1
fi

if ! "$PYTHON" -m PyInstaller --version >/dev/null 2>&1; then
    printf '%s\n' "PyInstaller is missing. Run: $PYTHON -m pip install -r requirements-build.txt" >&2
    exit 1
fi

APP_VERSION=$("$PYTHON" -c 'from app_version import __version__; print(__version__)')
exec "$PYTHON" -m PyInstaller \
    --clean \
    --noconfirm \
    --onedir \
    --windowed \
    --name "Paperstack-v$APP_VERSION" \
    --collect-all tkinterdnd2 \
    --add-data "paper_sizes.json:." \
    image_to_pdf.py
