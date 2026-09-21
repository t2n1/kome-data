# Đặc tả thiết kế — Đợt 3: Danh tính

**Ngày:** 2026-09-21
**Công ty:** 株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật
**Phạm vi:** thay mật khẩu chung bằng đăng nhập riêng từng người; chặn màn Kho dữ liệu theo quyền; mặc định "khách của tôi".
**Trạng thái:** Chờ duyệt
**Tài liệu liên quan:**
- `docs/superpowers/specs/2026-09-16-kome-data-platform-design.md` — **"đặc tả nền"**
- `docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md` §7 — **"lộ trình"**
- `docs/superpowers/specs/2026-09-17-dashboard-nguoi-dung-crm-dot-1-design.md` — **"spec đợt 1"**, tài liệu này thay thế phần danh tính của nó (§2)

---

## 1. Bối cảnh

Hôm nay cả hệ thống dùng **một mật khẩu chung** (`KOME_MAT_KHAU`). Hệ quả:

- Không biết ai đang xem gì, ai vừa nạp file, ai vừa bấm Hoàn tác.
- **Bất kỳ ai biết mật khẩu đều bấm được nút Hoàn tác** — nút mà đợt 2a vừa phát hiện có thể xoá cả một tháng doanh thu nếu bấm nhầm lô đối soát.
- Người nghỉ việc thì phải đổi mật khẩu của tất cả mọi người.

Đợt 3 sửa cái gốc đó. Nó cũng là điều kiện để các đợt sau cá nhân hoá được: CRM "khách của tôi" không có nghĩa nếu hệ thống không biết "tôi" là ai.

---

## 2. Quan hệ với spec đợt 1

Spec đợt 1 (2026-09-17) thiết kế đăng nhập theo người dùng ở §5.1, §5.3, §5.4. Lộ trình §2 đã quyết tách nó làm đôi: phần danh tính vào đợt này, phần CRM vào đợt 7.

**Tài liệu này thay thế §5.1, §5.3, §5.4 của spec đợt 1.** Phần lớn thiết kế ở đó được giữ nguyên (vé ký không trạng thái, `KOME_SESSION_SECRET`, scrypt, hai kết nối CSDL). Nhưng **một tiền đề của nó đã sai**, và điều đó đổi vài thứ:

> Spec đợt 1 đóng khung việc lọc theo `salesperson_code` như một **ranh giới bảo mật** — "sale chỉ thấy khách của mình", kèm test canh *"chặn lộ dữ liệu khách của người khác"*.

Chủ sở hữu đã quyết ngược lại: **năm sale không cần giấu nhau.** Công ty năm người, ai cũng biết khách của ai. Đăng nhập riêng là để **cá nhân hoá**, không phải để chặn.

Ba hệ quả:

1. Bộ lọc thành **mặc định tiện dụng**, không phải hàng rào. Rẻ hơn nhiều, và không cần lớp thực thi ở tầng truy vấn.
2. Test *"sale chỉ nhận khách đúng `salesperson_code` của mình"* trong spec đợt 1 §6 phải **bỏ**, không phải giữ — nó khẳng định một bất biến ta vừa quyết là không có.
3. Cột `vai_tro ('sale','quan_ly')` mất hẳn công việc nó được tạo ra để làm. Xem §5.

**Việc phải làm kèm:** cập nhật đầu spec đợt 1 ghi rõ nó đã tách làm đôi và phần danh tính bị tài liệu này thay thế — đây là một tiêu chí hoàn thành còn nợ của lộ trình (§12).

---

## 3. Ràng buộc kế thừa

**R1–R6** của đặc tả nền §3 nguyên vẹn. Ba cái chi phối mạnh nhất:

- **R1** — không có nhân sự IT → giảm tối đa số thứ có thể hỏng.
- **R2** — bảo trì bằng AI → công nghệ phổ thông, không "ma thuật".
- **R3** — OBC là sổ cái chính thức, dữ liệu OBC **chỉ đọc**.

Cộng thêm, từ `CLAUDE.md` và các đợt trước:

- **Không có kho phiên ở máy chủ.** Bắt buộc để chạy Vercel: mỗi lượt gọi có thể rơi vào tiến trình khác.
- **Migration LUÔN chạy bằng vai trò `postgres`** — `ALTER DEFAULT PRIVILEGES` trong migration không có `FOR ROLE`.
- `kome/web/app.py` **không nhập `kome.pipeline`/pandas/calamine ở mức ngoài cùng.**
- Không JS mới, không gói mới trong `requirements.txt`.

