"""Ghi điều kiện giao hàng / điều kiện bán (đặc tả 2026-09-29-doi-thu-giao-dien-moi-design.md §4.7, §5.4).

Đối thủ: sổ CHỈ THÊM (app.dinh_chinh_giao_hang / app.dinh_chinh_dieu_kien). KOME: app.giao_hang_kome (một dòng,
UPDATE). Mỗi lần ghi thêm một dòng app.doi_thu_nhat_ky CÙNG giao dịch — hai sổ đó KHÔNG có trong anh_chup._PHIEN_BAN,
ảnh chụp đổi nhờ dòng nhật ký (nếp 064). '' = xoá về "không ghi" (NULL ở mart.giao_hang_hien_hanh), không phải 0.
"""
import json
import math
from decimal import Decimal

from kome.doi_thu import LoiNhap, _ghi_nhat_ky, _so, _hai_so_le, DAI_TOI_DA, kiem_xung_dot

TRUONG_GIAO_HANG = ("bao_ship", "phi_ship", "phi_ship_theo", "mien_ship_tu", "mien_ship_kien", "thung_moi_kien",
                    "phu_phi", "phi_daibiki", "daibiki_tu", "daibiki_sau", "ck_mien_daibiki", "kien_toi_da_kg",
                    "ghep_kien", "thue", "cach_gui")
VUNG = ("hokkaido", "tohoku", "kanto", "chubu", "kansai", "chugoku", "shikoku", "kyushu", "okinawa")
_SO = {"phi_ship", "mien_ship_tu", "phi_daibiki", "daibiki_tu", "daibiki_sau", "kien_toi_da_kg"}
_NGUYEN = {"mien_ship_kien", "thung_moi_kien"}
# Sổ đính chính CHỈ THÊM: một dòng hỏng là hỏng vĩnh viễn — nên chặn ở cửa theo ĐÚNG cột đích (numeric(10,2) / (12,2) /
# (8,2), integer) và view 068 còn tự bỏ qua dòng không đọc được.
_TRAN_SO = {"phi_ship": Decimal("99999999.99"), "phi_daibiki": Decimal("99999999.99"), "daibiki_sau": Decimal("99999999.99"),
            "mien_ship_tu": Decimal("9999999999.99"), "daibiki_tu": Decimal("9999999999.99"),
            "kien_toi_da_kg": Decimal("999999.99")}
_DUONG = {"kien_toi_da_kg"}     # CHECK > 0 (các số ¥ cho phép 0)
_TRAN_NGUYEN = 10000
_TRAN_VUNG = 9_999_999
_BOOL = {"bao_ship", "ck_mien_daibiki"}
_TAP = {"phi_ship_theo": ("don", "thung", "kien"), "thue": ("bao", "chua", "khong_ro")}
LOAI_DK = ("ship", "khuyen_mai", "thanh_toan", "thue", "khac")


