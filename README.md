# cuanledger

API portofolio saham IDX — FastAPI + SQLite. Evolusi dari [prosperidr](https://github.com/jefridongkol09-spec/prosperidr) (CLI + CSV): business logic yang sama (`algoritma.py`, `api_harga.py`, sudah teruji lewat 14 tes yang ikut dibawa) dibungkus jadi API dengan database sungguhan alih-alih file lokal.

## Status

Baru dimulai — endpoint pertama sedang dibangun. Halaman ini akan diperbarui seiring endpoint bertambah.

## Non-goals

Ditulis eksplisit sejak awal, bukan kelalaian yang ditemukan belakangan:

- **Single-user.** Tidak ada konsep banyak pengguna atau kepemilikan data per akun.
- **Tanpa autentikasi.** Siapa pun yang bisa mengakses API bisa membaca/menulis semua data.
- **Tanpa deployment/hosting.** Proyek ini dijalankan lokal untuk demo, bukan dioperasikan di server publik.
- **Tanpa penanganan concurrent-write** di luar locking bawaan SQLite.

## Keputusan desain

**SQL mentah lewat `sqlite3` bawaan Python, bukan ORM.** Tujuan strategis proyek ini adalah menguasai SQL yang bisa dipertanggungjawabkan di wawancara — ORM menyembunyikan SQL persis di fase yang seharusnya disentuh langsung. SQLAlchemy punya tempatnya, tapi bukan di sini.

**Parameterized query, tanpa pengecualian.** Setiap nilai dari request klien masuk ke query lewat placeholder (`cursor.execute("... WHERE ticker = ?", (ticker,))`), tidak pernah dirakit lewat f-string/format string ke dalam SQL. Setiap request HTTP adalah trust boundary — beda dari prosperidr yang trust boundary-nya adalah file CSV lokal.

**Validasi dua lapis.** Pydantic (skema request) adalah gerbang pertama — mengembalikan `422` yang jelas sebelum data menyentuh database. `CHECK` constraint di skema SQLite adalah lapis kedua, defense-in-depth untuk jalur yang tidak lewat Pydantic (termasuk tes yang menanam data lewat insert langsung). `IntegrityError` dari lapis ini diterjemahkan eksplisit jadi respons `4xx`, tidak pernah dibiarkan bocor jadi `500` mentah.

**`POST` menolak duplikat.** Menambah posisi untuk ticker yang sudah ada mengembalikan `409 Conflict`, bukan diam-diam di-merge — beda dari `tambah` di prosperidr yang menggabungkan otomatis. Endpoint untuk mengubah posisi yang sudah ada adalah keputusan terpisah, menunggu gilirannya.

## Menjalankan

```
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pytest -v
```
