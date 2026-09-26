"""Tầng Python + API của Sản phẩm 360 (kome/san_pham_360.py)."""
from datetime import timedelta

import pytest

from kome import khach_hang as KH
from kome import ho_so_khach as HSK
from kome import san_pham_360 as SP360
from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY
from tests.test_mart_san_pham import _san_pham, _ton
from tests.test_san_pham import _dem_truy_van, _gia, _khach_web


def _gieo_mot_ma(conn, batch, ma="Q1"):
    _san_pham(conn, batch, ma, ten="Gạo thử 360")
    _ton(conn, batch, ma, sl=300)
    _ho_so_khach(conn, batch, "KQ01", "Quán đều")
    for i in range(4):
        _mua(conn, batch, "KQ01", HOM_NAY - timedelta(days=i * 7), hang=ma)
    _gia(conn, batch, ma, "03", 5250)
    _neo(conn, batch)


def test_ho_so_khong_co_ma_tra_None(conn, batch):
    _neo(conn, batch)
    assert SP360.ho_so(conn, "KHONG-CO") is None


def test_ho_so_khong_qua_5_truy_van_va_khong_rong(conn, batch, monkeypatch):
    _gieo_mot_ma(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    h = SP360.ho_so(conn, "Q1")
    assert h is not None and h["sp"].ma == "Q1"
    assert dem["n"] <= 5, f"ho_so() chạy {dem['n']} truy vấn"


def test_ho_so_24_thang_co_cot_nam_truoc(conn, batch):
    _gieo_mot_ma(conn, batch)
    t = SP360.ho_so(conn, "Q1")["thang"]
    assert len(t) == 24 and t[-1]["thang"] == f"{HOM_NAY:%Y-%m}"
    assert t[-1]["doanh_thu"] > 0
    assert t[-1]["dt_nam_truoc"] == t[-13]["doanh_thu"]


def test_mua_lai_TRUNG_TAP_voi_lich_mua_cua_ho_so_khach(conn, batch):
    """[CRITICAL] Một khái niệm hai chiều: cặp (khách, mã) nằm ở "khách đến ngày mua lại"
    của mã khi và chỉ khi mã nằm ở "Mã đến ngày mua lại" (lich_mua) của khách."""
    _gieo_mot_ma(conn, batch)
    h = SP360.ho_so(conn, "Q1")
    ma_khach = {x["ma"] for x in h["mua_lai"]}
    kh = KH.ho_so(conn, "KQ01")
    lich = HSK.lich_mua(kh.tat_ca_mat_hang, HOM_NAY)   # đúng lời gọi của ho_so_khach.py:154
    co_q1 = any(m["ma"] == "Q1" for m in lich["ma"])
    assert ("KQ01" in ma_khach) == co_q1
    assert co_q1, "gieo hỏng: KQ01 mua 4 lần nhịp 7 ngày phải có ngày dự kiến"
