"""kome/doi_thu.py — đọc/ghi của màn /doi-thu (đặc tả §4, §5)."""
from datetime import date
from decimal import Decimal
import json
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
    # Cùng (bid, ngày) = CÙNG một lô (một file nạp) — mart.dieu_kien_hien_hanh (068) lấy LÔ mới nhất của bên, nên hai
    # dòng của một gói phải chung batch_id như lúc nạp thật (fixture `batch` tạo lô mới mỗi lần gọi).
    lo = batch.__dict__.setdefault("_lo_dk", {})
    if (bid, ngay) not in lo:
        lo[(bid, ngay)] = batch(bid, ngay)
    conn.execute("INSERT INTO core.fact_dieu_kien_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon, loai, noi_dung)"
                 " VALUES (%s,%s,%s,%s,%s,%s)", (lo[(bid, ngay)], ma_dong, ben, ngay, loai, nd))
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


# ---- Final fix round: khoá nhóm HIỆN HÀNH (mart.nhom_cua_khoa, 063) · hàng Duyệt · 48 tỉnh -----------------

def _nhom_co_ten(conn, batch):
    """Nhóm có tên 'Nhóm cá' gồm NT01 + NT05; ba bên A/B/C chỉ bán NT05 (bảng giá) ở ¥540/560/580 /kg."""
    from tests.test_mart_doi_thu import _qs
    _nen_tin(conn, batch)
    _hang(conn, batch, "NT05", "Ca tra phi le")
    g = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm cá') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma VALUES ('NT01', %s), ('NT05', %s)", (g, g))
    conn.commit()
    for ben, gia in (("A", 540), ("B", 560), ("C", 580)):
        _qs(conn, batch, ben, gia, ma="NT05")
    return g


def test_the_ma_cua_hang_thuoc_nhom_co_ten_VAO_nhom_do(conn, batch):
    """[IMPORTANT] Thẻ `@<mã>` (khoá 'ma:NT01', lưu NGUYÊN như lúc ghi) của mã nằm trong nhóm có tên: giá khách kể
    so với các bên CÙNG NHÓM (cảnh báo bật), lên So sánh giá trong nhóm đó, Hiện trường đếm MỘT nhóm, hồ sơ khách
    / hồ sơ bên trả khoá nhóm."""
    from kome import lien_he as LH
    g = _nhom_co_ten(conn, batch)
    nk = f"n:{g}"
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    r = LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", cau, "", _the_kep(cau, "THAK", "ma:NT01"),
                        [_gia_ke("THAK", "ma:NT01", 1400)])
    conn.commit()
    assert r["canh_bao"] == ["Giá ¥1,400/kg lệch xa trung vị ¥560/kg của nhóm — kiểm lại đơn vị?"]
    # Sổ giữ nguyên chữ đã ghi.
    assert conn.execute("SELECT nhom_khoa FROM app.gia_doi_thu_tay WHERE loai_nguon = 'khach_ke'").fetchone()[0] == "ma:NT01"
    assert conn.execute("SELECT khoa FROM app.tiep_xuc_nhac WHERE loai = 'nhom'").fetchone()[0] == "ma:NT01"
    # So sánh giá: trong nhóm có tên, có đúng một dòng khách kể; trung vị không đổi (khách kể ngoài trung vị).
    ss = DT.so_sanh(conn)["nhom"]
    nhom = [n for n in ss if n["nhom_khoa"] == nk and n["don_vi_so"] == "kg"]
    assert len(nhom) == 1 and nhom[0]["ten_nhom"] == "Nhóm cá" and nhom[0]["trung_vi"] == 560
    assert [q["ma_doi_thu"] for q in nhom[0]["quan_sat"] if q["loai_nguon"] == "khach_ke"] == ["THAK"]
    assert not [n for n in ss if n["nhom_khoa"] == "ma:NT01"]
    # Hiện trường: tin thứ hai gắn thẳng @Nhóm cá — hai tin, MỘT nhóm.
    cau2 = "@ICHIBA có @Nhóm cá"
    _tin(conn, batch, "K0002", cau2, [{"loai": "doi_thu", "khoa": "ICHIBA", "vi_tri_dau": 0, "do_dai": 7},
                                      {"loai": "nhom", "khoa": nk, "vi_tri_dau": 11, "do_dai": 8}])
    h = DT.tong_quan(conn)["hien_truong"]
    assert h["nhom"] == [{"khoa": nk, "ten": "Nhóm cá", "so_tin": 2}]
    # Hồ sơ khách + hồ sơ bên: khoá nhóm hiện hành ở cả thẻ, nhóm, giá.
    t = DT.khach_doi_thu(conn, "K0001")["tin"][0]
    assert t["nhom"] == [{"khoa": nk, "ten": "Nhóm cá"}]
    assert [z["khoa"] for z in t["nhac"] if z["loai"] == "nhom"] == [nk]
    assert (t["gia"][0]["nhom_khoa"], t["gia"][0]["ten_nhom"]) == (nk, "Nhóm cá")
    kh = DT.ho_so_ben(conn, "THAK")["khach_dang_mua"][0]
    assert kh["nhom"] == [{"khoa": nk, "ten": "Nhóm cá"}]
    assert (kh["gia"][0]["nhom_khoa"], kh["gia"][0]["ten_nhom"]) == (nk, "Nhóm cá")


def test_doi_thanh_vien_nhom_SAU_khi_ghi_moi_cho_di_theo(conn, batch):
    """Giải lúc ĐỌC: thẻ 'ma:NT01' ghi khi NT01 còn lẻ; thêm NT01 vào nhóm sau đó -> mọi chỗ đọc theo nhóm mới."""
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    _nen_tin(conn, batch)
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), [_gia_ke("THAK", "ma:NT01", 900)])
    assert DT.tong_quan(conn)["hien_truong"]["nhom"][0]["khoa"] == "ma:NT01"
    g = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm cá') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma VALUES ('NT01', %s)", (g,))
    conn.commit()
    assert DT.tong_quan(conn)["hien_truong"]["nhom"][0]["khoa"] == f"n:{g}"
    assert conn.execute("SELECT nhom_khoa FROM mart.gia_doi_thu_quan_sat WHERE loai_nguon = 'khach_ke'"
                        ).fetchone()[0] == f"n:{g}"
    assert conn.execute("SELECT mart.nhom_cua_khoa('ma:NT01'), mart.nhom_cua_khoa('ma:KHONG'), mart.nhom_cua_khoa('n:7')"
                        ).fetchone() == (f"n:{g}", "ma:KHONG", "n:7")


def test_ly_do_ngung_khop_the_ma_cua_hang_KHAC_cung_nhom(conn, batch):
    """Mã ngừng mua NT05 thuộc 'Nhóm cá'; tin chỉ gắn '@<NT01>' (khoá 'ma:NT01', cùng nhóm) -> vẫn là lý do."""
    from datetime import timedelta
    from tests.test_khach_hang import HOM_NAY, _mua, _neo
    g = _nhom_co_ten(conn, batch)
    for i in range(5):
        _mua(conn, batch, "K0001", HOM_NAY - timedelta(days=40 + i * 7), hang="NT05")
    _neo(conn, batch)
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"))
    ly = DT.khach_doi_thu(conn, "K0001")["ly_do_ngung"]
    assert [(x["ma"], x["nhom_khoa"], x["ten_nhom"]) for x in ly] == [("NT05", f"n:{g}", "Nhóm cá")]


