"""Nạp hai bước (màn Kho dữ liệu → Nạp, đợt B 2026-09-24).

Kiểm = 5 cổng, KHÔNG ghi gì; Xác nhận = nạp đầy đủ (5 cổng chạy lại); Huỷ = xoá
file chờ. Sai nguy hiểm nhất: bước Kiểm lỡ ghi vào kho — người ta bấm Huỷ mà
dữ liệu đã nằm trong core."""
from datetime import date, datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import kho_du_lieu as KDL, nap_cho
from kome.web.app import create_app
from tests.spa_kd import kd, man, nguon

OK = Path("tests/fixtures/zaiko_ok.xlsx")
TEN = "在庫一覧_20260916.xlsx"


@pytest.fixture
def c(conn, test_db_url, tmp_path, monkeypatch):
    monkeypatch.setenv("ARCHIVE_DIR", str(tmp_path / "kho"))
    return TestClient(create_app(db_url=test_db_url))


def _dem(conn):
    return (conn.execute("SELECT count(*) FROM meta.ingest_batch").fetchone()[0],
            conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0])


def _kiem(c, o="ton", ten=TEN, f=OK):
    with f.open("rb") as fh:
        r = c.post("/upload/kiem", data={"o": o}, files={"files": (ten, fh)})
    assert r.status_code == 200
    return man(r.text)


def test_kiem_KHONG_ghi_gi_vao_kho(c, conn, tmp_path):
    """[IMPORTANT] Bước Kiểm chạy đủ 5 cổng mà không một dòng nào vào core/meta."""
    truoc = _dem(conn)
    m = _kiem(c)
    conn.rollback()
    assert _dem(conn) == truoc
    k = m["kiem"][0]
    assert k["ok"] and k["ma"] and k["row_count"] > 0 and k["bang"] == "core.fact_inventory_daily"
    assert [x["so"] for x in k["cong"]] == [1, 2, 3, 4, 5]
    assert all(x["trang_thai"] in ("dat", "canh") for x in k["cong"])
    # File nằm trong thư mục chờ, chưa vào kho lưu trữ.
    assert nap_cho.doc(tmp_path / "kho", k["ma"]) is not None
    assert m["cho"] and m["cho"][0]["ma"] == k["ma"]


def test_xac_nhan_nap_day_du_va_xoa_file_cho(c, conn, tmp_path):
    ma = _kiem(c)["kiem"][0]["ma"]
    r = c.post("/upload/xac-nhan", data={"ma": [ma]})
    assert r.status_code == 200
    m = man(r.text)
    kq = m["results"][0]
    assert kq["ok"] and kq["batch_id"] and not kq["skipped"]
    conn.rollback()
    lo, dong = _dem(conn)
    assert lo == 1 and dong == kq["row_count"]
    assert nap_cho.doc(tmp_path / "kho", ma) is None and m["cho"] == []
    # Bấm Xác nhận lần nữa (F5, bấm đúp): không nạp hai lần.
    kq2 = man(c.post("/upload/xac-nhan", data={"ma": [ma]}).text)["results"][0]
    assert not kq2["ok"] and "không còn" in kq2["blockers"][0]["message"]


def test_huy_xoa_file_cho_khong_nap(c, conn, tmp_path):
    ma = _kiem(c)["kiem"][0]["ma"]
    r = c.post("/upload/huy", data={"ma": [ma]}, follow_redirects=False)
    assert r.status_code == 303 and r.headers["location"] == "/kho-du-lieu/nap"
    assert nap_cho.doc(tmp_path / "kho", ma) is None
    conn.rollback()
    assert _dem(conn) == (0, 0)


def test_tha_nham_o_bi_chan_khong_kiem(c, conn):
    k = _kiem(c, o="ban")["kiem"][0]
    assert not k["ok"] and k["ma"] is None
    assert "không phải ô Bán hàng" in k["blockers"][0]["message"]
    assert k["cong"][0]["trang_thai"] == "chan"
    assert all(x["trang_thai"] == "khong_chay" for x in k["cong"][1:])


def test_file_bi_chan_khong_de_lai_file_cho(c, tmp_path):
    k = _kiem(c, f=Path("tests/fixtures/zaiko_thieu_cot.xlsx"))["kiem"][0]
    assert not k["ok"] and k["ma"] is None
    assert k["cong"][1]["trang_thai"] == "chan"            # cổng 2: thiếu cột
    assert nap_cho.danh_sach(tmp_path / "kho") == []


def test_o_nhieu_file_tu_nhan_loai(c):
    k = _kiem(c, o="")["kiem"][0]
    assert k["ok"] and k["spec_name"] == "zaiko"


