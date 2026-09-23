"""Đợt 5a Task 1 — bốn view của schema `mart` cho ngân sách.

Mỗi test ở đây canh một cách hiểu SAI mà nếu lọt thì trang vẫn vẽ ra bình
thường, chỉ là thiếu dòng hoặc nói sai số. Đó là loại lỗi tệ nhất: không ai
thấy nó, và người ta ra quyết định dựa trên nó.
"""
from datetime import date

import pandas as pd
import pytest


def _ban(conn, batch, ngay: date, sale: str, amount=110_000, tax=10_000,
         gp=30_000, khach="000000009292"):
    """Một dòng bán thật qua loader, không SQL tay."""
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale, amount, khach))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": khach, "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": amount, "tax_amount": tax, "cost": amount - tax - gp,
        "gross_profit": gp, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()
    return b


def _chi_tieu(conn, sale: str, thang: date, muc_tieu: int):
    conn.execute(
        "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
        "VALUES (%s, %s, %s)", (sale, thang, muc_tieu))
    conn.commit()


def test_nguoi_co_chi_tieu_ma_KHONG_ban_duoc_dong_nao_van_co_dong(conn, batch):
    """[CRITICAL] Nối `ban_theo LEFT JOIN ngan_sach` làm người có chỉ tiêu mà
    doanh thu 0 biến mất — đúng người cần nhìn nhất thì không có dòng nào, và
    trang vẫn vẽ ra bình thường."""
    _ban(conn, batch, date(2026, 5, 11), "0104")
    _chi_tieu(conn, "0105", date(2026, 5, 1), 9_000_000)
    r = conn.execute(
        "SELECT muc_tieu, thuc_te FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0105'").fetchone()
    assert r is not None, "người có chỉ tiêu mà 0 doanh thu phải VẪN có dòng"
    assert r[0] == 9_000_000 and r[1] == 0


