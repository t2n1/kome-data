"""Màn / khối CHƯA LÀM (chưa có nguồn dữ liệu) — MỘT công tắc.

Quyết định chủ DN 2026-09-28: tạm ẩn cho bớt rối, để đó làm sau. Không xoá gì:
khung "chưa có dữ liệu" (`kome.khoi_tong_quan.CHUA_CO`) và mục thanh bên
(`giao_dien/src/khung/muc.ts`, `url: null`) vẫn còn nguyên — chỉ không hiện.

  * `HIEN = False` → khối trong `KHOI` rời danh mục Tổng quan (`kome/web/bo_cuc.py`:
    không hiện, không có trong "Thêm chức năng" và mẫu vai trò; bố cục đã lưu có
    nó thì `chuan_hoa` bỏ qua), và thanh bên bỏ mọi mục mờ "chưa có" (nhóm hết
    mục thì bỏ luôn tiêu đề nhóm) — giao diện đọc cờ qua `window.__KOME__.hien_chua_co`.
  * Làm xong MỘT khối: viết hàm dữ liệu cho nó (`khoi_tong_quan.KHOI`), bỏ nó khỏi
    `CHUA_CO` và khỏi `KHOI` ở đây. Làm xong một màn: cho mục đó `url`.
  * Muốn xem lại tất cả khung "chưa có": đặt `HIEN = True`.

`KHOI` phải bằng đúng tập khoá của `khoi_tong_quan.CHUA_CO` (có test canh) — chép
ở đây để `bo_cuc` khỏi nhập `khoi_tong_quan` (kéo theo mọi mô-đun chỉ số).
"""
from __future__ import annotations

HIEN: bool = False

KHOI: frozenset[str] = frozenset({"dong_tien", "mua_hang", "khieu_nai", "hang_sap_ve", "thoi_tiet", "nhip_mua"})
