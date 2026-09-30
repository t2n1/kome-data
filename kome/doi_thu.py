"""Thị trường & đối thủ (/doi-thu) — đặc tả docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md.

Chỉ số ở mart (060): ở đây chỉ HỎI và gói JSON (mỗi hàm đọc ĐÚNG MỘT lượt hỏi), và GHI vào app
(mọi hàm ghi thêm một dòng app.doi_thu_nhat_ky trong CÙNG giao dịch; không commit — route commit).
Không bao giờ ghi core: sửa lỗi đọc = app.dinh_chinh_gia, giá đã đổi = app.gia_doi_thu_tay.
"""
from __future__ import annotations

import json
import re
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from kome.ten_hang import chuan_ten
from kome.tuoi_du_lieu import hom_nay_o_nhat

TRUONG_SUA = ("ten_goc", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
              "thue", "gom_ship", "kenh_gia", "muc_gia", "trang_thai",
              "so_goi_thung", "kl_goi_g", "bac", "khuyen_mai", "gia_truoc_km")
TRUONG_XOA_DUOC = ("khuyen_mai", "gia_truoc_km", "bac")   # "" / [] = xoá (khuyến mãi hết, bậc sai); trường khác không xoá được
DON_VI_SL = ("thung", "kg", "goi", "pallet")               # cùng lược đồ `bac` của 065 / scripts/goi_doi_thu.py::kiem_bac
DON_VI_GIA_BAC = ("thung", "kg", "goi")
BAC_TOI_DA = 10
SO_BAC_TOI_DA = Decimal("1000000000")                      # tu / gia của một bậc: chặn số khổng lồ (float -> inf làm hỏng JSON)
GOI_TOI_DA = 100000
KL_GOI_TOI_DA = Decimal("30000")                           # = CHECK kl_goi_g của 065
GIA_TRUOC_KM_TOI_DA = Decimal("9999999999")                # numeric(12,2) của 065 chứa tới 10^10 - 0,01
THUE = ("chua", "co", "khong_ro")
SHIP = ("co", "khong", "khong_ro")
TRANG_THAI = ("con", "het", "sap_ve", "khong_ro")
NHAN = ("cung_hang", "thay_the", "khong")
LOC_DUYET = ("", "can_xem", "bat_thuong", "chua_ghep", "chua_xac_nhan", "thieu_quy_cach", "da_xoa")
DAI_TOI_DA = 300


class LoiNhap(Exception):
    """Dữ liệu người nhập không hợp lệ — route trả 400 kèm câu này."""


class XungDot(Exception):
    """Có người ghi vào mục này SAU lúc pop-up mở (đợt 4b) — route trả 409 {loi, xung_dot: {ai, luc, sau}}.
    `ai` = tên người phụ trách / tên đăng nhập (None = script, máy không cổng đăng nhập); `luc` = ISO;
    `sau` = cột `sau` của dòng nhật ký đó; `id` = id nhật ký đó (sua_cuoi mới). `thay_boi` (đợt 4b, B14) = {nguon, id}
    của bản MỚI NHẤT đã thay dòng này (dòng tay qua thay_cho_tay_id, dòng nạp qua fact_goc_id): dòng đã bị thay thì không
    sửa được nữa, kể cả với ghi_de — pop-up mở bản mới."""

    def __init__(self, ai, luc: str, sau, id: int, thay_boi: dict | None = None):
        super().__init__("Dòng này đã có bản mới." if thay_boi else "Có người vừa sửa mục này.")
        self.ai, self.luc, self.sau, self.id, self.thay_boi = ai, luc, sau, id, thay_boi


_PHAY_NGHIN = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
_PHAY_THAP_PHAN = re.compile(r"^-?\d+,\d+$")
_SO_THUONG = re.compile(r"^-?\d+(\.\d+)?$")


def _so(v, ten, duong=False, phay_la_thap_phan=False):
    """Đọc số người gõ. '1,234' / '12,345.6' = phẩy nghìn; '0,5' / '12,75' = phẩy thập phân;
    phay_la_thap_phan=True (ô kg — không ai gõ hàng nghìn kg): dấu phẩy LUÔN là thập phân ('1,500' = 1.5);
    'nan' / 'inf' / '1e3' và mọi thứ khác không phải số thường -> LoiNhap."""
    if v in (None, ""):
        return None
    t = str(v).strip()
    if phay_la_thap_phan and _PHAY_THAP_PHAN.match(t):
        t = t.replace(",", ".")
    elif _PHAY_NGHIN.match(t):
        t = t.replace(",", "")
    elif _PHAY_THAP_PHAN.match(t):
        t = t.replace(",", ".")
    if not _SO_THUONG.match(t):
        raise LoiNhap(f"{ten} phải là số.")
    x = Decimal(t)
    if x < 0 or (duong and x == 0):
        raise LoiNhap(f"{ten} không được âm{' hoặc bằng 0' if duong else ''}.")
    return x


def _hai_so_le(x, ten, duong=False):
    """Số đã đọc → đúng dạng một cột numeric(·,2) sẽ lưu: làm tròn 0,01 (nửa lên), '-0' → 0 (`+ 0`). Trường phải > 0
    mà làm tròn thành 0 ('0.001') → LoiNhap — không để CSDL nổ CHECK (500), cũng không để sổ đính chính giữ một số
    mà view (regex không dấu trừ, ≤ 6 chữ số lẻ) bỏ qua. None → None; vô hạn / NaN → LoiNhap."""
    if x is None:
        return None
    if not x.is_finite():
        raise LoiNhap(f"{ten} quá lớn.")
    try:                                                       # quá độ chính xác 28 chữ số → InvalidOperation
        x = x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) + 0
    except InvalidOperation:
        raise LoiNhap(f"{ten} quá lớn.")
    if duong and x <= 0:
        raise LoiNhap(f"{ten} làm tròn 0,01 thành 0 — nhập số lớn hơn.")
    return x


def _chuoi_so(v, ten, duong=False, phay_la_thap_phan=False):
    x = _so(v, ten, duong, phay_la_thap_phan)
    return None if x is None else format(x, "f")


def kiem_bac_nhap(v) -> str:
    """Bậc người nhập (list hoặc chữ JSON) -> chữ JSON chuẩn hoá cho app.dinh_chinh_gia / gia_doi_thu_tay.
    Rỗng / None / [] = xoá bậc ('[]'). Chặt hơn view 067 (view chỉ bỏ qua bậc hỏng — lớp phòng thủ thứ hai)."""
    if v is None:
        v = []
    if isinstance(v, str):
        try:
            v = json.loads(v) if v.strip() else []
        except ValueError:
            raise LoiNhap("Bậc giá không đọc được.")
    if not isinstance(v, list) or len(v) > BAC_TOI_DA:
        raise LoiNhap(f"Bậc giá là danh sách tối đa {BAC_TOI_DA} bậc.")
    ra = []
    for b in v:
        if not isinstance(b, dict) or b.get("don_vi_sl") not in DON_VI_SL or b.get("don_vi_gia") not in DON_VI_GIA_BAC:
            raise LoiNhap("Mỗi bậc cần: từ bao nhiêu (thùng / kg / gói / pallet) và giá (/ thùng / kg / gói).")
        tu, gia = _so(b.get("tu"), "Số lượng của bậc", True), _so(b.get("gia"), "Giá của bậc", True)
        if tu is None or gia is None:
            raise LoiNhap("Bậc giá thiếu số lượng hoặc giá.")
        if tu > SO_BAC_TOI_DA or gia > SO_BAC_TOI_DA:
            raise LoiNhap("Số lượng hoặc giá của bậc quá lớn.")
        ra.append({"tu": int(tu) if tu == tu.to_integral_value() else float(tu), "don_vi_sl": b["don_vi_sl"],
                   "gia": int(gia) if gia == gia.to_integral_value() else float(gia), "don_vi_gia": b["don_vi_gia"]})
    return json.dumps(ra, ensure_ascii=False)


def _kiem(truong: str, v):
    if truong not in TRUONG_SUA:
        raise LoiNhap(f"Không sửa được trường '{truong}'.")
    if truong == "bac":
        return kiem_bac_nhap(v)
    if truong == "so_goi_thung":
        x = _so(v, "Số gói / thùng", True)
        if x is None:
            return None
        if x != x.to_integral_value() or x > GOI_TOI_DA:
            raise LoiNhap(f"Số gói / thùng phải là số nguyên từ 1 đến {GOI_TOI_DA}.")
        return str(int(x))
    if truong == "kl_goi_g":                                   # numeric(10,2) > 0 — sửa và giá tay lưu CÙNG một số
        x = _hai_so_le(_so(v, "Khối lượng 1 gói", True, True), "Khối lượng 1 gói", True)
        if x is not None and x > KL_GOI_TOI_DA:
            raise LoiNhap("Khối lượng 1 gói (g) quá lớn.")
        return None if x is None else format(x, "f")
    if truong == "gia_truoc_km":                               # numeric(12,2) ≥ 0
        x = _hai_so_le(_so(v, "Giá trước khuyến mãi"), "Giá trước khuyến mãi")
        if x is not None and x > GIA_TRUOC_KM_TOI_DA:
            raise LoiNhap("Giá trước khuyến mãi quá lớn.")
        return "" if x is None else format(x, "f")
    if truong == "gia_goc":
        return _chuoi_so(v, "Giá")
    if truong == "kg_moi_don_vi_gia":
        return _chuoi_so(v, "Số kg", True, True)
    for ten, tap in (("thue", THUE), ("gom_ship", SHIP), ("trang_thai", TRANG_THAI)):
        if truong == ten and v not in tap:
            raise LoiNhap(f"{ten} chỉ nhận {', '.join(tap)}.")
    s = (str(v).strip() if v is not None else "")[:DAI_TOI_DA]
    if truong == "ten_goc" and not s:
        raise LoiNhap("Tên hàng không được trống.")
    return s or None


def _ghi_nhat_ky(conn, loai, doi_tuong, truoc, sau, nguoi):
    conn.execute("""INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong, truoc, sau, nguoi_dung_id)
                    VALUES (%s, %s, %s, %s, %s)""",
                 (loai, doi_tuong, json.dumps(truoc, ensure_ascii=False, default=str) if truoc is not None else None,
                  json.dumps(sau, ensure_ascii=False, default=str) if sau is not None else None, nguoi))


# ---------------------------------------------------------------- chống sửa đè (đợt 4b)

_SO_NGUYEN = re.compile(r"[0-9]{1,19}")


def _doc_so_nguyen(v, loi: str) -> int:
    """Số nguyên ≥ 0 trong dải bigint, từ int hoặc chữ số ASCII (không bool / float / chữ số Unicode) — ngoài dải
    thì LoiNhap, không để CSDL nổ 500."""
    if isinstance(v, bool) or not isinstance(v, (int, str)) or not _SO_NGUYEN.fullmatch(str(v).strip()):
        raise LoiNhap(loi)
    x = int(str(v).strip())
    if x >= 2 ** 63:
        raise LoiNhap(loi)
    return x


def doc_da_xem(v) -> int:
    """`da_xem` pop-up gửi lên (sua_cuoi lúc mở) -> int ≥ 0. None / thiếu = 0 (chưa thấy lần sửa nào — kiểm chặt)."""
    return 0 if v is None else _doc_so_nguyen(v, "Mốc đã xem (da_xem) không hợp lệ.")


def doc_id(v, ten: str = "Mã dòng") -> int:
    x = _doc_so_nguyen(v, f"{ten} không hợp lệ.")
    if x == 0:
        raise LoiNhap(f"{ten} không hợp lệ.")
    return x


def kiem_xung_dot(conn, khoa: list[str], da_xem, ghi_de: bool) -> None:
    """Gọi ĐẦU mỗi hàm ghi của pop-up, trong CÙNG giao dịch. Có dòng nhật ký trên `khoa` mới hơn `da_xem` và không
    `ghi_de` -> XungDot (không ghi gì). `da_xem` None = lệnh gọi cũ / script: không kiểm. Không khoá hàng (sổ chỉ
    thêm, không có hàng để khoá): hai người bấm CÙNG lúc thì lần sau thắng, cả hai đều vào nhật ký."""
    if da_xem is None or ghi_de:
        return
    r = conn.execute("""SELECT nk.id, nk.luc, nk.sau, coalesce(sp.ten, nd.ten_dang_nhap)
                        FROM app.doi_thu_nhat_ky nk
                        LEFT JOIN app.nguoi_dung nd ON nd.id = nk.nguoi_dung_id
                        LEFT JOIN core.dim_salesperson sp ON sp.salesperson_code = nd.salesperson_code
                        WHERE nk.doi_tuong = ANY(%s) AND nk.id > %s ORDER BY nk.id DESC LIMIT 1""",
                     (list(khoa), da_xem)).fetchone()
    if r is not None:
        raise XungDot(r[3], r[1].isoformat(), r[2], r[0])


def sua_cuoi_cua(conn, khoa: list[str]) -> int:
    """max(id) nhật ký trên các khoá (0 = chưa ai sửa) — cùng định nghĩa `sua_cuoi` của các câu đọc."""
    return conn.execute("SELECT coalesce(max(id), 0) FROM app.doi_thu_nhat_ky WHERE doi_tuong = ANY(%s)",
                        (list(khoa),)).fetchone()[0]


# ---------------------------------------------------------------- ghi

LOI_DANG_AN = "Dòng này đang bị ẩn — khôi phục trước khi sửa."


def xac_nhan(conn, fact_id: int, nguoi) -> None:
    r = conn.execute("SELECT an FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s", (fact_id,)).fetchone()
    if r is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    if r[0]:                                   # 070: dòng đã ẩn chỉ khôi phục được, không xác nhận / sửa
        raise LoiNhap(LOI_DANG_AN)
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, nguoi_dung_id) VALUES (%s, 'xac_nhan', %s)",
                 (fact_id, nguoi))
    _ghi_nhat_ky(conn, "xac_nhan", f"gia:{fact_id}", None, None, nguoi)


def _kiem_khong_trong(thay_doi: dict) -> None:
    """Dòng NẠP: để trống không xoá được giá trị AI đã đọc (trừ TRUONG_XOA_DUOC)."""
    for k, v in thay_doi.items():
        if k in TRUONG_XOA_DUOC:
            continue
        if v is None or not str(v).strip():
            raise LoiNhap("Để trống không xoá được giá trị AI đã đọc — nhập giá trị đúng, hoặc dùng 'Giá đã đổi'.")


def sua(conn, fact_id: int, thay_doi: dict, nguoi) -> None:
    if not thay_doi:
        raise LoiNhap("Không có gì để sửa.")
    _kiem_khong_trong(thay_doi)
    sach = {k: _kiem(k, v) for k, v in thay_doi.items()}
    sach = {k: ("" if (k in TRUONG_XOA_DUOC and v is None) else v) for k, v in sach.items()}   # '' = xoá (view 067)
    cu = conn.execute(f"SELECT {', '.join(sach)} FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s",
                      (fact_id,)).fetchone()
    if cu is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    with conn.cursor() as cur:
        cur.executemany("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi, nguoi_dung_id) VALUES (%s,%s,%s,%s)",
                        [(fact_id, k, v, nguoi) for k, v in sach.items()])
    _ghi_nhat_ky(conn, "sua", f"gia:{fact_id}", dict(zip(sach, cu)), sach, nguoi)


