import os
import sqlite3

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from db import get_connection, buat_skema, ambil_semua_posisi, tambah_posisi

DB_PATH = os.environ.get("CUANLEDGER_DB", "cuanledger.db")

app = FastAPI()


def get_db():
    conn = get_connection(DB_PATH)
    buat_skema(conn)
    try:
        yield conn
    finally:
        conn.close()


class PosisiIn(BaseModel):
    ticker: str = Field(min_length=1)
    lot: int = Field(gt=0)
    harga_beli: int = Field(gt=0)

    @field_validator("ticker")
    @classmethod
    def normalisasi_ticker(cls, v):
        # Ticker IDX konvensinya uppercase, dan tanpa normalisasi di gerbang
        # ini, "bbca"/"BBCA"/"Bbca" akan lolos sebagai tiga posisi berbeda
        # lewat PRIMARY KEY yang case-sensitive - bug integritas data, bukan
        # cuma soal gaya penulisan.
        return v.strip().upper()


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
