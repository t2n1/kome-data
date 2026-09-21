# Đặc tả thiết kế — Đợt 4b: Sản phẩm · Kho hàng

**Ngày:** 2026-09-22
**Công ty:** 株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật
**Phạm vi:** hai trang mới — `/san-pham` (danh sách + hồ sơ mã hàng) và `/kho-hang` — theo gói thiết kế `Sản phẩm.dc.html` và `Kho hàng.dc.html`, trừ những khối không có dữ liệu.
**Trạng thái:** Chờ duyệt
**Tài liệu liên quan:**
- `docs/superpowers/specs/2026-09-22-dot-4a-customer-360-design.md` — **"đặc tả 4a"**, đợt liền trước
- `docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md` §7 — **"lộ trình"**

---

## 1. Bối cảnh

Đặc tả 4a §1 đã tách đợt 4 làm ba. Tài liệu này là **4b**: hai trang mới, cùng đọc
`core.dim_product` và `core.fact_inventory_daily`.

Hai màn này đứng chung một đợt vì chúng dùng chung đúng một chỉ số then chốt — **tốc độ
bán của một mã hàng** — và tách ra là viết công thức đó hai lần.

---

## 2. Ràng buộc kế thừa

**R1–R6** của đặc tả nền §3 nguyên vẹn. Cộng thêm, từ `CLAUDE.md` và các đợt trước:

- **Định nghĩa chỉ số CHỈ nằm ở `mart/`.**
- Mọi route chỉ đọc đi qua `open_app_conn`; chỉ `upload`/`kho_du_lieu`/`undo` dùng
  `open_conn`. Có test duyệt AST canh.
- `kome/web/app.py` không nhập `kome.pipeline`/pandas/calamine ở mức ngoài cùng.
- Mốc thời gian là `mart.moc_thoi_gian.hom_nay`, **không bao giờ** `current_date`.
- **Ngân sách vòng hỏi** (đo thật 2026-09-22): round-trip rỗng tới pooler Tokyo 47 ms,
  một lượt hỏi thật ~260 ms, CSDL tính một khối ~10 ms. Nút thắt là **số lượt hỏi**.
- Mọi template `include "_nav.html"` phải tự đóng `</main>` đúng một lần.
- Không thêm gói, không thêm một dòng JavaScript.
- **Mã (`*コード`) là TEXT.** `000000009292` đọc thành số sẽ mất số 0 đầu.
- **Số lượng CÓ phần thập phân** (`83.75` ケース); tiền luôn là số nguyên yên.

---

## 3. Đo đạc quyết định hình dạng đợt này

Đo thật trên CSDL production ngày 2026-09-22.

### 3.1 Gói thiết kế hư cấu về kho — và đó là chỗ lệch lớn nhất

| Gói thiết kế | Đo được | Hệ quả |
|---|---|---|
| **Ba kho**: `Osaka`, `Nagoya`, `Kho lạnh Osaka` | **Hai kho**: `0001 茨城第１倉庫（出荷専用）`, `1002 新・賞味期限用` | Bộ lọc kho đọc từ `core.dim_warehouse`, không viết cứng tên nào |
| Tồn kho có lịch sử để vẽ xu hướng | **Đúng 1 ngày chụp** (2026-09-16), 177 dòng, 142 mã | Mọi khối "xu hướng tồn" **cắt** |
| Hạn sử dụng là ngày | Cột `best_before` là **TEXT** và có giá trị chữ `賞味期限なし` (8 dòng); 1/177 dòng rỗng | Phải xử lý ba ca: ngày hợp lệ · "không hạn" · rỗng |
| `SHIPMENTS` — lô hàng đang về, có trạng thái | **Không có dữ liệu mua hàng ở bất kỳ đâu** | **Cắt** |
| `MUA_VU` — Tết / Obon / 忘年会 kèm hệ số | Kiến thức viết cứng, không phải dữ liệu | **Cắt** — thuộc đợt 8 (Dự báo) |

**Tên kho là phát hiện đáng chú ý nhất.** `1002 新・賞味期限用` nghĩa đen là "kho mới dùng
cho hạn sử dụng" — nó là một ngăn nghiệp vụ, không phải một kho địa lý. Trang phải hiện
đúng tên OBC trả về và **không** suy diễn gì thêm về địa điểm.

### 3.2 Lịch sử tồn kho sẽ tích luỹ, nhưng hôm nay chưa có

`core.fact_inventory_daily` khoá `(snapshot_date, product_code, warehouse_code)`, và quy
trình 13:30 nạp `在庫一覧` mỗi ngày. Nghĩa là lịch sử tồn kho **đang được tích luỹ từ hôm
nay trở đi**, chỉ là chưa có gì để vẽ.

