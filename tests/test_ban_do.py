"""Đợt 4c — bảng tra 47 tỉnh, view gộp theo tỉnh, và tầng Python dựng bản đồ."""
import re
from datetime import date, timedelta

import pandas as pd

from kome.ban_do import ban_do


# Ba hàm gieo dữ liệu dưới đây chép NGUYÊN VĂN từ tests/test_khach_hang.py —
# dùng chung cho cả ba task của đợt 4c (Task 2, Task 3 dùng lại). Tên và chữ
# ký phải giữ y hệt bản gốc, nếu không hai task sau chép lại sẽ lệch.

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


# Mốc thời gian của mọi phép tính = ngày bán mới nhất trong kho.
HOM_NAY = date(2026, 7, 31)


def test_dim_prefecture_du_47_tinh(conn):
    assert conn.execute("SELECT count(*) FROM core.dim_prefecture").fetchone()[0] == 47


def test_ma_jis_du_01_den_47_khong_thieu_khong_trung(conn):
    ma = [r[0] for r in conn.execute(
        "SELECT ma_jis FROM core.dim_prefecture ORDER BY ma_jis").fetchall()]
    assert ma == [f"{i:02d}" for i in range(1, 48)]


def test_khong_hai_tinh_cung_mot_o_luoi(conn):
    # Ràng buộc UNIQUE (hang_luoi, cot_luoi) của bảng đã chặn một INSERT trùng
    # ô ngay lúc migration chạy — nên test này KHÔNG BAO GIỜ đỏ vì DỮ LIỆU sai
    # (dữ liệu sai kiểu đó không lọt được qua migration để đến đây). Giá trị
    # thật của nó là canh CHÍNH RÀNG BUỘC còn tồn tại: bắt một migration sau
    # này lỡ DROP/CREATE lại bảng mà quên chép UNIQUE — lúc đó, và chỉ lúc đó,
    # một tỉnh chồng ô mới lọt vào được và bài test này mới có cơ hội đỏ.
    trung = conn.execute("""
        SELECT hang_luoi, cot_luoi, count(*) FROM core.dim_prefecture
        GROUP BY 1, 2 HAVING count(*) > 1""").fetchall()
    assert trung == []


def test_moi_vung_la_mot_khoi_lien_nhau(conn):
    # Kề 8 hướng (kể cả chéo). Một vùng bị vỡ làm đôi trên lưới là lưới đặt sai,
    # và mắt người đọc bản đồ sẽ thấy trước khi test thấy.
    o = {}
    for vung, h, c in conn.execute(
            "SELECT vung, hang_luoi, cot_luoi FROM core.dim_prefecture").fetchall():
        o.setdefault(vung, set()).add((h, c))
    for vung, cells in o.items():
        dau = next(iter(cells))
        tham, hang_doi = {dau}, [dau]
        while hang_doi:
            h, c = hang_doi.pop()
            for dh in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    ke = (h + dh, c + dc)
                    if ke in cells and ke not in tham:
                        tham.add(ke)
                        hang_doi.append(ke)
        assert tham == cells, f"vùng {vung} bị vỡ thành nhiều khối rời"


def test_ten_tinh_khop_chuoi_OBC_that(conn, batch):
    # Khoá nối là chính chuỗi tên tỉnh OBC ghi. Sai một ký tự là tỉnh đó rỗng
    # vĩnh viễn trên bản đồ, và không có lỗi nào nổ ra. Test phải DÙNG dòng nó
    # gieo — khẳng định phép NỐI THẬT (JOIN core.dim_customer trên
    # dim_prefecture.ten), không chỉ khẳng định dim_prefecture có sẵn dòng
    # '東京都' (điều đó đúng ngay cả khi phép nối hỏng hoàn toàn).
    conn.execute("""
        INSERT INTO core.dim_customer
            (customer_code, customer_name, prefecture, is_current, valid_from, batch_id)
        VALUES ('BD01', 'Quan an Tokyo', '東京都', true, '2026-01-01', %s)""", (batch(1),))
    dem = conn.execute("""
        SELECT count(*) FROM core.dim_prefecture p
        JOIN core.dim_customer c ON c.prefecture = p.ten
        WHERE c.customer_code = 'BD01'""").fetchone()[0]
    assert dem == 1


