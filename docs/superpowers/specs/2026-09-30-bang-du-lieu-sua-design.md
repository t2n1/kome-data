# Bảng dữ liệu sửa trực tiếp (Kho dữ liệu › Bảng dữ liệu) — đặc tả

Ngày: 2026-09-30 · Chủ DN duyệt trong chat cùng ngày: cách A ("lớp bản sửa cạnh dữ liệu OBC"), phác thảo bảng tính
("oke rồi làm đi"). Ba lựa chọn đã chốt:
- nạp OBC mới mà OBC **đổi đúng ô đó** thì OBC thắng;
- bản sửa có tác dụng ở **mọi màn hình**;
- chỉ người có **cờ quyền riêng** mới sửa được;
- sửa được **mọi cột dữ liệu gốc**: danh mục khách, danh mục sản phẩm, giá 売価No., tồn và hạn theo lô.

## 1. Luật số một — cái gì đổi, cái gì không

`core` VẪN chỉ đọc với web. Không câu UPDATE nào vào `core`. Loader, hoàn tác, trang Kho dữ liệu › Duyệt bảng vẫn thấy đúng dữ liệu
OBC. Bản sửa nằm ở sổ CHỈ THÊM `app.sua_du_lieu`. Mọi chỉ số đọc **giá trị hiệu lực** qua bốn view của `mart`:
`mart.dim_customer`, `mart.dim_product`, `mart.bang_gia_kome`, `mart.ton_hien_tai`.

Hệ quả có chủ ý:
- Con số trên web (theo ngành / tỉnh / người phụ trách / hạng, tồn, giá so đối thủ) có thể KHÁC OBC cho tới khi ai đó sửa
  trong OBC. Màn luôn chỉ ra ô lệch và có bộ lọc "Đã sửa trên web, OBC chưa có".
- Không đổi: tiền trên phiếu và người phụ trách ghi trên phiếu (`core.fact_sales_line`), sổ công nợ.

## 2. Sổ `app.sua_du_lieu` (migration `072`)

Mỗi dòng có các cột sau:
- `id bigserial`
- `bang text CHECK IN ('khach','san_pham','gia','ton')`
- `khoa text NOT NULL`
- `cot text NOT NULL`
- `gia_tri text` — giá trị mới; NULL = để trống.
- `gia_tri_obc text` — giá trị OBC của ô LÚC SỬA, dạng `::text` của cột nguồn.
- `gia_tri_truoc text` — giá trị hiệu lực trước lần sửa, dùng cho nhật ký.
- `bo boolean NOT NULL DEFAULT false` — true = bỏ bản sửa, về OBC.
- `nguoi_dung_id bigint REFERENCES app.nguoi_dung`
- `luc timestamptz DEFAULT now()`

Sổ CHỈ THÊM: `REVOKE UPDATE, DELETE` khỏi `kome_app`, cùng nếp 030 / 063 / 070. Chỉ mục `(bang, khoa, cot, id DESC)`.

**CHECK giá trị ở mức CSDL** (`sua_du_lieu_cot_check` + `sua_du_lieu_gia_tri_check`, hàm `mart.la_ngay_obc`): `kome_app` INSERT
thẳng được và sổ chỉ thêm, nên một dòng sai kiểu là MỌI view hiệu lực nổ vĩnh viễn (`::numeric`, `to_date`) mà không ai xoá được.
Vì vậy CSDL chặn, không chỉ Python: `stock_qty` / `case_qty` / `pack1_base_qty` là số không âm ≤ 4 chữ số thập phân; `gia_chua_thue`
> 0, không số mũ / NaN / Infinity; `best_before` rỗng, `賞味期限なし` hoặc ngày OBC CÓ THẬT (`mart.la_ngay_obc` — regex đơn thuần để
`2027年02月30日` lọt qua rồi `to_date` nổ). Dòng `bo = true` không xét giá trị.

Khoá theo bảng:

| bang | khoa | cot được phép |
|---|---|---|
| `khach` | `customer_code` | `customer_name, branch_name, rank_code, salesperson_code, closing_day_code, postcode, prefecture, city, address, building, phone, transfer_account` |
| `san_pham` | `product_code` | `product_name, name_ja, kind_code, food_category_code, rank_code, compete_code, barcode, unit, case_qty, shelf_code, introduced_on, pack1_code, pack1_base_qty` |
| `gia` | `mã|quy cách|bậc` (vd `NT01|02|01`) | `gia_chua_thue` |
| `ton` | `mã|kho` (vd `NT01|0001`) | `stock_qty, best_before` |

Mã (`customer_code`, `product_code`) KHÔNG sửa được — nó là khoá nối mọi thứ. Không thêm, không xoá dòng: khách / mã /
bậc giá / lô mới vẫn đến từ OBC. Ô giá / tồn TRỐNG, tức ô OBC không có, thì không sửa được.

### 2.1 Luật hiệu lực — viết ĐÚNG MỘT LẦN

- `mart.sua_moi_nhat`: dòng MỚI NHẤT của mỗi `(bang, khoa, cot)`. Dòng `bo = true` nghĩa là không có bản sửa.
- `mart.sua_theo_khoa`: gom các bản sửa đó thành MỘT `jsonb` mỗi `(bang, khoa)`, dạng `{cot: [gia_tri, gia_tri_obc]}`.
- `mart.ap_sua(obc text, j jsonb, cot text) RETURNS text` (`LANGUAGE sql IMMUTABLE`):
  - nếu `j` có `cot` VÀ `j->cot->>1 IS NOT DISTINCT FROM obc` thì trả `j->cot->>0`;
  - không thì trả `obc`.
  - Nghĩa là: OBC vẫn ghi đúng giá trị lúc sửa → bản sửa thắng; OBC đã ghi khác → OBC thắng, bản sửa tự hết hiệu lực,
    không cần ai dọn.
- `mart.lech_obc(obc text, j jsonb, cot text) RETURNS boolean`: bản sửa đang thắng (để vẽ vạch xanh / đếm "OBC chưa có").

Mọi view hiệu lực gọi hai hàm đó — không view nào viết lại điều kiện.

### 2.2 Cột cặp mã–tên

`rank_code` → `rank_name`, `salesperson_code` → `salesperson_name`, `closing_day_code` → `closing_day_name`,
`kind_code` → `kind_name`, `food_category_code` → `food_category_name`.

- Người sửa chọn MÃ trong danh sách có sẵn. Máy chủ từ chối mã lạ.
- View lấy TÊN theo mã hiệu lực:
  - `salesperson_name` ← `core.dim_salesperson.ten`;
  - các cặp còn lại ← từ điển mã → tên dựng từ chính bảng OBC (bản hiện hành: `DISTINCT ON (mã)`, tên không rỗng thắng).
- Mã không bị sửa thì tên giữ nguyên OBC.
- Ngành hàng (`food_category_name`) nhờ vậy luôn là một tên OBC có thật → `mart.ten_nganh` / báo cáo ngành không đẻ ra ngành mới.

## 3. View hiệu lực (072)

- **`mart.dim_customer`**: CÙNG cột, CÙNG thứ tự và kiểu với `core.dim_customer`, MỌI phiên bản SCD2. Bản sửa chỉ áp lên dòng
  `is_current`, vì các view chỉ đọc bản hiện hành (đã kiểm: không view nào đọc bản cũ).
  - Nạp OBC đổi một cột khác của khách thì sinh phiên bản mới, nhưng cột đã sửa vẫn bằng `gia_tri_obc` → bản sửa vẫn thắng.
- **`mart.dim_product`**: cùng cột với `core.dim_product`.
- **`mart.bang_gia_kome`** (thân mới, thêm HAI cột ở CUỐI: `gia_obc` — giá OBC chưa thuế, đúng số mà `gia_tri_obc` so — và `da_sua boolean`):
  - `gia_chua_thue` của dòng hiện hành = `ap_sua(gia OBC::text, j, 'gia_chua_thue')::numeric`.
  - `doi` và `duoi_gia_von` tính trên giá hiệu lực. `hai_cot_lech` giữ theo OBC.
  - `mart.gia_kome_bang`, trang đối thủ, `/bang-gia`, tab Giá & lãi tự đi theo.
