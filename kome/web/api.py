"""API JSON cho giao diện React (đặc tả 2026-09-23-giao-dien-react-design.md).

Mọi endpoint gọi lại ĐÚNG hàm tính sẵn — không định nghĩa chỉ số nào ở đây.
Cổng đăng nhập vẫn là middleware `chan_cua` của app.py (với /api/* nó trả 401
JSON thay vì chuyển hướng). Kết quả đi qua ảnh chụp theo phiên bản dữ liệu
(kome/web/anh_chup.py) và mang `ETag` = phiên bản đó: trình duyệt hỏi lại với
`If-None-Match` nhận `304` rỗng khi dữ liệu chưa đổi.
"""
from __future__ import annotations

import traceback

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from kome import khoi_tong_quan as KTQ
from kome.web import anh_chup


def _json(request: Request, du_lieu: str, phien_ban: str) -> Response:
    etag = f'W/"{phien_ban}"' if phien_ban else None
    if etag and request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    h = {"Cache-Control": "private, no-cache"}
    if etag:
        h["ETag"] = etag
    return Response(du_lieu, media_type="application/json", headers=h)


def _sale(request: Request, tat_ca: int) -> str | None:
    """Mặc định tiện dụng theo người đăng nhập (không phải hàng rào) — cùng nếp
    `_sale_dang_loc` của app.py; `?tat_ca=1` bỏ lọc."""
    nguoi = getattr(request.state, "nguoi", None)
    if tat_ca or nguoi is None:
        return None
    return nguoi.salesperson_code


def tao_api(open_app_conn) -> APIRouter:
    r = APIRouter(prefix="/api")

    @r.get("/tong-quan/{khoi}")
    def khoi_tong_quan(request: Request, khoi: str, tat_ca: int = 0):
        muc = KTQ.KHOI.get(khoi)
        if muc is None:
            return JSONResponse({"loi": f"Không có khối '{khoi}'."}, status_code=404)
        ham, theo_ngay, theo_sale = muc
        sale = _sale(request, tat_ca) if theo_sale else None
        khoa = f"tong-quan/{khoi}" + (f"?sale={sale or '*'}" if theo_sale else "")
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, khoa, lambda c: ham(c, sale), theo_ngay)
        except Exception:
            traceback.print_exc()
            return JSONResponse({"loi": "Không đọc được dữ liệu khối này."}, status_code=500)
        return _json(request, du_lieu, pb)

    @r.get("/thong-bao")
    def thong_bao(request: Request):
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, "thong-bao", lambda c: KTQ.thong_bao(c), theo_ngay=True)
        except Exception:
            traceback.print_exc()
            return JSONResponse({"loi": "Không đọc được thông báo."}, status_code=500)
        return _json(request, du_lieu, pb)

    return r