def gia_moi(conn, du_lieu: dict, nguoi) -> int:
    """'Giá đã đổi' (có fact_goc_id) hoặc 'thêm hàng AI bỏ sót' (có ma_doi_thu + ten_goc). Loại nguồn bắt buộc."""
    ln = du_lieu.get("loai_nguon")
    if not ln or not conn.execute("SELECT 1 FROM app.loai_nguon WHERE ma=%s", (ln,)).fetchone():
        raise LoiNhap("Chọn loại nguồn của giá này.")
    lk = kiem_lien_ket(du_lieu.get("lien_ket_bang_chung"), "Link bằng chứng")
    goc = None
    if du_lieu.get("fact_goc_id"):
        try:
            fact_goc = int(du_lieu["fact_goc_id"])
        except (TypeError, ValueError):
            raise LoiNhap("Mã dòng giá gốc không hợp lệ.")
        goc = conn.execute("""SELECT ma_doi_thu, ma_hang_dt, ten_goc, quy_cach_goc, don_vi_gia, kg_moi_don_vi_gia,
                                     thue, gom_ship, kenh_gia, muc_gia, so_goi_thung, kl_goi_g, an
                              FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s""",
                           (fact_goc,)).fetchone()
        if goc is None:
            raise LoiNhap("Không tìm thấy dòng giá gốc.")
        if goc[-1]:                                   # dòng tay mới sẽ không ẩn → dòng đã xoá lặng lẽ hiện lại (070)
            raise LoiNhap(LOI_DANG_AN)
        goc = goc[:-1]
    k = ("ma_doi_thu", "ma_hang_dt", "ten_goc", "quy_cach_goc", "don_vi_gia", "kg_moi_don_vi_gia",
         "thue", "gom_ship", "kenh_gia", "muc_gia", "so_goi_thung", "kl_goi_g")
    v = dict(zip(k, goc)) if goc else {}
    for truong in TRUONG_SUA:
        if truong in du_lieu and truong != "trang_thai":
            v[truong] = _kiem(truong, du_lieu[truong])
    if v.get("bac") == "[]":
        v["bac"] = None                                       # bậc rỗng = không có bậc (cột jsonb NULL)
    for truong in ("khuyen_mai", "gia_truoc_km"):
        v[truong] = v.get(truong) or None
    v["ma_doi_thu"] = v.get("ma_doi_thu") or du_lieu.get("ma_doi_thu")
    if not v.get("ma_doi_thu") or not v.get("ten_goc"):
        raise LoiNhap("Thiếu đối thủ hoặc tên hàng.")
    if not v.get("ma_hang_dt"):
        v["ma_hang_dt"] = "ten:" + chuan_ten(v["ten_goc"]) + "|" + chuan_ten(v.get("quy_cach_goc") or "")
    tt = _kiem("trang_thai", du_lieu.get("trang_thai") or "con")
    if v.get("gia_goc") is None and tt != "het":
        raise LoiNhap("Nhập giá (chỉ được bỏ trống khi ghi hàng đã hết).")
    tid = conn.execute(
        """INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, fact_goc_id, ten_goc, quy_cach_goc, gia_goc,
             don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia, trang_thai, loai_nguon,
             ghi_chu_nguon, lien_ket_bang_chung, so_goi_thung, kl_goi_g, bac, khuyen_mai, gia_truoc_km, nguoi_dung_id)
           VALUES (%(ma_doi_thu)s, %(ma_hang_dt)s, %(fact_goc_id)s, %(ten_goc)s, %(quy_cach_goc)s, %(gia_goc)s,
             %(don_vi_gia)s, %(kg_moi_don_vi_gia)s, %(thue)s, %(gom_ship)s, %(kenh_gia)s, %(muc_gia)s,
             %(trang_thai)s, %(loai_nguon)s, %(ghi_chu_nguon)s, %(lien_ket_bang_chung)s, %(so_goi_thung)s, %(kl_goi_g)s,
             %(bac)s::jsonb, %(khuyen_mai)s, %(gia_truoc_km)s, %(nguoi)s) RETURNING id""",
        {**{x: v.get(x) for x in k}, "bac": v.get("bac"), "khuyen_mai": v.get("khuyen_mai"), "gia_truoc_km": v.get("gia_truoc_km"),
         "gia_goc": v.get("gia_goc"), "fact_goc_id": fact_goc if goc else None,
         "trang_thai": tt, "loai_nguon": ln, "ghi_chu_nguon": (du_lieu.get("ghi_chu_nguon") or "")[:DAI_TOI_DA] or None,
         "lien_ket_bang_chung": lk, "nguoi": nguoi}).fetchone()[0]
    _ghi_nhat_ky(conn, "gia_moi" if goc else "them", f"tay:{tid}", None, v | {"loai_nguon": ln, "lien_ket_bang_chung": lk}, nguoi)
    return tid


DON_VI_GIA_KE = ("kg", "tui", "goi", "con", "qua", "thung", "lon", "chai", "hop", "cay", "bao", "khac")
GIA_KE_TOI_DA = Decimal("9999999")
# Khoá của thẻ / giá: fullmatch (KHÔNG `$` — nó khớp trước dấu xuống dòng cuối) và không khoảng trắng /
# ký tự điều khiển; sổ app.tiep_xuc_nhac chỉ-thêm nên một khoá bẩn ở lại vĩnh viễn.
KHOA_SACH = re.compile(r"[^\s\x00-\x1f\x7f\ud800-\udfff]+")          # + surrogate lẻ (JSON "\ud800") -> 400, không 500
KHOA_NHOM = re.compile(r"(ma:[^\s\x00-\x1f\x7f\ud800-\udfff]+|n:[0-9]{1,15})")

LIEN_KET_TOI_DA = 2000
_LIEN_KET = re.compile(r"https://[^\s\x00-\x1f\x7f\ud800-\udfff]+")
_THANG = re.compile(r"(19|20)\d{2}-(0[1-9]|1[0-2])")  # Postgres không có năm 0; 1900–2099


def kiem_lien_ket(v, ten: str):
    """Link ra ngoài (Drive, ảnh bằng chứng): rỗng → None; chỉ https://, không khoảng trắng / ký tự điều khiển /
    surrogate lẻ, ≤ LIEN_KET_TOI_DA. CHECK của 064 chặn lần nữa ở CSDL; giao diện kiểm lại lúc vẽ."""
    if v is None or v == "":
        return None
    if not isinstance(v, str) or len(v) > LIEN_KET_TOI_DA or not _LIEN_KET.fullmatch(v):
        raise LoiNhap(f"{ten} phải là một link https:// (dán nguyên link Google Drive).")
    return v


def dat_thu_muc(conn, thang, lien_ket, nguoi) -> None:
    """Link thư mục Drive "Tháng N" (đặc tả §11). Sửa được; mỗi lần ghi thêm một dòng nhật ký trong CÙNG giao dịch."""
    if not isinstance(thang, str) or not _THANG.fullmatch(thang):
        raise LoiNhap("Tháng phải có dạng YYYY-MM.")
    lk = kiem_lien_ket(lien_ket, "Link thư mục")
    if lk is None:
        raise LoiNhap("Dán link thư mục Google Drive của tháng.")
    ngay = f"{thang}-01"
    cu = conn.execute("SELECT lien_ket FROM app.thu_muc_nguon WHERE thang = %s", (ngay,)).fetchone()
    conn.execute("""INSERT INTO app.thu_muc_nguon (thang, lien_ket, sua_luc, sua_boi) VALUES (%s, %s, now(), %s)
                    ON CONFLICT (thang) DO UPDATE SET lien_ket = EXCLUDED.lien_ket, sua_luc = now(),
                      sua_boi = EXCLUDED.sua_boi""", (ngay, lk, nguoi))
    _ghi_nhat_ky(conn, "thu_muc", f"thang:{thang}", {"lien_ket": cu[0]} if cu else None, {"lien_ket": lk}, nguoi)


def gia_khach_ke(conn, ma_doi_thu: str, nhom_khoa: str, customer_code: str, tiep_xuc_id: int,
                 gia_goc, don_vi_gia: str, nguoi) -> int:
    """Giá khách kể (tin hiện trường `@`, đợt 2 — 063): một dòng `app.gia_doi_thu_tay` `loai_nguon='khach_ke'`.

    `ma_hang_dt` LƯU = 'ke:<khách>:<nhóm_khoa đã ghi>'; view 063 dựng lại khoá chuỗi LÚC ĐỌC theo nhóm HIỆN HÀNH
    ('ke:<khách>:<mart.nhom_cua_khoa(...)>') -> phân vùng `hien_hanh` tách theo (khách, bên, nhóm thật): tin trùng
    thì mới nhất là hiện trạng (kể cả lần gắn `ma:<mã>` rồi lần gắn `n:<nhóm>`), hai khách khác nhau không đè nhau. `nhom_khoa` ('ma:<mã KOME>' | 'n:<id>') đi thẳng
    vào cột `nhom_khoa` — không qua bước ghép. `kg_moi_don_vi_gia` = 1 khi đơn vị là kg, NULL khi khác (máy không
    đoán kg của gói / thùng); thuế / ship `khong_ro`. Cùng giao dịch: thêm một dòng nhật ký 'gia_moi'.
    Người gọi chịu trách nhiệm chuyện thẻ `@` (xem `lien_he.ghi_kem_nhac`); ở đây chỉ kiểm chính dòng giá."""
    if not isinstance(nhom_khoa, str) or not KHOA_NHOM.fullmatch(nhom_khoa):
        raise LoiNhap("Nhóm hàng sai định dạng (ma:<mã> hoặc n:<số>).")
    gia = _so(gia_goc, "Giá", duong=True)
    if gia is None:
        raise LoiNhap("Nhập giá.")
    if gia > GIA_KE_TOI_DA:
        raise LoiNhap("Giá quá lớn — kiểm lại số.")
    if don_vi_gia not in DON_VI_GIA_KE:
        raise LoiNhap(f"Đơn vị giá chỉ nhận: {', '.join(DON_VI_GIA_KE)}.")
    if not isinstance(ma_doi_thu, str) or not KHOA_SACH.fullmatch(ma_doi_thu) or conn.execute(
            "SELECT 1 FROM app.doi_thu WHERE ma = %s", (ma_doi_thu,)).fetchone() is None:
        raise LoiNhap(f"Không có đối thủ '{ma_doi_thu}'.")
    ten = conn.execute(
        """SELECT CASE WHEN left(%(k)s, 2) = 'n:'
                       THEN (SELECT ten FROM app.nhom_so_sanh WHERE id = substr(%(k)s, 3)::bigint)
                       ELSE (SELECT coalesce(nullif(product_name, ''), product_code) FROM core.dim_product
                             WHERE product_code = substr(%(k)s, 4)) END""", {"k": nhom_khoa}).fetchone()[0]
    if ten is None:
        raise LoiNhap(f"Không có nhóm hàng '{nhom_khoa}'.")
    tid = conn.execute(
        """INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia,
             thue, gom_ship, trang_thai, loai_nguon, customer_code, tiep_xuc_id, nhom_khoa, nguoi_dung_id)
           VALUES (%s, %s, %s, %s, %s, %s, 'khong_ro', 'khong_ro', 'con', 'khach_ke', %s, %s, %s, %s) RETURNING id""",
        (ma_doi_thu, f"ke:{customer_code}:{nhom_khoa}", ten, gia, don_vi_gia, 1 if don_vi_gia == "kg" else None,
         customer_code, tiep_xuc_id, nhom_khoa, nguoi)).fetchone()[0]
    _ghi_nhat_ky(conn, "gia_moi", f"tay:{tid}", None,
                 {"ma_doi_thu": ma_doi_thu, "nhom_khoa": nhom_khoa, "gia_goc": gia, "don_vi_gia": don_vi_gia,
                  "loai_nguon": "khach_ke", "customer_code": customer_code, "tiep_xuc_id": tiep_xuc_id}, nguoi)
    return tid


def dat_ghep(conn, ma_doi_thu: str, ma_hang_dt: str, product_code, nhom_id, nhan: str, nguoi) -> None:
    if nhan not in NHAN:
        raise LoiNhap("Nhãn ghép chỉ nhận cùng hàng / thay thế / không ghép.")
    if product_code is not None and product_code != "" and conn.execute(
            "SELECT 1 FROM core.dim_product WHERE product_code=%s", (product_code,)).fetchone() is None:
        raise LoiNhap(f"Không có mã KOME '{product_code}'.")
    cu = conn.execute("SELECT product_code, nhom_id, nhan FROM app.ghep_hang WHERE ma_doi_thu=%s AND ma_hang_dt=%s",
                      (ma_doi_thu, ma_hang_dt)).fetchone()
    conn.execute("""INSERT INTO app.ghep_hang (ma_doi_thu, ma_hang_dt, product_code, nhom_id, nhan, nguoi_dung_id)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (ma_doi_thu, ma_hang_dt) DO UPDATE SET product_code=EXCLUDED.product_code,
                      nhom_id=EXCLUDED.nhom_id, nhan=EXCLUDED.nhan, nguoi_dung_id=EXCLUDED.nguoi_dung_id, luc=now()""",
                 (ma_doi_thu, ma_hang_dt, product_code or None, nhom_id or None, nhan, nguoi))
    _ghi_nhat_ky(conn, "ghep", f"{ma_doi_thu}/{ma_hang_dt}",
                 dict(zip(("product_code", "nhom_id", "nhan"), cu)) if cu else None,
                 {"product_code": product_code, "nhom_id": nhom_id, "nhan": nhan}, nguoi)


def _kiem_ma_kome(conn, ma_kome) -> list[str]:
    """Mọi mã phải có trong core.dim_product — mã gõ nhầm không được vào nhóm (nhóm rỗng lặng lẽ)."""
    if not isinstance(ma_kome, (list, tuple)):
        raise LoiNhap("Danh sách mã KOME phải là một danh sách.")
    ma = [str(m).strip() for m in ma_kome]
    if any(not m for m in ma):
        raise LoiNhap("Có mã KOME để trống.")
    ma = list(dict.fromkeys(ma))
    if ma:
        co = {r[0] for r in conn.execute("SELECT product_code FROM core.dim_product WHERE product_code = ANY(%s)", (ma,))}
        for m in ma:
            if m not in co:
                raise LoiNhap(f"Không có mã KOME '{m}'.")
    return ma


def _nhom_cu(conn, ma: list[str]) -> dict:
    """{mã: nhom_id} của những mã ĐANG thuộc một nhóm — cột `truoc` của nhật ký."""
    if not ma:
        return {}
    return dict(conn.execute("SELECT product_code, nhom_id FROM app.nhom_so_sanh_ma WHERE product_code = ANY(%s)",
                             (ma,)).fetchall())


