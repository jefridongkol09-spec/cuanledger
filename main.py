import os
import sqlite3

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from db import (
    get_connection,
    buat_skema,
    ambil_semua_posisi,
    tambah_posisi,
    hapus_posisi,
    ambil_laporan_mentah,
)
from laporan import susun_laporan

DB_PATH = os.environ.get("CUANLEDGER_DB", "cuanledger.db")

app = FastAPI()


def get_db():
    conn = get_connection(DB_PATH)
    buat_skema(conn)
    try:
        yield conn
    finally:
        conn.close()


def normalisasi_ticker(ticker: str) -> str:
    # Ticker IDX konvensinya uppercase, dan tanpa normalisasi ini,
    # "bbca"/"BBCA"/"Bbca" akan lolos sebagai posisi berbeda lewat PRIMARY
    # KEY yang case-sensitive - bug integritas data, bukan cuma gaya
    # penulisan. Invarian ini bukan milik satu endpoint - setiap gerbang
    # masuk (body POST lewat Pydantic, path parameter DELETE, query param
    # nanti) wajib memanggil fungsi yang sama, bukan menulis ulang
    # .upper()-nya sendiri-sendiri dan diam-diam menyimpang.
    return ticker.strip().upper()


class PosisiIn(BaseModel):
    ticker: str = Field(min_length=1)
    lot: int = Field(gt=0)
    harga_beli: int = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def _normalisasi_ticker(cls, v):
        return normalisasi_ticker(v)


@app.get("/posisi")
def baca_posisi(conn=Depends(get_db)):
    return ambil_semua_posisi(conn)


@app.post("/posisi", status_code=201)
def buat_posisi(data: PosisiIn, conn=Depends(get_db)):
    try:
        tambah_posisi(conn, data.ticker, data.lot, data.harga_beli)
    except sqlite3.IntegrityError:
        # Satu-satunya IntegrityError yang realistis tersisa di titik ini
        # adalah pelanggaran PRIMARY KEY (ticker) - Pydantic sudah menutup
        # lot/harga_beli <= 0 sebelum sampai sini. Diterjemahkan eksplisit
        # jadi 409, bukan dibiarkan bocor jadi 500 mentah.
        raise HTTPException(status_code=409, detail=f"Posisi {data.ticker} sudah ada")

    return {"ticker": data.ticker, "lot": data.lot, "harga_beli": data.harga_beli}


@app.delete("/posisi/{ticker}", status_code=204)
def hapus_posisi_endpoint(ticker: str, conn=Depends(get_db)):
    ticker = normalisasi_ticker(ticker)
    berhasil = hapus_posisi(conn, ticker)
    if not berhasil:
        # Ketiadaan tidak boleh terlihat seperti keberhasilan - nilai yang
        # sama yang sudah ditegakkan di return_harian dan TOTAL* di
        # prosperidr. Klien tunggal proyek ini butuh sinyal debug yang jujur
        # (ticker salah ketik, state basi), bukan 204 idempoten yang
        # menyerap kesalahan itu diam-diam.
        raise HTTPException(status_code=404, detail=f"Posisi {ticker} tidak ditemukan")


@app.get("/laporan")
def baca_laporan(conn=Depends(get_db)):
    # def biasa, bukan async def - FastAPI/Starlette otomatis menjalankan
    # handler sinkron ini di threadpool eksternal, jadi panggilan blocking
    # (sqlite3 di sini, yfinance nanti di ?live=true) tidak membekukan
    # event loop tanpa perlu run_in_threadpool manual.
    baris_mentah = ambil_laporan_mentah(conn)
    return susun_laporan(baris_mentah)
