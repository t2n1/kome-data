"""Migration 060 — chỉ số mart của Thị trường & đối thủ (đặc tả §4.4)."""
from datetime import date
import json

import pytest

from tests.test_khach_hang import _mua, HOM_NAY


def _hang(conn, batch, ma="NT01", ten="Ca Ba sa cat khuc (500g x 20 packs)"):
    b = batch(9001)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, food_category_name, batch_id)
                    VALUES (%s, %s, '冷凍食品_VNM', %s) ON CONFLICT DO NOTHING""", (ma, ten, b))
    conn.commit()


def _qs(conn, batch, ben, gia, kg=1, thue="chua", ma="NT01", ngay=date(2026, 7, 20), trang="con",
        hang=None, nhan="thay_the", do_chac="chac"):
    b = batch(abs(hash((ben, gia, hang, ngay))) % 50_000 + 20_000, ngay)
    r = conn.execute(
        """INSERT INTO core.fact_gia_doi_thu (batch_id, ma_dong, ma_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon,
             ten_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, trang_thai, ma_kome_de_xuat, nhan_de_xuat, do_chac)
           VALUES (%s, 'x-1', %s, %s, %s, 'file', 'Basa', %s, 'kg', %s, %s, 'khong_ro', %s, %s, %s, %s) RETURNING id""",
        (b, ben, hang or f"ten:basa|{ben}", ngay, gia, kg, thue, trang, ma, nhan, do_chac)).fetchone()[0]
    conn.commit()
    return r


def test_quy_cach_tach_tu_ten_va_nguoi_sua_thang(conn, batch):
    _hang(conn, batch)
    _hang(conn, batch, "NT04", "Ca ro phi nguyen con (10kg/case)")
    q = dict(((r[0], (r[1], r[2], r[3])) for r in conn.execute(
        "SELECT product_code, kg_moi_goi, goi_moi_thung, kg_moi_thung FROM mart.quy_cach_kome")))
    assert q["NT01"] == (pytest.approx(0.5), 20, None)
    assert q["NT04"][2] == 10
    conn.execute("INSERT INTO app.quy_cach_kome (product_code, kg_moi_goi) VALUES ('NT01', 0.45)")
    conn.commit()
    assert float(conn.execute("SELECT kg_moi_goi FROM mart.quy_cach_kome WHERE product_code='NT01'").fetchone()[0]) == 0.45


def test_quy_cach_ngoac_toan_khoa_dau_sao_va_khong_ngoac(conn, batch):
    for ma, ten in (("Q1", "Vo ram Ha Tinh（200g x 30 packs）"), ("Q2", "Pho duy anh 4mm 400g *30packs"),
                    ("Q3", "Bun gao 1mm 400g 400g *30packs"), ("Q4", "Nuoc mam (500ml x 12 bottles)"),
                    ("Q5", "Gao thom (1.5kg x 8)")):
        _hang(conn, batch, ma, ten)
    q = {r[0]: (None if r[1] is None else float(r[1]), None if r[2] is None else float(r[2]))
         for r in conn.execute("SELECT product_code, kg_moi_goi, goi_moi_thung FROM mart.quy_cach_kome "
                               "WHERE product_code LIKE 'Q%'")}
    assert q["Q1"] == (pytest.approx(0.2), 30)
    assert q["Q2"] == (pytest.approx(0.4), 30)
    assert q["Q3"] == (pytest.approx(0.4), 30)
    assert q["Q4"] == (None, None)                 # ml không phải kg
    assert q["Q5"] == (pytest.approx(1.5), 8)


def test_gia_kome_kg_la_TY_SO_CAC_TONG_doc_ban_den_moc(conn, batch):
    _hang(conn, batch)
    # _mua: pack_code '02', qty 6, amount 110.000, tax 10.000 → 100.000 ÷ (6 thùng × 20 × 0,5 kg) = ¥1.666,7/kg
    _mua(conn, batch, "202601010001", HOM_NAY, hang="NT01")
    _mua(conn, batch, "009000000002", HOM_NAY, tien=550_000, tax=50_000, hang="NT01")     # mã nội bộ (044) — không được lọt
    y = conn.execute("SELECT yen_kg FROM mart.gia_kome_kg WHERE product_code='NT01'").fetchone()[0]
    assert float(y) == pytest.approx(100_000 / 60, rel=1e-6)


def test_quy_doi_chia_thue_dung_mot_lan_va_khong_kg_thi_don_vi(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 540, thue="co")
    _qs(conn, batch, "B", 100, kg=None)
    r = dict(conn.execute("SELECT ma_doi_thu, (yen_chuan, don_vi_so) FROM mart.gia_doi_thu_quan_sat").fetchall())
    assert float(r["A"][0]) == pytest.approx(500)
    assert r["B"][1] == "don_vi:kg"


def test_dinh_chinh_ap_tren_ban_nap_khong_dung_core(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "A", 850)
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'gia_goc', '580')", (fid,))
    conn.commit()
    g, tt = conn.execute("SELECT gia_goc, trang_thai_duyet FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert g == 580 and tt == "da_sua"
    assert conn.execute("SELECT gia_goc FROM core.fact_gia_doi_thu WHERE id=%s", (fid,)).fetchone()[0] == 850


def test_dinh_chinh_mo_coi_sau_hoan_tac_khong_no(conn, batch):
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (999999, 'gia_goc', '1')")
    conn.commit()
    assert conn.execute("SELECT count(*) FROM mart.gia_doi_thu_quan_sat").fetchone()[0] == 0


def test_bat_thuong_hon_2_lan_trung_vi_khi_du_3_ben_va_khong_vao_trung_vi(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580), ("D", 1400)]:
        _qs(conn, batch, ben, g)
    bt = dict(conn.execute("SELECT ma_doi_thu, bat_thuong FROM mart.gia_doi_thu_hien_hanh").fetchall())
    assert bt == {"A": False, "B": False, "C": False, "D": True}
    tv = conn.execute("SELECT trung_vi, cao_nhat, so_ben FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()
    assert float(tv[0]) == 560 and float(tv[1]) == 580 and tv[2] == 3


def test_nhom_duoi_3_ben_khong_xet_bat_thuong(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 100); _qs(conn, batch, "B", 900)
    assert not any(r[0] for r in conn.execute("SELECT bat_thuong FROM mart.gia_doi_thu_hien_hanh"))


def test_xac_nhan_go_co_bat_thuong(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    fid = _qs(conn, batch, "D", 1400)
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong) VALUES (%s, 'xac_nhan')", (fid,))
    conn.commit()
    assert conn.execute("SELECT bat_thuong FROM mart.gia_doi_thu_hien_hanh WHERE id=%s", (fid,)).fetchone()[0] is False


def test_het_hang_khong_vao_trung_vi(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 500); _qs(conn, batch, "B", 600); _qs(conn, batch, "C", 100, trang="het")
    assert float(conn.execute("SELECT thap_nhat FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()[0]) == 500


def test_quan_sat_moi_hon_thang_cu_va_quay_ve_moc(conn, batch):
    _hang(conn, batch)
    _mua(conn, batch, "202601010001", date(2026, 9, 20), hang="NT01")   # mốc dữ liệu = 20/9
    _qs(conn, batch, "A", 500, hang="h1", ngay=date(2026, 8, 5))
    _qs(conn, batch, "A", 520, hang="h1", ngay=date(2026, 9, 5))
    assert conn.execute("SELECT gia_goc FROM mart.gia_doi_thu_hien_hanh").fetchone()[0] == 520
    conn.execute("SELECT set_config('kome.moc', '2026-08-31', true)")
    assert conn.execute("SELECT gia_goc FROM mart.gia_doi_thu_hien_hanh").fetchone()[0] == 500
    conn.rollback()


def test_ghep_cua_nguoi_thang_de_xuat_va_nhom_co_ten_gop_ma(conn, batch):
    _hang(conn, batch); _hang(conn, batch, "NT99", "Ca Ba sa cat khuc (1kg x 10 packs)")
    _qs(conn, batch, "A", 500, hang="h1")
    _qs(conn, batch, "B", 520, hang="h2", ma="NT99")
    conn.execute("INSERT INTO app.ghep_hang (ma_doi_thu, ma_hang_dt, product_code, nhan) VALUES ('A', 'h1', NULL, 'khong')")
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Basa cắt khúc') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma VALUES ('NT01', %s), ('NT99', %s)", (n, n))
    conn.commit()
    r = dict(conn.execute("SELECT ma_doi_thu, (ma_kome, nhom_khoa, ten_nhom) FROM mart.gia_doi_thu_quan_sat").fetchall())
    assert r["A"][0] is None and r["A"][1] is None               # người nói "không ghép" → ra khỏi mọi nhóm
    assert r["B"][1] == f"n:{n}" and r["B"][2] == "Basa cắt khúc"


def test_khong_ghep_go_khoi_ca_nhom_chon_tay(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "A", 500, hang="h1")
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm X') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.ghep_hang (ma_doi_thu, ma_hang_dt, product_code, nhom_id, nhan) "
                 "VALUES ('A', 'h1', NULL, %s, 'khong')", (n,))
    conn.commit()
    assert conn.execute("SELECT nhom_khoa FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()[0] is None


def test_dinh_chinh_khong_phai_so_khong_lam_hong_view(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "A", 850)
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'gia_goc', '580円')", (fid,))
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'kg_moi_don_vi_gia', 'abc')", (fid,))
    conn.commit()
    g, kg = conn.execute("SELECT gia_goc, kg_moi_don_vi_gia FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert g == 850 and kg == 1


def test_gia_kome_kg_chi_nhan_pack_00_va_02(conn, batch):
    _hang(conn, batch)
    _mua(conn, batch, "202601010001", HOM_NAY, hang="NT01")            # '02' → 60 kg
    conn.execute("UPDATE core.fact_sales_line SET pack_code = '01' WHERE product_code = 'NT01'")
    conn.commit()
    assert conn.execute("SELECT count(*) FROM mart.gia_kome_kg WHERE product_code='NT01'").fetchone()[0] == 0


def test_so_sanh_nhom_co_cot_nganh_cua_ma_va_nganh_pho_bien_nhat_cua_nhom_co_ten(conn, batch):
    _hang(conn, batch)                                                   # NT01: 冷凍食品_VNM
    _qs(conn, batch, "A", 500)
    assert conn.execute("SELECT nganh FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()[0] == "冷凍食品_VNM"
    b = batch(9002)
    for ma, nganh in (("NT02", "冷凍食品_VNM"), ("NT03", "乾物_VNM")):
        conn.execute("INSERT INTO core.dim_product (product_code, product_name, food_category_name, batch_id) "
                     "VALUES (%s, 'X (1kg x 10)', %s, %s)", (ma, nganh, b))
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm hai ngành') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma VALUES ('NT01', %s), ('NT02', %s), ('NT03', %s)", (n, n, n))
    conn.commit()
    _qs(conn, batch, "B", 520, hang="h2")
    assert conn.execute("SELECT nganh FROM mart.so_sanh_nhom WHERE nhom_khoa=%s", (f"n:{n}",)).fetchone()[0] == "冷凍食品_VNM"


# ---- 063: giá khách kể (tin hiện trường `@`) ---------------------------------------------------------

def _ke(conn, khach, nhom_khoa, gia, ben="THAK", ten="Basa", don_vi="kg", kg=1, luc=None):
    """Một tin khách kể: giống hệt cách `doi_thu.gia_khach_ke` sẽ ghi (ma_hang_dt = 'ke:<khách>:<nhóm>')."""
    r = conn.execute(
        """INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia,
             thue, gom_ship, loai_nguon, customer_code, nhom_khoa, luc)
           VALUES (%s, %s, %s, %s, %s, %s, 'khong_ro', 'khong_ro', 'khach_ke', %s, %s, coalesce(%s, now())) RETURNING id""",
        (ben, f"ke:{khach}:{nhom_khoa}", ten, gia, don_vi, kg, khach, nhom_khoa, luc)).fetchone()[0]
    conn.commit()
    return r


def test_gia_khach_ke_mang_nhom_khoa_cua_the_hang_khong_qua_ghep(conn, batch):
    _hang(conn, batch, ten="Ca Ba sa cat khuc (500g x 20 packs)")
    fid = _ke(conn, "202601010001", "ma:NT01", 700)
    r = conn.execute("SELECT nhom_khoa, ten_nhom, loai_nguon, ma_kome FROM mart.gia_doi_thu_quan_sat "
                     "WHERE nguon = 'tay' AND id = %s", (fid,)).fetchone()
    assert r[0] == "ma:NT01" and r[1] == "Ca Ba sa cat khuc (500g x 20 packs)" and r[2] == "khach_ke" and r[3] is None
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm cá') RETURNING id").fetchone()[0]
    conn.commit()
    f2 = _ke(conn, "202601010002", f"n:{n}", 710)
    r = conn.execute("SELECT nhom_khoa, ten_nhom FROM mart.gia_doi_thu_quan_sat WHERE nguon='tay' AND id=%s", (f2,)).fetchone()
    assert r == (f"n:{n}", "Nhóm cá")


def test_gia_tay_khong_co_nhom_khoa_van_di_theo_ghep_nhu_cu(conn, batch):
    _hang(conn, batch)
    conn.execute("""INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, gia_goc, don_vi_gia, loai_nguon)
                    VALUES ('THAK', 'tay1', 'Basa', 500, 'kg', 'bang_gia')""")
    conn.commit()
    assert conn.execute("SELECT nhom_khoa FROM mart.gia_doi_thu_quan_sat WHERE nguon='tay'").fetchone()[0] is None


def test_gia_khach_ke_khong_vao_trung_vi_nhung_co_trong_hien_hanh_va_bi_bat_thuong(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    fid = _ke(conn, "202601010001", "ma:NT01", 1400)
    h = conn.execute("SELECT bat_thuong, trung_vi_nhom, so_ben_nhom FROM mart.gia_doi_thu_hien_hanh "
                     "WHERE nguon='tay' AND id=%s", (fid,)).fetchone()
    assert h[0] is True and float(h[1]) == 560 and h[2] == 3
    tv = conn.execute("SELECT trung_vi, cao_nhat, so_ben, so_quan_sat FROM mart.so_sanh_nhom "
                      "WHERE nhom_khoa='ma:NT01'").fetchone()
    assert float(tv[0]) == 560 and float(tv[1]) == 580 and tv[2] == 3 and tv[3] == 3


def test_hai_tin_khach_ke_cung_khach_ben_nhom_chi_tin_moi_nhat_hien_hanh(conn, batch):
    _hang(conn, batch)
    cu = _ke(conn, "202601010001", "ma:NT01", 600, luc="2026-07-01 09:00+09")
    moi = _ke(conn, "202601010001", "ma:NT01", 650, luc="2026-07-10 09:00+09")
    hh = dict(conn.execute("SELECT id, hien_hanh FROM mart.gia_doi_thu_quan_sat WHERE nguon='tay'").fetchall())
    assert hh == {cu: False, moi: True}


def test_tin_cua_hai_khach_khac_nhau_khong_de_nhau(conn, batch):
    _hang(conn, batch)
    a = _ke(conn, "202601010001", "ma:NT01", 600)
    b = _ke(conn, "202601010002", "ma:NT01", 640)
    hh = dict(conn.execute("SELECT id, hien_hanh FROM mart.gia_doi_thu_quan_sat WHERE nguon='tay'").fetchall())
    assert hh == {a: True, b: True}


def test_cot_ra_cua_quan_sat_giu_nguyen_thu_tu_060(conn):
    cols = [r[0] for r in conn.execute(
        """SELECT column_name FROM information_schema.columns
           WHERE table_schema = 'mart' AND table_name = 'gia_doi_thu_quan_sat' ORDER BY ordinal_position""")]
    assert cols[:5] == ["nguon", "id", "batch_id", "ma_doi_thu", "ten_doi_thu"]
    i = cols.index("tuoi_ngay")                        # cột 060 giữ thứ tự; 067 chỉ THÊM ở cuối
    assert cols[i - 2:i + 1] == ["nen_gia", "hien_hanh", "tuoi_ngay"]
    assert cols[i + 1:] == ["so_goi_thung", "kl_goi_g", "bac", "kg_thung_dt", "gia_goi", "gia_thung",
                            "gia_1", "gia_5", "gia_10", "gia_pallet"]


def test_nguon_quan_sat_thang_lo_theo_DATA_DATE_cua_lo_khong_theo_ngay_nguon(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 540, ngay=date(2026, 7, 20))          # lô data_date 2026-07-20
    conn.execute("UPDATE core.fact_gia_doi_thu SET ngay_nguon = '2026-06-30' WHERE id = %s", (fid,))
    conn.execute("INSERT INTO app.thu_muc_nguon (thang, lien_ket) VALUES ('2026-07-01', 'https://drive.google.com/t7')")
    conn.commit()
    r = conn.execute("""SELECT thang_lo, lien_ket_thu_muc, web_ben FROM mart.nguon_quan_sat
                        WHERE nguon = 'nap' AND id = %s""", (fid,)).fetchone()
    assert r == (date(2026, 7, 1), "https://drive.google.com/t7", "https://thak.jp/")


def test_nguon_quan_sat_gia_tay_mang_link_bang_chung(conn, batch):
    tid = conn.execute("""INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, gia_goc, don_vi_gia,
                            trang_thai, loai_nguon, lien_ket_bang_chung)
                          VALUES ('THAK', 'ten:x|', 'x', 500, 'kg', 'con', 'to_roi', 'https://drive.google.com/anh')
                          RETURNING id""").fetchone()[0]
    conn.commit()
    r = conn.execute("""SELECT thang_lo, lien_ket_thu_muc, lien_ket_bang_chung FROM mart.nguon_quan_sat
                        WHERE nguon = 'tay' AND id = %s""", (tid,)).fetchone()
    assert r == (None, None, "https://drive.google.com/anh")


def test_nguon_quan_sat_moi_quan_sat_dung_MOT_dong(conn, batch):
    _hang(conn, batch)
    for b, g in [("THAK", 540), ("HSC", 560)]:
        _qs(conn, batch, b, g)
    n_qs, n_ng = conn.execute("""SELECT (SELECT count(*) FROM mart.gia_doi_thu_quan_sat),
                                        (SELECT count(*) FROM mart.gia_doi_thu_quan_sat q
                                         JOIN mart.nguon_quan_sat n USING (nguon, id))""").fetchone()
    assert n_qs == n_ng == 2


# ---------------------------------------------------------------- 066 — kg theo 荷姿 OBC + bảng giá KOME

def _hang_pack(conn, batch, ma, ten, pack1_code, pack1_base_qty=None):
    b = batch(9002)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, food_category_name, pack1_code, pack1_base_qty, batch_id)
                    VALUES (%s, %s, '調味料_VNM', %s, %s, %s)""", (ma, ten, pack1_code, pack1_base_qty, b))
    conn.commit()


