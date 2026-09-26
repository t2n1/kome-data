"""Đợt 5b Task 1 — bảy view phân tích của `mart` cho `/bao-cao` và `/`
(migration 029_mart_phan_tich.sql).

Mỗi test canh một cách hiểu SAI mà nếu lọt thì trang vẫn vẽ ra bình thường,
chỉ là thiếu dòng hoặc nói sai số — loại lỗi tệ nhất vì không ai thấy nó.
"""
import json
from datetime import date

import pandas as pd
import pytest


def _ban(conn, batch, ngay: date, ma_hang: str, khach="000000009292",
         amount=110_000, tax=10_000, gp=30_000, sale="0104"):
    """Một dòng bán thật qua loader, không SQL tay."""
    from kome.loaders import sales
    b = batch(abs(hash((ngay, ma_hang, khach, amount, tax, sale))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{khach[-4:]}{ma_hang}", "line_seq": 1,
        "sales_date": ngay, "customer_code": khach, "product_code": ma_hang,
        "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
        "unit_cost": 3210, "amount": amount, "tax_amount": tax,
        "cost": amount - tax - gp, "gross_profit": gp, "paid_amount": 0,
        "salesperson_code": sale, "batch_id": b,
    }]), ngay, b)
    conn.commit()
    return b


def _nganh(conn, batch, ma_hang: str, ten_nganh: str):
    """Một dòng core.dim_product mang ngành (food_category_name) cho trước.

    Không có loader tiện cho dim_product trong test hiện có (chỉ có
    `_san_pham` của tests/test_mart_san_pham.py, không đặt food_category_name)
    nên INSERT thẳng — brief đợt 5b Task 1 chấp nhận cách này.
    """
    b = batch(abs(hash(("nganh", ma_hang))) % 40_000 + 300_000)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, food_category_name, batch_id)
           VALUES (%s, %s, %s, %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma_hang, f"Hàng {ma_hang}", ten_nganh, b))
    conn.commit()


# ---------------------------------------------------------------------------
# 3.1 + 3.2 — mart.ban_theo_nganh_thang
# ---------------------------------------------------------------------------

def test_tong_cac_nganh_bang_tong_thang_ke_ca_dong_ma_hang_rong(conn, batch):
    """[CRITICAL] LEFT JOIN sang dim_product: dòng mã hàng rỗng hoặc mã chưa
    vào danh mục vẫn phải giữ tiền của nó. JOIN thường (thay vì LEFT JOIN) sẽ
    làm mất hẳn hai dòng này, và tổng các ngành lệch tổng tháng."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _ban(conn, batch, date(2026, 5, 11), "", amount=11_000, tax=1_000, gp=2_000)
    _ban(conn, batch, date(2026, 5, 12), "ZZ99", amount=22_000, tax=2_000, gp=3_000)
    _ban(conn, batch, date(2026, 5, 13), "AA01", amount=33_000, tax=3_000, gp=4_000)

    tong_thang = conn.execute(
        "SELECT doanh_thu_thuan FROM mart.ban_theo_thang WHERE thang = '2026-05'"
    ).fetchone()[0]
    tong_nganh = conn.execute(
        "SELECT sum(doanh_thu_thuan) FROM mart.ban_theo_nganh_thang "
        "WHERE thang = '2026-05'").fetchone()[0]
    assert tong_nganh == tong_thang

    chua_phan_loai = conn.execute(
        "SELECT doanh_thu_thuan FROM mart.ban_theo_nganh_thang "
        "WHERE thang = '2026-05' AND nganh = '(chưa phân loại)'").fetchone()[0]
    assert chua_phan_loai == 22_000 - 2_000, \
        "mã chưa có trong danh mục phải rơi vào '(chưa phân loại)'"
    # 048: dòng mã hàng rỗng (端数) là phí & điều chỉnh — vẫn giữ tiền, khác nhãn.
    phi = conn.execute(
        "SELECT doanh_thu_thuan FROM mart.ban_theo_nganh_thang "
        "WHERE thang = '2026-05' AND nganh = 'Phí & điều chỉnh'").fetchone()[0]
    assert phi == 11_000 - 1_000


# ---------------------------------------------------------------------------
# 3.3 — mart.ban_theo_nganh_thang_so_sanh
# ---------------------------------------------------------------------------

def test_nganh_ban_nam_ngoai_ma_nam_nay_khong_ban_van_co_dong(conn, batch):
    """[CRITICAL] FULL JOIN giữa tháng này và tháng M-12: ngành sụt về 0 (bán
    năm ngoái, năm nay im bặt) phải VẪN có dòng — đó là ngành sụt mạnh nhất,
    thứ khối "ngành kéo xuống" cần thấy nhất. LEFT JOIN thường sẽ làm nó biến
    mất khỏi mọi báo cáo mà không lỗi nào nổ ra."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _nganh(conn, batch, "BB01", "Ngành B")
    _ban(conn, batch, date(2025, 5, 10), "AA01", amount=55_000, tax=5_000, gp=10_000)
    _ban(conn, batch, date(2026, 5, 10), "AA01", amount=66_000, tax=6_000, gp=12_000)
    _ban(conn, batch, date(2025, 5, 11), "BB01", amount=44_000, tax=4_000, gp=8_000,
         khach="000000009293")

    r = conn.execute(
        "SELECT doanh_thu_thuan, dt_cung_ky, co_cung_ky "
        "FROM mart.ban_theo_nganh_thang_so_sanh "
        "WHERE thang = '2026-05' AND nganh = 'Ngành B'").fetchone()
    assert r is not None, "ngành sụt về 0 phải VẪN có dòng, không được biến mất"
    assert r[0] == 0
    assert r[1] == 44_000 - 4_000
    assert r[2] is True


