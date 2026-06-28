# Rename Faktur UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tambahkan desktop UI CustomTkinter di atas script rename_faktur.py yang sudah ada, sehingga user non-teknis bisa pilih folder sumber, folder tujuan, lalu klik Sync untuk rename dan pindah PDF faktur pajak secara otomatis.

**Architecture:** Logic rename di-extract ke `core/rename_faktur.py` dengan parameter `log_callback` supaya UI bisa tangkap output real-time. UI di `ui/app.py` jalankan proses di background thread via `queue.Queue`, poll tiap 100ms ke UI thread. File CLI lama `rename_faktur.py` tetap berfungsi tanpa perubahan.

**Tech Stack:** Python 3.12+, customtkinter >= 5.2, pdfplumber >= 0.11 (sudah terinstall), pytest untuk unit test

## Global Constraints

- Python >= 3.12
- Jangan hapus atau ubah `rename_faktur.py` (file CLI lama harus tetap berfungsi)
- `core/rename_faktur.py` harus bisa diimport tanpa side effect (tidak ada `sys.exit()` di level modul)
- `log_callback` default ke `print` agar CLI tetap bisa pakai fungsi dari core
- Semua file baru pakai UTF-8

## File Map

| File | Action | Tanggung Jawab |
|------|--------|----------------|
| `pyproject.toml` | Modify | Tambah dependency customtkinter |
| `core/__init__.py` | Create | Package marker |
| `core/rename_faktur.py` | Create | Logic rename dengan log_callback |
| `ui/__init__.py` | Create | Package marker |
| `ui/app.py` | Create | CustomTkinter window + threading |
| `main.py` | Modify | Entry point launch UI |
| `tests/__init__.py` | Create | Package marker |
| `tests/test_core.py` | Create | Unit test untuk core logic |

---

### Task 1: Setup Dependencies dan Core Module

**Files:**
- Modify: `pyproject.toml`
- Create: `core/__init__.py`
- Create: `core/rename_faktur.py`
- Create: `tests/__init__.py`
- Create: `tests/test_core.py`

**Interfaces:**
- Produces:
  ```python
  # core/rename_faktur.py
  def ekstrak_nama_pembeli(pdf_path: str) -> str | None: ...
  def buat_nama_file_unik(folder: Path, nama_base: str, ekstensi: str = ".pdf") -> str: ...
  def rename_faktur(
      folder: str,
      output_folder: str,
      preview: bool = False,
      log_callback: Callable[[str], None] = print,
  ) -> dict:  # {"berhasil": int, "gagal": int, "skip": int}
  ```

- [ ] **Step 1: Tambah customtkinter ke pyproject.toml**

Edit `pyproject.toml` — ubah bagian `dependencies`:

```toml
[project]
name = "document-management-system"
version = "0.1.0"
description = "Add your description here"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "customtkinter>=5.2",
    "pdfplumber>=0.11",
]
```

- [ ] **Step 2: Install dependency baru**

```bash
uv sync
```

Expected output: resolving dan menginstall `customtkinter` dan dependensinya.

- [ ] **Step 3: Buat package markers**

Buat file kosong `core/__init__.py` dan `tests/__init__.py`.

- [ ] **Step 4: Tulis test yang gagal untuk buat_nama_file_unik**

Buat `tests/test_core.py`:

```python
import pytest
from pathlib import Path
from core.rename_faktur import buat_nama_file_unik, rename_faktur


def test_buat_nama_file_unik_no_conflict(tmp_path):
    result = buat_nama_file_unik(tmp_path, "PT ABC")
    assert result == "PT ABC.pdf"


def test_buat_nama_file_unik_with_conflict(tmp_path):
    (tmp_path / "PT ABC.pdf").touch()
    result = buat_nama_file_unik(tmp_path, "PT ABC")
    assert result == "PT ABC (2).pdf"


def test_buat_nama_file_unik_triple_conflict(tmp_path):
    (tmp_path / "PT ABC.pdf").touch()
    (tmp_path / "PT ABC (2).pdf").touch()
    result = buat_nama_file_unik(tmp_path, "PT ABC")
    assert result == "PT ABC (3).pdf"


def test_rename_faktur_folder_tidak_ada():
    logs = []
    result = rename_faktur(
        folder="/path/yang/tidak/ada",
        output_folder="/path/output",
        preview=True,
        log_callback=logs.append,
    )
    assert result == {"berhasil": 0, "gagal": 0, "skip": 0}
    assert any("tidak ditemukan" in log for log in logs)


def test_rename_faktur_folder_kosong(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    logs = []
    result = rename_faktur(
        folder=str(tmp_path),
        output_folder=str(output),
        preview=True,
        log_callback=logs.append,
    )
    assert result == {"berhasil": 0, "gagal": 0, "skip": 0}


def test_rename_faktur_preview_tidak_pindahkan_file(tmp_path):
    pdf = tmp_path / "12345.pdf"
    pdf.write_bytes(b"%PDF-1.4 fake content")
    output = tmp_path / "output"
    output.mkdir()

    logs = []
    result = rename_faktur(
        folder=str(tmp_path),
        output_folder=str(output),
        preview=True,
        log_callback=logs.append,
    )
    # File harus tetap ada di folder sumber (preview tidak pindah)
    assert pdf.exists()
    # Gagal karena fake PDF tidak bisa di-parse
    assert result["gagal"] == 1


def test_rename_faktur_log_callback_dipanggil(tmp_path):
    output = tmp_path / "output"
    output.mkdir()
    logs = []
    rename_faktur(
        folder=str(tmp_path),
        output_folder=str(output),
        preview=True,
        log_callback=logs.append,
    )
    # log_callback harus dipanggil minimal sekali
    assert len(logs) >= 1
```

