"""Khách hàng: danh sách, hồ sơ 360°, và cách xác định khách đang rời bỏ.

Trọng tâm: **trạng thái phải so với nhịp mua RIÊNG của từng khách.** Một ngưỡng
chung sẽ báo động nhầm ở khách mua thưa và im lặng ở khách mua dày — tức là bỏ
sót đúng những khách đang rời đi nhanh nhất.
"""
from datetime import date, timedelta

import pandas as pd
import pytest

from kome import khach_hang as KH


def _mua(conn, batch, ma_khach, ngay: date, tien=110_000, tax=10_000, gp=30_000,
         hang="XT07"):
    from kome.loaders import sales
    b = batch(abs(hash((ma_khach, ngay, hang))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ma_khach[-4:]}{ngay:%m%d}{hang}", "line_seq": 1,
        "sales_date": ngay, "customer_code": ma_khach, "product_code": hang,
        "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
        "unit_cost": 3210, "amount": tien, "tax_amount": tax,
        "cost": tien - tax - gp, "gross_profit": gp, "paid_amount": 0,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _ho_so_khach(conn, batch, ma, ten, **kw):
    """Một dòng core.dim_customer hiện hành."""
    b = batch(abs(hash(ma)) % 80_000 + 10_000)
    conn.execute(
        """INSERT INTO core.dim_customer
             (customer_code, valid_from, valid_to, is_current, customer_name,
              phone, prefecture, city, address, salesperson_code, batch_id)
           VALUES (%s, '2025-01-01', '9999-12-31', true, %s, %s, %s, %s, %s, %s, %s)""",
        (ma, ten, kw.get("phone", "080-0000-0000"), kw.get("prefecture", "東京都"),
         kw.get("city", "渋谷区"), kw.get("address", "1-1-1"),
         kw.get("salesperson_code", "0104"), b))
    conn.commit()


# Mốc thời gian của mọi phép tính = ngày bán mới nhất trong kho.
HOM_NAY = date(2026, 7, 31)


def _mua_deu(conn, batch, ma, nhip: int, so_lan: int, ngung_truoc: int = 0):
    """Khách mua đều `nhip` ngày một lần, lần cuối cách HOM_NAY `ngung_truoc` ngày."""
    for i in range(so_lan):
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=ngung_truoc + i * nhip))


def _neo(conn, batch):
    """Một giao dịch ĐÚNG NGÀY HOM_NAY, của một khách không dính tới phép thử.

    Bắt buộc ở mọi test có khách im lặng: mốc thời gian là ngày bán MỚI NHẤT
    trong kho (mart.moc_thoi_gian). Nếu mọi khách trong test đều im lặng thì
    mốc tự lùi theo và không ai "im" cả — test xanh/đỏ vì lý do không liên
    quan gì tới thứ nó định kiểm.
    """
    _mua(conn, batch, "000000000999", HOM_NAY)


def test_moc_thoi_gian_la_ngay_ban_MOI_NHAT_khong_phai_hom_nay(conn, batch):
    """[CRITICAL] Nếu lấy current_date làm mốc, thì một ngày không ai nạp file
    sẽ khiến CẢ 1.710 khách "im lặng thêm một ngày" — cảnh báo nhảy loạn vì
    một lý do không liên quan gì tới khách hàng."""
    _mua(conn, batch, "000000000001", date(2026, 5, 1))
    moc = conn.execute("SELECT hom_nay FROM mart.moc_thoi_gian").fetchone()[0]
    assert moc == date(2026, 5, 1)