def _kiem_truong(t: str, v):
    """→ chữ lưu vào gia_tri_moi ('' = xoá), hoặc giá trị Python cho app.giao_hang_kome."""
    if t not in TRUONG_GIAO_HANG:
        raise LoiNhap(f"Không sửa được trường '{t}'.")
    if v is None or (isinstance(v, str) and not v.strip()):
        return None
    if t in _BOOL:
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        if s not in ("true", "false"):
            raise LoiNhap(f"{t} chỉ nhận có / không.")
        return s == "true"
    if t in _SO:
        # Làm tròn về ĐÚNG dạng cột đích (numeric(·,2)) TRƯỚC khi kiểm: '-0' → 0, 7 chữ số lẻ → 2, '0.001' của trường
        # phải > 0 → LoiNhap. Chữ lưu vào sổ đối thủ phải khớp regex của 068 — không thì "đã lưu" mà view vẫn hiện số của lô.
        x = _hai_so_le(_so(v, t, t in _DUONG), t, t in _DUONG)
        if x > _TRAN_SO[t]:
            raise LoiNhap(f"{t} quá lớn.")
        return x
    if t in _NGUYEN:
        x = _so(v, t, True)
        if x != x.to_integral_value():
            raise LoiNhap(f"{t} phải là số nguyên.")
        if x > _TRAN_NGUYEN:
            raise LoiNhap(f"{t} tối đa {_TRAN_NGUYEN}.")
        return int(x)
    if t in _TAP:
        if v not in _TAP[t]:
            raise LoiNhap(f"{t} chỉ nhận {', '.join(_TAP[t])}.")
        return v
    if t == "phu_phi":
        if isinstance(v, str):
            def _cam(_c):       # NaN / Infinity / -Infinity: JSON của Python nhận, jsonb của Postgres không
                raise ValueError(_c)
            try:
                v = json.loads(v, parse_constant=_cam)
            except ValueError:
                raise LoiNhap("Phụ phí vùng không đọc được.")
        if not isinstance(v, dict) or any(k not in VUNG for k in v) or any(
                not (x == "khong_nhan" or (isinstance(x, (int, float)) and not isinstance(x, bool)
                                           and 0 <= x <= _TRAN_VUNG and math.isfinite(x)))
                for x in v.values()):
            raise LoiNhap("Phụ phí vùng: mỗi vùng một số ¥ (≥ 0) hoặc 'khong_nhan'.")
        return v
    return str(v).strip()[:DAI_TOI_DA]


def _chu(v) -> str:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dict):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, Decimal):
        return format(v, "f")
    return str(v)


def sua_giao_hang(conn, ma_doi_thu: str, thay_doi: dict, nguoi, da_xem=None, ghi_de: bool = False) -> None:
    """Một lần bấm Lưu ở pop-up giao hàng. ma_doi_thu 'KOME' → app.giao_hang_kome (mọi lần sửa đều đặt da_xac_nhan —
    một người đã đặt số; khoá 'xac_nhan': True = chỉ xác nhận số suy từ phiếu bán, không đổi trường nào). Đối thủ → một dòng app.dinh_chinh_giao_hang mỗi trường đổi.
    Chống sửa đè (đợt 4b): `da_xem` = sua_cuoi lúc mở pop-up, khoá 'giao:<bên>' (doi_thu.kiem_xung_dot); None = không
    kiểm (lệnh gọi cũ / script)."""
    kiem_xung_dot(conn, [f"giao:{ma_doi_thu}"], da_xem, ghi_de)
    thay_doi = dict(thay_doi or {})
    xac_nhan = bool(thay_doi.pop("xac_nhan", False))
    if not thay_doi and not xac_nhan:
        raise LoiNhap("Không có gì để sửa.")
    sach = {t: _kiem_truong(t, v) for t, v in thay_doi.items()}
    if ma_doi_thu == "KOME":
        cu = conn.execute(f"SELECT {', '.join(sach) or 'da_xac_nhan'} FROM app.giao_hang_kome").fetchone()
        dat = [f"{t} = %s" for t in sach] + ["sua_luc = now()", "sua_boi = %s", "da_xac_nhan = true"]
        conn.execute(f"UPDATE app.giao_hang_kome SET {', '.join(dat)}",
                     [json.dumps(v) if isinstance(v, dict) else v for v in sach.values()] + [nguoi])
        _ghi_nhat_ky(conn, "giao_hang", "giao:KOME", dict(zip(sach, cu)) if sach else None,
                     {**{t: _chu(v) for t, v in sach.items()}, **({"xac_nhan": True} if xac_nhan else {})}, nguoi)
        return
    if not conn.execute("SELECT 1 FROM app.doi_thu WHERE ma = %s", (ma_doi_thu,)).fetchone():
        raise LoiNhap("Không có đối thủ này.")
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.dinh_chinh_giao_hang (ma_doi_thu, truong, gia_tri_moi, nguoi_dung_id)
                           VALUES (%s, %s, %s, %s)""", [(ma_doi_thu, t, _chu(v), nguoi) for t, v in sach.items()])
    _ghi_nhat_ky(conn, "giao_hang", f"giao:{ma_doi_thu}", None, {t: _chu(v) for t, v in sach.items()}, nguoi)


_GIAO_HANG = """
SELECT json_build_object(
  'dong', (SELECT coalesce(json_agg(x ORDER BY x.thu_tu, x.ma_doi_thu), '[]')
           FROM (SELECT g.*, coalesce((SELECT max(nk.id) FROM app.doi_thu_nhat_ky nk
                                       WHERE nk.doi_tuong = 'giao:' || g.ma_doi_thu), 0) AS sua_cuoi
                 FROM mart.giao_hang_hien_hanh g) x),
  'bang_chung', (SELECT to_json(b) FROM mart.giao_hang_kome_bang_chung b))