def _kg(conn, ma):
    r = conn.execute("SELECT kg_00, kg_02 FROM mart.quy_cach_kome WHERE product_code=%s", (ma,)).fetchone()
    return tuple(None if x is None else float(x) for x in r)


def test_066_kg_theo_hanh_dong_goi_OBC(conn, batch):
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")      # không 荷姿: 00 = cả sản phẩm
    _hang_pack(conn, batch, "DK20", "Ngu Vi Huong 3g (3g x 100 pack x 4 boxes)", "02", 400)   # 02 = 400 × 00
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _hang(conn, batch, "NT09", "Ca X (500g x 20 packs)")                                      # chưa nạp 荷姿 → luật cũ
    assert _kg(conn, "BA02") == (pytest.approx(6.4), pytest.approx(6.4))
    assert _kg(conn, "DK20") == (pytest.approx(0.003), pytest.approx(1.2))
    assert _kg(conn, "NT01") == (pytest.approx(0.5), pytest.approx(10))
    assert _kg(conn, "NT09") == (pytest.approx(0.5), pytest.approx(10))


def test_066_gia_kome_kg_ma_ban_bang_00_la_ca_thung(conn, batch):
    """15 nhóm lệch (đo 2026-09-29): xốt Barona bán bằng '00' mà một '00' là cả thùng 6,4 kg."""
    import pandas as pd
    from kome.loaders import sales
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    b = batch(9003, HOM_NAY)
    # Cùng hình dạng dòng như tests/test_khach_hang.py::_mua, nhưng pack '00', qty 1, doanh thu thuần ¥6.266.
    sales.load(conn, pd.DataFrame([{
        "slip_no": "SBA02", "line_seq": 1, "sales_date": HOM_NAY, "customer_code": "202601010001",
        "product_code": "BA02", "pack_code": "00", "case_qty": 0, "qty": 1, "unit_price": 6266, "unit_cost": 5000,
        "amount": 6266, "tax_amount": 0, "cost": 5000, "gross_profit": 1266, "paid_amount": 0, "batch_id": b,
    }]), HOM_NAY, b)
    conn.commit()
    y = conn.execute("SELECT yen_kg FROM mart.gia_kome_kg WHERE product_code='BA02'").fetchone()[0]
    assert float(y) == pytest.approx(6266 / 6.4, rel=1e-6)      # ¥979/kg — KHÔNG phải ¥78.325/kg (coi '00' = 80g)


