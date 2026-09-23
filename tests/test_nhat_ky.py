"""Màn 20 (Nhật ký thao tác) + 21 (Cài đặt) — migration 033."""
from datetime import date

import pytest
from fastapi.testclient import TestClient

from kome import lien_he as LH
from kome import nhat_ky as NK
from kome.web import nguoi_dung as ND
from kome.web.app import create_app
from tests.test_bao_mat import BI_MAT, MK, _vao
from tests.test_khach_hang import _ho_so_khach


def _lo(conn, ten="売上伝票データ_20260915.xlsx", nap_boi=None, huy=False, huy_boi=None):
    return conn.execute(
        """INSERT INTO meta.ingest_batch (spec_name, source_file, digest, archived_to, row_count,
                                          total_amount, data_date, nap_boi, undone_at, huy_boi)
           VALUES ('uriage', %s, %s, 'x', 1234, 0, '2026-09-15', %s,
                   CASE WHEN %s THEN now() END, %s) RETURNING batch_id""",
        (ten, ten + str(huy), nap_boi, huy, huy_boi)).fetchone()[0]


# ---- Sổ quyền ----------------------------------------------------------------

def test_dat_quyen_ghi_so_chi_khi_doi_that(conn):
    an = ND.tao(conn, "an", MK)
    ND.dat_quyen(conn, "an", kho_du_lieu=True, ngan_sach=False)   # ngân sách vốn False
    ND.dat_quyen(conn, "an", kho_du_lieu=True)                    # không đổi gì
    conn.commit()
    r = conn.execute("SELECT nguoi_dung_id, co, gia_tri_cu, gia_tri_moi, sua_boi "
                     "FROM app.nhat_ky_quyen").fetchall()
    assert r == [(an, "duoc_vao_kho_du_lieu", False, True, None)]


def test_so_quyen_chi_them_kome_app_khong_sua_khong_xoa_duoc(conn):
    r = conn.execute(
        """SELECT has_table_privilege('kome_app', 'app.nhat_ky_quyen', 'INSERT'),
                  has_table_privilege('kome_app', 'app.nhat_ky_quyen', 'UPDATE'),
                  has_table_privilege('kome_app', 'app.nhat_ky_quyen', 'DELETE'),
                  has_column_privilege('kome_ingest', 'meta.ingest_batch', 'huy_boi', 'UPDATE')""").fetchone()
    assert r == (True, False, False, True)


def test_script_cap_quyen_quan_tri(conn, capsys):
    import sys
    from kome.config import GOC
    sys.path.insert(0, str(GOC / "scripts"))
    import tao_nguoi_dung as T
    ND.tao(conn, "chu", MK)
    conn.commit()
    assert T.chay(["quyen", "chu", "--quan-tri"], conn) == 0
    assert next(n for n in ND.liet_ke(conn) if n.ten_dang_nhap == "chu").duoc_quan_tri
    assert T.chay(["quyen", "chu", "--quan-tri", "--bo-quan-tri"], conn) == 2


# ---- Dòng thời gian ----------------------------------------------------------

def _nam_loai(conn, batch):
    an = ND.tao(conn, "an", MK, salesperson_code="0104")
    _lo(conn, "A.xlsx", nap_boi=an)
    _lo(conn, "B.xlsx", huy=True, huy_boi=an)
    conn.execute("""INSERT INTO app.ngan_sach_nhat_ky (salesperson_code, thang, muc_tieu_cu,
                    muc_tieu_moi, sua_boi) VALUES ('0104', '2026-07-01', NULL, 5000000, %s)""", (an,))
    ND.dat_quyen(conn, "an", ngan_sach=True, sua_boi=an)
    _ho_so_khach(conn, batch, "T0031", "Quan Tiep Xuc")
    LH.ghi(conn, "T0031", an, "goi", "tot", "Khách đặt thêm 2 thùng")
    conn.commit()
    return an


def test_dong_thoi_gian_gom_du_nam_loai(conn, batch):
    _nam_loai(conn, batch)
    ds = NK.dong_thoi_gian(conn)
    assert {d.loai for d in ds} == {"nap", "huy", "ngan_sach", "quyen", "tiep_xuc"}
    # lô B vừa có dòng nạp vừa có dòng hoàn tác
    assert sum(1 for d in ds if d.doi_tuong == "B.xlsx") == 2
    ns = next(d for d in ds if d.loai == "ngan_sach")
    assert ns.truoc_sau == ("(chưa đặt)", "¥5,000,000")
    q = next(d for d in ds if d.loai == "quyen")
    assert q.truoc_sau == ("không", "có") and "sửa Ngân sách" in q.noi_dung
    tx = next(d for d in ds if d.loai == "tiep_xuc")
    assert tx.noi_dung == "Quan Tiep Xuc: Khách đặt thêm 2 thùng"
    assert all(d.nguoi for d in ds if d.loai != "nap" or d.doi_tuong == "A.xlsx")


def test_loc_theo_loai_va_tim(conn, batch):
    _nam_loai(conn, batch)
    assert {d.loai for d in NK.dong_thoi_gian(conn, "huy")} == {"huy"}
    assert [d.doi_tuong for d in NK.dong_thoi_gian(conn, tim="2 thùng")] == ["T0031"]
    assert [d.loai for d in NK.dong_thoi_gian(conn, tim="quan tiep")] == ["tiep_xuc"]


