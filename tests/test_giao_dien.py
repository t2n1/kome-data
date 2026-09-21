"""Test của đợt 1 — nền giao diện.

Phần lớn test ở đây chỉ đọc file (kome.css, template, font) hoặc đọc HTML
trả về. Một số cần fixture `conn` để dựng app — chúng KHÔNG gieo dữ liệu, chỉ
cần schema có mặt. Test giao diện nào phải GIEO dữ liệu mới kiểm được thì nằm
ở tests/test_khach_hang.py, nơi có sẵn các hàm gieo.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from kome.web.app import create_app

CSS = Path("kome/web/static/kome.css")
TEMPLATES = Path("kome/web/templates")
FONTS = Path("kome/web/static/fonts")

TEN_FONT = [
    "IBMPlexSans-Regular.woff2",
    "IBMPlexSans-Medium.woff2",
    "IBMPlexSans-SemiBold.woff2",
    "IBMPlexSans-Bold.woff2",
    "IBMPlexMono-Regular.woff2",
    "IBMPlexMono-Medium.woff2",
    "IBMPlexMono-SemiBold.woff2",
]

# Mọi trang mở được mà không cần tham số. Trang hồ sơ khách và trang lỗi
# không nằm đây vì chúng cần dữ liệu hoặc một sự cố để hiện ra.
TRANG = ["/", "/khach-hang", "/bao-cao", "/can-xu-ly", "/kho-du-lieu"]


def test_css_duoc_phuc_vu(conn, test_db_url):
    """/static/kome.css phải trả về 200 và đúng kiểu nội dung.

    Chặn thảm hoạ: quên mount StaticFiles -> mọi trang mất sạch kiểu dáng
    nhưng vẫn trả 200, nên không test nào khác đỏ.
    """
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/static/kome.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    assert "--nen" in r.text


def test_moi_trang_deu_noi_toi_css(conn, test_db_url):
    """Chặn thảm hoạ: một trang quên include _chung.html -> trang đó trơ
    trụi trong khi bảy trang kia đẹp, và không ai để ý cho tới khi mở đúng
    trang đó."""
    client = TestClient(create_app(db_url=test_db_url))
    for duong_dan in TRANG:
        r = client.get(duong_dan)
        assert r.status_code == 200, duong_dan
        assert "/static/kome.css" in r.text, duong_dan


def test_khong_ma_mau_nao_ngoai_kome_css():
    """Mọi màu chỉ có MỘT nhà. Chặn thảm hoạ: ai đó gõ thẳng #fff vào một
    template -> trang đó trắng toát ở chế độ tối, trong khi test màu vẫn
    xanh vì nó chỉ soi kome.css."""
    for f in sorted(TEMPLATES.glob("*.html")):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"#[0-9A-Fa-f]{6}\b", text), f"{f.name} chứa mã màu"


def _bien_khai(khoi: str) -> set[str]:
    """Tên các biến được ĐỊNH NGHĨA trong một khối CSS.

    Chỉ khớp `--x:` (định nghĩa), không khớp `var(--x)` (sử dụng) — nên
    phần thân dưới file, vốn chỉ dùng biến, không lọt vào."""
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", khoi))


# Biến KHÔNG đổi theo chế độ sáng/tối: font là font, không có bản tối.
BIEN_KHONG_THEO_CHE_DO = {"--font-ui", "--font-so"}


def test_moi_bien_mau_deu_co_ban_toi():
    """Chặn thảm hoạ đã từng xảy ra: thêm một biến màu, quên bản tối ->
    chữ sẫm trên nền sẫm ở máy để giao diện tối. Trang vẫn trả 200 nên
    không test nào khác bắt được."""
    css = CSS.read_text(encoding="utf-8")
    moc = "@media (prefers-color-scheme: dark)"
    assert moc in css, "mất khối màu tối"
    sang, toi = css.split(moc, 1)
    thieu = _bien_khai(sang) - _bien_khai(toi) - BIEN_KHONG_THEO_CHE_DO
    assert not thieu, f"thiếu bản tối cho: {sorted(thieu)}"


def test_co_mau_hanh_dong_chinh_va_khong_con_mau_tim():
    """Bảng màu thiết kế dùng đỏ công ty #D62C27 cho hành động chính và
    trạng thái được chọn. Màu tím --chot-* của hệ cũ không còn chỗ đứng;
    để sót lại thì hai hệ màu cùng sống trong một file. Kiểm TỪNG khối
    riêng để bắt lỗi gõ sai một phía."""
    css = CSS.read_text(encoding="utf-8")
    moc = "@media (prefers-color-scheme: dark)"
    assert moc in css, "mất khối màu tối"
    sang, toi = css.split(moc, 1)
    # Kiểm khối sáng
    assert "--do:#D62C27" in sang.replace(" ", ""), "khối sáng: thiếu --do:#D62C27"
    # Kiểm khối tối
    assert "--do:#D62C27" in toi.replace(" ", ""), "khối tối: thiếu --do:#D62C27"
    # Không còn hệ cũ
    assert "--chot-" not in css


def test_moi_bien_dung_deu_duoc_dinh_nghia():
    """Mọi biến CSS var(--x) dùng ở bất cứ đâu (template + kome.css)
    phải có định nghĩa --x: trong kome.css. Chặn thảm hoạ: xoá một biến
    CSS nhưng quên sửa chỗ dùng nó -> var() không xác định, thuộc tính
    hỏng, SVG render sai màu hay mất nền. Không làm trang lỗi, không làm
    test nào đỏ — chỉ âm thầm vẽ sai, lộ ra khi người dùng mở đúng trang
    ở đúng chế độ."""
    css = CSS.read_text(encoding="utf-8")
    bien_dinh = _bien_khai(css)

    # Gom tập biến được DÙNG
    bien_dung = set()
    # Tìm trong CSS
    bien_dung.update(re.findall(r"var\(\s*(--[a-z0-9-]+)", css))
    # Tìm trong tất cả template
    for f in sorted(TEMPLATES.glob("*.html")):
        text = f.read_text(encoding="utf-8")
        bien_dung.update(re.findall(r"var\(\s*(--[a-z0-9-]+)", text))

    # Chắc chắn tất cả biến dùng đều được định nghĩa
    thieu = bien_dung - bien_dinh
    assert not thieu, f"Biến không được định nghĩa (quên sửa khi xoá?): {sorted(thieu)}"


def test_du_bay_file_font_va_khong_rong():
    """Chặn thảm hoạ: @font-face trỏ tới file không có -> trình duyệt im
    lặng rơi về font hệ thống, trang vẫn 200, không ai biết.

    Ngưỡng kích thước là ĐẠI DIỆN THÔ cho "font đầy đủ, không phải bản
    subset": bản subset `-Latin1` của IBM Plex chỉ ~17-22KB và KHÔNG có
    glyph tiếng Việt (đã đo thật bằng canvas.measureText — mọi ký tự có
    dấu rơi về font hệ thống, dấu tách rời khỏi chữ). Toàn bộ giao diện
    này là tiếng Việt nên đây là thảm hoạ nặng nhất có thể xảy ra với
    font, và trang vẫn trả 200 — không test nào khác bắt được.

    Ngưỡng đặt ở 35.000 byte, KHÔNG phải 60.000: bản đầy đủ đo thật của
    IBM Plex Mono chỉ ~49-50KB (Mono ít glyph phức tạp hơn Sans), thấp
    hơn 60.000. 35.000 nằm giữa hai nhóm với biên an toàn rộng cả hai
    phía (subset lớn nhất 22.260B, đầy đủ nhỏ nhất 49.248B).

    Giới hạn của chính test này: đây KHÔNG phải kiểm glyph thật. Kiểm
    glyph thật đòi giải nén woff2 (`fonttools` + `brotli`) — thêm một phụ
    thuộc mới, trái R1 (giảm tối đa số thứ có thể hỏng). Nếu một ngày IBM
    phát hành bản đầy đủ nhỏ hơn ngưỡng này, test sẽ báo động giả — người
    đọc cần biết đây là đại diện, không phải phép đo chính xác.

    `OFL.txt` (nguyên văn giấy phép SIL Open Font License) đi kèm ở đây
    KHÔNG vì thẩm mỹ mà vì đây là NGHĨA VỤ GIẤY PHÉP: OFL bắt buộc file
    giấy phép phải đi kèm khi phân phối lại font. Không có test nào canh
    nó thì ai dọn thư mục `fonts/` xoá nhầm sẽ không bị bắt — hậu quả là
    vi phạm giấy phép, nằm ngoài phạm vi kỹ thuật thuần tuý."""
    for ten in TEN_FONT:
        f = FONTS / ten
        assert f.exists(), f"thiếu {ten}"
        assert f.stat().st_size > 35_000, (
            f"{ten} nhỏ hơn 35.000 byte — có thể là bản subset -Latin1 "
            "thiếu glyph tiếng Việt, không phải bản đầy đủ"
        )
    ofl = FONTS / "OFL.txt"
    assert ofl.exists(), "thiếu OFL.txt — nghĩa vụ giấy phép SIL OFL của IBM Plex"
    assert ofl.stat().st_size > 0, "OFL.txt rỗng — không tính là kèm giấy phép"


def test_khong_goi_ra_ngoai_mang():
    """Chặn thảm hoạ: một link Google Fonts lọt vào -> máy trong công ty
    mất mạng là chữ Nhật rơi về font mặc định, và đó là lúc khó nhận ra
    nhất. Spec §5 đã chốt tự host."""
    ngoai = ("fonts.googleapis.com", "fonts.gstatic.com", "cdnjs", "unpkg.com", "jsdelivr")
    canh = [CSS] + sorted(TEMPLATES.glob("*.html"))
    for f in canh:
        text = f.read_text(encoding="utf-8")
        for x in ngoai:
            assert x not in text, f"{f.name} gọi ra ngoài mạng: {x}"


def test_sidebar_hien_du_nam_muc_va_ba_nhom(conn, test_db_url):
    """Chặn thảm hoạ: đổi khung điều hướng làm rơi mất một trang khỏi
    sidebar -> trang đó vẫn chạy nhưng không ai vào được nữa.

    Đợt 2a gộp /nap + /health + /phu-du-lieu thành một mục "Kho dữ liệu"
    (Task 4, db/… không liên quan) -> còn 5 mục thay vì 7, nhưng vẫn đúng ba
    nhóm."""
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/").text
    for duong_dan in ["/", "/bao-cao", "/khach-hang", "/can-xu-ly",
                      "/kho-du-lieu"]:
        assert f'href="{duong_dan}"' in html, f"sidebar thiếu {duong_dan}"
    for nhom in ["TỔNG QUAN", "KHÁCH HÀNG", "HỆ THỐNG"]:
        assert nhom in html, f"sidebar thiếu nhóm {nhom}"


def test_muc_dang_mo_duoc_danh_dau(conn, test_db_url):
    """Đánh dấu mục đang mở bằng CẢ class lẫn aria-current: người dùng
    trình đọc màn hình không thấy màu nền."""
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/bao-cao").text
    assert 'href="/bao-cao" class="dang-xem" aria-current="page"' in html


def test_ban_chi_doc_van_hien_muc_kho_du_lieu(conn, test_db_url, monkeypatch):
    """Đợt 2a (Task 4): mục Nạp/Sức khoẻ/Bảng phủ gộp thành một mục "Kho dữ
    liệu" duy nhất, KHÔNG còn bọc `{% if not chi_doc %}` ở tầng sidebar —
    màn /kho-du-lieu hiện được ở cả hai bản, chỉ tự ẩn khối nạp và khối hoàn
    tác BÊN TRONG chính nó. Bất biến "bản chỉ-đọc không mời bấm vào việc
    không làm được" giờ được canh ở tests/test_kho_du_lieu.py::
    test_ban_chi_doc_an_o_tha_file và ::test_ban_chi_doc_an_khoi_hoan_tac,
    không còn ở tầng sidebar này.

    Dùng KOME_CHI_DOC chứ KHÔNG dùng VERCEL: đặt VERCEL=1 làm
    `bao_mat.kiem_cau_hinh_phien` ném CauHinhSai ngay lúc dựng app nếu chưa
    có KOME_SESSION_SECRET, và nếu đặt khoá ký cho qua thì mọi trang lại
    chuyển hướng sang /dang-nhap — test sẽ đỏ vì hai lý do chẳng liên quan gì
    tới sidebar. `_chi_doc()` trong app.py chỉ sẵn đường này."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/").text
    assert 'href="/kho-du-lieu"' in html


