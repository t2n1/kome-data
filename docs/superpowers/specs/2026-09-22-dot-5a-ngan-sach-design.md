# Đặc tả thiết kế — Đợt 5a: Ngân sách (chỉ tiêu doanh thu theo nhân viên theo tháng)

**Ngày:** 2026-09-22
**Lộ trình:** `docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md` §7 (đợt 5), §9 (dữ liệu mới), §8.3 (vai trò)
**Màn liên quan:** 2 (Báo cáo) — phần ngân sách. Màn 1 (Dashboard) và 8 khối phân tích còn lại thuộc **đợt 5b**.

---

## 1. Vì sao tách 5a ra khỏi đợt 5

Lộ trình §7 mở đầu bằng nguyên tắc **"không đợt nào làm hai việc khó cùng lúc"**.
Đợt 5 như mô tả làm đúng hai việc khó:

- thêm một nguồn dữ liệu **ghi được** hoàn toàn mới, kèm **hàng rào quyền thật** đầu
  tiên của app ngoài luồng nạp OBC;
- dựng lại hai màn lớn nhất còn lại (Báo cáo 13 khối + Dashboard).

Đây đúng tình huống đã tách 2a/2b. Rủi ro dồn hết vào nửa đầu:

| | 5a — Ngân sách | 5b — Báo cáo phân tích + Dashboard |
|---|---|---|
| Ghi dữ liệu | **có** (bảng mới, màn nhập) | không |
| Hàng rào quyền mới | **có** | không |
| Hỏng thì sao | số chỉ tiêu sai hoặc mất | một trang thiếu khối |
| Tự đứng được | có — nhập chỉ tiêu xong thấy tiến độ ngay | có |

5a tự đứng được và 5b hoãn bao lâu cũng không chặn đợt nào.

---

## 2. Ràng buộc kế thừa

Mọi bất biến trong `CLAUDE.md` áp dụng nguyên vẹn. Năm cái chi phối tài liệu này
mạnh nhất:

- **Tiền luôn là số nguyên yên.** `muc_tieu` là `bigint`, không `numeric`.
- **Định nghĩa chỉ số chỉ nằm trong `mart/`.** Công thức "tiến độ", "mốc đáng lẽ đạt
  tới hôm nay" nằm trong view, không nằm trong Python hay Jinja.
- **Mốc thời gian là `mart.moc_thoi_gian.hom_nay`**, không phải `current_date` — xem §5.
- **Migration luôn chạy bằng vai trò `postgres`** (`ALTER DEFAULT PRIVILEGES` không có
  `FOR ROLE`).
- **"Không biết" khác "bằng không"** — nếp đã ghi cho `mart.san_pham_360.ton`. Ở đây:
  **không có dòng** = chưa đặt chỉ tiêu; `muc_tieu = 0` = đã đặt và đặt bằng không.
  Hai thứ khác nhau và màn hình phải hiện khác nhau (§6.4).

---

## 3. Dữ liệu

### 3.1 `app.ngan_sach`

```sql
CREATE TABLE app.ngan_sach (
    salesperson_code text NOT NULL REFERENCES core.dim_salesperson,
    thang            date NOT NULL REFERENCES core.dim_date (date_key)
                          CHECK (extract(day FROM thang) = 1),
    muc_tieu         bigint NOT NULL CHECK (muc_tieu >= 0),
    sua_luc          timestamptz NOT NULL DEFAULT now(),
    sua_boi          bigint NULL REFERENCES app.nguoi_dung,
    PRIMARY KEY (salesperson_code, thang)
);
```

**`thang` là `date` (ngày mùng 1), không phải `text 'YYYY-MM'`.** Lưu đúng kiểu ở tầng
lưu trữ thì CSDL tự chặn `'2026-13'` và `'26-07'`; `CHECK` chặn nốt ngày khác mùng 1,
nên không tồn tại được hai dòng "cùng tháng" khác ngày. Mọi view của `mart` lại đang
dùng khoá `thang text 'YYYY-MM'` (`ban_theo_thang`, `ban_theo_thang_so_sanh`,
`khach_theo_thang`, `san_pham_theo_thang`), nên **đúng MỘT chỗ đổi kiểu**:
`mart.ngan_sach_thang` (§5.2) phát ra `to_char(thang, 'YYYY-MM')`. Một phép đổi ở một
chỗ, mọi phép nối phía sau vẫn là so chuỗi như phần còn lại của `mart`.

