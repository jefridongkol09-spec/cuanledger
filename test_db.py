import sqlite3

import pytest

from db import buat_skema


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
