"""Công tắc ẩn màn / khối CHƯA LÀM (kome/man_chua_co.py — chủ DN chốt 2026-09-28)."""
from pathlib import Path

from kome import khoi_tong_quan as KTQ
from kome import man_chua_co as MCC
from kome.web import bo_cuc as BC

GOC = Path(__file__).resolve().parents[1]


def test_danh_sach_khoi_chua_lam_DUNG_BANG_CHUA_CO():
    """Bản chép ở man_chua_co phải trùng khoá của khoi_tong_quan.CHUA_CO — lệch là một
    khối chưa làm lọt lên Tổng quan, hoặc một khối đã làm xong vẫn bị ẩn."""
    assert set(MCC.KHOI) == set(KTQ.CHUA_CO)


def test_tat_cong_tac_thi_khoi_chua_lam_roi_danh_muc_va_mau_vai_tro():
    ma = {k["id"] for k in BC.danh_muc()["khoi"]}
    vai = {x for v in BC.danh_muc()["vai_tro"] for x in v["khoi"]}
    if MCC.HIEN:
        assert set(MCC.KHOI) <= ma
    else:
        assert not set(MCC.KHOI) & ma and not set(MCC.KHOI) & vai


def test_bo_cuc_da_luu_co_khoi_chua_lam_van_doc_duoc():
    ra = BC.chuan_hoa([{"id": "dong_tien", "rong": 1, "cao": 1}, {"id": "kpi", "rong": 3, "cao": 1}])
    ids = [o.id for o in ra]
    assert "kpi" in ids and (MCC.HIEN or "dong_tien" not in ids)


def test_thanh_ben_doc_co_hien_chua_co_cua_may_chu():
    muc = (GOC / "giao_dien/src/khung/muc.ts").read_text(encoding="utf-8")
    assert "KD.hien_chua_co" in muc and "g.muc.filter(m => m.url)" in muc
    app = (GOC / "kome/web/app.py").read_text(encoding="utf-8")
    assert '"hien_chua_co": MCC.HIEN' in app


def test_o_phai_tra_cua_khoi_chi_so_cung_theo_cong_tac():
    khoi = (GOC / "giao_dien/src/tong_quan/khoi.tsx").read_text(encoding="utf-8")
    assert '{KD.hien_chua_co && <OKpi chua nhan="Phải trả 7 ngày"' in khoi
