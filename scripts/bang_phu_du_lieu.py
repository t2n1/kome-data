"""Bảng phủ dữ liệu: tháng nào có, tháng nào thiếu, theo từng loại file.

Cách tính nằm ở `kome/coverage.py` — DÙNG CHUNG với trang web `/phu-du-lieu`.
File này chỉ lo phần in ra terminal. Đừng tính lại ở đây: hai chỗ tính riêng
là hai chỗ nói hai con số khác nhau.

Chạy (từ thư mục dự án, chạy được ở cả PowerShell lẫn Git Bash):
    python scripts/bang_phu_du_lieu.py            # CSDL thật
    python scripts/bang_phu_du_lieu.py --test     # CSDL thử nghiệm

Script tự đọc file .env, không cần nạp biến môi trường trước.

Ký hiệu:
    ●  có dữ liệu trong kho
    ·  không có dữ liệu
    số  số ngày có ảnh chụp trong tháng (chỉ cột tồn kho)
    —  ngoài phạm vi dữ liệu (trước 2025-03-03 công ty không còn lưu)

LƯU Ý: dấu `·` KHÔNG phân biệt được hai trường hợp —
  (a) chưa bao giờ xuất file cho tháng đó, và
  (b) đã xuất nhưng file bị cổng kiểm tra chặn (ví dụ bản xuất thiếu, sai mẫu).
Lý do: cổng kiểm tra chặn TRƯỚC khi ghi nhật ký nạp, nên kho không hề biết
file đó từng tồn tại. Muốn biết chắc thì đối chiếu với thư mục xuất của OBC.
"""
import os
import sys
from pathlib import Path

import psycopg

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from kome.coverage import tinh_bang_phu


def main(url: str) -> int:
    with psycopg.connect(url) as c:
        bang = tinh_bang_phu(c)

    print(f"BẢNG PHỦ DỮ LIỆU — database: {bang.database}\n")
    print("  ● có dữ liệu   · không có   — ngoài phạm vi (công ty không còn lưu)")
    print("  Cột tồn kho hiện SỐ NGÀY có ảnh chụp trong tháng\n")

    # Nhãn cột dùng chữ Latin ngắn: ký tự tiếng Nhật rộng gấp đôi nên cột sẽ lệch
    # trong terminal. Tên đầy đủ in ở phần chú giải bên dưới bảng.
    head = f"{'Thang':<9}{'Ky':>4}  " + "".join(f"{c.nhan:<7}" for c in bang.cot)
    print(head)
    print("-" * len(head))

    for t in bang.thang:
        row = f"{t.thang:<9}{t.company_fy:>4}  "
        row += "".join(f"{o.ky_hieu:<7}" for o in t.o)
        print(row)

    # Tổng kết từng kỳ (doanh thu thuần / lãi gộp / tỷ suất) CỐ Ý chỉ hiện trên
    # trang /phu-du-lieu: đầu ra terminal giữ nguyên như trước. Số liệu vẫn nằm
    # sẵn trong `bang.ky` nếu sau này muốn in ra đây.
    print("\nChu giai cot:")
    for c in bang.cot:
        print(f"  {c.nhan:<7} {c.chu_giai}")

    print("\nLoai du lieu CHUA vao kho:")
    for l in bang.thieu_bo_nap:
        print(f"  {l.ten_obc}  ({l.mo_ta}) — {l.ghi_chu}")
    return 0


if __name__ == "__main__":
    from kome.env import nap_env

    nap_env()
    key = "DATABASE_URL_TEST" if "--test" in sys.argv else "DATABASE_URL"
    sys.exit(main(os.environ[key]))
