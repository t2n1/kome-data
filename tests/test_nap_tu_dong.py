"""Nạp tự động từ obc_bot (đặc tả 2026-10-14-tu-dong-lay-obc-design.md §5).

Hai route JSON dưới /api/kho-du-lieu — cùng thân với POST /upload, cùng cổng
quyền của màn Kho dữ liệu (middleware gác theo tiền tố, không gác tay)."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import nap_cho
from kome.web.app import create_app

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"
MK = "mat-khau-obc-bot-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"


@pytest.fixture
def web(conn, test_db_url, tmp_path, monkeypatch):
    """Máy trong công ty, không cổng đăng nhập (mặc định conftest)."""
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    return TestClient(create_app(db_url=test_db_url))


def _nap(c, ten=TEN, noi_dung=None):
    return c.post("/api/kho-du-lieu/nap",
                  files=[("files", (ten, noi_dung if noi_dung is not None else OK.read_bytes()))])


def test_nap_tra_json_va_tao_lo(web, conn):
    r = _nap(web)
    assert r.status_code == 200
    k = r.json()["ket_qua"][0]
    assert k["ten_file"] == TEN and k["ok"] and not k["skipped"]
    assert k["spec_name"] == "zaiko" and k["data_date"] == "2026-09-16"
    assert k["batch_id"] and k["row_count"] > 0 and k["blockers"] == []
    assert conn.execute("SELECT count(*) FROM meta.ingest_batch").fetchone()[0] == 1


def test_nap_lai_cung_file_la_bo_qua(web):
    _nap(web)
    k = _nap(web).json()["ket_qua"][0]
    assert k["ok"] and k["skipped"] and k["batch_id"] is None


def test_ten_file_la_bi_cong_1_chan_va_noi_ra(web, conn):
    k = _nap(web, ten="khong_ro.xlsx").json()["ket_qua"][0]
    assert not k["ok"] and k["blockers"][0]["cong"] == 1 and k["blockers"][0]["loi"]
    assert conn.execute("SELECT count(*) FROM meta.ingest_batch").fetchone()[0] == 0


def test_ban_chi_doc_tra_403_json(conn, test_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")
    r = _nap(TestClient(create_app(db_url=test_db_url)))
    assert r.status_code == 403 and r.json()["loi"]


@pytest.fixture
def co_cong(conn, test_db_url, tmp_path, monkeypatch):
    """Có cổng đăng nhập; trả hàm dựng client cho một tài khoản có / không cờ."""
    from kome.web import nguoi_dung as ND
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")

    def _tao(kho_du_lieu: bool | None):
        c = TestClient(create_app(db_url=test_db_url))
        if kho_du_lieu is not None:
            ND.tao(conn, "obc-bot", MK, kho_du_lieu=kho_du_lieu)
            conn.commit()
            c.post("/dang-nhap", data={"ten": "obc-bot", "mat_khau": MK})
        return c
    return _tao


def test_chua_dang_nhap_401_json(co_cong):
    r = _nap(co_cong(None))
    assert r.status_code == 401 and r.json()["loi"]


def test_thieu_co_kho_du_lieu_403_json(co_cong):
    r = _nap(co_cong(False))
    assert r.status_code == 403 and r.json()["loi"]


def test_co_co_thi_nap_duoc_va_ghi_ai_nap(co_cong, conn):
    k = _nap(co_cong(True)).json()["ket_qua"][0]
    assert k["ok"] and k["batch_id"]
    conn.rollback()
    ai = conn.execute("""SELECT n.ten_dang_nhap FROM meta.ingest_batch b
                         JOIN app.nguoi_dung n ON n.id = b.nap_boi""").fetchone()[0]
    assert ai == "obc-bot"