**Quyết định:** không dựng khối nào phụ thuộc lịch sử tồn kho ở đợt này. Dựng một khối
trống chờ dữ liệu là dạy người ta cuộn nhanh (đặc tả 4a §4.2).

### 3.3 Dữ liệu có đủ cho phần còn lại

| Cần cho | Nguồn | Trạng thái |
|---|---|---|
| Danh mục 232 mã | `core.dim_product` | có sẵn |
| Lượng bán theo ngày, xu hướng 12 tháng | `core.fact_sales_line` (291.436 dòng) | có sẵn |
| Khách đang mua / chưa mua mã này | `mart.khach_mat_hang` (4a) | có sẵn |
| Tỷ suất theo mã | `mart.ty_suat_mat_hang` (4a, migration 021) | có sẵn |
| Bậc giá theo mã | `core.fact_price_list` | 4.185 dòng |
| Tồn hiện tại, giá trị tồn, hạn dùng | `core.fact_inventory_daily` | 1 ngày, 177 dòng |
| Tên kho | `core.dim_warehouse` | 2 kho |

---

## 4. Phạm vi

### 4.1 Trong phạm vi

**Trang `/san-pham` — danh sách:**
1. **Danh mục SKU** — bảng 232 mã: tên, doanh thu, tỷ suất, tồn, số khách đang mua.
2. Tìm kiếm + lọc theo **trạng thái tồn** (đủ · sắp thiếu · hết · tồn chết).

**Trang `/san-pham/{mã}` — hồ sơ một mã:**
3. **Lượng bán theo tháng** — 12 tháng gần nhất, vẽ SVG như `mart.khach_theo_thang`.
4. **Khách đang mua** — xếp theo doanh thu, kèm nhịp mua của họ với mã này.
5. **Khách đã ngừng mua mã này** — tín hiệu sớm hơn "khách ngừng mua hẳn".
6. **Tồn kho theo kho** — số lượng, giá trị, hạn dùng.
7. **Bậc giá** — bảng giá theo `price_level`, mỗi 荷姿 một dòng.

**Trang `/kho-hang`:**
8. **Bốn ô tổng quan** — số mã hết hàng · số mã sắp thiếu · số lô cận hạn · giá trị tồn chết.
9. **Tồn hiện tại** — bảng mọi dòng tồn, lọc theo kho và theo trạng thái.
10. **Cận hạn sử dụng** — lô sắp hết hạn, xếp theo ngày gần nhất.
11. **Giá trị tồn theo kho** — hai kho, kèm ngày chụp đang xem.

**Dữ liệu:** migration `023_mart_san_pham.sql` — tốc độ bán, trạng thái tồn, hạn dùng đã
phân tích.

### 4.2 Cắt khỏi phạm vi, và vì sao

| Khối trong gói thiết kế | Vì sao cắt |
|---|---|
| **Lịch hàng về 14 ngày tới** · **Lô cần bám** · **Khối lượng theo kho nhận** · **Sắp về kho** | Cần dữ liệu mua hàng / nhà cung cấp. Nhóm C — không nằm trong đợt nào |
| **Mùa vụ sắp tới** | Kiến thức viết cứng, không phải dữ liệu. Thuộc đợt 8 |
| **Mã cần đặt** | Cùng nguồn với "hàng về" |
| Mọi khối **xu hướng tồn kho theo thời gian** | Chỉ có 1 ngày chụp — §3.2 |
| **Giả định đang dùng** | Khối này liệt kê tham số của mô hình đặt hàng; không có mô hình đó thì không có giả định nào để liệt kê |

### 4.3 Không đụng tới

`kome/pipeline.py`, 5 cổng kiểm tra, `kome/coverage.py`, `kome/web/bao_mat.py`,
`kome/web/nguoi_dung.py`, màn Kho dữ liệu, và **hai trang khách hàng của 4a**.

---

## 5. Quyết định đã chốt

### 5.1 Tốc độ bán là chỉ số chung của cả hai màn

Cả bốn trạng thái tồn (đủ · sắp thiếu · hết · tồn chết) đều so tồn hiện tại với **tốc độ
bán**, nên tốc độ bán phải có đúng một nhà.

**Định nghĩa:** số lượng bán trung bình mỗi ngày trong **90 ngày gần nhất**, tính từ
`mart.moc_thoi_gian.hom_nay`.

Vì sao 90 ngày chứ không phải cả lịch sử: mã hàng thực phẩm đổi mùa, và một mã bán chạy
năm ngoái mà ba tháng nay không ai mua thì "tốc độ trung bình toàn lịch sử" sẽ nói dối
theo hướng nguy hiểm — nó bảo hàng còn chạy trong khi thực tế đang chết.

