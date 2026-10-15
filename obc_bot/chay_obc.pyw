"""KOME — lấy dữ liệu OBC và nạp lên web. Task Scheduler gọi bằng pythonw.exe (KHÔNG mở cửa sổ đen):
2026-10-15 cửa sổ console của bản .cmd bị đóng lúc 13:30:06 (^C) nên chương trình chết trước khi kịp hiện hộp hỏi."""
import os
import sys

os.chdir(r"C:\KOME\app")
sys.path.insert(0, r"C:\KOME\app")
nhat_ky = open(r"C:\KOME\obc_xuat\log\task.log", "a", encoding="utf-8")
sys.stdout = sys.stderr = nhat_ky
try:
    from datetime import datetime
    print(f"--- {datetime.now():%Y-%m-%d %H:%M:%S} bắt đầu", flush=True)
    from obc_bot.__main__ import main
    ma = main(["chay", "--cau-hinh", r"C:\KOME\may_b.toml"])
    print(f"--- kết thúc, mã {ma}", flush=True)
except BaseException:
    import traceback
    traceback.print_exc()
    ma = 1
finally:
    nhat_ky.flush()
sys.exit(ma)