---

## 4. Phạm vi

### 4.1 Trong phạm vi

- Migration `019_*.sql`: `core.dim_salesperson` (5 người OBC) + `app.nguoi_dung` + cấp `SELECT` trên `meta.ingest_batch` cho `kome_app` (§6.3).
- Đăng nhập bằng **tên người dùng + mật khẩu riêng**, thay hẳn `KOME_MAT_KHAU`.
- Vé ký bằng `KOME_SESSION_SECRET`, vẫn không trạng thái.
- Kết nối CSDL thứ hai `DATABASE_URL_APP` chạy bằng `kome_app_user`.
- **Chặn màn Kho dữ liệu** theo cờ `duoc_vao_kho_du_lieu` — cả ở sidebar lẫn ở route.
- Mặc định **"khách của tôi"** trên `/khach-hang` và `/can-xu-ly`, có nút xem tất cả.
- `scripts/tao_nguoi_dung.py` để chủ sở hữu tạo và sửa tài khoản.
- Cập nhật `docs/runbook.md`, `CLAUDE.md`, `docs/trien-khai-vercel.md`, và đầu spec đợt 1.

### 4.2 Cắt khỏi phạm vi, và vì sao

- **Màn Cài đặt (thiết kế số 21).** Nội dung duy nhất nó có ở đợt này là quản lý người dùng. Với 5–7 tài khoản đặt một lần, **một script đúng hơn một màn hình** — và khớp nếp đã có (`scripts/hoan_tac.py`, `scripts/bang_phu_du_lieu.py`). Dựng màn khi số tài khoản đủ nhiều để việc sửa tay thành phiền, không trước.
- **Màn Nhật ký thao tác (thiết kế số 20).** Ghi vết ai làm gì là một hệ thống riêng, đáng một đợt của nó. Đăng nhập riêng từng người là **điều kiện cần** cho nó — làm xong đợt này thì đợt đó mới có nghĩa.
- **Dashboard cá nhân hoá.** Chưa có dashboard theo vai trò để mà đặt mặc định; lộ trình §7 xếp nó ở đợt 5.

### 4.3 Không đụng tới

`kome/pipeline.py`, 5 cổng kiểm tra, `kome/coverage.py`, `kome/nhat_ky_nap.py`, `kome/tuoi_du_lieu.py`, `kome/config.py`. Màn Kho dữ liệu **không đổi nội dung**, chỉ thêm cổng chặn ở phía trước.

---

## 5. Quyết định đã chốt qua thảo luận

| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Tách vai trò CSDL bây giờ hay sau? | **Bây giờ.** Chủ sở hữu tạo `kome_app_user` trước, đợt này dựng theo | Nếu code mới lỡ viết `UPDATE core...`, chính CSDL từ chối — lớp an toàn ở tầng quyền, không phụ thuộc review code có bắt được lỗi hay không |
| Sale đăng nhập thì thấy gì? | **Thấy hết.** Mặc định lọc theo mình cho tiện, bấm một nút là xem được khách người khác | Công ty 5 người, ai cũng biết khách của ai. Đăng nhập riêng để **cá nhân hoá**, không phải để chặn |
| Ai vào được màn Kho dữ liệu? | **Chỉ người phụ trách nạp + chủ DN** | Đó là màn có nút xoá dữ liệu. Đợt 2a vừa phát hiện bấm nhầm lô đối soát sẽ xoá **cả tháng doanh thu** — hôm nay bất kỳ ai biết mật khẩu chung đều bấm được |
| Mô hình quyền | **Một boolean `duoc_vao_kho_du_lieu`**, bỏ `vai_tro` và `dashboard_mac_dinh` | Sau khi bỏ việc lọc-để-chặn, `vai_tro` chỉ còn đúng một việc có/không. Một cột làm một việc có/không thì nên là boolean. Thêm cột khi cần, không trước |
| Cài đặt + Nhật ký | **Cắt** khỏi đợt này | §4.2 |
| Quản lý tài khoản bằng gì | **Script**, không phải màn hình | §4.2 |

---

## 6. Kiến trúc

