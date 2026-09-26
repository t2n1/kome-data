"""Nguồn OBC công ty chưa dùng (kome/nguon_dung.py) — MỘT chỗ khai báo, mọi
màn đọc theo nó. Quyết định chủ DN 2026-09-24: chưa dùng công nợ, bảng giá,
nhà cung cấp."""
from pathlib import Path

from kome import coverage as COV, kho_du_lieu as KDL, nguon_dung as ND
from kome.config import SPECS
from kome.web import bo_cuc as BC

GOC = Path(__file__).resolve().parents[1]


def test_chua_dung_la_spec_co_that():
    assert ND.CHUA_DUNG <= set(SPECS), "khai một spec không tồn tại là ẩn nhầm chỗ khác"
    assert ND.tinh_nang() == {"cong_no": False, "bang_gia": False, "nha_cung_cap": False}


def test_kho_du_lieu_bo_nguon_chua_dung_ca_o_nap_lan_bang_phu():
    assert [o["ma"] for o in KDL.O_DUNG] == ["ban", "ton", "khach", "sp", "giao"]
    assert [c.khoa for c in COV.COT_DUNG] == ["ban", "ton", "tokuisaki", "shohin", "chokusousaki"]
    # COT đủ 8 vẫn là mô tả cho tài liệu sống (/kho-du-lieu/luong) — cố ý giữ.
    assert len(COV.COT) == 8


def test_bang_an_gom_core_va_mart_cua_cong_no():
    an = ND.bang_an(SPECS)
    assert {"core.dim_supplier", "core.fact_price_list", "core.fact_ar_ledger",
            "mart.cong_no_ben_tra", "mart.cong_no_phieu", "mart.so_cong_no_moi_nhat"} == an


def test_khoi_cong_no_khong_vao_danh_muc_hay_vai_tro_va_bo_cuc_cu_bo_qua_no():
    ma = [k["id"] for k in BC.danh_muc()["khoi"]]
    assert "cong_no" not in ma
    assert all("cong_no" not in v["khoi"] for v in BC.danh_muc()["vai_tro"])
    assert "cong_no" not in [o.id for o in BC.chuan_hoa([{"id": "cong_no", "rong": 1, "cao": 2}])]


def test_giao_dien_doc_co_tinh_nang_cua_may_chu_khong_tu_chep():
    """Các màn React ẩn theo `TN` (window.__KOME__.tinh_nang) — một nguồn."""
    src = GOC / "giao_dien" / "src"
    kd = (src / "khoi_dau.ts").read_text(encoding="utf-8")
    assert "export const TN" in kd and "KD.tinh_nang" in kd
    for f, dau_hieu in {"khung/muc.ts": "TN.cong_no", "tong_quan/khoi.tsx": "TN.cong_no && <OKpiCongNo",
                        "khach/HoSo.tsx": "TN.cong_no",
                        "khach/DanhSach.tsx": "TN.cong_no", "san_pham/HoSoSanPham.tsx": "TN.bang_gia"}.items():
        assert dau_hieu in (src / f).read_text(encoding="utf-8"), f
