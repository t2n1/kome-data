"""Bảng phủ dữ liệu — module dùng chung cho trang web và lệnh terminal.

Hai thứ phải luôn đúng ở đây:
  1. Kỳ kế toán là 1/8 → 31/7 (đọc từ core.dim_date), KHÔNG phải 4月始まり.
  2. "Ngoài phạm vi" KHÁC "không có dữ liệu" — tháng trước 2025-03-03 không
     bao giờ được hiện như thiếu dữ liệu.
"""
from datetime import date

import pandas as pd
import pytest

from kome.coverage import (CO, KHONG, NGHI, NGOAI, DAU_DU_LIEU, tinh_bang_phu,
                           tinh_bang_ngay)


def _nap_ban(conn, batch, ngay: date, amount=10_000, tax=1_000, gp=3_000):
    """Một dòng bán hàng thật cho ngày đã cho (qua loader, không SQL tay)."""
    from kome.loaders import sales

    b = batch(int(ngay.strftime("%Y%m%d")) % 100_000)
    sales.load(conn, pd.DataFrame([{
        "slip_no": ngay.strftime("S%Y%m%d"), "line_seq": 1, "sales_date": ngay,
        "customer_code": "000000009292", "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": amount, "tax_amount": tax, "cost": amount - tax - gp,
        "gross_profit": gp, "paid_amount": 0, "batch_id": b,
    }]), ngay, b)
    conn.commit()
    return b


def _nap_ton(conn, batch, ngay: date, n: int = 1):
    """n ảnh chụp tồn kho, mỗi ngày một ảnh, bắt đầu từ `ngay`."""
    from datetime import timedelta

    b = batch(900_000 + ngay.month * 100 + ngay.day)
    conn.execute(
        """INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name)
           VALUES ('01','Kho chinh') ON CONFLICT DO NOTHING"""
    )
    for i in range(n):
        d = ngay + timedelta(days=i)
        conn.execute(
            """INSERT INTO core.fact_inventory_daily
                 (snapshot_date, product_code, warehouse_code, stock_qty, batch_id)
               VALUES (%s, 'XT07', '01', 10, %s)""",
            (d, b),
        )
    conn.commit()
    return b


def _o(bang, thang: str, khoa: str):
    for t in bang.thang:
        if t.thang == thang:
            for o in t.o:
                if o.cot.khoa == khoa:
                    return o
    raise AssertionError(f"không tìm thấy ô {thang}/{khoa}")


def _ky(bang, fy: int):
    for k in bang.ky:
        if k.company_fy == fy:
            return k
    raise AssertionError(f"không tìm thấy kỳ {fy}")


def test_nhom_theo_ky_cong_ty_khong_phai_nam_tai_chinh_nhat(conn):
    """[IMPORTANT] Tháng 9/2025 thuộc kỳ công ty 2026 (1/8/25 → 31/7/26),
    còn năm tài chính Nhật chuẩn xếp nó vào 2025. Nếu ai đó thay
    core.dim_date.company_fy bằng công thức 4月始まり tự viết, test này đỏ."""
    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    fy = {t.thang: t.company_fy for t in bang.thang}
    assert fy["2025-09"] == 2026
    assert fy["2025-07"] == 2025        # tháng chốt của kỳ trước
    assert fy["2025-08"] == 2026        # ngày đầu kỳ mới
    assert [k.company_fy for k in bang.ky] == [2025, 2026, 2027]
    # Nhãn dùng SỐ KỲ theo cách công ty tự gọi (第7期), không phải năm kết thúc —
    # xem db/migrations/013_so_ky_ke_toan.sql. Kỳ 7 = 2025-08-01 → 2026-07-31.
    assert _ky(bang, 2026).nhan == "Kỳ 7 (2025-08 → 2026-07)"
    assert (_ky(bang, 2026).dau, _ky(bang, 2026).cuoi) == (
        date(2025, 8, 1), date(2026, 7, 31))