- [ ] **Step 5: Jalankan test, pastikan FAIL**

```bash
uv run pytest tests/test_core.py -v
```

Expected: `ModuleNotFoundError: No module named 'core'` atau semua FAIL karena `core/rename_faktur.py` belum ada.

- [ ] **Step 6: Buat core/rename_faktur.py**

Buat `core/rename_faktur.py`:

```python
import os
import re
import shutil
from pathlib import Path
from typing import Callable

try:
    import pdfplumber
except ImportError:
    raise ImportError("pdfplumber tidak terinstall. Jalankan: pip install pdfplumber")


def ekstrak_nama_pembeli(pdf_path: str) -> str | None:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            teks_penuh = ""
            for page in pdf.pages:
                teks = page.extract_text()
                if teks:
                    teks_penuh += teks + "\n"

        teks_penuh = re.sub(r'[ \t]+', ' ', teks_penuh)
        lines = teks_penuh.split('\n')

        in_bagian_pembeli = False
        for line in lines:
            line_strip = line.strip()
            if re.search(r'Pembeli\s+Barang\s+Kena\s+Pajak', line_strip, re.IGNORECASE):
                in_bagian_pembeli = True
                continue
            if in_bagian_pembeli:
                match = re.match(r'Nama\s*:\s*(.+)', line_strip, re.IGNORECASE)
                if match:
                    nama = match.group(1).strip()
                    return re.sub(r'[\\/*?:"<>|]', '', nama).strip()
                if re.match(r'NPWP\s*:', line_strip, re.IGNORECASE):
                    in_bagian_pembeli = False

        semua_nama = re.findall(r'Nama\s*:\s*(.+)', teks_penuh, re.IGNORECASE)
        if len(semua_nama) >= 2:
            return re.sub(r'[\\/*?:"<>|]', '', semua_nama[1].strip()).strip()
        elif len(semua_nama) == 1:
            return re.sub(r'[\\/*?:"<>|]', '', semua_nama[0].strip()).strip()

    except Exception:
        pass

    return None


def buat_nama_file_unik(folder: Path, nama_base: str, ekstensi: str = ".pdf") -> str:
    target = folder / f"{nama_base}{ekstensi}"
    if not target.exists():
        return f"{nama_base}{ekstensi}"
    counter = 2
    while True:
        nama_baru = f"{nama_base} ({counter}){ekstensi}"
        if not (folder / nama_baru).exists():
            return nama_baru
        counter += 1


def rename_faktur(
    folder: str,
    output_folder: str,
    preview: bool = False,
    log_callback: Callable[[str], None] = print,
) -> dict:
    folder_path = Path(folder).resolve()
    output_path = Path(output_folder).resolve()

    if not folder_path.exists():
        log_callback(f"❌ Folder tidak ditemukan: {folder_path}")
        return {"berhasil": 0, "gagal": 0, "skip": 0}

    pdf_files = sorted(folder_path.glob("*.pdf"))

    if not pdf_files:
        log_callback(f"⚠️  Tidak ada file PDF di folder: {folder_path}")
        return {"berhasil": 0, "gagal": 0, "skip": 0}

    if not preview:
        output_path.mkdir(parents=True, exist_ok=True)

    berhasil = 0
    gagal = 0
    skip = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        nama_file_lama = pdf_path.name
        nama_tanpa_ext = pdf_path.stem

        cleaned = nama_tanpa_ext.replace(' ', '').replace('(', '').replace(')', '').replace('-', '').replace('_', '')
        if not cleaned.isdigit():
            if re.search(r'(PT|CV|UD|PD|TB|KOPERASI)', nama_tanpa_ext, re.IGNORECASE):
                log_callback(f"{i:<4} {nama_file_lama:<40} (sudah direname) ⏭️  SKIP")
                skip += 1
                continue

        nama_pembeli = ekstrak_nama_pembeli(str(pdf_path))

        if nama_pembeli:
            nama_file_baru = buat_nama_file_unik(output_path, nama_pembeli)
            if not preview:
                try:
                    shutil.move(str(pdf_path), str(output_path / nama_file_baru))
                    log_callback(f"{i:<4} {nama_file_lama:<40} → {nama_file_baru} ✅")
                    berhasil += 1
                except Exception as e:
                    log_callback(f"{i:<4} {nama_file_lama:<40} ❌ ERROR: {e}")
                    gagal += 1
            else:
                log_callback(f"{i:<4} {nama_file_lama:<40} → {nama_file_baru} ✅")
                berhasil += 1
        else:
            log_callback(f"{i:<4} {nama_file_lama:<40} (nama tidak ditemukan) ❌")
            gagal += 1

    return {"berhasil": berhasil, "gagal": gagal, "skip": skip}
```

