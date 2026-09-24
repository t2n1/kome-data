"""API JSON cho giao diện React (đặc tả 2026-09-23-giao-dien-react-design.md).

Mọi endpoint gọi lại ĐÚNG hàm tính sẵn — không định nghĩa chỉ số nào ở đây.
Cổng đăng nhập vẫn là middleware `chan_cua` của app.py (với /api/* nó trả 401
JSON thay vì chuyển hướng). Kết quả đi qua ảnh chụp theo phiên bản dữ liệu
(kome/web/anh_chup.py) và mang `ETag` = phiên bản đó: trình duyệt hỏi lại với
`If-None-Match` nhận `304` rỗng khi dữ liệu chưa đổi.
"""
from __future__ import annotations

import hashlib
import traceback
from datetime import date
from urllib.parse import urlencode

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from kome import khach_hang as KH
from kome import khoang_xem as KX
from kome import khach_thang as KT
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
    `sale_dang_loc` bên dưới; `?tat_ca=1` bỏ lọc."""
    nguoi = getattr(request.state, "nguoi", None)
    if tat_ca or nguoi is None:
        return None
    return nguoi.salesperson_code


def sale_dang_loc(request: Request, tat_ca: int, nv: str = "") -> tuple[str | None, str | None]:
    """(mã sale, tên người) đang lọc, hoặc (None, None) nếu xem tất cả — MỘT
    định nghĩa cho mọi màn (Khách hàng, Bản đồ, Cần liên hệ).

    Không có người đăng nhập (máy trong công ty không bật cổng) hoặc người đó
    không phụ trách khách nào (chủ DN, kế toán, kho) => KHÔNG lọc gì. Lọc theo
    NULL thì họ mở lên thấy danh sách rỗng và tưởng mất dữ liệu.

    `nv` là lựa chọn TƯỜNG MINH từ ô lọc "Người phụ trách": nó thắng cả mặc
    định theo người đăng nhập lẫn `tat_ca`. `nv == KH.NV_MOI_NGUOI` ("mọi người
    phụ trách") cũng là lựa chọn tường minh — không có giá trị quy ước này thì
    mục đó gửi `nv=""`, rơi về mặc định và ô chọn khoe "mọi người" trong khi
    danh sách vẫn bị lọc. `KH.PT_TRONG` = chưa ai phụ trách.

    Vẫn KHÔNG phải hàng rào bảo mật: năm sale ai cũng biết khách của ai (đặc tả
    đợt 3 §5), nên chọn mã của người khác là hợp lệ."""
    if nv == KH.NV_MOI_NGUOI:
        return None, None
    if nv:
        return nv, None
    nguoi = getattr(request.state, "nguoi", None)
    if tat_ca or nguoi is None or not nguoi.salesperson_code:
        return None, None
    return nguoi.salesperson_code, nguoi.ten_sale or nguoi.ten_dang_nhap


def _khoa(goc: str, **ts) -> str:
    """Khoá ảnh chụp: đường dẫn + tham số ĐÃ CHUẨN HOÁ (sắp theo tên, bỏ giá
    trị rỗng) — hai URL cùng nghĩa dùng chung một ảnh chụp."""
    q = urlencode(sorted((k, str(v)) for k, v in ts.items() if v not in (None, "")))
    return goc + ("?" + q if q else "")


def thanh_json(o, bo: tuple[str, ...] = ()):
    """Dataclass -> dict KÈM mọi `@property` của lớp (asdict bỏ qua chúng, mà
    màn Báo cáo / Dự báo / Cần liên hệ đọc đúng các thuộc tính đó: `rong_thanh`,
    `tang_dt`, `lech`, `xong`…). Không tính gì mới — chỉ đọc lại thuộc tính đã
    có ở kome/*.py. `bo`: tên trường bỏ ra (vd chuỗi ngày dài chỉ dùng để vẽ)."""
    from dataclasses import fields, is_dataclass
    if is_dataclass(o) and not isinstance(o, type):
        d = {f.name: thanh_json(getattr(o, f.name), bo) for f in fields(o) if f.name not in bo}
        for ten in dir(type(o)):
            if ten not in bo and not ten.startswith("_") and isinstance(getattr(type(o), ten, None), property):
                d[ten] = thanh_json(getattr(o, ten), bo)
        return d
    if isinstance(o, dict):
        return {k: thanh_json(v, bo) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [thanh_json(v, bo) for v in o]
    return o


def du_lieu_bao_cao(c, ts: "KX.ThamSo | None" = None) -> dict:
    """Dữ liệu màn /bao-cao theo khoảng xem: số + hình học biểu đồ (tính ở
    kome/bao_cao.py, kome/ban_khoang.py và kome/ve_phan_tich.py — bất biến đối
    soát có test ở đó). Dạng Kỳ = màn Báo cáo cũ, không đổi số. Không tham số
    = tháng hiện tại — cũng là thứ `anh_chup.lam_nong` tính sẵn sau khi nạp."""
    from kome import ban_khoang as BK
    from kome.bao_cao import (chi_so_phu, nhom_theo_nganh, tien_do_ngan_sach,
                              tinh_bao_cao, ve_bieu_do, ve_luy_ke)
    from kome.ngan_sach import thang_cua_ky
    from kome.ve_phan_tich import ve_cay_o, ve_dong_gop, ve_duong_nho, ve_nhiet, ve_pareto
    kx = KX.giai_conn(c, ts or KX.ThamSo())
    if kx is None:
        bc = tinh_bao_cao(c, None)
        return {"bc": thanh_json(bc), "td": None, "khoang": None}
    bc = BK.tinh_bao_cao(c, kx)
    # Ngân sách: dạng Kỳ như cũ; dạng Tháng = tháng đang xem; dạng Khoảng
    # không có (ngân sách chỉ đặt theo tháng).
    td = (tien_do_ngan_sach(c, kx.company_fy) if kx.loai == "ky"
          else tien_do_ngan_sach(c, kx.company_fy, kx.thang) if kx.loai == "thang" else None)
    # Cùng cách dựng với route Jinja cũ (không hỏi CSDL thêm câu nào).
    thang_cuoi = kx.den.strftime("%Y-%m")
    thang_dau = kx.ngay_dau.strftime("%Y-%m")
    return thanh_json({
        "khoang": kx,
        "bc": bc, "td": td, "bd": ve_bieu_do(bc.thang), "lk": ve_luy_ke(td),
        "so_nho": {"dt": ve_duong_nho([o.doanh_thu for o in bc.thang]),
                   "lg": ve_duong_nho([o.lai_gop for o in bc.thang]),
                   "ts": ve_duong_nho([o.ty_suat for o in bc.thang]),
                   "kh": ve_duong_nho([o.so_khach for o in bc.thang])},
        "dg": ve_dong_gop(bc.nganh_ky),
        "co": ve_cay_o(nhom_theo_nganh(bc.nganh_ky, bc.hang_theo_nganh)),
        "nh": ve_nhiet(bc.nganh_thang, thang_cua_ky(bc.ky.company_fy), thang_cuoi, thang_dau),
        "pa": ve_pareto(bc.tap_trung),
        "ngay_dau_du_lieu": kx.ngay_dau,
        "td_phu": chi_so_phu(td) if td else None,
    })


def du_lieu_du_bao(c) -> dict:
    """Dữ liệu màn /du-bao (kome/du_bao.py + kome/ve_du_bao.py). `tong(kb)` /
    `theo(kb)` là PHƯƠNG THỨC — tính sẵn cho cả ba kịch bản để đổi kịch bản ở
    trình duyệt không phải hỏi lại máy chủ."""
    from kome import du_bao as DB
    from kome import ve_du_bao as VDB
    db = DB.du_bao(c)
    if db is None:
        return {"db": None}
    m = db.nam
    return thanh_json({
        "db": db, "kich_ban": DB.KICH_BAN,
        "tong": {kb: m.tong(kb) for kb in DB.KICH_BAN},
        "theo": {kb: [t.theo(kb) for t in m.du_bao] for kb in DB.KICH_BAN},
        "ve_chot": VDB.ve_chot_thang(db.chot) if db.chot else {"co": False},
        "ve_nam": {kb: VDB.ve_muoi_hai_thang(m, kb) for kb in DB.KICH_BAN} if m.du_bao else None,
    }, bo=("ngay",))


def du_lieu_kho_hang(c, kho: str = "", loc: str = "") -> dict:
    """Dữ liệu màn /kho-hang (`SP.kho_hang`, 2 lượt hỏi) + nhãn để giao diện
    không tự chép. Cũng là thứ `anh_chup.lam_nong` tính sẵn (không lọc)."""
    from kome import san_pham as SP
    return thanh_json({"k": SP.kho_hang(c, kho=kho, loc=loc),
                       "trang_thai": {a: list(b) for a, b in SP.TRANG_THAI_TON.items()},
                       "loai_han": {a: list(b) for a, b in SP.LOAI_HAN.items()},
                       "can_han_ngay": SP.CAN_HAN_NGAY})


# Khoá ảnh chụp danh mục sản phẩm — `anh_chup.lam_nong` làm nóng đúng khoá này.
KHOA_DANH_MUC = "san-pham/danh-muc"
KHOA_CONG_NO = "cong-no"


def _loi(thong_diep: str, ma: int = 500) -> JSONResponse:
    return JSONResponse({"loi": thong_diep}, status_code=ma)


def tao_api(open_app_conn) -> APIRouter:
    r = APIRouter(prefix="/api")

    @r.get("/tong-quan/{khoi}")
    def khoi_tong_quan(request: Request, khoi: str, tat_ca: int = 0, thang: str = "",
                       ky: str = "", tu: str = "", den: str = ""):
        muc = KTQ.KHOI.get(khoi)
        if muc is None:
            return JSONResponse({"loi": f"Không có khối '{khoi}'."}, status_code=404)
        ham, theo_ngay, theo_sale, theo_khoang = muc
        sale = _sale(request, tat_ca) if theo_sale else None
        ts = None
        if theo_khoang:
            try:
                ts = KX.doc_tham_so(thang, ky, tu, den)
            except KX.LoiKhoang as e:
                return _loi(str(e), 400)
        khoa = _khoa(f"tong-quan/{khoi}", **({"sale": sale or "*"} if theo_sale else {}),
                     **(ts.khoa() if ts else {}))
        tinh = (lambda c: ham(c, sale, ts)) if theo_khoang else (lambda c: ham(c, sale))
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, khoa, tinh, theo_ngay)
        except KX.LoiKhoang as e:
            return _loi(str(e), 400)
        except Exception:
            traceback.print_exc()
            return JSONResponse({"loi": "Không đọc được dữ liệu khối này."}, status_code=500)
        return _json(request, du_lieu, pb)

    @r.get("/pham-vi")
    def pham_vi(request: Request):
        """Dải dữ liệu bán hàng + các kỳ — cho bộ chọn khoảng xem (1 lượt hỏi)."""
        return _chup(request, "pham-vi", lambda c: KX.pham_vi(c), "Không đọc được dải dữ liệu.",
                     chi_nap=True)

    @r.get("/thong-bao")
    def thong_bao(request: Request):
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, "thong-bao", lambda c: KTQ.thong_bao(c), theo_ngay=True)
        except Exception:
            traceback.print_exc()
            return JSONResponse({"loi": "Không đọc được thông báo."}, status_code=500)
        return _json(request, du_lieu, pb)

    # ---- Khách hàng (giai đoạn 2) --------------------------------------
    # Ngân sách lượt hỏi của màn danh sách = 3 (bất biến /khach-hang): tong-quan
    # 1 + ds 2. Hồ sơ <= 8 (bất biến ho_so). Bản đồ 2 (bất biến /ban-do).

    def _chup(request, khoa, tinh, loi, chi_nap=False):
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, khoa, tinh, chi_nap=chi_nap)
        except KX.LoiKhoang as e:
            # Tháng / kỳ ngoài dải dữ liệu — chỉ biết được sau khi đọc dải.
            return _loi(str(e), 400)
        except Exception:
            traceback.print_exc()
            return _loi(loi)
        return _json(request, du_lieu, pb)

    @r.get("/khach-hang/ds")
    def kh_ds(request: Request, tim: str = "", loc: str = "", sap: str = "doanh_thu",
              giam: str = "", trang: int = 1, co: int = KH.MOI_TRANG, tat_ca: int = 0,
              nv: str = "", nhom: str = "", hang: str = "", tinh: str = "", nhan_thang: str = ""):
        """Màn danh sách: MỘT lượt gọi trả cả trang bảng lẫn khối tổng quan.
        Danh bạ (1 lượt hỏi nặng) đi qua ảnh chụp theo phiên bản NẠP; lọc /
        sắp / đếm làm bằng Python (kome.khach_hang._khop). Trúng ảnh chụp: 1
        lượt hỏi (phiên bản). Trượt: 2. Ngân sách màn danh sách <= 3 (bất biến)."""
        # `nhan_thang` (nhãn mart.khach_thang_nay) — KHÔNG phải `thang`: `?thang=YYYY-MM`
        # là tháng của khoảng xem chung (kome/khoang_xem.py).
        thang = nhan_thang
        sale, ten_sale = sale_dang_loc(request, tat_ca, nv)
        hang = ",".join(KH._ds_hang(hang))
        g = None if giam == "" else giam in ("1", "true")
        tim = tim.strip()[:100]
        bo_loc = dict(nhom=nhom or None, hang=hang or None, tinh=tinh or None)
        try:
            with open_app_conn() as conn:
                db, pb = anh_chup.lay_du_lieu(conn, anh_chup.KHOA_DANH_BA, KH.danh_ba,
                                              chi_nap=True)
        except Exception:
            traceback.print_exc()
            return _loi("Không đọc được danh bạ khách hàng.")
        tq = KH.tong_quan(db, sale, tim=tim, thang=thang or None, **bo_loc)
        t = KH.trang_danh_sach(db, tim=tim, loc=loc, sap=sap, trang=trang, sale=sale,
                               thang=thang or None, giam=g, co=co, **bo_loc)
        ten = ten_sale or next((n["ten"] for n in tq.nhan_vien if n["ma"] == sale), None)
        ra = {"trang": t, "tq": tq, "sale": sale, "ten_sale": ten, "hom_nay": db.get("hom_nay"),
              "nhan_trang_thai": {a: b[0] for a, b in KH.TRANG_THAI.items()},
              "can_xu_ly": list(KH.TRANG_THAI_CAN_XU_LY),
              "khong_ro": KH.KHONG_RO, "tinh_trong": KH.TINH_TRONG,
              "nv_moi_nguoi": KH.NV_MOI_NGUOI, "pt_trong": KH.PT_TRONG,
              "nhan_thang": KT.NHAN}
        # ETag = phiên bản danh bạ + chính URL: cùng URL, cùng dữ liệu -> 304.
        return _json(request, anh_chup.sang_json(ra),
                     hashlib.sha1(f"{pb}|{request.url.query}|{sale}".encode()).hexdigest()[:16] if pb else "")

    @r.get("/khach-hang/{ma}")
    def kh_ho_so(request: Request, ma: str):
        from kome import ho_so_khach as HSK
        # Nhật ký tiếp xúc thuộc phiên bản dữ liệu (app.nhat_ky_tiep_xuc có
        # trong _PHIEN_BAN), nên ghi xong một lần tiếp xúc là ảnh chụp tự mới.
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(
                    conn, _khoa("khach-hang/ho-so", ma=ma),
                    lambda c: (lambda h: None if h is None else HSK.cho_giao_dien(h))(KH.ho_so(c, ma)))
        except Exception:
            traceback.print_exc()
            return _loi("Không đọc được hồ sơ khách hàng.")
        if du_lieu == "null":
            return _loi(f"Không có khách hàng mã {ma}.", 404)
        return _json(request, du_lieu, pb)

    @r.get("/khach-hang/{ma}/dong")
    def kh_dong(request: Request, ma: str, tu: str, den: str):
        """Dòng bán của MỘT khách trong [tu, den], gộp theo ngày × mã × quy cách
        — khi bấm một tháng trên biểu đồ 12 tháng / một mốc trên dòng thời gian.
        Tối đa 62 ngày một lần hỏi. 1 lượt hỏi."""
        try:
            a, b = date.fromisoformat(tu), date.fromisoformat(den)
        except ValueError:
            return _loi("Ngày không đọc được.", 400)
        if b < a or (b - a).days > 62:
            return _loi("Khoảng ngày phải từ 0 tới 62 ngày.", 400)

        def tinh_(c):
            rows = c.execute(
                """SELECT d.sales_date, d.product_code,
                          coalesce(nullif(p.product_name, ''), d.product_code),
                          d.pack_code, sum(d.qty), sum(d.doanh_thu_thuan),
                          sum(d.gross_profit), count(DISTINCT d.slip_no)
                     FROM mart.dong_ban d
                     LEFT JOIN core.dim_product p ON p.product_code = d.product_code
                    WHERE d.customer_code = %s AND d.sales_date BETWEEN %s AND %s
                    GROUP BY 1, 2, 3, 4
                    ORDER BY 1 DESC, 6 DESC""", (ma, a, b)).fetchall()
            return {"tu": a, "den": b, "dong": [
                {"ngay": x[0], "ma": x[1], "ten": x[2],
                 "quy_cach": KH.QUY_CACH.get(x[3], x[3]), "so_luong": x[4],
                 "doanh_thu": int(x[5] or 0), "lai_gop": int(x[6] or 0), "so_phieu": x[7]}
                for x in rows]}
        # Dòng bán chỉ đọc core -> phiên bản theo dữ liệu nạp.
        return _chup(request, _khoa("khach-hang/dong", ma=ma, tu=a, den=b), tinh_,
                     "Không đọc được dòng bán.", chi_nap=True)

    @r.post("/khach-hang/{ma}/tiep-xuc")
    async def kh_tiep_xuc(request: Request, ma: str):
        """Thêm MỘT dòng app.nhat_ky_tiep_xuc (chỉ thêm — 030). Chỉ nhận
        `application/json`: một form của trang lạ không gửi được kiểu đó mà
        không qua preflight CORS — lớp chặn CSRF cộng thêm SameSite=Lax."""
        from kome import lien_he as LH
        if not request.headers.get("content-type", "").startswith("application/json"):
            return _loi("Chỉ nhận JSON.", 415)
        try:
            b = await request.json()
        except Exception:
            return _loi("Thân yêu cầu không phải JSON.", 400)
        nguoi = getattr(request.state, "nguoi", None)
        try:
            with open_app_conn() as conn:
                LH.ghi(conn, ma, nguoi.id if nguoi else None, str(b.get("kieu", "")),
                       str(b.get("ket_qua", "")), str(b.get("noi_dung", "")),
                       str(b.get("hen_lai", "") or ""))
                conn.commit()
        except LH.LoiNhap as e:
            return _loi(str(e), 400)
        except Exception:
            traceback.print_exc()
            return _loi("Không ghi được lần tiếp xúc.")
        return JSONResponse({"ok": True})

    # ---- Giai đoạn 3: Báo cáo · Dự báo · Cần liên hệ ------------------
    # Hình học biểu đồ vẫn tính ở kome/ve_phan_tich.py, kome/bao_cao.py,
    # kome/ve_du_bao.py (các bất biến đối soát / "không vẽ" có test ở đó) —
    # API trả nguyên, giao diện React chỉ vẽ + thêm tương tác.

    @r.get("/bao-cao")
    def bao_cao(request: Request, thang: str = "", ky: str = "", tu: str = "", den: str = ""):
        """Báo cáo theo khoảng xem (`?thang=` · `?ky=` · `?tu=&den=`; không tham
        số = tháng hiện tại). Đọc app.ngan_sach (tiến độ) -> phiên bản đầy đủ."""
        try:
            ts = KX.doc_tham_so(thang, ky, tu, den)
        except KX.LoiKhoang as e:
            return _loi(str(e), 400)
        return _chup(request, _khoa("bao-cao", **ts.khoa()), lambda c: du_lieu_bao_cao(c, ts),
                     "Không đọc được báo cáo.")

    @r.get("/du-bao")
    def du_bao(request: Request):
        # Đọc app.ngan_sach -> phiên bản đầy đủ.
        return _chup(request, "du-bao", du_lieu_du_bao, "Không đọc được dự báo.")

    @r.get("/lien-he")
    def lien_he(request: Request, tat_ca: int = 0, nv: str = "", ly_do: str = ""):
        from kome import lien_he as LH
        from kome.tuoi_du_lieu import hom_nay_o_nhat
        sale, ten_sale = sale_dang_loc(request, tat_ca, nv)
        hom_nay = hom_nay_o_nhat()

        def tinh_(c):
            ds = LH.danh_sach(c, hom_nay, sale=sale, ly_do=ly_do or None)
            return thanh_json({
                "ds": ds, "hoat_dong": LH.hoat_dong_gan_day(c, sale=sale),
                "hen": LH.hen_goi_lai(c, hom_nay, sale=sale), "hom_nay": hom_nay,
                "sale": sale, "ten_sale": ten_sale, "cot_thang": LH.COT_THANG,
                "an_ngay": LH.AN_KHI_KHONG_HEN, "ly_do_ds": {k: list(v) for k, v in LH.LY_DO.items()},
                "kieu_tx": {k: list(v) for k, v in LH.KIEU.items()},
                "ket_qua_tx": {k: list(v) for k, v in LH.KET_QUA.items()},
                "nv_moi_nguoi": KH.NV_MOI_NGUOI,
            })
        # Đọc nhật ký tiếp xúc (phiên bản đầy đủ) VÀ đồng hồ thật giờ Tokyo
        # (tạm ẩn / hẹn gọi lại hôm nay) -> theo_ngay.
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, _khoa("lien-he", sale=sale or "*", ly_do=ly_do),
                                           tinh_, theo_ngay=True)
        except Exception:
            traceback.print_exc()
            return _loi("Không đọc được danh sách cần liên hệ.")
        return _json(request, du_lieu, pb)

    @r.get("/ban-do")
    def ban_do(request: Request, tat_ca: int = 0, nv: str = "", chi_so: str = "khach"):
        from kome import ban_do as BD
        sale, ten_sale = sale_dang_loc(request, tat_ca, nv)

        def tinh_(c):
            t = BD.ban_do(c, sale=sale, chi_so=chi_so)
            return {"t": t, "sale": sale, "ten_sale": ten_sale, "chi_so_ds": BD.CHI_SO,
                    "o_rong": BD.O_RONG, "o_cao": BD.O_CAO}
        # Bản đồ chỉ đọc core/mart (không bảng `app` nào) -> phiên bản theo dữ liệu nạp.
        return _chup(request, _khoa("ban-do", sale=sale or "*", chi_so=chi_so), tinh_,
                     "Không đọc được bản đồ khách hàng.", chi_nap=True)

    # ---- Giai đoạn 4: Sản phẩm · Kho hàng -----------------------------
    # Cả bốn chỉ đọc core/mart (không bảng `app` nào) -> phiên bản theo dữ
    # liệu NẠP (`chi_nap`): ghi một lần tiếp xúc không làm chúng cũ.

    @r.get("/san-pham")
    def sp_danh_muc(request: Request):
        """Cả danh mục một lượt (232 mã) — lọc / sắp / tìm ở trình duyệt."""
        from kome import san_pham as SP
        return _chup(request, KHOA_DANH_MUC, SP.danh_muc,
                     "Không đọc được danh mục sản phẩm.", chi_nap=True)

    @r.get("/san-pham/{ma}")
    def sp_ho_so(request: Request, ma: str):
        """Hồ sơ một mã: `SP.ho_so` (trần 5 lượt hỏi, bất biến đặc tả 4b §5.5)."""
        from kome import san_pham as SP

        def tinh_(c):
            h = SP.ho_so(c, ma)
            return None if h is None else thanh_json({"h": h, "quy_cach": SP.QUY_CACH})
        try:
            with open_app_conn() as conn:
                du_lieu, pb = anh_chup.lay(conn, _khoa("san-pham/ho-so", ma=ma), tinh_, chi_nap=True)
        except Exception:
            traceback.print_exc()
            return _loi("Không đọc được hồ sơ mã hàng.")
        if du_lieu == "null":
            return _loi(f"Không có mã hàng {ma}.", 404)
        return _json(request, du_lieu, pb)

    @r.get("/san-pham/{ma}/ngay")
    def sp_ngay(request: Request, ma: str, thang: str):
        """Bán theo ngày của một mã trong một tháng + tháng trước. 1 lượt hỏi."""
        from kome import san_pham as SP
        import re
        if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", thang):
            return _loi("Tháng phải có dạng YYYY-MM.", 400)
        return _chup(request, _khoa("san-pham/ngay", ma=ma, thang=thang),
                     lambda c: SP.ban_theo_ngay(c, ma, thang),
                     "Không đọc được lượng bán theo ngày.", chi_nap=True)

    @r.get("/kho-hang")
    def kho_hang(request: Request, kho: str = "", loc: str = ""):
        """Màn Kho hàng: `SP.kho_hang` (ĐÚNG 2 lượt hỏi, bất biến đặc tả 4b).
        Mỗi khối theo đúng những bộ lọc nó không điều khiển — xem docstring
        của kho_hang(); giao diện chỉ hiện, không lọc lại."""
        from kome import san_pham as SP
        loc = loc if loc in SP.TRANG_THAI_TON else ""

        return _chup(request, _khoa("kho-hang", kho=kho, loc=loc),
                     lambda c: du_lieu_kho_hang(c, kho, loc),
                     "Không đọc được tồn kho.", chi_nap=True)

    # ---- Đợt 6: Công nợ ------------------------------------------------
    # Chỉ đọc core/mart -> phiên bản theo dữ liệu NẠP.

    @r.get("/cong-no")
    def cong_no(request: Request):
        """Màn Công nợ: MỘT ảnh chụp (`CN.man_hinh`, 2 lượt hỏi) — lọc ở trình duyệt."""
        from kome import cong_no as CN
        return _chup(request, KHOA_CONG_NO, lambda c: thanh_json(CN.man_hinh(c)),
                     "Không đọc được sổ công nợ.", chi_nap=True)

    @r.get("/cong-no/khach/{ma}")
    def cong_no_khach(request: Request, ma: str):
        """Tab Công nợ của hồ sơ khách (`CN.cua_khach`, ≤ 3 lượt hỏi)."""
        from kome import cong_no as CN
        return _chup(request, _khoa("cong-no/khach", ma=ma), lambda c: thanh_json(CN.cua_khach(c, ma)),
                     "Không đọc được công nợ của khách.", chi_nap=True)

    return r
