# kome/web/app.py
import os, shutil, tempfile, traceback
from datetime import timedelta
from pathlib import Path
from fastapi import FastAPI, Form, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from kome.config import SPECS
from kome.bao_cao import tinh_bao_cao, ve_bieu_do
from kome.coverage import tinh_bang_ngay, tinh_bang_phu
from kome import khach_hang as KH
from kome.db import connect
from kome.env import nap_env
from kome.tuoi_du_lieu import tinh_tuoi
from kome.web import bao_mat
from ops.backup import backup_status

# Tự đọc .env khi chạy ở máy trong công ty. `uvicorn kome.web.app:app` khởi
# động trong môi trường trống, nên không có dòng này thì trang chạy lên bình
# thường rồi báo lỗi đỏ ở /health — người dùng đọc thành "hỏng CSDL" chứ
# không đọc ra "quên nạp biến môi trường".
# bat_buoc=False: trên Vercel KHÔNG có file .env (biến lấy từ bảng cấu hình),
# và biến môi trường đã có sẵn luôn được ưu tiên hơn file.
nap_env(bat_buoc=False)

# CỐ Ý không nhập kome.pipeline ở đây. pipeline kéo theo pandas +
# python-calamine (~120 MB) chỉ để ĐỌC file Excel — thứ mà bản chỉ-đọc trên
# Vercel không bao giờ làm. Hai hàm ingest/undo_batch được nhập bên trong thân
# route, nên chúng chỉ nạp khi thật sự có người nạp hoặc hoàn tác dữ liệu.

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Cửa sổ soát ngày thiếu trên /health (tính lùi từ ngày bán gần nhất).
SO_NGAY_SOAT = 30


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


def _loi(request: Request, viec: str, exc: Exception, chung: dict) -> HTMLResponse:
    """Trang lỗi tiếng Việt cho mọi lỗi NGOÀI DỰ KIẾN.

    Công ty không có nhân sự IT: trang 500 mặc định của framework (tiếng Anh,
    đầy dấu vết ngăn xếp) làm người dùng tưởng mình bấm sai rồi thử lại —
    và đó chính là lúc lô mồ côi biến thành "đã nạp rồi, bỏ qua" màu xanh.
    Chuỗi ngoại lệ gốc CHỈ ghi ra nhật ký máy chủ, KHÔNG hiện lên trang.
    """
    print(f"[KOME] lỗi khi {viec}:\n{traceback.format_exc()}")
    return TEMPLATES.TemplateResponse(
        request, "error.html", {"viec": viec, **chung}, status_code=500
    )


