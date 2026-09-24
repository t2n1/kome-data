"""Đợt 4c — bảng tra 47 tỉnh, view gộp theo tỉnh, và tầng Python dựng bản đồ."""
import re
from datetime import date, timedelta
from html import unescape

import pandas as pd
import pytest
from pathlib import Path

from fastapi.testclient import TestClient

from kome.ban_do import ban_do
from kome.web.app import create_app


@pytest.fixture
def client(conn, test_db_url):
    """TestClient cho trang /ban-do (Task 3).

    Không có fixture `client` chung nào trong tests/conftest.py — mọi test
    khác trong dự án tự dựng TestClient(create_app(...)) tại chỗ. Fixture
    này chỉ gói lại đúng việc đó cho các test của Task 3 bên dưới, và phụ
    thuộc vào `conn` để đảm bảo CSDL đã được dọn sạch TRƯỚC KHI app dựng lên
    (test tự gieo dữ liệu qua `conn` ở đầu thân test)."""
    return TestClient(create_app(db_url=test_db_url))


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


# Hậu tố của từng mã JIS — HẰNG CỐ ĐỊNH của địa lý Nhật Bản, không suy ra
# được từ chính dữ liệu đang kiểm. Đúng BỐN mã lệch khỏi 県:
#   01 北海道 (道) · 13 東京都 (都) · 26 京都府 và 27 大阪府 (府).
# 43 mã còn lại đều là 県. Viết ra ở đây để đọc một cái là biết "mã nào phải
# mang hậu tố nào" — thứ mà một vòng lặp `in "都道府県"` không nói được.
HAU_TO_THEO_MA_JIS = {"01": "道", "13": "都", "26": "府", "27": "府"}
HAU_TO_MAC_DINH = "県"


def test_hau_to_dung_voi_tung_ma_jis_ca_47_dong(conn):
    # [Vòng soát toàn nhánh, mục 2] BẢN TRƯỚC của test này khẳng định
    # `ten[:-1] == ten_ngan` và `ten[-1] in "都道府県"` — hai điều kiện chỉ nói
    # về SỰ NHẤT QUÁN NỘI BỘ giữa hai cột, không nói gì về chuỗi OBC thật.
    # Docstring của nó tuyên bố bắt được "gõ sai hậu tố, vd 大阪県 thay vì
    # 大阪府", nhưng 大阪県 LỌT QUA CHÍNH NÓ: ten[:-1] = 大阪 = ten_ngan ✓ và
    # 県 nằm trong "都道府県" ✓. Tức nó canh đúng thứ nó KHÔNG hứa.
    #
    # Hồi quy mà nó bỏ lọt là hồi quy đắt nhất của bảng này (bẫy #7 của
    # CLAUDE.md): một migration sau đổi 大阪府 -> 大阪県 thì 大阪府 rỗng VĨNH
    # VIỄN trên /ban-do — phép nối (dim_prefecture.ten = dim_customer.
    # prefecture) chỉ lặng lẽ không khớp dòng nào, trang vẫn vẽ 47 ô bình
    # thường, không lỗi nào nổ ra.
    #
    # 47 hậu tố là HẰNG, nên khẳng định theo ma_jis (HAU_TO_THEO_MA_JIS ở
    # trên) chứ không theo một tập ký tự cho phép.
    #
    # NGOẠI LỆ DUY NHẤT về ten_ngan: 北海道 (ma_jis='01') — hậu tố 道 nằm SẴN
    # TRONG tên ngắn, nên ten == ten_ngan, không nối thêm gì. Ngoại lệ này
    # viết TƯỜNG MINH bằng đúng mã JIS '01', KHÔNG bỏ qua bằng một điều kiện
    # chung chung kiểu "nếu ten == ten_ngan thì cho qua" — làm vậy sẽ vô tình
    # cho qua CẢ một tỉnh khác lỡ gõ ten_ngan trùng hệt ten (tức bị thiếu mất
    # hậu tố), đúng loại lỗi gõ sai mà test này được viết ra để bắt.
    rows = conn.execute(
        "SELECT ma_jis, ten, ten_ngan FROM core.dim_prefecture ORDER BY ma_jis"
    ).fetchall()
    assert len(rows) == 47
    for ma_jis, ten, ten_ngan in rows:
        mong_doi = HAU_TO_THEO_MA_JIS.get(ma_jis, HAU_TO_MAC_DINH)
        assert ten[-1] == mong_doi, (
            f"{ma_jis}: '{ten}' có hậu tố '{ten[-1]}', phải là '{mong_doi}' — "
            "sai một ký tự là tỉnh này rỗng vĩnh viễn trên /ban-do, "
            "phép nối chỉ lặng lẽ không khớp dòng nào"
        )
        if ma_jis == "01":
            assert ten == ten_ngan == "北海道", "ngoại lệ 北海道 không còn đúng"
            continue
        assert ten[:-1] == ten_ngan, \
            f"{ma_jis}: '{ten}' không phải '{ten_ngan}' + một hậu tố"


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


