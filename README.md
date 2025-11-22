# YouTube Thumbnail Designer (Tkinter)

A desktop tool built with Python, Tkinter, and Pillow to craft high-converting YouTube thumbnails. It provides an interactive workspace to control layout, typography, imagery, and color grading aligned with best practices observed in top-performing thumbnails.

## ✨ Fitur Utama

- Kanvas pratinjau 1280×720 (skala ke 640×360) dengan rendering real-time.
- Pengaturan latar lengkap: solid, gradien multi-arah, atau gambar blur dengan koreksi brightness/contrast/saturation.
- Editor teks multi-layer:
  - Pilihan font premium (Montserrat, Bebas Neue, Anton).
  - Stroke, drop shadow, tracking, rotasi, dan batas lebar adaptif.
- Highlight overlay: mode banner, rectangle, circle dengan opacity, blur, dan rotasi.
- Layer gambar: impor, skala, rotasi, opacity, flip, dan shadow lembut.
- Panel manajemen layer dengan drag-order (naik/turun).
- Simpan/muat workspace (.json) dan ekspor PNG siap upload.

## 🚀 Persiapan

### Prasyarat
- Python 3.10+
- Pip

### Instalasi
```bash
python3 -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Menjalankan Aplikasi
```bash
python thumbnail_designer.py
```

## 📁 Struktur Proyek
```
├── assets/
│   └── fonts/               # Font bebas lisensi (Google Fonts)
├── thumbnail_designer.py    # Aplikasi utama
├── requirements.txt
└── README.md
```

## 💡 Tips Penggunaan
- Pastikan teks utama kontras tinggi dan gunakan stroke + shadow untuk legibility saat ukuran kecil.
- Posisi objek wajah/gambar di sisi kanan dengan skala besar; padukan overlay banner untuk callout teks.
- Gunakan gradien hangat (merah → kuning) atau filter saturasi tinggi untuk menarik perhatian.
- Simpan workspace untuk membuat variasi thumbnail cepat pada seri konten.

## 📄 Lisensi Font
Semua font yang dibundel berasal dari [Google Fonts](https://fonts.google.com/) dan lisensinya mengizinkan redistribusi.
