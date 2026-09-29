"""Thị trường & đối thủ (/doi-thu) — đặc tả docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md.

Chỉ số ở mart (060): ở đây chỉ HỎI và gói JSON (mỗi hàm đọc ĐÚNG MỘT lượt hỏi), và GHI vào app
(mọi hàm ghi thêm một dòng app.doi_thu_nhat_ky trong CÙNG giao dịch; không commit — route commit).
Không bao giờ ghi core: sửa lỗi đọc = app.dinh_chinh_gia, giá đã đổi = app.gia_doi_thu_tay.
"""
from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation

from kome.ten_hang import chuan_ten

TRUONG_SUA = ("ten_goc", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
              "thue", "gom_ship", "kenh_gia", "muc_gia", "trang_thai")
THUE = ("chua", "co", "khong_ro")
SHIP = ("co", "khong", "khong_ro")
TRANG_THAI = ("con", "het", "sap_ve", "khong_ro")
NHAN = ("cung_hang", "thay_the", "khong")
LOC_DUYET = ("", "can_xem", "bat_thuong", "chua_ghep", "chua_xac_nhan")
DAI_TOI_DA = 300


class LoiNhap(Exception):
    """Dữ liệu người nhập không hợp lệ — route trả 400 kèm câu này."""


def _so(v, ten, duong=False):
    if v in (None, ""):
        return None
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        raise LoiNhap(f"{ten} phải là số.")
    if x < 0 or (duong and x == 0):
        raise LoiNhap(f"{ten} không được âm{' hoặc bằng 0' if duong else ''}.")
    return x


def _kiem(truong: str, v):
    if truong not in TRUONG_SUA:
        raise LoiNhap(f"Không sửa được trường '{truong}'.")
    if truong == "gia_goc":
        return None if _so(v, "Giá") is None else str(_so(v, "Giá"))
    if truong == "kg_moi_don_vi_gia":
        return None if _so(v, "Số kg", True) is None else str(_so(v, "Số kg", True))
    for ten, tap in (("thue", THUE), ("gom_ship", SHIP), ("trang_thai", TRANG_THAI)):
        if truong == ten and v not in tap:
            raise LoiNhap(f"{ten} chỉ nhận {', '.join(tap)}.")
    s = (str(v).strip() if v is not None else "")[:DAI_TOI_DA]
    if truong == "ten_goc" and not s:
        raise LoiNhap("Tên hàng không được trống.")
    return s or None


def _ghi_nhat_ky(conn, loai, doi_tuong, truoc, sau, nguoi):
    conn.execute("""INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong, truoc, sau, nguoi_dung_id)
                    VALUES (%s, %s, %s, %s, %s)""",
                 (loai, doi_tuong, json.dumps(truoc, ensure_ascii=False, default=str) if truoc is not None else None,
                  json.dumps(sau, ensure_ascii=False, default=str) if sau is not None else None, nguoi))


# ---------------------------------------------------------------- ghi

def xac_nhan(conn, fact_id: int, nguoi) -> None:
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, nguoi_dung_id) VALUES (%s, 'xac_nhan', %s)",
                 (fact_id, nguoi))
    _ghi_nhat_ky(conn, "xac_nhan", f"gia:{fact_id}", None, None, nguoi)


def sua(conn, fact_id: int, thay_doi: dict, nguoi) -> None:
    if not thay_doi:
        raise LoiNhap("Không có gì để sửa.")
    sach = {k: _kiem(k, v) for k, v in thay_doi.items()}
    cu = conn.execute(f"SELECT {', '.join(sach)} FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s",
                      (fact_id,)).fetchone()
    if cu is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    with conn.cursor() as cur:
        cur.executemany("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi, nguoi_dung_id) VALUES (%s,%s,%s,%s)",
                        [(fact_id, k, v, nguoi) for k, v in sach.items()])
    _ghi_nhat_ky(conn, "sua", f"gia:{fact_id}", dict(zip(sach, cu)), sach, nguoi)


