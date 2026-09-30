"""Bảng giá KOME (/bang-gia) — mọi mã × quy cách × 売価No., kèm lần nạp trước.

Chỉ đọc: giá là dữ liệu OBC (取引単価データ) — sửa trong OBC rồi nạp lại. Mọi định nghĩa (lần nạp mới nhất ≤ mốc, luật
hai cột thuế, đã đổi, dưới giá vốn) ở `mart.bang_gia_kome` (071); "thiếu kg" = mã có giá mà không có dòng nào trong
`mart.gia_kome_bang` (tức không vào được phần so với đối thủ). Danh sách mã = danh mục /san-pham (bỏ phí / POSM / ※終売※
hết tồn — 048–050). Lọc / đếm ở trình duyệt (giao_dien/src/bang_gia/loc.ts).
"""
from __future__ import annotations

from kome.san_pham import QUY_CACH

# 標準価格 trước, rồi 売価No. theo số. 売価No.10 = khuyến mãi (mart.la_gia_km_kome, 066) — cùng nhãn san_pham_360.NHAN_BAC.
NHAN_BAC = {"std": "標準価格", "10": "No.10 · KM"}

_SQL = """
WITH dm AS (
    SELECT p.product_code AS ma, coalesce(nullif(p.product_name, ''), p.product_code) AS ten,
           mart.ten_nganh(p.food_category_name) AS nganh, mart.la_ngung_ban(p.rank_code, p.product_name) AS ngung_ban
    FROM mart.dim_product p
    WHERE NOT mart.khong_phai_hang(p.product_code, p.kind_code, p.food_category_name)
      AND NOT EXISTS (SELECT 1 FROM mart.ma_ngung_ban_an a WHERE a.product_code = p.product_code)
)
SELECT (SELECT coalesce(json_agg(json_build_array(ma, ten, nganh, ngung_ban) ORDER BY ma), '[]') FROM dm),
       (SELECT coalesce(json_agg(json_build_array(b.product_code, b.pack_code, b.price_level, b.hien_hanh, b.tu_ngay,
                                                  b.tu_ngay_truoc, round(b.gia_chua_thue), round(b.gia_truoc),
                                                  b.hai_cot_lech, b.gia_von, b.doi, b.duoi_gia_von)
                                 ORDER BY b.product_code, b.pack_code, b.price_level), '[]')
          FROM mart.bang_gia_kome b WHERE b.product_code IN (SELECT ma FROM dm)),
       (SELECT coalesce(json_agg(DISTINCT product_code), '[]') FROM mart.gia_kome_bang)
"""


def _thu_bac(lv: str):
    return (0, 0) if lv == "std" else (1, int(lv)) if lv.isdigit() else (2, lv)


def nhan_bac(lv: str) -> str:
    return NHAN_BAC.get(lv, f"No.{int(lv)}" if lv.isdigit() else lv)


def du_lieu(conn) -> dict:
    """ĐÚNG MỘT lượt hỏi. Giá là yên chưa thuế, làm tròn (bẫy #2: tiền là số nguyên)."""
    ds_ma, ds_gia, co_kg = conn.execute(_SQL).fetchone()
    co_kg = set(co_kg)
    ma = {m: {"ma": m, "ten": t, "nganh": n, "ngung_ban": bool(nb), "dong": []} for m, t, n, nb in ds_ma}
    dong: dict[tuple, dict] = {}
    bac, moi_nhat = set(), None
    for m, qc, lv, hh, tu, tu_tr, gia, truoc, lech, von, doi, duoi in ds_gia:
        d = dong.get((m, qc))
        if d is None:
            d = dong[(m, qc)] = {"qc": qc, "ten_qc": QUY_CACH.get(qc, qc), "tu": tu, "tu_truoc": tu_tr,
                                 "gia_von": None, "g": {}}
            ma[m]["dong"].append(d)
        if hh and von is not None:
            d["gia_von"] = int(von)
        d["g"][lv] = {"gia": None if gia is None else int(gia), "truoc": None if truoc is None else int(truoc),
                      "lech": bool(lech), "doi": bool(doi), "duoi": bool(duoi), "bo": not hh}
        bac.add(lv)
        moi_nhat = max(moi_nhat or tu, tu)
    for m in ma.values():
        m["thieu_kg"] = any(not x["bo"] for d in m["dong"] for x in d["g"].values()) and m["ma"] not in co_kg
    bac_xep = sorted(bac, key=_thu_bac)
    return {
        "bac": [{"ma": lv, "nhan": nhan_bac(lv)} for lv in bac_xep],
        "ma": list(ma.values()),
        "nganh": sorted({m["nganh"] for m in ma.values()}),
        "moi_nhat": moi_nhat,
    }
