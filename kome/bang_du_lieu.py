"""Bảng dữ liệu sửa trực tiếp (Kho dữ liệu › Bảng dữ liệu, 072). Đặc tả 2026-09-30-bang-du-lieu-sua-design.md §5.

core VẪN chỉ đọc: bản sửa ghi vào sổ CHỈ THÊM `app.sua_du_lieu`; màn nào cũng đọc giá trị HIỆU LỰC qua `mart.dim_customer`,
`mart.dim_product`, `mart.bang_gia_kome`, `mart.ton_hien_tai` (luật `mart.ap_sua` / `mart.lech_obc`, viết một lần ở 072).
File này là một trong số ít chỗ được đọc `core.dim_*` THÔ (tests/test_doc_hieu_luc.py): `gia_tri_obc` phải là ĐÚNG chữ mà
view hiệu lực so (`<cột core>::text`, `bang_gia_kome.gia_obc::text`, `ton_hien_tai.so_luong_obc::text` / `best_before_obc`)
— lệch một ký tự là bản sửa lặng lẽ không bao giờ áp.

Giá trị gửi trình duyệt là chuỗi dạng chuẩn, dựng bằng MỘT hàm (`_hien`) từ giá trị thô mà MỘT câu SQL (`_doc_tho`) trả ra —
GET, phép so 409 và phép so "về OBC" đều đi qua đúng hai thứ đó.
"""
from __future__ import annotations

import re
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from psycopg.types.json import Jsonb

LOAI = ("sp", "kh")
TOI_DA_O = 2000
DAI_TOI_DA = 200
BANG = {"sp": "san_pham", "kh": "khach"}

NHOM_DM = "Danh mục OBC"
NHOM_GIA = "Giá 売価No. (chưa thuế)"
NHOM_TON = "Tồn & hạn theo lô"
NHOM_CS = "Chỉ số (chỉ xem)"

# (mã cột = tên cột core / sổ, nhãn, kiểu). Phải đúng danh sách cột CHECK sua_du_lieu_cot_check của 072 (có test canh).
_DM = {
    "kh": [("customer_name", "Tên", "chu"), ("branch_name", "Chi nhánh", "chu"), ("rank_code", "Hạng OBC", "chon"),
           ("salesperson_code", "Người phụ trách", "chon"), ("closing_day_code", "Ngày chốt", "chon"),
           ("postcode", "Mã bưu điện", "chu"), ("prefecture", "Tỉnh", "chon"), ("city", "Thành phố", "chu"),
           ("address", "Địa chỉ", "chu"), ("building", "Toà nhà", "chu"), ("phone", "Điện thoại", "chu"),
           ("transfer_account", "TK chuyển khoản", "chu")],
    "sp": [("product_name", "Tên hàng", "chu"), ("name_ja", "Tên Nhật", "chu"), ("kind_code", "Loại (有形/無形)", "chon"),
           ("food_category_code", "Ngành", "chon"), ("rank_code", "Hạng", "chon"), ("compete_code", "Mã cạnh tranh", "chu"),
           ("barcode", "JAN", "chu"), ("unit", "Đơn vị", "chu"), ("case_qty", "Số / thùng", "so"),
           ("shelf_code", "Kệ", "chu"), ("introduced_on", "Ngày ra mắt", "chu"), ("pack1_code", "荷姿", "chu"),
           ("pack1_base_qty", "Số gói / 荷姿", "so")],
}
COT_DANH_MUC = {l: [c[0] for c in ds] for l, ds in _DM.items()}
_KIEU_DM = {l: {c[0]: c[2] for c in ds} for l, ds in _DM.items()}
_CHI_SO = {"sp": [("dt_12t", "DT 12 tháng", "so"), ("ton_tong", "Tồn tổng", "so")],
           "kh": [("dt_12t", "DT 12 tháng", "so"), ("lan_cuoi", "Lần mua cuối", "ngay")]}
_QC = {"00": "バラ", "02": "ケース"}
_COT_GIA = re.compile(r"^gia:([0-9A-Za-z]{1,8})\|([0-9A-Za-z]{1,8})$")
_COT_TON = re.compile(r"^(ton|han):([0-9A-Za-z]{1,16})$")
_NGAY_ISO = re.compile(r"^([0-9]{4})-([0-9]{2})-([0-9]{2})$")
_NGAY_OBC = re.compile(r"^([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日$")
_SO_NGHIN = re.compile(r"^[0-9]{1,3}(,[0-9]{3})+(\.[0-9]+)?$")
KHONG_HAN = "không hạn"
KHONG_HAN_OBC = "賞味期限なし"