- [ ] **Step 7: Jalankan test, pastikan PASS**

```bash
uv run pytest tests/test_core.py -v
```

Expected: semua 7 test PASS.

- [ ] **Step 8: Commit**

```bash
git add pyproject.toml core/__init__.py core/rename_faktur.py tests/__init__.py tests/test_core.py
git commit -m "feat: extract rename logic into core module with log_callback"
```

---

### Task 2: Build UI dengan CustomTkinter

**Files:**
- Create: `ui/__init__.py`
- Create: `ui/app.py`

**Interfaces:**
- Consumes:
  ```python
  from core.rename_faktur import rename_faktur
  # rename_faktur(folder, output_folder, preview, log_callback) -> dict
  ```
- Produces:
  ```python
  # ui/app.py
  class App(ctk.CTk):
      def mainloop(self) -> None: ...
  ```

- [ ] **Step 1: Buat ui/__init__.py**

Buat file kosong `ui/__init__.py`.

- [ ] **Step 2: Buat ui/app.py**

Buat `ui/app.py`:

```python
import queue
import threading
import tkinter.messagebox as mb
from tkinter import filedialog

import customtkinter as ctk

from core.rename_faktur import rename_faktur


class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Rename Faktur Pajak Coretax")
        self.geometry("720x520")
        self.minsize(600, 420)

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self._log_queue: queue.Queue = queue.Queue()
        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)

        # Title
        ctk.CTkLabel(
            self,
            text="Rename Faktur Pajak Coretax",
            font=ctk.CTkFont(size=18, weight="bold"),
        ).grid(row=0, column=0, padx=20, pady=(20, 10), sticky="w")

        # Folder pickers
        folder_frame = ctk.CTkFrame(self)
        folder_frame.grid(row=1, column=0, padx=20, pady=5, sticky="ew")
        folder_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(folder_frame, text="Folder Sumber", width=110, anchor="w").grid(
            row=0, column=0, padx=(12, 4), pady=10
        )
        self._source_entry = ctk.CTkEntry(folder_frame)
        self._source_entry.configure(state="disabled")
        self._source_entry.grid(row=0, column=1, padx=4, pady=10, sticky="ew")
        ctk.CTkButton(folder_frame, text="Browse", width=80, command=self._browse_source).grid(
            row=0, column=2, padx=(4, 12), pady=10
        )

        ctk.CTkLabel(folder_frame, text="Folder Tujuan", width=110, anchor="w").grid(
            row=1, column=0, padx=(12, 4), pady=(0, 10)
        )
        self._output_entry = ctk.CTkEntry(folder_frame)
        self._output_entry.configure(state="disabled")
        self._output_entry.grid(row=1, column=1, padx=4, pady=(0, 10), sticky="ew")
        ctk.CTkButton(folder_frame, text="Browse", width=80, command=self._browse_output).grid(
            row=1, column=2, padx=(4, 12), pady=(0, 10)
        )

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=20, pady=6, sticky="e")

        self._preview_btn = ctk.CTkButton(
            btn_frame, text="Preview", width=110, fg_color="gray50",
            hover_color="gray40", command=self._run_preview
        )
        self._preview_btn.grid(row=0, column=0, padx=(0, 8))

        self._sync_btn = ctk.CTkButton(
            btn_frame, text="Sync", width=110, command=self._run_sync
        )
        self._sync_btn.grid(row=0, column=1)

        # Log panel
        self._log_box = ctk.CTkTextbox(
            self,
            state="disabled",
            font=ctk.CTkFont(family="Courier New", size=12),
            wrap="none",
        )
        self._log_box.grid(row=3, column=0, padx=20, pady=6, sticky="nsew")

        # Summary bar
        self._summary_label = ctk.CTkLabel(self, text="", anchor="w")
        self._summary_label.grid(row=4, column=0, padx=20, pady=(2, 16), sticky="w")

    # --- folder pickers ---

    def _browse_source(self):
        path = filedialog.askdirectory(title="Pilih Folder Sumber")
        if path:
            self._set_entry(self._source_entry, path)

    def _browse_output(self):
        path = filedialog.askdirectory(title="Pilih Folder Tujuan")
        if path:
            self._set_entry(self._output_entry, path)

    def _set_entry(self, entry: ctk.CTkEntry, value: str):
        entry.configure(state="normal")
        entry.delete(0, "end")
        entry.insert(0, value)
        entry.configure(state="disabled")

    # --- actions ---

    def _run_preview(self):
        self._start_process(preview=True)

    def _run_sync(self):
        self._start_process(preview=False)

    def _start_process(self, preview: bool):
        source = self._source_entry.get()
        output = self._output_entry.get()

        if not source:
            mb.showerror("Error", "Pilih folder sumber terlebih dahulu.")
            return
        if not output:
            mb.showerror("Error", "Pilih folder tujuan terlebih dahulu.")
            return

        self._clear_log()
        self._set_buttons(enabled=False)
        mode = "PREVIEW (tidak ada file yang dipindah)" if preview else "SYNC (file akan dipindah)"
        self._append_log(f"Mode : {mode}")
        self._append_log("-" * 70)

        def worker():
            result = rename_faktur(
                folder=source,
                output_folder=output,
                preview=preview,
                log_callback=lambda msg: self._log_queue.put(("log", msg)),
            )
            self._log_queue.put(("done", result))

        threading.Thread(target=worker, daemon=True).start()
        self._poll_queue()

    # --- UI helpers ---

    def _clear_log(self):
        self._log_box.configure(state="normal")
        self._log_box.delete("1.0", "end")
        self._log_box.configure(state="disabled")
        self._summary_label.configure(text="")

    def _append_log(self, text: str):
        self._log_box.configure(state="normal")
        self._log_box.insert("end", text + "\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _set_buttons(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self._preview_btn.configure(state=state)
        self._sync_btn.configure(state=state)

    def _poll_queue(self):
        try:
            while True:
                kind, payload = self._log_queue.get_nowait()
                if kind == "log":
                    self._append_log(payload)
                elif kind == "done":
                    r = payload
                    self._summary_label.configure(
                        text=f"✅ Berhasil: {r['berhasil']}    ❌ Gagal: {r['gagal']}    ⏭  Dilewati: {r['skip']}"
                    )
                    self._set_buttons(enabled=True)
                    return
        except Exception:
            pass
        self.after(100, self._poll_queue)
```

