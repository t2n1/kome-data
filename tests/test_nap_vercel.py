"""Nạp hằng ngày trên bản Vercel (đặc tả 2026-09-25-nap-tren-vercel-design.md).

Trên Vercel ổ đĩa là tạm: file chờ xác nhận nằm trong `meta.nap_cho` (migration 045), file
gốc KHÔNG được lưu (`archived_to` NULL). Sai nguy hiểm nhất: lô không file gốc làm hỏng chặn
nạp trùng hay hoàn tác, và quyền mới trên `meta` lỡ cho xoá sổ lịch sử `meta.ingest_batch`."""
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

from kome import nap_cho
from kome.pipeline import ingest, undo_batch

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"


def _chep(tmp_path) -> Path:
    p = tmp_path / TEN
    p.write_bytes(OK.read_bytes())
    return p


# ---- Task 1: lô không có file gốc + quyền của 045 -------------------------

def test_lo_khong_file_goc_van_chan_nap_trung_va_hoan_tac_duoc(conn, tmp_path):
    p = _chep(tmp_path)
    kq = ingest(conn, p, None)
    assert kq.ok and kq.batch_id and not kq.skipped
    assert conn.execute("SELECT archived_to FROM meta.ingest_batch WHERE batch_id = %s",
                        (kq.batch_id,)).fetchone()[0] is None
    # Mã băm vẫn ghi — nạp lại cùng file bị bỏ qua, không thành hai lô.
    assert ingest(conn, p, None).skipped
    assert undo_batch(conn, kq.batch_id) > 0
    assert conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0] == 0


def test_quyen_045_chi_xoa_duoc_file_cho_khong_xoa_duoc_so_lich_su(conn):
    """[CRITICAL] kome_ingest được DELETE đúng meta.nap_cho — sổ meta.ingest_batch vẫn
    không xoá được (hoàn tác chỉ đặt undone_at). kome_app không chạm được file chờ."""
    r = conn.execute(
        """SELECT has_table_privilege('kome_ingest', 'meta.nap_cho', 'INSERT'),
                  has_table_privilege('kome_ingest', 'meta.nap_cho', 'SELECT'),
                  has_table_privilege('kome_ingest', 'meta.nap_cho', 'DELETE'),
                  has_table_privilege('kome_ingest', 'meta.ingest_batch', 'DELETE'),
                  has_table_privilege('kome_app', 'meta.nap_cho', 'SELECT'),
                  has_table_privilege('kome_report', 'meta.nap_cho', 'SELECT')""").fetchone()
    assert r == (True, True, True, False, False, False)


# ---- Task 2: kho file chờ trong CSDL + luồng hai bước trên Vercel ---------

import pytest
from fastapi.testclient import TestClient

from kome.db import connect
from kome.web.app import create_app
from tests.spa_kd import kd, man


@pytest.fixture
def kho(conn, test_db_url, tmp_path, monkeypatch):
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    return nap_cho.KhoCsdl(lambda: connect(test_db_url))


def _dem_cho(conn):
    conn.rollback()
    return conn.execute("SELECT count(*) FROM meta.nap_cho").fetchone()[0]


def test_kho_csdl_luu_doc_xoa(kho, conn):
    ma, duong = kho.luu(BytesIO(OK.read_bytes()), "../../" + TEN, "ton")
    assert duong.name == TEN and duong.read_bytes() == OK.read_bytes()
    f, meta = kho.doc(ma)
    assert f.name == TEN and f.read_bytes() == OK.read_bytes() and meta["o"] == "ton"
    ds = kho.danh_sach()
    assert [d["ma"] for d in ds] == [ma] and "noi_dung" not in ds[0]
    kho.xoa(ma)
    assert kho.doc(ma) is None and _dem_cho(conn) == 0


def test_kho_csdl_ma_sai_dang_khong_cham_csdl(kho):
    assert kho.doc("../../etc") is None and kho.doc("") is None
    kho.xoa("x' OR '1'='1")          # không nổ, không xoá gì


