# Giai đoạn 4 — Sản phẩm · Kho hàng (React)

Ngày: 2026-09-23 · Đặc tả cha: `2026-09-23-giao-dien-react-design.md` §6 · Bảng so gói
thiết kế: `Sản phẩm.dc.html`, `Kho hàng.dc.html` (bản so sánh 05_san_pham_kho.md).

## 1. Phạm vi
`/san-pham`, `/san-pham/{mã}`, `/kho-hang` chuyển sang React (template Jinja `san_pham.html`,
`san_pham_360.html`, `kho_hang.html` đã xoá). Dữ liệu:

| Endpoint | Gọi lại | Phiên bản ảnh chụp | Lượt hỏi |
|---|---|---|---|
| `GET /api/san-pham` | `SP.danh_muc` — CẢ danh mục (232 mã) | chỉ nạp | 1 |
| `GET /api/san-pham/{mã}` | `SP.ho_so` | chỉ nạp | ≤ 5 (trần đặc tả 4b §5.5) |
| `GET /api/san-pham/{mã}/ngay?thang=YYYY-MM` | `SP.ban_theo_ngay` | chỉ nạp | 1 |
| `GET /api/kho-hang?kho=&loc=` | `SP.kho_hang` | chỉ nạp | 2 (bất biến 4b) |

Cả bốn chỉ đọc `core`/`mart` (không bảng `app` nào) nên dùng `chi_nap=True`. `lam_nong`
làm nóng danh mục và màn kho không lọc.

## 2. Màn Sản phẩm = MỘT trang (như gói thiết kế)
Ô tổng quan → danh mục (chip ngành · chip trạng thái · ô tìm · sắp theo cột, 232 dòng trong
khung cuộn có tiêu đề dính) → hồ sơ 360° của mã đang chọn NGAY BÊN DƯỚI. `/san-pham/{mã}` là
cùng màn đó với một mã được chọn; chọn dòng là `pushState`. Cả danh mục một ảnh chụp nên lọc /
sắp / tìm chạy ở trình duyệt (`giao_dien/src/san_pham/loc.ts`) — cùng luật bộ đếm của
`danh_sach()`: mỗi dải chip đếm theo mọi bộ lọc TRỪ bộ lọc của chính nó.

Hai cột mới trong `danh_muc`, cùng câu lệnh (một CTE trên `mart.dong_ban`):
* `dt_12t` / `lg_12t` / `ts_12t` — cửa sổ 12 tháng ĐÚNG của `mart.hang_doanh_thu`
  (`sales_date > hom_nay - 365`); tỷ suất là tỷ số của các tổng. `san_pham_360.doanh_thu_thuan`
  là LUỸ KẾ — màn ghi rõ cột nào là cột nào.
* `thang_dt` — 12 tháng lịch tới tháng mốc (đường nhỏ trong bảng).
* `nganh` — `food_category_name`, rỗng thành `kome.bao_cao.NGANH_TRONG`. `san_pham_360.nhom`
  (`kind_name`) chỉ có 有形/無形 trên CSDL thật nên không dùng để lọc.

## 3. Quyết định khi gói thiết kế đòi thứ không có nguồn
| Gói thiết kế | Làm gì |
|---|---|
| Cột "Giá bán", "Δ 12T" theo mã | Không có "giá hiện hành" một con số (giá theo bậc 売価No. ở hồ sơ). Thay Δ bằng đường 12 tháng + DT 12 tháng thật |
| Ô "SKU tăng trưởng / đang giảm" | Thay bằng "Cần đặt hàng" (hết + sắp thiếu → tab Cần đặt) và "Tồn chết" — số thật từ `trang_thai` |
| Lượng bán theo ngày, cột nhạt cùng kỳ | CÓ — `/ngay` (mart.dong_ban + `mart.lich_kinh_doanh`), đổi số lượng/doanh thu/lãi gộp, so tháng trước CÙNG NGÀY khi tháng đang chạy |
| "Khách đang mua" có Δ từng khách | Thanh tỷ trọng + nhịp + trễ; không Δ (chưa có so cùng kỳ theo cặp) |
| "Khách chưa mua mã này" (cơ hội chào hàng, lý do viết tay) | Khung "chưa có dữ liệu" — cần cách chọn khách có kiểm chứng; OBC chỉ xuất mã loại hình khách |
| "Hàng về" / LÔ SẮP VỀ; tab "Hàng đang về" | "chưa có dữ liệu" — OBC chưa xuất 仕入・発注 |
| Tab "Cần đặt" có số lượng đề xuất + tạo PO | Danh sách mã hết/sắp thiếu với bán/ngày, còn đủ bán; KHÔNG đề xuất số lượng (thiếu lead time / MOQ / NCC); nút PO vô hiệu kèm lý do |
| Ba kho Osaka/Nagoya/Kho lạnh | Tên kho đọc `core.dim_warehouse` (bẫy #6) |
| Cột "Lô" | Không có mã lô trong 在庫一覧 → "Tồn theo dòng" (mã × kho × hạn) |
| Cột "Đủ bán" từng dòng tồn | Hiện `du_ban_ngay` CỦA CẢ MÃ (mọi kho), ghi rõ "(cả mã)" |
| "Đề xuất SALE" / "Chào khách lớn" | Liên kết "Khách đang mua mã này →" (hồ sơ mã) — không có trạng thái sale để lưu |
| "⤓ Xuất Excel" | "⤓ Xuất CSV" đúng các dòng bảng tồn đang hiện, làm ở trình duyệt |

## 4. Bất biến giữ nguyên (chuyển từ test HTML sang test API + mã React)
Tồn NULL in "—" (không `?? 0`); sáu nhãn trạng thái đọc từ API; màn chỉ hiện
`toc_do_ngay_theo_tuoi`; bốn loại hạn; quá hạn tách khối trước cận hạn; ô nào "mọi kho" nói
ra; `loc` lạ = không lọc, `kho` lạ = lọc thật + mục riêng; giá trị tồn = tổng đúng các dòng
bảng. Test: `tests/test_san_pham.py` (phần giai đoạn 4).