def test_tong_hop_30_ngay(conn, batch):
    an = _nam_loai(conn, batch)
    _lo(conn, "C.xlsx")                    # không rõ ai nạp
    th = NK.tong_hop_30_ngay(conn)
    # fixture `batch` (dựng khách) cũng là một lô nạp thật — đếm theo chính bảng
    so_lo, khong_ro = conn.execute(
        "SELECT count(*), count(*) FILTER (WHERE nap_boi IS NULL) FROM meta.ingest_batch").fetchone()
    assert th.theo_loai["nap"] == so_lo and th.theo_loai["huy"] == 1
    assert th.khong_ro_ai == khong_ro   # lô B: nap_boi NULL nhưng huy_boi có tên
    assert {d.loai for d in th.soat_lai} == {"huy", "quyen"}
    assert th.theo_nguoi[0][1] >= 4 and an


def test_man_nhat_ky_dung_2_truy_van(conn, batch, monkeypatch):
    _nam_loai(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    NK.dong_thoi_gian(conn)
    NK.tong_hop_30_ngay(conn)
    assert dem["n"] == 2


def test_csv_co_bom_va_tieu_de(conn, batch):
    _nam_loai(conn, batch)
    t = NK.csv(NK.dong_thoi_gian(conn))
    assert t.startswith("﻿thời điểm,loại,người") and "Hoàn tác lô" in t


# ---- Web ---------------------------------------------------------------------

def test_hai_trang_mo_duoc_khi_khong_co_cong(conn, batch, test_db_url):
    _nam_loai(conn, batch)
    c = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
    from tests.spa_kd import man, nguon
    t = c.get("/nhat-ky").text
    m = man(t)
    assert {d["loai"] for d in m["ds"]} >= {"nap", "huy"} and m["loai_ds"]["huy"][1] == "Hoàn tác lô"
    assert "Dòng thời gian" in nguon("he_thong", "NhatKy.tsx")
    assert c.get("/nhat-ky.csv").headers["content-type"].startswith("text/csv")
    m = man(c.get("/cai-dat").text)
    assert m["co_cong"] is False and m["duoc_sua"] is False
    assert "an" in {n["ten_dang_nhap"] for n in m["nguoi_dung"]}
    assert "chưa bật đăng nhập" in nguon("he_thong", "CaiDat.tsx")
    # không có cổng → không đổi được quyền, và KHÔNG ghi gì
    r = c.post("/cai-dat/quyen/1", data={"duoc_quan_tri": "1"})
    assert r.status_code == 303 and "loi=" in r.headers["location"]
    assert conn.execute("SELECT count(*) FROM app.nhat_ky_quyen").fetchone()[0] == 1


@pytest.fixture
def co_cong(monkeypatch, test_db_url):
    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    return lambda: TestClient(create_app(db_url=test_db_url), follow_redirects=False)


def test_khong_phai_quan_tri_thi_403(conn, co_cong):
    ND.tao(conn, "an", MK)
    b = ND.tao(conn, "binh", MK)
    conn.commit()
    c = co_cong()
    _vao(c)
    assert c.post(f"/cai-dat/quyen/{b}", data={"duoc_sua_ngan_sach": "1"}).status_code == 403
    assert not next(n for n in ND.liet_ke(conn) if n.id == b).duoc_sua_ngan_sach


def test_quan_tri_doi_quyen_nguoi_khac_va_ghi_so(conn, co_cong):
    a = ND.tao(conn, "an", MK)
    b = ND.tao(conn, "binh", MK, kho_du_lieu=True)
    conn.execute("UPDATE app.nguoi_dung SET duoc_quan_tri = true WHERE id = %s", (a,))
    conn.commit()
    c = co_cong()
    _vao(c)
    # bỏ ô kho dữ liệu, bật ô ngân sách
    r = c.post(f"/cai-dat/quyen/{b}", data={"duoc_sua_ngan_sach": "1"})
    assert r.status_code == 303 and "xong=" in r.headers["location"]
    n = next(x for x in ND.liet_ke(conn) if x.id == b)
    assert (n.duoc_vao_kho_du_lieu, n.duoc_sua_ngan_sach, n.duoc_quan_tri) == (False, True, False)
    so = conn.execute("SELECT co, gia_tri_moi, sua_boi FROM app.nhat_ky_quyen ORDER BY id").fetchall()
    assert so == [("duoc_vao_kho_du_lieu", False, a), ("duoc_sua_ngan_sach", True, a)]


def test_khong_tu_bo_quyen_quan_tri_cua_minh(conn, co_cong):
    a = ND.tao(conn, "an", MK)
    conn.execute("UPDATE app.nguoi_dung SET duoc_quan_tri = true WHERE id = %s", (a,))
    conn.commit()
    c = co_cong()
    _vao(c)
    r = c.post(f"/cai-dat/quyen/{a}", data={})
    assert "loi=" in r.headers["location"]
    assert next(x for x in ND.liet_ke(conn) if x.id == a).duoc_quan_tri


def test_hoan_tac_ghi_ten_nguoi_bam(conn, co_cong):
    a = ND.tao(conn, "an", MK, kho_du_lieu=True)
    conn.commit()
    lo = _lo(conn, "D.xlsx")
    conn.commit()
    c = co_cong()
    _vao(c)
    assert c.post(f"/undo/{lo}").status_code == 303
    r = conn.execute("SELECT undone_at IS NOT NULL, huy_boi FROM meta.ingest_batch WHERE batch_id = %s",
                     (lo,)).fetchone()
    assert r == (True, a)
