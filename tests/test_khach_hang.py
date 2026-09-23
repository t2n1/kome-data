"""Khách hàng: danh sách, hồ sơ 360°, và cách xác định khách đang rời bỏ.

Trọng tâm: **trạng thái phải so với nhịp mua RIÊNG của từng khách.** Một ngưỡng
chung sẽ báo động nhầm ở khách mua thưa và im lặng ở khách mua dày — tức là bỏ
sót đúng những khách đang rời đi nhanh nhất.
"""
import inspect
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
              phone, prefecture, city, address, salesperson_code,
              price_level_code, batch_id)
           VALUES (%s, '2025-01-01', '9999-12-31', true, %s, %s, %s, %s, %s, %s,
                   %s, %s)""",
        (ma, ten, kw.get("phone", "080-0000-0000"), kw.get("prefecture", "東京都"),
         kw.get("city", "渋谷区"), kw.get("address", "1-1-1"),
         kw.get("salesperson_code", "0104"), kw.get("price_level_code"), b))
    conn.commit()


def _mua_nhieu(conn, batch, dong, ma_lo="L"):
    """Nhiều dòng bán trong MỘT lần nạp.

    `_mua` mở một lô và một lượt hỏi cho MỖI dòng; test cần 40 khách nền để
    thang hạng doanh thu có ý nghĩa thì đó là 40 vòng qua pooler Tokyo. Hàm
    này gộp thành một `executemany`.

    `dong`: các bộ (mã khách, ngày, tiền đã gồm thuế, mã hàng).
    """
    from kome.loaders import sales
    b = batch(abs(hash((ma_lo, len(dong), dong[0]))) % 30_000 + 400_000)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"{ma_lo}{i}", "line_seq": 1, "sales_date": ngay,
        "customer_code": ma, "product_code": hang, "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": tien, "tax_amount": tien // 11,
        "cost": tien - tien // 11 - tien // 4, "gross_profit": tien // 4,
        "paid_amount": 0, "batch_id": b,
    } for i, (ma, ngay, tien, hang) in enumerate(dong)]), HOM_NAY, b)
    conn.commit()


def _hang_master(conn, batch, *cap):
    """Vài dòng core.dim_product. Khối "gợi ý" đi TỪ bảng mã hàng, nên không
    có dòng nào ở đây thì nó luôn rỗng và test hoá ra chẳng kiểm gì."""
    b = batch(abs(hash(("hang",) + cap)) % 40_000 + 200_000)
    for ma, ten in cap:
        conn.execute(
            """INSERT INTO core.dim_product (product_code, product_name, batch_id)
               VALUES (%s, %s, %s)""", (ma, ten, b))
    conn.commit()


def _bang_gia(conn, batch, bac: str, ma_hang: str, gia: int,
              quy_cach: str = "02", tu_ngay: str = "2026-01-01"):
    """Một dòng core.fact_price_list.

    `quy_cach` (荷姿区分) và `tu_ngay` để ngỏ vì khoá của bảng là
    (product_code, pack_code, price_level, valid_from) — cùng một mã hàng có
    nhiều dòng thật, và trang chỉ được hiện dòng MỚI NHẤT của TỪNG quy cách.
    """
    b = batch(abs(hash(("gia", bac, ma_hang, quy_cach, tu_ngay))) % 40_000 + 250_000)
    conn.execute(
        """INSERT INTO core.fact_price_list
             (product_code, pack_code, price_level, valid_from, price_ex_tax,
              price_in_tax, unit_cost, batch_id)
           VALUES (%s, %s, %s, %s, %s, %s, 0, %s)""",
        (ma_hang, quy_cach, bac, tu_ngay, gia, gia, b))
    conn.commit()


def _diem_giao(conn, batch, ma_khach: str, ma_diem: str, ten: str):
    b = batch(abs(hash(("giao", ma_diem))) % 40_000 + 300_000)
    conn.execute(
        """INSERT INTO core.dim_shipto
             (shipto_code, shipto_name, customer_code, address, batch_id)
           VALUES (%s, %s, %s, '2-2-2', %s)""", (ma_diem, ten, ma_khach, b))
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
    """Nếu bộ đếm chạy theo bộ lọc TRẠNG THÁI đang bật thì bấm vào một mục
    xong các con số khác về 0 hết, và không ai tìm đường quay lại.

    Bộ đếm đã chuyển sang `tong_quan_danh_ba` (vòng sửa cuối đợt 4a) — nó
    không nhận `loc` nữa, nên bất biến này giờ là bất biến CẤU TRÚC. Test vẫn
    giữ để nói rõ vì sao nó không được nhận."""
    _ho_so_khach(conn, batch, "000000000001", "Khach deu")
    _ho_so_khach(conn, batch, "000000000002", "Khach roi bo")
    _mua_deu(conn, batch, "000000000001", nhip=7, so_lan=6)
    _mua_deu(conn, batch, "000000000002", nhip=7, so_lan=6, ngung_truoc=40)

    t = KH.danh_sach(conn, loc="da_roi_bo")
    assert t.tong == 1                                    # danh sách bị lọc
    tq = KH.tong_quan_danh_ba(conn)
    assert tq.dem_trang_thai["binh_thuong"] == 1          # bộ đếm thì không
    assert "loc" not in inspect.signature(KH.tong_quan_danh_ba).parameters, \
        "bộ đếm nhận `loc` là bấm một mục xong các con số khác về 0"


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
    # Món cũ: mua 4 lần cách nhau 7 ngày (nhịp riêng = 7), lần cuối 120 ngày
    # trước — im hơn mười bảy lần nhịp của chính cặp khách–mã này.
    for i in range(4):
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

    for duong in ("/", "/khach-hang", "/lien-he", "/khach-hang/000000009292"):
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
    for duong in ("/", "/khach-hang", "/lien-he", "/bao-cao", "/health",
                  "/phu-du-lieu", "/nap"):
        t = c.get(duong).text
        for muc in ('href="/khach-hang"', 'href="/bao-cao"', 'href="/lien-he"'):
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
    assert sum(KH.tong_quan_danh_ba(conn, sale="0104").dem_trang_thai.values()) == 2
    t = KH.danh_sach(conn)
    assert sum(KH.tong_quan_danh_ba(conn).dem_trang_thai.values()) == t.tong


def test_tong_tat_ca_luon_dem_toan_bo_du_dang_loc(conn, batch):
    """Số trên nút "Xem tất cả khách (N)" phải là số THẬT lấy từ truy vấn,
    không phải con số của bộ lọc đang bật.

    So với `danh_sach(conn).tong` (không lọc) thay vì một số cứng: khách neo
    của `_neo` (xem `_tru_neo`) làm tổng công ty không cố định bằng 3. Đây
    không phải tautology — nó khẳng định đúng hợp đồng của `tong_tat_ca`: bỏ
    qua MỌI bộ lọc, nên sẽ đỏ ngay nếu ai đó lỡ cho nó chạy qua một cái.

    Kiểm cả ba bộ lọc mới cùng lúc, không chỉ `sale`: `tong_tat_ca` nay nằm
    trong UNION ALL của `tong_quan_danh_ba` cạnh `dem_trang_thai` — thứ CÓ
    lọc theo chúng — nên nhánh của nó rất dễ bị "sửa cho nhất quán" nhầm.
    Liên kết mang con số này (`?tat_ca=1`) bỏ hết bộ lọc, nên con số phải là
    con số người ta thấy SAU KHI bấm.
    """
    _hai_sale(conn, batch)
    tong = KH.danh_sach(conn).tong
    assert KH.tong_quan_danh_ba(conn, sale="0104").tong_tat_ca == tong
    assert KH.tong_quan_danh_ba(conn, sale="0104", nhom="im", hang="S",
                                tinh="東京都").tong_tat_ca == tong


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


# ---- dem_va_can_xu_ly: đếm + can_xu_ly gộp MỘT lượt hỏi (soát hiệu năng 5b) ----

def test_dem_va_can_xu_ly_dem_TOAN_CONG_TY_danh_sach_theo_sale(conn, batch, monkeypatch):
    """[IMPORTANT] Bộ đếm trả về phải KHÔNG lọc theo `sale` (dashboard dùng
    cho thanh sức khoẻ toàn công ty), còn danh sách thì lọc — giống hệt
    `can_xu_ly(sale=...)`. Và cả hàm chỉ được chạy ĐÚNG MỘT lượt hỏi: đây
    đúng là lý do hàm này tồn tại, thay cho count(*) riêng + can_xu_ly()
    riêng — hai câu cùng đánh giá lại mart.khach_360, view đắt nhất của mart
    (đo thật 2026-09-23: ~1.185 ms một lần)."""
    for ma, sale in (("R0104", "0104"), ("R0102", "0102")):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=90)
    _ho_so_khach(conn, batch, "R_OK", "Quán bình thường", salesperson_code="0104")
    _mua_deu(conn, batch, "R_OK", nhip=7, so_lan=6, ngung_truoc=0)
    _neo(conn, batch)

    dem_khac = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem_khac["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    dem, ds = KH.dem_va_can_xu_ly(conn, sale="0104")
    assert dem_khac["n"] == 1, f"chạy {dem_khac['n']} lượt hỏi, phải đúng 1"

    assert {k.ma for k in ds} == {"R0104"}, "danh sách PHẢI lọc theo sale"
    # Bộ đếm là của TOÀN CÔNG TY: cả hai khách "cần xử lý" (R0104 của 0104 và
    # R0102 của 0102) phải được đếm, không chỉ khách của 0104. (Nhãn cụ thể
    # là 'canh_bao' hay 'da_roi_bo' không quan trọng ở đây — cả hai đều thuộc
    # KH.TRANG_THAI_CAN_XU_LY; test khác đã canh nhãn chính xác.)
    can_xu_ly_toan_cty = sum(dem.get(t, 0) for t in KH.TRANG_THAI_CAN_XU_LY)
    assert can_xu_ly_toan_cty >= 2
    assert dem.get("binh_thuong", 0) >= 1

    dem_tat_ca, ds_tat_ca = KH.dem_va_can_xu_ly(conn)
    assert {k.ma for k in ds_tat_ca} == {"R0104", "R0102"}
    assert dem_tat_ca == dem, "bộ đếm không đổi dù không lọc theo sale"


def test_dem_va_can_xu_ly_rong_tra_dem_rong_danh_sach_rong(conn, batch):
    """CSDL trống (hoặc không khách nào khớp) không được làm câu LEFT JOIN ON
    true nổ ra một dòng "khách ma" toàn NULL trong danh sách."""
    _neo(conn, batch)
    dem, ds = KH.dem_va_can_xu_ly(conn, sale="khong-ai-ca")
    assert ds == []
    assert isinstance(dem, dict)


def test_dem_va_can_xu_ly_giong_HET_can_xu_ly_rieng(conn, batch):
    """Kết quả gộp phải khớp với can_xu_ly() gọi riêng — cùng thứ tự, cùng
    tập khách — chỉ khác số lượt hỏi."""
    for ma, sale in (("RG01", "0104"), ("RG02", "0104")):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", salesperson_code=sale)
    _mua_deu(conn, batch, "RG01", nhip=7, so_lan=6, ngung_truoc=90)
    _mua_deu(conn, batch, "RG02", nhip=7, so_lan=6, ngung_truoc=95)
    _neo(conn, batch)

    rieng = [k.ma for k in KH.can_xu_ly(conn, sale="0104")]
    _, gop = KH.dem_va_can_xu_ly(conn, sale="0104")
    assert [k.ma for k in gop] == rieng


# ---- Tổng quan danh bạ: bốn khối trong một truy vấn (task 3 đợt 4a) ----

def test_tong_quan_danh_ba_chay_dung_MOT_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Bốn khối phân tích = bốn vòng Tokyo nếu làm ẩu. Đo thật:
    một round-trip rỗng đã 47 ms, nên bốn khối rời nhau cộng thêm ~1 giây vào
    mỗi lần mở trang danh sách."""
    _ho_so_khach(conn, batch, "TQ01", "Quán TQ", salesperson_code="0104")
    _mua(conn, batch, "TQ01", HOM_NAY - timedelta(days=3))
    # TQ02 im lặng quá 2 lần nhịp riêng của nó -> chắc chắn rơi vào nhóm việc
    # 'im'. Khách DUY NHẤT của test này được dựng để vào nhóm đó, nên
    # nhom["im"] phải bằng ĐÚNG 1, không chỉ khác 0.
    _ho_so_khach(conn, batch, "TQ02", "Quán TQ rời bỏ")
    _mua_deu(conn, batch, "TQ02", nhip=7, so_lan=6, ngung_truoc=30)
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
    # [IMPORTANT] Bốn khẳng định trên chỉ canh CÁI KHOÁ — chúng đúng cả khi
    # điều kiện JOIN của một nhánh SQL sai và trả về 0 dòng, vì khoá được
    # sinh cứng từ THU_TU_HANG / bộ ba tên nhóm, không phải từ kết quả truy
    # vấn. Bù lại bằng khẳng định GIÁ TRỊ: mỗi khách trong danh bạ có ĐÚNG
    # một hạng, nên tổng số khách theo hạng phải khớp `tong` — sai điều kiện
    # JOIN ở khối 'hang' (vd JOIN thay vì LEFT JOIN, hay lệch cột) sẽ làm
    # tổng này lệch ngay.
    assert sum(n for _, n in tq.hang) == tq.tong
    # Và một khách CỤ THỂ (TQ02) phải rơi đúng nhóm việc mong đợi — không chỉ
    # "có nhóm nào đó khác rỗng".
    assert tq.nhom["im"] == 1


