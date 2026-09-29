"""Thị trường & đối thủ (/doi-thu) — đặc tả docs/superpowers/specs/2026-09-29-thi-truong-doi-thu-design.md.

Chỉ số ở mart (060): ở đây chỉ HỎI và gói JSON (mỗi hàm đọc ĐÚNG MỘT lượt hỏi), và GHI vào app
(mọi hàm ghi thêm một dòng app.doi_thu_nhat_ky trong CÙNG giao dịch; không commit — route commit).
Không bao giờ ghi core: sửa lỗi đọc = app.dinh_chinh_gia, giá đã đổi = app.gia_doi_thu_tay.
"""
from __future__ import annotations

import json
import re
from decimal import Decimal

from kome.ten_hang import chuan_ten
from kome.tuoi_du_lieu import hom_nay_o_nhat

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


_PHAY_NGHIN = re.compile(r"^-?\d{1,3}(,\d{3})+(\.\d+)?$")
_PHAY_THAP_PHAN = re.compile(r"^-?\d+,\d+$")
_SO_THUONG = re.compile(r"^-?\d+(\.\d+)?$")


def _so(v, ten, duong=False, phay_la_thap_phan=False):
    """Đọc số người gõ. '1,234' / '12,345.6' = phẩy nghìn; '0,5' / '12,75' = phẩy thập phân;
    phay_la_thap_phan=True (ô kg — không ai gõ hàng nghìn kg): dấu phẩy LUÔN là thập phân ('1,500' = 1.5);
    'nan' / 'inf' / '1e3' và mọi thứ khác không phải số thường -> LoiNhap."""
    if v in (None, ""):
        return None
    t = str(v).strip()
    if phay_la_thap_phan and _PHAY_THAP_PHAN.match(t):
        t = t.replace(",", ".")
    elif _PHAY_NGHIN.match(t):
        t = t.replace(",", "")
    elif _PHAY_THAP_PHAN.match(t):
        t = t.replace(",", ".")
    if not _SO_THUONG.match(t):
        raise LoiNhap(f"{ten} phải là số.")
    x = Decimal(t)
    if x < 0 or (duong and x == 0):
        raise LoiNhap(f"{ten} không được âm{' hoặc bằng 0' if duong else ''}.")
    return x


def _chuoi_so(v, ten, duong=False, phay_la_thap_phan=False):
    x = _so(v, ten, duong, phay_la_thap_phan)
    return None if x is None else format(x, "f")


def _kiem(truong: str, v):
    if truong not in TRUONG_SUA:
        raise LoiNhap(f"Không sửa được trường '{truong}'.")
    if truong == "gia_goc":
        return _chuoi_so(v, "Giá")
    if truong == "kg_moi_don_vi_gia":
        return _chuoi_so(v, "Số kg", True, True)
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
    if conn.execute("SELECT 1 FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s", (fact_id,)).fetchone() is None:
        raise LoiNhap("Không tìm thấy dòng giá này (có thể lô đã bị hoàn tác).")
    conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, nguoi_dung_id) VALUES (%s, 'xac_nhan', %s)",
                 (fact_id, nguoi))
    _ghi_nhat_ky(conn, "xac_nhan", f"gia:{fact_id}", None, None, nguoi)


def sua(conn, fact_id: int, thay_doi: dict, nguoi) -> None:
    if not thay_doi:
        raise LoiNhap("Không có gì để sửa.")
    for k, v in thay_doi.items():
        if v is None or not str(v).strip():
            raise LoiNhap("Để trống không xoá được giá trị AI đã đọc — nhập giá trị đúng, hoặc dùng 'Giá đã đổi'.")
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
        try:
            fact_goc = int(du_lieu["fact_goc_id"])
        except (TypeError, ValueError):
            raise LoiNhap("Mã dòng giá gốc không hợp lệ.")
        goc = conn.execute("""SELECT ma_doi_thu, ma_hang_dt, ten_goc, quy_cach_goc, don_vi_gia, kg_moi_don_vi_gia,
                                     thue, gom_ship, kenh_gia, muc_gia
                              FROM mart.gia_doi_thu_quan_sat WHERE nguon='nap' AND id=%s""",
                           (fact_goc,)).fetchone()
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
        v["ma_hang_dt"] = "ten:" + chuan_ten(v["ten_goc"]) + "|" + chuan_ten(v.get("quy_cach_goc") or "")
    tt = _kiem("trang_thai", du_lieu.get("trang_thai") or "con")
    if v.get("gia_goc") is None and tt != "het":
        raise LoiNhap("Nhập giá (chỉ được bỏ trống khi ghi hàng đã hết).")
    tid = conn.execute(
        """INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, fact_goc_id, ten_goc, quy_cach_goc, gia_goc,
             don_vi_gia, kg_moi_don_vi_gia, thue, gom_ship, kenh_gia, muc_gia, trang_thai, loai_nguon,
             ghi_chu_nguon, nguoi_dung_id)
           VALUES (%(ma_doi_thu)s, %(ma_hang_dt)s, %(fact_goc_id)s, %(ten_goc)s, %(quy_cach_goc)s, %(gia_goc)s,
             %(don_vi_gia)s, %(kg_moi_don_vi_gia)s, %(thue)s, %(gom_ship)s, %(kenh_gia)s, %(muc_gia)s,
             %(trang_thai)s, %(loai_nguon)s, %(ghi_chu_nguon)s, %(nguoi)s) RETURNING id""",
        {**{x: v.get(x) for x in k}, "gia_goc": v.get("gia_goc"), "fact_goc_id": fact_goc if goc else None,
         "trang_thai": tt, "loai_nguon": ln, "ghi_chu_nguon": (du_lieu.get("ghi_chu_nguon") or "")[:DAI_TOI_DA] or None,
         "nguoi": nguoi}).fetchone()[0]
    _ghi_nhat_ky(conn, "gia_moi" if goc else "them", f"tay:{tid}", None, v | {"loai_nguon": ln}, nguoi)
    return tid


