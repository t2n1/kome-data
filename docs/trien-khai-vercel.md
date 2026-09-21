# Đưa trang lên mạng bằng Vercel

Mục tiêu: có một địa chỉ kiểu `kome-data.vercel.app` để bạn và ban giám đốc mở
được từ bất cứ đâu, sau khi nhập mật khẩu chung của công ty.

---

## 1. Vì sao chỉ đưa phần XEM lên, không đưa phần NẠP

Không phải lựa chọn cho gọn. Đây là ba giới hạn cứng của Vercel:

| Giới hạn của Vercel | Số thật của KOME | Kết quả |
|---|---|---|
| Mỗi yêu cầu tối đa **4,5 MB** | file `売上伝票データ` nặng **~100 MB** | gấp **22 lần** — trả lỗi `413` |
| Ổ đĩa của hàm là **tạm**, ghi xong mất | hệ thống phải giữ **nguyên file Excel gốc** (lớp `raw`) | không giữ được |
| Hàm có **giới hạn thời gian chạy** | nạp một quý bán hàng mất **~88 giây** | đứt giữa chừng |

Vì vậy bản trên Vercel **luôn ở chế độ chỉ đọc**, do chính biến `VERCEL` của
Vercel quyết định (`kome/web/app.py::_chi_doc`). Không có công tắc nào bật lại
được — một nút nạp luôn hỏng còn tệ hơn không có nút nào.

**Nạp dữ liệu vẫn làm ở máy trong công ty như hiện nay**, xem `docs/runbook.md`.

---

## 2. Chuẩn bị 3 thứ trước khi bấm

### a) Mật khẩu chung

Nghĩ một mật khẩu **ít nhất 12 ký tự**. Trang sẽ từ chối khởi động nếu ngắn
hơn: mỗi lần gọi trên Vercel là một tiến trình riêng nên không đếm chung được
số lần đoán sai, độ dài mật khẩu chính là lớp bảo vệ duy nhất.

Gợi ý: ghép 4 từ tiếng Việt không dấu, ví dụ `bancom-muagao-thang-tam`.

**Đừng dùng lại mật khẩu OBC, Supabase hay email.**

### b) Chuỗi kết nối CSDL — dùng **cổng 6543**, không phải 5432

**Cách nhanh nhất, không cần vào Supabase:** mở file `.env` trong
`C:\Antigravity\kome-data` bằng Notepad, chép dòng `DATABASE_URL=...`, rồi
**đổi đúng một chỗ: `:5432` thành `:6543`**. Giữ nguyên mọi thứ khác.

Đã kiểm chứng ngày 2026-09-16 rằng chuỗi đổi kiểu này chạy đúng: hai cổng dùng
chung một máy chủ và một tên đăng nhập, chỉ khác cách giữ kết nối.

(Nếu muốn lấy từ nguồn: Supabase → **Connect** → **Transaction pooler**.)

Vì sao khác với máy ở công ty (cổng 5432):

- **5432** giữ nguyên một kết nối suốt phiên — hợp với việc nạp dữ liệu và
  chạy migration ở máy công ty.
- **6543** trả kết nối lại sau mỗi giao dịch — hợp với Vercel, nơi mỗi lần có
  người mở trang là một tiến trình mới.

Dùng sai cổng thì trang hỏng, và hỏng theo kiểu khó đoán nhất: **thử ở máy
mình thì êm, lên Vercel là lỗi ngay từ lượt xem thứ hai**. `kome/db.py` tự tắt
câu lệnh chuẩn bị sẵn khi thấy cổng `6543` — đã đo thật, xem ghi chú trong file.

### c) Tài khoản dùng riêng cho trang web (nên làm)

Hiện `DATABASE_URL` dùng `kome_ingest_user` — vai trò **ghi được** vào `core`.
Bản trên Vercel không cần quyền ghi. Nếu tạo được một người dùng chỉ đọc thì
dù trang bị chiếm cũng không ai xoá được dữ liệu. Lưu ý vai trò `kome_report`
hiện **không có** quyền đọc `meta.ingest_batch` nên chưa chạy được `/kho-du-lieu` —
việc này để lại cho Giai đoạn 1.

---

## 3. Các bước bấm

1. Vào <https://vercel.com>, đăng nhập **bằng chính tài khoản GitHub** đang
   giữ repo `t2n1/kome-data`.
2. **Add New… → Project** → chọn `kome-data` → **Import**.
3. Ở màn hình cấu hình, mục **Environment Variables**, thêm đúng hai biến:

   | Name | Value |
   |---|---|
   | `DATABASE_URL` | chuỗi kết nối **cổng 6543** ở mục 2b |
   | `KOME_MAT_KHAU` | mật khẩu ở mục 2a |

4. **Deploy**. Chờ khoảng 1–2 phút.
5. Mở địa chỉ Vercel đưa ra. Phải thấy trang đăng nhập 🔒.

Không phải khai báo gì thêm: Vercel nhận ra đây là ứng dụng FastAPI nhờ
`requirements.txt`, rồi nạp biến `app` trong file `server.py` ở gốc dự án.
**Đừng đổi tên `server.py`** — đổi là mọi đường dẫn trả về 404, trông y hệt
như code hỏng.

Từ đây, **mỗi lần đẩy code lên nhánh chính là Vercel tự triển khai lại** —
không phải bấm gì nữa.

---

