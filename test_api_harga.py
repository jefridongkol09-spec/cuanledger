import pandas as pd

import api_harga


class FakeTicker:
    def __init__(self, riwayat):
        self._riwayat = riwayat

    def history(self, period):
        return self._riwayat


def buat_df(close, tanggal):
    return pd.DataFrame({"Close": close}, index=pd.to_datetime(tanggal))


def test_ambil_harga_online_berhasil(monkeypatch):
    simbol_dipakai = []

    def fake_ticker(simbol):
        simbol_dipakai.append(simbol)
        df = buat_df([100.123, 200.456], ["2026-08-03", "2026-08-04"])
        return FakeTicker(df)

    monkeypatch.setattr(api_harga.yf, "Ticker", fake_ticker)

    hasil = api_harga.ambil_harga_online("BBCA")

    assert hasil == {"harga": [100.12, 200.46], "tanggal_terakhir": "2026-08-04"}
    assert simbol_dipakai == ["BBCA.JK"]


def test_ambil_harga_online_hari_terakhir_belum_tersedia(monkeypatch):
    # Hari terakhir kadang NaN (closing price belum dilaporkan Yahoo Finance)
    # tanpa DataFrame-nya kosong - harus dibuang, dan tanggal_terakhir harus
    # ikut mundur ke hari valid terakhir, bukan diam-diam tetap hari ini.
    df = buat_df([100.0, 200.0, float("nan")], ["2026-08-03", "2026-08-04", "2026-08-05"])
    monkeypatch.setattr(api_harga.yf, "Ticker", lambda simbol: FakeTicker(df))

    hasil = api_harga.ambil_harga_online("BBCA")

    assert hasil == {"harga": [100.0, 200.0], "tanggal_terakhir": "2026-08-04"}


def test_ambil_harga_online_nan_di_tengah_ditolak(monkeypatch, capsys):
    # NaN di TENGAH (bukan di ekor) berarti ada hari bolong - kalau dibuang
    # begitu saja lewat dropna(), hari sebelum dan sesudah gap jadi "berurutan"
    # secara list, dan hitung_return_harian akan menghitung return lintas-gap
    # itu seolah return satu hari. Data begini harus ditolak, bukan disambung.
    df = buat_df(
        [100.0, float("nan"), 105.0],
        ["2026-08-03", "2026-08-04", "2026-08-05"],
    )
    monkeypatch.setattr(api_harga.yf, "Ticker", lambda simbol: FakeTicker(df))

    hasil = api_harga.ambil_harga_online("BBCA")

    assert hasil is None
    assert "PERINGATAN" in capsys.readouterr().err


def test_ambil_harga_online_nol_di_tengah_ditolak(monkeypatch, capsys):
    # Kebijakan disatukan dengan NaN: harga 0 di IDX tidak pernah sah - sama
    # seperti NaN, keduanya tanda data korup/delisting, bukan pergerakan
    # pasar nyata. 0 di TENGAH window menolak seluruh data, sama seperti NaN.
    df = buat_df([100.0, 0.0, 105.0], ["2026-08-03", "2026-08-04", "2026-08-05"])
    monkeypatch.setattr(api_harga.yf, "Ticker", lambda simbol: FakeTicker(df))

    hasil = api_harga.ambil_harga_online("BBCA")

    assert hasil is None
    assert "PERINGATAN" in capsys.readouterr().err


def test_ambil_harga_online_nol_di_ekor_dibuang(monkeypatch):
    # 0 di EKOR (hari terakhir) diperlakukan sama seperti NaN di ekor -
    # dibuang, mundur ke hari valid terakhir, bukan ikut menolak semuanya.
    df = buat_df([100.0, 200.0, 0.0], ["2026-08-03", "2026-08-04", "2026-08-05"])
    monkeypatch.setattr(api_harga.yf, "Ticker", lambda simbol: FakeTicker(df))

    hasil = api_harga.ambil_harga_online("BBCA")

    assert hasil == {"harga": [100.0, 200.0], "tanggal_terakhir": "2026-08-04"}


def test_ambil_harga_online_semua_nan(monkeypatch):
    df = buat_df([float("nan"), float("nan")], ["2026-08-03", "2026-08-04"])
    monkeypatch.setattr(api_harga.yf, "Ticker", lambda simbol: FakeTicker(df))

    assert api_harga.ambil_harga_online("BBCA") is None


def test_ambil_harga_online_kosong(monkeypatch):
    monkeypatch.setattr(
        api_harga.yf, "Ticker", lambda simbol: FakeTicker(pd.DataFrame({"Close": []}))
    )

    assert api_harga.ambil_harga_online("TIDAKADA") is None


def test_ambil_harga_online_error_jaringan(monkeypatch):
    def gagal(simbol):
        raise ConnectionError("network down")

    monkeypatch.setattr(api_harga.yf, "Ticker", gagal)

    assert api_harga.ambil_harga_online("BBCA") is None
