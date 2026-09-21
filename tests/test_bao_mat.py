"""Cổng đăng nhập và chế độ chỉ-đọc — điều kiện để đưa trang lên Internet.

Trang này hiển thị doanh thu, lãi gộp, giá vốn từng mặt hàng và danh sách
2.080 khách hàng. Mọi test ở đây bảo vệ đúng một câu: **không ai xem được
thứ đó nếu không có mật khẩu**, và **không ai nạp/xoá dữ liệu qua bản công
khai**.
"""
import time

import pytest
from fastapi.testclient import TestClient

from kome.web import bao_mat
from kome.web.app import create_app

MK = "mat-khau-du-dai-2026"


@pytest.fixture
def khach(monkeypatch, test_db_url):
    """Trình duyệt KHÔNG tự đi theo chuyển hướng — phải thấy tận mắt mã 303."""
    def _tao(mat_khau: str | None = MK, vercel: bool = False):
        monkeypatch.delenv("KOME_CHI_DOC", raising=False)
        if mat_khau is None:
            monkeypatch.delenv("KOME_MAT_KHAU", raising=False)
        else:
            monkeypatch.setenv("KOME_MAT_KHAU", mat_khau)
        if vercel:
            monkeypatch.setenv("VERCEL", "1")
        else:
            monkeypatch.delenv("VERCEL", raising=False)
        # vercel=True => base_url https: bản công khai LUÔN chạy HTTPS, và
        # cookie phiên ở đó mang cờ Secure nên trình duyệt không gửi lại qua
        # HTTP. Giả lập bằng http:// sẽ dựng nên một thế giới không có thật,
        # nơi đăng nhập "thành công" rồi trang sau lại đòi đăng nhập.
        return TestClient(create_app(db_url=test_db_url), follow_redirects=False,
                          base_url="https://testserver" if vercel else "http://testserver")
    return _tao


# ---- Vé đăng nhập ------------------------------------------------------

def test_ve_hop_le_chi_voi_dung_mat_khau():
    ve = bao_mat.tao_ve(MK)
    assert bao_mat.ve_hop_le(ve, MK)
    assert not bao_mat.ve_hop_le(ve, "mat-khau-khac-dai")


def test_ve_het_han_sau_han_phien():
    """[IMPORTANT] Vé không hết hạn nghĩa là một máy tính bị mượn hôm nay vẫn
    xem được số liệu công ty vào năm sau."""
    ve = bao_mat.tao_ve(MK, bay_gio=1_000_000)
    assert bao_mat.ve_hop_le(ve, MK, bay_gio=1_000_000 + bao_mat.HAN_PHIEN_GIAY - 1)
    assert not bao_mat.ve_hop_le(ve, MK, bay_gio=1_000_000 + bao_mat.HAN_PHIEN_GIAY + 1)


def test_ve_gia_mao_bi_tu_choi():
    """Sửa hạn trong vé mà không ký lại thì chữ ký không khớp."""
    het, _, chu_ky = bao_mat.tao_ve(MK, bay_gio=time.time()).partition(".")
    xa = str(int(het) + 10 * 365 * 24 * 3600)
    assert not bao_mat.ve_hop_le(f"{xa}.{chu_ky}", MK)
    assert not bao_mat.ve_hop_le("khong-co-dau-cham", MK)
    assert not bao_mat.ve_hop_le(f"khong-phai-so.{chu_ky}", MK)
    assert not bao_mat.ve_hop_le(None, MK)


def test_doi_mat_khau_huy_moi_ve_dang_luu_hanh():
    """[IMPORTANT] Không có kho phiên ở máy chủ (bắt buộc, để chạy được trên
    Vercel), nên đổi mật khẩu là cách DUY NHẤT chặn người đã nghỉ việc."""
    assert not bao_mat.ve_hop_le(bao_mat.tao_ve(MK), MK + "-moi")


@pytest.mark.parametrize("tiep,mong", [
    ("/phu-du-lieu", "/phu-du-lieu"),
    ("https://site-gia.example", "/health"),   # địa chỉ tuyệt đối
    ("//site-gia.example", "/health"),         # cũng là tuyệt đối
    (None, "/health"),
])
def test_khong_lam_ban_dap_chuyen_huong(tiep, mong):
    """Trang đăng nhập của công ty không được đẩy người dùng sang site lạ."""
    assert bao_mat.duong_dan_an_toan(tiep) == mong