def test_tong_quan_danh_ba_loc_theo_sale(conn, batch):
    """[IMPORTANT] Nhánh `sale` sinh bốn placeholder (`p * 4`) trong UNION ALL
    nhưng trước bản sửa này CHƯA có test nào gọi `tong_quan_danh_ba(sale=...)`
    — ghi chú "đếm sai số tham số thì psycopg báo lỗi ngay" mô tả một lưới an
    toàn không tồn tại, vì không test nào đi qua nhánh có tham số."""
    _hai_sale(conn, batch)
    tq = KH.tong_quan_danh_ba(conn, sale="0104")
    assert tq.tong == 2                                   # chỉ K0104A, K0104B
    assert KH.tong_quan_danh_ba(conn).tong > tq.tong       # còn K0102C + khách neo


def test_trang_danh_sach_chay_dung_BA_luot_hoi(conn, batch, monkeypatch):
    """[IMPORTANT] `/khach-hang` = `tong_quan_danh_ba` (1) + `danh_sach` (2).

    Trước vòng sửa cuối đợt 4a là 5: `danh_sach` chạy thêm một câu đếm theo
    trạng thái và một câu đếm tổng công ty — hai câu mà `tong_quan_danh_ba`
    vốn đã quét đúng bảng đó rồi. Ở đây mỗi lượt hỏi là ~47 ms mạng tới
    Tokyo trước khi CSDL làm gì (§3.1), nên hai con số đó là ~94 ms mỗi lần
    mở trang, trả cho thứ đã nằm sẵn trong một câu lệnh khác.
    """
    _ho_so_khach(conn, batch, "BA01", "Quán ba lượt")
    _mua(conn, batch, "BA01", HOM_NAY)

    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    KH.tong_quan_danh_ba(conn)
    KH.danh_sach(conn)
    assert dem["n"] == 3, f"trang danh sách chạy {dem['n']} lượt hỏi, phải đúng 3"


