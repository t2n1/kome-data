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
4. File `元帳` có 5 dòng thông tin trước header — ĐÃ đo thật 2026-09-24 trên
   `請求先元帳` / `得意先元帳` (header ở dòng 6; sheet tên `得意先元帳` ở CẢ HAI loại sổ,
   phân biệt bằng dòng 集計軸項目 — `kome/so_cai.py`). `売上明細表`
   đã đo thật (2026-09-17): header ở dòng 1, KHÔNG có dòng rác — có thể do
   OBC đổi mẫu xuất, hoặc quan sát cũ chỉ đúng cho một cấu hình xuất khác.
   File master và `在庫一覧` thì header ở dòng 1.
5. `担当者` của OBC (5 người) KHÁC người nhập đơn trên web (7 tài khoản, gồm 2 arubaito).
6. Tên kho của OBC là **tên nghiệp vụ**, không phải địa điểm: `1002 新・賞味期限用`
   nghĩa là "ngăn dùng cho hạn sử dụng", không phải một địa chỉ kho. Gói thiết kế đợt
   4b có viết cứng ba tên `Osaka` / `Nagoya` / `Kho lạnh Osaka` — **không có thật**.
   Thực tế công ty có **MỘT kho vật lý** (Ibaraki); hai "kho" của OBC
   (`0001 茨城第１倉庫（出荷専用）`, `1002 新・賞味期限用`) là hai **LÔ theo hạn sử dụng**
   của cùng hàng trong kho đó (chủ DN xác nhận 2026-09-25): `0001` = lô ĐANG XUẤT,
   `1002` = lô hạn MỚI hơn đang chờ; `0001` của mã nào hết thì tồn `1002` của mã đó
   được chuyển lên `0001`. Đo trên ảnh chụp 2026-09-24: mọi `売上出荷数量` nằm ở `0001`
   (1002 = 0), 40 mã có ở cả hai, 0 mã chỉ có ở `1002`, không mã nào có hạn ở `1002`
   sớm hơn `0001`. Nên: "kho" trên màn là lô chứ không phải địa điểm; tồn / trạng thái
   của một mã là tổng HAI lô; so hai "kho" với nhau như hai chi nhánh là vô nghĩa.
   Đặt tên kho cứng ở đâu đó (thay vì đọc từ `core.dim_warehouse`) là thêm một kho ảo
   vào mọi bộ lọc.
