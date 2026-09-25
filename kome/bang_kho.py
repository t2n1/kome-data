"""Màn Kho dữ liệu → xem từng bảng (đợt C, 2026-09-24): Dữ liệu · Cột & khoá · Lần nạp.

CHỈ ĐỌC, bằng vai trò `kome_app` (kết nối của các trang đọc), trong giao dịch
`READ ONLY` có `statement_timeout`. Tên bảng KHÔNG BAO GIỜ ghép thẳng vào SQL:
nó phải là một quan hệ có thật của `core`/`mart`/`meta` mà vai trò này được
SELECT (tra `pg_class` + `has_table_privilege`), rồi mới vào câu lệnh qua
`psycopg.sql.Identifier`. Schema `app` bị loại hẳn (tài khoản, băm mật khẩu).

Đặc tả: docs/superpowers/specs/2026-09-24-kho-du-lieu-theo-thiet-ke-design.md §C.
"""
from __future__ import annotations

import csv
import io
import re
from datetime import date, datetime
from decimal import Decimal

from psycopg import sql

from kome.config import SPECS
from kome.nguon_dung import bang_an

SCHEMA = ("core", "mart", "meta")
MOI_TRANG = 50
TOI_DA_CSV = 50_000
HET_GIO = "20s"
_TEN = re.compile(r"^(core|mart|meta)\.([a-z_][a-z0-9_]*)$")
CHIP = ("tat_ca", "thang", "lo")


class KhongCoBang(LookupError):
    pass


def _chi_doc(conn) -> None:
    conn.execute("SET TRANSACTION READ ONLY")
    conn.execute(f"SET LOCAL statement_timeout = '{HET_GIO}'")


def danh_sach(conn) -> list[dict]:
    """Mọi bảng/view đọc được của core/mart/meta. Số dòng của bảng là
    `reltuples` (ước tính sau ANALYZE); view không có số dòng — nó tính lúc xem."""
    _chi_doc(conn)
    rows = conn.execute(
        """SELECT n.nspname, c.relname, c.relkind::text, greatest(c.reltuples, 0)::bigint,
                  obj_description(c.oid, 'pg_class')
           FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = ANY(%s) AND c.relkind IN ('r', 'v', 'm')
             AND has_table_privilege(c.oid, 'SELECT')
           ORDER BY array_position(%s, n.nspname::text), c.relname""",
        (list(SCHEMA), list(SCHEMA))).fetchall()
    conn.rollback()
    # Bảng/view của nguồn công ty chưa dùng không lên danh sách (kome/nguon_dung.py);
    # gõ thẳng /kho-du-lieu/bang/<tên> vẫn xem được — ẩn, không phải khoá.
    an = bang_an(SPECS)
    rows = [r for r in rows if f"{r[0]}.{r[1]}" not in an]
    return [{"schema": s, "ten": f"{s}.{t}", "ngan": t, "loai": "bang" if k == "r" else "view",
             "so_dong": n if k == "r" else None, "mo_ta": " ".join((m or "").split()) or None}
            for s, t, k, n, m in rows]


def _nguon_obc(ten: str) -> list[dict]:
    """File OBC nào đổ vào bảng này, kèm {cột hệ thống: tên cột OBC}."""
    return [{"spec": k, "ja": s.display_name, "cot": {v: ja for ja, v in s.columns.items()}}
            for k, s in SPECS.items() if s.core_table == ten]


