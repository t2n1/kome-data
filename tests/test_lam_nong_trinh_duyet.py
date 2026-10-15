"""Làm nóng ảnh chụp TỪ TRÌNH DUYỆT sau khi nạp tay trên Vercel (2026-10-15).

Trên Vercel `anh_chup.lam_nong` bị bỏ (luồng nền đóng băng sau khi trả lời) nên trang mở lần đầu sau mỗi lần nạp mất
3–6 s (đo thật). Sau một lần nạp CÓ lô mới, màn kết quả mang `lam_nong` = danh sách API để trình duyệt GET ngầm.
Ở máy công ty không cần (luồng nền làm). `obc_bot.web.TRANG_LAM_NONG` là bản chép bắt buộc của `DUONG_LAM_NONG`."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import nap_cho
from kome.web import anh_chup
from kome.web.app import create_app
from tests.spa_kd import man, nguon

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"


@pytest.fixture
def web(conn, test_db_url, tmp_path, monkeypatch):
    def _tao(vercel: bool):
        monkeypatch.delenv("KOME_CHI_DOC", raising=False)
        monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
        monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
        if vercel:
            monkeypatch.setenv("VERCEL", "1")
            monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-phien-du-dai-2026")
        else:
            monkeypatch.delenv("VERCEL", raising=False)
        # Vercel: cookie phiên mang cờ Secure ⇒ client phải đi https (cùng nếp tests/test_bao_mat.py).
        return TestClient(create_app(db_url=test_db_url),
                          base_url="https://testserver" if vercel else "http://testserver")
    return _tao


def _nap(c, noi_dung=None):
    return c.post("/upload", files=[("files", (TEN, noi_dung or OK.read_bytes()))])


def test_tren_vercel_nap_co_lo_moi_thi_man_mang_danh_sach_lam_nong(web, conn, monkeypatch):
    from kome.web import nguoi_dung as ND
    c = web(vercel=True)
    ND.tao(conn, "an", "mat-khau-cua-an-2026", kho_du_lieu=True)
    conn.commit()
    c.post("/dang-nhap", data={"ten": "an", "mat_khau": "mat-khau-cua-an-2026"})
    m = man(_nap(c).text)
    assert m["results"][0]["batch_id"] and m["lam_nong"] == list(anh_chup.DUONG_LAM_NONG)
    assert "lam_nong" not in man(_nap(c).text)          # nạp lại cùng file = bỏ qua, không có lô mới


def test_may_cong_ty_khong_can_lam_nong_tu_trinh_duyet(web):
    assert "lam_nong" not in man(_nap(web(vercel=False)).text)


def test_danh_sach_la_duong_api_GET_co_that():
    assert anh_chup.DUONG_LAM_NONG and all(d.startswith("/api/") for d in anh_chup.DUONG_LAM_NONG)
    assert "/api/kho-hang" in anh_chup.DUONG_LAM_NONG and "/api/tong-quan/kpi" in anh_chup.DUONG_LAM_NONG


def test_obc_bot_chep_DUNG_danh_sach_cua_web():
    from obc_bot.web import TRANG_LAM_NONG
    assert TRANG_LAM_NONG == anh_chup.DUONG_LAM_NONG


def test_giao_dien_goi_ngam_danh_sach_lam_nong():
    src = nguon("he_thong", "KhoDuLieu.tsx")
    assert "lam_nong" in src and "fetch(" in src
