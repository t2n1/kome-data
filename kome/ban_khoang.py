"""Số bán hàng theo KHOẢNG XEM (đặc tả 2026-09-24-khoang-xem-thang-design.md).

Chỉ HỎI các hàm `mart.*_khoang` (migration 039) và dựng lại đúng hình dạng dữ
liệu của `kome/bao_cao.py` (`BaoCao`, `Ky`, `O`, `NganhKy`, `TapTrung`) để
giao diện dùng lại mọi khối vẽ. KHÔNG định nghĩa chỉ số ở đây: tổng / tỷ suất /
tăng trưởng ngành đều tính trong `mart`; phép chia so sánh thừa kế
`bao_cao._SoCungKy` (một công thức, một chỗ).

Dạng Kỳ không đi qua module này: `tinh_bao_cao` gọi thẳng
`kome.bao_cao.tinh_bao_cao` để màn Báo cáo theo kỳ ra ĐÚNG số như trước — trừ khi
có kỳ so sánh tự chọn (`KhoangXem.tu_chon`).
"""
from __future__ import annotations

from datetime import date

from kome import bao_cao as BC
from kome.khoang_xem import KhoangXem

# Khoảng dài hơn chừng này ngày thì biểu đồ chính vẽ theo tháng thay vì ngày.
NGAY_TOI_DA_THEO_NGAY = 92


def _i(v) -> int | None:
    return int(v) if v is not None else None


def tong(conn, kx: KhoangXem) -> tuple[dict, list[BC.SoSanhSo]]:
    """Tổng của khoảng + mọi phép so, MỘT lượt hỏi (mỗi dải một dòng)."""
    dai = [(kx.tu, kx.den)]
    for s in kx.so_sanh:
        dai += [(s.tu_nay, s.den_nay), (s.tu, s.den)]
    gia_tri = ", ".join(f"({i}, %s::date, %s::date)" for i in range(len(dai)))
    rows = {r[0]: r[1:] for r in conn.execute(
        f"""SELECT v.i, t.dt, t.lg, t.ty_suat, t.so_phieu, t.so_khach
              FROM (VALUES {gia_tri}) v(i, tu, den)
              CROSS JOIN LATERAL mart.tong_khoang(v.tu, v.den) t""",
        [d for cap in dai for d in cap]).fetchall()}
    # Trong dải dữ liệu, không có phiếu = bán 0 đồng (không phải "không biết").
    n = rows[0]
    nay = {"dt": int(n[0] or 0), "lg": int(n[1] or 0),
           "ty_suat": float(n[2]) if n[2] is not None else None,
           "so_phieu": n[3] or 0, "so_khach": n[4] or 0}
    ss = []
    for j, s in enumerate(kx.so_sanh):
        a, b = rows[1 + 2 * j], rows[2 + 2 * j]
        ss.append(BC.SoSanhSo(
            ma=s.ma, nhan=s.nhan, co=s.co, tu=s.tu, den=s.den, tu_nay=s.tu_nay, den_nay=s.den_nay,
            dt=int(a[0] or 0), lg=int(a[1] or 0), so_khach=a[4] or 0,
            dt_ck=int(b[0] or 0) if s.co else None, lg_ck=int(b[1] or 0) if s.co else None,
            so_khach_ck=(b[4] or 0) if s.co else None))
    return nay, ss


