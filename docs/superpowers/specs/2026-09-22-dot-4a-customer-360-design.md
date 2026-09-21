# Đặc tả thiết kế — Đợt 4a: Customer 360

**Ngày:** 2026-09-22
**Công ty:** 株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật
**Phạm vi:** nâng cấp hai trang đã có — `/khach-hang` (danh sách) và `/khach-hang/{mã}` (hồ sơ) — lên đúng thiết kế `Customer 360.dc.html`, trừ những khối không có dữ liệu.
**Trạng thái:** Chờ duyệt
**Tài liệu liên quan:**
- `docs/superpowers/specs/2026-09-16-kome-data-platform-design.md` — **"đặc tả nền"**
- `docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md` §7 — **"lộ trình"**
- `design_handoff_kome/screens/Customer 360.dc.html` — **"gói thiết kế"** (ngoài repo)

---

## 1. Bối cảnh

Lộ trình xếp đợt 4 gồm bốn màn: Customer 360 · Sản phẩm · Kho hàng · Bản đồ. Đếm lại
khối lượng thật thì đó là ~21 khối, 3 trang mới và 1 bảng dữ liệu mới — trong khi đợt 2a
(một trang, 7 khối) đã tốn trọn một kế hoạch 5 task. Chính lộ trình §7 đặt nguyên tắc
*"không đợt nào làm hai việc khó cùng lúc"* và đã tách đợt 2 làm 2a/2b vì lý do này.

**Quyết định: tách đợt 4 làm ba.**

| Đợt | Nội dung | Vì sao đứng riêng được |
|---|---|---|
| **4a** | Customer 360 — nâng cấp hai trang đã có | Không cần dữ liệu mới. Giá trị hằng ngày cao nhất: đây là trang nhân viên mở nhiều nhất sau `/` |
| **4b** | Sản phẩm + Kho hàng | Hai trang mới, cùng nguồn `dim_product` / `fact_inventory_daily` |
| **4c** | Bản đồ khách hàng | Một trang mới + bảng tra 47 tỉnh → toạ độ (dữ liệu tĩnh, không từ OBC) |

Tài liệu này chỉ nói về **4a**.

---

## 2. Ràng buộc kế thừa

**R1–R6** của đặc tả nền §3 nguyên vẹn. Ba cái chi phối mạnh nhất ở đợt này:

- **R1** — không có nhân sự IT → giảm tối đa số thứ có thể hỏng.
- **R2** — bảo trì bằng AI → công nghệ phổ thông, không "ma thuật".
- **R3** — OBC là sổ cái chính thức, dữ liệu OBC **chỉ đọc**.

Cộng thêm, từ `CLAUDE.md` và các đợt trước:

- **Định nghĩa chỉ số CHỈ nằm ở `mart/`.** `kome/khach_hang.py` hiển thị và lọc, không tính.
- Mọi route chỉ đọc đi qua `open_app_conn` (vai trò `kome_app`); chỉ `upload`/
  `kho_du_lieu`/`undo` dùng `open_conn`. Có test duyệt AST canh.
- `kome/web/app.py` không nhập `kome.pipeline`/pandas/calamine ở mức ngoài cùng.
- Mốc thời gian là **ngày bán mới nhất trong kho** (`mart.moc_thoi_gian`), không phải
  `current_date`.
- Trạng thái quan hệ khách hàng so với **nhịp mua riêng của từng khách**, không với một
  ngưỡng chung.
- Lọc theo `salesperson_code` là **mặc định tiện dụng, không phải hàng rào** (đợt 3 §5).
- Không thêm gói, không thêm một dòng JavaScript.

---

## 3. Đo đạc quyết định hình dạng đợt này

Mọi con số dưới đây **đã đo thật** trên CSDL production ngày 2026-09-22, không suy đoán.

### 3.1 Nút thắt là số lượt hỏi, không phải sức tính

