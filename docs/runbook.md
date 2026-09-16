# Runbook — quy trình khi hỏng

Dành cho người **không rành kỹ thuật**. Mỗi dòng dưới đây là một sự cố có thể
gặp và **lệnh chép–dán được** để xử lý. Nếu làm theo mà vẫn không hết lỗi,
chụp lại toàn bộ màn hình (kể cả dòng lỗi màu đỏ) và gửi cho người phụ trách
kỹ thuật (AI bảo trì / đơn vị hỗ trợ) — đừng thử thêm cách khác.

**Chuẩn bị chung cho mọi lệnh bên dưới** (mở Git Bash tại thư mục dự án
`C:\Antigravity\kome-data`, chạy một lần đầu mỗi phiên làm việc):

```bash
cd /c/Antigravity/kome-data
set -a; source .env; set +a
```

---

| Sự cố | Dấu hiệu nhận biết | Cách xử lý (chép–dán từng khối, theo thứ tự) | Thời gian |
|---|---|---|---|
| **Nạp nhầm file** (nhầm ngày, nhầm file, nạp trùng) | Vào trang `/health` thấy số dòng hoặc tổng tiền sai ngay sau khi vừa nạp | 1) Tìm lần nạp vừa rồi:<br>`python -c "from kome.db import connect; [print(r) for r in connect().execute(\"SELECT batch_id, spec_name, source_file, loaded_at FROM meta.ingest_batch WHERE undone_at IS NULL ORDER BY loaded_at DESC LIMIT 5\").fetchall()]"`<br>2) Ghi lại `batch_id` của lần nạp sai, rồi hoàn tác (thay `123` bằng số đó):<br>`python -c "from kome.db import connect; from kome.pipeline import undo_batch; c = connect(); undo_batch(c, 123); print('da hoan tac')"`<br>3) Nạp lại đúng file qua trang nội bộ như bình thường | ~10 giây tìm + hoàn tác |
| **OBC đổi tên cột** (nạp file báo lỗi "thiếu cột" / cổng 2 chặn) | Trang nạp báo đỏ, nêu rõ tên cột thiếu | 1) Mở file cấu hình bằng Notepad, ví dụ:<br>`notepad config/files.yml`<br>2) Sửa tên cột OBC mới cho khớp cột hệ thống đang có (không đổi tên cột hệ thống, chỉ đổi tên cột OBC bên trái dấu `:`), lưu lại<br>3) Chạy lại toàn bộ kiểm tra để chắc chắn không hỏng gì khác:<br>`python -m pytest tests/ -v`<br>4) Nếu không chắc sửa đúng chỗ, đừng tự sửa — gửi ảnh chụp lỗi kèm file Excel mới cho AI bảo trì | ~5 phút (tự sửa) |
| **Số không khớp OBC** (báo cáo trong app lệch số so với sổ OBC) | Đối chiếu cuối tháng thấy tổng tiền lệch | Không cần xoá gì cả — xuất lại **đúng file đó** (cả kỳ, không xuất riêng phần lệch) từ OBC rồi kéo–thả lại vào trang nội bộ. Hệ thống tự nhận theo mã băm nội dung: file y hệt cũ → tự bỏ qua; file có sửa → tự ghi đè đúng dòng thay đổi | ~2 phút |
| **CSDL đầy 500 MB** (Supabase báo "storage full", trang nạp báo lỗi ghi dữ liệu) | Nạp file báo lỗi kết nối/ghi dữ liệu, hoặc email cảnh báo từ Supabase | 1) Đăng nhập https://supabase.com/dashboard bằng tài khoản công ty<br>2) Chọn dự án KOME → **Settings → Billing** → nâng cấp lên gói trả phí<br>**Không tự ý xoá dữ liệu để giải phóng chỗ** — dữ liệu kế toán không được xoá | ~5 phút (cần thẻ thanh toán công ty) |
| **Mất sạch CSDL** (Supabase báo dự án bị xoá/hỏng, hoặc không kết nối được nữa) | Mọi trang trong app đều báo lỗi kết nối CSDL | 1) Tạo CSDL Postgres mới trên Supabase (chọn **Session Pooler**, IPv4, cổng **5432** — không dùng cổng 6543), lấy chuỗi kết nối mới<br>2) Dựng lại cấu trúc bảng trên CSDL mới:<br>`python -c "from kome.db import connect; from db.migrate import apply_all; from pathlib import Path; [print(x) for x in apply_all(connect('<CHUOI_KET_NOI_MOI>'), Path('db/migrations'))]"`<br>3) Nếu có bản sao lưu gần nhất trong thư mục `backups/` (hoặc trên OneDrive), đổ dữ liệu vào CSDL mới đó — **luôn dùng chuỗi kết nối MỚI**, không phải `DATABASE_URL` cũ:<br>`python -c "from ops.restore_check import restore; print(restore('backups/kome_YYYYMMDD.zip', '<CHUOI_KET_NOI_MOI>'))"`<br>(đổi `kome_YYYYMMDD.zip` thành tên file sao lưu mới nhất, xem trong thư mục `backups/`)<br>4) Kiểm tra kết quả `restore()` in ra khớp số dòng kỳ vọng, rồi mới cập nhật `DATABASE_URL` trong `.env` thành chuỗi kết nối mới<br>5) Nếu **không có** bản sao lưu nào, nạp lại từ đầu bằng toàn bộ file Excel gốc đã lưu trên OneDrive, theo đúng thứ tự ngày, qua trang nội bộ như nạp bình thường | ~1 giờ (có sao lưu) |
| **Web app không truy cập được** (trang nạp/health không mở được) | Trình duyệt báo không kết nối được tới trang nội bộ | **Không làm gì với việc nạp dữ liệu** — việc xuất file từ OBC và lưu trên OneDrive vẫn diễn ra bình thường, không phụ thuộc web app. Báo cho AI bảo trì để khởi động lại máy chủ web; công việc kế toán không bị gián đoạn | — |

---

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
python -c "from ops.backup import dump, prune; import os, pathlib; dump(os.environ['DATABASE_URL'], pathlib.Path('backups')); prune(pathlib.Path('backups'))"
```

File sao lưu nằm trong thư mục `backups/` (không đưa vào git — xem
`.gitignore`). Chép thư mục này lên OneDrive định kỳ để có bản sao ở nơi
khác.

**Trang `/health` tự cảnh báo nếu quên sao lưu**: nếu bản sao lưu mới nhất
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
schtasks /create /sc daily /st 19:00 /tn KomeBackup /tr "cmd /c cd /d C:\Antigravity\kome-data && python -c \"from ops.backup import dump, prune; import os, pathlib; dump(os.environ['DATABASE_URL'], pathlib.Path('backups')); prune(pathlib.Path('backups'))\""
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
chính là lý do dải cảnh báo trên trang `/health` (ở trên) vẫn cần thiết dù
đã bật lịch tự động: mở trang mỗi ngày là cách duy nhất để biết chắc sao lưu
có thật sự chạy hay không.

**Mỗi quý phải thử khôi phục một lần** vào CSDL thử nghiệm (`DATABASE_URL_TEST`),
không bao giờ vào CSDL thật:

```bash
python -c "from ops.restore_check import verify; import os, pathlib; print(verify(sorted(pathlib.Path('backups').glob('*.zip'))[-1], os.environ['DATABASE_URL_TEST']))"
```

Kết quả phải là `{'ok': True, 'mismatches': {}, ...}`. Một bản sao lưu chưa
từng được thử khôi phục thì không phải bản sao lưu.