# ---- Cấu hình phải an toàn ngay từ lúc khởi động ------------------------

def test_tren_vercel_ma_khong_co_mat_khau_thi_app_chet_ngay(khach):
    """[CRITICAL] Không có mật khẩu + công khai = số liệu công ty mở cho cả
    Internet. Phải nổ lúc dựng app, nơi người triển khai đọc được nhật ký."""
    with pytest.raises(bao_mat.CauHinhSai, match="KOME_MAT_KHAU"):
        khach(mat_khau=None, vercel=True)


def test_mat_khau_qua_ngan_bi_tu_choi(khach):
    """Mỗi lần gọi trên Vercel là một tiến trình riêng nên không đếm chung
    được số lần đoán sai — độ dài mật khẩu là lớp bảo vệ duy nhất."""
    with pytest.raises(bao_mat.CauHinhSai, match="ký tự"):
        khach(mat_khau="ngan")


def test_chay_o_may_ca_nhan_khong_bat_buoc_mat_khau(khach):
    """Máy trong công ty chạy ở 127.0.0.1 — bắt đăng nhập ở đó chỉ làm chậm
    công việc hằng ngày mà không chặn được ai.

    Đợt 2a (Task 4): /health giờ chỉ 301 sang /kho-du-lieu — kiểm thẳng màn
    gộp, /health không còn render nội dung gì để kiểm."""
    r = khach(mat_khau=None).get("/kho-du-lieu")
    assert r.status_code == 200


# ---- Cổng chặn trên mọi trang ------------------------------------------

@pytest.mark.parametrize("duong_dan", ["/", "/kho-du-lieu", "/khach-hang"])
def test_chua_dang_nhap_thi_moi_trang_deu_bi_chan(khach, duong_dan):
    """Đợt 2a (Task 4): /health và /phu-du-lieu giờ chỉ 301 sang
    /kho-du-lieu — kiểm chúng ở đây không còn kiểm được gì (redirect rỗng
    trước khi middleware đăng nhập kịp chạm nội dung). Đổi sang ba trang
    THẬT SỰ có nội dung, và /kho-du-lieu PHẢI có mặt vì đó đúng là trang
    giờ mang nhật ký nạp, bảng phủ dữ liệu và khối Hoàn tác."""
    r = khach().get(duong_dan)
    assert r.status_code == 303
    assert r.headers["location"] == "/dang-nhap"
    assert "¥" not in r.text and "得意先" not in r.text


def test_dang_nhap_dung_thi_xem_duoc_va_sai_thi_khong(khach):
    c = khach()
    r = c.post("/dang-nhap", data={"mat_khau": "doan-bua-mot-cai"})
    assert r.status_code == 401
    assert bao_mat.TEN_COOKIE not in c.cookies

    r = c.post("/dang-nhap", data={"mat_khau": MK})
    assert r.status_code == 303
    # /health giờ chỉ 301 sang /kho-du-lieu (Task 4) — kiểm thẳng màn gộp.
    assert c.get("/kho-du-lieu").status_code == 200


def test_dang_nhap_xong_quay_lai_dung_trang_dinh_xem(khach):
    c = khach()
    c.get("/phu-du-lieu")                       # bị đẩy về /dang-nhap
    r = c.post("/dang-nhap", data={"mat_khau": MK})
    assert r.headers["location"] == "/phu-du-lieu"


def test_cookie_phien_khong_doc_duoc_bang_javascript(khach):
    """HttpOnly: một đoạn mã lạ chèn vào trang không đọc được vé để mang đi."""
    c = khach()
    r = c.post("/dang-nhap", data={"mat_khau": MK})
    dat = r.headers["set-cookie"]
    assert "httponly" in dat.lower()
    assert "samesite=lax" in dat.lower()


