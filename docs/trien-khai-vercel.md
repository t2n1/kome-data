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

Vào Supabase → **Connect** → **Transaction pooler**, chép chuỗi có dạng:

```
postgresql://postgres.<mã-dự-án>:<mật-khẩu>@aws-0-ap-northeast-1.pooler.supabase.com:6543/postgres
```

Vì sao khác với máy ở công ty (cổng 5432):

- **5432** giữ nguyên một kết nối suốt phiên — hợp với việc nạp dữ liệu và
  chạy migration ở máy công ty.
- **6543** trả kết nối lại sau mỗi giao dịch — hợp với Vercel, nơi mỗi lần có
  người mở trang là một tiến trình mới.

Dùng 5432 cho Vercel thì sau vài chục lượt xem sẽ hết chỗ kết nối và trang
báo lỗi. `kome/db.py` tự tắt câu lệnh chuẩn bị sẵn khi thấy cổng `6543`.

### c) Tài khoản dùng riêng cho trang web (nên làm)

Hiện `DATABASE_URL` dùng `kome_ingest_user` — vai trò **ghi được** vào `core`.
Bản trên Vercel không cần quyền ghi. Nếu tạo được một người dùng chỉ đọc thì
dù trang bị chiếm cũng không ai xoá được dữ liệu. Lưu ý vai trò `kome_report`
hiện **không có** quyền đọc `meta.ingest_batch` nên chưa chạy được `/health` —
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

- [ ] Vào thẳng `/health` khi chưa đăng nhập → bị đẩy về trang đăng nhập.
- [ ] Nhập mật khẩu sai → báo "Mật khẩu không đúng", **không** vào được.
- [ ] Nhập đúng → thấy bảng sức khoẻ dữ liệu.
- [ ] Thanh menu **không** có mục "📥 Nạp dữ liệu".
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

## Nguồn

- [Vercel Functions Limits](https://vercel.com/docs/functions/limitations)
- [Bypass the 4.5 MB body size limit](https://vercel.com/kb/guide/how-to-bypass-vercel-body-size-limit-serverless-functions)
- [Supabase — Connecting to your database](https://supabase.com/docs/guides/database/connecting-to-postgres)