### 6.1 Mô hình dữ liệu — migration `019_danh_tinh.sql`

Chạy bằng vai trò **`postgres`**, như mọi migration.

```sql
CREATE TABLE core.dim_salesperson (
    salesperson_code text PRIMARY KEY,
    ten              text NOT NULL
);

-- Năm người 担当者 của OBC. Số liệu lấy từ đặc tả nền §12.2 (đã đo từ dữ
-- liệu thật), KHÔNG suy đoán mới. Bảng này CHỈ chứa người OBC — không bao
-- giờ trộn với 7 tài khoản của web lên đơn (gồm 2 arubaito chỉ nhập đơn,
-- không phụ trách khách nào). Hai khái niệm khác nhau, xem CLAUDE.md.
INSERT INTO core.dim_salesperson (salesperson_code, ten) VALUES
    ('0002', '西村 巧'),
    ('0004', 'TRINH CONG MINH'),
    ('0102', 'NGUYEN PHUONG DUNG'),
    ('0104', 'TRAN THI LAN THANH'),
    ('0105', 'HA HUY LONG');

CREATE TABLE app.nguoi_dung (
    id                   bigserial PRIMARY KEY,
    ten_dang_nhap        text UNIQUE NOT NULL,
    mat_khau_hash        bytea NOT NULL,
    mat_khau_salt        bytea NOT NULL,
    -- NULL = người này không phụ trách khách nào (chủ DN, kế toán, kho).
    -- Khi NULL thì trang khách hàng không lọc gì — xem §6.5.
    salesperson_code     text NULL REFERENCES core.dim_salesperson,
    -- Cổng vào màn Kho dữ liệu: nạp file, hoàn tác lô. Mặc định FALSE —
    -- quyền phá huỷ phải được cấp tường minh, không phải thứ ai cũng có
    -- vì quên đặt.
    duoc_vao_kho_du_lieu boolean NOT NULL DEFAULT false,
    tao_luc              timestamptz NOT NULL DEFAULT now()
);

-- kome_app đọc được nhật ký nạp. Vai trò này CỐ Ý không ghi được vào
-- `core`, nhưng việc nó không ĐỌC được `meta` là một khoảng trống chứ
-- không phải chủ ý: trang chủ `/` cần `meta.ingest_batch` cho ô "hôm nay
-- đã có dữ liệu chưa". Chỉ SELECT, không INSERT/UPDATE/DELETE.
GRANT USAGE ON SCHEMA meta TO kome_app;
GRANT SELECT ON meta.ingest_batch TO kome_app;
```

**Vì sao không có `vai_tro`:** xem §5. Bỏ một cột dễ hơn thêm một cột sai.

### 6.2 Vé đăng nhập — vẫn không trạng thái

Cơ chế hiện tại (`kome/web/bao_mat.py:73-96`) suy khoá ký **từ chính mật khẩu chung**: đổi mật khẩu là mọi vé cũ chết ngay. Cách đó không dùng được khi có nhiều tài khoản — đổi mật khẩu một người không được làm mọi người khác bị đăng xuất.

**Tách khoá ký khỏi mật khẩu:**

- Biến môi trường mới **`KOME_SESSION_SECRET`** — khoá của hệ thống, không phải mật khẩu của ai.
- Mật khẩu từng người băm bằng **`hashlib.scrypt`** (có sẵn trong Python chuẩn — **không thêm gói mới**, đúng R2), salt ngẫu nhiên 16 byte lưu cùng.
- Vé: `"<id>.<hạn>.<HMAC-SHA256(f'{id}.{hạn}', KOME_SESSION_SECRET)>"`.

**Chữ ký phải phủ CẢ `id` lẫn `hạn`.** Ký riêng `hạn` thôi thì đổi `id` trong cookie là hoá thân thành người khác mà chữ ký vẫn đúng. Đây là chỗ dễ sai nhất của cả đợt và phải có test riêng.

Giữ nguyên `hmac.compare_digest` và thứ tự "so chữ ký trước khi đọc hạn" của bản hiện tại — ghi chú tại chỗ đã giải thích lý do (so sánh hết thời gian như nhau nên không đo được chữ ký đúng là gì).

