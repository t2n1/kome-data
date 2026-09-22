"""Cổng đăng nhập và chế độ chỉ-đọc — điều kiện để đưa trang lên Internet.

Trang này hiển thị doanh thu, lãi gộp, giá vốn từng mặt hàng và danh sách
2.080 khách hàng. Mọi test ở đây bảo vệ đúng một câu: **không ai xem được
thứ đó nếu không đăng nhập**, và **không ai nạp/xoá dữ liệu qua bản công
khai**.
"""
import re

import pytest
from fastapi.testclient import TestClient

from kome import khach_hang as KH
from kome.web import bao_mat
from kome.web.app import create_app

MK = "mat-khau-cua-an-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"


@pytest.fixture
def khach(monkeypatch, test_db_url, conn):
    """Trình duyệt KHÔNG tự đi theo chuyển hướng — phải thấy tận mắt mã 303.

    `bi_mat=None` => KHÔNG có cổng đăng nhập (máy trong công ty để trống
    KOME_SESSION_SECRET). Đó cũng là mặc định của mọi test khác trong repo,
    xem fixture autouse `_khong_cong_dang_nhap` ở conftest.py.
    """
    from kome.web import nguoi_dung as ND

    def _tao(bi_mat: str | None = BI_MAT, vercel: bool = False,
             tai_khoan: bool = True, kho_du_lieu: bool = True,
             sale: str | None = None):
        monkeypatch.delenv("KOME_CHI_DOC", raising=False)
        if bi_mat is None:
            monkeypatch.delenv("KOME_SESSION_SECRET", raising=False)
        else:
            monkeypatch.setenv("KOME_SESSION_SECRET", bi_mat)
        if vercel:
            monkeypatch.setenv("VERCEL", "1")
        else:
            monkeypatch.delenv("VERCEL", raising=False)
        if tai_khoan:
            ND.tao(conn, "an", MK, salesperson_code=sale, kho_du_lieu=kho_du_lieu)
            conn.commit()
        # vercel=True => base_url https: bản công khai LUÔN chạy HTTPS, và
        # cookie phiên ở đó mang cờ Secure nên trình duyệt không gửi lại qua
        # HTTP. Giả lập bằng http:// sẽ dựng nên một thế giới không có thật,
        # nơi đăng nhập "thành công" rồi trang sau lại đòi đăng nhập.
        return TestClient(create_app(db_url=test_db_url), follow_redirects=False,
                          base_url="https://testserver" if vercel else "http://testserver")
    return _tao


def _vao(c, ten: str = "an", mat_khau: str = MK):
    """Đăng nhập, trả về phản hồi của POST /dang-nhap."""
    return c.post("/dang-nhap", data={"ten": ten, "mat_khau": mat_khau})


# ---- Vé theo từng người (đợt 3) ---------------------------------------

def test_ve_mang_dung_id_nguoi_dang_nhap():
    assert bao_mat.doc_ve(bao_mat.tao_ve_cho(7, BI_MAT), BI_MAT) == 7


def test_doi_id_trong_ve_khong_hoa_than_duoc_thanh_nguoi_khac():
    """[CRITICAL] Đây là chỗ dễ sai nhất của cả đợt. Nếu chữ ký chỉ phủ phần
    HẠN mà không phủ ID, thì sửa một con số trong cookie là thành người khác —
    ví dụ thành đúng người có quyền vào Kho dữ liệu, nơi có nút xoá cả tháng
    doanh thu. Chữ ký PHẢI phủ cả hai."""
    ve = bao_mat.tao_ve_cho(7, BI_MAT)
    ma, het, chu_ky = ve.split(".")
    assert bao_mat.doc_ve(f"1.{het}.{chu_ky}", BI_MAT) is None
    assert bao_mat.doc_ve(f"999.{het}.{chu_ky}", BI_MAT) is None


def test_ve_het_han_thi_vo_hieu_du_chu_ky_dung():
    ve = bao_mat.tao_ve_cho(7, BI_MAT, bay_gio=1_000_000)
    assert bao_mat.doc_ve(ve, BI_MAT, bay_gio=1_000_000 + bao_mat.HAN_PHIEN_GIAY - 1) == 7
    assert bao_mat.doc_ve(ve, BI_MAT, bay_gio=1_000_000 + bao_mat.HAN_PHIEN_GIAY + 1) is None


def test_doi_bi_mat_phien_huy_moi_ve_dang_luu_hanh():
    """[IMPORTANT] Không có kho phiên ở máy chủ, nên đổi KOME_SESSION_SECRET
    là cách DUY NHẤT đăng xuất tất cả mọi người cùng lúc khi nghi rò rỉ."""
    assert bao_mat.doc_ve(bao_mat.tao_ve_cho(7, BI_MAT), BI_MAT + "-moi") is None