Vì sao trung bình chứ không phải trung vị (khác `mart.nhip_mua`): ở đây ta hỏi **"bao
nhiêu ngày nữa thì hết"**, tức một phép chia trên tổng lượng — trung bình đúng cho câu
đó. `nhip_mua` hỏi **"khoảng cách điển hình giữa hai lần mua"**, nơi một kỳ nghỉ Tết làm
trung bình lệch. Hai câu hỏi khác nhau, hai công thức khác nhau, và **ghi chú tại chỗ
phải nói ra điều đó** để người sau không "sửa cho nhất quán".

### 5.2 Bốn trạng thái tồn

| Trạng thái | Định nghĩa |
|---|---|
| **Hết hàng** | tồn = 0 **và** có bán trong 90 ngày gần nhất |
| **Sắp thiếu** | tồn > 0 và đủ bán **dưới 14 ngày** theo tốc độ bán |
| **Tồn chết** | tồn > 0 và đủ bán **trên 180 ngày**, hoặc tồn > 0 mà **không bán lần nào** trong 90 ngày |
| **Đủ** | còn lại |

Mã tồn = 0 **và** không bán gì trong 90 ngày thì **không** là "hết hàng" — nó là mã đã
ngừng kinh doanh, và xếp nó vào danh sách cần đặt hàng là tạo việc giả.

### 5.3 Hạn sử dụng: ba ca, không phải một

`best_before` là TEXT với ba dạng: `'2028年06月09日'` (ngày), `'賞味期限なし'` (không hạn),
và rỗng. Chuyển đổi nằm ở `mart`, không ở Python.

- Ngày hợp lệ → số ngày còn lại.
- `賞味期限なし` → **không bao giờ** vào khối "cận hạn". Đây là hàng không có hạn dùng, và
  xếp nó vào danh sách cần xả là sai nghiệp vụ.
- Rỗng → cũng không vào khối cận hạn, **nhưng phải đếm được**: trang hiện "1 dòng chưa có
  hạn dùng" thay vì im lặng bỏ qua.

**Bất biến:** không bao giờ dùng `to_date()` trần trên cột này — một giá trị chữ sẽ làm
cả truy vấn nổ và trang trắng. Dùng `CASE` kiểm dạng trước.

### 5.4 Ngày chụp: luôn hiện, luôn là ngày mới nhất

Mọi khối tồn kho đọc `snapshot_date` **mới nhất**, và trang **phải hiện ngày đó**. Hôm
nay chỉ có một ngày nên không ai thấy khác biệt; ngày mai có nhiều ngày thì một trang
không ghi ngày sẽ được đọc như "bây giờ" trong khi nó là ảnh chụp lúc 13:30 hôm trước.

### 5.5 Ngân sách vòng hỏi

- `/san-pham` (danh sách): **2 truy vấn** — một cho bảng, một cho bộ đếm trạng thái.
- `/san-pham/{mã}`: **tối đa 5 truy vấn**.
- `/kho-hang`: **2 truy vấn** — một cho bốn ô tổng quan + giá trị theo kho, một cho bảng.

Thấp hơn hẳn `/khach-hang` (3) và `ho_so()` (7) vì hai màn này ít khối hơn. **Có test đếm
cho cả ba.**

---

## 6. Kiến trúc

### 6.1 Migration `023_mart_san_pham.sql`

Chạy bằng vai trò **`postgres`**. Không `CREATE MATERIALIZED VIEW` (lý do: đặc tả 4a §3.1).

| View | Nội dung |
|---|---|
| `mart.toc_do_ban` | `(product_code, so_luong_90n, toc_do_ngay, doanh_thu_90n)` — §5.1 |
| `mart.ton_hien_tai` | `(product_code, warehouse_code, ten_kho, so_luong, gia_tri, best_before, han_con_lai, loai_han)` — một dòng mỗi (mã, kho) ở ngày chụp mới nhất; `loai_han` ∈ `ngay`/`khong_han`/`trong` (§5.3) |
| `mart.san_pham_360` | một dòng mỗi mã: tên, nhóm, doanh thu/lãi/tỷ suất, tồn tổng, `toc_do_ngay`, `du_ban_ngay`, `trang_thai` (§5.2), số khách đang mua |
| `mart.san_pham_theo_thang` | `(product_code, thang, so_luong, doanh_thu_thuan, lai_gop)` |

### 6.2 Tầng Python — `kome/san_pham.py` (mới)

File mới, cùng nếp `kome/khach_hang.py`: dataclass + hàm nhận `conn`, **không tính chỉ số
nào**, không tự mở kết nối.

- `danh_sach(conn, tim="", loc="", sap="doanh_thu", trang=1) -> TrangSanPham`
- `ho_so(conn, ma) -> HoSoSanPham | None`
- `kho_hang(conn, kho=None, loc=None) -> Kho`