class LoiO(Exception):
    """400 — lỗi từng ô (khoá `f"{k}\\t{cot}"`), gom một lần, KHÔNG ghi gì."""

    def __init__(self, thong_diep: str, o_loi: dict | None = None):
        super().__init__(thong_diep)
        self.o_loi = o_loi or {}


class XungDotO(Exception):
    """409 — ô đã đổi sau lúc trình duyệt đọc (`thay` ≠ hiệu lực hiện tại). KHÔNG ghi gì."""

    def __init__(self, xung_dot: list):
        super().__init__("Có ô đã được đổi sau lúc bạn mở bảng — xem giá trị mới rồi lưu lại.")
        self.xung_dot = xung_dot


class KhongDuQuyen(Exception):
    pass


# ---------------------------------------------------------------------------------------------------------------------
# Hạn sử dụng: trình duyệt dùng YYYY-MM-DD / "không hạn"; OBC ghi 'YYYY年MM月DD日' / '賞味期限なし'.
# ---------------------------------------------------------------------------------------------------------------------

def han_obc(iso_hoac_chu: str) -> str:
    s = (iso_hoac_chu or "").strip()
    if s == "":
        return ""
    if s.lower() == KHONG_HAN:
        return KHONG_HAN_OBC
    m = _NGAY_ISO.match(s)
    if not m:
        raise ValueError(f"Hạn phải dạng YYYY-MM-DD hoặc '{KHONG_HAN}'")
    d = date(int(m[1]), int(m[2]), int(m[3]))          # ngày không có thật → ValueError
    if d.year < 1:
        raise ValueError("Năm không hợp lệ")
    return f"{d.year:04d}年{d.month:02d}月{d.day:02d}日"


def han_iso(chu_obc: str | None) -> str:
    if chu_obc is None or chu_obc == "":
        return ""
    if chu_obc.strip(" 　") == KHONG_HAN_OBC:
        return KHONG_HAN
    m = _NGAY_OBC.match(chu_obc)
    if m:
        try:
            return date(int(m[1]), int(m[2]), int(m[3])).isoformat()
        except ValueError:
            pass
    return chu_obc


# ---------------------------------------------------------------------------------------------------------------------
# Một câu SQL đọc thô (GET, 409, về OBC, đọc lại sau khi lưu)
# ---------------------------------------------------------------------------------------------------------------------

def _obc_case(alias: str, loai: str, cot_sql: str) -> str:
    """Giá trị OBC (::text của cột core) của một cột danh mục tên động — MỘT biểu thức cho cả `lech` lẫn `gia_tri_obc`."""
    nhanh = " ".join(f"WHEN '{c}' THEN {alias}.{c}::text" for c in COT_DANH_MUC[loai])
    return f"CASE {cot_sql} {nhanh} END"


def _cot_e(loai: str) -> str:
    return ", ".join(f"e.{c}" for c in COT_DANH_MUC[loai])


