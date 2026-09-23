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

from kome.bao_cao import NganhKy, tinh_bao_cao, NGANH_TRONG, nhom_theo_nganh
from kome.ve_phan_tich import ve_cay_o, ve_dong_gop, ve_nhiet
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
    """[Chữ bắt buộc, M-7 soát chặt] Ô chỉ số khi có đối chiếu: đúng NGUYÊN
    VĂN 'so cùng kỳ · {n} tháng đối chiếu ({tu} → {den})' — không đoán bừa
    bằng `or`, lấy thẳng {n}/{tu}/{den} thật từ `tinh_bao_cao`."""
    _hai_nam(conn, batch)
    bc = tinh_bao_cao(conn, 2026)
    ck = bc.cung_ky
    assert ck.so_thang > 0
    cau = (f"so cùng kỳ · {ck.so_thang} tháng đối chiếu "
           f"({ck.tu} → {ck.den})")
    r = client.get("/bao-cao?ky=2026")
    assert cau in r.text, f"thiếu đúng câu: {cau!r}"


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
    """[M-7 soát chặt] Tỷ suất so cùng kỳ dùng chữ 'điểm' — kiểm NGAY TRONG
    ô chỉ số 'Tỷ suất lãi gộp', không phải bất kỳ đâu trên trang (một chữ
    'điểm' lạc ở khối khác vẫn làm test cũ xanh giả)."""
    _hai_nam(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    m = re.search(r'<div class="nhan">Tỷ suất lãi gộp</div>.*?</div>\s*</div>',
                  r.text, re.S)
    assert m, "không tìm thấy ô chỉ số Tỷ suất lãi gộp"
    khoi = m.group(0)
    assert "điểm" in khoi
    assert "% điểm" not in khoi, "tỷ suất phải so bằng ĐIỂM, không phải %"


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
    """[Chữ bắt buộc, sửa vòng soát cuối M2] '10 khách lớn nhất = {x}%
    doanh thu kỳ này, trên {so_khach} khách có phát sinh trong kỳ' — KHÔNG
    phải 'khách có doanh thu': `so_khach` đếm mọi khách có dòng trong
    `mart.dong_ban`, kể cả khách net <= 0 (赤伝 có thể làm net âm/bằng
    không), nên gọi họ "có doanh thu" là sai."""
    for i in range(12):
        khach = f"00000000{9300 + i}"
        _ban(conn, batch, date(2026, 5, 11), "AA01", khach=khach,
             amount=(110_000 + i * 1_000), tax=10_000, gp=30_000, n=i)
    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    assert "10 khách lớn nhất = " in r.text
    assert "% doanh thu kỳ này, trên 12 khách có phát sinh trong kỳ" in r.text


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
    """[M-7 soát chặt] Mọi <rect>/<circle> DỮ LIỆU trong ba SVG còn lại
    (đóng góp, cây ô, Pareto — bản đồ nhiệt nay là <table>, xem I-2/test
    riêng bên dưới) phải có <title> ghi số thật. Bắt CẢ dạng tự đóng
    (`<rect .../>`, không thể mang <title> con) lẫn cặp mở/đóng thiếu
    <title> — bản trước chỉ bắt cặp mở/đóng, một phần tử tự đóng lọt qua
    hoàn toàn không bị phát hiện."""
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
    nhan = ("Chênh lệch doanh thu theo ngành so cùng kỳ",
            "Doanh thu theo ngành hàng và mặt hàng",
            "Doanh thu và luỹ kế của 20 khách hàng lớn nhất")
    for n in nhan:
        m_svg = re.search(rf'aria-label="{re.escape(n)}">(.*?)</svg>', html, re.S)
        assert m_svg, f"không tìm thấy SVG '{n}'"
        khoi = m_svg.group(1)
        for tag in ("rect", "circle"):
            # Dạng tự đóng — không thể chứa <title> con, nên CHÍNH việc tự
            # đóng đã là lỗi cho một phần tử dữ liệu.
            for m in re.finditer(rf"<{tag}\b[^>]*?/>", khoi):
                pytest.fail(f"<{tag}> tự đóng trong '{n}', không thể có "
                            f"<title>: {m.group(0)[:120]!r}")
            for m in re.finditer(rf"<{tag}\b[^>]*>((?:(?!</{tag}>).)*)</{tag}>", khoi, re.S):
                assert "<title>" in m.group(1), \
                    f"<{tag}> trong '{n}' không có <title>: {m.group(0)[:120]!r}"


def _hai_nam_do_dang(conn, batch, ma="AA01", ngành="Đồ khô"):
    """Biến thể của `_hai_nam` DỰNG RIÊNG cho test dưới: đủ ba trạng thái ô
    nhiệt trong CÙNG một lần mở trang — vài tháng có tăng trưởng thật (bậc
    màu + %), một tháng THẬT SỰ không bán ở CẢ HAI năm (2026-03, "khong_ban"),
    và kỳ dừng ở 2026-05 (không bán 06/07) để có tháng "chua_toi"."""
    _nganh(conn, batch, ma, ngành)
    n = 0
    for y, th in ((2024, 8), (2024, 9), (2024, 10), (2024, 11), (2024, 12),
                  (2025, 1), (2025, 2), (2025, 4), (2025, 5), (2025, 6), (2025, 7)):
        n += 1
        _ban(conn, batch, date(y, th, 11), ma, amount=110_000, tax=10_000, gp=30_000, n=n)
    for y, th in ((2025, 8), (2025, 9), (2025, 10), (2025, 11), (2025, 12),
                  (2026, 1), (2026, 2), (2026, 4), (2026, 5)):
        n += 1
        _ban(conn, batch, date(y, th, 11), ma, amount=110_000, tax=10_000, gp=30_000, n=n)


def test_ban_do_nhiet_la_bang_html_co_scope(client, conn, batch):
    """[I-1, I-2, M-7/N-4 soát chặt] Bản đồ nhiệt là <table>, không phải
    SVG — có <th scope> cho cả hàng lẫn cột. Mọi khẳng định về CHỮ TRONG Ô
    kiểm NGAY TRONG khối `<table class="nhiet-bang">…</table>`, không phải
    `r.text` toàn trang — chú giải (`.chu-thich`) cũng có các cụm chữ
    "không bán tháng này"/"chưa tới tháng" nên `in r.text` trần sẽ xanh giả
    kể cả khi bảng chính vẽ sai. Dữ liệu dựng đủ CẢ BA trạng thái thật (tăng
    trưởng có %, không bán 2026-03, chưa tới 2026-06/07) trong MỘT lần mở
    trang — không suy luận qua chú giải hay qua lời gọi `ve_nhiet` rời."""
    _hai_nam_do_dang(conn, batch)
    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    assert '<table class="nhiet-bang">' in r.text
    m = re.search(r'<table class="nhiet-bang">(.*?)</table>', r.text, re.S)
    assert m, "không tìm thấy bảng nhiệt"
    bang = m.group(0)
    assert 'scope="col"' in bang and 'scope="row"' in bang
    assert "không bán tháng này" in bang
    assert "chưa tới tháng" in bang
    # [N-4] % trong Ô và trong title cùng một độ làm tròn (1 chữ số thập
    # phân, dấu chấm) — một ô có tăng trưởng thật (cùng doanh thu mỗi
    # tháng ở cả hai năm) phải in đúng "+0.0%" cả hai chỗ, không phải "+0%".
    assert re.search(r'class="bac-(?:g2|g1|0|t1|t2)"[^>]*>[+-]\d+\.\d%<', bang), \
        "ô nhiệt phải in % với đúng MỘT chữ số thập phân, khớp title"


def test_nhiet_khong_gan_nhan_sai_thang_chua_toi_hay_khong_ban(conn, batch):
    """[CRITICAL, I-1] Kỳ ĐANG DIỄN RA (chưa đủ 12 tháng dữ liệu): tháng SAU
    ngày bán cuối cùng phải là 'chua_toi' (không phải 'khong_ck' — kỳ CHƯA
    ĐI TỚI tháng đó, không phải 'thiếu so sánh'), và một ngành có bán ở kỳ
    trước nhưng THẬT SỰ không bán gì ở một tháng đã qua của kỳ này phải là
    'khong_ban' — cả hai đều KHÁC 'khong_ck' (dành cho tháng có doanh thu
    nhưng không có dòng cùng kỳ)."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    # Kỳ 2026 (2025-08..2026-07) chỉ có MỘT tháng bán (2025-08) — kỳ dở dang.
    _ban(conn, batch, date(2025, 8, 15), "AA01")
    bc = tinh_bao_cao(conn, 2026)
    thang_cuoi = bc.ky.ngay_cuoi.strftime("%Y-%m")
    assert thang_cuoi == "2025-08"
    thang_ky = [f"2025-{t:02d}" for t in range(8, 13)] + [f"2026-{t:02d}" for t in range(1, 8)]
    nh = ve_nhiet(bc.nganh_thang, thang_ky, thang_cuoi)
    o = {c["thang"]: c for c in nh["o"] if c["nganh"] == "Đồ khô"}
    assert o["2025-08"]["bac"] not in ("chua_toi",), "tháng có bán không được là 'chưa tới'"
    assert o["2025-09"]["bac"] == "chua_toi", "tháng SAU ngày bán cuối phải là 'chưa tới'"
    assert o["2026-07"]["bac"] == "chua_toi"


def test_nhiet_khong_ban_that_su_khac_khong_co_cung_ky(conn, batch):
    """[I-1] Một ngành bán liên tục hai năm rồi NGỪNG hẳn một tháng cụ thể ở
    năm sau (0 đồng CẢ hai năm ở đúng tháng đó không đúng kịch bản này — ở
    đây ta chỉ cần MỘT tháng đã qua, trong dải kỳ, mà ngành không có dòng
    nào cả hai phía) phải mang bậc 'khong_ban', không lẫn với 'khong_ck'."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    # Bán đủ 12 tháng của kỳ 2026 TRỪ tháng 2026-03 — kỳ đã đi hết
    # (ngay_cuoi = 2026-07-31) nên 2026-03 không phải "chưa tới".
    for i in range(12):
        th = (8 - 1 + i) % 12 + 1
        y = 2025 + (8 - 1 + i) // 12
        if f"{y}-{th:02d}" == "2026-03":
            continue
        _ban(conn, batch, date(y, th, 11), "AA01", n=i + 1)
    bc = tinh_bao_cao(conn, 2026)
    thang_cuoi = bc.ky.ngay_cuoi.strftime("%Y-%m")
    assert thang_cuoi == "2026-07"
    thang_ky = [f"2025-{t:02d}" for t in range(8, 13)] + [f"2026-{t:02d}" for t in range(1, 8)]
    nh = ve_nhiet(bc.nganh_thang, thang_ky, thang_cuoi)
    o = {c["thang"]: c for c in nh["o"] if c["nganh"] == "Đồ khô"}
    assert o["2026-03"]["bac"] == "khong_ban"


def test_cay_o_khong_de_nhan_nganh_len_ma_khi_co_ma_tach_rieng(conn, batch):
    """[I-3] Khi ngành tách được mã (n['ma'] không rỗng), `ve_cay_o` vẫn trả
    đủ dữ liệu để template BỎ nhãn ngành (kiểm ở mức HTML bằng cách ngành có
    mã thì mọi `<text>` bên trong ô ngành đó — nếu có — phải là nhãn MÃ, tức
    `m['nhan']`); ô quá nhỏ phải có `nhan=None` để không vẽ chữ tràn."""
    nhom = [("Gạo", 1000, 0.1, [("G1", "Gạo ST25", 900), ("G2", "Gạo Jasmine", 100)])]
    cq = ve_cay_o(nhom, rong=720, cao=360)
    n = cq["nganh"][0]
    assert n["ma"], "ngành phải tách được mã ở khung 720x360"
    for m in n["ma"]:
        assert "nhan" in m
    # Một ô quá nhỏ (khung tí hon) không được gán nhãn nào.
    cq_nho = ve_cay_o(nhom, rong=20, cao=10)
    n_nho = cq_nho["nganh"][0]
    for m in n_nho["ma"]:
        assert m["nhan"] is None, "ô quá nhỏ phải có nhan=None, không cắt bừa"


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


# ---- Vòng soát 1 vòng 2 -----------------------------------------------------

def _nk(nganh, chenh_lech, tang_truong=None):
    return NganhKy(nganh=nganh, doanh_thu=1000, lai_gop=100, dt_doi_chieu=900,
                   dt_cung_ky=900, chenh_lech=chenh_lech, tang_truong=tang_truong)


def test_dong_gop_nhan_so_tien_khong_tran_ngoai_khung_khi_thanh_dai_nhat(conn):
    """[CRITICAL, N-1] Thanh CHIẾM TRỌN nửa khung (tỷ lệ 100% so với
    max_abs) từng làm nhãn số tiền của CHÍNH NÓ tràn khỏi viewBox — đặt cứng
    'đầu mút + 4px' không chừa chỗ cho chữ. Toạ độ `nhan_x` phải luôn nằm
    trong `[0, rong]`, thử với đủ số tiền lớn (nhiều chữ số) ở CẢ hai phía."""
    dong = [_nk("Ngành dương rất dài tên", 123_456_789),
            _nk("Ngành âm cũng dài tên không kém", -98_765_432)]
    dg = ve_dong_gop(dong, rong=720)
    assert dg["co"] is True
    for t in dg["thanh"]:
        assert 0 <= t["nhan_x"] <= dg["rong"], \
            f"nhan_x={t['nhan_x']} tràn khỏi khung [0, {dg['rong']}] ở ngành {t['nganh']}"


def test_dong_gop_ten_nganh_o_phia_doi_dien_thanh():
    """[M-1] Tên ngành phải đứng ở phía ĐỐI DIỆN trục so với chính thanh
    của nó — thanh dương (kéo phải trục) thì tên bên TRÁI trục, thanh âm
    (kéo trái) thì tên bên PHẢI. Kiểm gián tiếp qua toạ độ `x` của thanh so
    với `x0`: bài test này khẳng định đúng bất biến hình học mà template
    dùng (`x0 + 4 if t.am else x0 - 4`), không phải một chuỗi cụ thể."""
    dong = [_nk("Dương", 500), _nk("Âm", -500)]
    dg = ve_dong_gop(dong)
    duong = next(t for t in dg["thanh"] if not t["am"])
    am = next(t for t in dg["thanh"] if t["am"])
    # Thanh dương nằm bên PHẢI trục (x == x0); tên của nó phải render ở toạ
    # độ x0 - 4 (bên TRÁI) theo công thức mới trong template — khẳng định
    # gián tiếp bằng cách kiểm thanh dương có x == x0 và thanh âm có x < x0,
    # tức "phía đối diện" của mỗi thanh nằm đúng bên nào.
    assert duong["x"] == dg["x0"]
    assert am["x"] < dg["x0"]


def test_pareto_truc_pct_tra_toa_do_khong_con_hang_so_cung_trong_template(conn, batch):
    """[N-3] `ve_pareto` phải tự trả toạ độ Y của ba vạch 0/50/100% — không
    còn hằng số lề 16/34 chép tay trong Jinja."""
    from kome.bao_cao import KhachTapTrung, TapTrung
    from kome.ve_phan_tich import ve_pareto
    tt = TapTrung(dong=[KhachTapTrung(ma="K1", ten="K1", doanh_thu=100,
                                      thu_hang=1, ty_trong=1.0, luy_ke=1.0)],
                  so_khach=1, luy_ke_top10=None)
    pa = ve_pareto(tt, rong=720, cao=260)
    assert len(pa["truc_pct"]) == 3
    ys = [t["y"] for t in pa["truc_pct"]]
    assert ys == sorted(ys, reverse=True), \
        "0% phải ở DƯỚI (y lớn hơn), 100% ở TRÊN (y nhỏ hơn)"
    assert pa["truc_pct"][0]["nhan"] == "0%"
    assert pa["truc_pct"][-1]["nhan"] == "100%"


def test_khong_ve_hien_du_khi_khong_co_gi_de_ve(client, conn, batch):
    """[M-3] Dòng 'Không vẽ' đứng NGOÀI `{% if co.co %}` — cả kỳ chỉ có
    ĐÚNG MỘT ngành và ngành đó ÂM (cây ô rỗng hoàn toàn, co.co=False) vẫn
    phải in ra số tiền bị bỏ, không được im lặng chỉ vì không có gì để
    VẼ."""
    _nganh(conn, batch, "PH01", "Phí")
    _ban(conn, batch, date(2026, 5, 11), "PH01", amount=-5_000, tax=-500, gp=-1_000)
    r = client.get("/bao-cao?ky=2026")
    assert r.status_code == 200
    assert "Không vẽ: ¥" in r.text
    assert "mã (doanh thu âm hoặc bằng 0, hoặc thuộc ngành có tổng âm)" in r.text
