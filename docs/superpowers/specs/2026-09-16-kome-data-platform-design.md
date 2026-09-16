# Đặc tả thiết kế — Nền dữ liệu & Báo cáo KOME

**Ngày:** 2026-09-16
**Công ty:** 株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật
**Phạm vi tài liệu:** Giai đoạn 0 (nền dữ liệu) + Giai đoạn 1 (báo cáo)
**Trạng thái:** Chờ duyệt

---

## 1. Bối cảnh

Công ty dùng phần mềm kế toán **OBC 奉行** làm sổ cái chính thức. Dữ liệu được xuất ra Excel và lưu thủ công, nhưng chưa có công cụ nào để phân tích. Song song, hai ứng dụng web đặt hàng đang chạy trên hai kho dữ liệu riêng biệt, không đồng bộ với nhau và không đồng bộ với OBC.

### 1.1 Quy mô thực tế (đo từ dữ liệu quý 2026-05 → 2026-07)

| Chỉ số | Giá trị |
|---|---:|
| Doanh thu quý | ¥390.126.850 |
| Lãi gộp quý | ¥114.315.334 (29,3%) |
| Doanh thu ngày (trung bình) | ¥6.095.732 |
| Số dòng bán/ngày | ~843 |
| Khách trong danh bạ | 2.080 |
| Khách có phát sinh trong quý | 1.198 |
| Mã hàng | 231 |
| Nhà cung cấp | 49 |
| Điểm giao thẳng (直送先) | 1.832 |

Quy mô năm ước tính **¥1,5–1,6 tỷ**.

### 1.2 Diễn biến đáng chú ý

| Tháng | Doanh thu | Lãi gộp | Tỷ suất |
|---|---:|---:|---:|
| 2026-05 | ¥93.429.081 | ¥30.994.135 | 33,2% |
| 2026-06 | ¥112.181.513 | ¥34.498.365 | 30,8% |
| 2026-07 | ¥184.516.256 | ¥48.822.834 | 26,5% |

Doanh thu tháng 7 gần gấp đôi tháng 5 nhưng **tỷ suất lãi gộp giảm 6,7 điểm**. Hiện không ai trong công ty giải thích được nguyên nhân. Đây là một trong những câu hỏi Giai đoạn 1 phải trả lời.

### 1.3 Cơ cấu khách hàng

**Theo hạng (ランク) — lợi nhuận tập trung cực mạnh:**

| Hạng | Số khách |
|---|---:|
| S (lãi gộp năm ≥ 5.000.000) | 4 |
| A (≥ 1.000.000) | 76 |
| B (≥ 500.000) | 114 |
| C (≥ 200.000) | 246 |
| D (< 200.000) | 484 |
| ZZZ / cấm gọi điện | 630 |
| Z / mất tích dài hạn | 164 |
| ZZ / không rõ liên lạc | 70 |
| Đối tượng loại trừ | 285 |

**80 khách hạng S+A tạo ra phần lớn lợi nhuận.**

**Theo ngành (業種・カテゴリー):** 577 tạp hoá VN · 269 quán ăn VN · 137 tạp hoá không phải VN · 105 pháp nhân chủ VN · 33 siêu thị · 29 pháp nhân Nhật · 895 chưa phân loại.

**Theo tỉnh:** Tokyo 290 · Osaka 241 · Saitama 191 · Aichi 168 · Chiba 126 · Kanagawa 112 · Hyogo 101 · Fukuoka 95 · Gunma 88 · Ibaraki 83 (48 tỉnh).

**Theo người phụ trách (売上主担当者):**

| Nhân viên | Số khách |
|---|---:|
| TRAN THI LAN THANH | 1.119 |
| HA HUY LONG | 473 |
| TRINH CONG MINH | 350 |
| NGUYEN PHUONG DUNG | 108 |
| 西村 巧 | 23 |

Một người đang giữ **54%** danh sách khách hàng.

**Theo trạng thái app đặt hàng (注文アプリ):**

| Trạng thái | Số khách |
|---|---:|
| Đã mở → đang dùng | 258 |
| Đã mở → **không dùng** | 855 |
| Đã mở → đang cân nhắc | 46 |
| Chưa mở | 2 |
| Chưa phân loại | 919 |

**855 khách đã được mở app rồi từ chối dùng.** Đây là tín hiệu kinh doanh quan trọng nhất phát hiện được trong khảo sát.

---

## 2. Hiện trạng kỹ thuật

### 2.1 Dữ liệu xuất từ OBC

Thư mục hiện tại: `OneDrive - 株式会社KOME/Desktop/データバックアップ` (**ổ OneDrive cá nhân** — rủi ro, xem §10.2).

**Xuất hằng tháng** (`1．毎月/`):

| File | Kích thước | Ghi chú |
|---|---|---|
| `得意先全情報` | 2.080 dòng × **317 cột** | Chứa đủ thuộc tính CRM |
| `商品データ` | 231 dòng × 194 cột | |
| `直送先` | 1.832 dòng × 29 cột | |
| `取引単価データ` | 395 dòng × 44 cột | 10 mức giá + giá vốn |
| `仕入先` | 49 dòng × 2 cột | |

**Xuất hằng quý** (`２．３か月ごと/`):

| File | Kích thước |
|---|---|
| `売上伝票データ` | 92.825 dòng × **271 cột** (~100 MB/quý) |
| `売上明細表` | 53.948 dòng × 66 cột (~16 MB/quý) |
| `入金伝票データ` | 525 dòng × 40 cột (chỉ 1 quý) |
| `得意先元帳` / `請求先元帳` | ~24.000 / ~20.000 dòng (chỉ 1 quý) |

Ngoài ra: **5.589 file PDF hoá đơn** + 13 file zip. Tên file PDF đã mã hoá sẵn `請求書_伝票No_得意先コード_得意先名_thời gian` → lập chỉ mục được **mà không cần đọc nội dung PDF**.

### 2.2 Vấn đề chất lượng dữ liệu đã phát hiện