def test_goi_y_nhac_ma_thuoc_nhom_goi_y_NHOM_kem_ten_hang(conn, batch):
    _hang(conn, batch)
    _hang(conn, batch, "NT05", "Ca tra phi le")
    g = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm cá') RETURNING id").fetchone()[0]
    conn.execute("INSERT INTO app.nhom_so_sanh_ma VALUES ('NT05', %s)", (g,))
    conn.commit()
    hang = DT.goi_y_nhac(conn)["hang"]
    assert hang[0] == {"khoa": f"n:{g}", "ten": "Nhóm cá", "loai": "nhom"}
    ma = {x["ma"]: x for x in hang if x["loai"] == "ma"}
    assert ma["NT05"] == {"khoa": f"n:{g}", "ten": "Ca tra phi le", "loai": "ma", "ma": "NT05", "ten_nhom": "Nhóm cá"}
    assert ma["NT01"] == {"khoa": "ma:NT01", "ten": "Ca Ba sa cat khuc (500g x 20 packs)", "loai": "ma", "ma": "NT01"}


def test_duyet_khach_ke_da_co_nhom_khong_vao_chua_ghep_va_cho_duyet_nhung_van_bat_thuong(conn, batch):
    """[IMPORTANT] Giá khách kể mang sẵn nhóm: không có gì để ghép -> không vào 'chưa ghép' và không đếm 'chờ duyệt';
    nhưng giá khách kể BẤT THƯỜNG vẫn thấy ở bộ lọc 'bất thường'."""
    from kome import lien_he as LH
    from tests.test_mart_doi_thu import _qs
    _nhom_co_ten(conn, batch)
    _qs(conn, batch, "D", 500, ma=None, hang="ten:la|D")               # bảng giá chưa ghép — vẫn phải hiện
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    r = LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", cau, "", _the_kep(cau, "THAK", "ma:NT01"),
                        [_gia_ke("THAK", "ma:NT01", 1400)])
    conn.commit()
    assert r["canh_bao"]                                               # khách kể này bất thường
    chua = DT.duyet(conn, loc="chua_ghep")["dong"]
    assert [x["ma_doi_thu"] for x in chua] == ["D"]
    bt = DT.duyet(conn, loc="bat_thuong")["dong"]
    assert [(x["ma_doi_thu"], x["loai_nguon"]) for x in bt] == [("THAK", "khach_ke")]
    ben = {b["ma"]: b for b in DT.tong_quan(conn)["ben"]}
    assert ben["THAK"]["cho_duyet"] == 0 and ben["THAK"]["so_dong"] == 1


