"""Dữ liệu từng KHỐI của trang Tổng quan (giao diện React, Dashboard.dc.html).

Mỗi khối một hàm `(conn, sale) -> dict` chuyển được sang JSON. Giao diện gọi
`/api/tong-quan/<khối>` RIÊNG cho từng khối đang hiện — khối ẩn không tốn truy
vấn nào. Kết quả đi qua ảnh chụp theo phiên bản dữ liệu (kome/web/anh_chup.py).

Module này KHÔNG định nghĩa chỉ số mới: mọi con số đọc từ view `mart` hoặc gọi
lại hàm đã có (`kome.tong_quan`, `kome.bao_cao.tien_do_ngan_sach`,
`kome.khach_hang.dem_va_can_xu_ly`, `kome.san_pham.lo_can_han`,
`kome.lien_he`, `kome.nhat_ky_nap`). Tỷ suất luôn là TỶ SỐ CỦA CÁC TỔNG
(CLAUDE.md). Khối số tổng KHÔNG lọc theo người đăng nhập; chỉ các khối "việc
của tôi" (`viec_hom_nay`, danh sách cần gọi) nhận `sale`.

Khối của gói thiết kế KHÔNG có nguồn (dòng tiền, mua hàng, khiếu nại,
hàng sắp về, thời tiết, tỷ lệ im lặng theo tuần) không có hàm ở đây — giao diện
vẽ khung "chưa có dữ liệu" và nói rõ thiếu nguồn nào (`CHUA_CO`).
"""
from __future__ import annotations

from dataclasses import asdict
from datetime import date

from kome import ban_khoang as BK
from kome import khach_hang as KH
from kome import khoang_xem as KX
from kome import san_pham as SP
from kome import tong_quan as TQ
from kome.bao_cao import tien_do_ngan_sach
from kome.tuoi_du_lieu import hom_nay_o_nhat, tinh_tuoi

# Khối không có nguồn dữ liệu thật -> câu giải thích hiện trong khung khối.
CHUA_CO = {
    "dong_tien": "Cần số dư ngân hàng, chi phí và phải trả — chưa có nguồn nào.",
    "mua_hang": "Cần dữ liệu đơn đặt nhà cung cấp (発注) — OBC chưa xuất đều đặn.",
    "khieu_nai": "Cần sổ trả hàng & khiếu nại — chưa có nơi ghi.",
    "hang_sap_ve": "Cần lịch hàng về (container / 発注残) — chưa có nguồn.",
    "thoi_tiet": "Cần nguồn dự báo thời tiết bên ngoài — chưa được duyệt.",
    "nhip_mua": "Cần lưu trạng thái khách theo từng tuần — hiện chỉ có trạng thái hôm nay.",
}


def _ty_so(tu, mau):
    return (tu / mau) if (tu is not None and mau) else None


def _kx(conn, ts):
    """Khoảng xem của khối (đặc tả khoảng xem §3.1). `ts` None = tháng hiện
    tại. +1 lượt hỏi (`pham_vi`). None = kho chưa có dòng bán nào."""
    return KX.giai_conn(conn, ts or KX.ThamSo())


def _ns_theo_khoang(conn, kx):
    """Ngân sách của khoảng: dạng Tháng = tháng đang xem; dạng Kỳ = như màn
    Báo cáo theo kỳ; dạng Khoảng = không có (chỉ tiêu chỉ đặt theo tháng)."""
    if kx is None or kx.loai == "khoang":
        return None
    return tien_do_ngan_sach(conn, kx.company_fy, kx.thang if kx.loai == "thang" else None)


def _so_sanh_json(ss) -> list[dict]:
    return [{"ma": s.ma, "nhan": s.nhan, "co": s.co, "tu": s.tu, "den": s.den,
             "dt": s.dt, "dt_ck": s.dt_ck, "tang": s.tang_dt, "lg": s.lg, "lg_ck": s.lg_ck,
             "tang_lg": s.tang_lg, "so_khach": s.so_khach, "so_khach_ck": s.so_khach_ck,
             "tang_khach": s.tang_khach} for s in ss]


# ---- Chỉ số hôm nay (6 ô) ---------------------------------------------------

