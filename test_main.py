import sqlite3

import pytest
from fastapi.testclient import TestClient

import main
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


@pytest.fixture
def api(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    buat_skema(conn)
    conn.close()

    app.dependency_overrides[get_db] = _override_get_db(db_path)
    try:
        yield TestClient(app), db_path
    finally:
        app.dependency_overrides.clear()


def test_get_posisi_mengembalikan_data(api):
    # Data ditanam lewat insert langsung ke DB, bukan lewat POST - kegagalan
    # POST tidak boleh menjatuhkan tes GET ini. Isolasi antar-endpoint sama
    # pentingnya dengan isolasi antar-tes.
    client, db_path = api
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO posisi (ticker, lot, harga_beli) VALUES (?, ?, ?)",
        ("BBCA", 10, 9500),
    )
    conn.commit()
    conn.close()

    response = client.get("/posisi")

    assert response.status_code == 200
    assert response.json() == [{"ticker": "BBCA", "lot": 10, "harga_beli": 9500}]


def test_post_posisi_berhasil(api):
    client, db_path = api

    response = client.post("/posisi", json={"ticker": "BBCA", "lot": 10, "harga_beli": 9500})

    assert response.status_code == 201
    assert response.json() == {"ticker": "BBCA", "lot": 10, "harga_beli": 9500}

    # Verifikasi persistensi lewat baca langsung ke DB, bukan lewat GET -
    # isolasi antar-endpoint yang sama seperti alasan tes GET di atas.
    conn = sqlite3.connect(db_path)
    baris = conn.execute("SELECT ticker, lot, harga_beli FROM posisi").fetchall()
    conn.close()
    assert baris == [("BBCA", 10, 9500)]


def test_post_posisi_menolak_lot_nol(api):
    client, _ = api
    response = client.post("/posisi", json={"ticker": "BBCA", "lot": 0, "harga_beli": 9500})
    assert response.status_code == 422


def test_post_posisi_menolak_lot_negatif(api):
    client, _ = api
    response = client.post("/posisi", json={"ticker": "BBCA", "lot": -5, "harga_beli": 9500})
    assert response.status_code == 422


def test_post_posisi_menolak_harga_beli_nol(api):
    client, _ = api
    response = client.post("/posisi", json={"ticker": "BBCA", "lot": 10, "harga_beli": 0})
    assert response.status_code == 422


def test_post_posisi_menolak_field_hilang(api):
    client, _ = api
    response = client.post("/posisi", json={"ticker": "BBCA", "lot": 10})
    assert response.status_code == 422


def test_post_posisi_menolak_tipe_salah(api):
    client, _ = api
    response = client.post(
        "/posisi", json={"ticker": "BBCA", "lot": "sepuluh", "harga_beli": 9500}
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert any("lot" in str(err.get("loc")) for err in detail)


def test_post_posisi_duplikat_ditolak(api):
    client, _ = api
    client.post("/posisi", json={"ticker": "BBCA", "lot": 10, "harga_beli": 9500})

    response = client.post("/posisi", json={"ticker": "BBCA", "lot": 5, "harga_beli": 9000})

    assert response.status_code == 409
    assert "BBCA" in response.json()["detail"]


def test_post_posisi_ticker_dinormalisasi_uppercase(api):
    client, db_path = api

    response = client.post("/posisi", json={"ticker": "bbca", "lot": 10, "harga_beli": 9500})

    assert response.status_code == 201
    assert response.json()["ticker"] == "BBCA"

    conn = sqlite3.connect(db_path)
    tickers = [baris[0] for baris in conn.execute("SELECT ticker FROM posisi").fetchall()]
    conn.close()
    assert tickers == ["BBCA"]


def test_post_posisi_duplikat_case_insensitive(api):
    # Konsekuensi langsung dari normalisasi uppercase: "bbca" dan "BBCA"
    # harus terdeteksi sebagai ticker yang sama, bukan dua posisi berbeda.
    client, _ = api
    client.post("/posisi", json={"ticker": "BBCA", "lot": 10, "harga_beli": 9500})

    response = client.post("/posisi", json={"ticker": "bbca", "lot": 5, "harga_beli": 9000})

    assert response.status_code == 409


def _tanam(db_path, ticker, lot, harga_beli):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO posisi (ticker, lot, harga_beli) VALUES (?, ?, ?)",
        (ticker, lot, harga_beli),
    )
    conn.commit()
    conn.close()


