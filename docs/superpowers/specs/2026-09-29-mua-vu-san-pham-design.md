# Mùa vụ sản phẩm (`/mua-vu`) — đặc tả thiết kế

Ngày: 2026-09-29 · Người yêu cầu: chủ DN · Trạng thái: đã duyệt trong trò chuyện

## 1. Mục đích

Kéo một thanh thời gian bên dưới, treemap phía trên đổi liên tục, để trả lời:
**mùa này mã nào bán chạy, và sang mùa khác nó còn bán chạy không** — so qua các năm.
Ba chỉ số: doanh thu thuần, lãi gộp, số lượng.

Dữ liệu thật hiện có: 2025-03-03 → 2026-09-28 (19 tháng), 232 mã, 11 ngành,
~48.000 cặp (mã × ngày có bán) trong `mart.ban_den_moc`. Xuân/hè/thu so được hai năm;
đông mới có một lần.

## 2. Quyết định đã chốt

| Câu hỏi | Chốt |
|---|---|
| Mỗi nấc thanh kéo | **Một ngày** (~570 nấc), từ ngày bán đầu tiên tới ngày bán cuối cùng |
| Con số của mỗi nấc | **Cửa sổ trượt N ngày kết thúc ở ngày đó**, N ∈ {7, 30, 90}, mặc định 30 |
| Cấu trúc treemap | **Hai tầng ngành → mã**, hiện MỌI mã (không gộp "(khác)"); ô quá nhỏ chỉ không in chữ |
| Loại khỏi hình | Phí & điều chỉnh (048), hàng tặng POSM (049) — tiền vẫn trong tổng, in ở dòng "Không vẽ". Mã nội bộ (044) đã bị `ban_den_moc` bỏ |
| Mã ※終売※ | **Vẫn hiện** ở những ngày nó có bán — đây là xem lại lịch sử (khác danh mục `/san-pham`, bất biến 050 là về "hiện tại") |
| Khoảng xem chung | Màn này **KHÔNG** theo khoảng xem (thanh kéo là trục thời gian của chính nó); thanh chọn khoảng ẩn (`main.tsx::boChon` trả `hien: false`) |
| URL | `?cs=` (chỉ số: `dt`/`lg`/`sl`) và `?n=` (7/30/90) lên URL qua `giuKhoang()`; vị trí thanh kéo KHÔNG lưu |

## 3. Bố cục

1. **Thanh chọn**: chỉ số (Doanh thu · Lãi gộp · Số lượng) · cửa sổ (7 · 30 · 90 ngày) ·
   chip ngành (bật/tắt; tắt ngành = bỏ khỏi hình VÀ cộng vào "Không vẽ" với nhãn "ngành đang tắt")
   · ô tìm mã → **đánh dấu** một mã (viền đậm, giữ khi kéo; `Esc` bỏ).
2. **Treemap** (SVG tự vẽ, không thư viện): diện tích theo chỉ số đang chọn, màu theo ngành
   (dùng lại bảng màu ngành của cây ô `/bao-cao`). Ô nổi (`chung/ONoi.tsx`, luật chạm hai lần
   như `BieuDo`): tên mã · ngành · số của cửa sổ · **cùng cửa sổ năm trước** (hoặc "—") · hạng
   trong ngành · % của ngành. Chạm/bấm lần 2 → `/san-pham/{mã}` (qua `giuKhoang()`); mã đã bị ẩn
   khỏi `/san-pham` (※終売※ hết tồn, bất biến 050) → không có liên kết, ô nổi ghi "đã ngừng kinh doanh".
3. **Dòng "Không vẽ"** dưới treemap, luôn hiện khi khác 0:
   "Không vẽ: phí & điều chỉnh ¥x · hàng tặng ¥y · n mã ≤ 0 trong cửa sổ ¥z · ngành đang tắt ¥w".
   Với chỉ số Số lượng, phí/POSM vẫn không vẽ nhưng in số lượng của chúng.
4. **Thanh thời gian**:
   * biểu đồ nhỏ doanh thu thuần theo ngày (toàn bộ, không theo ngành tắt/bật) làm nền;
   * vạch mốc đầu tháng, dải màu nhạt bốn mùa (Xuân 3–5 · Hè 6–8 · Thu 9–11 · Đông 12–2);
   * vùng tô = cửa sổ đang xem; con trượt = ngày cuối cửa sổ;
   * ▶ chạy tự động (mặc định 1 ngày / 80 ms; bấm lại dừng) · ◀ ▶ lùi/tiến một ngày · phím ← →
     (Shift + ← → = 7 ngày) · Home/End;
   * nhãn lớn: "30 ngày · 16/06 → 15/07/2025". Cửa sổ bắt đầu trước ngày dữ liệu đầu tiên →
     thêm "(chỉ có từ 03/03/2025 — cửa sổ chưa đủ N ngày)".
   * Vị trí mở trang: ngày bán cuối cùng.

