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
6. Tên kho của OBC là **tên nghiệp vụ**, không phải địa điểm: `1002 新・賞味期限用`
   nghĩa là "ngăn dùng cho hạn sử dụng", không phải một địa chỉ kho. Gói thiết kế đợt
   4b có viết cứng ba tên `Osaka` / `Nagoya` / `Kho lạnh Osaka` — **không có thật**.
   Thực tế công ty chỉ có HAI kho: `0001 茨城第１倉庫（出荷専用）` và `1002 新・賞味期限用`.
   Đặt tên kho cứng ở đâu đó (thay vì đọc từ `core.dim_warehouse`) là thêm một kho ảo
   vào mọi bộ lọc.

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
- `kome_app` — từ Đợt 3 (`019_danh_tinh.sql`), đây là vai trò chạy đăng nhập
  và **mọi trang chỉ đọc** (`kome_app_user` trong `DATABASE_URL_APP`, xem mục
  "Danh tính và quyền" bên dưới). Chỉ SELECT trên `core`/`mart`; đọc-ghi trên
  `app`. **Không có quyền UPDATE/DELETE trên `core`** — kể cả nếu code lỡ
  viết nhầm câu lệnh, CSDL sẽ từ chối. Có SELECT trên `meta.ingest_batch`
  (cấp từ `019_danh_tinh.sql`, nhắc lại quyền đã cấp ở `009_roles.sql`) — cần
  cho ô "hôm nay đã có dữ liệu chưa" ở trang `/`. Vẫn KHÔNG chạy được trang
  `/kho-du-lieu` (nạp/hoàn tác), vì màn đó cần ghi/xoá `core` — trang đó luôn
  đi qua `kome_ingest` qua `DATABASE_URL`.
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
| `/khach-hang` | Danh sách + tìm kiếm + lọc (trạng thái/nhóm việc/hạng/tỉnh/sale) + 4 khối phân tích | `mart.khach_360`, `khach_nhom_viec`, `hang_doanh_thu`, `tai_nhan_vien` |
| `/khach-hang/{mã}` | **Hồ sơ 360°** | `mart.khach_360`, `khach_mat_hang`, `khach_theo_thang`, `ty_suat_mat_hang` |
| `/can-xu-ly` | Khách đang rời đi, xếp theo tiền | `mart.khach_360` |
| `/bao-cao` | Báo cáo bán hàng theo kỳ | `mart.ban_theo_*` |
| `/san-pham` | Danh mục mã hàng + tìm kiếm + lọc theo trạng thái tồn | `mart.san_pham_360` |
| `/san-pham/{mã}` | **Hồ sơ mã hàng** | `mart.san_pham_360`, `san_pham_theo_thang`, `ton_hien_tai`, `khach_mat_hang`, `khach_360`, `core.fact_price_list` |
| `/kho-hang` | Bốn ô tổng quan tồn kho · bảng tồn · cận hạn/quá hạn · giá trị theo kho | `mart.ton_hien_tai`, `san_pham_360`, `core.dim_warehouse`, `core.fact_inventory_daily` (chỉ để lấy ngày chụp) |
| `/kho-du-lieu` | Nạp file OBC · sức khoẻ · độ phủ · hoàn tác lô | `meta.ingest_batch`, `core.*` |

**Bất biến:** `mart.hang_doanh_thu` là hạng **do ta tự tính theo doanh thu 12
tháng**, KHÔNG phải `得意先ランク` của OBC. `core.dim_customer.rank_code` có tồn tại
(10 nhóm) nhưng không file xuất nào ta nạp có TÊN của các mã đó, nên nó không dùng
được để hiển thị. Nhãn trên trang phải luôn đọc là "hạng theo doanh thu 12 tháng" —
gọi tắt là "hạng" thì sẽ có người đối chiếu với OBC rồi thấy lệch và không biết tin
cái nào.

**Bất biến:** `kome/khach_hang.py::ho_so()` chạy **không quá 8 truy vấn** (nay là
7 — chỗ trống là cố ý, để khối tiếp theo thêm được mà không phải nới trần), và cả
trang `/khach-hang` chạy **3**: `tong_quan_danh_ba` 1 (bốn khối phân tích + bộ đếm
trạng thái + tổng toàn công ty) và `danh_sach` 2 (đếm + lấy dòng). Đo thật
2026-09-22: một round-trip tới pooler Tokyo mất 47 ms và một lượt hỏi thật ~260 ms.
Nút thắt là **số lượt hỏi**, không phải sức tính — nên tối ưu đúng là gộp truy vấn,
không phải materialized view. Có test đếm.

