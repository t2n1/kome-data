# kome/web/app.py
import os, shutil, sys, tempfile, traceback
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from kome.bao_cao import (tinh_bao_cao, ve_bieu_do, tien_do_ngan_sach, ve_luy_ke,
                          nhom_theo_nganh)
from kome.coverage import tinh_bang_ngay, tinh_bang_phu
# kome/ve_phan_tich.py chỉ tính hình học SVG thuần Python (không conn, không
# pandas) — an toàn nhập ở mức ngoài cùng, cùng lý do với kome/san_pham.py.
from kome.ve_phan_tich import (ve_duong_nho, ve_dong_gop, ve_cay_o, ve_nhiet,
                               ve_pareto, ve_xu_huong)
from kome.ngan_sach import thang_cua_ky
from kome import khach_hang as KH
# kome/tong_quan.py (đợt 5b Task 5) — dữ liệu cho `/`. Chỉ dataclasses +
# gọi lại các hàm mart/khach_hang/san_pham đã có (+ psycopg qua `conn`),
# cùng lý do an toàn nhập ở mức ngoài cùng như kome/san_pham.py.
from kome import tong_quan as TQ
# Nhập ở mức ngoài cùng được: kome/san_pham.py chỉ dùng dataclasses/datetime
# (+ psycopg qua `conn` truyền vào), KHÔNG kéo pandas hay python-calamine —
# đúng ràng buộc mà test_trang_chi_doc_khong_phu_thuoc_pandas canh.
from kome import san_pham as SP
# kome/ban_do.py cũng chỉ dùng dataclasses, cùng lý do trên — an toàn nhập ở
# mức ngoài cùng.
from kome import ban_do as BD
from kome.db import connect
from kome.env import nap_env
from kome.nhat_ky_nap import lo_nap_gan_nhat, trang_thai_nap
# Nhập CẢ module (không chỉ `tinh_tuoi`): chế độ "theo-gio" của Task 2 gọi
# thẳng `TDL._bay_gio()` mỗi request để lấy giờ NHẬT THẬT, và test monkeypatch
# đúng tên thuộc tính đó trên module (`kome.tuoi_du_lieu._bay_gio`, xem
# tests/test_web.py). `from kome.tuoi_du_lieu import _bay_gio` sẽ chốt cứng
# tham chiếu hàm GỐC lúc nhập module — monkeypatch sau đó không còn tác dụng
# vì nó thay thuộc tính trên module tuoi_du_lieu, không thay biến cục bộ đã
# bind sẵn ở đây.
from kome import tuoi_du_lieu as TDL
from kome.tuoi_du_lieu import tinh_tuoi
from kome.web import bao_mat
from kome.web import nguoi_dung as ND
from kome.web import bo_cuc as BC
from kome.web import spa as SPA
from kome.web import anh_chup
from kome.web.api import tao_api
from kome.khoi_tong_quan import CHUA_CO as KTQ_CHUA_CO
from ops.backup import backup_status

# Đợt 4d (Task 2) — nút đổi giao diện sáng/tối, KHÔNG JS.
TEN_COOKIE_GIAO_DIEN = "kome_giao_dien"
CHE_DO_GIAO_DIEN_HOP_LE = ("he-thong", "sang", "toi", "theo-gio")
HAN_COOKIE_GIAO_DIEN_GIAY = 365 * 24 * 3600
# 18:00–06:00 giờ Nhật coi là "tối" cho chế độ theo-gio (đặc tả đợt 4d).
GIO_BAT_DAU_TOI = 18
GIO_KET_THUC_TOI = 6


def _che_do_giao_dien(request: Request) -> str:
    """Chế độ NGƯỜI DÙNG ĐÃ CHỌN (chưa quy ra sáng/tối) — giá trị lạ trong
    cookie (gõ tay, hoặc một cookie cũ từ bản trước) rơi về "he-thong", KHÔNG
    được làm trang nổ và KHÔNG được lọt nguyên văn ra HTML."""
    che_do = request.cookies.get(TEN_COOKIE_GIAO_DIEN, "he-thong")
    return che_do if che_do in CHE_DO_GIAO_DIEN_HOP_LE else "he-thong"


def _data_theme(che_do: str) -> str | None:
    """`data-theme` để render lên <html>, hoặc None để KHÔNG đặt gì (chế độ
    "he-thong" — nhường quyền quyết định cho @media (prefers-color-scheme)
    thuần CSS, xem kome.css)."""
    if che_do in ("sang", "toi"):
        return che_do
    if che_do == "theo-gio":
        # Giờ NHẬT THẬT, không phải giờ máy chủ (CSDL/Vercel chạy UTC) —
        # dùng lại nguyên hàm của kome/tuoi_du_lieu.py, xem chú thích ở nơi
        # nhập module phía trên.
        gio = TDL._bay_gio().hour
        return "toi" if (gio >= GIO_BAT_DAU_TOI or gio < GIO_KET_THUC_TOI) else "sang"
    return None

# Tự đọc .env khi chạy ở máy trong công ty. `uvicorn kome.web.app:app` khởi
# động trong môi trường trống, nên không có dòng này thì trang chạy lên bình
# thường rồi báo lỗi đỏ ở /kho-du-lieu — người dùng đọc thành "hỏng CSDL" chứ
# không đọc ra "quên nạp biến môi trường".
# bat_buoc=False: trên Vercel KHÔNG có file .env (biến lấy từ bảng cấu hình),
# và biến môi trường đã có sẵn luôn được ưu tiên hơn file.
nap_env(bat_buoc=False)

# CỐ Ý không nhập kome.pipeline ở đây. pipeline kéo theo pandas +
# python-calamine (~120 MB) chỉ để ĐỌC file Excel — thứ mà bản chỉ-đọc trên
# Vercel không bao giờ làm. Hai hàm ingest/undo_batch được nhập bên trong thân
# route, nên chúng chỉ nạp khi thật sự có người nạp hoặc hoàn tác dữ liệu.

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Cửa sổ soát ngày thiếu trên /kho-du-lieu (tính lùi từ ngày bán gần nhất).
SO_NGAY_SOAT = 30

# Mọi đường dẫn thuộc màn Kho dữ liệu — màn DUY NHẤT có nút xoá dữ liệu.
# Ba địa chỉ cũ ở cuối danh sách vẫn phải chặn dù chúng chỉ còn trả 301: để
# hở chúng là để người không có quyền dò ra cấu trúc màn bị cấm.
DUONG_KHO_DU_LIEU = ("/kho-du-lieu", "/upload", "/undo",
                     "/nap", "/health", "/phu-du-lieu")


def _thuoc_kho_du_lieu(duong: str) -> bool:
    """`/undo/12` cũng thuộc màn này, nên so bằng tiền tố có ranh giới `/`
    chứ không so bằng nhau — nhưng `/khach-hang` KHÔNG được dính vào
    `/kho-du-lieu` chỉ vì cùng vài ký tự đầu."""
    return any(duong == d or duong.startswith(d + "/") for d in DUONG_KHO_DU_LIEU)


# Màn Ngân sách: đặt và sửa chỉ tiêu doanh thu của cả công ty. Cùng nếp
# DUONG_KHO_DU_LIEU — gác cả cửa đọc lẫn cửa ghi. Gác mỗi GET là để nguyên
# cửa ghi mở toang cho ai biết gõ `curl`.
DUONG_NGAN_SACH = ("/ngan-sach",)


def _thuoc_ngan_sach(duong: str) -> bool:
    return any(duong == d or duong.startswith(d + "/") for d in DUONG_NGAN_SACH)


def _chi_doc() -> bool:
    """Trang có ở chế độ CHỈ ĐỌC không (ẩn hẳn phần nạp dữ liệu)?

    Trên Vercel thì LUÔN chỉ đọc, và đây không phải lựa chọn:
      * mỗi yêu cầu bị chặn ở 4,5 MB, còn một file 売上伝票データ nặng ~100 MB;
      * ổ đĩa của hàm serverless là tạm — ghi xong là mất, nên lớp `raw`
        (lưu nguyên file Excel gốc) không tồn tại được ở đó;
      * nạp một quý bán hàng mất ~88 giây, vượt giới hạn thời gian chạy.
    Ba thứ đó là giới hạn nền tảng. Cho phép bật nạp dữ liệu trên Vercel chỉ
    tạo ra một nút bấm luôn báo lỗi khó hiểu giữa chừng.

    Ngoài Vercel thì đặt KOME_CHI_DOC=1 nếu muốn dựng thêm một bản chỉ để xem.
    """
    return bao_mat.tren_mang() or os.environ.get("KOME_CHI_DOC", "").strip().lower() in (
        "1", "true", "yes", "co", "có")


def _ky_du_lieu(conn) -> dict:
    """Kỳ dữ liệu bán hàng + các ngày LÀM VIỆC không có dòng nào.

    Không có gì khác trong hệ thống phát hiện thiếu hẳn một ngày: nhân viên
    nghỉ ốm, không ai kéo–thả, hôm sau nạp bình thường và /kho-du-lieu xanh hết.
    Ba tháng sau báo cáo thiếu một ngày và không ai truy được ngày nào.

    Ngày nghỉ (cuối tuần VÀ ngày lễ Nhật, từ 032) bỏ qua bằng
    mart.lich_kinh_doanh — định nghĩa duy nhất của ngày làm việc. Ngày nghỉ
    riêng của công ty (Obon, 年末年始) KHÔNG có trong đó nên vẫn bị liệt kê —
    cảnh báo nhắc người đọc kiểm tra.
    """
    dau, cuoi = conn.execute(
        "SELECT min(sales_date), max(sales_date) FROM core.fact_sales_line"
    ).fetchone()
    if cuoi is None:
        return {"dau": None, "cuoi": None, "thieu": []}
    tu = max(dau, cuoi - timedelta(days=SO_NGAY_SOAT - 1))
    thieu = [
        r[0] for r in conn.execute(
            """SELECT d.ngay FROM mart.lich_kinh_doanh d
               WHERE d.la_ngay_kd
                 AND d.ngay BETWEEN %s AND %s
                 AND NOT EXISTS (SELECT 1 FROM core.fact_sales_line f
                                 WHERE f.sales_date = d.ngay)
               ORDER BY d.ngay""",
            (tu, cuoi),
        ).fetchall()
    ]
    return {"dau": dau, "cuoi": cuoi, "thieu": thieu, "tu": tu}