def gia_moi(conn, du_lieu: dict, nguoi) -> int:
    """'Giá đã đổi' (có fact_goc_id) hoặc 'thêm hàng AI bỏ sót' (có ma_doi_thu + ten_goc). Loại nguồn bắt buộc."""
    ln = du_lieu.get("loai_nguon")
    if not ln or not conn.execute("SELECT 1 FROM app.loai_nguon WHERE ma=%s", (ln,)).fetchone():
        raise LoiNhap("Chọn loại nguồn của giá này.")
    goc = None
    if du_lieu.get("fact_goc_id"):
        goc = conn.execute("""SELECT ma_doi_thu, ma_hang_dt, ten_goc, quy_cach_goc, don_vi_gia, kg_moi_don_vi_gia,
                                     thue, gom_ship, kenh_gia, muc_gia
                              FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s""",
                           (int(du_lieu["fact_goc_id"]),)).fetchone()
        if goc is None:
            raise LoiNhap("Không tìm thấy dòng giá gốc.")
    k = ("ma_doi_thu", "ma_hang_dt", "ten_goc", "quy_cach_goc", "don_vi_gia", "kg_moi_don_vi_gia",
         "thue", "gom_ship", "kenh_gia", "muc_gia")
    v = dict(zip(k, goc)) if goc else {}
    for truong in TRUONG_SUA:
        if truong in du_lieu and truong != "trang_thai":
            v[truong] = _kiem(truong, du_lieu[truong])
    v["ma_doi_thu"] = v.get("ma_doi_thu") or du_lieu.get("ma_doi_thu")
    if not v.get("ma_doi_thu") or not v.get("ten_goc"):
        raise LoiNhap("Thiếu đối thủ hoặc tên hàng.")
    if not v.get("ma_hang_dt"):
        v["ma_hang_dt"] = "tay:" + chuan_ten(v["ten_goc"]) + "|" + chuan_ten(v.get("quy_cach_goc") or "")
    tt = _kiem("trang_thai", du_lieu.get("trang_thai") or "con")
    tid = conn.execute(
        """INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, fact_goc_id, ten_goc, quy_cach_goc, gia_goc,
             don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia, trang_thai, loai_nguon,
             ghi_chu_nguon, nguoi_dung_id)
           VALUES (%(ma_doi_thu)s, %(ma_hang_dt)s, %(fact_goc_id)s, %(ten_goc)s, %(quy_cach_goc)s, %(gia_goc)s,
             %(don_vi_gia)s, %(kg_moi_don_vi_gia)s, %(thue)s, %(gom_ship)s, %(kenh_gia)s, %(muc_gia)s,
             %(trang_thai)s, %(loai_nguon)s, %(ghi_chu_nguon)s, %(nguoi)s) RETURNING id""",
        {**{x: v.get(x) for x in k}, "gia_goc": v.get("gia_goc"), "fact_goc_id": du_lieu.get("fact_goc_id"),
         "trang_thai": tt, "loai_nguon": ln, "ghi_chu_nguon": (du_lieu.get("ghi_chu_nguon") or "")[:DAI_TOI_DA] or None,
         "nguoi": nguoi}).fetchone()[0]
    _ghi_nhat_ky(conn, "gia_moi" if goc else "them", f"tay:{tid}", None, v | {"loai_nguon": ln}, nguoi)
    return tid


def dat_ghep(conn, ma_doi_thu: str, ma_hang_dt: str, product_code, nhom_id, nhan: str, nguoi) -> None:
    if nhan not in NHAN:
        raise LoiNhap("Nhãn ghép chỉ nhận cùng hàng / thay thế / không ghép.")
    cu = conn.execute("SELECT product_code, nhom_id, nhan FROM app.ghep_hang WHERE ma_doi_thu=%s AND ma_hang_dt=%s",
                      (ma_doi_thu, ma_hang_dt)).fetchone()
    conn.execute("""INSERT INTO app.ghep_hang (ma_doi_thu, ma_hang_dt, product_code, nhom_id, nhan, nguoi_dung_id)
                    VALUES (%s,%s,%s,%s,%s,%s)
                    ON CONFLICT (ma_doi_thu, ma_hang_dt) DO UPDATE SET product_code=EXCLUDED.product_code,
                      nhom_id=EXCLUDED.nhom_id, nhan=EXCLUDED.nhan, nguoi_dung_id=EXCLUDED.nguoi_dung_id, luc=now()""",
                 (ma_doi_thu, ma_hang_dt, product_code or None, nhom_id or None, nhan, nguoi))
    _ghi_nhat_ky(conn, "ghep", f"{ma_doi_thu}/{ma_hang_dt}",
                 dict(zip(("product_code", "nhom_id", "nhan"), cu)) if cu else None,
                 {"product_code": product_code, "nhom_id": nhom_id, "nhan": nhan}, nguoi)