def kpi(conn, sale=None, ts=None) -> dict:
    """Ô doanh thu + ngân sách theo KHOẢNG XEM; ô kho và ô khách tính đến hôm nay."""
    kx = _kx(conn, ts)
    nay, ss, spark = ({"dt": 0, "lg": 0, "so_khach": 0, "so_phieu": 0, "ty_suat": None}, [], [])
    if kx is not None:
        nay, ss = BK.tong(conn, kx)
        spark = [o.doanh_thu for o in BK.chuoi(conn, kx)[1]]
    ns = _ns_theo_khoang(conn, kx)
    dem, _ = KH.dem_va_can_xu_ly(conn, gioi_han=0, sale=None)
    kho = dict(conn.execute(
        "SELECT trang_thai, count(*)::int FROM mart.san_pham_360 GROUP BY 1").fetchall())
    can_han, so_qua_han = SP.lo_can_han(conn, gioi_han=1000)
    chinh = ss[0] if ss else None
    return {
        "khoang": kx,
        "doanh_thu": {
            "gia_tri": nay["dt"], "tu_ngay": kx.tu if kx else None, "den_ngay": kx.den if kx else None,
            "cung_ky": chinh.dt_ck if chinh else None, "tang": chinh.tang_dt if chinh else None,
            "lai_gop": nay["lg"], "ty_suat": nay["ty_suat"], "so_khach": nay["so_khach"],
            "so_phieu": nay["so_phieu"], "so_sanh": _so_sanh_json(ss), "spark": spark,
        },
        "ngan_sach": None if ns is None or not ns.co_ngan_sach else {
            "tien_do": ns.tien_do, "thuc_te": ns.thuc_te, "muc_tieu": ns.muc_tieu,
            "muc_tieu_den_hom_nay": ns.muc_tieu_den_hom_nay,
            "moc": _ty_so(ns.muc_tieu_den_hom_nay, ns.muc_tieu),
            "spark": [m.thuc_te for m in ns.luy_ke if m.thuc_te is not None],
            "thang": ns.thang,
            "tien_do_lg": ns.tien_do_lg, "thuc_te_lg": ns.thuc_te_lg, "muc_tieu_lg": ns.muc_tieu_lg,
        },
        "ngan_sach_chi_theo_thang": kx is not None and kx.loai == "khoang",
        "kho": {"het_hang": kho.get("het_hang", 0), "can_han": len(can_han),
                "qua_han": so_qua_han},
        "khach": {"can_goi": dem.get("canh_bao", 0), "roi_bo": dem.get("da_roi_bo", 0)},
    }


# ---- Tiến độ ngân sách tháng / Doanh thu theo sale ---------------------------

def ngan_sach(conn, sale=None, ts=None) -> dict | None:
    kx = _kx(conn, ts)
    if kx is not None and kx.loai == "khoang":
        return {"chi_theo_thang": True, "khoang": kx}
    ns = _ns_theo_khoang(conn, kx)
    if ns is None:
        return None
    from kome.bao_cao import chi_so_phu
    phu = chi_so_phu(ns)
    return {
        "thang": ns.thang, "co_ngan_sach": ns.co_ngan_sach,
        "thuc_te": ns.thuc_te, "muc_tieu": ns.muc_tieu,
        "muc_tieu_den_hom_nay": ns.muc_tieu_den_hom_nay, "tien_do": ns.tien_do,
        "moc": _ty_so(ns.muc_tieu_den_hom_nay, ns.muc_tieu),
        # 041: lãi gộp của CÔNG TY — ngân sách công ty nhập thẳng.
        "co_ngan_sach_lg": ns.co_ngan_sach_lg, "thuc_te_lg": ns.thuc_te_lg,
        "muc_tieu_lg": ns.muc_tieu_lg, "muc_tieu_lg_den_hom_nay": ns.muc_tieu_lg_den_hom_nay,
        "tien_do_lg": ns.tien_do_lg, "moc_lg": _ty_so(ns.muc_tieu_lg_den_hom_nay, ns.muc_tieu_lg),
        "ngay_kd": ns.ngay_kd, "ngay_kd_da_qua": ns.ngay_kd_da_qua,
        "ngay_kd_con_lai": phu["ngay_kd_con_lai"], "can_ban_moi_ngay": phu["can_ban_moi_ngay"],
        "nhip_chuan": phu["nhip_chuan"],
        "nguoi": [asdict(n) for n in ns.nguoi],
        "luy_ke": [asdict(m) for m in ns.luy_ke],
        "khoang": kx,
    }