| Phép đo | Kết quả |
|---|---|
| `EXPLAIN ANALYZE` của `mart.khach_mat_hang` lọc một khách | **10 ms** (dùng đúng index `fact_sales_line_customer_code_sales_date_idx`) |
| Cùng truy vấn đó, đo từ Python qua pooler | **260 ms** (đã hâm nóng) |
| Một round-trip rỗng (`SELECT 1`) | **47 ms** |
| Bốn truy vấn của trang hồ sơ hiện tại, đã hâm nóng | **~900 ms** |

**Hệ quả cho thiết kế:** CSDL tính nhanh; tiền nằm ở **mỗi lần mở kết nối và mỗi vòng
hỏi–đáp tới Tokyo**. Vì vậy:

- **KHÔNG dùng materialized view.** Nó giải quyết sức tính — thứ không phải vấn đề — và
  đổi lại phải có bước làm mới gắn vào pipeline nạp. Lộ trình §7 dành đợt 6 làm **đợt duy
  nhất động vào pipeline nạp**; kéo việc đó lên đợt 4a là thêm một chế độ hỏng mới
  (view cũ âm thầm) vào đúng trang người ta tin nhất.
- **Mở rộng view sẵn có thay vì thêm view mới.** Mỗi view mới là một vòng hỏi nữa.
- **Bất biến hiệu năng:** trang hồ sơ sau đợt này **không được vượt 8 truy vấn** (hôm nay
  là 6). Có test canh — xem §8.

### 3.2 Ba giả định của gói thiết kế không khớp dữ liệu thật

| Gói thiết kế giả định | Đo được | Quyết định |
|---|---|---|
| Hạng khách là **S·A·B·C·D** (`G_RANK`, `CK_RANK`, `HAN_GIA`) | `rank_code` là mã OBC, **10 nhóm** (`0008`: 605 · `0005`: 402 · `0004`: 246 · `0999`: 143 · …), và **không file xuất nào ta nạp có tên của các mã đó** | Không dùng `rank_code`. Tự xếp hạng theo **doanh thu 12 tháng**, và gọi đúng tên nó là vậy — xem §5.1 |
| **Giá riêng từng khách** | `core.fact_price_list` khoá theo `(product_code, pack_code, price_level)` — **không có `customer_code`**. `mart.khach_360` có `price_level_code` của từng khách | Dựng được, nhưng nó là **bậc giá** của khách chứ không phải giá đàm phán riêng. Tiêu đề khối phải nói đúng điều đó |
| **"Chưa ai phụ trách"** là một nhóm việc đáng có nút riêng | **1 khách** trên 1.710 | **Bỏ nhóm đó.** Một nút lọc ra đúng một khách là một nút chết |

### 3.3 Dữ liệu có đủ cho phần còn lại

| Cần cho | Nguồn | Trạng thái |
|---|---|---|
| Nhóm "Im lặng ≥ 2× nhịp" | `mart.khach_360.ty_le_im_lang` | có sẵn |
| Nhóm "Hạng cao đang tụt" | `mart.khach_theo_thang` | có sẵn |
| Nhóm "Khách mới chưa quay lại" | `mart.khach_360.lan_dau`, `ty_le_im_lang` | có sẵn |
| Tập trung ở đâu | `mart.khach_360.prefecture` | 47 tỉnh, **8 khách không có tỉnh** |
| Tải của từng nhân viên | `core.dim_salesperson` (5 người, đợt 3) | có sẵn |
| Điểm giao thẳng 直送先 | `core.dim_shipto` | 1.832 dòng, **532/1.710 khách có** |
| Bậc giá | `core.fact_price_list` (4.185 dòng) + `khach_360.price_level_code` | có sẵn |

---

## 4. Phạm vi

### 4.1 Trong phạm vi

**Trang danh sách `/khach-hang`** — thêm bốn khối và ba bộ lọc:

1. **Danh sách làm việc** — 4 nhóm bấm được, mỗi nhóm một câu mô tả và số đếm thật.
2. **Phân bố theo hạng** — theo hạng doanh thu tự tính (§5.1).
3. **Tập trung ở đâu** — theo tỉnh.
4. **Tải của từng nhân viên** — số khách và doanh thu mỗi người phụ trách.
5. Bộ lọc thêm: **chip hạng**, **chọn người phụ trách**, **chọn tỉnh** (bộ lọc trạng thái
   và ô tìm đã có).