def test_gia_tri_bang_nhau_cung_mot_bac_khong_chong_khoang_chu_giai(conn, batch):
    # [Vòng sửa 1] Người soát đo trên CSDL thật, theo từng người phụ trách:
    # 4/5 sale có ít nhất một cặp tỉnh CÙNG một giá trị nhưng rơi vào HAI bậc
    # màu khác nhau (vd bậc 1 và bậc 2 cùng ghi chú giải "1–1"; bậc 2 "2–3"
    # và bậc 3 "3–6" — hai khoảng CHỒNG NHAU tại giá trị 3). Nguyên văn người
    # dùng: "hai tỉnh cùng 1 khách mà một ô đậm hơn ô kia... tôi không biết
    # màu nào là bậc nào".
    #
    # Gieo đúng hình của ví dụ: hai tỉnh 1-khách, năm tỉnh 2-khách (7 tỉnh có
    # giá trị dương trên tổng 47, giống ca đo thật gây lỗi). Giá trị bằng
    # nhau PHẢI về cùng một bậc, và hai giá trị khác nhau (1 và 2) phải khác
    # bậc — nếu không, ntile thô cũng có thể tình cờ gộp chúng và test sẽ bỏ
    # sót đúng lỗi cần bắt.
    mot_khach = ["北海道", "沖縄県"]
    hai_khach = ["東京都", "大阪府", "愛知県", "福岡県", "宮城県"]
    for i, tinh in enumerate(mot_khach):
        ma = f"BDM{i:02d}"
        _ho_so_khach(conn, batch, ma, f"Quan {tinh} mot", prefecture=tinh)
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=5))
    for i, tinh in enumerate(hai_khach):
        for j in range(2):
            ma = f"BDH{i:02d}{j}"
            _ho_so_khach(conn, batch, ma, f"Quan {tinh} {j}", prefecture=tinh)
            _mua(conn, batch, ma, HOM_NAY - timedelta(days=5))

    t = ban_do(conn)
    o_theo_ten = {o.ten: o for o in t.o}
    bac_mot = {o_theo_ten[tinh].bac for tinh in mot_khach}
    bac_hai = {o_theo_ten[tinh].bac for tinh in hai_khach}
    assert len(bac_mot) == 1, "các tỉnh cùng 1 khách phải cùng một bậc"
    assert len(bac_hai) == 1, "các tỉnh cùng 2 khách phải cùng một bậc"
    assert bac_mot != bac_hai, "hai giá trị khác nhau (1 và 2) phải khác bậc"

    # Không hai mục chú giải nào (trong số các mục CÓ dữ liệu) trùng khoảng
    # [tu, den] — kể cả chồng một phần, không chỉ chồng hoàn toàn.
    khoang = [(c["tu"], c["den"]) for c in t.chu_giai if c["tu"] is not None]
    for i in range(len(khoang)):
        for j in range(i + 1, len(khoang)):
            tu_i, den_i = khoang[i]
            tu_j, den_j = khoang[j]
            assert den_i < tu_j or den_j < tu_i, \
                f"chú giải chồng khoảng: {khoang[i]} và {khoang[j]}"


