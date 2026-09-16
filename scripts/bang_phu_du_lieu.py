"""Bảng phủ dữ liệu: tháng nào có, tháng nào thiếu, theo từng loại file.

Đọc thẳng từ kho dữ liệu chứ không đếm tên file — vì file xuất theo quý chứa 3 tháng,
nên đếm file không cho biết tháng nào thiếu.

Chạy (từ thư mục dự án, chạy được ở cả PowerShell lẫn Git Bash):
    python scripts/bang_phu_du_lieu.py            # CSDL thật
    python scripts/bang_phu_du_lieu.py --test     # CSDL thử nghiệm

Script tự đọc file .env, không cần nạp biến môi trường trước.

Ký hiệu:
    ●  có dữ liệu trong kho
    ·  không có dữ liệu
    số  số ngày có ảnh chụp trong tháng (chỉ cột tồn kho)
    —  ngoài phạm vi dữ liệu (trước 2025-03 công ty không còn lưu)

LƯU Ý: dấu `·` KHÔNG phân biệt được hai trường hợp —
  (a) chưa bao giờ xuất file cho tháng đó, và
  (b) đã xuất nhưng file bị cổng kiểm tra chặn (ví dụ bản xuất thiếu, sai mẫu).
Lý do: cổng kiểm tra chặn TRƯỚC khi ghi nhật ký nạp, nên kho không hề biết
file đó từng tồn tại. Muốn biết chắc thì đối chiếu với thư mục xuất của OBC.
"""
import os
import sys
from datetime import date
from pathlib import Path

import psycopg


def nap_env() -> None:
    """Đọc .env ở thư mục dự án. Để chạy được mà không cần nạp biến môi trường trước.

    Tìm ngược lên từ vị trí script, nên chạy từ thư mục con cũng được.
    """
    for thu_muc in [Path(__file__).resolve().parent, *Path(__file__).resolve().parents]:
        f = thu_muc / ".env"
        if f.exists():
            for dong in f.read_text(encoding="utf-8").splitlines():
                dong = dong.strip()
                if dong and not dong.startswith("#") and "=" in dong:
                    k, v = dong.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())
            return
    sys.exit("Không tìm thấy file .env — hãy chạy từ trong thư mục dự án kome-data.")

# Kỳ kế toán công ty: 1/8 → 31/7. Dữ liệu bán bắt đầu 2025-03-03 (xem đặc tả §2.2.1).
DAU_DU_LIEU = date(2025, 3, 1)


def ky_ke_toan(d: date) -> int:
    """Năm KẾT THÚC kỳ. 2026 = kỳ 1/8/2025 → 31/7/2026."""
    return d.year + 1 if d.month >= 8 else d.year


def thang_trong_khoang(dau: date, cuoi: date) -> list[str]:
    out, y, m = [], dau.year, dau.month
    while (y, m) <= (cuoi.year, cuoi.month):
        out.append(f"{y}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def main(url: str) -> int:
    with psycopg.connect(url) as c:
        db = c.execute("SELECT current_database()").fetchone()[0]

        ban = dict(c.execute("""
            SELECT to_char(sales_date,'YYYY-MM'), count(*)
            FROM core.fact_sales_line GROUP BY 1""").fetchall())
        ton = dict(c.execute("""
            SELECT to_char(snapshot_date,'YYYY-MM'), count(DISTINCT snapshot_date)
            FROM core.fact_inventory_daily GROUP BY 1""").fetchall())

        # Master: lấy ngày từ TÊN FILE trong nhật ký nạp (file đặt tên _YYYYMMDD)
        master = {}
        for spec, src in c.execute("""
                SELECT spec_name, source_file FROM meta.ingest_batch
                WHERE undone_at IS NULL""").fetchall():
            import re
            m = re.search(r"_(\d{4})(\d{2})\d{2}\.xlsx$", src)
            if m and spec not in ("zaiko", "uriage"):
                master.setdefault(spec, set()).add(f"{m.group(1)}-{m.group(2)}")

        chan = {}
        for spec, src in c.execute("""
                SELECT spec_name, source_file FROM meta.ingest_batch
                WHERE undone_at IS NOT NULL""").fetchall():
            pass  # lô đã huỷ, không tính là có dữ liệu

    # Nhãn cột dùng chữ Latin ngắn: ký tự tiếng Nhật rộng gấp đôi nên cột sẽ lệch
    # trong terminal. Tên đầy đủ in ở phần chú giải bên dưới bảng.
    cot = [
        ("Ban", "ban", "売上伝票データ — bán hàng"),
        ("Ton", "ton", "在庫一覧 — tồn kho, ô hiện SỐ NGÀY có ảnh chụp"),
        ("Khach", "tokuisaki", "得意先全情報 — khách hàng"),
        ("SP", "shohin", "商品データ — sản phẩm"),
        ("NCC", "shiiresaki", "仕入先 — nhà cung cấp"),
        ("Giao", "chokusousaki", "直送先 — điểm giao thẳng"),
        ("Gia", "tanka", "取引単価データ — bảng giá"),
    ]
    thieu_bo_nap = [
        ("入金伝票データ", "phiếu thu", "1 quý (2026-05→07), chưa có bộ nạp"),
        ("得意先元帳", "sổ cái khách", "1 quý, chưa có bộ nạp"),
        ("請求先元帳", "sổ cái bên trả", "1 quý, chưa có bộ nạp"),
        ("他勘定振替明細", "xuất khác / hàng hỏng", "1 quý, chưa có bộ nạp"),
        ("仕入データ", "MUA HÀNG", "KHÔNG CÓ — lỗ hổng lớn nhất"),
        ("受注データ", "đơn đặt", "KHÔNG CÓ"),
    ]

    hom_nay = date.today()
    thang = thang_trong_khoang(date(2024, 8, 1), hom_nay)

    print(f"BẢNG PHỦ DỮ LIỆU — database: {db}\n")
    print("  ● có dữ liệu   · không có   — ngoài phạm vi (công ty không còn lưu)")
    print("  Cột tồn kho hiện SỐ NGÀY có ảnh chụp trong tháng\n")

    head = f"{'Thang':<9}{'Ky':>4}  " + "".join(f"{c[0]:<7}" for c in cot)
    print(head)
    print("-" * len(head))

    for t in thang:
        y, m = int(t[:4]), int(t[5:])
        ngoai = date(y, m, 1) < DAU_DU_LIEU
        row = f"{t:<9}{ky_ke_toan(date(y, m, 1)):>4}  "
        for nhan, khoa, _ in cot:
            if khoa == "ban":
                v = "●" if ban.get(t) else ("—" if ngoai else "·")
            elif khoa == "ton":
                v = str(ton[t]) if ton.get(t) else "·"
            else:
                v = "●" if t in master.get(khoa, set()) else "·"
            row += f"{v:<7}"
        print(row)

    print("\nChu giai cot:")
    for nhan, _, mo_ta in cot:
        print(f"  {nhan:<7} {mo_ta}")

    print("\nLoai du lieu CHUA vao kho:")
    for ja, vi, ghi in thieu_bo_nap:
        print(f"  {ja}  ({vi}) — {ghi}")
    return 0


if __name__ == "__main__":
    nap_env()
    key = "DATABASE_URL_TEST" if "--test" in sys.argv else "DATABASE_URL"
    sys.exit(main(os.environ[key]))