def test_ve_meo_mo_bi_tu_choi():
    ma, het, chu_ky = bao_mat.tao_ve_cho(7, BI_MAT).split(".")
    assert bao_mat.doc_ve(None, BI_MAT) is None
    assert bao_mat.doc_ve("", BI_MAT) is None
    assert bao_mat.doc_ve("khong-co-dau-cham", BI_MAT) is None
    assert bao_mat.doc_ve(f"{het}.{chu_ky}", BI_MAT) is None          # thiếu id
    assert bao_mat.doc_ve(f"7.{het}.{chu_ky}.thua", BI_MAT) is None   # thừa đoạn
    assert bao_mat.doc_ve(f"7.khong-phai-so.{chu_ky}", BI_MAT) is None
    assert bao_mat.doc_ve(f"khong-phai-so.{het}.{chu_ky}", BI_MAT) is None
    # Cookie là dữ liệu trình duyệt gửi lên, ai cũng nhét được ký tự ngoài
    # ASCII vào — compare_digest so hai str như vậy ném TypeError thay vì
    # trả về khác nhau, nên phải so trên bytes. Không có dòng này thì một
    # cookie rác không đưa người dùng về trang đăng nhập mà làm sập 500,
    # lặp lại ở mọi lượt gọi vì cookie hỏng vẫn còn trong trình duyệt.
    assert bao_mat.doc_ve(f"7.{het}.chu-ky-có-dấu", BI_MAT) is None


def test_hai_nguoi_khac_nhau_khong_bao_gio_dung_chung_ve():
    a = bao_mat.tao_ve_cho(7, BI_MAT, bay_gio=1_000_000)
    b = bao_mat.tao_ve_cho(8, BI_MAT, bay_gio=1_000_000)
    assert a != b


def test_cong_khai_ma_thieu_bi_mat_phien_thi_app_chet_ngay():
    """[CRITICAL] Bỏ mật khẩu chung là bỏ luôn chốt an toàn cũ. Chốt mới phải
    cùng hình dạng: công khai mà không có khoá ký thì KHÔNG dựng app."""
    with pytest.raises(bao_mat.CauHinhSai, match="KOME_SESSION_SECRET"):
        bao_mat.kiem_cau_hinh_phien(None, cong_khai=True)
    with pytest.raises(bao_mat.CauHinhSai, match="ký tự"):
        bao_mat.kiem_cau_hinh_phien("ngan", cong_khai=True)
    # Máy trong công ty: không có khoá cũng không sao, không có cổng đăng nhập.
    bao_mat.kiem_cau_hinh_phien(None, cong_khai=False)


def test_bi_mat_phien_doc_tu_bien_moi_truong(monkeypatch):
    monkeypatch.delenv("KOME_SESSION_SECRET", raising=False)
    assert bao_mat.bi_mat_phien() is None
    monkeypatch.setenv("KOME_SESSION_SECRET", "   ")
    assert bao_mat.bi_mat_phien() is None      # khoảng trắng = chưa đặt
    monkeypatch.setenv("KOME_SESSION_SECRET", f"  {BI_MAT}  ")
    assert bao_mat.bi_mat_phien() == BI_MAT


# ---- Chuyển hướng sau khi đăng nhập ------------------------------------

@pytest.mark.parametrize("tiep,mong", [
    ("/khach-hang", "/khach-hang"),
    ("https://site-gia.example", "/"),   # địa chỉ tuyệt đối
    ("//site-gia.example", "/"),         # cũng là tuyệt đối
    (None, "/"),
])
def test_khong_lam_ban_dap_chuyen_huong(tiep, mong):
    """Trang đăng nhập của công ty không được đẩy người dùng sang site lạ.

    Đích mặc định là "/" chứ KHÔNG còn là /kho-du-lieu (đợt 3): không phải ai
    cũng vào được màn đó nữa."""
    assert bao_mat.duong_dan_an_toan(tiep) == mong


# ---- Cấu hình phải an toàn ngay từ lúc khởi động ------------------------

def test_tren_vercel_ma_khong_co_khoa_ky_thi_app_chet_ngay(khach):
    """[CRITICAL] Không có cổng + công khai = số liệu công ty mở cho cả
    Internet. Phải nổ lúc dựng app, nơi người triển khai đọc được nhật ký."""
    with pytest.raises(bao_mat.CauHinhSai, match="KOME_SESSION_SECRET"):
        khach(bi_mat=None, vercel=True)


def test_khoa_ky_qua_ngan_bi_tu_choi(khach):
    with pytest.raises(bao_mat.CauHinhSai, match="ký tự"):
        khach(bi_mat="ngan")


def test_chay_o_may_ca_nhan_khong_bat_buoc_dang_nhap(khach):
    """Máy trong công ty chạy ở 127.0.0.1 — bắt đăng nhập ở đó chỉ làm chậm
    công việc hằng ngày mà không chặn được ai. Để TRỐNG KOME_SESSION_SECRET
    là không có cổng, y như để trống KOME_MAT_KHAU trước đây.

    ĐÁNH ĐỔI PHẢI BIẾT: không có cổng thì cũng KHÔNG CÓ phân quyền — ai mở
    được trang cũng bấm được nút Hoàn tác. Xem docs/runbook.md."""
    r = khach(bi_mat=None, tai_khoan=False).get("/kho-du-lieu")
    assert r.status_code == 200