def test_ten_la_ten_ngan_cong_dung_MOT_hau_to_ca_47_dong(conn):
    # [Vòng sửa 1, hạng mục 4] test_ten_tinh_khop_chuoi_OBC_that ở trên chỉ
    # phủ ĐÚNG 1/47 chuỗi (東京都). Một tỉnh khác gõ sai hậu tố (vd 大阪県 thay
    # vì 大阪府) sẽ lọt qua test đó mà không bị bắt — nó chỉ kiểm Tokyo.
    #
    # Test này quét cả 47 dòng đã gieo: `ten` phải bằng `ten_ngan` nối thêm
    # ĐÚNG MỘT ký tự hậu tố trong {都, 道, 府, 県} — đúng bất biến đo được
    # trên CSDL thật (CLAUDE.md: "cả 47 đều có hậu tố 都/道/府/県").
    #
    # NGOẠI LỆ DUY NHẤT: 北海道 (ma_jis='01') — hậu tố 道 nằm SẴN TRONG tên
    # ngắn, nên ten == ten_ngan, không nối thêm gì. Ngoại lệ này viết TƯỜNG
    # MINH bằng đúng mã JIS '01', KHÔNG bỏ qua bằng một điều kiện chung
    # chung kiểu "nếu ten == ten_ngan thì cho qua" — làm vậy sẽ vô tình cho
    # qua CẢ một tỉnh khác lỡ gõ ten_ngan trùng hệt ten (tức bị thiếu mất
    # hậu tố), đúng loại lỗi gõ sai mà test này được viết ra để bắt.
    rows = conn.execute(
        "SELECT ma_jis, ten, ten_ngan FROM core.dim_prefecture ORDER BY ma_jis"
    ).fetchall()
    assert len(rows) == 47
    for ma_jis, ten, ten_ngan in rows:
        if ma_jis == "01":
            assert ten == ten_ngan == "北海道", "ngoại lệ 北海道 không còn đúng"
            continue
        assert ten[:-1] == ten_ngan, \
            f"{ma_jis}: '{ten}' không phải '{ten_ngan}' + một hậu tố"
        assert ten[-1] in "都道府県", \
            f"{ma_jis}: hậu tố '{ten[-1]}' không nằm trong 都/道/府/県"


def test_khach_theo_tinh_dung_EXISTS_khong_JOIN_vao_khach_nhom_viec(conn):
    # [Vòng sửa 1] Bản đầu của test này gieo MỘT khách rồi so sánh
    # sum(so_khach) của view với count(*) của khach_360 — trang trí thuần
    # tuý: người soát dựng song song một bản SAI (LEFT JOIN thẳng vào
    # mart.khach_nhom_viec) và chạy cùng dữ liệu, cả hai bản cho CÙNG một số.
    # Lý do: khách BD01 (1 lần mua, khách duy nhất trong CSDL test) thuộc
    # ĐÚNG 0 nhóm việc — 1 lần mua thì trang_thai='chua_du_lich_su' (chưa đủ
    # 3 lần mua) chứ không phải 'im'; là khách duy nhất thì cume_dist=1.0 nên
    # hạng='D' chứ không 'S'/'A' nên không thể là 'tut'; ty_le_im_lang NULL
    # nên không phải 'moi'. Cả hai bản JOIN/EXISTS đều nhân với 0 dòng.
    #
    # Không có cách gieo một khách "vừa im vừa tụt" mà không mong manh: nó
    # phải khớp ĐỒNG THỜI công thức của cả hai nhóm việc, và vỡ ngay khi MỘT
    # trong hai công thức đổi — một test hồi quy không được phép phụ thuộc
    # vào chi tiết nội bộ dễ đổi của một view KHÁC.
    #
    # Nên canh ở TẦNG ĐỊNH NGHĨA thay vì tầng dữ liệu: đọc thẳng văn bản SQL
    # của view bằng pg_get_viewdef và khẳng định nó không nhắc tới
    # mart.khach_nhom_viec bằng JOIN — bất kể dữ liệu nào được gieo. Bắt
    # được đúng lớp lỗi migration 022 mô tả (LEFT JOIN nhân dòng), mà không
    # cần dựng ra được một ca dữ liệu thật sự lộ ra hậu quả đó.
    dinh_nghia = conn.execute(
        "SELECT pg_get_viewdef('mart.khach_theo_tinh'::regclass)").fetchone()[0]
    assert "khach_nhom_viec" in dinh_nghia, \
        "view không còn nhắc tới khach_nhom_viec — can_goi tính bằng gì?"
    assert re.search(r"(?i)\bjoin\s+mart\.khach_nhom_viec\b", dinh_nghia) is None, \
        "view JOIN thẳng vào khach_nhom_viec — phải dùng EXISTS (subquery), " \
        "nếu không một khách thuộc nhiều nhóm việc sẽ nhân dòng và thổi " \
        "phồng so_khach/doanh_thu_12t của tỉnh đó"


