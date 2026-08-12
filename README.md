# cuanledger

![CI](https://github.com/jefridongkol09-spec/cuanledger/actions/workflows/ci.yml/badge.svg)

API portofolio saham IDX — FastAPI + SQLite. Evolusi dari [prosperidr](https://github.com/jefridongkol09-spec/prosperidr) (CLI + CSV): business logic yang sama (`algoritma.py`, `api_harga.py`, dibawa masuk beserta 14 tes yang menyertainya) dibungkus jadi API dengan database sungguhan alih-alih file lokal. prosperidr membuktikan kemampuan menulis dan menguji Python; cuanledger membuktikan kemampuan mendesain kontrak — REST, SQL, dan kejujuran soal ketiadaan data — di atas fondasi yang sama.

## Untuk siapa

Pembaca README ini adalah pengguna API: yang dibutuhkan adalah kontrak (endpoint, status code, bentuk JSON), bukan daftar perintah terminal seperti di prosperidr. Kalau Anda mencari CLI portofolio yang jalan langsung dari terminal, prosperidr itu tujuannya; cuanledger untuk melihat bagaimana logika yang sama dibungkus jadi layanan HTTP dengan database.

## Instalasi & menjalankan

```
git clone https://github.com/jefridongkol09-spec/cuanledger.git
cd cuanledger
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn main:app --reload
```

(di Linux/macOS: `source .venv/bin/activate` alih-alih `Activate.ps1`. Windows: gunakan `py` alih-alih `python` kalau `python` tidak dikenali — masalah stub Microsoft Store yang sama seperti di prosperidr.)

Server berjalan di `http://127.0.0.1:8000`. FastAPI menyediakan dokumentasi interaktif gratis di **`http://127.0.0.1:8000/docs`** (Swagger UI) — bisa mencoba semua endpoint langsung dari browser tanpa `curl`, dengan skema request/response yang di-generate otomatis dari kode.

## Alur pemakaian

Dua langkah, bukan satu, karena `GET /laporan` sengaja tidak pernah menyentuh jaringan (lihat Keputusan Desain):

1. `POST /harga/refresh` — ambil harga live untuk semua ticker di `posisi`, simpan ke cache.
2. `GET /laporan` — baca cache itu, hitung laporan.

**Catatan intraday**: harga yang diambil `POST /harga/refresh` sebelum ~16:00 WIB adalah harga *berjalan* (belum settled), bukan penutupan final — sama seperti keterbatasan yang sudah dicatat di prosperidr, tapi lebih penting di sini karena klien API lebih mudah salah mengira angka itu presisi dibanding pengguna CLI yang mengetik sendiri dan tahu kapan dia menjalankannya.

## Endpoint

### `POST /posisi` — tambah posisi

```
$ curl -X POST localhost:8000/posisi -d '{"ticker":"BBCA","lot":10,"harga_beli":9500}'
{"ticker":"BBCA","lot":10,"harga_beli":9500}
```

`201 Created`. Ticker dinormalisasi uppercase di gerbang (`bbca` → `BBCA`) — invarian yang sama ditegakkan ulang di setiap endpoint yang menerima ticker, bukan cuma di sini.

Duplikat ditolak, bukan digabung:

```
$ curl -X POST localhost:8000/posisi -d '{"ticker":"BBCA","lot":5,"harga_beli":9000}'
{"detail":"Posisi BBCA sudah ada"}
```

`409 Conflict`.

Validasi gagal:

```
$ curl -X POST localhost:8000/posisi -d '{"ticker":"XYZZ","lot":0,"harga_beli":1000}'
{"detail":[{"type":"greater_than","loc":["body","lot"],"msg":"Input should be greater than 0","input":0,"ctx":{"gt":0}}]}
```

`422 Unprocessable Entity`.

### `GET /posisi` — daftar posisi

```
$ curl localhost:8000/posisi
[{"ticker":"BBCA","lot":10,"harga_beli":9500}]
```

### `DELETE /posisi/{ticker}` — hapus posisi

```
$ curl -X DELETE localhost:8000/posisi/BBCA   # 204 No Content
$ curl -X DELETE localhost:8000/posisi/BBCA   # 404 Not Found (sudah tidak ada)
```

### `POST /harga/refresh` — ambil harga live, simpan ke cache

```
$ curl -X POST localhost:8000/harga/refresh
{"diperbarui":["BBCA","TLKM"],"gagal":[]}
```

`200 OK` selalu, termasuk saat sebagian ticker gagal — kegagalan per-ticker adalah informasi di body, bukan status HTTP:

```json
{"diperbarui": ["BBCA"], "gagal": [{"ticker": "BBRI", "alasan": "gagal mengambil harga"}]}
```

### `GET /laporan` — laporan P/L

```
$ curl localhost:8000/laporan
```
```json
{
  "posisi": [
    {"ticker": "BBCA", "tanggal": "2026-08-12", "harga": 6350.0, "return_harian": 0.79,
     "nilai_pasar": 6350000.0, "modal": 9500000, "pl": -3150000.0, "pl_persen": -33.16},
    {"ticker": "TLKM", "tanggal": "2026-08-12", "harga": 2590.0, "return_harian": -0.77,
     "nilai_pasar": 3885000.0, "modal": 5550000, "pl": -1665000.0, "pl_persen": -30.0}
  ],
  "total": {"nilai_pasar": 10235000.0, "modal": 15050000, "pl": -4815000.0, "pl_persen": -31.99},
  "vintage_campuran": false,
  "tanggal_berbeda": [],
  "posisi_tanpa_harga": []
}
```

(Output nyata dari server yang benar-benar dijalankan, bukan dikarang — makanya harganya kelihatan jelek hari ini.)

## Kontrak `GET /laporan`: tiga tingkat ketiadaan

Nilai yang di prosperidr tercetak sebagai `N/A`/`TOTAL*`/`PERINGATAN` (dibaca manusia) di sini jadi struktur yang bisa diperiksa mesin:

**Posisi tanpa harga sama sekali** (`LEFT JOIN` mempertahankan barisnya — lihat Keputusan Desain — `modal` tetap tampil karena tidak bergantung harga saat ini, field lain `null`, ticker-nya masuk `posisi_tanpa_harga` di level atas, dan **dikeluarkan dari `total`**):
```json
{"ticker": "TLKM", "tanggal": null, "harga": null, "return_harian": null,
 "nilai_pasar": null, "modal": 5550000, "pl": null, "pl_persen": null}
```

**Satu titik data** (`return_harian` tidak terhitung karena tidak ada "kemarin" — `null` — tapi sisanya tetap terhitung dan masuk `total`):
```json
{"ticker": "BMRI", "tanggal": "2025-01-04", "harga": 6200, "return_harian": null,
 "nilai_pasar": 12400000, "modal": 12600000, "pl": -200000, "pl_persen": -1.59}
```

**Portofolio kosong**: `total: null` — bukan `ZeroDivisionError`, ditutup lewat invarian skema (`CHECK(lot>0)`/`CHECK(harga_beli>0)` menjamin setiap posisi berharga menyumbang modal positif), bukan `try/except` di sekitar pembagian.

**Vintage campuran**: kalau baris-baris posisi punya `tanggal` yang berbeda (mis. sebagian baru di-refresh, sebagian masih cache lama), `vintage_campuran: true` dan `tanggal_berbeda` berisi daftar tanggalnya — `total` tetap dijumlahkan (sama seperti `TOTAL*` di prosperidr), penandaannya yang terstruktur, bukan angkanya disembunyikan.

**Diskrepansi yang perlu diketahui klien**: karena `posisi_tanpa_harga` dikeluarkan dari agregat, `total.modal` **tidak sama dengan** jumlah field `modal` di semua baris `posisi`. `total` merepresentasikan "ringkasan posisi berharga", bukan "seluruh modal yang tertanam". Keputusan sadar, bukan bug.

## Keputusan desain

### Keputusan REST

**`DELETE` sukses = `204 No Content`, bukan `200` dengan body.** Tidak ada apa pun yang berarti untuk dikembalikan setelah delete — klien sudah tahu ticker apa yang mereka minta hapus, ada di URL-nya sendiri.

**`DELETE` ticker tidak ada = `404`, bukan `204` idempoten.** Bertentangan dengan doktrin idempotency HTTP murni, tapi konsisten dengan nilai yang berulang kali ditegakkan di kedua proyek ini: ketiadaan tidak boleh terlihat seperti keberhasilan. Klien tunggal API ini kemungkinan besar skrip/frontend sendiri di masa depan — `404` adalah sinyal debug yang berguna (ticker salah ketik), bukan gesekan retry-safety yang relevan untuk API multi-klien terdistribusi.

**`POST /posisi` menolak duplikat (`409`), bukan merge diam-diam** seperti `tambah` di CLI prosperidr. `POST` ke koleksi berarti "buat resource baru" secara konvensi REST — mengubah resource yang sudah ada lewat `POST` yang sama adalah kejutan yang seharusnya bisa dihindari.

**`GET /laporan` tetap murni selamanya; `POST /harga/refresh` terpisah.** Alur natural "fetch live lalu simpan ke cache" akan membuat `GET /laporan?live=true` menulis database — melanggar jaminan *safe method* `GET`. Dua alternatif ditolak dengan alasan masing-masing:
- *GET menulis cache, didokumentasikan* — ditolak: seluruh alasan tabel `harga` dibangun (bukan lagi CSV statis) adalah supaya caching bisa jadi sesuatu yang sungguhan; `GET` yang diam-diam menulis mendapat manfaat itu dengan membelanjakan kontrak HTTP, padahal ada alternatif bersih dengan biaya terbatas.
- *GET murni, hasil live dipakai lalu dibuang* — ditolak setelah diverifikasi (bukan diasumsikan) bahwa prosperidr sendiri **juga** tidak pernah menyimpan hasil live fetch-nya — opsi ini cuma mereproduksi keterbatasan itu, padahal sekarang ada database yang dibangun spesifik supaya tidak perlu begitu lagi.

### Keputusan teknis lain

**SQL mentah lewat `sqlite3` bawaan Python, bukan ORM.** Tujuan strategis proyek ini adalah SQL yang bisa dipertanggungjawabkan di wawancara — ORM menyembunyikan SQL persis di fase yang seharusnya disentuh langsung.

**Greatest-N-per-group via window function.** `return_harian` butuh dua harga terakhir per ticker — diselesaikan dengan `ROW_NUMBER() OVER (PARTITION BY ticker ORDER BY tanggal DESC)`, bukan correlated subquery atau self-join. Alat yang memang dirancang untuk kelas masalah ini.

**`LEFT JOIN` posisi↔harga, bukan `INNER JOIN`.** `INNER JOIN` akan menjatuhkan posisi tanpa data harga dari laporan tanpa suara.

**Parameterized query tanpa pengecualian.** Setiap nilai dari request klien masuk lewat placeholder (`cursor.execute("... WHERE ticker = ?", (ticker,))`), tidak pernah dirakit lewat f-string ke dalam SQL. Setiap request HTTP adalah trust boundary — beda dari prosperidr yang trust boundary-nya file CSV lokal.

**Validasi dua lapis.** Pydantic (skema request) adalah gerbang pertama, mengembalikan `422` sebelum data menyentuh database. `CHECK` constraint di skema SQLite adalah lapis kedua, defense-in-depth untuk jalur yang tidak lewat Pydantic (termasuk tes yang menanam data lewat insert langsung). `IntegrityError` dari lapis ini diterjemahkan eksplisit jadi `4xx`, tidak pernah dibiarkan bocor jadi `500` mentah.

**Kebijakan harga tidak valid (nol/NaN) naik jadi `CHECK (close > 0)` di skema** — kenaikan langsung dari kebijakan runtime yang sama di prosperidr, sekarang ditegakkan database, bukan filter Python.

## Non-goals

- **Single-user.** Tidak ada konsep banyak pengguna atau kepemilikan data per akun.
- **Tanpa autentikasi.** Siapa pun yang bisa mengakses API bisa membaca/menulis semua data.
- **Tanpa deployment/hosting.** Dijalankan lokal untuk demo, bukan dioperasikan di server publik.
- **Tanpa penanganan concurrent-write** di luar locking bawaan SQLite.

## Evolusi dari pitch awal

Rencana awal proyek ini adalah `GET /laporan?live=true` — query parameter yang memicu fetch live di endpoint yang sama dengan laporan. Itu berubah jadi `POST /harga/refresh` terpisah begitu jelas bahwa opsi itu berarti `GET` dengan efek samping tulis, melanggar *safe method*. Perubahan bentuk ini didokumentasikan di sini, bukan disembunyikan — README yang ditulis setelah desain final selesai gampang terlihat rapi karena tidak pernah menceritakan jalan yang ditolak; bagian "Keputusan desain" di atas ada supaya jalan yang ditolak itu tetap terlihat.

## Menjalankan tes

```
pip install -r requirements.txt
pytest -v
```

Test suite (46 tes) mencakup unit test murni yang tidak menyentuh database (`test_algoritma.py`, dan `susun_laporan()` di `laporan.py` yang diuji lewat `test_laporan.py` dengan data tangan) maupun tes integrasi lewat `TestClient` FastAPI dengan SQLite sekali pakai per tes.
