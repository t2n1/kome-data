"""Nhìn theo THÁNG: khách quen nào tháng này chưa mua (migration 036).

MỘT định nghĩa — `mart.khach_thang_nay.nhan`. Mọi màn ĐỌC nhãn và SO BẰNG
(`= 'tre'`), không màn nào tự tính lại "mua đều" hay "đến cùng ngày". Khác
nhóm 'im' (im lặng >= 2x nhịp mua riêng) của `mart.khach_nhom_viec`: đó là
theo nhịp riêng của khách, đây là theo tháng lịch. Hai tên, không gộp.
"""
from __future__ import annotations

# Nhãn của view, theo thứ tự xét (xem chú thích đầu 036).
NHAN = {
    "khong_goi": "Đã đóng cửa / ngừng giao dịch",
    "da_mua": "Tháng này đã mua",
    "tre": "Mua đều, tháng này chưa",
    "chua_toi_ngay": "Mua đều, chưa tới ngày thường mua",
    "khac": "Không mua đều, tháng này chưa mua",
}

# Một câu in dưới mọi khối dùng nhãn 'tre' — cách tính phải đọc được ngay.
CACH_TINH = ("Mua ≥ 2 trong 3 tháng trước, và ≥ 2 tháng trong đó đã có đơn "
             "đến cùng ngày này — tháng này chưa có đơn.")


def chua_mua(conn, sale: str | None = None, gioi_han: int = 40) -> dict:
    """Khối Tổng quan: bộ đếm theo nhãn (TOÀN CÔNG TY) + danh sách 'tre'
    (lọc theo `sale`, như khối "Cần gọi hôm nay"). MỘT lượt hỏi; view vào
    CTE MATERIALIZED vì câu này đọc nó hai lần."""
    dk, ts = ("AND salesperson_code = %s", [sale]) if sale else ("", [])
    rows = conn.execute(
        f"""WITH k AS MATERIALIZED (SELECT * FROM mart.khach_thang_nay)
            SELECT 'd' AS loai, nhan, count(*)::int, NULL::text, NULL::text, NULL::text,
                   NULL::text, NULL::text, NULL::int, NULL::bigint, NULL::numeric, NULL::numeric
              FROM k GROUP BY nhan
            UNION ALL
            SELECT 'c', NULL, count(*) FILTER (WHERE thang_truoc_den_ngay AND nhan <> 'khong_goi')::int,
                   max(thang), max(ngay_moc)::text, NULL, NULL, NULL, NULL, NULL, NULL, NULL
              FROM k
            UNION ALL
            SELECT * FROM (
              SELECT 'k', nhan, NULL::int, thang, ngay_moc::text, customer_code, ten,
                     salesperson_code, so_thang_mua_3, dt_tb_3_thang,
                     dt_thang_truoc, dt_thang_nay
                FROM k WHERE nhan = 'tre' {dk}
               ORDER BY dt_tb_3_thang DESC, customer_code LIMIT %s) t""",
        ts + [gioi_han]).fetchall()
    dem = {r[1]: r[2] for r in rows if r[0] == "d"}
    c = next((r for r in rows if r[0] == "c"), None)
    so_tre = sum(1 for r in rows if r[0] == "k")
    return {
        "thang": c[3] if c else None, "ngay_moc": c[4] if c else None,
        "dem": {k: dem.get(k, 0) for k in NHAN}, "nhan": NHAN, "cach_tinh": CACH_TINH,
        "thang_truoc_den_ngay": c[2] if c else 0,
        "sale": sale, "du": so_tre < gioi_han,
        "khach": [{"ma": r[5], "ten": r[6], "sale": r[7], "so_thang": r[8],
                   "tb_thang": int(r[9] or 0), "thang_truoc": int(r[10] or 0)}
                  for r in rows if r[0] == "k"],
    }
