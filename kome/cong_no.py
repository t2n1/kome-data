"""Công nợ & thu tiền (đợt 6) — đọc `mart.cong_no_ben_tra` + `mart.cong_no_phieu`
(migration 038). Module này KHÔNG định nghĩa chỉ số: số dư là cột 残高 của OBC,
phần còn nợ từng phiếu là phép chia "trả cũ trước" của view, hạn trả là phép suy
của view. Ở đây chỉ CỘNG các dòng view trả về, cho ô tổng và câu gợi ý.

Mốc của mọi con số là **cuối kỳ của lô sổ công nợ mới nhất** (`moc`), không phải
hôm nay — sổ nạp theo quý, nên màn hình phải luôn in "tính đến ngày nào".
"""
from __future__ import annotations

# Câu in NGUYÊN VĂN dưới các khối — cách tính phải nói được bằng một câu.
CACH_TINH = {
    "so_du": "Số dư là cột 残高 của sổ 請求先元帳 (OBC) ở dòng cuối của từng bên nhận hoá đơn.",
    "fifo": ("OBC không ghi phiếu nào đã được trả. Phần còn nợ chia vào phiếu theo giả định "
             "TRẢ CŨ TRƯỚC: số dư là của các phiếu mới nhất; phần lớn hơn tổng phiếu trong kỳ "
             "là nợ mang sang từ trước kỳ."),
    "tuoi": "Tuổi nợ đếm từ ngày phiếu tới cuối kỳ sổ.",
    "han": ("Hạn trả suy từ tên điều kiện thanh toán, chỉ hai mẫu: 末締/翌月末日 (chốt cuối tháng, "
            "trả cuối tháng sau) và 末締/翌月N日 (trả ngày N tháng sau). 代引請求 / その都度請求 / "
            "前払い … không suy được hạn nên KHÔNG tính là quá hạn."),
    "da_thu": "Đã thu trong kỳ = mang sang + bán chịu − số dư (phần tiền thu thật sự làm giảm nợ).",
}

NHOM_TUOI = [("d30", "0–30 ngày"), ("d60", "31–60 ngày"), ("d90", "61–90 ngày"),
             ("d90p", "Trên 90 ngày"), ("truoc_ky", "Mang sang từ trước kỳ")]
SAP_DEN_HAN = 7   # ngày — "đến hạn trong 7 ngày tới" tính từ mốc


def _ben(conn, ma: str | None = None) -> list[dict]:
    rows = conn.execute(
        f"""SELECT b.billing_customer_code, b.ten, b.dieu_kien, b.so_du, b.mang_sang,
                   b.ban_chiu_ky, b.da_thu_ky, b.lan_thu_cuoi, b.lan_ban_cuoi, b.so_khach,
                   b.salesperson_code, s.ten, b.ky_tu, b.ky_den
              FROM mart.cong_no_ben_tra b
              LEFT JOIN core.dim_salesperson s ON s.salesperson_code = b.salesperson_code
             WHERE {"b.billing_customer_code = %s" if ma else
                    "(b.so_du <> 0 OR b.ban_chiu_ky <> 0 OR b.da_thu_ky <> 0)"}
             ORDER BY b.so_du DESC, b.billing_customer_code""",
        (ma,) if ma else ()).fetchall()
    return [{"ma": r[0], "ten": r[1], "dieu_kien": r[2], "so_du": int(r[3]),
             "mang_sang": int(r[4]), "ban_chiu": int(r[5]), "da_thu": int(r[6]),
             "lan_thu_cuoi": r[7], "lan_ban_cuoi": r[8], "so_khach": int(r[9] or 0),
             "sale": r[10], "ten_sale": r[11], "ky_tu": r[12], "ky_den": r[13]} for r in rows]


def _phieu(conn, ma: str | None = None) -> list[dict]:
    rows = conn.execute(
        f"""SELECT billing_customer_code, loai, slip_no, entry_date, tong, con_lai, da_thu,
                   han_tra, tuoi_ngay, qua_han_ngay, nhom_tuoi
              FROM mart.cong_no_phieu
             {"WHERE billing_customer_code = %s" if ma else ""}
             ORDER BY qua_han_ngay DESC NULLS LAST, entry_date NULLS FIRST, slip_no""",
        (ma,) if ma else ()).fetchall()
    return [{"ma": r[0], "loai": r[1], "so": r[2], "ngay": r[3],
             "tong": None if r[4] is None else int(r[4]), "con_lai": int(r[5]),
             "da_thu": None if r[6] is None else int(r[6]), "han": r[7],
             "tuoi": r[8], "qua_han": r[9], "nhom": r[10]} for r in rows]


def tong_hop(ben: list[dict], phieu: list[dict]) -> dict:
    """Các ô tổng — CHỈ cộng dòng view trả về."""
    no = [b for b in ben if b["so_du"] > 0]
    du = [b for b in ben if b["so_du"] < 0]
    qh = [p for p in phieu if p["qua_han"] is not None and p["qua_han"] > 0]
    sap = [p for p in phieu if p["qua_han"] is not None and -SAP_DEN_HAN <= p["qua_han"] <= 0]
    khong_han = [p for p in phieu if p["qua_han"] is None]
    tuoi = {k: {"tien": 0, "dem": 0} for k, _ in NHOM_TUOI}
    for p in phieu:
        t = tuoi[p["nhom"]]
        t["tien"] += p["con_lai"]
        t["dem"] += 1 if p["loai"] == "phieu" else 0
    return {
        "tong_phai_thu": sum(b["so_du"] for b in no), "so_ben_no": len(no),
        "qua_han": sum(p["con_lai"] for p in qh), "so_phieu_qua_han": len(qh),
        "so_ben_qua_han": len({p["ma"] for p in qh}),
        "sap_den_han": sum(p["con_lai"] for p in sap), "so_phieu_sap": len(sap),
        "khong_suy_han": sum(p["con_lai"] for p in khong_han),
        "da_thu_ky": sum(b["da_thu"] for b in ben), "ban_chiu_ky": sum(b["ban_chiu"] for b in ben),
        "tra_du": sum(b["so_du"] for b in du), "so_ben_tra_du": len(du),
        "tuoi": [{"nhom": k, "nhan": n, **tuoi[k]} for k, n in NHOM_TUOI],
    }


