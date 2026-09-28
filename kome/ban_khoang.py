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
    dài hơn — kèm kỳ so đang bật (`so_sanh[0]`) khớp theo thứ tự.
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
        c = ck[i] if i < len(ck) else None
        dt_ck = int(c[2]) if c else None
        lg_ck = int(c[3]) if c else None
        ra.append(BC.O(
            thang=r[1], doanh_thu=dt, lai_gop=lg, ty_suat=BC._SoCungKy._ty_suat(dt, lg),
            co_cung_ky=dt_ck is not None, tang_truong=BC._SoCungKy._tang(dt, dt_ck),
            la_thang_chot=kieu == "thang" and r[1].endswith("-07"),
            so_phieu=r[4], so_khach=r[5], dt_cung_ky=dt_ck,
            lg_cung_ky=lg_ck, so_khach_cung_ky=c[5] if c else None,
            ty_suat_cung_ky=BC._SoCungKy._ty_suat(dt_ck, lg_ck) if c else None))
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
             "ty_suat": float(r[5]) if r[5] is not None else None, "so_khach": r[7],
             "la_phi": r[8], "la_hang_tang": r[9], "so_luong": float(r[6]) if r[6] is not None else None,
             "la_ngung_ban_het_ton": r[10]}
            for r in conn.execute(
                """SELECT product_code, ten_hang, food_category_name, dt, lg, ty_suat, so_luong, so_khach,
                          la_phi, la_hang_tang, la_ngung_ban_het_ton
                     FROM mart.mat_hang_khoang(%s, %s)""", (kx.tu, kx.den)).fetchall()]


def sale(conn, kx: KhoangXem) -> list[dict]:
    """Theo người phụ trách — cùng hình dạng `BaoCao.nhan_vien`, kèm doanh thu KỲ SO
    (`dt_ss`, dải `s.tu → s.den`) và phần khoảng xem đem so (`dt_nay_ss`) trong CÙNG
    câu (FULL JOIN: người chỉ bán ở kỳ so vẫn có dòng). Kỳ so không có dữ liệu:
    `dt_ss` None."""
    s = kx.so_sanh[0] if kx.so_sanh else None
    co = s is not None and s.co
    rows = conn.execute(
        """WITH a AS (SELECT * FROM mart.sale_khoang(%s, %s)),
                s AS (SELECT salesperson_code, dt FROM mart.sale_khoang(%s, %s)),
                n AS (SELECT salesperson_code, dt FROM mart.sale_khoang(%s, %s))
           SELECT coalesce(a.salesperson_code, s.salesperson_code), a.dt, a.lg, a.ty_suat,
                  a.so_khach, a.so_phieu, s.dt, n.dt
             FROM a FULL JOIN s ON coalesce(s.salesperson_code, '') = coalesce(a.salesperson_code, '')
             LEFT JOIN n ON coalesce(n.salesperson_code, '') = coalesce(a.salesperson_code, s.salesperson_code, '')
            ORDER BY a.dt DESC NULLS LAST""",
        (kx.tu, kx.den, s.tu if co else None, s.den if co else None,
         s.tu_nay if co else None, s.den_nay if co else None)).fetchall()
    return [dict(zip(("ma", "doanh_thu", "lai_gop", "ty_suat", "so_khach", "so_phieu", "dt_ss", "dt_nay_ss"),
                     (r[0], int(r[1] or 0), int(r[2] or 0),
                      float(r[3]) if r[3] is not None else None, r[4] or 0, r[5] or 0,
                      int(r[6] or 0) if co else None, int(r[7] or 0) if co else None)))
            for r in rows]


def nganh_thang_ss(conn, kx: KhoangXem) -> list[BC.NganhThang]:
    """Ngành × tháng của KỲ chứa ngày cuối khoảng, so với tháng dời `lech_thang` của
    kỳ so đang bật — cho bản đồ nhiệt + luỹ kế kỳ so (đặc tả 2026-09-28). MỘT lượt
    hỏi, thay `bao_cao.doc_nganh_thang` (cùng hình dạng + lãi gộp). Cùng hai luật của
    `mart.ban_theo_nganh_thang_so_sanh`: FULL JOIN (ngành chỉ bán ở tháng so vẫn có
    dòng doanh thu 0) và chỉ tháng của kỳ nằm trong dải dữ liệu; view đọc 2 lần nên vào CTE
    MATERIALIZED. `co_cung_ky` = tháng dời nằm trong dải dữ liệu (tháng dời không có
    phiếu mà vẫn trong dải = bán 0). Tăng trưởng = `_SoCungKy._tang` (mẫu số > 0).
    Kỳ so không lệch tròn tháng: không so ô nào."""
    s = kx.so_sanh[0] if kx.so_sanh else None
    lech = s.lech_thang if s is not None and s.co else None
    rows = conn.execute(
        """WITH n AS MATERIALIZED (SELECT thang, company_fy, nganh, doanh_thu_thuan AS dt, lai_gop AS lg
                                     FROM mart.ban_theo_nganh_thang),
                -- Mọi tháng của kỳ trong DẢI DỮ LIỆU (tới mốc) — kể cả tháng không bán
                -- gì: luỹ kế kỳ so cần đủ tháng, và tháng dời vẫn có thể có số.
                th AS (SELECT DISTINCT to_char(date_key, 'YYYY-MM') AS thang FROM core.dim_date
                        WHERE company_fy = %(fy)s
                          AND date_key BETWEEN date_trunc('month', (SELECT min(sales_date) FROM core.fact_sales_line))
                                           AND (SELECT hom_nay FROM mart.moc_thoi_gian)),
                a AS (SELECT thang, nganh, dt, lg FROM n WHERE company_fy = %(fy)s),
                b AS (SELECT to_char(to_date(thang, 'YYYY-MM') + make_interval(months => %(lech)s::int), 'YYYY-MM') AS thang,
                             nganh, dt, lg FROM n WHERE %(lech)s::int IS NOT NULL)
           SELECT coalesce(a.thang, b.thang), coalesce(a.nganh, b.nganh), a.dt, a.lg, b.dt, b.lg
             FROM a FULL JOIN b ON b.thang = a.thang AND b.nganh = a.nganh
            WHERE coalesce(a.thang, b.thang) IN (SELECT thang FROM th)
            ORDER BY 2, 1""", {"fy": kx.company_fy, "lech": lech}).fetchall()
    dau = kx.ngay_dau.strftime("%Y-%m")
    ra = []
    for r in rows:
        dt = int(r[2] or 0)
        co = lech is not None and _doi(r[0], -lech) >= dau
        ck = int(r[4] or 0) if co else None
        ra.append(BC.NganhThang(thang=r[0], nganh=r[1], doanh_thu=dt, dt_cung_ky=ck, co_cung_ky=co,
                                tang_truong=BC._SoCungKy._tang(dt, ck) if co else None,
                                lai_gop=int(r[3] or 0), lg_cung_ky=int(r[5] or 0) if co else None))
    return ra