7. `prefecture` của OBC là tên tỉnh chuẩn có hậu tố 都/道/府/県, đủ cả 47 tỉnh, và chỉ
   **1 trên 1.710 khách** bỏ trống — cột sạch nhất đã gặp, nên khoá nối
   (`core.dim_prefecture.ten` ↔ `core.dim_customer.prefecture`) là chính chuỗi tên,
   không cần lớp chuẩn hoá. Đổi một ký tự trong `core.dim_prefecture.ten` là tỉnh đó
   rỗng vĩnh viễn trên bản đồ khách hàng (`/ban-do`) mà không lỗi nào nổ ra — phép nối
   chỉ lặng lẽ không khớp dòng nào. Có test canh:
   `tests/test_ban_do.py::test_ten_tinh_khop_chuoi_OBC_that`,
   `::test_hau_to_dung_voi_tung_ma_jis_ca_47_dong` (khẳng định hậu tố theo ĐÚNG
   `ma_jis` — `01`→道, `13`→都, `26`/`27`→府, 43 mã còn lại→県; một điều kiện
   "hậu tố nằm trong 都/道/府/県" cho `大阪県` lọt qua).

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
| `/` | **Giao diện React** (2026-09-23, bám Dashboard.dc.html): 21 khối kéo thả / đổi cỡ / ẩn hiện, xem theo vai trò, chuông, ⌘K. Mỗi khối gọi `/api/tong-quan/<khối>` riêng (`kome/khoi_tong_quan.py`), qua ảnh chụp theo phiên bản dữ liệu; khối không có nguồn hiện khung "chưa có dữ liệu". Từ 2026-09-24 khối số bán hàng theo **khoảng xem** (`?thang=`/`?ky=`/`?tu=&den=`, mặc định tháng hiện tại) — xem bất biến "Khoảng xem" | như trên + `mart.ban_theo_thang_so_sanh`, `mart.ban_theo_nganh_thang_so_sanh`, `mart.tong_theo_ky`, `mart.uu_tien_lien_he`, `app.anh_chup_api` |
| `/khach-hang` | **React** (giai đoạn 2, bám Customer 360.dc.html) tab **Danh sách**: KPI · 8 phân khúc (gồm "mua đều, tháng này chưa", "có mua trong khoảng") · doanh thu + so sánh theo **khoảng xem** (`?thang=`…, sắp mặc định `dt_khoang`; nhãn tháng lọc bằng `?nhan_thang=`) · lọc tìm/hạng (nhiều)/phụ trách/tỉnh/trạng thái/nhãn tháng · bảng sắp xếp máy chủ 50/100/200 dòng · xuất CSV dòng đã chọn · 3 khối phân tích. `/api/khach-hang/ds` — một ảnh chụp danh bạ (`KH.danh_ba`) lọc bằng Python | `mart.khach_360`, `khach_nhom_viec`, `hang_doanh_thu`, `khach_thang_nay`, `tai_nhan_vien` |
| `/khach-hang/{mã}` | **Hồ sơ 360° React**: 5 tab (Tổng quan · Sản phẩm · Đơn hàng · Công nợ · Hồ sơ & liên hệ); ô tổng, mặt hàng và đơn hàng theo khoảng xem qua `/api/khach-hang/{mã}/khoang` (2 lượt, ngoài trần 8 của hồ sơ), biểu đồ 12 tháng bấm tháng xem mặt hàng, lưới 26 tuần, giỏ theo ngành, lịch mua dự kiến, ghi tiếp xúc (`POST /api/khach-hang/{mã}/tiep-xuc`, chỉ JSON). `/api/khach-hang/{mã}` (+ `/dong?tu=&den=`) | `mart.khach_360`, `khach_mat_hang`, `khach_theo_thang`, `khach_thang_nay`, `lan_mua`, `dong_ban`, `ty_suat_mat_hang` |
| `/lien-he` | **Cần liên hệ — React** (giai đoạn 3, bố cục CRM.dc.html; `/api/lien-he`) (đợt 7, thay `/can-xu-ly` — nay chỉ còn 301 về đây): cột theo lý do (lâu không mua · quá hạn · sắp đến hạn · mua đều tháng này chưa — 036) · hoạt động gần đây · hẹn gọi lại hôm nay · khách đang tạm ẩn. Ghi tiếp xúc ngay trên thẻ qua `POST /api/khach-hang/{mã}/tiep-xuc` (form cũ `POST /khach-hang/{mã}/tiep-xuc` vẫn còn). **3 truy vấn** | `mart.uu_tien_lien_he`, `mart.khach_thang_nay`, `app.nhat_ky_tiep_xuc` |
| `/ban-do` | Tab **Bản đồ** của màn Khách hàng (React) — lưới 47 tỉnh tô theo chỉ số (số khách/doanh thu 12 tháng/cần gọi lại + doanh thu / khách có mua trong khoảng xem — `mart.tinh_khoang`), lọc theo người phụ trách; bấm ô → tab Danh sách lọc tỉnh đó. `/api/ban-do` | `core.dim_prefecture`, `mart.khach_theo_tinh` |
| `/bao-cao` | **React** (giai đoạn 3, `/api/bao-cao?thang=` · `?ky=` · `?tu=&den=` — mặc định tháng hiện tại; dạng Kỳ = báo cáo theo kỳ cũ, không đổi số; hình học biểu đồ vẫn tính ở Python) Báo cáo bán hàng + (đợt 5b) ngành hàng lên/xuống · cây ô ngành → mã · bản đồ nhiệt ngành × tháng · Pareto tập trung khách | `mart.ban_theo_*`, `mart.ky_cung_ky`, `mart.ban_theo_nganh_thang_so_sanh`, `mart.nganh_ky_cung_ky`, `mart.tap_trung_khach` |
| `/du-bao` | **Dự báo doanh thu — React** (giai đoạn 3, `/api/du-bao`, đổi kịch bản ở trình duyệt) (đợt 8): chốt tháng (đường luỹ kế + khoảng sai số thật + theo người phụ trách) · 12 tháng tới (3 kịch bản) · đơn kỳ vọng 14 ngày · nguy cơ ngừng mua · dự báo đã chuẩn tới đâu. Toàn công ty, **3 truy vấn** | `mart.lich_kinh_doanh`, `mart.ban_theo_ngay`, `mart.tien_do_ngan_sach`, `mart.khach_360`, `mart.khoang_cach_mua` |
| `/ngan-sach` | Ngân sách theo tháng (041): khối **công ty** (12 tháng × doanh thu + lãi gộp, nhập thẳng) rồi khối **từng người phụ trách** (doanh thu + lãi gộp, không bắt buộc) + tổng từng người + phần lệch so với công ty. **Cần cờ `duoc_sua_ngan_sach`** | `app.ngan_sach_cong_ty`, `app.ngan_sach`, `core.dim_salesperson`, `core.dim_date` |
| `/san-pham` | **React** (giai đoạn 4, bám Sản phẩm.dc.html; khoảng xem: cột doanh thu / SL / khách trong khoảng từ `/api/san-pham/khoang`, ghép ở trình duyệt): MỘT trang — ô tổng quan · danh mục cả 232 mã (chip ngành / trạng thái, tìm, sắp — lọc ở trình duyệt trên MỘT ảnh chụp `/api/san-pham`, 1 lượt hỏi) · hồ sơ mã đang chọn ngay bên dưới | `mart.san_pham_360`, `mart.dong_ban`, `mart.moc_thoi_gian`, `core.dim_product` |
| `/san-pham/{mã}` | Cùng màn Sản phẩm với một mã được chọn (`pushState`): khách mua trong khoảng xem (`/api/san-pham/{mã}/khoang`, 2 lượt), biểu đồ theo ngày mở đúng tháng đang xem · hồ sơ (`/api/san-pham/{mã}`, ≤ 5 lượt) · bán theo ngày + cùng ngày tháng trước (`/ngay?thang=`, 1 lượt) · khách đang mua / đã bỏ · tồn theo kho · giá theo bậc · xu hướng theo tháng | `mart.san_pham_360`, `san_pham_theo_thang`, `ton_hien_tai`, `khach_mat_hang`, `khach_360`, `core.fact_price_list`, `mart.dong_ban`, `mart.lich_kinh_doanh` |
| `/kho-hang` | **React** (giai đoạn 4, bám Kho hàng.dc.html; `/api/kho-hang?kho=&loc=`, 2 lượt): tab Tồn hiện tại (5 ô · bảng tồn theo dòng + tìm + chip ngành (`?nganh=`, lọc ở trình duyệt) + CSV · quá hạn / sắp chuyển lô / không kịp bán trước hạn / cận hạn / giá trị theo ngành / theo lô) · Hàng đang về (chưa có dữ liệu) · Cần đặt (hết + sắp thiếu, KHÔNG đề xuất số lượng). "Kho" hiện là LÔ (bẫy #6, 042) | `mart.ton_hien_tai`, `mart.ton_theo_lo`, `san_pham_360`, `core.dim_warehouse`, `core.dim_product` (ngành), `core.fact_inventory_daily` (chỉ để lấy ngày chụp) |
| `/cong-no` | **Công nợ & thu tiền — React** (đợt 6, bám Công nợ.dc.html; `/api/cong-no`, MỘT ảnh chụp 2 lượt hỏi, lọc ở trình duyệt): 6 ô tổng · tuổi nợ (bấm để lọc) · phiếu còn nợ (tab quá hạn / sắp đến hạn / không suy được hạn / theo bên nhận hoá đơn) · lịch thu 7 ngày sau mốc · việc nên làm. Mốc = cuối kỳ sổ mới nhất. Tab Công nợ của hồ sơ khách: `/api/cong-no/khach/{mã}` | `mart.cong_no_ben_tra`, `mart.cong_no_phieu` (← `core.fact_ar_ledger`, sổ `請求先元帳`) |
| `/kho-du-lieu` | **Tổng quan độ phủ — React** (đợt B 2026-09-24, bám Kho dữ liệu.dc.html; thanh trái chung `TabKho.tsx::KhungKho`; máy chủ tính sẵn vào `window.__KOME__.man`, vai trò NẠP): sơ đồ 8 nguồn (màu theo nhịp — `kome/kho_du_lieu.py`) · 4 ô số (danh mục `pg_class`) · lưới theo ngày của MỘT tháng (`?ngay_thang=YYYY-MM`, KHÔNG `?thang=` — đó là khoảng xem chung) · sức khoẻ · bảng tháng | `meta.ingest_batch`, `core.*` |
| `/kho-du-lieu/nap` | **Nạp hai bước — React** (đợt B): mỗi loại file một ô (`kho_du_lieu.O_NAP`, cùng danh sách với sơ đồ nguồn; thả nhầm ô → chặn) · `POST /upload/kiem` (5 cổng qua `pipeline.kiem`, **không ghi gì**, file vào `<ARCHIVE_DIR>/_cho_xac_nhan/` — trên Vercel vào `meta.nap_cho`, 045) → `POST /upload/xac-nhan` (`ingest` đầy đủ, 5 cổng chạy lại) / `POST /upload/huy` · file chờ quá 24 giờ bị dọn · lô gần nhất + hoàn tác (`POST /undo/{lô}` → về `#lo-nap`). `POST /upload` một bước vẫn còn | `meta.ingest_batch`, `meta.nap_cho`, `core.*` |
| `/kho-du-lieu/luong` | Tài liệu sống (đợt 2b): bốn tầng · các nguồn OBC · 5 cổng + ngưỡng từng file · cạm bẫy OBC · lộ trình. **0 truy vấn** | `config/files.yml`, `kome/web/tai_lieu_sinh.json` |
| `/kho-du-lieu/cot-noi` | Tài liệu sống: ma trận khoá · file nối đi đâu · cột trong từng file (`?file=<spec>`). **0 truy vấn** | `config/files.yml` |
| `/kho-du-lieu/bang/{schema.bảng}` | **Xem một bảng — React** (đợt C 2026-09-24): Dữ liệu (tìm trên cả dòng, 50 dòng/trang, "Tháng gần nhất" / "Lô mới nhất", CSV ≤ 50.000 dòng) · Cột & khoá · Lần nạp. Thanh trái "Duyệt bảng" (`/api/kho-du-lieu/bang`). CHỈ ĐỌC bằng `kome_app` trong giao dịch `READ ONLY` (+ `statement_timeout` 20 s); tên bảng phải là quan hệ có thật của `core`/`mart`/`meta` mà vai trò đó SELECT được (`has_table_privilege`) rồi mới vào SQL qua `sql.Identifier` — schema `app` KHÔNG BAO GIỜ (băm mật khẩu). `/api/kho-du-lieu/*` nằm trong `DUONG_KHO_DU_LIEU` (cùng cổng quyền màn có nút xoá). Bảng: trang theo khoá chính + `count(*)` riêng (2 lượt); view: MỘT câu `count(*) OVER ()` (bất biến CTE-trùng) | danh mục `pg_class` + chính bảng đó (`kome/bang_kho.py`) |
| `/kho-du-lieu/duong-di` | **Dữ liệu đi đâu** (2026-09-24): mỗi cột OBC một phán quyết "bỏ khỏi bản xuất lần sau có sao không" — bộ nạp cần · màn hình đang dùng · nạp vào kho chưa ai dùng · có trong file kho không nạp; hình đường đi OBC → core → mart → màn; sơ đồ nối khoá; tải CSV cột bỏ được. **0 truy vấn** | `kome/web/cot_dung_sinh.json` (← `scripts/sinh_cot_dung.py`) |
| `/nhat-ky` | **Nhật ký thao tác** (màn 20): ĐỌC GỘP năm sổ đã có — nạp + hoàn tác (`meta.ingest_batch`, `nap_boi`/`huy_boi` từ 033), sửa ngân sách (`app.ngan_sach_nhat_ky`), đổi quyền (`app.nhat_ky_quyen`), ghi tiếp xúc (`app.nhat_ky_tiep_xuc`). Lọc `?loai=`/`?tim=`, `/nhat-ky.csv`. **2 truy vấn** | năm sổ trên |
| `/cai-dat` | **Cài đặt** (màn 21): người dùng & ba cờ quyền (đổi được CHỈ khi có `duoc_quan_tri` VÀ máy có cổng đăng nhập) · ngày lễ sắp tới · quy tắc khách · nguồn · hiển thị. Không bao giờ nhận mật khẩu | `app.nguoi_dung`, `mart.lich_kinh_doanh` |
| `/giao-dien` | Đổi chế độ sáng/tối/theo hệ thống/theo giờ, ghi cookie, chuyển hướng về trang đã gọi | không đọc CSDL — chỉ đọc/ghi cookie |

**Bất biến:** `mart.hang_doanh_thu` là hạng **do ta tự tính theo doanh thu 12
tháng**, KHÔNG phải `得意先ランク` của OBC. Từ 043 `得意先全情報` mang cả TÊN hạng OBC
(`core.dim_customer.rank_name`, vd. `Cランク／年間粗利額 200,000以上`,
`ZZZランク/電話禁止又は不要`) — nó CHỈ hiện ở tab Hồ sơ & liên hệ dưới nhãn
"Hạng OBC (得意先ランク)", không bao giờ thay hạng theo doanh thu. Nhãn trên trang phải
luôn đọc là "hạng theo doanh thu 12 tháng" — gọi tắt là "hạng" thì sẽ có người đối
chiếu với OBC rồi thấy lệch và không biết tin cái nào.

**Bất biến (043, 得意先全情報 mẫu 16 cột — chủ DN chốt 2026-09-25):** bản xuất BỎ
`業種・カテゴリーコード`, `注文アプリコード`, `売価No.コード`, `請求先コード`,
`インボイス登録番号`, `スポット区分コード`; THÊM `ビル等` (`building`), `ランク名`,
`売上主担当者名`, `請求締日名`, `振込専用口座番号１` (`transfer_account` — tài khoản chuyển
khoản riêng, TEXT; sale gõ số đó vào ô tìm của danh sách khách để ra khách). Sáu cột
cũ còn trong `core.dim_customer` (SCD2 = lịch sử) nhưng bộ nạp không ghi nữa — phiên
bản mới mang NULL, và **không chỗ nào được đọc chúng**. Hoàn tác SCD2 gán lại ĐÚNG
những cột mà ảnh trước của lô đó đã chụp (`customer.TRACKED + TRACKED_CU`), nên lô
nạp theo mẫu cũ vẫn hoàn tác được. Bên nhận hoá đơn (請求先) của một khách = 請求先コード
trên PHIẾU BÁN gần nhất ≤ mốc (`mart.ben_tra_cua_khach`, đo thật: khớp master cũ
1.704/1.710; chưa có phiếu = chính khách) — tab Công nợ của hồ sơ khách và
`mart.cong_no_ben_tra.so_khach` đọc CÙNG view đó. Khối "Bảng giá của bậc" ở hồ sơ
khách đã bỏ (không còn biết bậc giá của khách); giá theo bậc của từng MÃ vẫn ở
`/san-pham/{mã}`. Có test canh: `tests/test_load_customer.py`,
`tests/test_cong_no.py::test_ben_tra_cua_khach_doc_tu_PHIEU_BAN_GAN_NHAT`,
`tests/test_khach_hang.py::test_ho_so_mang_cot_mau_16_cot_va_tim_duoc_theo_so_tai_khoan`.
**Migration 043 phải chạy TRƯỚC khi nạp file mẫu mới / triển khai.**

**Bất biến (044, mã nội bộ — chủ DN chốt 2026-09-25):** `0090…`/`0099…` là NHÂN VIÊN mua
hàng; `999999999999` ("代引き登録用データ") và `202411000000` là mã giữ chỗ OBC. Định nghĩa
ĐÚNG MỘT LẦN: `mart.la_ma_noi_bo()`. Lọc ở `mart.ban_den_moc` (+ `mart.khach_chua_mua`) nên
bỏ khỏi MỌI số liệu bán hàng — **kể cả TỔNG doanh thu** (chủ DN chọn: nhân viên mua không
phải doanh thu bán hàng). Hệ quả có chủ ý: tổng doanh thu trên web THẤP hơn sổ OBC đúng phần
nhân viên mua (đo thật: 15 mã, ¥388.667 ≈ 0,02%) — đối soát tháng phải trừ ra. Không lọc:
`core` (OBC chỉ đọc), trang Kho dữ liệu (đối chiếu với FILE nên phải đủ dòng), sổ công nợ
(nợ thật). View mới đọc bảng bán phải đọc `mart.ban_den_moc` — đọc thẳng
`core.fact_sales_line` là vừa không quay về theo mốc vừa lọt nhân viên. Có test canh:
`tests/test_ma_noi_bo.py`.

**Bất biến (044, hạn trả):** `その都度請求` = trả trong **5 ngày làm việc sau ngày xuất
hàng** (ngày phiếu), ngày làm việc = `mart.lich_kinh_doanh.la_ngay_kd` (chưa trừ ngày nghỉ
riêng của công ty — cùng hạn chế đã ghi). Ba mẫu suy được hạn: `末締/翌月末日`,
`末締/翌月N日`, `その都度請求`; `代引請求` (thu hộ khi giao) / `前払い` vẫn "không suy được
hạn". Có test canh: `tests/test_cong_no.py::test_han_tra_TUNG_LAN_la_5_ngay_lam_viec_sau_ngay_xuat`.

**Mã khách = ngày đăng ký** (chủ DN xác nhận 2026-09-25): từ 2023-08 mã là `YYYYMMDD` + số
thứ tự 4 chữ số trong ngày (`202609240002` = khách mới thứ 2 ngày 24/9/2026); mã cũ
`000000xxxxxx` không mang ngày ("trước 8/2023"). Đọc ở `kome.khach_hang.ngay_dang_ky`, hiện ở
tab Hồ sơ. "Khách mới" của các màn vẫn theo LẦN MUA ĐẦU, không theo ngày đăng ký.
**Migration 044 phải chạy TRƯỚC khi triển khai.**

**Bất biến (045, nạp trên Vercel — chủ DN chốt 2026-09-25):** bản Vercel nạp / kiểm /
xác nhận / huỷ / hoàn tác được file HẰNG NGÀY; đối soát tháng / nạp lại cả quý (30–106
MB) vẫn ở máy công ty. File CHỜ xác nhận đi qua MỘT lớp kho (mô-đun `kome.nap_cho`):
`KhoDia` (thư mục `_cho_xac_nhan/`, máy công ty) hay `KhoCsdl` (bảng `meta.nap_cho`,
Vercel — bước Xác nhận có thể chạy ở phiên bản hàm khác bước Kiểm), chọn bằng
`KOME_KHO_NAP` (mặc định `csdl` khi `VERCEL`). Kho CSDL KHÔNG lưu file gốc:
`meta.ingest_batch.archived_to` NULL = "nạp ở nơi không lưu file gốc" — mã băm vẫn ghi
nên chặn nạp trùng không đổi. `kome_ingest` có DELETE trên ĐÚNG `meta.nap_cho` (sổ
`meta.ingest_batch` vẫn không xoá được); `kome_app` / `kome_report` không có quyền gì trên
bảng đó (dữ liệu thô chưa qua cổng). Trình duyệt chặn file / tổng file >
`app.GIOI_HAN_WEB` (4 MB, trần Vercel 4,5 MB) khi `window.__KOME__.gioi_han_tai_len` có
giá trị (chỉ Vercel). Làm nóng ảnh chụp bỏ qua trên Vercel (luồng nền bị đóng băng sau
khi trả lời). Có test canh: `tests/test_nap_vercel.py`,
`tests/test_bao_mat.py::test_tren_vercel_nap_duoc_nhung_van_sau_co_kho_du_lieu`. Đặc tả:
`docs/superpowers/specs/2026-09-25-nap-tren-vercel-design.md`.
**Migration 045 phải chạy TRƯỚC khi triển khai.**

**Bất biến:** `kome/khach_hang.py::ho_so()` chạy **không quá 8 truy vấn** (giai
đoạn 2 gộp "đã ngừng mua" vào câu mặt hàng nên nay là 7 — chỗ trống là cố ý), và
màn danh sách chạy **≤ 3**: từ giai đoạn 2 cả bảng lẫn khối tổng quan tính trên MỘT
ảnh chụp danh bạ (`KH.danh_ba`, 1 lượt hỏi, phiên bản CHỈ theo dữ liệu nạp —
`anh_chup.lay(..., chi_nap=True)`), lọc / sắp / đếm bằng MỘT bộ lọc Python
(`KH._khop`) — đo thật: lọc bằng SQL thì mỗi tổ hợp bộ lọc dựng lại `khach_360`,
3–10 s mỗi cú bấm. `danh_ba` đọc nhánh `'im'` từ `trang_thai IN
TRANG_THAI_CAN_XU_LY` (đúng định nghĩa nhánh đó của `mart.khach_nhom_viec`, có test
canh `tests/test_khach_hang_api.py::test_nhom_im_cua_danh_ba_DUNG_BANG_view_nhom_viec`). Đo thật
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
nhóm việc chứ không chép lại vị từ), và `can_xu_ly()` (khối "Cần gọi hôm nay" của `/`
qua `dem_va_can_xu_ly`). Từ đợt 7, hai cột "Lâu không mua" + "Quá hạn mua lại" của
`/lien-he` (`mart.uu_tien_lien_he`, `lau_khong_mua`/`qua_han`) cũng phải là ĐÚNG tập
đó. Có test canh cả bốn trả cùng một tập khách
(`tests/test_lien_he.py::test_hai_cot_dau_DUNG_BANG_nhom_viec_im`).

