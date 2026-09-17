# Đặc tả thiết kế — Đăng nhập theo người dùng + Dashboard + CRM đợt 1

**Ngày:** 2026-09-17
**Công ty:** 株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật
**Phạm vi tài liệu:** Giai đoạn 2 (CRM nội bộ) — **đợt 1**: thay cơ chế đăng nhập chung
bằng tài khoản riêng từng người, dựng khung dashboard bố cục cố định theo vai trò, và
tính năng CRM đầu tiên: **danh sách ưu tiên liên hệ + nhật ký chăm sóc khách**.
**Trạng thái:** Chờ duyệt
**Tài liệu liên quan:** `docs/superpowers/specs/2026-09-16-kome-data-platform-design.md`
(gọi tắt "đặc tả nền" trong tài liệu này) — đặc tả đó liệt kê "CRM nội bộ" là Giai đoạn 2,
ngoài phạm vi của nó. Tài liệu này mở đầu Giai đoạn 2.

---

## 1. Bối cảnh

Giai đoạn 0+1 đã chạy: nạp dữ liệu từ OBC, `mart.khach_360` tính đúng nhịp mua riêng
từng khách, trang `/can-xu-ly` liệt kê khách cần xử lý. Nhưng khảo sát thực tế cho thấy:

1. **Nhân viên Hà Huy Long (`0105`) đã tự xây một công cụ CRM thu nhỏ bằng Excel**
   (`販売分析.xlsx`) để bù vào chỗ thiếu: chấm điểm ưu tiên gọi khách theo số ngày im
   lặng, cảnh báo khách lớn đang giảm tốc độ mua, gợi ý upsell theo từng mặt hàng, và
   một bảng ghi chú khách hàng. 4 nhân viên còn lại thỉnh thoảng dùng ké.
2. **Điểm đau lớn nhất: mỗi ngày Long tự tay copy-paste dữ liệu từ file OBC xuất ra
   vào Excel** — hoàn toàn tách biệt với pipeline nạp dữ liệu đã tự động hoá của
   `kome-data`. Đây là công sức trùng lặp thuần tuý.
3. **Không nơi nào ghi lại kết quả các cuộc gọi/nhắn tin/thăm khách.** Toàn bộ nằm
   trong đầu hoặc tin nhắn cá nhân từng nhân viên — mất hoàn toàn nếu nhân viên nghỉ.
4. `/can-xu-ly` hiện chỉ hiện khách có `ty_le_im_lang >= 2` (đã ở mức cảnh báo), sắp
   theo doanh thu, **không lọc theo người phụ trách**, và không có khái niệm "lý do
   liên hệ" hay "điểm ưu tiên" — khách ở dải `1.0–2.0` (sắp đến hạn mua lại, đúng vùng
   Excel gọi là `そろそろ連絡`/`再注文確認`) hiện **không hiện ở đâu cả**. Nhân viên chỉ
   biết gọi sau khi khách đã trễ hẳn, không gọi được trước để giữ chân.

Người chủ sở hữu hệ thống đã mô tả bức tranh xa hơn (ngoài phạm vi tài liệu này, nhưng
định hình kiến trúc ở đây): một website có đăng nhập riêng từng người, dashboard cá
nhân hoá, và các mục điều hướng Report / CRM / Customer 360 / Product 360 / Đối thủ &
Thông tin thị trường. Quyết định đã chốt: **dựng khung đăng nhập-theo-người-dùng +
dashboard trước, CRM là nội dung đầu tiên đưa vào khung đó** — vì CRM cá nhân hoá
("chỉ hiện khách của tôi") không có ý nghĩa nếu chưa biết "tôi" là ai.

---

## 2. Quyết định đã chốt qua thảo luận

| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Đăng nhập chung hay riêng từng người? | **Riêng từng người**, thay hẳn `KOME_MAT_KHAU` chung | Cần biết ai xem/ghi gì; sale chỉ thấy khách mình phụ trách, quản lý thấy hết |
| Ai dùng dashboard? | 5 sale (theo `salesperson_code` OBC) + chủ DN/quản lý | Quản lý cần thấy toàn bộ, không bị lọc theo người |
| Bố cục dashboard | **Cố định theo vai trò**, kéo-thả để sau | Chưa đủ block hữu ích để việc tuỳ chỉnh có ý nghĩa; kéo-thả tốn công xây (lưu bố cục riêng, thư viện kéo-thả) |
| Tính năng CRM làm trước | **Danh sách ưu tiên liên hệ** (thay `営業エンジン`) | Tận dụng trực tiếp `mart.khach_360` đã có, xoá bỏ hoàn toàn việc Long phải copy-paste |
| Nhật ký chăm sóc có cần đi kèm không | **Có, bắt buộc đi cùng đợt này** | Danh sách ưu tiên vô nghĩa nếu gọi xong không ghi được kết quả — khách sẽ hiện lại y nguyên hôm sau |
| Trường tối thiểu của một lượt ghi chú | Kết quả, kênh liên hệ, ghi chú tự do, ngày hẹn gọi lại | Cả 4 đều được chọn là cần thiết |
| Vai trò CSDL cho phần ghi mới | **`kome_app`** (đã tạo ở Task 13, chưa ai dùng) | Đúng thiết kế đã có sẵn — SELECT `core`/`mart`, đọc-ghi `app`, không đụng được `core` kể cả lỡ tay |

