"""Cần gọi theo SẢN PHẨM (2026-10-16) — `kome.lien_he.theo_san_pham` + `/api/lien-he/san-pham`.

Không chỉ số mới: ba nhóm phải là ĐÚNG định nghĩa có sẵn của cặp khách–mã (024 / 053) — test so thẳng với chúng."""
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from kome import lien_he as LH
from kome.tuoi_du_lieu import hom_nay_o_nhat
from kome.web.app import create_app
from tests.test_khach_hang import _ho_so_khach, _neo, HOM_NAY
from tests.test_mart_sp360 import _dong, _sp_du


def _nen(conn, batch):
    """C1, C2 cùng ngành 米_VNM. Nhịp 7 ngày trừ khi ghi khác.
    - KL: mua C1 4 lần, lần cuối 8 ngày trước → quá ngày dự kiến 1 ngày, chưa tới 2× nhịp → ĐẾN LÚC MUA LẠI
    - KN: mua C1 4 lần, lần cuối 20 ngày trước → ≥ 2× nhịp → ĐÃ NGỪNG
    - KC: mua đều C2, chưa từng mua C1 → NÊN CHÀO (sale 0102)
    - KB: mua C1 nhịp 30 ngày, lần cuối 1 ngày trước → còn 29 ngày → KHÔNG vào nhóm nào
    - KX: ※廃業※ mua C1 như KL → không bao giờ vào danh sách gọi"""
    _sp_du(conn, batch, "C1", ten="Gạo một", nganh="米_VNM")
    _sp_du(conn, batch, "C2", ten="Gạo hai", nganh="米_VNM")
    for ma, ten, sale, ma_hang, nhip, cuoi in (
            ("KL01", "Lai", "0104", "C1", 7, 8), ("KN01", "Ngung", "0104", "C1", 7, 20),
            ("KC01", "Chao", "0102", "C2", 7, 1), ("KB01", "Binh", "0104", "C1", 30, 1),
            ("KX01", "※廃業※ Dong", "0104", "C1", 7, 8)):
        _ho_so_khach(conn, batch, ma, ten, salesperson_code=sale)
        for i in range(4):
            _dong(conn, batch, ma, HOM_NAY - timedelta(days=cuoi + i * nhip), ma_hang)
    _neo(conn, batch)


def _nhom(r):
    return {n["loai"]: {k["ma"] for k in n["khach"]} for n in r["nhom"]}


def test_ba_nhom_dung_dinh_nghia(conn, batch):
    _nen(conn, batch)
    r = LH.theo_san_pham(conn, ["C1"], hom_nay_o_nhat())
    assert _nhom(r) == {"lai": {"KL01"}, "ngung": {"KN01"}, "chao": {"KC01"}}
    assert r["san_pham"] == [{"ma": "C1", "ten": "Gạo một", "co": True}]
    viec = r["nhom"][0]["khach"][0]["viec"]
    assert [(v["loai"], v["con"]) for v in viec] == [("lai", -1)]


def test_nhom_TRUNG_TAP_voi_nhan_cap_va_nen_chao_cua_san_pham_360(conn, batch):
    """[CRITICAL] Một định nghĩa: 'ngung' = trang_thai_cap 'ngung' (024), 'chao' = mart.sp_khach_nen_chao (053),
    'lai' ⊆ cặp 'mua' có ngày dự kiến (vị từ của ho_so_khach.lich_mua)."""
    _nen(conn, batch)
    n = _nhom(LH.theo_san_pham(conn, ["C1"], hom_nay_o_nhat()))
    cap = conn.execute("SELECT customer_code, trang_thai_cap, du_kien_lan_toi FROM mart.khach_mat_hang_cua(ARRAY['C1'])").fetchall()
    assert n["ngung"] == {c for c, t, _ in cap if t == "ngung"}
    assert n["lai"] <= {c for c, t, d in cap if t == "mua" and d is not None}
    assert n["chao"] == {c for (c,) in conn.execute("SELECT customer_code FROM mart.sp_khach_nen_chao('C1')").fetchall()}


def test_nhieu_ma_moi_khach_vao_nhom_KHAN_NHAT_va_mang_moi_ly_do(conn, batch):
    _nen(conn, batch)
    r = LH.theo_san_pham(conn, ["C2", "C1"], hom_nay_o_nhat())
    n = _nhom(r)
    # KL: lai với C1 + nên chào C2 → nhóm lai, hai lý do.
    assert "KL01" in n["lai"] and "KL01" not in n["chao"]
    kl = next(k for x in r["nhom"] for k in x["khach"] if k["ma"] == "KL01")
    assert [(v["loai"], v["ma"]) for v in kl["viec"]] == [("lai", "C1"), ("chao", "C2")]
    tat_ca = [k["ma"] for x in r["nhom"] for k in x["khach"]]
    assert len(tat_ca) == len(set(tat_ca))   # không khách nào ở hai nhóm


def test_loc_theo_sale_va_ban_nhanh_bo_nhom_chao(conn, batch):
    _nen(conn, batch)
    assert _nhom(LH.theo_san_pham(conn, ["C1"], hom_nay_o_nhat(), sale="0102")) == {"lai": set(), "ngung": set(), "chao": {"KC01"}}
    r = LH.theo_san_pham(conn, ["C1"], hom_nay_o_nhat(), chao=False)
    assert _nhom(r) == {"lai": {"KL01"}, "ngung": {"KN01"}} and r["du"] is False


def test_mot_luot_hoi(conn, batch, monkeypatch):
    _nen(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    LH.theo_san_pham(conn, ["C1", "C2"], hom_nay_o_nhat())
    assert dem["n"] == 1


def test_doc_ma_giu_chu_bo_trung_va_cat_toi_da():
    assert LH.doc_ma_sp(" 000123 ,C1,,000123") == ["000123", "C1"]
    assert len(LH.doc_ma_sp(",".join(f"M{i}" for i in range(9)))) == LH.SP_TOI_DA


def test_khong_chon_ma_thi_rong_khong_hoi(conn):
    assert LH.theo_san_pham(conn, [], hom_nay_o_nhat())["nhom"] == []


@pytest.fixture
def client(conn, test_db_url):
    return TestClient(create_app(db_url=test_db_url), follow_redirects=False)


def test_api(client, conn, batch):
    _nen(conn, batch)
    r = client.get("/api/lien-he/san-pham?ma=C1&tat_ca=1")
    assert r.status_code == 200
    assert _nhom(r.json()) == {"lai": {"KL01"}, "ngung": {"KN01"}, "chao": {"KC01"}}
    r = client.get("/api/lien-he/san-pham?ma=C1&tat_ca=1&nhanh=1")
    assert set(_nhom(r.json())) == {"lai", "ngung"}