def test_doanh_thu_AM_khong_roi_vao_bac_TRONG(conn, batch):
    # [Vòng soát toàn nhánh, mục 3] Doanh thu 12 tháng của một tỉnh CÓ THỂ ÂM:
    # 赤伝 (phiếu đỏ — hàng trả lại, số ÂM, luật số một cấm lọc bỏ) của một
    # tỉnh chỉ có một hai khách có thể lớn hơn phần mua vào trong cùng 12
    # tháng. Bản trước của _tinh_bac() chỉ coi `> 0` là "có giá trị", nên tỉnh
    # đó rơi vào bậc 0 — bậc mà chú giải gọi là "Trống — không có doanh thu 12
    # tháng" trong khi CHÍNH Ô ĐÓ in ra `¥-100.000`. Màu nói một đằng, số nói
    # một nẻo.
    _ho_so_khach(conn, batch, "BDA1", "Quan Tokyo", prefecture="東京都")
    _mua(conn, batch, "BDA1", HOM_NAY - timedelta(days=5))
    _ho_so_khach(conn, batch, "BDA2", "Quan Osaka tra hang", prefecture="大阪府")
    _mua(conn, batch, "BDA2", HOM_NAY - timedelta(days=5),
         tien=-110_000, tax=-10_000, gp=-30_000)

    t = ban_do(conn, chi_so="doanh_thu")
    o = {x.ten: x for x in t.o}
    assert o["大阪府"].doanh_thu < 0, "fixture hỏng: 赤伝 không cho ra số âm"
    assert o["大阪府"].bac != 0, \
        "doanh thu ÂM bị xếp vào bậc 'trống' — ô in số âm mà chú giải nói 'không có'"
    # Bậc 0 vẫn phải nghĩa là ĐÚNG BẰNG 0, và 45 tỉnh còn lại đúng là như vậy.
    assert o["北海道"].doanh_thu == 0 and o["北海道"].bac == 0
    c0 = next(c for c in t.chu_giai if c["bac"] == 0)
    assert (c0["tu"], c0["den"]) == (0, 0), "bậc 0 phải là khoảng [0, 0]"
    # Chú giải của bậc chứa 大阪府 in ra khoảng THẬT — kể cả khi khoảng đó âm.
    c_am = next(c for c in t.chu_giai if c["bac"] == o["大阪府"].bac)
    assert c_am["tu"] == o["大阪府"].doanh_thu


def test_moi_47_tinh_thuoc_dung_mot_vung_trong_VUNG_THU_TU(conn, batch):
    # [Vòng sửa 1] 8 tên vùng là HẰNG PYTHON (VUNG_THU_TU) trong khi giá trị
    # `vung` nằm ở CSDL (core.dim_prefecture.vung, migration 025). Gõ sai
    # hoặc đổi tên một vùng ở một migration sau mà quên sửa hằng này thì cả
    # dải tỉnh của vùng đó biến mất khỏi mọi tổng theo vùng — không lỗi nào
    # nổ ra, trang vẫn vẽ ra bình thường, chỉ thiếu mấy tỉnh trong khối vùng.
    _hai_tinh(conn, batch)
    t = ban_do(conn)
    assert sum(v["so_tinh"] for v in t.vung) == 47


