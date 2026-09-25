"""Sinh ảnh chụp "cột OBC nào đang được dùng" cho màn Kho dữ liệu → Dữ liệu đi đâu.

Mục đích (chủ DN 2026-09-24): quyết định cột nào BỎ ĐƯỢC khỏi bản xuất OBC lần
sau. Đặc tả: docs/superpowers/specs/2026-09-24-kho-du-lieu-theo-thiet-ke-design.md §A.

    python scripts/sinh_cot_dung.py              # ghi kome/web/cot_dung_sinh.json
    python scripts/sinh_cot_dung.py --doc-tieu-de  # đọc lại config/obc_tieu_de.json

Chạy lại MỖI KHI sửa migration, `config/files.yml` hay mã trong `kome/` —
`tests/test_cot_dung.py::test_anh_chup_cot_dung_khong_cu` đỏ nếu quên.

Cần `DATABASE_URL_TEST` (CSDL thử nghiệm đã migrate — chỉ ĐỌC danh mục, không
đọc dòng dữ liệu nào). `--doc-tieu-de` chỉ đọc DÒNG TIÊU ĐỀ của file mới nhất
trong `raw_archive*/` — không đọc một dòng dữ liệu nào.

LUẬT: sai nguy hiểm duy nhất là báo "chưa dùng" cho một cột đang dùng. Mọi phép
dò ở đây nghiêng về "đang dùng": trùng tên là tính dùng, đọc cả view là tính
dùng mọi cột của view đó.
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
import tokenize
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))

RA = GOC / "kome" / "web" / "cot_dung_sinh.json"
TIEU_DE = GOC / "config" / "obc_tieu_de.json"
KHO_LUU = ("raw_archive_that", "raw_archive")

# Mã NẠP: cột được nhắc ở đây là cột bộ nạp cần (khoá, cột đối chiếu…). KHÔNG
# gồm kome/loaders/: loader liệt kê MỌI cột nó chép, nhắc tên không có nghĩa
# là cần — cột nó chép sang core được xét ở bước "màn nào đọc cột core đó".
MA_NAP = ["kome/pipeline.py", "kome/reader.py", "kome/gates.py", "kome/so_cai.py",
          "kome/archive.py"]

# Mô-đun không ĐỌC dữ liệu (cấu hình, tài liệu, loader) — có nhắc tên bảng
# nhưng không hiện số nào lên màn.
BO_QUA = {"kome/config.py": "cấu hình", "kome/nguon_dung.py": "tên bảng để ẩn khỏi giao diện (không đọc cột)", "kome/tai_lieu.py": "tài liệu sống (chỉ in tên bảng)"}

# Màn hình: (tên, đường dẫn).
MAN_HINH = {
    "tong_quan": ("Tổng quan", "/"), "bao_cao": ("Báo cáo", "/bao-cao"),
    "du_bao": ("Dự báo", "/du-bao"), "khach": ("Khách hàng", "/khach-hang"),
    "ho_so": ("Hồ sơ khách", "/khach-hang/{mã}"), "ban_do": ("Bản đồ", "/ban-do"),
    "lien_he": ("Cần liên hệ", "/lien-he"), "san_pham": ("Sản phẩm", "/san-pham"),
    "kho_hang": ("Kho hàng", "/kho-hang"), "cong_no": ("Công nợ", "/cong-no"),
    "ngan_sach": ("Ngân sách", "/ngan-sach"), "nhat_ky": ("Nhật ký", "/nhat-ky"),
    "cai_dat": ("Cài đặt", "/cai-dat"), "kho_du_lieu": ("Kho dữ liệu", "/kho-du-lieu"),
    "chung": ("Mã web chung (nhiều màn)", ""),
}

# Mô-đun → màn nó phục vụ. Test canh: mọi mô-đun nhắc `mart.`/`core.` phải có
# ở đây, trong MA_NAP hoặc BO_QUA (hoặc là loader).
MAN = {
    "kome/ban_do.py": ["ban_do"], "kome/ban_khoang.py": ["tong_quan", "bao_cao", "khach", "san_pham"],
    "kome/bao_cao.py": ["bao_cao", "tong_quan"], "kome/cong_no.py": ["cong_no", "ho_so", "tong_quan"],
    "kome/coverage.py": ["kho_du_lieu"], "kome/du_bao.py": ["du_bao"],
    "kome/ho_so_khach.py": ["ho_so"], "kome/khach_hang.py": ["khach", "ho_so", "tong_quan", "ban_do"],
    "kome/khach_thang.py": ["tong_quan", "lien_he", "khach"], "kome/khoang_xem.py": ["chung"],
    "kome/khoi_tong_quan.py": ["tong_quan"], "kome/lien_he.py": ["lien_he"],
    "kome/ngan_sach.py": ["ngan_sach"], "kome/nhat_ky.py": ["nhat_ky"],
    "kome/nhat_ky_nap.py": ["kho_du_lieu"], "kome/san_pham.py": ["san_pham", "kho_hang", "tong_quan"],
    "kome/tong_quan.py": ["tong_quan"], "kome/tuoi_du_lieu.py": ["tong_quan", "kho_du_lieu"],
    "kome/ve_phan_tich.py": ["bao_cao"], "kome/web/api.py": ["chung"], "kome/web/app.py": ["chung"],
    "kome/web/bo_cuc.py": ["tong_quan"], "kome/web/nguoi_dung.py": ["cai_dat"],
}

# Cột hệ thống KHÔNG nằm cùng tên trong core_table của file — loader ghi nó
# chỗ khác. Test canh: cột nào không có cùng tên trong core_table mà thiếu ở
# đây thì đỏ (sửa loader xong phải khai lại). Giá trị None = đọc rồi BỎ, không
# lưu vào đâu (bỏ khỏi bản xuất chỉ cần sửa files.yml, không mất lịch sử nào).
LUU_RIENG: dict[str, dict[str, str | None]] = {
    "zaiko": {"warehouse_name": "core.dim_warehouse.warehouse_name", "pack_name": None},
    "tanka": {**{f"price_ex_{i:02d}": "core.fact_price_list.price_ex_tax" for i in range(1, 11)},
              **{f"price_in_{i:02d}": "core.fact_price_list.price_in_tax" for i in range(1, 11)}},
    # row_title: dòng 【合計】/【繰越】 — kome/so_cai.py đọc để tách dòng tổng, không lưu.
    "seikyu_motocho": {"row_title": None},
}

_THAM_CHIEU = re.compile(r"\b(core|mart)\.([a-z_][a-z0-9_]*)")
_SAO = re.compile(r"(?:\bSELECT|,)\s*(?:[a-z_]\w*\.)?\*", re.I)


# ---------------------------------------------------------------------------
# Quét mã Python
# ---------------------------------------------------------------------------

# Gán cấp mô-đun mà mã nạp chỉ dùng để LIỆT KÊ cột cho loader chép (không
# phải cột bộ nạp cần) — bỏ khỏi phép dò của MA_NAP.
GAN_LIET_KE = {"LOADERS", "UNDO_TABLES", "UNDO_SCD2"}

# Mã nạp chỉ phục vụ MỘT số loại file: nhắc tên cột ở đó chỉ có nghĩa cho các
# loại đó (kome/so_cai.py đọc sổ cái — không liên quan cột cùng tên của file bán hàng).
MA_NAP_CHI_CHO = {"kome/so_cai.py": lambda sp: sp.so_cai_truc is not None}


def bo_gan(van: str, ten: set[str]) -> str:
    """Xoá (thành dòng trống) các phép gán cấp mô-đun `ten = …`."""
    import ast
    dong = van.splitlines(keepends=True)
    for n in ast.parse(van).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ten for t in n.targets):
            for i in range(n.lineno - 1, n.end_lineno):
                dong[i] = "\n"
    return "".join(dong)


def tu_trong_ma(van: str) -> tuple[set[str], list[str]]:
    """(từ, chuỗi): từ = mọi tên (NAME) + mọi từ trong chuỗi KHÔNG phải docstring
    và KHÔNG phải chú thích. Chú thích nhắc tên cột không làm cột đó "được dùng"."""
    # Mỗi phần tử của `chuoi` là MỘT cụm chuỗi liền nhau (chuỗi ghép kề nhau,
    # hay trọn một f-string kể cả phần {…}) — một câu SQL viết tách dòng vẫn
    # là một cụm, nên "câu này có `*` không" xét được theo từng câu.
    tu: set[str] = set()
    chuoi: list[str] = []
    cum: list[str] | None = None
    sau_f = 0                                  # độ sâu f-string
    F_BAT = {getattr(tokenize, n) for n in ("FSTRING_START", "TSTRING_START") if hasattr(tokenize, n)}
    F_TAT = {getattr(tokenize, n) for n in ("FSTRING_END", "TSTRING_END") if hasattr(tokenize, n)}
    F_GIUA = {getattr(tokenize, n) for n in ("FSTRING_MIDDLE", "TSTRING_MIDDLE") if hasattr(tokenize, n)}
    truoc = tokenize.NEWLINE
    for t in tokenize.generate_tokens(io.StringIO(van).readline):
        if t.type == tokenize.NAME:
            tu.add(t.string)
        la_chuoi = t.type == tokenize.STRING or t.type in F_BAT | F_TAT | F_GIUA
        if t.type in F_BAT:
            sau_f += 1
        elif t.type in F_TAT:
            sau_f -= 1
        if la_chuoi or sau_f:
            docstring = (cum is None and t.type == tokenize.STRING and truoc in (
                tokenize.NEWLINE, tokenize.INDENT, tokenize.DEDENT, tokenize.NL))
            if not docstring:
                if cum is None:
                    cum = []
                if t.type == tokenize.STRING or t.type in F_GIUA:
                    cum.append(t.string)
                    tu.update(re.findall(r"[A-Za-z_]\w*|[^\x00-\x7f]+", t.string))
        elif t.type not in (tokenize.NL, tokenize.COMMENT) and cum is not None:
            chuoi.append(" ".join(cum))
            cum = None
        if t.type not in (tokenize.COMMENT, tokenize.NL):
            truoc = t.type
    if cum:
        chuoi.append(" ".join(cum))
    return tu, chuoi


def sao_cua(cau: str) -> set[str] | None:
    """Những quan hệ `core`/`mart` mà câu SQL này đọc bằng `*`. None = có `*` mà
    không lần được (tính mọi quan hệ của mô-đun).

    - `x.*`: x là CTE `x AS (SELECT … FROM rel …)` → `*` của CTE đó (nếu CTE
      chọn `*` thì là rel, nếu CTE chọn cột tường minh thì các cột đó đã nằm
      trong phép dò chữ); x là bí danh `FROM rel x` → rel.
    - `SELECT *` trần: mọi quan hệ nhắc trong câu (không tách được mệnh đề FROM
      của từng tầng câu con)."""
    ra: set[str] = set()
    for m in _SAO.finditer(cau):
        bd = re.search(r"([a-z_]\w*)\.\*$", m.group(0), re.I)
        if not bd:
            qh = {f"{s}.{t}" for s, t in _THAM_CHIEU.findall(cau)}
            if not qh:
                return None
            ra |= qh
            continue
        x = bd.group(1)
        cte = re.search(rf"\b{x}\s+AS\s+(?:NOT\s+)?(?:MATERIALIZED\s+)?\(\s*SELECT\s+(.*?)\s+FROM\s+"
                        rf"(?:(core|mart)\.(\w+))?", cau, re.I | re.S)
        if cte:
            if re.fullmatch(r"(?:[a-z_]\w*\.)?\*", cte.group(1).strip(), re.I):
                if not cte.group(2):
                    return None
                ra.add(f"{cte.group(2)}.{cte.group(3)}")
            continue
        bi = re.search(rf"\b(core|mart)\.(\w+)(?:\s*\([^)]*\))?\s+(?:AS\s+)?{x}\b", cau, re.I)
        if bi:
            ra.add(f"{bi.group(1)}.{bi.group(2)}")
            continue
        return None
    return ra


_TU = re.compile(r"[A-Za-z_]\w*|[^\x00-\x7f]+")


def quet_ma(goc: Path) -> dict[str, dict]:
    """Mỗi mô-đun trong kome/: các CÂU SQL (cụm chuỗi có nhắc quan hệ core/mart)
    kèm từ của câu đó và quan hệ nào nó đọc bằng `*`; `manh` = từ của mọi cụm
    chuỗi KHÔNG nhắc quan hệ nào (danh sách cột ghép vào câu qua f-string, mệnh
    đề WHERE ghép thêm…) — cộng vào mọi câu của mô-đun, nghiêng về "đang dùng"."""
    ra = {}
    for f in sorted((goc / "kome").rglob("*.py")):
        duong = f.relative_to(goc).as_posix()
        van = f.read_text(encoding="utf-8")
        if duong in MA_NAP:
            van = bo_gan(van, GAN_LIET_KE)
        tu, chuoi = tu_trong_ma(van)
        cau, manh = [], set()
        for c in chuoi:
            qh = sorted({f"{a}.{b}" for a, b in _THAM_CHIEU.findall(c)})
            if not qh:
                manh |= set(_TU.findall(c))
                continue
            sao = sao_cua(c)
            cau.append({"qh": qh, "tu": set(_TU.findall(c)),
                        "sao": set(qh) if sao is None else sao})
        ra[duong] = {"qh": sorted({q for c in cau for q in c["qh"]}), "tu": tu,
                     "cau": cau, "manh": manh}
    return ra


# ---------------------------------------------------------------------------
# Danh mục Postgres
# ---------------------------------------------------------------------------

def doc_danh_muc(conn) -> dict:
    cot: dict[str, list[str]] = {}
    for qh, ten in conn.execute(
        """SELECT n.nspname || '.' || c.relname, a.attname
           FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           JOIN pg_attribute a ON a.attrelid = c.oid AND a.attnum > 0 AND NOT a.attisdropped
           WHERE n.nspname IN ('core', 'mart') AND c.relkind IN ('r', 'v', 'm')
           ORDER BY 1, a.attnum"""):
        cot.setdefault(qh, []).append(ten)
    loai = dict(conn.execute(
        """SELECT n.nspname || '.' || c.relname, c.relkind::text FROM pg_class c
           JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname IN ('core', 'mart') AND c.relkind IN ('r', 'v', 'm')""").fetchall())
    # View → (quan hệ, cột) nó đọc. refobjsubid = 0 là phụ thuộc cả quan hệ.
    dep: dict[str, set[tuple[str, str | None]]] = {}
    for v, r, a in conn.execute(
        """SELECT vn.nspname || '.' || v.relname, rn.nspname || '.' || r.relname, a.attname
           FROM pg_rewrite w
           JOIN pg_class v ON v.oid = w.ev_class JOIN pg_namespace vn ON vn.oid = v.relnamespace
           JOIN pg_depend d ON d.classid = 'pg_rewrite'::regclass AND d.objid = w.oid
                           AND d.refclassid = 'pg_class'::regclass
           JOIN pg_class r ON r.oid = d.refobjid JOIN pg_namespace rn ON rn.oid = r.relnamespace
           LEFT JOIN pg_attribute a ON a.attrelid = r.oid AND a.attnum = d.refobjsubid
           WHERE vn.nspname = 'mart' AND rn.nspname IN ('core', 'mart') AND r.oid <> v.oid"""):
        dep.setdefault(v, set()).add((r, a))
    # View → hàm mart nó gọi.
    for v, p in conn.execute(
        """SELECT vn.nspname || '.' || v.relname, pn.nspname || '.' || p.proname
           FROM pg_rewrite w
           JOIN pg_class v ON v.oid = w.ev_class JOIN pg_namespace vn ON vn.oid = v.relnamespace
           JOIN pg_depend d ON d.classid = 'pg_rewrite'::regclass AND d.objid = w.oid
                           AND d.refclassid = 'pg_proc'::regclass
           JOIN pg_proc p ON p.oid = d.refobjid JOIN pg_namespace pn ON pn.oid = p.pronamespace
           WHERE vn.nspname = 'mart' AND pn.nspname = 'mart'"""):
        dep.setdefault(v, set()).add((p, None))
    for ten, cot_ham in conn.execute(
        """SELECT n.nspname || '.' || p.proname,
                  CASE WHEN t.typrelid <> 0
                       THEN (SELECT array_agg(a.attname ORDER BY a.attnum) FROM pg_attribute a
                             WHERE a.attrelid = t.typrelid AND a.attnum > 0 AND NOT a.attisdropped)
                       ELSE (SELECT array_agg(x.ten ORDER BY x.i) FROM unnest(p.proargnames, p.proargmodes)
                             WITH ORDINALITY AS x(ten, mode, i) WHERE x.mode IN ('t', 'o')) END
           FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
           JOIN pg_type t ON t.oid = p.prorettype
           WHERE n.nspname = 'mart'"""):
        if cot_ham:
            cot.setdefault(ten, list(cot_ham))
    ham = dict(conn.execute(
        """SELECT n.nspname || '.' || p.proname, string_agg(p.prosrc, E'\n')
           FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
           WHERE n.nspname = 'mart' GROUP BY 1""").fetchall())
    dinh_nghia = dict(conn.execute(
        """SELECT n.nspname || '.' || c.relname, pg_get_viewdef(c.oid)
           FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname = 'mart' AND c.relkind = 'v'""").fetchall())
    khoa_ngoai = [
        {"tu": f"{a}.{ca}", "den": f"{b}.{cb}"} for a, ca, b, cb in conn.execute(
            """SELECT tn.nspname || '.' || t.relname, ta.attname, fn.nspname || '.' || f.relname, fa.attname
               FROM pg_constraint k
               JOIN pg_class t ON t.oid = k.conrelid JOIN pg_namespace tn ON tn.oid = t.relnamespace
               JOIN pg_class f ON f.oid = k.confrelid JOIN pg_namespace fn ON fn.oid = f.relnamespace
               CROSS JOIN LATERAL unnest(k.conkey, k.confkey) AS u(ck, fk)
               JOIN pg_attribute ta ON ta.attrelid = t.oid AND ta.attnum = u.ck
               JOIN pg_attribute fa ON fa.attrelid = f.oid AND fa.attnum = u.fk
               WHERE k.contype = 'f' AND tn.nspname = 'core' AND fn.nspname = 'core'
               ORDER BY 1, 2""")]
    return {"cot": cot, "loai": loai, "dep": {k: sorted(v, key=str) for k, v in dep.items()},
            "ham": ham, "dinh_nghia": dinh_nghia, "khoa_ngoai": khoa_ngoai}


def _tach_cap_0(van: str, sep: str = ",") -> list[str]:
    """Tách theo `sep` ở cấp ngoặc 0 (bỏ qua trong chuỗi '…')."""
    ra, sau, cap, trong_chuoi = [], 0, 0, False
    for i, ch in enumerate(van):
        if ch == "'":
            trong_chuoi = not trong_chuoi
        elif not trong_chuoi:
            if ch == "(":
                cap += 1
            elif ch == ")":
                cap -= 1
            elif ch == sep and cap == 0:
                ra.append(van[sau:i])
                sau = i + 1
    ra.append(van[sau:])
    return ra


def _vi_tri_cap_0(van: str, tu_khoa: str) -> int:
    """Vị trí đầu tiên của từ khoá (đứng riêng) ở cấp ngoặc 0, -1 nếu không có."""
    cap, trong_chuoi = 0, False
    for i, ch in enumerate(van):
        if ch == "'":
            trong_chuoi = not trong_chuoi
        elif not trong_chuoi:
            if ch == "(":
                cap += 1
            elif ch == ")":
                cap -= 1
            elif cap == 0 and (i == 0 or not (van[i - 1].isalnum() or van[i - 1] == "_")) \
                    and re.match(rf"{tu_khoa}(?![A-Za-z0-9_])", van[i:i + len(tu_khoa) + 1], re.I):
                return i
    return -1


def tach_view(dinh_nghia: str) -> tuple[dict[str, set[str]], set[str]] | None:
    """Định nghĩa view → ({cột ra: từ trong biểu thức của nó}, từ của phần còn lại
    — FROM / JOIN / WHERE / GROUP BY, thứ mà cột ra nào cũng kéo theo).
    None = không tách được (WITH, UNION…) → cả view được tính là đọc."""
    van = dinh_nghia.strip().rstrip(";")
    if not re.match(r"SELECT(?![A-Za-z0-9_])", van, re.I) or _vi_tri_cap_0(van, "UNION") >= 0 \
            or _vi_tri_cap_0(van, "INTERSECT") >= 0 or _vi_tri_cap_0(van, "EXCEPT") >= 0:
        return None
    than = van[6:]
    tu_con_lai: set[str] = set()
    m = re.match(r"\s*DISTINCT\s+ON\s*\(", than, re.I)
    if m:                                  # DISTINCT ON (…) thuộc "phần còn lại"
        cap, j = 1, m.end()
        while cap and j < len(than):
            cap += {"(": 1, ")": -1}.get(than[j], 0)
            j += 1
        tu_con_lai |= set(re.findall(r"[a-z_]\w*", than[:j]))
        than = than[j:]
    i = _vi_tri_cap_0(than, "FROM")
    if i < 0:
        return None
    tu_con_lai |= set(re.findall(r"[a-z_]\w*", than[i:]))
    cot: dict[str, set[str]] = {}
    for muc in _tach_cap_0(than[:i]):
        muc = muc.strip()
        m = re.search(r"\s+AS\s+\"?([a-z_]\w*)\"?\s*$", muc, re.I)
        if m:
            ten, bt = m.group(1), muc[:m.start()]
        else:
            ten, bt = muc.split(".")[-1].strip('"'), muc
        cot.setdefault(ten, set()).update(re.findall(r"[a-z_]\w*", bt))
    return cot, tu_con_lai


class Do:
    """Dò (quan hệ, tập cột được đọc) → {cột core bị dùng: các view mart nằm trên đường đi}.

    Lần theo TỪNG CỘT qua view: cột ra của view kéo theo những cột vào có tên
    xuất hiện trong biểu thức của nó, cộng mọi cột vào nhắc ở FROM / WHERE /
    GROUP BY. Trùng tên giữa hai bảng thì tính cả hai (nghiêng về "đang dùng").
    """

    def __init__(self, dm: dict):
        self.dm = dm
        self.nho: dict = {}
        self.tach = {v: tach_view(d) for v, d in dm["dinh_nghia"].items()}
        self.dep = {k: list(v) for k, v in dm["dep"].items()}
        # Hàm mart (LANGUAGE sql): pg_depend không ghi thân hàm → dựng "phụ thuộc"
        # từ chữ trong prosrc: mọi cột của mọi quan hệ nó nhắc (lọc theo cột được
        # đọc ở doc()), và thân hàm là một câu SELECT thì tách như view.
        for ten, van in dm["ham"].items():
            if ten in dm["loai"]:
                continue
            dep = []
            for s_, t in sorted(set(_THAM_CHIEU.findall(van))):
                r = f"{s_}.{t}"
                if r == ten:
                    continue
                if r in dm["cot"]:
                    dep += [(r, a) for a in dm["cot"][r]]
                else:
                    dep.append((r, None))
            self.dep[ten] = dep
            self.tach[ten] = tach_view(re.sub(r"^\s*\(|\)\s*$", "", van.strip()))

    def _gop(self, ra: dict, them: dict, view: str | None = None) -> None:
        for k, vs in them.items():
            ra.setdefault(k, set()).update(vs)
            if view:
                ra[k].add(view)

    def doc(self, qh: str, cot: frozenset | None) -> dict[tuple[str, str], set[str]]:
        """cot None = đọc mọi cột."""
        khoa = (qh, cot)
        if khoa in self.nho:
            return self.nho[khoa]
        self.nho[khoa] = {}            # chặn vòng
        ra: dict[tuple[str, str], set[str]] = {}
        if qh.startswith("core."):
            ra = {(qh, c): set() for c in (self.dm["cot"].get(qh, []) if cot is None else cot)
                  if c in self.dm["cot"].get(qh, [])}
        elif qh in self.dep:
            tach = self.tach.get(qh)
            van_ham = self.dm["ham"].get(qh) if qh not in self.dm["loai"] else None
            if cot is None and van_ham is not None:
                # "Đọc mọi cột" của một HÀM = mọi cột nó trả; hàm trả một giá trị
                # (vd. mart.moc_lui()) = những cột có tên trong thân hàm.
                if qh in self.dm["cot"]:
                    cot = frozenset(self.dm["cot"][qh])
                else:
                    tach = None
                    cot = frozenset()
            if cot is None:
                tu = None                   # đọc cả view / hàm
            elif tach is None:
                # Không tách được (WITH, UNION…): view → mọi cột pg_depend ghi;
                # hàm → mọi cột có tên trong thân hàm (có `*` thì mọi cột).
                van = self.dm["ham"].get(qh)
                tu = None if van is None or _SAO.search(van) else set(re.findall(r"[a-z_]\w*", van))
            else:
                bt, tu = tach
                tu = set(tu)
                for c in cot:
                    # Cột không có trong danh sách SELECT tường minh (vd. qua `*`
                    # trong thân hàm) → cột cùng tên ở quan hệ nguồn.
                    tu |= bt.get(c, {c})
            for r, a in self.dep[qh]:
                if a is None:
                    # Phụ thuộc cả quan hệ (hàng nguyên, hay một hàm mart).
                    if tu is None or r.split(".")[-1] in tu or r not in self.dm["cot"]:
                        self._gop(ra, self.doc(r, None), qh)
                elif tu is None or a in tu:
                    self._gop(ra, self.doc(r, frozenset([a])), qh)
        self.nho[khoa] = ra
        return ra


# ---------------------------------------------------------------------------
# Tiêu đề file thật
# ---------------------------------------------------------------------------

def doc_tieu_de(goc: Path = GOC) -> dict:
    """Dòng tiêu đề của file MỚI NHẤT mỗi loại trong raw_archive*/ — chỉ dòng tiêu đề."""
    from python_calamine import CalamineWorkbook
    from kome.config import SPECS
    ra = {}
    for ten, sp in SPECS.items():
        ung = []
        for kho in KHO_LUU:
            ung += list((goc / kho / ten).rglob("*.xlsx")) if (goc / kho / ten).exists() else []
        if not ung:
            continue
        f = max(ung, key=lambda p: (p.name.split("__")[0], p.stat().st_mtime))
        wb = CalamineWorkbook.from_path(str(f))
        tam = wb.get_sheet_by_name(sp.sheet) if sp.sheet in wb.sheet_names else wb.get_sheet_by_index(0)
        dong = tam.to_python(nrows=sp.header_row)
        tieu = [str(x).strip() for x in dong[sp.header_row - 1] if str(x).strip()]
        ra[ten] = {"file": f.name.split("__")[0] + f.suffix, "cot": tieu}
    return ra


# ---------------------------------------------------------------------------
# Phân loại
# ---------------------------------------------------------------------------

def phan_loai(specs, dm: dict, ma: dict, tieu_de: dict) -> dict:
    do = Do(dm)
    tu_nap = {f: ma[f]["tu"] for f in MA_NAP if f in ma}

    # (1) Mô-đun màn hình → cột core bị dùng + chuỗi view.
    dung: dict[tuple[str, str], dict] = {}     # (bảng core, cột) -> {man, view, ma}
    view_man: dict[str, set[str]] = {}

    def them(k, man, view=None, mo_dun=None):
        d = dung.setdefault(k, {"man": set(), "view": set(), "ma": set()})
        d["man"] |= set(man)
        if view:
            d["view"].add(view)
        if mo_dun:
            d["ma"].add(mo_dun)

    for f, m in ma.items():
        if f not in MAN:
            continue
        man = MAN[f]
        for cau in m["cau"]:
            tu = cau["tu"] | m["manh"]
            for qh in cau["qh"]:
                cot_qh = dm["cot"].get(qh)
                if cot_qh is None and qh not in dm["ham"]:
                    continue                # tên lạ (bảng app/meta, hay chữ trong chú thích SQL)
                # Câu đọc những cột có tên xuất hiện trong chính câu đó (cộng các
                # mảnh ghép của mô-đun); đọc bằng `*` thì mọi cột.
                chon = None if (qh in cau["sao"] or cot_qh is None) else frozenset(c for c in cot_qh if c in tu)
                for k, views in do.doc(qh, chon).items():
                    them(k, man, mo_dun=f)
                    dung[k]["view"] |= views
                    for v in views:
                        view_man.setdefault(v, set()).update(man)

    # (2) Từng file OBC.
    files = []
    for ten, sp in specs.items():
        can_nap = {**{k: "khoá của file" for k in sp.keys}}
        if sp.total_column:
            can_nap.setdefault(sp.total_column, "cột tổng tiền — cổng 4/5 đối chiếu")
        if sp.product_check:
            for c in [sp.product_check["result"], *sp.product_check["factors"]]:
                can_nap.setdefault(c, "cột kiểm số lượng × đơn giá = tiền (cổng 3)")
        for c in sp.required_date_columns:
            can_nap.setdefault(c, "ngày bắt buộc đọc được (cổng 3)")
        cot = []
        for ja, he in sp.columns.items():
            if he in LUU_RIENG.get(ten, {}):
                dich = LUU_RIENG[ten][he]
            elif sp.core_table and he in dm["cot"].get(sp.core_table, []):
                dich = f"{sp.core_table}.{he}"
            else:
                dich = "?"          # test canh: không được xảy ra
            nhac = sorted(f for f, tu in tu_nap.items() if (he in tu or ja in tu)
                          and MA_NAP_CHI_CHO.get(f, lambda _: True)(sp))
            if he in can_nap:
                loai, ly_do = "nap", can_nap[he]
            elif nhac:
                loai, ly_do = "nap", "mã nạp đọc cột này (" + ", ".join(nhac) + ")"
            else:
                loai, ly_do = "luu", ""
            d = {"man": set(), "view": set(), "ma": set()}
            if dich and dich != "?":
                b, c = dich.rsplit(".", 1)
                d = dung.get((b, c), d)
            if loai == "luu" and d["man"]:
                loai = "man"
            if loai == "luu":
                ly_do = ("đọc rồi bỏ — không lưu vào bảng nào" if dich is None
                         else "chỉ lưu trong kho, chưa màn nào hiện")
            elif loai == "man":
                qua = sorted(d["view"]) or sorted(d["ma"])
                ly_do = ("màn hình đọc qua " + ", ".join(qua[:3])
                         + (f" và {len(qua) - 3} chỉ số khác" if len(qua) > 3 else ""))
            cot.append({"ja": ja, "he": he, "core": dich, "loai": loai, "ly_do": ly_do,
                        "view": sorted(d["view"]), "man": sorted(d["man"]), "ma": sorted(d["ma"])})
        td = tieu_de.get(ten)
        if td:
            khai = set(sp.columns)
            for ja in td["cot"]:
                if ja not in khai:
                    cot.append({"ja": ja, "he": None, "core": None, "loai": "khong_nap",
                                "ly_do": "có trong file nhưng kho không nạp", "view": [], "man": [], "ma": []})
        files.append({"ten": ten, "ja": sp.display_name, "core_table": sp.core_table,
                      "mau": td["file"] if td else None, "cot": cot})

    # (3) Sơ đồ khoá.
    bang = sorted({sp.core_table for sp in specs.values() if sp.core_table}
                  | {k["tu"].rsplit(".", 1)[0] for k in dm["khoa_ngoai"]}
                  | {k["den"].rsplit(".", 1)[0] for k in dm["khoa_ngoai"]})
    noi = [dict(k, nguon="khoá ngoại CSDL") for k in dm["khoa_ngoai"] if k["den"] != k["tu"]]
    da = {(n["tu"], n["den"]) for n in noi}
    for sp in specs.values():
        for c, dich in sp.references.items():
            dsp = specs[dich]
            k = (f"{sp.core_table}.{c}", f"{dsp.core_table}.{dsp.keys[0]}")
            if k not in da and k[0].rsplit(".", 1)[0] != k[1].rsplit(".", 1)[0]:
                da.add(k)
                noi.append({"tu": k[0], "den": k[1], "nguon": "files.yml (nghiệp vụ)"})
    khoa_chinh = {sp.core_table: list(sp.keys) for sp in specs.values() if sp.core_table}

    return {
        "files": files,
        "man": {k: {"ten": v[0], "duong": v[1]} for k, v in MAN_HINH.items()},
        "view_man": {v: sorted(m) for v, m in sorted(view_man.items())},
        "khoa": {"bang": [{"ten": b, "cot": dm["cot"].get(b, []), "khoa": khoa_chinh.get(b, [])}
                          for b in bang],
                 "noi": sorted(noi, key=lambda n: (n["tu"], n["den"]))},
    }


def sinh(conn, goc: Path = GOC) -> dict:
    from kome.config import SPECS
    tieu_de = json.loads(TIEU_DE.read_text(encoding="utf-8")) if TIEU_DE.exists() else {}
    return phan_loai(SPECS, doc_danh_muc(conn), quet_ma(goc), tieu_de)


def van_ban(anh: dict) -> str:
    return json.dumps(anh, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def main() -> None:
    if "--doc-tieu-de" in sys.argv:
        TIEU_DE.write_text(van_ban(doc_tieu_de()), encoding="utf-8", newline="\n")
        print(f"OK: {TIEU_DE.relative_to(GOC).as_posix()}")
        return
    import psycopg
    from kome.env import nap_env
    nap_env(bat_buoc=False)
    with psycopg.connect(os.environ["DATABASE_URL_TEST"], prepare_threshold=None) as conn:
        anh = sinh(conn)
    RA.write_text(van_ban(anh), encoding="utf-8", newline="\n")
    print(f"OK: {RA.relative_to(GOC).as_posix()}")


if __name__ == "__main__":
    sys.exit(main())
