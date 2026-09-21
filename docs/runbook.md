# Runbook — quy trình khi hỏng

Dành cho người **không rành kỹ thuật**. Mỗi dòng dưới đây là một sự cố có thể
gặp và **lệnh chép–dán được** để xử lý. Nếu làm theo mà vẫn không hết lỗi,
chụp lại toàn bộ màn hình (kể cả dòng lỗi màu đỏ) và gửi cho người phụ trách
kỹ thuật (AI bảo trì / đơn vị hỗ trợ) — đừng thử thêm cách khác.

**Chuẩn bị chung cho mọi lệnh bên dưới** — chỉ một dòng, và chạy được ở **cả
PowerShell lẫn Git Bash**:

```bash
cd C:\Antigravity\kome-data
```

Không cần nạp biến môi trường, không cần dán chuỗi kết nối vào đâu cả: mọi
lệnh dưới đây **tự đọc file `.env`**. Mỗi lệnh đều có thêm tuỳ chọn `--test`
để chạy thử trên cơ sở dữ liệu thử nghiệm trước khi làm thật.

---

## Mở trang web ở máy trong công ty

```bash
python -m uvicorn kome.web.app:app --host 127.0.0.1 --port 8000
```

Rồi mở trình duyệt vào <http://127.0.0.1:8000>. Trang kéo–thả file nằm ở
mục **Kho dữ liệu** (<http://127.0.0.1:8000/kho-du-lieu>). Lệnh này **tự đọc `.env`** nên
không cần nạp biến môi trường trước. Cứ để cửa sổ đó mở; đóng cửa sổ là trang
tắt.

Nạp dữ liệu, sức khoẻ dữ liệu và bảng phủ dữ liệu nay nằm chung trong **một
màn Kho dữ liệu duy nhất** (những địa chỉ cũ tự chuyển hướng sang đó). Bản trên
mạng (Vercel) mở **cùng màn này**, chỉ ẩn hai khối: ô kéo–thả file và nút
**Hoàn tác** — xem [docs/trien-khai-vercel.md](trien-khai-vercel.md) để biết vì
sao và cách đưa lên.

---

## Trang trên mạng báo lỗi, hoặc không ai đăng nhập được

| Hiện tượng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| Trang không mở, Vercel báo lỗi khởi động | Thiếu `KOME_SESSION_SECRET`, hoặc chuỗi ngắn dưới 12 ký tự | Vercel → Settings → Environment Variables → sửa → **Redeploy** |
| Mở được một lúc rồi báo lỗi đỏ | `DATABASE_URL` đang dùng **cổng 5432** thay vì **6543** | Đổi sang chuỗi Transaction pooler (cổng 6543) → Redeploy |
| Cần chặn một người đã nghỉ việc | Tài khoản của họ vẫn còn | Xoá tài khoản: họ bị chặn ở **lượt bấm kế tiếp**, không cần chờ hết phiên. Nghi lộ khoá ký thì đổi `KOME_SESSION_SECRET` → **mọi người** phải đăng nhập lại |

Trang trên mạng **không nạp dữ liệu được** và điều đó là cố ý, không phải hỏng:
mỗi lần gửi bị Vercel chặn ở 4,5 MB còn một file `売上伝票データ` nặng khoảng
100 MB. Nạp dữ liệu vẫn làm ở máy trong công ty như thường lệ.

---

## Tài khoản đăng nhập

    python scripts/tao_nguoi_dung.py                      xem danh sách
    python scripts/tao_nguoi_dung.py them an --sale 0104
    python scripts/tao_nguoi_dung.py them minh --kho-du-lieu
    python scripts/tao_nguoi_dung.py doi-mat-khau an
    python scripts/tao_nguoi_dung.py quyen an --kho-du-lieu
    python scripts/tao_nguoi_dung.py quyen an --bo-kho-du-lieu

`--sale <mã>` gắn tài khoản với một trong 5 người phụ trách của OBC
(`core.dim_salesperson`) — trang khách hàng khi đó mặc định chỉ hiện khách của
họ. Bỏ `--sale` cho người không phụ trách khách nào (chủ DN, kế toán, kho): họ
thấy toàn bộ.

`--kho-du-lieu` mở màn Kho dữ liệu, tức **nạp file VÀ hoàn tác một lần nạp**.
Hoàn tác nhầm lô đối soát tháng sẽ xoá cả một tháng doanh thu khỏi kho. Chỉ
cấp cho người phụ trách nạp và chủ doanh nghiệp.

**Phải đặt `KOME_SESSION_SECRET` trong `.env` của máy trong công ty.** Để
trống thì trang chạy KHÔNG có đăng nhập và KHÔNG có phân quyền — ai mở được
trang cũng bấm được nút Hoàn tác. Đây cũng đúng là máy DUY NHẤT nạp và hoàn
tác được, nên để trống là vô hiệu hoá toàn bộ phần bảo vệ của đợt 3.

Quên mật khẩu: không có luồng tự phục hồi (cố ý — 5–7 người, một luồng khôi
phục qua email là thêm một cửa để tấn công). Người quản trị đặt lại bằng
`doi-mat-khau`.

---

## Tạo tài khoản đăng nhập cho từng vai trò

Migration `db/migrations/009_roles.sql` chỉ tạo 4 **vai trò** (`kome_ingest`,
`kome_app`, `kome_report`, và vai trò cấp quyền tương ứng) — không có mật
khẩu, không đăng nhập được (`NOLOGIN`). Đây là chủ ý: mật khẩu **không bao
giờ** được đặt trong file migration hay bất kỳ file nào đưa vào git.

Muốn tài khoản đăng nhập thật (ví dụ để ứng dụng nạp dữ liệu hoặc trang web
kết nối), làm **tay một lần** trên **SQL Editor của Supabase** (không chạy
qua migration, không chạy qua psql với `.env`):

```sql
CREATE USER kome_ingest_user LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_ingest;
CREATE USER kome_app_user    LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_app;
CREATE USER kome_report_user LOGIN PASSWORD '<mật khẩu mạnh>' IN ROLE kome_report;
```

Lưu ý:

- Đặt mật khẩu mạnh (sinh ngẫu nhiên, không tái dùng từ nơi khác). Mật khẩu
  chỉ tồn tại trong bảng điều khiển Supabase và trong biến môi trường của
  máy chạy ứng dụng — **không bao giờ commit vào git, không dán vào chat,
  không ghi trong file nào của repo**.
- Sau khi tạo xong, đổi `DATABASE_URL` trong `.env` sang chuỗi kết nối dùng
  `kome_ingest_user` (vai trò ghi được vào `core`/`meta`) cho việc nạp dữ
  liệu hằng ngày. Tài khoản `postgres` (superuser hiện tại) **chỉ dùng khi
  chạy migration** (`python -m db.migrate` hoặc tương đương), không dùng cho
  vận hành thường ngày.
- **Web app của Giai đoạn 0 chạy bằng `kome_ingest_user`** — chính là
  `DATABASE_URL` ở trên. Trang **Kho dữ liệu** (nạp, sức khoẻ, hoàn tác) đều
  cần ghi và xoá trong `core`, nên không dùng `kome_app_user` được.
- `kome_app_user` **chưa dùng ở Giai đoạn 0** — dành cho ứng dụng CRM ở Giai
  đoạn 2 (đọc `core`/`mart`, đọc-ghi `app` — **không ghi được vào `core`**, kể
  cả khi có bug trong code). Nó cũng không đọc được `meta.ingest_batch` nên
  không mở được trang **Kho dữ liệu**. `kome_report_user` chỉ đọc, dùng cho công cụ
  báo cáo/BI bên ngoài nếu có.
- **Migration luôn chạy bằng `postgres`**, không bao giờ bằng `kome_ingest_user`:
  `ALTER DEFAULT PRIVILEGES` trong migration không có `FOR ROLE`, chạy bằng vai
  trò khác thì quyền mặc định cho bảng mới sẽ âm thầm không áp dụng.
- Muốn đổi mật khẩu sau này: `ALTER USER kome_app_user PASSWORD '<mật khẩu mới>';`
  chạy tay trên SQL Editor, rồi cập nhật biến môi trường tương ứng.

---

## Trước khi chạy migration trên CSDL THẬT — kiểm một câu

Chạy **trước mỗi lần** `python -m db.migrate` trên CSDL thật (chỉ mất vài
giây). Nếu bỏ qua, migration có thể **thất bại giữa chừng**: các file `.sql`
chạy lần lượt, file nào lỗi thì dừng ở đó, những file sau không chạy và CSDL
nằm lại ở trạng thái nửa vời.

**Lý do cụ thể:** `db/migrations/010_*.sql` thêm ràng buộc
`CHECK (valid_to IS NULL OR valid_to >= valid_from)` cho `core.dim_customer`.
Ràng buộc này được kiểm với **dữ liệu đang có**, nên nếu CSDL thật đã lỡ chứa
dòng vi phạm — do đúng cái lỗi cũ mà 010 sinh ra để chặn: xuất lại trong cùng
ngày thì phiên bản cũ bị đóng bằng `ngày hôm trước`, thành khoảng thời gian âm
— thì 010 sẽ **báo lỗi và không chạy được**.

Chạy:

```bash
python scripts/kiem_truoc_migration.py
```

- **Không in ra dòng nào** (thấy `OK: khong co dong nao vi pham`) → chạy
  migration như bình thường.
- **In ra một hoặc nhiều dòng** → **khoan chạy migration**, làm tiếp 3 bước
  dưới đây.

### Nếu có dòng vi phạm

**Bước 1 — sao lưu trước đã** (xem mục "Sao lưu hằng đêm" bên dưới; đừng bỏ
qua bước này, các bước sau có xoá dòng):

```bash
python -m ops.backup
```

**Bước 2 — xem từng dòng vi phạm đã có bản thay thế chưa.** Chính lệnh kiểm ở
trên đã in sẵn cột **"Đã có bản thay thế?"** cho từng dòng.

- Nếu có dòng nào **KHÔNG** → **dừng lại**, chụp màn hình gửi người phụ trách
  kỹ thuật. Dòng đó là phiên bản duy nhất của khách, không được đụng vào.

**Bước 3 — dọn các dòng chết.** Chỉ chạy khi bước 2 cho **CÓ** hết. Những dòng
này không có ngày nào đọc ra được và đều đã có bản thay thế, nên xoá đi không
mất thông tin nào đang dùng được — đây là ngoại lệ duy nhất của luật "không bao
giờ xoá dòng trong `core.dim_customer`", làm một lần khi vá lỗi cũ:

```bash
python scripts/kiem_truoc_migration.py --don
```

Chạy lại câu kiểm ở đầu mục này (phải ra `OK: khong co dong nao vi pham`), rồi
mới chạy migration.

---

| Sự cố | Dấu hiệu nhận biết | Cách xử lý (chép–dán từng khối, theo thứ tự) | Thời gian |
|---|---|---|---|
| **Nạp nhầm file** (nhầm ngày, nhầm file, nạp trùng) | Vào trang `/kho-du-lieu` thấy số dòng hoặc tổng tiền sai ngay sau khi vừa nạp | 1) Mở trang **Kho dữ liệu**, khối **Lô nạp gần nhất**<br>2) Tìm dòng của file vừa nạp nhầm, bấm **Hoàn tác**, đọc số dòng sẽ bị xoá rồi xác nhận<br>3) Nạp lại đúng file qua ô kéo–thả ngay trên màn đó<br>**Cách khác nếu web app không mở được:** xem hàng **Web app không truy cập được** bên dưới | ~10 giây tìm + hoàn tác |
| **Thiếu một ngày dữ liệu** (hôm đó không ai kéo–thả: nghỉ ốm, quên, máy hỏng) | Vào trang `/kho-du-lieu` thấy dải **vàng** `⚠️ Thiếu N ngày làm việc` kèm danh sách ngày | 1) Xem ngày bị liệt kê có phải ngày nghỉ lễ Nhật / công ty nghỉ không — nếu đúng thì bỏ qua, hệ thống chỉ biết thứ Bảy–Chủ nhật, không biết ngày lễ<br>2) Nếu là ngày làm việc thật: mở OBC, xuất lại `売上伝票データ` của **đúng ngày đó**, kéo–thả vào trang nạp như bình thường<br>3) Tải lại `/kho-du-lieu`, dải vàng phải biến mất | ~3 phút/ngày |
| **Thiếu cả một tháng / một loại file** (không phải một ngày lẻ) | Vào trang `/kho-du-lieu` thấy ô **đỏ** ở tháng đó — ô **xám** `—` là "ngoài phạm vi", không phải thiếu, đừng đi tìm | 1) Mở OBC, xuất lại loại file của đúng tháng đó, kéo–thả vào trang nạp<br>2) Tải lại `/kho-du-lieu`, ô phải chuyển **xanh**<br>3) Ô đỏ cũng có thể là file ĐÃ xuất nhưng bị cổng kiểm tra chặn (trang không phân biệt được) — nếu chắc đã nạp rồi mà vẫn đỏ, xuất lại và xem trang nạp báo cổng nào chặn | ~3 phút/tháng |
| **OBC đổi tên cột** (nạp file báo lỗi "thiếu cột" / cổng 2 chặn) | Trang nạp báo đỏ, nêu rõ tên cột thiếu | 1) Mở file cấu hình bằng Notepad, ví dụ:<br>`notepad config/files.yml`<br>2) Sửa tên cột OBC mới cho khớp cột hệ thống đang có (không đổi tên cột hệ thống, chỉ đổi tên cột OBC bên trái dấu `:`), lưu lại<br>3) Chạy lại toàn bộ kiểm tra để chắc chắn không hỏng gì khác:<br>`python -m pytest tests/ -v`<br>4) Nếu không chắc sửa đúng chỗ, đừng tự sửa — gửi ảnh chụp lỗi kèm file Excel mới cho AI bảo trì | ~5 phút (tự sửa) |
| **Số không khớp OBC** (báo cáo trong app lệch số so với sổ OBC) | Đối chiếu cuối tháng thấy tổng tiền lệch | Không cần xoá gì cả — xuất lại **đúng file đó** (cả kỳ, không xuất riêng phần lệch) từ OBC rồi kéo–thả lại vào trang nội bộ. Hệ thống tự nhận theo mã băm nội dung: file y hệt cũ → tự bỏ qua; file có sửa → tự ghi đè đúng dòng thay đổi | ~2 phút |
| **CSDL đầy 500 MB** (Supabase báo "storage full", trang nạp báo lỗi ghi dữ liệu) | Nạp file báo lỗi kết nối/ghi dữ liệu, hoặc email cảnh báo từ Supabase | 1) Đăng nhập https://supabase.com/dashboard bằng tài khoản công ty<br>2) Chọn dự án KOME → **Settings → Billing** → nâng cấp lên gói trả phí<br>**Không tự ý xoá dữ liệu để giải phóng chỗ** — dữ liệu kế toán không được xoá | ~5 phút (cần thẻ thanh toán công ty) |
| **Mất sạch CSDL** (Supabase báo dự án bị xoá/hỏng, hoặc không kết nối được nữa) | Mọi trang trong app đều báo lỗi kết nối CSDL | 1) Tạo CSDL Postgres mới trên Supabase (chọn **Session Pooler**, IPv4, cổng **5432** — không dùng cổng 6543), lấy chuỗi kết nối mới<br>2) **Sửa `DATABASE_URL` trong file `.env`** thành chuỗi kết nối mới — làm bước này TRƯỚC thì mọi lệnh sau chạy được như bình thường, không phải dán chuỗi vào đâu cả<br>3) Dựng lại cấu trúc bảng:<br>`python db/migrate.py`<br>4) Nếu có bản sao lưu trong `backups/`, đổ dữ liệu vào:<br>`python -m ops.restore_check` (kiểm tra khôi phục được trước), rồi khôi phục thật theo hướng dẫn cuối sổ tay<br>5) Nếu **không có** bản sao lưu nào, nạp lại từ đầu bằng toàn bộ file Excel gốc đã lưu trên OneDrive, theo đúng thứ tự ngày, qua trang nội bộ như nạp bình thường | ~1 giờ (có sao lưu) |
| **Web app không truy cập được** (trang Kho dữ liệu không mở được) | Trình duyệt báo không kết nối được tới trang nội bộ | **Không làm gì với việc nạp dữ liệu** — việc xuất file từ OBC và lưu trên OneDrive vẫn diễn ra bình thường, không phụ thuộc web app. Báo cho AI bảo trì để khởi động lại máy chủ web; công việc kế toán không bị gián đoạn<br>**Cần hoàn tác gấp một lô nạp sai ngay lúc này (không đợi được)?** Mở Git Bash hoặc PowerShell tại thư mục dự án, chạy trực tiếp trên máy — không cần trình duyệt:<br>`python scripts/hoan_tac.py` → xem các lô nạp gần nhất<br>`python scripts/hoan_tac.py 123` → hoàn tác lô số 123 | — |