**Bất biến:** nhịp mua theo từng mã (`mart.nhip_mat_hang`) dùng **cùng công thức
trung vị** với nhịp mua của khách (`mart.nhip_mua`). Một khái niệm một công thức;
hai chỗ tính khác nhau là hai con số cùng tên nói hai điều.

**Bất biến:** trạng thái của một **cặp (khách, mã)** có **bốn** khối hiển thị và
chỉ **một** định nghĩa: cột `mart.khach_mat_hang.trang_thai_cap` (migration `024`)
— một **NHÃN ba giá trị**, xét theo đúng thứ tự này:
`'khong_goi'` (khách bị OBC đánh dấu ※廃業※/※取引停止※ — xét **TRƯỚC**, cùng nếp
`'ngung_giao_dich'` của `016`) · `'ngung'` (im lặng **≥ 2× nhịp mua riêng của
chính cặp đó**, `tre_ngay >= nhip_ngay`) · `'mua'` (còn lại, gồm cả cặp chưa đủ 3
lần mua nên `nhip_ngay` NULL — đó là "chưa đủ dữ liệu", KHÔNG phải "đã ngừng").
Bốn khối — "Mặt hàng đã ngừng mua" và "Tháng này chưa mua" của `/khach-hang/{mã}`,
"Khách đang mua mã này" và "Khách đã ngừng mua mã này" của `/san-pham/{mã}` —
**ĐỌC** cột này và **so bằng** (`= 'ngung'`, `= 'mua'`), không chỗ nào viết lại vị
từ (cùng nếp `022`) và không chỗ nào tự JOIN lấy `da_ngung` nữa: cờ ※廃業※ được
đọc **đúng một lần**, trong view, từ `mart.dau_hieu_khach` (nhà của nó theo `016`,
và rẻ hơn `khach_360`).

**NHÃN chứ không phải boolean, và KHÔNG ĐƯỢC dùng `NOT` trên nó.** Bản đầu của
`024` là boolean `ngung_mua` gói cổng ※廃業※ vào bên trong; phủ định một boolean
như thế **luôn đúng** với khách đã phá sản, nên mọi khối viết "phần còn lại" bằng
`NOT ngung_mua` lặng lẽ mở cửa lại cho trọn 281 khách đó — và ba chỗ Python phải
tự JOIN `da_ngung` để đắp tay, tức một cờ hai nguồn ba chỗ chép, đúng cái bệnh mà
`021`/`022` tồn tại để dẹp. So bằng với một nhãn không có lỗ đó, và thêm trạng
thái thứ tư sau này cũng không âm thầm dồn dòng vào khối nào.

Trước `024`, "đã ngừng" ở `/khach-hang/{mã}` dùng ngưỡng chung 90 ngày còn
`/san-pham/{mã}` dùng nhịp riêng, nên cùng một cặp cho hai câu trả lời ngược nhau
ở **cả hai chiều**, và cả hai đều thiếu cổng ※廃業※. `trang_thai_cap` là một
**CỘT, không phải bộ lọc dòng**: view vẫn giữ đủ mọi cặp, vì nó còn phục vụ khối
"khách đang mua mã này" và bảng top-15 mặt hàng — sự thật lịch sử, không phải danh
sách gọi lại. Khối "Tháng này chưa mua" là dải giữa: đã quá ngày dự kiến mua lại
(`tre_ngay IS NOT NULL`) nhưng nhãn vẫn là `'mua'`. Có test canh:
`tests/test_san_pham.py::test_hai_man_tra_loi_GIONG_NHAU_ve_mot_cap_khach_ma`,
`::test_khach_da_dong_cua_khong_lot_vao_khoi_goi_lai_nao` và
`::test_cap_cua_khach_da_dong_cua_mang_NHAN_RIENG_khong_phai_phu_dinh`.

**Bất biến:** khi một câu lệnh tham chiếu **cùng một view của `mart` nhiều hơn một
lần**, view đó phải vào CTE `AS MATERIALIZED` (ghi **tường minh**, đừng dựa vào mặc
định của Postgres 12+) và mọi nhánh đọc từ CTE. Postgres KHÔNG gộp các truy vấn con
trùng nhau: mỗi lần tham chiếu là một lần **đánh giá lại** cả view. `kho_hang()`
từng tham chiếu `mart.san_pham_360` 5 lần ở câu 1 và 3 lần ở câu 2 — mỗi lần kéo
theo `ty_suat_mat_hang`, `toc_do_ban` (2 lượt quét `fact_sales_line`) và CTE `sl`,
tức ~32 lượt quét bảng bán hàng cho MỘT lần mở trang. Ngân sách "≤ 2 truy vấn" đo
**số lượt hỏi**, không đo sức tính, nên nó không bắt được lớp lỗi này và màn hình
vẫn xanh trên CSDL test vài chục dòng.

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

Trang `/khach-hang` và `/lien-he` mặc định chỉ hiện khách của người đang
đăng nhập; `?tat_ca=1` bỏ lọc. Người có `salesperson_code` NULL (chủ DN, kế
toán) thấy toàn bộ ngay từ đầu. Riêng `/khach-hang` còn nhận `?nv=<mã sale>` để
chủ động xem danh bạ của MỘT người phụ trách khác — cùng nếp đợt 3: mặc định
tiện dụng, không phải hàng rào, không kiểm quyền, và luôn còn liên kết bỏ lọc.
`?nv=__moi_nguoi` (`KH.NV_MOI_NGUOI`) là mục "— mọi người phụ trách —" của ô lọc:
một GIÁ TRỊ QUY ƯỚC, không phải chuỗi rỗng, vì rỗng nghĩa là "không chọn gì" và
trang rơi về mặc định lọc theo người đăng nhập — tức ô chọn khoe "mọi người" trong
khi danh sách vẫn bị lọc. Cùng lý lẽ với `KH.TINH_TRONG` của ô Tỉnh.

**Bất biến (Đợt 2b):** tài liệu sống ở `/kho-du-lieu/luong` và `/cot-noi` được
**SINH RA, không chép tay** (lộ trình §7). Nguồn lúc chạy là `config/files.yml`
(kể cả hai trường `core_table` và `references` thêm ở đợt này) và
`kome.coverage`; bốn nguồn còn lại — `db/migrations/*.sql`, mục "Bẫy đã biết"
của file NÀY, `kome.gates.TEN_CONG`, bảng §7 của đặc tả lộ trình — KHÔNG có trên
Vercel (`.vercelignore` loại `docs/`/`db/`; `gates.py` nhập pandas), nên
`scripts/sinh_tai_lieu.py` chụp chúng vào `kome/web/tai_lieu_sinh.json` (commit
vào git). **Sửa một migration, mục "Bẫy đã biết", `TEN_CONG` hay bảng lộ trình
thì chạy lại `python scripts/sinh_tai_lieu.py`** — không chạy là
`tests/test_tai_lieu.py::test_anh_chup_tai_lieu_khong_cu` đỏ. `files.yml.core_table`
khai lại bảng đích của `pipeline.UNDO_TABLES` vì web không được nhập pipeline —
có test canh hai bản khớp (`::test_core_table_khop_undo_tables`).

**Bất biến ("Dữ liệu đi đâu", 2026-09-24):** phân loại "cột OBC nào bỏ được" SINH bởi
`scripts/sinh_cot_dung.py` (danh mục Postgres của CSDL test + `files.yml` + quét mã `kome/`) vào
`kome/web/cot_dung_sinh.json`; tiêu đề file thật chụp riêng ở `config/obc_tieu_de.json`
(`--doc-tieu-de`, chỉ dòng tiêu đề của file mới nhất trong `raw_archive*/`). **Sai nguy hiểm duy
nhất là báo "bỏ được" cho cột đang dùng**, nên mọi phép dò nghiêng về "đang dùng" (trùng tên là
dùng, `SELECT *` là dùng mọi cột, view không tách được là dùng cả view). Thêm một mô-đun đọc
`mart`/`core` = PHẢI khai vào `MAN` của script; loader ghi cột sang chỗ khác tên = khai
`LUU_RIENG`; sửa migration / files.yml / mã đọc cột = chạy lại script — ba điều đều có test canh
(`tests/test_cot_dung.py`). Bỏ một cột ĐANG khai nạp khỏi bản xuất mà chưa sửa `files.yml` là
cổng 2 chặn cả file. Đặc tả: `docs/superpowers/specs/2026-09-24-kho-du-lieu-theo-thiet-ke-design.md`.

Ba trang cũ — nạp (`nap`), sức khoẻ (`health`), độ phủ dữ liệu (`phu-du-lieu`)
— nay chỉ còn 301 về `/kho-du-lieu`, không render nội dung gì nữa.

**Bất biến (Đợt 4d; từ giai đoạn 5 là `giao_dien/src/khung/icon.tsx` + `muc.ts`):** icon thanh bên là TRANG TRÍ, chữ nhãn mới là
thứ đọc được (`aria-hidden="true" focusable="false"` trên mỗi `<svg>`) — bỏ
hai thuộc tính đó là trình đọc màn hình đọc icon rồi đọc lại nhãn, và Tab
dừng ở một phần tử không có gì để bấm. Sáu icon (Tổng quan/Báo cáo/Khách
hàng/Sản phẩm/Kho hàng/Kho dữ liệu) chép NGUYÊN VĂN từ object `I` trong
`kome-nav.js` của gói thiết kế, đúng ánh xạ NHÓM của chính gói đó. Hai icon
còn lại — `bell` cho "Cần liên hệ" (trước đợt 7: "Cần xử lý") và `pin` cho "Bản đồ" — là **TA CHỌN**
trong bộ 24 icon của gói thiết kế, vì gói đó không có mục "Cần xử lý" và gộp
bản đồ chung vào "Khách hàng & bản đồ" thay vì tách trang riêng như app này.
Ai chọn cái gì phải ghi rõ ra (xem chú thích đầu `icon.tsx` / `muc.ts`) — không ghi thì
người sau tưởng cả tám icon đều theo một ánh xạ có sẵn của gói thiết kế, rồi
đi tìm một ánh xạ không tồn tại khi thêm trang mới.