DON_VI_GIA_KE = ("kg", "tui", "goi", "con", "qua", "thung", "lon", "chai", "hop", "cay", "bao", "khac")
GIA_KE_TOI_DA = Decimal("9999999")
# Khoá của thẻ / giá: fullmatch (KHÔNG `$` — nó khớp trước dấu xuống dòng cuối) và không khoảng trắng /
# ký tự điều khiển; sổ app.tiep_xuc_nhac chỉ-thêm nên một khoá bẩn ở lại vĩnh viễn.
KHOA_SACH = re.compile(r"[^\s\x00-\x1f\x7f]+")
KHOA_NHOM = re.compile(r"(ma:[^\s\x00-\x1f\x7f]+|n:[0-9]{1,15})")


def gia_khach_ke(conn, ma_doi_thu: str, nhom_khoa: str, customer_code: str, tiep_xuc_id: int,
                 gia_goc, don_vi_gia: str, nguoi) -> int:
    """Giá khách kể (tin hiện trường `@`, đợt 2 — 063): một dòng `app.gia_doi_thu_tay` `loai_nguon='khach_ke'`.

    `ma_hang_dt` LƯU = 'ke:<khách>:<nhóm_khoa đã ghi>'; view 063 dựng lại khoá chuỗi LÚC ĐỌC theo nhóm HIỆN HÀNH
    ('ke:<khách>:<mart.nhom_cua_khoa(...)>') -> phân vùng `hien_hanh` tách theo (khách, bên, nhóm thật): tin trùng
    thì mới nhất là hiện trạng (kể cả lần gắn `ma:<mã>` rồi lần gắn `n:<nhóm>`), hai khách khác nhau không đè nhau. `nhom_khoa` ('ma:<mã KOME>' | 'n:<id>') đi thẳng
    vào cột `nhom_khoa` — không qua bước ghép. `kg_moi_don_vi_gia` = 1 khi đơn vị là kg, NULL khi khác (máy không
    đoán kg của gói / thùng); thuế / ship `khong_ro`. Cùng giao dịch: thêm một dòng nhật ký 'gia_moi'.
    Người gọi chịu trách nhiệm chuyện thẻ `@` (xem `lien_he.ghi_kem_nhac`); ở đây chỉ kiểm chính dòng giá."""
    if not isinstance(nhom_khoa, str) or not KHOA_NHOM.fullmatch(nhom_khoa):
        raise LoiNhap("Nhóm hàng sai định dạng (ma:<mã> hoặc n:<số>).")
    gia = _so(gia_goc, "Giá", duong=True)
    if gia is None:
        raise LoiNhap("Nhập giá.")
    if gia > GIA_KE_TOI_DA:
        raise LoiNhap("Giá quá lớn — kiểm lại số.")
    if don_vi_gia not in DON_VI_GIA_KE:
        raise LoiNhap(f"Đơn vị giá chỉ nhận: {', '.join(DON_VI_GIA_KE)}.")
    if not isinstance(ma_doi_thu, str) or not KHOA_SACH.fullmatch(ma_doi_thu) or conn.execute(
            "SELECT 1 FROM app.doi_thu WHERE ma = %s", (ma_doi_thu,)).fetchone() is None:
        raise LoiNhap(f"Không có đối thủ '{ma_doi_thu}'.")
    ten = conn.execute(
        """SELECT CASE WHEN left(%(k)s, 2) = 'n:'
                       THEN (SELECT ten FROM app.nhom_so_sanh WHERE id = substr(%(k)s, 3)::bigint)
                       ELSE (SELECT coalesce(nullif(product_name, ''), product_code) FROM core.dim_product
                             WHERE product_code = substr(%(k)s, 4)) END""", {"k": nhom_khoa}).fetchone()[0]
    if ten is None:
        raise LoiNhap(f"Không có nhóm hàng '{nhom_khoa}'.")
    tid = conn.execute(
        """INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, gia_goc, don_vi_gia, kg_moi_don_vi_gia,
             thue, gom_ship, trang_thai, loai_nguon, customer_code, tiep_xuc_id, nhom_khoa, nguoi_dung_id)
           VALUES (%s, %s, %s, %s, %s, %s, 'khong_ro', 'khong_ro', 'con', 'khach_ke', %s, %s, %s, %s) RETURNING id""",
        (ma_doi_thu, f"ke:{customer_code}:{nhom_khoa}", ten, gia, don_vi_gia, 1 if don_vi_gia == "kg" else None,
         customer_code, tiep_xuc_id, nhom_khoa, nguoi)).fetchone()[0]
    _ghi_nhat_ky(conn, "gia_moi", f"tay:{tid}", None,
                 {"ma_doi_thu": ma_doi_thu, "nhom_khoa": nhom_khoa, "gia_goc": gia, "don_vi_gia": don_vi_gia,
                  "loai_nguon": "khach_ke", "customer_code": customer_code, "tiep_xuc_id": tiep_xuc_id}, nguoi)
    return tid


