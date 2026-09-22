# Đợt 5b — Báo cáo phân tích + Dashboard chung

**Ngày:** 2026-09-23
**Màn liên quan:** 2 (Báo cáo, `/bao-cao`) — các khối phân tích còn lại; 1 (Dashboard, `/`).
**Nối tiếp:** đặc tả đợt 5a (`2026-09-22-dot-5a-ngan-sach-design.md`) — khối ngân sách giữ nguyên.
**Gói thiết kế:** `screens/Báo cáo.dc.html`, `screens/Dashboard.dc.html` (bản chép nằm ngoài
repo; số liệu trong đó là hằng số JS dựng tay, KHÔNG phải dữ liệu thật).

---

## 0. Cách đặc tả này được chốt

Chủ doanh nghiệp giao toàn quyền quyết định ("cứ làm hết, tự quyết") rồi đi ngủ. Câu trả
lời đã có từ trước và vẫn ràng buộc: **Dashboard một bố cục chung cho mọi người**. Mọi
lựa chọn khác trong tài liệu này là **phán quyết của người viết**, ghi ở §9 kèm lý do và
giá phải trả nếu sai, để người đọc sau lật lại được từng cái.

---

## 1. Phạm vi

| Màn | Thêm | Giữ nguyên |
|---|---|---|
| `/bao-cao` | 4 ô chỉ số có đường nhỏ và so cùng kỳ · biểu đồ 12 tháng thêm đường cùng kỳ · ngành hàng kéo lên/xuống · cây ô (treemap) ngành → mã · bản đồ nhiệt ngành × tháng · Pareto độ tập trung khách · bảng số chi tiết theo tháng (thu gọn) | chọn kỳ · ba khối ngân sách của 5a · bảng theo người phụ trách · bảng 10 mặt hàng lãi gộp cao nhất |
| `/` | dựng lại: 4 ô chỉ số tháng đến hôm nay · tiến độ ngân sách tháng (gọn) · xu hướng 30 ngày · sức khoẻ khách hàng · cần gọi hôm nay · hàng cận hạn · một dòng "chưa có dữ liệu" | dải "hôm nay đã có dữ liệu chưa" |

Không có khối nào vẽ bằng số bịa. Khối nào của gói thiết kế không có nguồn dữ liệu thì
**không dựng**, và tên nó nằm trong dòng "chưa có dữ liệu" của `/` (§6.7).

---

## 2. Dữ liệu thật đã đo (2026-09-23, CSDL thật, chỉ SELECT)

- Dữ liệu bán: 2025-03-03 → 2026-07-31, 291.436 dòng. Kỳ 6 chỉ có 5 tháng (3–7/2025),
  kỳ 7 đủ 12 tháng. Tháng có **cùng kỳ năm trước** chỉ là 2026-03 → 2026-07.
- "Ngành hàng" = `core.dim_product.food_category_name`: 10 giá trị có tên (ví dụ
  `食材（常温）＿VNM` ¥746 triệu, `調味料_VNM` ¥464 triệu) + chuỗi rỗng cho 10 mã
  `無形` (phí, chiết khấu — tổng ÂM, −¥26 triệu). `kind_*` chỉ có 有形/無形 nên không
  dùng làm ngành. `rank_*` là hạng OBC, không phải ngành.
- 47.816 dòng bán có `product_code = ''` (dòng chú thích của phiếu), tổng −¥15.115.
  Chúng không nối được sang `dim_product`.
- Top 10 khách của kỳ 7 chiếm **21,6%** doanh thu thuần; top 20 chiếm 29,0%.
- Thời gian thật của hai truy vấn nặng nhất (lượt chạy thứ hai, qua pooler Tokyo):
  so sánh ngành × tháng có `FULL JOIN` **246 ms**; độ tập trung khách bằng hàm cửa sổ
  **89 ms**.

---

## 3. Định nghĩa trong `mart` — migration `029_mart_phan_tich.sql`

Mọi view dưới đây là **định nghĩa chỉ số**, nên chúng nằm ở `mart`, không ở Python
(luật "Không được tự ý sửa" của `CLAUDE.md`). Migration kết thúc bằng dòng GRANT bắt
buộc:
`GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;`