**Bất biến:** lựa chọn sáng/tối lưu bằng **cookie (`kome_giao_dien`) + render
phía máy chủ** (`data-theme` trên `<html>`), KHÔNG bằng `localStorage`. Gói
thiết kế ghi `localStorage`; ta lệch có chủ ý: `localStorage` chỉ đọc được
SAU khi HTML đã vẽ xong, nên đổi sang nó là mua lại một nháy sai màu ở MỖI
lần tải trang — trang vẽ sáng rồi giật sang tối ngay khi JS kịp chạy. Cookie
đọc được ngay lúc server render, nên `data-theme` đã đúng trong chính HTML
đầu tiên gửi xuống, không có khung hình sai màu nào để thấy.

**Bất biến:** bảng màu tối viết HAI lần trong `kome.css` — một lần trong
`@media (prefers-color-scheme: dark){ :root:not([data-theme="sang"]) }`
(chế độ "theo hệ thống"), một lần cho `:root[data-theme="toi"]` (chọn tay) —
vì CSS không gộp được hai selector đó vào một khối. Hai bản PHẢI giống hệt
nhau, **kể cả khai báo `color-scheme:dark`, không chỉ các biến màu**: đổi
biến màu mà quên đổi `color-scheme` là chọn "Tối" trên một máy đang sáng cho
ra nội dung tối nhưng thanh cuộn và mọi ô `<select>` vẫn trắng chói —
`color-scheme` điều khiển đúng những phần trình duyệt tự vẽ mà CSS thường
không chạm tới. Trôi khỏi nhau (dù chỉ một khai báo) là "tối" chọn tay ra
một bộ màu khác "tối" theo hệ thống, và không ai thấy cho tới khi đặt hai
máy cạnh nhau. Có test canh:
`tests/test_giao_dien.py::test_hai_khoi_mau_toi_trong_css_GIONG_HET_NHAU` và
`::test_color_scheme_nam_trong_khoi_bang_toi`.

**Bất biến:** `/giao-dien` chuyển hướng CHỈ về đường dẫn nội bộ, lọc Referer
qua đúng `bao_mat.duong_dan_an_toan` đã dùng cho `?tiep=` sau đăng nhập —
không viết một bộ lọc đường dẫn thứ hai. An toàn nằm ở chỗ bỏ `scheme` +
`netloc` của Referer, KHÔNG nằm ở chỗ bỏ query: route GIỮ NGUYÊN query khi
chuyển hướng, vì đích đã là đường dẫn tương đối rồi nên giữ query không mở
thêm cửa nào — bỏ nó thì người đang lọc `/khach-hang?tinh=...&nv=...` bấm
"Tối" xong mất sạch bộ lọc, phải lọc lại từ đầu. Có test canh:
`tests/test_giao_dien.py::test_giao_dien_chuyen_huong_GIU_LAI_bo_loc_tren_query`.

**Bất biến:** `bao_mat.duong_dan_an_toan` chặn cả dạng `/` + gạch chéo ngược
+ tên miền, không chỉ `//tên-miền` — theo chuẩn phân tích URL của WHATWG,
gạch chéo ngược ngay sau gạch chéo đầu được trình duyệt coi NHƯ một gạch
chéo, nên `/\site-gia.example` là một địa chỉ tuyệt đối trá hình. Trước bản
siết (`dfbbcf0`) chuỗi đó vô hại chỉ vì Starlette mã hoá nó thành `%5C`
trước khi đặt vào header `Location` — tức an toàn phụ thuộc vào hành vi của
FRAMEWORK, thứ một bản nâng cấp có thể đổi mà không ai đụng tới file này.
Hàm này dùng chung cho `?tiep=` sau đăng nhập VÀ Referer của `/giao-dien`,
nên một lỗ ở đây là lỗ ở cả hai cửa. Có test canh:
`tests/test_bao_mat.py::test_duong_dan_an_toan_chan_ca_dang_gach_cheo_nguoc`.

**Bất biến:** trạng thái quan hệ khách hàng so số ngày im lặng với **nhịp mua
riêng của từng khách** (trung vị khoảng cách giữa các lần mua), KHÔNG với một
ngưỡng chung. Đo thật: ngưỡng chung 90 ngày bỏ sót 49 khách đang rời đi và báo
động nhầm 34 khách vẫn mua bình thường.

**Bất biến:** mốc thời gian là **ngày bán mới nhất trong kho**
(`mart.moc_thoi_gian`), KHÔNG phải `current_date`. Dùng `current_date` thì một
ngày không ai nạp file sẽ làm cả 1.710 khách "im lặng thêm một ngày".

**Bất biến (Mốc thời gian dời được, migration 040):** mốc đó LÙI được trong MỘT giao dịch —
`set_config('kome.moc', 'YYYY-MM-DD', true)` (`true` = chỉ giao dịch hiện tại; **KHÔNG BAO
GIỜ `SET` cấp phiên**: Supavisor giữ nó sang kết nối sau — sự cố thật 2026-09-24). `mart.moc_lui()`
= ngày lùi về hoặc NULL (mốc ≥ ngày bán mới nhất ⇒ NULL, tức y như không dời). MỘT chỗ viết điều
kiện "≤ mốc": `mart.ban_den_moc`; mọi view từng đọc thẳng `core.fact_sales_line` (`dong_ban`,
`lan_mua`, `khach_chua_mua`, `khach_mat_hang`, `khoang_cach_mat_hang`, `san_pham_360`,
`toc_do_ban`) đọc view đó — **view mới nào đọc bảng bán cũng phải đọc `mart.ban_den_moc`**,
đọc thẳng `core.fact_sales_line` là view đó không quay về khi xem tháng cũ. `ton_hien_tai` =
ảnh chụp ≤ mốc (không có ⇒ rỗng, màn nói "chưa có ảnh chụp tồn tới thời điểm này" — KHÔNG lấy
ảnh chụp sau mốc, quyết định của chủ DN); `so_cong_no_moi_nhat` = sổ kỳ ≤ mốc. Mốc của khoảng
xem suy theo cú pháp (`ThamSo.moc()`); `khoang_xem.giai_conn` đặt mốc + đọc dải trong MỘT lượt
(hai câu một round-trip), màn không giải khoảng dùng `khoang_xem.dat_moc` (0 lượt khi không có
tham số khoảng — ngân sách mặc định không đổi). Không quay về (có chủ ý): tên khách / người phụ
trách (bản hiện hành), tạm ẩn / hẹn gọi lại / "hôm nay đã nạp chưa" (đồng hồ thật). Đẳng thức
vàng có test canh: mốc D ≡ như thể kho chỉ có dữ liệu bán tới D (`tests/test_moc_lui.py`).
Đặc tả: `docs/superpowers/specs/2026-09-24-moc-thoi-gian-doi-duoc-design.md`.

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

**Bất biến (Đợt 7):** `app.nhat_ky_tiep_xuc` **CHỈ THÊM** — và đó là ràng buộc
của CSDL: migration `030` `REVOKE UPDATE, DELETE` khỏi `kome_app` trên ĐÚNG bảng này
(009 cấp mặc định cả bốn quyền trên mọi bảng `app`). Ghi sai thì ghi thêm một dòng
đính chính. Từ vựng kiểu/kết quả là của gói thiết kế (`KIEU_TX`/`KQ_TX` trong
`Customer 360.dc.html`): `goi`/`ghe`/`chat` · `tot`/`binh`/`xau` — CHECK của bảng và
hằng `kome.lien_he.KIEU`/`KET_QUA` phải đổi CÙNG nhau. Có test canh:
`tests/test_lien_he.py::test_nhat_ky_chi_them_kome_app_khong_sua_khong_xoa_duoc`.

**Bất biến (Đợt 7):** `/lien-he` có HAI loại "hôm nay" và không được gộp. AI cần
gọi (`mart.uu_tien_lien_he`) theo mốc dữ liệu `mart.moc_thoi_gian` như mọi chỉ số;
còn việc TẠM ẨN khách vừa liên hệ (tới `hen_lai`, hoặc `AN_KHI_KHONG_HEN` = 7 ngày
nếu không hẹn) và ô "Hẹn gọi lại hôm nay" theo **đồng hồ thật giờ Tokyo**
(`hom_nay_o_nhat`) — hẹn thứ Năm là thứ Năm ngoài đời. Đây là ngoại lệ THỨ HAI của
bất biến mốc thời gian, cùng lý lẽ với ô tuổi dữ liệu. Khách đang ẩn KHÔNG biến mất
lặng lẽ: khối "Đã liên hệ gần đây — đang tạm ẩn" liệt kê họ. `tut`/`moi` của
`mart.khach_nhom_viec` cố ý KHÔNG vào view (view đó dựng lại `khach_360` ba lần) —
trang trỏ sang `/khach-hang?nhom=tut|moi`.

**Bất biến (036, nhìn theo tháng):** "khách mua đều mà tháng này chưa mua" có
**một** định nghĩa — `mart.khach_thang_nay.nhan` (NHÃN, so bằng, không `NOT`:
`khong_goi` → `da_mua` → `tre` → `chua_toi_ngay` → `khac`) — và ba chỗ đọc: khối
Tổng quan `thang_nay_chua_mua`, cột thứ tư của `/lien-he` (đi chung câu danh sách,
vẫn 3 truy vấn; khách đã ở cột nhịp không lặp lại), việc hôm nay. "Tháng này" theo
mốc dữ liệu; "tháng có mua" = có phiếu doanh thu thuần > 0; "đến cùng ngày" =
`extract(day) <= ngày mốc`, mốc là ngày cuối tháng thì tính trọn tháng trước. Nhóm
này KHÁC nhóm `'im'` (nhịp riêng) — không gộp, mỗi khối in `khach_thang.CACH_TINH`.
Có test canh: `tests/test_khach_thang.py::test_ba_cho_doc_tra_CUNG_MOT_tap_khach`.
Đặc tả: `docs/superpowers/specs/2026-09-23-nhin-theo-thang-design.md`.

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