# ---------------------------------------------------------------------------
# Task 2 — kome/ban_do.py: bốn bất biến của đặc tả §8
# ---------------------------------------------------------------------------

def _hai_tinh(conn, batch):
    """Hai khách ở hai tỉnh khác nhau — nền chung của ba test dưới."""
    _ho_so_khach(conn, batch, "BD01", "Quan Tokyo", prefecture="東京都")
    _ho_so_khach(conn, batch, "BD02", "Quan Osaka", prefecture="大阪府")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    _mua(conn, batch, "BD02", HOM_NAY - timedelta(days=5))


def test_du_47_o_ke_ca_tinh_khong_co_khach(conn, batch):
    # LEFT JOIN từ dim_prefecture, KHÔNG group by trên khách. Gieo khách ở đúng
    # hai tỉnh; bản đồ vẫn phải có đủ 47 ô, 45 ô trong đó mang số 0.
    _hai_tinh(conn, batch)
    t = ban_do(conn)
    assert len(t.o) == 47
    assert sum(1 for o in t.o if o.so_khach == 0) == 45


def test_tinh_gia_tri_0_khac_bac_thap_nhat(conn, batch):
    # "Không có khách" khác "ít khách". Cùng màu là bản đồ nói dối về vùng trắng.
    _hai_tinh(conn, batch)
    t = ban_do(conn)
    o = {x.ten: x for x in t.o}
    assert o["東京都"].so_khach == 1 and o["北海道"].so_khach == 0
    assert o["北海道"].bac == 0
    assert o["東京都"].bac >= 1


def test_khach_khong_co_tinh_khong_bi_danh_roi_im_lang(conn, batch):
    # Đúng 1/1.710 khách thật rơi vào ca này. Nó phải hiện thành một con số,
    # không phải biến mất giữa bản đồ và tổng.
    _hai_tinh(conn, batch)
    _ho_so_khach(conn, batch, "BD03", "Khong ro tinh", prefecture="")
    _mua(conn, batch, "BD03", HOM_NAY - timedelta(days=5))
    t = ban_do(conn)
    assert t.khong_ro_tinh == 1
    assert sum(x.so_khach for x in t.o) + t.khong_ro_tinh == t.tong["so_khach"]


def test_ban_do_khong_qua_2_truy_van(conn, batch, monkeypatch):
    # Đếm LÚC CHẠY, không bằng AST: một truy vấn nằm trong vòng lặp hay trong
    # một nhánh `if` thì AST đếm là một, còn trang thật chạy bốn mươi bảy lượt.
    # Cơ chế đếm giống hệt tests/test_khach_hang.py và tests/test_san_pham.py
    # (bọc conn.execute qua monkeypatch), không dựng cơ chế thứ hai.
    _hai_tinh(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)

    monkeypatch.setattr(conn, "execute", demo)
    ban_do(conn)
    assert dem["n"] <= 2, f"{dem['n']} lượt hỏi, trần là 2"
