# Ngữ cảnh dự án kome-data

## Công ty làm gì
株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật.
~¥1,5 tỷ doanh thu/năm · 2.080 khách hàng · 232 mã hàng · 5 nhân viên phụ trách khách.
Khách chủ yếu là tạp hoá Việt (577) và quán ăn Việt (269), trải 48 tỉnh.

## Luật số một
**OBC 奉行 là sổ cái kế toán chính thức. Dữ liệu của nó CHỈ ĐỌC.**
Số sai thì sửa trong OBC rồi xuất lại — không bao giờ UPDATE trong CSDL này.

## Quy trình hằng ngày
13:30 nhân viên xuất 3 file từ OBC, kéo thả vào trang nội bộ.
Đầu mỗi tháng xuất lại toàn bộ tháng trước để bắt các phiếu đã bị sửa/huỷ (đối soát tháng).

## Từ điển
得意先 = khách hàng · 請求先 = bên nhận hoá đơn (có thể khác 得意先)
伝票 = phiếu · 赤伝 = phiếu đỏ (hàng trả lại, số ÂM, không được lọc bỏ)
粗利益 = lãi gộp · 単価 = đơn giá · 単位原価 = giá vốn đơn vị
締め日 = ngày chốt công nợ · 直送先 = điểm giao thẳng
担当者 = người phụ trách khách · 倉庫 = kho · 賞味期限 = hạn sử dụng
荷姿区分 = quy cách đóng gói (00 = バラ lẻ, 02 = ケース thùng)

## Bẫy đã biết
1. Mã (`*コード`) là TEXT. `000000009292` đọc thành số sẽ mất số 0 đầu → hỏng mọi liên kết.
2. Số lượng CÓ phần thập phân (`83.75` ケース). Tiền thì luôn là số nguyên yên.
3. Có bản xuất `得意先全情報` chỉ 201 dòng (xuất một phần — **cổng 3** chặn vì dưới `min_rows`) và bản chỉ 5 cột (sai mẫu — **cổng 2** chặn trước, `ColumnMismatch`, vì thiếu cột khai báo).
4. File `元帳` có 5 dòng rác trước header (CHƯA kiểm chứng lại). `売上明細表`
   đã đo thật (2026-09-17): header ở dòng 1, KHÔNG có dòng rác — có thể do
   OBC đổi mẫu xuất, hoặc quan sát cũ chỉ đúng cho một cấu hình xuất khác.
   File master và `在庫一覧` thì header ở dòng 1.
5. `担当者` của OBC (5 người) KHÁC người nhập đơn trên web (7 tài khoản, gồm 2 arubaito).

## Bốn vai trò CSDL (Task 13, `db/migrations/009_roles.sql`)
Luật số một ("OBC chỉ đọc") không chỉ là quy ước trong code — nó là ràng
buộc của chính CSDL. Bốn vai trò cấp cụm (`NOLOGIN`, mật khẩu đặt tay ngoài
git — xem `docs/runbook.md`):
- `kome_ingest` — vai trò của tiến trình nạp dữ liệu. SELECT/INSERT/UPDATE/
  **DELETE** trên `core`; SELECT/INSERT/UPDATE trên `meta` (không DELETE —
  `meta.ingest_batch` là bảng lịch sử, hoàn tác chỉ đặt `undone_at`). Đây là
  vai trò DUY NHẤT được ghi vào `core`. DELETE trên `core` là BẮT BUỘC: nút
  Hoàn tác chạy `DELETE FROM core.… WHERE batch_id = %s` (`010_*.sql`).
  **Web app của Giai đoạn 0 chạy bằng vai trò này** (`kome_ingest_user` trong
  `DATABASE_URL`) — nó vừa nạp dữ liệu vừa phục vụ trang `/kho-du-lieu` và
  `/undo/{batch_id}`.
- `kome_app` — **chưa ai dùng ở Giai đoạn 0**; dành cho ứng dụng CRM ở Giai
  đoạn 2. Chỉ SELECT trên `core`/`mart`; đọc-ghi trên `app`. **Không có quyền
  UPDATE/DELETE trên `core`** — kể cả nếu code lỡ viết nhầm câu lệnh, CSDL sẽ
  từ chối. Lưu ý nó KHÔNG có SELECT trên `meta.ingest_batch`, nên không chạy
  được trang `/kho-du-lieu` hiện tại.
- `kome_report` — chỉ SELECT, mọi schema (`core`, `mart`, `app`). Dùng cho
  công cụ báo cáo/BI ngoài ứng dụng chính.
- `postgres` (superuser hiện tại của Supabase) — chỉ dùng để chạy migration,
  không dùng cho vận hành thường ngày.

`ALTER DEFAULT PRIVILEGES` trong migration đảm bảo bảng tạo sau này cũng tự
nhận đúng quyền (TABLES *và* SEQUENCES), không cần GRANT tay mỗi lần thêm
bảng mới.