def _ky_du_lieu(conn) -> dict:
    """Kỳ dữ liệu bán hàng + các ngày LÀM VIỆC không có dòng nào.

    Không có gì khác trong hệ thống phát hiện thiếu hẳn một ngày: nhân viên
    nghỉ ốm, không ai kéo–thả, hôm sau nạp bình thường và /health xanh hết.
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


def create_app(db_url: str | None = None) -> FastAPI:
    """db_url=None => lấy DATABASE_URL. Test LUÔN truyền DATABASE_URL_TEST."""
    app = FastAPI(title="KOME — dữ liệu")
    archive_dir = Path(os.environ.get("ARCHIVE_DIR", "./raw_archive"))
    open_conn = lambda: connect(db_url)
    chi_doc = _chi_doc()

    mk = bao_mat.mat_khau()
    # Ném CauHinhSai ngay lúc dựng app, trước khi phục vụ dòng nào.
    bao_mat.kiem_cau_hinh(mk, cong_khai=bao_mat.tren_mang())

    # Biến mà MỌI trang đều cần để vẽ đúng thanh điều hướng. Gom vào một chỗ
    # để không trang nào bị sót: sót `chi_doc` thì trang đó vẫn mời người ta
    # bấm "Nạp dữ liệu" — một liên kết dẫn thẳng tới 403 trên bản công khai.
    chung = {"chi_doc": chi_doc, "co_mat_khau": bool(mk)}

    def _ve(request: Request, ten: str, ctx: dict, **kw) -> HTMLResponse:
        return TEMPLATES.TemplateResponse(request, ten, {**ctx, **chung}, **kw)

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
    if mk:
        @app.middleware("http")
        async def chan_cua(request: Request, call_next):
            if request.url.path == "/dang-nhap" or bao_mat.ve_hop_le(
                    request.cookies.get(bao_mat.TEN_COOKIE), mk):
                return await call_next(request)
            tiep = request.url.path
            if request.url.query:
                tiep += "?" + request.url.query
            resp = RedirectResponse("/dang-nhap", status_code=303)
            # Nhớ nơi người ta định đến để đăng nhập xong quay lại đúng chỗ,
            # nhưng chỉ nhớ trong cookie tạm — không đưa vào địa chỉ, vì địa
            # chỉ thì lộ ra lịch sử duyệt web và nhật ký máy chủ.
            resp.set_cookie("kome_tiep", tiep, max_age=600, httponly=True,
                            samesite="lax", secure=_chi_gui_qua_https(request))
            return resp

        @app.get("/dang-nhap", response_class=HTMLResponse)
        def form_dang_nhap(request: Request):
            return _ve(request, "dang_nhap.html", {"trang": None, "sai": False})

        @app.post("/dang-nhap")
        def nhan_dang_nhap(request: Request, mat_khau: str = Form("")):
            if not bao_mat.dung_mat_khau(mat_khau, mk):
                return _ve(request, "dang_nhap.html",
                           {"trang": None, "sai": True}, status_code=401)
            resp = RedirectResponse(
                bao_mat.duong_dan_an_toan(request.cookies.get("kome_tiep")),
                status_code=303)
            resp.set_cookie(
                bao_mat.TEN_COOKIE, bao_mat.tao_ve(mk),
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
        ngày. Trang nạp chuyển sang /nap và vẫn nằm trong thanh điều hướng.
        """
        try:
            with open_conn() as conn:
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
            return _loi(request, "mở trang tổng quan", e, chung)

    @app.get("/nap", response_class=HTMLResponse)
    def trang_nap(request: Request):
        if chi_doc:
            return _cam(request)
        try:
            return _ve(request, "upload.html", {"results": None, "trang": "nap"})
        except Exception as e:
            return _loi(request, "mở trang nạp dữ liệu", e, chung)

    @app.get("/khach-hang", response_class=HTMLResponse)
    def ds_khach(request: Request, tim: str = "", loc: str = "",
                 sap: str = "doanh_thu", trang: int = 1):
        try:
            with open_conn() as conn:
                t = KH.danh_sach(conn, tim=tim, loc=loc, sap=sap, trang=trang)
            return _ve(request, "khach_hang.html",
                       {"t": t, "trang_thai": KH.TRANG_THAI, "trang": "khach"})
        except Exception as e:
            return _loi(request, "mở danh sách khách hàng", e, chung)

    @app.get("/khach-hang/{ma}", response_class=HTMLResponse)
    def ho_so_khach(request: Request, ma: str):
        try:
            with open_conn() as conn:
                h = KH.ho_so(conn, ma)
            if h is None:
                return _ve(request, "khong_thay.html",
                           {"thu": f"khách hàng mã {ma}", "trang": "khach"},
                           status_code=404)
            return _ve(request, "khach_360.html",
                       {"h": h, "d": KH.ve_duong(h.thang), "trang": "khach"})
        except Exception as e:
            return _loi(request, "mở hồ sơ khách hàng", e, chung)

    @app.get("/can-xu-ly", response_class=HTMLResponse)
    def can_xu_ly(request: Request):
        try:
            with open_conn() as conn:
                ds = KH.can_xu_ly(conn)
            return _ve(request, "can_xu_ly.html", {"ds": ds, "trang": "can-xu-ly"})
        except Exception as e:
            return _loi(request, "mở danh sách cần xử lý", e, chung)

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
            return _ve(request, "upload.html", {"results": results, "trang": "nap"})
        except Exception as e:
            return _loi(request, "nạp file dữ liệu", e, chung)

    @app.get("/health", response_class=HTMLResponse)
    def health(request: Request):
        try:
            # BACKUP_DIR đọc mỗi lần gọi, không chốt lúc tạo app — test và
            # người vận hành đổi biến môi trường thì trang phải thấy ngay.
            backup_dir = Path(os.environ.get("BACKUP_DIR", "./backups"))
            with open_conn() as conn:
                # DISTINCT ON: lần nạp GẦN NHẤT của từng loại file.
                # max(loaded_at), max(row_count), max(total_amount) là ba hàm
                # độc lập lấy từ ba dòng khác nhau — sau một lần đối soát tháng
                # ~18.000 dòng thì trang LUÔN hiện 18.000, kể cả hôm nay OBC
                # xuất cắt cụt còn 60 dòng.
                rows = conn.execute(
                    """SELECT DISTINCT ON (spec_name)
                              spec_name, loaded_at, row_count, total_amount
                       FROM meta.ingest_batch WHERE undone_at IS NULL
                       ORDER BY spec_name, loaded_at DESC"""
                ).fetchall()
                ky = _ky_du_lieu(conn)
                tuoi = tinh_tuoi(conn)
            seen = {r[0]: r for r in rows}
            status = [
                {"name": s.display_name,
                 "last": seen[k][1] if k in seen else None,
                 "rows": seen[k][2] if k in seen else 0,
                 "total": seen[k][3] if k in seen else 0,
                 # File master / bảng giá KHÔNG mang giá trị tiền: total_column
                 # để trống CÓ CHỦ Ý (xem kome/config.py). Cột "Tổng tiền" phải
                 # hiện "—", không phải "¥0" — ¥0 làm người đọc tưởng hệ thống
                 # đếm hụt tiền và đi báo lỗi không tồn tại.
                 "co_tien": s.total_column is not None}
                for k, s in SPECS.items()
            ]
            # Bản chỉ-đọc KHÔNG nói gì về sao lưu. Sao lưu chạy trên máy nội
            # bộ, nơi có file .zip; máy chủ công khai không nhìn thấy thư mục
            # đó nên sẽ luôn kết luận "chưa sao lưu" — một dải đỏ vĩnh viễn
            # dạy người đọc bỏ qua dải đỏ, đúng thứ hệ thống này cần họ tin.
            backup = None if chi_doc else backup_status(backup_dir)
            return _ve(request, "health.html",
                       {"status": status, "backup": backup, "ky": ky,
                        "tuoi": tuoi, "trang": "suc-khoe"})
        except Exception as e:
            return _loi(request, "mở trang sức khoẻ dữ liệu", e, chung)

    @app.get("/bao-cao", response_class=HTMLResponse)
    def bao_cao(request: Request, ky: int | None = None):
        """Bảng điều khiển bán hàng. `?ky=` là company_fy (năm KẾT THÚC kỳ),
        bỏ trống thì lấy kỳ gần nhất có dữ liệu.

        Mọi định nghĩa chỉ số nằm ở schema `mart` (migration 014) — trang này
        chỉ hiển thị. Xem ghi chú đầu kome/bao_cao.py.
        """
        try:
            with open_conn() as conn:
                bc = tinh_bao_cao(conn, ky)
            return _ve(request, "bao_cao.html",
                       {"bc": bc, "bd": ve_bieu_do(bc.thang), "trang": "bao-cao"})
        except Exception as e:
            return _loi(request, "mở trang báo cáo", e, chung)

    @app.get("/phu-du-lieu", response_class=HTMLResponse)
    def phu_du_lieu(request: Request):
        """Bảng phủ dữ liệu: liếc mắt là thấy tháng/kỳ nào đang thiếu.

        Cách tính nằm ở kome/coverage.py — DÙNG CHUNG với lệnh terminal
        scripts/bang_phu_du_lieu.py. Trang này chỉ hiển thị.

        open_conn() để tôn trọng create_app(db_url=…): gọi connect() không
        tham số ở đây sẽ âm thầm đọc CSDL THẬT trong khi test tưởng mình
        đang dùng CSDL thử nghiệm.
        """
        try:
            with open_conn() as conn:
                bang = tinh_bang_phu(conn)
                bang_ngay = tinh_bang_ngay(conn)
            # Mẫu KHÔNG in `bang.database`: tên CSDL là thông tin kết nối,
            # còn trang này thì ai mở cũng xem được. Terminal in được vì chỉ
            # người chạy lệnh mới thấy.
            return _ve(request, "phu_du_lieu.html",
                       {"bang": bang, "bang_ngay": bang_ngay, "trang": "phu"})
        except Exception as e:
            return _loi(request, "mở trang bảng phủ dữ liệu", e, chung)

    @app.post("/undo/{batch_id}")
    def undo(request: Request, batch_id: int):
        if chi_doc:
            return _cam(request)
        try:
            from kome.pipeline import undo_batch
            with open_conn() as conn:
                undo_batch(conn, batch_id)
            return RedirectResponse("/health", status_code=303)
        except Exception as e:
            return _loi(request, "hoàn tác lần nạp dữ liệu", e, chung)

    return app

app = create_app()