def _lo_gia(conn, batch, ma, ngay, n):
    """MỘT lần nạp giá = MỘT lô cho mọi bậc của mã trong ngày đó (như price.py) — 066 lấy batch_id lớn nhất trong
    valid_from mới nhất, nên gieo mỗi bậc một lô là tự bỏ bậc của chính mình."""
    r = conn.execute("SELECT max(batch_id) FROM core.fact_price_list WHERE product_code = %s AND valid_from = %s",
                     (ma, ngay)).fetchone()[0]
    return r if r is not None else batch(n, ngay)


def _bang_gia(conn, batch, ma, lv, ex, inc, pack="02"):
    b = _lo_gia(conn, batch, ma, date(2026, 9, 8), 9100 + len(lv) + ex % 97)
    conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                      price_in_tax, unit_cost, batch_id) VALUES (%s, %s, %s, '2026-09-08', %s, %s, 0, %s)""",
                 (ma, pack, lv, ex, inc, b))
    conn.commit()


def test_066_gia_kome_chuan_va_luat_hai_cot(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _bang_gia(conn, batch, "NT01", "std", 0, 4900)          # chỉ có gồm thuế → ÷ 1,08
    _bang_gia(conn, batch, "NT01", "01", 5130, 5540)        # hai cột khớp → chưa thuế
    _bang_gia(conn, batch, "NT01", "10", 5900, 4900)        # gồm thuế < chưa thuế → mâu thuẫn → gồm thuế ÷ 1,08
    assert float(conn.execute("SELECT mart.gia_kome_chuan('NT01')").fetchone()[0]) == pytest.approx(4900 / 1.08 / 10)
    r = {x[0]: (float(x[1]), x[2]) for x in conn.execute(
        "SELECT price_level, yen_kg, hai_cot_lech FROM mart.gia_kome_bang WHERE product_code='NT01'")}
    assert r["01"] == (pytest.approx(513), False)
    assert r["10"] == (pytest.approx(4900 / 1.08 / 10), True)
    assert conn.execute("SELECT mart.la_gia_km_kome('10'), mart.la_gia_km_kome('01'), mart.la_gia_km_kome('std')").fetchone() \
        == (True, False, False)
    assert conn.execute("SELECT mart.gia_kome_chuan('KHONG_CO')").fetchone()[0] is None


def test_066_bang_gia_ma_chi_co_00_dung_kg_00(conn, batch):
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    _bang_gia(conn, batch, "BA02", "std", 0, 6804, pack="00")
    assert float(conn.execute("SELECT mart.gia_kome_chuan('BA02')").fetchone()[0]) == pytest.approx(6804 / 1.08 / 6.4)


def _gia_ngay(conn, batch, ma, lv, ex, inc, ngay, pack="02"):
    b = _lo_gia(conn, batch, ma, ngay, 9200 + len(lv) + ex % 89 + inc % 83)
    conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                      price_in_tax, unit_cost, batch_id) VALUES (%s, %s, %s, %s, %s, %s, 0, %s)""",
                 (ma, pack, lv, ngay, ex, inc, b))
    conn.commit()


