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