def tao_nhom(conn, ten: str, ma_kome: list[str], nguoi) -> int:
    ten = (ten or "").strip()
    if not 1 <= len(ten) <= 80:
        raise LoiNhap("Tên nhóm dài 1–80 ký tự.")
    ma_kome = _kiem_ma_kome(conn, ma_kome)
    if conn.execute("SELECT 1 FROM app.nhom_so_sanh WHERE lower(btrim(ten)) = lower(%s)", (ten,)).fetchone():
        raise LoiNhap("Đã có nhóm tên này.")
    cu = _nhom_cu(conn, ma_kome)
    nid = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES (%s) RETURNING id", (ten,)).fetchone()[0]
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.nhom_so_sanh_ma (product_code, nhom_id) VALUES (%s, %s)
                           ON CONFLICT (product_code) DO UPDATE SET nhom_id = EXCLUDED.nhom_id""",
                        [(m, nid) for m in ma_kome])
    _ghi_nhat_ky(conn, "nhom", f"nhom:{nid}", cu or None, {"ten": ten, "ma_kome": ma_kome}, nguoi)
    return nid


def them_ma_nhom(conn, nhom_id: int, ma_kome: list[str], nguoi) -> None:
    """Thêm mã vào một nhóm có sẵn; mã đang ở nhóm khác thì được CHUYỂN sang (mỗi mã một nhóm)."""
    ten = conn.execute("SELECT ten FROM app.nhom_so_sanh WHERE id=%s", (nhom_id,)).fetchone()
    if ten is None:
        raise LoiNhap("Không có nhóm này.")
    ma = _kiem_ma_kome(conn, ma_kome)
    if not ma:
        raise LoiNhap("Chọn ít nhất một mã KOME.")
    cu = _nhom_cu(conn, ma)
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.nhom_so_sanh_ma (product_code, nhom_id) VALUES (%s, %s)
                           ON CONFLICT (product_code) DO UPDATE SET nhom_id = EXCLUDED.nhom_id""",
                        [(m, nhom_id) for m in ma])
    _ghi_nhat_ky(conn, "nhom", f"nhom:{nhom_id}", cu or None, {"ten": ten[0], "ma_kome": ma}, nguoi)


def bo_ma_nhom(conn, product_code: str, nguoi) -> None:
    r = conn.execute("DELETE FROM app.nhom_so_sanh_ma WHERE product_code=%s RETURNING nhom_id", (product_code,)).fetchone()
    if r is None:
        raise LoiNhap("Mã này không thuộc nhóm nào.")
    _ghi_nhat_ky(conn, "nhom", f"nhom:{r[0]}", {product_code: r[0]}, {"bo_ma": product_code}, nguoi)


_COT_QC = ("kg_moi_goi", "goi_moi_thung", "kg_moi_thung")
_SCALE_QC = (Decimal("0.0001"), Decimal("0.01"), Decimal("0.0001"))    # độ chính xác cột app.quy_cach_kome


def sua_quy_cach(conn, product_code: str, kg_moi_goi, goi_moi_thung, kg_moi_thung, nguoi) -> None:
    """Lưu số quy cách người sửa. Biểu mẫu gửi lại CẢ BA ô, điền sẵn từ mart.quy_cach_kome (gồm giá trị SUY RA từ tên /
    荷姿). Ô nào bằng giá trị hiệu lực hiện tại (so bằng số, theo độ chính xác của cột) = "không sửa": giữ nguyên số người
    sửa ĐÃ CÓ của ô đó (NULL nếu chưa có) — không ghim số suy ra thành số "người sửa" (066 không cho nó thắng 荷姿).
    Ô khác giá trị hiệu lực = người sửa; ô để trống = xoá số người sửa."""
    gui = (_so(kg_moi_goi, "Kg mỗi gói", True, True), _so(goi_moi_thung, "Gói mỗi thùng", True),
           _so(kg_moi_thung, "Kg mỗi thùng", True, True))
    cu = conn.execute("SELECT kg_moi_goi, goi_moi_thung, kg_moi_thung FROM mart.quy_cach_kome WHERE product_code=%s",
                      (product_code,)).fetchone()
    if cu is None:
        raise LoiNhap("Không có mã KOME này.")
    co = conn.execute("SELECT kg_moi_goi, goi_moi_thung, kg_moi_thung FROM app.quy_cach_kome WHERE product_code=%s",
                      (product_code,)).fetchone() or (None, None, None)

    def _q(x, i):
        return None if x is None else Decimal(x).quantize(_SCALE_QC[i])

    moi = tuple(co[i] if (gui[i] is not None and cu[i] is not None and _q(gui[i], i) == _q(cu[i], i)) else gui[i]
                for i in range(3))
    doi = [i for i in range(3) if _q(moi[i], i) != _q(co[i], i)]
    if not doi:
        return
    if all(x is None for x in moi):
        conn.execute("DELETE FROM app.quy_cach_kome WHERE product_code=%s", (product_code,))
    else:
        conn.execute("""INSERT INTO app.quy_cach_kome (product_code, kg_moi_goi, goi_moi_thung, kg_moi_thung)
                        VALUES (%s,%s,%s,%s)
                        ON CONFLICT (product_code) DO UPDATE SET kg_moi_goi=EXCLUDED.kg_moi_goi,
                          goi_moi_thung=EXCLUDED.goi_moi_thung, kg_moi_thung=EXCLUDED.kg_moi_thung""",
                     (product_code, *moi))
    _ghi_nhat_ky(conn, "quy_cach", product_code, {_COT_QC[i]: cu[i] for i in doi}, {_COT_QC[i]: moi[i] for i in doi}, nguoi)


# ---------------------------------------------------------------- ghi từ pop-up (đợt 4b): một giao dịch, chống sửa đè

TRUONG_BEN = ("ten", "web", "ghi_chu")
TEN_BEN_TOI_DA = 80


def sua_ben(conn, ma: str, du_lieu: dict, nguoi, da_xem=None, ghi_de: bool = False) -> None:
    """Thông tin một bên đối thủ (app.doi_thu — bảng cấu hình của app, UPDATE). Chỉ ghi trường ĐỔI; nhật ký
    loai 'doi_thu', khoá 'ben:<mã>'. web '' = xoá (NULL); ghi_chu '' = xoá. app.doi_thu KHÔNG có trong
    anh_chup._PHIEN_BAN: ảnh chụp đổi nhờ dòng nhật ký cùng giao dịch (nếp 064) — mọi đường ghi phải đi qua hàm này."""
    if not isinstance(du_lieu, dict) or not du_lieu:
        raise LoiNhap("Không có gì để sửa.")
    for k in du_lieu:
        if k not in TRUONG_BEN:
            raise LoiNhap(f"Không sửa được trường '{k}'.")
    moi = {}
    if "ten" in du_lieu:
        t = du_lieu["ten"]
        if not isinstance(t, str) or not 1 <= len(t.strip()) <= TEN_BEN_TOI_DA:
            raise LoiNhap(f"Tên đối thủ dài 1–{TEN_BEN_TOI_DA} ký tự.")
        moi["ten"] = t.strip()
    if "web" in du_lieu:
        try:
            moi["web"] = kiem_lien_ket(du_lieu["web"], "Trang web")
        except LoiNhap:
            raise LoiNhap("Trang web phải là một link https:// (để trống = xoá).")
    if "ghi_chu" in du_lieu:
        g = "" if du_lieu["ghi_chu"] is None else du_lieu["ghi_chu"]
        if not isinstance(g, str) or len(g.strip()) > DAI_TOI_DA:
            raise LoiNhap(f"Ghi chú tối đa {DAI_TOI_DA} ký tự.")
        moi["ghi_chu"] = g.strip() or None
    kiem_xung_dot(conn, [f"ben:{ma}"], da_xem, ghi_de)
    r = conn.execute("SELECT ten, web, ghi_chu FROM app.doi_thu WHERE ma = %s", (ma,)).fetchone()
    if r is None:
        raise LoiNhap("Không có đối thủ này.")
    cu = dict(zip(TRUONG_BEN, r))
    doi = {k: v for k, v in moi.items() if v != cu[k]}
    if not doi:
        raise LoiNhap("Không có gì để sửa.")
    conn.execute(f"UPDATE app.doi_thu SET {', '.join(f'{k} = %s' for k in doi)} WHERE ma = %s", [*doi.values(), ma])
    _ghi_nhat_ky(conn, "doi_thu", f"ben:{ma}", {k: cu[k] for k in doi}, doi, nguoi)


_COT_TAY = ("ma_doi_thu", "ma_hang_dt", "fact_goc_id", "ten_goc", "quy_cach_goc", "gia_goc", "don_vi_gia",
            "kg_moi_don_vi_gia", "thue", "gom_ship", "kenh_gia", "muc_gia", "trang_thai", "loai_nguon", "ghi_chu_nguon",
            "customer_code", "tiep_xuc_id", "nhom_khoa", "lien_ket_bang_chung", "so_goi_thung", "kl_goi_g", "bac",
            "khuyen_mai", "gia_truoc_km")
_NGUON_TAY = ("loai_nguon", "lien_ket_bang_chung", "ghi_chu_nguon")


def _kiem_loai_nguon(conn, ln) -> str:
    if not ln or not isinstance(ln, str) or not conn.execute("SELECT 1 FROM app.loai_nguon WHERE ma=%s", (ln,)).fetchone():
        raise LoiNhap("Chọn loại nguồn của giá này.")
    return ln


def sua_tay(conn, tay_id: int, thay_doi: dict, nguoi, *, nguon: dict | None = None) -> int:
    """Sửa một dòng `app.gia_doi_thu_tay` (sổ CHỈ THÊM) = thêm dòng MỚI: chép dòng cũ (cùng bên / hàng / fact_goc_id /
    loại nguồn / nhóm / khách / tiếp xúc / link bằng chứng), áp `thay_doi` (TRUONG_SUA, qua `_kiem`), đặt
    `thay_cho_tay_id` = dòng cũ — mart.gia_doi_thu_quan_sat (067) không bao giờ cho dòng bị thay hiện hành, kể cả khi
    dòng mới sang phân vùng khác (sửa kênh / mức giá). "Đọc sai" (mặc định) giữ `luc` của dòng cũ (ngày nguồn / tuổi
    không đổi — vẫn là quan sát đó); `nguon` (đường 'Giá đã đổi' của pop-up) = now(), loai_nguon bắt buộc,
    lien_ket_bang_chung = đúng link gửi kèm (không gửi = không có — KHÔNG chép link của giá cũ), ghi_chu_nguon ghi đè
    khi CÓ khoá. Nhật ký HAI dòng — khoá 'tay:<cũ>' và 'tay:<mới>' — để sua_cuoi của cả hai khớp (pop-up cũ của dòng
    cũ bị 409). Trả id mới."""
    thay_doi = thay_doi or {}
    if not isinstance(thay_doi, dict):
        raise LoiNhap("Trường sửa phải là một đối tượng.")
    if not thay_doi and not nguon:
        raise LoiNhap("Không có gì để sửa.")
    sach = {k: _kiem(k, v) for k, v in thay_doi.items()}
    r = conn.execute(f"SELECT {', '.join(_COT_TAY)}, luc FROM app.gia_doi_thu_tay WHERE id = %s", (tay_id,)).fetchone()
    if r is None:
        raise LoiNhap("Không tìm thấy dòng giá này.")
    cu = dict(zip(_COT_TAY, r))
    luc_cu = r[-1]
    v = dict(cu)
    for k, x in sach.items():
        if k == "bac":
            x = None if x == "[]" else x                          # bậc rỗng = không có bậc (jsonb NULL, nếp gia_moi)
        elif k in ("khuyen_mai", "gia_truoc_km"):
            x = x or None
        v[k] = x
    if v["bac"] is not None and not isinstance(v["bac"], str):
        v["bac"] = json.dumps(v["bac"], ensure_ascii=False)     # jsonb đọc ra là list — chép lại nguyên văn
    doi = list(sach)
    if nguon:
        v["loai_nguon"] = _kiem_loai_nguon(conn, nguon.get("loai_nguon"))
        # Link bằng chứng thuộc về NGUỒN của giá: giá mới không mang link của giá cũ — không gửi = không có.
        v["lien_ket_bang_chung"] = kiem_lien_ket(nguon.get("lien_ket_bang_chung"), "Link bằng chứng")
        if "ghi_chu_nguon" in nguon:
            g = nguon.get("ghi_chu_nguon")
            v["ghi_chu_nguon"] = (g.strip()[:DAI_TOI_DA] if isinstance(g, str) else "") or None
        doi += [k for k in _NGUON_TAY if k in nguon or k in ("loai_nguon", "lien_ket_bang_chung")]
    if v["gia_goc"] is None and v["trang_thai"] != "het":
        raise LoiNhap("Nhập giá (chỉ được bỏ trống khi ghi hàng đã hết).")
    moi = conn.execute(
        f"""INSERT INTO app.gia_doi_thu_tay ({', '.join(_COT_TAY)}, nguoi_dung_id, thay_cho_tay_id, luc)
            VALUES ({', '.join('%s::jsonb' if k == 'bac' else '%s' for k in _COT_TAY)}, %s, %s, coalesce(%s, now()))
            RETURNING id""",
        [v[k] for k in _COT_TAY] + [nguoi, tay_id, None if nguon else luc_cu]).fetchone()[0]
    truoc = {k: cu[k] for k in doi}
    sau = {k: v[k] for k in doi} | {"tay_cu": tay_id, "tay_moi": moi}
    for khoa in (f"tay:{tay_id}", f"tay:{moi}"):
        _ghi_nhat_ky(conn, "gia_moi" if nguon else "sua", khoa, truoc, sau, nguoi)
    return moi


TRUONG_GIA = frozenset({"gia_goc", "don_vi_gia", "thue", "bac"})
VI_SAO_GIA = ("doc_sai", "da_doi")


def _doc_ma_kome(v):
    """Ô "Mã KOME" của pop-up: None / "" = bỏ mã; chữ (strip) ≤ DAI_TOI_DA; kiểu khác -> LoiNhap."""
    if v is None or v == "":
        return None
    if not isinstance(v, str) or len(v.strip()) > DAI_TOI_DA:
        raise LoiNhap("Mã KOME không hợp lệ.")
    return v.strip() or None


