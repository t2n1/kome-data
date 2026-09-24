"""Bảng điều khiển báo cáo — và các định nghĩa chỉ số ở schema `mart`.

Mỗi test ở đây canh một cách hiểu SAI về con số mà nếu lọt thì báo cáo vẫn
hiện ra bình thường, chỉ là nói sai. Đó là loại lỗi tệ nhất trong hệ thống
này: không ai thấy nó, và người ta ra quyết định dựa trên nó.
"""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from kome.bao_cao import tinh_bao_cao, ve_bieu_do


def _ban(conn, batch, ngay: date, amount, tax, gp, khach="000000009292", n=1):
    """Một dòng bán thật qua loader, không SQL tay."""
    from kome.loaders import sales
    b = batch(abs(hash((ngay, khach, amount))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{n}", "line_seq": 1, "sales_date": ngay,
        "customer_code": khach, "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": amount, "tax_amount": tax, "cost": amount - tax - gp,
        "gross_profit": gp, "paid_amount": 0, "batch_id": b,
    }]), ngay, b)
    conn.commit()
    return b


def test_doanh_thu_thuan_TRU_thue_khong_lay_thang_amount(conn, batch):
    """[CRITICAL] `amount` của OBC ĐÃ GỒM thuế tiêu dùng. Lấy thẳng nó làm
    doanh thu thì tỷ suất lãi gộp tụt xuống một cách vô cớ, và cả công ty đi
    truy một vấn đề không tồn tại."""
    _ban(conn, batch, date(2026, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    bc = tinh_bao_cao(conn)
    assert bc.ky.doanh_thu == 100_000, "phải là amount - tax_amount"
    assert bc.ky.lai_gop == 30_000
    assert bc.ky.ty_suat == pytest.approx(0.30)


def test_phieu_do_KHONG_bi_loc_bo(conn, batch):
    """[CRITICAL] 赤伝 (hàng trả lại) mang số ÂM. Lọc bỏ là báo cáo đẹp hơn
    thực tế — và nó nói dối nhiều nhất đúng lúc hàng bị trả về nhiều nhất."""
    _ban(conn, batch, date(2026, 5, 11), amount=220_000, tax=20_000, gp=60_000)
    _ban(conn, batch, date(2026, 5, 12), amount=-110_000, tax=-10_000, gp=-30_000, n=2)
    bc = tinh_bao_cao(conn)
    assert bc.ky.doanh_thu == 100_000, "doanh thu phải bị hàng trả lại kéo xuống"
    assert bc.ky.lai_gop == 30_000


def test_thang_khong_co_ky_truoc_phai_noi_KHONG_CO_khong_phai_0(conn, batch):
    """[IMPORTANT] Đặc tả §2.2.1: dữ liệu bán bắt đầu 2025-03-03, trước đó
    KHÔNG TỒN TẠI. Tháng không có tháng đối chiếu mà hiện 0% hoặc để trống thì
    người đọc hiểu thành "doanh thu sụt 100%"."""
    _ban(conn, batch, date(2026, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    bc = tinh_bao_cao(conn)
    t = next(o for o in bc.thang if o.thang == "2026-05")
    assert t.co_cung_ky is False
    assert t.tang_truong is None
    assert any("cùng kỳ" in c for c in bc.canh_bao)


def test_co_ky_truoc_thi_tinh_tang_truong(conn, batch):
    _ban(conn, batch, date(2025, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 5, 11), amount=220_000, tax=20_000, gp=60_000, n=2)
    bc = tinh_bao_cao(conn)                      # kỳ gần nhất = 2026
    t = next(o for o in bc.thang if o.thang == "2026-05")
    assert t.co_cung_ky is True
    assert t.tang_truong == pytest.approx(1.0)   # 100.000 -> 200.000


def test_ky_khong_du_12_thang_phai_canh_bao(conn, batch):
    """Kỳ 6 chỉ có 5 tháng trong phạm vi dữ liệu. Đem tổng kỳ đó so với kỳ đủ
    12 tháng là so 5 với 12 — và con số nào cũng "tăng trưởng" ngoạn mục."""
    _ban(conn, batch, date(2026, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    bc = tinh_bao_cao(conn)
    assert bc.ky.du_12_thang is False
    assert any("12 tháng" in c for c in bc.canh_bao)


def test_ty_suat_None_khi_chua_co_doanh_thu(conn):
    """Chưa có dữ liệu thì tỷ suất là None để màn hình nói "chưa có số".
    Hiện 0% sẽ bị đọc thành "bán mà không lãi đồng nào"."""
    bc = tinh_bao_cao(conn)
    assert bc.khong_co_du_lieu is True
    assert bc.ky.ty_suat is None
    assert bc.thang == [] and bc.tap_trung is None


def test_chon_dung_ky_qua_tham_so(conn, batch):
    _ban(conn, batch, date(2025, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 5, 11), amount=220_000, tax=20_000, gp=60_000, n=2)
    assert tinh_bao_cao(conn).ky.company_fy == 2026            # mặc định: gần nhất
    assert tinh_bao_cao(conn, 2025).ky.company_fy == 2025
    # Kỳ không tồn tại thì rơi về kỳ gần nhất, không nổ.
    assert tinh_bao_cao(conn, 1999).ky.company_fy == 2026


def test_nhan_ky_dung_so_ky_cong_ty_goi(conn, batch):
    """Ban giám đốc gọi nhau bằng "kỳ 7", không phải "kỳ 2026"."""
    _ban(conn, batch, date(2026, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    bc = tinh_bao_cao(conn)
    assert bc.ky.so_ky == 7
    assert bc.ky.nhan == "Kỳ 7 (2025-08 → 2026-07)"


def test_truc_ty_suat_KHONG_bat_dau_tu_0(conn, batch):
    """[IMPORTANT] Tỷ suất thật dao động trong khoảng 26–38%. Vẽ trục từ 0%
    thì đường gần như phẳng và giấu mất đúng thứ người ta mở trang để nhìn."""
    for thang, gp in ((3, 38_000), (4, 30_000), (5, 26_000)):
        _ban(conn, batch, date(2026, thang, 11), amount=110_000, tax=10_000,
             gp=gp, n=thang)
    bd = ve_bieu_do(tinh_bao_cao(conn).thang)
    assert bd["ts_lo"] > 0.10, "trục phải bám sát vùng số thật"
    assert bd["ts_lo"] < 0.26 < 0.38 < bd["ts_hi"], "phải bao trọn vùng số thật"
    assert len(bd["cot"]) == 3 and len(bd["diem"]) == 3


def test_bieu_do_rong_khong_no(conn):
    assert ve_bieu_do([]) == {"co": False}


def test_module_khong_tu_mo_ket_noi():
    """tinh_bao_cao() nhận sẵn kết nối. Hàm nào tự gọi connect() không tham số
    sẽ âm thầm đọc CSDL THẬT khi trang chạy với create_app(db_url=…)."""
    import ast
    import inspect

    import kome.bao_cao as B

    # Đọc bằng ast chứ không tìm chuỗi: chính ghi chú đầu file cũng nhắc tên
    # connect(), và một test bắt cả ghi chú thì đỏ vì lý do vô nghĩa.
    cay = ast.parse(inspect.getsource(B))
    goi = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    ten = {n.id for n in ast.walk(cay) if isinstance(n, ast.Name)}
    assert "connect" not in goi, "module không được tự mở kết nối"
    assert "DATABASE_URL" not in {c.value for c in ast.walk(cay)
                                  if isinstance(c, ast.Constant) and isinstance(c.value, str)}
    assert "os" not in ten, "không đọc biến môi trường ở đây"
    assert list(inspect.signature(B.tinh_bao_cao).parameters)[0] == "conn"


def test_dinh_nghia_chi_so_nam_o_mart_khong_o_python():
    """[IMPORTANT] CLAUDE.md: "Định nghĩa chỉ số ở chỗ khác ngoài `mart/`" nằm
    trong mục KHÔNG ĐƯỢC TỰ Ý SỬA. Nếu ai đó viết lại công thức trong Python
    cho tiện, trang web và câu SQL gõ tay sẽ trả hai con số khác nhau."""
    import inspect

    import kome.bao_cao as B

    src = inspect.getsource(B)
    assert "amount - tax_amount" not in src and "tax_amount" not in src, \
        "công thức doanh thu thuần phải nằm trong mart, không chép sang Python"
    assert "sum(" not in src.lower().replace("sum(b.", ""), \
        "không tự cộng dồn trong Python — hỏi mart"


NGUON_BAO_CAO = (Path(__file__).resolve().parent.parent
                 / "giao_dien" / "src" / "bao_cao" / "BaoCao.tsx")


def test_trang_bao_cao_mo_duoc_va_hien_so(conn, batch, test_db_url):
    """Giai đoạn 3: màn là React — kiểm dữ liệu API (doanh thu THUẦN, nhãn kỳ,
    hình học biểu đồ tính sẵn ở máy chủ) và mã giao diện (SVG tự vẽ, không
    thư viện biểu đồ nào — bất biến giao diện React của CLAUDE.md)."""
    import re

    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    _ban(conn, batch, date(2026, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    c = TestClient(create_app(db_url=test_db_url))
    r = c.get("/bao-cao")
    assert r.status_code == 200 and 'id="goc"' in r.text
    # Khoảng xem mặc định = tháng hiện tại (5/2026); dạng Kỳ = màn Báo cáo cũ.
    m = c.get("/api/bao-cao").json()
    assert m["bc"]["ky"]["nhan"] == "Tháng 5/2026" and m["bc"]["ky"]["doanh_thu"] == 100_000
    d = c.get("/api/bao-cao?ky=2026").json()
    assert d["bc"]["ky"]["doanh_thu"] == 100_000     # doanh thu THUẦN, không phải 110.000
    assert d["bc"]["thang"][0]["doanh_thu"] == 100_000
    assert "Kỳ 7" in d["bc"]["ky"]["nhan"]
    assert d["bd"]["co"] is True and len(d["bd"]["cot"]) == 1   # biểu đồ vẽ được, không cần mạng
    src = NGUON_BAO_CAO.read_text(encoding="utf-8")
    assert "<svg" in src
    nguon_nhap = re.findall(r'^import .*?from "([^"]+)"', src, re.M)
    la = [n for n in nguon_nhap if not (n.startswith(".") or n in ("react", "@tanstack/react-query"))]
    assert la == [], f"màn Báo cáo nhập thư viện ngoài (biểu đồ phải tự vẽ SVG): {la}"


def test_trang_bao_cao_co_trong_thanh_dieu_huong(conn, test_db_url):
    """Mục Báo cáo có mặt trên thanh bên của trang Jinja còn lại VÀ của thanh
    bên React (giao_dien/src/khung/muc.ts) — Giai đoạn 3: /bao-cao là React."""
    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    c = TestClient(create_app(db_url=test_db_url))
    for duong in ("/health", "/phu-du-lieu", "/nhat-ky"):
        assert 'id="goc"' in c.get(duong).text, duong   # mọi trang là vỏ React
    muc = (NGUON_BAO_CAO.parent.parent / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert 'url: "/bao-cao"' in muc