def test_trang_thai_theo_NHIP_RIENG_khong_theo_nguong_chung(conn, batch):
    """[CRITICAL] Lý do tồn tại của cả cách tính này.

    Khách A mua 7 ngày/lần, im 30 ngày  -> 4,3× nhịp -> ĐÃ RỜI BỎ.
    Khách B mua 60 ngày/lần, im 30 ngày -> 0,5× nhịp -> BÌNH THƯỜNG.
    Cùng 30 ngày im lặng, hai kết luận trái ngược. Một ngưỡng chung (vd "90
    ngày") sẽ nói cả hai đều bình thường, và bỏ sót khách A.
    """
    _ho_so_khach(conn, batch, "000000000001", "Quan an mua hang tuan")
    _ho_so_khach(conn, batch, "000000000002", "Tap hoa mua hai thang mot lan")
    _mua_deu(conn, batch, "000000000001", nhip=7, so_lan=6, ngung_truoc=30)
    _mua_deu(conn, batch, "000000000002", nhip=60, so_lan=6, ngung_truoc=30)
    _mua(conn, batch, "000000000003", HOM_NAY)      # giữ mốc thời gian

    tt = {k.ma: k for k in KH.danh_sach(conn).khach}
    assert tt["000000000001"].trang_thai == "da_roi_bo"
    assert tt["000000000002"].trang_thai == "binh_thuong"
    assert tt["000000000001"].so_ngay_im_lang == tt["000000000002"].so_ngay_im_lang == 30


def test_khach_OBC_da_danh_dau_dong_cua_KHONG_vao_danh_sach_goi(conn, batch):
    """[CRITICAL] 281/2.077 khách thật có dấu ※廃業※ / ※取引停止※ trong tên.

    Doanh nghiệp đã phá sản thì im lặng là ĐÚNG, không phải bất thường. Để lẫn
    vào thì danh sách "hôm nay nên gọi ai" đầy số điện thoại không ai bắt máy,
    và nhân viên bỏ dùng công cụ ngay tuần đầu — một cảnh báo bị mất tin còn
    tệ hơn không có cảnh báo nào.
    """
    _ho_so_khach(conn, batch, "000000000001", "※廃業・精算※CUA HANG DA DONG")
    _ho_so_khach(conn, batch, "000000000002", "※取引停止※CONG TY NGUNG")
    _ho_so_khach(conn, batch, "000000000003", "QUAN AN BINH THUONG")
    for ma in ("000000000001", "000000000002", "000000000003"):
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=30)
    _neo(conn, batch)

    tt = {k.ma: k.trang_thai for k in KH.danh_sach(conn).khach}
    assert tt["000000000001"] == "ngung_giao_dich"
    assert tt["000000000002"] == "ngung_giao_dich"
    assert tt["000000000003"] == "da_roi_bo", "khách còn sống vẫn phải bị cảnh báo"

    ma_can_goi = {k.ma for k in KH.can_xu_ly(conn)}
    assert "000000000001" not in ma_can_goi and "000000000002" not in ma_can_goi
    assert "000000000003" in ma_can_goi


def test_nhan_ca_HAI_cach_viet_thanh_ly_cua_OBC(conn, batch):
    """OBC có hai cách viết cho cùng một nghĩa: 廃業・精算 và 廃業・清算
    (210 và 40 khách thật). Bắt một cách là bỏ sót 40 khách."""
    for i, ten in enumerate(("※廃業・精算※A", "※廃業・清算※B", "※廃業※C",
                             "※取引禁止※D", "※使用禁止※E"), start=1):
        ma = f"00000000000{i}"
        _ho_so_khach(conn, batch, ma, ten)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=30)
    _neo(conn, batch)
    assert all(k.trang_thai == "ngung_giao_dich"
               for k in KH.danh_sach(conn).khach if k.ma != "000000000999")


def test_chua_du_lich_su_thi_KHONG_doan_bua(conn, batch):
    """[IMPORTANT] Mua một lần thì chưa biết nhịp của khách này. Đoán bừa một
    nhịp rồi báo động là cách nhanh nhất làm nhân viên mất tin vào cảnh báo."""
    _ho_so_khach(conn, batch, "000000000001", "Khach moi")
    _mua(conn, batch, "000000000001", HOM_NAY - timedelta(days=200))
    _mua(conn, batch, "000000000002", HOM_NAY)
    k = next(k for k in KH.danh_sach(conn).khach if k.ma == "000000000001")
    assert k.trang_thai == "chua_du_lich_su"
    assert k.ty_le_im_lang is None