def thong_tin(conn, ten: str) -> dict:
    """Bảng + cột + khoá + các lần nạp vào bảng đó. 2 lượt hỏi."""
    m = _TEN.match(ten or "")
    if not m:
        raise KhongCoBang(ten)
    _chi_doc(conn)
    rows = conn.execute(
        """SELECT c.relkind::text, greatest(c.reltuples, 0)::bigint, obj_description(c.oid, 'pg_class'),
                  a.attname, format_type(a.atttypid, a.atttypmod), a.attnotnull,
                  coalesce(a.attnum = ANY(pk.conkey), false),
                  (SELECT fn.nspname || '.' || f.relname || '.' || fa.attname
                     FROM pg_constraint k
                     JOIN pg_class f ON f.oid = k.confrelid JOIN pg_namespace fn ON fn.oid = f.relnamespace
                     JOIN pg_attribute fa ON fa.attrelid = f.oid
                          AND fa.attnum = k.confkey[array_position(k.conkey, a.attnum)]
                    WHERE k.conrelid = c.oid AND k.contype = 'f' AND a.attnum = ANY(k.conkey) LIMIT 1),
                  col_description(c.oid, a.attnum)
           FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
           LEFT JOIN pg_constraint pk ON pk.conrelid = c.oid AND pk.contype = 'p'
           WHERE n.nspname = %s AND c.relname = %s AND c.relkind IN ('r', 'v', 'm')
             AND has_table_privilege(c.oid, 'SELECT')
           ORDER BY a.attnum""", (m.group(1), m.group(2))).fetchall()
    if not rows:
        conn.rollback()
        raise KhongCoBang(ten)
    nguon = _nguon_obc(ten)
    ja = {he: j for n in nguon for he, j in n["cot"].items()}
    cot = [{"ten": r[3], "kieu": r[4], "khong_rong": r[5], "khoa_chinh": r[6], "khoa_ngoai": r[7],
            "ghi_chu": " ".join((r[8] or "").split()) or None, "ja": ja.get(r[3])} for r in rows]
    lan_nap = []
    if nguon:
        lan_nap = [{"batch_id": b, "spec": s, "ten_file": f, "duong_dan": d, "digest": g, "nap_luc": l,
                    "so_dong": n, "tong_tien": t, "ngay_du_lieu": dd, "huy_luc": h}
                   for b, s, f, d, g, l, n, t, dd, h in conn.execute(
                       """SELECT batch_id, spec_name, source_file, archived_to, digest, loaded_at,
                                 row_count, total_amount, data_date, undone_at
                          FROM meta.ingest_batch WHERE spec_name = ANY(%s)
                          ORDER BY loaded_at DESC, batch_id DESC LIMIT 30""",
                       ([n["spec"] for n in nguon],)).fetchall()]
    conn.rollback()
    k = rows[0]
    return {"ten": ten, "schema": m.group(1), "ngan": m.group(2), "loai": "bang" if k[0] == "r" else "view",
            "so_dong": k[1] if k[0] == "r" else None, "mo_ta": " ".join((k[2] or "").split()) or None,
            "cot": cot, "khoa_chinh": [c["ten"] for c in cot if c["khoa_chinh"]],
            "nguon": [{"spec": n["spec"], "ja": n["ja"]} for n in nguon],
            "cot_ngay": _cot_ngay(cot), "co_lo": any(c["ten"] == "batch_id" for c in cot),
            "lan_nap": lan_nap}


def _cot_ngay(cot: list[dict]) -> str | None:
    """Cột ngày cho nút "Tháng gần nhất": cột date/timestamp đầu tiên của bảng."""
    for c in cot:
        if c["kieu"] in ("date", "timestamp with time zone", "timestamp without time zone"):
            return c["ten"]
    return None


def _cau(tt: dict, tim: str, chip: str):
    """(câu SELECT, tham số) — mọi tên đi qua sql.Identifier, lấy từ `thong_tin`
    (tức từ danh mục), không từ tham số của người gọi."""
    rel = sql.Identifier(tt["schema"], tt["ngan"])
    dk, ts = [sql.SQL("true")], []
    if tim.strip():
        # Tìm trên CẢ DÒNG (mọi cột thành chữ) — không cần biết cột nào là mã.
        dk.append(sql.SQL("t::text ILIKE %s"))
        ts.append("%" + re.sub(r"([\\%_])", r"\\\1", tim.strip()) + "%")
    nguon = rel
    if tt["loai"] == "view" and chip in ("thang", "lo"):
        nguon = sql.Identifier("t0")          # view: tính MỘT lần (bất biến CTE-trùng)
    if chip == "thang" and tt["cot_ngay"]:
        c = sql.Identifier(tt["cot_ngay"])
        dk.append(sql.SQL("t.{c} >= (SELECT date_trunc('month', max({c})) FROM {n})").format(c=c, n=nguon))
    elif chip == "lo" and tt["co_lo"]:
        dk.append(sql.SQL("t.batch_id = (SELECT max(batch_id) FROM {n})").format(n=nguon))
    thu_tu = [sql.Identifier(c) for c in tt["khoa_chinh"]] or [sql.SQL("1")]
    dau = (sql.SQL("WITH t0 AS MATERIALIZED (SELECT * FROM {r}) ").format(r=rel)
           if nguon != rel else sql.SQL(""))
    return dau, (nguon if nguon != rel else rel), sql.SQL(" AND ").join(dk), sql.SQL(", ").join(thu_tu), ts