def ngan_sach_thang(conn, sale=None, ts=None) -> dict | None:
    """Khối "Tiến độ ngân sách tháng": như `ngan_sach` + đường luỹ kế để vẽ."""
    d = ngan_sach(conn, sale, ts)
    if d is not None and not d.get("chi_theo_thang"):
        d["duong"] = duong_luy_ke(conn, d["khoang"], d)
    return d


def duong_luy_ke(conn, kx, ns: dict) -> dict:
    """Đường luỹ kế của khối ngân sách tháng.

    Dạng Tháng (+1 lượt hỏi): mỗi ngày của tháng — doanh thu cộng dồn tới ngày đó
    (tháng hiện tại: tới mốc hôm nay, sau đó None; tháng cũ: trọn tháng), nhịp ngân sách = chỉ tiêu × số ngày làm việc
    đã qua ÷ số ngày làm việc của tháng — ĐÚNG công thức `muc_tieu_den_hom_nay` của
    `mart.tien_do_ngan_sach` áp cho từng ngày, nên tại mốc hai số trùng nhau (có
    test canh) — và luỹ kế tháng trước cùng ngày để so. Ngày làm việc đọc
    `mart.lich_kinh_doanh` (định nghĩa duy nhất), doanh thu đọc `mart.ngay_khoang`.
    Dạng Kỳ (0 lượt): luỹ kế theo tháng `TienDoNganSach.luy_ke` đã có sẵn."""
    if kx.loai != "thang":
        return {"kieu": "thang", "diem": [
            {"nhan": m["thang"], "tt": m["thuc_te"], "ns": m["ngan_sach"], "ss": None,
             "tt_lg": m["thuc_te_lg"], "ns_lg": m["ngan_sach_lg"], "ss_lg": None}
            for m in ns["luy_ke"]], "nhan_ss": None}
    dau = kx.tu
    cuoi = KX._cuoi_thang(dau.year, dau.month)
    # Tháng đang xem LÙI là tháng đã khép: vẽ trọn tới cuối tháng (ngày cuối không
    # bán gì thì đường nằm ngang — đúng sự thật). Tháng hiện tại dừng ở mốc hôm nay.
    den = cuoi if kx.dang_lui else kx.den
    dau_truoc = date(dau.year - (dau.month == 1), 12 if dau.month == 1 else dau.month - 1, 1)
    rows = conn.execute(
        """SELECT l.ngay, l.la_ngay_kd, coalesce(n.dt, 0), coalesce(n.lg, 0)
             FROM mart.lich_kinh_doanh l
             LEFT JOIN mart.ngay_khoang(%s, %s) n ON n.ngay = l.ngay
            WHERE l.ngay BETWEEN %s AND %s ORDER BY l.ngay""",
        (dau_truoc, den, dau_truoc, cuoi)).fetchall()
    truoc, cong, cong_lg = {}, 0, 0
    for r in rows:
        if r[0] < dau:
            cong += int(r[2])
            cong_lg += int(r[3])
            truoc[r[0].day] = (cong, cong_lg)
    nay = [r for r in rows if r[0] >= dau]
    ngay_kd = sum(1 for r in nay if r[1])
    muc_tieu, muc_tieu_lg = ns["muc_tieu"], ns["muc_tieu_lg"]
    diem, cong, cong_lg, kd = [], 0, 0, 0
    for r in nay:
        kd += bool(r[1])
        cong += int(r[2])
        cong_lg += int(r[3])
        co = r[0] <= den
        tr = truoc.get(r[0].day)
        diem.append({
            "nhan": r[0].isoformat(),
            "tt": cong if co else None,
            "ns": round(muc_tieu * kd / ngay_kd) if muc_tieu is not None and ngay_kd else None,
            "ss": tr[0] if tr else None,
            "tt_lg": cong_lg if co else None,
            "ns_lg": round(muc_tieu_lg * kd / ngay_kd) if muc_tieu_lg is not None and ngay_kd else None,
            "ss_lg": tr[1] if tr else None})
    return {"kieu": "ngay", "diem": diem, "nhan_ss": "Tháng trước", "den": den.isoformat()}