**Thu hồi quyền:** đổi `KOME_SESSION_SECRET` → đăng xuất **tất cả** (dùng khi nghi rò rỉ). Đổi mật khẩu một người → chỉ ảnh hưởng người đó ở lượt đăng nhập kế tiếp; vé đang có hiệu lực của họ sống tới hết hạn. Hạn vé là 12 giờ (`HAN_PHIEN_GIAY` hiện tại). Chấp nhận được ở quy mô này; vô hiệu hoá tức thì cần kho phiên, mà kho phiên phá luật Vercel.

### 6.3 Hai kết nối CSDL

| Kết nối | Vai trò | Dùng cho |
|---|---|---|
| `DATABASE_URL` | `kome_ingest_user` (hôm nay vẫn là `postgres`) | Màn Kho dữ liệu: nạp, hoàn tác, sức khoẻ, độ phủ |
| `DATABASE_URL_APP` | `kome_app_user` | Đăng nhập, `/`, `/khach-hang`, `/can-xu-ly`, `/bao-cao` |

`kome/db.py::connect()` đã nhận `url` tuỳ chọn — **không cần sửa hàm đó**.

Ranh giới: mọi route **đọc** đi qua `DATABASE_URL_APP`; chỉ màn Kho dữ liệu — nơi thật sự ghi và xoá `core` — dùng `DATABASE_URL`. Nếu code mới lỡ viết một câu ghi vào `core`, CSDL từ chối.

### 6.4 Chặn màn Kho dữ liệu

Middleware `chan_cua` hiện kiểm vé cho mọi đường dẫn. Thêm một cổng thứ hai **chỉ cho các đường dẫn của Kho dữ liệu**: `/kho-du-lieu`, `POST /upload`, `POST /undo/{id}`, và ba địa chỉ cũ đang trả 301.

**Cờ `duoc_vao_kho_du_lieu` KHÔNG nằm trong vé** — tra CSDL mỗi lần vào những đường dẫn đó, **qua `DATABASE_URL_APP`** (bảng `app.nguoi_dung` thuộc về kết nối đó; màn Kho dữ liệu vẫn đọc dữ liệu của nó qua `DATABASE_URL`). Lý do: đây là màn có nút xoá dữ liệu, nên thu hồi quyền phải có hiệu lực **ngay**, không phải chờ 12 giờ cho vé cũ hết hạn. Đây là màn một người mở một lần mỗi ngày, nên một truy vấn thêm không đáng kể.

Không có quyền thì:
- Sidebar **không hiện** mục Kho dữ liệu (cùng cơ chế `chi_doc` đang dùng để ẩn khối nạp).
- Route trả **403** kèm trang giải thích, không phải chuyển hướng im lặng. Người gõ thẳng địa chỉ cần biết vì sao mình không vào được, không phải tự hỏi trang có hỏng không.

### 6.5 Mặc định "khách của tôi"

`/khach-hang` và `/can-xu-ly`: nếu người đăng nhập có `salesperson_code`, mặc định chỉ hiện khách của họ. Một liên kết hiện rõ — *"Xem tất cả khách →"*, kèm số đếm thật lấy từ truy vấn chứ không viết cứng — bỏ bộ lọc (`?tat_ca=1`). Khi đang lọc, trang nói rõ đang lọc theo ai.

Người **không có** `salesperson_code` (chủ DN, kế toán): không lọc gì, thấy toàn bộ ngay từ đầu.

Đây **không phải** hàng rào bảo mật — chỉ là mặc định. Không có kiểm quyền nào ở đây, và điều đó là cố ý (§5).

### 6.6 Chốt an toàn thay cho `KOME_MAT_KHAU`

Hôm nay `bao_mat.kiem_cau_hinh` **từ chối dựng app** nếu chạy công khai (`VERCEL` được đặt) mà không có `KOME_MAT_KHAU`. Bỏ mật khẩu chung thì chốt đó mất, và một bản công khai không cổng là hỏng theo cách tệ nhất.

Thay bằng chốt cùng hình dạng: **từ chối dựng app nếu công khai mà `KOME_SESSION_SECRET` chưa đặt hoặc ngắn hơn `DAI_TOI_THIEU`**. Thông báo lỗi chỉ đúng chỗ phải sửa, như thông báo hiện tại đang làm với `KOME_MAT_KHAU`.

