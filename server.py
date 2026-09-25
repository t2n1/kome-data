"""Điểm vào cho Vercel. Toàn bộ ứng dụng nằm ở kome/web/app.py.

Vercel nhận diện FastAPI qua `requirements.txt`, rồi tìm một biến tên `app`
trong một file ở gốc dự án có tên thuộc danh sách nó chấp nhận — `server.py`
là một trong số đó. Không cần `vercel.json`: Vercel tự định tuyến MỌI đường
dẫn về ứng dụng này.

ĐỪNG đổi tên file này, và đừng đổi tên biến `app`. Đổi là Vercel không tìm
thấy ứng dụng nữa, và triệu chứng là trang trả về 404 ở mọi đường dẫn — trông
giống hệt như code bị hỏng, chứ không giống một file bị đổi tên.

Bản chạy trên Vercel LUÔN đòi mật khẩu (kome/web/bao_mat.py) — do biến môi trường
`VERCEL` quyết định chứ không phải file này, nên không thể lỡ tay tắt đi. Từ
migration 045 nó nạp được file hằng ngày (≤ 4 MB); đặt `KOME_CHI_DOC=1` nếu muốn
một bản chỉ để xem.
"""
from kome.web.app import app

__all__ = ["app"]