**Bất biến (042, tồn theo LÔ):** hai "kho" OBC là hai lô của MỘT kho vật lý (bẫy #6).
Vai trò lô theo **MÃ KHO**, viết ĐÚNG MỘT LẦN: `mart.kho_dang_xuat()` (= `0001`); thứ tự
bán = lô đang xuất trước, rồi lô chờ theo hạn tăng dần — KHÔNG suy vai trò từ hạn (hàng chỉ
đi ra từ `0001`). `mart.ton_theo_lo` tính bán từ / bán hết (tồn cộng dồn ÷
`toc_do_ngay_theo_tuoi` — đúng tốc độ xếp trạng thái, nên "bán hết" của lô CUỐI = 
`san_pham_360.du_ban_ngay`, đo thật 134/134), `khong_kip_ban` (bán hết SAU hạn; chưa quá
hạn; không tốc độ ⇒ NULL, không phải true) và `sap_chuyen_lo` (thuộc tính của MÃ, ở dòng
`thu_tu_lo = 1`: lô chờ còn hàng và lô đang xuất đã hết / < 14 ngày — cùng ngưỡng
`sap_thieu`). Khối "Sắp chuyển lô" KHÔNG theo bộ lọc lô (lọc lô chờ thì dòng mang cờ bị
lọc mất). Ngành hàng của `/kho-hang` = `core.dim_product` qua `mart.ten_nganh`, KHÔNG đọc
hai cột `食品分類` mà `在庫一覧` kèm từ 2026-09-24 (một khái niệm một nguồn). Có test canh:
`tests/test_ton_theo_lo.py`. **Migration 042 phải chạy TRƯỚC khi triển khai** (`/kho-hang`
và `/san-pham/{mã}` đọc view đó).

**Bất biến:** hai ô đếm trạng thái ở đầu `/kho-hang` KHÔNG co theo bộ lọc kho và
KHÔNG co theo bộ lọc trạng thái, còn ô "Giá trị tồn chết" thì co theo **cả hai**.
Khác nhau có chủ ý và trang phải nói ra: ô đếm là để so sánh giữa các kho nên phải
đứng yên, còn "giá trị tồn chết của kho này" là con số người ta dùng để quyết định
thanh lý — hiện tổng mọi kho bên cạnh một bảng đã lọc thì sai gần 2× ở công ty hai
kho.

**Bất biến:** bản đồ tỉnh (`/ban-do`) nối từ `core.dim_prefecture` **LEFT JOIN** sang
số liệu khách (`mart.khach_theo_tinh`), KHÔNG `GROUP BY` trên khách rồi vẽ ra bấy
nhiêu ô. Đổi thành `JOIN` (hay để `dim_prefecture` ở vế phải) là tỉnh chưa có khách
nào — hoặc chưa có khách của MỘT người phụ trách cụ thể khi lọc theo `sale` — biến
mất khỏi bản đồ, **mà trang vẫn vẽ ra bình thường, chỉ thiếu đúng một ô**, không lỗi
nào nổ ra để lộ chuyện đó. Điều này đã có thể lộ ra ngay HÔM NAY, không cần lọc gì:
`core.dim_customer` có đủ 47 tỉnh nhưng `mart.khach_360` chỉ 46 — 和歌山県 có 1 khách
trong `dim_customer` nhưng khách đó chưa từng có dòng bán nào, nên không có dòng
trong `khach_360` (view đó dựng từ `mart.lan_mua`, phải có ít nhất một lần bán). Bản
đồ TỔNG (không lọc gì) phải hiện 和歌山県 là một ô "0 khách" — thấy nó trống là ĐÚNG,
không phải dấu hiệu phép nối hỏng. Có test canh:
`tests/test_ban_do.py::test_du_47_o_ke_ca_tinh_khong_co_khach`.

**Bất biến:** `mart.khach_theo_tinh.can_goi` đếm bằng `EXISTS` trên
`mart.khach_nhom_viec`, KHÔNG `LEFT JOIN` nó — cùng hình mẫu migration `022`. Một
khách có thể thuộc NHIỀU nhóm việc cùng lúc (`im` và `tut` cùng lúc), nên JOIN thẳng
sẽ NHÂN DÒNG khách lên và thổi phồng cả `so_khach` lẫn `doanh_thu_12t` của tỉnh đó,
không chỉ `can_goi` — một tỉnh có nhiều khách vừa `im` vừa `tut` sẽ báo nhiều khách
hơn số khách nó thật sự có. Có test canh:
`tests/test_ban_do.py::test_khach_theo_tinh_dung_EXISTS_khong_JOIN_vao_khach_nhom_viec`.

**Bất biến:** mọi liên kết rời `/ban-do` sang `/khach-hang` — ô SVG **và** dòng
bảng xếp hạng — phải mang theo `tat_ca`/`nv`. Từ giai đoạn 2 hai màn là hai TAB
trên CÙNG một trạng thái lọc (`giao_dien/src/khach/loc.ts`); bấm ô / dòng chỉ đổi
`tinh` + tab (`BanDo.tsx::moTinh`), nên bộ lọc người phụ trách không có đường rơi.
`/khach-hang` thiếu hai tham số đó rơi về mặc định lọc theo NGƯỜI ĐANG ĐĂNG
NHẬP, nên bản đồ vẽ số của "tất cả" (hay của một đồng nghiệp) mà bấm vào lại ra
danh sách của chính mình — cùng lớp lỗi `kome/khach_hang.py::_vi_tu` đã ghi
("chip Tất cả (1.710) bấm vào ra 216 khách"), chỉ khác là nó bắc qua HAI MÀN
chứ không nằm gọn trong một màn.
Có test canh: `tests/test_ban_do.py::
test_bam_o_hay_dong_bang_GIU_NGUYEN_bo_loc_nguoi_phu_trach`.

**Bất biến:** bậc màu 0 của bản đồ (`kome/ban_do.py::_tinh_bac`) dành cho **ĐÚNG
BẰNG 0**, không phải "không dương". Doanh thu 12 tháng của một tỉnh CÓ THỂ ÂM
(赤伝 — phiếu đỏ, số ÂM, luật cấm lọc bỏ — của một tỉnh chỉ có một hai khách).
Xếp số âm vào bậc 0 là chú giải ghi "Trống — không có doanh thu 12 tháng" trong
khi chính ô đó in `¥-123.456`. Số âm tham gia chia phân vị như mọi giá trị khác
và chú giải in ra khoảng THẬT, kể cả khi khoảng đó âm. Có test canh:
`tests/test_ban_do.py::test_doanh_thu_AM_khong_roi_vao_bac_TRONG`.

**Bất biến:** `mart.tien_do_ngan_sach` nối chỉ tiêu với thực tế bằng **`FULL
JOIN`**, không `LEFT JOIN` theo chiều nào cả. Nối từ chỉ tiêu sang thực tế thì
tháng có doanh thu mà QUÊN đặt chỉ tiêu biến mất khỏi báo cáo; nối ngược lại
thì người CÓ chỉ tiêu mà bán 0 đồng biến mất — đúng người cần nhìn nhất thì
không có dòng nào. Cả hai chiều đều mất dòng **mà trang vẫn vẽ ra bình
thường**, không lỗi nào nổ ra, cùng lớp lỗi đã ghi cho `/ban-do`. Đo thật
2026-09-22: dữ liệu bán có **6** mã phụ trách (`0000` `0002` `0004` `0102`
`0104` `0105`) trong khi `core.dim_salesperson` chỉ có **5** — `0000` có 1
khách và ¥28.981 doanh thu kỳ 7 và không bao giờ đặt được chỉ tiêu (khoá ngoại
chặn), nên phép nối xuất phát từ chỉ tiêu làm số tiền đó bốc hơi. Màn hình
hiện nó thành một dòng "(mã không có trong danh sách phụ trách)". Có test
canh: `tests/test_ngan_sach_mart.py::test_nguoi_co_chi_tieu_ma_KHONG_ban_duoc_dong_nao_van_co_dong`,
`::test_thang_co_doanh_thu_ma_QUEN_dat_chi_tieu_van_co_dong`,
`::test_ma_phu_trach_ngoai_dim_salesperson_van_hien_doanh_thu`.

**Bất biến (041, ngân sách công ty):** ngân sách CÔNG TY là **số nhập thẳng**
(`app.ngan_sach_cong_ty`: `doanh_thu`, `lai_gop` — lãi gộp = 粗利益), **KHÔNG phải tổng chỉ tiêu
từng người**, và chưa đặt thì là "chưa đặt" — KHÔNG rơi về tổng từng người (hai định nghĩa cùng
tên là hai con số nói hai điều). Mọi chỗ đọc tiến độ công ty — Tổng quan (ô KPI, khối ngân sách,
khối theo tháng), Báo cáo, Dự báo chốt tháng — đọc `mart.tien_do_cong_ty` /
`mart.ngan_sach_cong_ty_thang`; `mart.tien_do_ngan_sach` chỉ còn là tiến độ TỪNG NGƯỜI (thêm bốn
cột lãi gộp cùng công thức). Mốc lãi gộp đến hôm nay = cùng công thức ngày làm việc. Hai bảng
ghi chung MỘT sổ `app.ngan_sach_nhat_ky` (`salesperson_code` NULL = công ty, `chi_so` =
`doanh_thu`/`lai_gop`) nên `anh_chup._PHIEN_BAN` và `/nhat-ky` không cần nhánh mới. Ô trống ≠ 0
ở cả bốn loại ô. Có test canh:
`tests/test_ngan_sach_bao_cao.py::test_ngan_sach_cong_ty_la_so_NHAP_THANG_khong_phai_tong_tung_nguoi`.
Đặc tả: `docs/superpowers/specs/2026-09-24-ngan-sach-cong-ty-design.md`.

**Bất biến:** `app.ngan_sach.thang` là **`date` mùng 1 có khoá ngoại tới
`core.dim_date`**, không phải `text 'YYYY-MM'`. `core.dim_date` phủ 2024-01-01
→ 2035-12-31, và `mart.ngan_sach_thang` nối sang nó để lấy `company_fy` — nên
một dòng chỉ tiêu ngoài dải lịch **biến mất khỏi mọi báo cáo mà không lỗi nào
nổ ra**: dữ liệu còn trong bảng, chỉ là không ai nhìn thấy nữa. Khoá ngoại
biến nó thành một lỗi ghi ngay tại chỗ nhập. Việc đổi `date` sang `'YYYY-MM'`
xảy ra ở **đúng một chỗ** cho mỗi bảng — `mart.ngan_sach_thang` (từng người) và
`mart.ngan_sach_cong_ty_thang` (công ty, 041) — vì mọi view khác của `mart` đều dùng khoá
tháng dạng chuỗi.

**Bất biến:** **không có dòng** trong `app.ngan_sach` = *chưa đặt chỉ tiêu*;
`muc_tieu = 0` = *đã đặt và đặt bằng không*. Màn nhập để ô trống cho cái thứ
nhất và in `0` cho cái thứ hai; `kome.ngan_sach.doc_so("")` trả `None` chứ
không trả `0`. Cùng nếp `mart.san_pham_360.ton` — hiện `0` cho thứ chưa biết
là nói một điều sai bằng con số. Và `kome.ngan_sach.luu()` **chỉ đụng những ô
đã đổi**: `sua_luc`/`sua_boi` phải trả lời "ai đổi con số NÀY lần cuối", không
phải "ai bấm Lưu lần cuối".

**Bất biến:** "ngày làm việc" có ĐÚNG MỘT định nghĩa:
`mart.lich_kinh_doanh.la_ngay_kd` (migration `031`) = không phải thứ Bảy/Chủ nhật
**và** không phải ngày lễ quốc gia Nhật (`core.dim_date.ngay_le`, migration `032`,
2024–2035). Bốn chỗ ĐỌC view đó, không chỗ nào tự viết lại vị từ:
`mart.ngay_kinh_doanh` (mẫu số "đến hôm nay" của ngân sách), màn `/du-bao`, bảng
phủ theo ngày (`kome/coverage.py::tinh_bang_ngay`), ô "hôm nay đã có dữ liệu chưa"
(`kome/tuoi_du_lieu.py`) và danh sách ngày thiếu của `/kho-du-lieu`
(`kome/web/app.py::_ky_du_lieu`). Ngày lễ SINH bởi `scripts/sinh_ngay_le.py` (luật
祝日法) và viết thành chữ trong 032; `tests/test_ngay_le.py` so khối đó với bộ sinh
và với lịch chính thức 2024–2026. Xuân/thu phân của năm xa là GẦN ĐÚNG (国立天文台
chỉ công bố trước một năm) — lệch thì sửa bằng migration MỚI.
HẠN CHẾ CÒN LẠI (có tên): ngày nghỉ RIÊNG của công ty (Obon, 年末年始 29/12–3/1)
KHÔNG có — đó là lịch của KOME, không có nguồn nào để đọc; đừng đoán. Tháng 8 và
tháng 12/1 vì vậy vẫn đếm thừa vài ngày làm việc, và `/kho-du-lieu` vẫn liệt kê
các ngày đó là "thiếu" (câu nhắc trên màn đã nói rõ). Đừng "sửa" bằng một định
nghĩa thứ hai (ví dụ "ngày có phiếu bán") — hai định nghĩa cùng tên là hai con số
nói hai điều.

**Bất biến:** `POST /ngan-sach` KHÔNG bị chế độ chỉ-đọc (`_chi_doc`) chặn —
chủ ý, không phải sót. Lý do: `_chi_doc` (nay chỉ theo `KOME_CHI_DOC`; trước 045
nó luôn bật trên Vercel) là công tắc của **luồng NẠP OBC**, **không phải phân
quyền**. Ghi 60 số nguyên không dính gì tới giới hạn của luồng nạp. Và bản Vercel là bản chạy **duy nhất bắt
buộc** có `KOME_SESSION_SECRET`, tức là nơi cờ quyền LUÔN được thi hành — máy
trong công ty mới là nơi có thể không có cổng nào. Chặn màn nhập ở Vercel là
lấy nó đi đúng ở chỗ nó an toàn nhất.

**Bất biến (Đợt 8):** mọi cách tính của `/du-bao` (`kome/du_bao.py`) phải giải
thích được bằng MỘT câu in ngay dưới khối, và không có hằng số bịa. Chốt tháng =
đã bán + (đã bán ÷ ngày làm việc đã qua) × ngày làm việc còn lại; khoảng thấp–cao
là sai số nhỏ nhất/lớn nhất của CHÍNH cách tính đó trên các tháng đủ ngày trước
(cần ≥ 3 tháng, không đủ thì in "—" chứ không đoán); 12 tháng tới = cùng tháng năm
trước × hệ số, hệ số cơ sở là **tỷ số của các tổng** (bất biến tỷ suất ở trên áp cả
ở đây — có test canh
`tests/test_du_bao.py::test_he_so_la_TY_SO_CUA_CAC_TONG_khong_phai_trung_binh_ty_so`).
"So với năm trước" chia cho tổng CÙNG CÁC THÁNG ĐÓ năm trước, không cho "12 tháng
qua" (hai khoảng khác độ dài khi có tháng không dự báo được). Gói thiết kế có
"88% chắc chắn" / "72% nguy cơ" — ta KHÔNG hiện phần trăm xác suất vì không đo
được; thay bằng "x/y lần mua đúng nhịp" và "im lặng n× nhịp mua riêng". Tháng đầu
của kho bắt đầu giữa chừng không bao giờ làm tháng đối chiếu hay tháng kiểm.

**Bất biến (Đợt 5b):** hai màn có "so cùng kỳ" nhưng đi theo HAI kiểu so khác
nhau, và mỗi ô phải luôn nói nó so cách nào — im lặng là để người đọc tự suy
diễn sai kiểu kia:
- `/bao-cao` so **cùng tháng với cùng tháng** (`mart.ky_cung_ky`): kỳ 6 chỉ có
  5 tháng dữ liệu, nên đem cả kỳ 6 so với cả kỳ 7 (12 tháng) ra "+140%" — đúng
  số học, sai hoàn toàn về kinh doanh. Mỗi dòng so cùng kỳ ở đây PHẢI in kèm số
  tháng đối chiếu ("▲ 4,2% so cùng kỳ · 5 tháng đối chiếu (2026-03 → 2026-07)"),
  không chỉ in phần trăm trần.
- `/` so **cùng dải ngày** (`mart.thang_den_hom_nay`, §3.7 migration `029`):
  1 → ngày hôm nay của tháng đó năm trước, KHÔNG phải trọn tháng năm trước. Đem
  12 ngày đầu tháng so với cả tháng thì giữa tháng nào cũng "sụt 60%".
Hai công thức không được gộp làm một: đổi `/` sang so cả tháng (hay ngược lại)
là âm thầm đổi ý nghĩa của phép so mà không ai để ý cho tới khi có người đối
chiếu tay. Có test canh:
`tests/test_phan_tich_mart.py::test_ky_cung_ky_chi_tinh_thang_doi_chieu`,
`::test_thang_den_hom_nay_so_cung_so_ngay_khong_tron_thang`,
`::test_thang_den_hom_nay_29_2_kep_ve_28_2`,
`tests/test_bao_cao_phan_tich_web.py::test_co_doi_chieu_hien_dung_cau`,
`::test_khong_co_doi_chieu_hien_dung_cau`.

**Bất biến:** "ngành hàng" là `food_category_name`, và biểu thức
`coalesce(nullif(food_category_name, ''), '(chưa phân loại)')` viết ĐÚNG MỘT
LẦN — từ migration `039` là hàm `mart.ten_nganh()`, và `mart.ban_theo_nganh_thang`
(LEFT JOIN từ dòng bán sang `core.dim_product`, `029`, thay lại ở `039`) cùng
`mart.nganh_khoang` gọi hàm đó. Mọi view ngành khác (`..._so_sanh`,
`nganh_ky_cung_ky`) đọc lại view đó, không tự viết biểu thức riêng — hai bản
chép của cùng một `coalesce` trôi khỏi nhau là mã hàng rỗng tách ra hai ô
"(chưa phân loại)" khác nhau trên cùng một trang. Hằng `kome.bao_cao.NGANH_TRONG`
là bản chép BẮT BUỘC ở tầng Python (`nhom_theo_nganh` ghép `mart.ban_theo_san_pham`,
thứ trả `food_category_name` THÔ chưa qua coalesce, vào theo tên ngành của
`nganh_ky`) — lệch một ký tự ở đây thì mã hàng rỗng của bảng đó rơi vào một
ô "(chưa phân loại)" riêng, cạnh ô gốc từ mart, mà không lỗi nào nổ ra. Có
test canh:
`tests/test_bao_cao_phan_tich_web.py::test_nganh_trong_khop_chu_view_tra_ra`,
`tests/test_phan_tich_mart.py::test_tong_cac_nganh_bang_tong_thang_ke_ca_dong_ma_hang_rong`.

**Bất biến:** `mart.ban_theo_nganh_thang_so_sanh` nối **FULL JOIN** giữa tháng
này và tháng M−12 theo ngành (cùng lớp bất biến FULL JOIN của
`mart.tien_do_ngan_sach` đã ghi ở trên) — ngành bán năm ngoái mà năm nay không
bán phải có dòng `doanh_thu_thuan = 0`, chính là ngành sụt mạnh nhất. Đổi sang
`LEFT JOIN` từ tháng này là ngành đó biến mất khỏi khối "kéo doanh thu xuống"
mà trang vẫn vẽ ra bình thường. View lọc chỉ giữ **tháng có trong kho** (chặn
bằng CTE `ct`); thiếu vị từ đó thì FULL JOIN đẻ ra 12 tháng tương lai từ dữ
liệu năm trước. View gốc được tham chiếu hai lần trong chính migration này nên
nó vào CTE `AS MATERIALIZED` ghi tường minh (bất biến CTE đã ghi ở trên). Có
test canh:
`tests/test_phan_tich_mart.py::test_nganh_ban_nam_ngoai_ma_nam_nay_khong_ban_van_co_dong`,
`::test_khong_sinh_dong_cho_thang_khong_co_trong_kho`,
`::test_nganh_so_sanh_chi_quet_fact_sales_line_mot_lan`.

**Bất biến:** Pareto tập trung khách (`mart.tap_trung_khach`) gộp theo
**KHÁCH**, KHÔNG theo `(khách, người phụ trách)` như `mart.ban_theo_khach`.
Một khách đổi người phụ trách giữa kỳ sẽ chiếm HAI cột trên biểu đồ nếu gộp
theo view kia — cùng khách, tiền chia đôi, độ tập trung bị tính thấp hơn thật.
Có test canh:
`tests/test_phan_tich_mart.py::test_tap_trung_khach_mot_khach_hai_nguoi_phu_trach_chi_mot_dong`.

**Bất biến:** cây ô (`ve_cay_o`, `kome/ve_phan_tich.py`) không vẽ được diện
tích ÂM — ngành/mã doanh thu ≤ 0 bị bỏ khỏi hình. Phần bị bỏ PHẢI in ra dưới
khối kèm số tiền thật ("Không vẽ: ¥−26.258.617 của 10 mã doanh thu âm"), không
được lặng lẽ bỏ: lặng lẽ bỏ là tổng cây ô lệch tổng ô chỉ số của kỳ mà không ai
biết vì sao. Bất biến đối soát: với MỌI đầu vào,
`sum(doanh_thu_ve của các ngành được vẽ) + khong_ve == sum(dt_nganh đầu vào)`.
Có test canh: `tests/test_ve_phan_tich.py::test_ve_cay_o_bo_nganh_am_va_cong_don_khong_ve`,
`::test_doi_soat_a_nganh_duong_co_mot_ma_am`, `::test_doi_soat_b_hon_5_ma_duong_cong_mot_ma_am`,
`::test_doi_soat_c_ca_nganh_am`,
`tests/test_bao_cao_phan_tich_web.py::test_khong_ve_hien_dung_cau_khi_co_doanh_thu_am`.

**Bất biến (034, bố cục Tổng quan):** mỗi người tự sắp khối, nhưng **cùng các
khối và cùng con số** cho mọi người — bố cục là cách XẾP, không phải bộ lọc dữ liệu.
Lưu ở `app.nguoi_dung.bo_cuc_tong_quan` (KHÔNG localStorage — máy chủ chèn sẵn vào
`window.__KOME__`, không có khung hình giật), đọc cùng lượt hỏi của cổng đăng nhập (0
truy vấn thêm). Mọi bố cục đi qua `kome/web/bo_cuc.py::chuan_hoa` lúc ghi và lúc đọc;
mã khối cũ của bản Jinja (`chi_so`, `can_han`…) đổi qua `MA_CU`. Danh mục 21 khối +
6 nhóm + 4 vai trò là `bo_cuc.KHOI`/`NHOM`/`VAI_TRO` (chép `MODULES`/`VAI_TRO` của gói
thiết kế) — giao diện ĐỌC danh mục đó, không tự chép. Mọi khối trong danh mục phải có
hoặc một hàm trong `kome/khoi_tong_quan.py::KHOI`, hoặc một câu trong `CHUA_CO` (có
test canh).

**Bất biến (giao diện React, 2026-09-23):** chủ doanh nghiệp đổi nguyên tắc "không
JavaScript" — màn nào đã chuyển (`/` trước tiên) là ứng dụng React (`giao_dien/`,
Vite + TS + TanStack Query, KHÔNG thư viện biểu đồ — biểu đồ SVG tự vẽ như gói thiết
kế, có ô nổi / bật tắt chú giải / bấm để lọc). Đặc tả:
`docs/superpowers/specs/2026-09-23-giao-dien-react-design.md`.
- **Bản build được COMMIT** ở `kome/web/spa/` (máy công ty không có Node). Sửa bất cứ
  gì trong `giao_dien/` là phải `cd giao_dien && npm run build` — không build là
  `tests/test_api.py::test_ban_build_khop_ma_nguon` đỏ (so dấu vân tay `spa/.nguon`).
  `giao_dien/` nằm trong `.vercelignore`; KHÔNG đặt `package.json` ở gốc repo.
