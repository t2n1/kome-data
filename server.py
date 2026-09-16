"""Điểm vào cho Vercel. Toàn bộ ứng dụng nằm ở kome/web/app.py.

Vercel nhận diện FastAPI qua `requirements.txt`, rồi tìm một biến tên `app`
trong một file ở gốc dự án có tên thuộc danh sách nó chấp nhận — `server.py`
là một trong số đó. Không cần `vercel.json`: Vercel tự định tuyến MỌI đường
dẫn về ứng dụng này.

ĐỪNG đổi tên file này, và đừng đổi tên biến `app`. Đổi là Vercel không tìm
thấy ứng dụng nữa, và triệu chứng là trang trả về 404 ở mọi đường dẫn — trông
giống hệt như code bị hỏng, chứ không giống một file bị đổi tên.

Bản chạy trên Vercel LUÔN ở chế độ chỉ đọc (kome/web/app.py::_chi_doc) và LUÔN
đòi mật khẩu (kome/web/bao_mat.py). Cả hai do biến môi trường `VERCEL` quyết
định chứ không phải file này, nên không thể lỡ tay tắt đi.
"""
from kome.web.app import app

__all__ = ["app"]
