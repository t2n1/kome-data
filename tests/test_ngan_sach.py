"""Đợt 5a Task 2 — tầng Python của màn nhập ngân sách."""
from datetime import date

import pandas as pd
import pytest

from kome.ngan_sach import BangNhap, LoiSo, bang_nhap, doc_so, luu


def _ban(conn, batch, ngay: date, sale: str = "0104"):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": "000000009292", "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": 110_000, "tax_amount": 10_000, "cost": 70_000,
        "gross_profit": 30_000, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


# ---- đọc số ---------------------------------------------------------------

@pytest.mark.parametrize("chuoi,mong", [
    ("12000000", 12_000_000),
    ("12.000.000", 12_000_000),
    ("12,000,000", 12_000_000),
    (" 12 000 000 ", 12_000_000),
    ("0", 0),
    ("12\xa0000", 12_000),      # NBSP — Excel dán ra kiểu này
    ("12　000", 12_000),    # dấu cách toàn chiều rộng — IME tiếng Nhật
    ("12\t000", 12_000),        # tab
])
def test_doc_so_chap_nhan_moi_kieu_dau_phan_cach(chuoi, mong):
    """Người gõ 60 ô sẽ gõ theo thói quen của họ, không theo thói quen của
    lập trình viên. Mọi kiểu phân cách đều phải ra cùng một số.

    [CRITICAL, vòng soát cuối việc 1] Ba ca NBSP/U+3000/tab canh đúng lỗi đã
    đo thật: `_PHAN_CACH` từng có hai khoá `" "` trùng nhau trong `dict`
    literal (Python tự gộp, NBSP biến mất không lỗi nào nổ) trong khi `_NHOM`
    dùng `\\s` (khớp cả ba ký tự này) — chuỗi qua được kiểm cấu trúc rồi
    `int()` ăn phải NBSP/U+3000/tab còn sót lại và ném ValueError TRẦN."""
    assert doc_so(chuoi) == mong


@pytest.mark.parametrize("chuoi", ["", "   ", None])
def test_o_trong_tra_None_chu_khong_phai_0(chuoi):
    """[CRITICAL] "Chưa đặt" KHÁC "bằng không" — cùng nếp
    mart.san_pham_360.ton. Ô trống trả 0 là ghi vào CSDL một chỉ tiêu bằng 0
    cho người chưa được giao chỉ tiêu nào."""
    assert doc_so(chuoi) is None


@pytest.mark.parametrize("chuoi", ["abc", "12x", "-5", "1.5", "１２３"])
def test_chuoi_rac_nem_LoiSo(chuoi):
    """[CRITICAL] `1.5` nằm trong danh sách này có chủ ý. Dấu chấm là dấu phân
    cách hàng nghìn kiểu Việt, nên một phép "bỏ hết dấu phân cách rồi kiểm tra
    còn toàn chữ số không" biến `1.5` thành **15** — một con số người gõ không
    hề định nhập, ghi vào CSDL không lỗi nào, và chỉ lộ ra khi ai đó nhìn thấy
    chỉ tiêu tháng là ¥15. Vì vậy `doc_so` kiểm CẤU TRÚC NHÓM: mọi nhóm sau
    dấu phân cách phải đúng 3 chữ số."""
    with pytest.raises(LoiSo):
        doc_so(chuoi)


# ---- bảng nhập ------------------------------------------------------------

def test_bang_nhap_co_du_12_thang_dung_thu_tu_ky(conn, batch):
    """Kỳ công ty chạy 1/8 → 31/7, nên tháng đầu bảng là 8月 chứ không phải
    1月. Sắp theo thứ tự lịch dương là bảng nói sai về kỳ."""
    _ban(conn, batch, date(2026, 5, 11))
    b = bang_nhap(conn)
    assert b.company_fy == 2026
    assert b.thang[0] == "2025-08" and b.thang[-1] == "2026-07"
    assert len(b.thang) == 12