def _sql_sp(chi_so: bool) -> str:
    dm = ", ".join(f"p.{c}::text" for c in COT_DANH_MUC["sp"])
    # Chỉ số chỉ xem đắt (quét mart.ban_den_moc) — chỉ GET cần; hai lượt đọc trong luu() bỏ hẳn CTE này.
    b = """b AS (SELECT s.product_code AS k, sum(s.amount - s.tax_amount)::text AS dt
      FROM mart.ban_den_moc s CROSS JOIN mart.moc_thoi_gian m
      WHERE s.sales_date > m.hom_nay - 365 AND s.sales_date <= m.hom_nay
        AND (%(ma)s::text[] IS NULL OR s.product_code = ANY(%(ma)s::text[]))
      GROUP BY s.product_code),""" if chi_so else ""
    b_cot, b_noi = ("b.dt", "LEFT JOIN b ON b.k = e.k") if chi_so else ("NULL", "")
    return f"""
WITH bg AS MATERIALIZED (
    SELECT g.product_code, g.pack_code, g.price_level, g.gia_chua_thue, g.gia_obc, g.da_sua, g.tu_ngay
    FROM mart.bang_gia_kome g
    WHERE g.hien_hanh AND (%(ma)s::text[] IS NULL OR g.product_code = ANY(%(ma)s::text[]))
),
th AS MATERIALIZED (
    SELECT t.product_code, t.warehouse_code, t.so_luong, t.best_before, t.so_luong_obc, t.best_before_obc,
           t.sua_so_luong, t.sua_han
    FROM mart.ton_hien_tai t
    WHERE %(ma)s::text[] IS NULL OR t.product_code = ANY(%(ma)s::text[])
),
sm AS MATERIALIZED (
    SELECT m.bang, m.khoa, m.cot, m.gia_tri, m.gia_tri_obc, m.bo, m.luc, u.ten_dang_nhap AS ai,
           split_part(m.khoa, '|', 1) AS k
    FROM mart.sua_moi_nhat m
    LEFT JOIN app.nguoi_dung u ON u.id = m.nguoi_dung_id
    WHERE m.bang IN ('san_pham', 'gia', 'ton')
      AND (%(ma)s::text[] IS NULL OR split_part(m.khoa, '|', 1) = ANY(%(ma)s::text[]))
),
e AS (
    SELECT p.product_code AS k, {dm} FROM mart.dim_product p
    WHERE %(ma)s::text[] IS NULL OR p.product_code = ANY(%(ma)s::text[])
),
g AS (SELECT product_code AS k, jsonb_object_agg(pack_code || '|' || price_level, gia_chua_thue::text) AS gia
      FROM bg GROUP BY product_code),
t AS (SELECT product_code AS k,
             jsonb_object_agg(warehouse_code, jsonb_build_array(so_luong::text, best_before)) AS ton,
             sum(so_luong)::text AS ton_tong
      FROM th GROUP BY product_code),
{b}
lech AS (
    SELECT sm.k, sm.cot AS ma_cot, {_obc_case('o', 'sp', 'sm.cot')} AS obc, sm.ai, sm.luc
    FROM sm JOIN core.dim_product o ON o.product_code = sm.khoa
    WHERE sm.bang = 'san_pham' AND NOT sm.bo
      AND mart.lech_obc({_obc_case('o', 'sp', 'sm.cot')},
                        jsonb_build_object(sm.cot, jsonb_build_array(sm.gia_tri, sm.gia_tri_obc)), sm.cot)
    UNION ALL
    SELECT sm.k, 'gia:' || bg.pack_code || '|' || bg.price_level, bg.gia_obc::text, sm.ai, sm.luc
    FROM bg JOIN sm ON sm.bang = 'gia' AND sm.cot = 'gia_chua_thue'
                   AND sm.khoa = bg.product_code || '|' || bg.pack_code || '|' || bg.price_level
    WHERE bg.da_sua
    UNION ALL
    SELECT sm.k, CASE sm.cot WHEN 'stock_qty' THEN 'ton:' ELSE 'han:' END || th.warehouse_code,
           CASE sm.cot WHEN 'stock_qty' THEN th.so_luong_obc::text ELSE th.best_before_obc END, sm.ai, sm.luc
    FROM th JOIN sm ON sm.bang = 'ton' AND sm.khoa = th.product_code || '|' || th.warehouse_code
    WHERE (sm.cot = 'stock_qty' AND th.sua_so_luong) OR (sm.cot = 'best_before' AND th.sua_han)
),
can AS (SELECT x ->> 0 AS bang, x ->> 1 AS khoa, x ->> 2 AS cot FROM jsonb_array_elements(%(can)s::jsonb) x),
obc AS (
    SELECT can.bang, can.khoa, can.cot,
           CASE can.bang WHEN 'san_pham' THEN {_obc_case('o', 'sp', 'can.cot')}
                         WHEN 'gia' THEN bg.gia_obc::text
                         WHEN 'ton' THEN CASE can.cot WHEN 'stock_qty' THEN th.so_luong_obc::text
                                                      ELSE th.best_before_obc END END AS raw,
           coalesce(o.product_code, bg.product_code, th.product_code) IS NOT NULL AS co,
           sm.gia_tri_obc AS m_obc, sm.bo AS m_bo, sm.ai, sm.luc
    FROM can
    LEFT JOIN core.dim_product o ON can.bang = 'san_pham' AND o.product_code = can.khoa
    LEFT JOIN bg ON can.bang = 'gia' AND bg.product_code || '|' || bg.pack_code || '|' || bg.price_level = can.khoa
    LEFT JOIN th ON can.bang = 'ton' AND th.product_code || '|' || th.warehouse_code = can.khoa
    LEFT JOIN sm ON sm.bang = can.bang AND sm.khoa = can.khoa AND sm.cot = can.cot
)
SELECT
    (SELECT json_agg(json_build_array(e.k, {_cot_e('sp')}, g.gia, t.ton, {b_cot}, t.ton_tong) ORDER BY e.k)
     FROM e LEFT JOIN g ON g.k = e.k LEFT JOIN t ON t.k = e.k {b_noi}),
    (SELECT json_agg(json_build_array(k, ma_cot, obc, ai, luc)) FROM lech),
    (SELECT json_agg(json_build_array(bang, khoa, cot, raw, co, m_obc, m_bo, ai, luc)) FROM obc),
    json_build_object(
      'gia', (SELECT json_agg(json_build_array(pack_code, price_level)
                              ORDER BY price_level <> 'std', price_level, pack_code)
              FROM (SELECT DISTINCT pack_code, price_level FROM bg) x),
      'kho', (SELECT json_agg(json_build_array(warehouse_code, warehouse_name) ORDER BY warehouse_code)
              FROM core.dim_warehouse),
      'kind_code', (SELECT json_agg(json_build_array(ma, ten) ORDER BY ma) FROM (
          SELECT DISTINCT ON (kind_code) kind_code AS ma, kind_name AS ten FROM core.dim_product
          WHERE coalesce(kind_code, '') <> '' ORDER BY kind_code, coalesce(kind_name, '') = '', kind_name) x),
      'food_category_code', (SELECT json_agg(json_build_array(ma, ten) ORDER BY ma) FROM (
          SELECT DISTINCT ON (food_category_code) food_category_code AS ma, food_category_name AS ten
          FROM core.dim_product WHERE coalesce(food_category_code, '') <> ''
          ORDER BY food_category_code, coalesce(food_category_name, '') = '', food_category_name) x),
      'rank_code', (SELECT json_agg(json_build_array(ma, ten) ORDER BY ma) FROM (
          SELECT DISTINCT ON (rank_code) rank_code AS ma, rank_name AS ten FROM core.dim_product
          WHERE coalesce(rank_code, '') <> '' ORDER BY rank_code, coalesce(rank_name, '') = '', rank_name) x),
      'anh_ton', (SELECT max(snapshot_date)::text FROM core.fact_inventory_daily
                  WHERE snapshot_date <= (SELECT coalesce(mart.moc_lui(), 'infinity'::date))),
      'lan_nap_gia', (SELECT max(tu_ngay)::text FROM bg))
"""


