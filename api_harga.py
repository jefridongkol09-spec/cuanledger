import sys

import pandas as pd
import yfinance as yf


def _tidak_valid(harga):
    # NaN dan harga 0 sama-sama tanda data korup/delisting di IDX - harga
    # saham sah tidak pernah 0. Satu kebijakan untuk keduanya, bukan dua.
    return pd.isna(harga) or harga == 0


def ambil_harga_online(ticker, hari=5):
    try:
        saham = yf.Ticker(f"{ticker}.JK")
        riwayat = saham.history(period=f"{hari}d")
    except Exception:
        return None

    tanggal = list(riwayat.index)
    tutup = list(riwayat["Close"])

    # buang harga tidak valid di ekor (hari yang belum ditutup) - boleh
    # berapa pun jumlahnya.
    while tutup and _tidak_valid(tutup[-1]):
        tutup.pop()
        tanggal.pop()

    if not tutup:
        return None

    # harga tidak valid yang tersisa berarti ada hari bolong di TENGAH data.
    # Kalau dibuang begitu saja, hari sebelum dan sesudah gap jadi terlihat
    # "berurutan" di list, dan hitung_return_harian akan menghitung return
    # lintas-gap itu seolah return satu hari. Tolak seluruh data, jangan
    # disambung diam-diam.
    if any(_tidak_valid(harga) for harga in tutup):
        print(
            f"PERINGATAN: data harga {ticker} punya hari bolong di tengah, ditolak",
            file=sys.stderr,
        )
        return None

    return {
        "harga": [round(float(harga), 2) for harga in tutup],
        "tanggal_terakhir": tanggal[-1].strftime("%Y-%m-%d"),
    }
