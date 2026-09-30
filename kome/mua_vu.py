"""Mùa vụ sản phẩm (/mua-vu) — dữ liệu mã × ngày cho treemap kéo theo thời gian.

Đặc tả: docs/superpowers/specs/2026-09-29-mua-vu-san-pham-design.md. Chỉ số ở
mart.mua_vu_ngay (058); ở đây chỉ đổi sang dạng CỘT gọn (~48.000 dòng thật — một
object mỗi dòng là gấp mấy lần cỡ JSON). Cửa sổ 7/30/90 ngày cộng ở trình duyệt
(giao_dien/src/mua_vu/du_lieu.ts) — kéo thanh không hỏi lại máy chủ.
"""
from __future__ import annotations

# Hai mã giả của 058 — phải khớp chữ trong migration.
MA_PHI = "__phi"
MA_TANG = "__tang"

_SQL = """
WITH v AS MATERIALIZED (SELECT * FROM mart.mua_vu_ngay),
dm AS (
    SELECT x.ma,
           CASE x.ma WHEN %(phi)s THEN 'Phí & điều chỉnh'
                     WHEN %(tang)s THEN 'Hàng tặng (POSM)'
                     ELSE coalesce(nullif(p.product_name, ''), x.ma) END AS ten,
           CASE WHEN x.ma IN (%(phi)s, %(tang)s) THEN ''
                ELSE mart.ten_nganh(p.food_category_name) END           AS nganh,
           (x.ma IN (SELECT product_code FROM mart.ma_ngung_ban_an))    AS an
    FROM (SELECT DISTINCT ma FROM v) x
    LEFT JOIN mart.dim_product p ON p.product_code = x.ma
)
SELECT (SELECT min(ngay) FROM v), (SELECT max(ngay) FROM v),
       (SELECT coalesce(json_agg(json_build_array(ma, ten, nganh, an) ORDER BY ma), '[]')
          FROM dm),
       (SELECT coalesce(json_agg(json_build_array(ma, ngay, doanh_thu_thuan, lai_gop, so_luong)
                                 ORDER BY ma, ngay), '[]')
          FROM v)
"""


def du_lieu(conn) -> dict:
    """ĐÚNG MỘT lượt hỏi. `dong.d` = số ngày tính từ `ngay_dau`; `dong.i` = chỉ số
    trong `ma`. Tiền là số nguyên, số lượng là số thập phân (bẫy #2)."""
    from datetime import date
    dau, cuoi, ds_ma, ds_dong = conn.execute(_SQL, {"phi": MA_PHI, "tang": MA_TANG}).fetchone()
    ma = [{"ma": m, "ten": t, "nganh": n, "an": bool(a)} for m, t, n, a in ds_ma]
    vi_tri = {m["ma"]: k for k, m in enumerate(ma)}
    dong = {"i": [], "d": [], "dt": [], "lg": [], "sl": []}
    for m, ngay, dt, lg, sl in ds_dong:
        dong["i"].append(vi_tri[m])
        dong["d"].append((date.fromisoformat(ngay) - dau).days)
        dong["dt"].append(int(dt or 0))
        dong["lg"].append(int(lg or 0))
        dong["sl"].append(float(sl or 0))
    return {
        "ngay_dau": dau.isoformat() if dau else None,
        "ngay_cuoi": cuoi.isoformat() if cuoi else None,
        "ma": ma,
        "nganh": sorted({m["nganh"] for m in ma if m["nganh"]}),
        "dong": dong,
        "phi": vi_tri.get(MA_PHI),
        "tang": vi_tri.get(MA_TANG),
    }