def tao_nhom(conn, ten: str, ma_kome: list[str], nguoi) -> int:
    ten = (ten or "").strip()
    if not 1 <= len(ten) <= 80:
        raise LoiNhap("Tên nhóm dài 1–80 ký tự.")
    if conn.execute("SELECT 1 FROM app.nhom_so_sanh WHERE lower(btrim(ten)) = lower(%s)", (ten,)).fetchone():
        raise LoiNhap("Đã có nhóm tên này.")
    nid = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES (%s) RETURNING id", (ten,)).fetchone()[0]
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.nhom_so_sanh_ma (product_code, nhom_id) VALUES (%s, %s)
                           ON CONFLICT (product_code) DO UPDATE SET nhom_id = EXCLUDED.nhom_id""",
                        [(m, nid) for m in ma_kome])
    _ghi_nhat_ky(conn, "nhom", f"nhom:{nid}", None, {"ten": ten, "ma_kome": ma_kome}, nguoi)
    return nid


def sua_quy_cach(conn, product_code: str, kg_moi_goi, goi_moi_thung, kg_moi_thung, nguoi) -> None:
    v = (_so(kg_moi_goi, "Kg mỗi gói", True), _so(goi_moi_thung, "Gói mỗi thùng", True),
         _so(kg_moi_thung, "Kg mỗi thùng", True))
    cu = conn.execute("SELECT kg_moi_goi, goi_moi_thung, kg_moi_thung FROM mart.quy_cach_kome WHERE product_code=%s",
                      (product_code,)).fetchone()
    if cu is None:
        raise LoiNhap("Không có mã KOME này.")
    conn.execute("""INSERT INTO app.quy_cach_kome VALUES (%s,%s,%s,%s)
                    ON CONFLICT (product_code) DO UPDATE SET kg_moi_goi=EXCLUDED.kg_moi_goi,
                      goi_moi_thung=EXCLUDED.goi_moi_thung, kg_moi_thung=EXCLUDED.kg_moi_thung""",
                 (product_code, *v))
    _ghi_nhat_ky(conn, "quy_cach", product_code, dict(zip(("kg_moi_goi", "goi_moi_thung", "kg_moi_thung"), cu)),
                 dict(zip(("kg_moi_goi", "goi_moi_thung", "kg_moi_thung"), v)), nguoi)


# ---------------------------------------------------------------- đọc (mỗi hàm ĐÚNG MỘT lượt hỏi)

_COT_QS = """ma_doi_thu, ten_doi_thu, nguon, id, ma_hang_dt, ngay_nguon, hinh_thuc_nguon, nguon_file, vi_tri,
             ten_goc, quy_cach_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia,
             gia_bac, gia_truoc_km, trang_thai, khuyen_mai, loai_nguon, ghi_chu, ma_kome, nhan, nhom_khoa,
             ten_nhom, trang_thai_duyet, round(yen_chuan) AS yen_chuan, don_vi_so, nen_gia, tuoi_ngay, bat_thuong"""

_TONG_QUAN = f"""
WITH h AS MATERIALIZED (SELECT * FROM mart.gia_doi_thu_hien_hanh),
dk AS (SELECT DISTINCT ON (ma_doi_thu, loai, noi_dung) ma_doi_thu, loai, noi_dung, ngay_nguon
       FROM core.fact_dieu_kien_doi_thu
       WHERE mart.moc_lui() IS NULL OR ngay_nguon <= mart.moc_lui()
       ORDER BY ma_doi_thu, loai, noi_dung, ngay_nguon DESC)
SELECT json_build_object(
  'ben', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten, 'web', d.web,
            'ngay_moi', x.ngay_moi, 'hinh_thuc', x.hinh_thuc, 'so_dong', coalesce(x.so_dong, 0),
            'cho_duyet', coalesce(x.cho_duyet, 0)) ORDER BY d.ma), '[]')
          FROM app.doi_thu d LEFT JOIN (
            SELECT ma_doi_thu, max(ngay_nguon) ngay_moi, max(hinh_thuc_nguon) hinh_thuc, count(*) so_dong,
                   count(*) FILTER (WHERE trang_thai_duyet IN ('can_xem', 'ai_doc') OR bat_thuong) cho_duyet
            FROM h GROUP BY 1) x ON x.ma_doi_thu = d.ma WHERE d.dang_theo_doi),
  'luoi', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'nganh', nganh, 'so_ma', n)), '[]') FROM (
            SELECT h.ma_doi_thu, mart.ten_nganh(p.food_category_name) nganh, count(DISTINCT h.ma_hang_dt) n
            FROM h JOIN core.dim_product p ON p.product_code = h.ma_kome GROUP BY 1, 2) z),
  'khuyen_mai', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'ten_goc', ten_goc, 'gia_goc', gia_goc,
            'gia_truoc_km', gia_truoc_km, 'khuyen_mai', khuyen_mai, 'ngay', ngay_nguon) ORDER BY ma_doi_thu, ten_goc), '[]')
          FROM h WHERE gia_truoc_km IS NOT NULL OR nullif(khuyen_mai, '') IS NOT NULL),
  'dieu_kien', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'loai', loai, 'noi_dung', noi_dung,
            'ngay', ngay_nguon) ORDER BY ma_doi_thu, loai), '[]') FROM dk WHERE loai <> 'khac'),
  'het_hang', (SELECT coalesce(json_agg(json_build_object('ben', ma_doi_thu, 'ten_goc', ten_goc, 'ma_kome', ma_kome,
            'ten_nhom', ten_nhom, 'trang_thai', trang_thai) ORDER BY ten_nhom, ma_doi_thu), '[]')
          FROM h WHERE trang_thai IN ('het', 'sap_ve') AND ma_kome IS NOT NULL))