def test_ma_cho_la_khong_duoc_cham_ngoai_thu_muc(tmp_path):
    """Mã chờ ghép vào đường dẫn — chuỗi lạ không được thoát khỏi thư mục chờ."""
    (tmp_path / "bi_mat.txt").write_text("x")
    for ma in ("../bi_mat.txt", "..", "", "A" * 32, "0" * 31):
        assert nap_cho.doc(tmp_path, ma) is None
        nap_cho.xoa(tmp_path, ma)
    assert (tmp_path / "bi_mat.txt").exists()
    assert nap_cho.ten_an_toan("../../x/在庫一覧_20260916.xlsx") == "在庫一覧_20260916.xlsx"
    assert nap_cho.ten_an_toan("..\\..\\a.xlsx") == "a.xlsx"


def test_ban_chi_doc_tu_choi_ca_ba(conn, test_db_url, monkeypatch):
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    c = TestClient(create_app(db_url=test_db_url))
    with OK.open("rb") as fh:
        assert c.post("/upload/kiem", files={"files": (TEN, fh)}).status_code == 403
    assert c.post("/upload/xac-nhan", data={"ma": ["0" * 32]}).status_code == 403
    assert c.post("/upload/huy", data={"ma": ["0" * 32]}).status_code == 403


def test_man_nap_va_duong_dan_cu(c):
    r = c.get("/kho-du-lieu/nap")
    assert r.status_code == 200
    m = man(r.text)
    assert [n["ma"] for n in m["nguon"]] == [o["ma"] for o in KDL.O_NAP if o["ma"] in KDL.MA_DUNG]
    assert "lo" in m and m["cho"] == []
    assert c.get("/nap", follow_redirects=False).headers["location"] == "/kho-du-lieu/nap"
    src = nguon("he_thong", "KhoDuLieu.tsx")
    assert 'action="/upload/kiem"' in src and 'action="/upload/xac-nhan"' in src and 'action="/upload/huy"' in src


# ---- Hàm thuần -------------------------------------------------------------

class _T:
    def __init__(self, spec, tt, ngay=None, tre=None):
        self.spec, self.trang_thai, self.ngay, self.tre = spec, tt, ngay, tre


class _Tuoi:
    def __init__(self, *nguon):
        self.nguon = list(nguon)


def test_nut_nguon_file_nen_khong_bao_gio_do():
    hom_nay = date(2026, 9, 24)
    status = [{"spec": "shohin", "last": datetime(2026, 9, 1, tzinfo=timezone.utc), "data_date": None},
              {"spec": "zaiko", "last": None, "data_date": None}]
    nut = {n["ma"]: n for n in KDL.nut_nguon(status, _Tuoi(_T("zaiko", "do", date(2026, 9, 18), 4)), hom_nay)}
    assert nut["sp"]["mau"] == "nen" and "23 ngày trước" in nut["sp"]["cau"]
    assert nut["ton"]["mau"] == "do" and "trễ 4 ngày làm việc" in nut["ton"]["cau"]
    assert nut["giao"]["mau"] == "nen" and nut["giao"]["cau"] == "chưa nạp lần nào"
    assert not {"ncc", "gia", "no"} & set(nut), "nguồn chưa dùng (kome/nguon_dung.py) không có nút"


def test_nap_hom_nay_tinh_theo_gio_tokyo():
    """08:00 sáng Nhật ngày 24 = 23:00 UTC ngày 23 — vẫn là "nạp hôm nay"."""
    status = [{"spec": "shohin", "last": datetime(2026, 9, 23, 23, 0, tzinfo=timezone.utc), "data_date": None}]
    nut = {n["ma"]: n for n in KDL.nut_nguon(status, _Tuoi(), date(2026, 9, 24))}
    assert nut["sp"]["nap_hom_nay"] is True


def test_tong_quan_co_du_khoi(c):
    """`?ngay_thang=` (không phải `?thang=` — khoảng xem chung) chỉ chọn sẵn tháng
    của khối từng ngày; mọi ngày của mọi tháng đã đi cùng lưới. Rác thì bỏ qua."""
    m = man(c.get("/kho-du-lieu?ngay_thang=2026-08").text)
    assert m["ngay_thang"] == "2026-08"
    assert "2026-08" in [t["thang"] for t in m["phu"]["thang"]]
    assert len(m["nguon"]) == len(KDL.O_DUNG)
    assert man(c.get("/kho-du-lieu?ngay_thang=rac").text)["ngay_thang"] is None
    assert kd(c.get("/kho-du-lieu").text)["tuoi"]["nguon"]