- **`mart.ton_hien_tai`** (thân mới, thêm BỐN cột ở CUỐI: `so_luong_obc`, `best_before_obc`, `sua_so_luong`, `sua_han` — thay cho một cột
  `da_sua`, vì số lượng và hạn là hai ô sửa độc lập và `gia_tri_obc` phải lấy ĐÚNG chữ OBC mà view so):
  - `so_luong` = hiệu lực của `stock_qty`, `best_before` = hiệu lực.
  - `gia_tri` = `stock_value` của OBC, hoặc `round(so_luong × stock_unit_cost)` khi số lượng bị sửa.
  - `loai_han` / `han_con_lai` tính trên hạn hiệu lực.
  - `ton_theo_lo`, `san_pham_360`, `ma_ngung_ban_an`, `/kho-hang`, cận hạn tự đi theo.
  - Số tồn đổi gần như mỗi ngày, nên bản sửa số tồn thường chỉ sống tới ảnh chụp sau. Màn nói ra điều này.

### 3.1 Chuyển mọi chỗ đọc sang view hiệu lực

- Migration 072, khối `DO` đọc định nghĩa SỐNG trong danh mục Postgres:
  - mọi view `mart.*` có tham chiếu `core.dim_customer` / `core.dim_product` → `pg_get_viewdef`, đổi chuỗi sang
    `mart.dim_customer` / `mart.dim_product`, `CREATE OR REPLACE VIEW` (cột ra y hệt nên không phải DROP view phụ thuộc);
  - mọi hàm `mart.*` có tham chiếu → `pg_get_functiondef`, đổi chuỗi, chạy lại.
  - Trừ chính hai view hiệu lực.
- Tên view hiệu lực trùng tên bảng (`dim_customer`) có chủ ý: `pg_get_viewdef` in cột dạng `dim_customer.cot` khi bảng không
  có bí danh, đổi schema thì tên đó vẫn trỏ đúng.
- **Test canh (bắt buộc):** trên danh mục của CSDL test, KHÔNG view / hàm nào trong `mart` (trừ hai view hiệu lực) còn chứa
  `core.dim_customer` / `core.dim_product`. Lý do: migration sau chép thân view từ file migration cũ sẽ lặng lẽ đưa chỗ đọc
  OBC thô trở lại.
- Đổi phía nguồn: thêm một cột vào `core.dim_customer` / `core.dim_product` nay phải tạo lại `mart.dim_*` (có test canh
  cùng cột / cùng kiểu / cùng thứ tự: `tests/test_bang_du_lieu_mart.py::test_view_hieu_luc_cung_cot_cung_kieu_voi_core`).
- Python: mọi chỗ HIỂN THỊ / phân tích / kiểm mã tồn tại đổi sang `mart.dim_*`. Giữ `core`: loader, pipeline, hoàn tác,
  `nhat_ky_nap`, `bang_kho`, và chính `kome/bang_du_lieu.py` (cần giá trị OBC). Test canh: danh sách trắng các file Python
  được nhắc `core.dim_customer` / `core.dim_product`.
- `kome_app` / `kome_report` / `kome_ingest` được SELECT bốn view hiệu lực và `mart.sua_*`.

## 4. Ảnh chụp, nhật ký, quyền

- `anh_chup._PHIEN_BAN` VÀ `_PHIEN_BAN_NAP` thêm `(SELECT max(id) FROM app.sua_du_lieu)`: bản sửa là "dữ liệu mới" như một
  lần nạp. Luật `chi_nap` ghi lại: không đọc bảng `app` nào NGOÀI `app.sua_du_lieu`.
- `/nhat-ky`: thêm nhánh `'du_lieu'` vào `_NGUON`:
  - đối tượng = `bang: khoa`, chi tiết = cột;
  - trước = `gia_tri_truoc`, sau = `gia_tri` (hoặc "về OBC" nếu `bo`).
- Cờ mới `app.nguoi_dung.duoc_sua_du_lieu boolean NOT NULL DEFAULT false`:
  - `nhat_ky_quyen` CHECK thêm cờ đó;
  - `ND.CO_QUYEN` thêm ở CUỐI; `dat_quyen(..., sua_du_lieu=None)`;
  - `scripts/tao_nguoi_dung.py quyen --sua-du-lieu | --bo-sua-du-lieu`;
  - Cài đặt tự có cột (dựng từ `co_quyen`); `window.__KOME__.nguoi.duoc_sua_du_lieu`.
  - Không có cổng đăng nhập (máy công ty thiếu `KOME_SESSION_SECRET`) thì ai cũng sửa được — cùng nếp hai cờ cũ.
