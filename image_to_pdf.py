"""A small, offline desktop app for combining images into one PDF."""

from __future__ import annotations

import os
import json
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


def load_page_sizes() -> dict[str, tuple[int, int] | None]:
    config_path = Path(__file__).with_name("paper_sizes.json")
    fallback = {"A4": (2480, 3508), "Letter": (2550, 3300)}
    try:
        with config_path.open("r", encoding="utf-8") as config_file:
            configured = json.load(config_file)
        sizes = {
            name: (int(dimensions[0]), int(dimensions[1]))
            for name, dimensions in configured.items()
            if isinstance(name, str) and isinstance(dimensions, list) and len(dimensions) == 2
        }
    except (OSError, ValueError, TypeError):
        sizes = fallback
    sizes["Fit each image"] = None
    return sizes


PAGE_SIZES = load_page_sizes()


class ImageToPdfApp(AppWindow):
    def __init__(self) -> None:
        super().__init__()
        self.title("Paperstack — Images to PDF")
        self.geometry("1040x700")
        self.minsize(840, 580)
        self.configure(bg="#f5f2eb")
        self.files: list[Path] = []
        self.thumbs: list[ImageTk.PhotoImage] = []
        self.adjustments: dict[str, dict[str, float]] = {}
        self.selected_index: int | None = None
        self.preview_photo: ImageTk.PhotoImage | None = None
        self.image_scale = tk.DoubleVar(value=100)
        self.image_x = tk.DoubleVar(value=0)
        self.image_y = tk.DoubleVar(value=0)
        self.page_size = tk.StringVar(value="A4")
        self.orientation = tk.StringVar(value="Portrait")
        self.page_dimensions = tk.StringVar(value="210.0 × 297.0 mm / 8.27 × 11.69 in")
        self.margin = tk.IntVar(value=0)
        self.margin_display = tk.StringVar(value="0.0 mm / 0.00 in")
        self.quality = tk.IntVar(value=90)
        self.status = tk.StringVar(value="Add images to begin")
        self._style()
        self._build()
        for variable in (self.page_size, self.orientation, self.margin):
            variable.trace_add("write", lambda *_args: self._render_page_preview())
        for variable in (self.page_size, self.orientation):
            variable.trace_add("write", lambda *_args: self._update_page_dimensions())
        self.margin.trace_add("write", lambda *_args: self._update_margin_display())

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
        style.configure("Reset.TButton", background="#eef2ed", foreground="#193c2d", borderwidth=0,
                        padding=(2, 1), font=("Segoe UI Symbol", 9))
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

        workspace = tk.PanedWindow(left, orient=tk.VERTICAL, sashwidth=8, sashrelief=tk.FLAT,
                                   bg="#dfe4dd", bd=0, showhandle=True, opaqueresize=True)
        workspace.pack(fill="both", expand=True)
        list_frame = ttk.Frame(workspace, style="Card.TFrame")
        self.listbox = tk.Listbox(list_frame, selectmode=tk.EXTENDED, activestyle="none", bd=0, highlightthickness=1,
                                  highlightbackground="#dfe4dd", bg="#fbfcfa", fg="#20231f",
                                  selectbackground="#dceadf", selectforeground="#193c2d", font=("Segoe UI", 11))
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.listbox.yview)
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self._select_image)
        if DND_FILES is not None:
            self.listbox.drop_target_register(DND_FILES)
            self.listbox.dnd_bind("<<Drop>>", self._on_drop)

        editor = ttk.Frame(workspace, style="Card.TFrame", padding=(0, 10, 0, 0))
        workspace.add(list_frame, minsize=110, stretch="always")
        workspace.add(editor, minsize=170, stretch="always")
        self.preview_canvas = tk.Canvas(editor, width=280, bg="#eef0eb", bd=0, highlightthickness=0)
        self.preview_canvas.pack(side="left", fill="both", expand=True)
        self.preview_canvas.bind("<Configure>", lambda _event: self._render_page_preview())
        controls = ttk.Frame(editor, style="Card.TFrame", padding=(18, 3, 0, 0))
        controls.pack(side="left", fill="both", expand=True)
        self.editor_title = ttk.Label(controls, text="Select an image to adjust it", style="Card.TLabel",
                                      font=("Segoe UI Semibold", 11))
        self.editor_title.pack(anchor="w", pady=(0, 8))
        self._adjustment_slider(controls, "Scale", self.image_scale, 10, 1000, 100)
        self._adjustment_slider(controls, "Horizontal position", self.image_x, -100, 100, 0)
        self._adjustment_slider(controls, "Vertical position", self.image_y, -100, 100, 0)
        presets = ttk.Frame(controls, style="Card.TFrame")
        presets.pack(fill="x", pady=(9, 2))
        for label, mode in (("Fit page", "page"), ("Fit width", "width"),
                            ("Fit height", "height"), ("Default size", "native")):
            ttk.Button(presets, text=label, style="Tool.TButton",
                       command=lambda selected=mode: self._apply_fit(selected)).pack(side="left", padx=(0, 4))

        align_row = ttk.Frame(controls, style="Card.TFrame")
        align_row.pack(fill="x", pady=(5, 0))
        ttk.Label(align_row, text="Align", style="Card.TLabel", width=8).pack(side="left")
        for symbol, horizontal, vertical in (
            ("↖", -1, -1), ("↑", 0, -1), ("↗", 1, -1),
            ("←", -1, 0), ("●", 0, 0), ("→", 1, 0),
            ("↙", -1, 1), ("↓", 0, 1), ("↘", 1, 1),
        ):
            ttk.Button(align_row, text=symbol, width=2, style="Reset.TButton",
                       command=lambda h=horizontal, v=vertical: self._apply_alignment(h, v)).pack(side="left", padx=1)

        ttk.Label(right, text="PDF settings", style="Card.TLabel", font=("Segoe UI Semibold", 15)).pack(anchor="w", pady=(0, 18))
        self._field(right, "Page size", ttk.Combobox(right, textvariable=self.page_size, values=list(PAGE_SIZES), state="readonly"))
        ttk.Label(right, textvariable=self.page_dimensions, style="Card.TLabel", foreground="#6d736c",
                  wraplength=235).pack(anchor="w", pady=(0, 17))
        self._field(right, "Orientation", ttk.Combobox(right, textvariable=self.orientation, values=["Portrait", "Landscape"], state="readonly"))
        margin_header = ttk.Frame(right, style="Card.TFrame")
        margin_header.pack(fill="x")
        ttk.Label(margin_header, text="Page margin", style="Card.TLabel").pack(side="left")
        ttk.Button(margin_header, text="↺", width=2, style="Reset.TButton",
                   command=lambda: self.margin.set(0)).pack(side="right")
        ttk.Label(margin_header, textvariable=self.margin_display, style="Card.TLabel",
                  foreground="#6d736c").pack(side="right", padx=(0, 7))
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

    def _update_margin_display(self) -> None:
        pixels = round(float(self.margin.get()))
        inches = pixels / 300.0
        millimetres = inches * 25.4
        self.margin_display.set(f"{millimetres:.1f} mm / {inches:.2f} in")

    def _update_page_dimensions(self) -> None:
        dimensions = PAGE_SIZES.get(self.page_size.get())
        if dimensions is None:
            self.page_dimensions.set("Matches each source image")
            return
        width, height = dimensions
        if self.orientation.get() == "Landscape":
            width, height = height, width
        width_in, height_in = width / 300.0, height / 300.0
        self.page_dimensions.set(
            f"{width_in * 25.4:.1f} × {height_in * 25.4:.1f} mm / "
            f"{width_in:.2f} × {height_in:.2f} in"
        )

    def _adjustment_slider(self, parent, label, variable, start, end, default) -> None:
        row = ttk.Frame(parent, style="Card.TFrame")
        row.pack(fill="x", pady=3)
        ttk.Label(row, text=label, style="Card.TLabel", width=18).pack(side="left")
        ttk.Scale(
            row, from_=start, to=end, variable=variable,
            command=lambda raw, target=variable: self._adjust_selected(target, raw),
        ).pack(side="left", fill="x", expand=True)
        ttk.Label(row, textvariable=variable, style="Card.TLabel", width=6).pack(side="right", padx=(8, 0))
        ttk.Button(
            row, text="↺", width=2, style="Reset.TButton",
            command=lambda target=variable, value=default: self._reset_adjustment(target, value),
        ).pack(side="right", padx=(6, 0))

    def _reset_adjustment(self, variable, default) -> None:
        variable.set(default)
        self._adjust_selected()

    def _layout_metrics(self, path: Path) -> tuple[int, int, int, int, int, int]:
        with Image.open(path) as source:
            image_width, image_height = ImageOps.exif_transpose(source).size
        page_spec = PAGE_SIZES[self.page_size.get()]
        if page_spec is None:
            margin = max(0, int(self.margin.get()))
            page_width, page_height = image_width + margin * 2, image_height + margin * 2
        else:
            page_width, page_height = page_spec
            if self.orientation.get() == "Landscape":
                page_width, page_height = page_height, page_width
            margin = min(max(0, int(self.margin.get())), page_width // 3, page_height // 3)
        return image_width, image_height, page_width, page_height, page_width - margin * 2, page_height - margin * 2

    def _apply_fit(self, mode: str) -> None:
        if self.selected_index is None or self.selected_index >= len(self.files):
            return
        iw, ih, _pw, _ph, aw, ah = self._layout_metrics(self.files[self.selected_index])
        base_scale = min(aw / iw, ah / ih)
        target_scale = {
            "page": base_scale,
            "width": aw / iw,
            "height": ah / ih,
            "native": 1.0,
        }[mode]
        self.image_scale.set(round(target_scale / base_scale * 100))
        self._adjust_selected()

    def _apply_alignment(self, horizontal: int, vertical: int) -> None:
        if self.selected_index is None or self.selected_index >= len(self.files):
            return
        iw, ih, _pw, _ph, aw, ah = self._layout_metrics(self.files[self.selected_index])
        base_scale = min(aw / iw, ah / ih) * self.image_scale.get() / 100.0
        rendered_width, rendered_height = iw * base_scale, ih * base_scale
        x_value = horizontal * (aw - rendered_width) / aw * 100 if aw else 0
        y_value = vertical * (ah - rendered_height) / ah * 100 if ah else 0
        self.image_x.set(round(x_value))
        self.image_y.set(round(y_value))
        self._adjust_selected()

    def _adjustment_for(self, path: Path) -> dict[str, float]:
        return self.adjustments.setdefault(str(path.resolve()).lower(), {"scale": 100.0, "x": 0.0, "y": 0.0})

    def _select_image(self, _event=None) -> None:
        selected = self.listbox.curselection()
        if not selected:
            return
        self.selected_index = selected[0]
        values = self._adjustment_for(self.files[self.selected_index])
        self.image_scale.set(values["scale"])
        self.image_x.set(values["x"])
        self.image_y.set(values["y"])
        self.editor_title.config(text=self.files[self.selected_index].name)
        self._render_page_preview()

    def _adjust_selected(self, changed_variable=None, raw_value=None) -> None:
        if changed_variable is not None and raw_value is not None:
            changed_variable.set(round(float(raw_value)))
        if self.selected_index is None or self.selected_index >= len(self.files):
            return
        values = self._adjustment_for(self.files[self.selected_index])
        values.update(
            scale=round(self.image_scale.get()),
            x=round(self.image_x.get()),
            y=round(self.image_y.get()),
        )
        self._render_page_preview()

    def _render_page_preview(self) -> None:
        if self.selected_index is None or self.selected_index >= len(self.files):
            return
        try:
            page = self._make_page(self.files[self.selected_index], preview=True)
            canvas_width = max(80, self.preview_canvas.winfo_width())
            canvas_height = max(80, self.preview_canvas.winfo_height())
            page.thumbnail((canvas_width - 24, canvas_height - 24), Image.Resampling.LANCZOS)
            self.preview_photo = ImageTk.PhotoImage(page)
            self.preview_canvas.delete("all")
            center_x, center_y = canvas_width // 2, canvas_height // 2
            self.preview_canvas.create_rectangle(
                center_x - page.width // 2 + 4, center_y - page.height // 2 + 4,
                center_x + page.width // 2 + 4, center_y + page.height // 2 + 4,
                fill="#cfd4cd", outline="",
            )
            self.preview_canvas.create_image(center_x, center_y, image=self.preview_photo)
        except Exception:
            pass

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
            self.adjustments.pop(str(self.files[index].resolve()).lower(), None)
            self.files.pop(index)
        self.selected_index = None
        self.preview_canvas.delete("all")
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

    def _make_page(self, path: Path, preview: bool = False) -> Image.Image:
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
        settings = self._adjustment_for(path)
        scale = min(available[0] / image.width, available[1] / image.height)
        scale *= settings["scale"] / 100.0
        fitted_size = (
            max(1, round(image.width * scale)),
            max(1, round(image.height * scale)),
        )
        image = image.resize(fitted_size, Image.Resampling.LANCZOS)
        page = Image.new("RGB", (width, height), "white")
        offset_x = round(settings["x"] / 100.0 * available[0] / 2)
        offset_y = round(settings["y"] / 100.0 * available[1] / 2)
        position = ((width - image.width) // 2 + offset_x, (height - image.height) // 2 + offset_y)
        page.paste(image, position)
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
