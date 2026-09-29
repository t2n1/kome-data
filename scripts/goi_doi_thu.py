"""Dựng gói bảng giá đối thủ từ các CSV đã đọc (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.1, §4.3, §7).

    python scripts/goi_doi_thu.py <thư mục CSV> --ngay 2026-08-31 --ra <thư mục ra>

Đọc mọi `spike_*.csv` (giá) và `spike_*_dieu_kien.csv` (điều kiện), ghi hai file nạp được:
doi_thu_gia_YYYYMMDD.xlsx, doi_thu_dieu_kien_YYYYMMDD.xlsx. Không chặn cả gói vì một dòng xấu:
dòng xấu mang do_chac=can_xem + lý do ở ghi_chu (cổng 5 của nguồn này, đặc tả §4.1).
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kome.loaders.doi_thu import COT_GIA, COT_DIEU_KIEN  # noqa: E402
from kome.ten_hang import chuan_ten  # noqa: E402

GIA_THAP = 20          # giá < 20 yên (một gói / một kg) gần như chắc là lỗi của nguồn
_WEB = re.compile(r"\.(jp|com|shop|asia|top)\b|Google Sheet|API", re.I)
_NGAY = [re.compile(r"(20\d\d)[.\-/](\d{1,2})[.\-/](\d{1,2})"), re.compile(r"(20\d\d)(\d\d)(\d\d)")]
_ID_BEN = re.compile(r"(?<![A-Za-z])(?:_id|id|mã SP|商品コード)\s*[:=]?\s*([A-Za-z0-9\-]{4,})")


def jan_hop_le(s: str) -> bool:
    s = (s or "").strip()
    if not re.fullmatch(r"\d{13}", s):
        return False
    tong = sum(int(c) * (3 if i % 2 else 1) for i, c in enumerate(s[:12]))
    return (10 - tong % 10) % 10 == int(s[12])


def ma_hang_dt(d: dict, jan_dung_duoc: bool = True) -> str:
    jan = (d.get("jan") or "").strip()
    if jan_dung_duoc and jan_hop_le(jan):
        return "jan:" + jan
    m = _ID_BEN.search(d.get("vi_tri") or "")
    if m:
        return "id:" + m.group(1)
    return "ten:" + chuan_ten(d.get("ten_goc", "")) + "|" + chuan_ten(d.get("quy_cach_goc", ""))


def suy_ngay(file: str, mac_dinh: date) -> date:
    for p in _NGAY:
        m = p.search(file or "")
        if m:
            try:
                return date(int(m[1]), int(m[2]), int(m[3]))
            except ValueError:
                pass
    return mac_dinh


def suy_trang_thai(d: dict) -> str:
    ghi = (d.get("ghi_chu") or "") + " " + (d.get("khuyen_mai") or "")
    if re.search(r"dự kiến|入荷予定|sắp về", ghi, re.I):
        return "sap_ve"
    t = d.get("trang_thai") or "khong_ro"
    return t if t in ("con", "het", "sap_ve", "khong_ro") else "khong_ro"


def suy_muc_gia(d: dict) -> str | None:
    if d.get("muc_gia"):
        return d["muc_gia"]
    ghi = (d.get("ghi_chu") or "").lower()
    if "special" in ghi or "đặc biệt" in ghi:
        return "dac_biet"
    if "pallet" in ghi:
        return "pallet"
    if "khách ngoài" in ghi or "ngoài vietcook" in ghi:
        return "khach_ngoai"
    if "kyushu" in ghi:
        return "kyushu"
    return None


def _so(v):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None


def dung_goi(gia: list[dict], dk: list[dict], ngay: date) -> tuple[list[dict], list[dict], list[str]]:
    canh: list[str] = []
    # 1. Gộp cặp chưa thuế / có thuế của CÙNG một ô (IMAI in cả hai cột): giữ dòng chưa thuế.
    nhom: dict[tuple, list[dict]] = {}
    for d in gia:
        nhom.setdefault((d.get("ben"), d.get("vi_tri"), d.get("ten_goc"), d.get("jan"), d.get("kenh_gia")), []).append(d)
    bo: set[int] = set()
    for ds in nhom.values():
        chua = [d for d in ds if d.get("thue") == "chua"]
        co = [d for d in ds if d.get("thue") == "co"]
        if len(chua) >= 1 and len(co) >= 1:
            chua[0]["ghi_chu"] = ((chua[0].get("ghi_chu") or "") + f" · 税込 ¥{co[0].get('gia_goc')}").strip(" ·")
            bo.update(id(x) for x in co)
    gia = [d for d in gia if id(d) not in bo]
    # 2. Bỏ dòng trùng y hệt (ảnh gửi trùng trang).
    thay, sach = set(), []
    for d in gia:
        k = (d.get("ben"), d.get("ten_goc"), d.get("quy_cach_goc"), d.get("gia_goc"), d.get("kenh_gia"),
             suy_muc_gia(d), d.get("don_vi_gia"))
        if k not in thay:
            thay.add(k)
            sach.append(d)
    # 3. JAN dùng làm khoá chỉ khi không trùng hai tên trong cùng bên.
    ten_cua_jan: dict[tuple, set] = {}
    for d in sach:
        if jan_hop_le(d.get("jan") or ""):
            ten_cua_jan.setdefault((d["ben"], d["jan"]), set()).add(chuan_ten(d.get("ten_goc", "")))
    ra, dem = [], {}
    for d in sach:
        ben = d["ben"]
        dem[ben] = dem.get(ben, 0) + 1
        ly_do = []
        jan = (d.get("jan") or "").strip()
        jan_ok = jan_hop_le(jan) and len(ten_cua_jan.get((ben, jan), ())) == 1
        if jan and not jan_hop_le(jan):
            ly_do.append(f"JAN {jan} sai chữ số kiểm")
        elif jan and not jan_ok:
            ly_do.append(f"JAN {jan} trùng nhiều mã cùng bên")
        g = _so(d.get("gia_goc"))
        if g is not None and g < GIA_THAP:
            ly_do.append(f"giá {d.get('gia_goc')} bất thường (< {GIA_THAP})")
        do_chac = "can_xem" if ly_do or d.get("do_chac") == "can_xem" else "chac"
        ghi = " · ".join(x for x in [d.get("ghi_chu") or "", *ly_do] if x)
        if ly_do:
            canh.append(f"{ben} {d.get('vi_tri')}: {'; '.join(ly_do)}")
        file = d.get("file") or ""
        o = {
            "ma_dong": f"{ben}-{dem[ben]:05d}", "ma_doi_thu": ben, "ma_hang_dt": ma_hang_dt(d, jan_ok),
            "ngay_nguon": suy_ngay(file, ngay).isoformat(), "hinh_thuc_nguon": "web" if _WEB.search(file) else "file",
            "nguon_file": file, "vi_tri": d.get("vi_tri"), "ten_goc": d.get("ten_goc"), "ten_nhat": d.get("ten_nhat"),
            "jan": jan or None, "quy_cach_goc": d.get("quy_cach_goc"), "gia_goc": d.get("gia_goc") or None,
            "don_vi_gia": d.get("don_vi_gia"), "kg_moi_don_vi_gia": d.get("kg_moi_don_vi_gia") or None,
            "thue": d.get("thue") or "khong_ro", "gom_ship": d.get("gom_ship") or "khong_ro",
            "kenh_gia": d.get("kenh_gia") or None, "muc_gia": suy_muc_gia(d), "gia_bac": d.get("gia_bac"),
            "gia_truoc_km": d.get("gia_truoc_km") or None, "trang_thai": suy_trang_thai(d),
            "han_su_dung": d.get("han_su_dung"), "khuyen_mai": d.get("khuyen_mai"),
            "ma_kome_de_xuat": d.get("ma_kome") or None,
            "nhan_de_xuat": d.get("nhan_ghep") if d.get("nhan_ghep") in ("cung_hang", "thay_the") else None,
            "ly_do_ghep": d.get("ly_do_ghep"), "do_chac": do_chac, "ghi_chu": ghi or None,
        }
        ra.append({c: o[c] for c in COT_GIA})
    dk_ra, dem_dk = [], {}
    for d in dk:
        ben = d["ben"]
        dem_dk[ben] = dem_dk.get(ben, 0) + 1
        loai = d.get("loai") if d.get("loai") in ("ship", "khuyen_mai", "thanh_toan", "thue", "khac") else "khac"
        dk_ra.append({"ma_dong": f"{ben}-{dem_dk[ben]:05d}", "ma_doi_thu": ben,
                      "ngay_nguon": suy_ngay(d.get("file") or "", ngay).isoformat(),
                      "nguon_file": d.get("file"), "vi_tri": d.get("vi_tri"), "loai": loai,
                      "noi_dung": d.get("noi_dung")})
    return ra, [x for x in dk_ra if (x["noi_dung"] or "").strip()], canh


def _doc(p: Path) -> list[dict]:
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("thu_muc", type=Path)
    ap.add_argument("--ngay", type=date.fromisoformat, required=True)
    ap.add_argument("--ra", type=Path, required=True)
    a = ap.parse_args()
    gia, dk = [], []
    for p in sorted(a.thu_muc.glob("spike_*.csv")):
        (dk if p.stem.endswith("_dieu_kien") else gia).extend(_doc(p))
    g, d, canh = dung_goi(gia, dk, a.ngay)
    a.ra.mkdir(parents=True, exist_ok=True)
    s = a.ngay.strftime("%Y%m%d")
    pd.DataFrame(g, columns=COT_GIA).to_excel(a.ra / f"doi_thu_gia_{s}.xlsx", sheet_name="gia", index=False)
    pd.DataFrame(d, columns=COT_DIEU_KIEN).to_excel(a.ra / f"doi_thu_dieu_kien_{s}.xlsx", sheet_name="dieu_kien", index=False)
    print(f"{len(g)} dòng giá · {len(d)} điều kiện · {len(canh)} cảnh báo")
    for c in canh[:50]:
        print("  ", c)


if __name__ == "__main__":
    main()