**Trang hồ sơ `/khach-hang/{mã}`** — thêm bốn khối, nâng cấp hai khối đã có:

6. **Tháng này chưa mua** — mã khách mua đều hai tháng trước mà tháng này chưa thấy.
7. **Gợi ý hàng chưa từng mua** — mã khách chưa từng mua, xếp theo tỷ suất lợi nhuận.
8. **Bậc giá đang áp dụng** — bảng giá theo `price_level_code` của khách.
9. **Điểm giao thẳng 直送先** — danh sách địa chỉ giao thẳng của khách.
10. Nâng **"Mặt hàng đang mua"**: thêm cột **nhịp mua theo từng mã** và **dự kiến lần tới**.
11. Nâng **"Mặt hàng đã ngừng mua"**: thêm cột **trễ bao nhiêu ngày so với nhịp của mã đó**.

**Dữ liệu:** migration `020_mart_khach_360.sql` — mở rộng `mart.khach_mat_hang` (nhịp
theo mã) và thêm các view cho bốn khối phân tích.

### 4.2 Cắt khỏi phạm vi, và vì sao

| Khối trong gói thiết kế | Vì sao cắt |
|---|---|
| **Hoá đơn chưa thanh toán** | Cần `得意先元帳`. Nhóm B — **đợt 6** mới viết bộ nạp |
| **Nhật ký tiếp xúc** | Nhập tay hoàn toàn. Nhóm C — **đợt 7** |
| **Nhóm việc "Nợ quá hạn"** | Cùng nguồn với trên — **đợt 6** |
| **Hình ảnh cửa hàng** | Không có nguồn ảnh ở bất kỳ đâu. Cắt hẳn |
| **Chat Facebook** | Không có tích hợp Messenger. Cắt hẳn |
| **Nhóm việc "Chưa ai phụ trách"** | 1 khách — xem §3.2 |

**Dựng khung rỗng có chú thích "sẽ có ở đợt 6" là phương án đã cân nhắc và bỏ.** Một
trang bắt người ta cuộn qua bốn ô trống mỗi ngày dạy họ cuộn nhanh — và ô thật nằm giữa
những ô trống đó sẽ bị cuộn qua theo.

### 4.3 Không đụng tới

`kome/pipeline.py`, 5 cổng kiểm tra, `kome/coverage.py`, `kome/nhat_ky_nap.py`,
`kome/tuoi_du_lieu.py`, `kome/web/bao_mat.py`, `kome/web/nguoi_dung.py`, màn Kho dữ liệu.
**`/can-xu-ly` giữ nguyên** — xem §5.4.

---

## 5. Quyết định đã chốt

### 5.1 Hạng khách: tự tính theo doanh thu, và nói thẳng ra là vậy

`rank_code` của OBC có 10 nhóm và không có tên ở đâu. Hiển thị "0008: 605 khách" không
nói gì với người đọc.

**Quyết định:** một chỉ số mới `hang_doanh_thu` trong `mart`, xếp khách theo doanh thu
thuần 12 tháng gần nhất thành năm bậc **S · A · B · C · D** theo phân vị:

| Hạng | Định nghĩa |
|---|---|
| S | 5% khách có doanh thu cao nhất |
| A | 15% tiếp theo |
| B | 30% tiếp theo |
| C | 30% tiếp theo |
| D | 20% còn lại, gồm cả khách doanh thu 0 |

Năm bậc và tên chữ cái lấy từ gói thiết kế; **cách chia là của ta**, vì OBC không cho.

**Bất biến:** nhãn trên trang phải đọc là **"hạng theo doanh thu 12 tháng"**, không phải
"hạng" trơ trọi. Gọi tắt là "hạng" thì sáu tháng nữa có người sẽ đối chiếu nó với
得意先ランク trong OBC và thấy lệch, rồi không biết cái nào đúng. Cả hai đều đúng — chúng
trả lời hai câu khác nhau.

