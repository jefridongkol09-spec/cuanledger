from laporan import susun_laporan


def test_susun_laporan_normal_dua_hari():
    baris = [
        {
            "ticker": "BBCA",
            "lot": 10,
            "harga_beli": 9500,
            "tanggal": "2025-01-04",
            "close": 9900,
            "rn": 1,
        },
        {
            "ticker": "BBCA",
            "lot": 10,
            "harga_beli": 9500,
            "tanggal": "2025-01-03",
            "close": 9700,
            "rn": 2,
        },
    ]

    hasil = susun_laporan(baris)

    assert hasil["posisi"] == [
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
    assert hasil["total"] == {
        "nilai_pasar": 9900000,
        "modal": 9500000,
        "pl": 400000,
        "pl_persen": 4.21,
    }
    assert hasil["vintage_campuran"] is False
    assert hasil["tanggal_berbeda"] == []
    assert hasil["posisi_tanpa_harga"] == []


def test_susun_laporan_posisi_tanpa_harga():
    # LEFT JOIN mempertahankan baris posisi meski tidak ada harga sama
    # sekali - ketiadaan tidak boleh membuat posisi lenyap diam-diam dari
    # laporan maupun dari total.
    baris = [
        {
            "ticker": "TLKM",
            "lot": 15,
            "harga_beli": 3700,
            "tanggal": None,
            "close": None,
            "rn": None,
        }
    ]

    hasil = susun_laporan(baris)

    assert hasil["posisi"] == [
        {
            "ticker": "TLKM",
            "tanggal": None,
            "harga": None,
            "return_harian": None,
            "nilai_pasar": None,
            "modal": 5550000,
            "pl": None,
            "pl_persen": None,
        }
    ]
    assert hasil["total"] is None
    assert hasil["posisi_tanpa_harga"] == ["TLKM"]


def test_susun_laporan_satu_titik_data_return_harian_null():
    baris = [
        {
            "ticker": "BMRI",
            "lot": 20,
            "harga_beli": 6300,
            "tanggal": "2025-01-04",
            "close": 6200,
            "rn": 1,
        }
    ]

    hasil = susun_laporan(baris)

    posisi = hasil["posisi"][0]
    assert posisi["return_harian"] is None
    assert posisi["harga"] == 6200
    assert posisi["nilai_pasar"] == 12400000
    assert posisi["pl"] == -200000
    assert posisi["pl_persen"] == -1.59
    # Satu titik data tetap masuk total - bedanya cuma return_harian yang
    # tidak terhitung, bukan seluruh posisinya jadi tidak diketahui.
    assert hasil["total"]["modal"] == 12600000


def test_susun_laporan_vintage_campuran():
    baris = [
        {
            "ticker": "BBCA",
            "lot": 10,
            "harga_beli": 9500,
            "tanggal": "2025-01-04",
            "close": 9900,
            "rn": 1,
        },
        {
            "ticker": "BBCA",
            "lot": 10,
            "harga_beli": 9500,
            "tanggal": "2025-01-03",
            "close": 9700,
            "rn": 2,
        },
        {
            "ticker": "BBRI",
            "lot": 50,
            "harga_beli": 4400,
            "tanggal": "2025-01-03",
            "close": 4550,
            "rn": 1,
        },
    ]

    hasil = susun_laporan(baris)

    assert hasil["vintage_campuran"] is True
    assert hasil["tanggal_berbeda"] == ["2025-01-03", "2025-01-04"]
    # Total tetap dijumlahkan (sama seperti TOTAL* di prosperidr) - yang
    # berubah cuma penandaannya, bukan angkanya disembunyikan.
    assert hasil["total"] == {
        "nilai_pasar": 32650000,
        "modal": 31500000,
        "pl": 1150000,
        "pl_persen": 3.65,
    }


def test_susun_laporan_posisi_tanpa_harga_tidak_dihitung_sebagai_vintage_campuran():
    # Posisi tanpa harga (tanggal: None) hidup berdampingan dengan posisi
    # berharga - None tidak boleh ikut masuk himpunan tanggal_semua dan
    # dianggap "tanggal berbeda". Sudah benar secara konstruksi (continue
    # melewati baris tanggal_semua.add sebelum sempat dieksekusi untuk
    # posisi tanpa harga), tapi belum pernah dikunci dengan tes sampai
    # sekarang.
    baris = [
        {
            "ticker": "BBCA",
            "lot": 10,
            "harga_beli": 9500,
            "tanggal": "2025-01-04",
            "close": 9900,
            "rn": 1,
        },
        {
            "ticker": "TLKM",
            "lot": 15,
            "harga_beli": 3700,
            "tanggal": None,
            "close": None,
            "rn": None,
        },
    ]

    hasil = susun_laporan(baris)

    assert hasil["vintage_campuran"] is False
    assert hasil["tanggal_berbeda"] == []
    assert hasil["posisi_tanpa_harga"] == ["TLKM"]


def test_susun_laporan_posisi_kosong():
    hasil = susun_laporan([])

    assert hasil == {
        "posisi": [],
        "total": None,
        "vintage_campuran": False,
        "tanggal_berbeda": [],
        "posisi_tanpa_harga": [],
    }
