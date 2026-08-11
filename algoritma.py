def cari_terbesar(data):
    if not data:
        return None
    terbesar = data[0]
    for nilai in data:
        if nilai > terbesar:
            terbesar = nilai
    return terbesar
def hitung_rata_rata(data):
    if not data:
        return None
    return sum(data) / len(data)
def cari_terkecil(data):
    if not data:
        return None
    terkecil = data[0]
    for nilai in data:
        if nilai < terkecil:
            terkecil = nilai
    return terkecil
def hitung_return_harian(data):
    hasil = []

    for i in range(1, len(data)):
        if data[i - 1] == 0 or data[i] == 0:
            # harga 0 = data korup/delisting, bukan pergerakan pasar sah -
            # lewati transisi yang menyentuhnya sama sekali (bukan cuma yang
            # jadi pembagi), jangan hitung -100% seolah itu pasar sungguhan.
            continue
        r = ((data[i] - data[i - 1]) / data[i - 1]) * 100
        hasil.append(r)

    return hasil