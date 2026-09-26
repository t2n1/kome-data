# Sản phẩm 360 — trang riêng (thiết kế)

Ngày: 2026-09-26 · Trạng thái: đã duyệt thiết kế trong hội thoại, chờ duyệt đặc tả.

## 1. Mục tiêu

`/san-pham/{mã}` hiện là hồ sơ nằm DƯỚI bảng danh mục (6 khối, một biểu đồ ngày + một biểu đồ
tháng). Chủ DN muốn một **trang riêng giống hồ sơ khách 360**, nhiều biểu đồ và insight hơn, liên
kết qua lại với hồ sơ khách. Trang phải trả lời bốn nhóm câu hỏi:

1. **Ai mua & ở đâu** — tập trung khách, 47 tỉnh, người phụ trách, khách mới / quay lại.
2. **Bán thế nào theo thời gian** — 24 tháng so cùng kỳ, 26 tuần, nhịp mua lại, cỡ đơn.
3. **Giá & lãi** — đơn giá thực bán theo tháng so giá bảng bậc, biên theo tháng, khách giá / biên thấp.
4. **Cơ hội bán thêm** — mua kèm cùng phiếu, khách nên chào, khách đến ngày mua lại.

Ngoài phạm vi: số lượng đề xuất đặt hàng, hàng đang về, mọi con số xác suất / "% khả năng mua".

## 2. Hướng đã chọn

**Tab tải lười, mỗi tab một endpoint.** Mở trang chỉ gọi hồ sơ (≤ 5 lượt) + khoảng (≤ 2 lượt); mỗi
tab gọi endpoint riêng khi được bấm. Chỉ số mới là hàm `mart.*` `LANGUAGE sql STABLE` trong
migration `051`–`053` (một migration mỗi nhóm), đọc `mart.ban_den_moc`.

Đã loại: một endpoint lớn (phá trần 5 lượt, bắt chờ cả khối mua kèm dù không ai mở tab);
materialized view (nút thắt là số lượt hỏi, và MV không quay về theo mốc).

## 3. Cấu trúc trang

- **`/san-pham`** chỉ còn là danh mục. Bấm dòng → điều hướng sang `/san-pham/{mã}` qua
  `giuKhoang()`. Hồ sơ nằm dưới bảng (`HoSoSanPham.tsx`) bị bỏ.
- **`/san-pham/{mã}`** là trang riêng, bố cục theo hồ sơ khách 360 (`khach/HoSo.tsx`):
  - **Thanh trên**: ← Danh mục · ô tìm mã · ‹ n/N ›. Thứ tự lấy theo danh mục đang lọc; không có
    trạng thái lọc thì theo thứ tự mặc định của danh mục.
  - **Đầu trang**: tên, ngành (`mart.ten_nganh`), nhãn trạng thái của `san_pham_360.trang_thai`
    (kèm "bán nốt tồn" khi `ngung_ban`), dòng phụ: mã · lần đầu – lần cuối bán.
  - **Cột trái dính "Việc với mã này"**:
    - tồn + còn đủ bán n ngày (`du_ban_ngay`, theo tuổi) + tốc độ `toc_do_ngay_theo_tuoi`;
    - cảnh báo: sắp thiếu / hết hàng / sắp chuyển lô / không kịp bán trước hạn / chưa rõ tồn;
    - **khách đến ngày mua lại** (tối đa 10);
    - **khách nên chào** (top 5, link "xem hết" mở tab Tồn & bán thêm).
    Mọi tên khách link `/khach-hang/{mã}`.
  - **Cột phải**:
    - 4 ô số: DT trong khoảng xem + so sánh (`/khoang`) · bán/ngày (theo tuổi) · biên lãi gộp 12
      tháng · khách đang mua / đã ngừng;
    - **biểu đồ 24 tháng**: cột DT năm nay, cột mờ cùng tháng năm trước, đường lãi gộp; bấm một
      tháng → mở tab Thời gian với biểu đồ ngày ở tháng đó;
    - **4 tab** (điều khiển bằng hash như khách 360): `#khach` · `#thoi_gian` · `#gia` ·
      `#ban_them`. Mặc định `#khach`.

### 3.1 Nội dung tab