def dat_ghep(conn, ma_doi_thu: str, ma_hang_dt: str, product_code, nhom_id, nhan: str, nguoi) -> None:
    if nhan not in NHAN:
        raise LoiNhap("Nhãn ghép chỉ nhận cùng hàng / thay thế / không ghép.")
    if product_code is not None and product_code != "" and conn.execute(
            "SELECT 1 FROM core.dim_product WHERE product_code=%s", (product_code,)).fetchone() is None:
        raise LoiNhap(f"Không có mã KOME '{product_code}'.")
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


def _kiem_ma_kome(conn, ma_kome) -> list[str]:
    """Mọi mã phải có trong core.dim_product — mã gõ nhầm không được vào nhóm (nhóm rỗng lặng lẽ)."""
    if not isinstance(ma_kome, (list, tuple)):
        raise LoiNhap("Danh sách mã KOME phải là một danh sách.")
    ma = [str(m).strip() for m in ma_kome]
    if any(not m for m in ma):
        raise LoiNhap("Có mã KOME để trống.")
    ma = list(dict.fromkeys(ma))
    if ma:
        co = {r[0] for r in conn.execute("SELECT product_code FROM core.dim_product WHERE product_code = ANY(%s)", (ma,))}
        for m in ma:
            if m not in co:
                raise LoiNhap(f"Không có mã KOME '{m}'.")
    return ma


def _nhom_cu(conn, ma: list[str]) -> dict:
    """{mã: nhom_id} của những mã ĐANG thuộc một nhóm — cột `truoc` của nhật ký."""
    if not ma:
        return {}
    return dict(conn.execute("SELECT product_code, nhom_id FROM app.nhom_so_sanh_ma WHERE product_code = ANY(%s)",
                             (ma,)).fetchall())


