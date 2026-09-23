"""Tầng Python của màn Sản phẩm và màn Kho hàng (`kome/san_pham.py`).

Ba thứ được canh kỹ nhất ở đây:

1. **"Không biết" khác "bằng không".** `ton` là NULL cho 90/232 mã không có dòng
   nào trong 在庫一覧. Một `or 0` ở tầng Python biến "chưa từng nhập kho" thành
   "kho đã hết" — và người đọc sẽ đi đặt hàng.
2. **Số lượng CÓ phần thập phân** (`83.75 ケース`). Ép `int` ở bất kỳ tầng nào là
   mất 0,75 thùng.
3. **Ngân sách vòng hỏi.** Đo thật: round-trip rỗng tới pooler Tokyo 47 ms, một
   lượt hỏi thật ~260 ms. Ba test đếm ĐẾM LÚC CHẠY (bọc `conn.execute`), không
   đọc mã nguồn — một câu lệnh sinh động vẫn phải bị đếm.
"""
from datetime import timedelta

from kome import khach_hang as KH
from kome import san_pham as SP
from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY
from tests.test_mart_san_pham import _ban_qty, _san_pham, _ton


def _ton_ngay(conn, batch, ma_hang, ngay, kho="0001", sl=100, gia=1000,
              han="2028年06月09日"):
    """Một dòng tồn ở ngày chụp TUỲ Ý — `_ton` ép cứng HOM_NAY nên không dùng
    được cho test "ngày chụp mới nhất"."""
    b = batch(abs(hash((ma_hang, kho, ngay, han))) % 70_000 + 1)
    conn.execute(
        """INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name)
           VALUES (%s, %s) ON CONFLICT DO NOTHING""", (kho, f"Kho {kho}"))
    conn.execute(
        """INSERT INTO core.fact_inventory_daily
             (snapshot_date, product_code, warehouse_code, pack_code, product_name,
              best_before, shipped_qty, stock_qty, stock_unit_cost, stock_value, batch_id)
           VALUES (%s, %s, %s, '00', %s, %s, 0, %s, %s, %s, %s)""",
        (ngay, ma_hang, kho, f"Hàng {ma_hang}", han, sl, gia, int(sl * gia), b))
    conn.commit()


def _gia(conn, batch, ma_hang, bac, gia, quy_cach="02", tu_ngay="2026-01-01"):
    b = batch(abs(hash(("g", ma_hang, bac, quy_cach, tu_ngay))) % 40_000 + 250_000)
    conn.execute(
        """INSERT INTO core.fact_price_list
             (product_code, pack_code, price_level, valid_from, price_ex_tax,
              price_in_tax, unit_cost, batch_id)
           VALUES (%s, %s, %s, %s, %s, %s, 0, %s)""",
        (ma_hang, quy_cach, bac, tu_ngay, gia, gia, b))
    conn.commit()


def _dem_truy_van(conn, monkeypatch):
    """Bọc `conn.execute` và đếm LÚC CHẠY. Đếm bằng AST không bắt được một câu
    lệnh chạy trong vòng lặp — đúng cái hình dạng mà ngân sách này cấm."""
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    return dem


# ---------------------------------------------------------------------------
# Ngân sách vòng hỏi — ba con số của đặc tả §5.5
# ---------------------------------------------------------------------------