def test_khong_sinh_dong_cho_thang_khong_co_trong_kho(conn, batch):
    """[CRITICAL] Không lọc theo tập tháng CÓ trong kho thì FULL JOIN sinh ra
    dòng cho 12 tháng tương lai (và quá khứ) chưa từng có dữ liệu, từ chính
    dữ liệu năm trước/năm sau."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _ban(conn, batch, date(2025, 5, 10), "AA01")
    _ban(conn, batch, date(2026, 5, 10), "AA01")

    dem = conn.execute(
        "SELECT count(*) FROM mart.ban_theo_nganh_thang_so_sanh "
        "WHERE thang IN ('2026-06', '2027-05')").fetchone()[0]
    assert dem == 0


def test_khong_co_thang_M_tru_12_thi_co_cung_ky_sai_va_dt_cung_ky_NULL(conn, batch):
    """[CRITICAL] "co_cung_ky = false" là sự thật về KHO (tháng M-12 chưa
    từng có dòng bán nào), khác hẳn "có tháng đó nhưng bằng 0" — dt_cung_ky
    phải NULL, không phải 0, để trang in ra "chưa có cùng kỳ" thay vì "sụt
    100%"."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _ban(conn, batch, date(2026, 5, 10), "AA01")

    r = conn.execute(
        "SELECT co_cung_ky, dt_cung_ky, tang_truong "
        "FROM mart.ban_theo_nganh_thang_so_sanh "
        "WHERE thang = '2026-05' AND nganh = 'Ngành A'").fetchone()
    assert r == (False, None, None)


def test_co_thang_M_tru_12_ma_nganh_khong_ban_thi_dt_cung_ky_bang_0(conn, batch):
    """[IMPORTANT] "co_cung_ky" xét theo THÁNG (cả công ty có bán không),
    KHÔNG theo ngành. Ngành B mới xuất hiện năm nay: tháng M-12 vẫn "có
    trong kho" (ngành A đã bán), nên dt_cung_ky của B phải là 0 (đã biết:
    không bán), không phải NULL (không biết)."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _nganh(conn, batch, "BB01", "Ngành B")
    _ban(conn, batch, date(2025, 5, 10), "AA01")
    _ban(conn, batch, date(2026, 5, 10), "BB01")

    r = conn.execute(
        "SELECT co_cung_ky, dt_cung_ky, tang_truong "
        "FROM mart.ban_theo_nganh_thang_so_sanh "
        "WHERE thang = '2026-05' AND nganh = 'Ngành B'").fetchone()
    assert r == (True, 0, None)


def test_tang_truong_NULL_khi_cung_ky_am(conn, batch):
    """[CRITICAL] Mẫu số ÂM (赤伝) mà không chặn bằng `> 0` sẽ cho tỷ lệ tăng
    trưởng NGƯỢC DẤU: doanh thu tăng thật (từ -50.000 lên 100.000) mà công
    thức ngây thơ ra "-300%", nói SỤT trong khi thực ra TĂNG."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _ban(conn, batch, date(2025, 5, 10), "AA01", amount=-60_000, tax=-10_000, gp=-20_000)
    _ban(conn, batch, date(2026, 5, 10), "AA01", amount=100_000, tax=0, gp=30_000)

    r = conn.execute(
        "SELECT dt_cung_ky, tang_truong FROM mart.ban_theo_nganh_thang_so_sanh "
        "WHERE thang = '2026-05' AND nganh = 'Ngành A'").fetchone()
    assert r[0] == -50_000
    assert r[1] is None, "mẫu số ÂM không có tỷ lệ tăng trưởng đọc được"