def sua_mat_hang(conn, b: dict, nguoi) -> dict:
    """MỘT lần bấm Lưu ở pop-up mặt hàng: ghép + sửa trường, CÙNG giao dịch (route commit một lần; lỗi ở bước nào thì
    không bước nào vào). Mọi phép kiểm đầu vào đã biết — trường, vì sao, loại nguồn, link / ghi chú nguồn, "có giá trừ
    khi hết", mã KOME / nhóm và loại dòng của ghép — chạy TRƯỚC lần ghi đầu tiên; sau đó chỉ còn lỗi CSDL ngoài dự
    kiến (khi ấy vẫn không commit). `b`:
      nguon 'nap'|'tay', id, da_xem (sua_cuoi lúc mở), ghi_de, nhan ('cung_hang'|'thay_the'|'khong'|null),
      ma_kome (CÓ khoá = đổi mã KOME của ghép; null / "" = bỏ mã), nhom_id (CÓ khoá = đổi nhóm ghép tường minh; null =
      theo mã KOME), thay_doi {TRUONG_SUA: giá trị}, vi_sao_gia ('doc_sai'|'da_doi'|null — bắt buộc khi thay_doi có
      TRUONG_GIA), loai_nguon / lien_ket_bang_chung / ghi_chu_nguon (đường 'da_doi').
    Ghép (B13, thay khung "Ghép với KOME" cũ của Duyệt — cùng luật `dat_ghep` của /ghep): mã phải có trong
    core.dim_product, nhóm trong app.nhom_so_sanh; nhãn khác 'khong' cần mã; đổi sang mã MỚI thì phải chọn cùng / khác
    thương hiệu (không lặng lẽ cất mã mới dưới nhãn 'khong'); giá khách kể đã mang nhóm (thẻ @hàng) không ghép lại ở
    đây. Khoá nhật ký / 409 = '<bên>/<hàng>' như cũ.
    Dòng ĐÃ BỊ THAY (B14 — dòng tay có bản sửa, dòng nạp có "giá đã đổi") -> XungDot(thay_boi=bản mới nhất), kể cả
    ghi_de: sửa bản cũ là tách nhánh lặng lẽ đè bản của người khác. Dòng ĐANG ẨN (070) -> LoiNhap(LOI_DANG_AN): chỉ khôi
    phục được (dat_an), không sửa.
    doc_sai: dòng nạp -> app.dinh_chinh_gia (`sua`), dòng tay -> dòng tay mới (`sua_tay`). da_doi: dòng nạp ->
    `gia_moi` (fact_goc_id; giá / trạng thái hiện hành làm nền để đổi mỗi thuế / đơn vị vẫn ghi được) + một dòng nhật
    ký 'gia:<id>' (pop-up cũ của dòng nạp đó bị 409 — nó không còn là hiện hành); dòng tay -> `sua_tay` với loại nguồn
    mới. Trả {nguon, id, sua_cuoi} của dòng pop-up nên hiện tiếp (dòng tay mới khi có)."""
    if not isinstance(b, dict):
        raise LoiNhap("Thân yêu cầu phải là một đối tượng JSON.")
    nguon = b.get("nguon")
    if nguon not in ("nap", "tay"):
        raise LoiNhap("Nguồn chỉ nhận nap / tay.")
    id_ = doc_id(b.get("id"))
    da_xem = doc_da_xem(b.get("da_xem"))
    ghi_de = b.get("ghi_de") is True
    nhan = b.get("nhan") or None
    if nhan is not None and nhan not in NHAN:
        raise LoiNhap("Nhãn ghép chỉ nhận cùng hàng / thay thế / không ghép.")
    co_ma, co_nhom = "ma_kome" in b, "nhom_id" in b
    ma_vao = _doc_ma_kome(b.get("ma_kome")) if co_ma else None
    nhom_vao = (None if b.get("nhom_id") in (None, "") else doc_id(b.get("nhom_id"), "Nhóm so sánh")) if co_nhom else None
    thay_doi = b.get("thay_doi") or {}
    if not isinstance(thay_doi, dict):
        raise LoiNhap("Trường sửa phải là một đối tượng.")
    vi_sao = b.get("vi_sao_gia") or None
    if vi_sao is not None and vi_sao not in VI_SAO_GIA:
        raise LoiNhap("Vì sao đổi giá chỉ nhận: đọc sai / giá đã đổi.")
    if TRUONG_GIA & set(thay_doi) and vi_sao is None:
        raise LoiNhap("Chọn vì sao đổi giá.")
    # Kiểm hết TRƯỚC lần ghi đầu tiên (dat_ghep): một phần hỏng thì không phần nào vào, kể cả khi người gọi lỡ commit.
    for k, v in thay_doi.items():
        _kiem(k, v)
    if nguon == "nap" and vi_sao != "da_doi":
        _kiem_khong_trong(thay_doi)
    if vi_sao == "da_doi" and thay_doi:
        _kiem_loai_nguon(conn, b.get("loai_nguon"))
        kiem_lien_ket(b.get("lien_ket_bang_chung"), "Link bằng chứng")
        if b.get("ghi_chu_nguon") is not None and not isinstance(b.get("ghi_chu_nguon"), str):
            raise LoiNhap("Ghi chú nguồn phải là chữ.")

    r = conn.execute(f"""SELECT q.ma_doi_thu, q.ma_hang_dt, q.ma_kome, q.nhan, q.gia_goc, q.trang_thai,
                                g.product_code, g.nhom_id, q.loai_nguon, q.nhom_khoa, {_thay_boi_sql('q.nguon', 'q.id')},
                                q.an
                         FROM mart.gia_doi_thu_quan_sat q LEFT JOIN app.ghep_hang g USING (ma_doi_thu, ma_hang_dt)
                         WHERE q.nguon = %s AND q.id = %s""", (nguon, id_)).fetchone()
    if r is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    ben, hang, ma_kome, nhan_cu, gia_cu, trang_thai_cu, ghep_ma, ghep_nhom, loai_nguon_cu, nhom_khoa_cu, thay_boi, da_an = r
    khoa_dong = f"{'gia' if nguon == 'nap' else 'tay'}:{id_}"
    khoa_ghep = f"{ben}/{hang}"
    if thay_boi is not None:
        # ai / lúc / đổi gì: lần ghi mới nhất trên khoá của dòng cũ (sua_tay / 'giá đã đổi' ghi cả nó), không có (giá mới
        # ghi từ đường cũ /gia-moi) thì trên khoá của bản mới.
        nk = conn.execute("""SELECT nk.id, nk.luc, nk.sau, coalesce(sp.ten, nd.ten_dang_nhap)
                             FROM app.doi_thu_nhat_ky nk
                             LEFT JOIN app.nguoi_dung nd ON nd.id = nk.nguoi_dung_id
                             LEFT JOIN core.dim_salesperson sp ON sp.salesperson_code = nd.salesperson_code
                             WHERE nk.doi_tuong = ANY(%s)
                             ORDER BY (nk.doi_tuong = %s) DESC, nk.id DESC LIMIT 1""",
                          ([khoa_dong, f"tay:{thay_boi['id']}"], khoa_dong)).fetchone()
        raise XungDot(nk[3] if nk else None, nk[1].isoformat() if nk else "", nk[2] if nk else None,
                      sua_cuoi_cua(conn, [khoa_dong, khoa_ghep]), thay_boi=thay_boi)
    if da_an:
        # 070: dòng đã ẨN chỉ khôi phục được (dat_an). Sửa nó thì lỗi lọt qua: dòng tay mới / giá đã đổi mang id mới,
        # không có trong sổ ẩn, nên "sửa một dòng đã xoá" lặng lẽ làm nó hiện lại. Kiểm SAU thay_boi: dòng đã bị thay
        # thì 409 mời mở bản mới có ích hơn.
        raise LoiNhap(LOI_DANG_AN)
    ke_da_nhom = loai_nguon_cu == "khach_ke" and nhom_khoa_cu is not None
    ma_hien = ma_kome if ma_kome is not None else ghep_ma      # mã đang dùng / mã đã nhớ ở lần bỏ nhóm trước
    ma_moi = ma_vao if co_ma else ma_hien
    nhom_moi = nhom_vao if co_nhom else ghep_nhom
    doi_ma, doi_nhom = ma_moi != ma_hien, nhom_moi != ghep_nhom
    doi_nhan = nhan is not None and nhan != nhan_cu
    nhan_moi = nhan if nhan is not None else (nhan_cu or "khong")
    doi_ghep = doi_nhan or doi_ma or doi_nhom
    if not doi_ghep and not thay_doi:
        raise LoiNhap("Không có gì để sửa.")
    if ke_da_nhom and (doi_ma or doi_nhom or (doi_nhan and nhan == "khong")):
        raise LoiNhap("Giá khách kể không bỏ ghép / ghép lại được ở đây.")   # nhóm của nó là thẻ @hàng (nhom_ke)
    if doi_ghep and nhan_moi != "khong" and ma_moi is None:
        raise LoiNhap("Chọn mã KOME trước.")
    if doi_ma and ma_moi is not None and nhan_moi == "khong":
        raise LoiNhap("Ghép với mã mới: chọn cùng thương hiệu hoặc khác thương hiệu.")
    if doi_ma and ma_moi is not None and conn.execute(
            "SELECT 1 FROM core.dim_product WHERE product_code=%s", (ma_moi,)).fetchone() is None:
        raise LoiNhap(f"Không có mã KOME '{ma_moi}'.")
    if doi_nhom and nhom_moi is not None and conn.execute(
            "SELECT 1 FROM app.nhom_so_sanh WHERE id=%s", (nhom_moi,)).fetchone() is None:
        raise LoiNhap("Không có nhóm so sánh này (có thể vừa bị xoá).")
    if thay_doi and (nguon == "tay" or vi_sao == "da_doi"):          # đường thêm dòng app.gia_doi_thu_tay
        gia = _kiem("gia_goc", thay_doi["gia_goc"]) if "gia_goc" in thay_doi else gia_cu
        tt = thay_doi.get("trang_thai", trang_thai_cu) or "con"
        if gia is None and tt != "het":
            raise LoiNhap("Nhập giá (chỉ được bỏ trống khi ghi hàng đã hết).")
    kiem_xung_dot(conn, [khoa_dong, khoa_ghep], da_xem, ghi_de)

    if doi_ghep:
        # Không gửi mã / nhóm: mã hiện hành (hoặc mã đã lưu ở lần 'khong' trước — bỏ nhóm rồi ghép lại vẫn nhớ mã), nhóm
        # ghép tường minh giữ nguyên; nhóm ngầm định (mã thuộc nhóm có tên) đi theo mã như cũ.
        dat_ghep(conn, ben, hang, ma_moi, nhom_moi, nhan_moi, nguoi)
    nguon_ra, id_ra = nguon, id_
    if thay_doi:
        if vi_sao == "da_doi":
            if nguon == "nap":
                id_ra = gia_moi(conn, {"fact_goc_id": id_, "gia_goc": gia_cu, "trang_thai": trang_thai_cu, **thay_doi,
                                       **{k: b.get(k) for k in _NGUON_TAY}}, nguoi)
                _ghi_nhat_ky(conn, "gia_moi", khoa_dong, None, {"tay_moi": id_ra}, nguoi)
            else:
                id_ra = sua_tay(conn, id_, thay_doi, nguoi,
                                nguon={k: b.get(k) for k in _NGUON_TAY if k in b or k == "loai_nguon"})
            nguon_ra = "tay"
        elif nguon == "nap":
            sua(conn, id_, thay_doi, nguoi)
        else:
            id_ra = sua_tay(conn, id_, thay_doi, nguoi)
    khoa_ra = f"{'gia' if nguon_ra == 'nap' else 'tay'}:{id_ra}"
    return {"nguon": nguon_ra, "id": id_ra, "sua_cuoi": sua_cuoi_cua(conn, [khoa_ra, khoa_ghep])}


# ---------------------------------------------------------------- ẩn / gộp mặt hàng (070)

def _khoa_ghep(conn, nguon: str, id_: int) -> list[str]:
    """[`<bên>/<hàng>`] của quan sát (khoá nhật ký của ghép) — để `sua_cuoi` trả về BẰNG `sua_cuoi` của các câu đọc, vốn
    gộp khoá của dòng với khoá ghép. Không có dòng -> []."""
    r = conn.execute("SELECT ma_doi_thu || '/' || ma_hang_dt FROM mart.gia_doi_thu_quan_sat WHERE nguon = %s AND id = %s",
                     (nguon, id_)).fetchone()
    return [] if r is None else [r[0]]


def dat_an(conn, b: dict, nguoi) -> dict:
    """Ẩn / khôi phục MỘT quan sát (070): sổ app.an_quan_sat CHỈ THÊM + nhật ký 'an' / 'hien' trên khoá của chính dòng
    ('gia:<id>' | 'tay:<id>' — cùng khoá 409 của pop-up), CÙNG giao dịch. Ẩn không xoá gì ở core. `b` = {nguon, id, an,
    da_xem, ghi_de}; thiếu / null `da_xem` = lệnh gọi từ script (không kiểm 409)."""
    if not isinstance(b, dict):
        raise LoiNhap("Thân yêu cầu phải là một đối tượng JSON.")
    nguon = b.get("nguon")
    if nguon not in ("nap", "tay"):
        raise LoiNhap("Nguồn chỉ nhận nap / tay.")
    id_ = doc_id(b.get("id"))
    an = b.get("an")
    if not isinstance(an, bool):
        raise LoiNhap("an phải là true / false.")
    khoa = f"{'gia' if nguon == 'nap' else 'tay'}:{id_}"
    kiem_xung_dot(conn, [khoa], None if b.get("da_xem") is None else doc_da_xem(b["da_xem"]), b.get("ghi_de") is True)
    r = conn.execute("SELECT an, hien_hanh, an_hien_hanh FROM mart.gia_doi_thu_quan_sat WHERE nguon = %s AND id = %s",
                     (nguon, id_)).fetchone()
    if r is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    if not (r[1] or r[2]):       # dòng lịch sử / đã bị thay: ẩn không có tác dụng nhìn thấy mà vẫn ghi nhật ký
        raise LoiNhap("Chỉ ẩn / khôi phục được dòng đang hiện (hoặc đang bị ẩn).")
    conn.execute("INSERT INTO app.an_quan_sat (nguon, quan_sat_id, an, nguoi_dung_id) VALUES (%s, %s, %s, %s)",
                 (nguon, id_, an, nguoi))
    _ghi_nhat_ky(conn, "an" if an else "hien", khoa, {"an": r[0]}, {"an": an}, nguoi)
    return {"nguon": nguon, "id": id_, "sua_cuoi": sua_cuoi_cua(conn, [khoa, *_khoa_ghep(conn, nguon, id_)])}


def _doc_ten_hang(v, ten: str) -> str:
    if not isinstance(v, str) or not 1 <= len(v.strip()) <= DAI_TOI_DA:
        raise LoiNhap(f"{ten} phải là chữ 1–{DAI_TOI_DA} ký tự.")
    return v.strip()


def _ghep_hieu_luc(conn, ben: str, dich: str):
    """(product_code, nhom_id, nhan) mà hàng `dich` của bên ĐANG mang, hoặc None. Ghép tường minh (app.ghep_hang, kể cả
    'khong') nếu có; không thì ghép AI của dòng hiện hành (không ẩn / không khách kể, ưu tiên mức cho khách thường rẻ nhất
    — gần với dòng đại diện mà KHÔNG phải dựng mart.gia_doi_thu_hien_hanh, view nặng): mã KOME + nhãn (nhãn null khi có
    mã → 'thay_the', cùng mặc định của 067). Mã AI phải có trong core.dim_product (dat_ghep từ chối mã lạ — mã AI chưa
    kiểm lúc nạp). Không có mã dùng được → None ('khong' chỉ chép khi nó là ghép tường minh). Đọc
    mart.gia_doi_thu_quan_sat lọc theo (bên, hàng) — hai cột nằm trong mọi PARTITION BY của view nên vị từ được đẩy xuống."""
    g = conn.execute("SELECT product_code, nhom_id, nhan FROM app.ghep_hang WHERE ma_doi_thu = %s AND ma_hang_dt = %s",
                     (ben, dich)).fetchone()
    if g is not None:
        return tuple(g)
    r = conn.execute("""SELECT q.ma_kome, q.nhan
                        FROM mart.gia_doi_thu_quan_sat q JOIN core.dim_product p ON p.product_code = q.ma_kome
                        WHERE q.ma_doi_thu = %s AND q.ma_hang_dt = %s AND q.hien_hanh AND q.loai_nguon <> 'khach_ke'
                        ORDER BY mart.la_muc_khach_thuong(q.muc_gia) DESC, (q.trang_thai = 'het'),
                                 q.yen_chuan NULLS LAST, q.nguon, q.id
                        LIMIT 1""", (ben, dich)).fetchone()
    if r is None:
        return None
    return (r[0], None, r[1] if r[1] in NHAN else "thay_the")


