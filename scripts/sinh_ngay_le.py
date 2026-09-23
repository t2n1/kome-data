"""Sinh danh sách ngày lễ quốc gia Nhật (国民の祝日) cho core.dim_date.

Dùng MỘT LẦN để viết khối VALUES của migration 032 (và mỗi lần cần nới dải
năm — khi đó viết migration MỚI, không sửa 032):

    python scripts/sinh_ngay_le.py 2024 2035 > khoi_values.sql

Luật (祝日法, bản hiện hành):
- Ngày cố định: 元日 1/1 · 建国記念の日 2/11 · 天皇誕生日 2/23 · 昭和の日 4/29 ·
  憲法記念日 5/3 · みどりの日 5/4 · こどもの日 5/5 · 山の日 8/11 · 文化の日 11/3 ·
  勤労感謝の日 11/23.
- Thứ Hai (Happy Monday): 成人の日 thứ Hai thứ 2 của tháng 1 · 海の日 thứ Hai thứ 3
  tháng 7 · 敬老の日 thứ Hai thứ 3 tháng 9 · スポーツの日 thứ Hai thứ 2 tháng 10.
- 春分の日 / 秋分の日: công thức thiên văn gần đúng dùng rộng rãi cho 1980–2099.
  Ngày CHÍNH THỨC chỉ được 国立天文台 công bố vào tháng 2 năm trước — năm nào lệch
  thì sửa bằng một migration mới, không sửa file này rồi tưởng 032 tự đổi.
- 振替休日: lễ rơi vào Chủ nhật → ngày thường đầu tiên sau đó là ngày nghỉ bù.
- 国民の休日: một ngày thường kẹp giữa hai ngày lễ → cũng là ngày nghỉ.

KHÔNG gồm ngày nghỉ riêng của công ty (Obon, 年末年始 29/12–3/1): đó là lịch của
KOME, không phải luật — không có ở đâu để đọc, và đoán thì là bịa.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta

CO_DINH = {(1, 1): "元日", (2, 11): "建国記念の日", (2, 23): "天皇誕生日",
           (4, 29): "昭和の日", (5, 3): "憲法記念日", (5, 4): "みどりの日",
           (5, 5): "こどもの日", (8, 11): "山の日", (11, 3): "文化の日",
           (11, 23): "勤労感謝の日"}
THU_HAI = {(1, 2): "成人の日", (7, 3): "海の日", (9, 3): "敬老の日", (10, 2): "スポーツの日"}


def _thu_hai(y: int, m: int, lan: int) -> date:
    d = date(y, m, 1)
    d += timedelta(days=(7 - d.weekday()) % 7)      # thứ Hai đầu tiên
    return d + timedelta(weeks=lan - 1)


def _phan(y: int, goc: float) -> int:
    return int(goc + 0.242194 * (y - 1980) - int((y - 1980) / 4))


def ngay_le(y: int) -> dict[date, str]:
    le = {date(y, m, d): ten for (m, d), ten in CO_DINH.items()}
    le.update({_thu_hai(y, m, lan): ten for (m, lan), ten in THU_HAI.items()})
    le[date(y, 3, _phan(y, 20.8431))] = "春分の日"
    le[date(y, 9, _phan(y, 23.2488))] = "秋分の日"
    # 振替休日
    for d in sorted(le):
        if d.weekday() == 6:
            bu = d + timedelta(days=1)
            while bu in le:
                bu += timedelta(days=1)
            le[bu] = "振替休日"
    # 国民の休日 — ngày thường (không phải Chủ nhật) kẹp giữa hai ngày lễ
    for d in sorted(le):
        g = d + timedelta(days=1)
        if g not in le and g + timedelta(days=1) in le and g.weekday() != 6:
            le[g] = "国民の休日"
    return dict(sorted(le.items()))


def khoi_values(tu: int, den: int) -> str:
    dong = [f"    ('{d.isoformat()}', '{ten}')"
            for y in range(tu, den + 1) for d, ten in ngay_le(y).items()]
    return ",\n".join(dong)


if __name__ == "__main__":
    tu, den = (int(a) for a in sys.argv[1:3]) if len(sys.argv) >= 3 else (2024, 2035)
    sys.stdout.buffer.write((khoi_values(tu, den) + "\n").encode("utf-8"))