def _sql_kh(chi_so: bool) -> str:
    dm = ", ".join(f"c.{x}::text" for x in COT_DANH_MUC["kh"])
    # mart.doanh_thu_12t dựng trên mart.khach_360 (~1,2 s trên CSDL thật) — chỉ GET cần; luu() bỏ hai CTE này.
    dl = """d AS (SELECT x.customer_code AS k, x.dt_12t::text AS dt FROM mart.doanh_thu_12t x
      WHERE %(ma)s::text[] IS NULL OR x.customer_code = ANY(%(ma)s::text[])),
l AS (SELECT x.customer_code AS k, max(x.sales_date)::text AS lan_cuoi FROM mart.lan_mua x
      WHERE %(ma)s::text[] IS NULL OR x.customer_code = ANY(%(ma)s::text[]) GROUP BY x.customer_code),""" if chi_so else ""
    dl_cot, dl_noi = ("d.dt, l.lan_cuoi", "LEFT JOIN d ON d.k = e.k LEFT JOIN l ON l.k = e.k") if chi_so else ("NULL, NULL", "")
    return f"""
WITH sm AS MATERIALIZED (
    SELECT m.bang, m.khoa, m.cot, m.gia_tri, m.gia_tri_obc, m.bo, m.luc, u.ten_dang_nhap AS ai, m.khoa AS k
    FROM mart.sua_moi_nhat m
    LEFT JOIN app.nguoi_dung u ON u.id = m.nguoi_dung_id
    WHERE m.bang = 'khach' AND (%(ma)s::text[] IS NULL OR m.khoa = ANY(%(ma)s::text[]))
),
e AS (
    SELECT c.customer_code AS k, {dm} FROM mart.dim_customer c
    WHERE c.is_current AND (%(ma)s::text[] IS NULL OR c.customer_code = ANY(%(ma)s::text[]))
),
{dl}
lech AS (
    SELECT sm.k, sm.cot AS ma_cot, {_obc_case('o', 'kh', 'sm.cot')} AS obc, sm.ai, sm.luc
    FROM sm JOIN core.dim_customer o ON o.is_current AND o.customer_code = sm.khoa
    WHERE NOT sm.bo
      AND mart.lech_obc({_obc_case('o', 'kh', 'sm.cot')},
                        jsonb_build_object(sm.cot, jsonb_build_array(sm.gia_tri, sm.gia_tri_obc)), sm.cot)
),
can AS (SELECT x ->> 0 AS bang, x ->> 1 AS khoa, x ->> 2 AS cot FROM jsonb_array_elements(%(can)s::jsonb) x),
obc AS (
    SELECT can.bang, can.khoa, can.cot, {_obc_case('o', 'kh', 'can.cot')} AS raw, o.customer_code IS NOT NULL AS co,
           sm.gia_tri_obc AS m_obc, sm.bo AS m_bo, sm.ai, sm.luc
    FROM can
    LEFT JOIN core.dim_customer o ON o.is_current AND o.customer_code = can.khoa
    LEFT JOIN sm ON sm.bang = can.bang AND sm.khoa = can.khoa AND sm.cot = can.cot
)
SELECT
    (SELECT json_agg(json_build_array(e.k, {_cot_e('kh')}, {dl_cot}) ORDER BY e.k)
     FROM e {dl_noi}),
    (SELECT json_agg(json_build_array(k, ma_cot, obc, ai, luc)) FROM lech),
    (SELECT json_agg(json_build_array(bang, khoa, cot, raw, co, m_obc, m_bo, ai, luc)) FROM obc),
    json_build_object(
      'rank_code', (SELECT json_agg(json_build_array(ma, ten) ORDER BY ma) FROM (
          SELECT DISTINCT ON (rank_code) rank_code AS ma, rank_name AS ten FROM core.dim_customer
          WHERE is_current AND coalesce(rank_code, '') <> ''
          ORDER BY rank_code, coalesce(rank_name, '') = '', rank_name) x),
      'salesperson_code', (SELECT json_agg(json_build_array(salesperson_code, ten) ORDER BY salesperson_code)
                           FROM core.dim_salesperson),
      'closing_day_code', (SELECT json_agg(json_build_array(ma, ten) ORDER BY ma) FROM (
          SELECT DISTINCT ON (closing_day_code) closing_day_code AS ma, closing_day_name AS ten FROM core.dim_customer
          WHERE is_current AND coalesce(closing_day_code, '') <> ''
          ORDER BY closing_day_code, coalesce(closing_day_name, '') = '', closing_day_name) x),
      'prefecture', (SELECT json_agg(json_build_array(ten, ten) ORDER BY ma_jis) FROM core.dim_prefecture))
"""


