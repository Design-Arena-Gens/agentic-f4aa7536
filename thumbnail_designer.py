import json
import uuid
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

try:
    import tkinter as tk
    from tkinter import colorchooser, filedialog, messagebox, ttk
except ImportError as exc:  # pragma: no cover - environment-specific
    raise SystemExit(
        "Tkinter tidak tersedia di lingkungan Python ini. "
        "Instal paket python3-tk / tk sesuai OS untuk menjalankan aplikasi GUI."
    ) from exc

from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps, ImageTk


ASSETS_DIR = Path(__file__).parent / "assets"
FONTS_DIR = ASSETS_DIR / "fonts"


def clamp(value: float, min_value: float, max_value: float) -> float:
    return max(min_value, min(value, max_value))


def ensure_font_path(font_file: str) -> Path:
    font_path = FONTS_DIR / font_file
    if not font_path.exists():
        raise FileNotFoundError(f"Missing font file: {font_path}")
    return font_path


def hex_to_rgba(hex_color: str, alpha: float = 1.0) -> Tuple[int, int, int, int]:
    rgb = ImageColor.getrgb(hex_color)
    return rgb[0], rgb[1], rgb[2], int(clamp(alpha, 0, 1) * 255)


@dataclass
class GradientSettings:
    start_color: str = "#ff3838"
    end_color: str = "#ffcf00"
    direction: str = "horizontal"  # horizontal | vertical | diagonal


@dataclass
class BackgroundSettings:
    mode: str = "solid"  # solid | gradient | image
    solid_color: str = "#202020"
    gradient: GradientSettings = field(default_factory=GradientSettings)
    image_path: Optional[str] = None
    blur_radius: float = 0.0
    brightness: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0


@dataclass
class ShadowSettings:
    enabled: bool = True
    offset_x: int = 6
    offset_y: int = 6
    blur_radius: int = 12
    color: str = "#000000"
    opacity: float = 0.6


@dataclass
class StrokeSettings:
    width: int = 6
    color: str = "#ffffff"


@dataclass
class TextLayer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = "Judul Utama"
    text: str = "Judul Thumbnail Menarik"
    font_file: str = "Montserrat-ExtraBold.ttf"
    font_size: int = 150
    color: str = "#ffffff"
    align: str = "center"  # left | center | right
    position_x: float = 0.5  # 0..1 relative
    position_y: float = 0.35
    max_width: float = 0.9  # relative
    tracking: int = 0
    rotation: float = 0.0
    shadow: ShadowSettings = field(default_factory=ShadowSettings)
    stroke: StrokeSettings = field(default_factory=StrokeSettings)


@dataclass
class ImageLayer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = "Gambar"
    image_path: Optional[str] = None
    scale: float = 1.0
    rotation: float = 0.0
    position_x: float = 0.75
    position_y: float = 0.65
    opacity: float = 1.0
    flip_horizontal: bool = False
    flip_vertical: bool = False
    add_shadow: bool = True
    shadow_blur: int = 24
    shadow_offset_x: int = 0
    shadow_offset_y: int = 12
    shadow_opacity: float = 0.7


@dataclass
class OverlayLayer:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    label: str = "Highlight"
    mode: str = "rectangle"  # rectangle | circle | banner
    color: str = "#ff3838"
    opacity: float = 0.85
    position_x: float = 0.5
    position_y: float = 0.3
    width: float = 0.8
    height: float = 0.25
    blur_radius: int = 0
    rotation: float = 0.0
    rounded: int = 40


def create_background_settings(data: Optional[Dict] = None) -> BackgroundSettings:
    if not data:
        return BackgroundSettings()
    payload = dict(data)
    gradient = payload.get("gradient")
    if isinstance(gradient, dict):
        payload["gradient"] = GradientSettings(**gradient)
    elif not isinstance(gradient, GradientSettings):
        payload["gradient"] = GradientSettings()
    return BackgroundSettings(**payload)


def create_text_layer(data: Optional[Dict] = None) -> TextLayer:
    if not data:
        return TextLayer()
    payload = dict(data)
    shadow = payload.get("shadow")
    if isinstance(shadow, dict):
        payload["shadow"] = ShadowSettings(**shadow)
    elif not isinstance(shadow, ShadowSettings):
        payload["shadow"] = ShadowSettings()
    stroke = payload.get("stroke")
    if isinstance(stroke, dict):
        payload["stroke"] = StrokeSettings(**stroke)
    elif not isinstance(stroke, StrokeSettings):
        payload["stroke"] = StrokeSettings()
    return TextLayer(**payload)


def create_image_layer(data: Optional[Dict] = None) -> ImageLayer:
    if not data:
        return ImageLayer()
    payload = dict(data)
    return ImageLayer(**payload)


def create_overlay_layer(data: Optional[Dict] = None) -> OverlayLayer:
    if not data:
        return OverlayLayer()
    payload = dict(data)
    return OverlayLayer(**payload)


