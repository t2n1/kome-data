"""Chỉ số của màn Sản phẩm và Kho hàng (migration 023).

Hai thứ được canh kỹ nhất ở đây: **cột `best_before` là TEXT và có giá trị CHỮ**
(`賞味期限なし`) lẫn trong đó, nên một `to_date()` trần sẽ làm cả trang trắng; và
**"không có dòng tồn" khác "tồn bằng 0"** — nhầm hai thứ đó là xếp một mã chưa
bao giờ nhập kho vào danh sách cần đặt hàng gấp.
"""
from datetime import date, timedelta

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY


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