def _ticker_tersisa(db_path):
    conn = sqlite3.connect(db_path)
    tickers = {baris[0] for baris in conn.execute("SELECT ticker FROM posisi").fetchall()}
    conn.close()
    return tickers


def _tanam_harga(db_path, ticker, tanggal, close):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO harga (ticker, tanggal, close) VALUES (?, ?, ?)",
        (ticker, tanggal, close),
    )
    conn.commit()
    conn.close()


def test_delete_posisi_berhasil(api):
    client, db_path = api
    _tanam(db_path, "BBCA", 10, 9500)

    response = client.delete("/posisi/BBCA")

    assert response.status_code == 204
    assert _ticker_tersisa(db_path) == set()


def test_delete_posisi_tidak_ditemukan(api):
    client, _ = api
    response = client.delete("/posisi/BBCA")
    assert response.status_code == 404


def test_delete_posisi_lintas_case(api):
    # Jebakan yang sama seperti normalisasi POST: ticker path parameter tidak
    # lewat model Pydantic sama sekali - gerbang berbeda, jadi normalisasi
    # harus ditegakkan ulang di sini secara eksplisit, bukan diasumsikan
    # otomatis mengikuti dari validator POST.
    client, db_path = api
    _tanam(db_path, "BBCA", 10, 9500)

    response = client.delete("/posisi/bbca")

    assert response.status_code == 204
    assert _ticker_tersisa(db_path) == set()


def test_delete_posisi_selektif(api):
    # Kontrol positif, pola yang sama dengan test_hapus_ticker di
    # prosperidr: membuktikan delete tidak menghapus semua baris, hanya
    # yang diminta - operasi destruktif pertama API ini wajib dibuktikan
    # selektif, bukan cuma "berhasil".
    client, db_path = api
    _tanam(db_path, "BBCA", 10, 9500)
    _tanam(db_path, "BBRI", 50, 4400)

    response = client.delete("/posisi/BBCA")

    assert response.status_code == 204
    assert _ticker_tersisa(db_path) == {"BBRI"}


def test_get_laporan_menggabungkan_posisi_dan_harga(api):
    # Tes integrasi end-to-end untuk JOIN + agregasi: membuktikan
    # ambil_laporan_mentah (SQL) dan susun_laporan (Python murni, sudah
    # diuji terpisah di test_laporan.py) benar-benar tersambung lewat
    # endpoint sungguhan - bukan cuma masing-masing benar sendiri-sendiri.
    client, db_path = api
    _tanam(db_path, "BBCA", 10, 9500)
    _tanam_harga(db_path, "BBCA", "2025-01-03", 9700)
    _tanam_harga(db_path, "BBCA", "2025-01-04", 9900)

    response = client.get("/laporan")

    assert response.status_code == 200
    body = response.json()
    assert body["posisi"] == [
        {
            "ticker": "BBCA",
            "tanggal": "2025-01-04",
            "harga": 9900,
            "return_harian": 2.06,
            "nilai_pasar": 9900000,
            "modal": 9500000,
            "pl": 400000,
            "pl_persen": 4.21,
        }
    ]
    assert body["total"]["pl"] == 400000
    assert body["vintage_campuran"] is False
    assert body["posisi_tanpa_harga"] == []