def test_ky_CHUA_CO_doanh_thu_nao_van_chon_duoc(conn, batch):
    """[IMPORTANT] Chỉ tiêu được đặt TRƯỚC khi bán. Lấy danh sách kỳ từ
    mart.tong_theo_ky (chỉ những kỳ ĐÃ có doanh thu) thì không ai đặt được
    chỉ tiêu cho năm sau, và lỗi chỉ lộ ra đúng lúc cần dùng."""
    _ban(conn, batch, date(2026, 5, 11))            # chỉ có kỳ 2026
    b = bang_nhap(conn)
    assert 2027 in b.moi_ky, "kỳ chưa có doanh thu vẫn phải chọn được"
    b27 = bang_nhap(conn, 2027)
    assert b27.thang[0] == "2026-08" and len(b27.thang) == 12


def test_ky_CUT_o_hai_dau_dai_lich_KHONG_vao_dai_chip(conn, batch):
    """[CRITICAL, vòng soát cuối việc 5] core.dim_date phủ 2024-01-01 →
    2035-12-31. Kỳ 2024 (8月/2023…7月/2024) thiếu năm cột đầu, kỳ 2036
    (8月/2035…7月/2036) thiếu bảy cột cuối — cả hai chỉ nằm MỘT PHẦN trong
    lịch. Trước bản sửa `DISTINCT company_fy` liệt kê cả hai, màn nhập vẽ đủ
    12 ô rồi bấm Lưu ném ForeignKeyViolation trên một cột không tồn tại. Kỳ
    ĐỦ 12 tháng (2026, 2027) vẫn phải còn nguyên trong dải chip."""
    _ban(conn, batch, date(2026, 5, 11))
    b = bang_nhap(conn)
    assert 2024 not in b.moi_ky, "kỳ 2024 cụt năm cột đầu không được chọn được"
    assert 2036 not in b.moi_ky, "kỳ 2036 cụt bảy cột cuối không được chọn được"
    assert 2026 in b.moi_ky and 2027 in b.moi_ky


def test_bang_nhap_co_du_nguoi_phu_trach_ke_ca_nguoi_chua_dat_chi_tieu(conn, batch):
    _ban(conn, batch, date(2026, 5, 11))
    b = bang_nhap(conn)
    assert [n.ma for n in b.nguoi] == ["0002", "0004", "0102", "0104", "0105"]
    assert b.o == {}, "chưa đặt gì thì không ô nào có giá trị"


def test_o_chua_dat_KHONG_co_trong_dict(conn, batch):
    """[CRITICAL] `o` chỉ chứa ô ĐÃ đặt. Trả 0 cho ô chưa đặt thì màn hình in
    `0` vào chỗ đáng lẽ để trống, và người đọc hiểu thành "chỉ tiêu bằng 0"."""
    _ban(conn, batch, date(2026, 5, 11))
    luu(conn, {("0104", "2026-05"): 0}, None)
    conn.commit()
    b = bang_nhap(conn)
    assert b.o == {("0104", "2026-05"): 0}
    assert ("0105", "2026-05") not in b.o


# ---- ghi ------------------------------------------------------------------

def _nhat_ky(conn):
    return conn.execute(
        """SELECT salesperson_code, thang, muc_tieu_cu, muc_tieu_moi
           FROM app.ngan_sach_nhat_ky ORDER BY id""").fetchall()


def test_luu_ghi_nhat_ky_cho_lan_dat_dau_tien(conn, batch):
    _ban(conn, batch, date(2026, 5, 11))
    assert luu(conn, {("0104", "2026-05"): 9_000_000}, None) == 1
    conn.commit()
    assert _nhat_ky(conn) == [("0104", date(2026, 5, 1), None, 9_000_000)]


def test_luu_KHONG_ghi_gi_khi_khong_co_gi_doi(conn, batch):
    """[CRITICAL] sua_luc/sua_boi phải trả lời "ai đổi con số NÀY lần cuối",
    không phải "ai bấm Lưu lần cuối". Ghi đè cả 60 ô mỗi lần bấm Lưu là xoá
    sạch thông tin đó và làm nhật ký đầy dòng không có gì thay đổi."""
    _ban(conn, batch, date(2026, 5, 11))
    luu(conn, {("0104", "2026-05"): 9_000_000}, None)
    conn.commit()
    assert luu(conn, {("0104", "2026-05"): 9_000_000}, None) == 0
    conn.commit()
    assert len(_nhat_ky(conn)) == 1