1. **Xuất không nhất quán.** `得意先全情報` có số dòng 1.938 → **201** → 2.081 → 2.105 qua 4 tháng. Bản tháng 7 chỉ 201 dòng là **xuất một phần**. Bản tháng 9 chỉ có **5 cột** thay vì 317 (dùng sai mẫu xuất).
2. **File báo cáo có 5 dòng tiêu đề rác** trước dòng tiêu đề thật (`売上明細表`, `得意先元帳`).
3. **Thư mục `VOID`** chứa bản trùng kỳ với thư mục chính.
4. **Kỳ dữ liệu lệch và thiếu.** `売上伝票データ` bắt đầu 2025-03, `売上明細表` bắt đầu 2025-02.
5. **Dữ liệu công nợ chỉ có 1 quý.** Muốn phân tích tuổi nợ theo thời gian phải xuất bổ sung từ OBC.

### 2.2.1 Ràng buộc vĩnh viễn về phạm vi dữ liệu

> **Dữ liệu bán hàng bắt đầu từ 2025-03-03. Trước mốc đó KHÔNG TỒN TẠI** — công ty không còn
> lưu. Đây là ràng buộc vĩnh viễn, không phải thiếu tạm. Đừng đi tìm.

**Kỳ kế toán của công ty là 1/8 → 31/7** (xem `db/migrations/012_ky_ke_toan_cong_ty.sql`),
nên phạm vi trên có nghĩa:

| So sánh | Khả thi |
|---|---|
| Tháng 3–7, năm 2025 so 2026 | ✅ 5 tháng gối nhau |
| Tháng 8–2, so cùng kỳ năm trước | ❌ không có năm trước |
| Trọn kỳ 2025 (8/2024–7/2025) so kỳ 2026 | ❌ kỳ 2025 chỉ có 5/12 tháng |
| Trọn kỳ 2026 so trọn kỳ 2027 | ⏳ từ tháng 8/2027 |

**Hệ quả bắt buộc cho thiết kế báo cáo:** mọi chỉ số "so với cùng kỳ năm trước" phải hiển thị
rõ **"không có dữ liệu cùng kỳ"** khi rơi vào tháng 8–2, chứ không được để trống hoặc hiện 0 —
số 0 ở đó sẽ bị đọc thành "năm ngoái không bán được gì".

### 2.3 Hai ứng dụng web đang chạy

| | Website lên đơn (nhân viên) | Web app đặt hàng (khách) |
|---|---|---|
| Địa chỉ | `xuanloc-blip.github.io/kome-order/` | `sale1.komejapan.com` |
| Công nghệ | 1 file HTML 235 KB, JS thuần | React + Vite |
| Nơi chạy | GitHub Pages | Vultr (Ubuntu 24.04) sau Cloudflare |
| **Backend** | Google Apps Script `…wszMofAslML69…` | Google Apps Script `…xcKCZEXMgD7ks…` |
| Ảnh sản phẩm | Google Drive | Unsplash / WordPress |

**Nguyên nhân gốc rễ của việc dữ liệu không đồng nhất: hai app gọi hai Apps Script khác nhau → hai Google Sheet khác nhau, và không cái nào nối với OBC.**

Hai Sheet hiện chứa **danh mục sản phẩm + ảnh + giá** và **danh sách khách hàng**. Chúng **không** chứa lịch sử đơn hàng → không có dữ liệu quý nào bị mắc kẹt, **rủi ro di trú gần bằng không**.

Đơn đặt từ cả hai web **đã tự động chảy vào OBC qua pipeline Python → CSV** do công ty tự xây.

> **Cần xác nhận:** nếu Sheet không giữ đơn, đơn đi thẳng từ Apps Script sang pipeline Python theo đường nào? Cần biết để nối bảng `app_order` ở giai đoạn sau.

**Cảnh báo về nền tảng hiện tại:** Google Apps Script giới hạn 6 phút mỗi lần chạy và có hạn ngạch gọi; Google Sheets chậm dần từ vài chục nghìn dòng. Với ~843 dòng/ngày trong 5 năm, nền tảng này **sẽ không trụ được**.

### 2.4 Hạ tầng Vultr hiện có

Ba VPS tự quản (**không có Managed Database**), tất cả ở **Tokyo**:

| Máy | Hệ điều hành | Tạo lúc | Vai trò |
|---|---|---|---|
| `Kome-Japan-Server` `167.179.64.245` | Custom Installed | 2022-10 | Máy chính |
| `Sales (DISC)` `139.180.206.125` | OpenLiteSpeed **WordPress** | 2024-01 | Website |
| `sale1.komejapan.com` `207.148.107.222` | Ubuntu 24.04 LTS | 2025-10 | App đặt hàng cho khách |

---

## 3. Ràng buộc

| # | Ràng buộc | Hệ quả thiết kế |
|---|---|---|
| R1 | **Công ty không có nhân sự IT** | Hỏng phải thấy ngay, sửa được bằng tay; giảm tối đa số thứ có thể hỏng |
| R2 | **Bảo trì bằng AI**, chủ sở hữu là 1 người | Công nghệ phổ thông, schema tường minh, không "ma thuật", mọi logic nằm trong file đọc được và lưu git |
| R3 | **OBC là sổ cái kế toán chính thức** | Dữ liệu OBC **chỉ đọc**; đơn từ app phải quay về OBC |
| R4 | Xuất dữ liệu **thủ công**, hằng ngày sau 13:30 | Không phụ thuộc máy nào bật 24/7 |
| R5 | Vòng đời **5 năm** | Không khoá chân nhà cung cấp; lưu được lịch sử thay đổi |
| R6 | Ngân sách nhỏ | Bắt đầu bằng gói miễn phí, nâng khi chạy thật |

---

## 4. Phạm vi

### 4.1 Toàn cảnh — 4 sản phẩm

Yêu cầu ban đầu gồm 5 hạng mục. Sau khi làm rõ "website bán hàng" là **B2B phục vụ chính khách sỉ hiện tại**, nó gộp với "web app đặt hàng" thành một sản phẩm. "Thông tin thị trường đối thủ" thực chất chỉ là vài bảng nhập tay → gộp vào CRM.

