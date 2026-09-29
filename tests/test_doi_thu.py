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
