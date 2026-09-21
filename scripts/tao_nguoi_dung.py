"""Tạo, sửa và liệt kê tài khoản đăng nhập của trang nội bộ.

Chạy (từ thư mục dự án, cả PowerShell lẫn Git Bash đều được):
    python scripts/tao_nguoi_dung.py                        liệt kê tài khoản
    python scripts/tao_nguoi_dung.py them an --sale 0104
    python scripts/tao_nguoi_dung.py them minh --kho-du-lieu
    python scripts/tao_nguoi_dung.py doi-mat-khau an
    python scripts/tao_nguoi_dung.py quyen an --kho-du-lieu
    python scripts/tao_nguoi_dung.py quyen an --bo-kho-du-lieu
    (thêm --test ở cuối để chạy trên CSDL thử nghiệm)

Script tự đọc .env, không cần nạp biến môi trường trước. Nó nối bằng
`DATABASE_URL_APP` (vai trò `kome_app` — vai trò DUY NHẤT có quyền trên schema
`app`), lùi về `DATABASE_URL` nếu biến đó còn trống.

MẬT KHẨU LUÔN NHẬP QUA BÀN PHÍM, không bao giờ nhận qua tham số dòng lệnh:
tham số nằm lại trong lịch sử shell và trong danh sách tiến trình, nơi ai
đăng nhập cùng máy cũng đọc được.

Vì sao là script chứ không phải một màn hình trong web app: 5–7 tài khoản đặt
một lần thì một màn hình là nhiều việc hơn để dựng, để bảo trì và để làm hỏng.
Dựng màn hình khi số tài khoản đủ nhiều để việc sửa tay thành phiền.

--kho-du-lieu là quyền vào màn Kho dữ liệu: nạp file VÀ hoàn tác một lần nạp.
Hoàn tác nhầm lô đối soát tháng sẽ xoá cả một tháng doanh thu khỏi kho. Chỉ
cấp cho người phụ trách nạp và chủ doanh nghiệp.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import psycopg

from kome.web import nguoi_dung as ND

DAI_TOI_THIEU = 12

HUONG_DAN = """    python scripts/tao_nguoi_dung.py                        liệt kê tài khoản
    python scripts/tao_nguoi_dung.py them <tên> [--sale <mã>] [--kho-du-lieu]
    python scripts/tao_nguoi_dung.py doi-mat-khau <tên>
    python scripts/tao_nguoi_dung.py quyen <tên> --kho-du-lieu | --bo-kho-du-lieu
    (thêm --test ở cuối để chạy trên CSDL thử nghiệm)"""


def _hoi_mat_khau(doc_mat_khau) -> str | None:
    """Hỏi hai lần. None nếu lệch nhau hoặc quá ngắn."""
    a = doc_mat_khau()
    b = doc_mat_khau()
    if a != b:
        print("Hai lần gõ không khớp nhau. Chưa đổi gì cả.")
        return None
    if len(a) < DAI_TOI_THIEU:
        print(f"Mật khẩu chỉ dài {len(a)} ký tự — phải từ {DAI_TOI_THIEU} trở lên.")
        return None
    return a


def liet_ke(conn) -> int:
    ds = ND.liet_ke(conn)
    if not ds:
        print("Chưa có tài khoản nào. Tạo bằng:  python scripts/tao_nguoi_dung.py them <tên>")
        return 0
    print(f"{'Tên đăng nhập':<20}{'Mã sale':<10}{'Phụ trách':<24}Kho dữ liệu")
    print("-" * 70)
    for n in ds:
        print(f"{n.ten_dang_nhap:<20}{n.salesperson_code or '—':<10}"
              f"{n.ten_sale or '—':<24}{'CÓ' if n.duoc_vao_kho_du_lieu else '—'}")
    print("\nKho dữ liệu = được nạp file VÀ hoàn tác lần nạp (xoá dữ liệu khỏi kho).")
    return 0


def them(conn, ten: str, sale: str | None, kho_du_lieu: bool, doc_mat_khau) -> int:
    mk = _hoi_mat_khau(doc_mat_khau)
    if mk is None:
        return 1
    try:
        ND.tao(conn, ten, mk, salesperson_code=sale, kho_du_lieu=kho_du_lieu)
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        print(f"Đã có tài khoản tên '{ten}'. Đổi mật khẩu bằng:  "
              f"python scripts/tao_nguoi_dung.py doi-mat-khau {ten}")
        return 1
    except psycopg.errors.ForeignKeyViolation:
        conn.rollback()
        print(f"Không có người phụ trách mã '{sale}' trong OBC. "
              f"Chạy không tham số để xem các mã đang dùng, hoặc bỏ --sale nếu "
              f"người này không phụ trách khách nào.")
        return 1
    conn.commit()
    print(f"Đã tạo '{ten}'"
          + (f", phụ trách mã {sale}" if sale else ", không phụ trách khách nào")
          + (", CÓ quyền vào Kho dữ liệu." if kho_du_lieu
             else ", không có quyền vào Kho dữ liệu."))
    return 0


def doi_mat_khau(conn, ten: str, doc_mat_khau) -> int:
    mk = _hoi_mat_khau(doc_mat_khau)
    if mk is None:
        return 1
    if not ND.doi_mat_khau(conn, ten, mk):
        print(f"Không có tài khoản tên '{ten}'. Chạy không tham số để xem danh sách.")
        return 1
    conn.commit()
    print(f"Đã đổi mật khẩu cho '{ten}'. Lần đăng nhập sau của họ dùng mật khẩu mới;\n"
          f"phiên đang mở của họ vẫn chạy tới khi hết hạn (12 giờ).\n"
          f"Cần cắt NGAY thì xoá tài khoản, hoặc đổi KOME_SESSION_SECRET "
          f"(đăng xuất tất cả mọi người).")
    return 0


def quyen(conn, ten: str, kho_du_lieu: bool) -> int:
    if not ND.dat_quyen(conn, ten, kho_du_lieu):
        print(f"Không có tài khoản tên '{ten}'. Chạy không tham số để xem danh sách.")
        return 1
    conn.commit()
    print(f"'{ten}' " + ("GIỜ vào được" if kho_du_lieu else "KHÔNG còn vào được")
          + " màn Kho dữ liệu. Có hiệu lực ngay ở lượt bấm kế tiếp của họ.")
    return 0


def chay(argv: list[str], conn, doc_mat_khau=None) -> int:
    """Mã thoát 0 = xong, khác 0 = có lỗi. `doc_mat_khau` tách ra để test
    được mà không phải vá getpass toàn cục."""
    doc_mat_khau = doc_mat_khau or (lambda: getpass.getpass("Mật khẩu: "))
    argv = [a for a in argv if a != "--test"]
    if not argv:
        return liet_ke(conn)

    lenh, *phan_con_lai = argv
    # ten lấy phần tử KHÔNG bắt đầu bằng "--", nên nếu mã sale vô tình đứng
    # trước tên (ví dụ "them --sale 0104 an") thì "0104" bị chọn làm ten thay
    # vì là chuỗi không "--" đầu tiên — script vẫn chạy, chỉ tạo nhầm tài
    # khoản tên "0104". Chấp nhận được cho một script chạy tay: hậu quả tự
    # bộc lộ ngay ở dòng "Đã tạo '0104'" in ra, người gõ thấy sai liền.
    ten = next((a for a in phan_con_lai if not a.startswith("--")), None)
    kho = "--kho-du-lieu" in phan_con_lai
    bo_kho = "--bo-kho-du-lieu" in phan_con_lai
    sale = None
    sale_thieu_gia_tri = False
    if "--sale" in phan_con_lai:
        i = phan_con_lai.index("--sale")
        if i + 1 < len(phan_con_lai):
            sale = phan_con_lai[i + 1]
        else:
            sale_thieu_gia_tri = True

    if lenh not in ("them", "doi-mat-khau", "quyen") or not ten:
        print(f"Không hiểu lệnh. Cách dùng:\n{HUONG_DAN}")
        return 2
    if sale_thieu_gia_tri:
        print("Thiếu mã sale sau --sale. Ví dụ:  "
              f"python scripts/tao_nguoi_dung.py them {ten} --sale 0104")
        return 2
    if lenh == "them":
        return them(conn, ten, sale, kho, doc_mat_khau)
    if lenh == "doi-mat-khau":
        return doi_mat_khau(conn, ten, doc_mat_khau)
    if kho and bo_kho:
        # Hai cờ trái nhau: cấp và bỏ quyền cùng lúc là dấu hiệu người gõ
        # không chắc mình muốn gì. Không được im lặng chọn nhánh cấp quyền —
        # đó là nhánh nguy hiểm hơn, mở đường vào nút Hoàn tác (xoá dữ liệu).
        print("Vừa --kho-du-lieu vừa --bo-kho-du-lieu — chỉ chọn một.")
        return 2
    if not kho and not bo_kho:
        print("Lệnh quyền cần --kho-du-lieu hoặc --bo-kho-du-lieu.")
        return 2
    return quyen(conn, ten, kho)


if __name__ == "__main__":
    import os
    from kome.db import connect
    from kome.env import nap_env

    nap_env()
    # Nối bằng DATABASE_URL_APP (vai trò `kome_app`), KHÔNG phải DATABASE_URL.
    # Bảng app.nguoi_dung nằm trong schema `app`, mà `kome_ingest` — vai trò
    # mà docs/runbook.md dạy đặt vào DATABASE_URL cho việc nạp dữ liệu hằng
    # ngày — không có cả USAGE trên schema đó. Đọc thẳng DATABASE_URL thì ngay
    # khi chủ sở hữu làm đúng theo runbook, MỌI lệnh của script (kể cả liệt kê)
    # chết bằng "permission denied for schema app" — tức không tạo nổi tài
    # khoản, không ai đăng nhập được, không ai nạp được dữ liệu lúc 13:30, và
    # không có luồng tự phục hồi nào. Có test canh:
    # tests/test_roles.py::test_app_lam_duoc_viec_cua_script_tai_khoan.
    #
    # Lùi về DATABASE_URL khi DATABASE_URL_APP còn trống: máy chưa tách hai
    # chuỗi kết nối (hoặc còn dùng `postgres`) vẫn chạy script được như cũ.
    if "--test" in sys.argv:
        url = os.environ["DATABASE_URL_TEST"]
    else:
        url = os.environ.get("DATABASE_URL_APP") or os.environ["DATABASE_URL"]
    with connect(url) as c:
        sys.exit(chay(sys.argv[1:], c))