**Không kiểm "đã có tài khoản nào chưa" lúc khởi động** — làm vậy là buộc việc dựng app phụ thuộc CSDL, và một CSDL chậm sẽ thành app không khởi động được.

`KOME_MAT_KHAU` bị **bỏ hẳn**, không duy trì song song hai cơ chế xác thực. Hai cổng đăng nhập là hai chỗ để sai.

---

## 7. Quản lý tài khoản — `scripts/tao_nguoi_dung.py`

Theo nếp `scripts/hoan_tac.py`: chạy bằng tay, in ra thứ cần biết, không có giao diện.

```
python scripts/tao_nguoi_dung.py                      liệt kê tài khoản
python scripts/tao_nguoi_dung.py them <tên> [--sale <mã>] [--kho-du-lieu]
python scripts/tao_nguoi_dung.py doi-mat-khau <tên>
python scripts/tao_nguoi_dung.py quyen <tên> --kho-du-lieu | --bo-kho-du-lieu
```

Mật khẩu nhập qua `getpass` — **không bao giờ nhận qua tham số dòng lệnh**: tham số nằm lại trong lịch sử shell và trong danh sách tiến trình. Script không in mật khẩu ra màn hình, không ghi vào log.

Lệnh liệt kê in: tên đăng nhập, mã sale, có quyền Kho dữ liệu không, tạo lúc nào. **Không in hash, không in salt.**

---

## 8. Việc tay ngoài git — làm TRƯỚC khi viết code

Ba việc chỉ chủ sở hữu làm được, và §6.3 phụ thuộc vào việc đầu tiên:

1. **SQL Editor của Supabase:** `CREATE USER kome_app_user LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_app;`
2. **`.env` và biến môi trường Vercel:** thêm `DATABASE_URL_APP` (dùng `kome_app_user`) và `KOME_SESSION_SECRET` (chuỗi ngẫu nhiên, tối thiểu 12 ký tự).
3. **Sau khi triển khai:** tạo tài khoản cho từng người bằng script §7, và cấp `--kho-du-lieu` cho **đúng** người phụ trách nạp và chủ DN.

Mật khẩu chỉ tồn tại trong bảng điều khiển Supabase và biến môi trường — **không commit vào git, không dán vào chat, không ghi trong file nào của repo.**

---

## 9. Kiểm thử

Test hiện có phải **xanh nguyên**, trừ những test về `KOME_MAT_KHAU` — cơ chế đó bị bỏ, nên test của nó phải được **viết lại cho cơ chế mới**, không phải xoá đi. Bất biến chúng canh (chưa đăng nhập thì không vào được; đăng xuất thì hết vào được; bản công khai bắt buộc có cổng) vẫn còn nguyên giá trị.

| Test | Chặn thảm hoạ gì |
|---|---|
| Đổi `id` trong vé mà giữ chữ ký → **vé không hợp lệ** | Hoá thân thành người khác bằng cách sửa một cookie |
| Vé hết hạn → không vào được, dù chữ ký đúng | Phiên sống mãi |
| Đổi `KOME_SESSION_SECRET` → mọi vé cũ chết | Không thu hồi được quyền khi nghi rò rỉ |
| Đổi mật khẩu một người → **không** làm người khác đăng xuất | Đúng cái lỗi của cơ chế cũ mà đợt này sinh ra để sửa |
| Sai mật khẩu → 401, không đặt cookie | Đăng nhập được mà không cần mật khẩu |
| Người **không** có `duoc_vao_kho_du_lieu`: `/kho-du-lieu` → 403, `POST /upload` → 403, `POST /undo/1` → 403 | Sale bấm nhầm nút xoá cả tháng doanh thu |
| Người không có quyền: sidebar không chứa liên kết Kho dữ liệu | Mời người ta bấm vào một thứ sẽ từ chối họ |
| Bỏ cờ quyền của một người → **lượt gọi kế tiếp** đã bị chặn, không chờ vé hết hạn | Thu hồi quyền phá huỷ mà phải đợi 12 giờ |
| `kome_app` **không** có quyền `UPDATE` trên `core.*` | "OBC chỉ đọc" bị phá bởi một dòng code viết nhầm |
| `kome_app` **có** quyền `SELECT` trên `meta.ingest_batch` | Trang chủ 500 trên bản chạy bằng `kome_app_user` vì thiếu quyền đọc |