def test_bo_dem_trang_thai_co_theo_ba_bo_loc_moi(conn, batch):
    """[IMPORTANT] Chip trạng thái mang theo `nhom`/`hang`/`tinh` trong href
    (biến `giu` của template). Bộ đếm không co theo chúng thì con số trên chip
    nói dối về chính danh sách mà nó mở ra: đang lọc nhóm việc `im` mà chip
    hiện "Tất cả (toàn bộ danh bạ)", bấm vào ra ít hơn hẳn.

    Đây là lý lẽ MỚI, thay lý lẽ cũ ("bộ đếm chỉ theo sale") — lý lẽ cũ viết
    khi trang có MỘT bộ lọc, giờ có năm.
    """
    for ma, ngung in (("D0001", 40), ("D0002", 2)):     # D0001 im, D0002 thì không
        _ho_so_khach(conn, batch, ma, f"Quán {ma}")
        for i in range(6):
            _mua(conn, batch, ma, HOM_NAY - timedelta(days=ngung + i * 7))
    _neo(conn, batch)

    tq_tat = KH.tong_quan_danh_ba(conn)
    tq_im = KH.tong_quan_danh_ba(conn, nhom="im")
    assert sum(tq_im.dem_trang_thai.values()) < sum(tq_tat.dem_trang_thai.values()), \
        "bộ đếm không co theo bộ lọc nhóm việc"
    # Và nó phải khớp CHÍNH XÁC số dòng danh sách mà chip "Tất cả" mở ra.
    assert sum(tq_im.dem_trang_thai.values()) == KH.danh_sach(conn, nhom="im").tong
    # Tỉnh cũng vậy: "(không rõ)" là khách chưa có hồ sơ 得意先全情報.
    tq_tinh = KH.tong_quan_danh_ba(conn, tinh=KH.TINH_TRONG)
    assert sum(tq_tinh.dem_trang_thai.values()) == \
        KH.danh_sach(conn, tinh=KH.TINH_TRONG).tong