def chuoi(conn, kx: KhoangXem) -> tuple[str, list[BC.O]]:
    """Chuỗi cho biểu đồ chính: theo NGÀY nếu khoảng ≤ 92 ngày, theo THÁNG nếu
    dài hơn — kèm phép so chính (`so_sanh[0]`, năm trước) khớp theo thứ tự.
    MỘT lượt hỏi."""
    kieu = "ngay" if kx.so_ngay <= NGAY_TOI_DA_THEO_NGAY else "thang"
    ham = "mart.ngay_khoang" if kieu == "ngay" else "mart.thang_khoang"
    nhan = "ngay::text" if kieu == "ngay" else "thang"
    s = kx.so_sanh[0] if kx.so_sanh else None
    cau = f"SELECT 0 AS k, {nhan}, dt, lg, so_phieu, so_khach FROM {ham}(%s, %s)"
    ts = [kx.tu, kx.den]
    # Kỳ so sánh tự chọn có thể dài khác hẳn (25 ngày với cả kỳ): hai chuỗi khác
    # độ hạt thì không xếp cạnh nhau theo thứ tự được — bỏ đường so, ô tổng vẫn so.
    cung_hat = s is not None and (((s.den - s.tu).days + 1 <= NGAY_TOI_DA_THEO_NGAY) == (kieu == "ngay"))
    if s is not None and s.co and cung_hat:
        cau += f" UNION ALL SELECT 1, {nhan}, dt, lg, so_phieu, so_khach FROM {ham}(%s, %s)"
        ts += [s.tu, s.den]
    rows = conn.execute(cau + " ORDER BY 1, 2", ts).fetchall()
    nay = [r for r in rows if r[0] == 0]
    ck = [r for r in rows if r[0] == 1]
    ra = []
    for i, r in enumerate(nay):
        dt, lg = int(r[2]), int(r[3])
        dt_ck = int(ck[i][2]) if i < len(ck) else None
        ra.append(BC.O(
            thang=r[1], doanh_thu=dt, lai_gop=lg, ty_suat=BC._SoCungKy._ty_suat(dt, lg),
            co_cung_ky=dt_ck is not None, tang_truong=BC._SoCungKy._tang(dt, dt_ck),
            la_thang_chot=kieu == "thang" and r[1].endswith("-07"),
            so_phieu=r[4], so_khach=r[5], dt_cung_ky=dt_ck))
    return kieu, ra


def nganh(conn, kx: KhoangXem) -> list[BC.NganhKy]:
    """Ngành so phép so chính (`mart.nganh_so_sanh_khoang`, FULL JOIN). Một lượt hỏi."""
    s = kx.so_sanh[0] if kx.so_sanh else None
    co = s is not None and s.co
    return [BC.NganhKy(nganh=r[0], doanh_thu=int(r[1] or 0), lai_gop=int(r[2] or 0),
                       dt_doi_chieu=_i(r[3]), dt_cung_ky=_i(r[4]), chenh_lech=_i(r[5]),
                       tang_truong=float(r[6]) if r[6] is not None else None)
            for r in conn.execute(
                """SELECT nganh, dt, lg, dt_doi_chieu, dt_cung_ky, chenh_lech, tang_truong
                     FROM mart.nganh_so_sanh_khoang(%s, %s, %s, %s, %s, %s)
                    ORDER BY chenh_lech, nganh""",
                (kx.tu, kx.den, s.tu_nay if co else None, s.den_nay if co else None,
                 s.tu if co else None, s.den if co else None)).fetchall()]


def mat_hang(conn, kx: KhoangXem) -> list[dict]:
    """Mọi mã hàng của khoảng — cùng hình dạng `BaoCao.hang_theo_nganh`."""
    return [{"ma": r[0], "ten": r[1], "nhom": r[2], "doanh_thu": _i(r[3]), "lai_gop": _i(r[4]),
             "ty_suat": float(r[5]) if r[5] is not None else None, "so_khach": r[7]}
            for r in conn.execute(
                """SELECT product_code, ten_hang, food_category_name, dt, lg, ty_suat, so_luong, so_khach
                     FROM mart.mat_hang_khoang(%s, %s)""", (kx.tu, kx.den)).fetchall()]


def sale(conn, kx: KhoangXem) -> list[dict]:
    """Theo người phụ trách — cùng hình dạng `BaoCao.nhan_vien`."""
    return [dict(zip(("ma", "doanh_thu", "lai_gop", "ty_suat", "so_khach", "so_phieu"),
                     (r[0], int(r[1] or 0), int(r[2] or 0),
                      float(r[3]) if r[3] is not None else None, r[4], r[5])))
            for r in conn.execute(
                """SELECT salesperson_code, dt, lg, ty_suat, so_khach, so_phieu
                     FROM mart.sale_khoang(%s, %s) ORDER BY dt DESC NULLS LAST""",
                (kx.tu, kx.den)).fetchall()]