| Giai đoạn | Hạng mục | Trạng thái |
|---|---|---|
| **0** | Nền dữ liệu: Postgres + trang nạp file + kiểm tra sức khoẻ | **Trong phạm vi tài liệu này** |
| **1** | Báo cáo + đồng bộ ngược 2 Google Sheet | **Trong phạm vi tài liệu này** |
| 2 | CRM nội bộ (gồm bảng thông tin đối thủ) | Ngoài phạm vi |
| 3 | Xây lại 2 web đặt hàng trên nền chung | Ngoài phạm vi |

**Một công ty không có IT không thể sở hữu nhiều sản phẩm phần mềm cùng lúc.** Mỗi giai đoạn phải chạy ổn định trước khi bắt đầu giai đoạn sau.

### 4.2 Trong phạm vi

- Kho dữ liệu PostgreSQL với mô hình 3 lớp
- Trang web nội bộ để kéo–thả file Excel, có 5 cổng kiểm tra
- Trang kiểm tra sức khoẻ dữ liệu
- Đồng bộ ngược master data ra 2 Google Sheet
- Hai báo cáo tự build: **① Tổng quan kinh doanh**, **② Khách rời bỏ (có nút hành động)**
- Sao lưu 3 lớp + quy trình khôi phục
- Tài liệu ngữ cảnh cho AI

### 4.3 Ngoài phạm vi

CRM nhập liệu; xây lại hai web app; lập chỉ mục PDF hoá đơn; phân tích công nợ theo thời gian (thiếu dữ liệu lịch sử); ba báo cáo còn lại (sản phẩm/giá, người bán, hiệu quả app) — làm sau khi hai báo cáo đầu chứng minh có người dùng.

---

## 5. Kiến trúc tổng thể

```
OBC 奉行  ──xuất tay 13:30──►  3 file Excel (cột cố định)
                                      │  kéo–thả vào trang nội bộ
                                      ▼
                        [ Ingest: 5 cổng kiểm tra → chuẩn hoá → upsert ]
                                      ▼
                    ┌──── PostgreSQL (nguồn sự thật duy nhất) ────┐
                    │                                              │
              Báo cáo tự build                        Đồng bộ ra 2 Google Sheet
              (trong web app)                         (hợp nhất 2 app đang chạy)
```

File Excel gốc được lưu trữ làm **lớp `raw`** — xem §6.1.

---

## 6. Mô hình dữ liệu

### 6.1 Ba lớp

| Lớp | Nơi lưu | Mục đích |
|---|---|---|
| `raw` | **File Excel gốc**, do trang nạp tự lưu trữ (không phải bảng CSDL) | Dựng lại toàn bộ từ số 0 bất cứ lúc nào |
| `core` | Bảng Postgres đã chuẩn hoá | Nguồn sự thật |
| `mart` | Bảng/view tổng hợp sẵn | Báo cáo chạy nhanh |
| `app` | Bảng do ứng dụng ghi | Dữ liệu OBC không có |

**Vì sao `raw` là file chứ không phải bảng:** lưu 271 cột dạng text vào Postgres tốn **~400–700 MB/năm**, làm nổ cả gói miễn phí lẫn gói trả tiền. Giữ file gốc đạt đúng mục đích với chi phí gần bằng 0. CSDL chỉ giữ một bảng nhật ký nhỏ: *file nào, mã băm gì, nạp lúc nào, ra bao nhiêu dòng*.

**Ai lưu trữ file:** chính trang nạp tự lưu mỗi file được kéo–thả vào, đặt tên theo `loại_ngày_mãbăm.xlsx`. Không phụ thuộc vào việc con người có nhớ chép file vào đúng thư mục hay không. Bản trong OneDrive vẫn giữ nguyên như lớp dự phòng thứ hai.

### 6.2 Lớp `core`

**Bảng chiều:**

| Bảng | Nguồn | Ghi chú |
|---|---|---|
| `dim_customer` | `得意先全情報` | **SCD2 — có lịch sử** |
| `dim_product` | `商品データ` | Lịch sử nhẹ |
| `dim_salesperson` | tách từ đơn bán | **Chỉ 5 `担当者` của OBC** — không gồm người nhập đơn, xem §12.1 |
| `dim_shipto` | `直送先` | 1.833 điểm |
| `dim_supplier` | `仕入先` | 50 NCC |
| `dim_warehouse` | `在庫一覧` | 2 kho — xem §6.7 |
| `dim_date` | tự sinh | Có 年度 Nhật (4月→3月), tuần, ngày lễ |

**Bảng sự kiện:**

| Bảng | Độ hạt | Ước tính 5 năm |
|---|---|---:|
| `fact_sales_line` | 1 dòng = 1 明細 của 1 伝票 | ~1.080.000 dòng |
| `fact_inventory_daily` | 1 sản phẩm × **1 kho** × 1 ngày | ~230.000 dòng |
| `fact_payment` | 1 明細 phiếu thu | ~50.000 dòng |
| `fact_price_list` | 1 sản phẩm × quy cách × mức giá | ~2.000 dòng, có lịch sử |

Tổng ước tính **~600 MB sau 5 năm** (không tính `raw`).

### 6.3 Nguồn cho dữ liệu bán hàng hằng ngày

Dùng mẫu **`売上伝票データ`** (271 cột), không dùng `売上明細表`.

Lý do: nó là tập cha — chứa đủ `金額`, `原価`, `粗利益`, `粗利益率`, `消費税額`, **và thêm `入金額１` / `入金伝票No.１` cho phép nối đơn bán với phiếu thu ngay trong một bảng**, cùng toàn bộ thuộc tính khách hàng (`業種`, `ランク`, `注文アプリ`, `請求締日`, `請求先`). Với ~843 dòng/ngày thì 271 cột không tốn kém gì.

Chỉ giữ khoảng 40 cột cần dùng vào `core`; phần còn lại vẫn truy lại được từ file gốc.

### 6.4 Lịch sử khách hàng (SCD2)

