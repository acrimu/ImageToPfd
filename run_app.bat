@echo off
set "APP_DIR=%~dp0"
python "%APP_DIR%image_to_pdf.py"
if errorlevel 1 (
  echo.
  echo Could not start Paperstack. Install Python and Pillow with:
  echo   pip install Pillow
  pause
)
