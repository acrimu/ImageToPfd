@echo off
setlocal
cd /d "%~dp0" || exit /b 1

where py >nul 2>nul
if errorlevel 1 (
    set "PYTHON=python"
) else (
    set "PYTHON=py -3"
)

%PYTHON% -c "import sys; sys.exit(sys.version_info < (3, 10))" >nul 2>nul
if errorlevel 1 (
    echo Python 3.10 or newer is required to build Paperstack.
    exit /b 1
)

%PYTHON% -m PyInstaller --version >nul 2>nul
if errorlevel 1 (
    echo PyInstaller is missing. Install build dependencies with:
    echo   %PYTHON% -m pip install -r requirements-build.txt
    exit /b 1
)

for /f "delims=" %%V in ('%PYTHON% -c "from app_version import __version__; print(__version__)"') do set "APP_VERSION=%%V"
if not defined APP_VERSION (
    echo Could not read the app version from app_version.py.
    exit /b 1
)

%PYTHON% -m PyInstaller --clean --noconfirm --onedir --windowed --name "Paperstack-v%APP_VERSION%" --collect-all tkinterdnd2 --add-data "paper_sizes.json;." image_to_pdf.py
if errorlevel 1 exit /b %errorlevel%

echo Build complete: dist\Paperstack-v%APP_VERSION%\Paperstack-v%APP_VERSION%.exe