Vì xuất snapshot khách hàng **mỗi ngày**, lưu được lịch sử thay đổi gần như miễn phí:

```
customer_code  valid_from   valid_to     rank  注文アプリ         担当者
0000009292     2025-04-01   2026-02-14   B     解放済→利用しない   LAN THANH
0000009292     2026-02-15   2026-08-31   A     解放済→利用中      LAN THANH
0000009292     2026-09-01   (hiện tại)   S     解放済→利用中      HA HUY LONG
```

Trả lời được những câu hỏi hôm nay **không thể** trả lời:

- Khách sau khi bắt đầu dùng app đặt hàng thì doanh số tăng hay giảm? *(258 đang dùng vs 855 đã bỏ)*
- Đổi người phụ trách thì khách tăng trưởng hay tụt?
- Khách tụt từ hạng A xuống C mất bao lâu, có dấu hiệu báo trước không?

**Chỉ so sánh trên tập cột có ý nghĩa nghiệp vụ.** So sánh toàn bộ 317 cột sẽ sinh 2.080 dòng mới mỗi ngày nếu có bất kỳ trường nào tự đổi.

### 6.5 Sáu luật bất biến

1. **Không bao giờ sửa dữ liệu OBC.** Sai thì sửa trong OBC rồi xuất lại.
2. **Nạp lại cùng file phải ra cùng kết quả.** Khoá tự nhiên: `伝票No. + số dòng`.
3. **Tiền luôn là số nguyên yên.** Không dùng số thực cho tiền; chỉ tỷ suất mới dùng thập phân.
4. **Mỗi chỉ số chỉ định nghĩa một lần, trong `mart/`.**
5. **Không xoá dòng trong bảng SCD2** — chỉ đóng `valid_to`.
6. **Cổng kiểm tra 1–3 đã chặn thì không được bỏ qua.**

### 6.6 Xử lý phiếu bị sửa hoặc huỷ

OBC cho phép sửa và huỷ phiếu cũ. Nếu chỉ xuất `売上日付 = hôm nay`, phiếu cũ bị sửa sẽ không bao giờ vào hệ thống và số liệu lệch dần.

**Giải pháp đã chọn — xuất ngày + đối soát tháng:** hằng ngày xuất theo ngày; **đầu mỗi tháng xuất lại toàn bộ tháng trước**, hệ thống tự ghi đè theo khoá. Tốn thêm 1 thao tác/tháng, đổi lại số liệu luôn khớp OBC.

*(Phương án thay thế nếu OBC hỗ trợ lọc theo `更新日`: xuất theo ngày cập nhật sẽ bắt được cả phiếu cũ vừa sửa — cần kiểm tra.)*

**赤伝 (phiếu đỏ / hàng trả lại):** giữ nguyên số âm, cộng dồn tự nhiên, **không lọc bỏ**. Báo cáo tách riêng chỉ số "hàng trả lại" để nhìn thấy được.

### 6.7 Dữ liệu tồn kho (`在庫一覧`)

Mẫu xuất: `在庫一覧_YYYYMMDD.xlsx`, sheet `在庫一覧表`, **13 cột, header ở dòng 1** (khác file báo cáo — không có 5 dòng rác). Đã khảo sát bản `20260916`: 177 dòng, 142 mã hàng.

| Cột |
|---|
| `商品コード` · `商品名` · `荷姿区分コード` · `荷姿区分名` · `倉庫コード` · `倉庫名` · `日本語` · `単位` · `賞味期限` · `売上出荷数量` · `在庫残数` · `在庫単価` · `在庫金額` |

**Độ hạt: `商品コード` + `倉庫コード`** (đã kiểm chứng: 177 khoá, 0 trùng). Thêm `荷姿区分` hoặc `賞味期限` vào khoá cũng không đổi kết quả.

**Hai kho:**

| Mã | Tên | Dòng | Giá trị |
|---|---|---:|---:|
| `0001` | 茨城第１倉庫（出荷専用） | 142 | ¥90.460.039 |
| `1002` | 新・賞味期限用 | 35 | ¥47.379.032 |

Tổng tồn kho ngày 2026-09-16: **¥137.839.071** ≈ **32 ngày giá vốn**.

**Ba luật bắt buộc rút ra từ dữ liệu thật:**

1. **`在庫残数` là số thập phân** (20/177 dòng có phần lẻ, ví dụ `83.75` ケース). Số lượng dùng kiểu `NUMERIC`, **không được ép số nguyên**. Luật bất biến #3 chỉ áp cho *tiền*, không áp cho *số lượng*.
2. **`在庫残数 × 在庫単価 = 在庫金額` khớp tuyệt đối** trên toàn bộ 177 dòng → dùng luôn làm công thức đối chiếu cho cổng kiểm tra 5.
3. **`賞味期限` có sẵn ở mức từng lô** → cho phép cảnh báo rủi ro hạn sử dụng theo tiền, xem §8.3 ③.

**`売上出荷数量` = số xuất *trong ngày*** (đã xác nhận). Vì vậy tính được vòng quay kho trực tiếp từ chuỗi snapshot hằng ngày, không cần suy ra từ dữ liệu bán hàng.

---

## 7. Pipeline nạp dữ liệu

### 7.1 Quy trình của con người (13:30 mỗi ngày)

1. Xuất 3 file từ OBC như thường lệ
2. Mở trang nội bộ, **kéo thả 3 file vào**
3. Đọc dòng kết quả

```
✅ 2026-09-16 · nạp xong trong 4 giây
   売上伝票データ    812 dòng   ¥3.482.910 doanh thu · ¥1.104.220 lãi gộp
   得意先全情報    2.081 dòng   +3 khách mới · 7 khách đổi thông tin
   在庫データ        232 dòng   4 mã sắp hết hàng

⚠️  1 cảnh báo — phiếu 081422 có lãi gộp âm ¥-12.400  [xem chi tiết]
```

Không có script chạy ngầm, không có máy nào phải bật, không có log để đi dò. **Sai là hiện ngay lúc người ta còn ngồi đó.** Với công ty không có IT, hệ thống hỏng trong im lặng nguy hiểm hơn hệ thống hỏng ồn ào.

