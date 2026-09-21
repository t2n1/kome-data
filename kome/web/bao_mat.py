"""Cổng đăng nhập: vé không trạng thái, ký bằng khoá của hệ thống.

Mỗi người một tài khoản riêng (app.nguoi_dung, migration 019) — trước đợt 3
cả công ty dùng chung một mật khẩu `KOME_MAT_KHAU`, và hệ quả là không ai
biết ai vừa bấm nút Hoàn tác, còn một người nghỉ việc thì phải đổi mật khẩu
của tất cả mọi người.

Vé đăng nhập là cookie tự chứng thực: `<id>.<hạn>.<chữ ký HMAC-SHA256>`.
Không có kho phiên ở máy chủ — điều kiện bắt buộc để chạy được trên Vercel,
nơi mỗi lần gọi có thể rơi vào một tiến trình khác và bộ nhớ không dùng chung.

Việc "mật khẩu này có đúng không" nằm ở kome/web/nguoi_dung.py. File này chỉ
giữ "cái cookie này có phải do mình ký không".
"""
import hashlib
import hmac
import os
import time

TEN_COOKIE = "kome_phien"
HAN_PHIEN_GIAY = 12 * 3600      # một ngày làm việc, không hơn
DAI_TOI_THIEU = 12


class CauHinhSai(RuntimeError):
    """Cấu hình bảo mật sai — app phải CHẾT NGAY, không phục vụ dòng nào.

    Chết lúc khởi động thì người triển khai thấy ngay trong nhật ký Vercel.
    Phục vụ tiếp trong khi không có mật khẩu thì không ai thấy gì cả, cho tới
    ngày số liệu công ty xuất hiện ở nơi không nên có.
    """


def tren_mang() -> bool:
    """Có đang chạy trên hạ tầng công khai không?

    Vercel luôn tự đặt biến `VERCEL` trong mọi môi trường chạy của nó. Ràng
    buộc này cố ý KHÔNG đọc từ cấu hình người dùng đặt tay: một trang công
    khai không có mật khẩu là hỏng, và không nên có cái công tắc nào để lỡ
    tay bật ra tình trạng đó.
    """
    return bool(os.environ.get("VERCEL"))


def duong_dan_an_toan(tiep: str | None) -> str:
    """Lọc tham số `?tiep=` trước khi chuyển hướng sau khi đăng nhập.

    Không lọc thì trang đăng nhập của công ty trở thành bàn đạp chuyển hướng
    sang site giả mạo: `/dang-nhap?tiep=https://site-gia.example` — nạn nhân
    thấy địa chỉ KOME quen thuộc, bấm vào, rồi bị đẩy đi nơi khác.
    `//site-gia.example` cũng là địa chỉ tuyệt đối, nên phải chặn cả nó.

    Đích mặc định là trang chủ chứ không phải /kho-du-lieu: từ đợt 3 không
    phải ai cũng vào được màn đó.
    """
    if tiep and tiep.startswith("/") and not tiep.startswith("//"):
        return tiep
    return "/"


# ---- Vé theo từng người (đợt 3) ---------------------------------------
# Cơ chế cũ (đã xoá ở đợt 3) suy khoá ký TỪ CHÍNH mật khẩu chung, nên đổi mật
# khẩu là mọi vé chết ngay. Cách đó không dùng được khi có nhiều tài khoản:
# đổi mật khẩu MỘT người không được phép làm bốn người còn lại bị đăng xuất.
#
# Khoá ký giờ là của HỆ THỐNG (KOME_SESSION_SECRET), không phải mật khẩu của
# ai cả. Thu hồi quyền vì thế tách làm hai mức:
#   * đổi KOME_SESSION_SECRET -> đăng xuất TẤT CẢ (dùng khi nghi rò rỉ)
#   * đổi mật khẩu một người  -> chỉ họ, ở lượt đăng nhập kế tiếp
# Vé đang có hiệu lực của người bị đổi mật khẩu sống tới hết hạn (12 giờ).
# Vô hiệu hoá tức thì cần kho phiên, mà kho phiên phá luật Vercel.
#
# Riêng quyền vào Kho dữ liệu KHÔNG nằm trong vé mà tra CSDL mỗi lượt gọi —
# xem kome/web/app.py. Đó là màn có nút xoá, thu hồi phải ăn ngay.


