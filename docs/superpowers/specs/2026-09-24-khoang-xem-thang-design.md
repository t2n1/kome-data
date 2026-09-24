# Khoảng xem — cả website mặc định theo tháng

Chủ doanh nghiệp (2026-09-24): "Tôi muốn toàn bộ website mặc định chỉ tập trung vào
từng tháng. Có nút xem theo kỳ hoặc xem theo khoảng thời gian."

Bốn quyết định đã chốt khi hỏi lại:

| Câu hỏi | Chốt |
|---|---|
| Áp cho màn nào | **Các màn doanh số**: Tổng quan, Báo cáo, Khách hàng (danh sách + hồ sơ + bản đồ), Sản phẩm. Kho hàng · Công nợ · Cần liên hệ · Dự báo giữ "tính theo hôm nay" |
| Tháng mặc định | **Tháng hiện tại** = tháng của ngày bán mới nhất (`mart.moc_thoi_gian`), mùng 1 → hôm nay |
| Giữ lựa chọn | **Chung cả website, nằm trên URL**; đổi màn vẫn giữ; đóng trình duyệt mở lại là về tháng hiện tại (không cookie, không localStorage) |
| Cái gì đổi theo | **Số bán hàng đổi** (doanh thu, lãi gộp, số đơn, số khách mua, top, bản đồ, biểu đồ). **Nhãn giữ theo hôm nay** (hạng 12 tháng, trạng thái khách/nhịp mua, tồn, tốc độ bán 90 ngày) — ghi rõ "tính đến hôm nay" |

## 1. Mô hình

Một **khoảng xem** cho cả website, ba dạng, đọc từ URL:

| Dạng | URL | Dải ngày | So với |
|---|---|---|---|
| Tháng | `?thang=YYYY-MM` (không tham số = tháng hiện tại) | mùng 1 → min(cuối tháng, hôm nay) | **tháng trước** cùng dải ngày (ngày cuối kẹp về cuối tháng trước) · **cùng tháng năm trước** cùng dải ngày (29/2 → 28/2, như `mart.thang_den_hom_nay`) |
| Kỳ | `?ky=<company_fy>` | 1/8 → 31/7 của kỳ, cắt theo dải dữ liệu | **cùng kỳ** trên các tháng đối chiếu (`mart.ky_cung_ky`, in "n tháng đối chiếu") |
| Khoảng | `?tu=YYYY-MM-DD&den=YYYY-MM-DD` | [tu, den] cắt theo dải dữ liệu | **khoảng liền trước** cùng số ngày · **cùng khoảng năm trước** |

- Hai dạng cùng lúc (vd `thang` + `ky`) → 400 "chỉ chọn một". Sai cú pháp → 400. Tháng/kỳ
  ngoài dải dữ liệu → 400 kèm lời nhắc; khoảng `tu/den` bị cắt vào dải dữ liệu, cắt xong
  rỗng → 400.
- Một phép so sánh chỉ **có** (`co = true`) khi tháng chứa ngày đầu của nó đã có dữ liệu
  (cùng luật `EXISTS … trong tháng` của `mart.thang_den_hom_nay`). Không có thì trả `co =
  false` và màn in "không có dữ liệu để so" — không bao giờ so với một khoảng chỉ có một
  phần dữ liệu mà không nói.
- Tháng hiện tại khi hôm nay là ngày cuối tháng = trọn tháng; so trọn tháng trước và trọn
  tháng năm trước.
- Mỗi khoảng có **một câu mô tả** sinh ở máy chủ: "Tháng 7/2026 · 1/7 → 31/7 · so 1/6 → 30/6
  và 1/7 → 31/7/2025".

`kome/khoang_xem.py` là chỗ **DUY NHẤT** hiểu khoảng xem: đọc tham số, kiểm, cắt, tính các
dải so sánh, sinh câu mô tả. Mọi API doanh số trả kèm object `khoang` của nó; giao diện
chỉ hiện, không tự tính ngày so sánh.

