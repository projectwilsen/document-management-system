# Design: UI Rename Faktur Pajak Coretax

**Date:** 2026-06-21
**Status:** Approved

## Overview

Tambahkan desktop UI berbasis CustomTkinter di atas script `rename_faktur.py` yang sudah ada. User dapat memilih folder sumber dan folder tujuan, lalu klik Sync untuk rename dan memindahkan PDF faktur pajak secara otomatis.

## Goals

- User non-teknis bisa pakai tool ini tanpa buka terminal
- Proses berjalan real-time dengan log yang terlihat langsung
- Bisa di-distribute sebagai `.exe` via PyInstaller

## Non-Goals

- Tidak mengubah logika ekstraksi nama di `rename_faktur.py`
- Tidak mendukung format selain PDF
- Tidak ada fitur undo/rollback setelah Sync

## Struktur File

```
document-management-system/
├── main.py              ← entry point, launch UI
├── core/
│   └── rename_faktur.py ← logika rename (refactor dari rename_faktur.py lama)
├── ui/
│   └── app.py           ← CustomTkinter window
├── rename_faktur.py     ← file CLI lama, tetap berfungsi normal
└── pyproject.toml
```

File `rename_faktur.py` lama tidak dihapus dan tetap bisa dipakai via CLI. Logika intinya di-extract ke `core/rename_faktur.py`.

## UI Layout

```
┌──────────────────────────────────────────────────┐
│           Rename Faktur Pajak Coretax            │
├──────────────────────────────────────────────────┤
│  Folder Sumber   [C:\faktur\...]    [Browse]     │
│  Folder Tujuan   [C:\output\...]    [Browse]     │
├──────────────────────────────────────────────────┤
│              [Preview]    [Sync]                 │
├──────────────────────────────────────────────────┤
│  ┌────────────────────────────────────────────┐  │
│  │ 1  9302847561038.pdf → PT ABC INDONESIA ✅ │  │
│  │ 2  1847362910485.pdf → PT XYZ JAYA     ✅ │  │
│  │ 3  2938475610293.pdf → (tidak ditemukan)❌ │  │
│  └────────────────────────────────────────────┘  │
│  ✅ Berhasil: 7   ❌ Gagal: 1   ⏭ Dilewati: 0   │
└──────────────────────────────────────────────────┘
```

### Komponen UI

- **FolderPicker** — label + entry (read-only) + tombol Browse. Dipakai dua kali: untuk folder sumber dan tujuan.
- **LogPanel** — scrollable text area, menampilkan progress tiap file real-time.
- **SummaryBar** — baris bawah menampilkan hitungan berhasil/gagal/dilewati setelah proses selesai.
- **ActionButtons** — tombol Preview dan Sync. Keduanya di-disable selama proses berjalan.

## Alur Interaksi

1. User klik **Browse** pada Folder Sumber → dialog pilih folder → path terisi di entry
2. User klik **Browse** pada Folder Tujuan → dialog pilih folder → path terisi di entry
3. User klik **Preview**:
   - Tombol di-disable
   - Background thread berjalan dengan `preview=True`
   - Log panel menampilkan hasil tanpa memindahkan file
   - Setelah selesai, summary muncul, tombol di-enable kembali
4. User klik **Sync**:
   - Tombol di-disable
   - Background thread berjalan dengan `preview=False`
   - Log panel menampilkan progress real-time tiap file
   - File PDF direname dan dipindahkan ke folder tujuan
   - Setelah selesai, summary muncul, tombol di-enable kembali

## Threading & Data Flow

Proses baca PDF berjalan di **background thread** agar UI tidak freeze.

```
[User klik Sync/Preview]
        │
        ▼
  Disable tombol
        │
        ▼
  Background thread ──── baca PDF satu per satu
        │                       │
        │              tiap file selesai:
        │              kirim pesan via log_callback
        │
        ▼
  UI thread (CTk.after polling tiap 100ms via queue)
        │
        ▼
  Tulis ke LogPanel real-time
        │
        ▼
  Semua selesai → tampilkan SummaryBar → enable tombol
```

### Perubahan pada core/rename_faktur.py

Fungsi `rename_faktur()` direfactor untuk menerima parameter `log_callback: Callable[[str], None]`. Semua `print()` diganti dengan `log_callback(pesan)`. Ini memungkinkan UI menangkap output tanpa redirect stdout.

Signature baru:
```python
def rename_faktur(
    folder: str,
    output_folder: str,
    preview: bool = False,
    log_callback: Callable[[str], None] = print,
) -> dict:  # returns {"berhasil": int, "gagal": int, "skip": int}
```

Default `log_callback=print` memastikan CLI lama tetap berfungsi.

## Dependencies Baru

```toml
[project.dependencies]
customtkinter = ">=5.2"
pdfplumber = ">=0.11"   # sudah terinstall
```

## Distribusi

Setelah UI selesai, bisa di-package dengan:
```
pyinstaller --onefile --windowed main.py
```
Menghasilkan satu file `.exe` yang bisa dibagikan tanpa perlu install Python.