def test_tong_quan_khong_ro_tinh_van_duoc_dem(conn, batch):
    """[IMPORTANT] Với ĐỦ tỉnh thật (nhiều hơn 8, như 48 tỉnh thật của công
    ty), "(không rõ)" phải vẫn xuất hiện trong khối 'Tập trung ở đâu' dù nó
    xếp hạng THẤP NHẤT. Trộn nó chung với các tỉnh thật rồi cắt top-9 (lỗi cũ)
    sẽ âm thầm đánh rơi đúng nhóm này khi có nhiều hơn 8 tỉnh thật xếp hạng
    cao hơn nó — CSDL thử nghiệm nhỏ (1-2 tỉnh) không bao giờ lộ ra lỗi này,
    vì "(không rõ)" luôn lọt vào top-9 khi tổng số nhóm còn dưới 9."""
    tinh_that = ["北海道", "青森県", "岩手県", "宮城県", "秋田県", "山形県",
                 "福島県", "茨城県", "栃木県"]                 # 9 tỉnh thật
    for i, t in enumerate(tinh_that):
        for j in range(3):          # mỗi tỉnh 3 khách -> luôn xếp trên "(không rõ)"
            ma = f"P{i}{j}"
            _ho_so_khach(conn, batch, ma, f"Quán {ma}", prefecture=t)
            _mua(conn, batch, ma, HOM_NAY - timedelta(days=3))
    _ho_so_khach(conn, batch, "KT01", "Quán không tỉnh", prefecture="")
    _mua(conn, batch, "KT01", HOM_NAY - timedelta(days=3))
    _neo(conn, batch)     # khách neo cũng không có dim_customer -> cũng "(không rõ)"

    tq = KH.tong_quan_danh_ba(conn)
    assert any(t[0] == "(không rõ)" for t in tq.tinh), \
        "'(không rõ)' bị cắt mất khi có nhiều hơn 8 tỉnh thật xếp hạng cao hơn"
    thuc = [t for t in tq.tinh if t[0] != "(không rõ)"]
    assert len(thuc) == 8, "top 8 tỉnh THẬT, không lẫn '(không rõ)' vào phép đếm"
    assert dict(tq.tinh)["(không rõ)"] == 2       # KT01 + khách neo


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
    mà không có gì báo. Khẳng định CẢ BA bộ lọc mới — nhóm việc đã có test
    riêng (`test_loc_theo_nhom_viec`) nên ở đây canh `tinh` và `hang`, cả hai
    kết hợp được với `sale` đã có từ đợt 3.
    """
    # K0001 doanh thu lớn, K0002 doanh thu rất nhỏ, khách neo ở giữa -> ba mức
    # doanh thu tách bạch cho ra ba hạng khác nhau (n=3: cume_dist 1/3 -> 'B',
    # 2/3 -> 'C', 3/3 -> 'D') — đủ để phân biệt bộ lọc `hang` mà không cần
    # đoán ngưỡng phần trăm chính xác.
    _ho_so_khach(conn, batch, "K0001", "Quán K lớn", salesperson_code="0104",
                 prefecture="愛知県")
    _mua(conn, batch, "K0001", HOM_NAY - timedelta(days=3),
         tien=1_000_000, tax=100_000, gp=300_000)
    _ho_so_khach(conn, batch, "K0002", "Quán K nhỏ", salesperson_code="0104",
                 prefecture="愛知県")
    _mua(conn, batch, "K0002", HOM_NAY - timedelta(days=3),
         tien=1_000, tax=100, gp=300)
    _neo(conn, batch)

    t = KH.danh_sach(conn, tinh="愛知県", sale="0104")
    assert "K0001" in {k.ma for k in t.khach}
    assert KH.danh_sach(conn, tinh="東京都", sale="0104").tong == 0

    assert {k.ma for k in KH.danh_sach(conn, hang="B", sale="0104").khach} == {"K0001"}
    assert {k.ma for k in KH.danh_sach(conn, hang="D", sale="0104").khach} == {"K0002"}


# ---- Hồ sơ 360°: bốn khối mới trong HAI truy vấn (task 6 đợt 4a) --------

def test_ho_so_khong_qua_8_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Mỗi vòng hỏi qua pooler Tokyo mất ~47 ms chỉ riêng mạng.
    Trang hồ sơ chậm dần từng đợt là cách nó chết mà không ai thấy ngày nào
    nó chết.

    Ngưỡng giữ nguyên 8 (bất biến của đặc tả §6.2) dù hàm nay chỉ chạy 7:
    chỗ trống đó CÓ CHỦ Ý — vòng sửa cuối đợt 4a gộp hai câu SELECT trùng
    mệnh đề lọc trên `mart.khach_360` để khối tiếp theo thêm được mà không
    phải phá bất biến. Siết xuống 7 là lấy lại đúng chỗ trống vừa tạo ra."""
    _ho_so_khach(conn, batch, "Q0001", "Quán đếm")
    _mua(conn, batch, "Q0001", HOM_NAY - timedelta(days=3))
    _neo(conn, batch)
    dem = {"n": 0}
    that = conn.execute
    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    KH.ho_so(conn, "Q0001")
    assert dem["n"] <= 8, f"ho_so() chạy {dem['n']} truy vấn"


