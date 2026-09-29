"""kome/doi_thu.py — đọc/ghi của màn /doi-thu (đặc tả §4, §5)."""
from datetime import date
from decimal import Decimal
import pytest

from kome import doi_thu as DT
from tests.test_mart_doi_thu import _hang, _qs


def _dem(conn, monkeypatch):
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    return dem


def test_sua_KHONG_dung_core_va_ghi_nhat_ky(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850)
    DT.sua(conn, fid, {"gia_goc": "580", "thue": "co"}, None)
    conn.commit()
    assert conn.execute("SELECT gia_goc FROM core.fact_gia_doi_thu WHERE id=%s", (fid,)).fetchone()[0] == 850
    assert conn.execute("SELECT count(*) FROM app.dinh_chinh_gia WHERE fact_id=%s", (fid,)).fetchone()[0] == 2
    assert conn.execute("SELECT loai FROM app.doi_thu_nhat_ky").fetchone()[0] == "sua"


def test_sua_tu_choi_truong_la_va_gia_tri_sai(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"batch_id": "1"}, None)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"thue": "co_le"}, None)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"gia_goc": "-5"}, None)


def test_gia_moi_bat_buoc_loai_nguon(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850, hang="h1")
    with pytest.raises(DT.LoiNhap):
        DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "550"}, None)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "550", "loai_nguon": "to_roi",
                            "ghi_chu_nguon": "Zalo 29/9"}, None)
    conn.commit()
    r = conn.execute("SELECT ma_doi_thu, ma_hang_dt, ten_goc, gia_goc FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()
    assert r == ("THAK", "h1", "Basa", 550)          # chép khoá hàng từ dòng gốc


def test_dat_ghep_ghi_de_va_nhat_ky(conn, batch):
    _hang(conn, batch)
    DT.dat_ghep(conn, "THAK", "h1", "NT01", None, "cung_hang", None)
    DT.dat_ghep(conn, "THAK", "h1", None, None, "khong", None)
    conn.commit()
    assert conn.execute("SELECT nhan FROM app.ghep_hang").fetchone()[0] == "khong"
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='ghep'").fetchone()[0] == 2


def test_tong_quan_so_sanh_duyet_moi_cai_MOT_luot(conn, batch, monkeypatch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    for ham in (DT.tong_quan, DT.so_sanh, lambda c: DT.duyet(c), lambda c: DT.khoi_san_pham(c, "NT01")):
        dem = _dem(conn, monkeypatch)
        ham(conn)
        assert dem["n"] == 1, ham
        monkeypatch.undo()


def test_so_sanh_tra_quan_sat_cua_tung_nhom(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    n = DT.so_sanh(conn)["nhom"][0]
    assert n["nhom_khoa"] == "ma:NT01" and n["so_ben"] == 3 and len(n["quan_sat"]) == 3


def test_duyet_loc_bat_thuong(conn, batch):
    _hang(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580), ("D", 1400)]:
        _qs(conn, batch, ben, g)
    assert [d["ma_doi_thu"] for d in DT.duyet(conn, loc="bat_thuong")["dong"]] == ["D"]


# ---------------------------------------------------------------- vòng sửa 1

def test_duyet_chua_ghep_khong_giu_lai_dong_da_chon_khong_ghep(conn, batch):
    _hang(conn, batch)
    _qs(conn, batch, "A", 540, hang="hA")
    _qs(conn, batch, "B", 560, hang="hB")
    ma = lambda: {d["ma_hang_dt"] for d in DT.duyet(conn, loc="chua_ghep")["dong"]}
    assert ma() == set() or ma() <= {"hA", "hB"}
    DT.dat_ghep(conn, "A", "hA", None, None, "khong", None)
    conn.commit()
    assert "hA" not in ma()


def test_duyet_chua_ghep_van_hien_dong_chua_ai_dung_toi(conn, batch):
    _hang(conn, batch)
    conn.execute("INSERT INTO core.fact_gia_doi_thu (batch_id, ma_dong, ma_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon,"
                 " ten_goc, gia_goc, trang_thai, do_chac) VALUES (%s,'x-9','A','hZ',%s,'file','La',100,'con','chac')",
                 (batch(9100), date(2026, 7, 20)))
    conn.commit()
    assert [d["ma_hang_dt"] for d in DT.duyet(conn, loc="chua_ghep")["dong"]] == ["hZ"]


def _dk(conn, batch, bid, ngay, ben, loai, nd, ma_dong):
    conn.execute("INSERT INTO core.fact_dieu_kien_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon, loai, noi_dung)"
                 " VALUES (%s,%s,%s,%s,%s,%s)", (batch(bid, ngay), ma_dong, ben, ngay, loai, nd))
    conn.commit()


def test_tong_quan_dieu_kien_chi_lay_goi_moi_nhat_cua_tung_ben(conn, batch):
    _dk(conn, batch, 9201, date(2026, 8, 5), "THAK", "ship", "freeship >= 20,000", "d-1")
    _dk(conn, batch, 9202, date(2026, 9, 5), "THAK", "ship", "freeship >= 30,000", "d-1")
    _dk(conn, batch, 9202, date(2026, 9, 5), "THAK", "thanh_toan", "chuyen khoan", "d-2")
    _dk(conn, batch, 9203, date(2026, 8, 9), "JVB", "ship", "mien phi tu 10,000", "d-1")
    dk = {(d["ben"], d["loai"], d["noi_dung"]) for d in DT.tong_quan(conn)["dieu_kien"]}
    assert dk == {("THAK", "ship", "freeship >= 30,000"), ("THAK", "thanh_toan", "chuyen khoan"),
                  ("JVB", "ship", "mien phi tu 10,000")}


def test_so_doc_phay_nghin_va_phay_thap_phan(conn, batch):
    assert DT._so("0,5", "g") == Decimal("0.5")
    assert DT._so("1,200", "g") == 1200
    assert DT._so("12,345.6", "g") == Decimal("12345.6")
    assert DT._so("12,75", "g") == Decimal("12.75")
    for xau in ("nan", "inf", "1e3", "1,2,3", "abc"):
        with pytest.raises(DT.LoiNhap):
            DT._so(xau, "g")
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850)
    DT.sua(conn, fid, {"gia_goc": "1,200", "kg_moi_don_vi_gia": "0,5"}, None)
    conn.commit()
    r = conn.execute("SELECT gia_goc, kg_moi_don_vi_gia FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s",
                     (fid,)).fetchone()
    assert (float(r[0]), float(r[1])) == (1200.0, 0.5)


def test_gia_moi_bat_buoc_gia_tru_khi_het(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850, hang="h1")
    with pytest.raises(DT.LoiNhap):
        DT.gia_moi(conn, {"fact_goc_id": fid, "loai_nguon": "to_roi"}, None)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "loai_nguon": "to_roi", "trang_thai": "het"}, None)
    assert tid