def test_nhip_dung_TRUNG_VI_khong_dung_trung_binh(conn, batch):
    """Một khách mua đều 7 ngày/lần rồi nghỉ Tết 60 ngày sẽ có TRUNG BÌNH ~14
    ngày — đủ để ngưỡng cảnh báo lệch gấp đôi. Trung vị bỏ qua lần bất thường."""
    _ho_so_khach(conn, batch, "000000000001", "Khach nghi Tet")
    ngay = HOM_NAY
    for cach in (0, 7, 7, 7, 7, 60, 7, 7, 7, 7):     # một khoảng 60 ngày lạc loài
        ngay = ngay - timedelta(days=cach)
        _mua(conn, batch, "000000000001", ngay)
    k = next(k for k in KH.danh_sach(conn).khach if k.ma == "000000000001")
    assert k.nhip_ngay == 7, f"trung vị phải là 7, không phải trung bình (~12,9)"


def test_tim_kiem_theo_ten_ma_dien_thoai_dia_chi(conn, batch):
    """Nhân viên không nhớ mình đang cầm mảnh thông tin nào — tên, mã, hay số
    điện thoại khách vừa đọc qua máy."""
    _ho_so_khach(conn, batch, "000000009292", "CHO VIET OSAKA",
                 phone="06-1234-5678", city="浪速区")
    _mua_deu(conn, batch, "000000009292", nhip=7, so_lan=4)
    for tu_khoa in ("OSAKA", "osaka", "9292", "1234-5678", "浪速"):
        assert KH.danh_sach(conn, tim=tu_khoa).tong == 1, tu_khoa
    assert KH.danh_sach(conn, tim="KHONG-CO-THAT").tong == 0


def test_sap_xep_chi_nhan_cot_trong_danh_sach_trang(conn, batch):
    """[CRITICAL] Tham số sắp xếp đi thẳng vào câu SQL. Trang này nằm trên
    Internet — ghép thẳng chuỗi từ URL là mở cửa cho SQL injection."""
    _mua(conn, batch, "000000000001", HOM_NAY)
    doc_hai = "doanh_thu_thuan; DROP TABLE core.fact_sales_line--"
    KH.danh_sach(conn, sap=doc_hai)                  # phải rơi về mặc định
    assert conn.execute("SELECT count(*) FROM core.fact_sales_line").fetchone()[0] == 1
    assert doc_hai not in KH.SAP_XEP


def test_dem_trang_thai_tinh_tren_TOAN_BO_khong_theo_bo_loc(conn, batch):
    """Nếu bộ đếm chạy theo bộ lọc đang bật thì bấm vào một mục xong các con số
    khác về 0 hết, và không ai tìm đường quay lại."""
    _ho_so_khach(conn, batch, "000000000001", "Khach deu")
    _ho_so_khach(conn, batch, "000000000002", "Khach roi bo")
    _mua_deu(conn, batch, "000000000001", nhip=7, so_lan=6)
    _mua_deu(conn, batch, "000000000002", nhip=7, so_lan=6, ngung_truoc=40)

    t = KH.danh_sach(conn, loc="da_roi_bo")
    assert t.tong == 1                                    # danh sách bị lọc
    assert t.dem_trang_thai["binh_thuong"] == 1           # bộ đếm thì không


def test_ho_so_360_day_du(conn, batch):
    _ho_so_khach(conn, batch, "000000009292", "QUAN AN TEST")
    _mua_deu(conn, batch, "000000009292", nhip=7, so_lan=5)
    _mua(conn, batch, "000000009292", HOM_NAY - timedelta(days=3), hang="XT08")
    h = KH.ho_so(conn, "000000009292")
    assert h.khach.ten == "QUAN AN TEST"
    assert h.ho_so["so_lan_mua"] > 0
    assert h.thang and h.mat_hang and h.lan_mua_gan_day
    assert KH.ho_so(conn, "MA-KHONG-CO-THAT") is None


