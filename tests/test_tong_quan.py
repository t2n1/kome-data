"""Đợt 5b Task 5 — dashboard chung `/` (kome/tong_quan.py).

Trang không còn gọi `tinh_bao_cao` (5 lượt hỏi chỉ để lấy ba con số của kỳ kế
toán): mọi khối giờ qua `kome.tong_quan.tong_quan()`, đọc `mart.thang_den_
hom_nay` (tháng đến hôm nay, so cùng dải ngày năm trước), không phải kỳ.
"""
from datetime import date, timedelta

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome import tong_quan as TQ
from kome.tuoi_du_lieu import tinh_tuoi
from kome.web.app import create_app

MK = "mat-khau-cua-lan-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"

HOM_NAY = date(2026, 7, 31)


def _ban(conn, batch, ngay: date, ma_hang: str = "AA01", khach="000000009292",
         amount=110_000, tax=10_000, gp=30_000, sale="0104", n=1):
    """Một dòng bán thật qua loader, cùng nếp tests/test_bao_cao_phan_tich.py."""
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
    return b


def _ho_so_khach(conn, batch, ma, ten, salesperson_code="0104"):
    """Một dòng core.dim_customer hiện hành, cùng nếp tests/test_khach_hang.py."""
    b = batch(abs(hash(ma)) % 80_000 + 10_000)
    conn.execute(
        """INSERT INTO core.dim_customer
             (customer_code, valid_from, valid_to, is_current, customer_name,
              phone, prefecture, city, address, salesperson_code, batch_id)
           VALUES (%s, '2025-01-01', '9999-12-31', true, %s, '080-0000-0000',
                   '東京都', '渋谷区', '1-1-1', %s, %s)""",
        (ma, ten, salesperson_code, b))
    conn.commit()


def _mua_deu(conn, batch, ma, nhip: int, so_lan: int, ngung_truoc: int = 0):
    """Khách mua đều `nhip` ngày một lần, lần cuối cách HOM_NAY `ngung_truoc` ngày."""
    for i in range(so_lan):
        _ban(conn, batch, HOM_NAY - timedelta(days=ngung_truoc + i * nhip),
             khach=ma, amount=11_000, tax=1_000, gp=3_000)


def _neo(conn, batch):
    """Một giao dịch ĐÚNG NGÀY HOM_NAY của khách không dính tới phép thử —
    bắt buộc ở mọi test có khách im lặng (mốc thời gian = ngày bán mới nhất
    trong kho), cùng nếp tests/test_khach_hang.py::_neo."""
    _ban(conn, batch, HOM_NAY, khach="000000000999")


def _dem_truy_van(conn, monkeypatch):
    """Bọc `conn.execute` và đếm LÚC CHẠY, cùng nếp tests/test_san_pham.py:50-62."""
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    return dem


def _web(test_db_url):
    return TestClient(create_app(db_url=test_db_url))


@pytest.fixture
def khach(monkeypatch, test_db_url, conn):
    """Dựng app CÓ cổng đăng nhập và một tài khoản "an", cùng nếp fixture
    `khach` của tests/test_ngan_sach_web.py."""
    from kome.web import nguoi_dung as ND

    def _tao(ngan_sach: bool = True):
        monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
        monkeypatch.delenv("VERCEL", raising=False)
        if not ND.dat_quyen(conn, "an", ngan_sach=ngan_sach):
            ND.tao(conn, "an", MK, kho_du_lieu=False, ngan_sach=ngan_sach)
        conn.commit()
        c = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
        c.post("/dang-nhap", data={"ten": "an", "mat_khau": MK})
        return c
    return _tao


# ---------------------------------------------------------------------------

