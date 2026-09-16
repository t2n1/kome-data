"""Kiểm cơ sở dữ liệu TRƯỚC khi chạy migration 010 trở đi.

Migration `010` thêm ràng buộc `CHECK (valid_to IS NULL OR valid_to >= valid_from)`
cho `core.dim_customer`. Ràng buộc được kiểm với dữ liệu ĐANG CÓ, nên nếu kho đã
lỡ chứa dòng vi phạm — do lỗi cũ: xuất lại trong cùng ngày thì phiên bản cũ bị
đóng bằng "ngày hôm trước", thành khoảng thời gian âm — thì migration sẽ báo lỗi
và **dừng giữa chừng**, các file sau không chạy.

Chạy (từ thư mục dự án, cả PowerShell lẫn Git Bash):
    python scripts/kiem_truoc_migration.py           # chỉ kiểm, không sửa gì
    python scripts/kiem_truoc_migration.py --don     # dọn các dòng chết
    python scripts/kiem_truoc_migration.py --test    # trên CSDL thử nghiệm

Script tự đọc .env, không cần nạp biến môi trường trước.
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from kome.db import connect
from kome.env import nap_env

TRUY_VAN = """
SELECT d.customer_sk, d.customer_code, d.valid_from, d.valid_to,
       EXISTS (SELECT 1 FROM core.dim_customer x
               WHERE x.customer_code = d.customer_code
                 AND x.customer_sk <> d.customer_sk
                 AND x.valid_from >= d.valid_from) AS co_ban_thay_the
FROM core.dim_customer d
WHERE d.valid_to < d.valid_from
ORDER BY d.customer_code, d.valid_from
"""


def main(url: str, don: bool) -> int:
    with connect(url) as c:
        co_bang = c.execute(
            """SELECT count(*) FROM information_schema.tables
               WHERE table_schema='core' AND table_name='dim_customer'"""
        ).fetchone()[0]
        if not co_bang:
            print("Kho chưa có bảng dim_customer — cứ chạy migration bình thường.")
            return 0

        rows = c.execute(TRUY_VAN).fetchall()
        if not rows:
            print("KHÔNG có dòng nào vi phạm. Chạy migration được bình thường.")
            return 0

        print(f"CÓ {len(rows)} dòng vi phạm — KHOAN chạy migration.\n")
        print(f"{'sk':>7}  {'Mã khách':<14}{'Từ':<12}{'Đến':<12}  Đã có bản thay thế?")
        print("-" * 70)
        for sk, ma, tu, den, thay in rows:
            print(f"{sk:>7}  {ma:<14}{str(tu):<12}{str(den):<12}  {'CÓ' if thay else 'KHÔNG'}")

        chua_thay = [r for r in rows if not r[4]]
        if chua_thay:
            print(f"\nDỪNG LẠI: {len(chua_thay)} dòng KHÔNG có bản thay thế.")
            print("Đó là phiên bản duy nhất của khách đó — không được xoá.")
            print("Chụp màn hình này gửi người phụ trách kỹ thuật.")
            return 2

        if not don:
            print("\nMọi dòng vi phạm đều đã có bản thay thế, nên xoá đi không mất")
            print("thông tin nào đang dùng được (chúng không có ngày nào đọc ra được).")
            print("\nSAO LƯU TRƯỚC:   python -m ops.backup")
            print("Rồi dọn:         python scripts/kiem_truoc_migration.py --don")
            return 1

        n = c.execute(
            """DELETE FROM core.dim_customer d
               WHERE d.valid_to < d.valid_from
                 AND EXISTS (SELECT 1 FROM core.dim_customer x
                             WHERE x.customer_code = d.customer_code
                               AND x.customer_sk <> d.customer_sk
                               AND x.valid_from >= d.valid_from)"""
        ).rowcount
        c.commit()
        print(f"\nĐã dọn {n} dòng chết. Chạy lại lệnh này để xác nhận, rồi chạy migration.")
        return 0


if __name__ == "__main__":
    nap_env()
    url = os.environ["DATABASE_URL_TEST" if "--test" in sys.argv else "DATABASE_URL"]
    sys.exit(main(url, don="--don" in sys.argv))
