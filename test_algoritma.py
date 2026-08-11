from algoritma import cari_terbesar, cari_terkecil, hitung_rata_rata, hitung_return_harian


def test_cari_terbesar():
    assert cari_terbesar([3, 1, 4, 1, 5]) == 5
    assert cari_terbesar([-2, -8, -1]) == -1
    assert cari_terbesar([]) is None


def test_cari_terkecil():
    assert cari_terkecil([5]) == 5
    assert cari_terkecil([-2, -8, -1]) == -8
    assert cari_terkecil([]) is None


def test_hitung_rata_rata():
    assert hitung_rata_rata([2, 4]) == 3.0
    assert hitung_rata_rata([]) is None


def test_hitung_return_harian():
    hasil = hitung_return_harian([100, 102, 99, 105])
    assert round(hasil[0], 2) == 2.0
    assert round(hasil[1], 2) == -2.94
    assert round(hasil[2], 2) == 6.06


def test_hitung_return_harian_lewati_transisi_yang_menyentuh_nol():
    # Harga 0 di IDX tidak pernah sah - tanda data korup/delisting, bukan
    # pergerakan pasar nyata (kebijakan yang sama dengan NaN di api_harga.py
    # dan data.py). Lewati transisi DARI maupun KE harga 0, jangan hitung
    # -100% seolah itu pergerakan pasar sungguhan.
    hasil = hitung_return_harian([100.0, 0.0, 105.0])
    assert hasil == []


def test_hitung_return_harian_nol_di_tengah_lewati_dua_transisi():
    hasil = hitung_return_harian([100.0, 110.0, 0.0, 50.0])
    # (110-100)/100=+10% tetap terhitung; kedua transisi yang menyentuh 0
    # (110->0 dan 0->50) dilewati, bukan cuma satu.
    assert hasil == [10.0]