---

## 3. Ràng buộc kế thừa từ đặc tả nền

- **R1–R6** (không có IT, bảo trì bằng AI, OBC chỉ đọc, xuất thủ công, vòng đời 5 năm,
  ngân sách nhỏ) vẫn áp dụng nguyên vẹn.
- **Không có kho phiên ở máy chủ** — điều kiện bắt buộc để chạy trên Vercel (mỗi lượt
  gọi có thể rơi vào tiến trình khác). Đổi sang đăng nhập riêng từng người **không được
  phá vỡ tính chất này** — xem §5.1.
- **Mọi logic nghiệp vụ nằm trong SQL ở `mart`**, không nằm trong code Python hay
  template — áp dụng cho cách tính điểm ưu tiên/lý do liên hệ.
- **Không sửa dữ liệu OBC** — `core`/`mart` vẫn chỉ đọc với mọi vai trò trừ `kome_ingest`.

---

## 4. Phạm vi

### 4.1 Trong phạm vi đợt này

- Bảng `core.dim_salesperson` (5 người OBC — dữ liệu đã có sẵn ở đặc tả nền §12.2,
  không suy đoán mới) và file `config/salesperson_map.yml` (đã được lên kế hoạch từ
  đặc tả nền, giờ hiện thực hoá).
- Bảng `app.nguoi_dung`: tài khoản đăng nhập, gồm vai trò (`sale` / `quan_ly`).
- Mở rộng cơ chế vé đăng nhập hiện có (`kome/web/bao_mat.py`) để mang theo danh tính
  người dùng, **vẫn không trạng thái**.
- Layout điều hướng dùng `{% block %}` thật (hiện `_nav.html` chỉ là include tĩnh),
  dashboard bố cục cố định, khác nhau giữa vai trò `sale` và `quan_ly`.
- View `mart` mới: điểm ưu tiên + lý do liên hệ, mở rộng vùng hiển thị xuống dải
  "sắp đến hạn" (`ty_le_im_lang` 1,0–2,0) mà không đổi các ngưỡng `trang_thai` hiện có
  của `mart.khach_360` (đã kiểm chứng bằng số liệu thật, không đụng vào).
- Bảng `app.nhat_ky_cham_soc`: kết quả, kênh, ghi chú, ngày hẹn gọi lại.
- Route CRM mới hiển thị danh sách ưu tiên liên hệ (lọc theo người đăng nhập nếu là
  sale, toàn bộ nếu là quản lý) và form ghi nhận kết quả liên hệ.
- Kết nối CSDL thứ hai trong code, xác thực bằng `kome_app`, dùng riêng cho các route
  mới — tách biệt khỏi kết nối `kome_ingest` hiện tại.

### 4.2 Ngoài phạm vi (đợt sau)

- Kéo-thả tuỳ chỉnh dashboard.
- Ba tính năng CRM còn lại: cảnh báo khách lớn giảm tốc, công cụ đẩy sản phẩm theo
  chiến dịch, gợi ý upsell theo từng khách + tag hành vi.
- Product 360, Đối thủ & Thông tin thị trường — chưa đủ rõ để spec, cần bàn riêng.
- Tự phục vụ đổi mật khẩu, quên mật khẩu, 2FA. MVP: chủ sở hữu đặt mật khẩu ban đầu
  cho từng người, giống cách `KOME_MAT_KHAU` đang được đặt tay hiện nay.

---

## 5. Kiến trúc

### 5.1 Đăng nhập theo người dùng, vẫn không lưu phiên ở máy chủ

