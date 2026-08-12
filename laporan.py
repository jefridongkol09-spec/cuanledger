def susun_laporan(baris_mentah):
    # Fungsi murni: input list dict hasil JOIN (db.ambil_laporan_mentah),
    # tidak menyentuh database sendiri - bisa diuji langsung dengan data
    # tangan, padanan filosofi algoritma.py di prosperidr.
    per_ticker = {}
    for b in baris_mentah:
        entri = per_ticker.setdefault(
            b["ticker"],
            {"lot": b["lot"], "harga_beli": b["harga_beli"], "harga": []},
        )
        if b["tanggal"] is not None:
            entri["harga"].append((b["tanggal"], b["close"]))

    posisi_hasil = []
    posisi_tanpa_harga = []
    tanggal_semua = set()
    total_nilai = 0
    total_modal = 0

    for ticker, info in per_ticker.items():
        lot = info["lot"]
        harga_beli = info["harga_beli"]
        modal = harga_beli * lot * 100
        harga_list = info["harga"]  # terurut rn=1,2 dari query -> [terbaru, sebelumnya]

        if not harga_list:
            posisi_hasil.append(
                {
                    "ticker": ticker,
                    "tanggal": None,
                    "harga": None,
                    "return_harian": None,
                    "nilai_pasar": None,
                    "modal": modal,
                    "pl": None,
                    "pl_persen": None,
                }
            )
            posisi_tanpa_harga.append(ticker)
            continue

        tanggal_terakhir, harga_terakhir = harga_list[0]

        if len(harga_list) >= 2:
            _, harga_sebelumnya = harga_list[1]
            return_harian = round(
                ((harga_terakhir - harga_sebelumnya) / harga_sebelumnya) * 100, 2
            )
        else:
            # Satu titik data = tidak ada "kemarin" untuk dibandingkan -
            # None ("tidak diketahui"), bukan 0.0 yang memfabrikasi
            # kepastian yang tidak ada. Prinsip yang sama seperti
            # return_harian di prosperidr.
            return_harian = None

        nilai_pasar = harga_terakhir * lot * 100
        pl = nilai_pasar - modal
        pl_persen = round((pl / modal) * 100, 2)

        posisi_hasil.append(
            {
                "ticker": ticker,
                "tanggal": tanggal_terakhir,
                "harga": harga_terakhir,
                "return_harian": return_harian,
                "nilai_pasar": nilai_pasar,
                "modal": modal,
                "pl": pl,
                "pl_persen": pl_persen,
            }
        )

        total_nilai += nilai_pasar
        total_modal += modal
        tanggal_semua.add(tanggal_terakhir)

    # total dihitung hanya dari posisi yang punya harga - CHECK(lot > 0) dan
    # CHECK(harga_beli > 0) di skema posisi menjamin setiap posisi berharga
    # menyumbang modal > 0, jadi total_modal > 0 setiap kali ada minimal
    # satu posisi berharga. ZeroDivisionError ditutup lewat invarian ini,
    # bukan try/except di sekitar pembagian.
    #
    # PENTING untuk klien: karena posisi_tanpa_harga dikeluarkan dari total,
    # total["modal"] TIDAK SAMA DENGAN jumlah field "modal" di semua baris
    # posisi (yang tanpa harga tetap menampilkan modal-nya sendiri, hanya
    # tidak disertakan ke agregat). total merepresentasikan "ringkasan
    # posisi berharga", bukan "seluruh modal yang tertanam". Ini keputusan
    # sadar, bukan bug - lihat posisi_tanpa_harga untuk daftar yang
    # dikecualikan.
    if total_modal > 0:
        total_pl = total_nilai - total_modal
        total = {
            "nilai_pasar": total_nilai,
            "modal": total_modal,
            "pl": total_pl,
            "pl_persen": round((total_pl / total_modal) * 100, 2),
        }
    else:
        total = None

    return {
        "posisi": posisi_hasil,
        "total": total,
        "vintage_campuran": len(tanggal_semua) > 1,
        "tanggal_berbeda": sorted(tanggal_semua) if len(tanggal_semua) > 1 else [],
        "posisi_tanpa_harga": posisi_tanpa_harga,
    }
