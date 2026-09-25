"""Nguồn OBC công ty CHƯA dùng — MỘT chỗ khai báo.

Quyết định chủ DN 2026-09-24: công ty chỉ xuất 売上明細表 / 在庫一覧 /
得意先全情報 / 直送先 (+ 商品データ). Chưa theo dõi công nợ, bảng giá theo bậc,
nhà cung cấp. Bộ nạp, bảng, view và màn hình của ba nguồn đó VẪN CÒN (không
xoá code đã chạy, không đụng migration) — chỉ ẨN khỏi giao diện: ô nạp, sơ đồ
nguồn, bảng phủ, "Duyệt bảng" của Kho dữ liệu; mục "Công nợ & thu tiền" ở thanh
bên; khối/ô công nợ ở Dashboard và màn Khách hàng; thẻ "giá theo bậc" ở hồ sơ
khách / hồ sơ mã. Ba trang tài liệu sống (/kho-du-lieu/luong, /cot-noi,
/duong-di) cố ý VẪN liệt kê đủ — chúng mô tả cái kho BIẾT nạp.

Bật lại một nguồn = bỏ nó khỏi CHUA_DUNG. Không có chỗ thứ hai phải sửa.
Module này không nhập gì nặng (bo_cuc, kho_du_lieu, web đều đọc nó).
"""
from __future__ import annotations

CHUA_DUNG: frozenset[str] = frozenset({"shiiresaki", "tanka", "seikyu_motocho"})

# Tính năng nào sống nhờ nguồn nào. Giao diện đọc `tinh_nang()` qua
# window.__KOME__.tinh_nang — không tự đoán từ tên spec.
_TINH_NANG = {"cong_no": "seikyu_motocho", "bang_gia": "tanka", "nha_cung_cap": "shiiresaki"}

# View của `mart` CHỈ phục vụ một nguồn chưa dùng — ẩn khỏi "Duyệt bảng" cùng
# bảng core của nguồn đó (core_table đọc từ files.yml, không chép ở đây).
MART_CUA = {"seikyu_motocho": ("mart.cong_no_ben_tra", "mart.cong_no_phieu", "mart.so_cong_no_moi_nhat")}


def dung(spec: str) -> bool:
    return spec not in CHUA_DUNG


def tinh_nang() -> dict[str, bool]:
    return {ten: dung(spec) for ten, spec in _TINH_NANG.items()}


def bang_an(specs) -> set[str]:
    """Bảng core + view mart của các nguồn chưa dùng. `specs` = kome.config.SPECS."""
    ra = {specs[s].core_table for s in CHUA_DUNG if s in specs and specs[s].core_table}
    for s in CHUA_DUNG:
        ra.update(MART_CUA.get(s, ()))
    return ra