# ---- Kết quả theo từng tháng (kỳ kế toán hiện hành) -------------------------

def theo_thang(conn, sale=None, ts=None) -> dict:
    """Các tháng của KỲ chứa ngày cuối khoảng xem; giao diện tô đậm các tháng
    thuộc khoảng (`khoang.tu` → `khoang.den`)."""
    kx = _kx(conn, ts)
    # FULL JOIN, không LEFT JOIN từ doanh thu (cùng bất biến của
    # mart.tien_do_ngan_sach): tháng ĐÃ ĐẶT ngân sách mà không có dòng bán nào
    # vẫn phải có dòng — bản LEFT JOIN làm tháng 8/2026 (ngân sách ¥92,7M, chưa
    # nạp dữ liệu) biến mất, và khối in "chưa đặt chỉ tiêu tháng nào". Chỉ lấy
    # tháng ≤ tháng của mốc: ngân sách các tháng tương lai không phải "kết quả".
    rows = [] if kx is None else conn.execute(
        """WITH s AS (SELECT * FROM mart.ban_theo_thang_so_sanh WHERE company_fy = %(fy)s),
                ns AS (SELECT * FROM mart.ngan_sach_cong_ty_thang WHERE company_fy = %(fy)s)
           SELECT coalesce(s.thang, ns.thang), %(fy)s, coalesce(s.thang_trong_ky, d.company_fy_month),
                  s.doanh_thu_thuan, s.lai_gop, s.so_khach,
                  coalesce(s.dt_cung_ky, ck.doanh_thu_thuan), coalesce(s.co_cung_ky, ck.thang IS NOT NULL),
                  ns.doanh_thu, ns.lai_gop
             FROM s FULL JOIN ns ON ns.thang = s.thang
             LEFT JOIN core.dim_date d ON s.thang IS NULL
                   AND d.date_key = to_date(ns.thang || '-01', 'YYYY-MM-DD')
             LEFT JOIN mart.ban_theo_thang ck ON s.thang IS NULL
                   AND ck.thang = to_char(to_date(ns.thang || '-01', 'YYYY-MM-DD') - interval '12 months', 'YYYY-MM')
            WHERE coalesce(s.thang, ns.thang) <= to_char(%(den)s::date, 'YYYY-MM')
            ORDER BY 1""", {"fy": kx.company_fy, "den": kx.den}).fetchall()
    thang = [{
        "thang": r[0], "company_fy": r[1], "thang_trong_ky": r[2],
        "doanh_thu": int(r[3] or 0), "lai_gop": int(r[4] or 0),
        "ty_suat": _ty_so(int(r[4] or 0), int(r[3] or 0)), "so_khach": r[5],
        "cung_ky": int(r[6]) if r[6] is not None else None, "co_cung_ky": r[7],
        # 041: ngân sách CÔNG TY (nhập thẳng), không cộng từ từng người.
        "ngan_sach": int(r[8]) if r[8] is not None else None,
        "ngan_sach_lg": int(r[9]) if r[9] is not None else None,
    } for r in rows]
    return {"company_fy": thang[0]["company_fy"] if thang else None, "thang": thang,
            "hom_nay": kx.hom_nay if kx else None, "khoang": kx}


# ---- Xu hướng doanh thu theo khoảng xem -------------------------------------

def xu_huong(conn, sale=None, ts=None) -> dict:
    """Doanh thu từng ngày (khoảng ≤ 92 ngày) hoặc từng tháng (dài hơn) của
    khoảng xem, kèm phép so chính (năm trước) khớp theo thứ tự."""
    kx = _kx(conn, ts)
    if kx is None:
        return {"khoang": None, "kieu": "ngay", "diem": []}
    kieu, o = BK.chuoi(conn, kx)
    return {"khoang": kx, "kieu": kieu,
            "diem": [[x.thang, x.doanh_thu, x.lai_gop, x.so_khach, x.dt_cung_ky] for x in o]}


# ---- Sức khoẻ khách hàng ----------------------------------------------------

def suc_khoe(conn, sale=None, ts=None) -> dict:
    KX.dat_moc(conn, ts)
    dem, _ = KH.dem_va_can_xu_ly(conn, gioi_han=0, sale=None)
    return {"dem": dem, "nhom": list(TQ.NHOM_SUC_KHOE),
            "nhan": {k: v[0] for k, v in KH.TRANG_THAI.items()}}


