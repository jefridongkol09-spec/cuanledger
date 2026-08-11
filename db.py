import sqlite3


def get_connection(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def buat_skema(conn):
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS posisi (
            ticker TEXT PRIMARY KEY,
            lot INTEGER NOT NULL CHECK (lot > 0),
            harga_beli INTEGER NOT NULL CHECK (harga_beli > 0)
        )
        """
    )
    conn.commit()


def ambil_semua_posisi(conn):
    baris = conn.execute("SELECT ticker, lot, harga_beli FROM posisi").fetchall()
    return [dict(b) for b in baris]


def tambah_posisi(conn, ticker, lot, harga_beli):
    conn.execute(
        "INSERT INTO posisi (ticker, lot, harga_beli) VALUES (?, ?, ?)",
        (ticker, lot, harga_beli),
    )
    conn.commit()


def hapus_posisi(conn, ticker):
    cursor = conn.execute("DELETE FROM posisi WHERE ticker = ?", (ticker,))
    conn.commit()
    return cursor.rowcount > 0