def _in(thong_diep: str) -> None:
    """In ra nhật ký máy chủ mà không bao giờ nổ vì bảng mã của console.

    Console Windows mặc định là cp1252, không mã hoá được chữ Việt có dấu —
    `print()` trần nổ UnicodeEncodeError, và ở lúc khởi động thì app không lên
    được. Ký tự không mã hoá được đổi thành dạng thoát (`\\u1ea2`) chứ không
    bỏ: cảnh báo vẫn phải đọc được, chỉ xấu đi một chút."""
    try:
        print(thong_diep, flush=True)
    except UnicodeEncodeError:
        ma = getattr(sys.stdout, "encoding", None) or "ascii"
        print(thong_diep.encode(ma, "backslashreplace").decode(ma), flush=True)


def create_app(db_url: str | None = None, db_url_app: str | None = None) -> FastAPI:
    """db_url=None => lấy DATABASE_URL. Test LUÔN truyền DATABASE_URL_TEST."""
    app = FastAPI(title="KOME — dữ liệu")
    # Phục vụ CSS và font từ đĩa. Dùng StaticFiles có sẵn trong FastAPI —
    # KHÔNG thêm gói nào vào requirements.txt (bản Vercel cố ý mỏng).
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).parent / "static")),
        name="static",
    )
    # File build của giao diện React (kome/web/spa/, commit vào git — đặc tả
    # 2026-09-23-giao-dien-react-design.md). Tên file có mã băm nội dung nên
    # trình duyệt giữ lâu được; không chứa một byte dữ liệu kinh doanh nào.
    app.mount("/assets", StaticFiles(directory=str(SPA.THU_MUC / "assets"), check_dir=False),
              name="assets")
    archive_dir = Path(os.environ.get("ARCHIVE_DIR", "./raw_archive"))
    open_conn = lambda: connect(db_url)
    chi_doc = _chi_doc()

    # Hai kết nối, hai vai trò CSDL (đặc tả đợt 3 §6.3):
    #   open_conn     -> DATABASE_URL     (kome_ingest_user): NẠP và HOÀN TÁC,
    #                                      chỉ màn Kho dữ liệu dùng
    #   open_app_conn -> DATABASE_URL_APP (kome_app_user): mọi trang còn lại,
    #                                      vai trò KHÔNG ghi được vào `core`
    # Lỡ tay viết một câu UPDATE core.… ở một trang đọc thì chính CSDL từ
    # chối — lớp an toàn ở tầng quyền, không phụ thuộc review code có bắt
    # được hay không.
    #
    # db_url truyền TƯỜNG MINH (test luôn truyền) thì kết nối app đi theo
    # đúng CSDL đó. Không có dòng này thì test chạy trên CSDL thử nghiệm
    # nhưng lại đọc app.nguoi_dung của CSDL THẬT trên máy có DATABASE_URL_APP.
    if db_url_app is None:
        db_url_app = db_url if db_url is not None else os.environ.get("DATABASE_URL_APP")
    if db_url_app is None:
        # Cảnh báo chứ không chết: vai trò CSDL là lớp phòng thủ thứ hai, còn
        # cổng đăng nhập mới là thứ chặn người lạ. Giết cả trang vì thiếu một
        # lớp phòng thủ thứ hai là đổi một rủi ro lấy một sự cố chắc chắn.
        _in("[KOME] CẢNH BÁO: chưa đặt DATABASE_URL_APP — các trang chỉ đọc "
              "đang chạy bằng vai trò nạp dữ liệu, tức có quyền ghi vào core. "
              "Xem docs/runbook.md, mục 'Hai kết nối CSDL'.")
    open_app_conn = lambda: connect(db_url_app)

    bi_mat = bao_mat.bi_mat_phien()
    # Ném CauHinhSai ngay lúc dựng app, trước khi phục vụ dòng nào.
    bao_mat.kiem_cau_hinh_phien(bi_mat, cong_khai=bao_mat.tren_mang())

    # Biến mà MỌI trang đều cần để vẽ đúng thanh điều hướng. Gom vào một chỗ
    # để không trang nào bị sót: sót `chi_doc` thì trang đó vẫn mời người ta
    # bấm "Nạp dữ liệu" — một liên kết dẫn thẳng tới 403 trên bản công khai.
    chung = {"chi_doc": chi_doc, "co_dang_nhap": bool(bi_mat)}

    def _ve(request: Request, ten: str, ctx: dict, **kw) -> HTMLResponse:
        # `nguoi` gắn bởi middleware chan_cua. getattr có mặc định vì KHÔNG
        # PHẢI lúc nào cũng có middleware: máy trong công ty để trống
        # KOME_SESSION_SECRET thì không có cổng, và /dang-nhap thì chạy
        # TRƯỚC khi ai kịp là ai.
        nguoi = getattr(request.state, "nguoi", None)
        # `nguoi is None` = không có cổng đăng nhập (máy trong công ty để
        # trống KOME_SESSION_SECRET) -> mọi thứ mở, y như trước đợt 3.
        hien_kho = nguoi is None or nguoi.duoc_vao_kho_du_lieu
        # Cùng lý lẽ với hien_kho: mời người ta bấm vào một thứ sẽ từ chối họ
        # thì tệ hơn là không hiện. `nguoi is None` = không có cổng đăng nhập
        # (máy trong công ty) -> mọi thứ mở, y như trước đợt 3.
        hien_ngan_sach = nguoi is None or nguoi.duoc_sua_ngan_sach
        # Chế độ giao diện đọc từ cookie MỖI LƯỢT (không chốt lúc dựng app,
        # khác `chung` ở trên): mỗi người một lựa chọn riêng trên cùng một
        # app. `che_do_giao_dien` cho _nav.html biết nút nào đang "đang
        # chọn"; `data_theme` cho _chung.html biết có đặt thuộc tính gì lên
        # <html> không (xem kome/web/app.py::_data_theme).
        che_do = _che_do_giao_dien(request)
        return TEMPLATES.TemplateResponse(
            request, ten,
            {**ctx, **chung, "nguoi": nguoi, "hien_kho": hien_kho,
             "hien_ngan_sach": hien_ngan_sach,
             "che_do_giao_dien": che_do, "data_theme": _data_theme(che_do)},
            **kw)

    def _loi(request: Request, viec: str, exc: Exception) -> HTMLResponse:
        """Trang lỗi tiếng Việt cho mọi lỗi NGOÀI DỰ KIẾN.

        Công ty không có nhân sự IT: trang 500 mặc định của framework (tiếng
        Anh, đầy dấu vết ngăn xếp) làm người dùng tưởng mình bấm sai rồi thử
        lại — và đó chính là lúc lô mồ côi biến thành "đã nạp rồi, bỏ qua"
        màu xanh. Chuỗi ngoại lệ gốc CHỈ ghi ra nhật ký máy chủ, KHÔNG hiện
        lên trang.

        Dựng ngữ cảnh QUA `_ve`, không dựng riêng một đường thứ hai: error.html
        include _nav.html, mà thanh điều hướng chỉ hiện mục Kho dữ liệu khi có
        biến `hien_kho`. Đường dựng riêng trước đây thiếu đúng biến đó, nên
        người CÓ quyền gặp lỗi lúc nạp file thì đứng lại trên một trang không
        còn đường nào về /kho-du-lieu — error.html không có liên kết của riêng
        nó, sidebar là lối ra duy nhất. Cùng lý lẽ với `_du_lieu_kho`: một chỗ
        dựng thì không bao giờ có hai chỗ trôi khỏi nhau.

        `_ve` KHÔNG chạm CSDL, nên trang này render được cả khi CSDL đang hỏng
        — điều kiện bắt buộc để middleware dùng nó (xem `chan_cua`).
        """
        _in(f"[KOME] lỗi khi {viec}:\n{traceback.format_exc()}")
        return _ve(request, "error.html", {"viec": viec, "trang": None},
                   status_code=500)

    def _chi_gui_qua_https(request: Request) -> bool:
        """Có gắn cờ Secure lên cookie không (cấm trình duyệt gửi qua HTTP)?

        Không chỉ đọc `request.url.scheme`: trên Vercel ứng dụng đứng sau một
        lớp proxy đã gỡ vỏ HTTPS trước khi tới đây, nên scheme có thể đọc ra
        "http" dù người dùng đang ở HTTPS — và cờ Secure sẽ âm thầm không được
        gắn. Đang chạy công khai thì chắc chắn là HTTPS, khẳng định thẳng.

        Ngược lại KHÔNG gắn cứng True: bản chạy ở máy dùng http://127.0.0.1,
        mà trình duyệt lặng lẽ vứt cookie Secure trên HTTP — đăng nhập xong
        vẫn bị đá về trang đăng nhập, không có thông báo nào giải thích.
        """
        return bao_mat.tren_mang() or request.url.scheme == "https"

    def _cam(request: Request) -> HTMLResponse:
        return _ve(request, "chi_doc.html", {"trang": None}, status_code=403)

    @app.get("/giao-dien")
    def doi_giao_dien(request: Request, che_do: str = "he-thong"):
        """Đổi chế độ sáng/tối/theo giờ, KHÔNG một dòng JS: lưu cookie rồi
        chuyển hướng về đúng trang đã gọi nút. Không chạm CSDL — chỉ đọc/ghi
        cookie, nên route này chạy được cả khi CSDL đang hỏng, cùng nếp với
        `_loi`/`_ve`.

        Giá trị lạ (gõ tay, hoặc một cookie/tham số từ bản trước) rơi về
        "he-thong" — KHÔNG được làm trang nổ, và cookie ghi ra CHỈ có thể là
        một trong bốn giá trị hợp lệ, không bao giờ chép nguyên văn tham số
        người dùng gửi lên.
        """
        if che_do not in CHE_DO_GIAO_DIEN_HOP_LE:
            che_do = "he-thong"

        # Chỉ chuyển hướng về ĐƯỜNG DẪN NỘI BỘ. Referer là dữ liệu người
        # dùng gửi lên (qua trình duyệt), KHÔNG phải thứ đáng tin — nhận
        # nguyên nó rồi RedirectResponse thẳng là mở một cửa chuyển hướng ra
        # ngoài: `/giao-dien?che_do=sang` kèm Referer giả từ một trang khác
        # sẽ đẩy người bấm sang nơi khác. Chỉ giữ PATH + QUERY (bỏ scheme/
        # host) rồi lọc lại bằng ĐÚNG hàm bao_mat.duong_dan_an_toan đã dùng
        # cho `?tiep=` sau đăng nhập — không viết một bộ lọc đường dẫn thứ
        # hai. An toàn nằm ở chỗ bỏ scheme+netloc (domain thật của Referer
        # không quan trọng — dù nó là trang của ai, ta chỉ tự chuyển hướng
        # NGAY TRÊN máy chủ KOME, chưa bao giờ nhảy sang máy chủ khác),
        # KHÔNG nằm ở chỗ bỏ query: đích đã là đường dẫn tương đối rồi, nên
        # giữ nguyên query không mở thêm cửa nào cả — mà bỏ nó thì người
        # đang lọc `/khach-hang?tinh=...&nv=...` bấm "Tối" xong mất sạch bộ
        # lọc, phải lọc lại từ đầu (vòng soát 1, mục 1).
        thamchieu = request.headers.get("referer")
        duong_thamchieu = None
        if thamchieu:
            r = urlparse(thamchieu)
            duong_thamchieu = r.path + (f"?{r.query}" if r.query else "")
        dich = bao_mat.duong_dan_an_toan(duong_thamchieu)

        resp = RedirectResponse(dich, status_code=303)
        resp.set_cookie(
            TEN_COOKIE_GIAO_DIEN, che_do, max_age=HAN_COOKIE_GIAO_DIEN_GIAY,
            samesite="lax", secure=_chi_gui_qua_https(request))
        return resp

    # ---- Cổng đăng nhập -------------------------------------------------
    # Dùng middleware chứ không phải dependency trên từng route: route nào
    # thêm về sau cũng tự động được che. Quên gắn dependency cho một route
    # mới là để hở đúng cái nó hiển thị, mà không có gì báo.
    if bi_mat:
        @app.middleware("http")
        async def chan_cua(request: Request, call_next):
            # Miễn trừ /static/ CÓ CHỦ Ý — đây là một lỗ thủng trong cổng bảo
            # mật, không phải sót. /static/ chỉ chứa kome.css và font: tài sản
            # thiết kế thuần tuý, không một byte dữ liệu kinh doanh nào đi qua
            # đường này. Thiếu dòng này thì CHÍNH trang đăng nhập — màn hình
            # ĐẦU TIÊN của bản Vercel — bị 303 mất cả CSS lẫn font. Có test
            # canh: tests/test_bao_mat.py::
            # test_static_khong_bi_chan_boi_cong_dang_nhap.
            if (request.url.path == "/dang-nhap"
                    or request.url.path.startswith("/static/")
                    or request.url.path.startswith("/assets/")):
                return await call_next(request)

            # Vé chỉ mang ID. Mọi thứ khác (còn tài khoản không, quyền gì) tra
            # CSDL MỖI LƯỢT — vé sống 12 giờ, mà người nghỉ việc thì phải bị
            # chặn ngay hôm nay, không phải 12 giờ nữa.
            ma = bao_mat.doc_ve(request.cookies.get(bao_mat.TEN_COOKIE), bi_mat)
            nguoi = None
            if ma is not None:
                try:
                    with open_app_conn() as c:
                        nguoi = ND.theo_id(c, ma)
                except Exception as e:
                    # Middleware tra CSDL ở MỌI lượt gọi, nên một lần Supabase
                    # trục trặc ở đây biến MỌI trang thành 500 trần của
                    # Starlette — đúng thứ `_loi` sinh ra để tránh. Trước đợt 3
                    # cổng là HMAC thuần, không chạm CSDL, nên lưới bắt lỗi
                    # từng đủ; giờ thì không.
                    #
                    # KHÔNG coi lỗi CSDL là "chưa đăng nhập": đá về /dang-nhap
                    # thì trang đăng nhập cũng tra CSDL và cũng hỏng, người
                    # dùng chỉ thấy một vòng lặp không lời giải thích.
                    return _loi(request, "kiểm tra phiên đăng nhập", e)
            if nguoi is None and request.url.path.startswith("/api/"):
                # Giao diện React tự chuyển về /dang-nhap khi thấy 401 — một
                # 303 ở đây thì fetch() lặng lẽ đi theo và nhận về HTML.
                return JSONResponse({"loi": "Chưa đăng nhập."}, status_code=401)
            if nguoi is None:
                resp = RedirectResponse("/dang-nhap", status_code=303)
                # Nhớ nơi người ta định đến để đăng nhập xong quay lại đúng
                # chỗ, nhưng chỉ nhớ trong cookie tạm — không đưa vào địa chỉ,
                # vì địa chỉ thì lộ ra lịch sử duyệt web và nhật ký máy chủ.
                #
                # CHỈ nhớ một lượt MỞ TRANG. Trình duyệt tự xin /favicon.ico
                # ngay khi hiện trang đăng nhập; nhớ cả nó là ghi đè nơi người
                # ta định đến, và đăng nhập xong bị đẩy tới {"detail":"Not
                # Found"} (lỗi thật trên Vercel, 2026-09-23). POST cũng không
                # nhớ: quay về một đường dẫn POST bằng GET là 405.
                la_mo_trang = (request.method == "GET"
                               and request.url.path != "/favicon.ico"
                               and request.headers.get("sec-fetch-dest",
                                                       "document") == "document")
                if la_mo_trang:
                    tiep = request.url.path
                    if request.url.query:
                        tiep += "?" + request.url.query
                    resp.set_cookie("kome_tiep", tiep, max_age=600, httponly=True,
                                    samesite="lax", secure=_chi_gui_qua_https(request))
                return resp

            request.state.nguoi = nguoi
            if not nguoi.duoc_vao_kho_du_lieu and _thuoc_kho_du_lieu(request.url.path):
                # 403 kèm trang giải thích, KHÔNG chuyển hướng im lặng: người
                # gõ thẳng địa chỉ cần biết vì sao mình không vào được, không
                # phải tự hỏi trang có hỏng không.
                return _ve(request, "cam_kho_du_lieu.html",
                           {"trang": None}, status_code=403)
            if not nguoi.duoc_sua_ngan_sach and _thuoc_ngan_sach(request.url.path):
                # Chặn ở middleware nên nó chặn CẢ GET LẪN POST bằng một chỗ
                # duy nhất — không có đường nào cho một route mới quên gác.
                return _ve(request, "cam_ngan_sach.html",
                           {"trang": None}, status_code=403)
            return await call_next(request)

        @app.get("/dang-nhap", response_class=HTMLResponse)
        def form_dang_nhap(request: Request):
            return _ve(request, "dang_nhap.html", {"trang": None, "sai": False})

        @app.post("/dang-nhap")
        def nhan_dang_nhap(request: Request, ten: str = Form(""),
                           mat_khau: str = Form("")):
            # Cùng lý do với try/except của `chan_cua`: /dang-nhap được miễn
            # trừ khỏi middleware nên lưới bắt lỗi ở đó không với tới đây, mà
            # đây lại là màn hình ĐẦU TIÊN của bản công khai.
            try:
                with open_app_conn() as c:
                    nguoi = ND.kiem_tra(c, ten.strip(), mat_khau)
            except Exception as e:
                return _loi(request, "kiểm tra tên và mật khẩu", e)
            if nguoi is None:
                # MỘT thông báo duy nhất cho cả "sai tên" lẫn "sai mật khẩu":
                # nói rõ cái nào sai là xác nhận giúp người ngoài rằng tên đó
                # CÓ TỒN TẠI trong công ty.
                return _ve(request, "dang_nhap.html",
                           {"trang": None, "sai": True}, status_code=401)
            resp = RedirectResponse(
                bao_mat.duong_dan_an_toan(request.cookies.get("kome_tiep")),
                status_code=303)
            resp.set_cookie(
                bao_mat.TEN_COOKIE, bao_mat.tao_ve_cho(nguoi.id, bi_mat),
                max_age=bao_mat.HAN_PHIEN_GIAY, httponly=True, samesite="lax",
                secure=_chi_gui_qua_https(request))
            resp.delete_cookie("kome_tiep")
            return resp

        @app.post("/dang-xuat")
        def dang_xuat():
            resp = RedirectResponse("/dang-nhap", status_code=303)
            resp.delete_cookie(bao_mat.TEN_COOKIE)
            return resp

    app.include_router(tao_api(open_app_conn))

    def _khoi_dau(request: Request) -> dict:
        """Những gì giao diện React cần để vẽ khung NGAY, không chờ /api."""
        nguoi = getattr(request.state, "nguoi", None)
        che_do = _che_do_giao_dien(request)
        return {
            "nguoi": None if nguoi is None else {
                "id": nguoi.id, "ten_dang_nhap": nguoi.ten_dang_nhap,
                "sale": nguoi.salesperson_code, "ten_sale": nguoi.ten_sale,
                "duoc_vao_kho_du_lieu": nguoi.duoc_vao_kho_du_lieu,
                "duoc_sua_ngan_sach": nguoi.duoc_sua_ngan_sach,
                "duoc_quan_tri": nguoi.duoc_quan_tri},
            "co_dang_nhap": bool(bi_mat), "chi_doc": chi_doc,
            "hien_kho": nguoi is None or nguoi.duoc_vao_kho_du_lieu,
            "hien_ngan_sach": nguoi is None or nguoi.duoc_sua_ngan_sach,
            "che_do_giao_dien": che_do,
            "bo_cuc": [o.dict() for o in BC.chuan_hoa(nguoi.bo_cuc if nguoi else None)],
            "sap_xep_duoc": nguoi is not None,
            "danh_muc": BC.danh_muc(),
            "chua_co": KTQ_CHUA_CO,
        }

    def _spa(request: Request, tuoi: bool = False) -> HTMLResponse:
        kd = _khoi_dau(request)
        if tuoi:
            # Ô "hôm nay đã có dữ liệu chưa" (kome/tuoi_du_lieu.py) — ĐỒNG HỒ
            # THẬT (ngoại lệ của bất biến mốc thời gian), nên KHÔNG qua ảnh
            # chụp. Chèn sẵn để nó hiện NGAY, TRÊN mọi con số, như bản Jinja.
            try:
                with open_app_conn() as conn:
                    t = tinh_tuoi(conn)
                kd["tuoi"] = {"hom_nay": t.hom_nay, "co_thieu": t.co_thieu,
                              "nguon": [{"spec": n.spec, "ten": n.ten, "ngay": n.ngay,
                                         "trang_thai": n.trang_thai, "tre": n.tre} for n in t.nguon]}
            except Exception:
                traceback.print_exc()
                kd["tuoi"] = None
        return HTMLResponse(SPA.trang(_data_theme(_che_do_giao_dien(request)), kd))

    # ---- Các trang ------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def trang_chu(request: Request, tat_ca: int = 0):
        """Trang chủ dùng chung: công ty đang thế nào, và hôm nay cần làm gì.

        Đợt 5b Task 5: `/` không còn gọi `tinh_bao_cao` (5 lượt hỏi chỉ để
        lấy ba con số của KỲ KẾ TOÁN) — mọi khối giờ qua
        `kome.tong_quan.tong_quan()`, đọc `mart.thang_den_hom_nay` (tháng
        đến hôm nay). `sale` dùng lại đúng `_sale_dang_loc` (mặc định tiện
        dụng theo người đăng nhập, `?tat_ca=1` bỏ lọc — cùng nếp
        `/can-xu-ly`), CHỈ áp cho khối "Cần gọi hôm nay"; các khối số tổng
        (tháng, xu hướng, sức khoẻ, ngân sách, hàng cận hạn) không lọc theo
        sale — xem docstring `kome.tong_quan.tong_quan`.
        """
        if not SPA.co_ban_build():
            return _loi(request, "mở trang tổng quan",
                        RuntimeError("Thiếu bản build giao diện (kome/web/spa/index.html). "
                                     "Chạy: cd giao_dien && npm run build"))
        return _spa(request, tuoi=True)

    @app.post("/tong-quan/bo-cuc")
    async def luu_bo_cuc(request: Request):
        """Lưu bố cục trang Tổng quan của người đang đăng nhập — tong_quan.js
        gửi sau mỗi lần kéo/đổi cỡ/ẩn/hiện. Chỉ nhận JSON; mọi giá trị đi qua
        `BC.chuan_hoa` (chỉ mã khối đã biết, kích thước kẹp trong dải), nên
        thứ ghi xuống luôn là một bố cục hợp lệ, dù gửi lên là gì.

        Không bị `_chi_doc` chặn — cùng lý lẽ `POST /ngan-sach` (CLAUDE.md):
        chế độ chỉ-đọc là giới hạn của luồng NẠP OBC, không phải phân quyền,
        và một mảng vài trăm byte vào app.nguoi_dung nằm thừa trong giới hạn."""
        nguoi = getattr(request.state, "nguoi", None)
        if nguoi is None:
            return JSONResponse({"loi": "Máy này chưa bật đăng nhập — không biết lưu bố cục cho ai."},
                                status_code=403)
        if not request.headers.get("content-type", "").startswith("application/json"):
            return JSONResponse({"loi": "Cần gửi JSON."}, status_code=415)
        than = await request.body()
        if len(than) > BC.DAI_TOI_DA:
            return JSONResponse({"loi": "Bố cục quá lớn."}, status_code=413)
        bo_cuc = BC.chuan_hoa(than)
        try:
            with open_app_conn() as conn:
                BC.luu(conn, nguoi.id, bo_cuc)
                conn.commit()
        except Exception:
            traceback.print_exc()
            return JSONResponse({"loi": "Không lưu được bố cục."}, status_code=500)
        return JSONResponse({"bo_cuc": [o.dict() for o in bo_cuc]})

    @app.post("/tong-quan/bo-cuc/mac-dinh")
    def bo_cuc_mac_dinh(request: Request):
        """Nút "Về bố cục mặc định" — một FORM thường, nên chạy được cả khi
        trình duyệt không chạy JavaScript."""
        nguoi = getattr(request.state, "nguoi", None)
        if nguoi is not None:
            try:
                with open_app_conn() as conn:
                    BC.luu(conn, nguoi.id, None)
                    conn.commit()
            except Exception as e:
                return _loi(request, "đưa bố cục về mặc định", e)
        return RedirectResponse("/", status_code=303)

    def _sale_dang_loc(request: Request, tat_ca: int,
                       nv: str = "") -> tuple[str | None, str | None]:
        """(mã sale, tên người) đang lọc, hoặc (None, None) nếu xem tất cả.

        Không có người đăng nhập (máy trong công ty không bật cổng) hoặc người
        đó không phụ trách khách nào (chủ DN, kế toán, kho) => KHÔNG lọc gì.
        Lọc theo NULL thì họ mở lên thấy danh sách rỗng và tưởng mất dữ liệu.

        `nv` là lựa chọn TƯỜNG MINH từ ô lọc "Người phụ trách" trên trang danh
        sách. Nó thắng cả mặc định theo người đăng nhập lẫn `tat_ca`: người ta
        vừa chọn một cái tên thì không có cách đọc nào khác. Tên đi kèm trả
        None vì ở đây chưa có CSDL trong tay — route tra tên từ
        `mart.tai_nhan_vien` (đã nằm sẵn trong `tong_quan_danh_ba`), không tốn
        thêm một vòng hỏi nào.

        `nv == KH.NV_MOI_NGUOI` là mục đầu của ô chọn — "mọi người phụ
        trách". Nó cũng là một lựa chọn TƯỜNG MINH, nên nó cũng thắng mặc
        định theo người đăng nhập. Không có giá trị quy ước này thì mục đó
        gửi `nv=""`, hàm rơi xuống nhánh mặc định và trả về đúng người đang
        đăng nhập — ô chọn khoe "mọi người" trong khi danh sách vẫn bị lọc.

        Vẫn KHÔNG phải hàng rào bảo mật: năm sale ai cũng biết khách của ai
        (đặc tả đợt 3 §5), nên chọn mã của người khác là hợp lệ.
        """
        if nv == KH.NV_MOI_NGUOI:
            return None, None
        if nv:
            return nv, None
        nguoi = getattr(request.state, "nguoi", None)
        if tat_ca or nguoi is None or not nguoi.salesperson_code:
            return None, None
        return nguoi.salesperson_code, nguoi.ten_sale or nguoi.ten_dang_nhap

    @app.get("/khach-hang", response_class=HTMLResponse)
    def ds_khach(request: Request, tim: str = "", loc: str = "",
                 sap: str = "doanh_thu", trang: int = 1, tat_ca: int = 0,
                 nhom: str = "", hang: str = "", tinh: str = "", nv: str = ""):
        try:
            sale, ten_sale = _sale_dang_loc(request, tat_ca, nv)
            with open_app_conn() as conn:
                # CÙNG một khối `with`, và tổng quan chạy TRƯỚC danh sách:
                # bảng "Tải của từng nhân viên" trong `tq` là chỗ duy nhất
                # biết mã sale nào ứng với tên nào, mà dải bộ lọc cần cái tên
                # đó để nói rõ đang xem khách của ai.
                tq = KH.tong_quan_danh_ba(conn, sale, nhom=nhom, hang=hang,
                                          tinh=tinh)
                # `sale and ten_sale is None` chứ không `nv and …`: chỉ có
                # nhánh `nv` là một mã sale (`KH.NV_MOI_NGUOI` không phải —
                # nó BỎ lọc, nên `sale` là None và không có tên nào để tra).
                if sale and ten_sale is None:
                    ten_sale = next((n["ten"] for n in tq.nhan_vien
                                     if n["ma"] == sale), sale)
                t = KH.danh_sach(conn, tim=tim, loc=loc, sap=sap, trang=trang,
                                 sale=sale, ten_sale=ten_sale, nhom=nhom,
                                 hang=hang, tinh=tinh)
            # Ô chọn Tỉnh: (giá trị trên URL, nhãn, số khách). Nhãn "(không
            # rõ)" do coalesce() sinh ra lúc hiển thị và KHÔNG nằm trong CSDL,
            # nên nó đi trên URL bằng giá trị quy ước KH.TINH_TRONG — đổ thẳng
            # nhãn ra `value` thì bấm vào nó luôn trả danh sách rỗng.
            tinh_chon = [(KH.TINH_TRONG if ten == KH.KHONG_RO else ten, ten, so)
                         for ten, so in tq.tinh]
            # Danh sách chỉ có 8 tỉnh đông nhất CỦA PHẠM VI ĐANG XEM, mà phạm
            # vi co theo sale/nv. Tỉnh đang lọc không nằm trong đó thì ô chọn
            # hiện "— mọi tỉnh —" trong khi danh sách vẫn đang bị lọc và mọi
            # liên kết vẫn mang `tinh=…`: ô điều khiển nói một đằng, dữ liệu
            # một nẻo, và bấm "Lọc" lần nữa là bộ lọc biến mất mà không ai
            # nhấn nút nào để xoá nó.
            if tinh and tinh not in [g for g, _, _ in tinh_chon]:
                tinh_chon.append(
                    (tinh, KH.KHONG_RO if tinh == KH.TINH_TRONG else tinh, None))
            # Ba bộ lọc mới đọc lại từ `t` (t.nhom/t.hang/t.tinh) chứ không
            # truyền thêm bản sao vào ctx: hai nguồn cho cùng một giá trị là
            # hai chỗ có thể trôi khỏi nhau. `nv` thì KHÔNG có trong `t` vì
            # nó không phải tham số của danh_sach() — nó đi qua `sale`.
            # Giá trị ĐANG được chọn của ô 担当者. Lấy từ `t.sale` (bộ lọc
            # THỰC SỰ đang áp dụng) chứ không từ `nv` (thứ người ta gõ trên
            # URL): mặc định của đợt 3 lọc theo người đăng nhập mà `nv` rỗng,
            # nên đọc `nv` thì ô chọn hiện "— mọi người phụ trách —" trong
            # khi danh sách chỉ có khách của một người. Không lọc ai thì rơi
            # về mục quy ước NV_MOI_NGUOI — chính là mục đầu.
            return _ve(request, "khach_hang.html",
                       {"t": t, "tq": tq, "trang_thai": KH.TRANG_THAI,
                        "trang": "khach", "tat_ca": bool(tat_ca), "nv": nv,
                        "nv_chon": t.sale or KH.NV_MOI_NGUOI,
                        "nv_moi_nguoi": KH.NV_MOI_NGUOI,
                        "tinh_chon": tinh_chon})
        except Exception as e:
            return _loi(request, "mở danh sách khách hàng", e)

    @app.get("/khach-hang/{ma}", response_class=HTMLResponse)
    def ho_so_khach(request: Request, ma: str, loi_tx: str = ""):
        try:
            with open_app_conn() as conn:
                h = KH.ho_so(conn, ma)
            if h is None:
                return _ve(request, "khong_thay.html",
                           {"thu": f"khách hàng mã {ma}", "trang": "khach"},
                           status_code=404)
            from kome import lien_he as LH
            return _ve(request, "khach_360.html",
                       {"h": h, "d": KH.ve_duong(h.thang), "trang": "khach",
                        "kieu_tx": LH.KIEU, "ket_qua_tx": LH.KET_QUA,
                        "hom_nay": TDL.hom_nay_o_nhat(), "loi_tx": loi_tx[:200]})
        except Exception as e:
            return _loi(request, "mở hồ sơ khách hàng", e)

    # /can-xu-ly (Giai đoạn 1) nay chỉ còn 301 về /lien-he (đợt 7): hai cột
    # "Lâu không mua" + "Quá hạn mua lại" của màn mới ĐÚNG là tập khách của
    # trang cũ (nhóm việc 'im'), cộng thêm dải "Sắp đến hạn" và nhật ký. Giữ
    # `tat_ca` để dấu trang "xem tất cả" cũ vẫn mở đúng phạm vi.
    @app.get("/can-xu-ly")
    def can_xu_ly(tat_ca: int = 0):
        return RedirectResponse("/lien-he?tat_ca=1" if tat_ca else "/lien-he",
                                status_code=301)

    # ---- Nhật ký thao tác (màn 20) + Cài đặt (màn 21) ---------------------
    @app.get("/nhat-ky", response_class=HTMLResponse)
    def nhat_ky(request: Request, loai: str = "", tim: str = ""):
        """Đọc gộp năm sổ đã có (kome/nhat_ky.py). ĐÚNG 2 lượt hỏi."""
        from kome import nhat_ky as NK
        try:
            loai = loai if loai in NK.LOAI else ""
            with open_app_conn() as conn:
                ds = NK.dong_thoi_gian(conn, loai or None, tim)
                th = NK.tong_hop_30_ngay(conn)
            return _ve(request, "nhat_ky.html", {
                "trang": "nhat-ky", "ds": ds, "th": th, "loai": loai, "tim": tim,
                "loai_ds": NK.LOAI, "gioi_han": 200})
        except Exception as e:
            return _loi(request, "mở nhật ký thao tác", e)

    @app.get("/nhat-ky.csv")
    def nhat_ky_csv(loai: str = "", tim: str = ""):
        from fastapi.responses import Response
        from kome import nhat_ky as NK
        loai = loai if loai in NK.LOAI else ""
        with open_app_conn() as conn:
            ds = NK.dong_thoi_gian(conn, loai or None, tim, gioi_han=100_000)
        return Response(NK.csv(ds), media_type="text/csv; charset=utf-8",
                        headers={"Content-Disposition": 'attachment; filename="nhat-ky-thao-tac.csv"'})

    # Nhãn cột quyền trên màn Cài đặt — thứ tự = ND.CO_QUYEN.
    _NHAN_CO = {"duoc_vao_kho_du_lieu": "Kho dữ liệu", "duoc_sua_ngan_sach": "Ngân sách",
                "duoc_quan_tri": "Quản trị"}
    _MUC_CAI_DAT = [
        ("nguoi-dung", "Người dùng & phân quyền", "ユーザー管理", "Ai đăng nhập được và ai được nạp/hoàn tác, sửa ngân sách, đổi quyền."),
        ("ngan-sach", "Ngân sách & ngày nghỉ", "予算設定", "Chỉ tiêu theo người và lịch ngày lễ dùng cho mọi phép tính tiến độ."),
        ("quy-tac", "Quy tắc khách hàng", "ランク管理", "Nhịp mua, im lặng, hạng theo doanh thu — định nghĩa trong mart."),
        ("nguon", "Nguồn dữ liệu & đồng bộ", "データ連携", "Các file OBC, nhịp nạp và cổng kiểm."),
        ("hien-thi", "Hiển thị", "表示設定", "Sáng/tối, đơn vị tiền, kỳ kế toán."),
    ]

    @app.get("/cai-dat", response_class=HTMLResponse)
    def cai_dat(request: Request, loi: str = "", xong: str = ""):
        """Xem được bởi mọi người đã đăng nhập; ĐỔI quyền chỉ người có
        duoc_quan_tri (kiểm ở POST). 2 lượt hỏi: danh sách tài khoản + ngày lễ."""
        nguoi = getattr(request.state, "nguoi", None)
        try:
            with open_app_conn() as conn:
                ds = ND.liet_ke(conn)
                ngay_le = conn.execute(
                    """SELECT ngay, ngay_le FROM mart.lich_kinh_doanh
                       WHERE ngay_le IS NOT NULL AND ngay >= %s ORDER BY ngay LIMIT 12""",
                    (TDL.hom_nay_o_nhat(),)).fetchall()
            return _ve(request, "cai_dat.html", {
                "trang": "cai-dat", "nguoi_dung": ds, "nguoi": nguoi, "ngay_le": ngay_le,
                "co_cong": bool(bi_mat), "duoc_sua": bool(bi_mat and nguoi and nguoi.duoc_quan_tri),
                "co_quyen": [(c, _NHAN_CO[c]) for c in ND.CO_QUYEN], "muc": _MUC_CAI_DAT,
                "loi": loi[:200], "xong": xong[:200]})
        except Exception as e:
            return _loi(request, "mở cài đặt", e)

    @app.post("/cai-dat/quyen/{id_nguoi}")
    async def doi_quyen(request: Request, id_nguoi: int):
        """Đổi ba cờ quyền của MỘT tài khoản. Bốn cổng, theo thứ tự:
        1. Không có cổng đăng nhập (máy chưa đặt KOME_SESSION_SECRET) → từ chối:
           ở đó cờ quyền không bảo vệ được gì, và không biết AI đang đổi.
        2. Người đổi không có duoc_quan_tri → 403.
        3. Tự bỏ quyền quản trị của CHÍNH MÌNH → từ chối: bấm nhầm một ô là
           công ty không còn ai đổi được quyền trên web nữa.
        4. Mỗi cờ đổi thật ghi một dòng app.nhat_ky_quyen (ND.dat_quyen)."""
        from urllib.parse import quote
        nguoi = getattr(request.state, "nguoi", None)
        if not bi_mat or nguoi is None:
            return RedirectResponse("/cai-dat?loi=" + quote(
                "Máy này chưa bật đăng nhập — không đổi quyền được ở đây."), status_code=303)
        if not nguoi.duoc_quan_tri:
            return _ve(request, "cam_cai_dat.html", {"trang": "cai-dat"}, status_code=403)
        form = await request.form()
        moi = {c: form.get(c) == "1" for c in ND.CO_QUYEN}
        try:
            with open_app_conn() as conn:
                dich = next((n for n in ND.liet_ke(conn) if n.id == id_nguoi), None)
                if dich is None:
                    return RedirectResponse("/cai-dat?loi=" + quote("Không có tài khoản đó."),
                                            status_code=303)
                if dich.id == nguoi.id and not moi["duoc_quan_tri"]:
                    return RedirectResponse("/cai-dat?loi=" + quote(
                        "Không tự bỏ quyền quản trị của chính mình — nhờ một người quản trị khác."),
                        status_code=303)
                ND.dat_quyen(conn, dich.ten_dang_nhap,
                             kho_du_lieu=moi["duoc_vao_kho_du_lieu"],
                             ngan_sach=moi["duoc_sua_ngan_sach"],
                             quan_tri=moi["duoc_quan_tri"], sua_boi=nguoi.id)
                conn.commit()
            return RedirectResponse("/cai-dat?xong=" + quote(
                f"Đã lưu quyền của {dich.ten_dang_nhap} — có hiệu lực ở lượt bấm kế tiếp của họ."),
                status_code=303)
        except Exception as e:
            return _loi(request, "đổi quyền", e)

    @app.get("/du-bao", response_class=HTMLResponse)
    def du_bao(request: Request, kb: str = "cs"):
        """Dự báo doanh thu (đợt 8). ĐÚNG 3 lượt hỏi — có test đếm. Toàn công
        ty, không lọc theo người đăng nhập (cùng nếp các khối số tổng của /)."""
        from kome import du_bao as DB
        from kome import ve_du_bao as VDB
        try:
            kb = kb if kb in DB.KICH_BAN else "cs"
            with open_app_conn() as conn:
                db = DB.du_bao(conn)
            ctx = {"trang": "du-bao", "db": db, "kb": kb, "kich_ban": DB.KICH_BAN}
            if db:
                ctx["ve_chot"] = VDB.ve_chot_thang(db.chot) if db.chot else {"co": False}
                ctx["ve_nam"] = VDB.ve_muoi_hai_thang(db.nam, kb)
            return _ve(request, "du_bao.html", ctx)
        except Exception as e:
            return _loi(request, "mở màn dự báo", e)

    @app.get("/lien-he", response_class=HTMLResponse)
    def lien_he(request: Request, tat_ca: int = 0, nv: str = "",
                ly_do: str = "", loi_tx: str = ""):
        """Danh sách ưu tiên liên hệ (đợt 7). ĐÚNG 3 lượt hỏi — có test đếm.
        Lọc theo người đăng nhập là mặc định tiện dụng, KHÔNG phải hàng rào
        (cùng nếp /khach-hang)."""
        from kome import lien_he as LH
        try:
            sale, ten_sale = _sale_dang_loc(request, tat_ca, nv)
            hom_nay = TDL.hom_nay_o_nhat()
            with open_app_conn() as conn:
                ds = LH.danh_sach(conn, hom_nay, sale=sale, ly_do=ly_do or None)
                hoat_dong = LH.hoat_dong_gan_day(conn, sale=sale)
                hen = LH.hen_goi_lai(conn, hom_nay, sale=sale)
            return _ve(request, "lien_he.html", {
                "trang": "lien-he", "ds": ds, "hoat_dong": hoat_dong, "hen": hen,
                "hom_nay": hom_nay, "sale": sale, "ten_sale": ten_sale,
                "tat_ca": bool(tat_ca), "nv": nv if nv != KH.NV_MOI_NGUOI else "",
                "an_ngay": LH.AN_KHI_KHONG_HEN, "kieu_tx": LH.KIEU,
                "ket_qua_tx": LH.KET_QUA, "loi_tx": loi_tx[:200],
                # Ghi xong quay về ĐÚNG trang này, kể cả bộ lọc đang xem.
                "tiep": request.url.path + (f"?{request.url.query}" if request.url.query else "")})
        except Exception as e:
            return _loi(request, "mở danh sách cần liên hệ", e)

    @app.post("/khach-hang/{ma}/tiep-xuc")
    def ghi_tiep_xuc(request: Request, ma: str, kieu: str = Form(""),
                     ket_qua: str = Form(""), noi_dung: str = Form(""),
                     hen_lai: str = Form(""), tiep: str = Form("")):
        """Thêm MỘT dòng app.nhat_ky_tiep_xuc bằng kết nối kome_app. KHÔNG bị
        chế độ chỉ-đọc chặn — cùng lý lẽ với POST /ngan-sach: `_chi_doc` tồn
        tại vì giới hạn của luồng NẠP OBC, còn một dòng chữ nằm thừa trong
        giới hạn đó, và bản Vercel là nơi cổng đăng nhập LUÔN bật.

        `tiep` lọc qua bao_mat.duong_dan_an_toan (bộ lọc DUY NHẤT của app) —
        một form lạ gửi `tiep=https://…` không biến nút Thêm thành bàn đạp."""
        from urllib.parse import quote
        from kome import lien_he as LH
        dich = bao_mat.duong_dan_an_toan(tiep or f"/khach-hang/{ma}#nhat-ky")
        nguoi = getattr(request.state, "nguoi", None)
        try:
            with open_app_conn() as conn:
                LH.ghi(conn, ma, nguoi.id if nguoi else None, kieu, ket_qua,
                       noi_dung, hen_lai)
                conn.commit()
        except LH.LoiNhap as e:
            duong, _, neo = dich.partition("#")
            noi = "&" if "?" in duong else "?"
            dich = f"{duong}{noi}loi_tx={quote(str(e))}" + (f"#{neo}" if neo else "")
        except Exception as e:
            return _loi(request, "ghi lần tiếp xúc", e)
        return RedirectResponse(dich, status_code=303)

    @app.get("/ban-do", response_class=HTMLResponse)
    def ban_do_khach_hang(request: Request, tat_ca: int = 0, nv: str = "",
                          chi_so: str = "khach"):
        """Bản đồ 47 tỉnh (đợt 4c). Ngân sách CẢ TRANG (không chỉ hàm
        BD.ban_do()) là 2 lượt hỏi — có test đếm lúc chạy
        (tests/test_ban_do.py::test_trang_ban_do_khong_qua_2_truy_van), nên
        route này KHÔNG được tự mở thêm một truy vấn nào (vd một danh sách
        tên đầy đủ của người phụ trách để đổ vào ô chọn — thứ /khach-hang có
        nhưng phải trả giá bằng một lượt hỏi riêng của tong_quan_danh_ba()).
        Vì vậy ô lọc bên dưới chỉ biết TÊN của người đang lọc khi đó là mặc
        định theo người đăng nhập (miễn phí, lấy từ session) — lọc sang một
        mã khác qua `?nv=` thì trang chỉ hiện lại đúng mã đó, không tra ra
        tên, giống hệt cách /can-xu-ly xử lý cùng ràng buộc.

        `sale`/`nv` cùng một nếp với /khach-hang: mặc định tiện dụng theo
        người đăng nhập, KHÔNG phải hàng rào bảo mật.
        """
        try:
            sale, ten_sale = _sale_dang_loc(request, tat_ca, nv)
            with open_app_conn() as conn:
                t = BD.ban_do(conn, sale=sale, chi_so=chi_so)
            return _ve(request, "ban_do.html",
                       {"t": t, "trang": "ban-do", "tat_ca": bool(tat_ca),
                        "nv": nv, "sale": sale, "ten_sale": ten_sale,
                        "nv_moi_nguoi": KH.NV_MOI_NGUOI, "chi_so_ds": BD.CHI_SO,
                        # Kích thước một ô lưới là HẰNG của kome/ban_do.py, không
                        # phải của template — truyền qua context để không viết
                        # cứng "60" lần thứ hai trong ban_do.html.
                        "o_rong": BD.O_RONG, "o_cao": BD.O_CAO})
        except Exception as e:
            return _loi(request, "mở bản đồ khách hàng", e)

    # ---- Hàng hoá: sản phẩm và kho hàng (đợt 4b) ------------------------
    # Cả ba route đều `open_app_conn` — chúng chỉ đọc. Có test duyệt AST canh
    # (tests/test_bao_mat.py::test_trang_chi_doc_khong_duoc_dung_ket_noi_nap_du_lieu).
    #
    # Mọi chỉ số nằm ở schema `mart` (migration 023) và mọi nhãn ở
    # kome/san_pham.py — ba route này chỉ lấy dữ liệu rồi giao cho template,
    # y hệt cặp route khách hàng ngay trên.

    @app.get("/san-pham", response_class=HTMLResponse)
    def ds_san_pham(request: Request, tim: str = "", loc: str = "",
                    sap: str = "doanh_thu", trang: int = 1):
        try:
            with open_app_conn() as conn:
                t = SP.danh_sach(conn, tim=tim, loc=loc, sap=sap, trang=trang)
            return _ve(request, "san_pham.html",
                       {"t": t, "trang_thai": SP.TRANG_THAI_TON,
                        "trang": "san-pham"})
        except Exception as e:
            return _loi(request, "mở danh sách sản phẩm", e)

    @app.get("/san-pham/{ma}", response_class=HTMLResponse)
    def ho_so_san_pham(request: Request, ma: str):
        try:
            with open_app_conn() as conn:
                h = SP.ho_so(conn, ma)
            if h is None:
                return _ve(request, "khong_thay.html",
                           {"thu": f"mã hàng {ma}", "trang": "san-pham",
                            "ve": "/san-pham", "ve_ten": "danh sách sản phẩm"},
                           status_code=404)
            # Mượn KH.ve_duong: nó chỉ TÍNH TOẠ ĐỘ từ cột `doanh_thu` của một
            # danh sách theo tháng — hình học thuần tuý, không một định nghĩa
            # chỉ số nào. Chép sang kome/san_pham.py là hai bản cùng công thức
            # sẽ trôi khỏi nhau, đúng lớp lỗi mà `_vi_tu` né ở tầng SQL.
            return _ve(request, "san_pham_360.html",
                       {"h": h, "d": KH.ve_duong(h.thang), "trang": "san-pham"})
        except Exception as e:
            return _loi(request, "mở hồ sơ sản phẩm", e)

    @app.get("/kho-hang", response_class=HTMLResponse)
    def man_kho_hang(request: Request, kho: str = "", loc: str = ""):
        try:
            with open_app_conn() as conn:
                k = SP.kho_hang(conn, kho=kho, loc=loc)
            # `can_han_ngay` đi ra template để tiêu đề khối và nhãn ô đếm đọc
            # CÙNG một hằng với truy vấn đã lọc (kome/san_pham.py::
            # CAN_HAN_NGAY). Viết cứng "90 ngày" vào HTML là để sẵn một ngày
            # ô đếm nói 60 còn tiêu đề vẫn nói 90.
            return _ve(request, "kho_hang.html",
                       {"k": k, "trang_thai": SP.TRANG_THAI_TON,
                        "can_han_ngay": SP.CAN_HAN_NGAY, "trang": "kho-hang"})
        except Exception as e:
            return _loi(request, "mở màn kho hàng", e)

    @app.post("/upload", response_class=HTMLResponse)
    def upload(request: Request, files: list[UploadFile]):
        if chi_doc:
            return _cam(request)
        try:
            from kome.pipeline import ingest
            results = []
            with open_conn() as conn:
                for f in files:
                    with tempfile.TemporaryDirectory() as tmp:
                        staged = Path(tmp) / f.filename
                        with staged.open("wb") as out:
                            shutil.copyfileobj(f.file, out)
                        results.append(ingest(conn, staged, archive_dir))
                _ghi_ai(conn, "nap_boi", [r.batch_id for r in results if r.batch_id],
                        getattr(request.state, "nguoi", None))
            if any(r.batch_id for r in results):
                anh_chup.lam_nong(open_app_conn)
            backup_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
            with open_conn() as conn:
                ctx = _du_lieu_kho(conn)
            ctx["backup"] = None if chi_doc else backup_status(backup_dir)
            return _ve(request, "kho_du_lieu.html",
                       {**ctx, "results": results, "trang": "kho-du-lieu", "tab": "van-hanh"})
        except Exception as e:
            return _loi(request, "nạp file dữ liệu", e)

    def _ghi_ai(conn, cot: str, batch_ids: list[int], nguoi) -> None:
        """Ghi AI nạp / AI hoàn tác vào meta.ingest_batch (033) cho Nhật ký
        thao tác. SAU khi ingest/undo đã commit, và nuốt mọi lỗi: đây là luồng
        13:30 — một lô đã nạp đúng không được trả về trang lỗi chỉ vì không
        ghi được tên người bấm (vd CSDL thật chưa chạy 033). Không có người
        (máy trong công ty chưa bật đăng nhập) thì không có gì để ghi."""
        if nguoi is None or not batch_ids:
            return
        assert cot in ("nap_boi", "huy_boi")
        try:
            conn.execute(f"UPDATE meta.ingest_batch SET {cot} = %s WHERE batch_id = ANY(%s)",
                         (nguoi.id, batch_ids))
            conn.commit()
        except Exception as e:
            conn.rollback()
            _in(f"[nhat-ky] không ghi được {cot} cho lô {batch_ids}: {e!r}")

    def _du_lieu_kho(conn):
        """Mọi thứ màn Kho dữ liệu cần, gom một chỗ.

        Route GET và route POST /upload đều render cùng màn này, nên cùng
        gọi hàm này — tách ra để hai chỗ không bao giờ trôi khỏi nhau.
        """
        return {"status": trang_thai_nap(conn),
                "ky": _ky_du_lieu(conn),
                "tuoi": tinh_tuoi(conn),
                "bang": tinh_bang_phu(conn),
                "bang_ngay": tinh_bang_ngay(conn),
                "lo": lo_nap_gan_nhat(conn)}

    @app.get("/kho-du-lieu", response_class=HTMLResponse)
    def kho_du_lieu(request: Request):
        try:
            # BACKUP_DIR đọc mỗi lần gọi, không chốt lúc tạo app — test và
            # người vận hành đổi biến môi trường thì trang phải thấy ngay.
            backup_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
            with open_conn() as conn:
                ctx = _du_lieu_kho(conn)
            # Bản chỉ-đọc KHÔNG nói gì về sao lưu: sao lưu chạy trên máy nội
            # bộ, máy chủ công khai không nhìn thấy thư mục .zip đó nên sẽ
            # luôn kết luận "chưa sao lưu" — một dải đỏ vĩnh viễn dạy người
            # đọc bỏ qua dải đỏ.
            ctx["backup"] = None if chi_doc else backup_status(backup_dir)
            return _ve(request, "kho_du_lieu.html",
                       {**ctx, "trang": "kho-du-lieu", "tab": "van-hanh"})
        except Exception as e:
            return _loi(request, "mở màn kho dữ liệu", e)

    # ---- Tài liệu sống (đợt 2b) -------------------------------------
    # 0 truy vấn: KHÔNG open_conn(). Nguồn là files.yml (lúc chạy) và ảnh
    # chụp kome/web/tai_lieu_sinh.json (sinh bởi scripts/sinh_tai_lieu.py) —
    # xem kome/tai_lieu.py. Nằm dưới tiền tố /kho-du-lieu/ nên middleware đã
    # gác bằng duoc_vao_kho_du_lieu, không cần ngoại lệ nào.
    @app.get("/kho-du-lieu/luong", response_class=HTMLResponse)
    def kho_du_lieu_luong(request: Request):
        from kome import tai_lieu as TL
        from kome.config import SPECS
        anh = TL.doc_anh_chup()
        return _ve(request, "kho_du_lieu_luong.html", {
            "trang": "kho-du-lieu", "tab": "luong", "md": TL.md_dong,
            "tang": TL.bon_tang(anh, SPECS), "nguon": TL.nguon_obc(SPECS, anh),
            "ranh_gioi": TL.ranh_gioi(anh),
            "chua_nap": TL.chua_nap(), "cong": TL.cong(anh),
            "nguong": TL.nguong(SPECS), "cam_bay": TL.cam_bay(anh),
            "lo_trinh": TL.lo_trinh(anh)})

    @app.get("/kho-du-lieu/cot-noi", response_class=HTMLResponse)
    def kho_du_lieu_cot_noi(request: Request, file: str | None = None):
        from kome import tai_lieu as TL
        from kome.config import SPECS
        ten = TL.chon_file(SPECS, file)
        return _ve(request, "kho_du_lieu_cot_noi.html", {
            "trang": "kho-du-lieu", "tab": "cot-noi", "file": ten,
            "file_ja": SPECS[ten].display_name, "core_table": SPECS[ten].core_table,
            "nguon": TL.nguon_obc(SPECS), "ma_tran": TL.ma_tran(SPECS),
            "noi": TL.noi_di_dau(SPECS, ten), "so_do": TL.so_do_noi(SPECS, ten),
            "dong_so_do": TL.DONG_SO_DO, "cot": TL.cot_cua(SPECS, ten)})

    # Ba địa chỉ cũ -> màn gộp. 301 chứ không 302: chúng biến mất vĩnh viễn,
    # và 301 cho trình duyệt cập nhật dấu trang. Neo để người bấm dấu trang cũ
    # rơi đúng khối họ vẫn mở, không phải cuộn đi tìm.
    #
    # /nap VẪN chuyển hướng ở bản chỉ-đọc, không trả 403: màn đích tự ẩn khối
    # nạp, còn 403 cho một dấu trang cũ là phạt người dùng vì một thay đổi họ
    # không gây ra.
    #
    # Viết ba hàm rời chứ không một vòng lặp sinh route: ba dòng lặp lại đọc
    # thẳng hơn một closure sinh hàm, và repo này chọn "không ma thuật" (R2).

    @app.get("/nap", include_in_schema=False)
    def _cu_nap():
        return RedirectResponse("/kho-du-lieu#nap", status_code=301)

    @app.get("/health", include_in_schema=False)
    def _cu_health():
        return RedirectResponse("/kho-du-lieu", status_code=301)

    @app.get("/phu-du-lieu", include_in_schema=False)
    def _cu_phu_du_lieu():
        return RedirectResponse("/kho-du-lieu#theo-thang", status_code=301)

    @app.get("/bao-cao", response_class=HTMLResponse)
    def bao_cao(request: Request, ky: int | None = None):
        """Bảng điều khiển bán hàng. `?ky=` là company_fy (năm KẾT THÚC kỳ),
        bỏ trống thì lấy kỳ gần nhất có dữ liệu.

        Mọi định nghĩa chỉ số nằm ở schema `mart` (migration 014 và 026) —
        trang này chỉ hiển thị. Xem ghi chú đầu kome/bao_cao.py.
        """
        try:
            with open_app_conn() as conn:
                bc = tinh_bao_cao(conn, ky)
                td = tien_do_ngan_sach(conn, ky)
            # [Đợt 5b Task 4] Bảy khối phân tích mới (spec §5) — mọi hình học
            # tính sẵn ở kome/ve_phan_tich.py, route chỉ gọi và truyền vào
            # template, không tính chỉ số nào ở đây.
            nhom = nhom_theo_nganh(bc.nganh_ky, bc.hang_theo_nganh)
            thang_ky = thang_cua_ky(bc.ky.company_fy)
            # [Vòng soát 1, I-1] Ranh giới "tháng chưa tới" của bản đồ nhiệt —
            # LẤY TỪ `bc.ky.ngay_cuoi` đã có sẵn (ngày bán mới nhất của CHÍNH
            # kỳ đang xem), không hỏi CSDL thêm câu nào. None khi kho rỗng.
            thang_cuoi = (bc.ky.ngay_cuoi.strftime("%Y-%m")
                          if bc.ky.ngay_cuoi else None)
            # [Vòng soát cuối, I-2] Tháng công ty có dòng bán ĐẦU TIÊN —
            # `bc.moi_ky[0]` là kỳ SỚM NHẤT (dong_ky đã ORDER BY company_fy ở
            # tinh_bao_cao()), lấy sẵn từ `bc`, KHÔNG hỏi CSDL thêm câu nào.
            # Chặn ve_nhiet tô ¥0 cho các tháng TRƯỚC khi có dữ liệu (một
            # NULL≠0 khác đối tượng nhưng cùng lớp lỗi với `san_pham_360.ton`
            # đã ghi ở CLAUDE.md).
            thang_dau = (bc.moi_ky[0].ngay_dau.strftime("%Y-%m")
                         if bc.moi_ky and bc.moi_ky[0].ngay_dau else None)
            so_nho = {
                "dt": ve_duong_nho([o.doanh_thu for o in bc.thang]),
                "lg": ve_duong_nho([o.lai_gop for o in bc.thang]),
                "ts": ve_duong_nho([o.ty_suat for o in bc.thang]),
                "kh": ve_duong_nho([o.so_khach for o in bc.thang]),
            }
            return _ve(request, "bao_cao.html",
                       {"bc": bc, "bd": ve_bieu_do(bc.thang), "td": td,
                        "lk": ve_luy_ke(td), "trang": "bao-cao",
                        "so_nho": so_nho,
                        "dg": ve_dong_gop(bc.nganh_ky),
                        "co": ve_cay_o(nhom),
                        "nh": ve_nhiet(bc.nganh_thang, thang_ky, thang_cuoi, thang_dau),
                        "pa": ve_pareto(bc.tap_trung)})
        except Exception as e:
            return _loi(request, "mở trang báo cáo", e)

    def _ngu_canh_ngan_sach(b) -> dict:
        """Đổi khoá bộ đôi sang khoá chuỗi cho Jinja, và cộng sẵn hai chiều
        tổng.

        `BangNhap.o` dùng khoá `(mã, tháng)` vì đó là khoá đúng ở tầng Python.
        Template thì tra bằng chính tên ô của biểu mẫu (`o-0104-2026-05`), nên
        đổi một lần ở đây thay vì để Jinja dựng lại bộ đôi ở mỗi trong 60 ô.

        Hai bảng tổng cộng từ `b.o` đã nằm sẵn trong bộ nhớ — KHÔNG thêm truy
        vấn nào. Ô chưa đặt không có mặt trong `b.o` nên nó không cộng vào
        tổng, đúng như phải thế: "chưa đặt" không phải "bằng không".

        `co_nguoi`/`co_thang`/`co_bat_ky` (vòng sửa 1): CÓ ít nhất một ô đã
        đặt cho hàng/cột/toàn bảng đó không. `sum()` trên một dải TRỐNG trả
        `0`, và một dải TỔNG in thẳng `¥0` cho "chưa đặt gì" là trang tự mâu
        thuẫn với chính dòng ghi chú "ô trống nghĩa là chưa đặt chỉ tiêu,
        khác với đặt bằng không" ngay phía trên nó. Ba cờ này để template
        chọn in `—` thay vì `¥0` khi không có ô nào đứng sau con số đó.
        """
        return {
            "b": b,
            "o_txt": {f"{ma}-{th}": v for (ma, th), v in b.o.items()},
            "tong_nguoi": {n.ma: sum(v for (m, _), v in b.o.items() if m == n.ma)
                           for n in b.nguoi},
            "tong_thang": {th: sum(v for (_, t), v in b.o.items() if t == th)
                           for th in b.thang},
            "co_nguoi": {n.ma: any(m == n.ma for m, _ in b.o) for n in b.nguoi},
            "co_thang": {th: any(t == th for _, t in b.o) for th in b.thang},
            "co_bat_ky": bool(b.o),
        }

    @app.get("/ngan-sach", response_class=HTMLResponse)
    def ngan_sach(request: Request, ky: int | None = None):
        """Bảng nhập chỉ tiêu: 5 người phụ trách × 12 tháng của một kỳ.

        Cổng quyền nằm ở middleware (`_thuoc_ngan_sach`), không ở đây — một
        chỗ gác cho cả GET lẫn POST.
        """
        from kome.ngan_sach import bang_nhap
        try:
            with open_app_conn() as conn:
                b = bang_nhap(conn, ky)
            return _ve(request, "ngan_sach.html",
                       {**_ngu_canh_ngan_sach(b), "da_go": {}, "loi": [],
                        "trang": "ngan-sach"})
        except Exception as e:
            return _loi(request, "mở trang ngân sách", e)

    @app.post("/ngan-sach")
    async def luu_ngan_sach(request: Request):
        """Ghi cả biểu mẫu trong MỘT giao dịch.

        Một ô rác => KHÔNG ghi ô nào và hiện lại đúng những gì người ta vừa
        gõ. Ghi một nửa rồi báo lỗi là để người ta không biết nửa nào đã vào,
        và bắt gõ lại 60 ô vì một ô sai là cách chắc chắn để không ai dùng màn
        này lần thứ hai.

        Vòng sửa 1: `ky` và việc tách tên ô giờ nằm TRONG `try`. Trước đó
        `int(form.get("ky") or 0)` với `ky=abc`, hay `khoa.split("-", 1)`
        với một tên ô méo (`o-` không kèm gì, hay `o-abc`) ném ValueError
        NGOÀI mọi lưới bắt lỗi — ra thẳng "Internal Server Error" trần của
        Starlette trên đúng màn GHI. Một tên ô méo giờ vào thẳng `loi` như
        một ô rác — đúng bản chất của nó — thay vì làm nổ cả request; `ky`
        méo vẫn rơi vào `except Exception` bên dưới, ra trang lỗi tiếng Việt
        của `_loi` chứ không phải vết ngăn xếp tiếng Anh.
        """
        from kome.ngan_sach import LoiSo, bang_nhap, doc_so, luu
        form = await request.form()
        nguoi = getattr(request.state, "nguoi", None)
        try:
            ky = int(form.get("ky") or 0) or None
            da_go = {k[2:]: str(v) for k, v in form.items() if k.startswith("o-")}

            gia_tri, loi = {}, []
            for khoa, chuoi in da_go.items():
                # rsplit chứ không split: mã (`*コード`) là TEXT không ràng
                # buộc định dạng, tự nó có thể mang dấu gạch ngang. `thang`
                # thì LUÔN đúng khuôn 'YYYY-MM' (hai nhóm số ở cuối), nên
                # tách từ PHẢI sang mới không lừa được. Tên ô không tách ra
                # đúng ba phần (kể cả rỗng, hay chỉ một khúc chữ) là một ô
                # rác — vào `loi`, không phải một lỗi lập trình.
                phan = khoa.rsplit("-", 2)
                if len(phan) != 3:
                    loi.append(khoa)
                    continue
                ma, nam, thang_phan = phan
                thang = f"{nam}-{thang_phan}"
                try:
                    gia_tri[(ma, thang)] = doc_so(chuoi)
                except LoiSo:
                    loi.append(khoa)

            with open_app_conn() as conn:
                if loi:
                    b = bang_nhap(conn, ky)
                    return _ve(request, "ngan_sach.html",
                               {**_ngu_canh_ngan_sach(b), "da_go": da_go,
                                "loi": loi, "trang": "ngan-sach"},
                               status_code=400)
                luu(conn, gia_tri, nguoi.id if nguoi else None)
                conn.commit()
            # `?ky=` (chuỗi rỗng) KHÔNG phải `None` với FastAPI — nó là một
            # chuỗi không ép được sang `int`, tức 422 chứ không phải "bỏ
            # trống". Một trang lỗi khó hiểu ngay sau khi vừa lưu THÀNH CÔNG
            # làm người dùng tưởng mất dữ liệu.
            return RedirectResponse(
                f"/ngan-sach?ky={ky}" if ky else "/ngan-sach", status_code=303)
        except Exception as e:
            return _loi(request, "lưu ngân sách", e)

    @app.post("/undo/{batch_id}")
    def undo(request: Request, batch_id: int):
        if chi_doc:
            return _cam(request)
        try:
            from kome.pipeline import undo_batch
            with open_conn() as conn:
                undo_batch(conn, batch_id)
                _ghi_ai(conn, "huy_boi", [batch_id], getattr(request.state, "nguoi", None))
            anh_chup.lam_nong(open_app_conn)
            return RedirectResponse("/kho-du-lieu", status_code=303)
        except Exception as e:
            return _loi(request, "hoàn tác lần nạp dữ liệu", e)

    return app

app = create_app()