# ---- Sản phẩm sắp hết hạn ---------------------------------------------------

def han_su_dung(conn, sale=None, ts=None) -> dict:
    KX.dat_moc(conn, ts)
    rows = conn.execute(
        f"""WITH t AS MATERIALIZED (SELECT * FROM mart.ton_hien_tai)
            SELECT t.product_code, coalesce(nullif(p.product_name, ''), t.product_code),
                   t.warehouse_code, t.ten_kho, t.best_before, t.han_con_lai,
                   t.so_luong, t.gia_tri
              FROM t LEFT JOIN core.dim_product p ON p.product_code = t.product_code
             WHERE ({SP.VI_TU_CAN_HAN}) OR ({SP.VI_TU_QUA_HAN})
             ORDER BY t.han_con_lai LIMIT 40""", [SP.CAN_HAN_NGAY]).fetchall()
    return {"can_han_ngay": SP.CAN_HAN_NGAY, "lo": [{
        "ma": r[0], "ten": r[1], "kho": r[2], "ten_kho": r[3], "han": r[4],
        "con_lai": r[5], "so_luong": r[6], "gia_tri": int(r[7] or 0)} for r in rows]}


# ---- Việc cần làm hôm nay (của người đang xem) ------------------------------

def viec_hom_nay(conn, sale=None, ts=None) -> dict:
    """Việc của người đang xem. Danh sách cần gọi / hàng cận hạn tính đến MỐC của
    khoảng xem (040); hẹn gọi lại và "hôm nay đã nạp chưa" theo ĐỒNG HỒ THẬT."""
    from kome import lien_he as LH
    KX.dat_moc(conn, ts)
    hom_nay = hom_nay_o_nhat()
    ds = LH.danh_sach(conn, hom_nay, sale=sale)
    hen = LH.hen_goi_lai(conn, hom_nay, sale=sale)
    can_han, so_qua_han = SP.lo_can_han(conn, gioi_han=5)
    tuoi = tinh_tuoi(conn)
    viec = []
    for n in tuoi.nguon:
        if n.trang_thai == "do":
            viec.append({"muc": "gap", "tag": "Dữ liệu", "chu": f"Chưa nạp {n.ten} hôm nay",
                         "lien_ket": "/kho-du-lieu", "han": "hôm nay"})
    for t in hen:
        viec.append({"muc": "gap", "tag": "Hẹn gọi", "chu": f"Gọi lại {t.ten_khach or t.ma_khach}"
                     + (f" — {t.noi_dung}" if t.noi_dung else ""),
                     "lien_ket": f"/khach-hang/{t.ma_khach}", "han": "hôm nay"})
    for cot in ds.cot:
        for k in cot.the[:3]:
            viec.append({"muc": "canh" if cot.ly_do != "sap_den_han" else "thuong", "tag": cot.nhan,
                         "chu": (f"Gọi {k.ten} — mua đều {k.so_thang}/3 tháng, tháng này chưa có đơn"
                                 if cot.ly_do == LH.COT_THANG else f"Gọi {k.ten} — im {k.so_ngay_im_lang} ngày"),
                         "lien_ket": f"/khach-hang/{k.ma}", "han": None})
    if so_qua_han:
        viec.append({"muc": "gap", "tag": "Kho", "chu": f"{so_qua_han} lô đã quá hạn sử dụng",
                     "lien_ket": "/kho-hang", "han": "hết ngày"})
    for d in can_han[:3]:
        viec.append({"muc": "canh", "tag": "Kho", "chu": f"{d['ten']} còn {d['han_con_lai']} ngày",
                     "lien_ket": f"/san-pham/{d['ma']}", "han": None})
    return {"viec": viec, "thieu_nguon": ["công nợ", "mua hàng", "khiếu nại"]}


# ---- Tháng này chưa mua (036) -----------------------------------------------

def thang_nay_chua_mua(conn, sale=None, ts=None) -> dict:
    KX.dat_moc(conn, ts)
    from kome.khach_thang import chua_mua
    return chua_mua(conn, sale=sale)


# ---- Nạp dữ liệu / phiếu gần nhất ------------------------------------------