def test_gia_moi_fact_goc_id_khong_phai_so_la_LoiNhap(conn, batch):
    with pytest.raises(DT.LoiNhap):
        DT.gia_moi(conn, {"fact_goc_id": "abc", "loai_nguon": "to_roi", "gia_goc": "5"}, None)


def test_xac_nhan_kiem_id_la_dong_DA_NAP(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850, hang="h1")
    DT.xac_nhan(conn, fid, None)
    assert conn.execute("SELECT count(*) FROM app.dinh_chinh_gia WHERE fact_id=%s AND truong='xac_nhan'",
                        (fid,)).fetchone()[0] == 1
    # dòng tay dùng bộ đếm id riêng: id của nó có thể TRÙNG số với một dòng core — nhưng không phải dòng đã nạp
    tid = DT.gia_moi(conn, {"ma_doi_thu": "THAK", "ten_goc": "Hang moi", "gia_goc": "5", "loai_nguon": "to_roi"}, None)
    while conn.execute("SELECT 1 FROM core.fact_gia_doi_thu WHERE id=%s", (tid,)).fetchone():
        tid = DT.gia_moi(conn, {"ma_doi_thu": "THAK", "ten_goc": "Hang moi", "gia_goc": "5", "loai_nguon": "to_roi"}, None)
    n_nhat_ky = conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='xac_nhan'").fetchone()[0]
    with pytest.raises(DT.LoiNhap):
        DT.xac_nhan(conn, tid, None)
    with pytest.raises(DT.LoiNhap):
        DT.xac_nhan(conn, 987654321, None)
    assert conn.execute("SELECT count(*) FROM app.dinh_chinh_gia WHERE fact_id IN (%s, 987654321)", (tid,)).fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='xac_nhan'").fetchone()[0] == n_nhat_ky