def test_ho_so_mang_bon_khoi_moi(conn, batch):
    """Bốn khối mới phải có DỮ LIỆU THẬT, không chỉ có mặt dưới dạng danh
    sách rỗng — một khối luôn rỗng thì không ai phát hiện nó hỏng."""
    _ho_so_khach(conn, batch, "B0001", "Quán bốn khối", price_level_code="03")
    # XT07: mua đều 7 ngày/lần, lần cuối 10 ngày trước -> dự kiến 3 ngày
    # trước, tức QUÁ HẠN 3 ngày, nhưng CHƯA tới hai lần nhịp (14 ngày) nên đây
    # KHÔNG phải "đã ngừng mua" — đúng khoảng trống mà khối "tháng này chưa
    # mua" lấp.
    #
    # Trước migration 024 khoảng này là "quá hạn nhưng chưa quá 90 ngày" và
    # test gieo lần cuối 30 ngày trước (trễ 23). Con số 23/30 ĐÓ khoá đúng
    # công thức 90 ngày mà 024 dẹp: với nhịp 7 ngày, im 30 ngày đã là hơn bốn
    # lần nhịp — khách đó bỏ mã này từ lâu, không phải "còn gọi kịp".
    for i in range(4):
        _mua(conn, batch, "B0001", HOM_NAY - timedelta(days=10 + i * 7))
    # XT09 bán cho một khách KHÁC -> có tỷ suất để xếp hạng gợi ý, và B0001
    # chưa từng mua nó.
    _mua(conn, batch, "000000000998", HOM_NAY - timedelta(days=5), hang="XT09")
    _hang_master(conn, batch, ("XT07", "Gạo Japonica"), ("XT09", "Nước mắm"))
    _bang_gia(conn, batch, "03", "XT07", 5250)
    _diem_giao(conn, batch, "B0001", "SH01", "Kho Shibuya")
    _neo(conn, batch)

    h = KH.ho_so(conn, "B0001")
    assert [m["ma"] for m in h.chua_mua_thang] == ["XT07"]
    assert h.chua_mua_thang[0]["tre"] == 3
    # …và nó KHÔNG được nằm luôn ở khối "đã ngừng mua": hai khối là hai dải
    # rời nhau của cùng một trục, không phải hai bộ lọc chồng nhau.
    assert "XT07" not in {m["ma"] for m in h.da_ngung_mua}
    assert "XT09" in {g["ma"] for g in h.goi_y}
    assert [b["ma"] for b in h.bac_gia] == ["XT07"]
    assert [d["ma"] for d in h.diem_giao] == ["SH01"]
    # Mặt hàng còn trong hạn mua bình thường KHÔNG được coi là "chưa mua"
    assert "XT09" not in {m["ma"] for m in h.chua_mua_thang}