### 3.1 Ngành hàng — MỘT biểu thức

`coalesce(nullif(p.food_category_name, ''), '(chưa phân loại)')` trên
`mart.dong_ban b LEFT JOIN core.dim_product p USING (product_code)`.

- **LEFT JOIN**: dòng có mã hàng rỗng hoặc mã chưa có trong danh mục vẫn giữ tiền của
  nó, rơi vào `(chưa phân loại)`. Tổng mọi ngành của một tháng **bằng đúng**
  `mart.ban_theo_thang.doanh_thu_thuan` của tháng đó. Có test canh.
- Biểu thức chỉ viết MỘT lần, trong `mart.ban_theo_nganh_thang`. Mọi view khác cần
  ngành đều đọc từ view đó.

### 3.2 `mart.ban_theo_nganh_thang`

Cột: `thang` (text `YYYY-MM`), `company_fy`, `nganh`, `doanh_thu_thuan`, `lai_gop`.
Gộp theo `(thang, nganh)`.

### 3.3 `mart.ban_theo_nganh_thang_so_sanh`

Mỗi `(thang, nganh)` kèm cùng kỳ năm trước. Cột: `thang`, `company_fy`, `nganh`,
`doanh_thu_thuan`, `lai_gop`, `dt_cung_ky`, `co_cung_ky`, `tang_truong`.

- **FULL JOIN** giữa tháng này và tháng M−12 theo `nganh`. Ngành bán năm ngoái mà năm
  nay không bán phải có dòng với `doanh_thu_thuan = 0`. Thiếu dòng đó thì khối "ngành
  kéo xuống" bỏ sót đúng ngành sụt mạnh nhất (sụt về 0) — cùng lớp lỗi với
  `mart.tien_do_ngan_sach` (bất biến FULL JOIN của `CLAUDE.md`).
- Chỉ giữ dòng có `thang` là **tháng có trong kho** (`SELECT DISTINCT thang` của chính
  CTE gốc). Không có vị từ này thì FULL JOIN sinh ra dòng cho 2026-08 → 2027-07 từ dữ
  liệu năm trước.
- `co_cung_ky` = tháng M−12 **có trong kho** (xét theo tháng, KHÔNG theo ngành). Có thì
  `dt_cung_ky = coalesce(…, 0)`; không có thì `dt_cung_ky` NULL. Cùng luật với cột
  `cung_ky` của `mart.tien_do_ngan_sach` (migration 028).
- `tang_truong` = `doanh_thu_thuan / dt_cung_ky − 1` **chỉ khi `dt_cung_ky > 0`**;
  ngược lại NULL.
- View gốc được tham chiếu hai lần, nên nó vào CTE `AS MATERIALIZED` ghi tường minh
  (bất biến CTE của `CLAUDE.md`).

### 3.3b `mart.nganh_ky_cung_ky` — ngành × kỳ

Mỗi `(company_fy, nganh)` một dòng, gộp từ `mart.ban_theo_nganh_thang_so_sanh`:
`doanh_thu_thuan`, `lai_gop` (cả kỳ) · `dt_doi_chieu` (chỉ các tháng `co_cung_ky`) ·
`dt_cung_ky` · `chenh_lech` (= `dt_doi_chieu − dt_cung_ky`) · `tang_truong` (chỉ khi
`dt_cung_ky > 0`).

Khối "ngành kéo lên/xuống" và màu của cây ô đọc từ đây. Tổng `chenh_lech` của mọi
ngành **bằng** `dt − dt_ck` của `mart.ky_cung_ky` cùng kỳ. Có test canh: hai con số
trên cùng một trang phải cộng khớp nhau.

### 3.4 `mart.ky_cung_ky` — so kỳ với cùng kỳ theo kiểu cùng tháng

Mỗi `company_fy` một dòng. Cột:

| Cột | Nghĩa |
|---|---|
| `company_fy` | kỳ |
| `so_thang_doi_chieu` | số tháng của kỳ có `co_cung_ky` |
| `thang_dau_doi_chieu`, `thang_cuoi_doi_chieu` | dải tháng đem so (NULL khi 0 tháng) |
| `dt`, `lg`, `so_khach` | trên **đúng các tháng đối chiếu** của kỳ này |
| `dt_ck`, `lg_ck`, `so_khach_ck` | trên các tháng M−12 tương ứng |