- **API không định nghĩa chỉ số.** `/api/...` gọi lại hàm/view có sẵn; tỷ suất vẫn
  là tỷ số của các tổng; ngân sách truy vấn từng khối có test đếm
  (`tests/test_api.py::NGAN_SACH_TRUY_VAN`). Chưa đăng nhập -> **401 JSON**, không 303.
- **Ảnh chụp theo phiên bản dữ liệu** (`kome/web/anh_chup.py`, migration `035`): đo
  thật trang `/` cũ ~9 s ở máy chủ. Phiên bản = lô nạp mới nhất + lần hoàn tác mới
  nhất + sửa ngân sách + ghi tiếp xúc + migration mới nhất + dấu vân tay mã `kome/`
  (+ ngày Tokyo cho khối theo đồng hồ thật). **Thêm một bảng mà web ghi được và màn
  nào đó đọc = PHẢI thêm nó vào `_PHIEN_BAN`**, không thì màn đó đứng yên sau khi
  người ta sửa. Không bao giờ trả ảnh chụp của phiên bản cũ. Sau nạp/hoàn tác,
  `lam_nong` tính sẵn trong luồng nền và nuốt lỗi. Test mặc định TẮT ảnh chụp
  (`KOME_ANH_CHUP=0`, conftest). **Migration 035 phải chạy TRƯỚC khi triển khai.**
- `window.__KOME__` (người đăng nhập, cờ quyền, bố cục, danh mục) chèn vào
  `index.html` qua `kome/web/spa.py::trang` — `<`, `>`, `&` được thoát (có test).