def test_o_de_trong_thi_XOA_chi_tieu_va_ghi_nhat_ky(conn, batch):
    _ban(conn, batch, date(2026, 5, 11))
    luu(conn, {("0104", "2026-05"): 9_000_000}, None)
    conn.commit()
    assert luu(conn, {("0104", "2026-05"): None}, None) == 1
    conn.commit()
    assert bang_nhap(conn).o == {}
    assert _nhat_ky(conn)[-1] == ("0104", date(2026, 5, 1), 9_000_000, None)


def test_xoa_dung_CAP_khong_xoa_tich_Descartes(conn, batch):
    """[CRITICAL] Câu đọc hiện trạng và câu XOÁ của luu() ghép (mã, tháng)
    theo VỊ TRÍ qua unnest(hai mảng song song). Nếu ai đó đổi sang hai vế lọc
    độc lập (`salesperson_code = ANY(...) AND thang = ANY(...)`), câu XOÁ sẽ
    xoá TÍCH DESCARTES của hai danh sách — mất chỉ tiêu của người khác ở
    tháng không ai yêu cầu xoá. Gieo 4 cặp (2 mã × 2 tháng), xoá đúng 2 cặp
    CHÉO NHAU, hai cặp còn lại phải còn nguyên."""
    _ban(conn, batch, date(2026, 5, 11))
    luu(conn, {
        ("0104", "2026-05"): 1_000_000,
        ("0104", "2026-06"): 2_000_000,
        ("0105", "2026-05"): 3_000_000,
        ("0105", "2026-06"): 4_000_000,
    }, None)
    conn.commit()

    assert luu(conn, {
        ("0104", "2026-05"): None,
        ("0105", "2026-06"): None,
    }, None) == 2
    conn.commit()

    b = bang_nhap(conn)
    assert ("0104", "2026-05") not in b.o
    assert ("0105", "2026-06") not in b.o
    assert b.o[("0104", "2026-06")] == 2_000_000, "tích Descartes sẽ xoá luôn cặp này"
    assert b.o[("0105", "2026-05")] == 3_000_000, "tích Descartes sẽ xoá luôn cặp này"


def test_luu_giu_nguoi_sua(conn, batch):
    from kome.web import nguoi_dung as ND
    _ban(conn, batch, date(2026, 5, 11))
    uid = ND.tao(conn, "an", "mat-khau-cua-an-2026")
    conn.commit()
    luu(conn, {("0104", "2026-05"): 9_000_000}, uid)
    conn.commit()
    r = conn.execute("SELECT sua_boi FROM app.ngan_sach").fetchone()
    assert r[0] == uid
    r2 = conn.execute("SELECT sua_boi FROM app.ngan_sach_nhat_ky").fetchone()
    assert r2[0] == uid