def test_thang_truoc_moc_du_lieu_la_NGOAI_PHAM_VI_khong_phai_thieu(conn):
    """[IMPORTANT] Đặc tả §2.2.1: dữ liệu bán hàng bắt đầu 2025-03-03, trước
    đó KHÔNG TỒN TẠI — công ty không còn lưu. "Ngoài phạm vi" và "thiếu dữ
    liệu" đòi hai hành động khác hẳn nhau: một bên là đừng đi tìm, một bên là
    phải xuất lại file từ OBC ngay. Hiện nhầm thành "thiếu" là bắt người ta
    đi tìm thứ vĩnh viễn không có."""
    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    assert DAU_DU_LIEU == date(2025, 3, 3)

    # 2024-08 .. 2025-02: TRỌN tháng nằm trước mốc -> ngoài phạm vi, MỌI cột.
    for thang in ("2024-08", "2024-12", "2025-02"):
        for o in next(t for t in bang.thang if t.thang == thang).o:
            assert o.trang_thai == NGOAI, f"{thang}/{o.cot.khoa}"
            assert o.ky_hieu == "—"

    # 2025-03 chứa chính ngày 3/3 -> trong phạm vi, thiếu là thiếu THẬT.
    t = next(t for t in bang.thang if t.thang == "2025-03")
    assert t.ngoai_pham_vi is False
    assert all(o.trang_thai == KHONG for o in t.o)
    assert _o(bang, "2025-03", "ban").ky_hieu == "·"


def test_ky_2025_khong_du_12_thang_trong_pham_vi(conn):
    """Kỳ 2025 (8/2024 → 7/2025) chỉ có 5 tháng trong phạm vi dữ liệu
    (3→7/2025). Đem tổng kỳ đó so với kỳ 2026 là so 5 tháng với 12 tháng."""
    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    assert _ky(bang, 2025).du_12_thang is False
    assert sum(1 for t in _ky(bang, 2025).thang if not t.ngoai_pham_vi) == 5
    assert _ky(bang, 2026).du_12_thang is True


def test_thang_chot_ky_lay_tu_dim_date(conn):
    """is_fy_end_month của core.dim_date: tháng 7, và chỉ tháng 7."""
    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    chot = sorted(t.thang for t in bang.thang if t.la_thang_chot_ky)
    assert chot == ["2025-07", "2026-07"]
    t = next(t for t in bang.thang if t.thang == "2026-07")
    assert t.company_fy_month == 12          # tháng thứ 12 của kỳ


def test_o_co_du_lieu_ban_hien_dau_tron(conn, batch):
    _nap_ban(conn, batch, date(2026, 5, 11))
    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    assert _o(bang, "2026-05", "ban").trang_thai == CO
    assert _o(bang, "2026-05", "ban").ky_hieu == "●"
    assert _o(bang, "2026-04", "ban").trang_thai == KHONG


def test_cot_ton_kho_hien_SO_NGAY_co_anh_chup(conn, batch):
    """[IMPORTANT] Tồn kho là dữ liệu HẰNG NGÀY: một tháng có 1 ngày ảnh chụp
    khác hẳn một tháng có 22 ngày. Dấu ● chung chung giấu mất chuyện đó."""
    _nap_ton(conn, batch, date(2026, 6, 1), n=3)
    _nap_ton(conn, batch, date(2026, 7, 1), n=1)
    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    assert _o(bang, "2026-06", "ton").so_ngay == 3
    assert _o(bang, "2026-06", "ton").ky_hieu == "3"
    assert _o(bang, "2026-07", "ton").ky_hieu == "1"
    assert _o(bang, "2026-08", "ton").so_ngay is None


def test_tong_ket_ky_dung_doanh_thu_THUAN_va_ty_suat(conn, batch):
    """Doanh thu thuần = sum(amount - tax_amount). Lấy thẳng `amount` là cộng
    cả thuế vào doanh thu, và tỷ suất lãi gộp tụt xuống một cách vô cớ."""
    _nap_ban(conn, batch, date(2026, 5, 11), amount=110_000, tax=10_000, gp=30_000)
    _nap_ban(conn, batch, date(2026, 6, 11), amount=220_000, tax=20_000, gp=70_000)
    # Dòng của kỳ TRƯỚC không được lẫn vào kỳ 2026.
    _nap_ban(conn, batch, date(2025, 5, 12), amount=55_000, tax=5_000, gp=10_000)

    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    k = _ky(bang, 2026)
    assert k.doanh_thu_thuan == 300_000
    assert k.lai_gop == 100_000
    assert k.ty_suat == pytest.approx(1 / 3)
    assert _ky(bang, 2025).doanh_thu_thuan == 50_000


def test_ty_suat_la_None_khi_chua_co_doanh_thu(conn):
    """Chưa có doanh thu thì tỷ suất phải là None để màn hình nói "chưa có
    số" — hiện 0% sẽ bị đọc thành "bán mà không lãi đồng nào"."""
    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    assert _ky(bang, 2026).ty_suat is None
    assert _ky(bang, 2026).doanh_thu_thuan == 0