**Bất biến:** `ALTER DEFAULT PRIVILEGES` trong các migration KHÔNG có mệnh đề
`FOR ROLE`, nên nó chỉ áp cho đối tượng do chính vai trò chạy migration tạo
ra → **migration phải LUÔN chạy bằng vai trò `postgres`**. Đổi vai trò chạy
migration thì quyền mặc định cho bảng mới sẽ âm thầm không áp dụng, và lỗi
chỉ lộ ra nhiều tháng sau bằng một `permission denied` giữa lúc nạp dữ liệu.

## Các trang của web app
| Đường dẫn | Việc | Dữ liệu lấy từ |
|---|---|---|
| `/` | Tổng quan + ô "hôm nay đã có dữ liệu chưa" | `mart.tong_theo_ky`, `mart.khach_360`, `meta.ingest_batch` |
| `/khach-hang` | Danh sách + tìm kiếm + lọc theo trạng thái | `mart.khach_360` |
| `/khach-hang/{mã}` | **Hồ sơ 360°** | `mart.khach_360`, `khach_mat_hang`, `khach_theo_thang` |
| `/can-xu-ly` | Khách đang rời đi, xếp theo tiền | `mart.khach_360` |
| `/bao-cao` | Báo cáo bán hàng theo kỳ | `mart.ban_theo_*` |
| `/kho-du-lieu` | Nạp file OBC · sức khoẻ · độ phủ · hoàn tác lô | `meta.ingest_batch`, `core.*` |

Trang `/khach-hang` và `/can-xu-ly` mặc định chỉ hiện khách của người đang
đăng nhập; `?tat_ca=1` bỏ lọc. Người có `salesperson_code` NULL (chủ DN, kế
toán) thấy toàn bộ ngay từ đầu.

Ba trang cũ — nạp (`nap`), sức khoẻ (`health`), độ phủ dữ liệu (`phu-du-lieu`)
— nay chỉ còn 301 về `/kho-du-lieu`, không render nội dung gì nữa.

**Bất biến:** trạng thái quan hệ khách hàng so số ngày im lặng với **nhịp mua
riêng của từng khách** (trung vị khoảng cách giữa các lần mua), KHÔNG với một
ngưỡng chung. Đo thật: ngưỡng chung 90 ngày bỏ sót 49 khách đang rời đi và báo
động nhầm 34 khách vẫn mua bình thường.

**Bất biến:** mốc thời gian là **ngày bán mới nhất trong kho**
(`mart.moc_thoi_gian`), KHÔNG phải `current_date`. Dùng `current_date` thì một
ngày không ai nạp file sẽ làm cả 1.710 khách "im lặng thêm một ngày".

**Ngoại lệ DUY NHẤT của bất biến trên:** ô "hôm nay đã có dữ liệu chưa"
(`kome/tuoi_du_lieu.py`) cố ý dùng ĐỒNG HỒ THẬT, vì câu hỏi của nó đúng là
"đến giờ này đã ai nạp chưa" — không thể trả lời bằng chính dữ liệu đang
thiếu. Ba ràng buộc của ô đó:
- "Hôm nay" tính theo **Asia/Tokyo trong Python**, KHÔNG dùng `current_date`
  của Postgres: CSDL chạy UTC, nên `current_date` vẫn là hôm qua suốt
  00:00–09:00 giờ Nhật — tức suốt buổi sáng làm việc.
- Chỉ ĐỎ khi đã qua **13:30** và hôm nay là ngày làm việc
  (`core.dim_date.is_weekend`). Đỏ từ sáng nghĩa là sáng nào cũng đỏ, và một
  dải đỏ vĩnh viễn dạy người đọc bỏ qua dải đỏ.
- "Đã có dữ liệu hôm nay" đọc `meta.ingest_batch.data_date` (ngày trong TÊN
  FILE, migration `018_*.sql`), KHÔNG đọc `loaded_at` và KHÔNG đếm dòng trong
  bảng fact: `core.dim_customer` là SCD2 nên ngày khách không đổi gì thì nạp
  `得意先全情報` xong không sinh dòng nào mang ngày hôm nay.

**Bất biến:** khách OBC đã đánh dấu `※廃業※` / `※取引停止※` trong TÊN (281/2.077
khách) không bao giờ vào danh sách gọi lại. Doanh nghiệp đã phá sản thì im lặng
là đúng, không phải bất thường — xem `db/migrations/016_*.sql`.

## Hai bản chạy của web app
| | Máy trong công ty | Vercel (công khai) |
|---|---|---|
| Nạp / Hoàn tác | có | **không** |
| Đăng nhập | tài khoản riêng (bật khi có `KOME_SESSION_SECRET`) | **bắt buộc** (`KOME_SESSION_SECRET`) |
| Cổng CSDL | 5432 (session pooler) | **6543** (transaction pooler) |
| Gói cài | `pip install -e .` (có pandas) | `requirements.txt` (**không** pandas) |
| Điểm vào | `uvicorn kome.web.app:app` | `server.py` ở gốc (Vercel tự tìm) |