Con số "~10 ms cho một khối" từng ghi ở đây là phép đo của `mart.khach_mat_hang`
**lọc một khách** — ca có vị từ đẩy xuống được. Nó KHÔNG mô tả truy vấn của
`tong_quan_danh_ba`, thứ tham chiếu `mart.khach_360` chín lần mà không lần nào có
`customer_code` để đẩy xuống. Chi phí thật của khối đó **chưa đo trên CSDL đầy** —
có mục KIỂM TAY riêng ở đặc tả đợt 4a §9, ngưỡng 500 ms.

**Bất biến:** bộ đếm của dải chip trạng thái (`TongQuan.dem_trang_thai`) co theo
**đúng những bộ lọc mà liên kết của chính chip đó mang theo** — `nhom`/`hang`/
`tinh`/`sale` — và KHÔNG theo `loc`. Một bộ đếm lọc theo chính bộ lọc mà nó bật là
bấm vào một mục xong các số khác về 0 hết; một bộ đếm bỏ qua bốn bộ lọc kia là con
số nói dối về danh sách mà nó mở ra ("Tất cả (1.710)" bấm vào ra 216 khách).
`tong_tat_ca` thì ngược lại — không lọc gì hết, vì liên kết của nó (`?tat_ca=1`) bỏ
mọi bộ lọc.

**Bất biến:** "khách đang rời đi" có **ba** chỗ hiển thị và chỉ **một** định nghĩa,
`mart.khach_nhom_viec` nhóm `'im'`: nút "Im lặng ≥ 2× nhịp", cột "Cần gọi" của bảng
tải nhân viên (`mart.tai_nhan_vien.so_khach_canh_bao`, migration `022` cho nó ĐỌC
nhóm việc chứ không chép lại vị từ), và `can_xu_ly()` của `/can-xu-ly`. Có test canh
cả ba trả cùng một tập khách.

**Bất biến:** nhịp mua theo từng mã (`mart.nhip_mat_hang`) dùng **cùng công thức
trung vị** với nhịp mua của khách (`mart.nhip_mua`). Một khái niệm một công thức;
hai chỗ tính khác nhau là hai con số cùng tên nói hai điều.

**Bất biến:** tỷ suất lãi gộp — ở BẤT KỲ view nào trong `mart` (`ty_suat_mat_hang`,
`ban_theo_*`, `khach_360.ty_suat`) — luôn là **tỷ số của các TỔNG**
(`sum(lãi gộp) / sum(doanh thu thuần)`), KHÔNG BAO GIỜ là trung bình của các tỷ số
từng dòng. Bản đầu của khối "Gợi ý hàng chưa từng mua" (đợt 4a) tính
`avg(gross_profit / (amount - tax_amount))` và hậu quả có thật: một dòng doanh thu
thuần vài yên (mẫu số nhỏ do 赤伝 — phiếu đỏ, số ÂM, luật không được lọc bỏ) cho ra
tỷ số hàng chục lần, khối xếp giảm dần theo tỷ suất rồi lấy 8 mã đầu, nên **những mã
rác đó chiếm trọn tám dòng gợi ý của MỌI khách**. Sửa ở `mart.ty_suat_mat_hang`
(migration `021`). Có test canh:
`tests/test_khach_hang.py::test_ty_suat_goi_y_la_TY_SO_CUA_CAC_TONG`.

Trang `/khach-hang` và `/can-xu-ly` mặc định chỉ hiện khách của người đang
đăng nhập; `?tat_ca=1` bỏ lọc. Người có `salesperson_code` NULL (chủ DN, kế
toán) thấy toàn bộ ngay từ đầu. Riêng `/khach-hang` còn nhận `?nv=<mã sale>` để
chủ động xem danh bạ của MỘT người phụ trách khác — cùng nếp đợt 3: mặc định
tiện dụng, không phải hàng rào, không kiểm quyền, và luôn còn liên kết bỏ lọc.
`?nv=__moi_nguoi` (`KH.NV_MOI_NGUOI`) là mục "— mọi người phụ trách —" của ô lọc:
một GIÁ TRỊ QUY ƯỚC, không phải chuỗi rỗng, vì rỗng nghĩa là "không chọn gì" và
trang rơi về mặc định lọc theo người đăng nhập — tức ô chọn khoe "mọi người" trong
khi danh sách vẫn bị lọc. Cùng lý lẽ với `KH.TINH_TRONG` của ô Tỉnh.

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