def test_lo_da_hoan_tac_khong_tinh_la_co_du_lieu(conn):
    """File master nhận diện qua tên file trong nhật ký nạp. Lô đã hoàn tác
    (undone_at) nghĩa là dữ liệu ĐÃ BỊ XOÁ khỏi kho — vẫn tô xanh là nói dối."""
    for undone, digest in ((None, "con"), ("now()", "da-huy")):
        conn.execute(
            f"""INSERT INTO meta.ingest_batch
                  (spec_name, source_file, digest, archived_to, row_count, undone_at,
                   data_date)
                VALUES ('shohin', '商品データ_20260610.xlsx', %s, '/tmp/x', 1,
                        {undone or 'NULL'}, DATE '2026-06-10')""",
            (digest,),
        )
    conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count, undone_at,
              data_date)
           VALUES ('shiiresaki', '仕入先_20260710.xlsx', 'ncc', '/tmp/x', 1, now(),
                   DATE '2026-07-10')"""
    )
    conn.commit()

    bang = tinh_bang_phu(conn, hom_nay=date(2026, 9, 16))
    assert _o(bang, "2026-06", "shohin").trang_thai == CO
    assert _o(bang, "2026-07", "shiiresaki").trang_thai == KHONG


def test_module_khong_tu_mo_ket_noi(conn):
    """tinh_bang_phu() nhận sẵn kết nối. Hàm nào tự gọi connect() không tham
    số sẽ âm thầm đọc CSDL THẬT khi trang web chạy với create_app(db_url=…)."""
    import inspect

    import kome.coverage as C

    src = inspect.getsource(C)
    assert "connect(" not in src
    assert "DATABASE_URL" not in src
    assert list(inspect.signature(C.tinh_bang_phu).parameters)[0] == "conn"


# --- Bảng theo NGÀY (3 nguồn của nhịp 13:30) -----------------------------

def _o_ngay(bang, ngay: date, khoa: str):
    d = next(n for n in bang.ngay if n.ngay == ngay)
    return next(o for o in d.o if o.cot.khoa == khoa)


def test_bang_ngay_dung_90_dong_va_ket_thuc_o_hom_nay(conn):
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 17))
    assert len(bang.ngay) == 90
    assert bang.cuoi == date(2026, 9, 17)
    assert bang.dau == date(2026, 6, 20)


def test_bang_ngay_xep_moi_nhat_len_dau(conn):
    """Hôm nay phải ở dòng đầu: người ta mở bảng này để hỏi "hôm qua có sót
    ngày nào không", không phải để đọc lại 90 ngày từ đầu."""
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 17))
    assert bang.ngay[0].ngay == date(2026, 9, 17)
    assert bang.ngay[-1].ngay == date(2026, 6, 20)


def test_ngay_co_ban_thi_CO_ngay_lam_viec_khong_co_thi_KHONG(conn, batch):
    _nap_ban(conn, batch, date(2026, 9, 16))          # thứ Tư
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 17))
    assert _o_ngay(bang, date(2026, 9, 16), "ban").trang_thai == CO
    assert _o_ngay(bang, date(2026, 9, 17), "ban").trang_thai == KHONG


def test_cuoi_tuan_la_NGHI_chu_khong_phai_thieu(conn):
    """Thứ Bảy/Chủ nhật không ai xuất file. 26 ô đỏ mỗi quý sẽ dạy người đọc
    lướt qua cả cột — đúng thứ bảng này sinh ra để chống."""
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 21))
    assert _o_ngay(bang, date(2026, 9, 19), "ban").trang_thai == NGHI   # thứ Bảy
    assert _o_ngay(bang, date(2026, 9, 20), "ban").trang_thai == NGHI   # Chủ nhật
    assert _o_ngay(bang, date(2026, 9, 18), "ban").trang_thai == KHONG  # thứ Sáu


def test_ngay_truoc_moc_du_lieu_la_NGOAI(conn):
    """Trước 2025-03-03 dữ liệu KHÔNG TỒN TẠI — không phải thiếu, không đi tìm."""
    bang = tinh_bang_ngay(conn, hom_nay=date(2025, 3, 10))
    assert _o_ngay(bang, date(2025, 2, 28), "ban").trang_thai == NGOAI
    assert _o_ngay(bang, date(2025, 3, 4), "ban").trang_thai == KHONG