# Bốn tên lớp badge trạng thái khách hàng, GHÉP Ở TẦNG PYTHON
# (kome/khach_hang.py) chứ không phải chuỗi tĩnh trong template -> grep trên
# *.html không bao giờ bắt được ai đang định nghĩa CSS đè lên chúng.
TEN_BADGE = ("ok", "canh", "loi", "nhat")


def test_ten_badge_khong_duoc_dung_lam_lop_tran_trong_css():
    """Chặn thảm hoạ đã XẢY RA THẬT: sidebar Task 4 đặt tên lớp `.canh`
    (đúng bản mô tả), nhưng `.canh` đã có nghĩa khác từ trước -- lớp badge
    "Cần gọi lại" ở dạng CÓ ĐỊNH TÍNH `.vien.canh` (kome.css, khối "Viên
    trạng thái"). `.vien.canh` chỉ khai background/border-color/color; mọi
    thuộc tính khác của `.canh` (sidebar: position:sticky, width:196px,
    height:100vh, display:flex...) áp thẳng lên badge, biến nó thành một
    khối 196px x 100vh dính trên đầu màn hình. 207 test vẫn xanh lúc đó vì
    không test nào soi việc MỘT TÊN LỚP bị TÁI SỬ DỤNG cho hai thứ khác
    nhau -- nó chỉ lộ ra khi có người mở đúng trang có đúng loại khách
    (`/can-xu-ly`, nhóm "Cần gọi lại").

    `ok`/`canh`/`loi`/`nhat` là bốn tên RẤT CHUNG (kome/khach_hang.py) --
    người viết CSS sau này rất dễ đặt lại một trong bốn tên đó cho một
    thành phần hoàn toàn khác, y hệt chuyện vừa xảy ra với `.canh`. Test
    này khẳng định bốn tên đó CHỈ được xuất hiện trong kome.css dưới dạng
    CÓ ĐỊNH TÍNH (`.vien.ok`, `.vien.canh`, `.vien.loi`, `.vien.nhat`) --
    tức luôn có một lớp khác đứng ngay trước, không đứng trần một mình.

    Khớp selector trần: một `.` đứng ở đầu selector (đầu file, sau khoảng
    trắng/xuống dòng, sau dấu phẩy, sau `{` đóng khối trước, hoặc sau `}`
    đóng khối liền trước — CSS nén kiểu `}.canh{` không có khoảng trắng)
    theo sau là đúng một trong bốn tên rồi hết từ (không phải tiền tố của
    tên dài hơn như `.loi-hop`).

    Quét CẢ kome.css LẪN mọi template (*.html): thảm hoạ `.canh` thật sự
    nằm trong một khối `<style>` của template (Task 4), không phải trong
    kome.css -- một test chỉ soi kome.css sẽ không bao giờ bắt được lần
    tái diễn tiếp theo, đúng như nó đã không bắt được lần đầu."""
    tran = re.compile(r'(?:^|[\s,{}])\.(' + "|".join(TEN_BADGE) + r')(?![\w-])')
    vi_pham = []
    for f in [CSS] + sorted(TEMPLATES.glob("*.html")):
        text = f.read_text(encoding="utf-8")
        for m in tran.finditer(text):
            vi_pham.append(f"{f.name}: .{m.group(1)}")
    assert not vi_pham, (
        f"lớp badge dùng TRẦN (không có định tính): {vi_pham} -- "
        "badge trạng thái sẽ ăn nguyên kiểu dáng của bất cứ thứ gì đang mượn "
        "tên này (xem docstring)"
    )