def test_khach_khong_co_tinh_khong_bi_danh_roi_im_lang(conn, batch):
    # [Vòng sửa 1] Bản đầu gieo prefecture="" (chuỗi rỗng) — SAI DẠNG dữ liệu
    # thật: đo được trên mart.khach_360 có đúng 1 dòng prefecture IS NULL và
    # 0 dòng chuỗi rỗng (chú thích migration 025 cũng ghi vậy). Với chuỗi
    # rỗng, `'' NOT IN (danh_sach_47_ten)` luôn TRUE dù có coalesce hay
    # không (không tên tỉnh nào rỗng), nên test cũ xanh ngay cả khi
    # coalesce(s.prefecture, '') ở kome/ban_do.py bị xoá mất — với NULL thật,
    # `NULL NOT IN (...)` trả NULL (không phải TRUE) và WHERE loại thẳng
    # dòng đó, "(không rõ tỉnh)" sẽ âm thầm hiện 0. Gieo đúng NULL để canh
    # được ca này.
    _hai_tinh(conn, batch)
    _ho_so_khach(conn, batch, "BD03", "Khong ro tinh", prefecture=None)
    _mua(conn, batch, "BD03", HOM_NAY - timedelta(days=5))
    t = ban_do(conn)
    assert t.khong_ro_tinh == 1
    # KHÔNG dùng "sum(o) + khong_ro_tinh == tong": hai truy vấn A/B cùng
    # nguồn mart.khach_theo_tinh nên đẳng thức đó gần như tự đúng bất kể
    # nhánh nào lặng lẽ đánh rớt khách NULL (cả ba số cùng thiếu-hụt một
    # lượng như nhau). Khẳng định TRỰC TIẾP: khách NULL tỉnh không lọt vào
    # bất kỳ ô nào trong 47 ô (tổng so_khach trên lưới vẫn đúng 2, không
    # phải 3) — đây là chỗ một LEFT JOIN sai hoặc một coalesce bị xoá sẽ lộ
    # ra, khác hẳn việc chỉ so hai tổng cộng dồn.
    assert sum(o.so_khach for o in t.o) == 2


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
    # Khoảng xem (đợt B): +1 lượt `khoang_xem.pham_vi` ở tầng API; bản thân
    # BD.ban_do vẫn đúng 2 (test_ban_do_khong_qua_2_truy_van).
    assert dem["n"] <= 3, f"{dem['n']} lượt hỏi, trần là 3"


# ---------------------------------------------------------------------------
# Task 3 — trang /ban-do
# ---------------------------------------------------------------------------

def _o(client, q: str = "") -> dict[str, dict]:
    """Ô bản đồ theo tên tỉnh, từ /api/ban-do (giai đoạn 2: bản đồ là tab React
    của màn Khách hàng, dữ liệu + hình học vẫn dựng ở kome/ban_do.py)."""
    r = client.get("/api/ban-do" + (f"?{q}" if q else ""))
    assert r.status_code == 200, r.text
    return {o["ten"]: o for o in r.json()["t"]["o"]}


BAN_DO_TSX = Path("giao_dien/src/khach/BanDo.tsx")


def test_moi_o_co_con_so_doc_duoc_chu_khong_chi_co_mau(conn, client, batch):
    # Bất biến: mã hoá bằng màu phải kèm thứ đọc được. API trả đủ 47 ô, mỗi ô
    # một con số; ô SVG in chính con số đó (không chỉ tô màu).
    _hai_tinh(conn, batch)
    o = _o(client)
    assert len(o) == 47
    assert all(isinstance(x["gia_tri"], int) for x in o.values())
    nguon = BAN_DO_TSX.read_text(encoding="utf-8")
    assert "{tien ? gon(o.gia_tri) : so(o.gia_tri)}" in nguon, "ô SVG không còn in con số"


def test_bam_o_dan_toi_danh_ba_da_loc_dung_tinh(conn, client, batch):
    # Bấm ô -> tab Danh sách lọc ĐÚNG tên tỉnh (tiếng Nhật, đi qua URL được mã
    # hoá bởi URLSearchParams trong loc.ts). Danh sách lọc theo tên đó phải ra
    # đúng số khách mà ô ghi.
    _hai_tinh(conn, batch)
    o = _o(client, "tat_ca=1")
    d = client.get("/api/khach-hang/ds?tat_ca=1&tinh=%E6%9D%B1%E4%BA%AC%E9%83%BD").json()
    assert d["trang"]["tong"] == o["東京都"]["so_khach"] >= 1
    assert 'moTinh = (ten: string) => dat({ tab: "danh_sach", tinh: ten }, true)' in BAN_DO_TSX.read_text(encoding="utf-8")


def _href(html: str, mau: str, ten_tinh: str) -> str:
    """href của một liên kết tỉnh, ĐÃ GIẢI MÃ thực thể HTML.

    `html.unescape` chứ không lấy nguyên văn: Jinja bật autoescape nên dấu `&`
    nối tham số ra HTML thành `&amp;` — ĐÚNG HTML, và trình duyệt tự giải mã
    thực thể trong giá trị thuộc tính trước khi điều hướng. Một test đọc
    nguyên văn rồi đưa thẳng cho TestClient sẽ gửi đi `?tinh=…&amp;nv=0104`,
    tức tham số thật tên là `amp;nv` và `nv` RỖNG — nghĩa là test đó vẫn XANH
    dù liên kết có mang `nv` hay không, đúng cái nó sinh ra để bắt.
    """
    m = re.search(mau.replace("TINH", re.escape(ten_tinh)), html)
    assert m, f"không tìm thấy liên kết của {ten_tinh}"
    return unescape(m.group(1))