def _gia(v):
    if isinstance(v, Decimal):
        return int(v) if v == v.to_integral_value() else float(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, (bytes, memoryview)):
        return "(nhị phân)"
    if isinstance(v, (dict, list)):
        import json
        return json.dumps(v, ensure_ascii=False, default=str)[:500]
    return v


def dong(conn, tt: dict, tim: str = "", chip: str = "tat_ca", trang: int = 1) -> dict:
    """Một trang 50 dòng + tổng số dòng khớp bộ lọc. Bảng: 2 lượt hỏi; view: 1."""
    chip = chip if chip in CHIP else "tat_ca"
    trang = max(1, trang)
    dau, nguon, dk, thu_tu, ts = _cau(tt, tim, chip)
    lim, off = sql.Literal(MOI_TRANG), sql.Literal((trang - 1) * MOI_TRANG)
    _chi_doc(conn)
    if tt["loai"] == "bang":
        # Bảng: trang theo khoá chính đi bằng chỉ mục, đếm riêng — `count(*) OVER ()`
        # buộc sắp xếp CẢ bảng (đo thật: fact_sales_line 291k dòng 6,1 s → dưới 1 s).
        # Hai câu = hai lượt hỏi (~50 ms mỗi lượt), vẫn rẻ hơn nhiều so với sắp cả bảng.
        q = sql.SQL("SELECT t.* FROM {n} t WHERE {dk} ORDER BY {o} LIMIT {l} OFFSET {x}").format(
            n=nguon, dk=dk, o=thu_tu, l=lim, x=off)
        d = sql.SQL("SELECT count(*) FROM {n} t WHERE {dk}").format(n=nguon, dk=dk)
        cur = conn.cursor()
        rows = cur.execute(q, ts).fetchall()
        tong = cur.execute(d, ts).fetchone()[0]
    else:
        # View: MỘT câu — hai câu là tính lại cả view hai lần.
        q = sql.SQL("{dau}SELECT t.*, count(*) OVER () FROM {n} t WHERE {dk} ORDER BY {o} LIMIT {l} OFFSET {x}").format(
            dau=dau, n=nguon, dk=dk, o=thu_tu, l=lim, x=off)
        kq = conn.execute(q, ts).fetchall()
        rows, tong = [r[:-1] for r in kq], (kq[0][-1] if kq else 0)
    conn.rollback()
    return {"dong": [[_gia(v) for v in r] for r in rows], "tong": tong,
            "trang": trang, "moi_trang": MOI_TRANG, "chip": chip}


def csv_van_ban(conn, tt: dict, tim: str = "", chip: str = "tat_ca") -> str:
    """CSV (có BOM, Excel mở thẳng) — tối đa TOI_DA_CSV dòng, cùng bộ lọc với màn."""
    chip = chip if chip in CHIP else "tat_ca"
    dau, nguon, dk, thu_tu, ts = _cau(tt, tim, chip)
    q = sql.SQL("{dau}SELECT t.* FROM {n} t WHERE {dk} ORDER BY {o} LIMIT {l}").format(
        dau=dau, n=nguon, dk=dk, o=thu_tu, l=sql.Literal(TOI_DA_CSV))
    _chi_doc(conn)
    rows = conn.execute(q, ts).fetchall()
    conn.rollback()
    out = io.StringIO()
    w = csv.writer(out, lineterminator="\r\n")
    w.writerow([c["ten"] for c in tt["cot"]])
    for r in rows:
        w.writerow(["" if v is None else _gia(v) for v in r])
    return "﻿" + out.getvalue()