"""


def giao_hang(conn) -> dict:
    """Tab Phí & giao hàng: `dong` = mart.giao_hang_hien_hanh (KOME đứng đầu — thu_tu 0) kèm `sua_cuoi` (max nhật ký
    'giao:<bên>', 0 = chưa sửa; pop-up gửi lại để chống sửa đè), `bang_chung` = dòng duy nhất của
    mart.giao_hang_kome_bang_chung. MỘT lượt hỏi."""
    return conn.execute(_GIAO_HANG).fetchone()[0]


def khoa_dieu_kien(fact_id, ma_doi_thu: str) -> str:
    """Khoá nhật ký của một điều kiện: 'dk:<fact_id>' (đã nạp) / 'dk:tay:<bên>' (MỌI dòng thêm tay của bên đó)."""
    return f"dk:{fact_id}" if fact_id is not None else f"dk:tay:{ma_doi_thu}"


def sua_dieu_kien(conn, *, fact_id, ma_doi_thu: str, loai: str, noi_dung: str, bo: bool, nguoi,
                  da_xem=None, ghi_de: bool = False) -> int:
    """Sửa / bỏ một điều kiện đã nạp (fact_id), hoặc thêm tay (fact_id None). Bỏ dòng thêm tay = gọi lại với bo=True
    và CÙNG (ma_doi_thu, loai, noi_dung) — xem mart.dieu_kien_hien_hanh (068). Chống sửa đè (đợt 4b): khoá
    `khoa_dieu_kien`; `da_xem` None = không kiểm. THÊM một dòng tay mới (fact_id None, bo False) không kiểm — thêm
    không đè lên ai (mọi dòng tay của bên chung một khoá, kiểm thì hai người thêm hai dòng khác nhau cũng bị 409)."""
    if fact_id is not None or bo:
        kiem_xung_dot(conn, [khoa_dieu_kien(fact_id, ma_doi_thu)], da_xem, ghi_de)
    if loai not in LOAI_DK:
        raise LoiNhap(f"Loại điều kiện chỉ nhận {', '.join(LOAI_DK)}.")
    nd = (noi_dung or "").strip()
    if not 1 <= len(nd) <= 300:
        raise LoiNhap("Nội dung điều kiện 1–300 ký tự.")
    if fact_id is not None and not conn.execute(
            "SELECT 1 FROM core.fact_dieu_kien_doi_thu WHERE id = %s AND ma_doi_thu = %s", (fact_id, ma_doi_thu)).fetchone():
        raise LoiNhap("Không tìm thấy điều kiện này (có thể lô đã bị hoàn tác).")
    if not conn.execute("SELECT 1 FROM app.doi_thu WHERE ma = %s", (ma_doi_thu,)).fetchone():
        raise LoiNhap("Không có đối thủ này.")
    i = conn.execute("""INSERT INTO app.dinh_chinh_dieu_kien (fact_id, ma_doi_thu, loai, noi_dung, bo, nguoi_dung_id)
                        VALUES (%s, %s, %s, %s, %s, %s) RETURNING id""",
                     (fact_id, ma_doi_thu, loai, nd, bool(bo), nguoi)).fetchone()[0]
    _ghi_nhat_ky(conn, "dieu_kien", khoa_dieu_kien(fact_id, ma_doi_thu),
                 None, {"loai": loai, "noi_dung": nd, "bo": bool(bo)}, nguoi)
    return i