def test_hien_truong_du_48_dong_tinh_ke_ca_chua_ro(conn, batch):
    from kome import lien_he as LH
    ten = [r[0] for r in conn.execute("SELECT ten FROM core.dim_prefecture ORDER BY ma_jis")]
    assert len(ten) == 47
    b = batch(9003)
    kh = [(f"P{i:04d}", t) for i, t in enumerate(ten + [""])]
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO core.dim_customer (customer_code, valid_from, valid_to, is_current, customer_name,
                                                          prefecture, batch_id)
                           VALUES (%s, '2025-01-01', '9999-12-31', true, %s, %s, %s)""",
                        [(m, m, t, b) for m, t in kh])
    for m, _ in kh:
        LH.ghi_kem_nhac(conn, m, None, "goi", "tot", "@THAK", "",
                        [{"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": 0, "do_dai": 5}], [])
    conn.commit()
    tinh = DT.tong_quan(conn)["hien_truong"]["tinh"]
    assert len(tinh) == 48 and "(chưa rõ)" in {x["tinh"] for x in tinh}


def test_khach_ke_gan_ma_roi_gan_nhom_MOT_dong_hien_hanh_la_gia_moi(conn, batch):
    """Cùng khách + cùng bên: lần đầu gắn `ma:NT01` (NT01 thuộc nhóm g), lần sau gắn `n:g` -> ĐÚNG MỘT dòng hiện hành
    trong nhóm g và là giá MỚI. Khoá chuỗi dựng lúc đọc (063); cột lưu `ma_hang_dt` giữ nguyên chữ đã ghi."""
    g = _nhom_co_ten(conn, batch)
    nk = f"n:{g}"
    cau = "Khách nói @THAK bán @Basa rẻ hơn mình"
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", "ma:NT01"), [_gia_ke("THAK", "ma:NT01", 600)], cach_day=5)
    conn.execute("UPDATE app.gia_doi_thu_tay SET luc = now() - interval '5 days' WHERE loai_nguon = 'khach_ke'")
    conn.commit()
    _tin(conn, batch, "K0001", cau, _the_kep(cau, "THAK", nk), [_gia_ke("THAK", nk, 620)])
    assert sorted(r[0] for r in conn.execute("SELECT ma_hang_dt FROM app.gia_doi_thu_tay WHERE loai_nguon = 'khach_ke'")) \
        == sorted(["ke:K0001:ma:NT01", f"ke:K0001:{nk}"])                        # sổ không đổi
    hh = conn.execute("""SELECT gia_goc, ma_hang_dt FROM mart.gia_doi_thu_hien_hanh
                         WHERE loai_nguon = 'khach_ke' AND nhom_khoa = %s""", (nk,)).fetchall()
    assert [(float(a), b) for a, b in hh] == [(620.0, f"ke:K0001:{nk}")]
    qs = DT.so_sanh(conn)["nhom"]
    ke = [q for n in qs if n["nhom_khoa"] == nk for q in n["quan_sat"] if q["loai_nguon"] == "khach_ke"]
    assert [q["gia_goc"] for q in ke] == [620]
    # Hồ sơ đối thủ: cả hai lần là CÙNG một chuỗi (lịch sử theo ma_hang_dt + kênh + mức), đúng một dòng hiện hành.
    ho = DT.ho_so_ben(conn, "THAK")["quan_sat"]
    chuoi = [q for q in ho if q["loai_nguon"] == "khach_ke"]
    assert {q["ma_hang_dt"] for q in chuoi} == {f"ke:K0001:{nk}"} and len(chuoi) == 2
    assert [q["gia_goc"] for q in chuoi if q["hien_hanh"]] == [620]
    # Khách khác vẫn là chuỗi riêng.
    _tin(conn, batch, "K0002", cau, _the_kep(cau, "THAK", nk), [_gia_ke("THAK", nk, 700)])
    assert conn.execute("""SELECT count(*) FROM mart.gia_doi_thu_hien_hanh
                           WHERE loai_nguon = 'khach_ke' AND nhom_khoa = %s""", (nk,)).fetchone()[0] == 2


@pytest.mark.parametrize("lk", ["http://drive.google.com/x", "javascript:alert(1)", "https://a b", "https://x\n",
                                 "https://\ud800", 5, ["https://x"], "https://" + "a" * 2000])
def test_kiem_lien_ket_tu_choi_dang_sai(lk):
    from kome import doi_thu as DT
    with pytest.raises(DT.LoiNhap):
        DT.kiem_lien_ket(lk, "Link")


def test_kiem_lien_ket_rong_la_None_va_https_giu_nguyen():
    from kome import doi_thu as DT
    assert DT.kiem_lien_ket(None, "Link") is None and DT.kiem_lien_ket("", "Link") is None
    assert DT.kiem_lien_ket("https://drive.google.com/x?id=1", "Link") == "https://drive.google.com/x?id=1"


def test_dat_thu_muc_upsert_va_ghi_nhat_ky(conn):
    from kome import doi_thu as DT
    DT.dat_thu_muc(conn, "2026-08", "https://drive.google.com/a", None)
    DT.dat_thu_muc(conn, "2026-08", "https://drive.google.com/b", None)
    conn.commit()
    assert conn.execute("SELECT thang::text, lien_ket FROM app.thu_muc_nguon").fetchall() == [("2026-08-01", "https://drive.google.com/b")]
    nk = conn.execute("SELECT truoc, sau FROM app.doi_thu_nhat_ky WHERE loai = 'thu_muc' ORDER BY id").fetchall()
    assert nk == [(None, {"lien_ket": "https://drive.google.com/a"}),
                  ({"lien_ket": "https://drive.google.com/a"}, {"lien_ket": "https://drive.google.com/b"})]


@pytest.mark.parametrize("thang", ["2026-13", "2026-8", "08-2026", "", None, 202608, "0000-01", "1899-12", "2100-01"])
def test_dat_thu_muc_thang_sai_dang(conn, thang):
    from kome import doi_thu as DT
    with pytest.raises(DT.LoiNhap):
        DT.dat_thu_muc(conn, thang, "https://drive.google.com/a", None)


def test_gia_moi_luu_link_bang_chung_va_tu_choi_link_sai(conn, batch):
    from kome import doi_thu as DT
    from tests.test_mart_doi_thu import _hang, _qs
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 540)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi",
                            "lien_ket_bang_chung": "https://drive.google.com/anh"}, None)
    conn.commit()
    assert conn.execute("SELECT lien_ket_bang_chung FROM app.gia_doi_thu_tay WHERE id = %s", (tid,)).fetchone()[0] \
        == "https://drive.google.com/anh"
    with pytest.raises(DT.LoiNhap):
        DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi",
                          "lien_ket_bang_chung": "javascript:x"}, None)


def test_cac_cau_doc_mang_4_khoa_nguon(conn, batch):
    from kome import doi_thu as DT
    from tests.test_mart_doi_thu import _hang, _qs
    _hang(conn, batch)
    for b, g in [("THAK", 540), ("HSC", 560), ("JVB", 580)]:
        _qs(conn, batch, b, g)                                            # lô data_date 2026-07-20
    DT.dat_thu_muc(conn, "2026-07", "https://drive.google.com/t7", None)
    conn.commit()
    qs = DT.so_sanh(conn)["nhom"][0]["quan_sat"] + DT.duyet(conn)["dong"] + DT.ho_so_ben(conn, "THAK")["quan_sat"]
    assert qs and all({"thang_lo", "lien_ket_thu_muc", "web_ben", "lien_ket_bang_chung"} <= set(q) for q in qs)
    thak = [q for q in DT.duyet(conn)["dong"] if q["ma_doi_thu"] == "THAK"][0]
    assert (thak["thang_lo"], thak["lien_ket_thu_muc"], thak["web_ben"]) == ("2026-07-01", "https://drive.google.com/t7",
                                                                             "https://thak.jp/")


# ---------------------------------------------------------------- sua_quy_cach: ô bằng số hiệu lực = không sửa (066)

def _ovr(conn, ma):
    return conn.execute("SELECT kg_moi_goi, goi_moi_thung, kg_moi_thung FROM app.quy_cach_kome WHERE product_code=%s",
                        (ma,)).fetchone()


def _kg00(conn, ma):
    return float(conn.execute("SELECT kg_00 FROM mart.quy_cach_kome WHERE product_code=%s", (ma,)).fetchone()[0])


def test_sua_quy_cach_o_bang_so_hieu_luc_khong_ghim_so_suy_ra(conn, batch):
    from tests.test_mart_doi_thu import _hang_pack
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    # đúng những gì biểu mẫu gửi lại: kg_moi_goi đã sửa, hai ô còn lại là giá trị hiệu lực (suy ra từ tên) 20 / 6.4
    DT.sua_quy_cach(conn, "BA02", "0.082", "20", "6.4", None)
    conn.commit()
    assert _ovr(conn, "BA02") == (Decimal("0.082"), None, None)
    assert _kg00(conn, "BA02") == pytest.approx(0.082 * 20 * 4)
    n = conn.execute("SELECT truoc, sau FROM app.doi_thu_nhat_ky WHERE loai='quy_cach'").fetchall()
    assert len(n) == 1 and set(n[0][1]) == {"kg_moi_goi"}                 # chỉ ghi ô thật sự đổi


def test_sua_quy_cach_khong_doi_gi_thi_khong_tao_dong_khong_ghi_nhat_ky(conn, batch):
    from tests.test_mart_doi_thu import _hang_pack
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    DT.sua_quy_cach(conn, "BA02", "0.08", "20", "6.4", None)
    conn.commit()
    assert _ovr(conn, "BA02") is None
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='quy_cach'").fetchone()[0] == 0


def test_sua_quy_cach_gui_so_khac_thi_luu_va_de_trong_thi_xoa(conn, batch):
    from tests.test_mart_doi_thu import _hang_pack
    _hang_pack(conn, batch, "BA02", "Xot Barona thit nuong sa (80g x 20 packs×4box)", "")
    DT.sua_quy_cach(conn, "BA02", "0.08", "20", "7", None)
    conn.commit()
    assert _ovr(conn, "BA02") == (None, None, Decimal("7"))
    assert _kg00(conn, "BA02") == pytest.approx(7)
    DT.sua_quy_cach(conn, "BA02", "0.08", "20", "7", None)                 # gửi lại đúng số hiệu lực (7): giữ nguyên
    conn.commit()
    assert _ovr(conn, "BA02") == (None, None, Decimal("7"))
    DT.sua_quy_cach(conn, "BA02", "0.08", "20", "", None)                  # để trống = xoá số người sửa
    conn.commit()
    assert _ovr(conn, "BA02") is None                                       # hết số người sửa nào thì bỏ hẳn dòng
    assert _kg00(conn, "BA02") == pytest.approx(6.4)


# ---------------------------------------------------------------- 4a: sửa gói/thùng, gram/gói, bậc, khuyến mãi

def test_sua_quy_cach_goi_va_bac_va_khuyen_mai(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {"so_goi_thung": "20", "kl_goi_g": "500",
                       "bac": [{"tu": 5, "don_vi_sl": "thung", "gia": "5,300", "don_vi_gia": "thung"}],
                       "khuyen_mai": "mua 10 tặng 1"}, None)
    conn.commit()
    r = conn.execute("SELECT so_goi_thung, kl_goi_g, bac, khuyen_mai FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert r[0] == 20 and float(r[1]) == 500 and r[2] == [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]
    assert r[3] == "mua 10 tặng 1"


def test_xoa_khuyen_mai_va_bac_duoc_nhung_khong_xoa_gia(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {"khuyen_mai": "", "bac": []}, None)
    conn.commit()
    km, bac = conn.execute("SELECT khuyen_mai, bac FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()
    assert km is None and bac == []
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"gia_goc": ""}, None)
    for t in ("so_goi_thung", "kl_goi_g"):                                   # hai trường này KHÔNG xoá được
        with pytest.raises(DT.LoiNhap):
            DT.sua(conn, fid, {t: ""}, None)


def test_xoa_gia_truoc_km_duoc(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {"gia_truoc_km": "600"}, None)
    conn.commit()
    assert conn.execute("SELECT gia_truoc_km FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()[0] == 600
    DT.sua(conn, fid, {"gia_truoc_km": ""}, None)
    conn.commit()
    assert conn.execute("SELECT gia_truoc_km FROM mart.gia_doi_thu_quan_sat WHERE id=%s", (fid,)).fetchone()[0] is None


@pytest.mark.parametrize("truong,v", [
    ("so_goi_thung", "0"), ("so_goi_thung", "2.5"), ("so_goi_thung", "100001"),
    ("kl_goi_g", "0"), ("kl_goi_g", "30001"),
    ("bac", [{"tu": 0, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}]),
    ("bac", [{"tu": 1, "don_vi_sl": "hop", "gia": 1, "don_vi_gia": "kg"}]),
    ("bac", [{"tu": 1, "don_vi_sl": "thung", "gia": 0, "don_vi_gia": "kg"}]),
    ("bac", [{"tu": 1, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "pallet"}]),
    ("bac", [{"tu": 1, "don_vi_sl": "thung", "gia": 1}]),
    ("bac", ["x"]), ("bac", {"tu": 1}), ("bac", 5),
    ("bac", "khong phai json"), ("bac", [{"tu": 1, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}] * 11),
    ("bac", [{"tu": "1" + "0" * 400, "don_vi_sl": "thung", "gia": 1, "don_vi_gia": "kg"}]),
    ("gia_truoc_km", "-1"), ("gia_truoc_km", "abc"), ("gia_truoc_km", "99999999999"),
])
def test_truong_moi_kiem_dau_vao(conn, batch, truong, v):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {truong: v}, None)


def test_bac_nhap_chu_json_chuan_hoa_va_bo_trong_la_xoa():
    assert json.loads(DT.kiem_bac_nhap('[{"tu": "5", "don_vi_sl": "kg", "gia": "1,200", "don_vi_gia": "kg"}]')) == \
        [{"tu": 5, "don_vi_sl": "kg", "gia": 1200, "don_vi_gia": "kg"}]
    assert DT.kiem_bac_nhap("") == "[]" and DT.kiem_bac_nhap([]) == "[]" and DT.kiem_bac_nhap(None) == "[]"


def test_gia_moi_mang_quy_cach_va_bac(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {"so_goi_thung": "20", "kl_goi_g": "500"}, None)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "5200", "loai_nguon": "to_roi",
                            "bac": [{"tu": 5, "don_vi_sl": "thung", "gia": 5000, "don_vi_gia": "thung"}]}, None)
    conn.commit()
    r = conn.execute("SELECT so_goi_thung, kl_goi_g, bac FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()
    assert r[0] == 20 and float(r[1]) == 500 and r[2][0]["gia"] == 5000


def test_gia_moi_khuyen_mai_gia_truoc_km_va_bo_trong_la_null(conn, batch):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "500", "loai_nguon": "to_roi",
                            "khuyen_mai": "giảm 50", "gia_truoc_km": "550", "bac": []}, None)
    tid2 = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "500", "loai_nguon": "to_roi",
                             "khuyen_mai": "", "gia_truoc_km": "", "bac": ""}, None)
    conn.commit()
    r = conn.execute("SELECT khuyen_mai, gia_truoc_km, bac FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()
    assert r[0] == "giảm 50" and r[1] == 550 and r[2] is None
    assert conn.execute("SELECT khuyen_mai, gia_truoc_km, bac FROM app.gia_doi_thu_tay WHERE id=%s", (tid2,)).fetchone() \
        == (None, None, None)


# ---------------------------------------------------------------- chuẩn hoá kl_goi_g / gia_truoc_km (soát cuối đợt 4a)

@pytest.mark.parametrize("truong,nhap,mong", [
    ("kl_goi_g", "500.1234567", Decimal("500.12")), ("kl_goi_g", "0.005", Decimal("0.01")),
    ("gia_truoc_km", "-0", Decimal("0")), ("gia_truoc_km", "550.1234567", Decimal("550.12"))])
def test_sua_va_gia_moi_luu_CUNG_mot_so_da_lam_tron(conn, batch, truong, nhap, mong):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    DT.sua(conn, fid, {truong: nhap}, None)
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "500", "loai_nguon": "to_roi", truong: nhap}, None)
    conn.commit()
    assert conn.execute(f"SELECT {truong} FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s", (fid,)).fetchone()[0] == mong
    assert conn.execute(f"SELECT {truong} FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()[0] == mong


@pytest.mark.parametrize("nhap", ["0.001", "0.004"])
def test_kl_goi_g_lam_tron_ve_0_la_LoiNhap_ca_hai_duong(conn, batch, nhap):
    _hang(conn, batch)
    fid = _qs(conn, batch, "NEXT", 550)
    with pytest.raises(DT.LoiNhap):
        DT.sua(conn, fid, {"kl_goi_g": nhap}, None)
    with pytest.raises(DT.LoiNhap):
        DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "500", "loai_nguon": "to_roi", "kl_goi_g": nhap}, None)



# ---------------------------------------------------------------- đợt 4b — dữ liệu đọc cho màn mới

_QS_4B = {"so_goi_thung", "kl_goi_g", "bac", "kg_thung_dt", "gia_goi", "gia_thung", "gia_1", "gia_5", "gia_10",
          "gia_pallet", "sua_cuoi"}
_NHOM_4B = {"gia_kome_chuan", "gia_kome_bang", "gia_kome_km", "gia_kome_so", "lech_trung_vi", "gia_kome_lech",
            "kome_kg_goi", "kome_goi_thung", "kome_kg_thung"}


def _ba_ben(conn, batch):
    _hang(conn, batch)
    return [_qs(conn, batch, b, g, hang=f"h{b}") for b, g in [("THAK", 540), ("HSC", 560), ("JVB", 580)]]


def _nguoi(conn, ten="lan"):
    i = conn.execute("INSERT INTO app.nguoi_dung (ten_dang_nhap, mat_khau_hash, mat_khau_salt) VALUES (%s, %s, %s)"
                     " RETURNING id", (ten, b"\x00", b"\x00")).fetchone()[0]
    conn.commit()
    return i


def test_4b_so_sanh_mang_khoa_nhom_moi_va_quan_sat_moi(conn, batch):
    _ba_ben(conn, batch)
    n = DT.so_sanh(conn)["nhom"][0]
    assert _NHOM_4B <= set(n)
    assert n["gia_kome_lech"] is False and n["gia_kome_so"] is None
    assert all(_QS_4B <= set(q) for q in n["quan_sat"])
    q = n["quan_sat"][0]
    assert q["gia_1"] == 540 and q["sua_cuoi"] == 0                      # làm tròn yên, chưa ai sửa = 0


def test_4b_sua_cuoi_theo_khoa_gia_va_khoa_ghep(conn, batch):
    fid, fid2, _ = _ba_ben(conn, batch)
    sc = lambda: next(q for q in DT.so_sanh(conn)["nhom"][0]["quan_sat"] if q["id"] == fid)["sua_cuoi"]
    assert sc() == 0
    DT.sua(conn, fid, {"gia_goc": "545"}, None)
    conn.commit()
    k1 = conn.execute("SELECT max(id) FROM app.doi_thu_nhat_ky WHERE doi_tuong=%s", (f"gia:{fid}",)).fetchone()[0]
    assert sc() == k1
    DT.sua(conn, fid2, {"gia_goc": "561"}, None)                           # sửa dòng KHÁC không đổi sua_cuoi
    conn.commit()
    assert sc() == k1
    DT.dat_ghep(conn, "THAK", "hTHAK", "NT01", None, "cung_hang", None)
    conn.commit()
    k2 = conn.execute("SELECT max(id) FROM app.doi_thu_nhat_ky WHERE doi_tuong='THAK/hTHAK'").fetchone()[0]
    assert k2 > k1 and sc() == k2


def test_4b_duyet_va_ho_so_ben_mang_cot_quan_sat_moi(conn, batch):
    _ba_ben(conn, batch)
    assert all(_QS_4B <= set(q) for q in DT.duyet(conn)["dong"])
    assert all(_QS_4B <= set(q) for q in DT.ho_so_ben(conn, "THAK")["quan_sat"])


def test_4b_tong_quan_khuyen_mai_het_hang_mang_khoa_mat_hang(conn, batch):
    _hang(conn, batch)
    km = _qs(conn, batch, "THAK", 540, hang="hkm")
    het = _qs(conn, batch, "HSC", 560, hang="hhet", trang="het")
    DT.sua(conn, km, {"khuyen_mai": "mua 10 tặng 1"}, None)
    conn.commit()
    t = DT.tong_quan(conn)
    k = t["khuyen_mai"][0]
    assert (k["nguon"], k["id"], k["ma_hang_dt"], k["ma_doi_thu"], k["ben"]) == ("nap", km, "hkm", "THAK", "THAK")
    h = t["het_hang"][0]
    assert (h["nguon"], h["id"], h["ma_hang_dt"], h["ma_doi_thu"], h["ten_doi_thu"]) == \
        ("nap", het, "hhet", "HSC", "HSC Station")


def test_4b_tong_quan_dieu_kien_doc_hien_hanh_bo_ghi_chu_doc_ap_dinh_chinh(conn, batch):
    from kome import doi_thu_giao as G
    _dk(conn, batch, 9301, date(2026, 9, 5), "THAK", "ship", "freeship >= 30,000", "d-1")
    _dk(conn, batch, 9301, date(2026, 9, 5), "THAK", "ghi_chu_doc", "chép vào ghi_chu", "d-2")
    _dk(conn, batch, 9301, date(2026, 9, 5), "THAK", "khac", "nghỉ Obon", "d-3")
    fid = conn.execute("SELECT id FROM core.fact_dieu_kien_doi_thu WHERE ma_dong='d-1'").fetchone()[0]
    G.sua_dieu_kien(conn, fact_id=fid, ma_doi_thu="THAK", loai="ship", noi_dung="freeship >= 25,000", bo=False, nguoi=None)
    G.sua_dieu_kien(conn, fact_id=None, ma_doi_thu="THAK", loai="thanh_toan", noi_dung="Chuyển khoản", bo=False, nguoi=None)
    conn.commit()
    dk = {d["noi_dung"]: d for d in DT.tong_quan(conn)["dieu_kien"]}
    assert set(dk) == {"freeship >= 25,000", "Chuyển khoản"}               # bỏ ghi_chu_doc (068) và 'khac' (Tổng quan)
    s = dk["freeship >= 25,000"]
    assert (s["id"], s["fact_id"], s["them_tay"], s["ben"], s["loai"]) == (fid, fid, False, "THAK", "ship")
    nk = dict(conn.execute("SELECT doi_tuong, max(id) FROM app.doi_thu_nhat_ky GROUP BY 1").fetchall())
    assert s["sua_cuoi"] == nk[f"dk:{fid}"]
    tay = dk["Chuyển khoản"]
    assert tay["them_tay"] is True and tay["fact_id"] is None and tay["id"] < 0 and tay["sua_cuoi"] == nk["dk:tay:THAK"]


def test_4b_ho_so_ben_giao_hang_sua_cuoi_ben_dieu_kien_va_gia_kome_so(conn, batch):
    from tests.test_mart_doi_thu import _bang_gia
    from tests.test_doi_thu_giao import _nap
    from kome import doi_thu_giao as G
    _ba_ben(conn, batch)
    _bang_gia(conn, batch, "NT01", "std", 0, 4900)                        # NT01 chưa 荷姿: kg_02 = 20 × 0,5 = 10 kg
    _nap(conn, batch, "THAK", phi_ship=605)
    _dk(conn, batch, 9302, date(2026, 9, 5), "THAK", "khac", "nghỉ Obon", "d-1")
    h = DT.ho_so_ben(conn, "THAK")
    assert h["giao_hang"]["ma_doi_thu"] == "THAK" and h["giao_hang"]["phi_ship"] == 605
    assert h["sua_cuoi_ben"] == 0
    assert [(d["loai"], d["noi_dung"], d["them_tay"]) for d in h["dieu_kien"]] == [("khac", "nghỉ Obon", False)]
    assert isinstance(h["dieu_kien"][0]["id"], int) and h["dieu_kien"][0]["sua_cuoi"] == 0
    assert h["quan_sat"] and all(q["gia_kome_so"] == round(4900 / 1.08 / 10) for q in h["quan_sat"])
    G.sua_giao_hang(conn, "THAK", {"phi_ship": "600"}, None)
    conn.execute("INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong) VALUES ('doi_thu', 'ben:THAK')")
    conn.commit()
    h = DT.ho_so_ben(conn, "THAK")
    assert h["sua_cuoi_ben"] == conn.execute("SELECT max(id) FROM app.doi_thu_nhat_ky WHERE doi_tuong='ben:THAK'").fetchone()[0]
    assert h["giao_hang"]["phi_ship"] == 600
    assert DT.ho_so_ben(conn, "HSC")["giao_hang"] is None                 # bên chưa có lô / sửa giao hàng → null


def test_4b_ho_so_ben_quan_sat_mang_gia_kome_lech_cua_nhom(conn, batch):
    from tests.test_mart_doi_thu import _bang_gia
    _ba_ben(conn, batch)                                                  # trung vị ~560 ¥/kg
    assert all(q["gia_kome_lech"] is False for q in DT.ho_so_ben(conn, "THAK")["quan_sat"])   # chưa có giá KOME
    _bang_gia(conn, batch, "NT01", "std", 0, 60000)                       # 60000 / 1,08 / 10 kg ≈ 5 556 > 3 × trung vị
    qs = DT.ho_so_ben(conn, "THAK")["quan_sat"]
    assert qs and all(q["gia_kome_lech"] is True for q in qs)
    n = next(x for x in DT.so_sanh(conn)["nhom"] if x["nhom_khoa"] == qs[0]["nhom_khoa"])
    assert n["gia_kome_lech"] is True                                     # CÙNG cờ với So sánh (một định nghĩa)


def test_4b_mat_hang_doc_ca_dong_lich_su_va_lich_su_sua_moi_nhat_truoc(conn, batch, monkeypatch):
    _hang(conn, batch)
    cu = _qs(conn, batch, "THAK", 540, hang="h1", ngay=date(2026, 7, 1))
    moi = _qs(conn, batch, "THAK", 560, hang="h1", ngay=date(2026, 8, 1))
    nd = _nguoi(conn)
    DT.sua(conn, cu, {"gia_goc": "545"}, nd)
    DT.dat_ghep(conn, "THAK", "h1", "NT01", None, "cung_hang", None)
    DT.sua(conn, moi, {"gia_goc": "565"}, None)                           # khoá của dòng KHÁC — không vào lịch sử của `cu`
    conn.commit()
    dem = _dem(conn, monkeypatch)
    m = DT.mat_hang(conn, "nap", cu)
    assert dem["n"] == 1
    monkeypatch.undo()
    q = m["quan_sat"]
    assert q["id"] == cu and q["hien_hanh"] is False and q["bat_thuong"] is False and q["gia_goc"] == 545
    assert _QS_4B <= set(q)
    ls = m["lich_su"]
    assert [x["doi_tuong"] for x in ls] == ["THAK/h1", f"gia:{cu}"]
    assert set(ls[0]) >= {"id", "loai", "ai", "luc", "truoc", "sau"}
    assert ls[0]["id"] > ls[1]["id"] and ls[1]["ai"] == "lan" and ls[0]["ai"] is None
    assert q["sua_cuoi"] == ls[0]["id"]
    assert DT.mat_hang(conn, "nap", moi)["quan_sat"]["hien_hanh"] is True
    assert DT.mat_hang(conn, "nap", 999999) is None
    with pytest.raises(DT.LoiNhap):
        DT.mat_hang(conn, "xyz", cu)


def test_4b_mat_hang_dong_tay_theo_khoa_tay(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi"}, None)
    conn.commit()
    m = DT.mat_hang(conn, "tay", tid)
    assert m["quan_sat"]["nguon"] == "tay" and m["quan_sat"]["hien_hanh"] is True
    assert [x["doi_tuong"] for x in m["lich_su"]] == [f"tay:{tid}"]


def test_4b_lich_su_nhieu_khoa_toi_da_5_va_50_dong(conn, batch):
    for i in range(55):
        conn.execute("INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong) VALUES ('giao_hang', %s)", (f"giao:{'AB'[i % 2]}",))
    conn.commit()
    ls = DT.lich_su(conn, ["giao:A", "giao:B"])
    assert len(ls) == 50 and [x["id"] for x in ls] == sorted((x["id"] for x in ls), reverse=True)
    assert DT.lich_su(conn, ["giao:C"]) == []
    for sai in (["a"] * 6, [], ["x" * 301], "giao:A", [1]):
        with pytest.raises(DT.LoiNhap):
            DT.lich_su(conn, sai)


# ---------------------------------------------------------------- đợt 4b task 2: ghi từ pop-up, chống sửa đè

@pytest.fixture
def ben_goc(conn):
    """app.doi_thu sống qua TRUNCATE (GIU_LAI) — test nào sửa THAK thì trả lại dòng gốc khi xong."""
    goc = conn.execute("SELECT ten, web, ghi_chu FROM app.doi_thu WHERE ma='THAK'").fetchone()
    yield
    conn.rollback()
    conn.execute("UPDATE app.doi_thu SET ten=%s, web=%s, ghi_chu=%s WHERE ma='THAK'", goc)
    conn.commit()


def _nk(conn, khoa=None):
    if khoa is None:
        return conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky").fetchone()[0]
    return conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE doi_tuong=%s", (khoa,)).fetchone()[0]


def _max_nk(conn):
    return conn.execute("SELECT coalesce(max(id), 0) FROM app.doi_thu_nhat_ky").fetchone()[0]


def _qs_dong(conn, nguon, id):
    return conn.execute("SELECT nhom_khoa, nhan, ma_kome, gia_goc, hien_hanh FROM mart.gia_doi_thu_quan_sat"
                        " WHERE nguon=%s AND id=%s", (nguon, id)).fetchone()


def test_4b2_nhan_khong_dua_dong_ra_khoi_nhom_va_doi_nhan_giu_ma_kome(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    assert _qs_dong(conn, "nap", fid)[:3] == ("ma:NT01", "thay_the", "NT01")
    ra = DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "nhan": "khong"}, None)
    conn.commit()
    assert _qs_dong(conn, "nap", fid)[0] is None
    assert ra["sua_cuoi"] == _max_nk(conn) and (ra["nguon"], ra["id"]) == ("nap", fid)
    ra = DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": ra["sua_cuoi"], "nhan": "cung_hang"}, None)
    conn.commit()
    assert _qs_dong(conn, "nap", fid)[:3] == ("ma:NT01", "cung_hang", "NT01")   # bỏ nhóm rồi ghép lại: nhớ mã KOME


def test_4b2_hai_truong_khong_gia_la_hai_dinh_chinh_MOT_nhat_ky(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0,
                           "thay_doi": {"so_goi_thung": "20", "khuyen_mai": "mua 10 tặng 1"}}, None)
    conn.commit()
    assert conn.execute("SELECT count(*) FROM app.dinh_chinh_gia WHERE fact_id=%s", (fid,)).fetchone()[0] == 2
    assert _nk(conn) == 1 and _nk(conn, f"gia:{fid}") == 1


@pytest.mark.parametrize("vi_sao", [None, ""])
def test_4b2_truong_gia_khong_co_vi_sao_la_LoiNhap(conn, batch, vi_sao):
    fid = _ba_ben(conn, batch)[0]
    with pytest.raises(DT.LoiNhap, match="vì sao"):
        DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "vi_sao_gia": vi_sao,
                               "thay_doi": {"gia_goc": "520"}}, None)


def test_4b2_da_doi_khong_loai_nguon_la_LoiNhap(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    with pytest.raises(DT.LoiNhap, match="loại nguồn"):
        DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "vi_sao_gia": "da_doi",
                               "thay_doi": {"gia_goc": "520"}}, None)


def test_4b2_doc_sai_la_dinh_chinh_da_doi_la_dong_tay_co_fact_goc(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "vi_sao_gia": "doc_sai",
                           "thay_doi": {"gia_goc": "545"}}, None)
    conn.commit()
    assert conn.execute("SELECT count(*) FROM app.gia_doi_thu_tay").fetchone()[0] == 0
    ra = DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": _max_nk(conn), "vi_sao_gia": "da_doi",
                                "thay_doi": {"thue": "co"}, "loai_nguon": "to_roi",
                                "lien_ket_bang_chung": "https://drive.google.com/x", "ghi_chu_nguon": "Zalo"}, None)
    conn.commit()
    r = conn.execute("SELECT id, fact_goc_id, gia_goc, thue, loai_nguon, lien_ket_bang_chung, ghi_chu_nguon"
                     " FROM app.gia_doi_thu_tay").fetchall()
    assert len(r) == 1 and r[0][1:] == (fid, 545, "co", "to_roi", "https://drive.google.com/x", "Zalo")
    assert (ra["nguon"], ra["id"]) == ("tay", r[0][0])
    assert ra["sua_cuoi"] == conn.execute("SELECT max(id) FROM app.doi_thu_nhat_ky WHERE doi_tuong IN (%s, 'THAK/hTHAK')",
                                          (f"tay:{ra['id']}",)).fetchone()[0]   # sua_cuoi của DÒNG MỚI (khoá của nó)
    assert _qs_dong(conn, "tay", r[0][0])[4] is True and _qs_dong(conn, "nap", fid)[4] is False
    assert _nk(conn, f"gia:{fid}") == 2                    # dòng nạp cũ cũng mang dấu → pop-up cũ của nó bị 409


def test_4b2_sua_dong_tay_la_dong_tay_MOI_va_hai_nhat_ky(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi", "khuyen_mai": "km",
                            "lien_ket_bang_chung": "https://drive.google.com/b"}, None)
    conn.commit()
    ra = DT.sua_mat_hang(conn, {"nguon": "tay", "id": tid, "da_xem": _max_nk(conn), "vi_sao_gia": "doc_sai",
                                "thay_doi": {"gia_goc": "525", "so_goi_thung": "20"}}, None)
    conn.commit()
    moi = ra["id"]
    assert ra["nguon"] == "tay" and moi != tid
    cot = "ma_doi_thu, ma_hang_dt, fact_goc_id, loai_nguon, lien_ket_bang_chung, khuyen_mai, gia_goc, so_goi_thung"
    cu_r = conn.execute(f"SELECT {cot} FROM app.gia_doi_thu_tay WHERE id=%s", (tid,)).fetchone()
    moi_r = conn.execute(f"SELECT {cot} FROM app.gia_doi_thu_tay WHERE id=%s", (moi,)).fetchone()
    assert cu_r[6] == 520 and cu_r[7] is None                               # dòng cũ không đổi (sổ chỉ thêm)
    assert moi_r[:6] == cu_r[:6] and moi_r[6:] == (525, 20)
    assert _nk(conn, f"tay:{tid}") == 2 and _nk(conn, f"tay:{moi}") == 1  # gia_moi + sửa ; sửa
    assert _qs_dong(conn, "tay", moi)[4] is True and _qs_dong(conn, "tay", tid)[4] is False
    assert ra["sua_cuoi"] == _max_nk(conn)


def test_4b2_sua_tay_da_doi_ghi_loai_nguon_moi(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi"}, None)
    conn.commit()
    ra = DT.sua_mat_hang(conn, {"nguon": "tay", "id": tid, "da_xem": _max_nk(conn), "vi_sao_gia": "da_doi",
                                "thay_doi": {"gia_goc": "510"}, "loai_nguon": "chung_tu"}, None)
    conn.commit()
    assert conn.execute("SELECT gia_goc, loai_nguon, fact_goc_id FROM app.gia_doi_thu_tay WHERE id=%s",
                        (ra["id"],)).fetchone() == (510, "chung_tu", fid)


def test_4b2_xung_dot_khong_ghi_gi_ghi_de_thi_ghi(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    lan = _nguoi(conn)
    da_xem = _max_nk(conn)
    DT.sua(conn, fid, {"muc_gia": "sỉ"}, lan)                               # người khác vừa sửa
    conn.commit()
    truoc = (_nk(conn), conn.execute("SELECT count(*) FROM app.dinh_chinh_gia").fetchone()[0])
    b = {"nguon": "nap", "id": fid, "da_xem": da_xem, "nhan": "khong", "thay_doi": {"kenh_gia": "web"}}
    with pytest.raises(DT.XungDot) as e:
        DT.sua_mat_hang(conn, b, None)
    conn.rollback()
    assert e.value.ai == "lan" and isinstance(e.value.luc, str) and "T" in e.value.luc
    assert e.value.sau == {"muc_gia": "sỉ"}
    assert (_nk(conn), conn.execute("SELECT count(*) FROM app.dinh_chinh_gia").fetchone()[0]) == truoc
    assert conn.execute("SELECT count(*) FROM app.ghep_hang").fetchone()[0] == 0
    DT.sua_mat_hang(conn, b | {"ghi_de": True}, None)
    conn.commit()
    assert _qs_dong(conn, "nap", fid)[0] is None and _nk(conn) == truoc[0] + 2


def test_4b2_xung_dot_theo_khoa_ghep_cua_hang(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    DT.dat_ghep(conn, "THAK", "hTHAK", "NT01", None, "cung_hang", None)    # ghép = khoá '<bên>/<hàng>'
    conn.commit()
    with pytest.raises(DT.XungDot):
        DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "thay_doi": {"kenh_gia": "web"}}, None)
    conn.rollback()
    DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": _max_nk(conn), "thay_doi": {"kenh_gia": "web"}}, None)


def test_4b2_khong_co_gi_doi_va_dau_vao_sai_la_LoiNhap(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    for b in ({"nguon": "nap", "id": fid},                                   # rỗng
              {"nguon": "nap", "id": fid, "nhan": "thay_the"},               # nhãn đang là thay_the
              {"nguon": "nap", "id": 999999, "nhan": "khong"},
              {"nguon": "xyz", "id": fid, "nhan": "khong"},
              {"nguon": "nap", "id": "abc", "nhan": "khong"},
              {"nguon": "nap", "id": fid, "nhan": "la"},
              {"nguon": "nap", "id": fid, "thay_doi": ["gia_goc"]},
              {"nguon": "nap", "id": fid, "thay_doi": {"kenh_gia": "x"}, "vi_sao_gia": "?"},
              {"nguon": "nap", "id": fid, "thay_doi": {"kenh_gia": "x"}, "da_xem": "abc"},
              {"nguon": "nap", "id": fid, "thay_doi": {"kenh_gia": "x"}, "da_xem": -1}):
        with pytest.raises(DT.LoiNhap):
            DT.sua_mat_hang(conn, {"da_xem": 0} | b, None)
        conn.rollback()


def test_4b2_mot_phan_hong_thi_khong_phan_nao_vao(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    with pytest.raises(DT.LoiNhap):
        DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "nhan": "khong", "thay_doi": {"so_goi_thung": "1.5"}}, None)
    conn.commit()                                          # kể cả khi người gọi LỠ commit: kiểm trước khi ghi
    assert conn.execute("SELECT count(*) FROM app.ghep_hang").fetchone()[0] == 0 and _nk(conn) == 0


def test_4b2_sua_ben_web_ten_ghi_chu_va_nhat_ky(conn, ben_goc):
    with pytest.raises(DT.LoiNhap):
        DT.sua_ben(conn, "THAK", {"web": "http://thak.jp"}, None)
    for sai in ({"ten": ""}, {"ten": "x" * 81}, {"ghi_chu": "x" * 301}, {"la": "1"}, {}, {"ten": 5}):
        with pytest.raises(DT.LoiNhap):
            DT.sua_ben(conn, "THAK", sai, None)
    with pytest.raises(DT.LoiNhap):
        DT.sua_ben(conn, "KHONG-CO", {"ten": "X"}, None)
    conn.rollback()
    DT.sua_ben(conn, "THAK", {"web": "https://thak.jp", "ghi_chu": "  gọi trước 10h ", "ten": "Thak Foods"}, None)
    conn.commit()
    assert conn.execute("SELECT ten, web, ghi_chu FROM app.doi_thu WHERE ma='THAK'").fetchone() == \
        ("Thak Foods", "https://thak.jp", "gọi trước 10h")
    DT.sua_ben(conn, "THAK", {"web": ""}, None, da_xem=_max_nk(conn))
    conn.commit()
    assert conn.execute("SELECT web FROM app.doi_thu WHERE ma='THAK'").fetchone()[0] is None
    r = conn.execute("SELECT loai, truoc, sau FROM app.doi_thu_nhat_ky WHERE doi_tuong='ben:THAK' ORDER BY id").fetchall()
    assert [x[0] for x in r] == ["doi_thu", "doi_thu"] and r[1][1:] == ({"web": "https://thak.jp"}, {"web": None})
    with pytest.raises(DT.XungDot):
        DT.sua_ben(conn, "THAK", {"ghi_chu": "x"}, None, da_xem=0)


def test_4b2_sua_muc_gia_dong_tay_dong_cu_het_hien_hanh_ngay_nguon_giu_nguyen(conn, batch):
    """Sửa kênh / mức giá đổi phân vùng hien_hanh: dòng cũ (bị thay) KHÔNG được còn hiện hành ở phân vùng cũ."""
    fid = _ba_ben(conn, batch)[0]
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi"}, None)
    conn.execute("UPDATE app.gia_doi_thu_tay SET luc = '2026-08-01 10:00+09' WHERE id=%s", (tid,))
    conn.commit()
    ra = DT.sua_mat_hang(conn, {"nguon": "tay", "id": tid, "da_xem": _max_nk(conn), "thay_doi": {"muc_gia": "sỉ"}}, None)
    conn.commit()
    hh = dict(conn.execute("SELECT id, hien_hanh FROM mart.gia_doi_thu_quan_sat WHERE nguon='tay'").fetchall())
    assert hh == {tid: False, ra["id"]: True}
    ngay = dict(conn.execute("SELECT id, ngay_nguon FROM mart.gia_doi_thu_quan_sat WHERE nguon='tay'").fetchall())
    assert ngay[ra["id"]] == ngay[tid] == date(2026, 8, 1)                 # "đọc sai" giữ ngày nguồn / tuổi
    assert conn.execute("SELECT thay_cho_tay_id FROM app.gia_doi_thu_tay WHERE id=%s", (ra["id"],)).fetchone()[0] == tid
    assert DT.mat_hang(conn, "tay", tid)["quan_sat"]["hien_hanh"] is False  # dòng bị thay vẫn đọc được (lịch sử)


def test_4b2_gia_da_doi_dong_tay_la_ngay_moi_va_thay_dong_cu(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    tid = DT.gia_moi(conn, {"fact_goc_id": fid, "gia_goc": "520", "loai_nguon": "to_roi"}, None)
    conn.execute("UPDATE app.gia_doi_thu_tay SET luc = '2026-08-01 10:00+09' WHERE id=%s", (tid,))
    conn.commit()
    ra = DT.sua_mat_hang(conn, {"nguon": "tay", "id": tid, "da_xem": _max_nk(conn), "vi_sao_gia": "da_doi",
                                "loai_nguon": "chung_tu", "thay_doi": {"kenh_gia": "web", "gia_goc": "500"}}, None)
    conn.commit()
    r = conn.execute("SELECT thay_cho_tay_id, (luc AT TIME ZONE 'Asia/Tokyo')::date > '2026-08-01'"
                     " FROM app.gia_doi_thu_tay WHERE id=%s", (ra["id"],)).fetchone()
    assert r == (tid, True)
    hh = dict(conn.execute("SELECT id, hien_hanh FROM mart.gia_doi_thu_quan_sat WHERE nguon='tay'").fetchall())
    assert hh == {tid: False, ra["id"]: True}


def test_4b2_gia_da_doi_dong_nap_doi_kenh_dong_nap_het_hien_hanh(conn, batch):
    fid = _ba_ben(conn, batch)[0]
    ra = DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "vi_sao_gia": "da_doi", "loai_nguon": "to_roi",
                                "thay_doi": {"kenh_gia": "web"}}, None)
    conn.commit()
    assert _qs_dong(conn, "nap", fid)[4] is False and _qs_dong(conn, "tay", ra["id"])[4] is True
    hien = conn.execute("SELECT nguon, id FROM mart.gia_doi_thu_hien_hanh WHERE ma_doi_thu='THAK'").fetchall()
    assert hien == [("tay", ra["id"])]                                      # MỘT quan sát hiện hành, không phải hai


def test_4b2_dong_bi_thay_sau_moc_van_hien_hanh_khi_xem_lui(conn, batch):
    """Dòng thay mới hơn mốc đang xem thì chưa 'thay' gì — dòng nạp vẫn hiện hành ở mốc cũ."""
    from tests.test_mart_doi_thu import _mua
    fid = _ba_ben(conn, batch)[0]
    _mua(conn, batch, "202601010001", date(2026, 9, 20), hang="NT01")
    DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "vi_sao_gia": "da_doi", "loai_nguon": "to_roi",
                           "thay_doi": {"kenh_gia": "web"}}, None)
    conn.commit()
    conn.execute("SELECT set_config('kome.moc', '2026-08-31', true)")
    assert _qs_dong(conn, "nap", fid)[4] is True
    conn.rollback()


def test_4b2_nhan_ghep_khong_ma_kome_va_khach_ke_bo_ghep_la_LoiNhap(conn, batch):
    from tests.test_mart_doi_thu import _ke
    _hang(conn, batch)
    fid = _qs(conn, batch, "THAK", 540, hang="hX", ma=None)
    with pytest.raises(DT.LoiNhap, match="Chọn mã KOME trước"):
        DT.sua_mat_hang(conn, {"nguon": "nap", "id": fid, "da_xem": 0, "nhan": "cung_hang"}, None)
    conn.rollback()
    ke = _ke(conn, "202601010001", "ma:NT01", 700)
    with pytest.raises(DT.LoiNhap, match="khách kể"):
        DT.sua_mat_hang(conn, {"nguon": "tay", "id": ke, "da_xem": 0, "nhan": "khong"}, None)
    conn.rollback()
    assert _nk(conn) == 0 and conn.execute("SELECT count(*) FROM app.ghep_hang").fetchone()[0] == 0

