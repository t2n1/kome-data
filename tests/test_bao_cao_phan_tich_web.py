"""Đợt 5b Task 4 — bảy khối phân tích mới hiển thị trên `/bao-cao`, cộng
token màu CSS mới.

Không kiểm lại công thức (đã có `tests/test_phan_tich_mart.py` và
`tests/test_bao_cao_phan_tich.py`) — chỉ kiểm trang RENDER đúng, chữ bắt
buộc hiện đúng điều kiện, và không có mã màu hex nào lọt vào template.
"""
import re
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome.bao_cao import tinh_bao_cao, NGANH_TRONG, nhom_theo_nganh
from kome.web.app import create_app

TEMPLATE = (Path(__file__).resolve().parent.parent
            / "kome" / "web" / "templates" / "bao_cao.html")


@pytest.fixture
def client(conn, test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def _ban(conn, batch, ngay: date, ma_hang: str, khach="000000009292",
         amount=110_000, tax=10_000, gp=30_000, sale="0104", n=1):
    """Một dòng bán thật qua loader, không SQL tay — cùng nếp
    tests/test_bao_cao_phan_tich.py."""
    from kome.loaders import sales
    b = batch(abs(hash((ngay, ma_hang, khach, amount, tax, sale, n))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{khach[-4:]}{ma_hang}{n}", "line_seq": 1,
        "sales_date": ngay, "customer_code": khach, "product_code": ma_hang,
        "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
        "unit_cost": 3210, "amount": amount, "tax_amount": tax,
        "cost": amount - tax - gp, "gross_profit": gp, "paid_amount": 0,
        "salesperson_code": sale, "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _nganh(conn, batch, ma_hang: str, ten_nganh: str):
    b = batch(abs(hash(("nganh", ma_hang))) % 40_000 + 300_000)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, food_category_name, batch_id)
           VALUES (%s, %s, %s, %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma_hang, f"Hàng {ma_hang}", ten_nganh, b))
    conn.commit()


def _hai_nam(conn, batch, ma="AA01", ngành="Đồ khô"):
    """Hai năm dữ liệu đủ để có tháng đối chiếu — kỳ 2025 (2024-08..2025-07)
    và kỳ 2026 (2025-08..2026-07), cùng mã/ngành mỗi tháng."""
    _nganh(conn, batch, ma, ngành)
    n = 0
    for nam, thang_bd in ((2024, 8), (2025, 8)):
        for i in range(12):
            th = (thang_bd - 1 + i) % 12 + 1
            y = nam + (thang_bd - 1 + i) // 12
            n += 1
            _ban(conn, batch, date(y, th, 11), ma, amount=110_000, tax=10_000,
                 gp=30_000, n=n)


def test_kho_rong_tra_200(client, conn):
    r = client.get("/bao-cao")
    assert r.status_code == 200


def test_kho_hai_nam_tra_200_va_hien_khoi_moi(client, conn, batch):
    _hai_nam(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    for tieu_de in ("Ngành hàng kéo doanh thu lên/xuống",
                    "Doanh thu đến từ danh mục nào",
                    "Tăng trưởng theo tháng và ngành",
                    "Doanh thu tập trung ở khách nào"):
        assert tieu_de in r.text


def test_co_doi_chieu_hien_dung_cau(client, conn, batch):
    """[Chữ bắt buộc] Ô chỉ số khi có đối chiếu: 'so cùng kỳ · {n} tháng đối
    chiếu ({tu} → {den})'."""
    _hai_nam(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    assert "so cùng kỳ · " in r.text
    assert "tháng đối chiếu (" in r.text
    assert "2025-08 → 2026-07" in r.text or "→ 2026-07)" in r.text


def test_khong_co_doi_chieu_hien_dung_cau(client, conn, batch):
    """[Chữ bắt buộc] Không có tháng đối chiếu: 'chưa có cùng kỳ để so'."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _ban(conn, batch, date(2026, 5, 11), "AA01")
    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    assert "chưa có cùng kỳ để so" in r.text
    # Khối "Ngành hàng kéo doanh thu lên/xuống" cũng phải nói ra, KHÔNG ẩn
    # tiêu đề.
    assert "Ngành hàng kéo doanh thu lên/xuống" in r.text
    assert "không có tháng nào để so cùng kỳ" in r.text


def test_ty_suat_so_bang_diem_khong_bang_phan_tram(client, conn, batch):
    """Tỷ suất so cùng kỳ dùng chữ 'điểm', không phải '%'."""
    _hai_nam(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    assert "điểm" in r.text
    assert "% điểm" not in r.text, "tỷ suất phải so bằng ĐIỂM, không phải %"


def test_nganh_trong_khop_chu_view_tra_ra(conn, batch):
    """[CRITICAL] NGANH_TRONG là CHỖ THỨ HAI viết nhãn '(chưa phân loại)' —
    phải khớp TỪNG CHỮ với biểu thức của mart.ban_theo_nganh_thang (029
    §3.1). Mã hàng KHÔNG có trong core.dim_product (LEFT JOIN -> NULL) phải
    rơi vào đúng MỘT ô '(chưa phân loại)' sau khi nhom_theo_nganh gộp lại,
    không tách thành hai ô khác nhãn."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _ban(conn, batch, date(2026, 5, 11), "AA01")
    # CC01 không có dòng nào trong core.dim_product -> food_category_name NULL.
    _ban(conn, batch, date(2026, 5, 12), "CC01", khach="000000009293", n=99)

    bc = tinh_bao_cao(conn, 2026)
    dong_view = conn.execute(
        """SELECT nganh FROM mart.ban_theo_nganh_thang
           WHERE thang = '2026-05' AND nganh NOT IN ('Đồ khô')""").fetchall()
    assert dong_view, "cần có dòng cho mã CC01 không phân loại"
    assert dong_view[0][0] == NGANH_TRONG

    nganh_trong = [nk for nk in bc.nganh_ky if nk.nganh == NGANH_TRONG]
    assert len(nganh_trong) == 1, "phải gộp về đúng MỘT ngành '(chưa phân loại)'"

    nhom = nhom_theo_nganh(bc.nganh_ky, bc.hang_theo_nganh)
    dong_trong = next(t for t in nhom if t[0] == NGANH_TRONG)
    ma_trong = [ma for ma, _ten, _dt in dong_trong[3]]
    assert "CC01" in ma_trong


def test_khong_ve_hien_dung_cau_khi_co_doanh_thu_am(client, conn, batch):
    """[Chữ bắt buộc, phán quyết controller] Ngành có TỔNG ÂM (không chỉ mã
    lẻ âm) cũng phải rơi vào 'Không vẽ' — chữ chính xác đã chốt:
    'Không vẽ: ¥{khong_ve:,} của {so_ma_khong_ve} mã (doanh thu âm hoặc
    bằng 0, hoặc thuộc ngành có tổng âm)'."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _ban(conn, batch, date(2026, 5, 11), "AA01")
    _nganh(conn, batch, "PH01", "Phí")
    _ban(conn, batch, date(2026, 5, 11), "PH01", khach="000000009294",
         amount=-5_000, tax=-500, gp=-1_000, n=77)

    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    assert ("mã (doanh thu âm hoặc bằng 0, hoặc thuộc ngành có tổng âm)"
            in r.text)
    assert "Không vẽ: ¥" in r.text


def test_khong_hien_khong_ve_khi_khong_co_am(client, conn, batch):
    _hai_nam(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    assert "Không vẽ:" not in r.text


def test_pareto_cau_tom_tat(client, conn, batch):
    """[Chữ bắt buộc] '{10} khách lớn nhất = {x}% doanh thu kỳ này, trên
    {so_khach} khách có doanh thu'."""
    for i in range(12):
        khach = f"00000000{9300 + i}"
        _ban(conn, batch, date(2026, 5, 11), "AA01", khach=khach,
             amount=(110_000 + i * 1_000), tax=10_000, gp=30_000, n=i)
    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    assert "10 khách lớn nhất = " in r.text
    assert "% doanh thu kỳ này, trên 12 khách có doanh thu" in r.text


def test_nhiet_chu_giai_co_khong_co_cung_ky(client, conn, batch):
    """[Chữ bắt buộc] Chú giải bản đồ nhiệt có 'không có cùng kỳ'."""
    _hai_nam(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    assert "không có cùng kỳ" in r.text


def test_khong_co_ma_mau_hex_trong_template():
    html = TEMPLATE.read_text(encoding="utf-8")
    # Loại trừ &#... (thực thể HTML) và href="#..." (neo trong trang).
    loc = re.sub(r"&#\w+;", "", html)
    loc = re.sub(r'href="#[^"]*"', "", loc)
    xau = re.findall(r"#[0-9a-fA-F]{3,8}\b", loc)
    assert xau == [], f"mã màu hex lọt vào template: {xau}"


def test_moi_rect_circle_du_lieu_co_title(client, conn, batch):
    """Mọi <rect>/<circle> DỮ LIỆU trong các SVG mới (đóng góp, cây ô, bản đồ
    nhiệt, Pareto) phải có <title> ghi số thật — cách duy nhất có 'tooltip'
    khi trang không dùng JavaScript nào."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _hai_nam(conn, batch)
    _nganh(conn, batch, "PH01", "Phí")
    _ban(conn, batch, date(2026, 5, 11), "PH01", khach="000000009294",
         amount=-5_000, tax=-500, gp=-1_000, n=77)
    for i in range(12):
        khach = f"00000000{9300 + i}"
        _ban(conn, batch, date(2026, 5, 20), "AA01", khach=khach,
             amount=(50_000 + i * 1_000), tax=5_000, gp=15_000, n=200 + i)

    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    html = r.text
    # Bốn SVG mới của spec §4.2: đóng góp, cây ô, bản đồ nhiệt, Pareto — tìm
    # bằng chính aria-label của mỗi svg rồi kiểm RIÊNG bên trong từng khối
    # (sparkline của ô chỉ số là trang trí, aria-hidden, không tính).
    nhan = ("Chênh lệch doanh thu theo ngành so cùng kỳ",
            "Doanh thu theo ngành hàng và mặt hàng",
            "Tăng trưởng doanh thu theo tháng và ngành",
            "Doanh thu và luỹ kế của 20 khách hàng lớn nhất")
    for n in nhan:
        m_svg = re.search(rf'aria-label="{re.escape(n)}">(.*?)</svg>', html, re.S)
        assert m_svg, f"không tìm thấy SVG '{n}'"
        khoi = m_svg.group(1)
        for tag in ("rect", "circle"):
            for m in re.finditer(rf"<{tag}\b[^>]*>((?:(?!</{tag}>).)*)</{tag}>", khoi, re.S):
                assert "<title>" in m.group(1), \
                    f"<{tag}> trong '{n}' không có <title>: {m.group(0)[:120]!r}"


def test_hai_khoi_mau_toi_trong_css_van_xanh():
    """[CLAUDE.md] Token màu mới (--nhiet-*, --duong-ck) phải thêm vào CẢ HAI
    khối tối và giữ chúng GIỐNG HỆT nhau — chạy lại chính test canh có sẵn."""
    from tests.test_giao_dien import test_hai_khoi_mau_toi_trong_css_GIONG_HET_NHAU as t
    t()


def test_ba_khoi_ngan_sach_5a_va_bang_nhan_vien_con_nguyen(client, conn, batch):
    """Bộ test 5a hiện có phải xanh nguyên — kiểm nhanh các khối đó vẫn còn
    mặt trên trang."""
    _ban(conn, batch, date(2026, 7, 31), "XT07", sale="0104")
    conn.execute(
        "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
        "VALUES (%s, %s, %s)", ("0104", date(2026, 7, 1), 6_000_000))
    conn.commit()
    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    assert "Tiến độ ngân sách" in r.text
    assert "Luỹ kế thực tế so với nhịp ngân sách" in r.text
    assert "Kết quả theo từng nhân viên" in r.text
    assert "Theo người phụ trách khách" in r.text


def test_bang_chi_tiet_theo_thang_dong_trong_details(client, conn, batch):
    _hai_nam(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    assert "<details>" in r.text
    assert "Bảng số chi tiết theo tháng" in r.text