# ---- Cổng chặn trên mọi trang ------------------------------------------

@pytest.mark.parametrize("duong_dan", ["/", "/kho-du-lieu", "/khach-hang"])
def test_chua_dang_nhap_thi_moi_trang_deu_bi_chan(khach, duong_dan):
    r = khach().get(duong_dan)
    assert r.status_code == 303
    assert r.headers["location"] == "/dang-nhap"
    assert "¥" not in r.text and "得意先" not in r.text


def test_dang_nhap_dung_thi_xem_duoc_va_sai_thi_khong(khach):
    c = khach()
    r = _vao(c, mat_khau="doan-bua-mot-cai")
    assert r.status_code == 401
    assert bao_mat.TEN_COOKIE not in c.cookies

    r = _vao(c, ten="khong-co-nguoi-nay")
    assert r.status_code == 401
    assert bao_mat.TEN_COOKIE not in c.cookies

    r = _vao(c)
    assert r.status_code == 303
    assert c.get("/kho-du-lieu").status_code == 200


def test_dang_nhap_xong_ve_trang_chu_chu_khong_phai_kho_du_lieu(khach):
    """[IMPORTANT] Không phải ai cũng vào được Kho dữ liệu (đợt 3). Đẩy mọi
    người vào đó sau khi đăng nhập nghĩa là một sale vừa gõ đúng mật khẩu
    xong thấy ngay một trang 403 — lời chào tệ nhất có thể."""
    c = khach(kho_du_lieu=False)
    assert _vao(c).headers["location"] == "/"


def test_dang_nhap_xong_quay_lai_dung_trang_dinh_xem(khach):
    c = khach()
    c.get("/khach-hang")                        # bị đẩy về /dang-nhap
    assert _vao(c).headers["location"] == "/khach-hang"


def test_doi_mat_khau_mot_nguoi_khong_lam_nguoi_khac_bi_dang_xuat(khach, conn):
    """[CRITICAL] Đây ĐÚNG LÀ cái lỗi của cơ chế cũ mà đợt 3 sinh ra để sửa:
    khoá ký suy từ chính mật khẩu chung, nên đổi mật khẩu là cả công ty bị
    đăng xuất. Giờ khoá ký là của hệ thống, tách hẳn khỏi mật khẩu của ai."""
    from kome.web import nguoi_dung as ND
    c = khach()
    ND.tao(conn, "binh", "mat-khau-cua-binh-2026")
    conn.commit()
    _vao(c)
    assert c.get("/").status_code == 200

    ND.doi_mat_khau(conn, "binh", "mat-khau-moi-cua-binh")
    conn.commit()
    assert c.get("/").status_code == 200, "đổi mật khẩu người khác làm mình văng ra"


def test_xoa_tai_khoan_thi_ve_con_han_cung_het_vao_duoc(khach, conn):
    """[IMPORTANT] Người nghỉ việc phải bị chặn NGAY, không phải chờ 12 giờ
    cho vé cũ hết hạn. Vé không trạng thái nên chữ ký vẫn đúng — thứ chặn họ
    là việc middleware tra CSDL mỗi lượt và không thấy tài khoản nữa."""
    c = khach()
    _vao(c)
    assert c.get("/").status_code == 200
    conn.execute("DELETE FROM app.nguoi_dung WHERE ten_dang_nhap = 'an'")
    conn.commit()
    r = c.get("/")
    assert r.status_code == 303 and r.headers["location"] == "/dang-nhap"


def test_doi_khoa_ky_thi_dang_xuat_tat_ca(khach, monkeypatch, test_db_url):
    """[IMPORTANT] Nghi rò rỉ thì phải có một cái công tắc đăng xuất TẤT CẢ."""
    c = khach()
    _vao(c)
    assert c.get("/").status_code == 200
    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT + "-doi-roi")
    c2 = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
    c2.cookies.update(c.cookies)          # cùng cái vé, app đã đổi khoá ký
    assert c2.get("/").status_code == 303


def test_cookie_phien_khong_doc_duoc_bang_javascript(khach):
    dat = _vao(khach()).headers["set-cookie"]
    assert "httponly" in dat.lower()
    assert "samesite=lax" in dat.lower()


def test_tren_hang_tang_cong_khai_cookie_luon_co_co_secure(khach):
    """[IMPORTANT] Không có cờ Secure thì trình duyệt chịu gửi vé đăng nhập
    qua HTTP thường, nơi ai chung mạng Wi-Fi cũng đọc được."""
    assert "secure" in _vao(khach(vercel=True)).headers["set-cookie"].lower()


def test_o_may_ca_nhan_khong_gan_secure(khach):
    assert "secure" not in _vao(khach()).headers["set-cookie"].lower()


def test_thoat_thi_het_xem_duoc(khach):
    c = khach()
    _vao(c)
    assert c.get("/kho-du-lieu").status_code == 200
    c.post("/dang-xuat")
    assert c.get("/kho-du-lieu").status_code == 303


