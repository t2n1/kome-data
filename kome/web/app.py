# kome/web/app.py
import os, shutil, sys, tempfile, traceback
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
from fastapi import FastAPI, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from kome.coverage import tinh_bang_ngay, tinh_bang_phu
from kome import khach_hang as KH
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

def _json_man(o):
    """Dữ liệu một màn -> đối tượng chỉ gồm kiểu JSON (dataclass KÈM @property qua
    `api.thanh_json`; ngày -> ISO; Decimal -> số; kiểu lạ như Path -> chuỗi)."""
    import json
    from dataclasses import asdict, is_dataclass
    from datetime import date, datetime
    from decimal import Decimal
    from kome.web.api import thanh_json

    def mac_dinh(x):
        if isinstance(x, (date, datetime)):
            return x.isoformat()
        if isinstance(x, Decimal):
            return int(x) if x == x.to_integral_value() else float(x)
        if is_dataclass(x):
            return asdict(x)
        if isinstance(x, (set, frozenset, tuple)):
            return list(x)
        return str(x)
    return json.loads(json.dumps(thanh_json(o), default=mac_dinh, ensure_ascii=False))


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

# Giai đoạn 5 (2026-09-23): KHÔNG còn template Jinja nào. Mọi màn trả vỏ React
# (kome/web/spa/index.html); màn nào máy chủ tính sẵn dữ liệu (Kho dữ liệu, Nhật
# ký, Cài đặt, Ngân sách) chèn nó vào window.__KOME__.man — CÙNG câu truy vấn
# như bản Jinja trước, nên ngân sách lượt hỏi và cổng quyền không đổi. Biểu mẫu
# (nạp, hoàn tác, ngân sách, quyền, đăng nhập) vẫn là <form method="post"> thật.

# Cửa sổ soát ngày thiếu trên /kho-du-lieu (tính lùi từ ngày bán gần nhất).
SO_NGAY_SOAT = 30

