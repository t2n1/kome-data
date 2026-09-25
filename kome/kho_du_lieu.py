"""Màn Kho dữ liệu theo gói thiết kế (đợt B, 2026-09-24): Tổng quan + Nạp hai bước.

Hàm thuần — mọi truy vấn là của `kome/web/app.py::_du_lieu_kho` / `_du_lieu_nap`.
Ở đây chỉ dựng hình dạng cho giao diện: tình trạng từng nguồn (cột cuối của lưới độ
phủ, các ô nạp), năm dòng cổng kiểm.

Đặc tả: docs/superpowers/specs/2026-09-24-kho-du-lieu-theo-thiet-ke-design.md §B.
"""
from __future__ import annotations

from datetime import date, datetime

from kome.config import SPECS
from kome.nguon_dung import dung
from kome.tuoi_du_lieu import MUI_GIO, spec_cua_o

# Các ô của màn Nạp = các nhánh của sơ đồ nguồn — MỘT danh sách. `specs`: loại
# file ô đó nhận (Bán hàng nhận cả 売上伝票データ lẫn nguồn dự phòng 売上明細表 —
# cùng đổ vào core.fact_sales_line). `nhip`: 'ngay' = nhịp 13:30 hằng ngày (cùng
# bộ với kome/tuoi_du_lieu.NGUON_HANG_NGAY), 'nen' = dữ liệu nền ít đổi, 'ky' =
# sổ theo kỳ. Ô của nguồn công ty CHƯA dùng (`kome.nguon_dung.CHUA_DUNG`) không
# lên màn Nạp lẫn sơ đồ nguồn (`O_DUNG`), nhưng file loại đó vẫn nạp được qua ô
# "Nạp nhiều file" (kho tự nhận loại theo tên file).
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
O_DUNG = [o for o in O_NAP if any(dung(s) for s in o["specs"])]
MA_DUNG = {o["ma"] for o in O_DUNG}


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
    for o in O_DUNG:
        lo = [theo_spec[s] for s in o["specs"] if s in theo_spec and theo_spec[s]["last"]]
        moi = max(lo, key=lambda s: s["last"]) if lo else None
        nap_luc = _ngay(moi["last"]) if moi else None
        # Ô tuổi của ô nạp = ô nào của tuoi_du_lieu nhận MỘT trong các spec của
        # nó (ô Bán hàng: `meisai` gom cả `uriage`) — đừng đọc `specs[0]`.
        t = next((tuoi_spec[s] for s in tuoi_spec if set(spec_cua_o(s)) & set(o["specs"])), None)
        if o["nhip"] == "ngay" and t is not None:
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