---

## Nút Hoàn tác đưa được về đúng trạng thái cũ

Trường hợp hay gặp nhất với file khách hàng (`得意先全情報`): 13:30 nạp lần đầu,
kế toán phát hiện sai, sửa trong OBC, xuất lại và kéo–thả lại **trong cùng
ngày**, rồi nhận ra file thứ hai cũng sai và bấm **Hoàn tác**.

Lần nạp thứ hai trong cùng ngày **sửa đè lên dòng cũ** (không tạo thêm phiên
bản mới, vì hai phiên bản cùng bắt đầu một ngày sẽ làm hỏng lịch sử). Trước
khi đè, hệ thống **chép lại giá trị cũ** vào nhật ký của chính lần nạp đó, nên
Hoàn tác trả khách về **đúng giá trị của lần nạp thứ nhất** — khách không biến
mất, và cũng không kẹt lại giá trị sai của lần nạp thứ hai. Sửa đè nhiều lần
trong ngày thì hoàn tác lùi được **từng bước một**, theo đúng thứ tự ngược lại.

Với các lần nạp **khác ngày** thì như cũ: hoàn tác xoá phiên bản mới và mở lại
phiên bản trước đó.

## Vì sao không có bước "chép chuỗi kết nối CSDL thật vào lệnh restore"