def test_danh_sach_san_pham_khong_qua_2_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Mỗi vòng hỏi qua pooler Tokyo mất ~47 ms chỉ riêng mạng.
    Trang chậm dần từng đợt là cách nó chết mà không ai thấy ngày nào nó chết."""
    _san_pham(conn, batch, "P001")
    _ton(conn, batch, "P001", sl=100)
    _ho_so_khach(conn, batch, "KP01", "Quán P001")
    _mua(conn, batch, "KP01", HOM_NAY - timedelta(days=3), hang="P001")
    _neo(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    SP.danh_sach(conn)
    assert dem["n"] <= 2, f"danh_sach() chạy {dem['n']} truy vấn"


def test_ho_so_san_pham_khong_qua_5_truy_van(conn, batch, monkeypatch):
    _san_pham(conn, batch, "P002")
    _ton(conn, batch, "P002", sl=100)
    _ho_so_khach(conn, batch, "KP02", "Quán P002")
    _mua(conn, batch, "KP02", HOM_NAY - timedelta(days=3), hang="P002")
    _gia(conn, batch, "P002", "03", 5250)
    _neo(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    # Giữ kết quả và khẳng định nó KHÔNG rỗng: một hồi quy làm câu đầu không
    # khớp dòng nào thì hàm thoát sớm bằng `return None` sau ĐÚNG MỘT truy
    # vấn, và một test chỉ đếm sẽ xanh rỡ trong khi trang đã trắng.
    h = SP.ho_so(conn, "P002")
    assert h is not None and h.sp.ma == "P002"
    assert dem["n"] <= 5, f"ho_so() chạy {dem['n']} truy vấn"


def test_kho_hang_khong_qua_2_truy_van(conn, batch, monkeypatch):
    _san_pham(conn, batch, "P003")
    _ton(conn, batch, "P003", sl=100)
    _ho_so_khach(conn, batch, "KP03", "Quán P003")
    _mua(conn, batch, "KP03", HOM_NAY - timedelta(days=3), hang="P003")
    _neo(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    k = SP.kho_hang(conn)
    assert k.dong, "đếm một hàm trả về rỗng thì không đếm gì cả"
    assert dem["n"] <= 2, f"kho_hang() chạy {dem['n']} truy vấn"


def test_kho_hang_co_loc_van_khong_qua_2_truy_van(conn, batch, monkeypatch):
    """Hai bộ lọc thêm mảnh WHERE vào cả hai câu lệnh — chúng không được phép
    đẻ ra một lượt hỏi thứ ba."""
    _san_pham(conn, batch, "P003B")
    _ton(conn, batch, "P003B", sl=100)
    _neo(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    SP.kho_hang(conn, kho="0001", loc="chua_ro_ton")
    assert dem["n"] <= 2, f"kho_hang(có lọc) chạy {dem['n']} truy vấn"


# ---------------------------------------------------------------------------
# "Không biết" khác "bằng không", và số lượng có phần thập phân
# ---------------------------------------------------------------------------

def test_ma_khong_co_dong_ton_thi_ton_la_None_khong_phai_0(conn, batch):
    """[CRITICAL] 90/232 mã không có dòng nào trong 在庫一覧. Một `or 0` ở tầng
    Python biến "chưa từng nhập kho" thành "kho đã hết" — trang hiện 0 và người
    đọc đi đặt hàng cho một mã có thể đang đầy kho."""
    _san_pham(conn, batch, "P004")
    _neo(conn, batch)
    t = SP.danh_sach(conn)
    sp = next(h for h in t.hang if h.ma == "P004")
    assert sp.ton is None, "None phải đi qua tầng Python nguyên vẹn"
    assert sp.trang_thai == "chua_ro_ton"
    assert SP.TRANG_THAI_TON["chua_ro_ton"][0] != SP.TRANG_THAI_TON["het_hang"][0]


def test_so_luong_giu_phan_thap_phan_qua_ca_ba_ham(conn, batch):
    """`83.75 ケース` là số thật trong dữ liệu OBC. Ép int là mất 0,75 thùng."""
    _san_pham(conn, batch, "P005")
    _ton(conn, batch, "P005", sl=83.75)
    _neo(conn, batch)

    sp = next(h for h in SP.danh_sach(conn).hang if h.ma == "P005")
    assert abs(float(sp.ton) - 83.75) < 0.001

    h = SP.ho_so(conn, "P005")
    assert abs(float(h.ton[0]["so_luong"]) - 83.75) < 0.001

    k = SP.kho_hang(conn)
    assert abs(float(k.dong[0]["so_luong"]) - 83.75) < 0.001


# ---------------------------------------------------------------------------
# Kho hàng: ngày chụp, danh sách kho, cận hạn
# ---------------------------------------------------------------------------

def test_kho_hang_lay_dung_ngay_chup_moi_nhat(conn, batch):
    """[IMPORTANT] Trang phải NÓI RA ngày chụp. Hôm nay chỉ có một ngày nên
    không ai thấy khác biệt; ngày mai có nhiều ngày thì một trang không ghi
    ngày sẽ được đọc như "bây giờ" trong khi nó là ảnh chụp 13:30 hôm trước."""
    _san_pham(conn, batch, "P006")
    _ton_ngay(conn, batch, "P006", HOM_NAY - timedelta(days=5), sl=10)
    _ton_ngay(conn, batch, "P006", HOM_NAY, sl=7)
    _neo(conn, batch)
    k = SP.kho_hang(conn)
    assert k.ngay_chup == HOM_NAY
    assert len(k.dong) == 1, "chỉ ảnh chụp mới nhất, không cộng dồn hai ngày"
    assert float(k.dong[0]["so_luong"]) == 7


def test_danh_sach_kho_lay_tu_du_lieu_khong_viet_cung(conn, batch):
    """Gói thiết kế viết cứng ba kho KHÔNG có thật (Osaka/Nagoya/Kho lạnh).
    Thêm một kho trong OBC thì bộ lọc phải tự có nó."""
    _san_pham(conn, batch, "P007")
    _ton(conn, batch, "P007", kho="9999")
    _neo(conn, batch)
    k = SP.kho_hang(conn)
    assert ("9999", "Kho 9999") in k.ds_kho


def test_loc_theo_kho_chi_giu_dong_cua_kho_do(conn, batch):
    _san_pham(conn, batch, "P008")
    _ton(conn, batch, "P008", kho="0001", sl=5)
    _ton(conn, batch, "P008", kho="1002", sl=9)
    _neo(conn, batch)
    k = SP.kho_hang(conn, kho="1002")
    assert [d["kho"] for d in k.dong] == ["1002"]
    # Bảng "giá trị theo kho" là Ô ĐIỀU KHIỂN của chính bộ lọc kho — nó KHÔNG
    # tự lọc theo mình, kẻo bấm vào một kho xong không còn đường quay lại.
    assert {t["ma"] for t in k.theo_kho} == {"0001", "1002"}


def test_loc_trang_thai_lam_co_lai_CA_bang_ton_lan_gia_tri_theo_kho(conn, batch):
    """[IMPORTANT] Bộ lọc trạng thái phải kéo theo MỌI con số nội dung trên
    màn, không chỉ cái bảng. Chọn "tồn chết" mà ô "giá trị theo kho" vẫn hiện
    tổng của toàn bộ kho là hai con số cạnh nhau trên một màn hình, không con
    số nào nói mình đang nói về tập nào."""
    _san_pham(conn, batch, "P040")                      # -> ton_chet
    _ton(conn, batch, "P040", sl=10, gia=1000)          # giá trị 10.000
    _ho_so_khach(conn, batch, "KP40", "Quán P040")
    _mua(conn, batch, "KP40", HOM_NAY - timedelta(days=200), hang="P040")
    _san_pham(conn, batch, "P041")                      # -> sap_thieu
    _ton(conn, batch, "P041", sl=5, gia=1000)           # giá trị 5.000
    _ho_so_khach(conn, batch, "KP41", "Quán P041")
    for i in range(5):
        _mua(conn, batch, "KP41", HOM_NAY - timedelta(days=i * 7), hang="P041")
    _neo(conn, batch)

    k = SP.kho_hang(conn)
    assert {d["ma"]: d["trang_thai"] for d in k.dong} == {
        "P040": "ton_chet", "P041": "sap_thieu"}
    assert [t["gia_tri"] for t in k.theo_kho] == [15_000]

    k = SP.kho_hang(conn, loc="ton_chet")
    assert [d["ma"] for d in k.dong] == ["P040"]
    assert [t["gia_tri"] for t in k.theo_kho] == [10_000], \
        "giá trị theo kho phải nói về CÙNG tập dòng mà bảng đang hiện"
    assert k.o_tong_quan["gia_tri_ton_chet"] == 10_000

    k = SP.kho_hang(conn, loc="sap_thieu")
    assert [t["gia_tri"] for t in k.theo_kho] == [5_000]
    assert k.o_tong_quan["gia_tri_ton_chet"] == 0
    # Bảng "giá trị theo kho" vẫn là ô ĐIỀU KHIỂN của bộ lọc kho, nên nó không
    # được tự lọc theo `kho` — bấm một kho xong phải còn đường quay lại.
    assert [t["ma"] for t in SP.kho_hang(conn, kho="0001").theo_kho] == ["0001"]


def test_loc_theo_kho_lam_co_lai_ca_khoi_can_han(conn, batch):
    """Khối cận hạn là khối NỘI DUNG, không điều khiển gì — nó phải theo bộ
    lọc kho, và ô đếm "số lô cận hạn" phải đi theo nó."""
    _san_pham(conn, batch, "P042")
    _san_pham(conn, batch, "P043")
    sap = HOM_NAY + timedelta(days=10)
    han = f"{sap.year}年{sap.month:02d}月{sap.day:02d}日"
    _ton(conn, batch, "P042", kho="0001", han=han)
    _ton(conn, batch, "P043", kho="1002", han=han)
    _neo(conn, batch)

    k = SP.kho_hang(conn)
    assert {d["ma"] for d in k.can_han} == {"P042", "P043"}
    assert k.o_tong_quan["can_han"] == 2

    k = SP.kho_hang(conn, kho="1002")
    assert [d["ma"] for d in k.can_han] == ["P043"]
    assert k.o_tong_quan["can_han"] == 1, "ô đếm phải đi theo chính bảng nó gắn nhãn"


def test_lo_da_qua_han_tach_khoi_lo_sap_het_han(conn, batch):
    """[IMPORTANT] Với hàng thực phẩm, "đã quá hạn" và "sắp hết hạn" là hai
    việc khác nhau. Trộn chung thì một lô quá hạn còn sót trong bản xuất đứng
    vĩnh viễn ở đầu bảng (xếp tăng dần) và cộng vào ô đếm mãi mãi — cái cần xử
    lý NGAY bị chôn trong danh sách cái cần theo dõi."""
    _san_pham(conn, batch, "P044")
    truoc = HOM_NAY - timedelta(days=5)
    _ton(conn, batch, "P044",
         han=f"{truoc.year}年{truoc.month:02d}月{truoc.day:02d}日")
    _neo(conn, batch)
    k = SP.kho_hang(conn)
    assert [d["ma"] for d in k.qua_han] == ["P044"]
    assert k.qua_han[0]["han_con_lai"] == -5
    assert k.can_han == [] and k.o_tong_quan["can_han"] == 0


def test_lo_can_han_khop_kho_hang_khong_dung_san_pham_360(conn, batch, monkeypatch):
    """[IMPORTANT] Soát hiệu năng đợt 5b: `lo_can_han()` phải trả về ĐÚNG
    những lô mà `kho_hang(conn).can_han[:n]`/`len(kho_hang(conn).qua_han)` đã
    trả (cùng lô, cùng thứ tự, cùng số quá hạn) — nhưng KHÔNG được đụng
    `mart.san_pham_360`, view nặng nhất của mart. `kho_hang()` vật hoá view
    đó hai lần chỉ để phục vụ đúng 5 dòng cận hạn của dashboard `/`."""
    _san_pham(conn, batch, "P200", ten="Cận hạn 1")
    _san_pham(conn, batch, "P201", ten="Cận hạn 2")
    # P202 CỐ Ý không có dòng trong core.dim_product — ca hiếm "mã tồn kho
    # không nằm trong 商品マスタ" mà cả kho_hang() lẫn lo_can_han() phải rơi về
    # hiện product_code, KHÔNG lỗi ra.
    _san_pham(conn, batch, "P203")  # sẽ quá hạn
    truoc = HOM_NAY - timedelta(days=5)
    sap1 = HOM_NAY + timedelta(days=3)
    sap2 = HOM_NAY + timedelta(days=8)
    sap3 = HOM_NAY + timedelta(days=10)
    _ton(conn, batch, "P200", han=f"{sap1.year}年{sap1.month:02d}月{sap1.day:02d}日")
    _ton(conn, batch, "P201", han=f"{sap2.year}年{sap2.month:02d}月{sap2.day:02d}日")
    _ton(conn, batch, "P202", han=f"{sap3.year}年{sap3.month:02d}月{sap3.day:02d}日")
    _ton(conn, batch, "P203",
         han=f"{truoc.year}年{truoc.month:02d}月{truoc.day:02d}日")
    _neo(conn, batch)

    k = SP.kho_hang(conn)
    assert [d["ma"] for d in k.can_han] == ["P200", "P201", "P202"]
    assert len(k.qua_han) == 1

    dem = {"n": 0, "cham_sp360": False}
    that = conn.execute

    def demo(sql, *a, **kw):
        dem["n"] += 1
        if isinstance(sql, str) and "san_pham_360" in sql:
            dem["cham_sp360"] = True
        return that(sql, *a, **kw)

    monkeypatch.setattr(conn, "execute", demo)
    can_han, so_qua_han = SP.lo_can_han(conn, gioi_han=5)
    assert dem["n"] == 1, f"lo_can_han() phải chạy ĐÚNG 1 lượt hỏi, chạy {dem['n']}"
    assert not dem["cham_sp360"], "lo_can_han() KHÔNG được đụng mart.san_pham_360"

    assert [d["ma"] for d in can_han] == [d["ma"] for d in k.can_han[:5]]
    assert [d["han_con_lai"] for d in can_han] == \
        [d["han_con_lai"] for d in k.can_han[:5]]
    assert so_qua_han == len(k.qua_han)
    # Tên hàng phải khớp CHÍNH XÁC những gì kho_hang() hiện, kể cả mã không có
    # tên trong core.dim_product (san_pham_360 rơi về chính mã).
    ten_kho_hang = {d["ma"]: d["ten"] for d in k.can_han}
    for d in can_han:
        assert d["ten"] == ten_kho_hang[d["ma"]]


def test_nhan_hien_thi_cung_mot_KIEU_o_ca_hai_man(conn, batch):
    """`nhan_trang_thai` phải là CHUỖI ở cả hai màn. Cùng một tên trả hai kiểu
    khác nhau là bắt template viết `d.nhan_trang_thai[0]` ở màn này và
    `sp.nhan_trang_thai` ở màn kia — rồi một ngày viết nhầm chỗ."""
    _san_pham(conn, batch, "P045")
    _ton(conn, batch, "P045", sl=50)
    _neo(conn, batch)
    sp = next(h for h in SP.danh_sach(conn).hang if h.ma == "P045")
    d = SP.kho_hang(conn).dong[0]
    assert isinstance(sp.nhan_trang_thai, str) and isinstance(sp.mau, str)
    assert d["nhan_trang_thai"] == sp.nhan_trang_thai and d["mau"] == sp.mau
    assert isinstance(d["nhan_han"], str) and isinstance(d["mau_han"], str)


def test_can_han_chi_gom_lo_co_HAN_THAT(conn, batch):
    """[CRITICAL] `賞味期限なし` là hàng KHÔNG có hạn dùng — xếp nó vào danh sách
    cần xả là sai nghiệp vụ. `khong_ro` ("ta không đọc được") phải hiện KHÁC
    `khong_han` ("hàng này không có hạn"), chứ không im lặng trộn làm một."""
    _san_pham(conn, batch, "P009")
    _san_pham(conn, batch, "P010")
    _san_pham(conn, batch, "P011")
    _san_pham(conn, batch, "P012")
    sap = HOM_NAY + timedelta(days=10)
    _ton(conn, batch, "P009", han=f"{sap.year}年{sap.month:02d}月{sap.day:02d}日")
    _ton(conn, batch, "P010", han="賞味期限なし")
    _ton(conn, batch, "P011", han="")
    _ton(conn, batch, "P012", han="2028/06/09")
    _neo(conn, batch)

    k = SP.kho_hang(conn)
    assert [d["ma"] for d in k.can_han] == ["P009"]
    assert k.o_tong_quan["can_han"] == 1
    # Cả bốn loại hạn phải ĐẾM ĐƯỢC ở bảng tồn, không lô nào biến mất.
    assert {d["ma"]: d["loai_han"] for d in k.dong} == {
        "P009": "ngay", "P010": "khong_han", "P011": "trong", "P012": "khong_ro"}
    assert SP.LOAI_HAN["khong_ro"][0] != SP.LOAI_HAN["khong_han"][0]


def test_o_tong_quan_dem_du_bon_o(conn, batch):
    _san_pham(conn, batch, "P013")
    _ton(conn, batch, "P013", sl=0)
    _ho_so_khach(conn, batch, "KP13", "Quán P013")
    _mua(conn, batch, "KP13", HOM_NAY - timedelta(days=3), hang="P013")
    _neo(conn, batch)
    k = SP.kho_hang(conn)
    assert set(k.o_tong_quan) == {"het_hang", "sap_thieu", "can_han",
                                  "gia_tri_ton_chet"}
    assert k.o_tong_quan["het_hang"] == 1


# ---------------------------------------------------------------------------
# Danh sách: bộ đếm, bộ lọc, sắp xếp
# ---------------------------------------------------------------------------

def test_dem_trang_thai_khong_theo_loc_nhung_tong_thi_co(conn, batch):
    """Bộ đếm trạng thái LÀ nhãn của dải chip lọc — nó tự lọc theo mình thì
    bấm một chip xong các con số khác về 0 hết, không ai quay lại được. `tong`
    thì ngược lại: nó phải là số dòng mà chính bảng bên dưới đang hiện."""
    _san_pham(conn, batch, "P014")          # không có dòng tồn -> chua_ro_ton
    _san_pham(conn, batch, "P015")
    _ton(conn, batch, "P015", sl=0)
    _ho_so_khach(conn, batch, "KP15", "Quán P015")
    _mua(conn, batch, "KP15", HOM_NAY - timedelta(days=3), hang="P015")
    _neo(conn, batch)

    t = SP.danh_sach(conn, loc="het_hang")
    assert [h.ma for h in t.hang] == ["P015"]
    assert t.tong == 1
    assert t.dem_trang_thai["chua_ro_ton"] == 1, "bộ đếm KHÔNG theo `loc`"
    assert t.dem_trang_thai["het_hang"] == 1


def test_tim_kiem_theo_ma_va_theo_ten(conn, batch):
    _san_pham(conn, batch, "P016", ten="Gạo ST25")
    _san_pham(conn, batch, "P017", ten="Nước mắm")
    _neo(conn, batch)
    assert [h.ma for h in SP.danh_sach(conn, tim="ST25").hang] == ["P016"]
    assert [h.ma for h in SP.danh_sach(conn, tim="P017").hang] == ["P017"]


def test_sap_xep_chi_nhan_gia_tri_trong_danh_sach_trang(conn, batch):
    """[CRITICAL] Trang này sắp nằm trên Internet. Ghép tham số URL vào SQL là
    đường mở cho SQL injection — giá trị lạ phải rơi về mặc định, không bao giờ
    đi vào câu lệnh."""
    _san_pham(conn, batch, "P018")
    _neo(conn, batch)
    t = SP.danh_sach(conn, sap="doanh_thu_thuan; DROP TABLE core.dim_product --")
    assert [h.ma for h in t.hang] == ["P018"]
    assert conn.execute(
        "SELECT count(*) FROM core.dim_product").fetchone()[0] == 1


def test_sau_nhan_trang_thai_ton_va_bon_loai_han():
    """`trang_thai` có SÁU nhãn, không phải bốn — `chua_ro_ton` ("không biết
    tồn") và `ngung` ("đã ngừng kinh doanh") là hai nhãn bổ sung của migration
    023. Thiếu một nhãn thì trang hiện mã thô cho 90/232 mã."""
    assert set(SP.TRANG_THAI_TON) == {"chua_ro_ton", "ngung", "het_hang",
                                      "sap_thieu", "ton_chet", "du"}
    assert set(SP.LOAI_HAN) == {"ngay", "khong_han", "trong", "khong_ro"}


# ---------------------------------------------------------------------------
# Hồ sơ một mã hàng
# ---------------------------------------------------------------------------

def test_ho_so_ma_khong_ton_tai_tra_None(conn, batch):
    _neo(conn, batch)
    assert SP.ho_so(conn, "KHONG-CO") is None


def test_ho_so_co_du_nam_khoi(conn, batch):
    """Năm khối phải có DỮ LIỆU THẬT, không chỉ có mặt dưới dạng danh sách
    rỗng — một khối luôn rỗng thì không ai phát hiện nó hỏng."""
    _san_pham(conn, batch, "P019", ten="Gạo ST25")
    _ton(conn, batch, "P019", sl=300)
    _gia(conn, batch, "P019", "03", 5250, quy_cach="02", tu_ngay="2026-06-01")
    _gia(conn, batch, "P019", "03", 460, quy_cach="00", tu_ngay="2026-01-01")
    # Khách đang mua: mua gần đây.
    _ho_so_khach(conn, batch, "KP19", "Quán đang mua")
    for i in range(3):
        _mua(conn, batch, "KP19", HOM_NAY - timedelta(days=i * 7), hang="P019")
    # Khách đã ngừng: mua đều 3 lần (nhịp 7 ngày) rồi im 120 ngày — hơn mười
    # bảy lần nhịp riêng của chính cặp khách–mã này.
    _ho_so_khach(conn, batch, "KP20", "Quán đã ngừng")
    for i in range(3):
        _mua(conn, batch, "KP20", HOM_NAY - timedelta(days=120 + i * 7), hang="P019")
    _neo(conn, batch)

    h = SP.ho_so(conn, "P019")
    assert h.sp.ma == "P019" and h.sp.ten == "Gạo ST25"
    assert [m["thang"] for m in h.thang] == sorted(m["thang"] for m in h.thang)
    assert [k["ma"] for k in h.khach_mua] == ["KP19"]
    assert [k["ma"] for k in h.khach_ngung] == ["KP20"]
    assert [t["kho"] for t in h.ton] == ["0001"]
    # Bảng giá: MỖI 荷姿 một dòng, và nhãn quy cách phải đọc được.
    assert sorted(g["quy_cach"] for g in h.bac_gia) == \
        sorted([SP.QUY_CACH["00"], SP.QUY_CACH["02"]])


def test_bac_gia_chi_hien_dong_MOI_NHAT_cua_tung_quy_cach(conn, batch):
    """[CRITICAL] core.fact_price_list giữ LỊCH SỬ giá — mỗi lần nạp master là
    một dòng MỚI. Không lọc thì sau ba lần nạp, một bậc giá hiện ba con số khác
    nhau dưới nhãn "giá đáng lẽ phải bán", trên đúng màn hình người ta nhìn
    TRƯỚC KHI báo giá cho khách.

    Hai dòng phải khác `valid_from` thật — hai dòng cùng ngày thì DISTINCT ON
    chẳng phải chọn gì, và bỏ hẳn nó đi test vẫn xanh."""
    _san_pham(conn, batch, "P022")
    _gia(conn, batch, "P022", "03", 5000, quy_cach="02", tu_ngay="2026-01-01")
    _gia(conn, batch, "P022", "03", 5250, quy_cach="02", tu_ngay="2026-06-01")
    _gia(conn, batch, "P022", "03", 460, quy_cach="00", tu_ngay="2026-01-01")
    _neo(conn, batch)

    bg = SP.ho_so(conn, "P022").bac_gia
    assert len(bg) == 2, "mỗi (bậc, quy cách) đúng MỘT dòng, không phải cả lịch sử"
    assert sorted((g["quy_cach"], g["gia"]) for g in bg) == sorted(
        [(SP.QUY_CACH["02"], 5250), (SP.QUY_CACH["00"], 460)])


def test_khach_ngung_mua_ma_nay_so_voi_NHIP_RIENG_khong_nguong_chung(conn, batch):
    """[CRITICAL] Bất biến của cả dự án: trạng thái quan hệ so với nhịp mua
    RIÊNG, không với một ngưỡng chung. Đo thật (đợt 3): ngưỡng chung 90 ngày bỏ
    sót 49 khách đang rời đi và báo động nhầm 34 khách vẫn mua bình thường.

    Hai khách dưới đây nằm HAI PHÍA của ranh giới thật mà lại CÙNG PHÍA của
    ngưỡng 90 ngày — nên một cài đặt dùng 90 sẽ xếp cả hai vào một rổ."""
    _san_pham(conn, batch, "P023")
    # Mua 7 ngày/lần, im 60 ngày = 8,5 lần nhịp -> ĐÃ NGỪNG mua mã này.
    # Ngưỡng chung 90 ngày sẽ bảo khách này "vẫn đang mua".
    _ho_so_khach(conn, batch, "KP23", "Quán mua dày")
    for i in range(4):
        _mua(conn, batch, "KP23", HOM_NAY - timedelta(days=60 + i * 7), hang="P023")
    # Mua 120 ngày/lần, im 100 ngày = chưa tới một nhịp -> VẪN ĐANG MUA.
    # Ngưỡng chung 90 ngày sẽ bảo khách này "đã ngừng".
    _ho_so_khach(conn, batch, "KP24", "Quán mua thưa")
    for i in range(4):
        _mua(conn, batch, "KP24", HOM_NAY - timedelta(days=100 + i * 120), hang="P023")
    _neo(conn, batch)

    h = SP.ho_so(conn, "P023")
    assert [k["ma"] for k in h.khach_ngung] == ["KP23"]
    assert [k["ma"] for k in h.khach_mua] == ["KP24"]


def test_hai_man_tra_loi_GIONG_NHAU_ve_mot_cap_khach_ma(conn, batch):
    """[CRITICAL] "Cặp (khách, mã) đã ngừng" là MỘT khái niệm, nên hai màn phải
    trả lời GIỐNG NHAU về cùng một cặp.

    Trước migration 024 có hai công thức: /khach-hang/{mã} dùng ngưỡng CHUNG
    (`hom_nay - lan_cuoi > 90`), /san-pham/{mã} dùng nhịp RIÊNG. Hai ca dưới
    đây nằm hai phía của ranh giới thật và CÙNG PHÍA của ngưỡng 90 — nên ngưỡng
    chung trả lời NGƯỢC LẠI nhịp riêng ở CẢ HAI ca, và người bán mở hai màn
    cạnh nhau không có cách nào biết tin màn nào.

    Nay cả hai ĐỌC mart.khach_mat_hang.trang_thai_cap."""
    _san_pham(conn, batch, "P025")
    # Mua 7 ngày/lần, im 60 ngày = 8,5 lần nhịp -> ĐÃ NGỪNG.
    # Ngưỡng chung 90 ngày nói ngược: "vẫn đang mua".
    _ho_so_khach(conn, batch, "KP25", "Quán mua dày")
    for i in range(4):
        _mua(conn, batch, "KP25", HOM_NAY - timedelta(days=60 + i * 7), hang="P025")
    # Mua 120 ngày/lần, im 100 ngày = chưa tới một nhịp -> VẪN ĐANG MUA.
    # Ngưỡng chung 90 ngày nói ngược: "đã ngừng".
    _ho_so_khach(conn, batch, "KP26", "Quán mua thưa")
    for i in range(4):
        _mua(conn, batch, "KP26", HOM_NAY - timedelta(days=100 + i * 120), hang="P025")
    _neo(conn, batch)

    sp = SP.ho_so(conn, "P025")
    assert [k["ma"] for k in sp.khach_ngung] == ["KP25"]
    assert [k["ma"] for k in sp.khach_mua] == ["KP26"]

    day = KH.ho_so(conn, "KP25")
    thua = KH.ho_so(conn, "KP26")
    assert "P025" in {m["ma"] for m in day.da_ngung_mua}, \
        "/khach-hang/{mã} nói 'vẫn mua' về đúng cặp mà /san-pham/{mã} nói 'đã ngừng'"
    assert "P025" not in {m["ma"] for m in thua.da_ngung_mua}, \
        "/khach-hang/{mã} nói 'đã ngừng' về đúng cặp mà /san-pham/{mã} nói 'vẫn mua'"
    # Hai khối của CÙNG một trang là hai dải RỜI NHAU, không chồng nhau: mã đã
    # vào "đã ngừng mua" thì không được nằm luôn ở "tháng này chưa mua".
    assert "P025" not in {m["ma"] for m in day.chua_mua_thang}


def test_khach_da_dong_cua_khong_lot_vao_khoi_goi_lai_nao(conn, batch):
    """[CRITICAL] Bất biến của CLAUDE.md: khách OBC đã đánh dấu ※廃業※ /
    ※取引停止※ (281/2.077 khách) KHÔNG BAO GIỜ vào danh sách gọi lại. Doanh
    nghiệp đã phá sản thì im lặng là đúng, không phải bất thường.

    mart.khach_nhom_viec có cổng đó từ migration 016, nhưng mart.khach_mat_hang
    thì KHÔNG — nên /can-xu-ly đúng trong khi khối "Khách đã ngừng mua mã này"
    của /san-pham/{mã} vẫn gọi tên một công ty đã đóng cửa. 024 đưa cổng đó vào
    chính định nghĩa `trang_thai_cap` (giá trị `'khong_goi'`).

    Và LỊCH SỬ không được mất theo: hồ sơ của chính khách đó vẫn phải hiện bảng
    mặt hàng. `trang_thai_cap` là một CỘT, không phải bộ lọc dòng của view."""
    _san_pham(conn, batch, "P026")
    _ho_so_khach(conn, batch, "KD01", "※廃業・精算※ QUAN DA DONG CUA")
    # Mua 7 ngày/lần rồi im 60 ngày: đúng hình dạng "đã ngừng" của ca trên.
    for i in range(4):
        _mua(conn, batch, "KD01", HOM_NAY - timedelta(days=60 + i * 7), hang="P026")
    _neo(conn, batch)

    # /san-pham/{mã}: không khối nào của trang bán hàng được nhắc tới họ.
    sp = SP.ho_so(conn, "P026")
    assert [k["ma"] for k in sp.khach_ngung] == []
    assert [k["ma"] for k in sp.khach_mua] == [], \
        "chặn khỏi khối 'đã ngừng' mà lại rơi sang khối 'ĐANG mua' là tệ hơn"

    # /khach-hang/{mã}: hai khối gọi lại rỗng, nhưng lịch sử còn nguyên.
    kh = KH.ho_so(conn, "KD01")
    assert [m["ma"] for m in kh.da_ngung_mua] == []
    assert [m["ma"] for m in kh.chua_mua_thang] == []
    assert "P026" in {m["ma"] for m in kh.mat_hang}, \
        "lọc dòng ở view thì hồ sơ khách ※廃業※ trắng trơn — phải là CỘT"


def test_cap_cua_khach_da_dong_cua_mang_NHAN_RIENG_khong_phai_phu_dinh(conn, batch):
    """[CRITICAL] HÌNH DẠNG của định nghĩa, không chỉ kết quả của nó.

    Bản đầu của migration 024 là một boolean `ngung_mua` GÓI cổng ※廃業※ vào
    bên trong (`tre_ngay >= nhip_ngay AND NOT da_ngung`). Boolean đó không phủ
    định được: `NOT ngung_mua` LUÔN đúng với khách đã đóng cửa, nên mọi khối
    viết "phần còn lại" bằng `NOT ngung_mua` lặng lẽ nhận lại trọn 281 khách đã
    phá sản — và ba chỗ Python phải tự JOIN `da_ngung` để đắp tay lại.

    Nay là một NHÃN ba giá trị và mỗi khối so BẰNG với nhãn của mình, nên khách
    ※…※ mang `'khong_goi'` — một giá trị RIÊNG, không thuộc khối nào — mà không
    khối nào phải biết ※廃業※ là gì. Test này khoá đúng điều đó ở tầng CSDL: nếu
    ai đó gộp `'khong_goi'` trở lại vào `'mua'` hay `'ngung'`, hoặc đổi cột về
    boolean, dòng dưới đây đỏ trước khi trang kịp gọi tên một công ty đã phá
    sản.

    KS02 là CHỨNG: cùng mã, cùng nhịp, nhưng còn sống và vẫn mua đều. Không có
    nó thì "khối 'đang mua' rỗng" có thể chỉ vì khối đó hỏng, và mọi khẳng định
    ở đây đúng một cách vô nghĩa."""
    _san_pham(conn, batch, "P027")
    # ※取引停止※ — một trong bảy cụm mà 016 nhận là "đã đóng cửa / ngừng giao
    # dịch", và KHÔNG phải cụm ※廃業※ mà test trên đã dùng: cổng là DANH SÁCH TỪ
    # KHOÁ, không phải một chuỗi.
    _ho_so_khach(conn, batch, "KD02", "※取引停止※ QUAN BI NGUNG GIAO DICH")
    # Nhịp 7 ngày, im 60 ngày = 8,5 lần nhịp: đúng hình dạng của `'ngung'` —
    # nhãn phải là `'khong_goi'` CHỈ vì nhánh ※…※ được xét TRƯỚC.
    for i in range(4):
        _mua(conn, batch, "KD02", HOM_NAY - timedelta(days=60 + i * 7), hang="P027")
    _ho_so_khach(conn, batch, "KS02", "QUAN CON SONG")
    for i in range(4):
        _mua(conn, batch, "KS02", HOM_NAY - timedelta(days=i * 7), hang="P027")
    _neo(conn, batch)

    nhan = dict(conn.execute(
        """SELECT customer_code, trang_thai_cap FROM mart.khach_mat_hang
           WHERE product_code = %s""", ("P027",)).fetchall())
    assert nhan["KD02"] == "khong_goi", \
        ("khách ※…※ phải mang NHÃN RIÊNG. Gói cổng đó vào một boolean thì phủ "
         "định boolean đó mở cửa lại đúng cho họ")
    assert nhan["KS02"] == "mua"

    # /san-pham/{mã}: khối chứng chạy, khách đã đóng cửa không ở khối NÀO.
    sp = SP.ho_so(conn, "P027")
    assert [k["ma"] for k in sp.khach_mua] == ["KS02"], \
        "chặn khỏi khối 'đã ngừng' mà lại rơi sang khối 'ĐANG mua' là tệ hơn"
    assert [k["ma"] for k in sp.khach_ngung] == []

    # /khach-hang/{mã}: hai khối gọi lại rỗng, lịch sử còn nguyên.
    kh = KH.ho_so(conn, "KD02")
    assert [m["ma"] for m in kh.da_ngung_mua] == []
    assert [m["ma"] for m in kh.chua_mua_thang] == []
    assert "P027" in {m["ma"] for m in kh.mat_hang}


def test_ho_so_hien_dung_cot_toc_do_giai_thich_du_ban_ngay(conn, batch):
    """[CRITICAL] `du_ban_ngay` và `trang_thai` được quyết bởi
    `toc_do_ngay_theo_tuoi`, KHÔNG phải `toc_do_ngay`. Hiện nhầm cột thì một
    dòng nói "tốc độ 0,33/ngày · còn đủ 140 ngày · đủ hàng" trong khi
    200/0,33 = 600 — ba ô mâu thuẫn mà người giữ kho không có cách nào đối
    chiếu."""
    _san_pham(conn, batch, "P021")
    _ton(conn, batch, "P021", sl=200)
    _ho_so_khach(conn, batch, "KP21", "Quán P021")
    _ban_qty(conn, batch, "KP21", HOM_NAY - timedelta(days=20), "P021", qty=10)
    _ban_qty(conn, batch, "KP21", HOM_NAY - timedelta(days=10), "P021", qty=10)
    _ban_qty(conn, batch, "KP21", HOM_NAY, "P021", qty=10)
    _neo(conn, batch)

    sp = SP.ho_so(conn, "P021").sp
    assert sp.toc_do_ngay_theo_tuoi is not None
    assert float(sp.toc_do_ngay) != float(sp.toc_do_ngay_theo_tuoi), \
        "mã mới: hai mẫu số khác nhau, nên hai cột phải khác nhau"
    assert abs(float(sp.ton) / float(sp.toc_do_ngay_theo_tuoi)
               - float(sp.du_ban_ngay)) < 0.01


# ---------------------------------------------------------------------------
# Ba trang mới: /san-pham, /san-pham/{mã}, /kho-hang (task 3)
#
# Test giao diện CẦN GIEO DỮ LIỆU nằm ở đây chứ không ở tests/test_giao_dien.py
# — cùng quy ước với tests/test_khach_hang.py, vì các hàm gieo ở đây.
# ---------------------------------------------------------------------------

def _khach_web(test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    return TestClient(create_app(db_url=test_db_url))


def _khoi(html: str, tu: str, den: str | None = None) -> str:
    """Đoạn HTML giữa hai tiêu đề. Dùng để khẳng định một dòng nằm trong ĐÚNG
    khối của nó: `assert ma in html` không phân biệt được khối "đã quá hạn"
    với khối "sắp hết hạn", mà đó chính là thứ hai khối này sinh ra để tách."""
    assert tu in html, f"không thấy khối {tu!r}"
    phan = html.split(tu, 1)[1]
    return phan.split(den, 1)[0] if den and den in phan else phan


def _chu(html: str) -> str:
    """Chữ trần của một mẩu HTML — bỏ thẻ, gộp khoảng trắng."""
    import re
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def _o(html: str, khoa: str, cot: str, sau: str | None = None) -> str:
    """Chữ trong ô ở CỘT `cot` của HÀNG chứa `khoa` (trong khối bắt đầu ở `sau`).

    Vì sao cần: khẳng định "chuỗi X có mặt đâu đó trong trang" — thậm chí
    "trong dòng" — KHÔNG canh được một bất biến về một Ô. Một mã chưa bán gì
    thì tỷ suất, tốc độ, còn-đủ-bán, bán-gần-nhất trên chính dòng đó đều đã là
    "—", nên `assert "—" in dong` vẫn xanh khi ô Tồn bị đổi thành `sp.ton or 0`
    — đúng hồi quy mà test mang tên. Y hệt: một nhãn in sẵn trong đoạn văn giải
    thích ngay trên bảng làm mọi `assert nhan in html` thành vô nghĩa.

    Chỉ số cột tra theo TÊN ở hàng tiêu đề chứ không viết cứng, để đổi thứ tự
    cột thì test đi theo chứ không đỏ oan.
    """
    import re
    if sau is not None:
        html = _khoi(html, sau)
    bang = next((b for b in re.findall(r"<table>.*?</table>", html, re.S)
                 if khoa in b), None)
    assert bang, f"không thấy bảng nào chứa {khoa!r}"
    dau = [_chu(t) for t in re.findall(r"<th[^>]*>(.*?)</th>", bang, re.S)]
    assert cot in dau, f"bảng không có cột {cot!r} (có: {dau})"
    dong = next(d for d in re.findall(r"<tr>(.*?)</tr>", bang, re.S) if khoa in d)
    return _chu(re.findall(r"<td[^>]*>(.*?)</td>", dong, re.S)[dau.index(cot)])


def test_ba_trang_moi_mo_duoc_va_khong_co_javascript(conn, batch, test_db_url):
    """[IMPORTANT] Ba trang phải mở được, và mã không tồn tại phải trả 404 chứ
    không phải 500 — gõ nhầm một ký tự trong địa chỉ là chuyện thường ngày."""
    _san_pham(conn, batch, "P100", ten="Gạo ST25 thử")
    _ton(conn, batch, "P100", sl=300)
    _ho_so_khach(conn, batch, "KP100", "Quán P100")
    _mua(conn, batch, "KP100", HOM_NAY - timedelta(days=3), hang="P100")
    _neo(conn, batch)
    c = _khach_web(test_db_url)

    for duong in ("/san-pham", "/san-pham/P100", "/kho-hang"):
        r = c.get(duong)
        assert r.status_code == 200, duong
        assert "<script" not in r.text, f"{duong}: không dùng JavaScript"
        assert "/static/kome.css" in r.text, f"{duong}: quên _chung.html"
    assert "Gạo ST25 thử" in c.get("/san-pham/P100").text
    assert c.get("/san-pham/MA-KHONG-CO").status_code == 404


def test_ba_muc_dieu_huong_moi_co_mat(conn, batch, test_db_url):
    """Trang chạy được mà không có trong thanh điều hướng thì không ai vào
    được — cùng thảm hoạ mà test_sidebar_hien_du_nam_muc canh cho đợt trước."""
    c = _khach_web(test_db_url)
    html = c.get("/").text
    assert "HÀNG HOÁ" in html, "thiếu nhóm HÀNG HOÁ trong sidebar"
    for duong in ('href="/san-pham"', 'href="/kho-hang"'):
        assert duong in html, f"sidebar thiếu {duong}"
    assert 'href="/san-pham" class="dang-xem"' in c.get("/san-pham").text


def test_cot_ton_hien_gach_ngang_chu_khong_phai_0(conn, batch, test_db_url):
    """[CRITICAL] 90/232 mã không có dòng nào trong 在庫一覧. Hiện `0` ở cột Tồn
    cho chúng là nói với người giữ kho rằng kho đã hết — và họ sẽ đi đặt hàng
    cho một mã có thể đang đầy kho.

    Khẳng định trên ĐÚNG Ô, không phải đúng dòng: mã này chưa bán gì nên tỷ
    suất, tốc độ, còn-đủ-bán và bán-gần-nhất trên chính dòng đó cũng là "—",
    nên một `assert "—" in dong` vẫn xanh khi ô Tồn bị đổi thành
    `sp.ton or 0`."""
    _san_pham(conn, batch, "P101", ten="Hàng chưa rõ tồn")
    _neo(conn, batch)
    html = _khach_web(test_db_url).get("/san-pham").text

    assert _o(html, "/san-pham/P101", "Tồn") == "—", \
        "ô Tồn của mã không có dòng tồn phải là — , không bao giờ là 0"
    assert _o(html, "/san-pham/P101", "Trạng thái") == "Chưa rõ tồn", \
        "nhãn phải nói 'chưa rõ', không phải 'hết hàng'"


def test_trang_san_pham_hien_du_SAU_nhan_trang_thai(conn, batch, test_db_url):
    """Sáu nhãn, không phải bốn. Thiếu một nhãn thì trang hiện mã thô
    (`chua_ro_ton`) cho đúng nhóm mã đông nhất — 90/232 mã.

    Khẳng định trong CHÍNH DẢI CHIP, không trên cả trang: đoạn văn giải thích
    ngay dưới dải chip đã in sẵn "Chưa rõ tồn" và "Ngừng kinh doanh" — đúng hai
    nhãn MỚI của migration 023 — nên `assert nhan in html` canh rỗng đúng hai
    nhãn đáng canh nhất."""
    import re
    _neo(conn, batch)
    html = _khach_web(test_db_url).get("/san-pham").text
    chip = re.search(r'<div class="loc">.*?</div>', html, re.S)
    assert chip, "không thấy dải chip trạng thái"
    for ma, (nhan, _mau) in SP.TRANG_THAI_TON.items():
        assert nhan in chip.group(0), f"dải chip thiếu nhãn {ma} ({nhan})"


def test_trang_360_hien_toc_do_THEO_TUOI_khong_phai_toc_do_ngay(conn, batch,
                                                               test_db_url):
    """[CRITICAL] `du_ban_ngay` và `trang_thai` do `toc_do_ngay_theo_tuoi`
    quyết. Hiện `toc_do_ngay` cạnh chúng là bày ra ba ô mâu thuẫn: "0,33/ngày ·
    còn 140 ngày · đủ hàng" trong khi 200/0,33 = 600."""
    _san_pham(conn, batch, "P102")
    _ton(conn, batch, "P102", sl=200)
    _ho_so_khach(conn, batch, "KP102", "Quán P102")
    for ngay in (20, 10, 0):
        _ban_qty(conn, batch, "KP102", HOM_NAY - timedelta(days=ngay), "P102", qty=10)
    _neo(conn, batch)

    sp = SP.ho_so(conn, "P102").sp
    assert float(sp.toc_do_ngay) != float(sp.toc_do_ngay_theo_tuoi), \
        "gieo hỏng: hai cột bằng nhau thì test này không kiểm được gì"
    html = _khach_web(test_db_url).get("/san-pham/P102").text
    assert "%.2f" % float(sp.toc_do_ngay_theo_tuoi) in html
    assert "%.2f" % float(sp.toc_do_ngay) not in html, \
        "trang đang hiện cột tốc độ KHÔNG quyết định trạng thái"


def test_kho_hang_hien_ngay_chup_va_du_BON_loai_han(conn, batch, test_db_url):
    """[IMPORTANT] Ảnh chụp 13:30 hôm trước đọc thành "bây giờ" là sai lệch cả
    một ngày tồn kho. Và `khong_ro` ("ta không đọc được ô này") phải hiện KHÁC
    `khong_han` ("hàng này không có hạn") — gộp làm một là biến một lời thú
    nhận về dữ liệu thành một lời khẳng định về hàng.

    Khẳng định trên ĐÚNG Ô của ĐÚNG LÔ, không trên cả trang: đoạn văn giải
    thích ngay trên bảng đã in nguyên văn cả bốn nhãn, nên gộp hai nhãn
    `khong_han`/`khong_ro` làm một — đúng hồi quy bị cấm — vẫn qua được một
    `assert nhan in html`. Và ngày chụp phải nằm ở ĐẦU TRANG (trước khối đầu
    tiên), không phải lẫn đâu đó phía dưới."""
    sap = HOM_NAY + timedelta(days=10)
    mong_doi = {"P103": "ngay", "P104": "khong_han", "P105": "trong",
                "P106": "khong_ro"}
    for ma, han in (("P103", f"{sap.year}年{sap.month:02d}月{sap.day:02d}日"),
                    ("P104", "賞味期限なし"), ("P105", ""), ("P106", "2028/06/09")):
        _san_pham(conn, batch, ma)
        _ton(conn, batch, ma, han=han)
    _neo(conn, batch)

    html = _khach_web(test_db_url).get("/kho-hang").text
    dau_trang = html.split("</h1>", 1)[1].split("<h2", 1)[0]
    assert str(HOM_NAY) in dau_trang, \
        "ngày chụp 在庫一覧 phải nằm ở đầu trang, trước khối đầu tiên"

    for ma, khoa in mong_doi.items():
        o = _o(html, ma, "Hạn sử dụng", sau="Tồn kho hiện tại")
        assert SP.LOAI_HAN[khoa][0] in o, f"{ma}: ô hạn không mang nhãn {khoa}"
        for khac, (nhan, _mau) in SP.LOAI_HAN.items():
            assert khac == khoa or nhan not in o, \
                f"{ma}: ô hạn mang CẢ nhãn {khac} — hai loại hạn đang bị gộp"


def test_kho_hang_tach_khoi_QUA_HAN_khoi_khoi_can_han(conn, batch, test_db_url):
    """[IMPORTANT] Với hàng thực phẩm "đã quá hạn" và "sắp hết hạn" là hai
    việc khác nhau: một cái phải xử lý ngay, một cái để theo dõi. Trộn chung
    thì cái cần xử lý ngay bị chôn trong danh sách cái cần theo dõi."""
    sap = HOM_NAY + timedelta(days=10)
    truoc = HOM_NAY - timedelta(days=5)
    _san_pham(conn, batch, "P107")
    _ton(conn, batch, "P107", han=f"{sap.year}年{sap.month:02d}月{sap.day:02d}日")
    _san_pham(conn, batch, "P108")
    _ton(conn, batch, "P108",
         han=f"{truoc.year}年{truoc.month:02d}月{truoc.day:02d}日")
    _neo(conn, batch)

    html = _khach_web(test_db_url).get("/kho-hang").text
    qua = _khoi(html, "Đã quá hạn", "Sắp hết hạn")
    can = _khoi(html, "Sắp hết hạn", "Tồn kho hiện tại")
    assert "P108" in qua and "P107" not in qua
    assert "P107" in can and "P108" not in can


def test_kho_hang_noi_ro_con_so_nao_la_cua_MOI_KHO(conn, batch, test_db_url):
    """[IMPORTANT] Ba con số trên màn này CỐ Ý không theo bộ lọc kho: bảng
    "giá trị theo kho" (nó là ô điều khiển của chính bộ lọc đó) và hai ô đếm
    trạng thái (`trang_thai` là thuộc tính của một MÃ tính trên tổng mọi kho —
    "mã hết hàng ở kho 0001" không có định nghĩa nào ở mart). Không ghi rõ thì
    chúng đứng cạnh những con số ĐÃ lọc, và không con số nào nói mình đang nói
    về tập nào.

    Mỗi khẳng định neo vào ĐÚNG KHỐI mà nó nói về, không đếm chuỗi trên cả
    trang: riêng mục `<option>— mọi kho —</option>` của ô lọc cộng với một câu
    duy nhất đã đủ cho `html.count("mọi kho") >= 2`, nên xoá hẳn lời chú thích
    của hai ô đếm mà test vẫn xanh.

    "Không theo bộ lọc kho" KHÁC "luôn liệt kê mọi kho": bảng vẫn co theo bộ
    lọc TRẠNG THÁI, và kho không còn dòng nào khớp thì vắng mặt hẳn."""
    _san_pham(conn, batch, "P109")
    _ton(conn, batch, "P109", kho="0001")
    _neo(conn, batch)
    html = _khach_web(test_db_url).get("/kho-hang?kho=0001").text

    # (1) Lời chú thích của bốn ô tổng quan: giữa khối thẻ số và ô lọc đầu tiên.
    o_dem = _khoi(html, 'class="the-so"', "<form")
    assert "mọi kho" in o_dem, \
        "hai ô đếm trạng thái không nói ra rằng chúng đếm trên mọi kho"
    # (2) Lời chú thích của bảng giá trị theo kho: giữa tiêu đề và chính bảng.
    #
    # "KHÔNG TỰ LỌC THEO KHO", chứ KHÔNG PHẢI "luôn liệt kê mọi kho" — hai câu
    # khác nhau và câu thứ hai SAI: nhánh 'kho' của kho_hang() có GROUP BY, nên
    # khi lọc trạng thái thì kho không còn dòng nào khớp biến mất khỏi bảng.
    # Bản trước của test này khoá đúng câu sai đó (và template còn tự mâu thuẫn
    # ngay câu sau: "luôn liệt kê mọi kho… Nhưng nó CÓ theo bộ lọc trạng thái").
    theo_kho = _khoi(html, "Giá trị theo kho", "<table")
    assert "không tự lọc theo kho" in theo_kho, \
        "bảng giá trị theo kho không nói ra rằng nó bỏ qua bộ lọc kho"

    # (3) …và khi CÓ lọc trạng thái thì nó phải nói ra cả vế kia: bảng co lại,
    # đường quay lại nằm ở ô chọn kho. Im lặng ở đây là để người đọc kết luận
    # một kho vừa biến mất khỏi bảng là một kho không còn tồn.
    html_loc = _khach_web(test_db_url).get("/kho-hang?loc=chua_ro_ton").text
    theo_kho_loc = _khoi(html_loc, "Giá trị theo kho", "<table")
    assert "bộ lọc trạng thái" in theo_kho_loc and "vắng mặt" in theo_kho_loc, \
        "lọc trạng thái mà bảng không nói ra rằng kho không khớp sẽ biến mất"


def test_bo_loc_la_tren_URL_khong_lam_do_trang(conn, batch, test_db_url):
    """[IMPORTANT] Tầng Python BỎ QUA một `loc` không có trong TRANG_THAI_TON
    (`_vi_tu`: `if loc in TRANG_THAI_TON`), nên dữ liệu trả về là dữ liệu KHÔNG
    lọc. Template phải đọc nó cùng một cách — tra thẳng `trang_thai[k.loc]` thì
    một ký tự gõ nhầm trên thanh địa chỉ làm cả trang trả 500, và dải chip lại
    hiện "không có mục nào đang chọn" trong khi bảng đang hiện mọi dòng.

    Phát hiện lúc tự soát của task 3, không phải từ một test có sẵn."""
    _san_pham(conn, batch, "P110")
    _ton(conn, batch, "P110", sl=5)
    _neo(conn, batch)
    c = _khach_web(test_db_url)

    for duong in ("/kho-hang?loc=khong-co-that", "/san-pham?loc=khong-co-that"):
        r = c.get(duong)
        assert r.status_code == 200, duong
        # Không lọc gì thì chip "Tất cả" phải là chip đang chọn — đúng những gì
        # bảng bên dưới đang hiện.
        assert 'class="dang-xem">Tất cả' in r.text, \
            f"{duong}: bộ lọc lạ bị bỏ qua ở tầng Python nhưng chip vẫn báo có lọc"

    # `kho` thì NGƯỢC LẠI: kome/san_pham.py lọc theo mọi giá trị chứ không có
    # danh sách trắng, nên bảng ĐANG bị lọc (và rỗng). Ô chọn phải nói ra điều
    # đó — không có option nào khớp thì trình duyệt hiện mục đầu ("— mọi kho
    # —") và ô điều khiển nói ngược hẳn với bảng ngay dưới nó. Cùng bất biến
    # với ô Tỉnh của khach_hang.html (đợt 4a).
    r = c.get("/kho-hang?kho=khong-co-that")
    assert r.status_code == 200
    assert '<option value="khong-co-that" selected' in r.text


def test_o_gia_tri_ton_chet_di_theo_CA_bo_loc_kho(conn, batch):
    """[CRITICAL] Ô "Giá trị tồn chết" là một con số YÊN mà người giữ kho hành
    động theo (xả hay không xả), và nó đứng ngay trên một bảng ĐÃ lọc theo kho.
    Không lọc theo kho thì mở `?kho=0001` sẽ thấy bảng chỉ còn kho 0001 mà thẻ
    vẫn là tổng MỌI kho — công ty có 2 kho nên sai số có thể gần 2×.

    Đây KHÁC hai ô đếm trạng thái: `trang_thai` là thuộc tính của một MÃ tính
    trên tổng mọi kho nên "mã hết hàng ở kho 0001" vô nghĩa, còn `gia_tri` thì
    có theo từng kho — "phần hàng chết đang chiếm chỗ tại kho này" là một câu
    hỏi có nghĩa và tính được, đúng câu hỏi của người vừa lọc theo kho."""
    _san_pham(conn, batch, "P050")
    _ton(conn, batch, "P050", kho="0001", sl=10, gia=1000)      # 10.000
    _ton(conn, batch, "P050", kho="1002", sl=5, gia=1000)       #  5.000
    _ho_so_khach(conn, batch, "KP50", "Quán P050")
    _mua(conn, batch, "KP50", HOM_NAY - timedelta(days=200), hang="P050")
    _neo(conn, batch)

    assert SP.kho_hang(conn).o_tong_quan["gia_tri_ton_chet"] == 15_000
    assert SP.kho_hang(conn, kho="0001").o_tong_quan["gia_tri_ton_chet"] == 10_000
    assert SP.kho_hang(conn, kho="1002").o_tong_quan["gia_tri_ton_chet"] == 5_000
    # Hai bộ lọc cùng lúc vẫn phải đúng — thứ tự tham số của câu lệnh gộp là
    # chỗ dễ lệch nhất khi thêm một mảnh vị từ.
    assert SP.kho_hang(conn, kho="0001",
                       loc="ton_chet").o_tong_quan["gia_tri_ton_chet"] == 10_000
    assert SP.kho_hang(conn, kho="0001",
                       loc="du").o_tong_quan["gia_tri_ton_chet"] == 0