def tap_trung(conn, kx: KhoangXem) -> BC.TapTrung | None:
    """20 khách lớn nhất + tổng số khách, MỘT lượt đọc (`count(*) OVER ()` tính
    trước LIMIT — cùng lý lẽ `bao_cao.tinh_bao_cao` bước 3)."""
    rows = conn.execute(
        """SELECT customer_code, ten_khach, dt, thu_hang, ty_trong, luy_ke, count(*) OVER ()
             FROM mart.tap_trung_khoang(%s, %s) ORDER BY thu_hang LIMIT 20""",
        (kx.tu, kx.den)).fetchall()
    if not rows:
        return None
    dong = [BC.KhachTapTrung(ma=r[0], ten=r[1], doanh_thu=int(r[2]), thu_hang=r[3],
                             ty_trong=float(r[4]) if r[4] is not None else None,
                             luy_ke=float(r[5]) if r[5] is not None else None) for r in rows]
    h10 = next((k for k in dong if k.thu_hang == 10), None)
    return BC.TapTrung(dong=dong, so_khach=rows[0][6] or 0, luy_ke_top10=h10.luy_ke if h10 else None)


def _so_thang(tu: date, den: date) -> int:
    return (den.year - tu.year) * 12 + den.month - tu.month + 1


def tinh_bao_cao(conn, kx: KhoangXem) -> BC.BaoCao:
    """Báo cáo của khoảng xem. Dạng Kỳ = `kome.bao_cao.tinh_bao_cao` nguyên vẹn
    (7 lượt hỏi) — trừ khi có kỳ so sánh tự chọn: khi đó đi nhánh khoảng để so
    đúng kỳ đã chọn. Dạng Tháng / Khoảng: 7 lượt hỏi (tổng + so sánh · chuỗi · mặt
    hàng · người phụ trách · ngành × tháng · ngành so sánh · Pareto)."""
    if kx.loai == "ky" and not kx.tu_chon:
        return BC.tinh_bao_cao(conn, kx.company_fy)
    nay, ss = tong(conn, kx)
    ky = BC.Ky(company_fy=kx.company_fy or 0, so_ky=kx.so_ky or 0, nhan=kx.nhan,
               doanh_thu=nay["dt"], lai_gop=nay["lg"], ty_suat=nay["ty_suat"],
               so_khach=nay["so_khach"], so_phieu=nay["so_phieu"],
               so_thang=_so_thang(kx.tu, kx.den), ngay_dau=kx.tu, ngay_cuoi=kx.den)
    _, thang = chuoi(conn, kx)
    hang_theo_nganh = mat_hang(conn, kx)
    return BC.BaoCao(
        ky=ky, moi_ky=[], thang=thang, hang=BC.top_lai_gop(hang_theo_nganh),
        nhan_vien=sale(conn, kx), canh_bao=list(kx.ghi_chu), cung_ky=None,
        nganh_thang=BC.doc_nganh_thang(conn, kx.company_fy) if kx.company_fy else [],
        nganh_ky=nganh(conn, kx), tap_trung=tap_trung(conn, kx),
        hang_theo_nganh=hang_theo_nganh, so_sanh=ss)


# ---- Đợt B: Khách hàng -------------------------------------------------------

def _ss_phu(kx: KhoangXem):
    """Phép so của CỘT SO SÁNH trên danh sách / hồ sơ khách: tháng trước (dạng
    Tháng) / khoảng liền trước (dạng Khoảng) — `so_sanh[1]`; dạng Kỳ chỉ có
    năm trước. Nhịp làm việc với khách là tháng này so tháng trước."""
    return kx.so_sanh[1] if len(kx.so_sanh) > 1 else kx.so_sanh[0]


