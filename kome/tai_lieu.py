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

# Phần văn xuôi DUY NHẤT viết trong code: một câu cho mỗi tầng. Danh sách
# bảng/view của từng tầng thì sinh từ migration (ảnh chụp).
TANG = [
    ("raw", "File gốc OBC",
     "Bản sao nguyên vẹn từng file đã nạp, lưu theo lô (raw_archive/). "
     "Không sửa, không xoá — là thứ để lần ngược mọi con số."),
    ("core", "Dữ liệu OBC đã chuẩn hoá",
     "Chỉ vai trò kome_ingest ghi. Mỗi dòng mang batch_id trỏ về meta.ingest_batch, "
     "nên hoàn tác được cả lô."),
    ("mart", "Định nghĩa chỉ số",
     "Chỉ có view. Mọi chỉ số của web app được định nghĩa ở đây và CHỈ ở đây."),
    ("app", "Dữ liệu web app tự ghi",
     "Tài khoản, ngân sách… — thứ OBC không có. Không bao giờ ghi ngược vào OBC."),
]


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


def nguon_obc(specs: dict[str, FileSpec]) -> list[dict]:
    return [{"ten": s.name, "ja": s.display_name, "mo_ta": _mo_ta(s),
             "mau": s.filename_pattern, "header_row": s.header_row,
             "keys": list(s.keys), "core_table": s.core_table,
             "tan_suat": _tan_suat(s)}
            for s in specs.values()]


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
    ra = []
    for ma, ten, mo_ta in TANG:
        if ma == "raw":
            muc = [s.display_name for s in specs.values()]
        elif ma == "core":
            muc = [f"core.{b}" for b in bang.get("core", [])] + \
                  [f"meta.{b}" for b in bang.get("meta", [])]
        else:
            muc = [f"{ma}.{b}" for b in bang.get(ma, [])]
        ra.append({"ma": ma, "ten": ten, "mo_ta": mo_ta, "muc": muc})
    return ra


def cong(anh: dict | None) -> list[dict]:
    return [{**c, "loai": "chặn" if c["chan"] else "cảnh báo"}
            for c in (anh or {}).get("cong", [])]


def cam_bay(anh: dict | None) -> list[str]:
    return list((anh or {}).get("cam_bay", []))


def lo_trinh(anh: dict | None) -> dict:
    return (anh or {}).get("lo_trinh", {"cot": [], "dong": []})