### 7.2 Năm cổng kiểm tra

| Cổng | Chặn cái gì | Hành vi |
|---|---|---|
| 1. Nhận diện file | Sai mẫu, sai loại, nhầm file | **Chặn** |
| 2. Khớp cột | Cột thiếu/đổi tên (OBC nâng cấp) | **Chặn**, báo rõ cột nào |
| 3. Hợp lý nghiệp vụ | Trùng ngày đã nạp, kỳ nhảy cóc, file rỗng, file cắt cụt | **Chặn** |
| 4. So sánh hôm trước | Doanh thu lệch >3 lần, số dòng rơi >50%, lãi gộp âm bất thường | Cảnh báo |
| 5. Đối chiếu tổng | Tổng `税抜金額` tính lại phải khớp tổng trong file | Cảnh báo |

**Không bao giờ âm thầm "sửa hộ" dữ liệu.**

Cổng 3 phải bắt được trường hợp thật đã xảy ra: bản `得意先全情報` 201 dòng và bản 5 cột.

### 7.3 Nạp lại vô hại

Mỗi file lưu kèm **mã băm nội dung**. Thả lại đúng file cũ → nhận ra và bỏ qua. Thả file cùng ngày nhưng đã sửa trong OBC → ghi đè theo khoá. Đây chính là cơ chế làm cho đối soát tháng (§6.6) hoạt động mà không cần thao tác gì thêm.

### 7.4 Đồng bộ ngược ra 2 Google Sheet

Mỗi đêm, sau khi kho đã sạch:

```
Postgres ──► Google Sheet của app nhân viên   (sản phẩm · giá · khách hàng)
         └─► Google Sheet của app khách hàng   (sản phẩm · giá · khách hàng)
```

Ghi đè đúng các cột master, **giữ nguyên các cột hai app tự quản** (ảnh, tên tiếng Việt, thứ tự hiển thị, ẩn/hiện). **Không sửa dòng code nào của hai web, không có downtime.**

Đây là hạng mục **giá trị cao nhất trên mỗi giờ công** trong toàn dự án — nó giải quyết vấn đề đang gây thiệt hại mỗi ngày, và phải làm **trước cả báo cáo**.

---

## 8. Báo cáo

### 8.1 Quyết định: tự build trong web app

Đã loại bỏ Power BI, Looker Studio và Metabase. Lý do ở §11.

**Nguyên tắc bất biến:**

> **Logic nghiệp vụ nằm trong SQL ở lớp `mart`, không nằm trong công cụ báo cáo.**

Đổi lại ba thứ: đổi lớp hiển thị lúc nào cũng được; AI bảo trì được vì mọi định nghĩa nằm trong file SQL có lịch sử git; một con số chỉ có một định nghĩa.

### 8.2 Hai báo cáo đầu tiên

**① Tổng quan kinh doanh**

Doanh thu / lãi gộp / tỷ suất theo ngày–tháng, so cùng kỳ năm trước. Trọng tâm là **phân rã nguyên nhân biến động**: tách phần thay đổi do *giá*, do *sản lượng*, do *cơ cấu mặt hàng*, do *khách mới/khách mất*.

Đây là báo cáo trả lời câu hỏi tháng 7 ở §1.2 — bán gấp đôi mà tỷ suất tụt 6,7 điểm là vì đẩy hàng giá thấp, vì giảm giá cho khách lớn, hay vì cơ cấu mặt hàng đổi? Ba nguyên nhân đòi ba hành động khác nhau.

**② Khách rời bỏ — có nút hành động**

```
NAM DUONG JP株式会社   lần cuối mua 67 ngày trước   lãi gộp 12T ¥847.000
                       [ Giao cho sale ]  [ Ghi chú cuộc gọi ]  [ Hẹn nhắc lại ]
```

Quý vừa rồi có **882 khách trong danh bạ không phát sinh đơn nào**. Đây là danh sách hành động, không phải biểu đồ để ngắm.

**Một danh sách khách rời bỏ không bấm hành động được là nửa sản phẩm** — đây chính là lý do quyết định chọn tự build thay vì dùng công cụ BI, vì công cụ BI về bản chất chỉ trưng bày.

### 8.3 Ba báo cáo làm sau

Chỉ làm khi hai báo cáo đầu chứng minh có người dùng hằng ngày:

- **③ Sản phẩm, giá và tồn kho** — ABC theo lãi gộp; mặt hàng tỷ suất đang tụt; **độ phân tán giá bán cùng một mã hàng giữa các khách** (hệ thống có 10 mức `売価No.`, gần như chắc chắn đang có hàng bán dưới mức lẽ ra phải bán). Phần tồn kho (¥137,8 triệu ≈ 32 ngày giá vốn) gồm: **cảnh báo rủi ro hạn sử dụng theo tiền** (phân nhóm còn <3 / 3-6 / 6-12 / >12 tháng, theo dõi xu hướng hằng ngày để phát hiện lô đang trôi về vùng nguy hiểm); **hàng chết** — còn tồn nhưng không bán được N tháng → vốn đọng; số ngày tồn kho theo từng mã.
- **④ Người bán hàng** — doanh thu/lãi gộp theo `担当者` kèm **độ phủ**: trong danh sách được giao, bao nhiêu khách thực sự có đơn? Con số 1.119 khách của LAN THANH chỉ có ý nghĩa khi biết bao nhiêu chưa từng được chạm tới.
- **⑤ Hiệu quả app đặt hàng** — so sánh **258 đang dùng · 855 đã bỏ · phần còn lại** về doanh thu/khách, tần suất, số dòng mỗi đơn, tỷ suất. Nhờ SCD2, so sánh được **chính khách đó trước và sau khi bật app**. Báo cáo này quyết định có nên đầu tư Giai đoạn 3 hay không.

---

## 9. Vận hành & bảo trì bằng AI

### 9.1 Kẻ thù thật sự là mất ngữ cảnh