def test_066_bac_khong_co_o_lan_nap_moi_nhat_thi_bien_mat_va_lui_moc_thi_hien_lai(conn, batch):
    """price.py bỏ bậc 0/0: khi 売価No.10 hết hạn không có dòng mới nào — view/`_bac_gia` không được giữ dòng cũ."""
    from kome import san_pham_360 as SP360
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _gia_ngay(conn, batch, "NT01", "std", 0, 4900, date(2026, 7, 1))
    _gia_ngay(conn, batch, "NT01", "10", 4000, 4320, date(2026, 7, 1))       # khuyến mãi của lần nạp cũ
    _gia_ngay(conn, batch, "NT01", "std", 0, 5400, date(2026, 7, 25))        # lần nạp mới: chỉ còn tiêu chuẩn
    _mua(conn, batch, "202601010001", HOM_NAY, hang="NT01")                  # để mốc lùi có nghĩa

    def bac():
        return ({r[0] for r in conn.execute("SELECT price_level FROM mart.gia_kome_bang WHERE product_code='NT01'")},
                {g["bac"] for g in SP360._bac_gia(conn, "NT01")})

    assert bac() == ({"std"}, {"標準価格"})
    assert float(conn.execute("SELECT mart.gia_kome_chuan('NT01')").fetchone()[0]) == pytest.approx(5400 / 1.08 / 10)
    conn.execute("SELECT set_config('kome.moc', '2026-07-20', true)")         # lùi về trước lần nạp mới
    assert bac() == ({"std", "10"}, {"標準価格", "10 · khuyến mãi"})
    assert float(conn.execute("SELECT mart.gia_kome_chuan('NT01')").fetchone()[0]) == pytest.approx(4900 / 1.08 / 10)
    conn.rollback()