def _doc_tho(conn, loai: str, ma: list[str] | None = None, can: list | None = None, chi_so: bool = True) -> dict:
    """ĐÚNG MỘT lượt hỏi. `ma` None = mọi dòng; `can` = [(bang, khoa, cot)] cần giá trị OBC + dòng sổ mới nhất (khi lưu).

    `chi_so=False` (hai lượt đọc của luu()): KHÔNG tính chỉ số chỉ xem đắt — `dt_12t` (cả sp lẫn kh, đọc
    mart.ban_den_moc / mart.doanh_thu_12t) và `lan_cuoi` (kh) — và dòng trả về KHÔNG mang các khoá đó. `ton_tong` (sp)
    vẫn có: nó cộng từ chính CTE tồn đã đọc (không tốn thêm) và đổi theo ô tồn vừa sửa."""
    sql = _sql_sp(chi_so) if loai == "sp" else _sql_kh(chi_so)
    dong, lech, obc, phu = conn.execute(sql, {"ma": ma, "can": Jsonb([list(x) for x in (can or [])])}).fetchone()
    n = len(COT_DANH_MUC[loai])
    ra = {}
    for r in dong or []:
        o = dict(zip(COT_DANH_MUC[loai], r[1:1 + n]))
        if loai == "sp":
            gia, ton, dt, o["ton_tong"] = r[1 + n:]
            if chi_so:
                o["dt_12t"] = dt
            for kq, v in (gia or {}).items():
                o[f"gia:{kq}"] = v
            for kho, (sl, bb) in (ton or {}).items():
                o[f"ton:{kho}"], o[f"han:{kho}"] = sl, bb
        else:
            if chi_so:
                o["dt_12t"], o["lan_cuoi"] = r[1 + n:]
        ra[r[0]] = o
    return {"dong": ra, "lech": lech or [], "obc": obc or [], "phu": phu}