Hàm `restore()` (trong `ops/restore_check.py`) **xoá sạch 4 schema**
(`core`, `mart`, `app`, `meta`) trước khi dựng lại — đây là hành động
**không thể hoàn tác**. Vì vậy `restore()` tự chặn và báo lỗi nếu URL truyền
vào trùng với `DATABASE_URL` (CSDL thật) đang cấu hình trong `.env`. Đó là
lý do quy trình "Mất sạch CSDL" ở trên luôn khôi phục vào một **CSDL mới**
trước, kiểm tra ổn rồi mới đổi `DATABASE_URL` trỏ sang CSDL đó — không bao
giờ gọi `restore()` thẳng vào `DATABASE_URL` hiện có.

## Sao lưu hằng đêm

Chạy hằng đêm (thủ công hoặc qua lịch hẹn giờ Windows), giữ 30 bản gần nhất
theo ngày + 12 bản cuối tháng (ngày lớn nhất trong tháng, khớp với chốt sổ):

```bash
python -m ops.backup
```

File sao lưu nằm trong thư mục `backups/` (không đưa vào git — xem
`.gitignore`). Chép thư mục này lên OneDrive định kỳ để có bản sao ở nơi
khác.

**Trang `/kho-du-lieu` tự cảnh báo nếu quên sao lưu**: nếu bản sao lưu mới nhất
cũ hơn 36 giờ (hoặc chưa có bản nào), đầu trang hiện dải đỏ
`⚠️ Chưa sao lưu ... — chạy sao lưu ngay` kèm sẵn lệnh ở trên để chép–dán.
Còn mới thì hiện dòng xanh `✅ Sao lưu gần nhất: ...`. Mở trang này mỗi ngày
là đủ để biết sao lưu có đang chạy thật hay không — không cần nhớ, không
cần dò log.