def test_066_nguoi_sua_kg_moi_goi_thi_kg_02_chay_theo_荷姿(conn, batch):
    _hang_pack(conn, batch, "DK20", "Ngu Vi Huong 3g (3g x 100 pack x 4 boxes)", "02", 400)
    # Form quy cách gửi cả ba trường: kg_moi_thung suy từ tên (1,2) bị lưu như số "người sửa" — không được khoá kg_02.
    conn.execute("INSERT INTO app.quy_cach_kome (product_code, kg_moi_goi, goi_moi_thung, kg_moi_thung) "
                 "VALUES ('DK20', 0.0035, 100, 1.2)")
    conn.commit()
    assert _kg(conn, "DK20")[1] == pytest.approx(0.0035 * 400)


def test_066_khong_荷姿_nguoi_sua_kg_moi_goi_thang_ten_ba_thua_so(conn, batch):
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    conn.execute("INSERT INTO app.quy_cach_kome (product_code, kg_moi_goi) VALUES ('BA02', 0.082)")
    conn.commit()
    assert _kg(conn, "BA02") == (pytest.approx(0.082 * 20 * 4), pytest.approx(0.082 * 20 * 4))


def test_066_pack1_NULL_ten_ba_thua_so_cho_kg_02(conn, batch):
    _hang(conn, batch, "DK21", "Ngu Vi Huong 3g (3g x 100 pack x 4 boxes)")
    assert _kg(conn, "DK21") == (pytest.approx(0.003), pytest.approx(3 / 1000 * 100 * 4))


