"""Nhiều bảng Tổng quan có tên cho mỗi người (056, kome/web/bang_tong_quan.py).
Đặc tả: docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md"""
import json
import re
from pathlib import Path

import psycopg
import pytest

GOC = Path(__file__).resolve().parents[1]
MIG = GOC / "db" / "migrations" / "056_bang_tong_quan.sql"


def _nguoi(conn, ten, bo_cuc=None):
    from kome.web import nguoi_dung as ND
    ND.tao(conn, ten, "mat-khau-bang-2026")
    if bo_cuc is not None:
        conn.execute("UPDATE app.nguoi_dung SET bo_cuc_tong_quan = %s WHERE ten_dang_nhap = %s",
                     (json.dumps(bo_cuc), ten))
    return conn.execute("SELECT id FROM app.nguoi_dung WHERE ten_dang_nhap = %s", (ten,)).fetchone()[0]


def _khoi_chep():
    m = re.search(r"-- CHEP: bat dau\n(.*?)-- CHEP: ket thuc", MIG.read_text(encoding="utf-8"), re.S)
    assert m, "056 thiếu khối chép dữ liệu cũ"
    return m.group(1)


# ---- Migration 056 -------------------------------------------------------

def test_056_chep_bo_cuc_cu_thanh_bang_cua_toi(conn):
    a = _nguoi(conn, "an", [{"id": "kpi", "rong": 1}])
    b = _nguoi(conn, "binh")                     # chưa từng sắp xếp
    conn.execute(_khoi_chep())
    conn.execute(_khoi_chep())                   # chạy lại không nhân dòng
    ds = conn.execute("SELECT nguoi_dung_id, ten, bo_cuc, thu_tu FROM app.bang_tong_quan").fetchall()
    assert [(r[0], r[1], r[3]) for r in ds] == [(a, "Bảng của tôi", 0)]
    assert ds[0][2][0]["id"] == "kpi"
    gan = dict(conn.execute("SELECT id, bang_gan_nhat FROM app.nguoi_dung").fetchall())
    assert gan[a] is not None and gan[b] is None


def test_ten_trung_khong_phan_biet_hoa_thuong_va_khoang_trang(conn):
    a = _nguoi(conn, "an")
    conn.execute("INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, thu_tu) VALUES (%s, 'Kho', 0)", (a,))
    with pytest.raises(psycopg.errors.UniqueViolation):
        conn.execute("INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, thu_tu) VALUES (%s, ' kho ', 1)", (a,))


def test_xoa_bang_gan_nhat_dat_ve_null(conn):
    a = _nguoi(conn, "an")
    bid = conn.execute("INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, thu_tu) VALUES (%s, 'X', 0) RETURNING id",
                       (a,)).fetchone()[0]
    conn.execute("UPDATE app.nguoi_dung SET bang_gan_nhat = %s WHERE id = %s", (bid, a))
    conn.execute("DELETE FROM app.bang_tong_quan WHERE id = %s", (bid,))
    assert conn.execute("SELECT bang_gan_nhat FROM app.nguoi_dung WHERE id = %s", (a,)).fetchone()[0] is None


def test_quyen_kome_app_ghi_duoc_kome_report_chi_doc(conn):
    def q(vai, p):
        return conn.execute("SELECT has_table_privilege(%s, 'app.bang_tong_quan', %s)", (vai, p)).fetchone()[0]
    assert all(q("kome_app", p) for p in ("SELECT", "INSERT", "UPDATE", "DELETE"))
    assert q("kome_report", "SELECT") and not q("kome_report", "INSERT")
    assert conn.execute("SELECT has_sequence_privilege('kome_app', 'app.bang_tong_quan_id_seq', 'USAGE')").fetchone()[0]