**`thang` có khoá ngoại tới `core.dim_date`, không chỉ một `CHECK`.** `core.dim_date`
phủ 2024-01-01 → 2035-12-31 (`004_dim_date.sql`). `mart.ngan_sach_thang` (§5.2) nối
sang `dim_date` để lấy `company_fy`, nên một dòng chỉ tiêu nằm ngoài dải đó sẽ **biến
mất khỏi mọi báo cáo mà không lỗi nào nổ ra** — dữ liệu còn trong bảng, chỉ là không ai
nhìn thấy nữa. Khoá ngoại biến nó thành một lỗi ghi ngay tại chỗ nhập. Khi lịch hết hạn
năm 2035, lỗi là "không đặt được chỉ tiêu 2036" — đọc ra ngay nguyên nhân, khác hẳn với
"chỉ tiêu 2036 lưu xong rồi mà báo cáo không thấy".

**`sua_boi` cho phép NULL.** NULL khi máy trong công ty không bật cổng đăng nhập
(`KOME_SESSION_SECRET` trống) — xem §4.3. Khoá ngoại để mặc định `NO ACTION`, **không**
`ON DELETE CASCADE`: xoá một tài khoản không được phép kéo theo chỉ tiêu của cả năm.

### 3.2 `app.ngan_sach_nhat_ky` — chỉ thêm, không sửa

```sql
CREATE TABLE app.ngan_sach_nhat_ky (
    id               bigserial PRIMARY KEY,
    salesperson_code text NOT NULL,
    thang            date NOT NULL,
    muc_tieu_cu      bigint NULL,
    muc_tieu_moi     bigint NULL,
    sua_boi          bigint NULL REFERENCES app.nguoi_dung,
    sua_luc          timestamptz NOT NULL DEFAULT now()
);
```

`muc_tieu_cu IS NULL` = đặt chỉ tiêu lần đầu cho ô đó. `muc_tieu_moi IS NULL` = xoá
chỉ tiêu (ô để trống). Cả hai cùng NULL không bao giờ được ghi.

**Không có khoá ngoại tới `app.ngan_sach`, và đó là chủ ý:** nhật ký phải sống sót sau
khi dòng chỉ tiêu bị xoá — chính lúc bị xoá mới là lúc cần biết ai xoá.

**Không có `UPDATE`/`DELETE` trong code.** Bảng chỉ được `INSERT`. Vai trò `kome_app`
vẫn có UPDATE/DELETE trên schema `app` theo `009_roles.sql` — đây là ràng buộc của code
và của bản soát, **không phải** của CSDL, và tài liệu này nói thẳng ra thay vì giả vờ
CSDL đang canh giúp.

### 3.3 Quyền trên hai bảng mới

Không cần `GRANT` tay: `009_roles.sql` (dòng 33–35) và `010_*.sql` (dòng 27–30) đã đặt
`ALTER DEFAULT PRIVILEGES IN SCHEMA app` cho cả TABLES lẫn SEQUENCES. Hai bảng mới tự
nhận quyền — **với điều kiện migration chạy bằng vai trò `postgres`**.

`kome_report` tự nhận SELECT trên hai bảng này. Giữ nguyên, **không** `REVOKE` như đã
làm với `app.nguoi_dung`: chỉ tiêu doanh thu là con số nghiệp vụ, không phải hash mật
khẩu.

Bốn view của `mart` thì **phải `GRANT` tay**, và đây là chỗ dễ quên nhất của cả đợt:
`ALTER DEFAULT PRIVILEGES IN SCHEMA core, mart` ở `009_roles.sql` (dòng 33) chỉ kể tên
`kome_app` và `kome_report` — **không có `kome_ingest`**. Vì vậy mọi migration từng
thêm view vào `mart` (`014`, `020`, `021`, `023`, `024`, `025`) đều kết thúc bằng đúng
một dòng:

```sql
GRANT SELECT ON ALL TABLES IN SCHEMA mart TO kome_app, kome_report, kome_ingest;
```

Quên dòng đó **không làm migration lỗi**. Nó lỗi bằng một `permission denied` nhiều
tháng sau, giữa lúc có người đang nạp dữ liệu lúc 13:30. Có test canh (§9).

