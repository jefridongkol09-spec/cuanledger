import sqlite3

import pytest

from db import buat_skema, simpan_harga


def test_skema_menolak_lot_nol_meski_pydantic_dilewati(tmp_path):
    # Bukan red-first dalam arti "belum dibangun" - CHECK constraint ini
    # sudah ada sejak PR #1. Ini mengunci bukti bahwa lapis kedua benar-benar
    # hidup: insert langsung ke DB (melewati Pydantic sepenuhnya, seperti
    # yang dilakukan tes-tes GET sebelumnya) tetap ditolak.
    conn = sqlite3.connect(tmp_path / "test.db")
    buat_skema(conn)

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO posisi (ticker, lot, harga_beli) VALUES (?, ?, ?)",
            ("BBCA", 0, 9500),
        )


def test_skema_harga_menolak_close_nol_atau_negatif(tmp_path):
    # Kenaikan langsung dari kebijakan _tidak_valid lama di prosperidr (0/NaN
    # = data korup, bukan harga pasar sah) - sekarang jadi CHECK constraint
    # di skema, bukan filter runtime di kode Python.
    conn = sqlite3.connect(tmp_path / "test.db")
    buat_skema(conn)

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO harga (ticker, tanggal, close) VALUES (?, ?, ?)",
            ("BBCA", "2025-01-01", 0),
        )


def test_skema_harga_menolak_duplikat_ticker_tanggal(tmp_path):
    # PRIMARY KEY (ticker, tanggal) komposit: satu harga per ticker per hari.
    # Feed harga yang mengirim baris duplikat untuk hari yang sama harus
    # ditolak sebagai IntegrityError, bukan diam-diam jadi baris ganda.
    conn = sqlite3.connect(tmp_path / "test.db")
    buat_skema(conn)
    conn.execute(
        "INSERT INTO harga (ticker, tanggal, close) VALUES (?, ?, ?)",
        ("BBCA", "2025-01-01", 9800),
    )
    conn.commit()

    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO harga (ticker, tanggal, close) VALUES (?, ?, ?)",
            ("BBCA", "2025-01-01", 9850),
        )


def test_simpan_harga_insert_baru(tmp_path):
    conn = sqlite3.connect(tmp_path / "test.db")
    buat_skema(conn)

    simpan_harga(conn, "BBCA", [("2025-01-01", 9800), ("2025-01-02", 9850)])

    baris = conn.execute(
        "SELECT ticker, tanggal, close FROM harga ORDER BY tanggal"
    ).fetchall()
    assert baris == [("BBCA", "2025-01-01", 9800), ("BBCA", "2025-01-02", 9850)]


def test_simpan_harga_upsert_menimpa_yang_sudah_ada(tmp_path):
    # Refresh berikutnya untuk tanggal yang sama harus MEMPERBARUI close-nya
    # (harga bisa direvisi/dikoreksi Yahoo Finance), bukan ditolak sebagai
    # duplikat PRIMARY KEY - beda dari tambah_posisi yang sengaja menolak
    # duplikat (409). Semantik "refresh" secara inheren berarti upsert.
    conn = sqlite3.connect(tmp_path / "test.db")
    buat_skema(conn)
    simpan_harga(conn, "BBCA", [("2025-01-01", 9800)])

    simpan_harga(conn, "BBCA", [("2025-01-01", 9999)])

    baris = conn.execute("SELECT ticker, tanggal, close FROM harga").fetchall()
    assert baris == [("BBCA", "2025-01-01", 9999)]