def test_cot_khach_doc_data_date_cua_lo_bo_qua_lo_da_hoan_tac(conn):
    for digest, ngay, undone in (("con", "2026-09-15", "NULL"),
                                 ("da-huy", "2026-09-16", "now()")):
        conn.execute(
            f"""INSERT INTO meta.ingest_batch
                  (spec_name, source_file, digest, archived_to, row_count,
                   undone_at, data_date)
                VALUES ('tokuisaki', '得意先全情報_x.xlsx', %s, '/tmp/x', 1,
                        {undone}, DATE '{ngay}')""",
            (digest,),
        )
    conn.commit()
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 17))
    assert _o_ngay(bang, date(2026, 9, 15), "tokuisaki").trang_thai == CO
    assert _o_ngay(bang, date(2026, 9, 16), "tokuisaki").trang_thai == KHONG


def test_dem_thieu_chi_dem_ngay_lam_viec(conn, batch):
    """Con số tóm tắt không được cộng cả cuối tuần vào, nếu không nó vô nghĩa."""
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 18), so_ngay=5)
    # 14/9 T2 .. 18/9 T6 -> 5 ngày làm việc, chưa nạp gì
    assert bang.thieu["ban"] == 5
    _nap_ban(conn, batch, date(2026, 9, 16))
    assert tinh_bang_ngay(conn, hom_nay=date(2026, 9, 18), so_ngay=5).thieu["ban"] == 4


def test_cuoi_tuan_khong_lam_tang_so_thieu(conn):
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 20), so_ngay=7)
    # 14/9 T2 .. 20/9 CN -> chỉ 5 ngày làm việc
    assert bang.thieu["ban"] == 5


# --- Lưới toàn cảnh (đặc tả 2026-09-25-tong-quan-do-phu-luoi) ---------------
# Ngày làm việc tháng 5/2026 tới 13/5: 1, 7, 8, 11, 12, 13 (4–6/5 là lễ, 2–3,
# 9–10 cuối tuần) — đọc từ mart.lich_kinh_doanh, không đoán.
NGAY_KD_T5 = [1, 7, 8, 11, 12, 13]


def _dong(luoi, khoa):
    return next(d for d in luoi.dong if d.khoa == khoa)


def _o_luoi(luoi, khoa, thang):
    i = [t.thang for t in luoi.thang].index(thang)
    return _dong(luoi, khoa).o[i]


def _lo_nen(conn, spec, ngay, huy=False, digest=None):
    conn.execute(
        f"""INSERT INTO meta.ingest_batch
              (spec_name, source_file, digest, archived_to, row_count, undone_at, data_date)
            VALUES (%s, %s, %s, '/tmp/x', 1, {'now()' if huy else 'NULL'}, %s)""",
        (spec, f"{spec}_{ngay:%Y%m%d}.xlsx", digest or f"{spec}{ngay}{huy}", ngay))
    conn.commit()


def test_luoi_dem_NGAY_LAM_VIEC_va_neu_dich_danh_ngay_thieu(conn, batch):
    """[IMPORTANT] Ô tháng phải nói ĐỦ hay THIẾU, không chỉ có/không: tháng có
    5/6 ngày bán mà hiện như tháng đủ là giấu đúng ngày cần xuất lại. Ngày lễ
    (4–6/5) không bao giờ là "thiếu"."""
    from kome.coverage import tinh_luoi_phu
    for d in (1, 7, 8, 11, 13):                      # sót 12/5
        _nap_ban(conn, batch, date(2026, 5, d))
    luoi = tinh_luoi_phu(conn, hom_nay=date(2026, 5, 13))
    o = _o_luoi(luoi, "ban", "2026-05")
    assert (o.trang_thai, o.so_co) == ("thieu", 5)
    t5 = next(t for t in luoi.thang if t.thang == "2026-05")
    assert t5.so_kd == 6 and [i + 1 for i, c in enumerate(t5.lich) if c == "1"] == NGAY_KD_T5
    assert o.ngay[11] == "k" and o.ngay[3] == "n" and o.ngay[0] == "c"   # 12/5 thiếu · 4/5 lễ · 1/5 có
    b = _dong(luoi, "ban")
    assert (b.dau, b.cuoi, b.thieu) == (date(2026, 5, 1), date(2026, 5, 13), [date(2026, 5, 12)])
    assert _o_luoi(luoi, "ban", "2026-04").trang_thai == "khong"
    assert luoi.thang[0].thang == "2025-03" and luoi.thang[-1].thang == "2026-05"