**Hai luật quyền khác nhau, đừng gộp.** Luật vừa nói là về SELECT trên *chính cái
view*. Luật thứ hai — Postgres kiểm quyền trên **bảng NỀN** theo **chủ sở hữu view**
(ở đây là `postgres`) — chỉ giải thích một chuyện khác: vì sao `mart.ngan_sach_thang`
đọc được `app.ngan_sach` **dù `kome_ingest` không hề có `USAGE` trên schema `app`**.
Gộp hai luật làm một sẽ dẫn tới kết luận sai rằng không cần `GRANT` gì cả. Hệ quả của
luật thứ hai vẫn đứng và vẫn đáng nhớ: **đặt gì vào một view của `mart` là công bố thứ
đó cho mọi vai trò đọc `mart`** — không đưa cột nhạy cảm nào vào theo đường này.

---

## 4. Quyền sửa ngân sách

### 4.1 Một cờ boolean, không phải cột `vai_tro`

Lộ trình §8.3 đề xuất hai cột `vai_tro` + `dashboard_mac_dinh` trên `app.nguoi_dung`.
**Migration `019_danh_tinh.sql` đã chạy không có cột nào trong hai cột đó** — bảng thật
chỉ có `salesperson_code` và `duoc_vao_kho_du_lieu`.

Đợt 5a **không** thêm `vai_tro`. Nó thêm đúng một cột:

```sql
ALTER TABLE app.nguoi_dung
    ADD COLUMN duoc_sua_ngan_sach boolean NOT NULL DEFAULT false;
```

Ba lý do:

1. **`dashboard_mac_dinh` đã thành cột chết.** Chủ sở hữu chọn một bố cục dashboard
   chung cho mọi người (quyết định 2026-09-22), nên cột "mở lên thì thấy module nào"
   không còn câu hỏi nào để trả lời.
2. **`vai_tro` làm hàng rào là gieo lại đúng mâu thuẫn §8.3 muốn dẹp.** `CLAUDE.md` ghi
   rõ: lọc theo `salesperson_code` là **mặc định tiện dụng, KHÔNG phải hàng rào bảo
   mật**. Dựng một cột tên "vai trò" rồi dùng nó gác một nút ghi dữ liệu là để hai
   nghĩa trái nhau sống chung trong một cột.
3. **Nếp đã có và đã chạy được:** `duoc_vao_kho_du_lieu` gác nút Hoàn tác đúng theo
   cách này. Một cờ, một nghĩa, một chỗ tra.

Thêm vai trình bày hay vai lọc về sau vẫn mở — tài liệu này không đóng cửa nào, nó chỉ
từ chối dựng sẵn một cột chưa có người dùng.

### 4.2 Cách gác

Sao y `duoc_vao_kho_du_lieu`:

- **Tra `app.nguoi_dung` MỖI LƯỢT GỌI**, không nhét cờ vào vé đăng nhập. Vé sống 12
  giờ; thu hồi quyền sửa chỉ tiêu phải ăn ngay hôm nay. (Bất biến đã ghi cho
  `duoc_vao_kho_du_lieu`, áp nguyên.)
- **403 kèm trang giải thích**, không chuyển hướng im lặng. Người gõ thẳng địa chỉ cần
  biết vì sao mình không vào được, không phải tự hỏi trang có hỏng không.
- Mục "Ngân sách" **ẩn khỏi thanh điều hướng** với người không có cờ — nhưng ẩn là
  lịch sự, 403 mới là hàng rào.
- Cờ gác **cả `GET /ngan-sach` lẫn `POST /ngan-sach`**. Gác mỗi GET là để nguyên cửa
  ghi mở toang cho ai biết gõ `curl`.

### 4.3 Cạm bẫy phải nói ra

Máy trong công ty để trống `KOME_SESSION_SECRET` thì **không có cổng đăng nhập và không
có phân quyền** — ai mở được trang cũng sửa được ngân sách, và `sua_boi` ghi NULL vì
không ai là ai. Đây **không phải lỗ mới**: `CLAUDE.md` đã ghi đúng cạm bẫy này cho nút
Hoàn tác. Đợt 5a chỉ làm nó gác thêm một thứ, nên câu cảnh báo trong `CLAUDE.md` và
`docs/runbook.md` phải được cập nhật để kể luôn cả ngân sách.