## 2. Định nghĩa chỉ số — vẫn ở `mart` (migration 039)

Hàm SQL có tham số `(tu date, den date)`, `LANGUAGE sql STABLE` (Postgres gộp thẳng vào câu
gọi, dùng chỉ mục `fact_sales_line(sales_date)` có sẵn):

| Hàm | Một dòng mỗi | Cột |
|---|---|---|
| `mart.dong_ban_khoang(tu, den)` | dòng bán | `SETOF mart.dong_ban` lọc `sales_date BETWEEN tu AND den` — nền của mọi hàm dưới |
| `mart.tong_khoang(tu, den)` | — (1 dòng) | dt, lg, ty_suat, so_phieu, so_khach, so_dong |
| `mart.ngay_khoang(tu, den)` | ngày (từ LỊCH, ngày không bán = 0) | ngay, dt, lg, so_phieu, so_khach |
| `mart.thang_khoang(tu, den)` | tháng (đã cắt theo dải) | thang, tu, den, dt, lg, so_phieu, so_khach |
| `mart.sale_khoang(tu, den)` | người phụ trách | như `mart.ban_theo_nhan_vien` |
| `mart.mat_hang_khoang(tu, den)` | mã hàng | như `mart.ban_theo_san_pham` |
| `mart.khach_khoang(tu, den)` | khách | dt, lg, ty_suat, so_phieu, so_ngay_mua, lan_cuoi |
| `mart.nganh_khoang(tu, den)` | ngành | nganh, dt, lg |
| `mart.tap_trung_khoang(tu, den)` | khách (Pareto) | như `mart.tap_trung_khach` |

- Tỷ suất = tỷ số của các tổng; doanh thu thuần, 赤伝 giữ nguyên (luật của `014`).
- Nhãn ngành: 039 thêm `mart.ten_nganh(text)` và `CREATE OR REPLACE VIEW
  mart.ban_theo_nganh_thang` để view đó gọi hàm này — biểu thức `coalesce(nullif(…,''),
  '(chưa phân loại)')` vẫn viết **một lần**, giờ ở trong hàm.
- Các view cũ (`ban_theo_thang`, `tong_theo_ky`, `ky_cung_ky`, `thang_den_hom_nay`, …) giữ
  nguyên; chế độ Kỳ của Báo cáo vẫn đọc chúng.

**Đẳng thức có test canh** (chuyển sang cách tính mới không làm đổi con số nào đang hiện):
1. `tong_khoang(1/M, cuối M)` = dòng `mart.ban_theo_thang` của tháng M (dt, lg, so_phieu,
   so_khach).
2. Tháng hiện tại qua `khoang_xem` + `tong_khoang` = `mart.thang_den_hom_nay` (dt, lg,
   so_khach, và dải ngày cùng kỳ `tu_ngay_ck`/`den_ngay_ck`, `co_cung_ky`).
3. `/api/bao-cao?ky=N` trả đúng số như trước đợt này.
4. `sum(ngay_khoang)` = `tong_khoang` (dt, lg); `sum(nganh_khoang)` = `tong_khoang.dt`.

## 3. Mỗi màn