def test_goi_y_khong_bao_gio_chua_ma_da_mua(conn, batch):
    """Gợi ý bán thứ họ vừa mua tuần trước làm người dùng bỏ luôn cả khối."""
    _ho_so_khach(conn, batch, "G0001", "Quán gợi ý")
    _mua(conn, batch, "G0001", HOM_NAY - timedelta(days=7), hang="XT07")
    # Bảng mã hàng phải có dòng, nếu không khối gợi ý luôn rỗng và khẳng
    # định bên dưới đúng một cách vô nghĩa.
    _hang_master(conn, batch, ("XT07", "Gạo Japonica"), ("XT09", "Nước mắm"))
    _mua(conn, batch, "000000000998", HOM_NAY - timedelta(days=5), hang="XT09")
    _neo(conn, batch)
    h = KH.ho_so(conn, "G0001")
    assert h.goi_y, "khối gợi ý rỗng — test không kiểm được gì"
    assert "XT07" not in {g["ma"] for g in h.goi_y}


def test_khach_khong_co_diem_giao_thi_khoi_tu_an(conn, batch, test_db_url):
    """Chỉ 532/1.710 khách có 直送先. Hiện một bảng rỗng cho 1.178 khách còn
    lại là dạy người ta cuộn nhanh — và ô THẬT nằm giữa những ô trống sẽ bị
    cuộn qua theo."""
    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    _ho_so_khach(conn, batch, "D0001", "Quán không điểm giao")
    _ho_so_khach(conn, batch, "D0002", "Quán có điểm giao")
    for ma in ("D0001", "D0002"):
        _mua_deu(conn, batch, ma, nhip=7, so_lan=4)
    _diem_giao(conn, batch, "D0002", "SH02", "Kho Nagoya")
    _neo(conn, batch)

    c = TestClient(create_app(db_url=test_db_url))
    html = c.get("/khach-hang/D0001").text
    assert "直送先" not in html
    assert "直送先" in c.get("/khach-hang/D0002").text, \
        "khối tự ẩn cả khi khách CÓ điểm giao — ẩn nhầm còn tệ hơn hiện rỗng"


def test_hai_bang_mat_hang_co_cot_nhip_va_tre(conn, batch, test_db_url):
    """Ba cột nhịp đã nằm sẵn trong mart.khach_mat_hang từ task 1-2; không
    đưa lên trang thì chúng chỉ là chi phí tính toán không ai đọc."""
    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    _ho_so_khach(conn, batch, "N0001", "Quán nhịp")
    _mua_deu(conn, batch, "N0001", nhip=7, so_lan=5)
    for i in range(4):          # món đã bỏ hẳn -> bảng "đã ngừng mua"
        _mua(conn, batch, "N0001", HOM_NAY - timedelta(days=120 + i * 7),
             hang="XT08")
    _neo(conn, batch)

    html = TestClient(create_app(db_url=test_db_url)).get("/khach-hang/N0001").text
    # Khớp CHÍNH ô tiêu đề `<th>`: ba chữ này đều có mặt trong đoạn văn giải
    # thích ngay trên bảng, nên khớp chuỗi trần thì cột biến mất test vẫn xanh.
    for cot in ("Nhịp", "Dự kiến lần tới", "Trễ"):
        assert f'<th class="so">{cot}</th>' in html, f"bảng mặt hàng thiếu cột {cot}"


# ---- Vòng sửa sau review đợt 4a ---------------------------------------