---

## 5. Định nghĩa chỉ số (`mart`)

### 5.1 `mart.ngay_kinh_doanh` — mẫu số của mọi phép "đến hôm nay"

```sql
CREATE VIEW mart.ngay_kinh_doanh AS
SELECT to_char(d.date_key, 'YYYY-MM')                                   AS thang,
       count(*) FILTER (WHERE NOT d.is_weekend)                         AS ngay_kd,
       count(*) FILTER (WHERE NOT d.is_weekend AND d.date_key <= m.hom_nay)
                                                                        AS ngay_kd_da_qua
FROM core.dim_date d CROSS JOIN mart.moc_thoi_gian m
GROUP BY 1;
```

**Hạn chế có tên: `core.dim_date` KHÔNG có cột ngày lễ Nhật.** `is_weekend` chỉ loại
thứ Bảy và Chủ nhật. Tháng có Tuần lễ Vàng (5月) hay Obon (8月) bị đếm thừa 2–4 ngày
làm việc, nên vạch mốc "đáng lẽ đạt tới hôm nay" **khắt khe hơn thực tế** ở đúng những
tháng đó. Ghi ra chứ không bịa một định nghĩa thứ hai (ví dụ "ngày có phiếu bán"), vì
hai định nghĩa cùng tên là hai con số nói hai điều. Thêm cột ngày lễ vào
`core.dim_date` là một việc nhỏ RIÊNG, làm sau được mà không phải sửa gì ở đây.

### 5.2 `mart.ngan_sach_thang` — chỉ tiêu, đã đổi khoá sang chuỗi

```sql
CREATE VIEW mart.ngan_sach_thang AS
SELECT to_char(n.thang, 'YYYY-MM') AS thang,
       d.company_fy,
       n.salesperson_code,
       n.muc_tieu
FROM app.ngan_sach n
JOIN core.dim_date d ON d.date_key = n.thang;
```

Đây là **chỗ duy nhất** đổi `date` sang `'YYYY-MM'`, và cũng là chỗ duy nhất tra
`company_fy` của tháng — lấy từ `core.dim_date`, **không tính tay**, theo luật số 3 của
`014_mart_bao_cao.sql`.

### 5.3 `mart.ban_theo_nhan_vien_thang` — thực tế theo người theo tháng

```sql
CREATE VIEW mart.ban_theo_nhan_vien_thang AS
SELECT thang,
       min(company_fy)      AS company_fy,
       salesperson_code,
       sum(doanh_thu_thuan) AS doanh_thu_thuan,
       sum(gross_profit)    AS lai_gop,
       sum(gross_profit)::numeric / nullif(sum(doanh_thu_thuan), 0) AS ty_suat,
       count(DISTINCT customer_code) AS so_khach,
       count(DISTINCT slip_no)       AS so_phieu
FROM mart.dong_ban
GROUP BY thang, salesperson_code;
```

Cùng khuôn `mart.ban_theo_nhan_vien` (`014`), chỉ đổi trục gộp từ kỳ sang tháng. Tỷ
suất vẫn là **tỷ số của các TỔNG** — bất biến đã ghi, không bao giờ là trung bình của
các tỷ số từng dòng.

### 5.4 `mart.tien_do_ngan_sach` — nơi ở của công thức tiến độ

```sql
CREATE VIEW mart.tien_do_ngan_sach AS
SELECT coalesce(b.thang, n.thang)                        AS thang,
       coalesce(b.company_fy, n.company_fy)              AS company_fy,
       coalesce(b.salesperson_code, n.salesperson_code)  AS salesperson_code,
       n.muc_tieu,
       coalesce(b.doanh_thu_thuan, 0)::bigint            AS thuc_te,
       k.ngay_kd,
       k.ngay_kd_da_qua,
       (n.muc_tieu * k.ngay_kd_da_qua::numeric / nullif(k.ngay_kd, 0))::bigint
                                                         AS muc_tieu_den_hom_nay,
       coalesce(b.doanh_thu_thuan, 0)::numeric / nullif(n.muc_tieu, 0) AS tien_do
FROM mart.ban_theo_nhan_vien_thang b
FULL JOIN mart.ngan_sach_thang     n ON n.thang = b.thang
                                    AND n.salesperson_code = b.salesperson_code
LEFT JOIN mart.ngay_kinh_doanh     k ON k.thang = coalesce(b.thang, n.thang);
```

