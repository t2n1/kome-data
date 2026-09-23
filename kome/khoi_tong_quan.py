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

from kome import khach_hang as KH
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


# ---- Chỉ số hôm nay (6 ô) ---------------------------------------------------

def kpi(conn, sale=None) -> dict:
    tn = conn.execute(
        """SELECT tu_ngay, den_ngay, dt, lg, so_khach, co_cung_ky, dt_ck, lg_ck
           FROM mart.thang_den_hom_nay""").fetchone()
    ngay = conn.execute(
        """SELECT ngay, doanh_thu_thuan FROM mart.ban_theo_ngay
           ORDER BY ngay DESC LIMIT 14""").fetchall()[::-1]
    ns = tien_do_ngan_sach(conn)
    dem, _ = KH.dem_va_can_xu_ly(conn, gioi_han=0, sale=None)
    kho = dict(conn.execute(
        "SELECT trang_thai, count(*)::int FROM mart.san_pham_360 GROUP BY 1").fetchall())
    can_han, so_qua_han = SP.lo_can_han(conn, gioi_han=1000)
    dt = int(tn[2] or 0) if tn else 0
    dt_ck = int(tn[6]) if tn and tn[6] is not None else None
    return {
        "doanh_thu": {
            "gia_tri": dt, "tu_ngay": tn[0] if tn else None, "den_ngay": tn[1] if tn else None,
            "cung_ky": dt_ck, "tang": _ty_so(dt - dt_ck, dt_ck) if dt_ck else None,
            "spark": [int(r[1] or 0) for r in ngay],
        },
        "ngan_sach": None if ns is None or not ns.co_ngan_sach else {
            "tien_do": ns.tien_do, "thuc_te": ns.thuc_te, "muc_tieu": ns.muc_tieu,
            "muc_tieu_den_hom_nay": ns.muc_tieu_den_hom_nay,
            "moc": _ty_so(ns.muc_tieu_den_hom_nay, ns.muc_tieu),
            "spark": [m.thuc_te for m in ns.luy_ke if m.thuc_te is not None],
            "thang": ns.thang,
        },
        "kho": {"het_hang": kho.get("het_hang", 0), "can_han": len(can_han),
                "qua_han": so_qua_han},
        "khach": {"can_goi": dem.get("canh_bao", 0), "roi_bo": dem.get("da_roi_bo", 0)},
    }


# ---- Tiến độ ngân sách tháng / Doanh thu theo sale ---------------------------

def ngan_sach(conn, sale=None) -> dict | None:
    ns = tien_do_ngan_sach(conn)
    if ns is None:
        return None
    from kome.bao_cao import chi_so_phu
    phu = chi_so_phu(ns)
    return {
        "thang": ns.thang, "co_ngan_sach": ns.co_ngan_sach,
        "thuc_te": ns.thuc_te, "muc_tieu": ns.muc_tieu,
        "muc_tieu_den_hom_nay": ns.muc_tieu_den_hom_nay, "tien_do": ns.tien_do,
        "moc": _ty_so(ns.muc_tieu_den_hom_nay, ns.muc_tieu),
        "ngay_kd": ns.ngay_kd, "ngay_kd_da_qua": ns.ngay_kd_da_qua,
        "ngay_kd_con_lai": phu["ngay_kd_con_lai"], "can_ban_moi_ngay": phu["can_ban_moi_ngay"],
        "nhip_chuan": phu["nhip_chuan"],
        "nguoi": [asdict(n) for n in ns.nguoi],
        "luy_ke": [asdict(m) for m in ns.luy_ke],
    }


# ---- Kết quả theo từng tháng (kỳ kế toán hiện hành) -------------------------

