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
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS harga (
            ticker TEXT NOT NULL,
            tanggal TEXT NOT NULL,
            close REAL NOT NULL CHECK (close > 0),
            PRIMARY KEY (ticker, tanggal)
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


def simpan_harga(conn, ticker, pasangan_tanggal_harga):
    # Upsert, bukan insert murni - refresh untuk tanggal yang sama harus
    # MEMPERBARUI close-nya (harga bisa direvisi Yahoo Finance setelah
    # penutupan), bukan ditolak sebagai duplikat PRIMARY KEY. Beda sengaja
    # dari tambah_posisi yang menolak duplikat (409) - "refresh" secara
    # semantik memang berarti timpa yang lama dengan yang baru.
    for tanggal, close in pasangan_tanggal_harga:
        conn.execute(
            """
            INSERT INTO harga (ticker, tanggal, close) VALUES (?, ?, ?)
            ON CONFLICT (ticker, tanggal) DO UPDATE SET close = excluded.close
            """,
            (ticker, tanggal, close),
        )
    conn.commit()


def ambil_laporan_mentah(conn):
    # greatest-n-per-group (n=2: harga terakhir + hari sebelumnya, untuk
    # hitung return_harian) lewat window function - cara paling langsung
    # menyatakan "ranking baris per grup, ambil N teratas", dibanding
    # correlated subquery atau self-join untuk kasus n=2. LEFT JOIN (bukan
    # INNER) supaya posisi tanpa satu baris harga pun tidak pernah lenyap
    # diam-diam dari hasil - itu persis "ketiadaan yang terlihat seperti
    # keberhasilan" yang sudah ditegakkan di seluruh proyek ini.
    baris = conn.execute(
        """
        WITH harga_terurut AS (
            SELECT
                ticker,
                tanggal,
                close,
                ROW_NUMBER() OVER (
                    PARTITION BY ticker ORDER BY tanggal DESC
                ) AS rn
            FROM harga
        )
        SELECT
            p.ticker AS ticker,
            p.lot AS lot,
            p.harga_beli AS harga_beli,
            h.tanggal AS tanggal,
            h.close AS close,
            h.rn AS rn
        FROM posisi p
        LEFT JOIN harga_terurut h ON h.ticker = p.ticker AND h.rn <= 2
        ORDER BY p.ticker, h.rn
        """
    ).fetchall()
    return [dict(b) for b in baris]