**`FULL JOIN`, không `LEFT JOIN` theo chiều nào cả — và đây là điểm dễ hỏng nhất của
đợt này.**

- Nối từ chỉ tiêu sang thực tế (`ngan_sach LEFT JOIN ban_theo`): tháng có doanh thu mà
  **quên đặt chỉ tiêu** biến mất khỏi báo cáo — doanh thu thật không xuất hiện ở đâu.
- Nối ngược lại (`ban_theo LEFT JOIN ngan_sach`): người **có chỉ tiêu mà bán được 0
  đồng** biến mất — đúng người cần nhìn nhất thì không có dòng nào.

Cả hai chiều đều mất dòng **mà trang vẫn vẽ ra bình thường**, không lỗi nào nổ ra để lộ
chuyện đó. Cùng lớp lỗi đã ghi cho `/ban-do`
(`dim_prefecture LEFT JOIN khach_theo_tinh`).

**Đo thật 2026-09-22 cho thấy chiều thứ nhất sẽ mất dòng NGAY HÔM NAY:** dữ liệu bán có
6 mã phụ trách (`0000`, `0002`, `0004`, `0102`, `0104`, `0105`) trong khi
`core.dim_salesperson` chỉ có 5 — **`0000` không tồn tại trong bảng phụ trách** nhưng có
1 khách và ¥28.981 doanh thu kỳ 7. Mã đó không bao giờ có chỉ tiêu (khoá ngoại chặn),
nên bất kỳ phép nối nào xuất phát từ chỉ tiêu đều làm số tiền đó bốc hơi. Màn hình phải
hiện nó thành một dòng riêng — xem §7.3.

`tien_do` dùng `nullif(muc_tieu, 0)`: chỉ tiêu 0 cho ra NULL và màn hình in "—". Chia
cho 0 thì trang chết; in "∞" thì người đọc tưởng đã vượt mức.

---

## 6. Màn `/ngan-sach`

### 6.1 Hình dáng

Một bảng: **hàng = 5 người phụ trách** (`core.dim_salesperson`, sắp theo mã),
**cột = 12 tháng của một kỳ** (8月 → 7月, đúng thứ tự kỳ công ty). Mỗi ô là một
`<input type="text" inputmode="numeric">`. Cột cuối: tổng năm của từng người (chỉ đọc).
Hàng cuối: tổng tháng của cả nhóm (chỉ đọc).

Chọn kỳ bằng dải chip như `/bao-cao` đang làm. Kỳ mặc định: kỳ của
`mart.moc_thoi_gian.hom_nay`.

**Màn nhập có 5 hàng, màn Báo cáo có thể có 6 — không mâu thuẫn.** Chỉ đặt được chỉ
tiêu cho mã có trong `core.dim_salesperson` (khoá ngoại chặn), nên màn nhập đúng 5
hàng. Màn Báo cáo hiện theo *doanh thu đã bán*, và doanh thu có thể mang mã ngoài danh
sách đó (§7.3). Đây là hai câu hỏi khác nhau — "đặt chỉ tiêu cho ai" và "tiền về từ mã
nào" — nên hai màn đếm khác nhau là đúng.

**Kỳ chưa có dòng bán nào vẫn phải chọn được.** Chỉ tiêu được đặt TRƯỚC khi bán — danh
sách kỳ trên màn này lấy từ `core.dim_date` (mọi kỳ có ĐỦ 12 tháng trong lịch — dải
`core.dim_date` phủ 2024-01-01 → 2035-12-31, nên hai đầu, kỳ 2024 và kỳ 2036, chỉ nằm
MỘT PHẦN trong lịch và phải bị loại, không thì bấm Lưu trên một cột không tồn tại là
`ForeignKeyViolation` trần), **không** lấy từ `mart.tong_theo_ky` (chỉ những kỳ đã có
doanh thu). Lấy nhầm nguồn thì không ai đặt được chỉ tiêu cho năm sau, và lỗi chỉ lộ ra
đúng lúc cần dùng.

