# kome/web/app.py
import os, shutil, tempfile
from pathlib import Path
from fastapi import FastAPI, UploadFile, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from kome.db import connect
from kome.pipeline import ingest, undo_batch, SPECS

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

def create_app(db_url: str | None = None) -> FastAPI:
    """db_url=None => lấy DATABASE_URL. Test LUÔN truyền DATABASE_URL_TEST."""
    app = FastAPI(title="KOME — nạp dữ liệu")
    archive_dir = Path(os.environ.get("ARCHIVE_DIR", "./raw_archive"))
    open_conn = lambda: connect(db_url)

    @app.get("/", response_class=HTMLResponse)
    def home(request: Request):
        return TEMPLATES.TemplateResponse(request, "upload.html", {"results": None})

    @app.post("/upload", response_class=HTMLResponse)
    def upload(request: Request, files: list[UploadFile]):
        results = []
        with open_conn() as conn:
            for f in files:
                with tempfile.TemporaryDirectory() as tmp:
                    staged = Path(tmp) / f.filename
                    with staged.open("wb") as out:
                        shutil.copyfileobj(f.file, out)
                    results.append(ingest(conn, staged, archive_dir))
        return TEMPLATES.TemplateResponse(request, "upload.html", {"results": results})

    @app.get("/health", response_class=HTMLResponse)
    def health(request: Request):
        with open_conn() as conn:
            rows = conn.execute(
                """SELECT spec_name, max(loaded_at), max(row_count), max(total_amount)
                   FROM meta.ingest_batch WHERE undone_at IS NULL GROUP BY spec_name"""
            ).fetchall()
        seen = {r[0]: r for r in rows}
        status = [
            {"name": s.display_name,
             "last": seen[k][1] if k in seen else None,
             "rows": seen[k][2] if k in seen else 0,
             "total": seen[k][3] if k in seen else 0}
            for k, s in SPECS.items()
        ]
        return TEMPLATES.TemplateResponse(request, "health.html", {"status": status})

    @app.post("/undo/{batch_id}")
    def undo(batch_id: int):
        with open_conn() as conn:
            undo_batch(conn, batch_id)
        return RedirectResponse("/health", status_code=303)

    return app

app = create_app()