- So **cùng tháng với cùng tháng**. Đem cả kỳ 7 (12 tháng) so với kỳ 6 (5 tháng) sẽ ra
  "+140%" — một con số đúng về số học mà nói dối về kinh doanh.
- `so_khach` là `count(DISTINCT customer_code)` trên `mart.dong_ban`, KHÔNG phải tổng
  số khách theo tháng: một khách mua 5 tháng vẫn là 1 khách.
- Tỷ suất cùng kỳ (`lg_ck / dt_ck`) không có cột riêng. Nó là tỷ số của hai tổng đã
  có, và màn hình tính nó từ hai cột đó — cùng luật "tỷ số của các TỔNG".

### 3.5 `mart.tap_trung_khach` — Pareto theo kỳ

Cột: `company_fy`, `customer_code`, `ten_khach`, `doanh_thu_thuan`, `thu_hang`,
`ty_trong`, `luy_ke`.

- Gộp theo **khách**, KHÔNG theo `(khách, người phụ trách)`. `mart.ban_theo_khach` gộp
  theo cả `salesperson_code`, nên một khách đổi người phụ trách giữa kỳ xuất hiện hai
  lần. Đem view đó vẽ Pareto là một khách chiếm hai cột, và độ tập trung bị hạ thấp.
- `ty_trong` = doanh thu khách / tổng doanh thu **mọi khách** của kỳ (kể cả khách âm).
  `luy_ke` là tổng cửa sổ theo thứ tự `doanh_thu_thuan DESC, customer_code`. Có mã khách
  làm khoá phụ để thứ tự xác định: hai khách bằng tiền nhau không đổi chỗ giữa hai lần
  mở trang.
- `nullif(tổng, 0)` ở mẫu số: kỳ có tổng bằng 0 cho NULL chứ không nổ phép chia.
- Tên khách lấy bản `is_current` của `core.dim_customer`, LEFT JOIN, rơi về
  `(chưa có tên)` — cùng nếp `mart.ban_theo_khach`.

### 3.6 `mart.ban_theo_ngay`

Cột: `ngay` (date), `thang`, `doanh_thu_thuan`, `lai_gop`, `so_phieu`, `so_khach`.

- Nối **từ `core.dim_date`** (LEFT JOIN sang dòng bán), cắt trong dải
  `[ngày bán đầu tiên, mart.moc_thoi_gian.hom_nay]`. Ngày không bán (Chủ nhật, nghỉ
  lễ) có dòng mang số 0, không biến mất. Biểu đồ xu hướng dựng từ dòng thì một ngày
  mất là trục hoành co lại, và hai tuần trông như ba tuần.
- `coalesce(…, 0)` là đúng ở đây. Ngày nằm trong dải dữ liệu mà không có phiếu nào
  thì doanh thu thật sự bằng 0, không phải "không biết".

### 3.7 `mart.thang_den_hom_nay` — tháng hiện hành so cùng kỳ, cùng số ngày

Một dòng. Cột: `thang` (tháng của `hom_nay`), `tu_ngay`, `den_ngay` (= `hom_nay`),
`dt`, `lg`, `so_khach`, `so_phieu`, `co_cung_ky`, `dt_ck`, `lg_ck`, `so_khach_ck`.

- Cùng kỳ = **cùng dải ngày** 1 → `day(hom_nay)` của tháng đó năm trước, KHÔNG phải
  cả tháng năm trước. Đem 12 ngày đầu tháng so với trọn một tháng thì giữa tháng nào
  cũng "sụt 60%".
- Ngày 29/2 không có ở năm trước: dải cùng kỳ kẹp về ngày cuối của tháng năm trước.
- `co_cung_ky` = tháng M−12 có trong kho (cùng nếp §3.3). Có thì `*_ck` là
  `coalesce(…, 0)`, không có thì NULL.
- "Hôm nay" là `mart.moc_thoi_gian.hom_nay`, không phải `current_date`.

---

## 4. Tầng Python

### 4.1 `kome/bao_cao.py`

