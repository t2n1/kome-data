"""Nạp gói bảng giá đối thủ qua luồng nạp chung (5 cổng, hoàn tác theo lô)."""
from datetime import date
import pandas as pd

from kome.loaders.doi_thu import COT_GIA, COT_DIEU_KIEN
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


def test_mot_o_nap_nhan_ca_hai_loai_file():
    from kome.kho_du_lieu import O_CUA
    assert O_CUA["doi_thu"]["specs"] == ["doi_thu_gia", "doi_thu_dieu_kien"]