Hai năm nữa, một phiên AI mới sẽ không biết `赤伝` là gì, không biết vì sao `raw` là file chứ không phải bảng, không biết `締め日` ảnh hưởng ra sao. Nó sẽ đoán, và đoán sai.

> **Repo phải tự mang theo ngữ cảnh của nó.** Đây là điều kiện để mô hình bảo trì bằng AI sống được 5 năm.

### 9.2 Cấu trúc repo

```
kome-data/
├── CLAUDE.md               ← ngữ cảnh cho AI  ⭐ quan trọng nhất
├── README.md               ← hướng dẫn cho người
├── docs/
│   ├── glossary-ja-vi.md   ← từ điển thuật ngữ OBC Nhật–Việt
│   ├── runbook.md          ← hỏng thì làm gì
│   └── decisions/          ← nhật ký quyết định
├── config/
│   ├── columns_uriage.yml  ← ánh xạ 271 cột OBC → cột CSDL
│   ├── columns_tokuisaki.yml
│   └── columns_zaiko.yml
├── db/migrations/          ← 001_*.sql, 002_*.sql … đánh số, chỉ thêm
├── mart/                   ← LOGIC NGHIỆP VỤ, SQL thuần
├── app/
│   ├── ingest/             ← đọc Excel + 5 cổng kiểm tra
│   ├── sync_sheets/        ← đồng bộ ngược ra 2 Google Sheet
│   ├── reports/
│   └── web/                ← FastAPI + HTML
└── tests/fixtures/         ← file Excel mẫu, gồm cả file hỏng cố ý
```

`config/*.yml` — OBC đổi tên cột thì sửa YAML, **không đụng code**. Đây là chỗ dễ hỏng nhất trong 5 năm.

`docs/decisions/` — mỗi quyết định kiến trúc một file ngắn: *chọn gì, vì sao, đã cân nhắc gì khác*.

### 9.3 Công nghệ và lý do

| Thành phần | Chọn | Lý do |
|---|---|---|
| Đọc Excel | Python + pandas + **python-calamine** | Đã dùng Python; calamine nhanh hơn openpyxl ~20 lần |
| Kho | **PostgreSQL** | Chuẩn mở, AI thạo nhất, không khoá chân |
| Đổi cấu trúc CSDL | **File `.sql` đánh số** | Không dùng công cụ migration phức tạp; AI đọc SQL thuần chính xác hơn |
| Web | **FastAPI + HTML đơn giản** | Cùng stack sẽ dùng lại cho CRM và app đặt hàng |
| Ánh xạ cột | **YAML tách riêng** | Sửa cấu hình, không sửa code |
| Test | **pytest** | Phủ đúng chỗ nguy hiểm |

### 9.4 Test — chỉ test chỗ thật sự nguy hiểm

Không đuổi theo tỷ lệ phủ. Sáu nhóm:

| Test | Chặn thảm hoạ gì |
|---|---|
| 5 cổng kiểm tra, với file hỏng thật | File cắt cụt lọt vào kho |
| Nạp 3 lần → cùng kết quả | Doanh thu nhân ba |
| SCD2: đổi hạng tạo bản mới, không đổi thì không tạo | Phình bảng hoặc mất lịch sử |
| Phiếu đỏ số âm cộng đúng | Doanh thu bị thổi phồng |
| Đối soát tháng với phiếu đã sửa | Số lệch dần khỏi OBC |
| Tổng từ `mart` khớp tổng từ `fact` | Báo cáo nói dối |

### 9.5 Sao lưu — ba lớp

Gói Supabase Free **không có sao lưu tự động**, nên phải tự làm:

| Lớp | Cách làm | Khôi phục được gì |
|---|---|---|
| 1. File Excel gốc | Đã có trong OneDrive | Dựng lại **toàn bộ** từ số 0 |
| 2. Kết xuất CSDL hằng đêm | `pg_dump` nén, đẩy lên OneDrive. Giữ 30 bản ngày + 12 bản tháng | Khôi phục nhanh |
| 3. Dữ liệu schema `app` | Kết xuất riêng | **Thứ duy nhất không dựng lại được từ Excel** |

> **Mỗi quý phải thử khôi phục một lần.** Một bản sao lưu chưa từng được thử khôi phục thì không phải bản sao lưu.

### 9.6 Quy trình khi hỏng

| Sự cố | Xử lý | Thời gian |
|---|---|---|
| Nạp nhầm file | Bấm **Hoàn tác lần nạp** | 10 giây |
| OBC đổi tên cột | Sửa `config/*.yml`, chạy test | 5 phút |
| Số không khớp OBC | Xuất lại cả tháng, thả vào | 2 phút |
| CSDL đầy 500 MB | Nâng gói | 5 phút |
| Mất sạch CSDL | Nạp lại từ file Excel gốc | ~1 giờ |
| Web app không truy cập được | **Việc nạp và OBC không bị ảnh hưởng** | — |

Dòng cuối là chủ ý thiết kế: **web app hỏng không làm gián đoạn kinh doanh.**

### 9.7 Phân quyền

| Tài khoản CSDL | Quyền |
|---|---|
| `ingest` | Ghi vào `core` |
| `app` | Đọc `core`, đọc–ghi `app` |
| `report` | **Chỉ đọc** |
| `admin` | Toàn quyền — chỉ khi chạy migration |

Mật khẩu để trong biến môi trường, **không bao giờ nằm trong git**. Khi cho AI xem code, không đưa kèm thông tin kết nối thật.

**Lưu ý pháp lý:** dữ liệu chứa tên, địa chỉ, điện thoại, email người phụ trách của 2.080 khách — là **個人情報** theo luật Nhật. Tránh chép nguyên khối ra máy cá nhân hoặc gửi lên dịch vụ ngoài khi không cần thiết.

### 9.8 Cách làm việc với AI

- **Hai project Supabase** (gói Free cho phép 2): một chạy thật, một để thử. Thử trước, áp sau.
- **Không để AI chạy lệnh thẳng lên CSDL thật.** Mọi thay đổi cấu trúc qua file migration đánh số.
- **Chạy test trước và sau mỗi lần sửa.**
- **Mỗi quyết định lớn thêm một file trong `docs/decisions/`.**

