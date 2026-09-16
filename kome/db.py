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
    nhanh hơn, đặt cho nó cái tên `_pg3_0`. Qua pooler giao dịch, kết nối sau
    có thể rơi vào đúng kết nối máy chủ mà kết nối trước đã đặt tên đó →
    `prepared statement "_pg3_0" already exists`.

    ĐÃ ĐO THẬT trên chính CSDL này (2026-09-16), và kết quả quan trọng hơn cái
    lỗi: **giữ MỘT kết nối rồi chạy lặp 12 lần thì KHÔNG hề lỗi**; mở 20 kết
    nối ngắn nối tiếp nhau thì **hỏng ngay ở kết nối thứ nhất**. Nghĩa là thử
    ở máy mình kiểu nào cũng thấy êm, còn trên Vercel — nơi mỗi lượt xem là
    một kết nối ngắn — thì hỏng ngay từ lượt thứ hai. Đây đúng là loại lỗi
    chỉ lộ ra sau khi đã triển khai xong.

    Cổng 5432 (session pooler, dùng ở máy trong công ty) giữ nguyên một kết
    nối máy chủ suốt phiên nên không dính, và cần giữ câu lệnh chuẩn bị sẵn
    để nạp dữ liệu cho nhanh.
    """
    url = url or os.environ["DATABASE_URL"]
    if CONG_POOLER_GIAO_DICH in url:
        return psycopg.connect(url, prepare_threshold=None)
    return psycopg.connect(url)
