"""Bộ nạp gói bảng giá đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4.1).

Gói do scripts/goi_doi_thu.py dựng — tên cột của file = tên cột hệ thống (files.yml khai
ánh xạ đồng nhất). `gia_goc`, `gia_truoc_km`, `kg_moi_don_vi_gia` KHÔNG khai money_columns:
bộ đọc ép ô trống thành 0, còn ở đây trống ≠ 0 và có giá lẻ .5 yên — đổi sang số ở ĐÂY.
Chỉ INSERT (mỗi lô là một lần đọc; lô mới hơn thắng ở mart), không upsert.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd
import psycopg

COT_GIA = [
    "ma_dong", "ma_doi_thu", "ma_hang_dt", "ngay_nguon", "hinh_thuc_nguon", "nguon_file", "vi_tri",
    "ten_goc", "ten_nhat", "jan", "quy_cach_goc", "gia_goc", "don_vi_gia", "kg_moi_don_vi_gia",
    "thue", "gom_ship", "kenh_gia", "muc_gia", "gia_bac", "gia_truoc_km", "trang_thai", "han_su_dung",
    "khuyen_mai", "ma_kome_de_xuat", "nhan_de_xuat", "ly_do_ghep", "do_chac", "ghi_chu",
]
COT_DIEU_KIEN = ["ma_dong", "ma_doi_thu", "ngay_nguon", "nguon_file", "vi_tri", "loai", "noi_dung"]
_SO = {"gia_goc", "gia_truoc_km", "kg_moi_don_vi_gia"}


def _so(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return None
    try:
        return Decimal(str(v).replace(",", "").strip())
    except InvalidOperation:
        return None


def _chu(v):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    s = str(v).strip()
    return s or None


def _gia_tri(cot, v, data_date):
    if cot in _SO:
        return _so(v)
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