---

## 10. Hạ tầng & chi phí

### 10.1 Lộ trình hạ tầng

| Giai đoạn | CSDL | Web app | ¥/tháng |
|---|---|---|---:|
| **Dựng & thử** | **Supabase Free** | VPS Vultr nhỏ | ~900 |
| **Chạy thật** | **Vultr Managed PostgreSQL** (Tokyo) | VPS Vultr nhỏ | ~3.200 |

Bắt đầu bằng Supabase Free vì **¥0, dựng trong 5 phút, không đụng vào bất kỳ máy nào đang chạy thật**.

Khi chạy thật, ưu tiên **Vultr Managed PostgreSQL** (~¥2.300/tháng): có sao lưu tự động, Vultr tự vá lỗi, cách ly hoàn toàn, cùng nhà cung cấp và cùng vùng Tokyo. *Phương án thay thế: VPS Vultr riêng tự cài Postgres (~¥900–1.500) — rẻ hơn nhưng phải tự lo sao lưu và bảo mật.*

**Chuyển đổi gần như miễn phí** vì cả hai đều là PostgreSQL chuẩn: `pg_dump` + `pg_restore`, khoảng 15 phút.

### 10.2 Hai việc phải làm về hạ tầng

**(a) Chuyển thư mục dữ liệu khỏi OneDrive cá nhân.** Dữ liệu đang nằm trong ổ OneDrive *cá nhân*. Người khác không thấy, và tài khoản bị khoá là mất truy cập. Nên chuyển sang thư viện tài liệu của một SharePoint Team Site — làm được trong 10 phút.

*Mức khẩn đã giảm sau khi chốt việc trang nạp tự lưu trữ file (§6.1): kho lưu trữ chính thức nằm trong hệ thống, còn OneDrive trở thành lớp dự phòng. Nhưng vẫn nên làm, vì hiện nó đang là bản gốc duy nhất của dữ liệu lịch sử từ 2025-02.*

**(b) Không đặt CSDL lên máy chủ đang chạy WordPress.** Ba lý do: tranh giành tài nguyên; rủi ro khi phát triển làm sập website; và quan trọng nhất — **WordPress là mục tiêu bị tấn công thường xuyên qua lỗ hổng plugin.** Nếu bị chiếm quyền, kẻ tấn công có luôn dữ liệu 2.080 khách hàng cùng toàn bộ doanh thu, giá vốn, lãi gộp. Vừa là thiệt hại cạnh tranh, vừa là sự cố rò rỉ 個人情報 phải báo cáo theo luật Nhật.

Cũng không nên đặt chung với `sale1.komejapan.com` vì nó đang phục vụ 258 khách thật.

---

## 11. Nhật ký quyết định

| # | Quyết định | Lý do |
|---|---|---|
| 1 | **PostgreSQL** làm nguồn sự thật duy nhất | Một kho nuôi cả 4 sản phẩm; dữ liệu nhỏ (~600 MB/5 năm); chuẩn mở, không khoá chân — khác Dataverse/Firebase |
| 2 | **Loại Power BI** | Postgres **bắt buộc đi qua on-premises data gateway** → cần một máy bật 24/7, đúng thứ cần loại bỏ. Thêm nữa: AI không sửa được file `.pbix` nhị phân |
| 3 | **Loại Looker Studio** | Dashboard cấu hình bằng bấm chuột, **không nằm trong git** → cùng điểm yếu với Power BI ở lớp hiển thị |
| 4 | **Loại Metabase** | Giá trị chính là để người không biết kỹ thuật tự làm báo cáo, nhưng thực tế họ sẽ hỏi chủ sở hữu. Câu hỏi tuỳ hứng đã có cách giải: hỏi AI viết SQL. Không đáng thêm ¥2.000/tháng và thêm một container phải trông |
| 5 | **Tự build báo cáo trong web app** | Chỉ cách này mới gắn được **nút hành động** vào báo cáo — công cụ BI về bản chất chỉ trưng bày |
| 6 | **Lớp `raw` là file, không phải bảng** | Lưu 271 cột text vào CSDL tốn ~400–700 MB/năm. File gốc đạt cùng mục đích, chi phí gần 0 |
| 7 | **Dùng `売上伝票データ` (271 cột)**, không dùng `売上明細表` | Là tập cha; có `入金額１` nối đơn bán với phiếu thu. ~843 dòng/ngày nên 271 cột không tốn kém |
| 8 | **Xuất ngày + đối soát tháng** | Bắt được phiếu cũ bị sửa/huỷ trong OBC; chỉ tốn 1 thao tác/tháng |
| 9 | **SCD2 cho khách hàng** | Snapshot hằng ngày làm lịch sử gần như miễn phí; trả lời được câu hỏi 258 vs 855 về app đặt hàng |
| 10 | **Kéo–thả thủ công**, không theo dõi thư mục tự động | Phản hồi tức thì đáng giá hơn tiết kiệm 30 giây; không phụ thuộc máy bật 24/7 |
| 11 | **Đồng bộ ngược ra Sheet trước khi làm báo cáo** | Giá trị cao nhất trên mỗi giờ công; giải quyết vấn đề đang gây thiệt hại mỗi ngày |
| 12 | **Supabase Free trước, Vultr Managed sau** | ¥0 khi dựng, không đụng hạ tầng đang chạy; chuyển đổi mất ~15 phút |

---

## 12. Rủi ro và giả định cần xác nhận