def _chep_ghep(conn, ben: str, hang: str, g_dich, g_dich_cu, nguoi) -> None:
    """Gộp `hang` vào một đích mang ghép hiệu lực `g_dich` (tính MỘT lần ở gop_mat_hang, trước mọi lần ghi): chép `g_dich`
    qua dat_ghep (409 / nhật ký 'ghep' trên '<bên>/<hàng>' như mọi lần ghép) khi `hang` CHƯA có ghép tường minh, HOẶC
    ghép tường minh của nó TRÙNG ghép hiệu lực của đích CŨ `g_dich_cu` (tức là ghép TỰ CHÉP ở lần gộp trước — gộp nối
    chuỗi A→…→C không được để hàng ở lại nhóm của A). Ghép tường minh KHÁC đích cũ = người đã chọn → giữ nguyên.
    Không chép thì đích mang ghép AI (ma_kome_de_xuat) để hai hàng ở HAI nhom_khoa — một mặt hàng hai đại diện."""
    if g_dich is None:
        return
    co = conn.execute("SELECT product_code, nhom_id, nhan FROM app.ghep_hang WHERE ma_doi_thu = %s AND ma_hang_dt = %s",
                      (ben, hang)).fetchone()
    if co is not None and (g_dich_cu is None or tuple(co) != tuple(g_dich_cu) or tuple(co) == tuple(g_dich)):
        return
    dat_ghep(conn, ben, hang, g_dich[0], g_dich[1], g_dich[2], nguoi)


def gop_mat_hang(conn, b: dict, nguoi) -> dict:
    """Gộp tay (bên, hàng) vào mặt hàng đích cùng bên (070; vao None = tách ra). LUÔN một bước: đích đang gộp vào C →
    ghi vào C; hàng đang gộp vào (bên, hàng) → ghi lại vào đích mới. Đích phải có dòng hiện hành của cùng bên; quy xong
    mà đích == chính nó → LoiNhap. Gộp (không phải tách) mà (bên, hàng) — hay hàng X được ghi lại vào đích — chưa có
    dòng app.ghep_hang → chép ghép HIỆU LỰC của đích (tường minh, không thì ghép AI của dòng đại diện; _chep_ghep) qua
    dat_ghep (cùng nhóm so sánh). 409 + nhật ký 'gop' trên '<bên>/<hàng>'. CÙNG giao dịch. `b` = {ma_doi_thu,
    ma_hang_dt, vao_ma_hang_dt | None, da_xem, ghi_de}; `vao_ma_hang_dt` rỗng cũng là tách. Trả {ma_doi_thu, ma_hang_dt,
    vao_ma_hang_dt (đích ĐÃ QUY), sua_cuoi}."""
    if not isinstance(b, dict):
        raise LoiNhap("Thân yêu cầu phải là một đối tượng JSON.")
    ben = _doc_ten_hang(b.get("ma_doi_thu"), "Mã đối thủ")
    hang = _doc_ten_hang(b.get("ma_hang_dt"), "Mã hàng đối thủ")
    vao = b.get("vao_ma_hang_dt")
    if vao is not None and not isinstance(vao, str):
        raise LoiNhap("Mặt hàng đích phải là chữ hoặc null (tách ra).")
    vao = _doc_ten_hang(vao, "Mặt hàng đích") if vao is not None and vao.strip() else None
    khoa = f"{ben}/{hang}"
    if conn.execute("SELECT 1 FROM app.doi_thu WHERE ma = %s", (ben,)).fetchone() is None:
        raise LoiNhap("Không có đối thủ này.")
    # Hai lần gộp cùng một bên chạy song song có thể đọc cùng trạng thái rồi ghi chéo nhau (phá bất biến "luôn một bước"):
    # khoá cố vấn theo bên, tự nhả cuối giao dịch — TRƯỚC mọi lần đọc bên dưới.
    conn.execute("SELECT pg_advisory_xact_lock(hashtext('gop_mat_hang:' || %s))", (ben,))
    kiem_xung_dot(conn, [khoa], None if b.get("da_xem") is None else doc_da_xem(b["da_xem"]), b.get("ghi_de") is True)
    if conn.execute("SELECT 1 FROM mart.gia_doi_thu_quan_sat WHERE ma_doi_thu = %s AND ma_hang_dt = %s LIMIT 1",
                    (ben, hang)).fetchone() is None:
        raise LoiNhap("Không tìm thấy mặt hàng này của đối thủ.")
    cu = conn.execute("SELECT vao_ma_hang_dt FROM app.gop_mat_hang WHERE ma_doi_thu = %s AND ma_hang_dt = %s "
                      "ORDER BY id DESC LIMIT 1", (ben, hang)).fetchone()
    cu = cu[0] if cu else None
    dich = vao
    if dich is not None:
        dd = conn.execute("SELECT vao_ma_hang_dt FROM app.gop_mat_hang WHERE ma_doi_thu = %s AND ma_hang_dt = %s "
                          "ORDER BY id DESC LIMIT 1", (ben, dich)).fetchone()
        if dd is not None and dd[0] is not None:
            dich = dd[0]                                  # đích đang gộp vào C → ghi vào C (luôn một bước)
        if dich == hang:
            raise LoiNhap("Không gộp một mặt hàng vào chính nó.")
        if conn.execute("SELECT 1 FROM mart.gia_doi_thu_quan_sat WHERE ma_doi_thu = %s AND ma_hang_dt = %s AND hien_hanh "
                        "LIMIT 1", (ben, dich)).fetchone() is None:
            raise LoiNhap("Mặt hàng đích không có dòng giá hiện hành của đối thủ này.")
    # Ghép hiệu lực đọc TRƯỚC mọi lần ghi (đích mới; hàng này — đích cũ của các X; đích cũ của chính hàng này), mỗi cái
    # MỘT lần — không mỗi X một lần.
    g_dich = _ghep_hieu_luc(conn, ben, dich) if dich is not None else None
    g_hang = _ghep_hieu_luc(conn, ben, hang) if dich is not None else None
    g_cu = _ghep_hieu_luc(conn, ben, cu) if dich is not None and cu is not None else None
    conn.execute("INSERT INTO app.gop_mat_hang (ma_doi_thu, ma_hang_dt, vao_ma_hang_dt, nguoi_dung_id) VALUES (%s, %s, %s, %s)",
                 (ben, hang, dich, nguoi))
    if dich is not None:
        # Hàng X đang gộp vào (bên, hàng) → ghi lại vào đích mới (tách: X giữ nguyên, vẫn trỏ hàng này — hợp lệ vì hàng
        # này nay không gộp đâu cả).
        for x in [r[0] for r in conn.execute(
                """SELECT ma_hang_dt FROM (SELECT DISTINCT ON (ma_hang_dt) ma_hang_dt, vao_ma_hang_dt FROM app.gop_mat_hang
                                           WHERE ma_doi_thu = %s ORDER BY ma_hang_dt, id DESC) t
                   WHERE vao_ma_hang_dt = %s ORDER BY ma_hang_dt""", (ben, hang)).fetchall()]:
            conn.execute("INSERT INTO app.gop_mat_hang (ma_doi_thu, ma_hang_dt, vao_ma_hang_dt, nguoi_dung_id) "
                         "VALUES (%s, %s, %s, %s)", (ben, x, dich, nguoi))
            _ghi_nhat_ky(conn, "gop", f"{ben}/{x}", {"vao": hang}, {"vao": dich}, nguoi)     # nhật ký trên khoá của chính X
            _chep_ghep(conn, ben, x, g_dich, g_hang, nguoi)
        _chep_ghep(conn, ben, hang, g_dich, g_cu, nguoi)
    _ghi_nhat_ky(conn, "gop", khoa, {"vao": cu}, {"vao": dich}, nguoi)
    return {"ma_doi_thu": ben, "ma_hang_dt": hang, "vao_ma_hang_dt": dich, "sua_cuoi": sua_cuoi_cua(conn, [khoa])}


# ---------------------------------------------------------------- đọc (mỗi hàm ĐÚNG MỘT lượt hỏi)

# Cột "bất thường" (chỉ quan sát HIỆN HÀNH có — mart.gia_doi_thu_hien_hanh): cờ + mốc đã dùng (B18: trung vị nhóm ≥ 3 bên,
# không thì giá KOME chuẩn của nhóm) để màn in lý do.
_COT_BT = "bat_thuong, round(moc_bat_thuong) AS moc_bat_thuong, moc_bat_thuong_la"
_COT_QS = f"""ma_doi_thu, ten_doi_thu, nguon, id, ma_hang_dt, ngay_nguon, hinh_thuc_nguon, nguon_file, vi_tri,
             ten_goc, quy_cach_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia,
             gia_bac, gia_truoc_km, trang_thai, khuyen_mai, loai_nguon, ghi_chu, ma_kome, nhan, nhom_khoa,
             ten_nhom, trang_thai_duyet, round(yen_chuan) AS yen_chuan, don_vi_so, nen_gia, tuoi_ngay,
             {_COT_BT},
             thang_lo, lien_ket_thu_muc, web_ben, lien_ket_bang_chung,
             so_goi_thung, kl_goi_g, bac, kg_thung_dt, round(gia_goi) AS gia_goi, round(gia_thung) AS gia_thung,
             round(gia_1) AS gia_1, round(gia_5) AS gia_5, round(gia_10) AS gia_10, round(gia_pallet) AS gia_pallet,
             mat_hang_khoa, an,
             coalesce((SELECT max(nk_.nk_id) FROM (SELECT id AS nk_id, doi_tuong AS nk_dt FROM app.doi_thu_nhat_ky) nk_
                       WHERE nk_.nk_dt IN (CASE nguon WHEN 'nap' THEN 'gia:' ELSE 'tay:' END || id,
                                           ma_doi_thu || '/' || ma_hang_dt)), 0) AS sua_cuoi"""
# 070: `mat_hang_khoa` (khoá mặt hàng sau gộp tay) và `an` (đã ẩn) — cột của mart.gia_doi_thu_quan_sat, có ở MỌI câu gọi.
# `_COT_MH` chỉ có ở mart.gia_doi_thu_hien_hanh: dòng ĐẠI DIỆN của mặt hàng, giá 1 pallet của mặt hàng, số mức giá.
# sua_cuoi (đợt 4b): lần ghi nhật ký MỚI NHẤT trên khoá của chính quan sát — 'gia:<id>' (dòng nạp: xác nhận / sửa) hoặc
# 'tay:<id>' (dòng tay), và '<bên>/<hàng>' (ghép); 0 = chưa ai sửa. Pop-up gửi lại số này để chống sửa đè. Cột nhật ký
# đổi tên trong bảng dẫn xuất (nk_id / nk_dt): `_COT_QS` dùng tên cột TRẦN của quan sát (nguon, id, …) ở mọi câu gọi, mà
# `id` trần bên trong một FROM app.doi_thu_nhat_ky sẽ trỏ vào id của NHẬT KÝ. Chỉ mục (doi_tuong, id DESC): 069.
_COT_MH = "dai_dien, round(gia_pallet_mh) AS gia_pallet_mh, so_muc"
_COT_QS_KHONG_BT = _COT_QS.replace(f"\n             {_COT_BT},", "")    # quan sát lịch sử (không hiện hành) không có bat_thuong
assert "bat_thuong" not in _COT_QS_KHONG_BT


def _sua_cuoi(khoa_sql: str) -> str:
    """Biểu thức SQL: max(id) nhật ký của MỘT khoá (0 khi chưa có) — khoá viết đủ bí danh, không dùng tên trần."""
    return f"coalesce((SELECT max(nkx_.id) FROM app.doi_thu_nhat_ky nkx_ WHERE nkx_.doi_tuong = {khoa_sql}), 0)"


def _thay_boi_sql(nguon: str, id_: str) -> str:
    """Biểu thức SQL (json | NULL): {nguon:'tay', id} = bản MỚI NHẤT đã thay quan sát (`nguon`, `id_` — biểu thức SQL đủ
    bí danh). Bước đầu: dòng tay có thay_cho_tay_id = id (quan sát tay) / fact_goc_id = id (quan sát nạp); rồi lần theo
    thay_cho_tay_id tới cuối chuỗi (≤ 50 bước). Hai bản cùng thay một dòng (sửa đè cũ) → id lớn hơn, đúng luật hien_hanh
    của 067. KHÔNG theo mốc: dòng đã bị thay NGOÀI ĐỜI thì không sửa tiếp được, dù đang xem lùi (B14)."""
    return f"""(WITH RECURSIVE c_(id, buoc) AS (
                  SELECT (SELECT max(t_.id) FROM app.gia_doi_thu_tay t_
                          WHERE ({nguon} = 'tay' AND t_.thay_cho_tay_id = {id_})
                             OR ({nguon} = 'nap' AND t_.fact_goc_id = {id_})), 1
                  UNION ALL
                  SELECT (SELECT max(t_.id) FROM app.gia_doi_thu_tay t_ WHERE t_.thay_cho_tay_id = c_.id), c_.buoc + 1
                  FROM c_ WHERE c_.id IS NOT NULL AND c_.buoc < 50)
                SELECT json_build_object('nguon', 'tay', 'id', c_.id) FROM c_ WHERE c_.id IS NOT NULL
                ORDER BY c_.buoc DESC LIMIT 1)"""


