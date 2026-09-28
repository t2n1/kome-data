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


# ---- kome/web/bang_tong_quan.py -----------------------------------------

from kome.web import bang_tong_quan as BT  # noqa: E402
from kome.web import bo_cuc as BC  # noqa: E402


def _ds(conn, nid):
    return conn.execute("SELECT id, ten, thu_tu FROM app.bang_tong_quan WHERE nguoi_dung_id = %s ORDER BY thu_tu",
                        (nid,)).fetchall()


def _loi(ham, *a):
    with pytest.raises(BT.LoiBang) as e:
        ham(*a)
    return e.value.ma


@pytest.mark.parametrize("ten,mong", [("  Kho  ", "Kho"), ("x" * 40, "x" * 40)])
def test_chuan_ten_cat_khoang_trang(ten, mong):
    assert BT.chuan_ten(ten) == mong


@pytest.mark.parametrize("ten", ["", "   ", "x" * 41, None, 5])
def test_chuan_ten_sai_la_422(ten):
    assert _loi(BT.chuan_ten, ten) == 422


def test_tu_tho_bo_phan_tu_hong_va_chuan_hoa_bo_cuc():
    ds = BT.tu_tho([{"id": 3, "ten": "A", "bo_cuc": [{"id": "kpi", "rong": 9}]}, {"ten": "không id"}, "rác"])
    assert [b.id for b in ds] == [3] and ds[0].bo_cuc[0] == BC.O("kpi", 3, 1)
    assert len(ds[0].bo_cuc) == len(BC.KHOI)
    assert BT.tu_tho(None) == [] and BT.tu_tho("không phải json") == []


def test_chon_theo_thu_tu_uu_tien():
    a, b = BT.Bang(1, "A", ()), BT.Bang(2, "B", ())
    assert BT.chon([a, b], "2", 1).id == 2          # ?bang= của mình
    assert BT.chon([a, b], "99", 2).id == 2         # ?bang= lạ -> gần nhất
    assert BT.chon([a, b], "x", None).id == 1       # rác, không gần nhất -> đầu
    assert BT.chon([a, b], None, 77).id == 1        # gần nhất không còn -> đầu
    assert BT.chon([], "1", 1).id is None           # không bảng nào -> ảo


def test_tao_tu_mac_dinh_vai_tro_va_chep(conn):
    a = _nguoi(conn, "an")
    m = BT.tao(conn, a, "Đầy đủ", "mac_dinh")
    assert m.bo_cuc == tuple(BC.mac_dinh())
    ma_vai, _, khoi_vai = BC.VAI_TRO[2]
    v = BT.tao(conn, a, "Kế toán", f"vai:{ma_vai}")
    assert {o.id for o in v.bo_cuc if not o.an} == set(khoi_vai)
    BT.luu_bo_cuc(conn, a, m.id, BC.chuan_hoa([{"id": "xu_huong", "rong": 1, "cao": 4}]))
    c = BT.tao(conn, a, "Bản chép", f"chep:{m.id}")
    assert c.bo_cuc[0] == BC.O("xu_huong", 1, 4)
    assert [r[2] for r in _ds(conn, a)] == [0, 1, 2]
    assert conn.execute("SELECT bang_gan_nhat FROM app.nguoi_dung WHERE id = %s", (a,)).fetchone()[0] == c.id


def test_tao_sai_quy_tac(conn):
    a, b = _nguoi(conn, "an"), _nguoi(conn, "binh")
    cua_b = BT.tao(conn, b, "Của Bình", "mac_dinh")
    BT.tao(conn, a, "Kho", "mac_dinh")
    assert _loi(BT.tao, conn, a, "  KHO ", "mac_dinh") == 409          # trùng
    assert _loi(BT.tao, conn, a, "X", "vai:khong_co") == 422
    assert _loi(BT.tao, conn, a, "X", "linh_tinh") == 422
    assert _loi(BT.tao, conn, a, "X", f"chep:{cua_b.id}") == 404       # chép bảng người khác
    for i in range(BT.TOI_DA - 1):
        BT.tao(conn, a, f"B{i}", "mac_dinh")
    assert _loi(BT.tao, conn, a, "Thừa", "mac_dinh") == 409
    assert len(_ds(conn, a)) == BT.TOI_DA


def test_bang_ao_luu_lan_dau_tao_DUNG_MOT_dong(conn):
    a = _nguoi(conn, "an")
    b1 = BT.luu_bo_cuc(conn, a, None, BC.chuan_hoa([{"id": "kpi", "rong": 1}]))
    b2 = BT.luu_bo_cuc(conn, a, None, BC.chuan_hoa([{"id": "kpi", "rong": 2}]))
    assert b1.id == b2.id and b1.ten == BT.TEN_MAC_DINH and len(_ds(conn, a)) == 1
    assert b2.bo_cuc[0].rong == 2


def test_so_huu_bang_nguoi_khac_la_404_va_khong_doi(conn):
    a, b = _nguoi(conn, "an"), _nguoi(conn, "binh")
    x = BT.tao(conn, b, "Của Bình", "mac_dinh")
    BT.tao(conn, a, "Của An", "mac_dinh")
    assert _loi(BT.luu_bo_cuc, conn, a, x.id, BC.mac_dinh()) == 404
    assert _loi(BT.doi_ten, conn, a, x.id, "Chiếm") == 404
    assert _loi(BT.xoa, conn, a, x.id) == 404
    assert _loi(BT.mo, conn, a, x.id) == 404
    assert _ds(conn, b)[0][1] == "Của Bình"


def test_doi_ten_xoa_va_bang_cuoi(conn):
    a = _nguoi(conn, "an")
    x, y = BT.tao(conn, a, "X", "mac_dinh"), BT.tao(conn, a, "Y", "mac_dinh")
    assert _loi(BT.doi_ten, conn, a, x.id, "y") == 409
    assert BT.doi_ten(conn, a, x.id, " Sáng thứ Hai ").ten == "Sáng thứ Hai"
    assert BT.doi_ten(conn, a, x.id, "sáng thứ hai").ten == "sáng thứ hai"   # đổi hoa thường của chính nó: được
    BT.mo(conn, a, y.id)
    assert BT.xoa(conn, a, y.id) == x.id
    assert conn.execute("SELECT bang_gan_nhat FROM app.nguoi_dung WHERE id = %s", (a,)).fetchone()[0] is None
    assert _loi(BT.xoa, conn, a, x.id) == 409


def test_sap_thu_tu_phai_dung_tap_bang_cua_minh(conn):
    a = _nguoi(conn, "an")
    x, y, z = (BT.tao(conn, a, t, "mac_dinh") for t in "XYZ")
    BT.sap_thu_tu(conn, a, [z.id, x.id, y.id])
    assert [r[1] for r in _ds(conn, a)] == ["Z", "X", "Y"]
    assert _loi(BT.sap_thu_tu, conn, a, [z.id, x.id]) == 422
    assert _loi(BT.sap_thu_tu, conn, a, [z.id, x.id, y.id, 999]) == 422
    assert _loi(BT.sap_thu_tu, conn, a, "rác") == 422
