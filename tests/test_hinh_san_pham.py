"""Hình sản phẩm: MỘT nguồn `config/hinh_san_pham.csv` → `kome/hinh_san_pham.py`
→ `window.__KOME__.hinh` → `giao_dien/src/chung/HinhMa.tsx`."""
import re

from kome import hinh_san_pham as HSP
from tests.spa_kd import kd, nguon


def test_doc_file_that_163_ma_moi_url_https_ma_giu_nguyen_chu():
    HSP.xoa_nho()
    h = HSP.doc()
    assert len(h) == 163
    assert all(u.startswith("https://") for u in h.values())
    assert all(isinstance(m, str) and m == m.strip() and m for m in h)
    assert "AO02" in h and "HAB05" in h


def test_bo_dong_khong_phai_https_va_ma_so_0_dau_giu_nguyen(tmp_path, monkeypatch):
    f = tmp_path / "hinh.csv"
    f.write_text(
        "﻿sku,imageUrl\n"
        " 000123 ,https://a.example/1.jpg\n"
        "X1,http://a.example/2.jpg\n"
        "X2,javascript:alert(1)\n"
        "X3,  \n"
        ",https://a.example/3.jpg\n"
        "X4, HTTPS://a.example/4.jpg?modified=1 \n",
        encoding="utf-8")
    monkeypatch.setattr(HSP, "DUONG", f)
    HSP.xoa_nho()
    h = HSP.doc()
    assert h == {"000123": "https://a.example/1.jpg"}
    HSP.xoa_nho()


def test_file_thieu_tra_rong(tmp_path, monkeypatch):
    monkeypatch.setattr(HSP, "DUONG", tmp_path / "khong_co.csv")
    HSP.xoa_nho()
    assert HSP.doc() == {}
    HSP.xoa_nho()


def test_doi_file_thi_doc_lai(tmp_path, monkeypatch):
    import os
    f = tmp_path / "hinh.csv"
    f.write_text("sku,imageUrl\nA,https://a/1.jpg\n", encoding="utf-8")
    monkeypatch.setattr(HSP, "DUONG", f)
    HSP.xoa_nho()
    assert HSP.doc() == {"A": "https://a/1.jpg"}
    f.write_text("sku,imageUrl\nB,https://a/2.jpg\n", encoding="utf-8")
    st = f.stat()
    os.utime(f, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
    assert HSP.doc() == {"B": "https://a/2.jpg"}
    HSP.xoa_nho()


def test_trang_san_pham_co_hinh_trong_window_kome(test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    HSP.xoa_nho()
    r = TestClient(create_app(db_url=test_db_url)).get("/san-pham")
    assert r.status_code == 200
    d = kd(r.text)
    assert "hinh" in d and d["hinh"].get("AO02", "").startswith("https://")


def test_bon_cho_hien_dung_HinhMa_khong_tu_viet_img():
    cho = [("mua_vu", "ManMuaVu.tsx"), ("mua_vu", "BanDoNhiet.tsx"),
           ("san_pham", "ManSanPham.tsx"), ("san_pham", "ho_so", "HoSoMa.tsx"),
           ("khach", "HoSoTab.tsx"), ("lien_he", "LienHe.tsx")]
    for p in cho:
        s = nguon(*p)
        assert "HinhMa" in s, p
        assert not re.search(r"<img\b", s), p
    # Chỉ thành phần chung được đọc bản đồ hình.
    assert "hinhCua" in nguon("chung", "HinhMa.tsx")
