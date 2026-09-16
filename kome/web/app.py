# kome/web/app.py
import os, shutil, tempfile, traceback
from datetime import timedelta
from pathlib import Path
from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from kome.db import connect
from kome.pipeline import ingest, undo_batch, SPECS
from ops.backup import backup_status

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

# Cửa sổ soát ngày thiếu trên /health (tính lùi từ ngày bán gần nhất).
SO_NGAY_SOAT = 30


def _loi(request: Request, viec: str, exc: Exception) -> HTMLResponse:
    """Trang lỗi tiếng Việt cho mọi lỗi NGOÀI DỰ KIẾN.

    Công ty không có nhân sự IT: trang 500 mặc định của framework (tiếng Anh,
    đầy dấu vết ngăn xếp) làm người dùng tưởng mình bấm sai rồi thử lại —
    và đó chính là lúc lô mồ côi biến thành "đã nạp rồi, bỏ qua" màu xanh.
    Chuỗi ngoại lệ gốc CHỈ ghi ra nhật ký máy chủ, KHÔNG hiện lên trang.
    """
    print(f"[KOME] lỗi khi {viec}:\n{traceback.format_exc()}")
    return TEMPLATES.TemplateResponse(
        request, "error.html", {"viec": viec}, status_code=500
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
    app = FastAPI(title="KOME — nạp dữ liệu")
    archive_dir = Path(os.environ.get("ARCHIVE_DIR", "./raw_archive"))
    open_conn = lambda: connect(db_url)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        try:
            return TEMPLATES.TemplateResponse(request, "upload.html", {"results": None})
        except Exception as e:
            return _loi(request, "mở trang nạp dữ liệu", e)

    @app.post("/upload", response_class=HTMLResponse)
    def upload(request: Request, files: list[UploadFile]):
        try:
            results = []
            with open_conn() as conn:
                for f in files:
                    with tempfile.TemporaryDirectory() as tmp:
                        staged = Path(tmp) / f.filename
                        with staged.open("wb") as out:
                            shutil.copyfileobj(f.file, out)
                        results.append(ingest(conn, staged, archive_dir))
            return TEMPLATES.TemplateResponse(request, "upload.html", {"results": results})
        except Exception as e:
            return _loi(request, "nạp file dữ liệu", e)

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
            seen = {r[0]: r for r in rows}
            status = [
                {"name": s.display_name,
                 "last": seen[k][1] if k in seen else None,
                 "rows": seen[k][2] if k in seen else 0,
                 "total": seen[k][3] if k in seen else 0}
                for k, s in SPECS.items()
            ]
            backup = backup_status(backup_dir)
            return TEMPLATES.TemplateResponse(
                request, "health.html", {"status": status, "backup": backup, "ky": ky}
            )
        except Exception as e:
            return _loi(request, "mở trang sức khoẻ dữ liệu", e)

    @app.post("/undo/{batch_id}")
    def undo(request: Request, batch_id: int):
        try:
            with open_conn() as conn:
                undo_batch(conn, batch_id)
            return RedirectResponse("/health", status_code=303)
        except Exception as e:
            return _loi(request, "hoàn tác lần nạp dữ liệu", e)

    return app

app = create_app()