"""


def tong_quan(conn) -> dict:
    return conn.execute(_TONG_QUAN).fetchone()[0]


_SO_SANH = f"""
WITH h AS MATERIALIZED (SELECT {_COT_QS} FROM mart.gia_doi_thu_hien_hanh WHERE nhom_khoa IS NOT NULL)
SELECT coalesce(json_agg(json_build_object(
         'nhom_khoa', s.nhom_khoa, 'ten_nhom', s.ten_nhom, 'don_vi_so', s.don_vi_so, 'ma_kome', s.ma_kome,
         'gia_kome', round(s.gia_kome), 'so_ben', s.so_ben, 'thap_nhat', round(s.thap_nhat), 'ben_thap_nhat', s.ben_thap_nhat,
         'trung_vi', round(s.trung_vi::numeric), 'cao_nhat', round(s.cao_nhat), 'ty_le_re_hon_kome', s.ty_le_re_hon_kome,
         'quan_sat', (SELECT coalesce(json_agg(to_json(h) ORDER BY h.yen_chuan NULLS LAST), '[]') FROM h
                      WHERE h.nhom_khoa = s.nhom_khoa AND h.don_vi_so = s.don_vi_so))
       ORDER BY s.so_ben DESC, s.ten_nhom), '[]')
FROM mart.so_sanh_nhom s
"""


def so_sanh(conn) -> dict:
    return {"nhom": conn.execute(_SO_SANH).fetchone()[0]}


_HO_SO = f"""
SELECT (SELECT to_json(d) FROM app.doi_thu d WHERE d.ma = %(ma)s),
       (SELECT coalesce(json_agg(json_build_object('loai', loai, 'noi_dung', noi_dung, 'ngay', ngay_nguon)
                ORDER BY ngay_nguon DESC), '[]') FROM core.fact_dieu_kien_doi_thu WHERE ma_doi_thu = %(ma)s
                AND (mart.moc_lui() IS NULL OR ngay_nguon <= mart.moc_lui())),
       (SELECT coalesce(json_agg(to_json(q) ORDER BY q.ten_goc, q.ngay_nguon DESC), '[]')
          FROM (SELECT {_COT_QS.replace(', bat_thuong', '')}, hien_hanh FROM mart.gia_doi_thu_quan_sat
                WHERE ma_doi_thu = %(ma)s) q)
"""


def ho_so_ben(conn, ma: str) -> dict | None:
    ben, dk, qs = conn.execute(_HO_SO, {"ma": ma}).fetchone()
    return None if ben is None else {"ben": ben, "dieu_kien": dk, "quan_sat": qs}


_DUYET = f"""
SELECT coalesce(json_agg(to_json(h) ORDER BY h.bat_thuong DESC, h.trang_thai_duyet, h.ma_doi_thu, h.ten_goc), '[]')
FROM (SELECT {_COT_QS} FROM mart.gia_doi_thu_hien_hanh
      WHERE (%(ben)s = '' OR ma_doi_thu = %(ben)s)
        AND CASE %(loc)s WHEN 'can_xem' THEN trang_thai_duyet = 'can_xem'
                         WHEN 'bat_thuong' THEN bat_thuong
                         WHEN 'chua_ghep' THEN ma_kome IS NULL
                         WHEN 'chua_xac_nhan' THEN trang_thai_duyet IN ('ai_doc', 'can_xem')
                         ELSE true END) h
"""


def duyet(conn, ben: str = "", loc: str = "") -> dict:
    if loc not in LOC_DUYET:
        loc = ""
    return {"dong": conn.execute(_DUYET, {"ben": ben, "loc": loc}).fetchone()[0]}


_KHOI_SP = """
SELECT to_json(s) FROM mart.so_sanh_nhom s
WHERE s.don_vi_so = 'kg' AND %(ma)s = ANY(s.ma_kome)
ORDER BY s.so_ben DESC LIMIT 1
"""


def khoi_san_pham(conn, ma: str) -> dict | None:
    r = conn.execute(_KHOI_SP, {"ma": ma}).fetchone()
    return r[0] if r else None