## 4. Kiểm lại sau khi triển khai (làm một lần, đừng bỏ)

Mở địa chỉ Vercel bằng **cửa sổ ẩn danh** (Ctrl+Shift+N) rồi soát:

- [ ] Vào thẳng `/kho-du-lieu` khi chưa đăng nhập → bị đẩy về trang đăng nhập.
- [ ] Nhập mật khẩu sai → báo "Mật khẩu không đúng", **không** vào được.
- [ ] Nhập đúng → thấy bảng sức khoẻ dữ liệu.
- [ ] Mở `/kho-du-lieu` → **không** thấy ô kéo–thả file, và **không** thấy nút
      **Hoàn tác** nào trong bảng "Lô nạp gần nhất". (Đây là cổng kiểm TAY duy
      nhất cho bất biến chỉ-đọc. Ô kiểm cũ soát mục menu "Nạp dữ liệu" — mục
      đó nay đã biến mất khỏi **cả hai** bản, nên ô kiểm ấy xanh kể cả khi bất
      biến vỡ hoàn toàn.)
- [ ] Không có dải đỏ "Chưa sao lưu" (sao lưu chạy ở máy công ty, trang này
      không nhìn thấy nên cố ý im lặng).
- [ ] Bấm **Thoát** → quay về trang đăng nhập.

---

## 5. Việc phải làm định kỳ

- **Đổi `KOME_MAT_KHAU` mỗi khi có người nghỉ việc.** Đổi xong, mọi vé đăng
  nhập đang lưu hành hết hiệu lực ngay — không có kho phiên ở máy chủ, nên đây
  là cách duy nhất "đuổi" một người đã biết mật khẩu cũ.
  Vào Vercel → Settings → Environment Variables → sửa → **Redeploy**.
- Vé đăng nhập tự hết hạn sau **12 giờ**, nên máy để quên ở văn phòng không
  mở được vào sáng hôm sau.

---

## 6. Khi cần đưa cả phần NẠP lên mạng

Chỉ có một đường: **một máy chủ thật** (VPS Vultr sẵn có, hoặc một máy trong
công ty mở cổng ra ngoài) — nơi có ổ đĩa thật để giữ lớp `raw` và không bị
chặn ở 4,5 MB. Lúc đó bỏ biến `VERCEL`/`KOME_CHI_DOC` là phần nạp tự hiện lại;
mã nguồn không phải đổi dòng nào.

**Đừng** đặt nó lên VPS đang chạy WordPress (`139.180.206.125`) hay
`sale1.komejapan.com` — hai máy đó đang phục vụ khách hàng thật.

---

## 7. Thư mục tĩnh (`static/`) đi cùng nhánh giao diện mới

Nhánh đưa app sang bảng màu/font mới thêm một thư mục tĩnh thật:
`kome/web/static/kome.css` và 7 file font `.woff2`. Ba điều cần biết trước
khi triển khai:

- Bản Vercel phục vụ `/static/kome.css` và các file font qua chính
  `StaticFiles` mount **trong `app.py`** (FastAPI), **không** qua tầng tĩnh
  riêng của Vercel. `.vercelignore` **không được** loại `kome/web/static/` —
  loại mất là toàn bộ giao diện vỡ ngay, không phải một tính năng nhỏ mất đi.

- **Bẫy triệu chứng đánh lừa:** nếu thư mục `static` không lên được máy chủ
  (ví dụ do `.vercelignore` loại nhầm), `StaticFiles(directory=…)` ném lỗi
  **ngay lúc dựng app** — nên **mọi** đường dẫn, kể cả `/dang-nhap`, đều trả
  về **500**. Trông y hệt code Python hỏng, không hề giống một file tĩnh bị
  thiếu; đừng mất thời gian soát logic route trước khi soát `.vercelignore`.

- **Bẫy im lặng:** nếu chỉ riêng file **font** 404 (ví dụ quên add vào git),
  `font-display:swap` trong `kome.css` lặng lẽ rơi về font hệ thống. Trang
  vẫn trả **200**, giao diện vẫn "chạy được", không test tự động nào biết —
  test font chỉ soát file trong repo, không soát việc file đó có LÊN được
  máy chủ hay không. Sau **mỗi lần triển khai**, tự mở
  `https://<deploy>/static/fonts/IBMPlexSans-Regular.woff2` bằng tay xem có
  trả về 200 không.

- Cổng đăng nhập (`kome/web/app.py`, middleware `chan_cua`) **miễn trừ
  `/static/` có chủ ý**, cùng với `/dang-nhap`. Trang đăng nhập là màn hình
  ĐẦU TIÊN của bản Vercel — nơi `KOME_MAT_KHAU` luôn bắt buộc — và nó cần
  chính `/static/kome.css` cùng các file font để hiển thị có kiểu dáng
  *trước khi* ai đăng nhập được. Nếu sau này có người "siết lại" cổng đăng
  nhập và bỏ miễn trừ này, `/dang-nhap` của bản công khai sẽ hiện trơ trụi,
  không CSS không font — có test canh:
  `tests/test_bao_mat.py::test_static_khong_bi_chan_boi_cong_dang_nhap`.

---

## Nguồn

- [Vercel Functions Limits](https://vercel.com/docs/functions/limitations)
- [Bypass the 4.5 MB body size limit](https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions)
- [Supabase — Connecting to your database](https://supabase.com/docs/guides/database/connecting-to-postgres)
