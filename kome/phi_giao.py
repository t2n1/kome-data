"""Phí khách trả THÊM cho một đơn mẫu theo điều kiện giao hàng của một bên (đặc tả giao diện mới §5.4).

MỘT thuật toán, hai bản: file này và giao_dien/src/doi_thu/phi_giao.ts — cả hai chạy tests/du_lieu/phi_giao_ca.json;
sửa một bản là sửa cả hai. Trường NULL mà cần tới → vào `chua_ro`, KHÔNG cộng 0 lặng lẽ. Không đoán phí.
"""
import math

VUNG_GOC = ("kanto", "chubu", "kansai")     # vùng không phụ thu khi bên đó không ghi


def _so(v):
    return None if v is None else float(v)


def tinh(dk: dict, don: dict) -> dict:
    tien, thung, vung, tra = float(don["tien"]), float(don["thung"]), don["vung"], don["tra"]
    ra = {"ship": 0, "vung": 0, "daibiki": 0, "chua_ro": [], "khong_nhan": False}
    tmk = dk.get("thung_moi_kien")
    kien = math.ceil(thung / tmk) if tmk else 1
    mien = (dk.get("mien_ship_tu") is not None and tien >= float(dk["mien_ship_tu"])) or \
           (dk.get("mien_ship_kien") is not None and thung >= dk["mien_ship_kien"] * (tmk or 1))
    if not dk.get("bao_ship") and not mien:
        if dk.get("phi_ship") is None:
            ra["chua_ro"].append("ship")
        else:
            he = {"thung": thung, "kien": kien}.get(dk.get("phi_ship_theo"), 1)
            ra["ship"] = _so(dk["phi_ship"]) * he
    if vung not in VUNG_GOC:
        pp = dk.get("phu_phi")
        if pp is None:
            ra["chua_ro"].append("vùng")
        elif pp.get(vung) == "khong_nhan":
            ra["khong_nhan"] = True
        elif pp.get(vung) is not None:
            ra["vung"] = float(pp[vung]) * kien
    if tra == "daibiki":
        if dk.get("daibiki_tu") is not None and tien >= float(dk["daibiki_tu"]):
            if dk.get("daibiki_sau") is None:          # tới ngưỡng mà không ghi phí sau ngưỡng: chưa rõ, KHÔNG phải miễn
                ra["chua_ro"].append("daibiki")
            else:
                ra["daibiki"] = _so(dk["daibiki_sau"])
        elif dk.get("phi_daibiki") is None:
            ra["chua_ro"].append("daibiki")
        else:
            ra["daibiki"] = _so(dk["phi_daibiki"])
    for k in ("ship", "vung", "daibiki"):          # số nguyên yên khi tròn — so khớp JSON của bản TS
        if float(ra[k]).is_integer():
            ra[k] = int(ra[k])
    return ra