| Tab | Khối |
|---|---|
| Khách hàng | Pareto tập trung khách · lưới 47 tỉnh của mã · theo người phụ trách · khách mới vs quay lại theo tháng · bảng khách mua trong khoảng / đang mua / đã ngừng |
| Thời gian | bán theo ngày (khối hiện có, `/ngay`) · lưới 26 tuần · phân bố nhịp mua lại · cỡ đơn theo quy cách |
| Giá & lãi | đơn giá thực bán theo tháng × quy cách, cạnh giá bảng bậc mới nhất · biên lãi gộp theo tháng · khách giá thấp nhất / biên thấp nhất · bảng giá theo bậc (dời từ hồ sơ cũ) |
| Tồn & bán thêm | tồn theo lô (link `/kho-hang?tim=`) · mua kèm cùng phiếu · khách nên chào đầy đủ |

### 3.2 Liên kết hai chiều

- Mọi tên / mã khách trên trang → `/khach-hang/{mã}`.
- Hồ sơ khách 360 đã link mọi mã hàng sang `/san-pham/{mã}` (`HoSoTab.tsx`, `HoSoViec.tsx`) — nay
  tới trang riêng, không cần sửa đích.
- Các link ngoài (`BaoCao.tsx`, `LienHe.tsx`, `tong_quan/khoi.tsx`) giữ nguyên đường dẫn.

## 4. Định nghĩa chỉ số (migration `051`–`053`)