**Chuyển động**: ô dời/co giãn bằng CSS transition (~200 ms, `transform` + `width/height` trên
`<rect>` qua thuộc tính `x/y/width/height`); `prefers-reduced-motion` → không transition. Khi đang
kéo liên tục, mỗi khung hình chỉ vẽ lại một lần (`requestAnimationFrame`).

**Ổn định vị trí**: thứ tự NGÀNH cố định theo tổng chỉ số trên TOÀN kỳ dữ liệu (không đổi khi kéo)
— ngành nhảy chỗ là mất dấu. Trong mỗi ngành mã xếp giảm dần theo giá trị cửa sổ (squarify cần thế).

## 4. Dữ liệu

### 4.1 Migration `058_mua_vu.sql` — `mart.mua_vu_ngay`

```sql
CREATE VIEW mart.mua_vu_ngay AS
SELECT CASE WHEN mart.la_phi_dieu_chinh(f.product_code, p.kind_code) THEN '__phi'
            WHEN mart.la_hang_tang(p.food_category_name)             THEN '__tang'
            ELSE f.product_code END                       AS ma,
       f.sales_date                                       AS ngay,
       sum(f.amount - f.tax_amount)                       AS doanh_thu_thuan,
       sum(f.gross_profit)                                AS lai_gop,
       sum(f.qty)                                         AS so_luong
FROM mart.ban_den_moc f
LEFT JOIN core.dim_product p ON p.product_code = f.product_code
GROUP BY 1, 2;
```

* Đọc `mart.ban_den_moc` (bất biến 040/044): bỏ mã nội bộ, quay về theo mốc, giữ 赤伝.
* Phí xét TRƯỚC POSM (cùng thứ tự `mart.la_dong_hang_tang`). Hai mã giả `__phi` / `__tang` không
  bao giờ trùng mã OBC (mã OBC không có `_`).
