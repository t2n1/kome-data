"""Sản phẩm 360 — trang riêng `/san-pham/{mã}` (đặc tả 2026-09-26-san-pham-360-trang-rieng-design.md).

`ho_so` phục vụ lúc MỞ trang (trần 5 lượt hỏi). Bốn hàm `tab_*` phục vụ từng tab, tải khi bấm.
Chỉ số mới là hàm `mart.sp_*` (migration 051–053) — Python không định nghĩa chỉ số, chỉ hỏi
và đổi hình dạng.
"""
from kome.san_pham import _COT, _so, _sp, LOAI_HAN, QUY_CACH

# Một câu cách tính cho mỗi khối — màn in ngay dưới khối (nút "Cách tính").
CACH_TINH = {
    "thang": "doanh thu thuần (chưa thuế) theo tháng; cột mờ = cùng tháng năm trước",
    "mua_lai": "ngày dự kiến = lần mua cuối + nhịp mua riêng của cặp khách–mã (≥ 3 lần mua) · "
               "cùng cách tính khối \"Mã đến ngày mua lại\" của hồ sơ khách",
    "nen_chao": "khách đang mua đều ít nhất một mã CÙNG NGÀNH mà chưa từng mua mã này · "
                "xếp theo doanh thu ngành đó 12 tháng · bỏ khách ※廃業※/※取引停止※",
    "tap_trung": "doanh thu thuần 12 tháng tới mốc, gộp theo khách, luỹ kế từ khách lớn nhất",
    "tinh": "tỉnh theo hồ sơ khách hiện hành · doanh thu thuần 12 tháng",
    "nguoi": "người phụ trách ghi trên từng dòng bán · 12 tháng",
    "khach_moi": "khách mới = tháng đó là lần đầu khách mua mã này; tháng có mua = doanh thu thuần > 0",
    "tuan": "26 tuần (thứ Hai → Chủ nhật) tới tuần chứa mốc",
    "nhip": "nhịp mua riêng của từng cặp khách–mã (trung vị khoảng cách, cần ≥ 3 lần mua)",
    "co_don": "số lượng trên từng dòng bán theo quy cách, 12 tháng · dòng âm là hàng trả lại (赤伝), đếm riêng",
    "don_gia": "đơn giá thực = tổng doanh thu thuần ÷ tổng số lượng, theo tháng và quy cách",
    "bien": "biên lãi gộp = tổng lãi gộp ÷ tổng doanh thu thuần của tháng",
    "khach_gia": "khách có doanh thu thuần > 0 và mua ≥ 2 ngày trong 12 tháng · đơn giá theo quy cách "
                 "bán nhiều nhất của mã",
    "mua_kem": "trong các phiếu 12 tháng có mã này: mã khác xuất hiện trên bao nhiêu % số phiếu đó · "
               "bỏ phí, hàng tặng, hàng ngừng kinh doanh đã hết tồn",
}


def _thang_lui(t: str, n: int) -> str:
    y, m = int(t[:4]), int(t[5:7]) - n
    while m <= 0:
        m += 12
        y -= 1
    return f"{y}-{m:02d}"


def _ton_lo(conn, ma: str) -> list[dict]:
    """Tồn theo LÔ (042, bẫy #6), xếp theo thứ tự bán. 1 lượt hỏi."""
    return [{"kho": t[0], "ten_kho": t[1], "so_luong": _so(t[2]),
             "gia_tri": int(t[3] or 0), "best_before": t[4], "loai_han": t[5],
             "nhan_han": LOAI_HAN.get(t[5], (t[5] or "—", "nhat"))[0],
             "mau_han": LOAI_HAN.get(t[5], (t[5] or "—", "nhat"))[1],
             "han_con_lai": t[6], "vai_tro_lo": t[7],
             "bat_dau_ban_sau": _so(t[8]), "ban_het_sau": _so(t[9]),
             "khong_kip_ban": t[10], "sap_chuyen_lo": t[11]}
            for t in conn.execute(
        """SELECT warehouse_code, ten_kho, so_luong, gia_tri, best_before,
                  loai_han, han_con_lai, vai_tro_lo, bat_dau_ban_sau,
                  ban_het_sau, khong_kip_ban, sap_chuyen_lo
           FROM mart.ton_theo_lo WHERE product_code = %s
           ORDER BY thu_tu_lo""", (ma,)).fetchall()]