- **Giai đoạn 2 (màn Khách hàng)** — đặc tả `2026-09-23-giai-doan-2-khach-hang-design.md`:
  `/khach-hang`, `/ban-do`, `/khach-hang/{mã}` là React (template Jinja đã xoá). Ảnh
  chụp nào dữ liệu KHÔNG đọc bảng `app` (danh bạ, bản đồ, dòng bán) dùng
  `chi_nap=True` — ghi tiếp xúc không làm chúng cũ; hồ sơ (đọc nhật ký) dùng phiên
  bản đầy đủ. `lam_nong` làm nóng cả danh bạ (`anh_chup.KHOA_DANH_BA`, ~6 s trên CSDL
  thật). Bản đồ vẫn là LƯỚI 47 tỉnh, không Leaflet. Khối gói thiết kế không có nguồn
  (công nợ, giá riêng, tạo đơn, ảnh, chat, gợi ý tiếp khách, "độ tin cậy %") là khung
  "chưa có" hoặc nút vô hiệu kèm lý do.
- **Giai đoạn 3 (Báo cáo · Dự báo · Cần liên hệ)** — đặc tả
  `2026-09-23-giai-doan-3-bao-cao-du-bao-lien-he-design.md`: template Jinja đã xoá. Hình
  học biểu đồ vẫn dựng ở `kome/bao_cao.py` / `kome/ve_phan_tich.py` / `kome/ve_du_bao.py`
  (bất biến đối soát có test ở đó) — React chỉ vẽ. JSON qua `api.thanh_json` (dataclass
  KÈM `@property`). Bốn số phụ của khối ngân sách tính ở MỘT chỗ,
  `kome.bao_cao.chi_so_phu` (dùng cho cả `/` và `/bao-cao`). Màn Cần liên hệ giữ bố cục
  CRM nhưng cột là LÝ DO gọi — không có "deal" / "% khả năng chốt" nào.
- **Giai đoạn 4 (Sản phẩm · Kho hàng)** — đặc tả
  `2026-09-23-giai-doan-4-san-pham-kho-hang-design.md`: template Jinja đã xoá. Danh mục là MỘT
  ảnh chụp cả 232 mã (`SP.danh_muc`, 1 lượt hỏi) — lọc/sắp/đếm ở trình duyệt
  (`giao_dien/src/san_pham/loc.ts`), cùng luật bộ đếm "mọi bộ lọc trừ của chính nó".
  "Doanh thu 12 tháng" của mã dùng ĐÚNG cửa sổ `mart.hang_doanh_thu`
  (`sales_date > hom_nay - 365`). Chip nhóm là NGÀNH (`food_category_name`, rỗng →
  `bao_cao.NGANH_TRONG`) — `san_pham_360.nhom` (`kind_name`) chỉ có 有形/無形 trên dữ liệu thật.
- **Giai đoạn 5 (Kho dữ liệu · Nhật ký · Cài đặt · Ngân sách · Đăng nhập · trang thông
  báo)** — đặc tả `2026-09-23-giai-doan-5-he-thong-design.md`: **KHÔNG còn template Jinja
  nào** (`kome/web/templates/` đã xoá, `jinja2` khỏi requirements). Route các màn này GIỮ
  NGUYÊN truy vấn cũ và chèn kết quả vào `window.__KOME__.man` (`app.py::_spa(man=…)`, qua
  `_json_man`) — ngân sách lượt hỏi và cổng quyền không đổi. Biểu mẫu (nạp, hoàn tác,
  ngân sách, quyền, đăng nhập) vẫn là `<form method="post">` THẬT. Lỗi 500 / 403 / bản
  chỉ-đọc là `window.__KOME__.thong_bao` vẽ trong khung chung (`he_thong/ThongBao.tsx`), thanh
  bên vẫn là lối ra; `/api/*` bị cấm nhận 403 JSON. Đăng nhập sai: vỏ React + `dang_nhap_sai`,
  mã 401.
- Thanh bên: sáu nhóm của gói thiết kế; màn chưa có hiện MỜ kèm "chưa có" (không giả
  vờ có); bốn màn bị cắt (lộ trình §4.2) không hiện; Kho dữ liệu / Ngân sách ẩn theo
  cờ quyền. Chuông chỉ báo thứ có nguồn thật (`khoi_tong_quan.thong_bao`).

**Bất biến (Khoảng xem, migration 039 — 2026-09-24):** cả website có MỘT khoảng xem,
nằm TRÊN URL (`?thang=YYYY-MM` · `?ky=<company_fy>` · `?tu=&den=`; không tham số = tháng
của `mart.moc_thoi_gian.hom_nay`, mùng 1 → hôm nay). Không cookie, không localStorage —
gửi link là thấy đúng khoảng; đóng trình duyệt là về tháng hiện tại. Bốn luật:
- **Một chỗ hiểu khoảng xem**: `kome/khoang_xem.py` (đọc tham số · cắt vào dải dữ liệu ·
  dải so sánh · câu mô tả). `so_sanh[0]` luôn là NĂM TRƯỚC; `[1]` là tháng trước / khoảng
  liền trước. Tháng dở dang so CÙNG DẢI NGÀY (29/2 → 28/2, đúng `mart.thang_den_hom_nay`),
  tháng trọn so trọn tháng; Kỳ so trên các tháng CẢ HAI phía có dữ liệu (đúng
  `mart.ky_cung_ky`). Phép so vào trước dải dữ liệu → `co = false`, màn in "không có dữ liệu
  để so". Giao diện KHÔNG tự tính ngày so sánh (`giao_dien/src/khung/khoang.ts` chỉ đọc/ghi
  URL và in `mo_ta` của máy chủ).
- **Chỉ số theo khoảng vẫn ở `mart`**: hàm `mart.*_khoang(tu, den)` (`LANGUAGE sql STABLE`,
  gộp thẳng vào câu gọi). `kome/ban_khoang.py` chỉ hỏi chúng và dựng lại hình dạng của
  `kome/bao_cao.py`. Đẳng thức có test canh (`tests/test_mart_khoang.py`,
  `tests/test_ban_khoang.py`): tháng trọn = `mart.ban_theo_thang`; tháng hiện tại =
  `mart.thang_den_hom_nay`; Σ ngày = Σ ngành = tổng khoảng; dạng Kỳ của `/bao-cao` = đúng
  số cũ (`BK.tinh_bao_cao` gọi thẳng `bao_cao.tinh_bao_cao`).
- **Số bán hàng đổi theo khoảng, và từ migration 040 MỌI THỨ quay về mốc của khoảng** (ngày
  cuối khoảng): hạng 12 tháng, trạng thái / nhịp mua, nhóm cần gọi, tồn, tốc độ, công nợ, dự
  báo — xem bất biến "Mốc thời gian dời được" bên dưới. Nhãn "hôm nay" đổi thành "đến
  <ngày>" khi đang xem lùi (`KhoangMayChu.dang_lui`, `khoang.ts::useNhanMoc`). Ngân sách chỉ
  theo tháng / kỳ — dạng Khoảng hiện câu nói rõ, không tự chia chỉ tiêu.
- **Khoá ảnh chụp** = đường dẫn + tham số khoảng chuẩn hoá THEO CÚ PHÁP
  (`ThamSo.khoa()`, không hỏi CSDL — "trúng ảnh chụp: 1 lượt hỏi" giữ nguyên); giải khoảng
  (+1 lượt `pham_vi`) chạy TRONG hàm tính. Khối Tổng quan theo khoảng: `KHOI[..][3] = True`,
  ngân sách lượt hỏi = cũ + 1 (`tests/test_api.py::NGAN_SACH_TRUY_VAN`). `/bao-cao` vẫn ≤ 11
  ở cả ba dạng (`tests/test_ban_khoang.py::test_bao_cao_thang_khong_qua_11_truy_van`).
- **Kỳ so sánh tự chọn** (`?ss_thang=` · `?ss_ky=` · `?ss_tu=&ss_den=`, 2026-09-25) THAY cả
  hai phép so mặc định bằng MỘT (`so_sanh = (SoSanh(ma='tu_chon'),)`, `KhoangXem.tu_chon`) — mọi
  màn đọc `so_sanh[0]`/`_ss_phu` tự đi theo. Tháng↔Tháng dở dang cắt cùng dải ngày, Kỳ↔Kỳ cùng vị
  trí trong kỳ (theo tháng có dữ liệu), tổ hợp khác nguyên văn + `mo_ta` in số ngày hai bên. Dải
  so phải kết thúc ≤ ngày cuối khoảng xem (400) — `mart.dong_ban` chỉ thấy dòng ≤ mốc, KHÔNG nới
  mốc. Màn không dùng phép so gọi `ThamSo.chinh()` (`api._ts(...).chinh()`) để đổi kỳ so sánh
  không làm ảnh chụp của chúng trượt. `/bao-cao?ky=&ss_*=` đi nhánh khoảng (không `cung_ky`).
  `datKhoang` giữ `ss_*`; chỉ `datSoSanh` đổi nó. Test: `tests/test_ky_so_sanh.py`. Đặc tả:
  `docs/superpowers/specs/2026-09-25-ky-so-sanh-tu-chon-design.md`.
Liên kết nội bộ giữ khoảng xem nhờ MỘT bộ viết lại `href` ở `document`
(`khoang.ts::ganVietLaiLienKet`); mọi `history.pushState/replaceState` của từng màn đi
qua `giuKhoang()` — thêm một màn có bộ lọc trên URL mà quên hàm đó là đổi bộ lọc xong mất
khoảng xem; điều hướng bằng JavaScript (`location.href = …`) cũng phải bọc `giuKhoang()`.
Bộ lọc nhãn tháng của `/khach-hang` là `?nhan_thang=` (KHÔNG `?thang=` — trùng tên là bộ lọc
nhãn bị đọc thành tháng xem). Màn theo khoảng: Tổng quan, Báo cáo (đợt A), Khách hàng — danh
sách / hồ sơ / bản đồ (đợt B), Sản phẩm — danh mục / hồ sơ mã (đợt C). Số theo khoảng của hồ
sơ khách và của Sản phẩm đi endpoint RIÊNG (`/api/khach-hang/{mã}/khoang`,
`/api/san-pham/khoang`, `/api/san-pham/{mã}/khoang`, mỗi cái 2 lượt) — hồ sơ khách đã chạm
trần 8 lượt, danh mục vẫn MỘT ảnh chụp 1 lượt. Danh sách khách ghép doanh số theo khoảng
(ảnh chụp riêng theo khoảng, `anh_chup.KHOA_DANH_BA_KHOANG`) vào danh bạ bằng
`KH.ghep_khoang` — BẢN SAO, không sửa danh bạ gốc (nó là ảnh chụp dùng chung mọi khoảng).
Cột so sánh ở Khách hàng / Sản phẩm là phép so PHỤ (`so_sanh[1]`: tháng trước / khoảng liền
trước; dạng Kỳ: năm trước). Bản đồ thêm hai chỉ số `dt_khoang` / `khach_mua`
(`mart.tinh_khoang`) — "Doanh thu 12 tháng" giữ nguyên. Đặc tả: `docs/superpowers/specs/2026-09-24-khoang-xem-thang-design.md`.

**Bất biến (Đợt 6, migration 038):** công nợ đọc sổ `請求先元帳` (spec `seikyu_motocho`
→ `core.fact_ar_ledger`), mỗi lô là ẢNH CHỤP một kỳ (kỳ đọc từ dòng 集計期間), mart đọc lô
có kỳ kết thúc muộn nhất (`mart.so_cong_no_moi_nhat`). Ba luật:
- **Số dư là cột `残高` của OBC** (dòng cuối từng bên), KHÔNG tự cộng lại. Đo thật: 12/215
  bên (nhóm mã 0090…) có phiếu thu mà 残高 không đổi — cộng tay 入金額 ra "đã thu" sai.
  "Đã thu trong kỳ" = mang sang + nợ + điều chỉnh − số dư; cổng 5 đối chiếu mang sang +
  【合計】 = số dư cuối (bản thật khớp 215/215).
- **Phần còn nợ từng phiếu là GIẢ ĐỊNH trả cũ trước** (`mart.cong_no_phieu`) — OBC không
  ghi phiếu nào đã trả. Màn phải in câu đó (`kome.cong_no.CACH_TINH["fifo"]`) và gọi cột là
  "Đã thu (ước)".