- `tinh_bao_cao` thêm các trường mới vào `BaoCao`:
  - `cung_ky`: dòng `mart.ky_cung_ky` của kỳ đang xem.
  - `nganh_thang`: các dòng `mart.ban_theo_nganh_thang_so_sanh` của kỳ (bản đồ nhiệt).
  - `nganh_ky`: các dòng `mart.nganh_ky_cung_ky` của kỳ (đóng góp, màu cây ô).
  - `tap_trung`: 20 dòng đầu của `mart.tap_trung_khach`, cùng tổng số khách có doanh
    thu và `luy_ke` tại hạng 10.
  - `hang_theo_nganh`: mọi dòng `mart.ban_theo_san_pham` của kỳ, dùng cho cây ô.
- `hang` (top 10 theo lãi gộp) lấy từ `hang_theo_nganh` bằng cách sắp xếp trong Python.
  Đây là sắp xếp để hiển thị, không phải định nghĩa chỉ số, và tiết kiệm một lượt hỏi.
- Bảng "10 khách hàng lớn nhất" cũ nhường chỗ cho Pareto. Pareto giữ đủ các cột cũ
  (tên, doanh thu), thêm tỷ trọng và luỹ kế.

### 4.2 Hình học (thuần Python, không chạm CSDL)

Cùng nếp `ve_bieu_do` và `ve_luy_ke`: tự tính toạ độ SVG. **Không thêm thư viện JS nào,
không CDN** — ràng buộc CSP của Vercel và bất biến "không có mã màu nào ngoài
`static/kome.css`" vẫn giữ.

| Hàm | Dựng gì |
|---|---|
| `ve_duong_nho(so)` | sparkline cho một ô chỉ số; điểm `None` làm đứt đường |
| `ve_bieu_do(thang)` | THÊM đường cùng kỳ nét đứt; tháng không có cùng kỳ thì đứt đường, KHÔNG vẽ về 0 |
| `ve_dong_gop(dong)` | thanh lệch hai phía quanh trục giữa, mỗi ngành một thanh, xếp theo chênh lệch |
| `ve_cay_o(nhom)` | treemap vuông hoá (squarified, Bruls và cộng sự 2000), hai tầng: ngành → tối đa 5 mã + một ô "khác" |
| `ve_nhiet(dong)` | lưới ngành × 12 tháng; ô không có cùng kỳ tô sọc với chú thích "không có cùng kỳ", KHÔNG tô như 0% |
| `ve_pareto(tt)` | cột doanh thu mỗi khách + đường luỹ kế theo trục % bên phải |

Ràng buộc chung:

- **Diện tích âm không vẽ được.** Cây ô chỉ nhận ngành và mã có doanh thu dương. Tổng
  phần bị bỏ ra (ngành `(chưa phân loại)` âm, mã âm) được IN RA dưới khối kèm số tiền:
  "Không vẽ: ¥−26.258.617 của 10 mã doanh thu âm (phí, chiết khấu)". Lặng lẽ bỏ thì
  tổng của cây ô lệch tổng ô chỉ số mà không ai biết vì sao.
- Bậc màu của bản đồ nhiệt và của cây ô đi theo **tăng trưởng**, 5 bậc đối xứng quanh
  0: ≤−20% · −20…−5% · −5…+5% · +5…+20% · ≥+20%. Màu lấy từ biến CSS (thêm vào
  `kome.css` cả khối sáng lẫn HAI khối tối — bất biến `color-scheme` của `CLAUDE.md`).
- Mọi phần tử SVG mang `<title>` ghi số thật, để rê chuột đọc được và trình đọc màn
  hình đọc được. Đây là cách duy nhất có "tooltip" khi không có JS.

### 4.3 `kome/tong_quan.py` (mới) — dữ liệu cho `/`

`tong_quan(conn, sale: str | None) -> TongQuan`. Nó gọi lại các hàm đã có thay vì viết
lại truy vấn:

| Khối | Nguồn |
|---|---|
| 4 ô chỉ số tháng | `mart.thang_den_hom_nay` |
| xu hướng 30 ngày | `mart.ban_theo_ngay`, 60 ngày cuối (30 ngày này + 30 ngày trước đó) |
| sức khoẻ khách | `mart.khach_360` đếm theo `trang_thai` (đúng truy vấn `/` đang chạy) |
| cần gọi hôm nay | `kome.khach_hang.can_xu_ly(conn, gioi_han=5, sale=sale)` |
| ngân sách tháng | `kome.bao_cao.tien_do_ngan_sach(conn)` |
| hàng cận hạn | `kome.san_pham.kho_hang(conn)` → 5 dòng đầu của `can_han`, số `qua_han` |

Mỗi khối một câu (các view khác hình, gộp chỉ để tiết kiệm lượt hỏi là đổi sự rõ ràng
lấy ~50 ms). Cả trang `/` chạy **≤ 11 truy vấn**: `tinh_tuoi` 2 · ba khối đầu 3 · cần
gọi 1 · ngân sách ≤ 3 · `kho_hang` 2. Có test đếm.

Trang `/` không gọi `tinh_bao_cao` nữa. Hiện nó chạy trọn 5 truy vấn của trang báo cáo
chỉ để lấy ba con số của kỳ.

---

## 5. `/bao-cao` — bố cục

Theo thứ tự trên trang (bám `Báo cáo.dc.html`):

1. Tiêu đề + chip chọn kỳ (đang có).
2. **4 ô chỉ số của kỳ**: Doanh thu thuần · Lãi gộp · Tỷ suất lãi gộp · Khách có đơn.
   Mỗi ô có sparkline 12 tháng của kỳ và một dòng so cùng kỳ từ `mart.ky_cung_ky`:
   - có tháng đối chiếu → "▲ 4,2% so cùng kỳ · 5 tháng đối chiếu (2026-03 → 2026-07)";
   - không có → "chưa có cùng kỳ để so — dữ liệu bắt đầu 2025-03-03".

   Dòng so sánh **luôn nói nó so bao nhiêu tháng**. Ô ghi doanh thu cả kỳ ¥1,5 tỷ cạnh
   dòng "▲4%" mà không nói 4% đó chỉ tính trên 5 tháng là hai con số trông như cùng một
   phép đo. Tỷ suất so bằng **điểm phần trăm** ("▲ 0,8 điểm"), không bằng %.
3. Ba khối ngân sách của 5a (không đổi).
4. **Doanh thu 12 tháng so cùng kỳ**: biểu đồ đang có + đường cùng kỳ nét đứt.
5. **Ngành hàng kéo doanh thu lên/xuống**: `ve_dong_gop` trên các tháng đối chiếu của
   kỳ. Tiêu đề phụ nói dải tháng. Không có tháng đối chiếu nào thì khối in một câu giải
   thích thay cho biểu đồ, và KHÔNG ẩn tiêu đề.
6. **Doanh thu đến từ danh mục nào**: cây ô cả kỳ, màu theo tăng trưởng cùng tháng của
   ngành (§3.4, cùng dải tháng đối chiếu). Ngành không có cùng kỳ thì màu trung tính.
7. **Tăng trưởng theo tháng và ngành**: bản đồ nhiệt.
8. **Doanh thu tập trung ở khách nào**: Pareto 20 khách + câu tóm tắt "10 khách lớn nhất
   = 21,6% doanh thu kỳ này, trên N khách có doanh thu".
9. **Bảng số chi tiết theo tháng**: `<details>` đóng sẵn, 12 dòng: Doanh thu · Lãi gộp ·
   Tỷ suất · Cùng kỳ · So cùng kỳ · Số phiếu. Cùng kỳ trống thì in "—" kèm chú thích,
   theo nếp bảng đang có.
10. Hai bảng giữ nguyên: 10 mặt hàng lãi gộp cao nhất · theo người phụ trách.

Ngân sách truy vấn của `/bao-cao`: **≤ 11** (kỳ + cùng kỳ 1 · tháng 1 · Pareto 1 · sản
phẩm 1 · người phụ trách 1 · ngành × tháng 1 · ngành × kỳ 1 · ngân sách ≤ 3). Ngành ×
tháng và ngành × kỳ KHÔNG gộp vào một câu: câu gộp sẽ tham chiếu
`ban_theo_nganh_thang_so_sanh` hai lần (một lần trực tiếp, một lần qua
`nganh_ky_cung_ky`), tức đánh giá view đó hai lần — đúng lớp lỗi của bất biến CTE. Có
test đếm.