Mọi hàm đọc `mart.ban_den_moc` (bỏ mã nội bộ 044, quay về theo mốc 040). Cửa sổ mặc định = **12
tháng kết thúc ở mốc** (`sales_date > hom_nay - 365`, cùng cửa sổ `mart.hang_doanh_thu`). "DT thuần"
luôn là `amount - tax_amount` (bẫy #8 — không bao giờ cộng `amount` thô qua hai nguồn). Mỗi khối
in MỘT câu cách tính ngay dưới khối (hằng trong Python, như `khach_thang.CACH_TINH`).

| Khối | Hàm | Định nghĩa | Bất biến giữ |
|---|---|---|---|
| 24 tháng | — | `mart.san_pham_theo_thang` có sẵn | — |
| Tập trung khách | `mart.sp_tap_trung_khach(ma)` | DT thuần 12 tháng gộp theo **khách** (không theo khách × người phụ trách), xếp giảm, luỹ kế % | nếp `mart.tap_trung_khach` |
| 47 tỉnh | `mart.sp_theo_tinh(ma)` | `core.dim_prefecture` **LEFT JOIN** DT thuần + số khách theo tỉnh của bản hiện hành `dim_customer` | đủ 47 ô; bậc 0 = đúng bằng 0, số âm vẫn chia bậc (dùng lại `kome/ban_do.py::_tinh_bac`) |
| Người phụ trách | `mart.sp_theo_nguoi(ma)` | theo `salesperson_code` trên dòng bán; mã ngoài `dim_salesperson` vẫn có dòng, tên "(mã không có trong danh sách phụ trách)" | nếp FULL JOIN ngân sách |
| Mới vs quay lại | `mart.sp_khach_moi_thang(ma)` | 12 tháng; "mới" = tháng đó chứa lần ĐẦU khách mua mã này (tính trên mọi dữ liệu ≤ mốc); còn lại "quay lại" | — |
| Nhịp mua lại | — | phân bố `mart.khach_mat_hang.nhip_ngay` của mã (ĐỌC cột có sẵn); cặp < 3 lần mua đếm riêng "chưa đủ dữ liệu" | một khái niệm một công thức |
| 26 tuần | `mart.sp_theo_tuan(ma)` | SL + DT thuần theo tuần ISO, 26 tuần kết thúc ở tuần chứa mốc, tuần không bán = 0 | — |
| Cỡ đơn | `mart.sp_co_don(ma)` | phân bố SL mỗi dòng bán theo `pack_code` (00 バラ / 02 ケース / khác), 12 tháng; dòng SL âm (赤伝) không lọc — đếm riêng "n dòng trả lại" | luật 赤伝 |
| Đơn giá thực | `mart.sp_don_gia_thang(ma)` | theo tháng × `pack_code`: `Σ DT thuần / Σ quantity` — **tỷ số các tổng**; tháng có `Σ quantity ≤ 0` → NULL | bất biến tỷ suất |
| Biên theo tháng | — | từ `san_pham_theo_thang`: `lai_gop / doanh_thu_thuan`, DT ≤ 0 → NULL | tỷ số các tổng |
| Khách giá / biên thấp | `mart.sp_khach_gia(ma)` | theo khách, 12 tháng, chỉ khách DT thuần > 0 và ≥ 2 lần mua; đơn giá = tỷ số các tổng theo quy cách phổ biến nhất của mã; biên = `Σ LG / Σ DT thuần` | bài học `021` (mẫu số tí hon do 赤伝) |
| Mua kèm | `mart.sp_mua_kem(ma)` | trong các phiếu (`slip_no`) 12 tháng có mã này: mỗi mã khác → số phiếu có cả hai và % trên số phiếu có mã này; bỏ `mart.khong_phai_hang(...)` và `mart.ma_ngung_ban_an`; top 15 | 048 / 049 / 050 |
| Khách đến ngày mua lại | — | `mart.khach_mat_hang` của mã: `trang_thai_cap = 'mua' AND du_kien_lan_toi IS NOT NULL`, `con = du_kien_lan_toi − mốc`, xếp `con` tăng rồi DT giảm, 10 dòng — CÙNG vị từ và thứ tự của `kome/ho_so_khach.py::lich_mua` (khối "Mã đến ngày mua lại" của khách 360), chỉ đảo chiều | so bằng nhãn, không `NOT` (024) |
| Khách nên chào | `mart.sp_khach_nen_chao(ma)` | khách có ≥ 1 cặp `trang_thai_cap = 'mua'` với mã **cùng ngành** (`mart.ten_nganh`), chưa từng có dòng với mã này; xếp theo DT thuần ngành đó 12 tháng; khách `'khong_goi'` tự bị loại vì không có cặp `'mua'`. Mã `la_ngung_ban` → rỗng, màn in "không chào hàng đã ngừng kinh doanh". Ngành "(chưa phân loại)" → rỗng kèm câu nói rõ | 016 / 024 / 050 |

Ghi chú:
- `mart.ban_den_moc` = `f.*` của `core.fact_sales_line` nên đã có `slip_no`, `pack_code`, `qty` (đã kiểm: 044). Số lượng là cột `qty`, cùng cột `san_pham_theo_thang.so_luong` dùng.
  thay view đó bằng bản có cột (giữ nguyên mọi vị từ) — kiểm trước khi viết hàm.
- Hàm nào tham chiếu một view `mart` hơn một lần → CTE `AS MATERIALIZED` ghi tường minh, vị từ
  `product_code` nằm TRONG CTE.
- Không phần trăm xác suất nào.

### 4.1 Khoảng xem và mốc

- 4 ô số: phần DT / SL / khách trong khoảng lấy từ `/api/san-pham/{mã}/khoang` (có sẵn); phần còn
  lại theo mốc.
- Mọi biểu đồ và tab: cửa sổ kết thúc ở **mốc của khoảng xem** (`khoang_xem.dat_moc`), nên xem lùi
  tháng cũ là cả trang quay về. Bảng "khách mua trong khoảng" giữ theo khoảng.
- Nhãn "hôm nay" đổi thành "đến <ngày>" khi đang xem lùi (`useNhanMoc`).

## 5. API và ngân sách lượt hỏi

Tất cả dùng ảnh chụp `chi_nap=True`, khoá = đường dẫn + `ThamSo.khoa()`.

| Endpoint | Tải khi | Trả | Trần |
|---|---|---|---|
| `GET /api/san-pham/{mã}` | mở trang | đầu trang · ô số (phần theo mốc) · 24 tháng · cột trái (tồn theo lô + cảnh báo · khách đến ngày mua lại + khách nên chào top 5 trong MỘT câu UNION) | **≤ 5** |
| `GET /api/san-pham/{mã}/khoang` | mở trang | có sẵn | ≤ 2 |
| `GET /api/san-pham/{mã}/ngay?thang=` | tab Thời gian | có sẵn | 1 |
| `GET /api/san-pham/{mã}/khach` | tab Khách hàng | Pareto · 47 tỉnh · người phụ trách · mới/quay lại · đang mua / đã ngừng | **≤ 3** |
| `GET /api/san-pham/{mã}/thoi-gian` | tab Thời gian | 26 tuần · nhịp mua lại · cỡ đơn | **≤ 2** |
| `GET /api/san-pham/{mã}/gia` | tab Giá & lãi | đơn giá × quy cách · giá bảng bậc · biên theo tháng · khách giá/biên thấp | **≤ 2** |
| `GET /api/san-pham/{mã}/ban-them` | tab Tồn & bán thêm | tồn theo lô · mua kèm · khách nên chào đầy đủ | **≤ 2** |

Route cụ thể (`/khach`, `/gia`…) khai TRƯỚC `/{mã}` hoặc dùng đường dẫn con để không đụng nhau
(nếp `/san-pham/khoang`). Hàm Python ở `kome/san_pham_360.py` (mô-đun mới; `kome/san_pham.py` giữ
danh mục / kho hàng) — khai vào `MAN` của `scripts/sinh_cot_dung.py`.

## 6. Lỗi và trạng thái rỗng

- Mã không có → 404; mã ※終売※ hết tồn → 404 với thông điệp `NGUNG_BAN` hiện có; trang vẽ
  `ThongBao` với lối về danh mục.
- Một tab lỗi → chỉ tab đó hiện lỗi, phần còn lại dùng được.
- Không đủ dữ liệu (nhịp cần ≥ 3 lần mua; chưa có ảnh chụp tồn ≤ mốc; chưa có giá bảng) → câu nói
  rõ, không in 0. `ton` NULL ≠ 0 (bất biến `san_pham_360.ton`).

## 7. Giao diện

- `giao_dien/src/san_pham/ho_so/`: `HoSoMa.tsx` (khung hai cột, thanh trên, tab), `ViecVoiMa.tsx`
  (cột trái), `TabKhach.tsx`, `TabThoiGian.tsx`, `TabGia.tsx`, `TabBanThem.tsx`. Bỏ
  `HoSoSanPham.tsx`; `BanTheoNgay` và `XuHuong` chuyển vào đây.
- Dùng lại `chung/BieuDo.tsx`, `chung/Khoi.tsx`, lưới tỉnh của `khach/BanDo.tsx` (tách thành thành
  phần dùng chung nếu cần — không chép), lớp `.hs2-*` (tách phần bố cục chung ra khỏi `khach.css`
  nếu cần — không chép).
- Mọi `pushState` / điều hướng qua `giuKhoang()`.
- `cd giao_dien && npm run build`, commit `kome/web/spa/`.

## 8. Test (viết trước)

`tests/test_san_pham_360.py`:
- trần lượt hỏi từng endpoint ở §5 (cập nhật `test_ngan_sach_luot_hoi_tung_endpoint`);
- Pareto: một khách hai người phụ trách = MỘT dòng;
- 47 tỉnh đủ kể cả tỉnh không có khách mua mã này; DT âm không rơi vào bậc 0;
- đơn giá là tỷ số các tổng (dữ liệu có dòng 赤伝 mẫu số nhỏ);
- cỡ đơn đếm dòng âm riêng, không lọc;
- mua kèm bỏ phí / POSM / ※終売※ hết tồn;
- "khách đến ngày mua lại" TRÙNG TẬP với vị từ khối tương ứng của hồ sơ khách (cùng cặp);
- khách nên chào: không có khách ※廃業※, không có khách đã mua mã này, rỗng với mã ※終売※;
- mã nội bộ 044 không xuất hiện ở khối nào;
- đẳng thức mốc lùi: mốc D ≡ kho chỉ có dữ liệu bán tới D (nếp `tests/test_moc_lui.py`);
- vỏ React trả được cho `/san-pham/{mã}`; 404 cho mã ※終売※ hết tồn.

Sửa test cũ phụ thuộc `HoSoSanPham` / `test_ho_so_co_du_nam_khoi`. Chạy lại
`scripts/sinh_tai_lieu.py` và `scripts/sinh_cot_dung.py`.

## 9. Tài liệu

- CLAUDE.md: sửa dòng `/san-pham` và `/san-pham/{mã}` trong bảng các trang; thêm mục bất biến ngắn
  cho `051`–`053` (hàm `mart.sp_*`, "khách đến ngày mua lại" dùng chung vị từ với khách 360, "Migration
  051–053 phải chạy TRƯỚC khi triển khai").