### 5.2 Nhịp mua theo từng mã hàng nằm trong `mart.khach_mat_hang`, không phải view mới

Ba khối cần nó: "Mặt hàng đang mua" (dự kiến lần tới), "Mặt hàng đã ngừng mua" (trễ bao
nhiêu), và "Tháng này chưa mua".

View `mart.khach_mat_hang` hiện đã gom theo `(customer_code, product_code)` và đã sắp
theo `sales_date` — thêm trung vị khoảng cách là **cùng một lượt quét**, không thêm chi
phí đáng kể. Tách ra view riêng thì ba khối đó thành ba vòng hỏi nữa (§3.1).

**Cách tính giống hệt `mart.nhip_mua` đang dùng cho toàn khách** — trung vị khoảng cách
giữa các lần mua liên tiếp. Dùng lại đúng công thức đó, không phát minh công thức thứ hai
cho cùng một khái niệm.

**Mã mua dưới 3 lần thì nhịp là NULL**, và trang phải hiện `—` chứ không hiện một con số.
Hai điểm dữ liệu cho ra một "nhịp" nghe như sự thật nhưng là tiếng ồn.

### 5.3 "Gợi ý hàng chưa từng mua" xếp theo tỷ suất, không theo thuật toán nào khác

Gói thiết kế xếp theo tỷ suất lợi nhuận và lấy 8 mã đầu. Giữ nguyên.

Không làm lọc cộng tác, không "khách giống bạn cũng mua". Với 232 mã hàng và 2.080 khách,
một danh sách "mã ta lãi nhiều mà khách này chưa từng mua" là thứ nhân viên bán hàng dùng
được ngay; một mô hình gợi ý là thứ không ai kiểm chứng được và sẽ không ai tin.

### 5.4 `/can-xu-ly` giữ nguyên tới đợt 7

Nhóm việc "Im lặng ≥ 2× nhịp" trùng việc của `/can-xu-ly`. Lộ trình §4.1 đã quyết: route
cũ giữ tới khi đợt 7 dựng trang "danh sách ưu tiên liên hệ" riêng, rồi mới bỏ.

**Chấp nhận hai nhà trong một thời gian.** Đổi lại là không đụng vào trang người ta đang
mở hằng ngày, giữa lúc đợt 3 vừa đổi cổng đăng nhập của chính nó.

**Bất biến:** hai chỗ phải đọc cùng một định nghĩa từ `mart` — không được để `/can-xu-ly`
dùng `trang_thai` còn nhóm việc dùng một ngưỡng viết tay. Có test canh: hai đường phải trả
về **cùng một tập mã khách**.

### 5.5 Bốn nhóm việc, không phải sáu

| Nhóm | Định nghĩa |
|---|---|
| Toàn bộ danh bạ | không lọc |
| Im lặng ≥ 2× nhịp | `ty_le_im_lang >= 2` |
| Hạng S·A đang tụt | hạng S hoặc A, doanh thu **30 ngày gần nhất** < 80% trung bình của **ba kỳ 30 ngày** liền trước |
| Khách mới chưa quay lại | `lan_dau` trong 90 ngày gần nhất **và** `ty_le_im_lang >= 1.2` |

Khách OBC đã đánh dấu `※廃業※` / `※取引停止※` **không** vào nhóm nào ngoài "Toàn bộ" —
cùng bất biến với `/can-xu-ly` (migration `016`).

---

## 6. Kiến trúc

### 6.1 Migration `020_mart_khach_360.sql`

Chạy bằng vai trò **`postgres`**, như mọi migration.

Bốn thay đổi, tất cả trong schema `mart`:

1. `CREATE OR REPLACE VIEW mart.khach_mat_hang` — thêm ba cột: `nhip_ngay` (trung vị
   khoảng cách giữa các lần mua mã đó), `du_kien_lan_toi` (`lan_cuoi + nhip_ngay`),
   `tre_ngay` (`moc_thoi_gian.hom_nay - du_kien_lan_toi`, chỉ dương mới có nghĩa).
