"""Hình học SVG (thuần Python) cho trang Doanh thu (2026-09-30): biểu đồ bong bóng
và cầu nối (waterfall). Cùng nếp `kome.ve_phan_tich`: chỉ TÍNH TOẠ ĐỘ trên số đã có
của `/api/bao-cao` (0 lượt hỏi thêm), không định nghĩa chỉ số — tỷ suất vẫn là tỷ số
các tổng do `mart` trả, tăng trưởng là cột của `mart.nganh_ky_cung_ky`.

Hai luật đối soát (có test ở `tests/test_ve_doanh_thu.py`):
* bong bóng: Σ `tien` của bóng được vẽ + `khong_ve` = Σ `tien` đầu vào — thứ không vẽ
  được (bóng ≤ 0, không có số so) PHẢI được nói ra, cùng luật cây ô;
* cầu nối: `dau` + Σ bước = `cuoi`, đúng từng yên.
"""
from __future__ import annotations

from math import sqrt
from typing import TYPE_CHECKING

from kome import dinh_dang as DD

if TYPE_CHECKING:
    from kome.bao_cao import NganhKy

# Tăng trưởng vượt ±100% bị KẸP ở mép trục (bóng mang cờ `kep`, ô nổi in số thật) —
# một danh mục mới ×5 không được ép mọi bóng khác vào một góc.
KEP_TANG = 1.0
TOP_MAT_HANG = 40
CAU_NOI_TOI_DA = 8


def _moc(lo: float, hi: float, so: int = 4) -> list[float]:
    if hi <= lo:
        return [lo]
    return [lo + (hi - lo) * i / so for i in range(so + 1)]


def ve_bong(diem: list[dict], rong: int = 520, cao: int = 320, x_moc: float | None = None,
            y_moc: float | None = None, kep_x: float | None = None, co_bong: float = .11) -> dict:
    """`diem`: mỗi phần tử `{ma, ten, x, y, kich, tien}` — `kich` quyết định cỡ bóng,
    `tien` là số dùng để đối soát / nói "không vẽ". Bóng thiếu `x`/`y` hoặc `kich ≤ 0`
    không vẽ được (diện tích âm vô nghĩa). `x_moc`/`y_moc`: đường chữ thập (0% tăng
    trưởng · biên của cả công ty). `kep_x`: kẹp |x| ở mép trục. `co_bong`: bán kính bóng lớn nhất
    / cạnh ngắn của khung."""
    trai, phai, tren, duoi = 44, 14, 12, 26
    ve, khong_ve, so_khong_ve = [], 0, 0
    for d in diem:
        if d.get("x") is None or d.get("y") is None or d.get("kich") is None or d["kich"] <= 0:
            khong_ve += d.get("tien") or 0
            so_khong_ve += 1
            continue
        ve.append(d)
    if not ve:
        return {"co": False, "khong_ve": khong_ve, "so_khong_ve": so_khong_ve}

    def kx(v: float) -> tuple[float, bool]:
        if kep_x is not None and abs(v) > kep_x:
            return (kep_x if v > 0 else -kep_x), True
        return v, False
    xs = [kx(d["x"])[0] for d in ve] + ([x_moc] if x_moc is not None else [])
    ys = [d["y"] for d in ve] + ([y_moc] if y_moc is not None else [])
    x_lo, x_hi, y_lo, y_hi = min(xs), max(xs), min(ys), max(ys)
    dx, dy = (x_hi - x_lo) or abs(x_hi) or 1, (y_hi - y_lo) or abs(y_hi) or 1
    x_lo, x_hi, y_lo, y_hi = x_lo - dx * .12, x_hi + dx * .12, y_lo - dy * .15, y_hi + dy * .15
    k_max = max(d["kich"] for d in ve)
    r_min, r_max = 4.0, min(rong, cao) * co_bong

    def X(v: float) -> float:
        return trai + (v - x_lo) / (x_hi - x_lo) * (rong - trai - phai)

    def Y(v: float) -> float:
        return tren + (1 - (v - y_lo) / (y_hi - y_lo)) * (cao - tren - duoi)
    bong = []
    # To trước, nhỏ sau — bóng nhỏ nằm TRÊN bóng lớn nên vẫn rê chuột tới được.
    for d in sorted(ve, key=lambda d: -d["kich"]):
        v, kep = kx(d["x"])
        bong.append({"ma": d["ma"], "ten": d["ten"], "x": d["x"], "y": d["y"], "kich": d["kich"],
                     "tien": d.get("tien"), "kep": kep, "cx": round(X(v), 1), "cy": round(Y(d["y"]), 1),
                     "r": round(r_min + (r_max - r_min) * sqrt(d["kich"] / k_max), 1)})
    return {"co": True, "rong": rong, "cao": cao, "trai": trai, "phai": rong - phai, "tren": tren,
            "day": cao - duoi, "bong": bong, "khong_ve": khong_ve, "so_khong_ve": so_khong_ve,
            "x_moc": round(X(x_moc), 1) if x_moc is not None else None,
            "y_moc": round(Y(y_moc), 1) if y_moc is not None else None,
            "truc_x": [{"x": round(X(v), 1), "v": v} for v in _moc(x_lo, x_hi)],
            "truc_y": [{"y": round(Y(v), 1), "v": v} for v in _moc(y_lo, y_hi)]}