- Trang nằm dưới `/kho-du-lieu`, nên XEM cần `duoc_vao_kho_du_lieu`. SỬA cần thêm `duoc_sua_du_lieu`: API ghi trả 403 JSON,
  giao diện vẽ chỉ-xem.

## 5. API (`kome/bang_du_lieu.py`, `kome/web/api.py`)

### `GET /api/kho-du-lieu/bang-du-lieu?loai=sp|kh`

Trả MỘT lượt hỏi, không qua ảnh chụp, `no-store`:

```
{ loai, cot: [{ma, nhan, nhom, kieu: 'chu'|'so'|'ngay'|'chon', sua: bool, chon?: [[mã, nhãn]]}],
  dong: [{k, o: {ma_cot: giá trị hiệu lực}}],
  lech: {"<k>	<ma_cot>": {obc, luc, ai}},   // ô bản sửa đang thắng; khoá nối bằng TAB (mã cột / khoá có thể chứa '|')
  anh_ton, lan_nap_gia }                      // cùng cấp với loai / cot / dong, KHÔNG nằm trong `moc`
```

Nhóm cột:
- **Sản phẩm**
  - "Danh mục OBC": các cột §2.
  - "Giá 売価No.": một cột mỗi (bậc × quy cách) có dữ liệu, `gia:<qc>|<bậc>`, sửa được ô có giá.
  - "Tồn & hạn theo lô": `ton:<kho>` / `han:<kho>` mỗi kho của `core.dim_warehouse`, ảnh chụp ≤ mốc.
  - "Chỉ số (chỉ xem)": doanh thu 12 tháng, tồn tổng.
- **Khách**
  - "Danh mục OBC".
  - "Chỉ số (chỉ xem)": doanh thu 12 tháng (`mart.doanh_thu_12t`), lần mua cuối.
- Hạn hiển thị / nhập dạng `YYYY-MM-DD` hoặc "không hạn". Máy chủ đổi qua lại với chữ OBC (`YYYY年MM月DD日` / `賞味期限なし`).

### `POST /api/kho-du-lieu/bang-du-lieu/luu`

Thân: `{loai, o: [{k, cot, gia_tri, thay}]}`. `thay` = giá trị hiệu lực trình duyệt đã thấy.
**Trình duyệt GHI LẠI `thay` ngay lúc ô vào chờ lưu lần đầu** (`logic.ts::ChoLuu.thay`), không đọc lại từ đệm lúc bấm Lưu: đệm có
thể đã đổi (tải lại, "Lấy bản mới", dòng đọc lại mang số người khác vừa ghi) — đọc lúc lưu là lặng lẽ "rebase" ô lên số mới và
409 không bao giờ nổ (mất cập nhật).

Máy chủ làm theo thứ tự:
1. Kiểm cờ quyền → 403.
2. Kiểm từng ô (cột được phép, kiểu, danh sách chọn, tỉnh ∈ `dim_prefecture`, số ≥ 0 hữu hạn, giá > 0, hạn đúng dạng) →
   400, kèm lỗi từng ô, không ghi gì.
3. Khoá advisory theo `loai` trong giao dịch; ô nào giá trị hiệu lực hiện tại ≠ `thay` → **409** kèm danh sách ô (giá trị
   mới + ai / lúc), không ghi gì.
4. Ghi MỘT giao dịch:
   - mỗi ô một dòng sổ, `gia_tri_obc` đọc từ `core` NGAY LÚC ĐÓ;
   - giá trị mới = OBC thì ghi `bo = true` (về OBC);
   - giá trị mới = hiệu lực hiện tại thì bỏ qua ô đó.
