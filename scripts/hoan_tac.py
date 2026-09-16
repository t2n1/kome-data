"""Xem các lần nạp gần đây và hoàn tác một lần nạp sai.

Chạy (từ thư mục dự án, cả PowerShell lẫn Git Bash đều được):
    python scripts/hoan_tac.py                 # liệt kê 10 lần nạp gần nhất
    python scripts/hoan_tac.py 123             # hoàn tác lô số 123
    python scripts/hoan_tac.py 123 --test      # trên CSDL thử nghiệm

Script tự đọc .env, không cần nạp biến môi trường trước.

Hoàn tác KHÔNG xoá dòng trong nhật ký — chỉ đánh dấu lô đã huỷ và dọn dữ liệu
của lô đó khỏi kho. Sau khi hoàn tác, nạp lại đúng file ấy được bình thường.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kome.db import connect
from kome.env import nap_env
from kome.pipeline import undo_batch


def liet_ke(url: str) -> None:
    with connect(url) as c:
        rows = c.execute(
            """SELECT batch_id, spec_name, source_file, row_count, total_amount, loaded_at
               FROM meta.ingest_batch WHERE undone_at IS NULL
               ORDER BY loaded_at DESC LIMIT 10"""
        ).fetchall()
    if not rows:
        print("Chưa có lần nạp nào.")
        return
    print(f"{'Lô':>5}  {'Loại':<14}{'Lúc':<18}{'Số dòng':>9}{'Tổng tiền':>16}  File")
    print("-" * 100)
    for bid, spec, src, n, tien, luc in rows:
        print(f"{bid:>5}  {spec:<14}{luc:%Y-%m-%d %H:%M}  {n:>9,}{tien:>16,}  {src}")
    print("\nMuốn hoàn tác lô nào thì chạy:  python scripts/hoan_tac.py <số lô>")


def hoan_tac(url: str, batch_id: int) -> None:
    with connect(url) as c:
        row = c.execute(
            """SELECT spec_name, source_file, row_count, undone_at
               FROM meta.ingest_batch WHERE batch_id = %s""",
            (batch_id,),
        ).fetchone()
        if row is None:
            sys.exit(f"Không có lô số {batch_id}. Chạy không tham số để xem danh sách.")
        spec, src, n, da_huy = row
        if da_huy:
            sys.exit(f"Lô {batch_id} ({src}) đã được hoàn tác lúc {da_huy:%Y-%m-%d %H:%M}.")
        print(f"Sắp hoàn tác lô {batch_id}: {spec} · {src} · {n:,} dòng")
        da_xoa = undo_batch(c, batch_id)
        c.commit()
    print(f"Đã hoàn tác. Dọn {da_xoa:,} dòng khỏi kho.")
    print("Nạp lại đúng file đó qua trang nội bộ được bình thường.")


if __name__ == "__main__":
    nap_env()
    url = os.environ["DATABASE_URL_TEST" if "--test" in sys.argv else "DATABASE_URL"]
    so = [a for a in sys.argv[1:] if a.isdigit()]
    hoan_tac(url, int(so[0])) if so else liet_ke(url)
