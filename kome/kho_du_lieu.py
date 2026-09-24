"""Màn Kho dữ liệu theo gói thiết kế (đợt B, 2026-09-24): Tổng quan + Nạp hai bước.

Hàm thuần — mọi truy vấn vẫn là của `kome/web/app.py::_du_lieu_kho` (cộng MỘT câu
danh mục `pg_class` cho ô "Bảng trong kho"/"Tổng số dòng"). Ở đây chỉ dựng hình
dạng cho giao diện: nút của sơ đồ nguồn, bốn ô số, các ô nạp, năm dòng cổng kiểm.

Đặc tả: docs/superpowers/specs/2026-09-24-kho-du-lieu-theo-thiet-ke-design.md §B.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta

from kome.config import SPECS
from kome.tuoi_du_lieu import MUI_GIO

# Các ô của màn Nạp = các nhánh của sơ đồ nguồn — MỘT danh sách. `specs`: loại
# file ô đó nhận (Bán hàng nhận cả 売上伝票データ lẫn nguồn dự phòng 売上明細表 —
# cùng đổ vào core.fact_sales_line). `nhip`: 'ngay' = nhịp 13:30 hằng ngày (cùng
# bộ với kome/tuoi_du_lieu.NGUON_HANG_NGAY), 'nen' = dữ liệu nền ít đổi, 'ky' =
# sổ theo kỳ.
O_NAP = [
    {"ma": "ban", "nhan": "Bán hàng", "specs": ["uriage", "meisai"], "nhip": "ngay"},
    {"ma": "ton", "nhan": "Tồn kho", "specs": ["zaiko"], "nhip": "ngay"},
    {"ma": "khach", "nhan": "Khách hàng", "specs": ["tokuisaki"], "nhip": "ngay"},
    {"ma": "sp", "nhan": "Sản phẩm", "specs": ["shohin"], "nhip": "nen"},
    {"ma": "ncc", "nhan": "Nhà cung cấp", "specs": ["shiiresaki"], "nhip": "nen"},
    {"ma": "giao", "nhan": "Giao thẳng", "specs": ["chokusousaki"], "nhip": "nen"},
    {"ma": "gia", "nhan": "Bảng giá", "specs": ["tanka"], "nhip": "nen"},
    {"ma": "no", "nhan": "Công nợ", "specs": ["seikyu_motocho"], "nhip": "ky"},
]
O_CUA = {o["ma"]: o for o in O_NAP}
O_CUA_SPEC = {s: o for o in O_NAP for s in o["specs"]}


def _ngay(x) -> date | None:
    """Ngày GIỜ TOKYO của một mốc (loaded_at là timestamptz UTC: nạp lúc 08:00
    sáng Nhật là 23:00 hôm trước theo UTC — "nạp hôm nay" phải tính giờ Nhật)."""
    if x is None:
        return None
    if isinstance(x, datetime):
        return (x.astimezone(MUI_GIO) if x.tzinfo else x).date()
    return x


def _dd(d: date | None) -> str:
    return d.strftime("%d/%m") if d else ""


def nut_nguon(status: list[dict], tuoi, hom_nay: date) -> list[dict]:
    """Mỗi ô nạp một nút: màu + một câu. 'ok' đúng nhịp · 'cho' chưa tới giờ
    13:30 · 'do' trễ — cần nạp · 'nen' dữ liệu nền / sổ theo kỳ (không có nhịp
    ngày nên không bao giờ đỏ vì "hôm nay chưa nạp")."""
    theo_spec = {s["spec"]: s for s in status}
    tuoi_spec = {n.spec: n for n in tuoi.nguon}
    ra = []
    for o in O_NAP:
        lo = [theo_spec[s] for s in o["specs"] if s in theo_spec and theo_spec[s]["last"]]
        moi = max(lo, key=lambda s: s["last"]) if lo else None
        nap_luc = _ngay(moi["last"]) if moi else None
        if o["nhip"] == "ngay" and o["specs"][0] in tuoi_spec:
            t = tuoi_spec[o["specs"][0]]
            mau, cau = {
                "xanh": ("ok", "cập nhật hôm nay"),
                "cho": ("cho", f"chưa tới 13:30 · dữ liệu đến {_dd(t.ngay)}" if t.ngay else "chưa tới 13:30"),
                "do": ("do", (f"trễ {t.tre} ngày làm việc — cần nạp" if t.tre else "chưa có hôm nay — cần nạp")
                       if t.ngay else "chưa nạp lần nào"),
                "nghi": ("nen", f"hôm nay nghỉ · dữ liệu đến {_dd(t.ngay)}" if t.ngay else "hôm nay nghỉ"),
            }[t.trang_thai]
        elif nap_luc is None:
            mau, cau = "nen", "chưa nạp lần nào"
        else:
            n = (hom_nay - nap_luc).days
            cau = ("nạp hôm nay" if n <= 0 else f"ổn định · {n} ngày trước")
            if o["nhip"] == "ky" and moi.get("data_date"):
                cau = f"sổ đến {_dd(moi['data_date'])} · " + cau
            mau = "nen"
        ra.append({"ma": o["ma"], "nhan": o["nhan"], "ja": " / ".join(SPECS[s].display_name for s in o["specs"]),
                   "spec": o["specs"][0], "nhip": o["nhip"], "mau": mau, "cau": cau,
                   "bang": SPECS[o["specs"][0]].core_table,
                   "nap_hom_nay": nap_luc == hom_nay, "nap_luc": moi["last"] if moi else None})
    return ra


def o_so(danh_muc: list[tuple], nut: list[dict]) -> list[dict]:
    """Bốn ô số của Tổng quan. `danh_muc` = (schema, tên, relkind, số dòng ước tính)
    của core/mart/meta — `reltuples` của Postgres, cập nhật sau mỗi ANALYZE, nên
    ghi "khoảng"."""
    bang_core = [(t, n) for s, t, k, n in danh_muc if s == "core" and k == "r"]
    tong = sum(max(n, 0) for _, n in bang_core)
    lon = max(bang_core, key=lambda x: x[1], default=(None, 0))
    theo_schema = {s: sum(1 for x in danh_muc if x[0] == s) for s in ("core", "mart", "meta")}
    tre = [n for n in nut if n["mau"] == "do"]
    hom_nay = [n for n in nut if n["nap_hom_nay"]]
    return [
        {"nhan": "Bảng trong kho", "gia": sum(theo_schema.values()),
         "phu": " · ".join(f"{s} {n}" for s, n in theo_schema.items()), "mau": ""},
        {"nhan": "Tổng số dòng (khoảng)", "gia": tong,
         "phu": f"lớn nhất: {lon[0]}" if lon[0] else "", "mau": ""},
        {"nhan": "Nguồn trễ lịch nạp", "gia": len(tre),
         "phu": " · ".join(n["nhan"] for n in tre) or "không nguồn nào trễ", "mau": "do" if tre else "ok"},
        {"nhan": "Loại file nạp hôm nay", "gia": len(hom_nay),
         "phu": " · ".join(n["nhan"] for n in hom_nay) or "chưa nạp gì hôm nay", "mau": ""},
    ]


def dong_cong(kq, ten_cong: dict[int, str]) -> list[dict]:
    """Năm dòng cổng kiểm của MỘT file: đạt / chặn / cảnh báo / không chạy (cổng
    trước đã chặn thì cổng sau không được chạy tới)."""
    chan = {}
    for b in kq.blockers:
        chan.setdefault(b.gate, []).append(b.message)
    canh = {}
    for w in kq.warnings:
        canh.setdefault(w.gate, []).append(w.message)
    # Cổng 1 (nhận tên file) và 2 (đủ cột) chặn thì file không được đọc tiếp;
    # cổng 3–5 chạy cùng một lượt (`gates.check`) nên chặn ở 3 vẫn có kết quả 4, 5.
    dau_chan = min(chan) if chan else None
    ra = []
    for n in sorted(ten_cong):
        if n in chan:
            tt, loi = "chan", chan[n]
        elif dau_chan in (1, 2) and n > dau_chan:
            tt, loi = "khong_chay", []
        elif n in canh:
            tt, loi = "canh", canh[n]
        else:
            tt, loi = "dat", []
        ra.append({"so": n, "ten": ten_cong[n], "trang_thai": tt, "loi": loi})
    return ra


def thang_luoi(tham_so: str | None, hom_nay: date, dau_du_lieu: date) -> tuple[date, date, dict]:
    """Tháng của lưới "Theo ngày": `?ngay_thang=YYYY-MM` (KHÔNG `?thang=` — tên đó
    là khoảng xem chung của cả website). Trả (ngày đầu, ngày cuối cắt ở hôm nay,
    điều hướng ‹ ›)."""
    dau = date(hom_nay.year, hom_nay.month, 1)
    if tham_so:
        try:
            y, m = (int(x) for x in tham_so.split("-"))
            dau = date(y, m, 1)
        except ValueError:
            pass
    dau = min(max(dau, date(dau_du_lieu.year, dau_du_lieu.month, 1)), date(hom_nay.year, hom_nay.month, 1))
    sau = date(dau.year + (dau.month == 12), dau.month % 12 + 1, 1)
    cuoi = min(sau - timedelta(days=1), hom_nay)
    truoc = date(dau.year - (dau.month == 1), (dau.month - 2) % 12 + 1, 1)
    return dau, cuoi, {
        "thang": dau.strftime("%Y-%m"),
        "truoc": truoc.strftime("%Y-%m") if truoc >= date(dau_du_lieu.year, dau_du_lieu.month, 1) else None,
        "sau": sau.strftime("%Y-%m") if sau <= hom_nay else None,
    }