def _bo_nhom_sql(ben: str, hang: str, nguon: str, id_: str) -> str:
    """Biểu thức SQL (json | NULL): quan sát (`ben`, `hang`, `nguon`, `id_` — biểu thức đủ bí danh) đang bị "Không liên
    quan — bỏ khỏi nhóm" (app.ghep_hang.nhan = 'khong') -> {nhan_cu, nhom_khoa, ten_nhom}: nhóm nó RỜI (nhóm ghép tường
    minh, không thì nhóm HIỆN HÀNH của mã đã nhớ qua mart.nhom_cua_khoa — cùng thứ tự với nhom_khoa của 067) và nhãn để
    "hoàn tác" (nhãn `truoc` của lần bỏ gần nhất trong nhật ký; không có thì nhãn AI đề xuất; không có nữa thì
    thay_the). Mã / nhóm không còn biết (lần bỏ cũ gửi product_code null) -> NULL: không có nhóm nào để quay về."""
    return f"""(SELECT json_build_object('nhom_khoa', k_.khoa, 'ten_nhom', {_ten_nhom('k_.khoa')}, 'nhan_cu', coalesce(
                  (SELECT nk_.truoc->>'nhan' FROM app.doi_thu_nhat_ky nk_
                   WHERE nk_.doi_tuong = {ben} || '/' || {hang} AND nk_.loai = 'ghep' AND nk_.sau->>'nhan' = 'khong'
                     AND nk_.truoc->>'nhan' IN ('cung_hang', 'thay_the') ORDER BY nk_.id DESC LIMIT 1),
                  (SELECT f_.nhan_de_xuat FROM core.fact_gia_doi_thu f_
                   WHERE {nguon} = 'nap' AND f_.id = {id_} AND f_.nhan_de_xuat IN ('cung_hang', 'thay_the')),
                  'thay_the'))
                FROM app.ghep_hang g_
                CROSS JOIN LATERAL (SELECT CASE WHEN g_.nhom_id IS NOT NULL THEN 'n:' || g_.nhom_id
                                                WHEN g_.product_code IS NOT NULL
                                                THEN mart.nhom_cua_khoa('ma:' || g_.product_code) END AS khoa) k_
                WHERE g_.ma_doi_thu = {ben} AND g_.ma_hang_dt = {hang} AND g_.nhan = 'khong' AND k_.khoa IS NOT NULL)"""


def _dieu_kien_json(a: str) -> str:
    """Một điều kiện của mart.dieu_kien_hien_hanh (bí danh `a`) -> JSON. sua_cuoi theo khoá ghi của
    doi_thu_giao.sua_dieu_kien: 'dk:<fact_id>' (điều kiện đã nạp), 'dk:tay:<bên>' (dòng thêm tay — MỘT khoá chung cho
    mọi dòng tay của bên đó)."""
    khoa = f"CASE WHEN {a}.them_tay THEN 'dk:tay:' || {a}.ma_doi_thu ELSE 'dk:' || {a}.fact_id END"
    return (f"json_build_object('id', {a}.id, 'fact_id', {a}.fact_id, 'ben', {a}.ma_doi_thu, 'loai', {a}.loai, "
            f"'noi_dung', {a}.noi_dung, 'ngay', {a}.ngay_nguon, 'them_tay', {a}.them_tay, 'sua_cuoi', {_sua_cuoi(khoa)})")

NGAY_HIEN_TRUONG = 30       # cửa sổ "hiện trường" của Tổng quan
NGAY_TIN_KHACH = 90         # cửa sổ tin của khách / của đối thủ (mặc định của đặc tả §6: "chỉ tính 90 ngày")


def _ten_nhom(k: str) -> str:
    """Biểu thức SQL: tên của nhóm có khoá `k` ('n:<id>' -> tên nhóm; 'ma:<mã>' -> tên hàng KOME; không có -> chính khoá)."""
    return (f"coalesce((SELECT ns_.ten FROM app.nhom_so_sanh ns_ WHERE ns_.id = CASE WHEN {k} ~ '^n:[0-9]+$' THEN substr({k}, 3)::bigint END), "
            f"(SELECT coalesce(nullif(sp_.product_name, ''), sp_.product_code) FROM core.dim_product sp_ "
            f"WHERE sp_.product_code = CASE WHEN left({k}, 3) = 'ma:' THEN substr({k}, 4) END), {k})")


# Giá khách kể đã mang nhóm (thẻ @hàng) — không có gì để ghép hay xác nhận ở màn Duyệt: không vào hàng "chưa ghép"
# và không vào số "chờ duyệt". Giá khách kể BẤT THƯỜNG vẫn hiện ở bộ lọc "bất thường" của Duyệt.
_KE_DA_NHOM = "(loai_nguon = 'khach_ke' AND nhom_khoa IS NOT NULL)"


_TONG_QUAN = f"""
WITH h AS MATERIALIZED (SELECT * FROM mart.gia_doi_thu_hien_hanh)
SELECT json_build_object(
  'ben', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten, 'web', d.web,
            'ngay_moi', x.ngay_moi, 'hinh_thuc', x.hinh_thuc, 'so_dong', coalesce(x.so_dong, 0),
            'so_muc', coalesce(x.so_muc, 0), 'cho_duyet', coalesce(x.cho_duyet, 0)) ORDER BY d.ma), '[]')
          FROM app.doi_thu d LEFT JOIN (
            SELECT ma_doi_thu, max(ngay_nguon) ngay_moi, max(hinh_thuc_nguon) hinh_thuc,
                   count(DISTINCT mat_hang_khoa) FILTER (WHERE loai_nguon <> 'khach_ke') so_dong, count(*) so_muc,
                   count(*) FILTER (WHERE (trang_thai_duyet IN ('can_xem', 'ai_doc') OR bat_thuong)
                                      AND NOT {_KE_DA_NHOM}) cho_duyet
            FROM h GROUP BY 1) x ON x.ma_doi_thu = d.ma WHERE d.dang_theo_doi),
  'luoi', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'nganh', nganh, 'so_ma', n)), '[]') FROM (
            SELECT h.ma_doi_thu, mart.ten_nganh(p.food_category_name) nganh, count(DISTINCT h.mat_hang_khoa) n
            FROM h JOIN core.dim_product p ON p.product_code = h.ma_kome
            WHERE h.loai_nguon <> 'khach_ke' GROUP BY 1, 2) z),
  'khuyen_mai', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'ten_goc', ten_goc, 'gia_goc', gia_goc,
            'gia_truoc_km', gia_truoc_km, 'khuyen_mai', khuyen_mai, 'ngay', ngay_nguon,
            'nguon', nguon, 'id', id, 'ma_hang_dt', ma_hang_dt, 'ma_doi_thu', ma_doi_thu) ORDER BY ma_doi_thu, ten_goc), '[]')
          FROM (SELECT DISTINCT ON (ma_doi_thu, mat_hang_khoa) * FROM h
                WHERE gia_truoc_km IS NOT NULL OR nullif(khuyen_mai, '') IS NOT NULL
                ORDER BY ma_doi_thu, mat_hang_khoa, dai_dien DESC, yen_chuan NULLS LAST, nguon, id) km_),
  -- Điều kiện HIỆN HÀNH (068: lô mới nhất của bên ≤ mốc, bỏ 'ghi_chu_doc', áp sửa / bỏ, cộng dòng thêm tay); Tổng quan bỏ 'khac'.
  'dieu_kien', (SELECT coalesce(json_agg({_dieu_kien_json('d')} ORDER BY d.ma_doi_thu, d.loai, d.id), '[]')
          FROM (SELECT id, fact_id, ma_doi_thu, loai, noi_dung, ngay_nguon, them_tay FROM mart.dieu_kien_hien_hanh
                WHERE loai <> 'khac') d),
  'het_hang', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'ten_goc', ten_goc, 'ma_kome', ma_kome,
            'ten_nhom', ten_nhom, 'trang_thai', trang_thai, 'nguon', nguon, 'id', id, 'ma_hang_dt', ma_hang_dt,
            'ma_doi_thu', ma_doi_thu, 'ten_doi_thu', ten_doi_thu) ORDER BY ten_nhom, ma_doi_thu), '[]')
          FROM h WHERE trang_thai IN ('het', 'sap_ve') AND ma_kome IS NOT NULL AND dai_dien),
  'hien_truong', (
    WITH tx AS MATERIALIZED (
        SELECT n.id, n.customer_code FROM app.nhat_ky_tiep_xuc n
        WHERE (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date > %(hom_nay)s::date - {NGAY_HIEN_TRUONG}
          AND EXISTS (SELECT 1 FROM app.tiep_xuc_nhac z WHERE z.tiep_xuc_id = n.id)),
    m AS MATERIALIZED (SELECT DISTINCT z.tiep_xuc_id, z.loai,
                              CASE WHEN z.loai = 'nhom' THEN mart.nhom_cua_khoa(z.khoa) ELSE z.khoa END AS khoa
                       FROM app.tiep_xuc_nhac z JOIN tx ON tx.id = z.tiep_xuc_id)
    SELECT json_build_object('ngay', {NGAY_HIEN_TRUONG}, 'tong', (SELECT count(*) FROM tx),
      'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', q.ma, 'ten', q.ten, 'so_tin', q.n) ORDER BY q.n DESC, q.ma), '[]')
                  FROM (SELECT m.khoa AS ma, d.ten, count(*) AS n FROM m JOIN app.doi_thu d ON d.ma = m.khoa
                        WHERE m.loai = 'doi_thu' GROUP BY 1, 2 ORDER BY 3 DESC, 1 LIMIT 10) q),
      'nhom', (SELECT coalesce(json_agg(json_build_object('khoa', q.khoa, 'ten', q.ten, 'so_tin', q.n) ORDER BY q.n DESC, q.khoa), '[]')
               FROM (SELECT x.khoa, x.ten, count(*) AS n
                     FROM (SELECT m.khoa, {_ten_nhom('m.khoa')} AS ten FROM m WHERE m.loai = 'nhom') x
                     GROUP BY 1, 2 ORDER BY 3 DESC, 1 LIMIT 10) q),
      'tinh', (SELECT coalesce(json_agg(json_build_object('tinh', q.tinh, 'so_tin', q.n) ORDER BY q.n DESC, q.tinh), '[]')
               FROM (SELECT coalesce(nullif(c.prefecture, ''), '(chưa rõ)') AS tinh, count(*) AS n
                     FROM tx LEFT JOIN core.dim_customer c ON c.customer_code = tx.customer_code AND c.is_current
                     GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 48) q)))      -- 47 tỉnh + "(chưa rõ)"
)
"""


def tong_quan(conn, hom_nay=None) -> dict:
    """Tổng quan thị trường. `hien_truong` (đợt 2): tin `@` của NGAY_HIEN_TRUONG ngày qua theo ĐỒNG HỒ THẬT giờ
    Tokyo (`hom_nay_o_nhat`, không theo mốc dữ liệu — tin hiện trường là sự kiện ngoài đời, cùng lý lẽ ngoại lệ
    thứ hai của bất biến mốc, xem `/lien-he`). "Tin" = MỘT lần tiếp xúc có ít nhất một thẻ; mỗi đối thủ / nhóm /
    tỉnh đếm số tin nhắc tới nó (không đếm số thẻ). Tỉnh = `core.dim_customer.prefecture` hiện hành."""
    return conn.execute(_TONG_QUAN, {"hom_nay": hom_nay or hom_nay_o_nhat()}).fetchone()[0]


# Hiện hành đọc MỘT lần (hh MATERIALIZED) cho cả hai nhánh: quan sát của nhóm (h) và "đã bỏ khỏi nhóm" (b — dòng hiện
# hành đang mang ghép 'khong', kèm nhóm nó rời + nhãn để hoàn tác; _bo_nhom_sql). Bất biến CTE-trùng.
_SO_SANH = f"""
WITH hh AS MATERIALIZED (SELECT * FROM mart.gia_doi_thu_hien_hanh),
h AS MATERIALIZED (SELECT {_COT_QS}, {_COT_MH} FROM hh LEFT JOIN mart.nguon_quan_sat USING (nguon, id) WHERE nhom_khoa IS NOT NULL),
b AS MATERIALIZED (
    SELECT x.*, coalesce((SELECT max(nk2_.id) FROM app.doi_thu_nhat_ky nk2_
                          WHERE nk2_.doi_tuong IN (CASE x.nguon WHEN 'nap' THEN 'gia:' ELSE 'tay:' END || x.id,
                                                   x.ma_doi_thu || '/' || x.ma_hang_dt)), 0) AS sua_cuoi
    FROM (SELECT hh.nguon, hh.id, hh.ma_doi_thu, hh.ten_doi_thu, hh.ma_hang_dt, hh.ten_goc, hh.don_vi_so,
                 {_bo_nhom_sql('hh.ma_doi_thu', 'hh.ma_hang_dt', 'hh.nguon', 'hh.id')} AS bo
          FROM hh WHERE hh.nhom_khoa IS NULL AND hh.loai_nguon <> 'khach_ke') x
    WHERE x.bo IS NOT NULL)
SELECT (SELECT coalesce(json_agg(json_build_object(
         'nhom_khoa', s.nhom_khoa, 'ten_nhom', s.ten_nhom, 'don_vi_so', s.don_vi_so, 'ma_kome', s.ma_kome,
         'gia_kome', round(s.gia_kome), 'so_ben', s.so_ben, 'thap_nhat', round(s.thap_nhat), 'ben_thap_nhat', s.ben_thap_nhat,
         'trung_vi', round(s.trung_vi::numeric), 'cao_nhat', round(s.cao_nhat), 'ty_le_re_hon_kome', s.ty_le_re_hon_kome,
         'nganh', s.nganh,
         'gia_kome_chuan', round(s.gia_kome_chuan), 'gia_kome_bang', s.gia_kome_bang, 'gia_kome_km', round(s.gia_kome_km),
         'gia_kome_so', round(s.gia_kome_so), 'lech_trung_vi', s.lech_trung_vi, 'gia_kome_lech', s.gia_kome_lech,
         'kome_kg_goi', s.kome_kg_goi, 'kome_goi_thung', s.kome_goi_thung, 'kome_kg_thung', s.kome_kg_thung,
         'quan_sat', (SELECT coalesce(json_agg(to_json(h) ORDER BY h.yen_chuan NULLS LAST), '[]') FROM h
                      WHERE h.nhom_khoa = s.nhom_khoa AND h.don_vi_so = s.don_vi_so))
       ORDER BY s.so_ben DESC, s.ten_nhom), '[]')
        FROM mart.so_sanh_nhom s),
       (SELECT coalesce(json_agg(json_build_object(
         'nguon', b.nguon, 'id', b.id, 'ma_doi_thu', b.ma_doi_thu, 'ten_doi_thu', b.ten_doi_thu, 'ten_goc', b.ten_goc,
         'don_vi_so', b.don_vi_so, 'nhom_khoa', b.bo->>'nhom_khoa', 'ten_nhom', b.bo->>'ten_nhom',
         'nhan_cu', b.bo->>'nhan_cu', 'sua_cuoi', b.sua_cuoi) ORDER BY b.bo->>'nhom_khoa', b.ma_doi_thu, b.ten_goc, b.id), '[]')
        FROM b)
"""


def so_sanh(conn) -> dict:
    """{nhom, da_bo}. `da_bo` (đợt 4b, B15): mặt hàng HIỆN HÀNH đang bị "Không liên quan — bỏ khỏi nhóm", mỗi phần tử
    mang nhóm nó rời (`nhom_khoa`, `ten_nhom`) và `nhan_cu` để hoàn tác (POST /sua-mat-hang nhan = nhan_cu, da_xem =
    sua_cuoi). Dòng bị bỏ khi chưa biết mã / nhóm (ghép 'khong' không mã) không có ở đây. MỘT lượt hỏi."""
    nhom, da_bo = conn.execute(_SO_SANH).fetchone()
    return {"nhom": nhom, "da_bo": da_bo}