def test_066_quy_cach_02_thang_00_khi_co_ca_hai_bac_gia(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _gia_ngay(conn, batch, "NT01", "std", 0, 5400, date(2026, 7, 1), pack="00")
    _gia_ngay(conn, batch, "NT01", "std", 0, 5400, date(2026, 7, 1), pack="02")
    r = conn.execute("SELECT pack_code, yen_kg FROM mart.gia_kome_bang WHERE product_code='NT01' AND price_level='std'").fetchall()
    assert len(r) == 1 and r[0][0] == "02" and float(r[0][1]) == pytest.approx(5400 / 1.08 / 10)


# ---------------------------------------------------------------- 067 — quy cách gói + giá bậc + KOME chuẩn ở So sánh

def _qs_bac(conn, batch, ben, gia_goc, don_vi, kg, bac, thue="chua", so_goi=None, kl_goi=None, muc=None):
    b = batch(abs(hash((ben, gia_goc, str(bac)))) % 50_000 + 60_000)
    r = conn.execute(
        """INSERT INTO core.fact_gia_doi_thu (batch_id, ma_dong, ma_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon,
             ten_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, trang_thai, ma_kome_de_xuat, nhan_de_xuat,
             do_chac, bac, so_goi_thung, kl_goi_g, muc_gia)
           VALUES (%s, 'x-1', %s, %s, '2026-08-20', 'file', 'Basa', %s, %s, %s, %s, 'khong_ro', 'con', 'NT01', 'cung_hang',
                   'chac', %s, %s, %s, %s) RETURNING id""",
        (b, ben, f"ten:basa|{ben}", gia_goc, don_vi, kg, thue, json.dumps(bac) if bac is not None else None,
         so_goi, kl_goi, muc)).fetchone()[0]
    conn.commit()
    return r


def _gia(conn, fid):
    r = conn.execute("""SELECT gia_1, gia_5, gia_10, gia_pallet, kg_thung_dt, gia_goi, gia_thung
                        FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s""", (fid,)).fetchone()
    return tuple(None if x is None else float(x) for x in r)


def test_067_gia_tai_so_luong_theo_bac_thung(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "NEXT", 5500, "thung", 10,
                  [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}], so_goi=20, kl_goi=500)
    g1, g5, g10, gp, kgt, ggoi, gth = _gia(conn, fid)
    assert (g1, g5, g10) == (pytest.approx(550), pytest.approx(530), pytest.approx(530))
    assert gp is None                                  # không ghi pallet → KHÔNG đoán
    assert kgt == pytest.approx(10) and ggoi == pytest.approx(275) and gth == pytest.approx(5500)


def test_067_bac_theo_kg_quy_ra_thung_bang_quy_cach(conn, batch):
    _hang(conn, batch)
    # Vietnam House: 25kg → 600/kg · 50kg → 580/kg; thùng 20 × 500g = 10 kg ⇒ 25 kg = 2,5 thùng, 50 kg = 5 thùng
    fid = _qs_bac(conn, batch, "VH", 610, "kg", 1,
                  [{"tu": 25, "don_vi_sl": "kg", "gia": 600, "don_vi_gia": "kg"},
                   {"tu": 50, "don_vi_sl": "kg", "gia": 580, "don_vi_gia": "kg"}], so_goi=20, kl_goi=500)
    g1, g5, g10, *_ = _gia(conn, fid)
    assert (g1, g5, g10) == (pytest.approx(610), pytest.approx(580), pytest.approx(580))


def test_067_bac_kg_khong_biet_quy_cach_thi_khong_ap_khong_doan(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "OBA", 530, "kg", 1, [{"tu": 48, "don_vi_sl": "kg", "gia": 510, "don_vi_gia": "kg"}])
    assert _gia(conn, fid)[:3] == (pytest.approx(530), pytest.approx(530), pytest.approx(530))