Chế độ chỉ-đọc do biến `VERCEL` quyết định (`kome/web/app.py::_chi_doc`), không
có công tắc tắt. Lý do là giới hạn nền tảng, không phải sở thích: mỗi yêu cầu
bị chặn ở **4,5 MB** trong khi `売上伝票データ` nặng ~100 MB; ổ đĩa là tạm nên lớp
`raw` không tồn tại được; nạp một quý mất ~88 giây, vượt giới hạn thời gian chạy.

**Bất biến:** `kome/web/app.py` KHÔNG được nhập `kome.pipeline` (hay pandas,
python-calamine) ở mức ngoài cùng — chỉ nhập bên trong thân route. `ingest`/
`undo_batch` kéo theo ~120 MB, mà `requirements.txt` của Vercel cố ý không có
chúng, nên nhập ở đầu file sẽ làm trang chết ngay khi khởi động. Có test canh:
`tests/test_bao_mat.py::test_trang_chi_doc_khong_phu_thuoc_pandas`.

**Bất biến:** qua cổng 6543 phải tắt câu lệnh chuẩn bị sẵn (`prepare_threshold
=None`, đã làm trong `kome/db.py`). Không tắt thì lỗi chỉ nổ sau vài chục lượt
xem — tức là lúc trang đã chạy được một thời gian và có người đang dùng.

Chi tiết triển khai: `docs/trien-khai-vercel.md`.

## Danh tính và quyền (Đợt 3, `db/migrations/019_danh_tinh.sql`)

Mỗi người một tài khoản (`app.nguoi_dung`), mật khẩu băm bằng `scrypt` với
salt riêng. Vé đăng nhập là cookie `<id>.<hạn>.<HMAC>` ký bằng
`KOME_SESSION_SECRET` — **khoá của hệ thống, không phải mật khẩu của ai**, nên
đổi mật khẩu một người không làm bốn người kia bị đăng xuất.

**Bất biến:** chữ ký của vé phải phủ **cả `id` lẫn `hạn`**. Ký riêng phần hạn
thì sửa một con số trong cookie là hoá thân thành người khác — kể cả thành
người có quyền bấm nút xoá dữ liệu. Có test canh: `tests/test_bao_mat.py::
test_doi_id_trong_ve_khong_hoa_than_duoc_thanh_nguoi_khac`.

**Bất biến:** cờ `duoc_vao_kho_du_lieu` **không nằm trong vé** — tra
`app.nguoi_dung` mỗi lượt gọi. Vé sống 12 giờ, mà thu hồi quyền trên màn có
nút xoá thì phải ăn ngay hôm nay.

**Bất biến:** lọc theo `salesperson_code` là **mặc định tiện dụng, KHÔNG phải
hàng rào bảo mật**. Công ty năm người, ai cũng biết khách của ai; đăng nhập
riêng là để cá nhân hoá, không phải để chặn. Không được thêm kiểm quyền vào
`/khach-hang` hay `/can-xu-ly`.

**CẠM BẪY — cổng chỉ tồn tại khi có khoá ký.** Để trống `KOME_SESSION_SECRET`
ở máy trong công ty là **không có đăng nhập và không có phân quyền**: ai mở
được trang cũng bấm được nút Hoàn tác — nút xoá được cả một tháng doanh thu.
Bản Vercel không dính (nó từ chối khởi động nếu thiếu khoá), nhưng bản Vercel
cũng không nạp/hoàn tác được gì. Nói cách khác: **cờ quyền chỉ bảo vệ được cái
nút nguy hiểm khi máy trong công ty CŨNG đặt `KOME_SESSION_SECRET`.**

Tạo và sửa tài khoản: `python scripts/tao_nguoi_dung.py` (xem `docs/runbook.md`).

### Hai kết nối CSDL
| Biến | Vai trò | Dùng cho |
|---|---|---|
| `DATABASE_URL` | `kome_ingest_user` | Màn Kho dữ liệu: nạp, hoàn tác |
| `DATABASE_URL_APP` | `kome_app_user` | Đăng nhập và mọi trang chỉ đọc |

Thiếu `DATABASE_URL_APP` thì app vẫn chạy (in cảnh báo) nhưng các trang đọc
chạy bằng vai trò có quyền ghi vào `core` — mất lớp phòng thủ, không mất trang.

## Không được tự ý sửa
- File trong `db/migrations/` đã chạy rồi — chỉ thêm file mới
- Luật bất biến trong kế hoạch/đặc tả
- Định nghĩa chỉ số ở chỗ khác ngoài `mart/`

## Chạy test
pytest -v
