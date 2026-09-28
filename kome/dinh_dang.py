"""Định dạng số cho CHỮ do máy chủ viết sẵn (câu tóm tắt, nhãn trục) — CHUẨN NHẬT, chủ DN
chốt 2026-09-29: ¥1,234,567 · ¥1,170万 / ¥1.2億 · 1.5× · 62.9%. Bản chép bắt buộc của
`giao_dien/src/dinh_dang.ts::yen` / `gon` (có test canh: tests/test_dinh_dang.py)."""


def yen(n: float | int | None) -> str:
    if n is None:
        return "—"
    v = round(n)
    return ("−¥" if v < 0 else "¥") + f"{abs(v):,}"


def gon(n: float | int | None) -> str:
    if n is None:
        return "—"
    a, dau = abs(n), ("−¥" if n < 0 else "¥")
    def bo0(x: str) -> str:
        return x[:-2] if x.endswith(".0") else x
    if a >= 1e8:
        return dau + bo0(f"{a / 1e8:.{0 if a >= 1e10 else 1}f}") + "億"
    if a >= 1e5:
        return dau + f"{round(a / 1e4):,}" + "万"
    if a >= 1e4:
        return dau + bo0(f"{a / 1e4:.1f}") + "万"
    return dau + f"{round(a):,}"