def test_kho_csdl_don_cu_chi_xoa_dong_qua_24_gio(kho, conn):
    cu, _ = kho.luu(BytesIO(b"a"), TEN, "")
    moi, _ = kho.luu(BytesIO(b"b"), TEN, "")
    conn.execute("UPDATE meta.nap_cho SET luc = now() - interval '25 hours' WHERE ma = %s", (cu,))
    conn.commit()
    kho.don_cu()
    assert [d["ma"] for d in kho.danh_sach()] == [moi]


def test_kieu_kho_mac_dinh(monkeypatch):
    monkeypatch.delenv("KOME_KHO_NAP", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    assert nap_cho.kieu_mac_dinh() == "dia"
    monkeypatch.setenv("VERCEL", "1")
    assert nap_cho.kieu_mac_dinh() == "csdl"
    monkeypatch.setenv("KOME_KHO_NAP", "dia")
    assert nap_cho.kieu_mac_dinh() == "dia"


@pytest.fixture
def web(conn, test_db_url, tmp_path, monkeypatch):
    """Bản 'Vercel' giả: file chờ trong CSDL, không có cổng đăng nhập (conftest)."""
    monkeypatch.setenv("KOME_KHO_NAP", "csdl")
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    return TestClient(create_app(db_url=test_db_url))


def _kiem(c, o="ton"):
    with OK.open("rb") as fh:
        r = c.post("/upload/kiem", data={"o": o}, files={"files": (TEN, fh)})
    assert r.status_code == 200
    return man(r.text)


def test_hai_buoc_voi_file_cho_trong_csdl(web, conn, tmp_path):
    m = _kiem(web)
    ma = m["kiem"][0]["ma"]
    assert ma and m["cho"][0]["ma"] == ma and _dem_cho(conn) == 1
    kq = man(web.post("/upload/xac-nhan", data={"ma": [ma]}).text)["results"][0]
    assert kq["ok"] and kq["batch_id"]
    assert _dem_cho(conn) == 0
    assert conn.execute("SELECT archived_to FROM meta.ingest_batch").fetchone()[0] is None
    assert not (tmp_path / "kho").exists()          # không một byte nào xuống ổ đĩa lưu trữ


def test_huy_va_tha_nham_o_khong_de_lai_dong_cho(web, conn):
    ma = _kiem(web)["kiem"][0]["ma"]
    web.post("/upload/huy", data={"ma": [ma]}, follow_redirects=False)
    assert _dem_cho(conn) == 0
    assert _kiem(web, o="ban")["kiem"][0]["ma"] is None
    assert _dem_cho(conn) == 0


def test_vercel_nap_duoc_tru_khi_KOME_CHI_DOC(conn, test_db_url, tmp_path, monkeypatch):
    """Chỉ-đọc thôi phụ thuộc VERCEL: bản công khai nạp được file hằng ngày; muốn một
    bản chỉ-xem thì đặt KOME_CHI_DOC=1."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    import kome.web.app as A
    assert not A._chi_doc()
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    assert A._chi_doc()


# ---- Task 3: giới hạn cỡ ở trình duyệt -----------------------------------

from tests.spa_kd import nguon


def test_gioi_han_tai_len_chi_bao_tren_vercel(conn, test_db_url, tmp_path, monkeypatch):
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    t = TestClient(create_app(db_url=test_db_url)).get("/kho-du-lieu/nap").text
    assert kd(t)["gioi_han_tai_len"] is None          # máy công ty: đối soát file 100 MB vẫn nạp được
    import kome.web.app as A
    monkeypatch.setattr(A.bao_mat, "tren_mang", lambda: True)
    # Dựng app "trên mạng" thật đòi cổng đăng nhập — kiểm hàm quyết định trực tiếp.
    assert A._gioi_han_tai_len() == A.GIOI_HAN_WEB == 4_000_000


def test_trinh_duyet_chan_file_qua_co_truoc_khi_gui():
    src = nguon("he_thong", "KhoDuLieu.tsx")
    assert "KD.gioi_han_tai_len" in src and "quá lớn cho bản web" in src
    # Ô từng loại kiểm trước requestSubmit; ô nhiều file kiểm TỔNG trong onSubmit.
    assert "quaCo(e.currentTarget.files)" in src and "onSubmit" in src