def _hien(ma_cot: str, tho):
    """Giá trị THÔ (::text từ CSDL, chữ OBC) → chuỗi dạng chuẩn gửi trình duyệt. MỘT hàm cho GET, 409 và về OBC."""
    if ma_cot.startswith("han:"):
        return han_iso(tho)
    if tho is None:
        return None
    if ma_cot.startswith("gia:"):
        return str(Decimal(tho).quantize(Decimal(1), rounding=ROUND_HALF_UP))    # = round() của Postgres với số > 0
    return tho


def _giong(a, b) -> bool:
    return (a or "") == (b or "")


def _cot(loai: str, phu: dict) -> list[dict]:
    ra = []
    for ma, nhan, kieu in _DM[loai]:
        c = {"ma": ma, "nhan": nhan, "nhom": NHOM_DM, "kieu": kieu, "sua": True}
        if kieu == "chon":
            c["chon"] = [list(x) for x in (phu.get(ma) or [])]
        ra.append(c)
    if loai == "sp":
        for qc, lv in phu.get("gia") or []:
            bac = "標準価格" if lv == "std" else (f"No.{int(lv)}" if lv.isdigit() else lv) + (" (KM)" if lv == "10" else "")
            ra.append({"ma": f"gia:{qc}|{lv}", "nhan": f"{bac} · {_QC.get(qc, qc)}", "nhom": NHOM_GIA, "kieu": "so",
                       "sua": True})
        for kho, ten in phu.get("kho") or []:
            ra.append({"ma": f"ton:{kho}", "nhan": f"Tồn · {ten}", "nhom": NHOM_TON, "kieu": "so", "sua": True})
            ra.append({"ma": f"han:{kho}", "nhan": f"Hạn · {ten}", "nhom": NHOM_TON, "kieu": "ngay", "sua": True})
    ra += [{"ma": ma, "nhan": nhan, "nhom": NHOM_CS, "kieu": kieu, "sua": False} for ma, nhan, kieu in _CHI_SO[loai]]
    return ra


def _dong_va_lech(tho: dict) -> tuple[list, dict]:
    dong = [{"k": k, "o": {c: _hien(c, v) for c, v in o.items()}} for k, o in tho["dong"].items()]
    lech = {f"{k}\t{c}": {"obc": _hien(c, obc), "ai": ai, "luc": luc} for k, c, obc, ai, luc in tho["lech"]}
    return dong, lech


def doc(conn, loai: str, sua_duoc: bool = True) -> dict:
    """GET — ĐÚNG 1 lượt hỏi. Ô `gia:` / `ton:` / `han:` VẮNG trong `o` = ô OBC không có (không sửa được)."""
    if loai not in LOAI:
        raise LoiO(f"loai phải là một trong {', '.join(LOAI)}")
    tho = _doc_tho(conn, loai)
    dong, lech = _dong_va_lech(tho)
    phu = tho["phu"]
    return {"loai": loai, "sua_duoc": bool(sua_duoc), "cot": _cot(loai, phu), "dong": dong, "lech": lech,
            "anh_ton": phu.get("anh_ton"), "lan_nap_gia": phu.get("lan_nap_gia")}


# ---------------------------------------------------------------------------------------------------------------------
# Lưu
# ---------------------------------------------------------------------------------------------------------------------