# Mọi đường dẫn thuộc màn Kho dữ liệu — màn DUY NHẤT có nút xoá dữ liệu.
# Ba địa chỉ cũ ở cuối danh sách vẫn phải chặn dù chúng chỉ còn trả 301: để
# hở chúng là để người không có quyền dò ra cấu trúc màn bị cấm.
DUONG_KHO_DU_LIEU = ("/kho-du-lieu", "/api/kho-du-lieu", "/upload", "/undo",
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

    def _loi(request: Request, viec: str, exc: Exception) -> HTMLResponse:
        """Trang lỗi tiếng Việt cho mọi lỗi NGOÀI DỰ KIẾN.

        Công ty không có nhân sự IT: trang 500 mặc định của framework (tiếng
        Anh, đầy dấu vết ngăn xếp) làm người dùng tưởng mình bấm sai rồi thử
        lại — và đó chính là lúc lô mồ côi biến thành "đã nạp rồi, bỏ qua"
        màu xanh. Chuỗi ngoại lệ gốc CHỈ ghi ra nhật ký máy chủ, KHÔNG hiện
        lên trang.

        Vẽ trong khung React CHUNG (`_thong_bao`), nên thanh bên — lối ra duy
        nhất của trang lỗi — có mục Kho dữ liệu đúng theo cờ quyền của người
        đang xem (window.__KOME__.hien_kho), y như mọi màn khác: một chỗ dựng
        thì không bao giờ có hai chỗ trôi khỏi nhau.

        KHÔNG chạm CSDL, nên trang này render được cả khi CSDL đang hỏng —
        điều kiện bắt buộc để middleware dùng nó (xem `chan_cua`).
        """
        _in(f"[KOME] lỗi khi {viec}:\n{traceback.format_exc()}")
        return _thong_bao(request, {"loai": "loi", "viec": viec}, 500)

    def _thong_bao(request: Request, tb: dict, ma: int) -> HTMLResponse:
        """Trang thông báo (lỗi 500 / không có quyền 403 / bản chỉ-đọc 403) vẽ
        trong khung React (giao_dien/src/he_thong/ThongBao.tsx). Thiếu bản build
        thì một trang HTML trần tối thiểu — vẫn tiếng Việt, vẫn không có vết
        ngăn xếp."""
        if not SPA.co_ban_build():
            import html
            chu = {"loi": f"Hệ thống gặp lỗi khi {tb.get('viec', '')}",
                   "chi_doc": "Bản này chỉ để xem"}.get(tb["loai"], "Bạn không có quyền vào màn này")
            return HTMLResponse(
                '<!doctype html><html lang="vi"><meta charset="utf-8"><title>KOME</title>'
                f"<h1>{html.escape(chu)}</h1><p>Thiếu bản build giao diện — chạy "
                "<code>cd giao_dien &amp;&amp; npm run build</code>.</p></html>", status_code=ma)
        return _spa(request, thong_bao=tb, status_code=ma)

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
        return _thong_bao(request, {"loai": "chi_doc"}, 403)

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
                return _cam_quyen(request, "cam_kho_du_lieu")
            if not nguoi.duoc_sua_ngan_sach and _thuoc_ngan_sach(request.url.path):
                # Chặn ở middleware nên nó chặn CẢ GET LẪN POST bằng một chỗ
                # duy nhất — không có đường nào cho một route mới quên gác.
                return _cam_quyen(request, "cam_ngan_sach")
            return await call_next(request)

        def _cam_quyen(request: Request, loai: str):
            # /api/* nhận JSON (giao diện React đọc được), trang nhận khung React.
            if request.url.path.startswith("/api/"):
                return JSONResponse({"loi": "Bạn không có quyền xem mục này."}, status_code=403)
            return _thong_bao(request, {"loai": loai}, 403)

        @app.get("/dang-nhap", response_class=HTMLResponse)
        def form_dang_nhap(request: Request):
            return _spa(request)

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
                return _spa(request, dang_nhap_sai=True, status_code=401)
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

    def _spa(request: Request, tuoi: bool = False, man=None, thong_bao: dict | None = None,
             dang_nhap_sai: bool = False, status_code: int = 200) -> HTMLResponse:
        """Vỏ index.html + window.__KOME__. `man` = dữ liệu màn tính sẵn (giai
        đoạn 5), `thong_bao` = trang lỗi / không có quyền."""
        kd = _khoi_dau(request)
        if man is not None:
            kd["man"] = _json_man(man)
        if thong_bao is not None:
            kd["thong_bao"] = thong_bao
        if dang_nhap_sai:
            kd["dang_nhap_sai"] = True
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
        return HTMLResponse(SPA.trang(_data_theme(_che_do_giao_dien(request)), kd),
                            status_code=status_code)

    # ---- Các trang ------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def trang_chu(request: Request, tat_ca: int = 0):
        """Trang chủ dùng chung: công ty đang thế nào, và hôm nay cần làm gì.

        Đợt 5b Task 5: `/` không còn gọi `tinh_bao_cao` (5 lượt hỏi chỉ để
        lấy ba con số của KỲ KẾ TOÁN) — mọi khối giờ qua
        `kome.tong_quan.tong_quan()`, đọc `mart.thang_den_hom_nay` (tháng
        đến hôm nay). `sale` dùng lại đúng `api.sale_dang_loc` (mặc định tiện
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


    # Giai đoạn 2 (đặc tả 2026-09-23-giai-doan-2-khach-hang-design.md): màn
    # Khách hàng là ứng dụng React — danh sách, hồ sơ 360° và bản đồ (tab của
    # cùng màn). Dữ liệu qua /api/khach-hang/* và /api/ban-do (kome/web/api.py).
    # Mã khách lạ: trang vẫn 200 (vỏ React), API trả 404 và giao diện nói
    # "không có khách mã …".
    def _man_khach(request: Request) -> HTMLResponse:
        """Vỏ index.html của một màn React (tên giữ từ giai đoạn 2 — nay phục
        vụ mọi màn đã chuyển ngoài `/`)."""
        if not SPA.co_ban_build():
            return _loi(request, "mở màn này",
                        RuntimeError("Thiếu bản build giao diện (kome/web/spa/index.html). "
                                     "Chạy: cd giao_dien && npm run build"))
        return _spa(request)

    @app.get("/khach-hang", response_class=HTMLResponse)
    def ds_khach(request: Request):
        return _man_khach(request)

    @app.get("/khach-hang/{ma}", response_class=HTMLResponse)
    def ho_so_khach(request: Request, ma: str):
        return _man_khach(request)

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
            return _spa(request, man={
                "ds": ds, "th": th, "loai": loai, "tim": tim,
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
            return _spa(request, man={
                "nguoi_dung": ds, "ngay_le": ngay_le,
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
            return _thong_bao(request, {"loai": "cam_cai_dat"}, 403)
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

    # Giai đoạn 3: Dự báo, Cần liên hệ, Báo cáo là ứng dụng React — dữ liệu qua
    # /api/du-bao, /api/lien-he, /api/bao-cao (kome/web/api.py).
    @app.get("/du-bao", response_class=HTMLResponse)
    def du_bao(request: Request):
        return _man_khach(request)

    @app.get("/lien-he", response_class=HTMLResponse)
    def lien_he(request: Request):
        return _man_khach(request)

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
    def ban_do_khach_hang(request: Request):
        """Tab "Bản đồ" của màn Khách hàng (React). Ngân sách lượt hỏi của bản
        đồ (2) giờ nằm ở /api/ban-do — tests/test_ban_do.py đếm ở đó."""
        return _man_khach(request)

    # ---- Hàng hoá: sản phẩm và kho hàng (giai đoạn 4 — React) -------------
    # Ba địa chỉ trả vỏ React; dữ liệu qua /api/san-pham, /api/san-pham/{mã}
    # (+ /ngay) và /api/kho-hang (kome/web/api.py -> kome/san_pham.py — mọi chỉ
    # số vẫn ở mart, migration 023). Mã hàng lạ: vỏ 200, API trả 404 và giao
    # diện nói "không có mã hàng …".

    @app.get("/san-pham", response_class=HTMLResponse)
    def ds_san_pham(request: Request):
        return _man_khach(request)

    @app.get("/san-pham/{ma}", response_class=HTMLResponse)
    def ho_so_san_pham(request: Request, ma: str):
        return _man_khach(request)

    @app.get("/kho-hang", response_class=HTMLResponse)
    def man_kho_hang(request: Request):
        return _man_khach(request)

    # Công nợ & thu tiền (đợt 6) — dữ liệu qua /api/cong-no (kome/cong_no.py ->
    # mart.cong_no_*, migration 038).
    @app.get("/cong-no", response_class=HTMLResponse)
    def man_cong_no(request: Request):
        return _man_khach(request)

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
            with open_conn() as conn:
                ctx = _du_lieu_nap(conn)
            return _man_kho(request, {**ctx, "results": results})
        except Exception as e:
            return _loi(request, "nạp file dữ liệu", e)

    # ---- Nạp hai bước (đợt B, 2026-09-24) ------------------------------
    # Kiểm: chép file vào thư mục chờ + 5 cổng (pipeline.kiem, KHÔNG ghi CSDL).
    # Xác nhận: pipeline.ingest ĐẦY ĐỦ trên đúng file đó (5 cổng chạy lại).
    # Huỷ: xoá file chờ. Cả ba nằm dưới /upload → middleware gác bằng
    # duoc_vao_kho_du_lieu như POST /upload; bản chỉ-đọc từ chối cả ba.

    def _ket_kiem(conn, ma: str, duong: Path, o: str) -> dict:
        from kome.gates import TEN_CONG
        from kome.pipeline import identify, kiem
        from kome import gates as G, kho_du_lieu as KDL, nap_cho
        from kome.config import SPECS
        spec, _ = identify(duong)
        if o and spec is not None and spec.name not in KDL.O_CUA.get(o, {}).get("specs", []):
            # Thả nhầm ô: không kiểm tiếp — người thả đang nghĩ là một file khác.
            dich = KDL.O_CUA_SPEC.get(spec.name)
            from kome.pipeline import IngestResult
            kq = IngestResult(ok=False, spec_name=spec.name, blockers=[G.Blocker(
                1, f"File này là {spec.display_name} ({dich['nhan'] if dich else spec.name}), "
                   f"không phải ô {KDL.O_CUA[o]['nhan']} — thả vào đúng ô của nó.")])
        else:
            kq = kiem(conn, duong)
        conn.rollback()                  # kiem chỉ đọc; không để giao dịch đọc treo
        cho = kq.ok and not kq.skipped
        if not cho:
            nap_cho.xoa(archive_dir, ma)
        sp = SPECS.get(kq.spec_name) if kq.spec_name else None
        return {"ma": ma if cho else None, "ten_file": duong.name, "o": o, "spec_name": kq.spec_name,
                "ja": sp.display_name if sp else None, "bang": sp.core_table if sp else None,
                "ok": kq.ok, "skipped": kq.skipped, "row_count": kq.row_count, "total": kq.total,
                "co_tien": bool(sp and sp.total_column), "data_date": kq.data_date,
                "blockers": kq.blockers, "warnings": kq.warnings,
                "cong": KDL.dong_cong(kq, TEN_CONG)}

    @app.post("/upload/kiem", response_class=HTMLResponse)
    def upload_kiem(request: Request, files: list[UploadFile], o: str = Form("")):
        if chi_doc:
            return _cam(request)
        try:
            from kome import nap_cho
            nap_cho.don_cu(archive_dir)
            ket = []
            with open_conn() as conn:
                for f in files:
                    ma, duong = nap_cho.luu(archive_dir, f.file, f.filename, o)
                    ket.append(_ket_kiem(conn, ma, duong, o))
                ctx = _du_lieu_nap(conn)
            return _man_kho(request, {**ctx, "kiem": ket})
        except Exception as e:
            return _loi(request, "kiểm file dữ liệu", e)

    @app.post("/upload/xac-nhan", response_class=HTMLResponse)
    def upload_xac_nhan(request: Request, ma: list[str] = Form([])):
        if chi_doc:
            return _cam(request)
        try:
            from kome import nap_cho
            from kome.pipeline import IngestResult, ingest
            from kome import gates as G
            results = []
            with open_conn() as conn:
                for m_ in ma:
                    x = nap_cho.doc(archive_dir, m_)
                    if x is None:
                        results.append(IngestResult(ok=False, blockers=[G.Blocker(
                            1, "File chờ không còn (đã xác nhận, đã huỷ, hay quá "
                               f"{nap_cho.GIU_GIO} giờ) — thả lại file để kiểm lại.")]))
                        continue
                    results.append(ingest(conn, x[0], archive_dir))
                    nap_cho.xoa(archive_dir, m_)
                _ghi_ai(conn, "nap_boi", [r.batch_id for r in results if r.batch_id],
                        getattr(request.state, "nguoi", None))
            if any(r.batch_id for r in results):
                anh_chup.lam_nong(open_app_conn)
            with open_conn() as conn:
                ctx = _du_lieu_nap(conn)
            return _man_kho(request, {**ctx, "results": results})
        except Exception as e:
            return _loi(request, "nạp file dữ liệu", e)

    @app.post("/upload/huy")
    def upload_huy(request: Request, ma: list[str] = Form([])):
        if chi_doc:
            return _cam(request)
        from kome import nap_cho
        for m_ in ma:
            nap_cho.xoa(archive_dir, m_)
        return RedirectResponse("/kho-du-lieu/nap", status_code=303)

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

    def _du_lieu_kho(conn, ngay_thang: str | None = None):
        """Mọi thứ màn Kho dữ liệu cần, gom một chỗ.

        Route GET và route POST /upload đều render cùng màn này, nên cùng
        gọi hàm này — tách ra để hai chỗ không bao giờ trôi khỏi nhau.
        """
        from kome import coverage as COV, kho_du_lieu as KDL
        tuoi = tinh_tuoi(conn)
        status = trang_thai_nap(conn)
        dau, cuoi, luoi = KDL.thang_luoi(ngay_thang, tuoi.hom_nay, COV.DAU_DU_LIEU)
        nguon = KDL.nut_nguon(status, tuoi, tuoi.hom_nay)
        # MỘT câu danh mục cho hai ô "Bảng trong kho" / "Tổng số dòng": reltuples
        # (ước tính của Postgres sau ANALYZE) — đếm thật count(*) từng bảng là
        # quét cả fact_sales_line mỗi lần mở màn.
        danh_muc = conn.execute(
            """SELECT n.nspname, c.relname, c.relkind::text, greatest(c.reltuples, 0)::bigint
               FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
               WHERE n.nspname IN ('core', 'mart', 'meta') AND c.relkind IN ('r', 'v', 'm')
               ORDER BY 1, 2""").fetchall()
        return {"man": "tong_quan", "status": status,
                "ky": _ky_du_lieu(conn),
                "tuoi": tuoi,
                "bang": tinh_bang_phu(conn),
                "bang_ngay": tinh_bang_ngay(conn, hom_nay=cuoi, so_ngay=(cuoi - dau).days + 1),
                "luoi": luoi, "nguon": nguon, "o_so": KDL.o_so(danh_muc, nguon)}

    def _du_lieu_nap(conn):
        """Màn Nạp: các ô nạp (cùng danh sách với sơ đồ nguồn), file đang chờ
        xác nhận, lô gần nhất + hoàn tác."""
        from kome import kho_du_lieu as KDL, nap_cho
        tuoi = tinh_tuoi(conn)
        nguon = KDL.nut_nguon(trang_thai_nap(conn), tuoi, tuoi.hom_nay)
        return {"man": "nap", "tuoi": tuoi, "nguon": nguon,
                "cho": [] if chi_doc else nap_cho.danh_sach(archive_dir),
                "lo": lo_nap_gan_nhat(conn)}

    def _man_kho(request: Request, ctx: dict) -> HTMLResponse:
        """Màn Kho dữ liệu React. Ô tuổi dữ liệu đi qua `window.__KOME__.tuoi`
        (cùng chỗ trang `/` đọc — một component DaiTuoi cho hai màn), lấy từ
        ĐÚNG lượt tính của `_du_lieu_kho` (không hỏi CSDL thêm). Ô bảng phủ bỏ
        bản chép `cot` trong từng ô — giao diện tra cột theo vị trí."""
        t = ctx.pop("tuoi")
        man = _json_man(ctx)
        # `BangPhu.database` (tên CSDL) CHỈ dành cho terminal — không bao giờ ra
        # trình duyệt (có test: không lộ thông tin kết nối).
        if "bang" in man:
            man["bang"].pop("database", None)
        for bang in ([*man["bang_ngay"]["ngay"], *[th for k in man["bang"]["ky"] for th in k["thang"]]]
                     if "bang" in man else []):
            for o in bang["o"]:
                o.pop("cot", None)
        kd = _khoi_dau(request)
        kd["man"] = man
        kd["tuoi"] = {"hom_nay": t.hom_nay, "co_thieu": t.co_thieu,
                      "nguon": [{"spec": n.spec, "ten": n.ten, "ngay": n.ngay,
                                 "trang_thai": n.trang_thai, "tre": n.tre} for n in t.nguon]}
        return HTMLResponse(SPA.trang(_data_theme(_che_do_giao_dien(request)), kd))

    @app.get("/kho-du-lieu/nap", response_class=HTMLResponse)
    def kho_du_lieu_nap(request: Request):
        try:
            with open_conn() as conn:
                ctx = _du_lieu_nap(conn)
            return _man_kho(request, ctx)
        except Exception as e:
            return _loi(request, "mở màn nạp dữ liệu", e)

    @app.get("/kho-du-lieu", response_class=HTMLResponse)
    def kho_du_lieu(request: Request, ngay_thang: str | None = None):
        try:
            # BACKUP_DIR đọc mỗi lần gọi, không chốt lúc tạo app — test và
            # người vận hành đổi biến môi trường thì trang phải thấy ngay.
            backup_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
            with open_conn() as conn:
                ctx = _du_lieu_kho(conn, ngay_thang)
            # Bản chỉ-đọc KHÔNG nói gì về sao lưu: sao lưu chạy trên máy nội
            # bộ, máy chủ công khai không nhìn thấy thư mục .zip đó nên sẽ
            # luôn kết luận "chưa sao lưu" — một dải đỏ vĩnh viễn dạy người
            # đọc bỏ qua dải đỏ.
            ctx["backup"] = None if chi_doc else backup_status(backup_dir)
            return _man_kho(request, ctx)
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
        return _spa(request, man={
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
        return _spa(request, man={
            "file": ten,
            "file_ja": SPECS[ten].display_name, "core_table": SPECS[ten].core_table,
            "nguon": TL.nguon_obc(SPECS), "ma_tran": TL.ma_tran(SPECS),
            "noi": TL.noi_di_dau(SPECS, ten), "so_do": TL.so_do_noi(SPECS, ten),
            "dong_so_do": TL.DONG_SO_DO, "cot": TL.cot_cua(SPECS, ten)})

    # Xem một bảng (đợt C): vỏ React, dữ liệu qua /api/kho-du-lieu/bang/{tên}.
    @app.get("/kho-du-lieu/bang/{ten}", response_class=HTMLResponse)
    def kho_du_lieu_bang(request: Request, ten: str):
        return _spa(request, man={"bang": ten})

    # "Dữ liệu đi đâu" (2026-09-24): cột OBC nào bỏ được ở lần xuất sau. 0 truy
    # vấn — ảnh chụp kome/web/cot_dung_sinh.json (scripts/sinh_cot_dung.py).
    @app.get("/kho-du-lieu/duong-di", response_class=HTMLResponse)
    def kho_du_lieu_duong_di(request: Request, file: str | None = None):
        from kome import cot_dung as CD
        return _spa(request, man=CD.man(file))

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
        return RedirectResponse("/kho-du-lieu/nap", status_code=301)

    @app.get("/health", include_in_schema=False)
    def _cu_health():
        return RedirectResponse("/kho-du-lieu", status_code=301)

    @app.get("/phu-du-lieu", include_in_schema=False)
    def _cu_phu_du_lieu():
        return RedirectResponse("/kho-du-lieu#theo-thang", status_code=301)

    @app.get("/bao-cao", response_class=HTMLResponse)
    def bao_cao(request: Request):
        return _man_khach(request)

    def _ngu_canh_ngan_sach(b) -> dict:
        """Dữ liệu màn Ngân sách cho giao diện React.

        `BangNhap.o` dùng khoá `(mã, tháng)` vì đó là khoá đúng ở tầng Python;
        JSON không có khoá bộ đôi nên đổi sang khoá chuỗi bằng CHÍNH tên ô của
        biểu mẫu (`0104-2026-05`, ô gửi lên là `o-0104-2026-05`). Ô chưa đặt
        KHÔNG có mặt — "chưa đặt" khác "bằng không", nên dải TỔNG (giao diện
        cộng từ `o_txt`) in "—" khi không ô nào đứng sau nó, chứ không in ¥0.
        KHÔNG thêm truy vấn nào.
        """
        # 041: khoá ô = `<đối tượng>-<chi_so>-<tháng>` (đối tượng = mã phụ trách hoặc
        # `CONG_TY`), đúng tên ô biểu mẫu `o-<khoá>`.
        from kome.ngan_sach import CONG_TY
        o = {f"{ma}-doanh_thu-{th}": v for (ma, th), v in b.o.items()}
        o.update({f"{ma}-lai_gop-{th}": v for (ma, th), v in b.o_lg.items()})
        o.update({f"{CONG_TY}-{cs}-{th}": v for (cs, th), v in b.cong_ty.items()})
        return {"ky": b.company_fy, "moi_ky": b.moi_ky, "thang": b.thang,
                "nguoi": [{"ma": n.ma, "ten": n.ten} for n in b.nguoi],
                "cong_ty": CONG_TY, "o_txt": o}

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
            return _spa(request, man={**_ngu_canh_ngan_sach(b), "da_go": {}, "loi": []})
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
        from kome.ngan_sach import CHI_SO, LoiSo, bang_nhap, doc_so, luu
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
                # 041: `<đối tượng>-<chi_so>-YYYY-MM`; tên ô cũ `<mã>-YYYY-MM` (không
                # có chi_so) = doanh thu của người đó.
                phan = khoa.rsplit("-", 3)
                if len(phan) == 4 and phan[1] in CHI_SO:
                    ma, chi_so, nam, thang_phan = phan
                else:
                    phan = khoa.rsplit("-", 2)
                    if len(phan) != 3:
                        loi.append(khoa)
                        continue
                    (ma, nam, thang_phan), chi_so = phan, "doanh_thu"
                if not ma:
                    loi.append(khoa)
                    continue
                thang = f"{nam}-{thang_phan}"
                try:
                    gia_tri[(ma, chi_so, thang)] = doc_so(chuoi)
                except LoiSo:
                    loi.append(khoa)

            with open_app_conn() as conn:
                if loi:
                    b = bang_nhap(conn, ky)
                    return _spa(request, man={**_ngu_canh_ngan_sach(b), "da_go": da_go,
                                              "loi": loi}, status_code=400)
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
            return RedirectResponse("/kho-du-lieu/nap#lo-nap", status_code=303)
        except Exception as e:
            return _loi(request, "hoàn tác lần nạp dữ liệu", e)

    return app

app = create_app()