* Doanh thu thuần = `amount - tax_amount`, đúng ở cả `uriage` lẫn `meisai` (bẫy #8).
* `GRANT SELECT` cho `kome_app`, `kome_report`, `kome_ingest` (ALTER DEFAULT PRIVILEGES đã phủ,
  vẫn ghi tường minh như các migration mart khác). Chạy bằng `postgres`.

### 4.2 `kome/mua_vu.py::du_lieu(conn) -> dict` — ĐÚNG MỘT lượt hỏi

Một câu, hai CTE: dòng của view + danh mục mã (`core.dim_product`: tên theo công thức
`san_pham_360.ten_hang`, ngành qua `mart.ten_nganh(food_category_name)`, cờ `an` =
`product_code IN (SELECT product_code FROM mart.ma_ngung_ban_an)` để biết có liên kết sang `/san-pham` không).
Danh mục = mọi mã XUẤT HIỆN trong view (LEFT JOIN sang `dim_product`): mã bán mà không có trong
master vẫn có dòng — tên = chính mã, ngành = `'(chưa phân loại)'` — không được rơi mất tiền.
Trả dạng **cột gọn** (không object mỗi dòng):

```json
{
  "ngay_dau": "2025-03-03", "ngay_cuoi": "2026-09-28",
  "ma":   [{"ma": "…", "ten": "…", "nganh": "…", "an": false}, …],
  "nganh": ["…", …],
  "dong": {"i": [chỉ số mã], "d": [số ngày tính từ ngay_dau], "dt": […], "lg": […], "sl": […]},
  "phi": 0, "tang": 1
}
```

`phi`/`tang` = chỉ số của hai mã giả trong mảng `ma`. `sl` là số thập phân (bẫy #2), tiền là số
nguyên. Ước lượng ~48.000 dòng ≈ 1 MB JSON thô (nén gzip nhỏ hơn nhiều).

### 4.3 `GET /api/mua-vu`

`_chup(request, KHOA_MUA_VU, MV.du_lieu, "Không đọc được dữ liệu mùa vụ.", chi_nap=True)` —
ảnh chụp theo phiên bản dữ liệu NẠP (không đọc bảng `app`). Không nhận tham số khoảng: trúng ảnh
chụp = 1 lượt hỏi, trượt = 2 (phiên bản + dữ liệu). Thêm vào `tests/test_api.py::NGAN_SACH_TRUY_VAN`.
`GET /mua-vu` trả vỏ React (`app.py`, cùng nếp `/san-pham`).

## 5. Tính ở trình duyệt (`giao_dien/src/mua_vu/`)

* `du_lieu.ts`: dựng mảng **luỹ kế** `L[chỉ số][mã][ngày]` (Float64Array, 232 × 575 × 3 ≈ 400k số,
  ~3 MB bộ nhớ) một lần khi tải. Giá trị cửa sổ `[a, b]` của một mã = `L[b] − L[a−1]` — O(1).
  Cùng cửa sổ năm trước: `[a', b']` = cùng ngày lịch lùi 1 năm (29/2 → 28/2, đúng
  `mart.thang_den_hom_nay`); `a' < ngay_dau` → "—" (không so cửa sổ thiếu ngày).
* `cay_o.ts::squarify` — bản TypeScript của `kome/ve_phan_tich.py::_squarify`. **Ngoại lệ có chủ ý**
  của nếp "hình học biểu đồ tính ở Python" (giai đoạn 3): kéo liên tục thì không hỏi máy chủ mỗi
  nấc được. Hai bản chạy CHUNG `tests/du_lieu/squarify_ca.json` (cùng nếp `luoi_nen_ca.json`):
  `tests/test_squarify_ca.py` (Python) và `cay_o.test.ts` (Vitest) — sửa một bản là sửa cả hai.
* `cay_o.ts::xep(gia_tri_ma, nganh_bat, thu_tu_nganh, khung)` → `{o: [...], khong_ve: {...}}`.
  Diện tích ngành = tổng các mã DƯƠNG của ngành (cùng lý lẽ `doanh_thu_ve` của `ve_cay_o`); mã ≤ 0
  vào `khong_ve.am`. **Bất biến đối soát**: với mọi đầu vào,
  `Σ ô được vẽ + khong_ve.phi + khong_ve.tang + khong_ve.am + khong_ve.tat = tổng cửa sổ` (mọi mã
  kể cả hai mã giả). Có test canh ở `cay_o.test.ts`.
* Định dạng số qua `dinh_dang.ts` (chuẩn Nhật, 万/億).

## 6. Lưu ý in trong ⓘ (`Khoi.cach_tinh`) và cảnh báo

* ⓘ: "Mỗi ô = tổng N ngày kết thúc ở ngày đang chọn. Doanh thu thuần (chưa thuế), đã gồm phiếu đỏ
  (trả hàng, số âm). Không tính mua hàng của nhân viên. Phí & điều chỉnh và hàng tặng không phải sản
  phẩm nên không vẽ, nhưng tiền vẫn có trong tổng."
* ⓘ khi chỉ số = Số lượng: "Số lượng cộng lẫn thùng (ケース) và lẻ (バラ): so MỘT mã qua các mùa là
  đúng, so kích thước ô giữa hai mã khác nhau thì không."
* Cảnh báo (`Khoi.canh_bao`, luôn hiện khi xảy ra): cửa sổ chưa đủ N ngày; năm trước không có dữ
  liệu cho cửa sổ này.

## 7. Thanh bên

`giao_dien/src/khung/muc.ts`: nhóm có "Sản phẩm", mục mới
`{ ma: "muavu", nhan: "Mùa vụ sản phẩm", url: "/mua-vu", icon: "chart" }` ngay sau "Sản phẩm".
Icon `chart` có sẵn trong bộ 24 icon của gói thiết kế — **TA CHỌN** (gói thiết kế không có màn này),
ghi vào chú thích đầu `muc.ts` như bất biến Đợt 4d yêu cầu.

## 8. Test

* `tests/test_mua_vu.py`
  * `mua_vu_ngay` cộng theo tháng × mã (trừ mã giả) = `mart.san_pham_theo_thang` của mã hàng thật
    (ba chỉ số);
  * tổng mọi dòng (kể cả `__phi`/`__tang`) theo ngày = `Σ (amount − tax_amount)` của
    `mart.ban_den_moc` ngày đó — không mất tiền;
  * dòng phí vào `__phi`, dòng POSM vào `__tang`, dòng 無形 trong `雑貨_VNM` vào `__phi` (phí trước);
  * phiếu đỏ giữ số âm; mã nội bộ không có mặt; mốc lùi (`kome.moc`) cắt đúng;
  * `du_lieu()` chạy đúng 1 truy vấn; `sl` giữ phần thập phân; mã giữ số 0 đầu.
* `tests/test_squarify_ca.py` + `cay_o.test.ts`: cùng file ca; đối soát tổng; ổn định thứ tự ngành.
* `tests/test_api.py`: ngân sách truy vấn `/api/mua-vu`; chưa đăng nhập → 401 JSON.
* `tests/test_tai_lieu.py` / `test_cot_dung.py`: chạy lại `scripts/sinh_tai_lieu.py` và
  `scripts/sinh_cot_dung.py` (migration mới + mô-đun mới đọc `mart` — khai vào `MAN`).
* `npm run build` + `tests/test_api.py::test_ban_build_khop_ma_nguon`.

## 9. Không làm (cố ý, YAGNI)

* Không lọc theo khách / người phụ trách / tỉnh.
* Không lưu vị trí thanh kéo lên URL.
* Không dự báo mùa, không tự gắn nhãn "mã theo mùa".
* Không theo khoảng xem chung của website.

## 10. Triển khai

**Migration 058 phải chạy TRƯỚC khi triển khai.** Ghi thêm một dòng vào bảng "Các trang của web
app" và một mục bất biến ngắn trong `CLAUDE.md` (ngoại lệ hình học ở trình duyệt + file ca chung).