def tao_nhom(conn, ten: str, ma_kome: list[str], nguoi) -> int:
    ten = (ten or "").strip()
    if not 1 <= len(ten) <= 80:
        raise LoiNhap("Tên nhóm dài 1–80 ký tự.")
    ma_kome = _kiem_ma_kome(conn, ma_kome)
    if conn.execute("SELECT 1 FROM app.nhom_so_sanh WHERE lower(btrim(ten)) = lower(%s)", (ten,)).fetchone():
        raise LoiNhap("Đã có nhóm tên này.")
    cu = _nhom_cu(conn, ma_kome)
    nid = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES (%s) RETURNING id", (ten,)).fetchone()[0]
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.nhom_so_sanh_ma (product_code, nhom_id) VALUES (%s, %s)
                           ON CONFLICT (product_code) DO UPDATE SET nhom_id = EXCLUDED.nhom_id""",
                        [(m, nid) for m in ma_kome])
    _ghi_nhat_ky(conn, "nhom", f"nhom:{nid}", cu or None, {"ten": ten, "ma_kome": ma_kome}, nguoi)
    return nid


def them_ma_nhom(conn, nhom_id: int, ma_kome: list[str], nguoi) -> None:
    """Thêm mã vào một nhóm có sẵn; mã đang ở nhóm khác thì được CHUYỂN sang (mỗi mã một nhóm)."""
    ten = conn.execute("SELECT ten FROM app.nhom_so_sanh WHERE id=%s", (nhom_id,)).fetchone()
    if ten is None:
        raise LoiNhap("Không có nhóm này.")
    ma = _kiem_ma_kome(conn, ma_kome)
    if not ma:
        raise LoiNhap("Chọn ít nhất một mã KOME.")
    cu = _nhom_cu(conn, ma)
    with conn.cursor() as cur:
        cur.executemany("""INSERT INTO app.nhom_so_sanh_ma (product_code, nhom_id) VALUES (%s, %s)
                           ON CONFLICT (product_code) DO UPDATE SET nhom_id = EXCLUDED.nhom_id""",
                        [(m, nhom_id) for m in ma])
    _ghi_nhat_ky(conn, "nhom", f"nhom:{nhom_id}", cu or None, {"ten": ten[0], "ma_kome": ma}, nguoi)


def bo_ma_nhom(conn, product_code: str, nguoi) -> None:
    r = conn.execute("DELETE FROM app.nhom_so_sanh_ma WHERE product_code=%s RETURNING nhom_id", (product_code,)).fetchone()
    if r is None:
        raise LoiNhap("Mã này không thuộc nhóm nào.")
    _ghi_nhat_ky(conn, "nhom", f"nhom:{r[0]}", {product_code: r[0]}, {"bo_ma": product_code}, nguoi)


def sua_quy_cach(conn, product_code: str, kg_moi_goi, goi_moi_thung, kg_moi_thung, nguoi) -> None:
    v = (_so(kg_moi_goi, "Kg mỗi gói", True, True), _so(goi_moi_thung, "Gói mỗi thùng", True),
         _so(kg_moi_thung, "Kg mỗi thùng", True, True))
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

NGAY_HIEN_TRUONG = 30       # cửa sổ "hiện trường" của Tổng quan
NGAY_TIN_KHACH = 90         # cửa sổ tin của khách / của đối thủ (mặc định của đặc tả §6: "chỉ tính 90 ngày")


def _ten_nhom(k: str) -> str:
    """Biểu thức SQL: tên của nhóm có khoá `k` ('n:<id>' -> tên nhóm; 'ma:<mã>' -> tên hàng KOME; không có -> chính khoá)."""
    return (f"coalesce((SELECT ns_.ten FROM app.nhom_so_sanh ns_ WHERE ns_.id = CASE WHEN {k} ~ '^n:[0-9]+$' THEN substr({k}, 3)::bigint END), "
            f"(SELECT coalesce(nullif(sp_.product_name, ''), sp_.product_code) FROM core.dim_product sp_ "
            f"WHERE sp_.product_code = CASE WHEN left({k}, 3) = 'ma:' THEN substr({k}, 4) END), {k})")


# Giá khách kể đã mang nhóm (thẻ @hàng) — không có gì để ghép hay xác nhận ở màn Duyệt: không vào hàng "chưa ghép"
# và không vào số "chờ duyệt". Giá khách kể BẤT THƯỜNG vẫn hiện ở bộ lọc "bất thường" của Duyệt.
_KE_DA_NHOM = "(loai_nguon = 'khach_ke' AND nhom_khoa IS NOT NULL)"


_TONG_QUAN = f"""
WITH h AS MATERIALIZED (SELECT * FROM mart.gia_doi_thu_hien_hanh),
dk0 AS (SELECT * FROM core.fact_dieu_kien_doi_thu WHERE mart.moc_lui() IS NULL OR ngay_nguon <= mart.moc_lui()),
dk AS (SELECT DISTINCT f.ma_doi_thu, f.loai, f.noi_dung, f.ngay_nguon      -- chỉ gói MỚI NHẤT của từng bên
       FROM dk0 f WHERE f.ngay_nguon = (SELECT max(g.ngay_nguon) FROM dk0 g WHERE g.ma_doi_thu = f.ma_doi_thu))