**Bất biến:** `mart.toc_do_ban` dùng **trung bình 90 ngày**, còn `mart.nhip_mua` dùng
**trung vị** — KHÁC NHAU CÓ CHỦ Ý. `toc_do_ban` trả lời "bao nhiêu ngày nữa thì hết
hàng" (một phép chia trên tổng lượng, nên trung bình đúng); `nhip_mua` trả lời "khoảng
cách điển hình giữa hai lần mua" (nơi một kỳ nghỉ Tết làm trung bình lệch). Đừng "sửa
cho nhất quán".

**Bất biến:** `mart.toc_do_ban` có **HAI** cột tốc độ và chúng không thay nhau được.
`toc_do_ngay` chia cho HẰNG 90; `toc_do_ngay_theo_tuoi` chia cho `least(90, hom_nay -
lan_dau + 1)` — số ngày mã THỰC SỰ có mặt. Mọi con số dùng để RA QUYẾT ĐỊNH đều đi
theo cột thứ hai: `san_pham_360.du_ban_ngay` và `san_pham_360.trang_thai`. Với mã đã
bán quá 90 ngày hai cột BẰNG NHAU, nên lỗi không lộ ra ở phần lớn dữ liệu — nó chỉ
lộ ở mã mới. Một mã ra mắt 20 ngày bán 30 đơn vị mà chia cho 90 cho ra tốc độ thấp
hơn thật gần 4,5 lần, và "còn đủ bán bao nhiêu ngày" bị thổi phồng đúng bấy nhiêu
lần, đẩy một mã đang bán chạy vào nhãn tồn chết. Màn hình phải hiện **đúng cột đã
dùng để phân loại** — hiện `toc_do_ngay` bên cạnh một nhãn tính từ
`toc_do_ngay_theo_tuoi` thì người giữ kho đọc được "tốc độ 0,33/ngày · còn đủ 140
ngày" trên cùng một dòng và không có cách nào đối chiếu. Xem chú thích dài trong
`db/migrations/023_mart_san_pham.sql`.

**Bất biến:** `core.fact_inventory_daily.best_before` là **TEXT** và chứa cả giá trị chữ
`賞味期限なし` lẫn chuỗi rỗng. **Không bao giờ `to_date()` trần trên cột này** — một giá
trị chữ làm cả truy vấn nổ và trang trắng, mà nó chỉ nổ khi trong kho có đúng loại hàng
đó, tức sau khi đã triển khai. `mart.ton_hien_tai` kiểm dạng bằng regex trước và phân
**BỐN** loại: `ngay` / `khong_han` / `trong` / `khong_ro` (chuỗi không rỗng nhưng không
khớp regex ngày và không đúng y hệt `賞味期限なし` — "không đọc được", KHÁC "không có
hạn dùng").

**Bất biến:** `mart.san_pham_360.ton` là **NULL** khi mã không có dòng tồn nào, không
phải `0`. 90/232 mã chưa từng có dòng trong `在庫一覧`. "Không biết" khác "bằng không" —
hiện `0` là nói kho đã hết, và người đọc sẽ đi đặt hàng.

**Bất biến:** hai ô đếm trạng thái ở đầu `/kho-hang` KHÔNG co theo bộ lọc kho và
KHÔNG co theo bộ lọc trạng thái, còn ô "Giá trị tồn chết" thì co theo **cả hai**.
Khác nhau có chủ ý và trang phải nói ra: ô đếm là để so sánh giữa các kho nên phải
đứng yên, còn "giá trị tồn chết của kho này" là con số người ta dùng để quyết định
thanh lý — hiện tổng mọi kho bên cạnh một bảng đã lọc thì sai gần 2× ở công ty hai
kho.

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