def test_moi_template_dung_nav_deu_dong_main():
    """`_nav.html` MỞ `<main class="noi-dung">` và KHÔNG đóng (xem chú
    thích Jinja đầu file) -- mỗi template include nó phải tự thêm `</main>`
    ở cuối. Ghi chú giải thích chuyện này nằm trong bản mô tả nhiệm vụ,
    tức NGOÀI repo -- người mở `_nav.html` sáu tháng nữa không có nó trong
    tay nếu chỉ đọc code. Không viết cứng số lượng file: tự tìm mọi
    template include `_nav.html`, để thêm trang mới cũng được canh.

    Tìm bằng REGEX, không khớp chuỗi y hệt `{% include "_nav.html" %}`:
    một template dùng `{%- include -%}` (cắt khoảng trắng) hoặc nháy đơn
    `'_nav.html'` sẽ bị chuỗi y hệt BỎ QUA LẶNG LẼ -- một test canh một
    bất biến giòn (chỉ đúng cho đúng một cách viết cú pháp Jinja) thì
    không canh gì cả."""
    mau_include = re.compile(r'\{%-?\s*include\s*["\']_nav\.html["\']')
    dung_nav = [
        f for f in sorted(TEMPLATES.glob("*.html"))
        if mau_include.search(f.read_text(encoding="utf-8"))
    ]
    assert dung_nav, "không tìm thấy template nào include _nav.html"
    for f in dung_nav:
        text = f.read_text(encoding="utf-8")
        assert text.count("</main>") == 1, (
            f"{f.name} include _nav.html (mở <main> không đóng) nhưng có "
            f"{text.count('</main>')} thẻ </main>, cần đúng 1"
        )


