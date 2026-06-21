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