| # | Vấn đề | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| A1 | **Mẫu xuất hằng ngày chưa được chốt trong OBC** | Cao — quyết định toàn bộ ánh xạ cột | Xuất thử 1 ngày, đối chiếu với `config/*.yml` trước khi viết code |
| A2 | ~~Mẫu xuất tồn kho chưa khảo sát~~ | — | **✅ ĐÃ GIẢI QUYẾT** — đã khảo sát `在庫一覧_20260916.xlsx`, xem §6.7. Còn một điểm nhỏ: ý nghĩa cột `売上出荷数量` |
| A3 | OBC có hỗ trợ lọc theo `更新日` không | Thấp | Nếu có thì thay được đối soát tháng |
| A4 | Đơn từ Apps Script đi vào pipeline Python theo đường nào | Thấp ở GĐ 0+1, cao ở GĐ 2+ | Cần xác nhận trước Giai đoạn 2 |
| A5 | **Danh sách nhân viên bán hàng lệch giữa OBC và web lên đơn** | Trung bình | Xem bên dưới — cần một bảng ánh xạ |
| R1 | **Bus factor = 1** | Cao | `CLAUDE.md` + `docs/decisions/` + test; repo tự mang ngữ cảnh |
| R2 | Supabase Free hết 500 MB | Thấp (~năm thứ 3) | Nâng gói hoặc chuyển Vultr |
| R3 | OBC đổi cấu trúc cột khi nâng phiên bản | Trung bình | Cổng 2 chặn; sửa YAML, không sửa code |
| R4 | Mở rộng phạm vi sang GĐ 2–3 quá sớm | Cao | Mỗi giai đoạn phải chạy ổn định trước khi sang giai đoạn sau |

### 12.1 Chi tiết A5 — ĐÃ GIẢI QUYẾT: hai khái niệm khác nhau

**Kết luận: không phải lỗi dữ liệu.** `05 愛華 本田` và `06 Hà Minh Chiến` là **arubaito hỗ trợ nhập đơn**, không phải người phụ trách khách hàng. Hai danh sách dưới đây là hai chiều dữ liệu độc lập và **tuyệt đối không được gộp**:

| Khái niệm | Nguồn | Số người | Ý nghĩa |
|---|---|---|---|
| **`担当者`** — người phụ trách khách | OBC (`売上主担当者`) | 5 | Sở hữu mối quan hệ khách hàng. **Đây mới là "nhân viên bán hàng".** |
| **Người lên đơn** | Web `kome-order` | 7 | Chỉ là người gõ đơn vào máy (gồm 2 arubaito + 1 quản trị) |

**Hệ quả bắt buộc:**

- `dim_salesperson` chỉ chứa **5 người từ OBC**. Sạch, không pha tạp.
- Người lên đơn thuộc bảng `app_user` trong schema `app` — phạm vi Giai đoạn 2/3.
- **Báo cáo ④ (người bán hàng) phải dùng `担当者` của OBC, tuyệt đối không dùng người gõ đơn.** Nếu nhầm, arubaito sẽ hiện ra như người bán hàng giỏi nhất công ty.
- Vẫn cần `config/salesperson_map.yml` để ánh xạ 4 người có mặt ở cả hai nơi (mã khác nhau: `0004`↔`01`, `0104`↔`02`, `0105`↔`03`, `0102`↔`04`), **ghép bằng mã, không ghép bằng tên** — tên viết khác nhau giữa hai hệ thống (chữ hoa không dấu vs có dấu).

**Một lợi ích ngoài dự kiến:** vì `kome-order` là nơi nhân viên gõ đơn hộ khách (đơn qua điện thoại/LINE), còn `sale1.komejapan.com` là nơi khách tự đặt, nên **phân biệt được đơn khách tự đặt với đơn được gõ hộ**. Đây chính là nhóm đối chứng mà báo cáo ⑤ cần để đo hiệu quả thật của app đặt hàng.

### 12.2 Bảng đối chiếu nhân sự (tham khảo)

| OBC (`売上主担当者`) | Web lên đơn (`kome-order`) | Vai trò |
|---|---|---|
| `0002` 西村 巧 | *(không có)* | 担当者 (23 khách) |
| `0004` TRINH CONG MINH | `01` Trình Công Minh | 担当者 (350 khách) |
| `0102` NGUYEN PHUONG DUNG | `04` Nguyễn Phương Dung | 担当者 (108 khách) |
| `0104` TRAN THI LAN THANH | `02` Trần Thị Lan Thanh | 担当者 (1.119 khách) |
| `0105` HA HUY LONG | `03` Hà Huy Long | 担当者 (473 khách) |
| *(không có)* | `05` 愛華 本田 | **Arubaito — chỉ nhập đơn** |
| *(không có)* | `06` Hà Minh Chiến | **Arubaito — chỉ nhập đơn** |
| *(không có)* | `07` Quản trị viên | Tài khoản quản trị |

---

## 13. Tiêu chí hoàn thành

**Giai đoạn 0:**

- [ ] Nạp được 1 ngày dữ liệu thật từ 3 file, ra đúng số liệu
- [ ] Nạp lại cùng file 3 lần → kết quả không đổi
- [ ] File hỏng thật (bản 201 dòng, bản 5 cột) bị cổng kiểm tra chặn
- [ ] Nạp lại được toàn bộ dữ liệu lịch sử từ 2025-02 đến nay
- [ ] Tổng doanh thu quý 2026-05→07 khớp **¥390.126.850**
- [ ] Tổng tồn kho ngày 2026-09-16 khớp **¥137.839.071** trên **177 dòng / 2 kho**
- [ ] Trang kiểm tra sức khoẻ hiển thị đúng kỳ dữ liệu và cảnh báo
- [ ] Sao lưu hằng đêm chạy được, và **đã thử khôi phục thành công một lần**

**Giai đoạn 1:**

- [ ] Hai Google Sheet nhận được master data mỗi đêm; hai web app chạy bình thường, không sửa code
- [ ] Báo cáo ① giải thích được vì sao tỷ suất tháng 7 giảm 6,7 điểm
- [ ] Báo cáo ② liệt kê đúng danh sách khách rời bỏ và bấm được nút hành động
- [ ] Nhân viên văn phòng tự nạp dữ liệu hằng ngày **mà không cần hỏi ai**

---

## 14. Bước tiếp theo

1. Chủ sở hữu đọc và duyệt đặc tả này
2. Chốt mẫu xuất hằng ngày trong OBC, xuất thử 1 ngày (A1, A2)
3. Lập kế hoạch triển khai chi tiết
4. Bắt đầu Giai đoạn 0
