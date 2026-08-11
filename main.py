import os

from fastapi import Depends, FastAPI

from db import get_connection, buat_skema, ambil_semua_posisi

DB_PATH = os.environ.get("CUANLEDGER_DB", "cuanledger.db")

app = FastAPI()


def get_db():
    conn = get_connection(DB_PATH)
    buat_skema(conn)
    try:
        yield conn
    finally:
        conn.close()


@app.get("/posisi")
def baca_posisi(conn=Depends(get_db)):
    return ambil_semua_posisi(conn)