### 6.2 Nhập số

`inputmode="numeric"` chứ không `type="number"`: `type="number"` trên Chrome cuộn chuột
là đổi số, và người dùng bảng 60 ô sẽ cuộn.

Chấp nhận dấu phân cách: `12.000.000`, `12,000,000`, `12000000` đều ra cùng một số.
Ô trống = **xoá chỉ tiêu** (xoá dòng + ghi nhật ký với `muc_tieu_moi IS NULL`), KHÁC
với `0` = đặt chỉ tiêu bằng không.

Chuỗi không đọc được thành số → **không ghi gì cả cho TOÀN BỘ biểu mẫu**, hiện lại đúng
những gì người ta vừa gõ kèm lời báo ô nào sai. Ghi một nửa rồi báo lỗi là để người ta
không biết nửa nào đã vào.

### 6.3 Ghi

Một `POST`, một giao dịch. Đọc giá trị hiện có (1 truy vấn), so với giá trị gửi lên,
**chỉ đụng những ô đã đổi**, và mỗi ô đổi ghi một dòng `app.ngan_sach_nhat_ky`.

Vì sao chỉ đụng ô đã đổi: `sua_luc`/`sua_boi` phải trả lời "ai đổi con số NÀY lần
cuối", không phải "ai bấm Lưu lần cuối". Ghi đè cả 60 ô mỗi lần bấm Lưu là xoá sạch
thông tin đó và làm nhật ký đầy những dòng không có gì thay đổi.

**Ngân sách truy vấn: `GET` không quá 4 lượt hỏi, `POST` không quá 4** — đọc hiện
trạng · ghi những ô có giá trị mới · xoá những ô vừa bị để trống · ghi nhật ký. Một
biểu mẫu chỉ đặt thêm chỉ tiêu (không xoá ô nào) chạy ba. Có test đếm, như các màn
khác. Con số này đo **số lượt hỏi**, không đo sức tính: thứ nó tồn tại để cấm là vòng
lặp một câu lệnh mỗi ô — 60 ô × 47 ms là gần ba giây chỉ để bấm một nút Lưu.

### 6.4 "Chưa đặt" khác "bằng không"

Ô chưa có dòng hiện **trống**, không hiện `0`. Ô có dòng `muc_tieu = 0` hiện `0`. Tổng
cột bỏ qua ô trống. Cùng nếp `mart.san_pham_360.ton` — hiện `0` cho thứ chưa biết là
nói một điều sai bằng con số.

### 6.5 Không có nút xoá cả kỳ, không có nút chép từ kỳ trước

YAGNI. Chép từ kỳ trước nghe tiện nhưng nó là cửa duy nhất tạo ra 60 dòng nhật ký trong
một cú bấm, và chưa ai hỏi tới nó. Thêm sau rẻ.

---

## 7. Khối ngân sách trên `/bao-cao`

Đợt 5b dựng lại toàn bộ màn Báo cáo. 5a **chỉ thêm khối vào màn đang có**, không đụng
bố cục cũ.

### 7.1 Tiến độ ngân sách tháng

Tháng lấy theo `mart.moc_thoi_gian.hom_nay`, **không theo đồng hồ thật**.

**Đo thật 2026-09-22:** phiếu bán mới nhất trong kho là **2026-07-31**; file master mới
nhất đã nạp là 2026-09-08, tồn kho 2026-09-16. Tức gần hai tháng không ai nạp file bán
hàng. Nếu khối này lấy `current_date` thì nó báo "tháng 9 đạt 0% ngân sách" trong khi
sự thật là **chưa ai nạp dữ liệu tháng 9** — con số sai đúng loại làm người ta đi hỏi
nhân viên vì sao không bán được gì.

Khối phải **in ra tháng nó đang nói** và **in ra ngày mốc**, ví dụ: "Tiến độ ngân sách
tháng 2026-07 · số liệu đến 31/07/2026". Ô "hôm nay đã có dữ liệu chưa" ở trang `/` là
chỗ nói chuyện dữ liệu cũ; khối này chỉ cần không nói dối.

Nội dung: thanh tiến độ toàn nhóm + vạch mốc `muc_tieu_den_hom_nay`, kèm số tuyệt đối.
Vạch mốc là màu; **con số phần trăm in ra ngay cạnh** (bất biến màu-kèm-chữ).