# ---------------------------------------------------------------------------
# 3.3b — mart.nganh_ky_cung_ky
# ---------------------------------------------------------------------------

def test_tong_chenh_lech_nganh_bang_chenh_lech_ky(conn, batch):
    """[CRITICAL] Hai con số trên cùng một trang phải cộng khớp nhau: tổng
    chenh_lech theo TỪNG NGÀNH phải bằng đúng dt - dt_ck gộp CẢ KỲ của
    mart.ky_cung_ky. Lệch nhau nghĩa là hai view định nghĩa "tháng đối chiếu"
    khác nhau ở đâu đó."""
    _nganh(conn, batch, "AA01", "Ngành A")
    _nganh(conn, batch, "BB01", "Ngành B")
    # Tháng 04: chỉ ngành A bán, KHÔNG có cùng kỳ (2025-04 trống toàn công ty)
    # -> không được tính vào chenh_lech lẫn ky_cung_ky.
    _ban(conn, batch, date(2026, 4, 10), "AA01", amount=50_000, tax=0, gp=10_000)
    # Tháng 05: cả hai ngành bán cả hai năm -> tháng đối chiếu.
    _ban(conn, batch, date(2025, 5, 10), "AA01", amount=60_000, tax=0, gp=15_000)
    _ban(conn, batch, date(2026, 5, 10), "AA01", amount=90_000, tax=0, gp=20_000)
    _ban(conn, batch, date(2025, 5, 11), "BB01", amount=40_000, tax=0, gp=8_000,
         khach="000000009293")
    _ban(conn, batch, date(2026, 5, 11), "BB01", amount=30_000, tax=0, gp=6_000,
         khach="000000009293")
    # Tháng 06: A bán cả hai năm; B chỉ bán năm ngoái (sụt về 0) -> vẫn là
    # tháng đối chiếu (cả công ty có bán ở M và M-12).
    _ban(conn, batch, date(2025, 6, 10), "AA01", amount=70_000, tax=0, gp=17_000)
    _ban(conn, batch, date(2026, 6, 10), "AA01", amount=80_000, tax=0, gp=18_000)
    _ban(conn, batch, date(2025, 6, 11), "BB01", amount=20_000, tax=0, gp=4_000,
         khach="000000009293")

    tong_chenh_lech = conn.execute(
        "SELECT sum(chenh_lech) FROM mart.nganh_ky_cung_ky WHERE company_fy = 2026"
    ).fetchone()[0]
    dt, dt_ck = conn.execute(
        "SELECT dt, dt_ck FROM mart.ky_cung_ky WHERE company_fy = 2026").fetchone()
    assert tong_chenh_lech == dt - dt_ck


# ---------------------------------------------------------------------------
# 3.4 — mart.ky_cung_ky
# ---------------------------------------------------------------------------

def test_ky_cung_ky_chi_tinh_thang_doi_chieu(conn, batch):
    """[CRITICAL] So CÙNG THÁNG với cùng tháng, không so cả kỳ với cả kỳ. Kỳ
    2026 (1/8/2025 -> 31/7/2026) có 2025-09 (không có cùng kỳ 2024-09) và
    2026-05 (có cùng kỳ 2025-05): chỉ 2026-05 được tính vào dt, và
    so_thang_doi_chieu phải là 1, không phải 2."""
    _ban(conn, batch, date(2025, 9, 10), "AA01", amount=50_000, tax=0, gp=10_000)
    _ban(conn, batch, date(2026, 5, 10), "AA01", amount=90_000, tax=0, gp=20_000)
    _ban(conn, batch, date(2025, 5, 10), "AA01", amount=60_000, tax=0, gp=15_000)

    r = conn.execute(
        "SELECT so_thang_doi_chieu, thang_dau_doi_chieu, thang_cuoi_doi_chieu, dt "
        "FROM mart.ky_cung_ky WHERE company_fy = 2026").fetchone()
    assert r == (1, "2026-05", "2026-05", 90_000)