def test_ty_suat_goi_y_la_TY_SO_CUA_CAC_TONG(conn, batch):
    """[CRITICAL] Trung bình của TỶ SỐ TỪNG DÒNG khác tỷ số của các TỔNG, và
    ở đây bản sai nguy hiểm hơn là chuyện thuần khiết: một dòng doanh thu
    thuần vài yên cho ra tỷ số hàng chục lần, mà khối gợi ý xếp theo tỷ suất
    giảm dần rồi lấy 8 dòng đầu — nên đúng những mã rác đó chiếm trọn tám
    dòng gợi ý của MỌI khách. 赤伝 (số âm, luật dự án cấm lọc bỏ) làm mẫu số
    âm nhỏ, nên chuyện này có thật.

    XT09 bán hai lần: một dòng bình thường (lãi 30.000/doanh thu thuần
    100.000 = 30%) và một dòng tí hon (5/1 = 500%).
      * tỷ số của các tổng   = 30.005 / 100.001 ≈ 30,0%   <- ĐÚNG
      * trung bình các tỷ số = (0,3 + 5,0) / 2 = 265%     <- SAI
    """
    _ho_so_khach(conn, batch, "T0001", "Quán tỷ suất")
    _mua(conn, batch, "T0001", HOM_NAY - timedelta(days=7), hang="XT07")
    _hang_master(conn, batch, ("XT07", "Gạo Japonica"), ("XT09", "Nước mắm"))
    _mua(conn, batch, "000000000998", HOM_NAY - timedelta(days=5), hang="XT09")
    _mua(conn, batch, "000000000998", HOM_NAY - timedelta(days=6),
         tien=11, tax=10, gp=5, hang="XT09")
    _neo(conn, batch)

    g = next(g for g in KH.ho_so(conn, "T0001").goi_y if g["ma"] == "XT09")
    assert abs(g["ty_suat"] - 0.30) < 0.01, \
        f"tỷ suất {g['ty_suat']:.4f} — trung bình của các tỷ số (~2,65) chứ không phải tỷ số của các tổng"


def test_ty_suat_mat_hang_dung_cung_cong_thuc_voi_bao_cao(conn, batch):
    """Chỉ số chỉ có MỘT nhà. mart.ty_suat_mat_hang và mart.ban_theo_san_pham
    (014) phải trả cùng một con số khi kho chỉ có một kỳ kế toán — khác nhau
    là một trong hai đang tính sai."""
    _mua(conn, batch, "000000000998", HOM_NAY, hang="XT09")
    _mua(conn, batch, "000000000998", HOM_NAY - timedelta(days=1),
         tien=11, tax=10, gp=5, hang="XT09")
    a = conn.execute("SELECT ty_suat FROM mart.ty_suat_mat_hang "
                     "WHERE product_code = 'XT09'").fetchone()[0]
    b = conn.execute("SELECT ty_suat FROM mart.ban_theo_san_pham "
                     "WHERE product_code = 'XT09'").fetchone()[0]
    assert abs(float(a) - float(b)) < 1e-9


def test_loc_tinh_trong_tim_dung_khach_chua_co_ho_so(conn, batch):
    """[IMPORTANT] Khối "Tập trung ở đâu" nói "(không rõ): N", bấm vào phải ra
    ĐÚNG N khách đó. Đổ thẳng nhãn "(không rõ)" vào `<option value>` thì
    `danh_sach` chạy `prefecture = '(không rõ)'` — không dòng nào khớp, và
    người dùng thấy hai con số mâu thuẫn trên cùng một màn hình. Đúng nhóm
    khách cần dọn (có dòng bán nhưng chưa có hồ sơ 得意先全情報) lại là nhóm
    không có đường nào mở ra."""
    _ho_so_khach(conn, batch, "P0001", "Quán có tỉnh", prefecture="愛知県")
    _mua(conn, batch, "P0001", HOM_NAY - timedelta(days=3))
    _mua(conn, batch, "000000000998", HOM_NAY - timedelta(days=3))  # không hồ sơ
    _neo(conn, batch)

    t = KH.danh_sach(conn, tinh=KH.TINH_TRONG)
    assert {k.ma for k in t.khach} == {"000000000998", "000000000999"}
    tq = KH.tong_quan_danh_ba(conn)
    assert dict(tq.tinh)[KH.KHONG_RO] == t.tong, \
        "con số trong khối phân tích và số dòng bộ lọc trả về phải khớp"


def test_bang_gia_chi_hien_gia_MOI_NHAT_cua_TUNG_QUY_CACH(conn, batch):
    """[IMPORTANT] kome/loaders/price.py ghi một dòng MỚI mỗi lần nạp master,
    và khoá bảng có cả `pack_code`. Không lọc thì sau ba lần nạp trang hiện
    cùng một tên hàng SÁU LẦN với sáu con số khác nhau (3 lần nạp × 2 quy
    cách), dưới nhãn "giá đáng lẽ phải bán". Đây là màn hình người ta nhìn
    TRƯỚC KHI báo giá cho khách."""
    _ho_so_khach(conn, batch, "V0001", "Quán bảng giá", price_level_code="03")
    _mua(conn, batch, "V0001", HOM_NAY - timedelta(days=3))
    _hang_master(conn, batch, ("XT07", "Gạo Japonica"))
    _bang_gia(conn, batch, "03", "XT07", 1000, quy_cach="00", tu_ngay="2026-01-01")
    _bang_gia(conn, batch, "03", "XT07", 1200, quy_cach="00", tu_ngay="2026-06-01")
    _bang_gia(conn, batch, "03", "XT07", 5000, quy_cach="02", tu_ngay="2026-06-01")
    _neo(conn, batch)

    bg = KH.ho_so(conn, "V0001").bac_gia
    assert [b["gia"] for b in bg] == [1200, 5000], \
        "giá cũ vẫn còn, hoặc hai quy cách bị trộn làm một"
    assert [b["quy_cach"] for b in bg] == ["バラ (lẻ)", "ケース (thùng)"]
    assert all(b["tu_ngay"] == "2026-06-01" for b in bg)