def test_dat_ghep_ma_kome_go_nham_la_LoiNhap(conn, batch):
    _hang(conn, batch)
    with pytest.raises(DT.LoiNhap, match="NT0l"):
        DT.dat_ghep(conn, "THAK", "h1", "NT0l", None, "cung_hang", None)
    assert conn.execute("SELECT count(*) FROM app.ghep_hang").fetchone()[0] == 0
    DT.dat_ghep(conn, "THAK", "h1", "NT01", None, "cung_hang", None)          # mã thật: qua
    DT.dat_ghep(conn, "THAK", "h1", None, None, "khong", None)                # không mã: qua


def test_kg_dau_phay_LUON_la_thap_phan_con_gia_giu_luat_nghin(conn, batch):
    assert DT._so("1,500", "k", True, True) == Decimal("1.5")
    assert DT._so("0,5", "k", True, True) == Decimal("0.5")
    assert DT._so("1.5", "k", True, True) == Decimal("1.5")
    assert DT._so("1,500", "g") == 1500
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850)
    DT.sua(conn, fid, {"kg_moi_don_vi_gia": "1,500"}, None)
    conn.commit()
    assert float(conn.execute("SELECT kg_moi_don_vi_gia FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s",
                              (fid,)).fetchone()[0]) == 1.5
    assert DT._chuoi_so("1,500", "Giá") == "1500"


def test_sua_tu_choi_gia_tri_trong(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 850)
    for v in ("", "   ", None):
        with pytest.raises(DT.LoiNhap, match="Để trống"):
            DT.sua(conn, fid, {"quy_cach_goc": v}, None)
    with pytest.raises(DT.LoiNhap, match="Để trống"):
        DT.sua(conn, fid, {"gia_goc": "5", "thue": ""}, None)
    assert conn.execute("SELECT count(*) FROM app.dinh_chinh_gia WHERE fact_id=%s", (fid,)).fetchone()[0] == 0


