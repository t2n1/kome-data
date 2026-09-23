"""Hình học SVG (thuần Python) cho màn Dự báo — bám `Dự báo.dc.html`.

Chỉ TÍNH TOẠ ĐỘ, không định nghĩa chỉ số (công thức ở `kome.du_bao`, dữ liệu
ở `mart`). Màu do template gán bằng biến CSS — không mã màu nào ở đây.
"""
from __future__ import annotations

from kome.du_bao import ChotThang, MuoiHaiThang


def _bac(dinh: float, so_bac: int = 4) -> list[float]:
    """Các mốc trục tung "tròn": 1/2/2,5/5 × 10^k."""
    if dinh <= 0:
        return [0.0]
    tho = dinh / so_bac
    mu = 10 ** (len(str(int(tho))) - 1)
    for he in (1, 2, 2.5, 5, 10):
        if he * mu >= tho:
            buoc = he * mu
            break
    return [buoc * i for i in range(so_bac + 1)]


def _trieu(v: float) -> str:
    return f"¥{v / 1_000_000:.0f}M" if v >= 10_000_000 else f"¥{v / 1_000_000:.1f}M".replace(".", ",")


def ve_chot_thang(c: ChotThang, rong: int = 960, cao: int = 280) -> dict:
    """Đường luỹ kế theo NGÀY LỊCH của tháng: thực tế tới hôm nay, rồi ba đường
    dự báo (cơ sở nét đứt, thấp/cao) và nhịp ngân sách (nếu đã đặt). Phần cộng
    thêm của mỗi ngày tương lai tăng theo SỐ NGÀY LÀM VIỆC tới ngày đó — thứ
    Bảy/Chủ nhật là bậc phẳng, đúng như công thức chốt tháng."""
    trai, phai, tren, duoi = 64, 20, 16, 30
    ngay = c.ngay
    D = len(ngay)
    if D == 0:
        return {"co": False}
    nhip = c.da_ban / c.e if c.e else 0.0
    them_cs = c.co_so - c.da_ban
    ty_thap = (c.thap - c.da_ban) / them_cs if c.thap is not None and them_cs else None
    ty_cao = (c.cao - c.da_ban) / them_cs if c.cao is not None and them_cs else None

    dinh = max([c.co_so, c.cao or 0, c.ngan_sach or 0, c.da_ban, 1]) * 1.08
    moc = _bac(dinh)
    dinh = max(dinh, moc[-1])

    def X(i: int) -> float:
        return trai + (i / max(D - 1, 1)) * (rong - trai - phai)

    def Y(v: float) -> float:
        return tren + (1 - v / dinh) * (cao - tren - duoi)

    tt, cs, th, ca, ns = [], [], [], [], []
    luy_ke, kd_qua, kd_sau = 0, 0, 0
    i_nay = 0
    for i, n in enumerate(ngay):
        if n.la_kd:
            kd_qua += 1
        if n.ngay <= c.hom_nay:
            luy_ke += n.dt or 0
            tt.append((X(i), Y(luy_ke)))
            i_nay = i
        else:
            if n.la_kd:
                kd_sau += 1
            them = nhip * kd_sau
            cs.append((X(i), Y(c.da_ban + them)))
            if ty_thap is not None:
                th.append((X(i), Y(c.da_ban + them * ty_thap)))
                ca.append((X(i), Y(c.da_ban + them * ty_cao)))
        if c.ngan_sach:
            ns.append((X(i), Y(c.ngan_sach * kd_qua / c.n if c.n else 0)))
    diem_nay = (X(i_nay), Y(c.da_ban))
    # Đường dự báo xuất phát TỪ điểm hôm nay, không lơ lửng cách một ngày.
    for ds in (cs, th, ca):
        if ds:
            ds.insert(0, diem_nay)

    def pl(ds):
        return " ".join(f"{x:.1f},{y:.1f}" for x, y in ds)

    dai = ""
    if th and ca:
        dai = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in ca) + " L" + \
              " L".join(f"{x:.1f},{y:.1f}" for x, y in reversed(th)) + " Z"
    nhan_ngay = [{"x": round(X(i), 1), "nhan": str(n.ngay.day)}
                 for i, n in enumerate(ngay)
                 if n.ngay.day in (1, 5, 10, 15, 20, 25) or i == D - 1]
    cuoi = cs[-1] if cs else diem_nay
    return {"co": True, "rong": rong, "cao": cao, "trai": trai, "phai": rong - phai,
            "truc": [{"y": round(Y(v), 1), "nhan": _trieu(v)} for v in moc],
            "tt": pl(tt), "cs": pl(cs), "thap": pl(th), "cao_": pl(ca), "ns": pl(ns), "dai": dai,
            "x_nay": round(diem_nay[0], 1), "y_nay": round(diem_nay[1], 1),
            "x_cuoi": round(cuoi[0], 1), "y_cuoi": round(cuoi[1], 1),
            "nhan_ngay": nhan_ngay, "day_truc": cao - duoi}


def ve_muoi_hai_thang(m: MuoiHaiThang, kb: str = "cs", rong: int = 960, cao: int = 300) -> dict:
    """Cột 12 tháng đã qua (thực tế) + 12 tháng tới (kịch bản đang chọn), kèm
    râu thận trọng–lạc quan trên mỗi cột dự báo."""
    trai, phai, tren, duoi = 64, 16, 16, 30
    cot_ds = [(t, v, None) for t, v in m.lich_su] + [(t.thang, t.theo(kb), t) for t in m.du_bao]
    if not cot_ds:
        return {"co": False}
    dinh = max([max(v, 0) for _, v, _ in cot_ds] + [t.cao for t in m.du_bao] + [1]) * 1.08
    moc = _bac(dinh)
    dinh = max(dinh, moc[-1])
    buoc = (rong - trai - phai) / len(cot_ds)
    w = buoc * 0.62

    def Y(v: float) -> float:
        return tren + (1 - max(v, 0) / dinh) * (cao - tren - duoi)
    cot, rau, nhan = [], [], []
    for i, (th, v, tdb) in enumerate(cot_ds):
        x = trai + i * buoc + (buoc - w) / 2
        cot.append({"x": round(x, 1), "y": round(Y(v), 1), "w": round(w, 1),
                    "h": round(Y(0) - Y(v), 1), "loai": "db" if tdb else "tt",
                    "chu": f"{th}: ¥{v:,}" + (" (dự báo)" if tdb else "")})
        if tdb:
            rau.append({"x": round(x + w / 2, 1), "y1": round(Y(tdb.cao), 1), "y2": round(Y(tdb.thap), 1)})
        nhan.append({"x": round(x + w / 2, 1), "nhan": f"{th[5:]}/{th[2:4]}"})
    x_chia = trai + len(m.lich_su) * buoc if m.du_bao and m.lich_su else None
    return {"co": True, "rong": rong, "cao": cao, "trai": trai, "phai": rong - phai,
            "truc": [{"y": round(Y(v), 1), "nhan": _trieu(v)} for v in moc],
            "cot": cot, "rau": rau, "nhan": nhan,
            "x_chia": round(x_chia, 1) if x_chia else None, "day_truc": cao - duoi}