def test_moi_trang_that_co_dung_mot_the_viewport(conn, test_db_url):
    """Thiếu <meta name="viewport"> -> điện thoại dựng viewport ảo ~980px,
    quy tắc gập sidebar ở @media (max-width:720px) trong kome.css không bao
    giờ kích hoạt, dù CSS đúng 100%. Thẻ này đặt DUY NHẤT một chỗ trong
    _chung.html (một nhà, mọi trang include) — template không được tự khai
    thêm bản của riêng mình, kẻo có trang thành 2 thẻ (trình duyệt dùng thẻ
    ĐẦU, nhưng 2 thẻ là dấu hiệu code trùng lặp không ai dọn)."""
    client = TestClient(create_app(db_url=test_db_url))
    for duong_dan in TRANG:
        html = client.get(duong_dan).text
        so_luong = html.count('name="viewport"')
        assert so_luong == 1, f"{duong_dan} có {so_luong} thẻ viewport, cần đúng 1"


# Selector TRẦN bị cấm trong kome.css: những tên mà một template ĐÃ khai lại
# trong khối <style> của riêng nó. Thứ tự nguồn chỉ phân xử được các thuộc
# tính CẢ HAI cùng khai; thuộc tính chỉ có trong kome.css thì không có đối
# thủ và vẫn rò sang trang kia.
SELECTOR_CAM_TRAN = {
    ".mau": ("bao_cao.html khai .mau cho ba ô màu chú giải biểu đồ nhưng chỉ "
             "khai width/height/border-radius/display — border, line-height, "
             "text-align, font-weight của kome.css rò thẳng sang, thêm cho "
             "chúng một viền xám chưa từng có. Dùng '.chu-giai .mau'."),
    "button": ("mọi nút trong app (đăng nhập, tìm, đăng xuất, Xoá lô) đã có "
               "kiểu riêng theo lớp — một 'button{…}' trần đè lên tất cả. "
               "Dùng một lớp, ví dụ '.nut-nap'."),
}


