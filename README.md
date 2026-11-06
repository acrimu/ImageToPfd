# Paperstack — Images to PDF

Paperstack is a simple desktop app for combining images into a single, polished PDF. Arrange pages, choose a paper size, adjust each image, and export everything locally—your files never leave your computer.

## Features

- Combine multiple images into one PDF
- Reorder or remove images before exporting
- Drag and drop files into the app
- Preview every page as you edit it
- Scale, position, align, and fit each image independently
- Choose from ISO, US, and photo paper sizes, or match each source image
- Switch between portrait and landscape orientation
- Adjust page margins, output resolution, and image quality
- Correct image orientation automatically using EXIF metadata
- Work entirely offline

## Supported image formats

PNG, JPG/JPEG, WebP, BMP, and TIFF.

## Requirements

- Python 3.10 or newer
- [Pillow](https://python-pillow.org/)
- [tkinterdnd2](https://pypi.org/project/tkinterdnd2/)
- Tkinter (normally included with Python on Windows and macOS)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/acrimu/ImageToPfd.git ImageToPdf
   cd ImageToPdf
   ```

2. Optional but recommended: create and activate a virtual environment.

   **Windows (PowerShell)**

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   **macOS/Linux**

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install the dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

## Run the app

On Windows, double-click `run_app.bat` or run:

```powershell
.\run_app.bat
```

On macOS or Linux, run:

```bash
./run_app.sh
```

If needed, make the script executable with `chmod +x run_app.sh`. You can also start the Python script directly on any supported platform:

```bash
python image_to_pdf.py
```

On some macOS or Linux systems, use `python3` instead of `python`.
The app version appears in the window title and is maintained in `app_version.py` to match its Git tag.

## Build a standalone app

Builds must be made on the operating system they target; PyInstaller does not cross-compile between macOS, Windows, and Linux.

1. Install Python 3.10 or newer and the build dependencies:

   ```bash
   python3 -m pip install -r requirements-build.txt
   ```

   On Windows, use `py -3 -m pip install -r requirements-build.txt` instead.

2. Run the script for your operating system from the project folder:

   - **macOS:** `./build_macos.sh` (creates `dist/Paperstack-v<version>.app`)
   - **Linux:** `./build_linux.sh` (creates `dist/Paperstack-v<version>/`)
   - **Windows:** `build_windows.bat` (creates `dist\Paperstack-v<version>\`)

   The macOS and Linux scripts may need to be made executable once with `chmod +x build_macos.sh build_linux.sh`.
   On Linux, install the system Tkinter package first if it is missing (for example, `sudo apt install python3-tk` on Ubuntu or Debian).
   Linux builds depend on the build system's glibc version, so build on the oldest Linux distribution you intend to support.

The output includes the app and its runtime files. Distribute the complete app bundle or folder, not just the executable inside it.

## Usage

1. Select **Add images**, or drag images into the file list.
2. Select an image to preview and adjust its scale, position, fit, or alignment.
3. Use **Move up**, **Move down**, and **Remove** to organize the pages.
4. Choose the page size, orientation, margin, output resolution, and image quality.
5. Select **Create PDF**, choose a destination, and save the document.

Each imported image becomes one PDF page, in the order shown in the app.

## PDF size and quality

Paperstack defaults to **150 DPI** and **75% image quality** to keep generated PDFs reasonably small. Use the export controls to choose the balance that fits your needs:

- **150 DPI** — smallest files; recommended for screens, email, and everyday documents
- **200 DPI** — a balance between file size and print detail
- **300 DPI** — highest detail; recommended when print quality matters more than file size

Lowering **Image quality** reduces the file size further. Because source formats such as PNG, WebP, and JPEG use different compression methods, the resulting PDF may be larger or smaller than the combined source files.

## Custom paper sizes

Paper sizes are defined in [`paper_sizes.json`](paper_sizes.json) as pixel dimensions at 300 DPI:

```json
{
  "A4": [2480, 3508],
  "Letter": [2550, 3300]
}
```

Add another name and `[width, height]` pair to make a custom size appear in the page-size menu. Restart Paperstack after changing the file.

## Troubleshooting

### `ModuleNotFoundError`

Install the project dependencies with:

```bash
python -m pip install -r requirements.txt
```

### Tkinter is missing on Linux

Tkinter may need to be installed through your system package manager. For example, on Ubuntu or Debian:

```bash
sudo apt install python3-tk
```

### Drag and drop is unavailable

The app still supports selecting images with **Add images**. To enable drag and drop, ensure `tkinterdnd2` is installed in the same Python environment used to run Paperstack.

## Privacy

Paperstack processes images locally and does not upload them or require an internet connection.

## License

This project is available under the [MIT License](LICENSE).