def _yen(n: int) -> str:
    return "¥" + f"{n:,}".replace(",", ".")


def _viec(ben: list[dict], phieu: list[dict], tq: dict) -> list[str]:
    """Câu gợi ý — mỗi câu đọc thẳng từ số trên màn, không phán đoán thêm."""
    out = []
    theo_ben: dict[str, int] = {}
    for p in phieu:
        if p["qua_han"] is not None and p["qua_han"] > 0:
            theo_ben[p["ma"]] = theo_ben.get(p["ma"], 0) + p["con_lai"]
    ten = {b["ma"]: b["ten"] for b in ben}
    if theo_ben:
        ma, tien = max(theo_ben.items(), key=lambda x: x[1])
        lau = max(p["qua_han"] for p in phieu if p["ma"] == ma and p["qua_han"])
        out.append(f"Quá hạn nhiều nhất: {ten.get(ma, ma)} — {_yen(tien)} ({lau} ngày ở phiếu cũ nhất).")
    if tq["tong_phai_thu"] and ben and ben[0]["so_du"] > 0:
        b = ben[0]
        pc = round(b["so_du"] / tq["tong_phai_thu"] * 100)
        if pc >= 30:
            out.append(f"{b['ten']} ({b['dieu_kien'] or 'không rõ điều kiện'}) chiếm {pc}% tổng phải thu"
                       f" — đối chiếu riêng bên này.")
    if tq["so_ben_tra_du"]:
        out.append(f"{tq['so_ben_tra_du']} bên đang trả dư (số dư âm, tổng {_yen(-tq['tra_du'])})"
                   f" — kiểm tra có cần hoàn tiền hay trừ vào đơn sau.")
    return out


def man_hinh(conn) -> dict:
    """Màn /cong-no: MỘT ảnh chụp, 2 lượt hỏi. Lọc / tìm ở trình duyệt."""
    ben = _ben(conn)
    phieu = _phieu(conn)
    moc = next((b["ky_den"] for b in ben), None)
    tu = next((b["ky_tu"] for b in ben), None)
    tq = tong_hop(ben, phieu)
    return {"co_du_lieu": bool(ben), "ky_tu": tu, "moc": moc, "tq": tq, "ben": ben,
            "phieu": phieu, "viec": _viec(ben, phieu, tq), "cach_tinh": CACH_TINH,
            "sap_den_han_ngay": SAP_DEN_HAN}


def cua_khach(conn, ma: str) -> dict:
    """Tab Công nợ của hồ sơ khách: bên nhận hoá đơn của khách + phiếu của bên đó.
    ≤ 3 lượt hỏi. Công nợ ghi theo 請求先, nên khách dùng chung bên (vd. 代引専用)
    thấy số của CẢ bên — màn nói rõ điều đó bằng `so_khach`."""
    r = conn.execute(
        "SELECT billing_customer_code FROM core.dim_customer WHERE customer_code = %s AND is_current",
        (ma,)).fetchone()
    ben_ma = (r[0] if r and r[0] else ma)
    ben = _ben(conn, ben_ma)
    if not ben:
        # Có sổ nào TỚI MỐC đang xem không (040: sổ có kỳ kết thúc ≤ mốc).
        co = conn.execute("SELECT EXISTS (SELECT 1 FROM mart.so_cong_no_moi_nhat)").fetchone()[0]
        return {"co_so": bool(co), "ben": None, "ben_ma": ben_ma, "phieu": [], "tq": None,
                "cach_tinh": CACH_TINH}
    phieu = _phieu(conn, ben_ma)
    return {"co_so": True, "ben": ben[0], "ben_ma": ben_ma, "la_chinh": ben_ma == ma,
            "phieu": phieu[:60], "so_phieu": len(phieu), "tq": tong_hop(ben, phieu),
            "cach_tinh": CACH_TINH}


def khoi_tong_quan(conn, sale=None) -> dict | None:
    """Khối "Tuổi nợ phải thu" của trang `/`: 2 lượt hỏi (như màn chính)."""
    m = man_hinh(conn)
    if not m["co_du_lieu"]:
        return None
    theo_ben: dict[str, int] = {}
    for p in m["phieu"]:
        if p["nhom"] in ("d90p", "truoc_ky") or (p["qua_han"] or 0) > 0:
            theo_ben[p["ma"]] = theo_ben.get(p["ma"], 0) + p["con_lai"]
    ten = {b["ma"]: b["ten"] for b in m["ben"]}
    lau = sorted(theo_ben.items(), key=lambda x: -x[1])[:4]
    return {"moc": m["moc"], "tq": m["tq"],
            "lau_nhat": [{"ma": a, "ten": ten.get(a, a), "tien": t} for a, t in lau],
            "cach_tinh": CACH_TINH["tuoi"]}