### 7.2 Luỹ kế thực tế so với nhịp ngân sách

Biểu đồ SVG tự tính toạ độ (như `bao_cao.ve_bieu_do`), 12 tháng của kỳ: một đường luỹ
kế thực tế, một đường nhịp ngân sách. **Không thư viện JS** — lý do đã ghi trong
`kome/bao_cao.py`: trang phải chạy cả trên Vercel (nơi CSP chặn script ngoài) lẫn ở máy
không có mạng.

Đường luỹ kế thực tế **dừng ở tháng của `hom_nay`**, không kéo dài tới hết kỳ bằng số
0 — một đường rơi xuống 0 đọc thành "doanh thu sụp", không phải "chưa có dữ liệu".

### 7.3 Thanh tiến độ theo từng nhân viên

Một thanh mỗi người, `thuc_te / muc_tieu`, vạch mốc như §7.1. Tên người lấy từ
`core.dim_salesperson.ten`.

**Dòng cho mã phụ trách không có trong `core.dim_salesperson`** (hôm nay là `0000`):
hiện nhãn `0000 — (mã không có trong danh sách phụ trách)`, có doanh thu, không có chỉ
tiêu, không có thanh tiến độ. Bỏ dòng này đi là giấu doanh thu thật; gắn cho nó một chỉ
tiêu là bịa ra một con số.

### 7.4 Bảng số chi tiết theo nhân viên

Cột: Nhân viên · Thực tế · Chỉ tiêu · Tiến độ · Mốc đến hôm nay · Cùng kỳ năm trước ·
So cùng kỳ · Tỷ trọng. Tháng của `hom_nay`. Cùng kỳ năm trước đọc từ
`mart.ban_theo_nhan_vien_thang` của tháng trừ 12; **thiếu thì để trống và nói rõ**,
theo đúng nếp `co_cung_ky` của `mart.ban_theo_thang_so_sanh` (dữ liệu bán bắt đầu
2025-03-03, trước mốc đó KHÔNG TỒN TẠI).

---

## 8. Những gì 5a KHÔNG làm

- Dashboard (màn 1) và 8 khối phân tích của màn Báo cáo — **đợt 5b**.
- Cột `vai_tro`, cột `dashboard_mac_dinh` — §4.1.
- Ngày lễ Nhật trong `core.dim_date` — §5.1.
- Hoa hồng & thưởng (màn 4) — nhánh có điều kiện, lộ trình §8.1.
- Chỉ tiêu theo mã hàng, theo tỉnh, theo khách — chưa ai hỏi tới.

---

## 9. Kiểm thử

Chạy trên CSDL thử nghiệm (`DATABASE_URL_TEST`), tuần tự, như mọi test của dự án.

| Test | Canh cái gì |
|---|---|
| `test_tien_do_giu_ca_hai_chieu_thieu` | Người có chỉ tiêu mà 0 đồng doanh thu VẪN có dòng; tháng có doanh thu mà không có chỉ tiêu VẪN có dòng (§5.4) |
| `test_ma_phu_trach_ngoai_dim_van_hien_doanh_thu` | Dòng bán với `salesperson_code` không có trong `core.dim_salesperson` → doanh thu vẫn xuất hiện (§7.3) |
| `test_o_trong_khac_o_bang_khong` | Ô trống → không có dòng; ô `0` → có dòng `muc_tieu = 0`; hai thứ hiện khác nhau (§6.4) |
| `test_moc_thoi_gian_theo_hom_nay_khong_theo_dong_ho` | Đặt `hom_nay` lệch hẳn đồng hồ → khối tiến độ nói tháng của `hom_nay` (§7.1) |
| `test_khong_co_co_thi_403_ca_GET_lan_POST` | `duoc_sua_ngan_sach = false` → cả hai cửa trả 403, và **POST không ghi gì** (§4.2) |
| `test_thu_hoi_co_an_ngay_khong_doi_het_ve` | Đổi cờ trong CSDL → lượt gọi kế tiếp đã bị chặn, không cần đăng nhập lại (§4.2) |
| `test_mot_o_sai_thi_khong_ghi_o_nao` | Một ô chữ rác → toàn bộ biểu mẫu không ghi (§6.2) |
| `test_chi_ghi_nhat_ky_cho_o_da_doi` | Bấm Lưu mà không đổi gì → 0 dòng nhật ký (§6.3) |
| `test_ngan_sach_truy_van` | `GET` ≤ 4, `POST` ≤ 4 lượt hỏi (§6.3) |
| `test_ky_chua_co_doanh_thu_van_chon_duoc` | Kỳ không có dòng bán nào vẫn nằm trong dải chip (§6.1) |
| `test_ty_suat_van_la_ty_so_cua_cac_tong` | `ban_theo_nhan_vien_thang.ty_suat` (§5.3) |
| `test_bon_view_moi_deu_cap_SELECT_cho_ca_ba_vai_tro` | Bốn view mới của `mart` đều có SELECT cho `kome_app`, `kome_report` **và `kome_ingest`** — vai trò mà `ALTER DEFAULT PRIVILEGES` của `009` không kể tên (§3.3) |
| `test_migrate` (đã có) | Migration mới chạy được, và chạy lại không hỏng gì |