Luật chung: tiêu đề khối nào đi theo khoảng xem thì ghi khoảng ("Doanh thu · Tháng
7/2026"); khối tính theo hôm nay ghi "tính đến hôm nay".

### 3.1 Tổng quan (`/`) — đợt A

| Khối | Theo khoảng |
|---|---|
| `kpi` | Ô doanh thu = `tong_khoang`, so theo §1 (hai phép so ở dạng Tháng/Khoảng). Ô ngân sách: tiến độ tháng đang xem (dạng Tháng) / kỳ (dạng Kỳ) / không có (dạng Khoảng — "ngân sách chỉ theo tháng/kỳ"). Ô kho, ô khách: **hôm nay** |
| `xu_huong` | Ngày trong khoảng (`ngay_khoang`) + đường mờ của phép so thứ nhất. Bỏ nút 7N/30N/90N/1N |
| `theo_thang` | Các tháng của kỳ chứa ngày cuối khoảng; tô đậm tháng thuộc khoảng |
| `ns_thang`, `so_sanh_sale` | Tháng đang xem (Tháng) / tháng cuối kỳ đã có dữ liệu (Kỳ) / khung "ngân sách chỉ theo tháng/kỳ" (Khoảng) |
| `hieu_suat_nganh` | `nganh_khoang` so với phép so thứ nhất |
| `tuong_quan` | Doanh thu × số ngày mua **trong khoảng** (`khach_khoang`); màu = trạng thái hôm nay |
| `danh_sach_khach` | Top 60 theo doanh thu trong khoảng, cột so phép so thứ nhất; trạng thái hôm nay |
| `tang_truong`, `bien_loi_nhuan` | Vẫn theo kỳ/quý (bản chất nhiều kỳ); tô đậm kỳ/quý chứa khoảng |
| còn lại (`suc_khoe_khach`, `viec_hom_nay`, `thang_nay_chua_mua`, `han_su_dung`, `cong_no`, `don_hang`) | Hôm nay — không đổi |

### 3.2 Báo cáo (`/bao-cao`) — đợt A

- Mặc định = tháng hiện tại (trước: kỳ hiện tại). Dạng Kỳ = màn hiện có, không đổi số.
- Dạng Tháng/Khoảng: ô tổng (`tong_khoang` + so sánh), biểu đồ chính (theo ngày nếu ≤ 92
  ngày, theo tháng nếu dài hơn — `ngay_khoang` / `thang_khoang`), theo người phụ trách
  (`sale_khoang`), mặt hàng + cây ô (`mat_hang_khoang`), ngành kéo lên/xuống (`nganh_khoang`
  so phép so thứ nhất), Pareto (`tap_trung_khoang`), ngân sách như `ns_thang`. Bản đồ nhiệt
  ngành × tháng = các tháng của kỳ chứa ngày cuối khoảng.
- Bất biến 5b vẫn đúng: mỗi con số so sánh in kèm dải ngày nó so.

### 3.3 Khách hàng — đợt B

- Danh sách: thêm cột doanh thu / lãi gộp / số đơn trong khoảng + cột so; sắp mặc định theo
  doanh thu trong khoảng; chip "có mua trong khoảng". Hạng / trạng thái / phân khúc / cột 12
  tháng giữ. Thêm đúng **một** lượt hỏi (`khach_khoang` cho cả danh bạ, ảnh chụp theo
  khoảng) ghép bằng Python ⇒ ngân sách màn danh sách **≤ 4** (trước: 3).
- Hồ sơ: ô tổng theo khoảng; biểu đồ 12 tháng giữ, tô đậm tháng thuộc khoảng; tab Sản phẩm
  và Đơn hàng mặc định lọc theo khoảng. Nhịp mua / lịch dự kiến / trạng thái giữ.
- Bản đồ: chỉ số doanh thu và "số khách mua" theo khoảng; "cần gọi lại" giữ hôm nay.

### 3.4 Sản phẩm — đợt C

- Danh mục: thêm cột doanh thu / số lượng / số khách trong khoảng (`mat_hang_khoang`) + sắp
  theo chúng; tồn / tốc độ 90 ngày / trạng thái giữ hôm nay.
- Hồ sơ mã: biểu đồ bán theo ngày mặc định = khoảng xem; khách mua mã này trong khoảng.

### 3.5 Không đổi

Kho hàng, Công nợ, Cần liên hệ, Dự báo: bộ chọn hiện MỜ kèm "màn này luôn tính theo hôm
nay" (Công nợ: "theo kỳ sổ mới nhất"). Tham số khoảng vẫn nằm trên URL để quay lại màn doanh
số không mất lựa chọn. Màn hệ thống (Kho dữ liệu, Nhật ký, Cài đặt, Ngân sách, Đăng nhập)
không hiện bộ chọn. Trong lúc đợt B/C chưa xong, màn Khách hàng / Sản phẩm hiện bộ chọn mờ
"màn này chưa theo khoảng xem".

## 4. Giao diện

- **Bộ chọn chung** `<KhoangXem>` (`giao_dien/src/khung/KhoangXem.tsx`) vẽ ở đầu vùng nội
  dung (`main.khung-than`) do `main.tsx` quyết định theo đường dẫn: nút `‹ Tháng 7/2026 ›`,
  nút gạt **Tháng · Kỳ · Khoảng**, ở Khoảng có hai ô ngày + nút nhanh (30 ngày, quý này, từ
  đầu năm), dòng mô tả của máy chủ. Nút tiến khoá ở tháng/kỳ cuối có dữ liệu, nút lùi ở
  đầu. Tháng đầu kho (bắt đầu giữa chừng) có ghi chú "chưa đủ tháng".
- **Dải dữ liệu** cho bộ chọn: `GET /api/pham-vi` (1 lượt hỏi, ảnh chụp `chi_nap`): ngày đầu,
  hôm nay, danh sách kỳ.
- **Trạng thái**: `giao_dien/src/khung/khoang.ts` — `docKhoang(search)`, `useKhoang()`
  (useSyncExternalStore; đổi khoảng = `history.replaceState` + báo cho mọi thành phần, KHÔNG
  tải lại trang), `thamSoKhoang()` để gắn vào mọi lời gọi API doanh số, `giuKhoang(url)` để
  mọi `history.pushState/replaceState` của từng màn (bộ lọc khách, sản phẩm, Báo cáo, Cần
  liên hệ, Kho hàng, Công nợ, Dự báo) không làm rơi tham số khoảng.
- **Liên kết**: một bộ nghe `pointerdown` / `focusin` / `contextmenu` ở `document` (gắn MỘT
  lần trong `main.tsx`) viết lại `href` của mọi `<a href="/…">` nội bộ thành `giuKhoang(href)`
  ngay trước khi người dùng bấm / mở tab mới / chép liên kết. Liên kết đã mang tham số khoảng
  riêng thì giữ nguyên. Trừ `/giao-dien`, `/dang-xuat`, `/kho-du-lieu*`, `/static`.
- Khoá TanStack Query của mọi lời gọi doanh số có kèm `thamSoKhoang()`.

## 5. Tốc độ

- Khoá ảnh chụp = đường dẫn + tham số khoảng **đã chuẩn hoá theo cú pháp** (không hỏi CSDL
  để chuẩn hoá — giữ "trúng ảnh chụp: 1 lượt hỏi"). Không tham số = khoá mặc định; `lam_nong`
  làm nóng đúng các khoá mặc định như hôm nay.
- Việc giải khoảng (cắt dải, so sánh, câu mô tả) chạy TRONG hàm tính của ảnh chụp: +1 lượt
  hỏi (`pham_vi`) khi trượt ảnh chụp.
- Ngân sách lượt hỏi: `/bao-cao` ≤ 11 giữ nguyên (dạng Tháng: phạm vi 1 · tổng + so sánh 1 ·
  chuỗi ngày 1 · mặt hàng 1 · người phụ trách 1 · ngành nay + so 1 · nhiệt 1 · Pareto 1 ·
  ngân sách 3 = 11). Từng khối Tổng quan theo khoảng: ngân sách cũ + 1. Có test đếm.
- Ngưỡng: mỗi khối theo khoảng ≤ 500 ms cho một tháng trên CSDL thật (đo, chỉ SELECT).

## 6. Kiểm

- `tests/test_khoang_xem.py`: đọc/kiểm tham số (400 đúng ca), cắt dải, so sánh tháng (giữa
  tháng, cuối tháng, 31/3 → 28/2 hoặc 29/2, 29/2 → 28/2 năm trước), kỳ (tháng đối chiếu),
  khoảng (liền trước cùng số ngày), `co` khi so vào trước dải dữ liệu, câu mô tả.
- `tests/test_mart_khoang.py`: bốn đẳng thức §2, `ten_nganh` khớp `bao_cao.NGANH_TRONG`,
  ngày không bán có dòng 0, phiếu đỏ không bị lọc.
- API: mọi endpoint doanh số nhận ba dạng, trả `khoang`, khoá ảnh chụp khác nhau theo khoảng;
  test đếm truy vấn cập nhật.
- Giao diện: build lại (`test_ban_build_khop_ma_nguon`); xem thử trên trình duyệt ba dạng,
  đổi màn giữ khoảng, mobile 375 px không tràn ngang.

## 7. Triển khai

Đợt A → B → C, mỗi đợt một nhánh, test đủ, build, merge `--no-ff`. Migration `039` chạy bằng
`postgres` trên CSDL thật TRƯỚC khi push đợt A. Sau mỗi đợt cập nhật `CLAUDE.md` (bảng trang,
bất biến mới "khoảng xem" + "một chỗ hiểu khoảng xem") và `python scripts/sinh_tai_lieu.py`.

## 8. Ghi chú khi làm đợt A (2026-09-24)

- **Thứ tự phép so**: `so_sanh[0]` luôn là **năm trước** (so "chính": nét đứt trên biểu đồ,
  ngành kéo lên/xuống, cây ô); `so_sanh[1]` là tháng trước (dạng Tháng) / khoảng liền trước
  (dạng Khoảng). Dạng Kỳ chỉ có năm trước.
- **Trùng tên tham số**: màn Khách hàng từng dùng `?thang=` cho bộ lọc NHÃN
  (`mart.khach_thang_nay`: `tre`, `da_mua`…). Đổi thành `?nhan_thang=` (URL và
  `/api/khach-hang/ds`) để `?thang=` chỉ còn nghĩa "tháng đang xem"; `khoang.ts::docKhoang`
  chỉ nhận `thang` đúng dạng `YYYY-MM`.
- **Đo thật (CHỈ SELECT, thân hàm 039 chạy như câu thường, 2026-09-24)**: một tháng — phạm vi
  103 ms, tổng + 2 phép so ~125 ms (lần đầu nguội ~2 s), chuỗi ngày 85 ms, mặt hàng 237 ms,
  ngành 35 ms, Pareto 98 ms, tương quan (đọc `khach_360`) ~1,2 s. Khoảng cả năm: tổng + so
  sánh ~4,8 s, mặt hàng ~1,5 s — chỉ lần đầu, sau đó là ảnh chụp.

## 9. Ghi chú khi làm đợt B + C (2026-09-24)

- Ngân sách lượt hỏi thật (ảnh chụp tắt, tính mới): `/api/khach-hang/ds` ≤ 5 (danh bạ 1 + phạm
  vi 1 + doanh số theo khoảng 1 + khung), `/api/ban-do` ≤ 3 (phạm vi + 2 — `BD.ban_do` vẫn đúng
  2), `/api/khach-hang/{mã}/khoang`, `/api/san-pham/khoang`, `/api/san-pham/{mã}/khoang` ≤ 2.
  Trúng ảnh chụp: 1 lượt mỗi ảnh chụp như mọi màn.
- 039 thêm `mart.khach_mat_hang_khoang` và `mart.tinh_khoang` (chưa chạy trên CSDL thật nên
  sửa thẳng 039 thay vì thêm 040).
- Điều hướng bằng JavaScript (dòng bảng khách, ô tìm nhanh, ⌘K, chấm tương quan) bọc
  `giuKhoang()` — bộ viết lại `href` chỉ bắt thẻ `<a>`.
