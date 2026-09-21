"""Cổng đăng nhập và chế độ chỉ-đọc — điều kiện để đưa trang lên Internet.

Trang này hiển thị doanh thu, lãi gộp, giá vốn từng mặt hàng và danh sách
2.080 khách hàng. Mọi test ở đây bảo vệ đúng một câu: **không ai xem được
thứ đó nếu không đăng nhập**, và **không ai nạp/xoá dữ liệu qua bản công
khai**.
"""
import pytest
from fastapi.testclient import TestClient

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