def danh_ba_khoang(conn, kx: KhoangXem) -> dict:
    """Doanh số trong khoảng của MỌI khách + dải so sánh phụ — MỘT lượt hỏi
    (`mart.khach_khoang` hai dải, FULL JOIN: khách chỉ mua ở dải so sánh vẫn
    có dòng). Ghép vào danh bạ ở kome/khach_hang.py::ghep_khoang."""
    s = _ss_phu(kx)
    rows = conn.execute(
        """SELECT coalesce(a.customer_code, b.customer_code), a.dt, a.lg, a.so_phieu, b.dt
             FROM mart.khach_khoang(%s, %s) a
             FULL JOIN mart.khach_khoang(%s, %s) b USING (customer_code)""",
        (kx.tu, kx.den, s.tu if s.co else None, s.den if s.co else None)).fetchall()
    return {"khoang": kx, "so_sanh": s,
            "dong": {r[0]: [_i(r[1]), _i(r[2]), r[3], _i(r[4])] for r in rows}}


def cua_khach(conn, kx: KhoangXem, ma: str) -> dict:
    """Số trong khoảng của MỘT khách — MỘT lượt hỏi (ba khối JSON trong một
    dòng): tổng + mọi phép so (`mart.khach_khoang`), mặt hàng trong khoảng
    (`mart.khach_mat_hang_khoang`), các ngày mua trong khoảng (`mart.lan_mua`).
    Hồ sơ khách (`khach_hang.ho_so`) đã chạm trần 8 lượt hỏi — số theo khoảng
    đi endpoint RIÊNG chứ không nới trần."""
    dai = [(kx.tu, kx.den)]
    for s in kx.so_sanh:
        dai += [(s.tu_nay, s.den_nay), (s.tu, s.den) if s.co else (None, None)]
    gia_tri = ", ".join(f"({i}, %s::date, %s::date)" for i in range(len(dai)))
    r = conn.execute(
        f"""SELECT
              (SELECT json_agg(json_build_object('i', v.i, 'dt', t.dt, 'lg', t.lg,
                                                 'so_phieu', t.so_phieu, 'so_ngay', t.so_ngay_mua) ORDER BY v.i)
                 FROM (VALUES {gia_tri}) v(i, tu, den)
                 LEFT JOIN LATERAL (SELECT * FROM mart.khach_khoang(v.tu, v.den) k
                                     WHERE k.customer_code = %s) t ON true),
              (SELECT coalesce(json_agg(json_build_object('ma', m.product_code, 'ten', m.ten_hang,
                                  'doanh_thu', m.dt, 'lai_gop', m.lg, 'so_luong', m.so_luong,
                                  'so_ngay', m.so_ngay_mua, 'lan_cuoi', m.lan_cuoi)
                                  ORDER BY m.dt DESC NULLS LAST, m.product_code), '[]')
                 FROM mart.khach_mat_hang_khoang(%s, %s) m WHERE m.customer_code = %s),
              (SELECT coalesce(json_agg(json_build_object('ngay', l.sales_date, 'so_phieu', l.n,
                                  'doanh_thu', l.dt) ORDER BY l.sales_date DESC), '[]')
                 FROM (SELECT sales_date, count(*) AS n, sum(doanh_thu_thuan) AS dt
                         FROM mart.lan_mua WHERE customer_code = %s AND sales_date BETWEEN %s AND %s
                        GROUP BY 1) l)""",
        [d for cap in dai for d in cap] + [ma, kx.tu, kx.den, ma, ma, kx.tu, kx.den]).fetchone()
    t = {x["i"]: x for x in (r[0] or [])}

    def so(i, k):
        v = (t.get(i) or {}).get(k)
        return int(v) if v is not None else 0
    ss = []
    for j, s in enumerate(kx.so_sanh):
        ss.append(BC.SoSanhSo(
            ma=s.ma, nhan=s.nhan, co=s.co, tu=s.tu, den=s.den, tu_nay=s.tu_nay, den_nay=s.den_nay,
            dt=so(1 + 2 * j, "dt"), lg=so(1 + 2 * j, "lg"), so_khach=None,
            dt_ck=so(2 + 2 * j, "dt") if s.co else None, lg_ck=so(2 + 2 * j, "lg") if s.co else None,
            so_khach_ck=None))
    return {"khoang": kx,
            "tong": {"dt": so(0, "dt"), "lg": so(0, "lg"), "so_phieu": so(0, "so_phieu"),
                     "so_ngay": so(0, "so_ngay"),
                     "ty_suat": BC._SoCungKy._ty_suat(so(0, "dt"), so(0, "lg"))},
            "so_sanh": ss, "mat_hang": r[1], "ngay": r[2]}