_NHOM_QUY_CACH = """
SELECT json_build_object(
  'nhom', (SELECT coalesce(json_agg(json_build_object('id', n.id, 'ten', n.ten, 'ma', coalesce(
             (SELECT json_agg(json_build_object('ma', m.product_code, 'ten', p.product_name) ORDER BY m.product_code)
              FROM app.nhom_so_sanh_ma m LEFT JOIN core.dim_product p USING (product_code)
              WHERE m.nhom_id = n.id), '[]')) ORDER BY n.ten), '[]') FROM app.nhom_so_sanh n),
  'quy_cach', (SELECT coalesce(json_agg(json_build_object('ma', z.product_code, 'ten', z.product_name, 'nganh', z.nganh,
                 'kg_moi_goi', z.kg_moi_goi, 'goi_moi_thung', z.goi_moi_thung, 'kg_moi_thung', z.kg_moi_thung,
                 'da_sua', z.da_sua) ORDER BY z.nganh, z.product_code), '[]')
               FROM (SELECT p.product_code, p.product_name, mart.ten_nganh(p.food_category_name) AS nganh,
                            q.kg_moi_goi, q.goi_moi_thung, q.kg_moi_thung, q.da_sua
                     FROM core.dim_product p JOIN mart.quy_cach_kome q USING (product_code)
                     WHERE NOT mart.khong_phai_hang(p.product_code, p.kind_code, p.food_category_name)) z))
"""


def nhom_va_quy_cach(conn) -> dict:
    """Nhóm so sánh (kèm danh sách mã) + quy cách KOME của hàng thật (không phí, không POSM). MỘT lượt hỏi."""
    return conn.execute(_NHOM_QUY_CACH).fetchone()[0]


# gia_kome_so của nhóm từng quan sát: mart.so_sanh_nhom (view nặng) đọc MỘT lần qua CTE MATERIALIZED, không mỗi dòng.
_HO_SO = f"""
WITH ss AS MATERIALIZED (SELECT nhom_khoa, don_vi_so, gia_kome_so, gia_kome_lech FROM mart.so_sanh_nhom),
bt AS MATERIALIZED (SELECT nguon, id, bat_thuong, moc_bat_thuong, moc_bat_thuong_la, dai_dien, gia_pallet_mh, so_muc
                    FROM mart.gia_doi_thu_hien_hanh WHERE ma_doi_thu = %(ma)s)
SELECT (SELECT to_json(d) FROM app.doi_thu d WHERE d.ma = %(ma)s),
       (SELECT coalesce(json_agg({_dieu_kien_json('d')} ORDER BY d.ngay_nguon DESC, d.loai, d.id), '[]')
          FROM mart.dieu_kien_hien_hanh d WHERE d.ma_doi_thu = %(ma)s),
       (SELECT coalesce(json_agg(to_json(q) ORDER BY q.ten_goc, q.ngay_nguon DESC), '[]')
          FROM (SELECT {_COT_QS_KHONG_BT}, hien_hanh, round(ss.gia_kome_so) AS gia_kome_so,
                       coalesce(ss.gia_kome_lech, false) AS gia_kome_lech,
                       coalesce(bt.bat_thuong, false) AS bat_thuong, round(bt.moc_bat_thuong) AS moc_bat_thuong,
                       bt.moc_bat_thuong_la, coalesce(bt.dai_dien, false) AS dai_dien,
                       round(bt.gia_pallet_mh) AS gia_pallet_mh, coalesce(bt.so_muc, 1) AS so_muc,
                       CASE WHEN hien_hanh AND nhom_khoa IS NULL AND loai_nguon <> 'khach_ke'
                            THEN {_bo_nhom_sql('gia_doi_thu_quan_sat.ma_doi_thu', 'gia_doi_thu_quan_sat.ma_hang_dt',
                                               'gia_doi_thu_quan_sat.nguon', 'gia_doi_thu_quan_sat.id')} END AS bo_nhom
                FROM mart.gia_doi_thu_quan_sat LEFT JOIN mart.nguon_quan_sat USING (nguon, id)
                LEFT JOIN ss USING (nhom_khoa, don_vi_so) LEFT JOIN bt USING (nguon, id)
                WHERE ma_doi_thu = %(ma)s) q),
       (SELECT coalesce(json_agg(json_build_object(
                  'tiep_xuc_id', t.id, 'ma_khach', t.customer_code, 'ten_khach', t.ten_khach, 'ngay', t.ngay,
                  'nhom', (SELECT coalesce(json_agg(json_build_object('khoa', x.khoa, 'ten', x.ten) ORDER BY x.khoa), '[]')
                           FROM (SELECT DISTINCT k.khoa, {_ten_nhom('k.khoa')} AS ten FROM app.tiep_xuc_nhac z
                                 CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(z.khoa) AS khoa) k
                                 WHERE z.tiep_xuc_id = t.id AND z.loai = 'nhom') x),
                  'gia', (SELECT coalesce(json_agg(json_build_object('nhom_khoa', k.khoa, 'ten_nhom', {_ten_nhom('k.khoa')},
                                'gia_goc', g.gia_goc, 'don_vi_gia', g.don_vi_gia) ORDER BY g.id), '[]')
                          FROM app.gia_doi_thu_tay g CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(g.nhom_khoa) AS khoa) k
                          WHERE g.tiep_xuc_id = t.id AND g.ma_doi_thu = %(ma)s AND g.loai_nguon = 'khach_ke'))
                ORDER BY t.thoi_diem DESC, t.id DESC), '[]')
          FROM (SELECT n.id, n.customer_code, n.thoi_diem, c.customer_name AS ten_khach,
                       (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date AS ngay
                FROM app.nhat_ky_tiep_xuc n
                LEFT JOIN core.dim_customer c ON c.customer_code = n.customer_code AND c.is_current
                WHERE (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date > %(hom_nay)s::date - {NGAY_TIN_KHACH}
                  AND EXISTS (SELECT 1 FROM app.tiep_xuc_nhac z
                              WHERE z.tiep_xuc_id = n.id AND z.loai = 'doi_thu' AND z.khoa = %(ma)s)
                ORDER BY n.thoi_diem DESC, n.id DESC LIMIT 100) t),
       (SELECT to_json(g) FROM (SELECT gh.*, {_sua_cuoi("'giao:' || gh.ma_doi_thu")} AS sua_cuoi
                                FROM mart.giao_hang_hien_hanh gh WHERE gh.ma_doi_thu = %(ma)s) g),
       {_sua_cuoi("'ben:' || %(ma)s")}
"""


def ho_so_ben(conn, ma: str, hom_nay=None) -> dict | None:
    """Hồ sơ một đối thủ. `khach_dang_mua` (đợt 2): tin `@` NGAY_TIN_KHACH ngày qua nhắc bên này — mỗi phần tử là
    MỘT lần tiếp xúc (khách + tên hiện hành, các nhóm được nhắc, giá khách kể cho CHÍNH bên này). Theo đồng hồ thật
    giờ Tokyo (`hom_nay_o_nhat`), không theo mốc dữ liệu — xem `tong_quan`. Vẫn MỘT lượt hỏi.
    Đợt 4b: `dieu_kien` = mart.dieu_kien_hien_hanh của bên (kèm id / fact_id / them_tay / sua_cuoi); mỗi quan sát mang
    `gia_kome_so` của nhóm nó (null nếu không có); `giao_hang` = dòng mart.giao_hang_hien_hanh của bên (kèm sua_cuoi
    theo khoá 'giao:<bên>') hoặc null; `sua_cuoi_ben` = max nhật ký 'ben:<mã>' (0 = chưa sửa). Mỗi quan sát còn mang
    `gia_kome_lech` của nhóm nó (mart.so_sanh_nhom: giá KOME > 3× / < ⅓ trung vị; không có nhóm → false) — màn không vẽ
    những dòng đó như giá thật. `bo_nhom` (B15) = {nhom_khoa, ten_nhom, nhan_cu} của dòng hiện hành đang bị "bỏ khỏi
    nhóm" (_bo_nhom_sql), còn lại null — dải "Đã bỏ khỏi nhóm … hoàn tác" của tab Đối thủ. `bat_thuong` / `moc_bat_thuong`
    / `moc_bat_thuong_la` (B18) = cột của mart.gia_doi_thu_hien_hanh (dòng lịch sử: false / null) — màn vẽ xám, không đếm."""
    ben, dk, qs, kh, gh, scb = conn.execute(_HO_SO, {"ma": ma, "hom_nay": hom_nay or hom_nay_o_nhat()}).fetchone()
    return None if ben is None else {"ben": ben, "dieu_kien": dk, "quan_sat": qs, "khach_dang_mua": kh,
                                     "giao_hang": gh, "sua_cuoi_ben": scb}


KHOA_LICH_SU_TOI_DA = 5
LICH_SU_TOI_DA = 50


def _lich_su_sql(khoa_sql: str) -> str:
    """Lịch sử sửa (mới nhất trước, ≤ LICH_SU_TOI_DA dòng) của các khoá nhật ký `khoa_sql` (biểu thức text[]).
    `ai` = tên người phụ trách của tài khoản, không có thì tên đăng nhập (cùng nếp khach_doi_thu; app.nguoi_dung không
    có cột tên hiển thị); null = ghi từ script / máy không có cổng đăng nhập."""
    return f"""(SELECT coalesce(json_agg(json_build_object('id', nk.id, 'loai', nk.loai, 'doi_tuong', nk.doi_tuong,
                    'ai', coalesce(sp.ten, nd.ten_dang_nhap), 'luc', nk.luc, 'truoc', nk.truoc, 'sau', nk.sau)
                    ORDER BY nk.id DESC), '[]')
                FROM (SELECT * FROM app.doi_thu_nhat_ky WHERE doi_tuong = ANY({khoa_sql})
                      ORDER BY id DESC LIMIT {LICH_SU_TOI_DA}) nk
                LEFT JOIN app.nguoi_dung nd ON nd.id = nk.nguoi_dung_id
                LEFT JOIN core.dim_salesperson sp ON sp.salesperson_code = nd.salesperson_code)"""


def lich_su(conn, khoa: list[str]) -> list:
    """Lịch sử sửa của 1–KHOA_LICH_SU_TOI_DA khoá nhật ký ('gia:<id>', 'giao:<bên>', …). Đọc tươi, MỘT lượt hỏi."""
    if (not isinstance(khoa, list) or not 1 <= len(khoa) <= KHOA_LICH_SU_TOI_DA
            or any(not isinstance(k, str) or not 1 <= len(k) <= DAI_TOI_DA for k in khoa)):
        raise LoiNhap(f"Cần 1–{KHOA_LICH_SU_TOI_DA} khoá, mỗi khoá 1–{DAI_TOI_DA} ký tự.")
    return conn.execute(f"SELECT {_lich_su_sql('%(khoa)s')}", {"khoa": khoa}).fetchone()[0]


# Một mặt hàng cho pop-up sửa: đọc mart.gia_doi_thu_quan_sat (KHÔNG chỉ hiện hành — sửa được cả dòng lịch sử);
# bat_thuong / dai_dien / gia_pallet_mh / so_muc chỉ có nghĩa với dòng hiện hành (lấy từ mart.gia_doi_thu_hien_hanh —
# MỘT lần, LATERAL), dòng lịch sử = false / false / NULL / 1.
_MAT_HANG = f"""
WITH q AS MATERIALIZED (
    SELECT {_COT_QS_KHONG_BT}, hien_hanh FROM mart.gia_doi_thu_quan_sat LEFT JOIN mart.nguon_quan_sat USING (nguon, id)
    WHERE nguon = %(nguon)s AND id = %(id)s)
SELECT (SELECT to_json(x) FROM (
          SELECT q.*, coalesce(mh.bat_thuong, false) AS bat_thuong,
                 coalesce(mh.dai_dien, false) AS dai_dien, round(mh.gia_pallet_mh) AS gia_pallet_mh,
                 coalesce(mh.so_muc, 1) AS so_muc,
                 g.product_code AS ma_ghep, g.nhom_id AS nhom_ghep,
                 {_thay_boi_sql('q.nguon', 'q.id')} AS thay_boi
          FROM q LEFT JOIN app.ghep_hang g ON g.ma_doi_thu = q.ma_doi_thu AND g.ma_hang_dt = q.ma_hang_dt
          LEFT JOIN LATERAL (SELECT h.bat_thuong, h.dai_dien, h.gia_pallet_mh, h.so_muc FROM mart.gia_doi_thu_hien_hanh h
                             WHERE q.hien_hanh AND h.nguon = q.nguon AND h.id = q.id) mh ON true) x),
       {_lich_su_sql("ARRAY(SELECT v.k FROM q CROSS JOIN LATERAL (VALUES "
                     "(CASE q.nguon WHEN 'nap' THEN 'gia:' ELSE 'tay:' END || q.id), "
                     "(q.ma_doi_thu || '/' || q.ma_hang_dt)) v(k))")}
"""


def mat_hang(conn, nguon: str, id: int) -> dict | None:
    """{"quan_sat", "lich_su"} của MỘT quan sát (nguồn 'nap' | 'tay'); None = không có (hoặc sau mốc). MỘT lượt hỏi.
    Lịch sử theo khoá của chính dòng: 'gia:<id>' / 'tay:<id>' và '<bên>/<hàng>' (ghép). Quan sát mang thêm `ma_ghep` /
    `nhom_ghep` (dòng app.ghep_hang, kể cả khi nhãn 'khong' — ô "Mã KOME" / "Nhóm" của pop-up) và `thay_boi` ({nguon,
    id} bản mới nhất đã thay dòng này, null = chưa bị thay — B14: pop-up khoá Lưu và mời mở bản mới)."""
    if nguon not in ("nap", "tay"):
        raise LoiNhap("Nguồn chỉ nhận nap / tay.")
    if not 0 < int(id) < 2 ** 63:                            # ngoài bigint: không có dòng nào (không để CSDL nổ 500)
        return None
    qs, ls = conn.execute(_MAT_HANG, {"nguon": nguon, "id": int(id)}).fetchone()
    return None if qs is None else {"quan_sat": qs, "lich_su": ls}