def nap_gan_nhat(conn, sale=None, ts=None) -> dict:
    KX.dat_moc(conn, ts)
    from kome.nhat_ky_nap import lo_nap_gan_nhat
    lo = lo_nap_gan_nhat(conn, gioi_han=6)
    phieu = conn.execute(
        """SELECT l.sales_date, l.slip_no, l.customer_code, k.ten, l.doanh_thu_thuan
             FROM mart.lan_mua l LEFT JOIN mart.khach_360 k USING (customer_code)
            ORDER BY l.sales_date DESC, l.slip_no DESC LIMIT 8""").fetchall()
    return {
        "lo": [{"loai": x.loai, "ten_file": x.ten_file, "ngay_du_lieu": x.ngay_du_lieu,
                "nap_luc": x.nap_luc, "so_dong": x.so_dong} for x in lo],
        "phieu": [{"ngay": r[0], "so": r[1], "ma": r[2], "ten": r[3] or r[2],
                   "tien": int(r[4] or 0)} for r in phieu],
    }


# ---- Danh sách khách hàng ---------------------------------------------------

def danh_sach_khach(conn, sale=None, ts=None) -> dict:
    """60 khách doanh thu cao nhất TRONG KHOẢNG XEM, kèm doanh thu của phép so
    phụ (tháng trước / khoảng liền trước; dạng Kỳ: năm trước) và các nhãn
    tính đến hôm nay (trạng thái, nhịp, doanh thu 12 tháng)."""
    kx = _kx(conn, ts)
    nhan = {k: v[0] for k, v in KH.TRANG_THAI.items()}
    if kx is None:
        return {"khoang": None, "so_sanh": None, "khach": [], "nhan": nhan}
    ss = kx.so_sanh[1] if len(kx.so_sanh) > 1 else kx.so_sanh[0]
    rows = conn.execute(
        """WITH a AS (SELECT customer_code, dt FROM mart.khach_khoang(%s, %s)),
                b AS (SELECT customer_code, dt FROM mart.khach_khoang(%s, %s))
           SELECT k.customer_code, k.ten, k.salesperson_code, s.ten, k.doanh_thu_thuan,
                  k.ty_le_im_lang, k.trang_thai, k.so_ngay_im_lang, k.nhip_ngay,
                  a.dt, coalesce(b.dt, 0)
             FROM a JOIN mart.khach_360 k USING (customer_code)
             LEFT JOIN b USING (customer_code)
             LEFT JOIN core.dim_salesperson s ON s.salesperson_code = k.salesperson_code
            WHERE NOT k.da_ngung
            ORDER BY a.dt DESC NULLS LAST LIMIT 60""",
        (kx.tu, kx.den, ss.tu if ss.co else None, ss.den if ss.co else None)).fetchall()
    return {"khoang": kx, "so_sanh": {"ma": ss.ma, "nhan": ss.nhan, "co": ss.co, "tu": ss.tu, "den": ss.den},
            "khach": [{
                "ma": r[0], "ten": r[1], "sale": r[2], "ten_sale": r[3],
                "doanh_thu": int(r[4] or 0), "ty_le_im_lang": float(r[5]) if r[5] is not None else None,
                "trang_thai": r[6], "so_ngay_im_lang": r[7], "nhip_ngay": r[8],
                "thang_nay": int(r[9] or 0), "thang_truoc": int(r[10]) if ss.co else None} for r in rows],
            "nhan": nhan}


# ---- Hiệu suất theo ngành hàng ----------------------------------------------

def hieu_suat_nganh(conn, sale=None, ts=None) -> dict:
    """Ngành của khoảng xem so phép so chính (`mart.nganh_so_sanh_khoang`)."""
    kx = _kx(conn, ts)
    rows = [] if kx is None else sorted(BK.nganh(conn, kx), key=lambda n: -n.doanh_thu)
    co = bool(kx and kx.so_sanh and kx.so_sanh[0].co)
    tong = sum(n.doanh_thu for n in rows)
    return {"thang": kx.nhan if kx else None, "khoang": kx, "nganh": [{
        "nganh": n.nganh, "doanh_thu": n.doanh_thu, "lai_gop": n.lai_gop,
        "ty_trong": _ty_so(n.doanh_thu, tong), "ty_suat": _ty_so(n.lai_gop, n.doanh_thu),
        "cung_ky": n.dt_cung_ky, "co_cung_ky": co, "tang_truong": n.tang_truong} for n in rows]}