SELECT json_build_object(
  'ben', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten, 'web', d.web,
            'ngay_moi', x.ngay_moi, 'hinh_thuc', x.hinh_thuc, 'so_dong', coalesce(x.so_dong, 0),
            'cho_duyet', coalesce(x.cho_duyet, 0)) ORDER BY d.ma), '[]')
          FROM app.doi_thu d LEFT JOIN (
            SELECT ma_doi_thu, max(ngay_nguon) ngay_moi, max(hinh_thuc_nguon) hinh_thuc, count(*) so_dong,
                   count(*) FILTER (WHERE (trang_thai_duyet IN ('can_xem', 'ai_doc') OR bat_thuong)
                                      AND NOT {_KE_DA_NHOM}) cho_duyet
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
          FROM h WHERE trang_thai IN ('het', 'sap_ve') AND ma_kome IS NOT NULL),
  'hien_truong', (
    WITH tx AS MATERIALIZED (
        SELECT n.id, n.customer_code FROM app.nhat_ky_tiep_xuc n
        WHERE (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date > %(hom_nay)s::date - {NGAY_HIEN_TRUONG}
          AND EXISTS (SELECT 1 FROM app.tiep_xuc_nhac z WHERE z.tiep_xuc_id = n.id)),
    m AS MATERIALIZED (SELECT DISTINCT z.tiep_xuc_id, z.loai,
                              CASE WHEN z.loai = 'nhom' THEN mart.nhom_cua_khoa(z.khoa) ELSE z.khoa END AS khoa
                       FROM app.tiep_xuc_nhac z JOIN tx ON tx.id = z.tiep_xuc_id)
    SELECT json_build_object('ngay', {NGAY_HIEN_TRUONG}, 'tong', (SELECT count(*) FROM tx),
      'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', q.ma, 'ten', q.ten, 'so_tin', q.n) ORDER BY q.n DESC, q.ma), '[]')
                  FROM (SELECT m.khoa AS ma, d.ten, count(*) AS n FROM m JOIN app.doi_thu d ON d.ma = m.khoa
                        WHERE m.loai = 'doi_thu' GROUP BY 1, 2 ORDER BY 3 DESC, 1 LIMIT 10) q),
      'nhom', (SELECT coalesce(json_agg(json_build_object('khoa', q.khoa, 'ten', q.ten, 'so_tin', q.n) ORDER BY q.n DESC, q.khoa), '[]')
               FROM (SELECT x.khoa, x.ten, count(*) AS n
                     FROM (SELECT m.khoa, {_ten_nhom('m.khoa')} AS ten FROM m WHERE m.loai = 'nhom') x
                     GROUP BY 1, 2 ORDER BY 3 DESC, 1 LIMIT 10) q),
      'tinh', (SELECT coalesce(json_agg(json_build_object('tinh', q.tinh, 'so_tin', q.n) ORDER BY q.n DESC, q.tinh), '[]')
               FROM (SELECT coalesce(nullif(c.prefecture, ''), '(chưa rõ)') AS tinh, count(*) AS n
                     FROM tx LEFT JOIN core.dim_customer c ON c.customer_code = tx.customer_code AND c.is_current
                     GROUP BY 1 ORDER BY 2 DESC, 1 LIMIT 48) q)))      -- 47 tỉnh + "(chưa rõ)"
)
"""


def tong_quan(conn, hom_nay=None) -> dict:
    """Tổng quan thị trường. `hien_truong` (đợt 2): tin `@` của NGAY_HIEN_TRUONG ngày qua theo ĐỒNG HỒ THẬT giờ
    Tokyo (`hom_nay_o_nhat`, không theo mốc dữ liệu — tin hiện trường là sự kiện ngoài đời, cùng lý lẽ ngoại lệ
    thứ hai của bất biến mốc, xem `/lien-he`). "Tin" = MỘT lần tiếp xúc có ít nhất một thẻ; mỗi đối thủ / nhóm /
    tỉnh đếm số tin nhắc tới nó (không đếm số thẻ). Tỉnh = `core.dim_customer.prefecture` hiện hành."""
    return conn.execute(_TONG_QUAN, {"hom_nay": hom_nay or hom_nay_o_nhat()}).fetchone()[0]


_SO_SANH = f"""
WITH h AS MATERIALIZED (SELECT {_COT_QS} FROM mart.gia_doi_thu_hien_hanh WHERE nhom_khoa IS NOT NULL)
SELECT coalesce(json_agg(json_build_object(
         'nhom_khoa', s.nhom_khoa, 'ten_nhom', s.ten_nhom, 'don_vi_so', s.don_vi_so, 'ma_kome', s.ma_kome,
         'gia_kome', round(s.gia_kome), 'so_ben', s.so_ben, 'thap_nhat', round(s.thap_nhat), 'ben_thap_nhat', s.ben_thap_nhat,
         'trung_vi', round(s.trung_vi::numeric), 'cao_nhat', round(s.cao_nhat), 'ty_le_re_hon_kome', s.ty_le_re_hon_kome,
         'nganh', s.nganh,
         'quan_sat', (SELECT coalesce(json_agg(to_json(h) ORDER BY h.yen_chuan NULLS LAST), '[]') FROM h
                      WHERE h.nhom_khoa = s.nhom_khoa AND h.don_vi_so = s.don_vi_so))
       ORDER BY s.so_ben DESC, s.ten_nhom), '[]')
FROM mart.so_sanh_nhom s
"""


def so_sanh(conn) -> dict:
    return {"nhom": conn.execute(_SO_SANH).fetchone()[0]}


_NHOM_QUY_CACH = """
SELECT json_build_object(
  'nhom', (SELECT coalesce(json_agg(json_build_object('id', n.id, 'ten', n.ten, 'ma', coalesce(
             (SELECT json_agg(json_build_object('ma', m.product_code, 'ten', p.product_name) ORDER BY m.product_code)
              FROM app.nhom_so_sanh_ma m LEFT JOIN core.dim_product p USING (product_code)
              WHERE m.nhom_id = n.id), '[]')) ORDER BY n.ten), '[]') FROM app.nhom_so_sanh n),
  'quy_cach', (SELECT coalesce(json_agg(json_build_object('ma', z.product_code, 'ten', z.product_name, 'nganh', z.nganh,
                 'kg_moi_goi', z.kg_moi_goi, 'goi_moi_thung', z.goi_moi_thung, 'kg_moi_thung', z.kg_moi_thung,
                 'da_sua', z.da_sua) ORDER BY z.nganh, z.product_code), '[]')
               FROM (SELECT p.product_code, p.product_name, mart.ten_nganh(p.food_category_name) AS nganh,
                            q.kg_moi_goi, q.goi_moi_thung, q.kg_moi_thung, q.da_sua
                     FROM core.dim_product p JOIN mart.quy_cach_kome q USING (product_code)
                     WHERE NOT mart.khong_phai_hang(p.product_code, p.kind_code, p.food_category_name)) z))
