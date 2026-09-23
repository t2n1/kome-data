"""Sinh ảnh chụp tài liệu sống cho màn Kho dữ liệu (đợt 2b).

Chạy lại MỖI KHI sửa một trong bốn nguồn dưới đây — test
`tests/test_tai_lieu.py::test_anh_chup_tai_lieu_khong_cu` đỏ nếu quên:

    python scripts/sinh_tai_lieu.py

Nguồn (đều KHÔNG có trên Vercel, nên web đọc ảnh chụp thay vì đọc thẳng):
- `db/migrations/*.sql`   → bảng/view theo schema (khối "Bốn tầng")
- `kome/gates.py`         → hằng TEN_CONG (khối "Đối chiếu bắt buộc")
- `CLAUDE.md`             → mục "Bẫy đã biết" (khối "Cạm bẫy riêng của OBC")
- đặc tả lộ trình §7      → bảng các đợt (khối "Lộ trình")
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
RA = GOC / "kome" / "web" / "tai_lieu_sinh.json"
LO_TRINH = GOC / "docs" / "superpowers" / "specs" / "2026-09-21-lo-trinh-24-man-hinh-design.md"
SCHEMA = ("core", "mart", "app", "meta")

_TAO = re.compile(
    r"\bCREATE\s+(?:OR\s+REPLACE\s+)?(?:TABLE|VIEW|MATERIALIZED\s+VIEW)\s+"
    r"(?:IF\s+NOT\s+EXISTS\s+)?(core|mart|app|meta)\.(\w+)", re.I)
_XOA = re.compile(
    r"\bDROP\s+(?:TABLE|VIEW|MATERIALIZED\s+VIEW)\s+(?:IF\s+EXISTS\s+)?"
    r"(core|mart|app|meta)\.(\w+)", re.I)


def bang_theo_schema(thu_muc: Path) -> dict[str, list[str]]:
    """Duyệt migration theo thứ tự tên file, sự kiện theo thứ tự trong file:
    CREATE thêm, DROP bỏ. Bỏ chú thích `--` trước — chú thích nhắc tên một
    view cũ không được làm nó sống lại."""
    con: dict[str, set[str]] = {s: set() for s in SCHEMA}
    for f in sorted(thu_muc.glob("*.sql")):
        sql = re.sub(r"--[^\n]*", "", f.read_text(encoding="utf-8"))
        su_kien = [(m.start(), "tao", m) for m in _TAO.finditer(sql)] + \
                  [(m.start(), "xoa", m) for m in _XOA.finditer(sql)]
        for _, loai, m in sorted(su_kien, key=lambda x: x[0]):
            s, t = m.group(1).lower(), m.group(2).lower()
            (con[s].add if loai == "tao" else con[s].discard)(t)
    return {s: sorted(v) for s, v in con.items()}


def ten_cong() -> list[dict]:
    """Hằng `kome.gates.TEN_CONG` / `CHAN`. Nhập ở đây được (script chạy ở máy
    có pandas); web thì không, nên mới cần ảnh chụp."""
    sys.path.insert(0, str(GOC))
    from kome.gates import CHAN, TEN_CONG
    return [{"so": n, "ten": TEN_CONG[n], "chan": n in CHAN} for n in sorted(TEN_CONG)]


def cam_bay(claude_md: Path) -> list[str]:
    """Mục `## Bẫy đã biết`: mỗi mục `N. ` tới hết đoạn; dòng thụt lề nối
    tiếp gộp vào bằng một dấu cách."""
    van = claude_md.read_text(encoding="utf-8")
    m = re.search(r"^## Bẫy đã biết\s*\n(.*?)(?=^## )", van, re.S | re.M)
    if not m:
        raise SystemExit("CLAUDE.md không có mục '## Bẫy đã biết'")
    muc: list[str] = []
    for dong in m.group(1).splitlines():
        if re.match(r"^\d+\.\s", dong):
            muc.append(re.sub(r"^\d+\.\s+", "", dong).strip())
        elif dong.strip() and muc:
            muc[-1] += " " + dong.strip()
    return muc


def _o(dong: str) -> list[str]:
    return [c.strip() for c in dong.strip().strip("|").split("|")]


def lo_trinh(dac_ta: Path) -> dict:
    """Bảng markdown ĐẦU TIÊN sau tiêu đề `## 7. Lộ trình`."""
    van = dac_ta.read_text(encoding="utf-8")
    m = re.search(r"^## 7\. Lộ trình\s*\n(.*?)(?=^## )", van, re.S | re.M)
    if not m:
        raise SystemExit("Đặc tả lộ trình không có mục '## 7. Lộ trình'")
    # Bảng đầu tiên = chuỗi dòng `|` liền nhau đầu tiên.
    bang: list[str] = []
    for d in m.group(1).splitlines():
        if d.startswith("|"):
            bang.append(d)
        elif bang:
            break
    return {"cot": _o(bang[0]), "dong": [_o(d) for d in bang[2:]]}


def sinh(goc: Path = GOC) -> dict:
    return {
        "bang": bang_theo_schema(goc / "db" / "migrations"),
        "cong": ten_cong(),
        "cam_bay": cam_bay(goc / "CLAUDE.md"),
        "lo_trinh": lo_trinh(goc / LO_TRINH.relative_to(GOC)),
    }


def van_ban(anh: dict) -> str:
    return json.dumps(anh, ensure_ascii=False, sort_keys=True, indent=1) + "\n"


def main() -> None:
    RA.write_text(van_ban(sinh()), encoding="utf-8", newline="\n")
    # ASCII: console Windows của máy công ty là cp1252, in chữ có dấu thì nổ
    # UnicodeEncodeError SAU khi file đã ghi xong — người chạy tưởng hỏng.
    print(f"OK: {RA.relative_to(GOC).as_posix()}")


if __name__ == "__main__":
    sys.exit(main())
