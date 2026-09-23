# Đặc tả thiết kế — Đợt 7: Cần liên hệ + nhật ký tiếp xúc

**Ngày:** 2026-09-23 · **Trạng thái:** đã duyệt trong hội thoại, đã triển khai
**Liên quan:** lộ trình §7–§8.2 · đặc tả đợt 1 §5.5–5.6 (bản gốc của ý tưởng) ·
gói thiết kế `CRM.dc.html` (bố cục màn) và `Customer 360.dc.html` (khối "Nhật ký
tiếp xúc", từ vựng `KIEU_TX`/`KQ_TX`).

## 1. Vì sao
Nhân viên Hà Huy Long tự dựng danh sách "hôm nay gọi ai" bằng Excel, và kết quả mọi
cuộc gọi không được ghi ở đâu (đặc tả đợt 1 §1). `/can-xu-ly` chỉ hiện khách đã trễ
hẳn (≥ 2× nhịp); dải "sắp đến hạn" (1–2×) — lúc gọi còn giữ được khách — không hiện
ở đâu cả. Đo CSDL thật 2026-09-23: 169 khách ở dải đó, 75 quá hạn, 136 lâu không mua.

## 2. Quyết định

| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Bố cục | Màn `CRM.dc.html`: ô chỉ số → **cột theo LÝ DO** (thay cột giai đoạn deal) → "Hoạt động gần đây" + "Hẹn gọi lại hôm nay" | Chủ dự án yêu cầu bám handoff; đơn vị công việc là cuộc gọi, không phải hợp đồng (lộ trình §8.2) nên không kéo–thả |
| Từ vựng nhật ký | Đúng gói thiết kế: `goi`/`ghe`/`chat` · `tot`/`binh`/`xau` | Bám handoff. Thay bộ `dat_hang/tu_choi/…` của đặc tả đợt 1 |
| Trường thêm so với handoff | `hen_lai` (ngày hẹn) | Quyết định khách ẩn tới bao giờ; không có thì danh sách hoặc hiện lại y nguyên, hoặc ẩn vô thời hạn |
| Lý do | `lau_khong_mua` = `da_roi_bo`, `qua_han` = `canh_bao`, `sap_den_han` = `binh_thuong` ∧ `ty_le_im_lang ≥ 1` | Đọc lại `trang_thai` của `mart.khach_360` — không định nghĩa mới. Hai cột đầu = nhóm việc `'im'` |
| `tut`/`moi` | KHÔNG vào view; trang trỏ sang `/khach-hang?nhom=` | `mart.khach_nhom_viec` dựng lại `khach_360` 3 lần (~1,2 s mỗi lần trên CSDL thật) |
| Ẩn sau khi ghi | Tới `hen_lai` (hôm đó HIỆN), hoặc 7 ngày nếu không hẹn; khối "đang tạm ẩn" liệt kê | Không ẩn = hiện lại như chưa ai gọi; ẩn lặng lẽ = mất khách khỏi tầm mắt |
| "Hôm nay" của việc ẩn/hẹn | Đồng hồ thật giờ Tokyo | Hẹn là ngày ngoài đời; ngoại lệ thứ hai của bất biến mốc thời gian |
| Sửa/xoá nhật ký | Không — chỉ thêm, **CSDL chặn** (`REVOKE UPDATE, DELETE`) | Sổ tay năm người không có biên tập viên |
| Khoá ngoại tới khách | Không (SCD2); Python kiểm `is_current` trước khi ghi | `customer_code` không duy nhất trên cả bảng |
| Ghi ở bản Vercel | Được | Cùng lý lẽ `POST /ngan-sach` — `_chi_doc` là giới hạn luồng nạp, không phải phân quyền |
| `/can-xu-ly` | 301 → `/lien-he` (giữ `tat_ca`); sidebar "Cần liên hệ" | Lộ trình §4.1: bỏ route cũ khi đợt 7 xong |
| Ngân sách truy vấn | `/lien-he` = 3; `ho_so()` = 8 (chạm trần) | Có test đếm |

## 3. Thành phần
`db/migrations/030_lien_he.sql` (bảng `app.nhat_ky_tiep_xuc`, view
`mart.uu_tien_lien_he`) · `kome/lien_he.py` · `kome/khach_hang.py` (`HoSo.nhat_ky`) ·
`kome/web/app.py` (`GET /lien-he`, `POST /khach-hang/{mã}/tiep-xuc`, 301
`/can-xu-ly`) · `templates/lien_he.html`, `_ghi_tiep_xuc.html`, khối `#nhat-ky` trong
`khach_360.html` · `kome.css` · `tests/test_lien_he.py`.

Biểu mẫu: chip là `<input type=radio>` trong `<label>` (`:has(:checked)`), không JS.
`tiep` (trang quay về) lọc qua `bao_mat.duong_dan_an_toan`. Lỗi biểu mẫu quay về kèm
`?loi_tx=` — câu tiếng Việt, không phải CheckViolation.

## 4. Không làm
Kanban cơ hội bán (lộ trình §8.2) · nhắc việc qua email · sửa/xoá dòng nhật ký ·
"Giao cho nhân viên"/"Xuất Excel" của danh bạ trong handoff.
