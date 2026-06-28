"""
Auto-Rename Faktur Pajak Coretax
=================================
Script ini membaca semua PDF faktur pajak di satu folder,
mengekstrak nama perusahaan client (pembeli), lalu rename
file secara otomatis.

Cara pakai:
    python rename_faktur.py
    python rename_faktur.py --folder /path/ke/folder/faktur
    python rename_faktur.py --folder ./faktur --preview

Opsi:
    --folder    Folder berisi PDF faktur (default: folder yang sama dengan script)
    --preview   Tampilkan preview rename tanpa eksekusi (dry run)
"""

import os
import re
import sys
import argparse
import shutil
from pathlib import Path

try:
    import pdfplumber
except ImportError:
    print("❌ Library pdfplumber belum terinstall.")
    print("   Jalankan: pip install pdfplumber")
    sys.exit(1)


def ekstrak_nama_pembeli(pdf_path: str) -> str | None:
    """
    Ekstrak nama pembeli dari PDF faktur pajak Coretax.
    Mencari baris 'Nama : PT XXX' di bagian Pembeli.
    """
    try:
        with pdfplumber.open(pdf_path) as pdf:
            teks_penuh = ""
            for page in pdf.pages:
                teks = page.extract_text()
                if teks:
                    teks_penuh += teks + "\n"

        # Cari bagian "Pembeli" dulu, lalu ambil nama setelahnya
        # Pattern: setelah kata "Pembeli", cari "Nama : <nama perusahaan>"
        
        # Normalisasi spasi berlebih
        teks_penuh = re.sub(r'[ \t]+', ' ', teks_penuh)
        lines = teks_penuh.split('\n')

        in_bagian_pembeli = False
        for i, line in enumerate(lines):
            line_strip = line.strip()

            # Deteksi masuk bagian Pembeli
            if re.search(r'Pembeli\s+Barang\s+Kena\s+Pajak', line_strip, re.IGNORECASE):
                in_bagian_pembeli = True
                continue

            # Kalau sudah di bagian pembeli, cari baris "Nama"
            if in_bagian_pembeli:
                # Match "Nama : PT ABC" atau "Nama: PT ABC"
                match = re.match(r'Nama\s*:\s*(.+)', line_strip, re.IGNORECASE)
                if match:
                    nama = match.group(1).strip()
                    # Bersihkan karakter yang tidak valid untuk nama file
                    nama_bersih = re.sub(r'[\\/*?:"<>|]', '', nama)
                    nama_bersih = nama_bersih.strip()
                    return nama_bersih

                # Kalau sudah lewat baris NPWP, keluar dari bagian pembeli
                if re.match(r'NPWP\s*:', line_strip, re.IGNORECASE) and in_bagian_pembeli:
                    # Lewati satu NPWP penjual, tapi kalau sudah in_bagian_pembeli ini NPWP pembeli
                    in_bagian_pembeli = False

        # Fallback: cari langsung pola nama perusahaan umum di seluruh teks
        # Coba cari dua baris "Nama :" — ambil yang kedua (pembeli)
        semua_nama = re.findall(r'Nama\s*:\s*(.+)', teks_penuh, re.IGNORECASE)
        if len(semua_nama) >= 2:
            nama = semua_nama[1].strip()
            nama_bersih = re.sub(r'[\\/*?:"<>|]', '', nama)
            return nama_bersih.strip()
        elif len(semua_nama) == 1:
            nama = semua_nama[0].strip()
            nama_bersih = re.sub(r'[\\/*?:"<>|]', '', nama)
            return nama_bersih.strip()

    except Exception as e:
        print(f"   ⚠️  Error membaca {os.path.basename(pdf_path)}: {e}")

    return None


def buat_nama_file_unik(folder: Path, nama_base: str, ekstensi: str = ".pdf") -> str:
    """Kalau nama file sudah ada, tambahkan (2), (3), dst."""
    target = folder / f"{nama_base}{ekstensi}"
    if not target.exists():
        return f"{nama_base}{ekstensi}"

    counter = 2
    while True:
        nama_baru = f"{nama_base} ({counter}){ekstensi}"
        if not (folder / nama_baru).exists():
            return nama_baru
        counter += 1


def rename_faktur(folder: str, preview: bool = False):
    folder_path = Path(folder).resolve()

    if not folder_path.exists():
        print(f"❌ Folder tidak ditemukan: {folder_path}")
        sys.exit(1)

    pdf_files = sorted(folder_path.glob("*.pdf"))

    if not pdf_files:
        print(f"⚠️  Tidak ada file PDF di folder: {folder_path}")
        return

    processed_path = folder_path / "processed"
    if not preview:
        processed_path.mkdir(exist_ok=True)

    print(f"\n📁 Folder  : {folder_path}")
    print(f"📂 Output  : {processed_path}")
    print(f"📄 Total PDF: {len(pdf_files)} file")
    if preview:
        print("👁️  Mode    : PREVIEW (tidak ada file yang diubah)\n")
    else:
        print("✏️  Mode    : RENAME & PINDAH\n")

    print(f"{'NO':<4} {'FILE LAMA':<30} {'FILE BARU':<50} {'STATUS'}")
    print("-" * 110)

    berhasil = 0
    gagal = 0
    skip = 0

    for i, pdf_path in enumerate(pdf_files, 1):
        nama_file_lama = pdf_path.name

        # Skip kalau nama file sudah bukan angka random (sudah pernah direname)
        # Opsional: hapus kondisi ini kalau mau proses semua PDF
        nama_tanpa_ext = pdf_path.stem
        if not nama_tanpa_ext.replace(' ', '').replace('(', '').replace(')', '').replace('-', '').replace('_', '').isdigit():
            # Cek apakah ini memang sudah berbentuk nama perusahaan
            if re.search(r'(PT|CV|UD|PD|TB|KOPERASI)', nama_tanpa_ext, re.IGNORECASE):
                print(f"{i:<4} {nama_file_lama:<30} {'(sudah direname)':<50} ⏭️  SKIP")
                skip += 1
                continue

        nama_pembeli = ekstrak_nama_pembeli(str(pdf_path))

        if nama_pembeli:
            nama_file_baru = buat_nama_file_unik(processed_path, nama_pembeli)
            status = "✅ OK"

            if not preview:
                try:
                    shutil.move(str(pdf_path), str(processed_path / nama_file_baru))
                except Exception as e:
                    status = f"❌ ERROR: {e}"
                    gagal += 1
                    print(f"{i:<4} {nama_file_lama:<30} {nama_file_baru:<50} {status}")
                    continue

            berhasil += 1
            print(f"{i:<4} {nama_file_lama:<30} {nama_file_baru:<50} {status}")
        else:
            status = "❌ Nama tidak ditemukan"
            gagal += 1
            print(f"{i:<4} {nama_file_lama:<30} {'(tidak berubah)':<50} {status}")

    print("-" * 110)
    print(f"\n📊 Ringkasan:")
    print(f"   ✅ Berhasil : {berhasil} file")
    print(f"   ❌ Gagal    : {gagal} file")
    print(f"   ⏭️  Dilewati : {skip} file")

    if preview and berhasil > 0:
        print(f"\n💡 Jalankan tanpa --preview untuk eksekusi rename.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Auto-rename faktur pajak Coretax berdasarkan nama client"
    )
    parser.add_argument(
        "--folder",
        default=".",
        help="Folder berisi PDF faktur pajak (default: folder saat ini)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="Dry run: tampilkan preview tanpa rename"
    )

    args = parser.parse_args()
    rename_faktur(args.folder, args.preview)