# ---- Doanh thu × tần suất mua -----------------------------------------------

def tuong_quan(conn, sale=None, ts=None) -> dict:
    """Doanh thu × số ngày mua TRONG KHOẢNG XEM; màu = trạng thái tính đến hôm nay."""
    kx = _kx(conn, ts)
    rows = [] if kx is None else conn.execute(
        """SELECT k.customer_code, h.ten, k.dt, k.so_ngay_mua, h.trang_thai, k.ty_suat
             FROM mart.khach_khoang(%s, %s) k
             JOIN mart.khach_360 h USING (customer_code)
            WHERE NOT h.da_ngung AND k.dt > 0
            ORDER BY k.dt DESC LIMIT 400""", (kx.tu, kx.den)).fetchall()
    return {"khoang": kx, "khach": [{"ma": r[0], "ten": r[1], "doanh_thu": int(r[2] or 0), "so_lan": r[3],
                                     "trang_thai": r[4], "ty_suat": float(r[5]) if r[5] is not None else None}
                                    for r in rows]}


# ---- Số khách đang mua theo kỳ ----------------------------------------------

def tang_truong(conn, sale=None, ts=None) -> dict:
    """Theo kỳ (bản chất nhiều kỳ) — `chon` = kỳ chứa ngày cuối khoảng xem."""
    kx = _kx(conn, ts)
    rows = conn.execute(
        """SELECT company_fy, nhan, so_thang_co_du_lieu, so_khach, doanh_thu_thuan
             FROM mart.tong_theo_ky ORDER BY company_fy""").fetchall()
    return {"chon": kx.company_fy if kx else None, "khoang": kx,
            "ky": [{"company_fy": r[0], "nhan": r[1], "so_thang": r[2], "so_khach": r[3],
                    "doanh_thu": int(r[4] or 0)} for r in rows]}


# ---- Biên lợi nhuận GỘP theo quý (biên ròng: chưa có chi phí) ---------------