def theo_thang(conn, sale=None) -> dict:
    rows = conn.execute(
        """WITH ky AS (SELECT max(company_fy) AS fy FROM mart.ban_theo_thang_so_sanh),
                ns AS (SELECT thang, sum(muc_tieu)::bigint AS muc_tieu
                         FROM mart.ngan_sach_thang GROUP BY thang)
           SELECT s.thang, s.company_fy, s.thang_trong_ky, s.doanh_thu_thuan, s.lai_gop,
                  s.so_khach, s.dt_cung_ky, s.co_cung_ky, ns.muc_tieu
             FROM mart.ban_theo_thang_so_sanh s
             JOIN ky ON s.company_fy = ky.fy
             LEFT JOIN ns ON ns.thang = s.thang
            ORDER BY s.thang""").fetchall()
    thang = [{
        "thang": r[0], "company_fy": r[1], "thang_trong_ky": r[2],
        "doanh_thu": int(r[3] or 0), "lai_gop": int(r[4] or 0),
        "ty_suat": _ty_so(int(r[4] or 0), int(r[3] or 0)), "so_khach": r[5],
        "cung_ky": int(r[6]) if r[6] is not None else None, "co_cung_ky": r[7],
        "ngan_sach": int(r[8]) if r[8] is not None else None,
    } for r in rows]
    return {"company_fy": thang[0]["company_fy"] if thang else None, "thang": thang,
            "hom_nay": conn.execute("SELECT hom_nay FROM mart.moc_thoi_gian").fetchone()[0]}


# ---- Xu hướng doanh thu (giao diện chọn khung 7N/30N/90N/1N) -----------------

def xu_huong(conn, sale=None) -> dict:
    """Hai năm doanh thu theo ngày (cũ -> mới) — đủ cho khung 1N so với 1N
    liền trước. Đổi khung ở trình duyệt, không gọi lại máy chủ."""
    rows = conn.execute(
        """SELECT ngay, doanh_thu_thuan, lai_gop, so_khach FROM mart.ban_theo_ngay
           ORDER BY ngay DESC LIMIT 730""").fetchall()[::-1]
    return {"ngay": [[r[0], int(r[1] or 0), int(r[2] or 0), r[3] or 0] for r in rows]}


# ---- Sức khoẻ khách hàng ----------------------------------------------------

def suc_khoe(conn, sale=None) -> dict:
    dem, _ = KH.dem_va_can_xu_ly(conn, gioi_han=0, sale=None)
    return {"dem": dem, "nhom": list(TQ.NHOM_SUC_KHOE),
            "nhan": {k: v[0] for k, v in KH.TRANG_THAI.items()}}


# ---- Sản phẩm sắp hết hạn ---------------------------------------------------

def han_su_dung(conn, sale=None) -> dict:
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

def viec_hom_nay(conn, sale=None) -> dict:
    from kome import lien_he as LH
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

def thang_nay_chua_mua(conn, sale=None) -> dict:
    from kome.khach_thang import chua_mua
    return chua_mua(conn, sale=sale)


# ---- Nạp dữ liệu / phiếu gần nhất ------------------------------------------

def nap_gan_nhat(conn, sale=None) -> dict:
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

def danh_sach_khach(conn, sale=None) -> dict:
    rows = conn.execute(
        """WITH m AS (SELECT to_char(hom_nay, 'YYYY-MM') AS t,
                             to_char(hom_nay - interval '1 month', 'YYYY-MM') AS t1
                        FROM mart.moc_thoi_gian)
           SELECT k.customer_code, k.ten, k.salesperson_code, s.ten, k.doanh_thu_thuan,
                  k.ty_le_im_lang, k.trang_thai, k.so_ngay_im_lang, k.nhip_ngay,
                  coalesce(a.doanh_thu_thuan, 0), coalesce(b.doanh_thu_thuan, 0)
             FROM mart.khach_360 k CROSS JOIN m
             LEFT JOIN mart.khach_theo_thang a ON a.customer_code = k.customer_code AND a.thang = m.t
             LEFT JOIN mart.khach_theo_thang b ON b.customer_code = k.customer_code AND b.thang = m.t1
             LEFT JOIN core.dim_salesperson s ON s.salesperson_code = k.salesperson_code
            WHERE NOT k.da_ngung
            ORDER BY k.doanh_thu_thuan DESC NULLS LAST LIMIT 60""").fetchall()
    return {"khach": [{
        "ma": r[0], "ten": r[1], "sale": r[2], "ten_sale": r[3],
        "doanh_thu": int(r[4] or 0), "ty_le_im_lang": float(r[5]) if r[5] is not None else None,
        "trang_thai": r[6], "so_ngay_im_lang": r[7], "nhip_ngay": r[8],
        "thang_nay": int(r[9]), "thang_truoc": int(r[10])} for r in rows],
        "nhan": {k: v[0] for k, v in KH.TRANG_THAI.items()}}


# ---- Hiệu suất theo ngành hàng ----------------------------------------------

