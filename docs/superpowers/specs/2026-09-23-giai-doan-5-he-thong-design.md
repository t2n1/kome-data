# Giai đoạn 5 — Kho dữ liệu · Nhật ký · Cài đặt · Ngân sách · Đăng nhập (React) — xoá Jinja

Ngày: 2026-09-23 · Đặc tả cha: `2026-09-23-giao-dien-react-design.md` §6 ("hết giai đoạn 5
thì xoá template Jinja"). Gói thiết kế: `Kho dữ liệu.dc.html`, `Nhật ký.dc.html`,
`Cài đặt.dc.html`, `Đăng nhập.dc.html`. `/ngan-sach` không thuộc giai đoạn nào trước đây —
chuyển luôn ở đây, vì nó là trang Jinja cuối cùng.

## 1. Cách chuyển: máy chủ tính sẵn, React vẽ
Các màn này là màn QUẢN TRỊ, ít người mở, và đã có sẵn ngân sách lượt hỏi + cổng quyền được
test canh. Nên route GIỮ NGUYÊN câu truy vấn cũ và chèn kết quả vào `window.__KOME__.man`
(`app.py::_spa(man=…)`, chuyển JSON bằng `_json_man` = `api.thanh_json` + ngày ISO /
Decimal số). Không thêm endpoint `/api` nào → không mở thêm cửa nào phải gác.

| Màn | Dữ liệu | Lượt hỏi |
|---|---|---|
| `/kho-du-lieu` (+ `POST /upload` vẽ lại cùng màn kèm kết quả) | `_du_lieu_kho` (vai trò NẠP) + sao lưu; ô tuổi dữ liệu qua `window.__KOME__.tuoi` — cùng `DaiTuoi` của `/` | như cũ |
| `/kho-du-lieu/luong`, `/cot-noi` | `kome/tai_lieu.py` | 0 |
| `/nhat-ky` | `NK.dong_thoi_gian` + `tong_hop_30_ngay` | 2 |
| `/cai-dat` | `ND.liet_ke` + ngày lễ | 2 |
| `/ngan-sach` | `bang_nhap` (khoá bộ đôi đổi sang tên ô `ma-YYYY-MM`) | như cũ |

## 2. Biểu mẫu vẫn là biểu mẫu thật
Nạp (`multipart`, một ô nhiều file), hoàn tác (`<details>` rồi nút), ngân sách (một giao dịch;
ô rác → 400 + `da_go` hiện lại đúng chữ đã gõ), đổi quyền (`form=` HTML5 theo cột), đăng
nhập, đăng xuất: `<form method="post">` như bản Jinja — chạy cả khi JavaScript hỏng, bảo vệ
CSRF giữ nguyên (SameSite=Lax), không đổi hành vi nào ở máy chủ.

## 3. Trang thông báo
`_loi` (500), bản chỉ-đọc (403), không có quyền Kho dữ liệu / Ngân sách / đổi quyền (403) →
`window.__KOME__.thong_bao`, vẽ trong khung chung (`he_thong/ThongBao.tsx`) — thanh bên vẫn là
lối ra của trang lỗi và ẩn/hiện mục theo cờ quyền như mọi màn. `_loi` không chạm CSDL (điều
kiện để middleware dùng được). Thiếu bản build → trang HTML trần tối thiểu. `/api/*` bị cấm →
403 JSON. Đăng nhập sai → vỏ React + `dang_nhap_sai`, mã 401 (một thông báo cho cả sai tên lẫn
sai mật khẩu).

## 4. Đăng nhập (so với gói thiết kế)
Giữ bố cục hai cột (dải đỏ | biểu mẫu), nút Hiện/Ẩn mật khẩu. KHÔNG: email (đăng nhập bằng
tên), SSO Google, "nhớ đăng nhập" (vé cố định 12 giờ), "quên mật khẩu" (chỉ qua script), số
liệu công ty (trang công khai, chưa ai đăng nhập), ma trận vai trò (app có 3 cờ nhị phân).

## 5. Dọn
Xoá `kome/web/templates/` (toàn bộ), `Jinja2Templates`, `_ve`, `_sale_dang_loc` (gọi thẳng
`api.sale_dang_loc`), `tai_lieu.md_dong` + `markupsafe` (React có `md()` riêng, không
innerHTML), `jinja2` khỏi `requirements.txt` / `pyproject.toml`. Test HTML chuyển sang đọc
`window.__KOME__` + mã React (cùng bất biến).