---

## 6. `/` — Dashboard chung

Một bố cục cho mọi người. Không kéo thả, không chọn khối, không cài đặt theo vai trò
(câu trả lời của chủ doanh nghiệp).

1. Dải "hôm nay đã có dữ liệu chưa" (đang có, không đổi).
2. **4 ô chỉ số tháng đến hôm nay**: Doanh thu · Lãi gộp · Tỷ suất · Khách có đơn, mỗi ô
   so cùng kỳ **cùng số ngày** (§3.7). Nhãn nói rõ dải ngày: "1–31/07/2026 so với
   1–31/07/2025".
3. **Tiến độ ngân sách tháng**: một thanh tổng + một thanh mỗi người, tái dùng
   `rong_thanh`/`rong_moc` của `TienDoNguoi`. Chưa đặt chỉ tiêu nào thì in "Chưa đặt
   chỉ tiêu tháng này", kèm liên kết `/ngan-sach` **chỉ khi** người đang xem có cờ
   `duoc_sua_ngan_sach`. Liên kết tới một trang 403 là một lời hứa trang không giữ.
   Có liên kết "Xem chi tiết" sang `/bao-cao`.
4. **Xu hướng 30 ngày**: cột doanh thu từng ngày + đường 30 ngày ngay trước đó, xếp
   theo thứ tự ngày (ngày thứ 1 với ngày thứ 1). Không dùng "cùng thứ trong tuần" — giữ
   đơn giản và nói rõ trong chú giải.
5. **Sức khoẻ khách hàng**: một thanh chia đoạn theo `trang_thai` của `mart.khach_360`
   (cùng bốn nhóm `/` đang hiện), mỗi đoạn là một liên kết sang `/khach-hang?loc=…`.
6. Hai cột cạnh nhau:
   - **Cần gọi hôm nay**: 5 khách đầu của `can_xu_ly`, mặc định theo người đăng nhập
     (cùng nếp `/can-xu-ly`), liên kết "Xem tất cả" sang `/can-xu-ly`.
   - **Hàng cận hạn**: 5 lô đầu của `can_han` + số lô đã quá hạn, liên kết `/kho-hang`.
     Ngưỡng là `kome.san_pham.CAN_HAN_NGAY`. Hàm `kho_hang` được gọi thẳng, nên "cận
     hạn" có đúng một định nghĩa.
7. **Chưa có dữ liệu**: một dòng chữ nhỏ ghi Công nợ · Dòng tiền · Mua hàng · Khiếu nại
   · Thời tiết — "chưa có nguồn dữ liệu, sẽ thêm khi nạp được". Dòng "Tồn kho — chưa
   có" hiện nay phải bỏ: `/kho-hang` đã có từ đợt 4b.

Khối cần gọi lọc theo người đăng nhập; các khối số tổng thì **không lọc**. Dashboard là
"công ty đang thế nào". Lọc tổng công ty theo từng sale là một câu hỏi khác, và nó đã có
nhà ở `/bao-cao` (bảng theo người phụ trách) và `/khach-hang?nv=`. Ghi rõ dưới khối:
"Danh sách của {tên} · Xem của mọi người".

---

## 7. Kiểm thử

Tất cả chạy trên `DATABASE_URL_TEST`, dữ liệu gieo tay.

- `tests/test_phan_tich_mart.py`:
  - tổng các ngành của một tháng = `ban_theo_thang` của tháng đó, kể cả dòng mã hàng
    rỗng;
  - ngành bán năm ngoái mà năm nay không bán vẫn có dòng, `doanh_thu_thuan = 0`;
  - không sinh dòng cho tháng không có trong kho;
  - `co_cung_ky` sai khi M−12 không có trong kho, và `dt_cung_ky` khi đó là NULL;
  - `tang_truong` NULL khi cùng kỳ ≤ 0;
  - `ky_cung_ky` chỉ tính các tháng đối chiếu, và `so_khach` đếm khách DISTINCT qua
    nhiều tháng;
  - tổng `chenh_lech` của `nganh_ky_cung_ky` = `dt − dt_ck` của `ky_cung_ky`;
  - `tap_trung_khach`: khách có hai người phụ trách trong kỳ chỉ ra một dòng; `luy_ke`
    của dòng cuối = 1;
  - `ban_theo_ngay`: ngày không bán có dòng 0, không có ngày sau `hom_nay`;
  - `thang_den_hom_nay`: cùng kỳ tính cùng số ngày chứ không trọn tháng; 29/2 kẹp về
    28/2;
  - `has_table_privilege` SELECT của cả ba vai trò trên mỗi view mới;
  - EXPLAIN của `ban_theo_nganh_thang_so_sanh` có đúng MỘT lượt gộp trên
    `fact_sales_line` (nếp test của migration 028).