def test_mat_hang_da_ngung_mua(conn, batch):
    """Khách vẫn mua, nhưng đã bỏ hẳn một mặt hàng — tín hiệu sớm hơn nhiều so
    với việc khách ngừng mua toàn bộ."""
    _ho_so_khach(conn, batch, "000000009292", "KHACH BO MOT MON")
    for i in range(4):     # món cũ: mua 4 lần, dừng cách đây hơn 90 ngày
        _mua(conn, batch, "000000009292", HOM_NAY - timedelta(days=120 + i * 7),
             hang="XT08")
    _mua_deu(conn, batch, "000000009292", nhip=7, so_lan=5)   # món mới, vẫn mua
    h = KH.ho_so(conn, "000000009292")
    bo = {m["ma"] for m in h.da_ngung_mua}
    assert "XT08" in bo
    assert "XT07" not in bo, "món vẫn đang mua không được coi là đã bỏ"


def test_ho_so_mang_nhip_theo_tung_ma(conn, batch):
    """Ba khối của trang hồ sơ cần nhịp theo mã. Lấy nó từ mart chứ không tính
    ở Python — định nghĩa chỉ số chỉ có một nhà."""
    _ho_so_khach(conn, batch, "MH01", "Quán mặt hàng")
    for i in range(5):
        _mua(conn, batch, "MH01", HOM_NAY - timedelta(days=i * 7), hang="XT07")
    _neo(conn, batch)
    h = KH.ho_so(conn, "MH01")
    m = next(x for x in h.mat_hang if x["ma"] == "XT07")
    assert m["nhip"] == 7
    assert m["du_kien"] is not None


def test_can_xu_ly_xep_theo_TIEN_khong_theo_muc_im_lang(conn, batch):
    """Gọi lại khách ¥5 triệu im 3× nhịp đáng hơn khách ¥50.000 im 10× nhịp,
    dù con số thứ hai trông đáng báo động hơn."""
    _ho_so_khach(conn, batch, "000000000001", "Khach LON im vua")
    _ho_so_khach(conn, batch, "000000000002", "Khach NHO im rat lau")
    _mua_deu(conn, batch, "000000000001", nhip=7, so_lan=6, ngung_truoc=30)
    for i in range(6):     # khách nhỏ: cùng nhịp, im lâu hơn nhiều, tiền ít hơn
        _mua(conn, batch, "000000000002", HOM_NAY - timedelta(days=120 + i * 7),
             tien=11_000, tax=1_000, gp=3_000)
    _neo(conn, batch)
    ds = KH.can_xu_ly(conn)
    assert [k.ma for k in ds][:2] == ["000000000001", "000000000002"]