def bi_mat_phien() -> str | None:
    """Khoá ký vé, hoặc None nếu không đặt (máy trong công ty, không có cổng)."""
    return os.environ.get("KOME_SESSION_SECRET", "").strip() or None


def kiem_cau_hinh_phien(bi_mat: str | None, cong_khai: bool) -> None:
    """Gọi lúc dựng app. Ném CauHinhSai nếu cấu hình không an toàn.

    Cùng hình dạng với chốt an toàn của cơ chế mật khẩu chung mà nó thay thế
    (đã xoá ở đợt 3): một bản chạy công khai KHÔNG CÓ CỔNG NÀO là hỏng theo
    cách tệ nhất, nên phải chết lúc khởi động, nơi người triển khai đọc được
    nhật ký Vercel.

    CỐ Ý không kiểm "đã có tài khoản nào trong CSDL chưa": làm vậy là buộc
    việc dựng app phụ thuộc CSDL, và một CSDL chậm sẽ thành app không khởi
    động được.
    """
    if bi_mat is None:
        if cong_khai:
            raise CauHinhSai(
                "Trang đang chạy trên hạ tầng công khai nhưng chưa đặt biến môi "
                "trường KOME_SESSION_SECRET.\n"
                "Vào Vercel → Settings → Environment Variables, thêm "
                "KOME_SESSION_SECRET là một chuỗi ngẫu nhiên dài ít nhất "
                f"{DAI_TOI_THIEU} ký tự, rồi triển khai lại."
            )
        return
    if len(bi_mat) < DAI_TOI_THIEU:
        raise CauHinhSai(
            f"KOME_SESSION_SECRET chỉ dài {len(bi_mat)} ký tự — phải từ "
            f"{DAI_TOI_THIEU} trở lên.\n"
            "Đây là khoá ký vé đăng nhập: đoán ra nó là tự ký được vé cho bất "
            "kỳ tài khoản nào, không cần biết mật khẩu của ai."
        )


def _ky(noi_dung: str, bi_mat: str) -> str:
    return hmac.new(bi_mat.encode("utf-8"), noi_dung.encode("utf-8"),
                    hashlib.sha256).hexdigest()


def tao_ve_cho(id_nguoi: int, bi_mat: str, bay_gio: float | None = None) -> str:
    """Vé `<id>.<hạn>.<chữ ký>`, hết hạn sau HAN_PHIEN_GIAY."""
    het = int((bay_gio if bay_gio is not None else time.time()) + HAN_PHIEN_GIAY)
    than = f"{id_nguoi}.{het}"
    return f"{than}.{_ky(than, bi_mat)}"


def doc_ve(ve: str | None, bi_mat: str, bay_gio: float | None = None) -> int | None:
    """id người trong vé, hoặc None nếu vé sai chữ ký / hết hạn / méo mó.

    CHỮ KÝ PHỦ CẢ id LẪN HẠN. Ký riêng phần hạn thôi thì sửa một con số trong
    cookie là hoá thân thành người khác mà chữ ký vẫn đúng — kể cả thành người
    có quyền bấm nút xoá dữ liệu.

    Giữ nguyên thứ tự "so chữ ký TRƯỚC khi đọc hạn" của cơ chế cũ:
    hmac.compare_digest chạy hết thời gian như nhau dù sai ở ký tự nào, nên
    không đo được chữ ký đúng là gì.

    So trên BYTES (encode trước khi đưa vào compare_digest), không so thẳng
    str: cookie là dữ liệu trình duyệt gửi lên, ai cũng nhét được ký tự ngoài
    ASCII vào; compare_digest ném TypeError với hai str như vậy, và vé "méo
    mó" khi đó không trả None như docstring hứa mà làm sập cả lượt gọi.
    """
    if not ve:
        return None
    phan = ve.split(".")
    if len(phan) != 3:
        return None
    ma, het, chu_ky = phan
    if not hmac.compare_digest(chu_ky.encode("utf-8"),
                               _ky(f"{ma}.{het}", bi_mat).encode("utf-8")):
        return None
    try:
        if (bay_gio if bay_gio is not None else time.time()) >= int(het):
            return None
        return int(ma)
    except ValueError:
        return None