def _so_thap_phan(s: str) -> Decimal:
    s = s.strip().replace(" ", "")
    if _SO_NGHIN.match(s):
        s = s.replace(",", "")
    if not re.fullmatch(r"[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)", s):
        raise ValueError("Phải là một số (vd 24 hoặc 83.75)")
    try:
        d = Decimal(s)
    except InvalidOperation:
        raise ValueError("Phải là một số")
    return d


def _chuan_so_luong(v) -> str:
    d = _so_thap_phan(str(v if v is not None else ""))
    if d < 0:
        raise ValueError("Số lượng phải ≥ 0")
    d = d.quantize(Decimal("0.0001"), rounding=ROUND_HALF_UP)
    if d == 0:
        d = Decimal("0.0000")
    if d >= Decimal(10) ** 10:
        raise ValueError("Số quá lớn")
    return format(d, "f")


def _chuan_gia(v) -> str:
    d = _so_thap_phan(str(v if v is not None else ""))
    if d != d.to_integral_value():
        raise ValueError("Giá phải là số nguyên yên")
    if d <= 0:
        raise ValueError("Giá phải là số > 0")
    if d >= Decimal(10) ** 12:
        raise ValueError("Giá quá lớn")
    return str(int(d))


def _dich(loai: str, k: str, ma_cot: str) -> tuple[str, str, str, str]:
    """(bang, khoa, cot trong sổ, kiểu) của một ô, hoặc ValueError nếu cột không sửa được."""
    if ma_cot in _KIEU_DM[loai]:
        return BANG[loai], k, ma_cot, _KIEU_DM[loai][ma_cot]
    if loai == "sp":
        m = _COT_GIA.match(ma_cot)
        if m:
            return "gia", f"{k}|{m[1]}|{m[2]}", "gia_chua_thue", "gia"
        m = _COT_TON.match(ma_cot)
        if m:
            return ("ton", f"{k}|{m[2]}", "stock_qty", "so") if m[1] == "ton" else \
                   ("ton", f"{k}|{m[2]}", "best_before", "ngay")
    if ma_cot in {c[0] for c in _CHI_SO[loai]}:
        raise ValueError("Cột này chỉ xem, không sửa được")
    raise ValueError("Cột này không sửa được")


def _chuan(kieu: str, v) -> str:
    """Chuẩn hoá giá trị người gõ về dạng LƯU (qua được CHECK của 072); ValueError nếu sai."""
    if kieu == "so":
        return _chuan_so_luong(v)
    if kieu == "gia":
        return _chuan_gia(v)
    if kieu == "ngay":
        return han_obc("" if v is None else str(v))
    s = "" if v is None else str(v).strip()
    if len(s) > DAI_TOI_DA:
        raise ValueError(f"Tối đa {DAI_TOI_DA} ký tự")
    return s