def test_trang_danh_sach_giu_bo_loc_moi_qua_lien_ket(conn, batch, test_db_url,
                                                     monkeypatch):
    """[IMPORTANT] Sót một liên kết là người đang lọc bấm một cái bị ném về
    danh sách đầy mà không hiểu vì sao.

    Test này PHẢI gieo dữ liệu. Bản đầu chạy trên CSDL vừa bị TRUNCATE nên
    `t.khach` rỗng, nhánh `{% if t.khach %}` không render, và BỐN liên kết
    sắp xếp cùng HAI liên kết phân trang — đúng những cái nó nói mình bảo vệ
    — không hề có mặt trong HTML được kiểm. Ngưỡng 8 vẫn đạt nhờ các chip,
    nên xoá `giu` khỏi chính nút "Sau →" mà test vẫn xanh.
    """
    import re as _re

    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    # 40 khách nền doanh thu nhỏ. Hạng 'S' là 5% trên cùng theo cume_dist,
    # nên với ít hơn ~20 khách thì KHÔNG AI là 'S' và bộ lọc hang=S trả về
    # danh sách rỗng — tức cái lỗ cũ quay lại.
    _mua_nhieu(conn, batch,
               [(f"F{i:03d}", HOM_NAY - timedelta(days=3), 1_100, "XT07")
                for i in range(40)], ma_lo="F")
    # Hai khách mục tiêu: 愛知県, doanh thu lớn nhất kho (-> 'S'), im 40 ngày
    # trên nhịp 7 ngày (-> nhóm việc 'im').
    for ma in ("A0001", "A0002"):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", prefecture="愛知県")
    _mua_nhieu(conn, batch,
               [(ma, HOM_NAY - timedelta(days=40 + i * 7), 5_000_000, "XT07")
                for ma in ("A0001", "A0002") for i in range(6)], ma_lo="A")
    _neo(conn, batch)

    monkeypatch.setattr(KH, "MOI_TRANG", 1)      # 2 khách khớp -> 2 trang
    c = TestClient(create_app(db_url=test_db_url))
    html = c.get("/khach-hang?nhom=im&hang=S&tinh=愛知県").text
    assert "Quán A0001" in html, \
        "không khách nào khớp cả ba bộ lọc — test lại không đi qua thứ nó bảo vệ"

    def _lien_ket(mau, ten):
        m = _re.search(r'href="(/khach-hang\?' + mau + r'[^"]*)"', html)
        assert m, f"không thấy liên kết {ten} trong HTML"
        for ky in ("nhom=im", "hang=S", "tinh="):
            assert ky in m.group(1), f"liên kết {ten} rơi mất {ky}"

    for sap in ("doanh_thu", "ty_suat", "im_lang", "gan_nhat"):
        _lien_ket("sap=" + sap, f"sắp xếp {sap}")
    _lien_ket("trang=2", "phân trang 'Sau →'")

    assert html.count("nhom=im") >= 8, "bộ lọc nhóm rơi khỏi một số liên kết"
    assert "hang=S" in html and "tinh=" in html


def test_o_chon_tinh_khong_am_tham_xoa_bo_loc_dang_bat(conn, batch, test_db_url):
    """[IMPORTANT] Danh sách `<option>` chỉ có 8 tỉnh đông nhất CỦA PHẠM VI
    ĐANG XEM, mà phạm vi co theo sale/nv. Tỉnh đang lọc không nằm trong đó
    thì `<select>` hiện "— mọi tỉnh —" trong khi danh sách vẫn đang bị lọc và
    mọi liên kết vẫn mang `tinh=…`: ô điều khiển nói một đằng, dữ liệu một
    nẻo. Bấm "Lọc" lần nữa là bộ lọc biến mất mà không ai nhấn nút nào để
    xoá nó."""
    from fastapi.testclient import TestClient
    from kome.web.app import create_app

    _ho_so_khach(conn, batch, "O0001", "Quán Tokyo", prefecture="東京都")
    _mua(conn, batch, "O0001", HOM_NAY - timedelta(days=3))
    _neo(conn, batch)

    c = TestClient(create_app(db_url=test_db_url))
    html = c.get("/khach-hang?tinh=沖縄県").text
    assert '<option value="沖縄県" selected>' in html, \
        "tỉnh đang lọc không có option của chính nó — ô chọn sẽ âm thầm xoá bộ lọc"