def test_gia_moi_hang_moi_co_khoa_GIONG_goi_doi_thu(conn, batch):
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location("goi", Path("scripts/goi_doi_thu.py"))
    G = importlib.util.module_from_spec(spec); spec.loader.exec_module(G)
    tid = DT.gia_moi(conn, {"ma_doi_thu": "THAK", "ten_goc": "Bột Năng  Tài Ký 400g", "quy_cach_goc": "400g x 24",
                            "gia_goc": "180", "loai_nguon": "to_roi"}, None)
    khoa = conn.execute("SELECT ma_hang_dt FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()[0]
    assert khoa == G.ma_hang_dt({"ten_goc": "Bột Năng  Tài Ký 400g", "quy_cach_goc": "400g x 24"})
    assert khoa.startswith("ten:")
    tid2 = DT.gia_moi(conn, {"ma_doi_thu": "THAK", "ten_goc": "Hang khong quy cach", "gia_goc": "5",
                             "loai_nguon": "to_roi"}, None)
    khoa2 = conn.execute("SELECT ma_hang_dt FROM app.gia_doi_thu_tay WHERE id=%s", (tid2,)).fetchone()[0]
    assert khoa2 == G.ma_hang_dt({"ten_goc": "Hang khong quy cach", "quy_cach_goc": ""})


# ---------------------------------------------------------------- đợt 1b: nhóm & quy cách

def _sp(conn, batch, ma, ten, nganh="冷凍食品_VNM", kind=None):
    conn.execute("INSERT INTO core.dim_product (product_code, product_name, food_category_name, kind_code, batch_id) "
                 "VALUES (%s, %s, %s, %s, %s) ON CONFLICT DO NOTHING", (ma, ten, nganh, kind, batch(9001)))
    conn.commit()


def test_nhom_va_quy_cach_MOT_luot_khong_phi_khong_posm_co_danh_sach_ma(conn, batch, monkeypatch):
    _hang(conn, batch)
    _sp(conn, batch, "NT02", "Ca (1kg x 10 packs)")
    _sp(conn, batch, "MKT01", "Poster", "雑貨_VNM")
    _sp(conn, batch, "FEE01", "Phi ship", "冷凍食品_VNM", kind="1")
    n = DT.tao_nhom(conn, "Basa", ["NT01", "NT02"], None)
    conn.commit()
    dem = _dem(conn, monkeypatch)
    d = DT.nhom_va_quy_cach(conn)
    assert dem["n"] == 1
    monkeypatch.undo()
    ma = [q["ma"] for q in d["quy_cach"]]
    assert "NT01" in ma and "NT02" in ma and "MKT01" not in ma and "FEE01" not in ma
    q1 = next(q for q in d["quy_cach"] if q["ma"] == "NT01")
    assert q1["nganh"] == "冷凍食品_VNM" and float(q1["kg_moi_goi"]) == 0.5 and q1["da_sua"] is False
    assert set(q1) == {"ma", "ten", "nganh", "kg_moi_goi", "goi_moi_thung", "kg_moi_thung", "da_sua"}
    g = next(x for x in d["nhom"] if x["id"] == n)
    assert g["ten"] == "Basa" and [m["ma"] for m in g["ma"]] == ["NT01", "NT02"] and g["ma"][0]["ten"]


def test_them_ma_nhom_chuyen_tu_nhom_khac_va_nhat_ky_co_truoc(conn, batch):
    _hang(conn, batch)
    _sp(conn, batch, "NT02", "Ca (1kg x 10 packs)")
    a = DT.tao_nhom(conn, "A", ["NT01"], None)
    b = DT.tao_nhom(conn, "B", [], None)
    DT.them_ma_nhom(conn, b, ["NT01", "NT02"], None)
    conn.commit()
    assert dict(conn.execute("SELECT product_code, nhom_id FROM app.nhom_so_sanh_ma").fetchall()) == {"NT01": b, "NT02": b}
    truoc, sau = conn.execute("SELECT truoc, sau FROM app.doi_thu_nhat_ky WHERE loai='nhom' ORDER BY id DESC LIMIT 1").fetchone()
    assert truoc == {"NT01": a} and sau["ma_kome"] == ["NT01", "NT02"]
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='nhom'").fetchone()[0] == 3


def test_them_ma_nhom_loi_nhap(conn, batch):
    _hang(conn, batch)
    a = DT.tao_nhom(conn, "A", [], None)
    n0 = conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky").fetchone()[0]
    with pytest.raises(DT.LoiNhap, match="NT0l"):
        DT.them_ma_nhom(conn, a, ["NT01", "NT0l"], None)
    with pytest.raises(DT.LoiNhap):
        DT.them_ma_nhom(conn, 987654321, ["NT01"], None)
    with pytest.raises(DT.LoiNhap):
        DT.them_ma_nhom(conn, a, [], None)
    assert conn.execute("SELECT count(*) FROM app.nhom_so_sanh_ma").fetchone()[0] == 0
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky").fetchone()[0] == n0


def test_bo_ma_nhom_xoa_va_ma_khong_thuoc_nhom_la_LoiNhap(conn, batch):
    _hang(conn, batch)
    a = DT.tao_nhom(conn, "A", ["NT01"], None)
    DT.bo_ma_nhom(conn, "NT01", None)
    conn.commit()
    assert conn.execute("SELECT count(*) FROM app.nhom_so_sanh_ma").fetchone()[0] == 0
    truoc = conn.execute("SELECT truoc FROM app.doi_thu_nhat_ky WHERE loai='nhom' ORDER BY id DESC LIMIT 1").fetchone()[0]
    assert truoc == {"NT01": a}
    with pytest.raises(DT.LoiNhap):
        DT.bo_ma_nhom(conn, "NT01", None)


def test_tao_nhom_ma_la_LoiNhap_va_nhat_ky_ghi_nhom_cu(conn, batch):
    _hang(conn, batch)
    a = DT.tao_nhom(conn, "A", ["NT01"], None)
    with pytest.raises(DT.LoiNhap, match="NT0l"):
        DT.tao_nhom(conn, "B", ["NT0l"], None)
    assert conn.execute("SELECT count(*) FROM app.nhom_so_sanh WHERE ten='B'").fetchone()[0] == 0
    b = DT.tao_nhom(conn, "B", ["NT01"], None)
    conn.commit()
    truoc = conn.execute("SELECT truoc FROM app.doi_thu_nhat_ky WHERE doi_tuong=%s", (f"nhom:{b}",)).fetchone()[0]
    assert truoc == {"NT01": a}


# ---- Đợt 2 (063): tin hiện trường `@` — các khối đọc ---------------------------------------------------

def _tin(conn, batch, khach, cau, the, gia=(), cach_day=0):
    """Ghi MỘT tin qua đường ghi thật (`ghi_kem_nhac`), commit, rồi (tuỳ chọn) lùi ngày của lần tiếp xúc."""
    from kome import lien_he as LH
    r = LH.ghi_kem_nhac(conn, khach, None, "goi", "tot", cau, "", list(the), list(gia))
    if cach_day:
        conn.execute("UPDATE app.nhat_ky_tiep_xuc SET thoi_diem = now() - make_interval(days => %s) WHERE id = %s",
                     (cach_day, r["id"]))
    conn.commit()
    return r["id"]


def _cau(ben):
    return f"Khách nói @{ben} bán @Basa rẻ hơn mình"


def _the_kep(cau, ben, nhom):
    """Hai thẻ: `@<ben>` (đối thủ) rồi `@Basa` (nhóm)."""
    from tests.test_lien_he import _the
    return [_the(cau, "doi_thu", ben, "@" + ben), _the(cau, "nhom", nhom, "@Basa")]


def _gia_ke(ben, nhom, gia, dv="kg"):
    return {"ma_doi_thu": ben, "nhom_khoa": nhom, "gia_goc": gia, "don_vi_gia": dv}


def _nen_tin(conn, batch):
    from tests.test_khach_hang import _ho_so_khach
    _hang(conn, batch)
    _ho_so_khach(conn, batch, "K0001", "Quán một", prefecture="東京都")
    _ho_so_khach(conn, batch, "K0002", "Quán hai", prefecture="大阪府")


def test_goi_y_nhac_dung_mot_luot_va_dung_noi_dung(conn, batch, monkeypatch):
    _hang(conn, batch)
    b = batch(9002)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, kind_code, food_category_name, batch_id)
                    VALUES ('FEE1', 'Phi giao hang', '1', '', %s)""", (b,))
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm cá') RETURNING id").fetchone()[0]
    conn.execute("UPDATE app.doi_thu SET dang_theo_doi = false WHERE ma = 'YUMI'")
    conn.commit()
    dem = _dem(conn, monkeypatch)
    r = DT.goi_y_nhac(conn)
    assert dem["n"] == 1
    ma = {x["ma"] for x in r["doi_thu"]}
    assert "THAK" in ma and "YUMI" not in ma and set(r["doi_thu"][0]) == {"ma", "ten"}
    hang = {x["khoa"]: x for x in r["hang"]}
    assert hang[f"n:{n}"] == {"khoa": f"n:{n}", "ten": "Nhóm cá", "loai": "nhom"}
    assert hang["ma:NT01"]["loai"] == "ma" and hang["ma:NT01"]["ten"].startswith("Ca Ba sa")
    assert "ma:FEE1" not in hang                       # phí không phải hàng
    assert r["hang"][0]["loai"] == "nhom"              # nhóm có tên đứng trước mã


def test_khach_doi_thu_tin_90_ngay_dung_mot_luot(conn, batch, monkeypatch):
    from datetime import timedelta
    from kome.tuoi_du_lieu import hom_nay_o_nhat
    _nen_tin(conn, batch)
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), [_gia_ke("THAK", "ma:NT01", 1200)], cach_day=12)
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), cach_day=100)     # ngoài 90 ngày
    _tin(conn, batch, "K0002", _cau("ICHIBA"), _the_kep(_cau("ICHIBA"), "ICHIBA", "ma:NT01"))                # khách khác
    from kome import lien_he as LH
    LH.ghi(conn, "K0001", None, "goi", "tot", "không thẻ nào")                        # tin không thẻ: không vào
    conn.commit()
    dem = _dem(conn, monkeypatch)
    r = DT.khach_doi_thu(conn, "K0001")
    assert dem["n"] == 1
    assert len(r["tin"]) == 1
    t = r["tin"][0]
    assert t["noi_dung"] == cau and t["ngay"] == (hom_nay_o_nhat() - timedelta(days=12)).isoformat()
    assert t["doi_thu"] == [{"ma": "THAK", "ten": "THAK JSC"}]
    assert t["nhom"] == [{"khoa": "ma:NT01", "ten": "Ca Ba sa cat khuc (500g x 20 packs)"}]
    assert t["gia"] == [{"ma_doi_thu": "THAK", "ten_doi_thu": "THAK JSC", "nhom_khoa": "ma:NT01",
                         "ten_nhom": "Ca Ba sa cat khuc (500g x 20 packs)", "gia_goc": 1200, "don_vi_gia": "kg"}]
    assert {"tiep_xuc_id", "ngay", "nguoi"} <= set(t)
    assert t["nhac"] == [{"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": 10, "do_dai": 5},
                         {"loai": "nhom", "khoa": "ma:NT01", "vi_tri_dau": 20, "do_dai": 5}]
    assert r["ly_do_ngung"] == []


def test_khach_doi_thu_nhac_theo_thu_tu_trong_cau_vi_tri_theo_ky_tu(conn, batch, monkeypatch):
    """`nhac` sắp theo `vi_tri_dau` (thứ tự trong câu), KHÔNG theo thứ tự mảng gửi lên hay theo mã; vị trí là
    KÝ TỰ Unicode như đã lưu (emoji đứng trước = 1, không phải 2 đơn vị UTF-16). Hai đối thủ trong một tin."""
    def _the(cau, loai, khoa, nhan):      # đúng như giao diện gửi: chỉ số chuỗi JS (đơn vị UTF-16)
        u16 = lambda x: len(x.encode("utf-16-le")) // 2
        return {"loai": loai, "khoa": khoa, "vi_tri_dau": u16(cau[:cau.index(nhan)]), "do_dai": u16(nhan)}
    _nen_tin(conn, batch)
    _hang(conn, batch, "NT02", "Tom su dong lanh")
    cau = "🐟 @THAK bán @Basa, còn @ICHIBA bán @Tom"
    # Mảng gửi lên cố ý đảo: nhóm sau cùng trước, đối thủ sau trước đối thủ đầu.
    the = [_the(cau, "nhom", "ma:NT02", "@Tom"), _the(cau, "doi_thu", "ICHIBA", "@ICHIBA"),
           _the(cau, "nhom", "ma:NT01", "@Basa"), _the(cau, "doi_thu", "THAK", "@THAK")]
    assert the[3]["vi_tri_dau"] == 3                       # UTF-16: emoji = 2 đơn vị + khoảng trắng
    _tin(conn, batch, "K0001", cau, the)
    dem = _dem(conn, monkeypatch)
    t = DT.khach_doi_thu(conn, "K0001")["tin"][0]
    assert dem["n"] == 1
    assert t["nhac"] == [{"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": 2, "do_dai": 5},
                         {"loai": "nhom", "khoa": "ma:NT01", "vi_tri_dau": 12, "do_dai": 5},
                         {"loai": "doi_thu", "khoa": "ICHIBA", "vi_tri_dau": 23, "do_dai": 7},
                         {"loai": "nhom", "khoa": "ma:NT02", "vi_tri_dau": 35, "do_dai": 4}]
    for z in t["nhac"]:                                    # vị trí ký tự khớp đúng chữ trong câu đã lưu
        assert t["noi_dung"][z["vi_tri_dau"]] == "@"


def test_ly_do_ngung_chi_ra_cap_da_ngung_mua_cung_nhom_duoc_nhac(conn, batch):
    """[CRITICAL] Chỉ cặp (khách, mã) mà bất biến 024 xếp 'ngung' VÀ mã thuộc nhóm được nhắc trong 90 ngày."""
    from datetime import timedelta
    from tests.test_khach_hang import HOM_NAY, _mua, _neo
    _nen_tin(conn, batch)
    _hang(conn, batch, "NT02", "Tom su dong lanh")
    _hang(conn, batch, "NT03", "Muc ong dong lanh")
    _hang(conn, batch, "NT04", "Bach tuoc dong lanh")
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm hải sản') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma VALUES ('NT03', %s)", (n,))
    conn.commit()
    # NT01: mua đều 7 ngày/lần rồi im 40 ngày -> 'ngung' · NT03: như NT01 (thuộc nhóm có tên) · NT04: 'ngung' nhưng KHÔNG ai nhắc
    # NT02: còn mua (lần cuối cách mốc 2 ngày) -> 'mua', dù được nhắc
    for hang, im in (("NT01", 40), ("NT03", 40), ("NT04", 40), ("NT02", 2)):
        for i in range(5):
            _mua(conn, batch, "K0001", HOM_NAY - timedelta(days=im + i * 7), hang=hang)
    _neo(conn, batch)
    trang = dict(conn.execute("SELECT product_code, trang_thai_cap FROM mart.khach_mat_hang WHERE customer_code='K0001'").fetchall())
    assert trang["NT01"] == trang["NT03"] == trang["NT04"] == "ngung" and trang["NT02"] == "mua"
    cau = "@THAK @Basa @Tom @Muc"
    the = [{"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": 0, "do_dai": 5},
           {"loai": "nhom", "khoa": "ma:NT01", "vi_tri_dau": 6, "do_dai": 5},
           {"loai": "nhom", "khoa": "ma:NT02", "vi_tri_dau": 12, "do_dai": 4},
           {"loai": "nhom", "khoa": f"n:{n}", "vi_tri_dau": 17, "do_dai": 4}]
    _tin(conn, batch, "K0001", cau, the, cach_day=12)
    ly = DT.khach_doi_thu(conn, "K0001")["ly_do_ngung"]
    assert {x["ma"] for x in ly} == {"NT01", "NT03"}
    x1 = next(x for x in ly if x["ma"] == "NT01")
    assert x1["nhom_khoa"] == "ma:NT01" and x1["doi_thu"] == [{"ma": "THAK", "ten": "THAK JSC"}]
    assert x1["ten"].startswith("Ca Ba sa") and x1["lan_cuoi"] == (HOM_NAY - timedelta(days=40)).isoformat()
    assert x1["so_ngay"] == 40 and x1["tin_ngay"] and x1["tiep_xuc_id"]
    x3 = next(x for x in ly if x["ma"] == "NT03")
    assert x3["nhom_khoa"] == f"n:{n}" and x3["ten_nhom"] == "Nhóm hải sản"


def test_ly_do_ngung_khong_co_tin_thi_rong_du_khach_da_ngung(conn, batch):
    from datetime import timedelta
    from tests.test_khach_hang import HOM_NAY, _mua, _neo
    _nen_tin(conn, batch)
    for i in range(5):
        _mua(conn, batch, "K0001", HOM_NAY - timedelta(days=40 + i * 7), hang="NT01")
    _neo(conn, batch)
    assert DT.khach_doi_thu(conn, "K0001") == {"tin": [], "ly_do_ngung": []}


def test_ho_so_ben_khach_dang_mua_tin_90_ngay_cua_dung_ben(conn, batch, monkeypatch):
    _nen_tin(conn, batch)
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), [_gia_ke("THAK", "ma:NT01", 1200)], cach_day=3)
    _tin(conn, batch, "K0002", cau, _the_kep(cau, "THAK", "ma:NT01"), cach_day=20)
    _tin(conn, batch, "K0002", _cau("ICHIBA"), _the_kep(_cau("ICHIBA"), "ICHIBA", "ma:NT01"))                 # bên khác
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), cach_day=120)      # quá 90 ngày
    dem = _dem(conn, monkeypatch)
    r = DT.ho_so_ben(conn, "THAK")
    assert dem["n"] == 1
    kh = r["khach_dang_mua"]
    assert [(x["ma_khach"], x["ten_khach"]) for x in kh] == [("K0001", "Quán một"), ("K0002", "Quán hai")]
    assert kh[0]["nhom"] == [{"khoa": "ma:NT01", "ten": "Ca Ba sa cat khuc (500g x 20 packs)"}]
    assert kh[0]["gia"] == [{"nhom_khoa": "ma:NT01", "ten_nhom": "Ca Ba sa cat khuc (500g x 20 packs)",
                             "gia_goc": 1200, "don_vi_gia": "kg"}]
    assert kh[1]["gia"] == [] and {"tiep_xuc_id", "ngay"} <= set(kh[0])
    assert DT.ho_so_ben(conn, "KHONG-CO") is None


def test_tong_quan_hien_truong_30_ngay_theo_ben_nhom_tinh(conn, batch, monkeypatch):
    _nen_tin(conn, batch)
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), cach_day=2)
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), cach_day=9)
    _tin(conn, batch, "K0002", _cau("ICHIBA"), _the_kep(_cau("ICHIBA"), "ICHIBA", "ma:NT01"))
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), cach_day=45)      # quá 30 ngày
    dem = _dem(conn, monkeypatch)
    h = DT.tong_quan(conn)["hien_truong"]
    assert dem["n"] == 1
    assert h["ngay"] == 30 and h["tong"] == 3
    assert [(x["ma"], x["ten"], x["so_tin"]) for x in h["doi_thu"]] == [("THAK", "THAK JSC", 2), ("ICHIBA", "Ichiba Foods", 1)]
    assert [(x["khoa"], x["so_tin"]) for x in h["nhom"]] == [("ma:NT01", 3)]
    assert h["nhom"][0]["ten"].startswith("Ca Ba sa")
    assert [(x["tinh"], x["so_tin"]) for x in h["tinh"]] == [("東京都", 2), ("大阪府", 1)]


def test_tong_quan_hien_truong_rong_khi_chua_co_tin(conn, batch):
    h = DT.tong_quan(conn)["hien_truong"]
    assert h == {"ngay": 30, "tong": 0, "doi_thu": [], "nhom": [], "tinh": []}