class ThumbnailDesigner(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("YouTube Thumbnail Designer - Pro Toolkit")
        self.geometry("1320x840")
        self.minsize(1180, 720)

        self.base_width = 1280
        self.base_height = 720
        self.preview_width = 640
        self.preview_height = 360

        self.background = BackgroundSettings()
        self.text_layers: List[TextLayer] = []
        self.image_layers: List[ImageLayer] = []
        self.overlay_layers: List[OverlayLayer] = []

        self.current_text_id: Optional[str] = None
        self.current_image_id: Optional[str] = None
        self.current_overlay_id: Optional[str] = None

        self.layer_order: List[Tuple[str, str]] = []  # list of (layer_type, id)

        self._setup_fonts()
        self._setup_ui()
        self._add_default_layers()

        self.render_thumbnail()

    def _setup_fonts(self) -> None:
        family_map = {}
        for font_file in sorted(FONTS_DIR.glob("*.ttf")):
            try:
                font = ImageFont.truetype(str(font_file), size=64)
                family_map[font_file.name] = font_file.stem.replace("-", " ")
            except OSError:
                continue
        if not family_map:
            raise RuntimeError("Tidak ada font yang tersedia. Pastikan folder assets/fonts berisi file .ttf.")
        self.font_options = family_map

    def _setup_ui(self) -> None:
        root_pane = ttk.Panedwindow(self, orient=tk.HORIZONTAL)
        root_pane.pack(fill=tk.BOTH, expand=True)

        controls_frame = ttk.Frame(root_pane, padding=14)
        preview_frame = ttk.Frame(root_pane, padding=12)

        root_pane.add(controls_frame, weight=1)
        root_pane.add(preview_frame, weight=1)

        self._build_controls(controls_frame)
        self._build_preview(preview_frame)

    def _build_controls(self, parent: ttk.Frame) -> None:
        notebook = ttk.Notebook(parent)
        notebook.pack(fill=tk.BOTH, expand=True)

        background_tab = ttk.Frame(notebook, padding=10)
        text_tab = ttk.Frame(notebook, padding=10)
        overlays_tab = ttk.Frame(notebook, padding=10)
        images_tab = ttk.Frame(notebook, padding=10)
        effects_tab = ttk.Frame(notebook, padding=10)

        notebook.add(background_tab, text="Latar")
        notebook.add(text_tab, text="Teks")
        notebook.add(overlays_tab, text="Highlight")
        notebook.add(images_tab, text="Gambar")
        notebook.add(effects_tab, text="Efek")

        self._build_background_tab(background_tab)
        self._build_text_tab(text_tab)
        self._build_overlay_tab(overlays_tab)
        self._build_images_tab(images_tab)
        self._build_effects_tab(effects_tab)

    def _build_preview(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Pratinjau 1280x720").pack(anchor=tk.W)
        canvas_wrapper = ttk.Frame(parent, borderwidth=1, relief=tk.SOLID, padding=4)
        canvas_wrapper.pack(fill=tk.BOTH, expand=True)

        self.preview_canvas = tk.Canvas(
            canvas_wrapper,
            width=self.preview_width,
            height=self.preview_height,
            bg="#111111",
            highlightthickness=0,
        )
        self.preview_canvas.pack()

        buttons_frame = ttk.Frame(parent, padding=(0, 12, 0, 0))
        buttons_frame.pack(fill=tk.X)

        ttk.Button(buttons_frame, text="Ekspor PNG...", command=self.export_thumbnail).pack(side=tk.LEFT)
        ttk.Button(buttons_frame, text="Simpan workspace...", command=self.save_workspace).pack(side=tk.LEFT, padx=8)
        ttk.Button(buttons_frame, text="Muat workspace...", command=self.load_workspace).pack(side=tk.LEFT)

    def _build_background_tab(self, parent: ttk.Frame) -> None:
        mode_frame = ttk.Labelframe(parent, text="Mode Latar", padding=8)
        mode_frame.pack(fill=tk.X, pady=(0, 8))

        mode_var = tk.StringVar(value=self.background.mode)
        mode_var.trace_add("write", lambda *_: self._update_background_mode(mode_var.get()))

        ttk.Radiobutton(mode_frame, text="Solid", variable=mode_var, value="solid").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Gradient", variable=mode_var, value="gradient").pack(anchor=tk.W)
        ttk.Radiobutton(mode_frame, text="Gambar", variable=mode_var, value="image").pack(anchor=tk.W)

        solid_frame = ttk.Labelframe(parent, text="Solid", padding=8)
        solid_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(
            solid_frame,
            text="Pilih Warna...",
            command=lambda: self._choose_color("background_solid", self.background.solid_color),
        ).pack(anchor=tk.W)

        gradient_frame = ttk.Labelframe(parent, text="Gradient", padding=8)
        gradient_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(
            gradient_frame,
            text="Warna Awal...",
            command=lambda: self._choose_color("gradient_start", self.background.gradient.start_color),
        ).pack(anchor=tk.W)

        ttk.Button(
            gradient_frame,
            text="Warna Akhir...",
            command=lambda: self._choose_color("gradient_end", self.background.gradient.end_color),
        ).pack(anchor=tk.W, pady=(6, 0))

        direction_var = tk.StringVar(value=self.background.gradient.direction)
        direction_var.trace_add("write", lambda *_: self._set_gradient_direction(direction_var.get()))

        direction_combo = ttk.Combobox(
            gradient_frame,
            state="readonly",
            values=["horizontal", "vertical", "diagonal"],
            textvariable=direction_var,
        )
        direction_combo.pack(fill=tk.X, pady=(6, 0))

        image_frame = ttk.Labelframe(parent, text="Gambar", padding=8)
        image_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Button(image_frame, text="Pilih Gambar Latar...", command=self._load_background_image).pack(anchor=tk.W)
        ttk.Button(image_frame, text="Hapus Gambar", command=self._clear_background_image).pack(anchor=tk.W, pady=(6, 0))

        slider_frame = ttk.Labelframe(parent, text="Koreksi", padding=8)
        slider_frame.pack(fill=tk.X)

        self._add_labeled_slider(
            slider_frame,
            "Blur",
            0,
            20,
            self.background.blur_radius,
            lambda value: self._set_background_numeric("blur_radius", float(value)),
        )
        self._add_labeled_slider(
            slider_frame,
            "Brightness",
            0.5,
            1.5,
            self.background.brightness,
            lambda value: self._set_background_numeric("brightness", float(value)),
        )
        self._add_labeled_slider(
            slider_frame,
            "Kontras",
            0.5,
            1.6,
            self.background.contrast,
            lambda value: self._set_background_numeric("contrast", float(value)),
        )
        self._add_labeled_slider(
            slider_frame,
            "Saturasi",
            0.2,
            1.8,
            self.background.saturation,
            lambda value: self._set_background_numeric("saturation", float(value)),
        )

    def _build_text_tab(self, parent: ttk.Frame) -> None:
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.X)

        self.text_list = tk.Listbox(list_frame, height=5)
        self.text_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.text_list.bind("<<ListboxSelect>>", self._on_text_select)

        buttons = ttk.Frame(list_frame)
        buttons.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="+", width=4, command=self._add_text_layer).pack(pady=(0, 4))
        ttk.Button(buttons, text="Duplikat", width=8, command=self._duplicate_text_layer).pack(pady=(0, 4))
        ttk.Button(buttons, text="Hapus", width=8, command=self._remove_text_layer).pack()

        self.text_controls = ttk.Frame(parent)
        self.text_controls.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        # Text entry
        ttk.Label(self.text_controls, text="Teks").grid(row=0, column=0, sticky=tk.W)
        self.text_entry = tk.Text(self.text_controls, height=3)
        self.text_entry.grid(row=1, column=0, columnspan=3, sticky="nsew")
        self.text_entry.bind("<KeyRelease>", lambda event: self._update_current_text("text", self.text_entry.get("1.0", tk.END).strip()))

        # Font selection
        ttk.Label(self.text_controls, text="Font").grid(row=2, column=0, pady=(8, 0), sticky=tk.W)
        self.font_var = tk.StringVar()
        font_combo = ttk.Combobox(
            self.text_controls, textvariable=self.font_var, state="readonly", values=list(self.font_options.values())
        )
        font_combo.grid(row=3, column=0, sticky="ew")
        font_combo.bind("<<ComboboxSelected>>", lambda *_: self._change_text_font())

        ttk.Label(self.text_controls, text="Ukuran").grid(row=2, column=1, pady=(8, 0), sticky=tk.W)
        self.font_size_var = tk.IntVar(value=120)
        font_size_spin = ttk.Spinbox(self.text_controls, from_=40, to=280, textvariable=self.font_size_var, increment=4)
        font_size_spin.grid(row=3, column=1, sticky="ew")
        font_size_spin.bind("<KeyRelease>", lambda *_: self._change_text_size())
        font_size_spin.bind("<<Increment>>", lambda *_: self._change_text_size())
        font_size_spin.bind("<<Decrement>>", lambda *_: self._change_text_size())

        ttk.Label(self.text_controls, text="Align").grid(row=2, column=2, pady=(8, 0), sticky=tk.W)
        self.align_var = tk.StringVar()
        align_combo = ttk.Combobox(self.text_controls, state="readonly", textvariable=self.align_var, values=["left", "center", "right"])
        align_combo.grid(row=3, column=2, sticky="ew")
        align_combo.bind("<<ComboboxSelected>>", lambda *_: self._update_current_text("align", self.align_var.get()))

        # Color buttons
        ttk.Button(
            self.text_controls,
            text="Warna Teks...",
            command=lambda: self._choose_color("text_color", self._get_current_text().color),
        ).grid(row=4, column=0, pady=(8, 0), sticky="ew")
        ttk.Button(
            self.text_controls,
            text="Warna Stroke...",
            command=lambda: self._choose_color("stroke_color", self._get_current_text().stroke.color),
        ).grid(row=4, column=1, pady=(8, 0), sticky="ew")
        ttk.Button(
            self.text_controls,
            text="Warna Shadow...",
            command=lambda: self._choose_color("shadow_color", self._get_current_text().shadow.color),
        ).grid(row=4, column=2, pady=(8, 0), sticky="ew")

        # Sliders
        self._add_labeled_slider(
            self.text_controls,
            "Stroke",
            0,
            20,
            6,
            lambda value: self._update_current_text("stroke_width", int(float(value))),
            row=5,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Tracking",
            -40,
            120,
            0,
            lambda value: self._update_current_text("tracking", int(float(value))),
            row=6,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Rotasi",
            -45,
            45,
            0,
            lambda value: self._update_current_text("rotation", float(value)),
            row=7,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Posisi X",
            0.05,
            0.95,
            0.5,
            lambda value: self._update_current_text("position_x", float(value)),
            row=8,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Posisi Y",
            0.05,
            0.95,
            0.35,
            lambda value: self._update_current_text("position_y", float(value)),
            row=9,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Lebar Maks",
            0.3,
            1.0,
            0.9,
            lambda value: self._update_current_text("max_width", float(value)),
            row=10,
        )

        self.shadow_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.text_controls,
            text="Aktifkan Shadow",
            command=self._toggle_text_shadow,
            variable=self.shadow_var,
        ).grid(row=11, column=0, pady=(8, 0), sticky=tk.W)

        self._add_labeled_slider(
            self.text_controls,
            "Shadow X",
            -40,
            40,
            6,
            lambda value: self._update_shadow_value("offset_x", int(float(value))),
            row=12,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Shadow Y",
            -40,
            40,
            6,
            lambda value: self._update_shadow_value("offset_y", int(float(value))),
            row=13,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Shadow Blur",
            0,
            50,
            12,
            lambda value: self._update_shadow_value("blur_radius", int(float(value))),
            row=14,
        )
        self._add_labeled_slider(
            self.text_controls,
            "Shadow Opacity",
            0.0,
            1.0,
            0.6,
            lambda value: self._update_shadow_value("opacity", float(value)),
            row=15,
        )

        for i in range(3):
            self.text_controls.columnconfigure(i, weight=1)
        for j in range(16):
            self.text_controls.rowconfigure(j, weight=0)
        self.text_controls.rowconfigure(1, weight=1)

    def _build_overlay_tab(self, parent: ttk.Frame) -> None:
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.X)

        self.overlay_list = tk.Listbox(list_frame, height=5)
        self.overlay_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.overlay_list.bind("<<ListboxSelect>>", self._on_overlay_select)

        buttons = ttk.Frame(list_frame)
        buttons.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="+", width=4, command=self._add_overlay_layer).pack(pady=(0, 4))
        ttk.Button(buttons, text="Duplikat", width=8, command=self._duplicate_overlay_layer).pack(pady=(0, 4))
        ttk.Button(buttons, text="Hapus", width=8, command=self._remove_overlay_layer).pack()

        self.overlay_controls = ttk.Frame(parent)
        self.overlay_controls.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        ttk.Label(self.overlay_controls, text="Mode").grid(row=0, column=0, sticky=tk.W)
        self.overlay_mode_var = tk.StringVar()
        overlay_mode_combo = ttk.Combobox(
            self.overlay_controls,
            textvariable=self.overlay_mode_var,
            state="readonly",
            values=["rectangle", "circle", "banner"],
        )
        overlay_mode_combo.grid(row=1, column=0, sticky="ew")
        overlay_mode_combo.bind("<<ComboboxSelected>>", lambda *_: self._update_overlay("mode", self.overlay_mode_var.get()))

        ttk.Button(
            self.overlay_controls,
            text="Warna Overlay...",
            command=lambda: self._choose_color("overlay_color", self._get_current_overlay().color),
        ).grid(row=1, column=1, padx=(8, 0), sticky="ew")

        self._add_labeled_slider(
            self.overlay_controls,
            "Opacity",
            0.1,
            1.0,
            0.85,
            lambda value: self._update_overlay("opacity", float(value)),
            row=2,
        )
        self._add_labeled_slider(
            self.overlay_controls,
            "Posisi X",
            0.0,
            1.0,
            0.5,
            lambda value: self._update_overlay("position_x", float(value)),
            row=3,
        )
        self._add_labeled_slider(
            self.overlay_controls,
            "Posisi Y",
            0.0,
            1.0,
            0.3,
            lambda value: self._update_overlay("position_y", float(value)),
            row=4,
        )
        self._add_labeled_slider(
            self.overlay_controls,
            "Lebar",
            0.1,
            1.2,
            0.8,
            lambda value: self._update_overlay("width", float(value)),
            row=5,
        )
        self._add_labeled_slider(
            self.overlay_controls,
            "Tinggi",
            0.05,
            1.0,
            0.25,
            lambda value: self._update_overlay("height", float(value)),
            row=6,
        )
        self._add_labeled_slider(
            self.overlay_controls,
            "Rotasi",
            -45,
            45,
            0,
            lambda value: self._update_overlay("rotation", float(value)),
            row=7,
        )
        self._add_labeled_slider(
            self.overlay_controls,
            "Blur",
            0,
            60,
            0,
            lambda value: self._update_overlay("blur_radius", int(float(value))),
            row=8,
        )
        self._add_labeled_slider(
            self.overlay_controls,
            "Rounded",
            0,
            150,
            40,
            lambda value: self._update_overlay("rounded", int(float(value))),
            row=9,
        )

        for column in range(2):
            self.overlay_controls.columnconfigure(column, weight=1)

    def _build_images_tab(self, parent: ttk.Frame) -> None:
        list_frame = ttk.Frame(parent)
        list_frame.pack(fill=tk.X)

        self.image_list = tk.Listbox(list_frame, height=5)
        self.image_list.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.image_list.bind("<<ListboxSelect>>", self._on_image_select)

        buttons = ttk.Frame(list_frame)
        buttons.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(buttons, text="+", width=4, command=self._add_image_layer).pack(pady=(0, 4))
        ttk.Button(buttons, text="Duplikat", width=8, command=self._duplicate_image_layer).pack(pady=(0, 4))
        ttk.Button(buttons, text="Hapus", width=8, command=self._remove_image_layer).pack()

        self.image_controls = ttk.Frame(parent)
        self.image_controls.pack(fill=tk.BOTH, expand=True, pady=(12, 0))

        ttk.Button(self.image_controls, text="Pilih Gambar...", command=self._change_image_path).grid(
            row=0, column=0, columnspan=2, sticky="ew"
        )
        self.image_shadow_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            self.image_controls,
            text="Shadow",
            command=self._toggle_image_shadow,
            variable=self.image_shadow_var,
        ).grid(row=1, column=0, sticky=tk.W, pady=(8, 0))

        self._add_labeled_slider(
            self.image_controls,
            "Skala",
            0.2,
            2.5,
            1.0,
            lambda value: self._update_image("scale", float(value)),
            row=2,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Rotasi",
            -45,
            45,
            0,
            lambda value: self._update_image("rotation", float(value)),
            row=3,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Posisi X",
            0.0,
            1.0,
            0.75,
            lambda value: self._update_image("position_x", float(value)),
            row=4,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Posisi Y",
            0.0,
            1.0,
            0.65,
            lambda value: self._update_image("position_y", float(value)),
            row=5,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Opacity",
            0.1,
            1.0,
            1.0,
            lambda value: self._update_image("opacity", float(value)),
            row=6,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Shadow Blur",
            0,
            60,
            24,
            lambda value: self._update_image("shadow_blur", int(float(value))),
            row=7,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Shadow Offset X",
            -60,
            60,
            0,
            lambda value: self._update_image("shadow_offset_x", int(float(value))),
            row=8,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Shadow Offset Y",
            -60,
            60,
            12,
            lambda value: self._update_image("shadow_offset_y", int(float(value))),
            row=9,
        )
        self._add_labeled_slider(
            self.image_controls,
            "Shadow Opacity",
            0.0,
            1.0,
            0.7,
            lambda value: self._update_image("shadow_opacity", float(value)),
            row=10,
        )

        self.flip_h_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.image_controls,
            text="Flip Horizontal",
            command=lambda: self._toggle_image_flip("flip_horizontal"),
            variable=self.flip_h_var,
        ).grid(row=11, column=0, sticky=tk.W, pady=(8, 0))
        self.flip_v_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            self.image_controls,
            text="Flip Vertikal",
            command=lambda: self._toggle_image_flip("flip_vertical"),
            variable=self.flip_v_var,
        ).grid(row=11, column=1, sticky=tk.W, pady=(8, 0))

        for column in range(2):
            self.image_controls.columnconfigure(column, weight=1)

    def _build_effects_tab(self, parent: ttk.Frame) -> None:
        ttk.Label(parent, text="Urutan Layer").pack(anchor=tk.W)

        self.layer_tree = ttk.Treeview(parent, columns=("type",), show="tree")
        self.layer_tree.pack(fill=tk.BOTH, expand=True, pady=(4, 8))
        self.layer_tree.bind("<<TreeviewSelect>>", self._on_tree_select)

        reorder_frame = ttk.Frame(parent)
        reorder_frame.pack(fill=tk.X)
        ttk.Button(reorder_frame, text="Naikkan", command=lambda: self._shift_layer(-1)).pack(side=tk.LEFT)
        ttk.Button(reorder_frame, text="Turunkan", command=lambda: self._shift_layer(1)).pack(side=tk.LEFT, padx=6)

        # Color grading controls
        grading = ttk.Labelframe(parent, text="Color Grading", padding=10)
        grading.pack(fill=tk.X, pady=(12, 0))

        self._add_labeled_slider(
            grading,
            "Brightness",
            0.5,
            1.6,
            self.background.brightness,
            lambda value: self._set_background_numeric("brightness", float(value)),
        )
        self._add_labeled_slider(
            grading,
            "Kontras",
            0.5,
            1.6,
            self.background.contrast,
            lambda value: self._set_background_numeric("contrast", float(value)),
        )
        self._add_labeled_slider(
            grading,
            "Saturasi",
            0.2,
            2.0,
            self.background.saturation,
            lambda value: self._set_background_numeric("saturation", float(value)),
        )

        ttk.Button(parent, text="Reset Layer", command=self._reset_layers).pack(fill=tk.X, pady=(12, 0))

    def _add_labeled_slider(
        self,
        parent: tk.Widget,
        label: str,
        min_value: float,
        max_value: float,
        default: float,
        command,
        row: Optional[int] = None,
    ) -> None:
        container = ttk.Frame(parent)
        if row is None:
            container.pack(fill=tk.X, pady=4)
        else:
            container.grid(row=row, column=0, columnspan=3, sticky="ew", pady=4)

        ttk.Label(container, text=label).pack(anchor=tk.W)
        slider = ttk.Scale(
            container,
            from_=min_value,
            to=max_value,
            value=default,
            orient=tk.HORIZONTAL,
            command=command,
        )
        slider.pack(fill=tk.X)

        value_label = ttk.Label(container, text=f"{default:.2f}" if isinstance(default, float) else str(int(default)))
        value_label.pack(anchor=tk.E)

        def on_slide(value: str) -> None:
            if isinstance(min_value, int) and isinstance(max_value, int):
                value_label.config(text=str(int(float(value))))
            else:
                value_label.config(text=f"{float(value):.2f}")
            command(value)

        slider.configure(command=on_slide)
        slider.set(default)

    def _add_default_layers(self) -> None:
        headline = create_text_layer(
            {"label": "Headline", "text": "Tingkatkan Views\nDalam 5 Menit!", "font_size": 170}
        )
        subhead = create_text_layer(
            {
                "label": "Subheadline",
                "text": "Strategi Thumbnail Viral",
                "font_size": 90,
                "position_y": 0.62,
                "color": "#ffcf00",
                "shadow": {
                    "enabled": True,
                    "offset_x": 4,
                    "offset_y": 4,
                    "blur_radius": 8,
                    "color": "#000000",
                    "opacity": 0.7,
                },
                "stroke": {"width": 4, "color": "#111111"},
            }
        )
        overlay = create_overlay_layer(
            {
                "label": "Banner",
                "mode": "banner",
                "color": "#ff3838",
                "opacity": 0.88,
                "position_x": 0.5,
                "position_y": 0.6,
                "width": 0.9,
                "height": 0.3,
                "rotation": -2,
            }
        )
        self.text_layers.extend([headline, subhead])
        self.overlay_layers.append(overlay)

        for layer in self.text_layers:
            self.text_list.insert(tk.END, layer.label)
            self.layer_order.append(("text", layer.id))
        self.overlay_list.insert(tk.END, overlay.label)
        self.layer_order.append(("overlay", overlay.id))

        self.current_text_id = headline.id
        self.text_list.selection_set(0)
        self._sync_text_controls(headline)

        self._refresh_layer_tree()

    def _choose_color(self, target: str, initial: str) -> None:
        color = colorchooser.askcolor(color=initial)
        if color and color[1]:
            if target == "background_solid":
                self.background.solid_color = color[1]
            elif target == "gradient_start":
                self.background.gradient.start_color = color[1]
            elif target == "gradient_end":
                self.background.gradient.end_color = color[1]
            elif target == "text_color":
                self._update_current_text("color", color[1])
            elif target == "stroke_color":
                self._update_current_text("stroke_color", color[1])
            elif target == "shadow_color":
                self._update_shadow_value("color", color[1])
            elif target == "overlay_color":
                self._update_overlay("color", color[1])
            self.render_thumbnail()

    def _set_gradient_direction(self, direction: str) -> None:
        self.background.gradient.direction = direction
        self.render_thumbnail()

    def _load_background_image(self) -> None:
        file_path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All Files", "*.*")]
        )
        if file_path:
            self.background.image_path = file_path
            self.background.mode = "image"
            self.render_thumbnail()

    def _clear_background_image(self) -> None:
        self.background.image_path = None
        self.render_thumbnail()

    def _update_background_mode(self, mode: str) -> None:
        self.background.mode = mode
        self.render_thumbnail()

    def _set_background_numeric(self, field_name: str, value: float) -> None:
        setattr(self.background, field_name, value)
        self.render_thumbnail()

    def _add_text_layer(self) -> None:
        layer = create_text_layer({"label": f"Teks {len(self.text_layers) + 1}"})
        self.text_layers.append(layer)
        self.text_list.insert(tk.END, layer.label)
        self.layer_order.append(("text", layer.id))
        self._select_text_layer(layer.id)
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _duplicate_text_layer(self) -> None:
        current = self._get_current_text()
        if not current:
            return
        clone = create_text_layer(asdict(current))
        clone.id = str(uuid.uuid4())
        clone.label = f"{current.label} (copy)"
        self.text_layers.append(clone)
        self.text_list.insert(tk.END, clone.label)
        self.layer_order.append(("text", clone.id))
        self._select_text_layer(clone.id)
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _remove_text_layer(self) -> None:
        idx = self._get_text_index()
        if idx is None:
            return
        layer = self.text_layers.pop(idx)
        self.layer_order = [item for item in self.layer_order if item != ("text", layer.id)]
        self.text_list.delete(idx)
        self.current_text_id = self.text_layers[idx - 1].id if self.text_layers else None
        if self.current_text_id:
            self._select_text_layer(self.current_text_id)
        else:
            self.text_entry.delete("1.0", tk.END)
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _select_text_layer(self, layer_id: str) -> None:
        self.current_text_id = layer_id
        index = next((i for i, layer in enumerate(self.text_layers) if layer.id == layer_id), None)
        if index is not None:
            self.text_list.selection_clear(0, tk.END)
            self.text_list.selection_set(index)
            self.text_list.activate(index)
            self._sync_text_controls(self.text_layers[index])

    def _on_text_select(self, event) -> None:
        idx = self._get_text_index()
        if idx is not None:
            layer = self.text_layers[idx]
            self.current_text_id = layer.id
            self._sync_text_controls(layer)

    def _get_text_index(self) -> Optional[int]:
        selection = self.text_list.curselection()
        if selection:
            return selection[0]
        return None

    def _get_current_text(self) -> Optional[TextLayer]:
        if not self.current_text_id:
            return None
        for layer in self.text_layers:
            if layer.id == self.current_text_id:
                return layer
        return None

    def _sync_text_controls(self, layer: TextLayer) -> None:
        self.text_entry.delete("1.0", tk.END)
        self.text_entry.insert(tk.END, layer.text)
        self.font_var.set(self.font_options.get(layer.font_file, next(iter(self.font_options.values()))))
        self.font_size_var.set(layer.font_size)
        self.align_var.set(layer.align)
        self.shadow_var.set(layer.shadow.enabled)

    def _change_text_font(self) -> None:
        selection = self.font_var.get()
        for file_name, display in self.font_options.items():
            if display == selection:
                self._update_current_text("font_file", file_name)
                break

    def _change_text_size(self) -> None:
        try:
            size = int(self.font_size_var.get())
        except (ValueError, tk.TclError):
            return
        self._update_current_text("font_size", size)

    def _update_current_text(self, field_name: str, value) -> None:
        layer = self._get_current_text()
        if not layer:
            return
        if field_name == "text":
            layer.text = value
        elif field_name == "color":
            layer.color = value
        elif field_name == "font_file":
            layer.font_file = value
        elif field_name == "font_size":
            layer.font_size = value
        elif field_name == "align":
            layer.align = value
        elif field_name == "position_x":
            layer.position_x = value
        elif field_name == "position_y":
            layer.position_y = value
        elif field_name == "max_width":
            layer.max_width = value
        elif field_name == "tracking":
            layer.tracking = value
        elif field_name == "rotation":
            layer.rotation = value
        elif field_name == "stroke_width":
            layer.stroke.width = value
        elif field_name == "stroke_color":
            layer.stroke.color = value
        self.render_thumbnail()

    def _toggle_text_shadow(self) -> None:
        layer = self._get_current_text()
        if not layer:
            return
        layer.shadow.enabled = not layer.shadow.enabled
        self.shadow_var.set(layer.shadow.enabled)
        self.render_thumbnail()

    def _update_shadow_value(self, field_name: str, value) -> None:
        layer = self._get_current_text()
        if not layer:
            return
        setattr(layer.shadow, field_name, value)
        self.render_thumbnail()

    def _add_overlay_layer(self) -> None:
        layer = create_overlay_layer({"label": f"Highlight {len(self.overlay_layers) + 1}"})
        self.overlay_layers.append(layer)
        self.overlay_list.insert(tk.END, layer.label)
        self.layer_order.append(("overlay", layer.id))
        self._select_overlay_layer(layer.id)
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _duplicate_overlay_layer(self) -> None:
        layer = self._get_current_overlay()
        if not layer:
            return
        clone = create_overlay_layer(asdict(layer))
        clone.id = str(uuid.uuid4())
        clone.label = f"{layer.label} (copy)"
        self.overlay_layers.append(clone)
        self.overlay_list.insert(tk.END, clone.label)
        self.layer_order.append(("overlay", clone.id))
        self._select_overlay_layer(clone.id)
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _remove_overlay_layer(self) -> None:
        idx = self._get_overlay_index()
        if idx is None:
            return
        layer = self.overlay_layers.pop(idx)
        self.layer_order = [item for item in self.layer_order if item != ("overlay", layer.id)]
        self.overlay_list.delete(idx)
        if self.overlay_layers:
            next_id = self.overlay_layers[max(0, idx - 1)].id
            self._select_overlay_layer(next_id)
        else:
            self.current_overlay_id = None
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _on_overlay_select(self, event) -> None:
        idx = self._get_overlay_index()
        if idx is not None:
            layer = self.overlay_layers[idx]
            self.current_overlay_id = layer.id
            self._sync_overlay_controls(layer)

    def _select_overlay_layer(self, layer_id: str) -> None:
        self.current_overlay_id = layer_id
        index = next((i for i, layer in enumerate(self.overlay_layers) if layer.id == layer_id), None)
        if index is not None:
            self.overlay_list.selection_clear(0, tk.END)
            self.overlay_list.selection_set(index)
            self.overlay_list.activate(index)
            self._sync_overlay_controls(self.overlay_layers[index])

    def _get_overlay_index(self) -> Optional[int]:
        selection = self.overlay_list.curselection()
        if selection:
            return selection[0]
        return None

    def _get_current_overlay(self) -> Optional[OverlayLayer]:
        if not self.current_overlay_id:
            return None
        for layer in self.overlay_layers:
            if layer.id == self.current_overlay_id:
                return layer
        return None

    def _sync_overlay_controls(self, layer: OverlayLayer) -> None:
        self.overlay_mode_var.set(layer.mode)

    def _update_overlay(self, field_name: str, value) -> None:
        layer = self._get_current_overlay()
        if not layer:
            return
        setattr(layer, field_name, value)
        self.render_thumbnail()

    def _add_image_layer(self) -> None:
        layer = create_image_layer({"label": f"Gambar {len(self.image_layers) + 1}"})
        self.image_layers.append(layer)
        self.image_list.insert(tk.END, layer.label)
        self.layer_order.append(("image", layer.id))
        self._select_image_layer(layer.id)
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _duplicate_image_layer(self) -> None:
        layer = self._get_current_image()
        if not layer:
            return
        clone = create_image_layer(asdict(layer))
        clone.id = str(uuid.uuid4())
        clone.label = f"{layer.label} (copy)"
        self.image_layers.append(clone)
        self.image_list.insert(tk.END, clone.label)
        self.layer_order.append(("image", clone.id))
        self._select_image_layer(clone.id)
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _remove_image_layer(self) -> None:
        idx = self._get_image_index()
        if idx is None:
            return
        layer = self.image_layers.pop(idx)
        self.layer_order = [item for item in self.layer_order if item != ("image", layer.id)]
        self.image_list.delete(idx)
        if self.image_layers:
            next_id = self.image_layers[max(0, idx - 1)].id
            self._select_image_layer(next_id)
        else:
            self.current_image_id = None
        self._refresh_layer_tree()
        self.render_thumbnail()

    def _on_image_select(self, event) -> None:
        idx = self._get_image_index()
        if idx is not None:
            layer = self.image_layers[idx]
            self.current_image_id = layer.id
            self.image_shadow_var.set(layer.add_shadow)
            self.flip_h_var.set(layer.flip_horizontal)
            self.flip_v_var.set(layer.flip_vertical)
            self.render_thumbnail()

    def _select_image_layer(self, layer_id: str) -> None:
        self.current_image_id = layer_id
        index = next((i for i, layer in enumerate(self.image_layers) if layer.id == layer_id), None)
        if index is not None:
            self.image_list.selection_clear(0, tk.END)
            self.image_list.selection_set(index)
            self.image_list.activate(index)
            layer = self.image_layers[index]
            self.image_shadow_var.set(layer.add_shadow)
            self.flip_h_var.set(layer.flip_horizontal)
            self.flip_v_var.set(layer.flip_vertical)

    def _get_image_index(self) -> Optional[int]:
        selection = self.image_list.curselection()
        if selection:
            return selection[0]
        return None

    def _get_current_image(self) -> Optional[ImageLayer]:
        if not self.current_image_id:
            return None
        for layer in self.image_layers:
            if layer.id == self.current_image_id:
                return layer
        return None

    def _change_image_path(self) -> None:
        layer = self._get_current_image()
        if not layer:
            return
        path = filedialog.askopenfilename(
            filetypes=[("Image Files", "*.png *.jpg *.jpeg *.webp *.bmp"), ("All files", "*.*")]
        )
        if path:
            layer.image_path = path
            self.render_thumbnail()

    def _update_image(self, field_name: str, value) -> None:
        layer = self._get_current_image()
        if not layer:
            return
        setattr(layer, field_name, value)
        self.render_thumbnail()

    def _toggle_image_shadow(self) -> None:
        layer = self._get_current_image()
        if not layer:
            return
        layer.add_shadow = not layer.add_shadow
        self.image_shadow_var.set(layer.add_shadow)
        self.render_thumbnail()

    def _toggle_image_flip(self, field_name: str) -> None:
        layer = self._get_current_image()
        if not layer:
            return
        current = getattr(layer, field_name)
        setattr(layer, field_name, not current)
        if field_name == "flip_horizontal":
            self.flip_h_var.set(layer.flip_horizontal)
        else:
            self.flip_v_var.set(layer.flip_vertical)
        self.render_thumbnail()

    def _refresh_layer_tree(self) -> None:
        self.layer_tree.delete(*self.layer_tree.get_children())
        for index, (layer_type, layer_id) in enumerate(self.layer_order):
            label = ""
            if layer_type == "text":
                layer = next((t for t in self.text_layers if t.id == layer_id), None)
                label = f"Teks: {layer.label if layer else 'Unknown'}"
            elif layer_type == "overlay":
                layer = next((o for o in self.overlay_layers if o.id == layer_id), None)
                label = f"Overlay: {layer.label if layer else 'Unknown'}"
            elif layer_type == "image":
                layer = next((i for i in self.image_layers if i.id == layer_id), None)
                label = f"Gambar: {layer.label if layer else 'Unknown'}"
            self.layer_tree.insert("", index, iid=f"{layer_type}:{layer_id}", text=label)

    def _shift_layer(self, direction: int) -> None:
        if not self.layer_tree.selection():
            return
        selected = self.layer_tree.selection()[0]
        try:
            index = next(i for i, item in enumerate(self.layer_order) if f"{item[0]}:{item[1]}" == selected)
        except StopIteration:
            return
        new_index = clamp(index + direction, 0, len(self.layer_order) - 1)
        if new_index == index:
            return
        self.layer_order.insert(int(new_index), self.layer_order.pop(index))
        self._refresh_layer_tree()
        self.render_thumbnail()
        self.layer_tree.selection_set(f"{self.layer_order[int(new_index)][0]}:{self.layer_order[int(new_index)][1]}")

    def _on_tree_select(self, event) -> None:
        selection = self.layer_tree.selection()
        if not selection:
            return
        layer_type, layer_id = selection[0].split(":")
        if layer_type == "text":
            self._select_text_layer(layer_id)
        elif layer_type == "overlay":
            self._select_overlay_layer(layer_id)
        elif layer_type == "image":
            self._select_image_layer(layer_id)

    def _reset_layers(self) -> None:
        if not messagebox.askyesno("Reset", "Reset semua layer ke default?"):
            return
        self.text_layers.clear()
        self.overlay_layers.clear()
        self.image_layers.clear()
        self.layer_order.clear()

        self.text_list.delete(0, tk.END)
        self.overlay_list.delete(0, tk.END)
        self.image_list.delete(0, tk.END)

        self._add_default_layers()
        self.render_thumbnail()

    def render_thumbnail(self) -> None:
        base_image = Image.new("RGBA", (self.base_width, self.base_height), "#111111")

        if self.background.mode == "solid":
            background_layer = Image.new("RGBA", (self.base_width, self.base_height), self.background.solid_color)
        elif self.background.mode == "gradient":
            background_layer = self._render_gradient_background()
        else:
            background_layer = self._render_image_background()

        base_image = Image.alpha_composite(base_image, background_layer)

        for layer_type, layer_id in self.layer_order:
            if layer_type == "overlay":
                layer = next((o for o in self.overlay_layers if o.id == layer_id), None)
                if layer:
                    base_image = Image.alpha_composite(base_image, self._render_overlay_layer(layer))
            elif layer_type == "image":
                layer = next((i for i in self.image_layers if i.id == layer_id), None)
                if layer and layer.image_path:
                    base_image = Image.alpha_composite(base_image, self._render_image_layer(layer))
            elif layer_type == "text":
                layer = next((t for t in self.text_layers if t.id == layer_id), None)
                if layer:
                    base_image = Image.alpha_composite(base_image, self._render_text_layer(layer))

        self.latest_image = base_image
        preview = base_image.resize((self.preview_width, self.preview_height), Image.LANCZOS)
        self.preview_photo = ImageTk.PhotoImage(preview)
        self.preview_canvas.delete("all")
        self.preview_canvas.create_image(self.preview_width / 2, self.preview_height / 2, image=self.preview_photo)

    def _render_gradient_background(self) -> Image.Image:
        gradient_layer = Image.new("RGBA", (self.base_width, self.base_height))
        draw = ImageDraw.Draw(gradient_layer)

        start = hex_to_rgba(self.background.gradient.start_color)
        end = hex_to_rgba(self.background.gradient.end_color)

        if self.background.gradient.direction == "horizontal":
            for x in range(self.base_width):
                ratio = x / (self.base_width - 1)
                color = tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(4))
                draw.line([(x, 0), (x, self.base_height)], fill=color)
        elif self.background.gradient.direction == "vertical":
            for y in range(self.base_height):
                ratio = y / (self.base_height - 1)
                color = tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(4))
                draw.line([(0, y), (self.base_width, y)], fill=color)
        else:
            for y in range(self.base_height):
                for x in range(self.base_width):
                    ratio = (x + y) / (self.base_width + self.base_height)
                    color = tuple(int(start[i] + (end[i] - start[i]) * ratio) for i in range(4))
                    draw.point((x, y), fill=color)

        gradient_layer = self._apply_background_corrections(gradient_layer)
        return gradient_layer

    def _render_image_background(self) -> Image.Image:
        base = Image.new("RGBA", (self.base_width, self.base_height), self.background.solid_color)
        if not self.background.image_path or not Path(self.background.image_path).exists():
            return base
        try:
            img = Image.open(self.background.image_path).convert("RGBA")
        except OSError:
            return base
        img = ImageOps.fit(img, (self.base_width, self.base_height), Image.LANCZOS)
        if self.background.blur_radius > 0:
            img = img.filter(ImageFilter.GaussianBlur(self.background.blur_radius))
        img = self._apply_background_corrections(img)
        base = Image.alpha_composite(base, img)
        return base

    def _apply_background_corrections(self, img: Image.Image) -> Image.Image:
        if self.background.brightness != 1.0:
            img = ImageEnhance.Brightness(img).enhance(self.background.brightness)
        if self.background.contrast != 1.0:
            img = ImageEnhance.Contrast(img).enhance(self.background.contrast)
        if self.background.saturation != 1.0:
            img = ImageEnhance.Color(img).enhance(self.background.saturation)
        return img

    def _render_overlay_layer(self, layer: OverlayLayer) -> Image.Image:
        overlay = Image.new("RGBA", (self.base_width, self.base_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        width = int(self.base_width * layer.width)
        height = int(self.base_height * layer.height)
        x = int(self.base_width * layer.position_x)
        y = int(self.base_height * layer.position_y)
        rect = [x - width // 2, y - height // 2, x + width // 2, y + height // 2]

        color = hex_to_rgba(layer.color, layer.opacity)
        if layer.mode == "rectangle":
            draw.rounded_rectangle(rect, radius=layer.rounded, fill=color)
        elif layer.mode == "circle":
            draw.ellipse(rect, fill=color)
        elif layer.mode == "banner":
            banner_rect = [
                rect[0],
                rect[1],
                rect[2],
                rect[3] - int(height * 0.25),
            ]
            draw.rounded_rectangle(banner_rect, radius=layer.rounded, fill=color)
            triangle_height = int(height * 0.35)
            triangle = [
                (rect[0], rect[3] - triangle_height),
                (rect[0] + width // 4, rect[3]),
                (rect[0] + width // 2, rect[3] - triangle_height),
            ]
            draw.polygon(triangle, fill=color)
            triangle2 = [
                (rect[2], rect[3] - triangle_height),
                (rect[2] - width // 4, rect[3]),
                (rect[2] - width // 2, rect[3] - triangle_height),
            ]
            draw.polygon(triangle2, fill=color)

        if layer.blur_radius > 0:
            overlay = overlay.filter(ImageFilter.GaussianBlur(layer.blur_radius))

        if layer.rotation != 0:
            overlay = overlay.rotate(layer.rotation, expand=False, center=(x, y), resample=Image.BICUBIC)

        return overlay

    def _render_text_layer(self, layer: TextLayer) -> Image.Image:
        temp = Image.new("RGBA", (self.base_width, self.base_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(temp)

        font_path = ensure_font_path(layer.font_file)
        font = ImageFont.truetype(str(font_path), size=layer.font_size)

        lines = layer.text.splitlines()
        max_width_pixels = int(self.base_width * layer.max_width)
        rendered_lines = []
        for line in lines:
            if not line.strip():
                rendered_lines.append("")
                continue
            words = line.split(" ")
            current_line = ""
            for word in words:
                attempt = f"{current_line} {word}".strip()
                bbox = font.getbbox(self._apply_tracking(attempt, layer.tracking))
                width = bbox[2] - bbox[0]
                if width <= max_width_pixels:
                    current_line = attempt
                else:
                    if current_line:
                        rendered_lines.append(current_line)
                    current_line = word
            rendered_lines.append(current_line)

        text_image = Image.new("RGBA", (self.base_width, self.base_height), (0, 0, 0, 0))
        text_draw = ImageDraw.Draw(text_image)

        total_height = sum(font.getbbox(line)[3] - font.getbbox(line)[1] for line in rendered_lines if line)
        total_height += (len(rendered_lines) - 1) * int(font.size * 0.1)
        cursor_y = int(self.base_height * layer.position_y - total_height / 2)

        for line in rendered_lines:
            if not line:
                cursor_y += int(font.size * 1.1)
                continue
            display_line = self._apply_tracking(line, layer.tracking)
            bbox = font.getbbox(display_line)
            line_width = bbox[2] - bbox[0]
            if layer.align == "left":
                cursor_x = int(self.base_width * layer.position_x - max_width_pixels / 2)
            elif layer.align == "right":
                cursor_x = int(self.base_width * layer.position_x + max_width_pixels / 2 - line_width)
            else:
                cursor_x = int(self.base_width * layer.position_x - line_width / 2)

            if layer.shadow.enabled and layer.shadow.opacity > 0:
                shadow_layer = Image.new("RGBA", (self.base_width, self.base_height), (0, 0, 0, 0))
                shadow_draw = ImageDraw.Draw(shadow_layer)
                shadow_color = hex_to_rgba(layer.shadow.color, layer.shadow.opacity)
                shadow_draw.text(
                    (cursor_x + layer.shadow.offset_x, cursor_y + layer.shadow.offset_y),
                    display_line,
                    font=font,
                    fill=shadow_color,
                    align=layer.align,
                )
                if layer.shadow.blur_radius > 0:
                    shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(layer.shadow.blur_radius))
                text_image = Image.alpha_composite(text_image, shadow_layer)

            if layer.stroke.width > 0:
                self._draw_text_with_stroke(
                    text_draw,
                    (cursor_x, cursor_y),
                    display_line,
                    font,
                    layer.color,
                    layer.stroke.color,
                    layer.stroke.width,
                )
            else:
                text_draw.text((cursor_x, cursor_y), display_line, font=font, fill=layer.color, align=layer.align)

            cursor_y += int(font.size * 1.1)

        if layer.rotation != 0:
            text_image = text_image.rotate(layer.rotation, expand=False, center=(
                int(self.base_width * layer.position_x),
                int(self.base_height * layer.position_y),
            ), resample=Image.BICUBIC)

        temp = Image.alpha_composite(temp, text_image)
        return temp

    def _apply_tracking(self, text: str, tracking: int) -> str:
        if tracking == 0:
            return text
        return (" " * max(0, tracking // 20)).join(list(text))

    def _draw_text_with_stroke(
        self,
        draw: ImageDraw.ImageDraw,
        position: Tuple[int, int],
        text: str,
        font: ImageFont.FreeTypeFont,
        fill_color: str,
        stroke_color: str,
        stroke_width: int,
    ) -> None:
        x, y = position
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx * dx + dy * dy <= stroke_width * stroke_width:
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
        draw.text((x, y), text, font=font, fill=fill_color)

    def _render_image_layer(self, layer: ImageLayer) -> Image.Image:
        overlay = Image.new("RGBA", (self.base_width, self.base_height), (0, 0, 0, 0))
        if not layer.image_path or not Path(layer.image_path).exists():
            return overlay

        try:
            img = Image.open(layer.image_path).convert("RGBA")
        except OSError:
            return overlay

        if layer.flip_horizontal:
            img = ImageOps.mirror(img)
        if layer.flip_vertical:
            img = ImageOps.flip(img)

        img_width, img_height = img.size
        target_width = int(self.base_width * 0.4 * layer.scale)
        ratio = target_width / img_width
        img = img.resize((int(img_width * ratio), int(img_height * ratio)), Image.LANCZOS)

        if layer.opacity < 1.0:
            alpha = img.split()[3]
            alpha = alpha.point(lambda p: int(p * layer.opacity))
            img.putalpha(alpha)

        if layer.add_shadow and layer.shadow_opacity > 0:
            shadow = Image.new("RGBA", img.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_mask = img.split()[3]
            shadow_draw.bitmap((0, 0), shadow_mask, fill=hex_to_rgba("#000000", layer.shadow_opacity))
            if layer.shadow_blur > 0:
                shadow = shadow.filter(ImageFilter.GaussianBlur(layer.shadow_blur))
            position = (
                int(self.base_width * layer.position_x - img.size[0] / 2 + layer.shadow_offset_x),
                int(self.base_height * layer.position_y - img.size[1] / 2 + layer.shadow_offset_y),
            )
            overlay.alpha_composite(shadow, position)

        img = img.rotate(layer.rotation, expand=True, resample=Image.BICUBIC)

        position = (
            int(self.base_width * layer.position_x - img.size[0] / 2),
            int(self.base_height * layer.position_y - img.size[1] / 2),
        )
        overlay.alpha_composite(img, position)
        return overlay

    def export_thumbnail(self) -> None:
        if not hasattr(self, "latest_image"):
            self.render_thumbnail()
        file_path = filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG Image", "*.png")],
            initialfile="thumbnail.png",
        )
        if not file_path:
            return
        self.latest_image.save(file_path, format="PNG")
        messagebox.showinfo("Sukses", f"Thumbnail disimpan ke {file_path}")

    def save_workspace(self) -> None:
        data = {
            "background": asdict(self.background),
            "text_layers": [asdict(layer) for layer in self.text_layers],
            "image_layers": [asdict(layer) for layer in self.image_layers],
            "overlay_layers": [asdict(layer) for layer in self.overlay_layers],
            "layer_order": self.layer_order,
        }
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("Workspace", "*.json")],
            initialfile="workspace.json",
        )
        if not file_path:
            return
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        messagebox.showinfo("Sukses", "Workspace disimpan.")

    def load_workspace(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("Workspace", "*.json")])
        if not path:
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.background = create_background_settings(data.get("background"))
        self.text_layers = [create_text_layer(layer) for layer in data.get("text_layers", [])]
        self.image_layers = [create_image_layer(layer) for layer in data.get("image_layers", [])]
        self.overlay_layers = [create_overlay_layer(layer) for layer in data.get("overlay_layers", [])]
        self.layer_order = [tuple(item) for item in data.get("layer_order", [])]

        self.text_list.delete(0, tk.END)
        for layer in self.text_layers:
            self.text_list.insert(tk.END, layer.label)
        self.overlay_list.delete(0, tk.END)
        for layer in self.overlay_layers:
            self.overlay_list.insert(tk.END, layer.label)
        self.image_list.delete(0, tk.END)
        for layer in self.image_layers:
            self.image_list.insert(tk.END, layer.label)

        self.current_text_id = self.text_layers[0].id if self.text_layers else None
        if self.current_text_id:
            self._select_text_layer(self.current_text_id)
        self.current_overlay_id = self.overlay_layers[0].id if self.overlay_layers else None
        if self.current_overlay_id:
            self._select_overlay_layer(self.current_overlay_id)
        self.current_image_id = self.image_layers[0].id if self.image_layers else None
        if self.current_image_id:
            self._select_image_layer(self.current_image_id)

        self._refresh_layer_tree()
        self.render_thumbnail()


def run() -> None:
    app = ThumbnailDesigner()
    app.mainloop()


if __name__ == "__main__":
    run()
