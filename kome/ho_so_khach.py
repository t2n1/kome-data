"""Hồ sơ 360° cho giao diện React (giai đoạn 2) — chỉ CHUYỂN DẠNG, không SQL.

Nhận `kome.khach_hang.HoSo` (đã lấy đủ trong <= 8 lượt hỏi) và dựng các khối
mà gói thiết kế `Customer 360.dc.html` vẽ: 6 ô số, lưới 26 tuần, giỏ theo
ngành, lịch mua dự kiến, danh sách mã sắp đến ngày mua, thẻ tự động.

Không định nghĩa chỉ số mới: mọi con số là TỔNG / ĐẾM trên các dòng mà `mart`
đã tính (khach_mat_hang, lan_mua, khach_theo_thang, khach_thang_nay). Tỷ suất
theo ngành là TỶ SỐ CỦA CÁC TỔNG (bất biến CLAUDE.md), không trung bình tỷ số.
Mọi cửa sổ thời gian tính từ MỐC DỮ LIỆU (`HoSo.hom_nay` = mart.moc_thoi_gian),
không từ đồng hồ thật.
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date, timedelta

from kome import khach_hang as KH
from kome import khach_thang as KT
from kome import lien_he as LH

# Cửa sổ của khối "Dự báo đơn kế tiếp" (gói thiết kế: "dự đoán đã quá 14 ngày").
DU_BAO_NGAY = 14
SO_TUAN = 26


def _ty_so(tu, mau):
    return (tu / mau) if (tu is not None and mau) else None


def _d(x) -> date | None:
    if x is None or isinstance(x, date):
        return x
    return date.fromisoformat(str(x)[:10])


def tuan_26(ngay_mua: list[dict], moc: date | None) -> list[dict]:
    """26 tuần lùi từ mốc (phần tử 0 = tuần CŨ nhất, phần tử cuối = tuần chứa
    mốc). Mỗi tuần: tổng doanh thu và số ngày có mua."""
    if moc is None:
        return []
    ra = []
    for i in range(SO_TUAN - 1, -1, -1):
        den = moc - timedelta(days=7 * i)
        tu = den - timedelta(days=6)
        dong = [n for n in ngay_mua if tu <= _d(n["ngay"]) <= den]
        ra.append({"tu": tu, "den": den, "so_ngay": len(dong),
                   "doanh_thu": int(sum(n["doanh_thu"] or 0 for n in dong))})
    return ra


def cua_so(ngay_mua: list[dict], moc: date | None, tu_ngay: int, den_ngay: int) -> int:
    """Tổng doanh thu các ngày mua trong (mốc - tu_ngay, mốc - den_ngay]."""
    if moc is None:
        return 0
    a, b = moc - timedelta(days=tu_ngay), moc - timedelta(days=den_ngay)
    return int(sum(n["doanh_thu"] or 0 for n in ngay_mua if a < _d(n["ngay"]) <= b))


def theo_nganh(mat_hang: list[dict]) -> dict:
    """Giỏ hàng theo ngành. Ngành doanh thu <= 0 KHÔNG vẽ được (donut / chấm)
    và phải nói ra số tiền bị bỏ — cùng bất biến cây ô (`ve_cay_o`)."""
    g: dict[str, dict] = {}
    for m in mat_hang:
        x = g.setdefault(m["nganh"], {"nganh": m["nganh"], "doanh_thu": 0, "lai_gop": 0, "so_ma": 0})
        x["doanh_thu"] += int(m["doanh_thu"] or 0)
        x["lai_gop"] += int(m["lai_gop"] or 0)
        x["so_ma"] += 1
    ve = sorted((x for x in g.values() if x["doanh_thu"] > 0), key=lambda x: -x["doanh_thu"])
    tong = sum(x["doanh_thu"] for x in ve)
    for x in ve:
        x["ty_trong"] = _ty_so(x["doanh_thu"], tong)
        x["bien"] = _ty_so(x["lai_gop"], x["doanh_thu"])
    bo = [x for x in g.values() if x["doanh_thu"] <= 0]
    return {"nganh": ve, "khong_ve": sum(x["doanh_thu"] for x in bo), "so_nganh_khong_ve": len(bo)}


def lich_mua(mat_hang: list[dict], moc: date | None) -> dict:
    """Mã có ngày dự kiến mua lại (khach_mat_hang.du_kien_lan_toi). `con` < 0 =
    đã quá ngày dự kiến. Chỉ mã còn nhãn 'mua' — mã 'ngung' đã có khối riêng,
    'khong_goi' (※廃業※) không bao giờ vào danh sách gọi."""
    if moc is None:
        return {"ma": [], "so_tre": 0, "tong": 0}
    ds = []
    for m in mat_hang:
        if m["du_kien"] is None or m["trang_thai_cap"] != "mua":
            continue
        ds.append({"ma": m["ma"], "ten": m["ten"], "du_kien": m["du_kien"],
                   "con": (_d(m["du_kien"]) - moc).days, "nhip": m["nhip"],
                   "lan_cuoi": m["lan_cuoi"], "doanh_thu": int(m["doanh_thu"] or 0),
                   "tb_moi_lan": _ty_so(float(m["so_luong"] or 0), m["so_lan"])})
    ds.sort(key=lambda x: (x["con"], -x["doanh_thu"]))
    return {"ma": ds, "so_tre": sum(1 for x in ds if x["con"] < 0), "tong": len(ds)}


def the_tu_dong(h: KH.HoSo, hang: str | None) -> list[dict]:
    """Thẻ suy ra từ dữ liệu THẬT — mỗi thẻ kèm câu giải thích nó đến từ đâu."""
    k, the = h.khach, []
    if hang in ("S", "A"):
        the.append({"chu": f"⭐ Hạng {hang}", "vi": "hạng theo doanh thu 12 tháng (không phải 得意先ランク)"})
    if k.trang_thai == "da_roi_bo":
        the.append({"chu": "💤 Lâu không mua", "vi": "im lặng ≥ 4× nhịp mua riêng", "mau": "do"})
    elif k.trang_thai == "canh_bao":
        the.append({"chu": "⏰ Quá nhịp mua", "vi": "im lặng 2–4× nhịp mua riêng", "mau": "canh"})
    t = h.thang_nay or {}
    if t.get("nhan") == "tre":
        the.append({"chu": "📅 Mua đều, tháng này chưa", "vi": KT.CACH_TINH, "mau": "canh"})
    elif t.get("nhan") == "da_mua":
        the.append({"chu": "✅ Tháng này đã mua", "vi": f"tháng {_thang(t.get('thang'))}", "mau": "ok"})
    if k.nhip_ngay is not None and k.nhip_ngay <= 7:
        the.append({"chu": "🔁 Tần suất cao", "vi": f"nhịp mua {round(k.nhip_ngay)} ngày"})
    ngung = sum(1 for m in h.tat_ca_mat_hang if m["trang_thai_cap"] == "ngung")
    if ngung:
        the.append({"chu": f"📉 {ngung} mã đã ngừng mua", "vi": "im lặng ≥ 2× nhịp riêng của cặp khách–mã", "mau": "canh"})
    return the


def _thang(t: str | None) -> str:
    """'2026-07' -> '7/2026'."""
    if not t:
        return "—"
    y, m = t.split("-")
    return f"{int(m)}/{y}"


def dien_giai(h: KH.HoSo, lich: dict) -> str:
    """Một câu tóm tắt từ số thật (banner diễn giải của gói thiết kế)."""
    k, t, cau = h.khach, h.thang_nay or {}, []
    if t.get("nhan") == "da_mua":
        so = t["dt_thang_truoc_den_ngay"]
        tang = _ty_so(t["dt_thang_nay"] - so, so) if so else None
        cau.append(f"Tháng {_thang(t['thang'])} đã mua ¥{t['dt_thang_nay']:,}".replace(",", ".")
                   + (f", {'hơn' if tang >= 0 else 'kém'} {abs(tang) * 100:.0f}% so tháng trước cùng ngày"
                      if tang is not None else ""))
    elif t.get("nhan") == "tre":
        cau.append(f"Mua đều ({t['so_thang_mua_3']}/3 tháng trước) nhưng tháng {_thang(t['thang'])} chưa có đơn")
    elif t.get("nhan") == "chua_toi_ngay":
        cau.append(f"Tháng {_thang(t['thang'])} chưa có đơn — khách thường mua muộn hơn trong tháng")
    if k.trang_thai in KH.TRANG_THAI_CAN_XU_LY and k.so_ngay_im_lang is not None:
        cau.append(f"im lặng {k.so_ngay_im_lang} ngày"
                   + (f" ({k.ty_le_im_lang:.1f}× nhịp {round(k.nhip_ngay)} ngày)".replace(".", ",")
                      if k.ty_le_im_lang and k.nhip_ngay else ""))
    ngung = sum(1 for m in h.tat_ca_mat_hang if m["trang_thai_cap"] == "ngung")
    if ngung:
        cau.append(f"{ngung} mã đã ngừng mua")
    if lich["so_tre"]:
        cau.append(f"{lich['so_tre']} mã đã quá ngày mua lại dự kiến")
    return (". ".join([cau[0][:1].upper() + cau[0][1:]] + cau[1:]) + ".") if cau else ""


def cho_giao_dien(h: KH.HoSo) -> dict:
    hang = h.ho_so.get("hang_dt")
    moc = _d(h.hom_nay)
    lich = lich_mua(h.tat_ca_mat_hang, moc)
    k = h.khach
    ngung = [m for m in h.tat_ca_mat_hang if m["trang_thai_cap"] == "ngung"]
    return {
        "khach": asdict(k), "hang": hang, "ho_so": h.ho_so, "hom_nay": moc,
        "nhan_trang_thai": {a: b[0] for a, b in KH.TRANG_THAI.items()},
        "thang_nay": h.thang_nay, "nhan_thang": KT.NHAN, "cach_tinh_thang": KT.CACH_TINH,
        "dien_giai": dien_giai(h, lich), "the": the_tu_dong(h, hang),
        "o_so": {
            "dt_30": cua_so(h.ngay_mua, moc, 30, 0),
            "dt_30_truoc": cua_so(h.ngay_mua, moc, 60, 30),
            "so_ma_dang_mua": sum(1 for m in h.tat_ca_mat_hang if m["trang_thai_cap"] == "mua"),
            "so_ma_ngung": len(ngung),
        },
        "thang": h.thang, "tuan": tuan_26(h.ngay_mua, moc),
        "nganh": theo_nganh(h.tat_ca_mat_hang),
        "mat_hang": h.tat_ca_mat_hang, "da_ngung_mua": ngung[:10],
        "chua_mua_thang": h.chua_mua_thang, "goi_y": h.goi_y,
        "lich": {**lich, "ma": lich["ma"][:10]},
        "du_bao": [x for x in lich["ma"] if x["con"] <= DU_BAO_NGAY],
        "lan_mua_gan_day": h.lan_mua_gan_day, "diem_giao": h.diem_giao,
        "nhat_ky": [{**asdict(n), "icon": n.icon, "nhan_kieu": n.nhan_kieu,
                     "nhan_ket_qua": n.nhan_ket_qua, "mau_ket_qua": n.mau_ket_qua,
                     "ngay": n.ngay} for n in h.nhat_ky],
        "kieu_tx": {a: list(b) for a, b in LH.KIEU.items()},
        "ket_qua_tx": {a: list(b) for a, b in LH.KET_QUA.items()},
    }
