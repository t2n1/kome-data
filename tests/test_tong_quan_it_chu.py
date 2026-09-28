"""Luật chữ của Tổng quan (đặc tả 2026-09-28-tong-quan-it-chu-design.md §4):
không bảng, không dòng `phu` tự do, câu cách tính của máy chủ đi qua ⓘ (`cach_tinh=`)."""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[1]
KHOI = (GOC / "giao_dien/src/tong_quan/khoi.tsx").read_text(encoding="utf-8")


def test_tong_quan_khong_con_bang():
    assert "<table" not in KHOI


def test_tong_quan_khong_con_dong_phu_tu_do():
    # `className="phu"`, `className="phu nhat-chu"`, `className={"phu …` — KHÔNG khớp `khoi-phu`, `tng-phu`.
    assert re.findall(r'className=\{?["`]phu(?![-\w])', KHOI) == []
    assert 'className="phu"' not in KHOI


def test_cach_tinh_may_chu_di_qua_i_khong_in_tran():
    assert re.findall(r">\s*\{d\??\.cach_tinh\}", KHOI) == []
    assert "cach_tinh={d?.cach_tinh}" in KHOI


def test_net_dut_chi_cho_ky_so_thang_nay_chua_mua_khong_ve_vach():
    """Khối Tháng này chưa mua so với THÁNG TRƯỚC — không phải kỳ so, nên không truyền `ss`
    / `nhan_ss` cho ThanhNgang (vạch đứt dành riêng cho kỳ so)."""
    than = KHOI.split("export function KhoiThangNay")[1].split("export function")[0]
    assert "nhan_ss" not in than and "ss:" not in than
