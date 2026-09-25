# Tổng quan độ phủ — lưới tháng × loại dữ liệu

Chủ doanh nghiệp (2026-09-25): "để xem web app đã có dữ liệu của tháng nào, data nào rất khó theo
dõi". Đã duyệt phác thảo "lưới toàn cảnh" + gọn các khối cũ, dời xuống.

## 1. Vì sao màn cũ khó đọc
- Câu "có dữ liệu tháng nào" bị chia ba chỗ: lưới NGÀY (một tháng một lần, ‹ ›), bảng THÁNG (mỗi kỳ
  kế toán một bảng, tháng xếp dọc, ô chỉ `●`/`·`), dòng "Kỳ dữ liệu bán hàng" trong khối Sức khoẻ.
- Ô tháng chỉ nói CÓ/KHÔNG: tháng có 3 ngày bán cũng là `●`.
- Nửa trên (sơ đồ tròn 8 nguồn, 4 ô "số bảng / tổng số dòng") không trả lời câu đó.
- Không lộ ra tháng nào bán hàng đến từ `売上明細表` (ít cột, `amount` chưa thuế — bẫy #8).

## 2. Màn mới (`/kho-du-lieu`)
1. **Tóm tắt** (`#hom-nay`): mỗi nguồn LỊCH SỬ một ô — "có từ A → B", "thiếu n ngày làm việc" (giữa
   ngày đầu và ngày cuối CÓ dữ liệu; ngày chưa tới lượt nạp là việc của cột tình trạng) — cộng ô
   "Hôm nay: x/3 file 13:30 đã nạp" (từ `nguon`, nhịp `ngay`).
2. **Lưới** (`#theo-thang`): dòng = 8 loại file OBC (`coverage.COT`; nguồn chưa nạp hiện "không có", không biến mất), cột = tháng từ
   tháng của `DAU_DU_LIEU` tới tháng hiện tại, dải kỳ kế toán trên đầu (`core.dim_date.company_fy_label`,
   tháng chốt kỳ đánh dấu). Hai nhóm dòng, vì trả lời hai câu khác nhau:
   - **Lịch sử** (bán hàng, tồn kho, công nợ nếu dùng) — ô = ngày LÀM VIỆC có dữ liệu / ngày làm việc
     của tháng (cắt ở `DAU_DU_LIEU` và hôm nay): `du` · `thieu` (in số ngày có) · `khong`.
     Bán hàng: ô mang cờ `meisai` khi có ngày đến từ `売上明細表` → vẽ sọc + chú giải.
   - **Dữ liệu nền** (khách hàng, sản phẩm, giao thẳng…; bản mới đè bản cũ) — ô = `moi` khi tháng đó
     có lô mang `data_date` trong tháng, không thì `trong`. Ô trống ở nhóm này KHÔNG phải thiếu.
   - Đầu dòng: nhãn + tên OBC, bấm → `/kho-du-lieu/bang/<core_table>`. Cuối dòng: tình trạng của
     nguồn (`kho_du_lieu.nut_nguon` — màu + câu có sẵn), nền thêm "bản dd/mm".
3. **Chi tiết tháng** (`#theo-ngay`): bấm một tháng → từng ngày của tháng đó cho mọi dòng (lịch sử:
   có / có từ 売上明細表 / thiếu / nghỉ; nền: chấm ngày có bản mới), kèm danh sách ngày làm việc
   thiếu và câu "xuất lại … của đúng ngày đó từ OBC". Mặc định tháng mới nhất; `?ngay_thang=YYYY-MM`
   (giữ tên cũ — `?thang=` là khoảng xem chung) chọn sẵn, đổi tháng ghi URL qua `giuKhoang()`.
   Toàn bộ ngày của mọi tháng đi cùng MỘT lần tải (một chuỗi ký tự mỗi dòng × tháng) — đổi tháng
   không hỏi máy chủ.
4. **Cuối trang, thu gọn** (`<details>`): Sức khoẻ & sao lưu (bảng lần nạp cuối — `status`,
   `backup` như cũ) · Loại dữ liệu chưa vào kho (`THIEU_BO_NAP`) · Hạn chế cần biết (ô "không có"
   không phân biệt chưa xuất / bị cổng chặn; trước `DAU_DU_LIEU` không tồn tại; Obon/年末年始 vẫn
   đếm là ngày làm việc).

Bỏ: sơ đồ tròn, 4 ô số (và câu danh mục `pg_class` của chúng), lưới ngày ‹ ›, bảng tháng theo kỳ
(kèm doanh thu/lãi gộp từng kỳ — không phải độ phủ; số đó có ở `/bao-cao`), `_ky_du_lieu`.

## 3. Máy chủ
- `kome/coverage.py::tinh_luoi_phu(conn, hom_nay)` → `LuoiPhu` — MỘT nơi tính (cùng nếp file). Năm
  câu: lịch (`mart.lich_kinh_doanh` ⋈ `core.dim_date`), ngày bán (+ `bool_or(source = 'meisai')`),
  ngày ảnh chụp tồn, `data_date` các lô chưa hoàn tác, kỳ sổ công nợ (chỉ khi nguồn đó đang dùng).
  "Ngày làm việc" = `mart.lich_kinh_doanh.la_ngay_kd` (định nghĩa duy nhất). Khách hàng đọc
  `data_date` (không đếm dòng SCD2 — cùng lý lẽ `tinh_bang_ngay`).
- `tinh_bang_phu` giữ cho `scripts/bang_phu_du_lieu.py`; `tinh_bang_ngay` giữ (test ngày lễ đọc).
- `_du_lieu_kho` → `status`, `tuoi`, `nguon`, `phu`, `ngay_thang`, `backup`.

## 4. Test
- `tinh_luoi_phu`: tháng đủ / thiếu (đếm đúng ngày làm việc, ngày lễ không tính thiếu) / không; cờ
  `meisai`; nền `moi` theo `data_date`, lô hoàn tác không tính; `thieu` nêu đích danh ngày
  (thay test `/health` cũ); ngày nghỉ có bán vẫn là "có"; chỉ nguồn đang dùng.
- Màn: đủ khối (`hom-nay`, `theo-thang`, `theo-ngay`, sức khoẻ), `?ngay_thang=` đi qua, không lộ
  tên CSDL, bản chỉ-đọc vẫn có `status`, `backup` null.