- [ ] **Step 3: Commit**

```bash
git add ui/__init__.py ui/app.py
git commit -m "feat: add CustomTkinter UI with folder picker, log panel, and sync button"
```

---

### Task 3: Wire main.py dan Verifikasi Manual

**Files:**
- Modify: `main.py`

**Interfaces:**
- Consumes:
  ```python
  from ui.app import App
  # App().mainloop()
  ```

- [ ] **Step 1: Update main.py**

Ganti isi `main.py` dengan:

```python
from ui.app import App


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Jalankan aplikasi**

```bash
uv run python main.py
```

Expected: jendela "Rename Faktur Pajak Coretax" muncul.

- [ ] **Step 3: Test manual — Preview**

1. Klik **Browse** Folder Sumber → pilih folder `document/` di project ini
2. Klik **Browse** Folder Tujuan → pilih folder baru (buat dulu atau pilih folder kosong)
3. Klik **Preview**
4. Verifikasi: log panel menampilkan hasil rename per file, tidak ada file yang berpindah

- [ ] **Step 4: Test manual — Sync**

1. Folder sumber: `document/`
2. Folder tujuan: folder berbeda
3. Klik **Sync**
4. Verifikasi: log tampil real-time, file PDF sudah pindah ke folder tujuan dengan nama baru

- [ ] **Step 5: Test manual — validasi input kosong**

1. Klik **Sync** tanpa memilih folder sumber
2. Verifikasi: muncul dialog error "Pilih folder sumber terlebih dahulu."

- [ ] **Step 6: Verifikasi CLI lama masih berfungsi**

```bash
uv run python rename_faktur.py --folder document --preview
```

Expected: output tabel rename muncul di terminal seperti sebelumnya (tidak ada perubahan perilaku).

- [ ] **Step 7: Jalankan semua test**

```bash
uv run pytest tests/ -v
```

Expected: semua test PASS.

- [ ] **Step 8: Commit final**

```bash
git add main.py
git commit -m "feat: wire main.py to launch UI, complete rename faktur UI"
```