def _khach_dang_ngung(conn, ma: str) -> tuple[list[dict], list[dict]]:
    """Khách đang mua (top 20) / đã ngừng mua (top 10) mã này — ĐỌC trang_thai_cap (024).
    1 lượt hỏi. (Chuyển nguyên từ SP.ho_so cũ.)

    Hai khối khách gộp làm MỘT lượt hỏi: cùng một view, cùng bộ cột, chỉ khác
    vị từ — đúng ca mà UNION ALL không phải đệm NULL cho nhánh nào.

    HAI KHỐI ĐỌC `trang_thai_cap` CỦA mart.khach_mat_hang (migration 024),
    không viết lại vị từ ở đây. Đó là định nghĩa DUY NHẤT của "cặp (khách,
    mã) đang ở trạng thái nào", dùng chung với hai khối của /khach-hang/{mã}
    — trước 024 hai màn có hai công thức và trả lời ngược nhau về cùng một
    cặp.

    Nhãn ba giá trị: `'khong_goi'` (khách bị OBC đánh dấu ※廃業※, xét trước
    hết), `'ngung'` (im lặng >= 2 × NHỊP RIÊNG của chính cặp đó), `'mua'`
    (còn lại). Không phải ngưỡng chung: đo thật, ngưỡng 90 ngày bỏ sót 49
    khách đang rời đi và báo động nhầm 34 khách vẫn mua bình thường. Khách
    mua 7 ngày/lần im 60 ngày đã rời đi từ lâu; khách mua 120 ngày/lần im
    100 ngày vẫn đang mua bình thường.

    MỖI NHÁNH SO BẰNG VỚI ĐÚNG NHÃN CỦA MÌNH, KHÔNG NHÁNH NÀO DÙNG `NOT`.
    Hai khối này là DANH SÁCH BÁN HÀNG, nên cả hai đều không được chứa khách
    đã đóng cửa — và `'khong_goi'` là một giá trị RIÊNG nên nó tự rơi ra
    ngoài cả hai mà không nhánh nào phải biết ※廃業※ là gì. Bản trước của 024
    dùng boolean `ngung_mua` gói cổng ※廃業※ vào bên trong, nên `NOT
    ngung_mua` LUÔN đúng với một doanh nghiệp đã đóng cửa: họ trượt thẳng từ
    khối "đã ngừng" sang khối "ĐANG mua mã này" — trang khẳng định một công
    ty đã phá sản vẫn đang lấy hàng — và nhánh 'mua' phải tự JOIN lấy
    `k.da_ngung` để đắp lại. Nhãn dẹp chỗ đắp tay đó; `da_ngung` nay chỉ được
    đọc một lần, trong view.

    Sự thật lịch sử của cặp đó KHÔNG mất: view vẫn giữ đủ dòng, và hồ sơ của
    chính khách ※廃業※ vẫn hiện bảng top-15 mặt hàng như cũ.

    `xep` là hạng TRONG TỪNG NHÁNH, tính bằng row_number() theo đúng khoá mà
    nhánh đó dùng để cắt top-N. ORDER BY ở lớp NGOÀI đọc `xep` chứ không tin
    vào thứ tự dòng của nhánh — thứ tự đó không được bảo đảm qua UNION ALL,
    và đợt 4a đã dính đúng lỗi này. (ORDER BY … LIMIT trong nhánh vẫn cần,
    nhưng để CHỌN đúng top-N, không phải để giữ thứ tự.)

    LEFT JOIN khach_360 chứ không JOIN: một khách có dòng bán thì luôn có
    dòng ở khach_360 hôm nay, nhưng mất tên khách là mất cả DÒNG nếu dùng
    INNER — và đây là khối "ai đang mua mã này", nơi thiếu một khách nguy
    hiểm hơn nhiều so với hiện mã thay cho tên. khach_360 ở đây CHỈ để lấy
    TÊN: cờ ※廃業※ không còn được đọc ở chỗ này nữa, nó đã nằm trong nhãn.

    HAI CTE `AS MATERIALIZED`, ghi TƯỜNG MINH: cả hai nhánh đều đọc
    khach_mat_hang và khach_360, mà Postgres KHÔNG gộp hai truy vấn con
    giống nhau — mỗi lần tham chiếu là một lần dựng lại cả view (khach_360
    gộp toàn bộ mart.lan_mua). Vị từ `product_code = %s` nằm BÊN TRONG CTE
    nên vẫn đẩy xuống được; vật hoá ở đây chỉ bỏ đi lần dựng THỨ HAI.
    """
    khach = conn.execute(f"""
        WITH h AS MATERIALIZED (
            SELECT customer_code, doanh_thu_thuan, so_luong, so_lan, lan_cuoi,
                   nhip_ngay, tre_ngay, trang_thai_cap
              FROM mart.khach_mat_hang WHERE product_code = %s
        ), k AS MATERIALIZED (
            SELECT customer_code, ten FROM mart.khach_360
        )
        SELECT khoi, ma, ten, doanh_thu, so_luong, so_lan, lan_cuoi, nhip, tre
        FROM (
            (SELECT 'mua'::text AS khoi, h.customer_code AS ma,
                    coalesce(nullif(k.ten, ''), h.customer_code) AS ten,
                    h.doanh_thu_thuan AS doanh_thu, h.so_luong, h.so_lan,
                    h.lan_cuoi, h.nhip_ngay AS nhip, h.tre_ngay AS tre,
                    row_number() OVER (ORDER BY h.doanh_thu_thuan DESC NULLS LAST)
                      AS xep
               FROM h
               LEFT JOIN k ON k.customer_code = h.customer_code
              WHERE h.trang_thai_cap = 'mua'
              ORDER BY h.doanh_thu_thuan DESC NULLS LAST
              LIMIT 20)
            UNION ALL
            (SELECT 'ngung', h.customer_code,
                    coalesce(nullif(k.ten, ''), h.customer_code),
                    h.doanh_thu_thuan, h.so_luong, h.so_lan, h.lan_cuoi,
                    h.nhip_ngay, h.tre_ngay,
                    row_number() OVER (ORDER BY h.doanh_thu_thuan DESC NULLS LAST)
               FROM h
               LEFT JOIN k ON k.customer_code = h.customer_code
              WHERE h.trang_thai_cap = 'ngung'
              ORDER BY h.doanh_thu_thuan DESC NULLS LAST
              LIMIT 10)
        ) u ORDER BY khoi, xep
    """, (ma,)).fetchall()

    def _khach(r):
        return {"ma": r[1], "ten": r[2], "doanh_thu": int(r[3] or 0),
                "so_luong": _so(r[4]), "so_lan": r[5], "lan_cuoi": r[6],
                "nhip": _so(r[7]), "tre": r[8]}

    khach_mua = [_khach(r) for r in khach if r[0] == "mua"]
    khach_ngung = [_khach(r) for r in khach if r[0] == "ngung"]
    return khach_mua, khach_ngung