Cơ chế hiện tại (`bao_mat.py`) cố ý suy khoá ký HMAC **từ chính mật khẩu chung** — đổi
mật khẩu là mọi vé cũ hết hạn ngay, đó là cách "đuổi" một người nghỉ việc mà không cần
kho phiên. Cơ chế này không còn phù hợp khi có nhiều tài khoản: đổi mật khẩu của một
người không được phép làm mọi người khác bị đăng xuất.

**Quyết định:** tách khoá ký ra khỏi mật khẩu người dùng.

- Thêm biến môi trường mới **`KOME_SESSION_SECRET`** — một khoá bí mật duy nhất của
  hệ thống, không phải mật khẩu của ai cả, chỉ dùng để ký vé.
- Mật khẩu từng người **không lưu dạng chữ thường** — băm bằng `hashlib.scrypt`
  (có sẵn trong Python chuẩn, **không thêm thư viện phụ thuộc mới**, đúng tinh thần
  "công nghệ phổ thông" của đặc tả nền), lưu kèm salt ngẫu nhiên trong `app.nguoi_dung`.
- Vé mới: `"<user_id>.<hạn>.<HMAC-SHA256((user_id, hạn), KOME_SESSION_SECRET)>"` —
  vẫn là chuỗi tự chứng thực, không cần tra CSDL để xác thực vé (chỉ tra CSDL lúc đăng
  nhập để kiểm mật khẩu). Đổi `KOME_SESSION_SECRET` = đăng xuất TẤT CẢ mọi người (dùng
  khi nghi ngờ rò rỉ); còn đổi mật khẩu một người chỉ ảnh hưởng người đó ở lượt đăng
  nhập kế tiếp — không đăng xuất được vé đang có hiệu lực của riêng người đó ngay lập
  tức (chấp nhận được: hạn vé hiện tại là 12 giờ, và MVP không cần vô hiệu hoá tức thì).
- **Đăng nhập theo người dùng thay thế hoàn toàn** cổng `KOME_MAT_KHAU` hiện tại — không
  duy trì song song hai cơ chế xác thực. Middleware `chan_cua` kiểm vé mới; `/nap`,
  `/health`, `/phu-du-lieu` được gộp vào cùng hệ thống tài khoản, giới hạn hiển thị theo
  vai trò `quan_ly` giống cách `_nav.html` đang ẩn `/nap` khi `chi_doc=true`.

### 5.2 Không đổi công nghệ frontend

Hiện tại: Jinja2 server-render thuần, không JS framework, không CSS framework
(`kome/web/templates/`, không có `static/`). Vì bố cục dashboard đợt này **cố định**,
không cần JS phức tạp — giữ nguyên đúng công nghệ đang dùng. Quyết định về thư viện
kéo-thả (khi làm đợt sau) hoãn tới lúc đó, không quyết định trước cho một tính năng
chưa xây.

### 5.3 Tách kết nối CSDL theo vai trò ngay trong code

`kome/db.py` hiện có một kết nối duy nhất, xác thực bằng `kome_ingest_user` (theo luật
đã ghi trong `CLAUDE.md`), đọc từ biến môi trường `DATABASE_URL`. Người dùng
`kome_app_user` **đã được tạo sẵn** từ trước (`docs/runbook.md`, cùng lượt tạo với
`kome_ingest_user`) nhưng chưa ai dùng — không cần tạo tài khoản CSDL mới, chỉ cần:

1. Thêm biến môi trường mới `DATABASE_URL_APP` — chuỗi kết nối dùng `kome_app_user`.
2. Trong code, gọi `db.connect(os.environ["DATABASE_URL_APP"])` (hàm `connect()` ở
   `kome/db.py` đã nhận `url` tuỳ chọn, không cần sửa hàm này) cho **mọi route mới**
   trong đợt này (đăng nhập, dashboard, danh sách ưu tiên liên hệ, ghi nhật ký).

Route nạp/hoàn tác hiện tại giữ nguyên kết nối `DATABASE_URL`/`kome_ingest_user` — không đổi.

Lợi ích không chỉ là đúng thiết kế Task 13: nếu code CRM mới lỡ viết nhầm một câu lệnh
`UPDATE core...`, CSDL tự chặn (`kome_app` không có quyền đó) — một lớp an toàn nằm ở
tầng quyền, không phụ thuộc vào việc review code có bắt được lỗi hay không.

### 5.4 Mô hình dữ liệu mới (migration `017_...sql`, chạy bằng vai trò `postgres`)