def test_module_khong_tu_mo_ket_noi():
    import ast
    import inspect

    import kome.khach_hang as M

    cay = ast.parse(inspect.getsource(M))
    goi = {n.func.id for n in ast.walk(cay)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    assert "connect" not in goi
    assert list(inspect.signature(M.danh_sach).parameters)[0] == "conn"


def test_cac_trang_moi_mo_duoc(conn, batch, test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    _ho_so_khach(conn, batch, "000000009292", "QUAN AN TEST")
    _mua_deu(conn, batch, "000000009292", nhip=7, so_lan=5)
    c = TestClient(create_app(db_url=test_db_url))

    for duong in ("/", "/khach-hang", "/can-xu-ly", "/khach-hang/000000009292"):
        r = c.get(duong)
        assert r.status_code == 200, duong
        assert "<script" not in r.text, f"{duong}: không dùng JavaScript"

    assert "QUAN AN TEST" in c.get("/khach-hang/000000009292").text
    assert c.get("/khach-hang/MA-KHONG-CO").status_code == 404
    # Trang nạp chuyển từ "/" sang "/nap"; "/" giờ là Tổng quan.
    assert "Tổng quan" in c.get("/").text
    assert "Nạp dữ liệu OBC" in c.get("/nap").text


def test_moi_trang_deu_co_khung_dieu_huong(conn, test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    c = TestClient(create_app(db_url=test_db_url))
    for duong in ("/", "/khach-hang", "/can-xu-ly", "/bao-cao", "/health",
                  "/phu-du-lieu", "/nap"):
        t = c.get(duong).text
        for muc in ('href="/khach-hang"', 'href="/bao-cao"', 'href="/can-xu-ly"'):
            assert muc in t, f"{duong} thiếu {muc}"


# ---- Mặc định "khách của tôi" (đợt 3) ----------------------------------

def _hai_sale(conn, batch):
    """Hai khách của 0104, một khách của 0102."""
    for ma, ten, sale in (("K0104A", "Quán A", "0104"),
                          ("K0104B", "Quán B", "0104"),
                          ("K0102C", "Quán C", "0102")):
        _ho_so_khach(conn, batch, ma, ten, salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=14, so_lan=5)
    _neo(conn, batch)


# Khách của `_neo` — có dòng bán nhưng không có hồ sơ trong dim_customer, nên
# vẫn hiện trong mart.khach_360 (view dựng từ bảng bán hàng). Test nào khẳng
# định một TẬP CHÍNH XÁC phải bỏ nó ra, như các test khác trong file này đã làm.
NEO = "000000000999"


def _tru_neo(khach) -> set[str]:
    return {k.ma for k in khach} - {NEO}


def test_loc_theo_sale_chi_hien_khach_cua_nguoi_do(conn, batch):
    _hai_sale(conn, batch)
    t = KH.danh_sach(conn, sale="0104")
    assert {k.ma for k in t.khach} == {"K0104A", "K0104B"}
    assert t.tong == 2
    assert t.sale == "0104"


def test_khong_truyen_sale_thi_hien_tat_ca(conn, batch):
    _hai_sale(conn, batch)
    t = KH.danh_sach(conn)
    assert _tru_neo(t.khach) == {"K0104A", "K0104B", "K0102C"}
    assert t.sale is None


def test_bo_dem_trang_thai_di_theo_bo_loc_sale(conn, batch):
    """Đang lọc "khách của tôi" mà bộ đếm vẫn khoe con số toàn công ty thì
    bấm vào một mục xong ra danh sách ngắn hơn hẳn con số vừa đọc.

    Dòng thứ hai KHÔNG so với một số cứng: `_neo` chèn thêm một khách neo
    không mã sale vào `mart.khach_360` (xem `_tru_neo`), nên tổng công ty
    không phải lúc nào cũng bằng 3. Bất biến thật sự cần canh là bộ đếm CỘNG
    LẠI đúng bằng `tong` khi không lọc tìm/trạng thái — không phụ thuộc khách
    neo có mặt hay không.
    """
    _hai_sale(conn, batch)
    assert sum(KH.danh_sach(conn, sale="0104").dem_trang_thai.values()) == 2
    t = KH.danh_sach(conn)
    assert sum(t.dem_trang_thai.values()) == t.tong


def test_tong_tat_ca_luon_dem_toan_bo_du_dang_loc(conn, batch):
    """Số trên nút "Xem tất cả khách (N)" phải là số THẬT lấy từ truy vấn,
    không phải con số của bộ lọc đang bật.

    So với `danh_sach(conn).tong` (không lọc) thay vì một số cứng: khách neo
    của `_neo` (xem `_tru_neo`) làm tổng công ty không cố định bằng 3. Đây
    không phải tautology — nó khẳng định đúng hợp đồng của `tong_tat_ca`: bỏ
    qua bộ lọc sale, nên sẽ đỏ ngay nếu ai đó lỡ cho nó chạy qua bộ lọc.
    """
    _hai_sale(conn, batch)
    assert KH.danh_sach(conn, sale="0104").tong_tat_ca == KH.danh_sach(conn).tong


def test_loc_sale_ket_hop_duoc_voi_tim_kiem_va_loc_trang_thai(conn, batch):
    _hai_sale(conn, batch)
    t = KH.danh_sach(conn, tim="Quán A", sale="0104")
    assert [k.ma for k in t.khach] == ["K0104A"]
    assert KH.danh_sach(conn, tim="Quán C", sale="0104").tong == 0


def test_can_xu_ly_loc_duoc_theo_sale(conn, batch):
    """Khách im lặng của 0102 không được lẫn vào danh sách gọi lại của 0104."""
    for ma, sale in (("R0104", "0104"), ("R0102", "0102")):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=90)
    _neo(conn, batch)
    assert {k.ma for k in KH.can_xu_ly(conn, sale="0104")} == {"R0104"}
    assert {k.ma for k in KH.can_xu_ly(conn)} == {"R0104", "R0102"}


# ---- Tổng quan danh bạ: bốn khối trong một truy vấn (task 3 đợt 4a) ----

def test_tong_quan_danh_ba_chay_dung_MOT_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Bốn khối phân tích = bốn vòng Tokyo nếu làm ẩu. Đo thật:
    một round-trip rỗng đã 47 ms, nên bốn khối rời nhau cộng thêm ~1 giây vào
    mỗi lần mở trang danh sách."""
    _ho_so_khach(conn, batch, "TQ01", "Quán TQ", salesperson_code="0104")
    _mua(conn, batch, "TQ01", HOM_NAY - timedelta(days=3))
    _neo(conn, batch)

    dem = {"n": 0}
    that = conn.execute
    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    tq = KH.tong_quan_danh_ba(conn)
    assert dem["n"] == 1, f"chạy {dem['n']} truy vấn, phải đúng 1"

    assert tq.tong >= 1
    assert [h[0] for h in tq.hang] == ["S", "A", "B", "C", "D"]
    assert len(tq.nhan_vien) == 5
    assert set(tq.nhom) == {"im", "tut", "moi"}


def test_tong_quan_khong_ro_tinh_van_duoc_dem(conn, batch):
    """8 khách không có tỉnh (đo thật). Bỏ im lặng thì tổng của khối 'Tập trung
    ở đâu' không khớp tổng danh bạ và không ai biết vì sao."""
    _ho_so_khach(conn, batch, "KT01", "Quán không tỉnh", prefecture="")
    _mua(conn, batch, "KT01", HOM_NAY - timedelta(days=3))
    _neo(conn, batch)
    tq = KH.tong_quan_danh_ba(conn)
    assert any(t[0] == "(không rõ)" for t in tq.tinh)


# ---- Ba bộ lọc mới: nhóm việc, hạng, tỉnh (task 4 đợt 4a) --------------

def test_loc_theo_nhom_viec(conn, batch):
    for ma, ngung in (("L0001", 40), ("L0002", 2)):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}")
        for i in range(6):
            _mua(conn, batch, ma, HOM_NAY - timedelta(days=ngung + i * 7))
    _neo(conn, batch)
    t = KH.danh_sach(conn, nhom="im")
    assert "L0001" in {k.ma for k in t.khach}
    assert "L0002" not in {k.ma for k in t.khach}


def test_ba_bo_loc_moi_ket_hop_duoc_voi_nhau_va_voi_sale(conn, batch):
    """Bấm hai bộ lọc mà một cái im lặng bị bỏ là người dùng đọc sai danh sách
    mà không có gì báo."""
    _ho_so_khach(conn, batch, "K0001", "Quán K", salesperson_code="0104",
                 prefecture="愛知県")
    _mua(conn, batch, "K0001", HOM_NAY - timedelta(days=3))
    _neo(conn, batch)
    t = KH.danh_sach(conn, tinh="愛知県", sale="0104")
    assert "K0001" in {k.ma for k in t.khach}
    assert KH.danh_sach(conn, tinh="東京都", sale="0104").tong == 0