2. `CREATE VIEW mart.hang_doanh_thu` — `(customer_code, hang)` theo §5.1.
3. `CREATE VIEW mart.khach_nhom_viec` — `(customer_code, nhom)` cho bốn nhóm §5.5.
   Một khách có thể thuộc nhiều nhóm.
4. `CREATE VIEW mart.tai_nhan_vien` — `(salesperson_code, ten, so_khach, doanh_thu,
   so_khach_canh_bao)`.

**Không `CREATE MATERIALIZED VIEW`** — xem §3.1.

### 6.2 Tầng Python

`kome/khach_hang.py` nhận thêm tham số lọc và ba hàm đọc mới. Vẫn **không tính chỉ số
nào** — mọi công thức ở `mart`.

- `danh_sach(..., nhom=None, hang=None, tinh=None)` — ba bộ lọc mới, cùng nếp `sale`.
- `tong_quan_danh_ba(conn, sale=None) -> TongQuan` — **một** truy vấn trả về cả bốn khối
  phân tích (nhóm việc + phân bố hạng + theo tỉnh + tải nhân viên) bằng `UNION ALL`, để
  bốn khối không thành bốn vòng hỏi.
- `ho_so(conn, ma)` — trả thêm `chua_mua_thang`, `goi_y`, `bac_gia`, `diem_giao`.

**Bất biến:** `ho_so` đã có 6 truy vấn; sau đợt này **không quá 8**. Bốn khối mới gộp vào
hai truy vấn.

### 6.3 Tầng giao diện

Không template mới. Sửa `khach_hang.html` (thêm 4 khối + 3 bộ lọc) và `khach_360.html`
(thêm 4 khối + 2 cột).

Biểu đồ vẽ bằng **SVG tự tính toạ độ**, đúng nếp `kome/bao_cao.py::ve_bieu_do` và
`kome/khach_hang.py::ve_duong` đã có. Không thêm thư viện chart.

Màu và khoảng cách lấy từ `kome/web/static/kome.css` (đợt 1) — gói thiết kế dùng cùng bộ
token, nên không cần thêm biến CSS mới.

---

## 7. Rủi ro & giả định

| # | Vấn đề | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| R1 | `hang_doanh_thu` là chỉ số **ta tự đặt ra**, chủ DN chưa duyệt | Trung bình | §5.1 buộc nhãn nói rõ "theo doanh thu 12 tháng". Đổi cách chia là sửa một view |
| R2 | Trang hồ sơ vốn đã ~900 ms; thêm 2 truy vấn nữa | Trung bình | §6.2 giới hạn 8 truy vấn, có test đếm. Nếu vượt thì gộp tiếp, không nới trần |
| R3 | 8 khách không có tỉnh → khối "Tập trung ở đâu" thiếu họ | Thấp | Hiện một dòng "không rõ tỉnh: 8" thay vì bỏ im lặng |
| R4 | Chỉ 532/1.710 khách có 直送先 | Thấp | Khối tự ẩn khi khách không có, không hiện bảng rỗng |
| R5 | So doanh thu "tháng này" với tháng trước là so một tháng **dở dang** với một tháng đủ — khách nào cũng trông như đang tụt vào ngày mùng 3 | Trung bình | Dùng **cửa sổ trượt 30 ngày** tính từ `mart.moc_thoi_gian.hom_nay`, so với ba cửa sổ 30 ngày liền trước. Mọi kỳ đều dài bằng nhau nên không có kỳ nào dở dang |
| R6 | Nhịp theo mã làm `khach_mat_hang` nặng thêm | Thấp | Đã đo: view hiện tại 10 ms CSDL. Thêm một hàm cửa sổ trong cùng lượt quét. Task 1 đo lại |

---

## 8. Kiểm thử