def test_tren_hang_tang_cong_khai_cookie_luon_co_co_secure(khach):
    """[IMPORTANT] Không có cờ Secure thì trình duyệt chịu gửi vé đăng nhập
    qua HTTP thường, nơi ai chung mạng Wi-Fi cũng đọc được.

    Không suy ra cờ này từ `request.url.scheme`: trên Vercel ứng dụng đứng sau
    proxy đã gỡ vỏ HTTPS, scheme có thể đọc ra "http" và cờ âm thầm biến mất.
    """
    r = khach(vercel=True).post("/dang-nhap", data={"mat_khau": MK})
    assert "secure" in r.headers["set-cookie"].lower()


def test_o_may_ca_nhan_khong_gan_secure(khach):
    """Ngược lại: máy trong công ty chạy http://127.0.0.1, gắn Secure ở đó là
    trình duyệt vứt cookie đi và không ai đăng nhập được, không lời giải thích."""
    r = khach().post("/dang-nhap", data={"mat_khau": MK})
    assert "secure" not in r.headers["set-cookie"].lower()


def test_thoat_thi_het_xem_duoc(khach):
    """/health giờ chỉ 301 sang /kho-du-lieu (Task 4) — kiểm thẳng màn gộp,
    trạng thái đăng nhập/đăng xuất không đổi."""
    c = khach()
    c.post("/dang-nhap", data={"mat_khau": MK})
    assert c.get("/kho-du-lieu").status_code == 200
    c.post("/dang-xuat")
    assert c.get("/kho-du-lieu").status_code == 303


def test_mat_khau_khong_bao_gio_hien_tren_trang(khach):
    """Kể cả trang đăng nhập sai — người đứng sau lưng cũng đọc được màn hình."""
    c = khach()
    for r in (c.get("/dang-nhap"), c.post("/dang-nhap", data={"mat_khau": "sai"})):
        assert MK not in r.text


def test_static_khong_bi_chan_boi_cong_dang_nhap(khach):
    """[CRITICAL] Task chuyển CSS/font ra /static (nhánh giao diện) khiến
    /dang-nhap PHỤ THUỘC vào một tài nguyên mà chính cổng đăng nhập chặn.

    Trước nhánh giao diện, CSS nằm inline trong _chung.html nên trang đăng
    nhập tự mang theo kiểu dáng. Từ khi CSS/font chuyển ra kome/web/static/,
    middleware `chan_cua` (chỉ miễn trừ đúng path "/dang-nhap") đá
    GET /static/kome.css và mọi file font về 303 /dang-nhap — trên bản
    Vercel (nơi KOME_MAT_KHAU LUÔN bắt buộc), màn hình ĐẦU TIÊN người dùng
    thấy là một trang trơ trụi, không CSS không font.

    Bộ test cũ không bắt được vì hầu hết chạy với khach(mat_khau=None) —
    tức không có middleware nào cả. Test này phải dựng app CÓ mật khẩu."""
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
    c.post("/dang-nhap", data={"mat_khau": MK})

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
    c.post("/dang-nhap", data={"mat_khau": MK})
    t = c.get("/kho-du-lieu").text
    assert "Nạp từ OBC" not in t and 'href="/nap"' not in t
    assert 'id="nap"' not in t
    assert "在庫一覧" in t and 'href="/khach-hang"' in t


def test_ban_chi_doc_khong_bao_dong_sao_luu_gia(khach):
    """[IMPORTANT] Máy chủ công khai không nhìn thấy thư mục sao lưu nên luôn
    kết luận "chưa sao lưu". Một dải đỏ vĩnh viễn dạy người đọc bỏ qua dải
    đỏ — đúng thứ hệ thống này cần họ tin."""
    c = khach(vercel=True)
    c.post("/dang-nhap", data={"mat_khau": MK})
    # /health chỉ 301 sang /kho-du-lieu (Task 4) — khối sức khoẻ giờ nằm ở đó.
    t = c.get("/kho-du-lieu").text
    assert "Chưa sao lưu" not in t
    assert "máy trong công ty" in t


def test_ban_o_may_ca_nhan_van_nap_duoc(khach):
    """/nap giờ LUÔN 301 sang /kho-du-lieu#nap (Task 4) — theo tới đích để
    xác nhận khối nạp vẫn còn, còn hiện."""
    c = khach(mat_khau=None)
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
    assert not any(m.startswith(("kome.pipeline", "pandas", "calamine")) for m in muc),         f"app.py nhập ở mức ngoài cùng: {sorted(muc)}"