def test_khong_co_selector_tran_de_ro_kieu_dang():
    """[IMPORTANT] Chặn thảm hoạ đã XẢY RA THẬT hai lần trong đợt 2a.

    (1) `.mau` trần trong kome.css rò `border`/`line-height`/`text-align`/
    `font-weight` sang ba ô màu chú giải của /bao-cao, thêm cho chúng một
    viền xám không ai yêu cầu. (2) `upload.html` cũ có `button{…}` trần; khi
    chép sang kome.css thì nó sẽ đè lên MỌI nút khác của app.

    Cả hai đều không làm test nào đỏ và không làm trang lỗi — chúng chỉ vẽ
    sai, ở một trang khác với trang người sửa đang mở."""
    css = CSS.read_text(encoding="utf-8")
    vi_pham = []
    for ten, vi_sao in SELECTOR_CAM_TRAN.items():
        # Selector đứng ĐẦU một selector: đầu dòng, hoặc ngay sau `}`/`,`.
        # `.chu-giai .mau{` và `.o-tim button{` KHÔNG khớp — chúng có một
        # lớp định tính đứng trước, đúng thứ ta muốn.
        mau = re.compile(r"(?m)(?:^|[},])\s*" + re.escape(ten) + r"\s*[{,]")
        if mau.search(css):
            vi_pham.append(f"{ten}: {vi_sao}")
    assert not vi_pham, "kome.css có selector trần:\n" + "\n".join(vi_pham)