```
core.dim_salesperson
  salesperson_code   text PK   -- '0002','0004','0102','0104','0105' (đặc tả nền §12.2)
  ten                text
  ma_web_order        text NULL  -- '01'..'04', ánh xạ config/salesperson_map.yml
  la_arubaito         boolean NOT NULL DEFAULT false  -- luôn false ở đây: bảng này
                                                       -- CHỈ chứa 5 người OBC, không
                                                       -- bao giờ trộn người lên đơn

app.nguoi_dung
  id                 bigint PK
  ten_dang_nhap      text UNIQUE
  mat_khau_hash      bytea
  mat_khau_salt      bytea
  vai_tro            text CHECK IN ('sale', 'quan_ly')
  salesperson_code   text NULL REFERENCES core.dim_salesperson
                       -- NULL bắt buộc khi vai_tro = 'quan_ly'
                       -- NOT NULL bắt buộc khi vai_tro = 'sale'
  tao_luc            timestamptz DEFAULT now()

app.nhat_ky_cham_soc
  id                 bigint PK
  customer_code      text        -- khoá tự nhiên, KHÔNG ép số (luật CLAUDE.md #1)
  nguoi_dung_id       bigint REFERENCES app.nguoi_dung
  thoi_diem          timestamptz DEFAULT now()
  kenh               text CHECK IN ('goi_dien','messenger','den_tham')
  ket_qua            text CHECK IN ('dat_hang','tu_choi','khong_nghe_may','khac')
  ghi_chu            text NULL
  ngay_hen_lai       date NULL
```

Ràng buộc CHECK ở `nguoi_dung` (salesperson_code NULL khi và chỉ khi `quan_ly`) đảm
bảo không thể tạo một tài khoản "sale không có khách nào" hay "quản lý bị lọc theo
khách" do nhập liệu sai — lỗi hiện ngay lúc tạo tài khoản, không phải lúc dùng.

### 5.5 View `mart` mới — lý do liên hệ + điểm ưu tiên

**Không sửa `mart.khach_360`** — các ngưỡng `trang_thai` (`canh_bao >= 2`,
`da_roi_bo >= 4`) đã được kiểm chứng bằng số liệu thật và có lý do rõ ràng trong
`016_khach_ngung_giao_dich.sql`. Thêm một view riêng, **đọc từ `khach_360`**, phủ dải
rộng hơn cho đúng mục đích "ai cần gọi hôm nay":

```sql
CREATE VIEW mart.uu_tien_lien_he AS
SELECT customer_code, salesperson_code, ten, phone, doanh_thu_thuan,
       ty_le_im_lang, nhip_ngay, so_ngay_im_lang,
       CASE
         WHEN ty_le_im_lang >= 4   THEN 'lau_khong_mua'
         WHEN ty_le_im_lang >= 2   THEN 'qua_han_xac_nhan'
         WHEN ty_le_im_lang >= 1   THEN 'sap_den_han'
       END AS ly_do
FROM mart.khach_360
WHERE trang_thai NOT IN ('ngung_giao_dich', 'chua_du_lich_su')
  AND ty_le_im_lang >= 1;
```

**Sắp xếp**, giữ đúng nguyên tắc đã có ở `/can-xu-ly` (ưu tiên khách giá trị cao hơn
mức độ trễ — một khách ¥5 triệu trễ 3 lần quan trọng hơn khách ¥50 nghìn trễ 10 lần):
sắp theo nhóm `ly_do` (`lau_khong_mua` → `qua_han_xac_nhan` → `sap_den_han`), trong
từng nhóm sắp theo `doanh_thu_thuan` giảm dần. Cố tình **không** dùng một công thức
nhân điểm kiểu Excel (`優先度`) — công thức đó không giải thích được, khó bảo trì, và
không ai (kể cả Long) nhớ rõ vì sao ra đúng con số đó.

### 5.6 Route & luồng (mức chức năng, chưa vào chi tiết giao diện)

- `/dang-nhap`: chọn tài khoản + mật khẩu, thay hẳn ô nhập `KOME_MAT_KHAU` chung.
- `/` (dashboard): nội dung khác nhau theo `vai_tro` — sale thấy khối "Cần liên hệ hôm
  nay" lọc theo `salesperson_code` của chính họ; quản lý thấy toàn công ty.
- Trang danh sách ưu tiên liên hệ: liệt kê `mart.uu_tien_lien_he`, mỗi dòng có lối vào
  ghi nhận kết quả (ghi vào `app.nhat_ky_cham_soc`).
- Hồ sơ khách `/khach-hang/{mã}`: thêm mục lịch sử nhật ký chăm sóc (đọc
  `app.nhat_ky_cham_soc` theo `customer_code`) — tận dụng trang đã có, không tạo trang
  mới.

---

## 6. Vận hành & kiểm thử