def hieu_suat_nganh(conn, sale=None) -> dict:
    rows = conn.execute(
        """WITH t AS (SELECT max(thang) AS thang FROM mart.ban_theo_nganh_thang_so_sanh)
           SELECT s.thang, s.nganh, s.doanh_thu_thuan, s.lai_gop, s.dt_cung_ky,
                  s.co_cung_ky, s.tang_truong
             FROM mart.ban_theo_nganh_thang_so_sanh s JOIN t USING (thang)
            ORDER BY s.doanh_thu_thuan DESC""").fetchall()
    tong = sum(int(r[2] or 0) for r in rows)
    return {"thang": rows[0][0] if rows else None, "nganh": [{
        "nganh": r[1], "doanh_thu": int(r[2] or 0), "lai_gop": int(r[3] or 0),
        "ty_trong": _ty_so(int(r[2] or 0), tong), "ty_suat": _ty_so(int(r[3] or 0), int(r[2] or 0)),
        "cung_ky": int(r[4]) if r[4] is not None else None, "co_cung_ky": r[5],
        "tang_truong": float(r[6]) if r[6] is not None else None} for r in rows]}


# ---- Doanh thu × tần suất mua -----------------------------------------------

def tuong_quan(conn, sale=None) -> dict:
    rows = conn.execute(
        """SELECT customer_code, ten, doanh_thu_thuan, so_lan_mua, trang_thai, ty_suat
             FROM mart.khach_360 WHERE NOT da_ngung AND doanh_thu_thuan > 0
            ORDER BY doanh_thu_thuan DESC LIMIT 400""").fetchall()
    return {"khach": [{"ma": r[0], "ten": r[1], "doanh_thu": int(r[2] or 0), "so_lan": r[3],
                       "trang_thai": r[4], "ty_suat": float(r[5]) if r[5] is not None else None}
                      for r in rows]}


# ---- Số khách đang mua theo kỳ ----------------------------------------------

def tang_truong(conn, sale=None) -> dict:
    rows = conn.execute(
        """SELECT company_fy, nhan, so_thang_co_du_lieu, so_khach, doanh_thu_thuan
             FROM mart.tong_theo_ky ORDER BY company_fy""").fetchall()
    return {"ky": [{"company_fy": r[0], "nhan": r[1], "so_thang": r[2], "so_khach": r[3],
                    "doanh_thu": int(r[4] or 0)} for r in rows]}


# ---- Biên lợi nhuận GỘP theo quý (biên ròng: chưa có chi phí) ---------------

def bien_loi_nhuan(conn, sale=None) -> dict:
    rows = conn.execute(
        """SELECT company_fy, (thang_trong_ky - 1) / 3 + 1 AS quy, min(thang), max(thang),
                  count(*)::int, sum(doanh_thu_thuan)::bigint, sum(lai_gop)::bigint
             FROM mart.ban_theo_thang GROUP BY 1, 2 ORDER BY 1, 2""").fetchall()[-6:]
    return {"quy": [{"company_fy": r[0], "quy": r[1], "tu": r[2], "den": r[3], "so_thang": r[4],
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

def cong_no(conn, sale=None) -> dict | None:
    """Sổ 請求先元帳 mới nhất (mart.cong_no_*, migration 038). None = chưa nạp sổ."""
    from kome import cong_no as CN
    return CN.khoi_tong_quan(conn)


# Mã khối -> (hàm, theo_ngay, theo_sale). Mã trùng `kome/web/bo_cuc.py::KHOI`.
KHOI = {
    "kpi": (kpi, False, False),
    "ns_thang": (ngan_sach, False, False),
    "so_sanh_sale": (ngan_sach, False, False),
    "theo_thang": (theo_thang, False, False),
    "xu_huong": (xu_huong, False, False),
    "suc_khoe_khach": (suc_khoe, False, False),
    "han_su_dung": (han_su_dung, False, False),
    "viec_hom_nay": (viec_hom_nay, True, True),
    "thang_nay_chua_mua": (thang_nay_chua_mua, False, True),
    "cong_no": (cong_no, False, False),
    "don_hang": (nap_gan_nhat, False, False),
    "danh_sach_khach": (danh_sach_khach, False, False),
    "hieu_suat_nganh": (hieu_suat_nganh, False, False),
    "tuong_quan": (tuong_quan, False, False),
    "tang_truong": (tang_truong, False, False),
    "bien_loi_nhuan": (bien_loi_nhuan, False, False),
}