def test_mat_khau_khong_bao_gio_hien_tren_trang(khach):
    """Kể cả trang đăng nhập sai — người đứng sau lưng cũng đọc được màn hình."""
    c = khach()
    for r in (c.get("/dang-nhap"), _vao(c, mat_khau="sai")):
        assert MK not in r.text


def test_static_khong_bi_chan_boi_cong_dang_nhap(khach):
    """[CRITICAL] Task chuyển CSS/font ra /static (nhánh giao diện) khiến
    /dang-nhap PHỤ THUỘC vào một tài nguyên mà chính cổng đăng nhập chặn.

    Trước nhánh giao diện, CSS nằm inline trong _chung.html nên trang đăng
    nhập tự mang theo kiểu dáng. Từ khi CSS/font chuyển ra kome/web/static/,
    middleware `chan_cua` (chỉ miễn trừ đúng path "/dang-nhap") đá
    GET /static/kome.css và mọi file font về 303 /dang-nhap — trên bản
    Vercel (nơi KOME_SESSION_SECRET LUÔN bắt buộc), màn hình ĐẦU TIÊN người
    dùng thấy là một trang trơ trụi, không CSS không font.

    Bộ test cũ không bắt được vì hầu hết chạy với khach(bi_mat=None) — tức
    không có middleware nào cả. Test này phải dựng app CÓ cổng đăng nhập."""
    c = khach()
    r = c.get("/static/kome.css")
    assert r.status_code == 200, "CSS bị cổng đăng nhập chặn — /dang-nhap sẽ trơ trụi"
    assert "text/css" in r.headers["content-type"]

    r = c.get("/static/fonts/IBMPlexSans-Regular.woff2")
    assert r.status_code == 200, "font bị cổng đăng nhập chặn — /dang-nhap mất chữ Việt"

    # Cổng vẫn phải đóng với TRANG THẬT — miễn trừ /static không được nới
    # rộng ra thành miễn trừ mọi thứ.
    r = c.get("/")
    assert r.status_code == 303
    assert r.headers["location"] == "/dang-nhap"


# ---- Hai kết nối, hai vai trò CSDL --------------------------------------

def test_db_url_truyen_tay_thang_bien_moi_truong(monkeypatch, test_db_url, conn):
    """[CRITICAL] `create_app(db_url=…)` phải kéo theo CẢ kết nối app.

    Nếu `db_url_app` đi lấy thẳng DATABASE_URL_APP từ môi trường, test sẽ chạy
    trên CSDL thử nghiệm nhưng ĐỌC `app.nguoi_dung` của CSDL THẬT — và hỏng
    kiểu đó thì không có gì đỏ, chỉ có một bộ test nói dối.

    Cách canh: trỏ DATABASE_URL_APP vào một máy chủ không tồn tại. Luật còn
    đúng thì trang đọc vẫn mở bình thường; luật bị phá thì route đi tìm máy
    chủ ma, ngoại lệ rơi vào `_loi` và trả 500.
    """
    monkeypatch.setenv("DATABASE_URL_APP", "postgresql://khong-ton-tai/khong-co")
    c = TestClient(create_app(db_url=test_db_url))
    assert c.get("/khach-hang").status_code == 200


def test_trang_chi_doc_khong_duoc_dung_ket_noi_nap_du_lieu():
    """[CRITICAL] Chỉ ba route THẬT SỰ ghi/xoá được dùng `open_conn`
    (DATABASE_URL, vai trò kome_ingest_user — ghi được vào `core`). Mọi route
    còn lại phải đi `open_app_conn` (kome_app_user, KHÔNG ghi được vào `core`).

    Không có test này thì regression im lặng tuyệt đối: trong test hai kết nối
    luôn trỏ cùng một CSDL, nên một route đọc lỡ dùng `open_conn` vẫn xanh hết
    — cho tới đúng ngày DATABASE_URL_APP được đặt thật ở máy chủ, lúc đó trang
    đó âm thầm chạy bằng vai trò ghi được vào `core`, tức phá Luật số một.

    Duyệt MỌI hàm có decorator trong `create_app` chứ không liệt kê cứng tên
    năm route đọc: route thêm về sau phải tự động bị canh, đúng tinh thần
    "quên gắn cho route mới thì có thứ báo" của chính middleware.

    Soi mã nguồn bằng ast, cùng kiểu với
    test_trang_chi_doc_khong_phu_thuoc_pandas ở trên.
    """
    import ast
    import inspect

    import kome.web.app as A

    DUOC_GHI = {"upload", "kho_du_lieu", "undo"}

    tao = next(n for n in ast.parse(inspect.getsource(A)).body
               if isinstance(n, ast.FunctionDef) and n.name == "create_app")
    ten_route, vi_pham = set(), []
    for n in ast.walk(tao):
        # `decorator_list` là thứ phân biệt route/middleware với mấy hàm phụ
        # trong create_app (_ve, _cam, _du_lieu_kho — chúng nhận conn sẵn).
        if not isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) or not n.decorator_list:
            continue
        ten_route.add(n.name)
        if n.name in DUOC_GHI:
            continue
        if any(isinstance(g, ast.Call) and isinstance(g.func, ast.Name)
               and g.func.id == "open_conn" for g in ast.walk(n)):
            vi_pham.append(n.name)
    # Đổi tên một route ghi (hoặc đổi cách khai báo route) làm vòng duyệt trên
    # rỗng đi mà test vẫn xanh — khẳng định này bắt chính nó mất hiệu lực.
    assert DUOC_GHI <= ten_route, \
        f"không thấy đủ ba route ghi dữ liệu — test mất hiệu lực: {sorted(ten_route)}"
    assert not vi_pham, \
        f"route chỉ đọc dùng open_conn (vai trò ghi được vào core): {vi_pham}"