### Bật sao lưu tự động (khuyến nghị — chạy một lần)

Việc chạy tay mỗi đêm rất dễ quên. Windows có sẵn tiện ích **Task Scheduler**
để tự chạy lệnh sao lưu vào một giờ cố định, không cần cài thêm gì. Bật một
lần rồi thôi — không cần đụng lại trừ khi máy đổi vị trí thư mục dự án.

Mở **Git Bash** hoặc **PowerShell** tại thư mục dự án, chạy lệnh sau **một
lần duy nhất** (tạo tác vụ chạy mỗi ngày lúc 19:00 — sau giờ kế toán xuất
file 13:30 là an toàn, đổi `19:00` nếu muốn giờ khác):

```bash
schtasks /create /sc daily /st 19:00 /tn KomeBackup /tr "cmd /c cd /d C:\Antigravity\kome-data && python -m ops.backup"
```

Kiểm tra tác vụ đã tạo đúng chưa:

```bash
schtasks /query /tn KomeBackup
```

Muốn chạy thử ngay để xem có lỗi không (không cần đợi tới giờ hẹn):

```bash
schtasks /run /tn KomeBackup
```

Muốn tắt hẳn (ví dụ đổi cách sao lưu khác sau này):

```bash
schtasks /delete /tn KomeBackup /f
```

**Lưu ý quan trọng cho người không rành kỹ thuật:** Task Scheduler chỉ chạy
được khi **máy tính đang bật và không ở chế độ ngủ (sleep)** vào đúng giờ
hẹn — nó không tự đánh thức máy dậy để chạy. Nếu máy tắt hoặc ngủ lúc 19:00,
sao lưu hôm đó sẽ không chạy và không có gì báo cho biết ngay lúc đó. Đây
chính là lý do dải cảnh báo trên trang `/kho-du-lieu` (ở trên) vẫn cần thiết dù
đã bật lịch tự động: mở trang mỗi ngày là cách duy nhất để biết chắc sao lưu
có thật sự chạy hay không.

**Mỗi quý phải thử khôi phục một lần** vào CSDL thử nghiệm (`DATABASE_URL_TEST`),
không bao giờ vào CSDL thật:

```bash
python -m ops.restore_check
```

Kết quả phải là `{'ok': True, 'mismatches': {}, ...}`. Một bản sao lưu chưa
từng được thử khôi phục thì không phải bản sao lưu.