def test_trang_chu_khong_qua_11_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Đo thật: một round-trip tới pooler Tokyo mất 47 ms. Ngân
    sách của cả trang `/` (tong_quan + tinh_tuoi) là <= 11 lượt hỏi.

    [Soát vòng 1] Gieo SẴN một chỉ tiêu tháng — không seed thì khối ngân
    sách chạy trên nhánh "chưa ai đặt chỉ tiêu" (danh sách người rỗng), một
    trường hợp NHẸ HƠN thực tế: công ty này 5 người, tháng nào cũng có ít
    nhất vài người có chỉ tiêu. Đếm trên nhánh rỗng không chứng minh được gì
    về ca THẬT sẽ chạy hằng ngày."""
    _ban(conn, batch, date(2026, 7, 10))
    conn.execute(
        "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
        "VALUES ('0104', '2026-07-01', 3000000)")
    conn.commit()
    dem = _dem_truy_van(conn, monkeypatch)
    TQ.tong_quan(conn, None)
    tinh_tuoi(conn)
    assert dem["n"] <= 11, f"chạy {dem['n']} truy vấn"


def test_o_chi_so_so_cung_so_ngay(conn, batch):
    """`ThangNay` phải so CÙNG DẢI NGÀY năm trước (1 -> ngày của hôm nay),
    KHÔNG phải cả tháng năm trước — đem 10 ngày đầu tháng so cả tháng thì
    tháng nào cũng "sụt 60%"."""
    _ban(conn, batch, date(2025, 7, 5), amount=110_000, tax=10_000, gp=30_000)
    _ban(conn, batch, date(2026, 7, 10), amount=220_000, tax=20_000, gp=60_000, n=2)
    tq = TQ.tong_quan(conn, None)
    tn = tq.thang_nay
    assert tn is not None
    assert tn.thang == "2026-07"
    assert tn.tu_ngay == date(2026, 7, 1) and tn.den_ngay == date(2026, 7, 10)
    assert tn.tu_ngay_ck == date(2025, 7, 1) and tn.den_ngay_ck == date(2025, 7, 10)
    assert tn.dt == 200_000 and tn.dt_ck == 100_000
    assert tn.tang_dt == pytest.approx(1.0)


def test_lien_ket_ngan_sach_chi_hien_khi_co_quyen(khach, conn, batch):
    """Liên kết `/ngan-sach` chỉ hiện khi người xem CÓ cờ `duoc_sua_ngan_sach`
    — mời bấm vào một thứ sẽ từ chối họ tệ hơn không hiện, cùng bất biến đã
    canh cho `/bao-cao` (tests/test_ngan_sach_web.py).

    [Soát vòng 1] `_nav.html` CŨNG có một liên kết `/ngan-sach` riêng (mục
    sidebar), gác bởi ĐÚNG cùng cờ `hien_ngan_sach` — `in`/`not in` trên
    chuỗi `href="/ngan-sach"` không phân biệt được "khối ngân sách của
    dashboard thiếu liên kết" với "chỉ có mỗi liên kết sidebar", vì cả hai
    trường hợp đều cho kết quả `in html` giống nhau khi sidebar đã đúng.
    Đếm SỐ LẦN xuất hiện: không quyền -> 0 (cả sidebar lẫn dashboard đều ẩn);
    có quyền, CHƯA đặt chỉ tiêu tháng này -> 2 (sidebar + liên kết "Đặt chỉ
    tiêu" của khối ngân sách trên dashboard)."""
    _ban(conn, batch, date(2026, 7, 10))
    html_khong_quyen = khach(ngan_sach=False).get("/").text
    assert html_khong_quyen.count('href="/ngan-sach"') == 0

    html_co_quyen = khach(ngan_sach=True).get("/").text
    assert html_co_quyen.count('href="/ngan-sach"') == 2
    assert "Đặt chỉ tiêu" in html_co_quyen


def test_khong_con_khoi_ton_kho_chua_co_du_lieu(conn, batch, test_db_url):
    """`/kho-hang` đã có từ đợt 4b — dòng "Tồn kho — chưa có" của bản `/` cũ
    phải bỏ. Năm nguồn còn thiếu phải liệt kê đủ, đúng chữ."""
    _ban(conn, batch, date(2026, 7, 10))
    html = _web(test_db_url).get("/").text
    assert "Tồn kho" not in html
    assert "chưa có nguồn dữ liệu" in html
    for ten in ("Công nợ", "Dòng tiền", "Mua hàng", "Khiếu nại", "Thời tiết"):
        assert ten in html, f"thiếu nguồn {ten}"


def _dang_nhap_lan(conn, batch, monkeypatch, test_db_url):
    """Đăng nhập "lan" (mã sale 0104), trả về TestClient đã có cookie phiên —
    dùng chung cho các test cần một người đăng nhập có `salesperson_code`."""
    from kome.web import nguoi_dung as ND

    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
    monkeypatch.delenv("VERCEL", raising=False)
    if not ND.dat_quyen(conn, "lan"):
        ND.tao(conn, "lan", MK, salesperson_code="0104")
    conn.commit()
    c = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
    c.post("/dang-nhap", data={"ten": "lan", "mat_khau": MK})
    return c


def test_can_goi_mac_dinh_loc_theo_nguoi_dang_nhap(conn, batch, monkeypatch, test_db_url):
    """Khối "Cần gọi hôm nay" mặc định chỉ hiện khách của người đăng nhập,
    `?tat_ca=1` bỏ lọc — cùng nếp `/can-xu-ly`."""
    for ma, sale in (("R0104", "0104"), ("R0102", "0102")):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=90)
    _neo(conn, batch)

    c = _dang_nhap_lan(conn, batch, monkeypatch, test_db_url)

    html = c.get("/").text
    assert "R0104" in html and "R0102" not in html

    html_tat_ca = c.get("/?tat_ca=1").text
    assert "R0104" in html_tat_ca and "R0102" in html_tat_ca


