# Đặc tả thiết kế — Màn 20 (Nhật ký thao tác) + 21 (Cài đặt)

**Ngày:** 2026-09-23 · **Trạng thái:** chủ dự án giao "làm hết" — quyết định ghi ở đây, đã triển khai
**Liên quan:** lộ trình §7 (đợt 3, hai màn bị cắt khỏi đợt 3 — đặc tả đợt 3 §4.2) · gói thiết kế `Nhật ký.dc.html`, `Cài đặt.dc.html`.

## Vì sao làm bây giờ
Đặc tả đợt 3 cắt hai màn vì "ghi vết là một hệ thống riêng" và "script đúng hơn màn hình khi có 5–7 tài khoản".
Từ đợt 5a/7 hệ thống đã có ba sổ chỉ-thêm (ngân sách, tiếp xúc, lô nạp) — nhật ký giờ là ĐỌC GỘP, không phải hệ thống mới.

## Quyết định
| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Bảng nhật ký chung? | **Không** — đọc gộp 5 nguồn (`kome/nhat_ky.py`) | Bản sao thứ hai của sự kiện sẽ lệch sổ gốc |
| Thiếu gì để trả lời "ai" | `meta.ingest_batch.nap_boi`/`huy_boi` + sổ `app.nhat_ky_quyen` (033) | Nút Hoàn tác xoá được một tháng doanh thu — phải biết ai bấm |
| Loại thao tác | nạp · hoàn tác · ngân sách · quyền · tiếp xúc | Không dựng "sửa giá/duyệt/hạn mức" của prototype — hệ thống không có thao tác đó |
| Cài đặt dựng gì | Người dùng & 3 cờ quyền · ngày lễ · quy tắc (đọc) · nguồn (liên kết) · hiển thị | Chỉ thứ có thật đằng sau; "tính năng bật/tắt", "kênh gửi", ngưỡng hạng sửa được: KHÔNG (công tắc không nối vào đâu là nói dối) |
| Ai đổi được quyền | Cờ mới `duoc_quan_tri`, cấp lần đầu bằng script | Cùng nếp hai cờ trước: quyền ghi phải cấp tường minh |
| Mật khẩu trên web | **Không bao giờ** | Đặc tả đợt 3 §4.2 |
| Máy chưa bật đăng nhập | Cài đặt từ chối đổi quyền | Không biết ai đổi; cờ cũng chưa bảo vệ gì |
| Tự bỏ quản trị | Từ chối | Chống khoá chính mình ra ngoài |
| 30 ngày của khối tổng hợp | Đồng hồ thật (`now()`) | Sổ sự kiện ngoài đời, không phải chỉ số trên dữ liệu bán |
| Xuất CSV | Có (`/nhat-ky.csv`, BOM UTF-8) | Nút "⤓ Xuất CSV" của gói thiết kế |

## Thành phần
`db/migrations/033_nhat_ky_thao_tac.sql` · `kome/nhat_ky.py` · `kome/web/nguoi_dung.py` (`CO_QUYEN`, `dat_quyen` ghi sổ) ·
`scripts/tao_nguoi_dung.py` (`--quan-tri`) · `kome/web/app.py` (`/nhat-ky`, `/nhat-ky.csv`, `/cai-dat`, `POST /cai-dat/quyen/{id}`, `_ghi_ai`) ·
`templates/nhat_ky.html`, `cai_dat.html`, `cam_cai_dat.html`, `_nav.html` (icon `cal`/`gear` của `kome-nav.js`) · `tests/test_nhat_ky.py`.