---

## 10. KIỂM TAY của chủ sở hữu

Sau khi `python db/migrate.py` chạy bằng vai trò `postgres`:

1. `/ngan-sach` khi **chưa** cấp cờ → 403 kèm trang giải thích, mục "Ngân sách" không
   có trong thanh điều hướng.
2. `python scripts/tao_nguoi_dung.py quyen <tên> --ngan-sach` → vào được.
3. Nhập chỉ tiêu 5 người cho 12 tháng kỳ 7, bấm Lưu, tải lại trang → đúng số vừa nhập.
4. Sửa một ô, bấm Lưu → `SELECT * FROM app.ngan_sach_nhat_ky ORDER BY id DESC LIMIT 5`
   có đúng **một** dòng mới, đúng số cũ và số mới.
5. `/bao-cao` → khối tiến độ nói **tháng 2026-07** (không phải tháng theo đồng hồ), và
   in ra ngày mốc.
6. Thời gian mở `/ngan-sach` và `/bao-cao` — **lấy lần chạy THỨ HAI**, ngưỡng
   **1.500 ms** như các màn của đợt 4.

---

## 11. Rủi ro

| | Rủi ro | Mức | Xử lý |
|---|---|---|---|
| R1 | Máy công ty để trống `KOME_SESSION_SECRET` → không có hàng rào nào | **Cao** | Ghi vào `CLAUDE.md` và `docs/runbook.md`; không sửa được bằng code — cổng chỉ tồn tại khi có khoá ký |
| R2 | Phép nối chỉ tiêu ↔ thực tế mất dòng mà không lỗi nào nổ | Cao | `FULL JOIN` + test canh cả hai chiều (§5.4, §9) |
| R3 | Ngày lễ Nhật làm vạch mốc khắt khe hơn thực tế | Thấp | Ghi thành hạn chế có tên (§5.1); thêm cột ngày lễ là việc riêng |
| R4 | Dữ liệu bán dừng 31/7/2026 → người đọc tưởng trang hỏng | Trung bình | Khối in rõ tháng và ngày mốc (§7.1) |
| R5 | Không ai nhập chỉ tiêu → màn Báo cáo có 4 khối rỗng | Trung bình | Khối rỗng hiện một dòng "Chưa đặt chỉ tiêu cho kỳ này" kèm liên kết sang `/ngan-sach`, không hiện 0% |

---

## 12. Tiêu chí hoàn thành

- [ ] Migration `026` tạo `app.ngan_sach`, `app.ngan_sach_nhat_ky`, cột
      `duoc_sua_ngan_sach`, và 4 view `mart` của §5
- [ ] `/ngan-sach` nhập và lưu được, gác bằng cờ ở cả GET và POST
- [ ] `scripts/tao_nguoi_dung.py` cấp/thu được cờ mới và hiện nó trong bảng liệt kê
- [ ] 4 khối ngân sách trên `/bao-cao` (§7.1–7.4)
- [ ] Toàn bộ test §9 xanh, và bộ test cũ không đỏ thêm cái nào
- [ ] `CLAUDE.md` + `docs/runbook.md` cập nhật: cờ mới, cạm bẫy §4.3, bất biến §5.4
- [ ] Chủ sở hữu làm xong KIỂM TAY §10