5. Trả các ô sau khi lưu (hiệu lực + `lech`). Dòng đọc lại chỉ mang ô sửa được (`o`), KHÔNG mang khoá chỉ số chỉ-xem
   (`dt_12t`, `ton_tong`, `lan_cuoi`): hai lượt đọc trong `luu()` bỏ hẳn CTE quét `mart.ban_den_moc`; trình duyệt giữ chỉ số cũ
   của dòng khi trộn.
   Lỗi 400 / 409 đánh khoá từng ô `"<k>	<cot>"` (cùng dạng khoá `lech`).

Trần 2.000 ô mỗi lần lưu.

## 6. Giao diện (`giao_dien/src/bang_du_lieu/`)

- Mục mới trong thanh trái Kho dữ liệu: "Bảng dữ liệu" → `/kho-du-lieu/bang-du-lieu`, `?loai=kh` cho tab Khách hàng
  (URL qua `giuKhoang`).
- Theo phác thảo đã duyệt:
  - hai tab Sản phẩm / Khách hàng;
  - khung "Chọn cột" chia nhóm, ô tick; cột khoá có 🔒; lựa chọn nhớ trong `localStorage` theo loại, đọc/ghi trong `try`;
  - ô tìm (bỏ dấu), nút lọc "Đã sửa trên web, OBC chưa có";
  - "n ô chưa lưu" · Huỷ · Lưu.
- Bảng tính:
  - dòng tiêu đề và cột mã đứng yên;
  - chỉ vẽ các dòng trong khung nhìn (dòng cao cố định) — 2.142 khách;
  - chọn ô bằng chuột / mũi tên (`bang_sua_logic.ts::oKeTiep` / `neoKeTiep`, neo theo KHOÁ dòng);
  - Enter / F2 / gõ ký tự để sửa, Esc bỏ, Tab / Enter đi tiếp;
  - cột `chon` là ô chọn;
  - dán khối TSV từ Excel vào các ô sửa được bắt đầu từ ô đang chọn (ô không sửa được bỏ qua, báo số ô bỏ).
- Ô:
  - đang sửa chưa lưu = nền vàng;
  - bản sửa đang thắng = vạch xanh trái, rê chuột: "OBC: … · sửa bởi … lúc …";
  - ⋯ trên ô lệch có "Về giá trị OBC".
- Lưu:
  - 400 → ô lỗi viền đỏ + câu lỗi, giữ chữ đã gõ;
  - 409 → dải "n ô vừa bị người khác / lần nạp OBC đổi" với "Lấy bản mới" (bỏ phần gõ của các ô đó) và "Ghi đè"
    (gửi lại với `thay` mới).
  - Rời trang khi còn ô chưa lưu → hỏi (`beforeunload`).
- Không có `duoc_sua_du_lieu` → mọi ô chỉ xem, đầu trang nói cần cờ nào.

## 7. Kiểm

- **pytest**
  - `ap_sua` / `lech_obc`: OBC giữ nguyên → sửa thắng; OBC đổi → OBC thắng; `bo` → OBC.
  - `dim_customer` qua nạp SCD2 (đổi cột khác vẫn giữ bản sửa, đổi đúng cột thì mất).
  - Cột cặp mã–tên.
  - Giá: gia_kome_bang / so với đối thủ đi theo.
  - Tồn / hạn: ton_theo_lo, cận hạn đi theo.
  - Sổ chỉ thêm (kome_app không UPDATE / DELETE).
  - API: 400 / 403 / 409, một giao dịch, 1 lượt hỏi GET.
  - Nhật ký, cờ quyền, ảnh chụp đổi phiên bản khi sửa.
  - Test canh không view / hàm / file Python nào đọc OBC thô ngoài danh sách trắng.
  - Toàn bộ test cũ vẫn xanh: với sổ rỗng mọi số y như trước.
- **vitest**: logic bảng (chọn / di chuyển / dán TSV / gom ô chờ / đếm lọc lệch), chọn cột nhớ theo loại.
- **Trình duyệt**: dữ liệu thật chỉ đọc (POST bị chặn) và CSDL thử ở máy (lưu thật).
- **Đo thật sau migration** (chỉ đọc): thời gian `khach_360`, `san_pham_360`, `so_sanh_nhom` trước và sau 072 với sổ rỗng.
- **Migration 072 phải chạy TRƯỚC khi triển khai** (bằng `db/migrate.py`, vai trò postgres, chủ DN đồng ý).
