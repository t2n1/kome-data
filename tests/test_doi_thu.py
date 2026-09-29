"""kome/doi_thu.py — đọc/ghi của màn /doi-thu (đặc tả §4, §5)."""
from datetime import date
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