def _href_o_svg(html: str, ten_tinh: str) -> str:
    """href của thẻ <a> bọc ĐÚNG ô SVG của một tỉnh."""
    return _href(html, r'<a href="([^"]+)">\s*<g class="o" data-tinh="TINH"',
                 ten_tinh)


def _href_dong_bang(html: str, ten_tinh: str) -> str:
    """href của thẻ <a> trong dòng bảng xếp hạng của một tỉnh."""
    return _href(html, r'<td><a href="([^"]+)">TINH</a></td>', ten_tinh)


def test_bam_o_hay_dong_bang_GIU_NGUYEN_bo_loc_nguoi_phu_trach(conn, client, batch):
    # [Vòng soát toàn nhánh, mục 1] Bấm một tỉnh trên bản đồ phải mở danh sách
    # ĐÚNG phạm vi bản đồ đang vẽ: bản đồ lọc theo đồng nghiệp (`nv`) mà danh
    # sách rơi về "khách của tôi" là lỗi "chip Tất cả (1.710) bấm vào ra 216
    # khách", chỉ khác là nó bắc qua HAI màn.
    #
    # Giai đoạn 2: bản đồ và danh sách là hai TAB trên CÙNG một trạng thái lọc
    # (giao_dien/src/khach/loc.ts). Bấm ô / dòng bảng CHỈ đổi `tinh` + tab —
    # `nv`/`tat_ca` không có đường nào rơi mất. Kiểm cả hai tầng: (1) mã giao
    # diện — cả ô SVG lẫn dòng bảng đi qua đúng `moTinh`; (2) dữ liệu — cùng
    # `nv`, ô ghi 1 khách thì danh sách lọc tỉnh đó ra đúng 1 khách đó.
    #
    # HAI khách CÙNG MỘT TỈNH, khác người phụ trách — cố ý: hai tỉnh khác nhau
    # thì riêng `tinh` đã lọc ra một người và test xanh cả khi `nv` rơi mất.
    _ho_so_khach(conn, batch, "BD01", "Cua A", prefecture="東京都",
                 salesperson_code="0102")
    _ho_so_khach(conn, batch, "BD02", "Cua B", prefecture="東京都",
                 salesperson_code="0104")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    _mua(conn, batch, "BD02", HOM_NAY - timedelta(days=5))

    nguon = BAN_DO_TSX.read_text(encoding="utf-8")
    assert nguon.count("moTinh(o.ten)") == 3, "ô SVG (bấm + phím) và dòng bảng phải cùng đi qua moTinh"
    assert 'dat({ tab: "danh_sach", tinh: ten }, true)' in nguon

    assert _o(client, "tat_ca=1")["東京都"]["so_khach"] == 2
    o = _o(client, "nv=0104")
    assert o["東京都"]["so_khach"] == 1, "fixture hỏng: bản đồ không hề bị lọc theo nv"
    t = client.get("/api/khach-hang/ds?nv=0104&tinh=東京都").json()["trang"]
    assert [k["ten"] for k in t["khach"]] == ["Cua B"], \
        "ô ghi 1 khách nhưng danh sách cùng bộ lọc ra khác"


def test_cuoi_trang_hien_TONG_de_doi_chieu(conn, client, batch):
    # [Vòng soát toàn nhánh, mục 4] "47 ô + (không rõ tỉnh)" mời người đọc cộng
    # lại — phải cho họ chính con số đó để đối chiếu.
    _hai_tinh(conn, batch)
    _ho_so_khach(conn, batch, "BD03", "Khong ro tinh", prefecture=None)
    _mua(conn, batch, "BD03", HOM_NAY - timedelta(days=5))

    t = client.get("/api/ban-do").json()["t"]
    assert t["tong"]["so_khach"] == 3          # 2 khách trên lưới + 1 "(không rõ tỉnh)"
    assert t["khong_ro_tinh"] == 1
    assert {"doanh_thu", "can_goi"} <= set(t["tong"])
    nguon = BAN_DO_TSX.read_text(encoding="utf-8")
    assert "t.tong.so_khach" in nguon and "t.tong.doanh_thu" in nguon and "t.tong.can_goi" in nguon


