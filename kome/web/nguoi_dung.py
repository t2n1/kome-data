"""Tài khoản đăng nhập: băm mật khẩu, xác thực, và quyền vào Kho dữ liệu.

Module này KHÔNG biết gì về HTTP — không FastAPI, không cookie, không vé.
Nó chỉ nói chuyện với `app.nguoi_dung` (migration 019). Vé đăng nhập nằm ở
kome/web/bao_mat.py, và ranh giới đó là cố ý: một chỗ giữ "mật khẩu này có
đúng không", một chỗ giữ "cái cookie này có phải do mình ký không".

Băm bằng `hashlib.scrypt` của THƯ VIỆN CHUẨN — không thêm gói nào (R2: công
ty không có nhân sự IT, mỗi gói phụ thuộc là một thứ nữa có thể hỏng khi cài
lại). scrypt cố ý chậm và tốn bộ nhớ: đo trên chính máy này là ~50 ms một lần
băm, tức một người đăng nhập không thấy chậm, còn ai lấy được bản sao CSDL thì
dò mật khẩu chậm hơn hàng triệu lần so với SHA-256 trần.

Không tự commit: người gọi quyết định ranh giới giao dịch.
"""
import hashlib
import hmac
import os
from dataclasses import dataclass

# Tham số scrypt. n=2^14, r=8, p=1 tốn ~16 MB bộ nhớ mỗi lần băm — nằm gọn
# trong giới hạn mặc định của OpenSSL, đã chạy thật trên máy này.
# ĐỔI BỘ SỐ NÀY LÀ MỌI MẬT KHẨU CŨ HẾT XÁC THỰC ĐƯỢC. Muốn đổi thì phải đặt
# lại mật khẩu cho tất cả mọi người (scripts/tao_nguoi_dung.py doi-mat-khau).
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
DAI_HASH = 32
DAI_SALT = 16

# Truy vấn dùng chung cho kiem_tra/theo_id/liet_ke. LEFT JOIN chứ không JOIN:
# người không phụ trách khách nào (chủ DN, kế toán) có salesperson_code NULL
# và vẫn phải đăng nhập được.
_CHON = f"""SELECT n.id, n.ten_dang_nhap, n.salesperson_code,
                   n.duoc_vao_kho_du_lieu, s.ten
            FROM app.nguoi_dung n
            LEFT JOIN core.dim_salesperson s
                   ON s.salesperson_code = n.salesperson_code"""


@dataclass(frozen=True)
class NguoiDung:
    """Người đang đăng nhập. CỐ Ý không mang hash/salt: cái gì không có trong
    đối tượng thì không có đường nào lọt lên trang hay vào nhật ký."""
    id: int
    ten_dang_nhap: str
    salesperson_code: str | None
    duoc_vao_kho_du_lieu: bool
    ten_sale: str | None


def _nguoi(r) -> NguoiDung:
    return NguoiDung(id=r[0], ten_dang_nhap=r[1], salesperson_code=r[2],
                     duoc_vao_kho_du_lieu=r[3], ten_sale=r[4])


def bam(mat_khau: str, salt: bytes) -> bytes:
    return hashlib.scrypt(mat_khau.encode("utf-8"), salt=salt,
                          n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=DAI_HASH)


def tao(conn, ten: str, mat_khau: str, salesperson_code: str | None = None,
        kho_du_lieu: bool = False) -> int:
    """Tạo tài khoản, trả về id. Ném UniqueViolation nếu tên đã có,
    ForeignKeyViolation nếu mã sale không có trong core.dim_salesperson."""
    salt = os.urandom(DAI_SALT)
    return conn.execute(
        """INSERT INTO app.nguoi_dung
             (ten_dang_nhap, mat_khau_hash, mat_khau_salt, salesperson_code,
              duoc_vao_kho_du_lieu)
           VALUES (%s, %s, %s, %s, %s) RETURNING id""",
        (ten, bam(mat_khau, salt), salt, salesperson_code or None, kho_du_lieu),
    ).fetchone()[0]


def kiem_tra(conn, ten: str, mat_khau: str) -> NguoiDung | None:
    """Tên + mật khẩu có đúng không. None nếu sai bất cứ thứ gì."""
    r = conn.execute(
        "SELECT mat_khau_hash, mat_khau_salt FROM app.nguoi_dung WHERE ten_dang_nhap = %s",
        (ten,)).fetchone()
    if r is None:
        # Vẫn băm một lần với salt vứt đi rồi mới trả None. Trả thẳng None ở
        # đây thì "tên không tồn tại" trả lời trong ~0 ms còn "sai mật khẩu"
        # mất ~50 ms — chênh lệch đó đủ để người ngoài dò ra DANH SÁCH TÊN
        # ĐĂNG NHẬP của công ty mà không cần biết mật khẩu nào.
        bam(mat_khau, b"\x00" * DAI_SALT)
        return None
    if not hmac.compare_digest(bytes(r[0]), bam(mat_khau, bytes(r[1]))):
        return None
    return _nguoi(conn.execute(
        f"{_CHON} WHERE n.ten_dang_nhap = %s", (ten,)).fetchone())


def theo_id(conn, id_nguoi: int) -> NguoiDung | None:
    """Tra người theo id trong vé. None nếu tài khoản đã bị xoá — middleware
    dựa vào đó để một vé còn hạn của người đã xoá không vào được nữa."""
    r = conn.execute(f"{_CHON} WHERE n.id = %s", (id_nguoi,)).fetchone()
    return _nguoi(r) if r else None


def doi_mat_khau(conn, ten: str, mat_khau_moi: str) -> bool:
    """False nếu không có tài khoản tên đó. Salt cũng đổi theo — mật khẩu mới
    thì mọi thứ dẫn tới nó đều mới."""
    salt = os.urandom(DAI_SALT)
    return conn.execute(
        """UPDATE app.nguoi_dung SET mat_khau_hash = %s, mat_khau_salt = %s
           WHERE ten_dang_nhap = %s""",
        (bam(mat_khau_moi, salt), salt, ten)).rowcount == 1


def dat_quyen(conn, ten: str, kho_du_lieu: bool) -> bool:
    """False nếu không có tài khoản tên đó."""
    return conn.execute(
        "UPDATE app.nguoi_dung SET duoc_vao_kho_du_lieu = %s WHERE ten_dang_nhap = %s",
        (kho_du_lieu, ten)).rowcount == 1


def liet_ke(conn) -> list[NguoiDung]:
    return [_nguoi(r) for r in conn.execute(
        f"{_CHON} ORDER BY n.ten_dang_nhap").fetchall()]