_DUYET = f"""
WITH h AS (
    SELECT s_.*, count(*) OVER () AS tong_,
           row_number() OVER (ORDER BY s_.ma_doi_thu, s_.ten_mh_, s_.mat_hang_khoa, s_.dai_dien DESC, s_.yc_ NULLS LAST,
                                       s_.nguon, s_.id) AS ord_
    FROM (
    SELECT {_COT_QS}, {_COT_MH}, h.yen_chuan AS yc_,
           min(lower(h.ten_goc)) OVER (PARTITION BY h.ma_doi_thu, h.mat_hang_khoa) AS ten_mh_
    FROM mart.gia_doi_thu_hien_hanh h LEFT JOIN mart.nguon_quan_sat USING (nguon, id)
    WHERE (%(ben)s = '' OR ma_doi_thu = %(ben)s)
      AND CASE %(loc)s WHEN 'can_xem' THEN trang_thai_duyet = 'can_xem'
                       WHEN 'bat_thuong' THEN bat_thuong
                       WHEN 'chua_ghep' THEN ma_kome IS NULL AND NOT {_KE_DA_NHOM} AND NOT EXISTS (
                           SELECT 1 FROM app.ghep_hang g
                           WHERE g.ma_doi_thu = h.ma_doi_thu AND g.ma_hang_dt = h.ma_hang_dt)
                       WHEN 'chua_xac_nhan' THEN trang_thai_duyet IN ('ai_doc', 'can_xem')
                       WHEN 'thieu_quy_cach' THEN loai_nguon <> 'khach_ke' AND (so_goi_thung IS NULL OR kl_goi_g IS NULL)
                       ELSE true END) s_
    ORDER BY ord_
    LIMIT %(toi_da)s)
SELECT coalesce(json_agg(to_jsonb(h) - 'tong_' - 'ord_' - 'ten_mh_' - 'yc_' ORDER BY h.ord_), '[]'),
       coalesce(max(h.tong_), 0)
FROM h
"""
# 070: thứ tự = bên → TÊN mặt hàng (`ten_mh_` = tên nhỏ nhất, không phân hoa thường, trong các mức ĐANG LỌC của mặt hàng)
# → khoá mặt hàng → đại diện trước → giá tăng dần: các mức của MỘT mặt hàng đứng liền nhau, danh sách theo ABC (khoá
# mặt hàng trần là mã hàng đối thủ — 'ten:basa|…' / JAN — xếp theo nó là thứ tự không đọc được). Bộ lọc "Bất thường"
# vẫn có, chỉ không còn đẩy dòng bất thường lên đầu. `ord_` = thứ tự đó, để json_agg xếp lại ĐÚNG như câu trong
# (yen_chuan của _COT_QS đã làm tròn — sắp theo cột làm tròn thì hoà nhau khác thứ tự; `yc_` = giá chưa tròn). Hàm cửa
# sổ lồng hàm cửa sổ không được → `ten_mh_` / `yc_` tính ở câu con `s_`.

# "Đã xoá" (070): quan sát ẨN đang là mới nhất của phân vùng (mart.gia_doi_thu_quan_sat.an_hien_hanh) — bảng Duyệt liệt kê để
# khôi phục. Dòng lịch sử không có cờ bất thường / đại diện: false / NULL / 1 — cùng hình dạng với dòng hiện hành.
_DUYET_DA_XOA = f"""
WITH h AS (
    SELECT s_.*, count(*) OVER () AS tong_,
           row_number() OVER (ORDER BY s_.ma_doi_thu, s_.ten_mh_, s_.mat_hang_khoa, s_.dai_dien DESC, s_.yc_ NULLS LAST,
                                       s_.nguon, s_.id) AS ord_
    FROM (
    SELECT {_COT_QS_KHONG_BT}, false AS bat_thuong, NULL::numeric AS moc_bat_thuong, NULL::text AS moc_bat_thuong_la,
           false AS dai_dien, NULL::numeric AS gia_pallet_mh, 1::bigint AS so_muc, q.yen_chuan AS yc_,
           min(lower(q.ten_goc)) OVER (PARTITION BY q.ma_doi_thu, q.mat_hang_khoa) AS ten_mh_
    FROM mart.gia_doi_thu_quan_sat q LEFT JOIN mart.nguon_quan_sat USING (nguon, id)
    WHERE an_hien_hanh AND (%(ben)s = '' OR ma_doi_thu = %(ben)s)) s_
    ORDER BY ord_
    LIMIT %(toi_da)s)
SELECT coalesce(json_agg(to_jsonb(h) - 'tong_' - 'ord_' - 'ten_mh_' - 'yc_' ORDER BY h.ord_), '[]'),
       coalesce(max(h.tong_), 0)
FROM h
"""
# Trần (bảng sửa 2026-09-30): toàn bộ bảng giá thật = 5,26 MB JSON > trần phản hồi Vercel 4,5 MB. 800 ≥ bên lớn nhất
# (NEXT 716 dòng, ~1 MB). `tong` = số dòng khớp bộ lọc TRƯỚC khi cắt — màn nói "đang hiện n / tong, chọn một bên".
DONG_TOI_DA_DUYET = 800


def duyet(conn, ben: str = "", loc: str = "") -> dict:
    """Bảng Duyệt / sửa: {"dong": ≤ DONG_TOI_DA_DUYET quan sát hiện hành, "tong": số dòng khớp}. MỘT lượt hỏi.
    `thieu_quy_cach` = thiếu gói/thùng hoặc tịnh 1 gói, không tính khách kể (= so_sanh_logic.ts::thieuQuyCach + veDuoc).
    `da_xoa` (070) = quan sát đã ẨN (khôi phục được), câu riêng — vẫn MỘT lượt hỏi. Mọi dòng mang `mat_hang_khoa`, `an`,
    `dai_dien`, `gia_pallet_mh`, `so_muc`; thứ tự bên → tên mặt hàng (ABC) → mặt hàng → đại diện trước → giá tăng dần."""
    if loc not in LOC_DUYET:
        loc = ""
    cau = _DUYET_DA_XOA if loc == "da_xoa" else _DUYET
    dong, tong = conn.execute(cau, {"ben": ben, "loc": loc, "toi_da": DONG_TOI_DA_DUYET}).fetchone()
    return {"dong": dong, "tong": tong}


_KHOI_SP = """
SELECT to_json(s) FROM mart.so_sanh_nhom s
WHERE s.don_vi_so = 'kg' AND %(ma)s = ANY(s.ma_kome)
ORDER BY s.so_ben DESC LIMIT 1
"""


def khoi_san_pham(conn, ma: str) -> dict | None:
    r = conn.execute(_KHOI_SP, {"ma": ma}).fetchone()
    return r[0] if r else None


_GOI_Y_NHAC = f"""
SELECT json_build_object(
  'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten) ORDER BY d.ma), '[]')
              FROM app.doi_thu d WHERE d.dang_theo_doi),
  'hang', (SELECT coalesce(json_agg(json_strip_nulls(json_build_object('khoa', z.khoa, 'ten', z.ten, 'loai', z.loai,
                                                                       'ma', z.ma, 'ten_nhom', z.ten_nhom))
                                    ORDER BY z.thu_tu, z.ten, z.khoa, z.ma), '[]')
           FROM (SELECT 0 AS thu_tu, 'n:' || n.id AS khoa, n.ten, 'nhom' AS loai, NULL::text AS ma, NULL::text AS ten_nhom
                 FROM app.nhom_so_sanh n
                 UNION ALL
                 SELECT 1, k.khoa, coalesce(nullif(p.product_name, ''), p.product_code), 'ma', p.product_code,
                        CASE WHEN left(k.khoa, 2) = 'n:' THEN {_ten_nhom('k.khoa')} END
                 FROM core.dim_product p CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa('ma:' || p.product_code) AS khoa) k
                 WHERE NOT mart.khong_phai_hang(p.product_code, p.kind_code, p.food_category_name)) z))
"""


def goi_y_nhac(conn) -> dict:
    """Danh sách gợi ý cho ô `@` của ô ghi tiếp xúc. MỘT lượt hỏi.
    `doi_thu`: đối thủ đang theo dõi. `hang`: nhóm so sánh có tên (`loai = 'nhom'`, khoá `n:<id>`, đứng trước)
    rồi mã KOME hàng thật (`loai = 'ma'`, `ma` = mã; không phí / POSM — cùng vị từ `nhom_va_quy_cach`). Mã thuộc một
    nhóm có tên VẪN được gợi ý (sale gõ tên hàng chứ không nhớ tên nhóm) nhưng khoá của nó là NHÓM
    (`mart.nhom_cua_khoa` -> `n:<id>`, kèm `ten_nhom`); mã lẻ giữ khoá `ma:<mã>`. Thẻ `@hàng` vì vậy luôn trỏ tới nhóm
    so sánh thật của mã (R-A)."""
    return conn.execute(_GOI_Y_NHAC).fetchone()[0]


_KHACH_DOI_THU = f"""
WITH tx AS MATERIALIZED (
    SELECT n.id, n.thoi_diem, (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date AS ngay, n.noi_dung,
           coalesce(s.ten, nd.ten_dang_nhap) AS nguoi
    FROM app.nhat_ky_tiep_xuc n
    LEFT JOIN app.nguoi_dung nd ON nd.id = n.nguoi_dung_id
    LEFT JOIN core.dim_salesperson s ON s.salesperson_code = nd.salesperson_code
    WHERE n.customer_code = %(ma)s
      AND (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date > %(hom_nay)s::date - {NGAY_TIN_KHACH}
      AND EXISTS (SELECT 1 FROM app.tiep_xuc_nhac z WHERE z.tiep_xuc_id = n.id)
    ORDER BY n.thoi_diem DESC, n.id DESC LIMIT 100),
dt AS MATERIALIZED (
    SELECT DISTINCT z.tiep_xuc_id, z.khoa AS ma, d.ten
    FROM tx JOIN app.tiep_xuc_nhac z ON z.tiep_xuc_id = tx.id AND z.loai = 'doi_thu'
    JOIN app.doi_thu d ON d.ma = z.khoa),
nh AS MATERIALIZED (     -- khoá nhóm HIỆN HÀNH (mart.nhom_cua_khoa, 063): 'ma:<mã>' của mã thuộc nhóm có tên -> 'n:<nhóm>'
    SELECT DISTINCT z.tiep_xuc_id, k.khoa, {_ten_nhom('k.khoa')} AS ten
    FROM tx JOIN app.tiep_xuc_nhac z ON z.tiep_xuc_id = tx.id AND z.loai = 'nhom'
    CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(z.khoa) AS khoa) k),
ngung AS (      -- cặp (khách, mã) đã ngừng mua theo bất biến 024; view lọc theo khách nên vị từ đẩy xuống được
    SELECT h.product_code AS ma, coalesce(nullif(h.ten_hang, ''), h.product_code) AS ten, h.lan_cuoi,
           (SELECT hom_nay FROM mart.moc_thoi_gian) - h.lan_cuoi AS so_ngay,
           mart.nhom_cua_khoa('ma:' || h.product_code) AS nhom_khoa
    FROM mart.khach_mat_hang h
    WHERE h.customer_code = %(ma)s AND h.trang_thai_cap = 'ngung'),
ly AS (         -- mỗi mã ngừng mua: tin MỚI NHẤT nhắc nhóm HIỆN HÀNH của nó (cả hai phía qua mart.nhom_cua_khoa)
    SELECT DISTINCT ON (g.ma) g.ma, g.ten, g.lan_cuoi, g.so_ngay, nh.khoa AS nhom_khoa, nh.ten AS ten_nhom,
           tx.id AS tiep_xuc_id, tx.ngay AS tin_ngay
    FROM ngung g
    JOIN nh ON nh.khoa = g.nhom_khoa
    JOIN tx ON tx.id = nh.tiep_xuc_id
    ORDER BY g.ma, tx.thoi_diem DESC, tx.id DESC)
SELECT json_build_object(
  'tin', (SELECT coalesce(json_agg(json_build_object(
             'tiep_xuc_id', tx.id, 'ngay', tx.ngay, 'nguoi', tx.nguoi, 'noi_dung', tx.noi_dung,
             'nhac', (SELECT coalesce(json_agg(json_build_object('loai', z.loai,
                             'khoa', CASE WHEN z.loai = 'nhom' THEN mart.nhom_cua_khoa(z.khoa) ELSE z.khoa END,
                             'vi_tri_dau', z.vi_tri_dau, 'do_dai', z.do_dai) ORDER BY z.vi_tri_dau), '[]')
                      FROM app.tiep_xuc_nhac z WHERE z.tiep_xuc_id = tx.id),
             'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten) ORDER BY d.ma), '[]')
                         FROM dt d WHERE d.tiep_xuc_id = tx.id),
             'nhom', (SELECT coalesce(json_agg(json_build_object('khoa', h.khoa, 'ten', h.ten) ORDER BY h.khoa), '[]')
                      FROM nh h WHERE h.tiep_xuc_id = tx.id),
             'gia', (SELECT coalesce(json_agg(json_build_object('ma_doi_thu', t.ma_doi_thu, 'ten_doi_thu', d.ten,
                             'nhom_khoa', k.khoa, 'ten_nhom', h.ten, 'gia_goc', t.gia_goc, 'don_vi_gia', t.don_vi_gia)
                             ORDER BY t.id), '[]')
                     FROM app.gia_doi_thu_tay t
                     CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(t.nhom_khoa) AS khoa) k
                     JOIN app.doi_thu d ON d.ma = t.ma_doi_thu
                     LEFT JOIN nh h ON h.tiep_xuc_id = t.tiep_xuc_id AND h.khoa = k.khoa
                     WHERE t.tiep_xuc_id = tx.id AND t.loai_nguon = 'khach_ke'))
           ORDER BY tx.thoi_diem DESC, tx.id DESC), '[]') FROM tx),
  'ly_do_ngung', (SELECT coalesce(json_agg(json_build_object(
             'ma', ly.ma, 'ten', ly.ten, 'nhom_khoa', ly.nhom_khoa, 'ten_nhom', ly.ten_nhom,
             'lan_cuoi', ly.lan_cuoi, 'so_ngay', ly.so_ngay, 'tiep_xuc_id', ly.tiep_xuc_id, 'tin_ngay', ly.tin_ngay,
             'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten) ORDER BY d.ma), '[]')
                         FROM dt d WHERE d.tiep_xuc_id = ly.tiep_xuc_id))
           ORDER BY ly.lan_cuoi DESC, ly.ma), '[]') FROM ly))
"""


def khach_doi_thu(conn, ma_khach: str, hom_nay=None) -> dict:
    """Khối "Đang mua của đối thủ" của hồ sơ khách 360 — MỘT lượt hỏi (hồ sơ `ho_so()` giữ trần 8 nên khối này
    đi endpoint riêng). NGAY_TIN_KHACH ngày qua theo ĐỒNG HỒ THẬT giờ Tokyo (`hom_nay_o_nhat`; xem `tong_quan`).

    `tin`: mỗi lần tiếp xúc có thẻ `@` — đối thủ, nhóm (khoá + tên), giá khách kể kèm theo, ngày, người ghi, câu gốc,
    và `nhac` = MỌI thẻ theo thứ tự trong câu (`vi_tri_dau` tăng dần; vị trí/độ dài theo KÝ TỰ Unicode như đã lưu ở
    `app.tiep_xuc_nhac` — giao diện đổi sang UTF-16 nếu cần tô chữ). Mọi khoá NHÓM trả ra (`nhac`, `nhom`, `gia`,
    `ly_do_ngung`) là khoá HIỆN HÀNH qua `mart.nhom_cua_khoa` — thẻ đã lưu giữ nguyên như lúc ghi. Giao diện ghép "đối thủ gần nhất đứng trước"
    từ đúng danh sách này (cùng vòng lặp lúc ghi), không dò chữ trong câu.
    `ly_do_ngung`: các cặp (khách, mã) `mart.khach_mat_hang.trang_thai_cap = 'ngung'` (bất biến 024) mà nhóm của mã —
    thẻ `ma:<mã>` hoặc `n:<nhóm có tên chứa mã>` — được nhắc trong các tin trên; mỗi mã một dòng, tin MỚI NHẤT nhắc
    nhóm đó, kèm các đối thủ được nhắc CÙNG lần tiếp xúc ấy."""
    return conn.execute(_KHACH_DOI_THU, {"ma": ma_khach, "hom_nay": hom_nay or hom_nay_o_nhat()}).fetchone()[0]