def _doi(thang: str, n: int) -> str:
    """'YYYY-MM' dời n tháng."""
    t = int(thang[:4]) * 12 + int(thang[5:7]) - 1 + n
    return f"{t // 12:04d}-{t % 12 + 1:02d}"


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
        return BC.tinh_bao_cao(conn, kx.company_fy, kx.so_sanh[0] if kx.so_sanh else None)
    nay, ss = tong(conn, kx)
    ky = BC.Ky(company_fy=kx.company_fy or 0, so_ky=kx.so_ky or 0, nhan=kx.nhan,
               doanh_thu=nay["dt"], lai_gop=nay["lg"], ty_suat=nay["ty_suat"],
               so_khach=nay["so_khach"], so_phieu=nay["so_phieu"],
               so_thang=_so_thang(kx.tu, kx.den), ngay_dau=kx.tu, ngay_cuoi=kx.den)
    _, thang = chuoi(conn, kx)
    nt = nganh_thang_ss(conn, kx) if kx.company_fy else []
    # Tổng kỳ so theo tháng — cộng TRƯỚC khi tách phí / POSM (Σ ngành = tổng tháng).
    thang_ss: dict[str, list] = {}
    for n in nt:
        if n.co_cung_ky:
            t = thang_ss.setdefault(n.thang, [0, 0])
            t[0] += n.dt_cung_ky or 0
            t[1] += n.lg_cung_ky or 0
    hang_theo_nganh, nganh_ky, nganh_thang, phi, hang_tang = BC.tach_phi(
        mat_hang(conn, kx), nganh(conn, kx), nt)
    return BC.BaoCao(
        ky=ky, moi_ky=[], thang=thang, hang=BC.top_lai_gop(hang_theo_nganh),
        nhan_vien=sale(conn, kx), canh_bao=list(kx.ghi_chu), cung_ky=None,
        nganh_thang=nganh_thang, nganh_ky=nganh_ky, tap_trung=tap_trung(conn, kx),
        hang_theo_nganh=hang_theo_nganh, so_sanh=ss, phi=phi, hang_tang=hang_tang,
        thang_ss=thang_ss)


# ---- Đợt B: Khách hàng -------------------------------------------------------

def danh_ba_khoang(conn, kx: KhoangXem) -> dict:
    """Doanh số trong khoảng của MỌI khách + kỳ so đang bật — MỘT lượt hỏi
    (`mart.khach_khoang` hai dải, FULL JOIN: khách chỉ mua ở dải so sánh vẫn
    có dòng). Ghép vào danh bạ ở kome/khach_hang.py::ghep_khoang."""
    s = kx.so_sanh[0]
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
                                  'so_ngay', m.so_ngay_mua, 'lan_cuoi', m.lan_cuoi,
                                  'la_phi', m.la_phi, 'la_hang_tang', m.la_hang_tang,
                                  'la_ngung_ban_het_ton', m.la_ngung_ban_het_ton)
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
    """Doanh số trong khoảng của MỌI mã + kỳ so đang bật — MỘT lượt hỏi
    (`mart.mat_hang_khoang` hai dải, FULL JOIN). Giao diện ghép vào danh mục
    theo mã (không cộng / chia gì thêm)."""
    s = kx.so_sanh[0]
    rows = conn.execute(
        """SELECT coalesce(a.product_code, b.product_code), a.dt, a.lg, a.so_luong, a.so_khach, b.dt
             FROM mart.mat_hang_khoang(%s, %s) a
             FULL JOIN mart.mat_hang_khoang(%s, %s) b USING (product_code)""",
        (kx.tu, kx.den, s.tu if s.co else None, s.den if s.co else None)).fetchall()
    return {"khoang": kx, "so_sanh": s,
            "dong": {r[0]: [_i(r[1]), _i(r[2]), float(r[3]) if r[3] is not None else None, r[4], _i(r[5])]
                     for r in rows}}


def cua_ma(conn, kx: KhoangXem, ma: str, gioi_han: int = 30) -> dict:
    """Một mã trong khoảng — MỘT lượt hỏi: tổng + kỳ so đang bật
    (`mart.mat_hang_khoang`) và khách mua mã này trong khoảng
    (`mart.khach_mat_hang_khoang`, `gioi_han` khách doanh thu cao nhất + tổng số khách)."""
    s = kx.so_sanh[0]
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