"""


def nhom_va_quy_cach(conn) -> dict:
    """Nhóm so sánh (kèm danh sách mã) + quy cách KOME của hàng thật (không phí, không POSM). MỘT lượt hỏi."""
    return conn.execute(_NHOM_QUY_CACH).fetchone()[0]


_HO_SO = f"""
SELECT (SELECT to_json(d) FROM app.doi_thu d WHERE d.ma = %(ma)s),
       (SELECT coalesce(json_agg(json_build_object('loai', loai, 'noi_dung', noi_dung, 'ngay', ngay_nguon)
                ORDER BY ngay_nguon DESC), '[]') FROM core.fact_dieu_kien_doi_thu WHERE ma_doi_thu = %(ma)s
                AND (mart.moc_lui() IS NULL OR ngay_nguon <= mart.moc_lui())),
       (SELECT coalesce(json_agg(to_json(q) ORDER BY q.ten_goc, q.ngay_nguon DESC), '[]')
          FROM (SELECT {_COT_QS.replace(', bat_thuong', '')}, hien_hanh FROM mart.gia_doi_thu_quan_sat
                WHERE ma_doi_thu = %(ma)s) q),
       (SELECT coalesce(json_agg(json_build_object(
                  'tiep_xuc_id', t.id, 'ma_khach', t.customer_code, 'ten_khach', t.ten_khach, 'ngay', t.ngay,
                  'nhom', (SELECT coalesce(json_agg(json_build_object('khoa', x.khoa, 'ten', x.ten) ORDER BY x.khoa), '[]')
                           FROM (SELECT DISTINCT k.khoa, {_ten_nhom('k.khoa')} AS ten FROM app.tiep_xuc_nhac z
                                 CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(z.khoa) AS khoa) k
                                 WHERE z.tiep_xuc_id = t.id AND z.loai = 'nhom') x),
                  'gia', (SELECT coalesce(json_agg(json_build_object('nhom_khoa', k.khoa, 'ten_nhom', {_ten_nhom('k.khoa')},
                                'gia_goc', g.gia_goc, 'don_vi_gia', g.don_vi_gia) ORDER BY g.id), '[]')
                          FROM app.gia_doi_thu_tay g CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(g.nhom_khoa) AS khoa) k
                          WHERE g.tiep_xuc_id = t.id AND g.ma_doi_thu = %(ma)s AND g.loai_nguon = 'khach_ke'))
                ORDER BY t.thoi_diem DESC, t.id DESC), '[]')
          FROM (SELECT n.id, n.customer_code, n.thoi_diem, c.customer_name AS ten_khach,
                       (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date AS ngay
                FROM app.nhat_ky_tiep_xuc n
                LEFT JOIN core.dim_customer c ON c.customer_code = n.customer_code AND c.is_current
                WHERE (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date > %(hom_nay)s::date - {NGAY_TIN_KHACH}
                  AND EXISTS (SELECT 1 FROM app.tiep_xuc_nhac z
                              WHERE z.tiep_xuc_id = n.id AND z.loai = 'doi_thu' AND z.khoa = %(ma)s)
                ORDER BY n.thoi_diem DESC, n.id DESC LIMIT 100) t)
"""


def ho_so_ben(conn, ma: str, hom_nay=None) -> dict | None:
    """Hồ sơ một đối thủ. `khach_dang_mua` (đợt 2): tin `@` NGAY_TIN_KHACH ngày qua nhắc bên này — mỗi phần tử là
    MỘT lần tiếp xúc (khách + tên hiện hành, các nhóm được nhắc, giá khách kể cho CHÍNH bên này). Theo đồng hồ thật
    giờ Tokyo (`hom_nay_o_nhat`), không theo mốc dữ liệu — xem `tong_quan`. Vẫn MỘT lượt hỏi."""
    ben, dk, qs, kh = conn.execute(_HO_SO, {"ma": ma, "hom_nay": hom_nay or hom_nay_o_nhat()}).fetchone()
    return None if ben is None else {"ben": ben, "dieu_kien": dk, "quan_sat": qs, "khach_dang_mua": kh}


_DUYET = f"""
SELECT coalesce(json_agg(to_json(h) ORDER BY h.bat_thuong DESC, h.trang_thai_duyet, h.ma_doi_thu, h.ten_goc), '[]')
FROM (SELECT {_COT_QS} FROM mart.gia_doi_thu_hien_hanh h
      WHERE (%(ben)s = '' OR ma_doi_thu = %(ben)s)
        AND CASE %(loc)s WHEN 'can_xem' THEN trang_thai_duyet = 'can_xem'
                         WHEN 'bat_thuong' THEN bat_thuong
                         WHEN 'chua_ghep' THEN ma_kome IS NULL AND NOT {_KE_DA_NHOM} AND NOT EXISTS (
                             SELECT 1 FROM app.ghep_hang g
                             WHERE g.ma_doi_thu = h.ma_doi_thu AND g.ma_hang_dt = h.ma_hang_dt)
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


_GOI_Y_NHAC = f"""
SELECT json_build_object(
  'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten) ORDER BY d.ma), '[]')
              FROM app.doi_thu d WHERE d.dang_theo_doi),
  'hang', (SELECT coalesce(json_agg(json_strip_nulls(json_build_object('khoa', z.khoa, 'ten', z.ten, 'loai', z.loai,
                                                                       'ma', z.ma, 'ten_nhom', z.ten_nhom))
                                    ORDER BY z.thu_tu, z.ten, z.khoa, z.ma), '[]')
           FROM (SELECT 0 AS thu_tu, 'n:' || n.id AS khoa, n.ten, 'nhom' AS loai, NULL::text AS ma, NULL::text AS ten_nhom
                 FROM app.nhom_so_sanh n
                 UNION ALL
                 SELECT 1, k.khoa, coalesce(nullif(p.product_name, ''), p.product_code), 'ma', p.product_code,
                        CASE WHEN left(k.khoa, 2) = 'n:' THEN {_ten_nhom('k.khoa')} END
                 FROM core.dim_product p CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa('ma:' || p.product_code) AS khoa) k
                 WHERE NOT mart.khong_phai_hang(p.product_code, p.kind_code, p.food_category_name)) z))
"""


def goi_y_nhac(conn) -> dict:
    """Danh sách gợi ý cho ô `@` của ô ghi tiếp xúc. MỘT lượt hỏi.
    `doi_thu`: đối thủ đang theo dõi. `hang`: nhóm so sánh có tên (`loai = 'nhom'`, khoá `n:<id>`, đứng trước)
    rồi mã KOME hàng thật (`loai = 'ma'`, `ma` = mã; không phí / POSM — cùng vị từ `nhom_va_quy_cach`). Mã thuộc một
    nhóm có tên VẪN được gợi ý (sale gõ tên hàng chứ không nhớ tên nhóm) nhưng khoá của nó là NHÓM
    (`mart.nhom_cua_khoa` -> `n:<id>`, kèm `ten_nhom`); mã lẻ giữ khoá `ma:<mã>`. Thẻ `@hàng` vì vậy luôn trỏ tới nhóm
    so sánh thật của mã (R-A)."""
    return conn.execute(_GOI_Y_NHAC).fetchone()[0]


_KHACH_DOI_THU = f"""
WITH tx AS MATERIALIZED (
    SELECT n.id, n.thoi_diem, (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date AS ngay, n.noi_dung,
           coalesce(s.ten, nd.ten_dang_nhap) AS nguoi
    FROM app.nhat_ky_tiep_xuc n
    LEFT JOIN app.nguoi_dung nd ON nd.id = n.nguoi_dung_id
    LEFT JOIN core.dim_salesperson s ON s.salesperson_code = nd.salesperson_code
    WHERE n.customer_code = %(ma)s
      AND (n.thoi_diem AT TIME ZONE 'Asia/Tokyo')::date > %(hom_nay)s::date - {NGAY_TIN_KHACH}
      AND EXISTS (SELECT 1 FROM app.tiep_xuc_nhac z WHERE z.tiep_xuc_id = n.id)
    ORDER BY n.thoi_diem DESC, n.id DESC LIMIT 100),
dt AS MATERIALIZED (
    SELECT DISTINCT z.tiep_xuc_id, z.khoa AS ma, d.ten
    FROM tx JOIN app.tiep_xuc_nhac z ON z.tiep_xuc_id = tx.id AND z.loai = 'doi_thu'
    JOIN app.doi_thu d ON d.ma = z.khoa),
nh AS MATERIALIZED (     -- khoá nhóm HIỆN HÀNH (mart.nhom_cua_khoa, 063): 'ma:<mã>' của mã thuộc nhóm có tên -> 'n:<nhóm>'
    SELECT DISTINCT z.tiep_xuc_id, k.khoa, {_ten_nhom('k.khoa')} AS ten
    FROM tx JOIN app.tiep_xuc_nhac z ON z.tiep_xuc_id = tx.id AND z.loai = 'nhom'
    CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(z.khoa) AS khoa) k),
ngung AS (      -- cặp (khách, mã) đã ngừng mua theo bất biến 024; view lọc theo khách nên vị từ đẩy xuống được
    SELECT h.product_code AS ma, coalesce(nullif(h.ten_hang, ''), h.product_code) AS ten, h.lan_cuoi,
           (SELECT hom_nay FROM mart.moc_thoi_gian) - h.lan_cuoi AS so_ngay,
           mart.nhom_cua_khoa('ma:' || h.product_code) AS nhom_khoa
    FROM mart.khach_mat_hang h
    WHERE h.customer_code = %(ma)s AND h.trang_thai_cap = 'ngung'),
ly AS (         -- mỗi mã ngừng mua: tin MỚI NHẤT nhắc nhóm HIỆN HÀNH của nó (cả hai phía qua mart.nhom_cua_khoa)
    SELECT DISTINCT ON (g.ma) g.ma, g.ten, g.lan_cuoi, g.so_ngay, nh.khoa AS nhom_khoa, nh.ten AS ten_nhom,
           tx.id AS tiep_xuc_id, tx.ngay AS tin_ngay
    FROM ngung g
    JOIN nh ON nh.khoa = g.nhom_khoa
    JOIN tx ON tx.id = nh.tiep_xuc_id
    ORDER BY g.ma, tx.thoi_diem DESC, tx.id DESC)
SELECT json_build_object(
  'tin', (SELECT coalesce(json_agg(json_build_object(
             'tiep_xuc_id', tx.id, 'ngay', tx.ngay, 'nguoi', tx.nguoi, 'noi_dung', tx.noi_dung,
             'nhac', (SELECT coalesce(json_agg(json_build_object('loai', z.loai,
                             'khoa', CASE WHEN z.loai = 'nhom' THEN mart.nhom_cua_khoa(z.khoa) ELSE z.khoa END,
                             'vi_tri_dau', z.vi_tri_dau, 'do_dai', z.do_dai) ORDER BY z.vi_tri_dau), '[]')
                      FROM app.tiep_xuc_nhac z WHERE z.tiep_xuc_id = tx.id),
             'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten) ORDER BY d.ma), '[]')
                         FROM dt d WHERE d.tiep_xuc_id = tx.id),
             'nhom', (SELECT coalesce(json_agg(json_build_object('khoa', h.khoa, 'ten', h.ten) ORDER BY h.khoa), '[]')
                      FROM nh h WHERE h.tiep_xuc_id = tx.id),
             'gia', (SELECT coalesce(json_agg(json_build_object('ma_doi_thu', t.ma_doi_thu, 'ten_doi_thu', d.ten,
                             'nhom_khoa', k.khoa, 'ten_nhom', h.ten, 'gia_goc', t.gia_goc, 'don_vi_gia', t.don_vi_gia)
                             ORDER BY t.id), '[]')
                     FROM app.gia_doi_thu_tay t
                     CROSS JOIN LATERAL (SELECT mart.nhom_cua_khoa(t.nhom_khoa) AS khoa) k
                     JOIN app.doi_thu d ON d.ma = t.ma_doi_thu
                     LEFT JOIN nh h ON h.tiep_xuc_id = t.tiep_xuc_id AND h.khoa = k.khoa
                     WHERE t.tiep_xuc_id = tx.id AND t.loai_nguon = 'khach_ke'))
           ORDER BY tx.thoi_diem DESC, tx.id DESC), '[]') FROM tx),
  'ly_do_ngung', (SELECT coalesce(json_agg(json_build_object(
             'ma', ly.ma, 'ten', ly.ten, 'nhom_khoa', ly.nhom_khoa, 'ten_nhom', ly.ten_nhom,
             'lan_cuoi', ly.lan_cuoi, 'so_ngay', ly.so_ngay, 'tiep_xuc_id', ly.tiep_xuc_id, 'tin_ngay', ly.tin_ngay,
             'doi_thu', (SELECT coalesce(json_agg(json_build_object('ma', d.ma, 'ten', d.ten) ORDER BY d.ma), '[]')
                         FROM dt d WHERE d.tiep_xuc_id = ly.tiep_xuc_id))
           ORDER BY ly.lan_cuoi DESC, ly.ma), '[]') FROM ly))
"""


def khach_doi_thu(conn, ma_khach: str, hom_nay=None) -> dict:
    """Khối "Đang mua của đối thủ" của hồ sơ khách 360 — MỘT lượt hỏi (hồ sơ `ho_so()` giữ trần 8 nên khối này
    đi endpoint riêng). NGAY_TIN_KHACH ngày qua theo ĐỒNG HỒ THẬT giờ Tokyo (`hom_nay_o_nhat`; xem `tong_quan`).

    `tin`: mỗi lần tiếp xúc có thẻ `@` — đối thủ, nhóm (khoá + tên), giá khách kể kèm theo, ngày, người ghi, câu gốc,
    và `nhac` = MỌI thẻ theo thứ tự trong câu (`vi_tri_dau` tăng dần; vị trí/độ dài theo KÝ TỰ Unicode như đã lưu ở
    `app.tiep_xuc_nhac` — giao diện đổi sang UTF-16 nếu cần tô chữ). Mọi khoá NHÓM trả ra (`nhac`, `nhom`, `gia`,
    `ly_do_ngung`) là khoá HIỆN HÀNH qua `mart.nhom_cua_khoa` — thẻ đã lưu giữ nguyên như lúc ghi. Giao diện ghép "đối thủ gần nhất đứng trước"
    từ đúng danh sách này (cùng vòng lặp lúc ghi), không dò chữ trong câu.
    `ly_do_ngung`: các cặp (khách, mã) `mart.khach_mat_hang.trang_thai_cap = 'ngung'` (bất biến 024) mà nhóm của mã —
    thẻ `ma:<mã>` hoặc `n:<nhóm có tên chứa mã>` — được nhắc trong các tin trên; mỗi mã một dòng, tin MỚI NHẤT nhắc
    nhóm đó, kèm các đối thủ được nhắc CÙNG lần tiếp xúc ấy."""
    return conn.execute(_KHACH_DOI_THU, {"ma": ma_khach, "hom_nay": hom_nay or hom_nay_o_nhat()}).fetchone()[0]
