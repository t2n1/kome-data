"""Migration 060 — chỉ số mart của Thị trường & đối thủ (đặc tả §4.4)."""
from datetime import date
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
    assert cols[-3:] == ["nen_gia", "hien_hanh", "tuoi_ngay"]
