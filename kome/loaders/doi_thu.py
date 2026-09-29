"""Bộ nạp gói bảng giá đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.1).

Gói do scripts/goi_doi_thu.py dựng — tên cột của file = tên cột hệ thống (files.yml khai
ánh xạ đồng nhất). `gia_goc`, `gia_truoc_km`, `kg_moi_don_vi_gia` KHÔNG khai money_columns:
bộ đọc ép ô trống thành 0, còn ở đây trống ≠ 0 và có giá lẻ .5 yên — đổi sang số ở ĐÂY.
Chỉ INSERT (mỗi lô là một lần đọc; lô mới hơn thắng ở mart), không upsert.
"""
import json
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
import psycopg

COT_GIA = [
    "ma_dong", "ma_doi_thu", "ma_hang_dt", "ngay_nguon", "hinh_thuc_nguon", "nguon_file", "vi_tri",
    "ten_goc", "ten_nhat", "jan", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
    "thue", "gom_ship", "kenh_gia", "muc_gia", "gia_bac", "gia_truoc_km", "trang_thai", "han_su_dung",
    "khuyen_mai", "ma_kome_de_xuat", "nhan_de_xuat", "ly_do_ghep", "do_chac", "ghi_chu",
    "so_goi_thung", "kl_goi_g", "bac",
]
COT_DIEU_KIEN = ["ma_dong", "ma_doi_thu", "ngay_nguon", "nguon_file", "vi_tri", "loai", "noi_dung"]
COT_GIAO_HANG = [
    "ma_dong", "ma_doi_thu", "ngay_nguon", "bao_ship", "phi_ship", "phi_ship_theo", "mien_ship_tu", "mien_ship_kien",
    "thung_moi_kien", "phu_phi", "phi_daibiki", "daibiki_tu", "daibiki_sau", "ck_mien_daibiki", "kien_toi_da_kg",
    "ghep_kien", "thue", "cach_gui", "nguon_chu", "nguon_file",
]
_SO = {"gia_goc", "gia_truoc_km", "kg_moi_don_vi_gia", "so_goi_thung", "kl_goi_g",
       "phi_ship", "mien_ship_tu", "mien_ship_kien", "thung_moi_kien", "phi_daibiki", "daibiki_tu", "daibiki_sau",
       "kien_toi_da_kg"}
_JSON = {"bac", "phu_phi"}
_BOOL = {"bao_ship", "ck_mien_daibiki"}


def _so(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return None
    try:
        x = Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        return None
    return x if x.is_finite() else None       # 'NaN' / 'Infinity' → không ghi (NaN của Postgres lớn hơn mọi số: lọt CHECK '>= 0')


def _chu(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def _json(v):
    s = _chu(v)
    return None if s is None else json.dumps(json.loads(s), ensure_ascii=False)   # gói đã kiểm lược đồ (goi_doi_thu.py)


def _bool(v):
    s = _chu(v)
    if s is None:
        return None
    return {"true": True, "1": True, "co": True, "false": False, "0": False, "khong": False}[s.lower()]


def _gia_tri(cot, v, data_date):
    if cot in _SO:
        return _so(v)
    if cot in _JSON:
        return _json(v)
    if cot in _BOOL:
        return _bool(v)
    if cot == "ngay_nguon":
        return v or data_date
    return _chu(v)


def _nap(conn, bang, cot, df, data_date, batch_id) -> int:
    rows = [tuple(_gia_tri(c, getattr(r, c), data_date) for c in cot) + (batch_id,)
            for r in df.itertuples(index=False)]
    with conn.cursor() as cur:
        cur.executemany(
            f"INSERT INTO {bang} ({', '.join(cot)}, batch_id) VALUES ({', '.join(['%s'] * (len(cot) + 1))})",
            rows)
    conn.commit()
    return len(rows)


def load_gia(conn: psycopg.Connection, df: pd.DataFrame, data_date: date, batch_id: int) -> int:
    return _nap(conn, "core.fact_gia_doi_thu", COT_GIA, df, data_date, batch_id)


def load_dieu_kien(conn: psycopg.Connection, df: pd.DataFrame, data_date: date, batch_id: int) -> int:
    return _nap(conn, "core.fact_dieu_kien_doi_thu", COT_DIEU_KIEN, df, data_date, batch_id)


def load_giao_hang(conn: psycopg.Connection, df: pd.DataFrame, data_date: date, batch_id: int) -> int:
    return _nap(conn, "core.fact_giao_hang_doi_thu", COT_GIAO_HANG, df, data_date, batch_id)