def test_thang_co_doanh_thu_ma_QUEN_dat_chi_tieu_van_co_dong(conn, batch):
    """[CRITICAL] Nối chiều ngược lại làm doanh thu thật không xuất hiện ở đâu."""
    _ban(conn, batch, date(2026, 5, 11), "0104")
    r = conn.execute(
        "SELECT muc_tieu, thuc_te FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert r is not None, "tháng có doanh thu mà chưa đặt chỉ tiêu phải VẪN có dòng"
    assert r[0] is None and r[1] == 100_000


def test_ma_phu_trach_ngoai_dim_salesperson_van_hien_doanh_thu(conn, batch):
    """[CRITICAL] Đo thật 2026-09-22: dữ liệu bán có 6 mã phụ trách, còn
    core.dim_salesperson chỉ có 5 — mã `0000` có 1 khách và ¥28.981 kỳ 7. Mã
    đó không bao giờ đặt được chỉ tiêu (khoá ngoại chặn), nên phép nối nào
    xuất phát từ chỉ tiêu cũng làm số tiền đó bốc hơi."""
    _ban(conn, batch, date(2026, 5, 11), "0000", amount=33_000, tax=3_000, gp=9_000)
    r = conn.execute(
        "SELECT thuc_te FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0000'").fetchone()
    assert r is not None and r[0] == 30_000


def test_chi_tieu_bang_0_cho_tien_do_NULL_khong_lam_no_trang(conn, batch):
    """Chia cho 0 thì trang chết; in "∞" thì người đọc tưởng đã vượt mức."""
    _ban(conn, batch, date(2026, 5, 11), "0104")
    _chi_tieu(conn, "0104", date(2026, 5, 1), 0)
    r = conn.execute(
        "SELECT tien_do FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert r[0] is None


def test_moc_den_hom_nay_theo_ngay_lam_viec_da_qua(conn, batch):
    """Mốc = chỉ tiêu × (ngày làm việc đã qua / tổng ngày làm việc của tháng).
    hom_nay = ngày bán mới nhất trong kho, KHÔNG phải current_date."""
    _ban(conn, batch, date(2026, 5, 15), "0104")     # hom_nay = 2026-05-15
    _chi_tieu(conn, "0104", date(2026, 5, 1), 10_000_000)
    r = conn.execute(
        """SELECT ngay_kd, ngay_kd_da_qua, muc_tieu_den_hom_nay
           FROM mart.tien_do_ngan_sach
           WHERE thang = '2026-05' AND salesperson_code = '0104'""").fetchone()
    # 5/2026: 21 ngày trong tuần − 3 ngày lễ Tuần lễ Vàng rơi vào ngày thường
    # (4/5, 5/5, 6/5 振替休日 — migration 032) = 18; tới hết 15/5 là 11 − 3 = 8.
    # Đây CHÍNH là hạn chế có tên của 026 được gỡ: trước 032 vạch mốc tháng 5
    # khắt khe hơn thực tế ba ngày.
    assert (r[0], r[1]) == (18, 8)
    # `::bigint` của Postgres LÀM TRÒN (không cắt cụt), nên cho phép lệch 1 yên
    # thay vì khẳng định một trong hai cách quy tròn — con số này không dùng để
    # đối chiếu sổ sách, nó là vạch mốc trên một thanh tiến độ.
    assert r[2] == pytest.approx(10_000_000 * 8 / 18, abs=1)


def test_thang_da_qua_han_thi_moc_bang_dung_chi_tieu(conn, batch):
    """Tháng đã trôi qua hết so với hom_nay thì mốc phải là 100% chỉ tiêu,
    không phải một con số tròn tuỳ tiện."""
    _ban(conn, batch, date(2026, 7, 31), "0104")     # hom_nay = 2026-07-31
    _chi_tieu(conn, "0104", date(2026, 5, 1), 10_000_000)
    r = conn.execute(
        "SELECT muc_tieu_den_hom_nay FROM mart.tien_do_ngan_sach "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert r[0] == 10_000_000


def test_ty_suat_theo_thang_la_TY_SO_CUA_CAC_TONG(conn, batch):
    """[IMPORTANT] Bất biến của dự án: tỷ suất ở BẤT KỲ view nào của `mart`
    luôn là sum(lãi gộp)/sum(doanh thu thuần), không bao giờ là trung bình
    của các tỷ số từng dòng. Một dòng doanh thu thuần vài yên (mẫu số nhỏ do
    赤伝) cho ra tỷ số hàng chục lần và kéo lệch cả bảng."""
    _ban(conn, batch, date(2026, 5, 11), "0104", amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 5, 12), "0104", amount=1_100, tax=100, gp=900,
         khach="000000009293")
    r = conn.execute(
        "SELECT ty_suat FROM mart.ban_theo_nhan_vien_thang "
        "WHERE thang = '2026-05' AND salesperson_code = '0104'").fetchone()
    assert abs(float(r[0]) - (30_900 / 101_000)) < 1e-9


def test_chi_tieu_ngoai_dai_lich_bi_CHAN_ngay_luc_ghi(conn):
    """core.dim_date phủ 2024-01-01 → 2035-12-31. Không có khoá ngoại thì một
    dòng chỉ tiêu ngoài dải đó biến mất khỏi mọi báo cáo mà không lỗi nào nổ —
    dữ liệu còn trong bảng, chỉ là không ai nhìn thấy nữa."""
    import psycopg
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute(
            "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
            "VALUES ('0104', DATE '2036-01-01', 1000)")
    conn.rollback()


def test_khong_ghi_duoc_thang_khong_phai_mung_1(conn):
    """Hai dòng "cùng tháng" khác ngày là hai chỉ tiêu cho một tháng."""
    import psycopg
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
            "VALUES ('0104', DATE '2026-05-15', 1000)")
    conn.rollback()


def test_co_moi_mac_dinh_FALSE(conn):
    """Quyền ghi phải được cấp TƯỜNG MINH, không phải thứ ai cũng có vì người
    tạo tài khoản quên đặt."""
    from kome.web import nguoi_dung as ND
    ND.tao(conn, "an", "mat-khau-cua-an-2026")
    conn.commit()
    r = conn.execute(
        "SELECT duoc_sua_ngan_sach FROM app.nguoi_dung WHERE ten_dang_nhap='an'"
    ).fetchone()
    assert r[0] is False


# ---- 028: vòng soát cuối 2 — cung_ky/co_cung_ky/tang_truong trên chính
# mart.tien_do_ngan_sach (thay cho mart.ban_theo_nhan_vien_thang_so_sanh
# của 027, đã bị DROP vì lọc sai trục và gây hồi quy — xem 028) -----------

def test_cung_ky_DUNG_khi_KHONG_ban_thang_nay_nhung_CO_ban_cung_ky(conn, batch):
    """[CRITICAL, vòng soát cuối 2, việc 1] Đây CHÍNH XÁC là hồi quy do 027
    gây ra. 027 lọc mart.ban_theo_nhan_vien_thang_so_sanh theo THÁNG ĐANG
    XÉT — nên một người CÓ muc_tieu mà KHÔNG một dòng bán nào trong tháng đó
    (đúng người mà FULL JOIN của 026 tồn tại để giữ, chú thích của 026 gọi
    là "đúng người cần nhìn nhất") không hề có mặt trong view so sánh, bất
    kể năm ngoái cùng tháng họ có bán được bao nhiêu. Đây CHÍNH XÁC là setup
    của test_nguoi_co_chi_tieu_ma_KHONG_ban_duoc_dong_nao_van_co_dong (mã
    0105) cộng thêm một dòng bán ở tháng cùng kỳ — không test nào của vòng
    sửa trước chạm ca này."""
    # 0104 bán tháng đang xét (2026-05) để tháng đó TỒN TẠI trong kho.
    _ban(conn, batch, date(2026, 5, 11), "0104")
    # 0105 KHÔNG bán gì tháng 2026-05, nhưng CÓ bán ở đúng tháng cùng kỳ
    # (2025-05) — doanh thu thuần = 88.000 - 8.000 = 80.000.
    _ban(conn, batch, date(2025, 5, 20), "0105", amount=88_000, tax=8_000,
         gp=20_000, khach="000000009293")
    _chi_tieu(conn, "0105", date(2026, 5, 1), 9_000_000)

    r = conn.execute(
        """SELECT thuc_te, cung_ky, co_cung_ky, tang_truong
           FROM mart.tien_do_ngan_sach
           WHERE thang = '2026-05' AND salesperson_code = '0105'""").fetchone()
    assert r is not None, "0105 phải VẪN có dòng (chỉ tiêu mà 0 doanh thu)"
    assert r[0] == 0, "0105 không bán gì tháng đang xét"
    assert r[1] == 80_000, \
        "cung_ky phải là doanh thu THẬT của 0105 năm ngoái, không phải None"
    assert r[2] is True
    assert r[3] == pytest.approx(0 / 80_000 - 1), "0 / 80.000 - 1 = -100%"


def test_cung_ky_KHONG_TON_TAI_khi_thang_M12_chua_co_du_lieu_trong_kho(conn, batch):
    """[CRITICAL, vòng soát cuối 2, việc 1] "co_cung_ky = false" là một sự
    thật về KHO (tháng M-12 chưa từng có dòng bán nào ở BẤT KỲ ai), không
    phải một sự thật riêng về người đang xét — đây là ca DUY NHẤT được in
    "không có dữ liệu"."""
    _ban(conn, batch, date(2025, 4, 20), "0104")   # M=2025-04, M-12=2024-04
    r = conn.execute(
        """SELECT cung_ky, co_cung_ky FROM mart.tien_do_ngan_sach
           WHERE thang = '2025-04' AND salesperson_code = '0104'""").fetchone()
    assert r == (None, False)


def test_cung_ky_TON_TAI_ban_0_dong_khac_KHONG_TON_TAI(conn, batch):
    """[IMPORTANT, vòng soát cuối, việc 3] "co_cung_ky = false" CHỈ đúng khi
    tháng cùng kỳ không có dòng bán nào TRONG CẢ CÔNG TY. Một tháng CÓ dòng
    (dù ròng bằng 0) phải cho `co_cung_ky = true, cung_ky = 0` — khác hẳn
    "không tồn tại"."""
    _ban(conn, batch, date(2026, 7, 31), "0104", amount=100_000, tax=0, gp=30_000)
    _ban(conn, batch, date(2025, 7, 11), "0104", amount=0, tax=0, gp=0,
         khach="000000009293")
    r = conn.execute(
        """SELECT cung_ky, co_cung_ky, tang_truong
           FROM mart.tien_do_ngan_sach
           WHERE thang = '2026-07' AND salesperson_code = '0104'""").fetchone()
    assert r[0] == 0
    assert r[1] is True
    assert r[2] is None, "mẫu số 0 cũng không có tỷ lệ tăng trưởng đọc được"


def test_cung_ky_AM_khong_ra_tang_truong_nguoc_dau(conn, batch):
    """[CRITICAL] Kiểm THẲNG ở tầng view rằng gate `> 0` (không phải `<>
    0`) chặn đúng mẫu số ÂM do 赤伝. `100.000 / -50.000 - 1 = -3.0`, tức
    -300%: một con số nói doanh thu SỤT trong khi thật ra nó TĂNG."""
    _ban(conn, batch, date(2026, 7, 31), "0104", amount=100_000, tax=0, gp=30_000)
    _ban(conn, batch, date(2025, 7, 11), "0104", amount=-60_000, tax=-10_000,
         gp=-20_000, khach="000000009293")
    r = conn.execute(
        """SELECT cung_ky, co_cung_ky, tang_truong
           FROM mart.tien_do_ngan_sach
           WHERE thang = '2026-07' AND salesperson_code = '0104'""").fetchone()
    assert r[0] == -50_000
    assert r[1] is True, "có dòng cùng kỳ (dù âm) thì co_cung_ky phải TRUE"
    assert r[2] is None, "mẫu số ÂM không có tỷ lệ tăng trưởng đọc được"


def test_view_so_sanh_027_da_bi_DROP_o_028(conn):
    """[Vòng soát cuối 2] mart.ban_theo_nhan_vien_thang_so_sanh (027) không
    còn ai đọc — kome/bao_cao.py giờ đọc thẳng ba cột mới trên
    mart.tien_do_ngan_sach (028). Khẳng định nó thật sự đã biến mất, để
    không ai vô tình để lại một view chết mang chú thích sai (027 nói
    dt_cung_ky "NULL hoặc 0 tuỳ nguồn" — sai, amount/tax_amount NOT NULL từ
    007 nên sum() trên nhóm không rỗng không bao giờ NULL)."""
    r = conn.execute(
        """SELECT 1 FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'mart'
             AND c.relname = 'ban_theo_nhan_vien_thang_so_sanh'""").fetchone()
    assert r is None, "view thừa của 027 phải đã bị DROP ở 028"


# ---- 027: vòng soát cuối — sua_boi ON DELETE SET NULL ----------------------

def test_xoa_tai_khoan_da_tung_sua_ngan_sach_van_xoa_duoc(conn):
    """[CRITICAL, vòng soát cuối việc 7] docs/runbook.md và
    scripts/tao_nguoi_dung.py dạy thẳng "cần chặn một người đã nghỉ việc /
    cần cắt NGAY thì xoá tài khoản: họ bị chặn ở lượt bấm kế tiếp" —
    kome/web/nguoi_dung.py::theo_id() dựa vào việc DELETE đó THÀNH CÔNG.
    Trước bản sửa, `sua_boi REFERENCES app.nguoi_dung` (ON DELETE mặc định
    NO ACTION) chặn đúng thủ tục đó cho tài khoản ĐÃ TỪNG sửa ngân sách —
    tức chính chủ DN, người CẦN cắt quyền khẩn cấp nhất. Vì
    app.ngan_sach_nhat_ky không bao giờ xoá dòng, chặn đó là VĨNH VIỄN.

    Sau bản sửa (ON DELETE SET NULL): xoá được, và dòng ngân sách + dòng
    nhật ký VẪN CÒN NGUYÊN với sua_boi = NULL — giữ lại nhật ký quan trọng
    hơn giữ lại tên người sửa."""
    from kome.ngan_sach import luu
    from kome.web import nguoi_dung as ND
    uid = ND.tao(conn, "chu", "mat-khau-cua-chu-2026", ngan_sach=True)
    conn.commit()
    luu(conn, {("0104", "2026-05"): 9_000_000}, uid)
    conn.commit()

    conn.execute("DELETE FROM app.nguoi_dung WHERE id = %s", (uid,))
    conn.commit()

    r = conn.execute(
        "SELECT muc_tieu, sua_boi FROM app.ngan_sach "
        "WHERE salesperson_code = '0104' AND thang = '2026-05-01'").fetchone()
    assert r == (9_000_000, None), "dòng ngân sách phải CÒN, sua_boi thành NULL"

    r2 = conn.execute(
        "SELECT muc_tieu_moi, sua_boi FROM app.ngan_sach_nhat_ky "
        "WHERE salesperson_code = '0104' AND thang = '2026-05-01'").fetchone()
    assert r2 == (9_000_000, None), "dòng nhật ký phải CÒN, sua_boi thành NULL"


def test_bon_view_moi_deu_cap_SELECT_cho_ca_ba_vai_tro(conn):
    """[IMPORTANT] ALTER DEFAULT PRIVILEGES của 009 KHÔNG kể tên kome_ingest,
    nên view mới của `mart` không tự có quyền cho vai trò đó. Mọi migration
    thêm view vào `mart` (014, 020, 021, 023, 024, 025) đều phải kết thúc
    bằng một dòng GRANT tường minh. Quên dòng đó thì lỗi không nổ ra lúc
    migration chạy — nó nổ bằng `permission denied` nhiều tháng sau, giữa lúc
    có người đang nạp dữ liệu lúc 13:30.

    [Vòng soát cuối 2] `ban_theo_nhan_vien_thang_so_sanh` (027) đã bị DROP ở
    028 nên rời khỏi danh sách này. `tien_do_ngan_sach` không cần một dòng
    GRANT mới ở 028: `CREATE OR REPLACE VIEW` giữ nguyên OID và mọi quyền đã
    cấp trước đó (từ 026), miễn cột cũ không bị đổi tên/kiểu/thứ tự — 028
    chỉ THÊM ba cột vào cuối, nên quyền cũ vẫn còn nguyên. Test này canh
    đúng điều đó: nếu giả định trên sai, nó sẽ đỏ dù 028 không viết dòng
    GRANT nào."""
    thieu = conn.execute(
        """SELECT c.relname, r.rolname
           FROM pg_class c
           JOIN pg_namespace n ON n.oid = c.relnamespace
           CROSS JOIN (VALUES ('kome_app'), ('kome_report'), ('kome_ingest'))
                      AS r(rolname)
           WHERE n.nspname = 'mart'
             AND c.relname IN ('ngay_kinh_doanh', 'ngan_sach_thang',
                               'ban_theo_nhan_vien_thang', 'tien_do_ngan_sach')
             AND NOT has_table_privilege(r.rolname, c.oid, 'SELECT')
           ORDER BY 1, 2""").fetchall()
    assert thieu == [], f"thiếu SELECT: {thieu}"