# ---- Chế độ chỉ-đọc ----------------------------------------------------

def test_tren_vercel_khong_nap_va_khong_hoan_tac_duoc(khach):
    """[CRITICAL] Vercel chặn mỗi yêu cầu ở 4,5 MB còn file bán hàng nặng
    ~100 MB, và ổ đĩa ở đó là tạm nên lớp `raw` không tồn tại. Để nút nạp
    sống trên bản công khai là mời người ta nạp nửa chừng rồi hỏng."""
    c = khach(vercel=True)
    _vao(c)

    r = c.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", b"x")})
    assert r.status_code == 403
    assert "chỉ để xem" in r.text

    assert c.post("/undo/1").status_code == 403

    # "/" giờ là trang Tổng quan — chỉ đọc, nên bản công khai xem được bình
    # thường.
    assert c.get("/").status_code == 200
    # /nap giờ LUÔN 301 sang /kho-du-lieu#nap (Task 4), kể cả ở bản chỉ-đọc:
    # màn đích tự ẩn khối nạp thay vì trả 403 cho một dấu trang cũ. Chặn
    # thật sự nằm ở POST /upload phía trên, không phải ở GET /nap.
    r = c.get("/nap", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/kho-du-lieu#nap"
    assert c.get("/kho-du-lieu").status_code == 200


def test_ban_chi_doc_an_han_muc_nap_du_lieu(khach):
    """Một liên kết luôn dẫn tới trang từ chối thì tệ hơn là không có.

    Đợt 2a (Task 4): /health chỉ 301 sang /kho-du-lieu, và mục nạp riêng
    trong sidebar biến mất — thay bằng một mục "Kho dữ liệu" duy nhất, còn
    khối nạp bên TRONG màn đó tự ẩn ở bản chỉ-đọc (id="nap")."""
    c = khach(vercel=True)
    _vao(c)
    t = c.get("/kho-du-lieu").text
    assert "Nạp từ OBC" not in t and 'href="/nap"' not in t
    assert 'id="nap"' not in t
    assert "在庫一覧" in t and 'href="/khach-hang"' in t


def test_ban_chi_doc_khong_bao_dong_sao_luu_gia(khach):
    """[IMPORTANT] Máy chủ công khai không nhìn thấy thư mục sao lưu nên luôn
    kết luận "chưa sao lưu". Một dải đỏ vĩnh viễn dạy người đọc bỏ qua dải
    đỏ — đúng thứ hệ thống này cần họ tin."""
    c = khach(vercel=True)
    _vao(c)
    # /health chỉ 301 sang /kho-du-lieu (Task 4) — khối sức khoẻ giờ nằm ở đó.
    t = c.get("/kho-du-lieu").text
    assert "Chưa sao lưu" not in t
    assert "máy trong công ty" in t


def test_ban_o_may_ca_nhan_van_nap_duoc(khach):
    """/nap giờ LUÔN 301 sang /kho-du-lieu#nap (Task 4) — theo tới đích để
    xác nhận khối nạp vẫn còn, còn hiện."""
    c = khach(bi_mat=None, tai_khoan=False)
    r = c.get("/nap", follow_redirects=False)
    assert r.status_code == 301
    assert r.headers["location"] == "/kho-du-lieu#nap"
    t = c.get("/kho-du-lieu").text
    assert 'id="nap"' in t and "Nạp dữ liệu OBC" in t


def test_trang_chi_doc_khong_phu_thuoc_pandas():
    """[IMPORTANT] requirements.txt của Vercel cố ý KHÔNG có pandas và
    python-calamine (~120 MB, chỉ dùng để ĐỌC file Excel — việc bản chỉ-đọc
    không bao giờ làm). Nếu ai đó đưa `from kome.pipeline import …` lên đầu
    app.py, trang trên Vercel sẽ chết ngay khi khởi động vì thiếu thư viện,
    còn ở máy mình thì vẫn chạy ngon lành — nên lỗi chỉ lộ ra sau khi đã
    triển khai."""
    import ast
    import inspect

    import kome.web.app as A

    # Đọc bằng ast chứ không tìm chuỗi: chính ghi chú trong file cũng nhắc tên
    # kome.pipeline, và một test bắt cả ghi chú thì đỏ vì lý do vô nghĩa.
    cay = ast.parse(inspect.getsource(A))
    muc = set()
    for n in cay.body:                       # CHỈ mức ngoài cùng — nhập bên
        if isinstance(n, ast.Import):        # trong thân hàm thì không sao
            muc |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            muc.add(n.module or "")
    assert not any(m.startswith(("kome.pipeline", "pandas", "calamine")) for m in muc), \
        f"app.py nhập ở mức ngoài cùng: {sorted(muc)}"


# ---- Quyền vào màn Kho dữ liệu (đợt 3) ---------------------------------

def test_khong_co_quyen_thi_moi_duong_vao_kho_du_lieu_deu_403(khach):
    """[CRITICAL] Màn Kho dữ liệu là màn có nút xoá. Đợt 2a đã phát hiện bấm
    nhầm lô đối soát sẽ xoá CẢ MỘT THÁNG doanh thu — trước đợt 3, bất kỳ ai
    biết mật khẩu chung đều bấm được nút đó.

    Chặn cả POST: ẩn cái nút đi mà vẫn nhận POST thì người gõ thẳng địa chỉ
    (hoặc một trang lạ tự gửi form) vẫn xoá được dữ liệu."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    r = c.get("/kho-du-lieu")
    assert r.status_code == 403
    assert "在庫一覧" not in r.text, "trang 403 vẫn lộ nội dung màn Kho dữ liệu"
    assert c.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", b"x")}).status_code == 403
    assert c.post("/undo/1").status_code == 403


def test_ba_dia_chi_cu_cung_bi_chan(khach):
    """/nap, /health, /phu-du-lieu chỉ 301 sang /kho-du-lieu, nhưng để hở
    chúng thì người không có quyền vẫn dò được cấu trúc màn bị cấm."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    for d in ("/nap", "/health", "/phu-du-lieu"):
        assert c.get(d).status_code == 403, d


def test_trang_403_noi_ro_vi_sao_chu_khong_chuyen_huong_im_lang(khach):
    """Người gõ thẳng địa chỉ cần biết vì sao mình không vào được, không phải
    tự hỏi trang có hỏng không."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    t = c.get("/kho-du-lieu").text
    assert "không có quyền" in t
    assert 'href="/"' in t          # còn đường quay ra


def test_co_quyen_thi_van_vao_binh_thuong(khach):
    c = khach(kho_du_lieu=True)
    _vao(c)
    assert c.get("/kho-du-lieu").status_code == 200


def test_bo_co_quyen_thi_luot_goi_KE_TIEP_da_bi_chan(khach, conn):
    """[CRITICAL] Thu hồi quyền phá huỷ mà phải đợi 12 giờ cho vé hết hạn là
    không thu hồi được. Cờ quyền CỐ Ý không nằm trong vé, chính vì chuyện
    này — nó được tra lại ở mỗi lượt gọi."""
    from kome.web import nguoi_dung as ND
    c = khach(kho_du_lieu=True)
    _vao(c)
    assert c.get("/kho-du-lieu").status_code == 200
    ND.dat_quyen(conn, "an", False)
    conn.commit()
    assert c.get("/kho-du-lieu").status_code == 403


def test_khong_co_quyen_thi_sidebar_khong_moi_bam_vao_kho_du_lieu(khach):
    """Một liên kết luôn dẫn tới trang từ chối thì tệ hơn là không có."""
    c = khach(kho_du_lieu=False)
    _vao(c)
    t = c.get("/khach-hang").text
    assert 'href="/kho-du-lieu"' not in t
    assert 'href="/khach-hang"' in t        # các mục khác vẫn còn


def test_co_quyen_thi_sidebar_van_co_muc_kho_du_lieu(khach):
    c = khach(kho_du_lieu=True)
    _vao(c)
    assert 'href="/kho-du-lieu"' in c.get("/khach-hang").text


def _no(*a, **k):
    """Giả lập một lỗi ngoài dự kiến (CSDL rụng, truy vấn hỏng…)."""
    raise RuntimeError("CSDL rung giua chung")


def test_trang_loi_van_con_duong_ve_kho_du_lieu(khach, monkeypatch):
    """[IMPORTANT] error.html KHÔNG có liên kết nào của riêng nó — chỉ ba bước
    "chụp màn hình, gửi cho người phụ trách, đừng thử lại" — nên sidebar là lối
    ra duy nhất. Đợt 3 bọc mục Kho dữ liệu trong `{% if hien_kho %}`, mà `_loi`
    lúc đó dựng ngữ cảnh bằng một đường riêng không có biến đó: Jinja Undefined
    là falsy, mục biến mất khỏi CHÍNH trang lỗi, kể cả với người CÓ quyền.
    Nghĩa là nạp file gặp lỗi lúc 13:30 thì người phụ trách đứng lại trên một
    trang không có cách nào quay về /kho-du-lieu ngoài gõ tay địa chỉ."""
    from kome import khach_hang as KH
    c = khach(kho_du_lieu=True)
    _vao(c)
    monkeypatch.setattr(KH, "danh_sach", _no)
    r = c.get("/khach-hang")
    assert r.status_code == 500
    assert "Hệ thống gặp lỗi" in r.text
    assert 'href="/kho-du-lieu"' in r.text, "trang lỗi mất đường về Kho dữ liệu"


def test_trang_loi_van_khong_moi_nguoi_khong_co_quyen(khach, monkeypatch):
    """Chiều ngược lại của test trên: gộp ngữ cảnh về một chỗ không được biến
    trang lỗi thành kẽ hở mời người không có quyền bấm vào màn bị cấm."""
    from kome import khach_hang as KH
    c = khach(kho_du_lieu=False)
    _vao(c)
    monkeypatch.setattr(KH, "danh_sach", _no)
    r = c.get("/khach-hang")
    assert r.status_code == 500
    assert 'href="/kho-du-lieu"' not in r.text


def test_csdl_hong_o_cong_dang_nhap_van_ra_trang_loi_tieng_viet(
        khach, monkeypatch, capsys):
    """[IMPORTANT] Middleware `chan_cua` tra app.nguoi_dung ở MỌI lượt gọi, nên
    một lần Supabase trục trặc biến MỌI trang thành 500 trần của Starlette
    (tiếng Anh, đầy dấu vết ngăn xếp) — công ty không có nhân sự IT và `_loi`
    tồn tại chính xác vì lý do đó. Trước đợt 3 cổng là HMAC thuần, không chạm
    CSDL, nên lưới bắt lỗi của từng route là đủ; giờ thì không.

    Cũng kiểm hai chuyện dễ mất: lỗi vẫn ghi ra nhật ký máy chủ (không nuốt),
    và KHÔNG bị hiểu thành "chưa đăng nhập" rồi đá về /dang-nhap — trang đó
    cũng tra CSDL và cũng hỏng, người dùng chỉ thấy một vòng lặp."""
    from kome.web import nguoi_dung as ND
    c = khach()
    _vao(c)
    monkeypatch.setattr(ND, "theo_id", _no)
    r = c.get("/khach-hang")
    assert r.status_code == 500, "lỗi CSDL trong middleware không ra trang lỗi"
    assert "Hệ thống gặp lỗi" in r.text
    assert "RuntimeError" not in r.text, "chuỗi ngoại lệ gốc lọt lên trang"
    assert "CSDL rung giua chung" in capsys.readouterr().out, "lỗi bị nuốt"


def test_khong_co_cong_dang_nhap_thi_khong_chan_ai(khach):
    """Máy trong công ty để trống KOME_SESSION_SECRET: không có đăng nhập thì
    cũng không có khái niệm quyền — mọi thứ mở như trước đợt 3."""
    c = khach(bi_mat=None, tai_khoan=False)
    assert c.get("/kho-du-lieu").status_code == 200
    assert 'href="/kho-du-lieu"' in c.get("/khach-hang").text


# ---- Mặc định "khách của tôi" (đợt 3) ----------------------------------

def test_dang_nhap_co_ma_sale_thi_trang_khach_mac_dinh_loc_theo_minh(khach):
    """Mặc định TIỆN DỤNG, không phải hàng rào: trang nói rõ đang lọc theo ai
    và có một liên kết hiện rõ để xem tất cả."""
    c = khach(sale="0104")
    _vao(c)
    t = c.get("/khach-hang").text
    assert "TRAN THI LAN THANH" in t
    assert "tat_ca=1" in t, "không có đường thoát khỏi bộ lọc"


def test_bam_xem_tat_ca_thi_bo_loc(khach):
    c = khach(sale="0104")
    _vao(c)
    r = c.get("/khach-hang?tat_ca=1")
    assert r.status_code == 200
    assert "Đang xem khách của" not in r.text


def test_chon_moi_nguoi_phu_trach_thi_that_su_bo_loc(khach, conn, batch):
    """[IMPORTANT] Mục đầu của ô lọc 担当者 phải THẬT SỰ bỏ lọc.

    Trước vòng sửa này mục đó mang giá trị RỖNG, mà rỗng nghĩa là "không chọn
    gì" -> trang rơi về mặc định của đợt 3 và lọc theo người ĐANG ĐĂNG NHẬP.
    Kết quả: ô chọn khoe "— mọi người phụ trách —" trong khi danh sách vẫn
    chỉ có khách của một người — đúng cái "ô điều khiển nói một đằng, dữ liệu
    một nẻo" mà test của ô Tỉnh được viết ra để chặn. Và vì form lọc chỉ mang
    `tat_ca` khi nó ĐÃ bật, trên bản Vercel nhân viên không có đường nào từ ô
    đó ra xem toàn công ty.
    """
    from tests.test_khach_hang import HOM_NAY, _ho_so_khach, _mua

    _ho_so_khach(conn, batch, "S0104", "Quan CUA MINH", salesperson_code="0104")
    _ho_so_khach(conn, batch, "S0102", "Quan NGUOI KHAC", salesperson_code="0102")
    for ma in ("S0104", "S0102"):
        _mua(conn, batch, ma, HOM_NAY)

    c = khach(sale="0104")
    _vao(c)

    mac_dinh = c.get("/khach-hang").text
    assert "Quan NGUOI KHAC" not in mac_dinh, "mặc định đợt 3 đã hỏng"
    # Ô chọn phải nói đúng cái đang xảy ra: đang lọc theo 0104 thì nó hiện
    # tên 0104, KHÔNG hiện "— mọi người phụ trách —".
    assert '<option value="__moi_nguoi" selected>' not in mac_dinh, \
        "ô chọn khoe 'mọi người' trong khi danh sách đang bị lọc theo một người"

    moi_nguoi = c.get(f"/khach-hang?nv={KH.NV_MOI_NGUOI}").text
    assert "Quan NGUOI KHAC" in moi_nguoi and "Quan CUA MINH" in moi_nguoi, \
        "chọn '— mọi người phụ trách —' mà danh sách vẫn bị lọc theo người đăng nhập"
    assert "Đang xem khách của" not in moi_nguoi
    assert '<option value="__moi_nguoi" selected>' in moi_nguoi


def test_nguoi_khong_phu_trach_khach_nao_thay_toan_bo_ngay_tu_dau(khach):
    """[IMPORTANT] Chủ DN, kế toán, kho có salesperson_code NULL. Lọc theo
    NULL thì họ mở lên thấy danh sách rỗng và tưởng hệ thống mất dữ liệu."""
    c = khach(sale=None)
    _vao(c)
    assert "Đang xem khách của" not in c.get("/khach-hang").text


def test_nut_dang_xuat_co_icon_VA_van_con_chu(khach):
    """Đợt 4d: nút Đăng xuất nằm NGOÀI <nav> và chỉ render khi có cổng đăng
    nhập, nên test icon ở tests/test_giao_dien.py không với tới được nó.

    Cùng bất biến với các mục điều hướng: icon là trang trí, chữ mới là nhãn.
    Đây là nút DUY NHẤT trong sidebar kết thúc một phiên làm việc — một cái
    nút chỉ có hình thì người mới sẽ phải đoán, và đoán sai ở đây nghĩa là
    bấm nhầm rồi mất chỗ đang làm dở.
    """
    c = khach()
    _vao(c)
    html = c.get("/").text
    thoat = re.search(r'<div class="thoat">(.*?)</div>', html, re.S).group(1)
    the_svg = re.findall(r"<svg[^>]*>", thoat)
    assert the_svg, "nút Đăng xuất thiếu icon"
    for the in the_svg:
        assert 'aria-hidden="true"' in the, the
        assert 'focusable="false"' in the, the
    chu = re.sub(r"<svg.*?</svg>", "", thoat, flags=re.S)
    assert "Đăng xuất" in chu


def test_duong_dan_an_toan_chan_ca_dang_gach_cheo_nguoc():
    """`/\noi-khac.example` là địa chỉ tuyệt đối trá hình.

    Theo chuẩn phân tích URL của WHATWG, gạch chéo ngược ngay sau gạch chéo
    đầu được coi NHƯ một gạch chéo, nên chuỗi đó tương đương `//noi-khac…`.
    Hôm nay Starlette mã hoá nó thành `%5C` trước khi đặt vào header
    `Location` nên nó vô hại — nhưng đó là hành vi của framework, không phải
    của ta. Chặn tại hàm này thì an toàn không phụ thuộc vào bản nâng cấp nào.
    """
    bs = chr(92)
    assert bao_mat.duong_dan_an_toan("/" + bs + "noi-khac.example") == "/"
    assert bao_mat.duong_dan_an_toan("/" + bs + bs + "/noi-khac.example") == "/"
    # Không được chặn nhầm đường dẫn nội bộ có query — đó là ca CHÍNH của
    # nút đổi giao diện: bấm "Tối" ở một danh sách đang lọc phải quay lại
    # đúng danh sách đó, còn nguyên bộ lọc.
    assert (bao_mat.duong_dan_an_toan("/khach-hang?tinh=%E6%9D%B1%E4%BA%AC%E9%83%BD&nv=0102")
            == "/khach-hang?tinh=%E6%9D%B1%E4%BA%AC%E9%83%BD&nv=0102")


def test_canh_bao_khoi_dong_khong_giet_app_tren_console_cp1252(monkeypatch):
    """Console Windows mặc định là cp1252, không mã hoá được chữ Việt có dấu.
    Một `print()` tiếng Việt lúc khởi động nổ UnicodeEncodeError và app không
    lên được — đúng ở chỗ cảnh báo "mất một lớp phòng thủ" lại thành sự cố
    chắc chắn. Cảnh báo phải vẫn in ra (không nuốt), chỉ đổi ký tự không mã
    hoá được thành dạng thoát."""
    import io
    import sys
    ra = io.TextIOWrapper(io.BytesIO(), encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", ra)
    monkeypatch.delenv("DATABASE_URL_APP", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    create_app()
    ra.flush()
    chu = ra.buffer.getvalue().decode("cp1252")
    assert "DATABASE_URL_APP" in chu, "cảnh báo bị nuốt"
