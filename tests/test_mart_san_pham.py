"""Chỉ số của màn Sản phẩm và Kho hàng (migration 023).

Hai thứ được canh kỹ nhất ở đây: **cột `best_before` là TEXT và có giá trị CHỮ**
(`賞味期限なし`) lẫn trong đó, nên một `to_date()` trần sẽ làm cả trang trắng; và
**"không có dòng tồn" khác "tồn bằng 0"** — nhầm hai thứ đó là xếp một mã chưa
bao giờ nhập kho vào danh sách cần đặt hàng gấp.
"""
from datetime import date, timedelta

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY


def _ban_qty(conn, batch, ma_khach, ngay, ma_hang, qty,
             tien=110_000, tax=10_000, gp=30_000):
    """Một dòng bán với SỐ LƯỢNG tuỳ ý — âm để mô phỏng 赤伝 (hàng trả lại).
    `_mua` ép cứng qty=6 nên không dùng được cho các test cần số lượng khác."""
    import pandas as pd
    from kome.loaders import sales
    b = batch(abs(hash((ma_khach, ngay, ma_hang, qty))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"Q{ma_khach[-4:]}{ngay:%m%d}{ma_hang}", "line_seq": 1,
        "sales_date": ngay, "customer_code": ma_khach, "product_code": ma_hang,
        "pack_code": "02", "case_qty": 1, "qty": qty, "unit_price": 5250,
        "unit_cost": 3210, "amount": tien, "tax_amount": tax,
        "cost": tien - tax - gp, "gross_profit": gp, "paid_amount": 0,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _ton(conn, batch, ma_hang, kho="0001", sl=100, gia=1000, han="2028年06月09日"):
    """Một dòng tồn kho ở ngày chụp HOM_NAY."""
    b = batch(abs(hash((ma_hang, kho, han))) % 70_000 + 1)
    conn.execute(
        """INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name)
           VALUES (%s, %s) ON CONFLICT DO NOTHING""",
        (kho, f"Kho {kho}"))
    conn.execute(
        """INSERT INTO core.fact_inventory_daily
             (snapshot_date, product_code, warehouse_code, pack_code, product_name,
              best_before, shipped_qty, stock_qty, stock_unit_cost, stock_value, batch_id)
           VALUES (%s, %s, %s, '00', %s, %s, 0, %s, %s, %s, %s)""",
        (HOM_NAY, ma_hang, kho, f"Hàng {ma_hang}", han, sl, gia, int(sl * gia), b))
    conn.commit()


def _san_pham(conn, batch, ma_hang, ten="Hàng thử"):
    b = batch(abs(hash(("sp", ma_hang))) % 60_000 + 1)
    conn.execute(
        """INSERT INTO core.dim_product (product_code, product_name, kind_name, batch_id)
           VALUES (%s, %s, 'Gạo', %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma_hang, ten, b))
    conn.commit()


def test_han_su_dung_chu_khong_lam_no_truy_van(conn, batch):
    """[CRITICAL] `賞味期限なし` nghĩa là 'không có hạn sử dụng'. Một `to_date()`
    trần trên cột này làm cả truy vấn nổ và trang trắng — và nó chỉ nổ khi có
    đúng loại hàng đó trong kho, tức sau khi đã triển khai."""
    _san_pham(conn, batch, "K001")
    _ton(conn, batch, "K001", han="賞味期限なし")
    r = conn.execute(
        """SELECT loai_han, han_con_lai FROM mart.ton_hien_tai
           WHERE product_code = 'K001'""").fetchone()
    assert r[0] == "khong_han"
    assert r[1] is None, "hàng không hạn thì không có 'còn lại bao nhiêu ngày'"


def test_han_su_dung_rong_van_dem_duoc(conn, batch):
    """Một lô không rõ hạn phải ĐẾM ĐƯỢC, không được biến mất. Đo thật: 1/177
    dòng tồn hiện tại rỗng hạn."""
    _san_pham(conn, batch, "K002")
    _ton(conn, batch, "K002", han="")
    r = conn.execute(
        "SELECT loai_han FROM mart.ton_hien_tai WHERE product_code='K002'").fetchone()
    assert r[0] == "trong"


def test_han_su_dung_ngay_tinh_duoc_so_ngay_con_lai(conn, batch):
    _san_pham(conn, batch, "K003")
    sau = HOM_NAY + timedelta(days=30)
    _ton(conn, batch, "K003", han=f"{sau.year}年{sau.month:02d}月{sau.day:02d}日")
    _mua(conn, batch, "X0001", HOM_NAY, hang="K003")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT loai_han, han_con_lai FROM mart.ton_hien_tai WHERE product_code='K003'"
    ).fetchone()
    assert r[0] == "ngay" and r[1] == 30


def test_ton_0_ma_khong_ban_gi_90_ngay_thi_KHONG_phai_het_hang(conn, batch):
    """[IMPORTANT] Mã đã ngừng kinh doanh không phải mã cần đặt gấp. Xếp nhầm
    là tạo việc giả mỗi ngày cho người phụ trách kho."""
    _san_pham(conn, batch, "K004")
    _ton(conn, batch, "K004", sl=0)
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K004'").fetchone()
    assert r[0] != "het_hang"


def test_ton_0_ma_CO_ban_gan_day_thi_la_het_hang(conn, batch):
    _san_pham(conn, batch, "K005")
    _ton(conn, batch, "K005", sl=0)
    _ho_so_khach(conn, batch, "KH005", "Quán K005")
    for i in range(5):
        _mua(conn, batch, "KH005", HOM_NAY - timedelta(days=i * 7), hang="K005")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K005'").fetchone()
    assert r[0] == "het_hang"


def test_ma_moi_ra_mat_khong_bao_gio_la_ton_chet(conn, batch):
    """[IMPORTANT] Mã vừa nhập về tuần trước bán chậm là chuyện bình thường.
    Gắn nhãn 'tồn chết' cho nó là xúi người ta xả một mã vừa mua."""
    _san_pham(conn, batch, "K006")
    _ton(conn, batch, "K006", sl=500)
    _ho_so_khach(conn, batch, "KH006", "Quán K006")
    _mua(conn, batch, "KH006", HOM_NAY - timedelta(days=5), hang="K006")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K006'").fetchone()
    assert r[0] != "ton_chet"


def test_ma_ton_nhieu_ban_cham_la_ton_chet(conn, batch):
    _san_pham(conn, batch, "K007")
    _ton(conn, batch, "K007", sl=10_000)
    _ho_so_khach(conn, batch, "KH007", "Quán K007")
    for i in range(3):
        _mua(conn, batch, "KH007", HOM_NAY - timedelta(days=80 + i), hang="K007")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai, du_ban_ngay FROM mart.san_pham_360 WHERE product_code='K007'"
    ).fetchone()
    assert r[0] == "ton_chet"
    # Mẫu số "công bằng cho hàng mới": lần bán đầu 82 ngày trước -> mẫu số
    # least(90, 82+1)=83, không phải 90. so_luong_90n=18 (3 lần x 6 đơn vị).
    assert abs(float(r[1]) - 10_000 * 83 / 18) < 0.01


def test_ma_khong_co_dong_ton_thi_ton_la_NULL_khong_phai_0(conn, batch):
    """[IMPORTANT] "Không biết" khác "bằng không". 90/232 mã không có dòng tồn
    nào; hiện 0 cho chúng là nói rằng kho đã hết, và người đọc sẽ đi đặt hàng."""
    _san_pham(conn, batch, "K008")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT ton FROM mart.san_pham_360 WHERE product_code='K008'").fetchone()
    assert r[0] is None


def test_toc_do_ban_la_trung_binh_90_ngay(conn, batch):
    """Khác `mart.nhip_mua` (trung vị) CÓ CHỦ Ý — xem ghi chú trong 023."""
    _san_pham(conn, batch, "K009")
    _ho_so_khach(conn, batch, "KH009", "Quán K009")
    for i in range(9):                      # 9 lần × 6 đơn vị = 54 trong 90 ngày
        _mua(conn, batch, "KH009", HOM_NAY - timedelta(days=i * 10), hang="K009")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT so_luong_90n, toc_do_ngay FROM mart.toc_do_ban WHERE product_code='K009'"
    ).fetchone()
    assert float(r[0]) == 54.0
    assert abs(float(r[1]) - 54.0 / 90) < 0.001


def test_so_luong_giu_phan_thap_phan(conn, batch):
    """`83.75 ケース` là số thật trong dữ liệu OBC. Ép int là mất 0,75 thùng."""
    _san_pham(conn, batch, "K010")
    _ton(conn, batch, "K010", sl=83.75)
    r = conn.execute(
        "SELECT so_luong FROM mart.ton_hien_tai WHERE product_code='K010'").fetchone()
    assert abs(float(r[0]) - 83.75) < 0.001


def test_ten_kho_lay_tu_dim_warehouse(conn, batch):
    """Bộ lọc kho phải đọc từ bảng, không viết cứng tên. Thêm kho thứ ba thì nó
    phải tự xuất hiện — gói thiết kế viết cứng ba tên KHÔNG có thật trong OBC."""
    _san_pham(conn, batch, "K011")
    _ton(conn, batch, "K011", kho="9999")
    r = conn.execute(
        "SELECT ten_kho FROM mart.ton_hien_tai WHERE product_code='K011'").fetchone()
    assert r[0] == "Kho 9999"


# ---------------------------------------------------------------------------
# Vòng sửa sau review: "không biết tồn" khác "tồn bằng 0" trong CHÍNH
# trang_thai (không chỉ ở cột ton), ngoại lệ "mã mới" không được đè het_hang,
# tốc độ âm do 赤伝, mẫu số 90 cố định thổi phồng mã mới, và loai_han bắt-tất
# sai.
# ---------------------------------------------------------------------------

def test_khong_co_dong_ton_nhung_van_ban_thi_chua_ro_ton_khong_phai_het_hang(conn, batch):
    """[CRITICAL] Một mã không nằm trong bản xuất 在庫一覧 (90/232 mã) mà vẫn
    bán đều không được hiện 'hết hàng, đặt gấp' — đó là khẳng định chắc chắn
    về một con số ta không biết. Phải có nhãn RIÊNG cho 'không biết'."""
    _san_pham(conn, batch, "K012")
    _ho_so_khach(conn, batch, "KH012", "Quán K012")
    _mua(conn, batch, "KH012", HOM_NAY - timedelta(days=3), hang="K012")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT ton, trang_thai FROM mart.san_pham_360 WHERE product_code='K012'"
    ).fetchone()
    assert r[0] is None
    assert r[1] == "chua_ro_ton"


def test_ma_moi_ton_0_van_la_het_hang_khong_phai_du(conn, batch):
    """[CRITICAL] Ngoại lệ 'mã mới ra mắt' chỉ được phép chắn nhãn tồn chết,
    KHÔNG được đè lên hết hàng: một mã ra mắt 20 ngày trước, bán 2 lần, tồn về
    0 vẫn đang cần nhập hàng GẤP, không phải 'đủ hàng'."""
    _san_pham(conn, batch, "K013")
    _ton(conn, batch, "K013", sl=0)
    _ho_so_khach(conn, batch, "KH013", "Quán K013")
    _mua(conn, batch, "KH013", HOM_NAY - timedelta(days=20), hang="K013")
    _mua(conn, batch, "KH013", HOM_NAY - timedelta(days=10), hang="K013")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K013'").fetchone()
    assert r[0] == "het_hang"


def test_toc_do_am_do_hang_tra_lai_khong_bao_gio_la_sap_thieu(conn, batch):
    """[CRITICAL] 赤伝 (hàng trả lại) giữ số ÂM theo luật của dự án, nên tổng
    số lượng 90 ngày có thể ÂM khi cửa sổ đó chỉ toàn hàng trả. toc_do_ngay ÂM
    mà đọc thành 'sắp thiếu' thì giục nhập hàng cho một mã đang chảy ngược."""
    _san_pham(conn, batch, "K014")
    _ton(conn, batch, "K014", sl=500)
    _ho_so_khach(conn, batch, "KH014", "Quán K014")
    _mua(conn, batch, "KH014", HOM_NAY - timedelta(days=200), hang="K014")
    _ban_qty(conn, batch, "KH014", HOM_NAY - timedelta(days=5), "K014", qty=-2)
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai, du_ban_ngay FROM mart.san_pham_360 WHERE product_code='K014'"
    ).fetchone()
    assert r[0] == "ton_chet"
    assert r[1] is None, "tốc độ âm không chia được -- không phải 0, không phải vô cực"


def test_mau_so_dong_khong_thoi_phong_du_ban_ngay_cho_ma_moi(conn, batch):
    """Mẫu số CỐ ĐỊNH 90 (của mart.toc_do_ban) làm tốc độ một mã mới ra mắt
    thấp hơn thật, rồi 'còn đủ bán bao nhiêu ngày' bị thổi phồng đúng bấy
    nhiêu lần -- đẩy một mã đang bán tốt vào nhãn tồn chết."""
    _san_pham(conn, batch, "K015")
    _ton(conn, batch, "K015", sl=200)
    _ho_so_khach(conn, batch, "KH015", "Quán K015")
    _ban_qty(conn, batch, "KH015", HOM_NAY - timedelta(days=20), "K015", qty=10)
    _ban_qty(conn, batch, "KH015", HOM_NAY - timedelta(days=10), "K015", qty=10)
    _ban_qty(conn, batch, "KH015", HOM_NAY, "K015", qty=10)
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai, du_ban_ngay FROM mart.san_pham_360 WHERE product_code='K015'"
    ).fetchone()
    assert r[0] != "ton_chet"
    # Mẫu số động: least(90, 20+1)=21 -> tốc độ = 30/21. Mẫu số 90 cố định
    # (bản trước sửa) sẽ cho 200/(30/90)=600 ngày -> sai sang 'ton_chet'.
    assert abs(float(r[1]) - 200 / (30 / 21)) < 0.01


def test_han_su_dung_khong_doc_duoc_la_khong_ro_khong_phai_khong_han(conn, batch):
    """[CRITICAL] Một chuỗi không khớp regex ngày và không đúng y hệt
    '賞味期限なし' (ví dụ OBC đổi mẫu xuất sang '2028/06/09') là 'không đọc
    được', KHÔNG được ngầm hiểu thành 'không có hạn sử dụng' -- lô đó sẽ biến
    mất khỏi mọi cảnh báo hạn một cách im lặng."""
    _san_pham(conn, batch, "K017")
    _ton(conn, batch, "K017", han="2028/06/09")
    r = conn.execute(
        "SELECT loai_han, han_con_lai FROM mart.ton_hien_tai WHERE product_code='K017'"
    ).fetchone()
    assert r[0] == "khong_ro"
    assert r[1] is None


def test_san_pham_theo_thang_gop_dung_thang_va_ma(conn, batch):
    """View thứ tư -- chưa có test nào trước vòng sửa này. Một lỗi tên cột
    trong GROUP BY sẽ lọt thẳng tới task 2 nếu không canh ở đây."""
    _san_pham(conn, batch, "K016")
    _ho_so_khach(conn, batch, "KH016", "Quán K016")
    _mua(conn, batch, "KH016", HOM_NAY, hang="K016")
    _mua(conn, batch, "KH016", HOM_NAY - timedelta(days=5), hang="K016")
    r = conn.execute(
        """SELECT thang, so_luong, doanh_thu_thuan, lai_gop
           FROM mart.san_pham_theo_thang WHERE product_code='K016'""").fetchone()
    assert r[0] == f"{HOM_NAY:%Y-%m}"
    assert float(r[1]) == 12.0          # 2 lần x 6 đơn vị (mặc định của _mua)
    assert r[2] == 200_000              # 2 x (110.000 - 10.000)
    assert r[3] == 60_000               # 2 x 30.000


# ---------------------------------------------------------------------------
# Vòng sửa lần 2: một hồi quy CRITICAL do chính vòng sửa lần 1 gây ra (`NOT
# moi` trên NULL), cộng công thức "tốc độ theo tuổi mã" cần một cái tên riêng
# thay vì âm thầm khác nghĩa với cột `toc_do_ngay` đã xuất ra, cộng một khe hở
# trong regex một chữ số chưa có test nào canh.
# ---------------------------------------------------------------------------

def test_ma_khong_ban_gi_lau_ngay_van_la_ton_chet_du_khong_co_dong_toc_do_ban(conn, batch):
    """[CRITICAL] Hồi quy do vòng sửa trước: một mã không bán gì trong 90 ngày
    thì KHÔNG có dòng nào trong mart.toc_do_ban. Nếu cờ "mã mới" được tính
    bằng cách JOIN qua view đó, nó sẽ là NULL cho đúng mã cần bị coi là "không
    mới" nhất -- và `NOT NULL` cũng là NULL, nên nhánh tồn chết không chạy,
    rơi thẳng xuống 'du'. Một mã tồn 10.000, bán lần cuối cách đây 200 ngày là
    tồn chết THẬT, không phải 'đủ hàng'."""
    _san_pham(conn, batch, "K018")
    _ton(conn, batch, "K018", sl=10_000)
    _ho_so_khach(conn, batch, "KH018", "Quán K018")
    _mua(conn, batch, "KH018", HOM_NAY - timedelta(days=200), hang="K018")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT trang_thai FROM mart.san_pham_360 WHERE product_code='K018'").fetchone()
    assert r[0] == "ton_chet"


def test_han_su_dung_ngay_mot_chu_so_thang_ngay_van_doc_duoc(conn, batch):
    """Regex vừa được nới thành 1-2 chữ số cho tháng/ngày -- phần vừa nới đó
    chưa có test nào canh trực tiếp bằng đầu vào MỘT chữ số thật (mọi test
    khác chỉ dùng dạng đệm 0 hai chữ số)."""
    _san_pham(conn, batch, "K019")
    dich = date(2028, 6, 9)
    han = f"{dich.year}年{dich.month}月{dich.day}日"        # '2028年6月9日', không đệm 0
    _ton(conn, batch, "K019", han=han)
    _mua(conn, batch, "X0002", HOM_NAY, hang="K019")
    _neo(conn, batch)
    r = conn.execute(
        "SELECT loai_han, han_con_lai FROM mart.ton_hien_tai WHERE product_code='K019'"
    ).fetchone()
    assert r[0] == "ngay"
    assert r[1] == (dich - HOM_NAY).days


def test_han_khong_han_co_khoang_trang_toan_giac_van_nhan_dung(conn, batch):
    """Sửa nhân thể: btrim() trước khi so khớp '賞味期限なし' -- một ô OBC có
    đệm khoảng trắng ở đuôi (kể cả khoảng trắng TOÀN GIÁC／全角, U+3000) không
    được rơi nhầm xuống 'khong_ro'."""
    _san_pham(conn, batch, "K020")
    _ton(conn, batch, "K020", han="賞味期限なし　")     # có dấu cách toàn giác ở cuối
    r = conn.execute(
        "SELECT loai_han FROM mart.ton_hien_tai WHERE product_code='K020'").fetchone()
    assert r[0] == "khong_han"