def test_ky_cung_ky_dem_khach_DISTINCT_qua_nhieu_thang(conn, batch):
    """[IMPORTANT] so_khach là count(DISTINCT customer_code) trên toàn bộ các
    tháng đối chiếu của kỳ, KHÔNG phải tổng số khách theo từng tháng cộng
    lại — một khách mua nhiều tháng vẫn là 1 khách."""
    khach = "000000009292"
    _ban(conn, batch, date(2025, 4, 10), "AA01", amount=10_000, tax=0, gp=2_000, khach=khach)
    _ban(conn, batch, date(2026, 4, 10), "AA01", amount=11_000, tax=0, gp=2_000, khach=khach)
    _ban(conn, batch, date(2025, 5, 10), "AA01", amount=12_000, tax=0, gp=3_000, khach=khach)
    _ban(conn, batch, date(2026, 5, 10), "AA01", amount=13_000, tax=0, gp=3_000, khach=khach)

    r = conn.execute(
        "SELECT so_khach FROM mart.ky_cung_ky WHERE company_fy = 2026").fetchone()
    assert r[0] == 1


def test_ky_khong_co_thang_doi_chieu_van_co_dong_voi_so_thang_0(conn, batch):
    """[CRITICAL] Kỳ chỉ toàn tháng không đối chiếu vẫn phải hiện MỘT dòng
    (chứ không phải biến mất khỏi báo cáo): so_thang_doi_chieu = 0, dt NULL
    — "chưa so được", khác "so ra 0"."""
    _ban(conn, batch, date(2026, 4, 10), "AA01")  # không có dòng 2025-04 nào

    r = conn.execute(
        "SELECT so_thang_doi_chieu, dt FROM mart.ky_cung_ky "
        "WHERE company_fy = 2026").fetchone()
    assert r is not None, "kỳ không có tháng đối chiếu vẫn phải có MỘT dòng"
    assert r == (0, None)


# ---------------------------------------------------------------------------
# 3.5 — mart.tap_trung_khach
# ---------------------------------------------------------------------------

def test_tap_trung_khach_mot_khach_hai_nguoi_phu_trach_chi_mot_dong(conn, batch):
    """[CRITICAL] Gộp theo KHÁCH, không theo (khách, người phụ trách) như
    mart.ban_theo_khach. Một khách đổi người phụ trách giữa kỳ phải VẪN là
    một dòng, tiền cộng lại — không chiếm hai cột trên Pareto, không hạ thấp
    độ tập trung."""
    khach = "000000009292"
    _ban(conn, batch, date(2026, 5, 10), "AA01", amount=110_000, tax=10_000, gp=20_000,
         khach=khach, sale="0104")
    _ban(conn, batch, date(2026, 5, 20), "AA01", amount=55_000, tax=5_000, gp=10_000,
         khach=khach, sale="0105")

    rows = conn.execute(
        "SELECT customer_code, doanh_thu_thuan, thu_hang, luy_ke "
        "FROM mart.tap_trung_khach WHERE company_fy = 2026").fetchall()
    assert len(rows) == 1, "cùng khách hai người phụ trách phải gộp thành MỘT dòng"
    assert rows[0][1] == (110_000 - 10_000) + (55_000 - 5_000)
    assert rows[0][2] == 1
    assert rows[0][3] == pytest.approx(1.0), "luỹ kế tại hạng cao nhất phải bằng 1"


def test_tap_trung_khach_thu_tu_xac_dinh_khi_bang_tien(conn, batch):
    """[IMPORTANT] Không có khoá phụ thì hai khách bằng tiền có thể đổi chỗ
    giữa hai lần mở trang (thứ tự không xác định của Postgres khi ORDER BY
    chỉ có một cột nhiều dòng trùng giá trị). customer_code làm khoá phụ để
    thứ tự luôn giống nhau.

    Đồng thời canh cửa sổ `luy_ke` dùng `ROWS BETWEEN UNBOUNDED PRECEDING AND
    CURRENT ROW`, không phải `RANGE` (mặc định của `ORDER BY` không khai báo
    khung): hai khách bằng tiền dùng RANGE sẽ gộp cả hai vào CÙNG một khung
    "ngang hàng", khiến cả hai dòng cùng nhảy thẳng lên luỹ kế 100% thay vì
    tăng dần 50% rồi 100%. Cũng canh cửa sổ có PARTITION BY company_fy: nếu
    thiếu, tổng ở mẫu số sẽ cộng cả các kỳ khác."""
    _ban(conn, batch, date(2026, 5, 10), "AA01", amount=110_000, tax=10_000, gp=20_000,
         khach="000000000002")
    _ban(conn, batch, date(2026, 5, 11), "AA01", amount=110_000, tax=10_000, gp=20_000,
         khach="000000000001")

    rows = conn.execute(
        "SELECT customer_code, luy_ke FROM mart.tap_trung_khach "
        "WHERE company_fy = 2026 ORDER BY thu_hang").fetchall()
    assert [r[0] for r in rows] == ["000000000001", "000000000002"]
    assert rows[0][1] == pytest.approx(0.5), "hạng 1 (ROWS) chỉ luỹ kế chính nó"
    assert rows[1][1] == pytest.approx(1.0), "hạng 2 luỹ kế cả hai"


