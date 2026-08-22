"""A small, offline desktop app for combining images into one PDF."""

from __future__ import annotations

import os
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageOps, ImageTk

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    AppWindow = TkinterDnD.Tk
except ImportError:
    DND_FILES = None
    AppWindow = tk.Tk


IMAGE_TYPES = [("Image files", "*.png *.jpg *.jpeg *.webp *.bmp *.tif *.tiff"), ("All files", "*.*")]
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
PAGE_SIZES = {
    "A4": (2480, 3508),
    "Letter": (2550, 3300),
    "Fit each image": None,
}


class ImageToPdfApp(AppWindow):
    def __init__(self) -> None:
        super().__init__()
        self.title("Paperstack — Images to PDF")
        self.geometry("1040x700")
        self.minsize(840, 580)
        self.configure(bg="#f5f2eb")
        self.files: list[Path] = []
        self.thumbs: list[ImageTk.PhotoImage] = []
        self.page_size = tk.StringVar(value="A4")
        self.orientation = tk.StringVar(value="Portrait")
        self.margin = tk.IntVar(value=80)
        self.quality = tk.IntVar(value=90)
        self.status = tk.StringVar(value="Add images to begin")
        self._style()
        self._build()

    def _style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background="#f5f2eb")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("TLabel", background="#f5f2eb", foreground="#20231f", font=("Segoe UI", 10))
        style.configure("Title.TLabel", font=("Georgia", 26, "bold"), foreground="#193c2d")
        style.configure("Muted.TLabel", foreground="#6d736c")
        style.configure("Card.TLabel", background="#ffffff")
        style.configure("TButton", font=("Segoe UI Semibold", 10), padding=(14, 9))
        style.configure("Primary.TButton", background="#e3673f", foreground="white", borderwidth=0)
        style.map("Primary.TButton", background=[("active", "#cb5331"), ("disabled", "#c9c9c9")])
        style.configure("Tool.TButton", background="#eef2ed", foreground="#193c2d", borderwidth=0, padding=(10, 7))
        style.configure("TCombobox", padding=7)

    def _build(self) -> None:
        header = ttk.Frame(self, padding=(32, 24, 32, 12))
        header.pack(fill="x")
        title_box = ttk.Frame(header)
        title_box.pack(side="left")
        ttk.Label(title_box, text="Paperstack", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_box, text="Turn your images into one tidy PDF — entirely offline.", style="Muted.TLabel").pack(anchor="w", pady=(3, 0))
        self.add_btn = ttk.Button(header, text="＋ Add images", style="Primary.TButton", command=self.add_images)
        self.add_btn.pack(side="right", pady=8)

        body = ttk.Frame(self, padding=(32, 8, 32, 20))
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, style="Card.TFrame", padding=18)
        left.pack(side="left", fill="both", expand=True)
        right = ttk.Frame(body, style="Card.TFrame", padding=22, width=285)
        right.pack(side="right", fill="y", padx=(18, 0))
        right.pack_propagate(False)

        toolbar = ttk.Frame(left, style="Card.TFrame")
        toolbar.pack(fill="x", pady=(0, 12))
        self.count_label = ttk.Label(toolbar, text="0 images", style="Card.TLabel", font=("Segoe UI Semibold", 11))
        self.count_label.pack(side="left")
        ttk.Button(toolbar, text="Remove", style="Tool.TButton", command=self.remove_selected).pack(side="right")
        ttk.Button(toolbar, text="Move down", style="Tool.TButton", command=lambda: self.move(1)).pack(side="right", padx=5)
        ttk.Button(toolbar, text="Move up", style="Tool.TButton", command=lambda: self.move(-1)).pack(side="right")

        list_frame = ttk.Frame(left, style="Card.TFrame")
        list_frame.pack(fill="both", expand=True)
        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, activestyle="none", bd=0, highlightthickness=1,
                                  highlightbackground="#dfe4dd", bg="#fbfcfa", fg="#20231f",
                                  selectbackground="#dceadf", selectforeground="#193c2d", font=("Segoe UI", 11))
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.listbox.bind("<Double-Button-1>", lambda _e: self.preview_selected())
        if DND_FILES is not None:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)

        ttk.Label(right, text="PDF settings", style="Card.TLabel", font=("Segoe UI Semibold", 15)).pack(anchor="w", pady=(0, 18))
        self._field(right, "Page size", ttk.Combobox(right, textvariable=self.page_size, values=list(PAGE_SIZES), state="readonly"))
        self._field(right, "Orientation", ttk.Combobox(right, textvariable=self.orientation, values=["Portrait", "Landscape"], state="readonly"))
        ttk.Label(right, text="Page margin", style="Card.TLabel").pack(anchor="w")
        ttk.Scale(right, from_=0, to=240, variable=self.margin).pack(fill="x", pady=(7, 17))
        ttk.Label(right, text="Image quality", style="Card.TLabel").pack(anchor="w")
        ttk.Scale(right, from_=55, to=100, variable=self.quality).pack(fill="x", pady=(7, 4))
        ttk.Label(right, text="Smaller  ←  →  Sharper", style="Card.TLabel", foreground="#7c827b").pack(fill="x")
        ttk.Separator(right).pack(fill="x", pady=22)
        ttk.Label(right, textvariable=self.status, style="Card.TLabel", foreground="#6d736c", wraplength=235).pack(anchor="w")
        self.export_btn = ttk.Button(right, text="Create PDF", style="Primary.TButton", command=self.export_pdf, state="disabled")
        self.export_btn.pack(side="bottom", fill="x")
        ttk.Label(right, text="Files never leave your computer.", style="Card.TLabel", foreground="#7c827b").pack(side="bottom", pady=(0, 12))

    def _field(self, parent: ttk.Frame, label: str, widget: ttk.Widget) -> None:
        ttk.Label(parent, text=label, style="Card.TLabel").pack(anchor="w")
        widget.pack(fill="x", pady=(7, 17))

    def add_images(self) -> None:
        chosen = filedialog.askopenfilenames(title="Choose images", filetypes=IMAGE_TYPES)
        self._append_images(chosen)

    def _append_images(self, names) -> None:
        existing = {str(p.resolve()).lower() for p in self.files}
        for name in names:
            path = Path(name)
            key = str(path.resolve()).lower()
            if path.is_file() and path.suffix.lower() in SUPPORTED_EXTENSIONS and key not in existing:
                self.files.append(path)
                existing.add(key)
        self.refresh()

    def _on_drop(self, event) -> str:
        self._append_images(self.tk.splitlist(event.data))
        return "break"

    def refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        for i, path in enumerate(self.files, 1):
            try:
                with Image.open(path) as im:
                    size = f"{im.width} × {im.height}"
            except Exception:
                size = "unreadable"
            self.listbox.insert(tk.END, f"  {i:02d}     {path.name}     ·     {size}")
        n = len(self.files)
        self.count_label.config(text=f"{n} image{'s' if n != 1 else ''}")
        empty_hint = "Add images or drag and drop them here" if DND_FILES is not None else "Add images to begin"
        self.status.set(f"Ready to create a {n}-page PDF" if n else empty_hint)
        self.export_btn.config(state="normal" if n else "disabled")

    def remove_selected(self) -> None:
        for index in reversed(self.listbox.curselection()):
            self.files.pop(index)
        self.refresh()

    def move(self, offset: int) -> None:
        selected = list(self.listbox.curselection())
        if len(selected) != 1:
            return
        old = selected[0]
        new = old + offset
        if 0 <= new < len(self.files):
            self.files[old], self.files[new] = self.files[new], self.files[old]
            self.refresh()
            self.listbox.selection_set(new)

    def preview_selected(self) -> None:
        selected = self.listbox.curselection()
        if not selected:
            return
        try:
            with Image.open(self.files[selected[0]]) as source:
                im = ImageOps.exif_transpose(source).convert("RGB")
                im.thumbnail((720, 520))
                photo = ImageTk.PhotoImage(im)
            win = tk.Toplevel(self)
            win.title(self.files[selected[0]].name)
            win.configure(bg="#20231f")
            label = tk.Label(win, image=photo, bg="#20231f", padx=18, pady=18)
            label.image = photo
            label.pack()
        except Exception as exc:
            messagebox.showerror("Preview unavailable", str(exc))

    def _make_page(self, path: Path) -> Image.Image:
        with Image.open(path) as source:
            image = ImageOps.exif_transpose(source)
            if image.mode in ("RGBA", "LA") or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, "white")
                image = Image.alpha_composite(background, rgba).convert("RGB")
            else:
                image = image.convert("RGB")

        page_spec = PAGE_SIZES[self.page_size.get()]
        if page_spec is None:
            margin = max(0, int(self.margin.get()))
            width, height = image.width + margin * 2, image.height + margin * 2
        else:
            width, height = page_spec
            if self.orientation.get() == "Landscape":
                width, height = height, width
            margin = min(max(0, int(self.margin.get())), width // 3, height // 3)
        available = (width - margin * 2, height - margin * 2)
        # Fit to the available area in either direction. `thumbnail()` only
        # shrinks images, so small images previously remained small on the page.
        scale = min(available[0] / image.width, available[1] / image.height)
        fitted_size = (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        )
        image = image.resize(fitted_size, Image.Resampling.LANCZOS)
        page = Image.new("RGB", (width, height), "white")
        page.paste(image, ((width - image.width) // 2, (height - image.height) // 2))
        return page

    def export_pdf(self) -> None:
        destination = filedialog.asksaveasfilename(title="Save PDF", defaultextension=".pdf",
                                                   filetypes=[("PDF document", "*.pdf")], initialfile="images.pdf")
        if not destination:
            return
        self.export_btn.config(state="disabled", text="Creating…")
        self.status.set("Processing images…")
        self.update_idletasks()
        pages: list[Image.Image] = []
        try:
            for path in self.files:
                pages.append(self._make_page(path))
            pages[0].save(destination, "PDF", save_all=True, append_images=pages[1:],
                          resolution=300.0, quality=int(self.quality.get()), optimize=True)
            size_mb = os.path.getsize(destination) / (1024 * 1024)
            self.status.set(f"Saved {len(pages)} pages · {size_mb:.1f} MB")
            if messagebox.askyesno("PDF created", f"Your PDF was saved successfully.\n\n{destination}\n\nOpen it now?"):
                os.startfile(destination)
        except Exception as exc:
            self.status.set("Could not create the PDF")
            messagebox.showerror("Export failed", f"The PDF could not be created:\n\n{exc}")
        finally:
            for page in pages:
                page.close()
            self.export_btn.config(state="normal", text="Create PDF")


if __name__ == "__main__":
    ImageToPdfApp().mainloop()
