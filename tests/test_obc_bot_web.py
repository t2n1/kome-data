"""obc_bot.web gọi THẲNG web app thật qua TestClient (cùng giao diện .get/.post
với requests.Session) — chứng minh đầu-cuối: đăng nhập -> hôm nay -> nạp."""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import nap_cho
from kome.web.app import create_app
from obc_bot.web import KhachWeb, LoiWeb

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"
MK = "mat-khau-obc-bot-2026"


@pytest.fixture
def khach(conn, test_db_url, tmp_path, monkeypatch):
    from kome.web import nguoi_dung as ND
    monkeypatch.delenv("KOME_CHI_DOC", raising=False)
    monkeypatch.setenv("KOME_SESSION_SECRET", "bi-mat-phien-du-dai-2026")
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    monkeypatch.setattr(nap_cho, "THU_MUC_TAM", tmp_path / "tam")

    def _tao(kho_du_lieu=True):
        ND.tao(conn, "obc-bot", MK, kho_du_lieu=kho_du_lieu)
        conn.commit()
        return KhachWeb("http://testserver", phien=TestClient(create_app(db_url=test_db_url)))
    return _tao


def _file(tmp_path) -> Path:
    p = tmp_path / TEN
    p.write_bytes(OK.read_bytes())
    return p


def test_dang_nhap_hom_nay_nap(khach, tmp_path):
    w = khach()
    w.dang_nhap("obc-bot", MK)
    assert set(w.hom_nay()["da_co"]) == {"ban", "ton", "khach"}
    k = w.nap([_file(tmp_path)])[0]
    assert k["ok"] and k["spec_name"] == "zaiko" and k["batch_id"]


def test_sai_mat_khau_noi_ro(khach):
    with pytest.raises(LoiWeb, match="mật khẩu"):
        khach().dang_nhap("obc-bot", "sai")


def test_chua_dang_nhap_noi_ro(khach, tmp_path):
    with pytest.raises(LoiWeb, match="đăng nhập"):
        khach().nap([_file(tmp_path)])


def test_thieu_co_kho_du_lieu_noi_ro(khach, tmp_path):
    w = khach(kho_du_lieu=False)
    w.dang_nhap("obc-bot", MK)
    with pytest.raises(LoiWeb, match="từ chối"):
        w.nap([_file(tmp_path)])


class _PhienHong:
    def get(self, *a, **k):
        raise ConnectionError("down")

    post = get


def test_loi_mang_thanh_LoiWeb(tmp_path):
    w = KhachWeb("http://x", phien=_PhienHong())
    f = _file(tmp_path)
    for goi in (lambda: w.dang_nhap("a", "b"), w.hom_nay, lambda: w.nap([f])):
        with pytest.raises(LoiWeb, match="Không kết nối"):
            goi()


def test_file_khong_doc_duoc_thanh_LoiWeb(khach, tmp_path):
    w = khach()
    with pytest.raises(LoiWeb, match="Không đọc được file"):
        w.nap([tmp_path / "khong_co.xlsx"])