def test_nut_nap_va_o_chon_file_co_kieu_dang():
    """[IMPORTANT] "Nạp" là nút hành động chính của màn DUY NHẤT có người
    dùng hằng ngày (13:30, ba file OBC). `upload.html` cũ tạo kiểu cho nó
    bằng `button{…}` + `input[type=file]{…}`; Task 4 xoá template đó mà không
    chép hai quy tắc sang kome.css, nên nút thành nút trần mặc định của
    trình duyệt — nút duy nhất trong app không có kiểu dáng, và không test
    nào đỏ vì trang vẫn trả 200."""
    nap = (TEMPLATES / "_nap.html").read_text(encoding="utf-8")
    css = CSS.read_text(encoding="utf-8")
    for lop, o in (("nut-nap", 'nút submit "Nạp"'), ("chon-file", "ô chọn file")):
        assert f'class="{lop}"' in nap, f"_nap.html: {o} chưa mang lớp .{lop}"
        assert f".{lop}{{" in css.replace(" ", ""), \
            f"kome.css chưa khai .{lop} — {o} sẽ trần trụi"


# ---- Trang danh sách khách: 4 khối + 3 bộ lọc (task 5 đợt 4a) ----------

def test_trang_danh_sach_co_du_bon_khoi_va_ba_bo_loc(conn, test_db_url):
    """[IMPORTANT] Bốn khối là bốn câu hỏi khác nhau; thiếu một khối thì
    không test nào khác đỏ, vì trang vẫn trả 200 và vẫn có danh sách."""
    c = TestClient(create_app(db_url=test_db_url))
    html = c.get("/khach-hang").text
    # Khối 1: danh sách làm việc — bốn nút
    for ten in ("Toàn bộ danh bạ", "Im lặng", "đang tụt", "Khách mới"):
        assert ten in html, f"thiếu nút nhóm việc: {ten}"
    # Ba khối phân tích
    assert "luoi-3" in html, "ba khối phân tích không nằm trong .luoi-3"
    for tieu_de in ("hạng doanh thu 12 tháng", "Tập trung ở đâu",
                    "Tải của từng nhân viên"):
        assert tieu_de in html, f"thiếu khối: {tieu_de}"
    # Ba bộ lọc: chip hạng, select người phụ trách, select tỉnh. Phải khớp
    # CHÍNH thẻ <select> — `name="nv"` khớp cả ô ẩn của form tìm kiếm, nên
    # xoá hẳn hai ô chọn mà test vẫn xanh.
    assert '<select name="nv"' in html and '<select name="tinh"' in html
    assert "hang=S" in html and "hang=D" in html


def test_nhan_hang_khong_bao_gio_tro_troi(conn, test_db_url):
    """[IMPORTANT] core.dim_customer.rank_code (得意先ランク của OBC, 10 nhóm
    không có tên ở đâu) cũng tồn tại. Gọi tắt chỉ số của ta là "hạng" thì sáu
    tháng nữa sẽ có người đối chiếu với OBC, thấy lệch, và không biết tin cái
    nào. Cả hai đều đúng — chúng trả lời hai câu khác nhau."""
    c = TestClient(create_app(db_url=test_db_url))
    html = c.get("/khach-hang").text.lower()
    assert "hạng doanh thu 12 tháng" in html
    # Ngoại lệ DUY NHẤT: tên nút nhóm việc "Hạng S·A đang tụt" — câu mô tả
    # ngay dưới nó đã viết đủ chữ "theo doanh thu 12 tháng".
    # Nhận CẢ HAI cách viết: đặc tả nói "hạng theo doanh thu 12 tháng", còn
    # tiêu đề khối trong bản mô tả là "Phân bố theo hạng doanh thu 12 tháng".
    # Cấm một trong hai là bắt người viết sau chọn giữa đặc tả và test.
    tro_troi = re.findall(r"hạng(?! (?:theo )?doanh thu 12 tháng)(?! s·a)", html)
    assert not tro_troi, \
        f"{len(tro_troi)} chỗ ghi 'hạng' trơ trọi — sẽ bị đối chiếu nhầm với 得意先ランク"
