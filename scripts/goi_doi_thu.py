"""Dựng gói bảng giá đối thủ từ các CSV đã đọc (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.1, §4.3, §7).

    python scripts/goi_doi_thu.py <thư mục CSV> --ngay 2026-08-31 --ra <thư mục ra>

Đọc mọi `spike_*.csv` (giá), `spike_*_dieu_kien.csv` (điều kiện) và `spike_*_giao_hang.csv` (giao hàng),
ghi các file nạp được: doi_thu_gia_YYYYMMDD.xlsx, doi_thu_dieu_kien_YYYYMMDD.xlsx và (khi có dòng)
doi_thu_giao_hang_YYYYMMDD.xlsx. Không chặn cả gói vì một dòng xấu:
dòng xấu mang do_chac=can_xem + lý do ở ghi_chu (cổng 5 của nguồn này, đặc tả §4.1).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kome.loaders.doi_thu import COT_GIA, COT_DIEU_KIEN, COT_GIAO_HANG  # noqa: E402
from kome.ten_hang import chuan_ten  # noqa: E402

GIA_THAP = 20          # giá < 20 yên (một gói / một kg) gần như chắc là lỗi của nguồn
_WEB = re.compile(r"\.(jp|com|shop|asia|top)\b|\bGoogle Sheet\b|\bAPI\b")
_NGAY = [re.compile(r"(20\d\d)[.\-/](\d{1,2})[.\-/](\d{1,2})"), re.compile(r"(20\d\d)(\d\d)(\d\d)")]
_ID_BEN = re.compile(r"(?<![A-Za-z])(?:_id|id|mã SP|商品コード)\s*[:=]?\s*([A-Za-z0-9\-]{4,})")
DON_VI_SL = ("thung", "kg", "goi", "pallet")
DON_VI_GIA_BAC = ("thung", "kg", "goi")
BAC_TOI_DA = 10
KL_GOI_G_TOI_DA = 30000          # CHECK 065: kl_goi_g in (0, 30000]
_CO = {"yes", "true", "1", "co", "có"}
_KHONG = {"no", "false", "0", "khong", "không"}
# Câu người ĐỌC tự ghi (không phải điều kiện của bên) — tháng 8 lọt vào dieu_kien (VIETCOOK, HSC, JVB, EIHATSU, THAK).
_GHI_CHU_DOC = re.compile(r"chép vào|ghi_chu|không in (phí|thông tin)|không tìm thấy|dữ liệu này|trên các trang đã đọc"
                          r"|in ở từng ô|mỗi (ô|mặt hàng) (ghi|in)|— không chép", re.I)
_VUNG = ("hokkaido", "tohoku", "kanto", "chubu", "kansai", "chugoku", "shikoku", "kyushu", "okinawa")


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
    t = d.get("trang_thai") or "khong_ro"
    t = t if t in ("con", "het", "sap_ve", "khong_ro") else "khong_ro"
    # Only return "sap_ve" if status is het, khong_ro, or empty (not if con)
    if t in ("het", "khong_ro"):
        ghi = (d.get("ghi_chu") or "") + " " + (d.get("khuyen_mai") or "")
        if re.search(r"dự kiến|入荷予定|sắp về", ghi, re.I):
            return "sap_ve"
    return t


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
        x = float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None      # NaN / inf không bao giờ là số hợp lệ


def la_ghi_chu_doc(noi_dung: str) -> bool:
    return bool(_GHI_CHU_DOC.search(noi_dung or ""))


def kiem_bac(s) -> tuple[list[dict] | None, str | None]:
    """Chữ JSON của cột `bac` → danh sách bậc chuẩn hoá (lược đồ 065) hoặc (None, lý do). Trống → (None, None)."""
    if s is None or str(s).strip() == "":
        return None, None
    try:
        v = json.loads(s)
    except (TypeError, ValueError):
        return None, f"bac không phải JSON: {str(s)[:40]}"
    if not isinstance(v, list) or not 1 <= len(v) <= BAC_TOI_DA:
        return None, f"bac phải là mảng 1–{BAC_TOI_DA} bậc"
    ra = []
    for b in v:
        if not isinstance(b, dict):
            return None, "mỗi bậc phải là object"
        tu, gia = _so(b.get("tu")), _so(b.get("gia"))
        if not tu or tu <= 0 or not gia or gia <= 0:
            return None, "bậc cần tu > 0 và gia > 0"
        if b.get("don_vi_sl") not in DON_VI_SL or b.get("don_vi_gia") not in DON_VI_GIA_BAC:
            return None, f"đơn vị bậc phải thuộc {DON_VI_SL} / {DON_VI_GIA_BAC}"
        ra.append({"tu": int(tu) if tu == int(tu) else tu, "don_vi_sl": b["don_vi_sl"],
                   "gia": int(gia) if gia == int(gia) else gia, "don_vi_gia": b["don_vi_gia"]})
    return ra, None


def _nguyen(v):
    x = _so(v)
    return int(x) if x is not None and x == int(x) and x > 0 else None


def _bool(v, ten: str, ben: str, canh: list[str]) -> str | None:
    """Cột đúng/sai → "true"/"false" cho bộ nạp (chỉ nhận true/1/co · false/0/khong); lạ → None + cảnh báo."""
    t = str(v or "").strip().lower()
    if not t:
        return None
    if t in _CO:
        return "true"
    if t in _KHONG:
        return "false"
    canh.append(f"{ben} giao hàng: {ten} = {str(v)[:20]!r} không phải đúng/sai")
    return None


def _khong_am(v, ten: str, ben: str, canh: list[str], *, duong: bool = False) -> float | None:
    """Số >= 0 (hoặc > 0 khi duong) theo CHECK 065; ngoài khoảng → None + cảnh báo."""
    x = _so(v)
    if x is None:
        return None
    if x < 0 or (duong and x == 0):
        canh.append(f"{ben} giao hàng: {ten} = {v} ngoài khoảng ({'> 0' if duong else '>= 0'})")
        return None
    return x


def _phu_phi(s) -> tuple[str | None, str | None]:
    if s is None or str(s).strip() == "":
        return None, None
    try:
        v = json.loads(s)
    except (TypeError, ValueError):
        return None, "phu_phi không phải JSON"
    if not isinstance(v, dict) or any(k not in _VUNG for k in v) or \
            any(not (x == "khong_nhan" or (isinstance(x, (int, float)) and not isinstance(x, bool) and x >= 0))
                for x in v.values()):
        return None, 'phu_phi: {"<vùng>": ¥ hoặc "khong_nhan"}, vùng thuộc ' + "/".join(_VUNG)
    return json.dumps(v, ensure_ascii=False), None


def dung_goi(gia: list[dict], dk: list[dict], ngay: date, giao: list[dict] | None = None
             ) -> tuple[list[dict], list[dict], list[dict], list[str]]:
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
        bac, loi_bac = kiem_bac(d.get("bac"))
        if loi_bac:
            ly_do.append(loi_bac)
        kl = _so(d.get("kl_goi_g"))
        if kl is not None and kl > KL_GOI_G_TOI_DA:
            ly_do.append(f"kl_goi_g {d.get('kl_goi_g')} > {KL_GOI_G_TOI_DA} g (nhầm đơn vị?)")
            kl = None
        if bac and g is not None:
            cung_dv = [b["gia"] for b in bac if b["don_vi_gia"] == (d.get("don_vi_gia") or "")]
            if cung_dv and max(cung_dv) > g:
                ly_do.append("gia_goc phải là giá lẻ (bậc mua ít nhất), không phải bậc rẻ nhất")
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
            "so_goi_thung": _nguyen(d.get("so_goi_thung")),
            "kl_goi_g": kl if (kl or 0) > 0 else None,
            "bac": json.dumps(bac, ensure_ascii=False) if bac else None,
        }
        ra.append({c: o[c] for c in COT_GIA})
    dk_ra, dem_dk = [], {}
    for d in dk:
        ben = d["ben"]
        dem_dk[ben] = dem_dk.get(ben, 0) + 1
        loai = d.get("loai") if d.get("loai") in ("ship", "khuyen_mai", "thanh_toan", "thue", "khac") else "khac"
        if la_ghi_chu_doc(d.get("noi_dung")):
            loai = "ghi_chu_doc"
        dk_ra.append({"ma_dong": f"{ben}-{dem_dk[ben]:05d}", "ma_doi_thu": ben,
                      "ngay_nguon": suy_ngay(d.get("file") or "", ngay).isoformat(),
                      "nguon_file": d.get("file"), "vi_tri": d.get("vi_tri"), "loai": loai,
                      "noi_dung": d.get("noi_dung")})
    gh_ra, dem_gh = [], {}
    for d in giao or []:
        ben = d["ben"]
        dem_gh[ben] = dem_gh.get(ben, 0) + 1
        pp, loi = _phu_phi(d.get("phu_phi"))
        if loi:
            canh.append(f"{ben} giao hàng: {loi}")
        theo = d.get("phi_ship_theo") if d.get("phi_ship_theo") in ("don", "thung", "kien") else None
        thue = d.get("thue") if d.get("thue") in ("bao", "chua", "khong_ro") else None
        gh_ra.append({
            "ma_dong": f"{ben}-{dem_gh[ben]:05d}", "ma_doi_thu": ben,
            "ngay_nguon": suy_ngay(d.get("file") or "", ngay).isoformat(),
            "bao_ship": _bool(d.get("bao_ship"), "bao_ship", ben, canh),
            "phi_ship": _khong_am(d.get("phi_ship"), "phi_ship", ben, canh), "phi_ship_theo": theo,
            "mien_ship_tu": _khong_am(d.get("mien_ship_tu"), "mien_ship_tu", ben, canh), "mien_ship_kien": _nguyen(d.get("mien_ship_kien")),
            "thung_moi_kien": _nguyen(d.get("thung_moi_kien")), "phu_phi": pp, "phi_daibiki": _khong_am(d.get("phi_daibiki"), "phi_daibiki", ben, canh),
            "daibiki_tu": _khong_am(d.get("daibiki_tu"), "daibiki_tu", ben, canh),
            "daibiki_sau": _khong_am(d.get("daibiki_sau"), "daibiki_sau", ben, canh),
            "ck_mien_daibiki": _bool(d.get("ck_mien_daibiki"), "ck_mien_daibiki", ben, canh),
            "kien_toi_da_kg": _khong_am(d.get("kien_toi_da_kg"), "kien_toi_da_kg", ben, canh, duong=True),
            "ghep_kien": d.get("ghep_kien") or None, "thue": thue, "cach_gui": d.get("cach_gui") or None,
            "nguon_chu": d.get("nguon_chu") or None, "nguon_file": d.get("file") or None,
        })
    return ra, [x for x in dk_ra if (x["noi_dung"] or "").strip()], gh_ra, canh


def _doc(p: Path) -> list[dict]:
    with open(p, encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def main() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    import pandas as pd
    ap = argparse.ArgumentParser()
    ap.add_argument("thu_muc", type=Path)
    ap.add_argument("--ngay", type=date.fromisoformat, required=True)
    ap.add_argument("--ra", type=Path, required=True)
    a = ap.parse_args()
    gia, dk, giao = [], [], []
    for p in sorted(a.thu_muc.glob("spike_*.csv")):
        (dk if p.stem.endswith("_dieu_kien") else giao if p.stem.endswith("_giao_hang") else gia).extend(_doc(p))
    g, d, gh, canh = dung_goi(gia, dk, a.ngay, giao)
    a.ra.mkdir(parents=True, exist_ok=True)
    s = a.ngay.strftime("%Y%m%d")
    pd.DataFrame(g, columns=COT_GIA).to_excel(a.ra / f"doi_thu_gia_{s}.xlsx", sheet_name="gia", index=False)
    pd.DataFrame(d, columns=COT_DIEU_KIEN).to_excel(a.ra / f"doi_thu_dieu_kien_{s}.xlsx", sheet_name="dieu_kien", index=False)
    if gh:
        pd.DataFrame(gh, columns=COT_GIAO_HANG).to_excel(a.ra / f"doi_thu_giao_hang_{s}.xlsx", sheet_name="giao_hang", index=False)
    print(f"{len(g)} dòng giá · {len(d)} điều kiện · {len(gh)} giao hàng · {len(canh)} cảnh báo")
    for c in canh[:50]:
        print("  ", c)


if __name__ == "__main__":
    main()
