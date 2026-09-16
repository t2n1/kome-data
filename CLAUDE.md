# Ngữ cảnh dự án kome-data

## Công ty làm gì
株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật.
~¥1,5 tỷ doanh thu/năm · 2.080 khách hàng · 232 mã hàng · 5 nhân viên phụ trách khách.
Khách chủ yếu là tạp hoá Việt (577) và quán ăn Việt (269), trải 48 tỉnh.

## Luật số một
**OBC 奉行 là sổ cái kế toán chính thức. Dữ liệu của nó CHỈ ĐỌC.**
Số sai thì sửa trong OBC rồi xuất lại — không bao giờ UPDATE trong CSDL này.

## Quy trình hằng ngày
13:30 nhân viên xuất 3 file từ OBC, kéo thả vào trang nội bộ.
Đầu mỗi tháng xuất lại toàn bộ tháng trước để bắt các phiếu đã bị sửa/huỷ (đối soát tháng).

## Từ điển
得意先 = khách hàng · 請求先 = bên nhận hoá đơn (có thể khác 得意先)
伝票 = phiếu · 赤伝 = phiếu đỏ (hàng trả lại, số ÂM, không được lọc bỏ)
粗利益 = lãi gộp · 単価 = đơn giá · 単位原価 = giá vốn đơn vị
締め日 = ngày chốt công nợ · 直送先 = điểm giao thẳng
担当者 = người phụ trách khách · 倉庫 = kho · 賞味期限 = hạn sử dụng
荷姿区分 = quy cách đóng gói (00 = バラ lẻ, 02 = ケース thùng)

## Bẫy đã biết
1. Mã (`*コード`) là TEXT. `000000009292` đọc thành số sẽ mất số 0 đầu → hỏng mọi liên kết.
2. Số lượng CÓ phần thập phân (`83.75` ケース). Tiền thì luôn là số nguyên yên.
3. Có bản xuất `得意先全情報` chỉ 201 dòng (xuất một phần) và bản chỉ 5 cột (sai mẫu) — cổng 3 phải chặn.
4. File báo cáo (`売上明細表`, `元帳`) có 5 dòng rác trước header. File master và `在庫一覧` thì header ở dòng 1.
5. `担当者` của OBC (5 người) KHÁC người nhập đơn trên web (7 tài khoản, gồm 2 arubaito).

## Bốn vai trò CSDL (Task 13, `db/migrations/009_roles.sql`)
Luật số một ("OBC chỉ đọc") không chỉ là quy ước trong code — nó là ràng
buộc của chính CSDL. Bốn vai trò cấp cụm (`NOLOGIN`, mật khẩu đặt tay ngoài
git — xem `docs/runbook.md`):
- `kome_ingest` — vai trò của tiến trình nạp dữ liệu. SELECT/INSERT/UPDATE
  trên `core` và `meta`. Đây là vai trò DUY NHẤT được ghi vào `core`.
- `kome_app` — vai trò của ứng dụng web. Chỉ SELECT trên `core`/`mart`;
  đọc-ghi trên `app`. **Không có quyền UPDATE/DELETE trên `core`** — kể cả
  nếu code lỡ viết nhầm câu lệnh, CSDL sẽ từ chối.
- `kome_report` — chỉ SELECT, mọi schema (`core`, `mart`, `app`). Dùng cho
  công cụ báo cáo/BI ngoài ứng dụng chính.
- `postgres` (superuser hiện tại của Supabase) — chỉ dùng để chạy migration,
  không dùng cho vận hành thường ngày.

`ALTER DEFAULT PRIVILEGES` trong migration đảm bảo bảng tạo sau này cũng tự
nhận đúng quyền, không cần GRANT tay mỗi lần thêm bảng mới.

## Không được tự ý sửa
- File trong `db/migrations/` đã chạy rồi — chỉ thêm file mới
- Luật bất biến trong kế hoạch/đặc tả
- Định nghĩa chỉ số ở chỗ khác ngoài `mart/`

## Chạy test
pytest -v