- **Hạn trả chỉ suy từ hai mẫu tên điều kiện** (`末締/翌月末日`, `末締/翌月N日`). 代引請求 /
  その都度請求 / 前払い … → "không suy được hạn", KHÔNG BAO GIỜ tính là quá hạn — `代引専用`
  (tiền hãng vận chuyển thu hộ) chiếm ~¥93M số dư, gán hạn đoán cho nó là thổi phồng
  "quá hạn" lên gấp mấy lần. Tuổi nợ đếm từ ngày phiếu tới CUỐI KỲ SỔ (mốc dữ liệu).
Công nợ ghi theo BÊN NHẬN HOÁ ĐƠN (請求先), không theo từng khách: danh sách khách không
lọc/đếm theo nợ; hồ sơ khách hiện số của cả bên. `得意先元帳` (không có 残高) và
`入金伝票データ` (đã nằm trong sổ) CỐ Ý chưa có bộ nạp. Đặc tả:
`docs/superpowers/specs/2026-09-24-dot-6-cong-no-design.md`. Có test canh: `tests/test_cong_no.py`.

**Bất biến:** Dashboard (`/`, đợt 5b) là "công ty đang thế nào" — mọi khối SỐ
TỔNG (4 ô chỉ số tháng, xu hướng 30 ngày, sức khoẻ khách, tiến độ ngân sách,
hàng cận hạn) KHÔNG lọc theo người đăng nhập. CHỈ khối "Cần gọi hôm nay" lọc
theo `sale` (mặc định người đăng nhập, `?tat_ca=1` bỏ lọc — cùng nếp
`/can-xu-ly`). Lọc cả trang theo từng sale là một câu hỏi khác, đã có nhà ở
`/bao-cao` (bảng theo người phụ trách) và `/khach-hang?nv=`. Khối nào của gói
thiết kế không có nguồn dữ liệu thật (công nợ, dòng tiền, mua hàng, khiếu nại,
thời tiết) thì KHÔNG được dựng bằng số bịa — dòng "Tồn kho — chưa có" cũ phải
bỏ hẳn (`/kho-hang` đã có từ đợt 4b), không phải thay bằng số giả. Tuổi nợ phải thu
có nguồn từ đợt 6 (khối `cong_no`, sổ 請求先元帳). Có test
canh: `tests/test_tong_quan.py::test_can_goi_mac_dinh_loc_theo_nguoi_dang_nhap`,
`::test_o_chi_so_so_cung_so_ngay`, `::test_khong_con_khoi_ton_kho_chua_co_du_lieu`.

**Bất biến (soát hiệu năng đợt 5b):** dashboard `/` KHÔNG được gọi thẳng
`kome.san_pham.kho_hang()` hay `kome.khach_hang.can_xu_ly()` cộng một câu
`count(*) GROUP BY trang_thai` riêng — dù cả hai đều "đúng", chúng đánh giá
lại `mart.khach_360`/`mart.san_pham_360` NHIỀU LẦN cho một lần mở trang. Đo
thật trên CSDL thật (2026-09-23, chỉ đọc): một mình
`SELECT trang_thai, count(*) FROM mart.khach_360 GROUP BY 1` mất **~1.185
ms** — view đó bị dựng lại hoàn toàn, không phải một chỉ mục tra thẳng. Trước
vòng sửa này `/` gọi nó (qua `count(*)` riêng) rồi gọi lại LẦN NỮA (qua
`can_xu_ly()`) cho cùng một lần mở trang, cộng thêm `kho_hang()` — vốn vật
hoá `mart.san_pham_360` (view NẶNG NHẤT của mart, kéo theo
`mart.ty_suat_mat_hang` và hai lượt quét `fact_sales_line`) HAI LẦN — chỉ để
lấy 5 dòng "hàng cận hạn" và một con số đếm quá hạn. Cộng dồn, trang chắc
chắn vượt ngưỡng 1.500 ms của đặc tả §8.
Sửa bằng hai hàm RIÊNG cho dashboard, không phải bằng một tham số điều kiện
trên hai hàm cũ (thứ sẽ làm `kho_hang()`/`can_xu_ly()` phình ra để phục vụ
một người gọi khác hẳn về hình dạng):
- `kome.khach_hang.dem_va_can_xu_ly()` — MỘT câu lệnh, CTE `k AS MATERIALIZED`
  vật hoá `mart.khach_360` đúng MỘT LẦN, nhánh `d` đếm trên đó (không lọc
  `sale` — dashboard cần số TOÀN CÔNG TY), nhánh `c` lọc lấy danh sách (CÓ
  lọc `sale`, giống `can_xu_ly()`).
- `kome.san_pham.lo_can_han()` — MỘT câu lệnh trên `mart.ton_hien_tai`
  (KHÔNG đụng `san_pham_360`); tên hàng tái tạo công thức
  `san_pham_360.ten_hang` bằng `LEFT JOIN core.dim_product` thay vì vật hoá
  cả view chỉ để lấy đúng một cột.
Cả hai dùng chung HẰNG với hàm gốc (`kome.khach_hang.TRANG_THAI_CAN_XU_LY`,
`kome.san_pham.VI_TU_CAN_HAN`/`VI_TU_QUA_HAN`) — MỘT định nghĩa "cần xử lý"/
"cận hạn", không phải hai bản chép sẽ trôi khỏi nhau. `kho_hang()`/
`can_xu_ly()` vẫn còn nguyên (`kho_hang()` cho `/kho-hang`; `can_xu_ly()` là đối
chứng của test và định nghĩa gốc, dù `/can-xu-ly` từ đợt 7 chỉ còn 301) — mỗi màn đó
CẦN đủ mọi cột/bộ lọc mà hàm gốc tương ứng cung cấp, và không đánh giá view
đắt hai lần cho MỘT lần mở CHÍNH MÀN CỦA NÓ. Có test canh:
`tests/test_khach_hang.py::test_dem_va_can_xu_ly_dem_TOAN_CONG_TY_danh_sach_theo_sale`,
`::test_dem_va_can_xu_ly_giong_HET_can_xu_ly_rieng`,
`tests/test_san_pham.py::test_lo_can_han_khop_kho_hang_khong_dung_san_pham_360`,
`tests/test_tong_quan.py::test_trang_chu_dung_khach_360_MOT_lan_khong_dung_san_pham_360`.

**Bất biến:** ngân sách truy vấn: `/bao-cao` ≤ **11** truy vấn, `/` ≤ **9**
truy vấn (đếm cả các câu ở tầng route như `tinh_tuoi`; siết từ 11 xuống 9 ở
soát hiệu năng đợt 5b — xem bất biến ngay trên). [Vòng soát cuối, M8]
`_sale_dang_loc` KHÔNG chạy câu SQL nào — nó chỉ đọc `request.state.nguoi`
(đã gắn sẵn bởi middleware) và tham số `nv`/`tat_ca` trên URL, không mở kết
nối — nên không tính vào ngân sách này; dòng trước đây liệt nó cùng
`tinh_tuoi` (thứ CÓ chạy SQL) là sai. Ngân
sách đo **số lượt hỏi**, không đo sức tính — cùng lý lẽ đã ghi cho `/khach-hang`
ở trên. Ở `/bao-cao`, ngành × tháng (`mart.ban_theo_nganh_thang_so_sanh`) và
ngành × kỳ (`mart.nganh_ky_cung_ky`) KHÔNG được gộp vào một câu: câu gộp sẽ
tham chiếu `ban_theo_nganh_thang_so_sanh` hai lần (một lần trực tiếp, một lần
qua `nganh_ky_cung_ky` — view sau ĐỌC view trước), tức đánh giá lại view đó hai
lần, đúng lớp lỗi của bất biến CTE-trùng đã ghi ở trên. Có test đếm:
`tests/test_bao_cao_phan_tich.py::test_bao_cao_khong_qua_11_truy_van`,
`tests/test_tong_quan.py::test_trang_chu_khong_qua_9_truy_van`.

## Hai bản chạy của web app
| | Máy trong công ty | Vercel (công khai) |
|---|---|---|
| Nạp / Hoàn tác | có (mọi cỡ file) | có — file ≤ 4 MB (hằng ngày); file chờ trong `meta.nap_cho`, **không** lưu file gốc (045) |
| Đăng nhập | tài khoản riêng (bật khi có `KOME_SESSION_SECRET`) | **bắt buộc** (`KOME_SESSION_SECRET`) |
| Cổng CSDL | 5432 (session pooler) | **6543** (transaction pooler) |
| Gói cài | `pip install -e .` | `requirements.txt` (có pandas từ 045) |
| Điểm vào | `uvicorn kome.web.app:app` | `server.py` ở gốc (Vercel tự tìm) |

Chế độ chỉ-đọc do `KOME_CHI_DOC=1` quyết định (`kome/web/app.py::_chi_doc`), hoặc tự
bật khi không có kết nối nạp (`DATABASE_URL`). Trước 045 nó LUÔN bật trên Vercel; nay
bản Vercel nạp được file hằng ngày — xem bất biến 045. Giới hạn nền tảng vẫn còn: mỗi
yêu cầu **4,5 MB** (`売上伝票データ` cả quý 63–106 MB), ổ đĩa tạm, giới hạn thời gian
chạy — nên đối soát tháng vẫn ở máy công ty.

**Bất biến:** `kome/web/app.py` KHÔNG được nhập `kome.pipeline` (hay pandas,
python-calamine) ở mức ngoài cùng — chỉ nhập bên trong thân route. `ingest`/
`undo_batch` kéo theo ~120 MB; nhập ở đầu file là MỌI trang đọc (và mỗi lần khởi động
nguội trên Vercel) trả giá cho thứ chỉ luồng nạp cần. Từ 045 `requirements.txt` CÓ
pandas, nên lỗi này không còn làm trang chết — nó chỉ làm mọi trang chậm đi. Có test canh:
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
`/khach-hang` hay `/lien-he`.

**Bất biến (màn 20/21, migration 033):** Nhật ký thao tác KHÔNG có bảng gom
riêng — nó đọc gộp các sổ đã có (`kome/nhat_ky.py::_NGUON`). Thêm một loại thao
tác mới là thêm MỘT nhánh vào khối UNION đó, không phải chép sự kiện sang bảng
thứ hai (hai sổ sẽ lệch nhau đúng ngày một đường ghi quên sổ kia). Ba cờ quyền
(`duoc_vao_kho_du_lieu`, `duoc_sua_ngan_sach`, `duoc_quan_tri`) đổi qua đúng MỘT
hàm — `nguoi_dung.dat_quyen` — và hàm đó ghi `app.nhat_ky_quyen` trong cùng giao
dịch, cả khi gọi từ script (`sua_boi` NULL). `app.nhat_ky_quyen` chỉ thêm (CSDL
chặn UPDATE/DELETE với `kome_app`). Màn Cài đặt từ chối đổi quyền khi máy CHƯA có
`KOME_SESSION_SECRET` (không biết ai đang đổi, và cờ chưa bảo vệ gì), và từ chối
người tự bỏ cờ quản trị của chính mình (bấm nhầm một ô là không còn ai đổi được
quyền trên web). Tạo tài khoản và mật khẩu vẫn CHỈ qua script. `_ghi_ai` (ghi
`nap_boi`/`huy_boi`) chạy SAU khi nạp/hoàn tác đã commit và nuốt lỗi — luồng 13:30
không được hỏng vì không ghi được tên người bấm. Có test canh:
`tests/test_nhat_ky.py`.

**CẠM BẪY — cổng chỉ tồn tại khi có khoá ký.** Để trống `KOME_SESSION_SECRET`
ở máy trong công ty là **không có đăng nhập và không có phân quyền**: ai mở
được trang cũng bấm được nút Hoàn tác — nút xoá được cả một tháng doanh thu.
Bản Vercel không dính (nó từ chối khởi động nếu thiếu khoá — từ 045 nó cũng nạp và
hoàn tác được, luôn sau cổng đăng nhập). Nói cách khác: **hai cờ quyền
(`duoc_vao_kho_du_lieu` và `duoc_sua_ngan_sach`) chỉ bảo vệ được nút Hoàn tác
và màn Ngân sách khi máy trong công ty CŨNG đặt `KOME_SESSION_SECRET`.**

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