def luu(conn, loai: str, o: list[dict], nguoi_id: int | None, co_quyen: bool) -> dict:
    """POST — kiểm quyền → kiểm dạng → khoá advisory → đọc (1 lượt) → lỗi ô (400) → xung đột (409) → ghi. Commit do route.

    Trả `{dong, lech, so_o}`. `dong` = các dòng đã đọc lại để trình duyệt VÁ bộ đệm: CHỈ mang cột danh mục / giá / tồn /
    hạn (+ `ton_tong` của sp) — KHÔNG mang chỉ số chỉ xem `dt_12t` / `lan_cuoi` (không tính lại khi lưu; trình duyệt giữ
    giá trị đã có). Cả hai lượt đọc ở đây dùng `chi_so=False`: không đụng mart.doanh_thu_12t / mart.ban_den_moc."""
    if not co_quyen:
        raise KhongDuQuyen("Bạn cần cờ 'Sửa dữ liệu' để lưu.")
    if loai not in LOAI:
        raise LoiO(f"loai phải là một trong {', '.join(LOAI)}")
    if not isinstance(o, list):
        raise LoiO("o phải là một danh sách ô")
    if len(o) > TOI_DA_O:
        raise LoiO(f"Tối đa {TOI_DA_O} ô mỗi lần lưu")
    loi: dict[str, str] = {}
    o_hl = []                                                   # (khoá dây, k, ma_cot, bang, khoa, cot, kieu, gia_tri gốc, thay)
    da_thay: set[str] = set()                                   # khoá dây đã gặp — phát hiện ô lặp trong O(n)
    for i, x in enumerate(o):
        if not isinstance(x, dict) or not isinstance(x.get("k"), str) or not isinstance(x.get("cot"), str) \
                or not x["k"] or len(x["k"]) > 64 or "|" in x["k"] or "thay" not in x or "gia_tri" not in x:
            loi[f"#{i}"] = "Ô thiếu hoặc sai k / cot / gia_tri / thay"
            continue
        kd = f"{x['k']}\t{x['cot']}"
        if kd in da_thay:
            loi[kd] = "Ô lặp trong cùng một lần lưu"
            continue
        da_thay.add(kd)
        try:
            bang, khoa, cot, kieu = _dich(loai, x["k"], x["cot"])
        except ValueError as e:
            loi[kd] = str(e)
            continue
        o_hl.append((kd, x["k"], x["cot"], bang, khoa, cot, kieu, x["gia_tri"], x["thay"]))
    # Lỗi dạng ở trên CHƯA ném: ô còn lại vẫn được kiểm với CSDL để người sửa thấy MỌI lỗi trong một lần.
    if not o_hl:
        if loi:
            raise LoiO("Có ô không hợp lệ — không lưu ô nào.", loi)
        return {"dong": [], "lech": {}, "so_o": 0}

    conn.execute("SELECT pg_advisory_xact_lock(hashtext('bang_du_lieu:' || %s))", (loai,))
    tho = _doc_tho(conn, loai, sorted({y[1] for y in o_hl}), [(y[3], y[4], y[5]) for y in o_hl], chi_so=False)
    obc = {(r[0], r[1], r[2]): r for r in tho["obc"]}
    chon = {c: {str(x[0]) for x in (tho["phu"].get(c) or [])} for c, _, kieu in _DM[loai] if kieu == "chon"}

    ghi, xung = [], []
    for kd, k, ma_cot, bang, khoa, cot, kieu, gt, thay in o_hl:
        _, _, _, raw, co, m_obc, m_bo, ai, luc = obc[(bang, khoa, cot)]
        hien_obc = _hien(ma_cot, raw)
        if not co or k not in tho["dong"]:
            loi[kd] = "Ô này không có trong OBC — không sửa được" if bang in ("gia", "ton") else "Không có mã này"
            continue
        try:
            moi = _chuan(kieu, gt)
        except ValueError as e:
            loi[kd] = str(e)
            continue
        hien_moi = _hien(ma_cot, moi)
        ve_obc = _giong(hien_moi, hien_obc)
        if kieu == "chon" and not ve_obc and moi not in chon[ma_cot]:
            loi[kd] = "Tỉnh không có trong 47 tỉnh" if ma_cot == "prefecture" else "Mã không có trong danh sách"
            continue
        hien_nay = _hien(ma_cot, tho["dong"][k].get(ma_cot))
        if not _giong(hien_nay, None if thay is None else str(thay)):
            # ai / lúc chỉ khi dòng sổ mới nhất (bản sửa hay lần về OBC) còn là thứ đang hiện: OBC đã ghi khác thì
            # giá trị mới đến từ lần nạp OBC, không từ ai cả.
            ton_tai = m_bo is not None and m_obc == raw
            xung.append({"k": k, "cot": ma_cot, "gia_tri": hien_nay,
                         "ai": ai if ton_tai else None, "luc": luc if ton_tai else None})
            continue
        if _giong(hien_moi, hien_nay):
            continue
        truoc = tho["dong"][k].get(ma_cot)
        ghi.append((bang, khoa, cot, raw if ve_obc else moi, raw, truoc, ve_obc, nguoi_id))
    if loi:
        raise LoiO("Có ô không hợp lệ — không lưu ô nào.", loi)
    if xung:
        raise XungDotO(xung)
    if ghi:
        with conn.cursor() as cur:
            cur.executemany("""INSERT INTO app.sua_du_lieu (bang, khoa, cot, gia_tri, gia_tri_obc, gia_tri_truoc, bo,
                                                            nguoi_dung_id)
                               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""", ghi)
    dong, lech = _dong_va_lech(_doc_tho(conn, loai, sorted({y[1] for y in o_hl}), chi_so=False))
    return {"dong": dong, "lech": lech, "so_o": len(ghi)}