def _harga_tersimpan(db_path, ticker):
    conn = sqlite3.connect(db_path)
    baris = conn.execute(
        "SELECT tanggal, close FROM harga WHERE ticker = ? ORDER BY tanggal", (ticker,)
    ).fetchall()
    conn.close()
    return baris


def test_refresh_harga_berhasil(api, monkeypatch):
    client, db_path = api
    _tanam(db_path, "BBCA", 10, 9500)

    monkeypatch.setattr(
        main,
        "ambil_harga_online",
        lambda ticker: {
            "harga": [9700.0, 9900.0],
            "tanggal": ["2025-01-03", "2025-01-04"],
            "tanggal_terakhir": "2025-01-04",
        },
    )

    response = client.post("/harga/refresh")

    assert response.status_code == 200
    assert response.json() == {"diperbarui": ["BBCA"], "gagal": []}
    assert _harga_tersimpan(db_path, "BBCA") == [
        ("2025-01-03", 9700.0),
        ("2025-01-04", 9900.0),
    ]


def test_refresh_harga_sebagian_gagal_tidak_menghentikan_yang_lain(api, monkeypatch):
    # Mencakup skenario timeout: ambil_harga_online sengaja tidak
    # membedakan timeout dari kegagalan lain (lihat api_harga.py -
    # bentuk kegagalan API eksternal tidak bisa diprediksi, jadi tidak
    # dipura-pura dibedakan). Kegagalan generik ini SAMA dengan reaksi
    # yang diharapkan untuk timeout - satu tes ini membuktikan keduanya:
    # partial-failure isolation dan reaksi terhadap timeout, tanpa
    # benar-benar menunggu apa pun.
    client, db_path = api
    _tanam(db_path, "BBCA", 10, 9500)
    _tanam(db_path, "BBRI", 50, 4400)

    def fetch_palsu(ticker):
        if ticker == "BBRI":
            return None  # simulasi timeout/kegagalan jaringan - sudah
            # ditangani di dalam ambil_harga_online, keluar sebagai None
        return {
            "harga": [4600.0],
            "tanggal": ["2025-01-04"],
            "tanggal_terakhir": "2025-01-04",
        }

    monkeypatch.setattr(main, "ambil_harga_online", fetch_palsu)

    response = client.post("/harga/refresh")

    assert response.status_code == 200
    body = response.json()
    assert body["diperbarui"] == ["BBCA"]
    assert body["gagal"] == [{"ticker": "BBRI", "alasan": "gagal mengambil harga"}]
    # BBCA tersimpan meski BBRI gagal - satu ticker gagal tidak boleh
    # menggagalkan refresh untuk ticker lain.
    assert _harga_tersimpan(db_path, "BBCA") == [("2025-01-04", 4600.0)]
    assert _harga_tersimpan(db_path, "BBRI") == []


def test_refresh_harga_posisi_kosong(api, monkeypatch):
    client, _ = api
    monkeypatch.setattr(main, "ambil_harga_online", lambda ticker: None)

    response = client.post("/harga/refresh")

    assert response.status_code == 200
    assert response.json() == {"diperbarui": [], "gagal": []}


def test_refresh_lalu_laporan_mencerminkan_data_baru(api, monkeypatch):
    # Bukti ujung-ke-ujung: refresh menulis ke tabel yang sama yang dibaca
    # GET /laporan - dua endpoint yang benar masing-masing tidak cukup,
    # harus benar-benar tersambung.
    client, db_path = api
    _tanam(db_path, "BBCA", 10, 9500)

    monkeypatch.setattr(
        main,
        "ambil_harga_online",
        lambda ticker: {
            "harga": [9700.0, 9900.0],
            "tanggal": ["2025-01-03", "2025-01-04"],
            "tanggal_terakhir": "2025-01-04",
        },
    )
    client.post("/harga/refresh")

    response = client.get("/laporan")

    assert response.status_code == 200
    posisi = response.json()["posisi"][0]
    assert posisi["harga"] == 9900.0
    assert posisi["return_harian"] == 2.06