def _bac_gia(conn, ma: str) -> list[dict]:
    """Giá theo bậc — dòng MỚI NHẤT mỗi (bậc, quy cách). 1 lượt hỏi. (Chuyển từ SP.ho_so cũ.)"""
    # DISTINCT ON … ORDER BY valid_from DESC: fact_price_list giữ LỊCH SỬ giá.
    return [{"bac": g[0], "quy_cach": QUY_CACH.get(g[1], g[1]), "pack_code": g[1],
             "gia": int(g[2]), "tu_ngay": g[3]}
            for g in conn.execute(
        """SELECT DISTINCT ON (price_level, pack_code)
                  price_level, pack_code, price_ex_tax, valid_from
           FROM core.fact_price_list WHERE product_code = %s
           ORDER BY price_level, pack_code, valid_from DESC""", (ma,)).fetchall()]


def ho_so(conn, ma: str) -> dict | None:
    """Phần mở trang của Sản phẩm 360. None nếu mã không có trong san_pham_360.

    NGÂN SÁCH: 4 lượt hỏi (trần 5, có test đếm). 1) san_pham_360 + ngành + mốc;
    2) 24 tháng; 3) tồn theo lô; 4) cột trái: khách đến ngày mua lại + khách nên chào
    + hai số đếm, gộp MỘT câu.
    """
    r = conn.execute(
        f"""SELECT {', '.join('s.' + c.strip() for c in _COT.split(','))},
                   mart.ten_nganh(p.food_category_name, p.product_code, p.kind_code),
                   (SELECT hom_nay FROM mart.moc_thoi_gian)
              FROM mart.san_pham_360 s
              LEFT JOIN core.dim_product p ON p.product_code = s.product_code
             WHERE s.product_code = %s""", (ma,)).fetchone()
    if r is None:
        return None
    sp, nganh, hom_nay = _sp(r[:16]), r[16], r[17]

    cuoi = f"{hom_nay:%Y-%m}" if hom_nay else None
    theo = {t[0]: t for t in conn.execute(
        """SELECT thang, so_luong, doanh_thu_thuan, lai_gop
             FROM mart.san_pham_theo_thang
            WHERE product_code = %s AND thang >= %s ORDER BY thang""",
        (ma, _thang_lui(cuoi, 35) if cuoi else "0000-00")).fetchall()}
    thang = []
    if cuoi:
        for i in range(23, -1, -1):
            t = _thang_lui(cuoi, i)
            x, y = theo.get(t), theo.get(_thang_lui(t, 12))
            thang.append({"thang": t, "so_luong": _so(x[1]) if x else 0.0,
                          "doanh_thu": int(x[2] or 0) if x else 0,
                          "lai_gop": int(x[3] or 0) if x else 0,
                          "dt_nam_truoc": int(y[2] or 0) if y else 0})

    ton = _ton_lo(conn, ma)

    # Cột trái — MỘT câu. `h` vật hoá khach_mat_hang của ĐÚNG mã này (vị từ trong CTE, đẩy
    # xuống được) vì ba nhánh cùng đọc nó. Vị từ "đến ngày mua lại" = của
    # kome/ho_so_khach.py::lich_mua: trang_thai_cap = 'mua' AND du_kien_lan_toi IS NOT NULL.
    trai = conn.execute("""
        WITH h AS MATERIALIZED (
            SELECT customer_code, du_kien_lan_toi, nhip_ngay, lan_cuoi, doanh_thu_thuan, trang_thai_cap
              FROM mart.khach_mat_hang WHERE product_code = %s
        ), c AS MATERIALIZED (SELECT * FROM mart.sp_khach_nen_chao(%s))
        SELECT 'lai'::text, h.customer_code, coalesce(nullif(d.customer_name, ''), h.customer_code),
               h.du_kien_lan_toi, h.nhip_ngay::numeric, h.lan_cuoi, h.doanh_thu_thuan::numeric, NULL::bigint
          FROM h LEFT JOIN core.dim_customer d ON d.customer_code = h.customer_code AND d.is_current
         WHERE h.trang_thai_cap = 'mua' AND h.du_kien_lan_toi IS NOT NULL
        UNION ALL
        (SELECT 'chao', c.customer_code, c.ten, NULL::date, NULL::numeric, c.lan_cuoi,
                c.doanh_thu_nganh, c.so_ma_nganh FROM c
          ORDER BY c.doanh_thu_nganh DESC, c.customer_code LIMIT 5)
        UNION ALL
        SELECT 'dem', NULL, NULL, NULL, count(*) FILTER (WHERE trang_thai_cap = 'mua'), NULL,
               count(*) FILTER (WHERE trang_thai_cap = 'ngung'), (SELECT count(*) FROM c)
          FROM h
    """, (ma, ma)).fetchall()

    mua_lai = sorted(
        ({"ma": x[1], "ten": x[2], "du_kien": x[3],
          "con": (x[3] - hom_nay).days if hom_nay else None,
          "nhip": _so(x[4]), "lan_cuoi": x[5], "doanh_thu": int(x[6] or 0)}
         for x in trai if x[0] == "lai"),
        key=lambda d: (d["con"], -d["doanh_thu"]))
    nen_chao = [{"ma": x[1], "ten": x[2], "lan_cuoi": x[5], "doanh_thu_nganh": int(x[6] or 0),
                 "so_ma_nganh": int(x[7] or 0)} for x in trai if x[0] == "chao"]
    dem = next(x for x in trai if x[0] == "dem")
    return {"sp": sp, "nganh": nganh, "hom_nay": hom_nay, "thang": thang, "ton": ton,
            "mua_lai": mua_lai[:10], "mua_lai_tong": len(mua_lai),
            "nen_chao": nen_chao, "nen_chao_tong": int(dem[7] or 0),
            "so_dang_mua": int(dem[4] or 0), "so_da_ngung": int(dem[6] or 0),
            "ngung_ban": sp.ngung_ban, "cach_tinh": CACH_TINH}