def test_luu_khong_qua_4_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Mỗi vòng hỏi qua pooler Tokyo mất ~47 ms chỉ riêng mạng.
    60 ô ghi thành 60 câu lệnh là gần ba giây chỉ để bấm một nút Lưu.

    BỐN là trần: đọc hiện trạng · ghi · xoá · nhật ký. Lượt đo dưới đây vừa
    ĐẶT ô mới vừa XOÁ ô đã có trong CÙNG một lệnh gọi, để chạm đúng cả bốn
    câu lệnh — một phiên bản trước của test này chỉ đặt thêm nên không bao
    giờ chạm nhánh XOÁ, và mốc "≤ 4" chưa từng được đo thật ở nhánh đó."""
    _ban(conn, batch, date(2026, 5, 11))
    gia_tri = {(ma, f"2026-{t:02d}") : 1_000_000
               for ma in ("0002", "0004", "0102", "0104", "0105")
               for t in range(1, 8)}

    # Đặt trước hai ô để lượt đo có cái để XOÁ (chạm cả 4 nhánh: đọc · ghi ·
    # xoá · nhật ký), rồi để hai ô đó trống trong lượt đo.
    luu(conn, {("0002", "2026-01"): 500_000, ("0004", "2026-01"): 500_000}, None)
    conn.commit()
    gia_tri[("0002", "2026-01")] = None
    gia_tri[("0004", "2026-01")] = None

    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    luu(conn, gia_tri, None)
    assert dem["n"] <= 4, f"luu() chạy {dem['n']} truy vấn cho 35 ô"


def test_bang_nhap_khong_qua_4_truy_van(conn, batch, monkeypatch):
    _ban(conn, batch, date(2026, 5, 11))
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    bang_nhap(conn)
    assert dem["n"] <= 4, f"bang_nhap() chạy {dem['n']} truy vấn"


# ---- người phụ trách không còn bán (thiết kế lại 2026-09-25) ----------------

def _hien(b):
    return {n.ma: n.hien for n in b.nguoi}


def test_nguoi_khong_ban_90_ngay_bi_AN_nguoi_dang_ban_van_hien(conn, batch):
    """Suy từ DOANH SỐ, không từ khách được giao: OBC vẫn giao khách cho người đã nghỉ."""
    _ban(conn, batch, date(2026, 9, 10), "0104")
    _ban(conn, batch, date(2026, 5, 1), "0102")      # 132 ngày trước mốc
    b = bang_nhap(conn, 2027)
    h = _hien(b)
    assert h["0104"] is True
    assert h["0102"] is False, "không bán trong 90 ngày tới mốc thì ẩn"
    assert h["0002"] is False, "chưa từng bán thì ẩn"
    n = {x.ma: x for x in b.nguoi}
    assert n["0102"].ban_cuoi == date(2026, 5, 1) and n["0102"].con_ban is False
    assert n["0002"].ban_cuoi is None


def test_nguoi_da_nghi_nhung_CO_CHI_TIEU_trong_ky_van_hien(conn, batch):
    """[CRITICAL] Không bao giờ giấu số đã lưu: ẩn người có chỉ tiêu là màn nói "chưa đặt"
    trong khi Báo cáo vẫn tính số đó."""
    _ban(conn, batch, date(2026, 9, 10), "0104")
    luu(conn, {("0002", "lai_gop", "2026-10"): 500_000}, None)
    conn.commit()
    b = bang_nhap(conn, 2027)
    assert _hien(b)["0002"] is True
    assert _hien(b)["0102"] is False


def test_xem_KY_CU_thi_nguoi_con_ban_trong_ky_do_van_hien(conn, batch):
    """Kỳ 2026 (8/2025–7/2026): người bán trong kỳ đó hiện dù nay đã nghỉ."""
    _ban(conn, batch, date(2026, 9, 10), "0104")
    _ban(conn, batch, date(2026, 3, 2), "0102")
    assert _hien(bang_nhap(conn, 2026))["0102"] is True
    assert _hien(bang_nhap(conn, 2027))["0102"] is False


def test_thuc_te_la_doanh_thu_thuan_theo_thang_cong_ty_bang_tong_cac_nguoi(conn, batch):
    """Thực tế tham khảo = `mart.ban_theo_nhan_vien_thang` (doanh thu THUẦN = amount − thuế);
    dòng công ty = cộng mọi người, bằng đúng `mart.ban_theo_thang`."""
    from kome.ngan_sach import CONG_TY
    _ban(conn, batch, date(2025, 10, 6), "0104")
    _ban(conn, batch, date(2025, 10, 7), "0105")
    b = bang_nhap(conn, 2027)          # kỳ trước = 2026 (8/2025–7/2026) cũng phải có
    assert b.thuc_te[("0104", "doanh_thu", "2025-10")] == 100_000
    assert b.thuc_te[("0104", "lai_gop", "2025-10")] == 30_000
    assert b.thuc_te[(CONG_TY, "doanh_thu", "2025-10")] == 200_000
    mart = conn.execute("SELECT doanh_thu_thuan FROM mart.ban_theo_thang WHERE thang = '2025-10'").fetchone()[0]
    assert b.thuc_te[(CONG_TY, "doanh_thu", "2025-10")] == mart
