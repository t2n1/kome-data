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
    # Khách đã ngừng: mua đều 3 lần rồi im quá 90 ngày.
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