def bong_danh_muc(nganh_ky: "list[NganhKy]", ty_suat_cty: float | None, lg: bool = False) -> dict:
    """x = tăng/giảm so kỳ so, y = biên lãi gộp (tỷ số các tổng của danh mục), bóng =
    doanh thu (hoặc lãi gộp). `nganh_ky` đã tách phí / POSM (`bao_cao.tach_phi`)."""
    return ve_bong([{"ma": n.nganh, "ten": n.nganh, "x": n.tang_truong,
                     "y": n.lai_gop / n.doanh_thu if n.doanh_thu > 0 else None,
                     "kich": n.lai_gop if lg else n.doanh_thu, "tien": n.lai_gop if lg else n.doanh_thu}
                    for n in nganh_ky], x_moc=0.0, y_moc=ty_suat_cty, kep_x=KEP_TANG)


def bong_mat_hang(hang_theo_nganh: list[dict], ty_suat_cty: float | None, lg: bool = False) -> dict:
    """Top `TOP_MAT_HANG` mã theo doanh thu (bỏ dòng gộp ※終売※ không mã): x = số khách
    mua, y = tỷ suất lãi gộp của mã (cột mart), bóng = doanh thu (hoặc lãi gộp)."""
    hang = sorted((h for h in hang_theo_nganh if h.get("ma")),
                  key=lambda h: h["doanh_thu"] if h["doanh_thu"] is not None else float("-inf"),
                  reverse=True)[:TOP_MAT_HANG]
    ra = ve_bong([{"ma": h["ma"], "ten": h["ten"], "x": h["so_khach"], "y": h["ty_suat"],
                   "kich": h["lai_gop"] if lg else h["doanh_thu"],
                   "tien": h["lai_gop"] if lg else h["doanh_thu"], "nhom": h.get("nhom")}
                  for h in hang], y_moc=ty_suat_cty, co_bong=.075)
    ra["so_ma"] = len(hang)
    return ra


def ve_cau_noi(nganh_ky: "list[NganhKy]", toi_da: int = CAU_NOI_TOI_DA,
               rong: int = 720, cao: int = 260) -> dict:
    """Kỳ so → mỗi danh mục cộng / trừ `chenh_lech` → kỳ này (trên CÙNG dải đối chiếu:
    đầu = Σ `dt_cung_ky`, cuối = Σ `dt_doi_chieu`). `toi_da` danh mục đổi nhiều nhất,
    phần còn lại gộp một bước. Danh mục không có số so không vào cầu (nói ra ở
    `khong_so`). Trục KHÔNG từ 0 (bước vài trăm vạn trên tổng hàng trăm triệu sẽ
    không thấy) — `day` là đáy trục, màn phải nói ra."""
    so = [n for n in nganh_ky if n.chenh_lech is not None and n.dt_cung_ky is not None
          and n.dt_doi_chieu is not None]
    khong = [n for n in nganh_ky if n not in so]
    if not so:
        return {"co": False}
    dau = sum(n.dt_cung_ky for n in so)
    cuoi = sum(n.dt_doi_chieu for n in so)
    sap = sorted(so, key=lambda n: -abs(n.chenh_lech))
    buoc = [(n.nganh, n.chenh_lech, 1) for n in sap[:toi_da]]
    con = sap[toi_da:]
    if con:
        buoc.append((f"Danh mục khác ({len(con)})", sum(n.chenh_lech for n in con), len(con)))
    buoc.sort(key=lambda b: -b[1])
    muc, chay = [dau], dau
    for _, v, _ in buoc:
        chay += v
        muc.append(chay)
    lo, hi = min(muc + [cuoi]), max(muc + [cuoi])
    bien = (hi - lo) * .15 or abs(hi) * .05 or 1
    day = max(lo - bien, 0) if lo >= 0 else lo - bien
    dinh = hi + bien
    trai, phai, tren, duoi = 56, 10, 12, 40
    n = len(buoc) + 2
    w_o = (rong - trai - phai) / n
    w = w_o * .64

    def Y(v: float) -> float:
        return tren + (1 - (v - day) / (dinh - day)) * (cao - tren - duoi)

    def cot(i, nhan, tu, den, loai, gia, so_dm=1):
        x = trai + i * w_o + (w_o - w) / 2
        y1, y2 = Y(max(tu, den)), Y(min(tu, den))
        return {"nhan": nhan, "x": round(x, 1), "w": round(w, 1), "y": round(y1, 1),
                "h": round(max(y2 - y1, 1), 1), "loai": loai, "gia": gia, "tu": tu, "den": den,
                "so_dm": so_dm, "cx": round(x + w / 2, 1)}
    ds = [cot(0, "Kỳ so", day, dau, "dau", dau)]
    chay = dau
    for i, (ten, v, k) in enumerate(buoc, start=1):
        ds.append(cot(i, ten, chay, chay + v, "tang" if v >= 0 else "giam", v, k))
        chay += v
    ds.append(cot(n - 1, "Kỳ này", day, cuoi, "cuoi", cuoi))
    return {"co": True, "rong": rong, "cao": cao, "trai": trai, "day_truc": cao - duoi,
            "cot": ds, "dau": dau, "cuoi": cuoi, "day": day,
            # Vạch nối ngang: đỉnh luỹ kế sau mỗi cột tới cột kế.
            "noi": [{"x1": round(a["x"] + a["w"], 1), "x2": b["x"], "y": round(Y(a["den"]), 1)}
                    for a, b in zip(ds[:-1], ds[1:])],
            "truc": [{"y": round(Y(v), 1), "nhan": DD.gon(v)} for v in _moc(day, dinh)],
            "khong_so": {"so": len(khong), "tien": sum(n.doanh_thu for n in khong)}}