# ---------------------------------------------------------------------------
# 3.6 — mart.ban_theo_ngay
# ---------------------------------------------------------------------------

def test_ban_theo_ngay_ngay_khong_ban_co_dong_0_va_khong_qua_hom_nay(conn, batch):
    """[CRITICAL] Nối TỪ lịch: ngày không bán trong dải dữ liệu phải có dòng
    mang số 0 (biết là 0, không phải "không có dữ liệu"), nếu không trục
    hoành của biểu đồ xu hướng co lại và một tuần trông ngắn hơn thật. Không
    được có dòng sau ngày bán mới nhất — đó là tương lai, "không biết"."""
    _ban(conn, batch, date(2026, 5, 11), "AA01")
    _ban(conn, batch, date(2026, 5, 13), "AA01")

    giua = conn.execute(
        "SELECT doanh_thu_thuan, lai_gop, so_phieu, so_khach FROM mart.ban_theo_ngay "
        "WHERE ngay = '2026-05-12'").fetchone()
    assert giua == (0, 0, 0, 0)

    sau = conn.execute(
        "SELECT count(*) FROM mart.ban_theo_ngay WHERE ngay > '2026-05-13'").fetchone()[0]
    assert sau == 0


# ---------------------------------------------------------------------------
# 3.7 — mart.thang_den_hom_nay
# ---------------------------------------------------------------------------

def test_thang_den_hom_nay_so_cung_so_ngay_khong_tron_thang(conn, batch):
    """[CRITICAL] Cùng kỳ = cùng DẢI NGÀY (mùng 1 -> ngày N năm trước), KHÔNG
    phải trọn tháng năm trước. Đem 12 ngày đầu tháng so với cả một tháng thì
    giữa tháng nào cũng "sụt" giả tạo."""
    _ban(conn, batch, date(2026, 5, 12), "AA01", amount=11_000, tax=1_000, gp=2_000)
    _ban(conn, batch, date(2025, 5, 10), "AA01", amount=22_000, tax=2_000, gp=4_000,
         khach="000000009293")
    _ban(conn, batch, date(2025, 5, 20), "AA01", amount=33_000, tax=3_000, gp=6_000,
         khach="000000009294")

    dt_ck, den_ngay_ck = conn.execute(
        "SELECT dt_ck, den_ngay_ck FROM mart.thang_den_hom_nay").fetchone()
    assert den_ngay_ck == date(2025, 5, 12)
    assert dt_ck == 22_000 - 2_000, \
        "chỉ 2025-05-10 (<= den_ngay_ck) được tính, KHÔNG gồm 2025-05-20"


def test_thang_den_hom_nay_29_2_kep_ve_28_2(conn, batch):
    """[IMPORTANT] Ngày 29/2 không tồn tại ở năm không nhuận trước đó: dải
    cùng kỳ phải kẹp về ngày cuối tháng 2 năm trước (28/2), không được lỗi
    hay lệch sang 1/3. core.dim_date phủ tới 2035 nên 2028-02-29 hợp lệ."""
    _ban(conn, batch, date(2028, 2, 29), "AA01")

    r = conn.execute("SELECT den_ngay_ck FROM mart.thang_den_hom_nay").fetchone()
    assert r[0] == date(2027, 2, 28)


