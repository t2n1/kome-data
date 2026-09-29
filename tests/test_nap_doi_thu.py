"""Nạp gói bảng giá đối thủ qua luồng nạp chung (5 cổng, hoàn tác theo lô)."""
from datetime import date
import pandas as pd
import pytest

from kome.loaders.doi_thu import COT_GIA, COT_DIEU_KIEN, COT_GIAO_HANG
from kome.pipeline import ingest, undo_batch


def _dong(i, **kw):
    d = {c: None for c in COT_GIA}
    d.update(ma_dong=f"THAK-{i:05d}", ma_doi_thu="THAK", ma_hang_dt=f"jan:893000000000{i}",
             ngay_nguon="2026-08-05", hinh_thuc_nguon="file", nguon_file="THAK-HANG-KHO.pdf",
             vi_tri=f"tr{i}", ten_goc=f"Hàng {i}", gia_goc="335", don_vi_gia="goi",
             kg_moi_don_vi_gia="0.052", thue="co", gom_ship="khong_ro", trang_thai="con", do_chac="chac")
    d.update(kw)
    return d


def _goi_gia(tmp_path, dong, ngay="20260831"):
    p = tmp_path / f"doi_thu_gia_{ngay}.xlsx"
    pd.DataFrame(dong, columns=COT_GIA).to_excel(p, sheet_name="gia", index=False)
    return p


def test_nap_gia_giu_ma_la_chu_va_gia_trong_la_NULL(conn, tmp_path):
    p = _goi_gia(tmp_path, [_dong(1), _dong(2, gia_goc=None, jan="0012345678905"), _dong(3, gia_goc="172.5")])
    r = ingest(conn, p, tmp_path / "archive")
    assert r.ok, r.blockers
    rows = conn.execute("SELECT ma_dong, gia_goc, jan, ngay_nguon FROM core.fact_gia_doi_thu ORDER BY ma_dong").fetchall()
    assert rows[0][1] == 335 and rows[1][1] is None and float(rows[2][1]) == 172.5
    assert rows[1][2] == "0012345678905"          # số 0 đầu còn nguyên (bẫy #1)
    assert rows[0][3] == date(2026, 8, 5)


def test_hoan_tac_xoa_sach_lo(conn, tmp_path):
    r = ingest(conn, _goi_gia(tmp_path, [_dong(1), _dong(2)]), tmp_path / "archive")
    undo_batch(conn, r.batch_id)
    assert conn.execute("SELECT count(*) FROM core.fact_gia_doi_thu").fetchone()[0] == 0


def test_dieu_kien_nap_rieng(conn, tmp_path):
    p = tmp_path / "doi_thu_dieu_kien_20260831.xlsx"
    pd.DataFrame([{"ma_dong": "YUMI-00001", "ma_doi_thu": "YUMI", "ngay_nguon": "2026-08-01",
                   "nguon_file": "YUMI FOODS.pdf", "vi_tri": "tr1", "loai": "ship",
                   "noi_dung": "Kiện 28kg ghép 3 sản phẩm - bao thuế bao ship!"}],
                 columns=COT_DIEU_KIEN).to_excel(p, sheet_name="dieu_kien", index=False)
    assert ingest(conn, p, tmp_path / "archive").ok
    assert conn.execute("SELECT loai FROM core.fact_dieu_kien_doi_thu").fetchone()[0] == "ship"


def test_nap_gia_mang_quy_cach_goi_va_bac_la_json(conn, tmp_path):
    bac = '[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]'
    p = _goi_gia(tmp_path, [_dong(1, so_goi_thung="20", kl_goi_g="500", bac=bac), _dong(2)])
    r = ingest(conn, p, tmp_path / "archive")
    assert r.ok, r.blockers
    rows = conn.execute("SELECT so_goi_thung, kl_goi_g, bac FROM core.fact_gia_doi_thu ORDER BY ma_dong").fetchall()
    assert rows[0][0] == 20 and float(rows[0][1]) == 500
    assert rows[0][2] == [{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]
    assert rows[1] == (None, None, None)          # trống = NULL, không phải 0


def _goi_giao_hang(tmp_path, dong, ngay="20260831"):
    p = tmp_path / f"doi_thu_giao_hang_{ngay}.xlsx"
    pd.DataFrame(dong, columns=COT_GIAO_HANG).to_excel(p, sheet_name="giao_hang", index=False)
    return p


def test_nap_giao_hang_NULL_la_khong_ghi_va_phu_phi_la_json(conn, tmp_path):
    d = {c: None for c in COT_GIAO_HANG}
    d.update(ma_dong="IMAI-00001", ma_doi_thu="IMAI", ngay_nguon="2026-08-31", bao_ship="false", phi_ship="605",
             phi_ship_theo="thung", mien_ship_tu="20000", phu_phi='{"tohoku": 400, "hokkaido": 800}', phi_daibiki="440",
             nguon_chu="Free delivery for over ¥20,000")
    r = ingest(conn, _goi_giao_hang(tmp_path, [d]), tmp_path / "archive")
    assert r.ok, r.blockers
    row = conn.execute("""SELECT bao_ship, phi_ship, phi_ship_theo, mien_ship_tu, phu_phi, phi_daibiki, daibiki_tu, thue
                          FROM core.fact_giao_hang_doi_thu""").fetchone()
    assert row[0] is False and row[1] == 605 and row[2] == "thung" and row[3] == 20000
    assert row[4] == {"tohoku": 400, "hokkaido": 800} and row[5] == 440
    assert row[6] is None and row[7] is None       # không ghi → NULL


def test_hoan_tac_giao_hang_xoa_sach_lo(conn, tmp_path):
    d = {c: None for c in COT_GIAO_HANG}
    d.update(ma_dong="YUMI-00001", ma_doi_thu="YUMI", ngay_nguon="2026-08-31", bao_ship="true")
    r = ingest(conn, _goi_giao_hang(tmp_path, [d]), tmp_path / "archive")
    assert r.ok, r.blockers
    undo_batch(conn, r.batch_id)
    assert conn.execute("SELECT count(*) FROM core.fact_giao_hang_doi_thu").fetchone()[0] == 0


def test_mot_o_nap_nhan_ca_ba_loai_file():
    from kome.kho_du_lieu import O_CUA
    assert O_CUA["doi_thu"]["specs"] == ["doi_thu_gia", "doi_thu_dieu_kien", "doi_thu_giao_hang"]


@pytest.mark.parametrize("v", ["NaN", "nan", "Infinity", "-inf", "sNaN", float("inf")])
def test_bo_nap_khong_bao_gio_luu_so_NaN_hay_vo_han(v):
    from kome.loaders.doi_thu import _so
    assert _so(v) is None


def test_bo_nap_van_doc_so_thuong():
    from decimal import Decimal
    from kome.loaders.doi_thu import _so
    assert _so("1,234.5") == Decimal("1234.5") and _so(" 605 ") == Decimal("605") and _so("") is None
