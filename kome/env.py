"""Đọc file .env để mọi script chạy được mà không cần nạp biến môi trường trước.

Vì sao cần: người dùng hệ thống này không rành kỹ thuật, và máy chạy Windows —
nơi PowerShell KHÔNG hiểu cú pháp `set -a; source .env` của Bash. Bắt họ nhớ
nạp biến môi trường trước khi chạy là cách chắc chắn để lệnh trong sổ tay
không chạy được đúng lúc cần nhất.

Quan trọng hơn: **Windows Task Scheduler chạy lệnh trong môi trường trống rỗng**.
Lệnh sao lưu hằng đêm nếu phụ thuộc biến môi trường đã nạp sẵn sẽ lỗi mỗi đêm
mà không ai biết — và một bản sao lưu không bao giờ chạy thì bằng không.

Biến môi trường đã có sẵn LUÔN được ưu tiên, nên chạy trong CI hoặc container
(nơi không có file .env) vẫn hoạt động bình thường.
"""
import os
import sys
from pathlib import Path


def nap_env(bat_buoc: bool = True) -> Path | None:
    """Nạp `.env` tìm được gần nhất, đi ngược lên từ vị trí file này.

    Không ghi đè biến môi trường đã có. Trả về đường dẫn file đã đọc, hoặc None.
    Đặt `bat_buoc=False` nếu thiếu .env vẫn chạy tiếp được.
    """
    for thu_muc in Path(__file__).resolve().parents:
        f = thu_muc / ".env"
        if f.exists():
            for dong in f.read_text(encoding="utf-8").splitlines():
                dong = dong.strip()
                if dong and not dong.startswith("#") and "=" in dong:
                    k, v = dong.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            return f
    if bat_buoc:
        sys.exit(
            "Không tìm thấy file .env.\n"
            "Hãy chạy lệnh từ trong thư mục dự án kome-data, ví dụ:\n"
            "    cd C:\\Antigravity\\kome-data"
        )
    return None