**Vì sao file mới chứ không thêm vào `kome/khach_hang.py`:** file đó đã ~480 dòng và nói
về khách hàng. Trộn sản phẩm vào là một file hai chủ đề, và repo này đã chọn tách theo
trách nhiệm (`bao_cao.py`, `coverage.py`, `nhat_ky_nap.py`, `tuoi_du_lieu.py`).

### 6.3 Ba trang mới

`kome/web/templates/san_pham.html`, `san_pham_360.html`, `kho_hang.html` — cùng nếp
template đã có. Thêm hai mục vào `_nav.html` dưới nhóm mới **HÀNG HOÁ**.

Biểu đồ vẽ SVG tự tính toạ độ, đúng nếp `kome/bao_cao.py::ve_bieu_do`.

---

## 7. Rủi ro & giả định

| # | Vấn đề | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| R1 | Chỉ 1 ngày chụp tồn kho | Cao — quyết định phạm vi | §3.2: cắt mọi khối cần lịch sử |
| R2 | 142/232 mã có dòng tồn; 90 mã còn lại không có | Trung bình | Mã không có dòng tồn hiện "—", không hiện 0 — "không biết" khác "bằng không" |
| R3 | `best_before` là TEXT có giá trị chữ | Cao — `to_date()` trần làm trang trắng | §5.3, `CASE` kiểm dạng; có test cho cả ba ca |
| R4 | Tên kho là tên nghiệp vụ tiếng Nhật, không phải địa điểm | Thấp | Hiện nguyên văn OBC, không suy diễn |
| R5 | Tốc độ bán 90 ngày với mã mới ra mắt tuần trước sẽ rất thấp | Trung bình | Mã có `lan_dau` trong 90 ngày thì `trang_thai` là `đủ`, không bao giờ là `tồn chết` |
| R6 | Số lượng có phần thập phân (`83.75` ケース) | Thấp | `numeric`, không ép `int` ở bất kỳ đâu |

---

## 8. Kiểm thử

| Test | Chặn thảm hoạ gì |
|---|---|
| `best_before = '賞味期限なし'` → không vào khối cận hạn, không làm nổ truy vấn | Trang trắng vì một giá trị chữ trong cột ngày |
| `best_before` rỗng → không vào cận hạn nhưng **đếm được** | Một lô không rõ hạn biến mất khỏi mọi báo cáo |
| Mã tồn 0 **và** không bán 90 ngày → **không** là "hết hàng" | Danh sách cần đặt hàng đầy mã đã ngừng kinh doanh |
| Mã mới ra mắt trong 90 ngày → không bao giờ là "tồn chết" | Xả hàng một mã vừa mới nhập về |
| `toc_do_ban` dùng **trung bình 90 ngày**, và ghi chú nói rõ vì sao khác `nhip_mua` | "Sửa cho nhất quán" làm hỏng một trong hai |
| Mã không có dòng tồn → hiện `—`, không hiện `0` | "Không biết" bị đọc thành "hết hàng" |
| Ngày chụp hiện trên trang và là ngày **mới nhất** | Đọc ảnh chụp hôm qua như tình trạng bây giờ |
| Số lượng giữ phần thập phân qua cả ba tầng | `83.75 ケース` thành `83` |
| `/san-pham` ≤ 2 truy vấn · `/san-pham/{mã}` ≤ 5 · `/kho-hang` ≤ 2 | Trang chậm dần từng đợt |
| Bộ lọc kho đọc từ `dim_warehouse`, không viết cứng tên | Thêm kho thứ ba thì bộ lọc im lặng bỏ sót nó |

---

## 9. Tiêu chí hoàn thành

- [ ] `/san-pham` liệt kê 232 mã, tìm và lọc theo trạng thái tồn được
- [ ] `/san-pham/{mã}` có 5 khối, ≤ 5 truy vấn (có test đếm)
- [ ] `/kho-hang` có 4 ô tổng quan + 3 khối, ≤ 2 truy vấn (có test đếm)
- [ ] Ba ca của `best_before` xử đúng, có test cho cả ba
- [ ] Ngày chụp hiện trên `/kho-hang`
- [ ] Hai mục mới trong thanh điều hướng, nhóm **HÀNG HOÁ**
- [ ] `CLAUDE.md` ghi chỉ số mới và bất biến "hai công thức cho hai câu hỏi khác nhau"
- [ ] `pytest -v` xanh toàn bộ
- [ ] **KIỂM TAY sau khi chạy migration lên production:** mở `/san-pham`, một hồ sơ mã
      hàng, và `/kho-hang` — xem bằng mắt, đối chiếu vài con số với `在庫一覧` gốc

---

## 10. Bước tiếp theo

1. Lập kế hoạch triển khai (writing-plans)
2. Thực thi, kiểm chứng, merge
3. Đợt 4c: Bản đồ khách hàng