def test_loc_nv_co_ca_ban_do_lan_bang_lan_dai_vung(conn, client, batch):
    # Một bộ lọc co bản đồ mà không co bảng là hai con số khác nhau cho cùng
    # một câu hỏi, trên cùng một màn hình.
    _ho_so_khach(conn, batch, "BD01", "Cua A", prefecture="東京都",
                 salesperson_code="0102")
    _ho_so_khach(conn, batch, "BD02", "Cua B", prefecture="大阪府",
                 salesperson_code="0104")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    _mua(conn, batch, "BD02", HOM_NAY - timedelta(days=5))
    t = client.get("/api/ban-do?nv=0102").json()["t"]
    o = {x["ten"]: x["gia_tri"] for x in t["o"]}
    # 大阪府 vẫn phải còn trên bản đồ (ô số 0) — `len(o) == 47` là khẳng định thật.
    assert o["東京都"] == 1 and o["大阪府"] == 0 and len(o) == 47
    bang = {x["ten"]: x["so_khach"] for x in t["bang"]}
    assert bang["東京都"] == 1 and bang["大阪府"] == 0 and len(bang) == 47
    vung = {v["vung"]: v["gia_tri"] for v in t["vung"]}
    assert vung["関東"] == 1 and vung["近畿"] == 0


def test_trang_ban_do_khong_qua_2_truy_van(conn, client, batch, monkeypatch):
    # Đo ENDPOINT (không chỉ hàm `ban_do`): route có thể lỡ thêm một lượt hỏi
    # ngoài hàm đó (vd danh sách người phụ trách). Bọc psycopg.Connection.execute
    # vì endpoint mở kết nối riêng. Ảnh chụp tắt trong test (conftest).
    _hai_tinh(conn, batch)
    import psycopg
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)

    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = client.get("/api/ban-do")
    assert r.status_code == 200
    # Khoảng xem (đợt B): +1 lượt `khoang_xem.pham_vi` ở tầng API; bản thân
    # BD.ban_do vẫn đúng 2 (test_ban_do_khong_qua_2_truy_van).
    assert dem["n"] <= 3, f"{dem['n']} lượt hỏi, trần là 3"


def test_chu_giai_bo_qua_bac_rong_nhung_luon_hien_bac_0(conn, client, batch):
    # [Bất biến task-3-brief §1] Luật "giá trị bằng nhau phải cùng bậc" khiến
    # một bậc GIỮA có thể trống. Bậc trống không có khoảng giá trị thật nào để
    # nói nên KHÔNG in; bậc 0 là màu riêng trên bản đồ nên LUÔN in.
    mot_khach = ["北海道", "沖縄県"]
    hai_khach = ["東京都", "大阪府", "愛知県", "福岡県", "宮城県"]
    for i, tinh in enumerate(mot_khach):
        ma = f"BDL{i:02d}"
        _ho_so_khach(conn, batch, ma, f"Quan {tinh} mot", prefecture=tinh)
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=5))
    for i, tinh in enumerate(hai_khach):
        for j in range(2):
            ma = f"BDK{i:02d}{j}"
            _ho_so_khach(conn, batch, ma, f"Quan {tinh} {j}", prefecture=tinh)
            _mua(conn, batch, ma, HOM_NAY - timedelta(days=5))

    t = ban_do(conn)
    bac_rong = [c["bac"] for c in t.chu_giai
                if c["bac"] != 0 and c["so_tinh"] == 0]
    assert bac_rong, "ca gieo phải tạo ra ít nhất một bậc giữa trống (fixture hỏng?)"
    assert any(c["bac"] == 0 for c in client.get("/api/ban-do").json()["t"]["chu_giai"])
    assert "t.chu_giai.filter(c => c.bac === 0 || c.so_tinh > 0)" in BAN_DO_TSX.read_text(encoding="utf-8"), \
        "chú giải phải bỏ bậc trống nhưng luôn giữ bậc 0"


