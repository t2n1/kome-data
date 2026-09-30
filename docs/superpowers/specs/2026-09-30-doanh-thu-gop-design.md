# Trang Doanh thu — gộp Báo cáo · Dự báo · Ngân sách (2026-09-30)

Chủ DN: "ba trang chung với nhau, gộp lại cho gọn, ít chữ, nhiều graph"; chọn bố cục "1 trang, 1 biểu đồ chính";
"phải có lợi nhuận"; "bubble graph"; gọi nhóm ngành là **Danh mục**.

## Địa chỉ
- `/bao-cao` = trang **Doanh thu** (thanh bên: MỘT mục "Doanh thu", icon `chart`). `/du-bao` → **301** `/bao-cao` (giữ query).
- `/ngan-sach` GIỮ NGUYÊN (màn nhập, cờ `duoc_sua_ngan_sach`, `<form method="post">` thật) nhưng rời thanh bên; vào bằng nút
  "✎ Sửa ngân sách" trên trang Doanh thu (chỉ hiện khi `KD.hien_ngan_sach`).
- `/api/bao-cao` và `/api/du-bao` giữ nguyên hai endpoint / hai ảnh chụp; trang gọi cả hai song song. Ngân sách lượt hỏi KHÔNG
  đổi: `/api/bao-cao` ≤ 11, `/api/du-bao` = 3.

## Công tắc Doanh thu | Lãi gộp
Đầu trang, đổi cả trang (trạng thái trình duyệt). "Lợi nhuận" = lãi gộp 粗利益 — lợi nhuận ròng không có nguồn, không vẽ.
Khối nào chưa có số lãi gộp (cầu nối, Pareto khách, Danh mục × tháng, nguy cơ ngừng mua) vẫn vẽ doanh thu và nói ra ở nhãn.

## Bố cục (không bảng nào trừ bản đồ nhiệt — `<table>` có `scope` là bất biến cũ)
1. **4 ô số**: Đã bán (+ đường nhỏ, dòng so kỳ so kèm số tháng đối chiếu — bất biến 5b) · Dự kiến chốt tháng (khoảng thấp–cao;
   ⓘ = cách tính + "dự báo đã chuẩn tới đâu") · % ngân sách tháng (thanh + vạch mốc hôm nay) · Biên lãi gộp.
2. **Biểu đồ chính** (`BieuDo`) — 12 tháng của kỳ: cột thực tế · cột nền dự báo (tháng của mốc = chốt dự kiến; tháng sau =
   12 tháng tới theo kịch bản Cơ sở / Thận trọng / Lạc quan) · đường LIỀN ngân sách công ty · cột ma kỳ so (nét đứt chỉ cho kỳ
   so). Dạng Khoảng: cột theo ngày/tháng + cột ma, không ngân sách / dự báo (nói ra). ⓘ = tổng 12 tháng tới, so năm trước.
3. **Luỹ kế tháng này** (hình của `ve_du_bao.ve_chot_thang`) — chỉ khi tháng đang xem là tháng của mốc.
4. **Cầu nối** (`ve_phan_tich.ve_cau_noi`): kỳ so → từng danh mục ± → kỳ này. Đối soát: đầu + Σ bước = cuối (có test).
5. **Bong bóng Danh mục** (`ve_bong`): x = tăng/giảm % so kỳ so, y = biên lãi %, bóng = doanh thu (hoặc lãi gộp). Danh mục
   doanh thu ≤ 0 hoặc không có số so KHÔNG vẽ và PHẢI in "Không vẽ: … " (cùng luật cây ô).
6. **Bong bóng Mặt hàng**: top 40 theo doanh thu (bỏ phí / POSM / dòng ※終売※ gộp): x = số khách mua, y = biên lãi %,
   bóng = doanh thu (hoặc lãi gộp); bấm → `/san-pham/{mã}`.
7. **Người phụ trách**: thanh đã bán + phần dự báo thêm tới cuối tháng + vạch ngân sách + vạch đứt kỳ so.
8. **Pareto khách** (hình cũ, bỏ bảng) · 9. **Danh mục × tháng** (bản đồ nhiệt cũ) · 10. **Nguy cơ ngừng mua** (thanh).
Dòng nhỏ cuối: Phí & điều chỉnh / Hàng tặng POSM (ⓘ liệt kê). Nút ⤓ CSV giữ.

Bỏ khỏi trang: bảng top 10 lãi gộp (thay bằng bong bóng mặt hàng), bảng tháng / bảng nhân viên chi tiết, khối "Đơn kỳ vọng 14
ngày" (dữ liệu vẫn ở `/api/du-bao`), cây ô và "ngành kéo lên/xuống" (thay bằng cầu nối + bong bóng; cây ô vẫn ở `/mua-vu`).
Câu "Cách tính: …" của đợt 8 chuyển vào ⓘ của khối (cùng luật Tổng quan ít chữ); câu ngoại lệ vẫn luôn hiện.

## Dự báo lãi gộp (mới, `kome/du_bao.py`)
CÙNG hai công thức, áp lên chuỗi lãi gộp theo ngày (`mart.ban_theo_ngay.lai_gop`, đọc trong câu lịch có sẵn — 0 lượt mới):
chốt tháng lãi gộp = đã có + (đã có ÷ ngày làm việc đã qua) × ngày còn lại; khoảng thấp–cao = sai số của chính cách đó trên
tháng cũ; 12 tháng tới = lãi gộp cùng tháng năm trước × hệ số (TỶ SỐ CỦA CÁC TỔNG lãi gộp). Tháng "đủ ngày" xét theo DOANH THU
(một tập tháng cho cả hai chỉ số). Người phụ trách thêm lãi gộp (cột có sẵn của `mart.tien_do_ngan_sach`).

## Tên
"Danh mục" = `food_category_name` (食品分類) — CHỈ đổi chữ hiển thị trên trang này; nhãn `(chưa phân loại)` và mọi hằng giữ nguyên.
