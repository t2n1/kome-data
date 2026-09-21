# kome/web/app.py
import os, shutil, tempfile, traceback
from datetime import timedelta
from pathlib import Path
from fastapi import FastAPI, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from kome.bao_cao import tinh_bao_cao, ve_bieu_do
from kome.coverage import tinh_bang_ngay, tinh_bang_phu
from kome import khach_hang as KH
from kome.db import connect
from kome.env import nap_env
from kome.nhat_ky_nap import lo_nap_gan_nhat, trang_thai_nap
from kome.tuoi_du_lieu import tinh_tuoi
from kome.web import bao_mat
from kome.web import nguoi_dung as ND
from ops.backup import backup_status

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

    Cuối tuần bỏ qua bằng core.dim_date.is_weekend. Ngày lễ Nhật KHÔNG có
    trong dim_date nên vẫn bị liệt kê — cảnh báo nhắc người đọc kiểm tra.
    """
    dau, cuoi = conn.execute(
        "SELECT min(sales_date), max(sales_date) FROM core.fact_sales_line"
    ).fetchone()
    if cuoi is None:
        return {"dau": None, "cuoi": None, "thieu": []}
    tu = max(dau, cuoi - timedelta(days=SO_NGAY_SOAT - 1))
    thieu = [
        r[0] for r in conn.execute(
            """SELECT d.date_key FROM core.dim_date d
               WHERE d.is_weekend = false
                 AND d.date_key BETWEEN %s AND %s
                 AND NOT EXISTS (SELECT 1 FROM core.fact_sales_line f
                                 WHERE f.sales_date = d.date_key)
               ORDER BY d.date_key""",
            (tu, cuoi),
        ).fetchall()
    ]
    return {"dau": dau, "cuoi": cuoi, "thieu": thieu, "tu": tu}


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
        print("[KOME] CẢNH BÁO: chưa đặt DATABASE_URL_APP — các trang chỉ đọc "
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
        return TEMPLATES.TemplateResponse(
            request, ten, {**ctx, **chung, "nguoi": nguoi, "hien_kho": hien_kho}, **kw)

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
        print(f"[KOME] lỗi khi {viec}:\n{traceback.format_exc()}")
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
                    or request.url.path.startswith("/static/")):
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
            if nguoi is None:
                tiep = request.url.path
                if request.url.query:
                    tiep += "?" + request.url.query
                resp = RedirectResponse("/dang-nhap", status_code=303)
                # Nhớ nơi người ta định đến để đăng nhập xong quay lại đúng
                # chỗ, nhưng chỉ nhớ trong cookie tạm — không đưa vào địa chỉ,
                # vì địa chỉ thì lộ ra lịch sử duyệt web và nhật ký máy chủ.
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

    # ---- Các trang ------------------------------------------------------
    @app.get("/", response_class=HTMLResponse)
    def tong_quan(request: Request):
        """Trang chủ: công ty đang thế nào, và hôm nay cần làm gì.

        TRƯỚC ĐÂY `/` là trang nạp dữ liệu. Đổi vì nạp dữ liệu là việc của MỘT
        người, MỘT lần mỗi ngày, còn `/` là thứ mọi người mở nhiều lần mỗi
        ngày. Khối nạp giờ nằm trong /kho-du-lieu (Đợt 2a, Task 1-4), và mục
        đó vẫn còn trong thanh điều hướng.
        """
        try:
            with open_app_conn() as conn:
                bc = tinh_bao_cao(conn)
                dem = dict(conn.execute(
                    "SELECT trang_thai, count(*) FROM mart.khach_360 GROUP BY 1"
                ).fetchall())
                so_ngay_ton = conn.execute(
                    "SELECT count(DISTINCT snapshot_date) FROM core.fact_inventory_daily"
                ).fetchone()[0]
                tuoi = tinh_tuoi(conn)
            return _ve(request, "tong_quan.html",
                       {"bc": bc, "dem": dem, "so_ngay_ton": so_ngay_ton,
                        "tuoi": tuoi, "trang": "tong-quan"})
        except Exception as e:
            return _loi(request, "mở trang tổng quan", e)

    def _sale_dang_loc(request: Request, tat_ca: int) -> tuple[str | None, str | None]:
        """(mã sale, tên người) đang lọc, hoặc (None, None) nếu xem tất cả.

        Không có người đăng nhập (máy trong công ty không bật cổng) hoặc người
        đó không phụ trách khách nào (chủ DN, kế toán, kho) => KHÔNG lọc gì.
        Lọc theo NULL thì họ mở lên thấy danh sách rỗng và tưởng mất dữ liệu.
        """
        nguoi = getattr(request.state, "nguoi", None)
        if tat_ca or nguoi is None or not nguoi.salesperson_code:
            return None, None
        return nguoi.salesperson_code, nguoi.ten_sale or nguoi.ten_dang_nhap

    @app.get("/khach-hang", response_class=HTMLResponse)
    def ds_khach(request: Request, tim: str = "", loc: str = "",
                 sap: str = "doanh_thu", trang: int = 1, tat_ca: int = 0):
        try:
            sale, ten_sale = _sale_dang_loc(request, tat_ca)
            with open_app_conn() as conn:
                t = KH.danh_sach(conn, tim=tim, loc=loc, sap=sap, trang=trang,
                                 sale=sale, ten_sale=ten_sale)
            return _ve(request, "khach_hang.html",
                       {"t": t, "trang_thai": KH.TRANG_THAI, "trang": "khach",
                        "tat_ca": bool(tat_ca)})
        except Exception as e:
            return _loi(request, "mở danh sách khách hàng", e)

    @app.get("/khach-hang/{ma}", response_class=HTMLResponse)
    def ho_so_khach(request: Request, ma: str):
        try:
            with open_app_conn() as conn:
                h = KH.ho_so(conn, ma)
            if h is None:
                return _ve(request, "khong_thay.html",
                           {"thu": f"khách hàng mã {ma}", "trang": "khach"},
                           status_code=404)
            return _ve(request, "khach_360.html",
                       {"h": h, "d": KH.ve_duong(h.thang), "trang": "khach"})
        except Exception as e:
            return _loi(request, "mở hồ sơ khách hàng", e)

    @app.get("/can-xu-ly", response_class=HTMLResponse)
    def can_xu_ly(request: Request, tat_ca: int = 0):
        try:
            sale, ten_sale = _sale_dang_loc(request, tat_ca)
            with open_app_conn() as conn:
                ds = KH.can_xu_ly(conn, sale=sale)
            return _ve(request, "can_xu_ly.html",
                       {"ds": ds, "trang": "can-xu-ly", "sale": sale,
                        "ten_sale": ten_sale})
        except Exception as e:
            return _loi(request, "mở danh sách cần xử lý", e)

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
            backup_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
            with open_conn() as conn:
                ctx = _du_lieu_kho(conn)
            ctx["backup"] = None if chi_doc else backup_status(backup_dir)
            return _ve(request, "kho_du_lieu.html",
                       {**ctx, "results": results, "trang": "kho-du-lieu"})
        except Exception as e:
            return _loi(request, "nạp file dữ liệu", e)

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
                       {**ctx, "trang": "kho-du-lieu"})
        except Exception as e:
            return _loi(request, "mở màn kho dữ liệu", e)

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

        Mọi định nghĩa chỉ số nằm ở schema `mart` (migration 014) — trang này
        chỉ hiển thị. Xem ghi chú đầu kome/bao_cao.py.
        """
        try:
            with open_app_conn() as conn:
                bc = tinh_bao_cao(conn, ky)
            return _ve(request, "bao_cao.html",
                       {"bc": bc, "bd": ve_bieu_do(bc.thang), "trang": "bao-cao"})
        except Exception as e:
            return _loi(request, "mở trang báo cáo", e)

    @app.post("/undo/{batch_id}")
    def undo(request: Request, batch_id: int):
        if chi_doc:
            return _cam(request)
        try:
            from kome.pipeline import undo_batch
            with open_conn() as conn:
                undo_batch(conn, batch_id)
            return RedirectResponse("/kho-du-lieu", status_code=303)
        except Exception as e:
            return _loi(request, "hoàn tác lần nạp dữ liệu", e)

    return app

app = create_app()
