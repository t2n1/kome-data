import os
import psycopg

# Cổng 6543 của Supabase là "transaction pooler": mỗi giao dịch có thể rơi vào
# một kết nối máy chủ KHÁC. Đó chính là thứ cần cho bản chạy trên Vercel —
# mỗi lần gọi là một tiến trình mới, mở rồi đóng kết nối liên tục — nhưng nó
# phá vỡ câu lệnh chuẩn bị sẵn (prepared statement).
CONG_POOLER_GIAO_DICH = ":6543"


def connect(url: str | None = None) -> psycopg.Connection:
    """Mở kết nối Postgres. Mật khẩu chỉ đến từ biến môi trường.

    psycopg 3 tự chuẩn bị sẵn một câu lệnh sau vài lần chạy giống nhau để đi
    nhanh hơn. Qua pooler giao dịch, câu lệnh được chuẩn bị trên một kết nối
    máy chủ rồi lần sau lại gọi trên kết nối khác → `prepared statement "_pg3_0"
    does not exist`, hoặc `already exists`. Lỗi này KHÔNG xuất hiện ngay: phải
    đủ số lần chạy lặp mới nổ, nên nó sẽ nổ khi trang đã chạy được một thời
    gian và có người đang xem. Tắt hẳn khi thấy cổng 6543.

    Cổng 5432 (session pooler, dùng ở máy trong công ty) giữ nguyên một kết
    nối máy chủ suốt phiên nên không dính, và cần giữ câu lệnh chuẩn bị sẵn
    để nạp dữ liệu cho nhanh.
    """
    url = url or os.environ["DATABASE_URL"]
    if CONG_POOLER_GIAO_DICH in url:
        return psycopg.connect(url, prepare_threshold=None)
    return psycopg.connect(url)