def bien_loi_nhuan(conn, sale=None, ts=None) -> dict:
    """Theo quý (6 quý gần nhất) — `thang_chon` = tháng của ngày cuối khoảng xem;
    giao diện tô đậm quý có `tu ≤ thang_chon ≤ den`."""
    kx = _kx(conn, ts)
    rows = conn.execute(
        """SELECT company_fy, (thang_trong_ky - 1) / 3 + 1 AS quy, min(thang), max(thang),
                  count(*)::int, sum(doanh_thu_thuan)::bigint, sum(lai_gop)::bigint
             FROM mart.ban_theo_thang GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()[-6:]
    return {"thang_chon": kx.den.strftime("%Y-%m") if kx else None, "khoang": kx,
            "quy": [{"company_fy": r[0], "quy": r[1], "tu": r[2], "den": r[3], "so_thang": r[4],
                     "doanh_thu": int(r[5] or 0), "lai_gop": int(r[6] or 0),
                     "bien_gop": _ty_so(int(r[6] or 0), int(r[5] or 0))} for r in rows]}


# ---- Chuông thông báo (khung chung) -----------------------------------------

def thong_bao(conn, sale=None) -> dict:
    """Chỉ những gì CÓ nguồn thật. Mỗi mục một mã ổn định (để giao diện nhớ
    "đã đọc") và một liên kết tới đúng màn xử lý nó."""
    tb = []
    for n in tinh_tuoi(conn).nguon:
        if n.trang_thai == "do":
            tb.append({"ma": f"nap-{n.spec}-{hom_nay_o_nhat()}", "muc": "gap", "loai": "DỮ LIỆU",
                       "tieu_de": f"Chưa nạp {n.ten} hôm nay",
                       "noi_dung": f"Dữ liệu mới nhất: {n.ngay or 'chưa bao giờ'}"
                                   + (f" · trễ {n.tre} ngày làm việc" if n.tre else ""),
                       "lien_ket": "/kho-du-lieu"})
    for r in conn.execute(
            """SELECT customer_code, ten, so_ngay_im_lang, ty_le_im_lang, ly_do, doanh_thu_thuan
                 FROM mart.uu_tien_lien_he WHERE ly_do IN ('lau_khong_mua', 'qua_han')
                ORDER BY doanh_thu_thuan DESC NULLS LAST LIMIT 4""").fetchall():
        nhip = f" — {float(r[3]):.1f}× nhịp mua riêng".replace(".", ",") if r[3] is not None else ""
        tb.append({"ma": f"khach-{r[0]}-{r[2]}", "muc": "canh", "loai": "KHÁCH HÀNG",
                   "tieu_de": f"{r[1]} im lặng {r[2]} ngày",
                   "noi_dung": ("Lâu không mua" if r[4] == "lau_khong_mua" else "Quá hạn mua lại") + nhip,
                   "lien_ket": f"/khach-hang/{r[0]}"})
    for r in conn.execute(
            """SELECT product_code, ten_hang FROM mart.san_pham_360
                WHERE trang_thai = 'het_hang' ORDER BY doanh_thu_thuan DESC NULLS LAST LIMIT 3""").fetchall():
        tb.append({"ma": f"het-{r[0]}", "muc": "gap", "loai": "KHO", "tieu_de": f"{r[1]} đã hết hàng",
                   "noi_dung": "Tồn kho bằng 0 trong ảnh chụp 在庫一覧 mới nhất.",
                   "lien_ket": f"/san-pham/{r[0]}"})
    can_han, so_qua_han = SP.lo_can_han(conn, gioi_han=3)
    if so_qua_han:
        tb.append({"ma": f"qua-han-{so_qua_han}", "muc": "gap", "loai": "KHO",
                   "tieu_de": f"{so_qua_han} lô đã quá hạn sử dụng", "noi_dung": "Cần xử lý hoặc tiêu huỷ.",
                   "lien_ket": "/kho-hang"})
    for d in can_han:
        tb.append({"ma": f"can-han-{d['ma']}-{d['kho']}", "muc": "canh", "loai": "KHO",
                   "tieu_de": f"{d['ten']} còn {d['han_con_lai']} ngày hạn dùng",
                   "noi_dung": d["ten_kho"] or d["kho"], "lien_ket": f"/san-pham/{d['ma']}"})
    return {"tb": tb}


# ---- Tuổi nợ phải thu (đợt 6) -----------------------------------------------

def cong_no(conn, sale=None, ts=None) -> dict | None:
    """Sổ 請求先元帳 có kỳ kết thúc muộn nhất ≤ mốc (mart.cong_no_*, 038 + 040).
    None = chưa có sổ tới mốc."""
    from kome import cong_no as CN
    KX.dat_moc(conn, ts)
    return CN.khoi_tong_quan(conn)


# Mã khối -> (hàm, theo_ngay, theo_sale, theo_khoang). Mã trùng
# `kome/web/bo_cuc.py::KHOI`. `theo_khoang`: hàm nhận `ts` (khoảng xem,
# kome/khoang_xem.py) và khoá ảnh chụp mang tham số khoảng.
KHOI = {
    "kpi": (kpi, False, False, True),
    "ns_thang": (ngan_sach_thang, False, False, True),
    "so_sanh_sale": (ngan_sach, False, False, True),
    "theo_thang": (theo_thang, False, False, True),
    "xu_huong": (xu_huong, False, False, True),
    # Từ 040 ("mọi thứ quay về tháng đó") cả các khối "tính đến hôm nay" cũng
    # theo khoảng xem: chúng đặt MỐC của khoảng (KX.dat_moc) trước khi đọc mart.
    "suc_khoe_khach": (suc_khoe, False, False, True),
    "han_su_dung": (han_su_dung, False, False, True),
    "viec_hom_nay": (viec_hom_nay, True, True, True),
    "thang_nay_chua_mua": (thang_nay_chua_mua, False, True, True),
    "cong_no": (cong_no, False, False, True),
    "don_hang": (nap_gan_nhat, False, False, True),
    "danh_sach_khach": (danh_sach_khach, False, False, True),
    "hieu_suat_nganh": (hieu_suat_nganh, False, False, True),
    "tuong_quan": (tuong_quan, False, False, True),
    "tang_truong": (tang_truong, False, False, True),
    "bien_loi_nhuan": (bien_loi_nhuan, False, False, True),
}
