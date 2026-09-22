"""Đợt 4c — bảng tra 47 tỉnh, view gộp theo tỉnh, và tầng Python dựng bản đồ."""
import re
from datetime import date, timedelta

import pandas as pd
import pytest
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
    assert dem["n"] <= 2, f"{dem['n']} lượt hỏi, trần là 2"


# ---------------------------------------------------------------------------
# Task 3 — trang /ban-do
# ---------------------------------------------------------------------------

def _o_svg(html: str) -> list[str]:
    """Nội dung từng ô của bản đồ, cắt theo <g class="o">…</g>.

    Cắt theo Ô chứ không quét cả TRANG: đoạn văn giải thích phía trên bản đồ
    có nhắc tên tỉnh và có cả con số, nên một khẳng định quét cả trang sẽ xanh
    kể cả khi trong SVG không còn chữ nào — đúng lỗi đã bắt ở đợt 4b.
    """
    return re.findall(r'<g class="o"[^>]*>(.*?)</g>', html, re.S)


def test_moi_o_co_con_so_doc_duoc_chu_khong_chi_co_mau(conn, client, batch):
    # Bất biến _chung.html:76-77: mã hoá bằng màu phải kèm thứ đọc được.
    _hai_tinh(conn, batch)
    html = client.get("/ban-do").text
    o = _o_svg(html)
    assert len(o) == 47
    for noi_dung in o:
        assert re.search(r">\s*\d[\d.,]*\s*<", noi_dung), noi_dung


def test_bam_o_dan_toi_danh_ba_da_loc_dung_tinh(conn, client, batch):
    # Tên tỉnh là tiếng Nhật -> href phải được mã hoá URL. Quên `|urlencode`
    # thì liên kết vẫn trông đúng trên trang mà bấm vào ra danh sách rỗng.
    _hai_tinh(conn, batch)
    html = client.get("/ban-do").text
    assert "/khach-hang?tinh=%E6%9D%B1%E4%BA%AC%E9%83%BD" in html


def test_loc_nv_co_ca_ban_do_lan_bang_lan_dai_vung(conn, client, batch):
    # Một bộ lọc co bản đồ mà không co bảng là hai con số khác nhau cho cùng
    # một câu hỏi, trên cùng một màn hình.
    _ho_so_khach(conn, batch, "BD01", "Cua A", prefecture="東京都",
                 salesperson_code="0102")
    _ho_so_khach(conn, batch, "BD02", "Cua B", prefecture="大阪府",
                 salesperson_code="0104")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    _mua(conn, batch, "BD02", HOM_NAY - timedelta(days=5))
    html = client.get("/ban-do?nv=0102").text
    o = {t: n for t, n in re.findall(
        r'<g class="o" data-tinh="([^"]+)"[^>]*>.*?class="so">([\d.,]+)<', html, re.S)}
    assert o["東京都"] == "1" and o["大阪府"] == "0"
    # 大阪府 vẫn phải còn trên bản đồ (ô số 0), không được biến mất khi lọc —
    # `len(o) == 47` là khẳng định thật, còn `"大阪府" in html` thì không: tên
    # tỉnh nằm sẵn trong bảng 47 dòng nên chuỗi đó luôn có mặt.
    assert len(o) == 47
    # Dải vùng cũng phải co: 関東 còn 1 khách, 近畿 còn 0.
    vung = dict(re.findall(r'<li class="vung" data-vung="([^"]+)">[^<]*<b>(\d+)</b>', html))
    assert vung["関東"] == "1" and vung["近畿"] == "0"


def test_trang_ban_do_khong_qua_2_truy_van(conn, client, batch, monkeypatch):
    # Cùng cơ chế đếm với test của tầng Python, nhưng đo TRANG: route có thể
    # lỡ thêm một lượt hỏi ngoài hàm `ban_do` (vd danh sách người phụ trách).
    # Đúng cơ chế tests/test_san_pham.py dùng cho /kho-hang (bọc conn.execute
    # qua monkeypatch), không dựng cơ chế thứ ba. Đo trên MỘT kết nối cụ thể:
    # route mở kết nối riêng của chính nó qua open_app_conn(), nên phải bọc
    # NGAY TRƯỚC lượt gọi — không bọc được `conn` của fixture (route không hề
    # dùng nó) mà phải theo dõi tại tầng psycopg qua kome.db.connect có sẵn
    # kết nối test, tức bọc lớp Connection.execute của chính module psycopg.
    _hai_tinh(conn, batch)
    import psycopg
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)

    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    r = client.get("/ban-do")
    assert r.status_code == 200
    assert dem["n"] <= 2, f"{dem['n']} lượt hỏi, trần là 2"


def test_chu_giai_bo_qua_bac_rong_nhung_luon_hien_bac_0(conn, client, batch):
    # [Bất biến task-3-brief §1] Luật "giá trị bằng nhau phải cùng bậc" khiến
    # một bậc GIỮA có thể trống (vd [1, 1, 2] cho bậc [1, 1, 3] -> bậc 2
    # trống). Gieo đúng hình đó: 2 tỉnh 1-khách, 5 tỉnh 2-khách — dồn cụm
    # khiến bậc 3/4/5 trống hẳn (xem test_ban_do.py::
    # test_gia_tri_bang_nhau_cung_mot_bac_khong_chong_khoang_chu_giai của
    # Task 2, cùng dữ liệu). Bậc 0 (40 tỉnh còn lại, 0 khách) PHẢI luôn hiện
    # vì nó là màu riêng trên bản đồ — người đọc cần biết màu đó nghĩa là gì.
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

    html = client.get("/ban-do").text
    for b in bac_rong:
        assert f'data-bac="{b}"' not in html, \
            f"bậc {b} trống (so_tinh=0) nhưng vẫn bị in ra chú giải"
    # Bậc 0 luôn hiện, kể cả khi không có tỉnh nào giá trị 0 (không phải ca ở
    # đây — 40/47 tỉnh còn lại đều 0 khách — nhưng bất biến vẫn phải đúng ở
    # đây: cứ có mặt trong chu_giai là phải in ra).
    assert 'data-bac="0"' in html