def test_067_bac_pallet_chi_ap_cho_pallet_va_thue_chia_mot_lan(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "A", 5400, "thung", 10,
                  [{"tu": 1, "don_vi_sl": "pallet", "gia": 4860, "don_vi_gia": "thung"}], thue="co")
    g1, g5, g10, gp, *_ = _gia(conn, fid)
    assert g1 == pytest.approx(500) and g10 == pytest.approx(500) and gp == pytest.approx(450)


def test_067_dinh_chinh_bac_va_quy_cach_thang_ban_nap(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "NEXT", 5500, "thung", 10, None)
    for t, v in (("bac", '[{"tu": 10, "don_vi_sl": "thung", "gia": 5000, "don_vi_gia": "thung"}]'),
                 ("so_goi_thung", "20"), ("kl_goi_g", "500"), ("khuyen_mai", "mua 10 tặng 1")):
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, %s, %s)", (fid, t, v))
    conn.commit()
    g1, g5, g10, *_ = _gia(conn, fid)
    assert (g1, g5, g10) == (pytest.approx(550), pytest.approx(550), pytest.approx(500))
    km, sg = conn.execute("SELECT khuyen_mai, so_goi_thung FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert km == "mua 10 tặng 1" and sg == 20
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'khuyen_mai', '')", (fid,))
    conn.commit()
    assert conn.execute("SELECT khuyen_mai FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()[0] is None


def test_067_thong_ke_nhom_van_tren_gia_le(conn, batch):
    _hang(conn, batch)
    for ben, g in (("A", 5400), ("B", 5600), ("C", 5800)):
        _qs_bac(conn, batch, ben, g, "thung", 10, [{"tu": 5, "don_vi_sl": "thung", "gia": 3000, "don_vi_gia": "thung"}])
    tv = conn.execute("SELECT trung_vi FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()[0]
    assert float(tv) == pytest.approx(560)             # bậc 5 thùng (300/kg) KHÔNG kéo trung vị


def test_067_so_sanh_nhom_mang_gia_kome_chuan_va_bang_va_km(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _qs(conn, batch, "A", 540)
    _bang_gia(conn, batch, "NT01", "std", 0, 4900)
    _bang_gia(conn, batch, "NT01", "01", 5130, 5540)
    _bang_gia(conn, batch, "NT01", "10", 4500, 4860)
    r = conn.execute("""SELECT gia_kome_chuan, gia_kome_bang, gia_kome_km, ty_le_re_hon_kome
                        FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'""").fetchone()
    assert float(r[0]) == pytest.approx(4900 / 1.08 / 10)
    assert set(r[1]) == {"01"}                          # std và 10 (khuyến mãi) KHÔNG vào dải giá thường
    assert float(r[2]) == pytest.approx(450)
    assert float(r[3]) == 0                             # A ¥540 không rẻ hơn chuẩn ¥453,7


def test_067_pallet_chi_ap_bac_pallet_khong_ap_bac_thung_lon(conn, batch):
    _hang(conn, batch)
    # Bậc "từ 100 thùng" rẻ hơn cả bậc pallet — pallet KHÔNG được giả định ≥ 100 thùng.
    fid = _qs_bac(conn, batch, "P1", 5400, "thung", 10,
                  [{"tu": 100, "don_vi_sl": "thung", "gia": 4000, "don_vi_gia": "thung"},
                   {"tu": 1, "don_vi_sl": "pallet", "gia": 4900, "don_vi_gia": "thung"}])
    assert _gia(conn, fid)[3] == pytest.approx(490)
    # Không có bậc pallet ghi rõ → gia_pallet NULL, dù có bậc thùng rất lớn.
    fid2 = _qs_bac(conn, batch, "P2", 5400, "thung", 10,
                   [{"tu": 100, "don_vi_sl": "thung", "gia": 4000, "don_vi_gia": "thung"}])
    assert _gia(conn, fid2)[3] is None


def test_067_dinh_chinh_bac_hong_khong_lam_sap_view_dung_bac_nap(conn, batch):
    _hang(conn, batch)
    fid = _qs_bac(conn, batch, "NEXT", 5500, "thung", 10,
                  [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}])
    for v in ("khong phai json", '{"tu": 1}', '[{"tu": "x", "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "thung"}]'):
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'bac', %s)", (fid, v))
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (%s, 'so_goi_thung', '99999999999')",
                     (fid,))
        conn.commit()
        g = _gia(conn, fid)
        if v.startswith("["):       # mảng hợp lệ mà phần tử hỏng → phần tử đó bị bỏ, không nổ; không bậc nào áp
            assert g[:3] == (pytest.approx(550), pytest.approx(550), pytest.approx(550))
        else:                       # không phải mảng JSON → dùng bậc đã nạp
            assert g[:3] == (pytest.approx(550), pytest.approx(530), pytest.approx(530))
        assert conn.execute("SELECT count(*) FROM mart.so_sanh_nhom").fetchone()[0] >= 0


def test_so_sanh_nhom_tv_gia_la_CTE_MATERIALIZED_tuong_minh(conn):
    """tv_gia được đọc hai lần (chinh, kome) → bất biến CTE-trùng: ghi `AS MATERIALIZED` tường minh."""
    d = conn.execute("SELECT pg_get_viewdef('mart.so_sanh_nhom'::regclass)").fetchone()[0]
    for cte in ("h", "kb", "tv_gia"):
        assert f"{cte} AS MATERIALIZED" in d, cte