# ---- Đợt C: Sản phẩm ---------------------------------------------------------

def danh_muc_khoang(conn, kx: KhoangXem) -> dict:
    """Doanh số trong khoảng của MỌI mã + dải so sánh phụ — MỘT lượt hỏi
    (`mart.mat_hang_khoang` hai dải, FULL JOIN). Giao diện ghép vào danh mục
    theo mã (không cộng / chia gì thêm)."""
    s = _ss_phu(kx)
    rows = conn.execute(
        """SELECT coalesce(a.product_code, b.product_code), a.dt, a.lg, a.so_luong, a.so_khach, b.dt
             FROM mart.mat_hang_khoang(%s, %s) a
             FULL JOIN mart.mat_hang_khoang(%s, %s) b USING (product_code)""",
        (kx.tu, kx.den, s.tu if s.co else None, s.den if s.co else None)).fetchall()
    return {"khoang": kx, "so_sanh": s,
            "dong": {r[0]: [_i(r[1]), _i(r[2]), float(r[3]) if r[3] is not None else None, r[4], _i(r[5])]
                     for r in rows}}


def cua_ma(conn, kx: KhoangXem, ma: str, gioi_han: int = 30) -> dict:
    """Một mã trong khoảng — MỘT lượt hỏi: tổng + phép so phụ
    (`mart.mat_hang_khoang`) và khách mua mã này trong khoảng
    (`mart.khach_mat_hang_khoang`, `gioi_han` khách doanh thu cao nhất + tổng số khách)."""
    s = _ss_phu(kx)
    r = conn.execute(
        """SELECT
              (SELECT json_build_object('dt', a.dt, 'lg', a.lg, 'so_luong', a.so_luong, 'so_khach', a.so_khach)
                 FROM mart.mat_hang_khoang(%s, %s) a WHERE a.product_code = %s),
              (SELECT b.dt FROM mart.mat_hang_khoang(%s, %s) b WHERE b.product_code = %s),
              (SELECT coalesce(json_agg(json_build_object('ma', x.customer_code, 'ten', x.ten,
                                  'doanh_thu', x.dt, 'so_luong', x.so_luong, 'so_ngay', x.so_ngay_mua,
                                  'lan_cuoi', x.lan_cuoi) ORDER BY x.dt DESC NULLS LAST, x.customer_code), '[]')
                 FROM (SELECT k.*, coalesce(nullif(c.customer_name, ''), k.customer_code) AS ten
                         FROM mart.khach_mat_hang_khoang(%s, %s) k
                         LEFT JOIN core.dim_customer c ON c.customer_code = k.customer_code AND c.is_current
                        WHERE k.product_code = %s
                        ORDER BY k.dt DESC NULLS LAST, k.customer_code LIMIT %s) x)""",
        (kx.tu, kx.den, ma, s.tu if s.co else None, s.den if s.co else None, ma,
         kx.tu, kx.den, ma, gioi_han)).fetchone()
    t = r[0] or {}
    dt = int(t.get("dt") or 0)
    return {"khoang": kx, "so_sanh": s,
            "tong": {"dt": dt, "lg": int(t.get("lg") or 0), "so_luong": t.get("so_luong") or 0,
                     "so_khach": t.get("so_khach") or 0},
            "dt_ss": (int(r[1] or 0) if s.co else None),
            "tang": BC._SoCungKy._tang(dt, int(r[1] or 0)) if s.co else None,
            "khach": r[2]}