def test_thanh_suc_khoe_lien_ket_mang_tat_ca_1(conn, batch, test_db_url):
    """[Soát vòng 1, IMPORTANT] Bộ đếm của thanh sức khoẻ (`tq.dem`) LUÔN
    KHÔNG lọc theo sale (toàn công ty), nên mọi liên kết rời khỏi nó phải
    mang `tat_ca=1` — thiếu nó, `/khach-hang`/`/can-xu-ly` rơi về mặc định
    lọc theo người đăng nhập và bấm vào "216 khách bình thường" (đếm của cả
    công ty) lại ra danh sách rỗng/khác của riêng một người — đúng lớp lỗi
    "chip Tất cả (1.710) bấm vào ra 216 khách" đã ghi trong CLAUDE.md.

    Cần gieo đủ ba nhóm (canh_bao/binh_thuong/ngung_giao_dich) để cả ba đoạn
    thanh thật sự có mặt (đoạn `so == 0` không render, xem tong_quan.html)."""
    _ho_so_khach(conn, batch, "R_CANH", "Quán R_CANH")
    _mua_deu(conn, batch, "R_CANH", nhip=7, so_lan=6, ngung_truoc=20)
    _ho_so_khach(conn, batch, "R_BINH", "Quán R_BINH")
    _mua_deu(conn, batch, "R_BINH", nhip=7, so_lan=6, ngung_truoc=0)
    _ho_so_khach(conn, batch, "R_NGUNG", "Quán R_NGUNG ※廃業※")
    _mua_deu(conn, batch, "R_NGUNG", nhip=7, so_lan=1, ngung_truoc=0)
    _neo(conn, batch)

    html = _web(test_db_url).get("/").text
    assert 'href="/can-xu-ly?tat_ca=1"' in html
    assert 'href="/khach-hang?loc=binh_thuong&amp;tat_ca=1"' in html
    assert 'href="/khach-hang?loc=ngung_giao_dich&amp;tat_ca=1"' in html


def test_xem_tat_ca_can_goi_giu_nguyen_trang_thai_loc(conn, batch, monkeypatch, test_db_url):
    """[Soát vòng 1] Khối "Cần gọi hôm nay" đang hiện của AI quyết định liên
    kết "Xem tất cả" phải mang theo trạng thái đó: đang xem của riêng mình
    (mặc định) -> `/can-xu-ly` (không tham số, /can-xu-ly cũng mặc định lọc
    theo mình — nhất quán); đang xem của MỌI NGƯỜI (`?tat_ca=1`) -> phải giữ
    `tat_ca=1`, không thì bấm vào lại rơi về lọc-theo-mình."""
    for ma, sale in (("R0104", "0104"), ("R0102", "0102")):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=90)
    _neo(conn, batch)
    c = _dang_nhap_lan(conn, batch, monkeypatch, test_db_url)

    html = c.get("/").text
    assert 'href="/can-xu-ly">Xem tất cả' in html

    html_tat_ca = c.get("/?tat_ca=1").text
    assert 'href="/can-xu-ly?tat_ca=1">Xem tất cả' in html_tat_ca


def test_dang_xem_moi_nguoi_co_lien_ket_quay_ve_danh_sach_cua_toi(
        conn, batch, monkeypatch, test_db_url):
    """[Soát vòng 1] `?tat_ca=1` chỉ có đường ĐI (`/?tat_ca=1`) mà không có
    đường VỀ thì người đăng nhập có mã sale riêng bị kẹt ở chế độ "mọi
    người" — phải có liên kết quay lại `/` (không tham số) để xem danh sách
    của chính mình."""
    _ban(conn, batch, date(2026, 7, 10))
    c = _dang_nhap_lan(conn, batch, monkeypatch, test_db_url)

    html_tat_ca = c.get("/?tat_ca=1").text
    assert "Xem danh sách của tôi" in html_tat_ca
    assert 'href="/">Xem danh sách của tôi' in html_tat_ca

    # Đang xem CỦA MÌNH (mặc định) thì KHÔNG cần liên kết quay về chính nó.
    html_cua_toi = c.get("/").text
    assert "Xem danh sách của tôi" not in html_cua_toi


def test_trang_chu_kho_rong_van_200(test_db_url):
    r = _web(test_db_url).get("/")
    assert r.status_code == 200


def test_doan_suc_khoe_rong_ti_le_dung_khong_dem_chua_du_lich_su():
    """4 nhóm hiển thị, KHÔNG có 'chua_du_lich_su' (không phải một tình
    trạng quan hệ) — trộn nó vào sẽ pha loãng ba nhóm còn lại."""
    dem = {"canh_bao": 1, "da_roi_bo": 1, "binh_thuong": 2,
           "chua_du_lich_su": 100, "ngung_giao_dich": 0}
    doan = TQ.doan_suc_khoe(dem)
    assert {d["nhom"] for d in doan} == set(TQ.NHOM_SUC_KHOE)
    tong = sum(d["rong"] for d in doan)
    assert tong == pytest.approx(100.0)
    binh_thuong = next(d for d in doan if d["nhom"] == "binh_thuong")
    assert binh_thuong["rong"] == pytest.approx(50.0)  # 2/4