- `tests/test_bao_cao_phan_tich.py`: hình học (cây ô phủ kín khung, không ô nào diện
  tích âm; sparkline đứt ở `None`; ô nhiệt không có cùng kỳ mang lớp sọc); ngân sách
  ≤ 11 truy vấn; trang render khi CSDL rỗng; dòng "không vẽ" hiện khi có doanh thu âm.
- `tests/test_tong_quan.py`: ≤ 11 truy vấn; ô chỉ số tháng so cùng số ngày; liên kết
  `/ngan-sach` chỉ có khi có cờ; dòng "Tồn kho — chưa có" không còn; khối cần gọi mặc
  định lọc theo người đăng nhập.
- Bộ test cũ phải xanh nguyên, trừ các khẳng định về bố cục cũ của `/` (được viết lại,
  không xoá mà không thay).

---

## 8. KIỂM TAY (chủ doanh nghiệp, sau khi chạy migration 029)

1. Mở `/bao-cao` kỳ 7, đọc thời gian ở lần mở thứ hai: **dưới 1.500 ms**.
2. Mở `/`, lần thứ hai: **dưới 1.500 ms**.
3. Đối chiếu doanh thu kỳ 7 trên ô chỉ số với tổng 12 dòng của bảng chi tiết: phải
   bằng nhau đến từng yên.
4. Đối chiếu ô "Doanh thu tháng đến hôm nay" của `/` với OBC 売上明細表 cùng dải ngày.
5. Chuyển máy sang chế độ tối: bản đồ nhiệt và cây ô phải đọc được.

---

## 9. Phán quyết thay chủ doanh nghiệp

| # | Phán quyết | Vì sao | Sai thì tốn gì |
|---|---|---|---|
| P1 | Ngành hàng = `food_category_name` | cột duy nhất có nghĩa "ngành"; `kind` chỉ có 有形/無形 | đổi một biểu thức trong `029` bằng migration mới |
| P2 | So cùng kỳ theo cùng tháng, và luôn nói bao nhiêu tháng | kỳ 6 chỉ có 5 tháng; so cả kỳ ra số vô nghĩa | không |
| P3 | Dashboard không lọc theo người đăng nhập, trừ khối cần gọi | "công ty thế nào" là một câu hỏi; lọc là mặc định tiện dụng, không phải hàng rào | thêm tham số `sale` cho `tong_quan` |
| P4 | Không dựng khối thiếu nguồn (công nợ, dòng tiền, mua hàng, khiếu nại, thời tiết, việc hôm nay tổng hợp) | số bịa trên dashboard phá niềm tin vào cả trang | không — thêm khi có nguồn |
| P5 | Không có nút "Tải Excel" | chưa ai hỏi; bảng chi tiết chép được | một route CSV |
| P6 | Không có khối "khách hiện hữu và khách mới" | dữ liệu mới từ 2025-03, nên mọi khách của kỳ 6 đều là "mới" | định nghĩa lại khi có dữ liệu dài hơn |
| P7 | Xu hướng 30 ngày so với 30 ngày ngay trước, không so cùng thứ | đơn giản, nói rõ trong chú giải | đổi một view |
| P8 | Không kéo thả, không chọn khối | câu trả lời của chủ doanh nghiệp | — |

---

## 10. Không làm trong 5b

Những mục đã quyết không làm ở §9 (P4–P6, P8) · cột ngày lễ trong `core.dim_date` ·
bản đồ Leaflet (đang tạm dừng vì chưa duyệt gửi địa chỉ khách ra ngoài) · hoa hồng.