def test_066_nap_lai_CUNG_ngay_bac_bi_bo_thi_bien_mat(conn, batch):
    """File đính chính cùng valid_from: price.py upsert (khoá có valid_from) đổi batch_id của bậc còn lại, bậc bị bỏ giữ
    batch_id cũ — "lần nạp mới nhất" phải là batch_id lớn nhất TRONG valid_from mới nhất, không chỉ valid_from."""
    from kome import san_pham_360 as SP360
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    ngay = date(2026, 7, 25)
    b1, b2 = batch(9301, ngay), batch(9302, ngay)
    assert b2 > b1
    for lv, inc in (("std", 4900), ("10", 4320)):                        # file đầu: tiêu chuẩn + khuyến mãi
        conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                          price_in_tax, unit_cost, batch_id) VALUES ('NT01', '02', %s, %s, 0, %s, 0, %s)""", (lv, ngay, inc, b1))
    conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                      price_in_tax, unit_cost, batch_id) VALUES ('NT01', '02', 'std', %s, 0, 5400, 0, %s)
                    ON CONFLICT (product_code, pack_code, price_level, valid_from) DO UPDATE SET
                      price_in_tax = EXCLUDED.price_in_tax, batch_id = EXCLUDED.batch_id""", (ngay, b2))   # file sửa: bỏ bậc 10
    conn.commit()
    assert {r[0] for r in conn.execute("SELECT price_level FROM mart.gia_kome_bang WHERE product_code='NT01'")} == {"std"}
    assert [(g["bac"], g["gia"]) for g in SP360._bac_gia(conn, "NT01")] == [("標準価格", 5000)]


# ---------------------------------------------------------------- đợt 4b — so_sanh_nhom: giá KOME để so + quy cách mã chính

_COT_4B = "gia_kome_so, lech_trung_vi, gia_kome_lech, kome_kg_goi, kome_goi_thung, kome_kg_thung"


def test_4b_so_sanh_nhom_gia_kome_so_la_chuan_va_lech_khi_qua_3_lan_trung_vi(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    for ben, g in (("A", 100), ("B", 120), ("C", 140)):
        _qs(conn, batch, ben, g)
    _bang_gia(conn, batch, "NT01", "std", 0, 4900)                         # chuẩn ¥453,7/kg > 3 × trung vị ¥120
    so, lech, bat, kg_goi, goi_thung, kg_thung = conn.execute(
        f"SELECT {_COT_4B} FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone()
    chuan = 4900 / 1.08 / 10
    assert float(so) == pytest.approx(chuan)
    assert isinstance(lech, float) and lech == pytest.approx(chuan / 120 - 1)
    assert bat is True
    assert (float(kg_goi), float(goi_thung), float(kg_thung)) == (pytest.approx(0.5), 20, pytest.approx(10))


def test_4b_gia_kome_lech_false_khi_gan_trung_vi_va_khong_co_gia_kome(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _qs(conn, batch, "A", 540)
    assert conn.execute(f"SELECT gia_kome_so, gia_kome_lech FROM mart.so_sanh_nhom WHERE nhom_khoa='ma:NT01'").fetchone() \
        == (None, False)                                                   # chưa có giá KOME → không "lệch"
    _bang_gia(conn, batch, "NT01", "std", 0, 4900)
    so, lech, bat = conn.execute("SELECT gia_kome_so, lech_trung_vi, gia_kome_lech FROM mart.so_sanh_nhom "
                                 "WHERE nhom_khoa='ma:NT01'").fetchone()
    assert bat is False and lech == pytest.approx(4900 / 1.08 / 10 / 540 - 1)


def test_4b_quy_cach_la_cua_ma_CHINH_ban_nhieu_kg_nhat(conn, batch):
    _hang_pack(conn, batch, "NT01", "Ca Ba sa cat khuc (500g x 20 packs)", "02", 20)
    _hang_pack(conn, batch, "NT02", "Ca Ba sa phi le (1kg x 10 packs)", "02", 10)
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Basa') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma (product_code, nhom_id) VALUES ('NT01', %s), ('NT02', %s)", (n, n))
    conn.commit()
    _qs(conn, batch, "A", 540)
    _mua(conn, batch, "202601010001", HOM_NAY, hang="NT02")               # NT02 bán nhiều kg nhất → mã chính
    kg_goi, goi_thung, kg_thung = conn.execute(
        "SELECT kome_kg_goi, kome_goi_thung, kome_kg_thung FROM mart.so_sanh_nhom WHERE nhom_khoa=%s", (f"n:{n}",)).fetchone()
    assert (float(kg_goi), float(goi_thung), float(kg_thung)) == (pytest.approx(1), 10, pytest.approx(10))


def test_4b_chinh_la_CTE_MATERIALIZED_tuong_minh(conn):
    """chinh nay được đọc hai lần (bang, quy cách mã chính) → bất biến CTE-trùng."""
    d = conn.execute("SELECT pg_get_viewdef('mart.so_sanh_nhom'::regclass)").fetchone()[0]
    assert "chinh AS MATERIALIZED" in d
