"""Tài liệu sống của màn Kho dữ liệu (đợt 2b) — hàm thuần, 0 truy vấn CSDL.

Luật gốc (lộ trình §7): tài liệu sống phải SINH RA, không chép tay. Mọi tên
cột, tên khoá, ngưỡng, tên bảng hiện trên trang đến từ một nguồn máy đọc được:

- LÚC CHẠY: `config/files.yml` (qua `kome.config.SPECS`) và `kome.coverage`.
- LÚC SINH: migration, CLAUDE.md, `kome/gates.py`, đặc tả lộ trình — bốn thứ
  không có mặt trên Vercel (`.vercelignore` loại `docs/` và `db/`; `gates.py`
  thì nhập pandas). `scripts/sinh_tai_lieu.py` đọc chúng và ghi ảnh chụp
  `kome/web/tai_lieu_sinh.json`; test `test_anh_chup_tai_lieu_khong_cu` canh
  ảnh chụp không cũ so với nguồn.

KHÔNG nhập pandas / kome.pipeline / kome.gates ở đây: trang này chạy cả ở bản
Vercel, nơi `requirements.txt` cố ý không có pandas.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from markupsafe import Markup, escape

from kome import coverage
from kome.config import FileSpec

ANH_CHUP = Path(__file__).resolve().parent / "web" / "tai_lieu_sinh.json"

# File mặc định của trang Cột nối — file chở ¥1,5 tỷ/năm, nối với nhiều file
# nhất, nên là chỗ đáng xem đầu tiên.
FILE_MAC_DINH = "uriage"

# `meisai` là nguồn bán hàng DỰ PHÒNG (migration 017), không có cột riêng ở
# bảng phủ (`coverage.COT`) vì nó đổ vào cùng bảng với `uriage`.
_MO_TA_NGOAI_COT = {"meisai": "bán hàng (nguồn dự phòng của 売上伝票データ)"}

# Bốn tầng — ĐÚNG bốn tầng của gói thiết kế (Kho dữ liệu.dc.html: TANG):
# OBC → raw → core → mart. (Schema `app` không phải một tầng của luồng OBC —
# nó là "sự thật về hoạt động", nằm ở khối "Ai là sự thật về cái gì".)
# Phần văn xuôi DUY NHẤT viết trong code: tên, một câu mô tả và dòng chân của
# mỗi tầng. Danh sách của từng tầng thì SINH (file từ files.yml, bảng/view từ
# migration).
TANG = [
    ("OBC", "Hệ nguồn", "do",
     "商奉行 / 蔵奉行 — nơi kế toán và kho thao tác hằng ngày. Web app không bao giờ ghi vào đây.",
     ""),
    ("raw", "Lưu nguyên văn", "canh",
     "Chép y hệt file OBC đã nạp, không sửa một ký tự, kèm mã băm để biết file có bị đổi không (raw_archive/).",
     "giữ vĩnh viễn"),
    ("core", "Đã làm sạch", "lam",
     "Mã giữ dạng TEXT, khách lưu theo hiệu lực từ–đến, mỗi dòng mang batch_id để hoàn tác cả lô. Chỉ kome_ingest ghi.",
     "nguồn tính toán duy nhất"),
    ("mart", "Định nghĩa chỉ số", "ok",
     "Chỉ có view — tính lại mỗi lần đọc, không lưu gì. Mọi chỉ số của màn hình định nghĩa ở đây và CHỈ ở đây.",
     "dẫn tới màn hình"),
]


def kieu_nap(core_table: str | None, chu_thich: dict) -> tuple[str, str]:
    """Kiểu nạp của một file — SUY từ bảng đích và câu COMMENT ON của chính
    bảng đó trong migration (ảnh chụp), không khai tay. (nhãn, lớp .vien.<lớp>)"""
    if core_table == "core.fact_sales_line":
        return ("theo ngày + đối soát tháng", "canh")
    if core_table == "core.fact_inventory_daily":
        return ("snapshot ngày", "lam")
    if "SCD2" in chu_thich.get(core_table or "", ""):
        return ("full + lịch sử", "ok")
    return ("full", "nhat")


def md_dong(s: str) -> Markup:
    """Markdown một dòng → HTML an toàn. ESCAPE TRƯỚC, rồi mới thay hai mẫu
    `**đậm**` và `` `mã` ``: thay trước rồi escape là mở cửa cho mọi thẻ HTML
    lọt trong nguồn; đánh `|safe` lên chuỗi thô cũng vậy."""
    t = str(escape(s))
    t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return Markup(t)


# ---- Lúc chạy: files.yml + coverage -------------------------------------

def _cot_phu(s: FileSpec):
    """Cột của bảng phủ ứng với spec — nối bằng TÊN OBC, không bằng khoá:
    khoá của coverage (`ban`, `ton`) khác tên spec (`uriage`, `zaiko`)."""
    return next((c for c in coverage.COT if c.ten_obc == s.display_name), None)


def _mo_ta(s: FileSpec) -> str:
    c = _cot_phu(s)
    return c.mo_ta if c else _MO_TA_NGOAI_COT.get(s.name, "")


def _tan_suat(s: FileSpec) -> str:
    c = _cot_phu(s)
    return "hằng ngày 13:30" if c and c.khoa in coverage.KHOA_NGAY else "vài lần mỗi năm"


def nguon_obc(specs: dict[str, FileSpec], anh: dict | None = None) -> list[dict]:
    ct = (anh or {}).get("chu_thich", {})
    ra = []
    for s in specs.values():
        nhan, mau = kieu_nap(s.core_table, ct)
        ra.append({"ten": s.name, "ja": s.display_name, "mo_ta": _mo_ta(s),
                   "mau": s.filename_pattern, "header_row": s.header_row,
                   "khoa": list(s.keys), "core_table": s.core_table,
                   "tan_suat": _tan_suat(s), "kieu": nhan, "kieu_mau": mau})
    return ra


def chua_nap() -> list:
    return list(coverage.THIEU_BO_NAP)


def nguong(specs: dict[str, FileSpec]) -> list[dict]:
    """Ngưỡng thật của từng file cho cổng 3–5, đọc thẳng từ spec."""
    return [{"ten": s.name, "ja": s.display_name, "min_rows": s.min_rows,
             "row_drop": s.warn_row_drop_ratio, "spike": s.warn_total_spike,
             "drop": s.warn_total_drop, "total_column": s.total_column,
             "product_check": s.product_check,
             "required_date": list(s.required_date_columns),
             "dedup": s.dedup_on_keys}
            for s in specs.values()]


def _khoa_dich(specs: dict[str, FileSpec], dich: str) -> str:
    return specs[dich].keys[0]


def khoa_chung(specs: dict[str, FileSpec]) -> list[str]:
    """Cột của ma trận: mọi cột là khoá của ít nhất một spec, hoặc là cột
    nguồn của một `references`. Giữ thứ tự xuất hiện đầu tiên trong files.yml."""
    ra: list[str] = []
    for s in specs.values():
        for c in [*s.keys, *s.references]:
            if c not in ra:
                ra.append(c)
    return ra


def _ja_cua(specs: dict[str, FileSpec], cot: str) -> str:
    """Tên OBC của một cột hệ thống — lấy ở spec ĐẦU TIÊN có cột đó."""
    for s in specs.values():
        for ja, vi in s.columns.items():
            if vi == cot:
                return ja
    return cot


def ma_tran(specs: dict[str, FileSpec]) -> dict:
    """◆ khoá chính · ● khoá ngoại · ○ có cột nhưng không phải khoá · "" không có."""
    cot = khoa_chung(specs)
    hang = []
    for s in specs.values():
        co = set(s.columns.values())
        o = []
        for c in cot:
            if c in s.keys:
                o.append("◆")
            elif c in s.references:
                o.append("●")
            elif c in co:
                o.append("○")
            else:
                o.append("")
        hang.append({"ten": s.name, "ja": s.display_name, "o": o})
    return {"cot": [{"vi": c, "ja": _ja_cua(specs, c)} for c in cot], "hang": hang}


def chon_file(specs: dict[str, FileSpec], ten: str | None) -> str:
    return ten if ten in specs else FILE_MAC_DINH


def noi_di_dau(specs: dict[str, FileSpec], ten: str) -> dict:
    s = specs[ten]
    tro_ra = [{"cot": c, "ja": _ja_cua(specs, c), "dich": d,
               "dich_ja": specs[d].display_name, "khoa_dich": _khoa_dich(specs, d)}
              for c, d in s.references.items()]
    tro_vao = [{"nguon": k.name, "nguon_ja": k.display_name, "cot": c}
               for k in specs.values() for c, d in k.references.items() if d == ten]
    return {"tro_ra": tro_ra, "tro_vao": tro_vao}


DONG_SO_DO = 34   # px mỗi hàng của sơ đồ nối — template dùng CÙNG số này


def so_do_noi(specs: dict[str, FileSpec], ten: str) -> dict:
    """Sơ đồ "File này nối đi đâu" của gói thiết kế: cột nối bên trái, file
    ghép được bên phải, đường cong SVG ở giữa. Hình học tính ở máy chủ (không
    JS): mỗi hàng cao DONG_SO_DO, đường đi từ tâm hàng trái sang tâm hàng phải.

    Trái = khoá ngoại của file (trỏ RA) + khoá chính mà file khác trỏ VÀO.
    Phải = mọi file ở đầu bên kia của các đường đó, không trùng."""
    s = specs[ten]
    n = noi_di_dau(specs, ten)
    trai, phai, duong = [], [], []

    def _phai(ma):
        if ma not in phai:
            phai.append(ma)
        return phai.index(ma)

    for x in n["tro_ra"]:
        trai.append({"cot": x["cot"], "ja": x["ja"], "vai": "khoá ngoại"})
        duong.append((len(trai) - 1, _phai(x["dich"]), "ra"))
    if n["tro_vao"]:
        k = s.keys[0]
        trai.append({"cot": k, "ja": _ja_cua(specs, k), "vai": "khoá chính"})
        for x in n["tro_vao"]:
            d = (len(trai) - 1, _phai(x["nguon"]), "vao")
            if d not in duong:          # uriage trỏ vào khách bằng HAI cột
                duong.append(d)
    h = DONG_SO_DO
    cao = max(len(trai), len(phai), 1) * h

    def y(i):
        return i * h + h / 2
    return {
        "trai": trai,
        "phai": [{"ten": m, "ja": specs[m].display_name} for m in phai],
        "cao": cao,
        "duong": [{"d": f"M0,{y(a):g} C50,{y(a):g} 50,{y(b):g} 100,{y(b):g}", "loai": l}
                  for a, b, l in duong],
    }


def _kieu(s: FileSpec, cot: str) -> str:
    if cot in s.code_columns:
        return "mã (text)"
    if cot in s.money_columns:
        return "tiền (yên)"
    if cot in s.qty_columns:
        return "số lượng"
    if cot in s.rate_columns:
        return "tỷ lệ"
    if cot in s.date_columns or cot in s.required_date_columns:
        return "ngày"
    return "chữ"


def cot_cua(specs: dict[str, FileSpec], ten: str) -> list[dict]:
    s = specs[ten]
    ra = []
    for ja, vi in s.columns.items():
        if vi in s.keys:
            vai, noi = "◆", ""
        elif vi in s.references:
            d = s.references[vi]
            vai, noi = "●", f"{specs[d].display_name} ({_khoa_dich(specs, d)})"
        else:
            vai, noi = "", ""
        ra.append({"ja": ja, "vi": vi, "kieu": _kieu(s, vi), "vai": vai, "noi": noi})
    return ra


# ---- Lúc chạy: đọc ảnh chụp ---------------------------------------------

def doc_anh_chup(duong: Path = ANH_CHUP) -> dict | None:
    """None khi thiếu/hỏng — trang vẫn vẽ các khối lấy từ files.yml, khối cần
    ảnh chụp hiện dòng nhắc chạy script. Không trang lỗi."""
    try:
        return json.loads(duong.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def bon_tang(anh: dict | None, specs: dict[str, FileSpec]) -> list[dict]:
    bang = (anh or {}).get("bang", {})
    muc = {
        "OBC": [s.display_name for s in specs.values()],
        "raw": ["raw_archive/ — một bản cho mỗi lô"] + [f"meta.{b}" for b in bang.get("meta", [])],
        "core": [f"core.{b}" for b in bang.get("core", [])],
        "mart": [f"mart.{b}" for b in bang.get("mart", [])],
    }
    return [{"ma": ma, "ten": ten, "mau": mau, "mo_ta": mo_ta, "giu": giu, "muc": muc[ma]}
            for ma, ten, mau, mo_ta, giu in TANG]


def ranh_gioi(anh: dict | None) -> list[dict]:
    """Khối "Ai là sự thật về cái gì" — hai thẻ của gói thiết kế (RANH_GIOI).
    Danh sách SINH từ schema: `core` là sự thật của OBC (tiền, hàng, khách),
    `app` là sự thật của web app (hoạt động). Mỗi mục kèm câu COMMENT ON của
    chính bảng đó nếu migration có viết."""
    bang = (anh or {}).get("bang", {})
    ct = (anh or {}).get("chu_thich", {})

    def ds(schema):
        return [{"ten": f"{schema}.{b}", "chu_thich": ct.get(f"{schema}.{b}", "")}
                for b in bang.get(schema, [])]
    return [
        {"ten": "OBC là sự thật về tiền", "mau": "do", "muc": ds("core"),
         "ghi_chu": "Chỉ đọc. Số sai thì sửa trong OBC rồi xuất lại — không bao giờ UPDATE ở đây."},
        {"ten": "App là sự thật về hoạt động", "mau": "ok", "muc": ds("app"),
         "ghi_chu": "Thứ OBC không có. Không bao giờ ghi ngược vào OBC."},
    ]


def cong(anh: dict | None) -> list[dict]:
    return [{**c, "loai": "chặn" if c["chan"] else "cảnh báo"}
            for c in (anh or {}).get("cong", [])]


def cam_bay(anh: dict | None) -> list[dict]:
    """Thẻ (tên, cách xử) như CAM_BAY của gói thiết kế: tên = câu ĐẦU của mục
    trong CLAUDE.md, phần còn lại là thân. Tách tại dấu chấm/hai chấm đầu tiên
    có khoảng trắng theo sau — `83.75` hay `1.710` không bị cắt."""
    ra = []
    for muc in (anh or {}).get("cam_bay", []):
        m = re.match(r"^(.+?[.:])\s+(.*)$", muc, re.S)
        ra.append({"ten": m.group(1), "cach": m.group(2)} if m else {"ten": muc, "cach": ""})
    return ra


def lo_trinh(anh: dict | None) -> list[dict]:
    """Thẻ như LO_TRINH của gói thiết kế: số đợt, nội dung, dữ liệu mới, và
    các màn (tách cột "Màn" theo `·`). Bảng §7 của đặc tả lộ trình có đúng bốn
    cột Đợt · Nội dung · Màn · Dữ liệu mới."""
    lt = (anh or {}).get("lo_trinh", {"cot": [], "dong": []})
    ra = []
    for d in lt["dong"]:
        if len(d) < 4:
            continue
        so = d[0].replace("*", "")
        man = [m.strip() for m in d[2].split("·") if m.strip() and m.strip() != "—"]
        ra.append({"so": so, "noi_dung": d[1], "man": man, "du_lieu": d[3]})
    return ra
