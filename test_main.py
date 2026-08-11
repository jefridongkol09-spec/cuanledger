import sqlite3

from fastapi.testclient import TestClient

from main import app, get_db
from db import buat_skema


def _override_get_db(db_path):
    def _override():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    return _override


def test_get_posisi_mengembalikan_data(tmp_path):
    # Data ditanam lewat insert langsung ke DB, bukan lewat POST - kegagalan
    # POST tidak boleh menjatuhkan tes GET ini. Isolasi antar-endpoint sama
    # pentingnya dengan isolasi antar-tes.
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    buat_skema(conn)
    conn.execute(
        "INSERT INTO posisi (ticker, lot, harga_beli) VALUES (?, ?, ?)",
        ("BBCA", 10, 9500),
    )
    conn.commit()
    conn.close()

    app.dependency_overrides[get_db] = _override_get_db(db_path)
    try:
        client = TestClient(app)
        response = client.get("/posisi")

        assert response.status_code == 200
        assert response.json() == [{"ticker": "BBCA", "lot": 10, "harga_beli": 9500}]
    finally:
        app.dependency_overrides.clear()