def test_thang_den_hom_nay_M_tru_12_khong_co_du_lieu_thi_ck_la_NULL(conn, batch):
    """[CRITICAL] "co_cung_ky = false" (tháng M-12 chưa từng có dòng bán nào)
    phải cho dt_ck/lg_ck/so_khach_ck NULL — "chưa có cùng kỳ để so", KHÔNG
    phải 0 ("có cùng kỳ, và cùng kỳ bằng 0"). Nhầm hai trường hợp này là ô
    chỉ số in ra "▼100% so cùng kỳ" cho một tháng chưa hề có dữ liệu năm
    trước để so, thay vì câu "chưa có cùng kỳ để so"."""
    _ban(conn, batch, date(2026, 5, 12), "AA01")  # không có dòng nào ở 2025-05

    r = conn.execute(
        "SELECT co_cung_ky, dt_ck, lg_ck, so_khach_ck "
        "FROM mart.thang_den_hom_nay").fetchone()
    assert r == (False, None, None, None)


def test_thang_den_hom_nay_kho_rong_khong_co_dong(conn):
    """[IMPORTANT] "hôm nay" của view này là ngày bán mới nhất trong kho
    (mart.moc_thoi_gian). Kho rỗng thì không có "hôm nay" nào để tính — view
    phải trả về 0 dòng, không phải một dòng NULL khiến trang render lỗi."""
    dem = conn.execute("SELECT count(*) FROM mart.thang_den_hom_nay").fetchone()[0]
    assert dem == 0


# ---------------------------------------------------------------------------
# Quyền + kế hoạch truy vấn
# ---------------------------------------------------------------------------

def test_ba_vai_tro_deu_SELECT_duoc_moi_view_moi(conn):
    """[IMPORTANT] ALTER DEFAULT PRIVILEGES của 009 KHÔNG kể tên kome_ingest,
    nên view mới của `mart` không tự có quyền cho vai trò đó. Quên dòng GRANT
    tường minh ở cuối 029 thì lỗi không nổ lúc migration chạy — nó nổ bằng
    `permission denied` nhiều tháng sau, giữa lúc có người đang nạp dữ liệu."""
    thieu = conn.execute(
        """SELECT c.relname, r.rolname
           FROM pg_class c
           JOIN pg_namespace n ON n.oid = c.relnamespace
           CROSS JOIN (VALUES ('kome_app'), ('kome_report'), ('kome_ingest'))
                      AS r(rolname)
           WHERE n.nspname = 'mart'
             AND c.relname IN ('ban_theo_nganh_thang', 'ban_theo_nganh_thang_so_sanh',
                               'nganh_ky_cung_ky', 'ky_cung_ky', 'tap_trung_khach',
                               'ban_theo_ngay', 'thang_den_hom_nay')
             AND NOT has_table_privilege(r.rolname, c.oid, 'SELECT')
           ORDER BY 1, 2""").fetchall()
    assert thieu == [], f"thiếu SELECT: {thieu}"


def test_nganh_so_sanh_chi_quet_fact_sales_line_mot_lan(conn, batch):
    """[nếp test migration 028, bất biến CTE của CLAUDE.md] mart.dong_ban chỉ
    tham chiếu core.fact_sales_line một lần. mart.ban_theo_nganh_thang_so_sanh
    dùng lại mart.ban_theo_nganh_thang (dựng trên mart.dong_ban) HAI LẦN
    (`a` và `tr` trong FULL JOIN của CTE `cap`) — nếu CTE gốc `nt` không vào
    `MATERIALIZED` tường minh, Postgres đánh giá lại toàn bộ view gốc ở mỗi
    lần tham chiếu, tăng gấp đôi số lượt quét fact_sales_line.

    Đếm SỐ LẦN quan hệ fact_sales_line xuất hiện trong cây kế hoạch (đếm tham
    chiếu quan hệ), không đếm KIỂU quét: CSDL test nhỏ nên planner chọn Seq
    Scan ở mọi chỗ, kiểu quét không phản ánh CSDL thật."""
    _ban(conn, batch, date(2026, 5, 10), "AA01")

    raw = conn.execute(
        "EXPLAIN (FORMAT JSON) SELECT * FROM mart.ban_theo_nganh_thang_so_sanh"
    ).fetchone()[0]
    plan = json.loads(raw) if isinstance(raw, str) else raw

    def dem(node) -> int:
        n = 1 if node.get("Relation Name") == "fact_sales_line" else 0
        for con in node.get("Plans", []):
            n += dem(con)
        return n

    tong = sum(dem(p["Plan"]) for p in plan)
    assert tong == 1, f"fact_sales_line bị quét {tong} lần, phải là 1"
