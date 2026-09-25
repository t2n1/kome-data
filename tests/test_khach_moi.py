"""Khách mới đăng ký (044): ngày đăng ký đọc từ MÃ KHÁCH `YYYYMMDD` + 4 số.

Một định nghĩa — `mart.ngay_dang_ky(mã)` — và một hàm theo khoảng,
`mart.khach_moi_khoang(tu, den)`. Mã cũ (`000000…`, mã ngắn, `009…`) không
suy được ngày nên KHÔNG BAO GIỜ là khách mới. Đơn đầu đọc qua
`mart.ban_den_moc`, nên xem tháng cũ thì "chưa mua" là chưa mua tính đến lúc đó.
"""
from datetime import date

import pytest

from kome import khoang_xem as KX
from kome import khoi_tong_quan as KTQ
from tests.test_khach_hang import _ho_so_khach, _mua_nhieu

T = 110_000


@pytest.mark.parametrize("ma, ngay", [
    ("202607150001", date(2026, 7, 15)),
    ("202402290003", date(2024, 2, 29)),     # năm nhuận
    ("202502290001", None),                  # 29/2 không có năm 2025
    ("202504310001", None),                  # 31/4 không có
    ("202613010001", None),                  # tháng 13
    ("000000009292", None),                  # mã cũ
    ("009000000001", None),                  # tài khoản nhân viên
    ("999999999999", None),
    ("9996", None),                          # mã ngắn
    ("0", None),
    ("", None),
    ("20260715000", None),                   # thiếu một số
    ("2026071500011", None),                 # thừa một số
])
def test_ngay_dang_ky_chi_doc_ma_ngay_hop_le(conn, ma, ngay):
    assert conn.execute("SELECT mart.ngay_dang_ky(%s)", (ma,)).fetchone()[0] == ngay


def test_ngay_dang_ky_null_khi_ma_null(conn):
    assert conn.execute("SELECT mart.ngay_dang_ky(NULL)").fetchone()[0] is None


def _nen(conn, batch):
    """Dữ liệu bán tới 10/8/2026 (neo Z). Khách:
    202607150001  đăng ký 15/7, mua 20/7            -> mới tháng 7, đã mua
    202607200002  đăng ký 20/7, mua lần đầu 5/8     -> mới tháng 7; xem tháng 7 = CHƯA mua
    202607250003  đăng ký 25/7, chưa bao giờ mua    -> mới tháng 7, chưa mua
                  (SAU ngày bán cuối của tháng 7 — 20/7 — như tháng kết thúc vào
                  Chủ nhật: khoảng tháng 7 dừng ở 20/7 nhưng đăng ký phải đếm tới 31/7)
    202608020001  đăng ký 2/8                        -> không thuộc tháng 7
    202507100001  đăng ký 10/7/2025                  -> năm trước
    202606100001  đăng ký 10/6/2026                  -> tháng trước
    000000001234  mã cũ, mua 20/7                    -> KHÔNG tính
    9996          mã ngắn                            -> KHÔNG tính"""
    for ma in ("202607150001", "202607200002", "202607250003", "202608020001",
               "202507100001", "202606100001", "000000001234", "9996"):
        _ho_so_khach(conn, batch, ma, f"Khach {ma}")
    _mua_nhieu(conn, batch, [
        ("202607150001", date(2026, 7, 20), T, "X"),
        ("202607200002", date(2026, 8, 5), T, "X"),
        ("000000001234", date(2026, 7, 20), T, "X"),
        ("Z", date(2025, 7, 1), T, "X"),
        ("Z", date(2026, 8, 10), T, "X"),
    ])


def test_khoi_dem_khach_moi_theo_khoang_va_moc(conn, batch):
    _nen(conn, batch)
    d = KTQ.khach_moi(conn, None, KX.ThamSo(thang="2026-07"))
    assert d["so_khach"] == 3
    assert (d["da_mua"], d["chua_mua"]) == (1, 2)
    ma = {k["ma"]: k for k in d["khach"]}
    assert set(ma) == {"202607150001", "202607200002", "202607250003"}
    # Đơn đầu 5/8 nằm SAU mốc 31/7 -> tính đến tháng 7 là chưa mua.
    assert ma["202607200002"]["lan_dau"] is None
    assert ma["202607150001"]["lan_dau"] == date(2026, 7, 20)
    assert ma["202607150001"]["doanh_thu"] == T - T // 11
    # Danh sách mới nhất trước.
    assert [k["ma"] for k in d["khach"]][0] == "202607250003"


def test_khoi_so_nam_truoc_va_thang_truoc(conn, batch):
    _nen(conn, batch)
    d = KTQ.khach_moi(conn, None, KX.ThamSo(thang="2026-07"))
    assert len(d["so_sanh"]) == 2
    nam, thang = d["so_sanh"]
    assert nam["co"] and nam["so_khach"] == 1
    assert thang["co"] and thang["so_khach"] == 1


def test_khoi_mo_lai_thang_sau_thi_da_mua(conn, batch):
    _nen(conn, batch)
    d = KTQ.khach_moi(conn, None, KX.ThamSo(thang="2026-08"))
    assert d["so_khach"] == 1 and d["khach"][0]["ma"] == "202608020001"
    # 12 tháng tới tháng 8: tháng 7 nay có 2 khách đã mua (đơn 5/8 đã ≤ mốc).
    t7 = next(t for t in d["thang"] if t["thang"] == "2026-07")
    assert (t7["so_khach"], t7["da_mua"]) == (3, 2)


def test_12_thang_ket_thuc_o_thang_cua_khoang(conn, batch):
    _nen(conn, batch)
    d = KTQ.khach_moi(conn, None, KX.ThamSo(thang="2026-07"))
    assert [t["thang"] for t in d["thang"]] == [f"{y}-{m:02d}" for y, m in
                                               [(2025, m) for m in range(8, 13)] + [(2026, m) for m in range(1, 8)]]
    t = {x["thang"]: x for x in d["thang"]}
    assert (t["2026-07"]["so_khach"], t["2026-07"]["da_mua"]) == (3, 1)
    assert t["2026-06"]["so_khach"] == 1
    assert "2026-08" not in t   # đăng ký sau mốc không lọt vào


def test_khoi_trong_khi_kho_rong(conn):
    d = KTQ.khach_moi(conn, None, None)
    assert d["so_khach"] == 0 and d["khach"] == [] and d["khoang"] is None