def test_luoi_thang_du_va_ngay_nghi_co_ban_van_la_co(conn, batch):
    from kome.coverage import tinh_luoi_phu
    for d in NGAY_KD_T5 + [9]:                       # 9/5 thứ Bảy vẫn có phiếu
        _nap_ban(conn, batch, date(2026, 5, d))
    luoi = tinh_luoi_phu(conn, hom_nay=date(2026, 5, 13))
    o = _o_luoi(luoi, "ban", "2026-05")
    assert (o.trang_thai, o.so_co, o.meisai) == ("du", 6, False)
    assert o.ngay[8] == "c" and _dong(luoi, "ban").thieu == []


def test_luoi_danh_dau_ngay_ban_tu_MEISAI(conn, batch):
    """Bẫy #8: `amount` của 売上明細表 là số chưa thuế, ít cột hơn — tháng đến từ
    nguồn đó phải nhìn ra được trên lưới."""
    from kome.coverage import tinh_luoi_phu
    for d in NGAY_KD_T5:
        _nap_ban(conn, batch, date(2026, 5, d))
    conn.execute("UPDATE core.fact_sales_line SET source = 'meisai' WHERE sales_date = '2026-05-13'")
    conn.commit()
    luoi = tinh_luoi_phu(conn, hom_nay=date(2026, 5, 13))
    o = _o_luoi(luoi, "ban", "2026-05")
    assert o.trang_thai == "du" and o.meisai is True
    assert o.ngay[12] == "m" and o.ngay[0] == "c"


def test_luoi_ton_kho_dem_ngay_anh_chup(conn, batch):
    from kome.coverage import tinh_luoi_phu
    _nap_ton(conn, batch, date(2026, 5, 11), n=3)
    luoi = tinh_luoi_phu(conn, hom_nay=date(2026, 5, 13))
    o = _o_luoi(luoi, "ton", "2026-05")
    assert (o.trang_thai, o.so_co) == ("thieu", 3)
    t = _dong(luoi, "ton")
    assert (t.dau, t.cuoi, t.thieu) == (date(2026, 5, 11), date(2026, 5, 13), [])


def test_luoi_du_lieu_nen_theo_data_date_bo_lo_hoan_tac(conn):
    """Dữ liệu nền: bản mới đè bản cũ — ô là "tháng này có bản mới", không phải
    đủ/thiếu. Lô đã hoàn tác không còn trong kho nên không tính."""
    from kome.coverage import tinh_luoi_phu
    _lo_nen(conn, "shohin", date(2026, 4, 10))
    _lo_nen(conn, "shohin", date(2026, 5, 12), huy=True)
    _lo_nen(conn, "tokuisaki", date(2026, 5, 13))
    luoi = tinh_luoi_phu(conn, hom_nay=date(2026, 5, 13))
    sp = _dong(luoi, "shohin")
    assert sp.nhom == "nen" and sp.cuoi == date(2026, 4, 10)
    assert _o_luoi(luoi, "shohin", "2026-04").trang_thai == "moi"
    assert _o_luoi(luoi, "shohin", "2026-04").ngay[9] == "b"
    assert _o_luoi(luoi, "shohin", "2026-05").trang_thai == "trong"
    assert _o_luoi(luoi, "tokuisaki", "2026-05").ngay[12] == "b"
    assert _dong(luoi, "ban").nhom == "lich_su" and _dong(luoi, "ban").dau is None


def test_luoi_chi_co_nguon_dang_dung_va_bang_dich(conn):
    from kome.coverage import COT, tinh_luoi_phu
    luoi = tinh_luoi_phu(conn, hom_nay=date(2026, 5, 13))
    assert [d.khoa for d in luoi.dong] == [c.khoa for c in COT]
    assert _dong(luoi, "seikyu_motocho").nhom == "lich_su" and _dong(luoi, "tanka").nhom == "nen"
    assert _dong(luoi, "ban").bang == "core.fact_sales_line" and _dong(luoi, "ban").spec == "uriage"
    assert _dong(luoi, "ban").nhan == "Bán hàng"
    assert all(len(o.ngay) == len(t.lich) for d in luoi.dong for o, t in zip(d.o, luoi.thang))