Hai test quyền cuối dùng **`has_table_privilege('kome_app', …)`** với fixture
`fresh_conn`, theo đúng nếp `tests/test_roles.py` đã có. Cách đó kiểm được quyền
**mà không cần tài khoản đăng nhập nào tồn tại** — quan trọng, vì CSDL thử nghiệm
không có `kome_app_user`.
| Công khai (`VERCEL=1`) mà thiếu `KOME_SESSION_SECRET` → app **không dựng được** | Bản công khai không có cổng nào |
| `/khach-hang` mặc định lọc theo người đăng nhập; `?tat_ca=1` bỏ lọc | Mặc định không chạy, hoặc chạy mà không thoát ra được |
| Người không có `salesperson_code` → không lọc gì | Chủ DN mở lên thấy danh sách rỗng |

---

## 10. Rủi ro & giả định

| # | Vấn đề | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| D1 | `kome_app_user` chưa tồn tại lúc viết đặc tả này (đã kiểm 2026-09-21: chỉ có 3 vai trò `NOLOGIN`, app chạy bằng `postgres`) | **Cao — chặn §6.3** | §8 việc 1, làm trước khi viết code |
| D2 | Đổi cơ chế đăng nhập là đổi thứ chặn cửa bản công khai. Sai một bước là mở toang | Cao | §6.6 chốt an toàn; và triển khai Vercel phải kiểm tay ngay sau đó |
| D3 | `core.dim_salesperson` seed 5 người bằng migration. Nếu OBC thêm/bớt người thì bảng lệch | Thấp | Số liệu lấy từ đặc tả nền §12.2 đã đo thật. Thêm người là một migration mới một dòng |
| D4 | 7 khách hiện có `salesperson_code` rỗng (`''`, đã đo ở spec đợt 1 G6) | Thấp | Mặc định lọc sẽ không hiện họ cho ai. Chấp nhận được: nút "Xem tất cả" vẫn thấy, và đây là mặc định chứ không phải hàng rào |
| D5 | Người dùng quên mật khẩu, không có luồng tự phục hồi | Thấp | Chủ sở hữu đặt lại bằng script §7. Đúng cách `KOME_MAT_KHAU` đang được đặt hôm nay |
| D6 | Tra CSDL mỗi lượt vào Kho dữ liệu (§6.4) thêm một truy vấn | Thấp | Màn này mở một lần mỗi ngày. Đổi lại là thu hồi quyền có hiệu lực ngay — đúng thứ đáng đánh đổi cho một màn có nút xoá |

---

## 11. Tiêu chí hoàn thành

- [ ] Đăng nhập bằng tài khoản riêng; `KOME_MAT_KHAU` không còn trong code
- [ ] Sửa `id` trong vé không hoá thân được thành người khác (có test)
- [ ] Người không có quyền: không thấy mục Kho dữ liệu, và gõ thẳng địa chỉ thì nhận 403 — cả `/kho-du-lieu`, `/upload`, `/undo`
- [ ] Bỏ cờ quyền → lượt gọi kế tiếp đã bị chặn
- [ ] `kome_app` không ghi được vào `core` (kiểm bằng test, không chỉ bằng đọc migration)
- [ ] `/khach-hang` và `/can-xu-ly` mặc định lọc theo người đăng nhập, có nút xem tất cả
- [ ] `scripts/tao_nguoi_dung.py` tạo/sửa/liệt kê được, không in mật khẩu
- [ ] `runbook.md`, `CLAUDE.md`, `trien-khai-vercel.md` cập nhật; đầu spec đợt 1 ghi rõ đã bị thay thế phần danh tính
- [ ] `pytest -v` xanh toàn bộ
- [ ] Triển khai Vercel rồi **kiểm tay**: chưa đăng nhập không vào được; đăng nhập bằng tài khoản không có quyền thì không thấy Kho dữ liệu

---

## 12. Bước tiếp theo

1. Chủ sở hữu đọc và duyệt đặc tả này
2. **Việc tay §8** — tạo `kome_app_user`, thêm hai biến môi trường
3. Lập kế hoạch triển khai (writing-plans)
4. Thực thi, kiểm chứng bằng mắt, merge, deploy
5. Đợt kế tiếp theo lộ trình: đợt 4 — Customer 360 · Sản phẩm · Kho hàng · Bản đồ