Bổ sung vào bộ test hiện có (`pytest -v`):

| Test | Chặn thảm hoạ gì |
|---|---|
| Vé mới xác thực đúng, hết hạn đúng giờ, không cần tra CSDL | Đăng nhập sai người, hoặc phải lưu phiên (phá luật Vercel) |
| Đổi `KOME_SESSION_SECRET` đăng xuất mọi người; đổi mật khẩu 1 người không ảnh hưởng người khác | Thu hồi quyền truy cập không đúng phạm vi |
| Sale đăng nhập chỉ nhận khách đúng `salesperson_code` của mình từ `mart.uu_tien_lien_he` | Lộ dữ liệu khách của người khác |
| Kết nối `kome_app` thử `UPDATE core.dim_customer` → bị CSDL từ chối | Luật "OBC chỉ đọc" bị phá bởi một dòng code CRM viết nhầm |
| Tạo `app.nguoi_dung` với `vai_tro='sale'` và `salesperson_code=NULL` → bị CSDL từ chối | Tài khoản sale không lọc được khách |
| Ghi + đọc lại `app.nhat_ky_cham_soc` theo đúng khách | Nhật ký ghi sai khách hoặc mất khi đọc lại |

Không đổi gì ở pipeline nạp (`/nap`, 5 cổng kiểm tra, đối soát tháng) — route đó tiếp
tục dùng kết nối `kome_ingest` như cũ, không rủi ro tới luồng đang chạy ổn định.

---

## 7. Rủi ro & giả định cần xác nhận

| # | Vấn đề | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| G1 | `core.dim_salesperson` và `config/salesperson_map.yml` chưa từng được tạo, dù đã lên kế hoạch từ đặc tả nền | Trung bình | Dùng đúng bảng đối chiếu đã đo ở đặc tả nền §12.2, không suy đoán mới |
| G2 | Mật khẩu ban đầu của từng người: ai đặt, gửi bằng kênh nào | Thấp | Chủ sở hữu đặt tay từng người, giống cách `KOME_MAT_KHAU` hiện đặt — ngoài phạm vi kỹ thuật của tài liệu này |
| G3 | Đợt sau (kéo-thả) sẽ cần một bảng lưu bố cục riêng từng người | Thấp | Chỉ ghi chú tên dự kiến `app.bo_cuc_dashboard` ở đây để tránh trùng tên sau này — **không tạo bảng này bây giờ** |
| G4 | `ty_le_im_lang >= 1` có thể tạo danh sách khá dài (nhiều khách "sắp đến hạn") | Trung bình | Đo thử trên dữ liệu thật sau khi triển khai; nếu quá dài, cân nhắc thêm ngưỡng doanh thu tối thiểu — quyết định sau khi có số liệu, không đoán trước |

---

## 8. Tiêu chí hoàn thành

- [ ] Đăng nhập bằng tài khoản riêng; `KOME_MAT_KHAU` không còn là cổng duy nhất
- [ ] Sale đăng nhập chỉ thấy khách/danh sách liên hệ của đúng `salesperson_code` mình; quản lý thấy toàn bộ
- [ ] Danh sách ưu tiên liên hệ hiện đúng 3 nhóm lý do (`sap_den_han`, `qua_han_xac_nhan`, `lau_khong_mua`), sắp đúng thứ tự đã định nghĩa
- [ ] Ghi nhận kết quả liên hệ lưu đủ 4 trường (kết quả, kênh, ghi chú, ngày hẹn lại), xem lại được trên hồ sơ khách 360°
- [ ] Route nạp/hoàn tác hiện tại không đổi hành vi, không đổi kết nối CSDL
- [ ] Thử ghi vào `core` bằng kết nối `kome_app` → bị từ chối (kiểm chứng bằng test, không chỉ bằng đọc migration)
- [ ] `pytest -v` xanh toàn bộ, bao gồm các test mới ở §6

---

## 9. Bước tiếp theo

1. Chủ sở hữu đọc và duyệt đặc tả này
2. Thêm biến môi trường `DATABASE_URL_APP` (dùng `kome_app_user` đã có sẵn) và
   `KOME_SESSION_SECRET` (khoá ký vé mới) vào `.env` và vào cấu hình triển khai
3. Viết migration `017_...sql` (bảng + view, chạy bằng vai trò `postgres`)
4. Lập kế hoạch triển khai chi tiết (writing-plans)
5. Triển khai, chạy `pytest -v`, kiểm thử tay luồng đăng nhập + ghi nhật ký trên trình duyệt trước khi coi là xong
