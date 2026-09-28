"""Cách xem của từng khối Tổng quan (đặc tả 2026-09-29-tong-quan-luoi-12-cot-design.md §2.5).

Danh mục ở máy chủ (`bo_cuc.CACH_XEM`); giao diện đọc nó qua `useCachXem`. Các test canh
hai chiều: mọi cách xem trong danh mục có nhánh vẽ trong khoi.tsx, và khối nào đọc
`useCachXem` thì có mặt trong danh mục (không có cách xem chỉ sống ở giao diện)."""
import re
from pathlib import Path

from kome.web import bo_cuc as BC

GOC = Path(__file__).resolve().parents[1]
KHOI = (GOC / "giao_dien/src/tong_quan/khoi.tsx").read_text(encoding="utf-8")


def _than_ham():
    phan = re.split(r"\nexport function (\w+)", KHOI)
    return {phan[i]: phan[i + 1] for i in range(1, len(phan), 2)}


def _ham_cua_khoi():
    """`VE` của khoi.tsx: mã khối -> tên thành phần."""
    ve = KHOI.split("export const VE")[1].split("};")[0]
    return dict(re.findall(r"(\w+): (?:p|\(\)) => <(\w+)", ve))


def test_moi_cach_xem_co_nhanh_ve_trong_khoi_tsx():
    than, ham = _than_ham(), _ham_cua_khoi()
    for ma, cach in BC.CACH_XEM.items():
        ten = ham[ma]
        t = than[ten]
        assert f'useCachXem("{ma}", p)' in t, f"{ten} không đọc cách xem của {ma}"
        assert "cach_xem={" in t, f"{ten} không đưa dải cách xem vào <Khoi>"
        assert f"{ma}: p => <{ten} {{...p}} />" in KHOI, f"VE không truyền xem cho {ma}"
        for m, _ in cach[1:]:          # cách đầu là nhánh mặc định (else)
            assert f'"{m}"' in t, f"{ten}: thiếu nhánh vẽ cho cách xem '{m}'"


def test_khong_co_cach_xem_chi_song_o_giao_dien():
    doc = set(re.findall(r'useCachXem\("(\w+)"', KHOI))
    assert doc == set(BC.CACH_XEM)


def test_cach_xem_khong_ve_net_dut_cho_thu_khong_phai_ky_so():
    """Nét đứt / cột ma chỉ dành cho kỳ so (đặc tả 2026-09-28 §6) — kể cả ở cách xem mới:
    mọi chuỗi `duong_dut` / `cot_ma` phải lấy màu kỳ so."""
    for m in re.finditer(r'kieu: [^,]*"(duong_dut|cot_ma)"[^}]*', KHOI):
        assert "MAU_SS" in m.group(0), m.group(0)