| Test | Chặn thảm hoạ gì |
|---|---|
| Nhịp theo mã của khách mua < 3 lần là NULL | Bịa một con số từ hai điểm dữ liệu |
| Nhịp theo mã dùng **cùng công thức** `mart.nhip_mua` (trung vị) | Hai định nghĩa cho cùng một khái niệm |
| Nhóm "Im lặng ≥ 2× nhịp" và `/can-xu-ly` trả **cùng tập mã khách** | Hai trang nói hai điều về cùng một câu hỏi |
| Khách `※廃業※` không lọt vào nhóm việc nào ngoài "Toàn bộ" | Gọi lại một doanh nghiệp đã phá sản |
| `hang_doanh_thu` phủ **đúng 100%** khách, không trùng bậc | Khách biến mất khỏi mọi bộ lọc hạng |
| Ba bộ lọc mới kết hợp được với nhau và với `sale`/`tim`/`loc` | Bấm hai bộ lọc thì một cái im lặng bị bỏ |
| `ho_so()` chạy **không quá 8 truy vấn** | Trang hồ sơ chậm dần từng đợt cho tới lúc không ai mở |
| Bốn khối phân tích chạy trong **một** truy vấn | Bốn vòng Tokyo cho một lần mở trang |
| Khách không có 直送先 → khối tự ẩn, không hiện bảng rỗng | Ô trống dạy người ta cuộn nhanh |
| "Gợi ý" không bao giờ chứa mã khách **đã** mua | Gợi ý bán thứ họ vừa mua tuần trước |
| Trang danh sách vẫn mặc định lọc theo sale (đợt 3) sau khi thêm bộ lọc mới | Bất biến của đợt trước bị đợt sau vô hiệu hoá |

---

## 9. Tiêu chí hoàn thành

- [ ] `/khach-hang` có 4 nhóm việc bấm được, số đếm khớp danh sách hiện ra
- [ ] `/khach-hang` có 3 khối phân tích, lấy trong **một** truy vấn
- [ ] Ba bộ lọc mới (hạng · người phụ trách · tỉnh) kết hợp được với nhau và giữ qua phân trang
- [ ] `/khach-hang/{mã}` có 4 khối mới; hai khối cũ có thêm cột nhịp/trễ
- [ ] `ho_so()` không quá 8 truy vấn (có test đếm)
- [ ] Nhóm "Im lặng" và `/can-xu-ly` trả cùng một tập khách (có test)
- [ ] Nhãn hạng đọc là "hạng theo doanh thu 12 tháng" ở mọi chỗ nó xuất hiện
- [ ] `CLAUDE.md` ghi chỉ số mới và bất biến 8-truy-vấn; `runbook.md` không cần đổi
- [ ] `pytest -v` xanh toàn bộ
- [ ] Mở `/khach-hang` và một hồ sơ khách thật, **xem bằng mắt**: không ô trống, không số lệch
- [ ] **KIỂM TAY (chỉ chủ sở hữu, sau khi chạy `python db/migrate.py` lên production —
      xem `docs/runbook.md`):** migration 020 mới chạy trên CSDL thử nghiệm (gần như
      rỗng), nên chi phí thật của `mart.khach_mat_hang` sau khi thêm nhịp theo mã CHƯA
      đo được. Chạy lệnh dưới đây **hai lần liên tiếp** và lấy con số LẦN THỨ HAI (lần
      đầu là cache lạnh — đã đo trên view cũ: 272 ms lần đầu rồi 7 ms các lần sau).
      Ngưỡng: dưới **100 ms** ở lần thứ hai. Vượt thì báo lại, đừng tự tối ưu.

      ```bash
      python -u -c "import os;from kome.db import connect;from kome.env import nap_env;nap_env(bat_buoc=False);c=connect(os.environ['DATABASE_URL']);[print([r[0] for r in c.execute('EXPLAIN (ANALYZE, TIMING OFF) SELECT * FROM mart.khach_mat_hang WHERE customer_code=%s',('000000009292',)).fetchall()][-1]) for _ in range(2)]"
      ```

---

## 10. Bước tiếp theo

1. Lập kế hoạch triển khai (writing-plans)
2. Thực thi, kiểm chứng bằng mắt, merge
3. Đợt 4b: Sản phẩm + Kho hàng
