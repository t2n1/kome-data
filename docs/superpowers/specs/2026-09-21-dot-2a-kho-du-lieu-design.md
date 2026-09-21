# Đặc tả thiết kế — Đợt 2a: Kho dữ liệu, phần vận hành

**Ngày:** 2026-09-21
**Công ty:** 株式会社KOME — bán buôn thực phẩm Việt Nam tại Nhật
**Phạm vi:** gộp `/nap` + `/health` + `/phu-du-lieu` thành một màn `/kho-du-lieu`, thêm giao diện Hoàn tác.
**Trạng thái:** Chờ duyệt
**Tài liệu liên quan:**
- `docs/superpowers/specs/2026-09-21-lo-trinh-24-man-hinh-design.md` §7 — lộ trình, gọi tắt **"lộ trình"**
- `docs/superpowers/specs/2026-09-16-kome-data-platform-design.md` — **"đặc tả nền"**

---

## 1. Bối cảnh

Đợt 1 đã xong và đã lên production: bảng màu, font, sidebar. Đợt 2a là màn hình
đầu tiên được dựng lại theo gói thiết kế.

Màn này **là màn duy nhất trong cả lộ trình đang có người phụ thuộc hằng ngày** —
quy trình 13:30. Đó vừa là lý do nó được xếp sớm, vừa là ràng buộc lớn nhất của
đợt: làm hỏng nó là làm hỏng việc duy nhất hệ thống đang thật sự phục vụ.

Ba trang hiện tại và thứ chúng làm:

| Trang | Nội dung | Ai dùng |
|---|---|---|
| `/nap` | một ô kéo–thả nhận nhiều file, submit rồi hiện danh sách kết quả | một người, một lần mỗi ngày |
| `/health` | ô tuổi dữ liệu · cảnh báo sao lưu · kỳ dữ liệu + ngày thiếu · bảng 7 loại (nạp lần cuối / số dòng / tổng tiền) | người nạp, và bất cứ ai nghi số sai |
| `/phu-du-lieu` | bảng theo ngày (90 ngày, 3 nguồn) · bảng theo tháng (toàn kỳ, 7 loại) | khi cần biết tháng nào thiếu |

---

## 2. Phạm vi

### 2.1 Trong phạm vi

- Màn `/kho-du-lieu` gộp toàn bộ nội dung ba trang trên, **không bỏ sót khối nào**.
- Ba địa chỉ cũ chuyển hướng 301 về màn mới.
- Giao diện **Hoàn tác** cho các lô nạp gần nhất (route `POST /undo/{batch_id}` đã tồn tại, chỉ thiếu giao diện).
- Cập nhật `docs/runbook.md` — xem §7.
- Cập nhật bảng "Các trang của web app" trong `CLAUDE.md`.

### 2.2 Ngoài phạm vi — thuộc đợt 2b

Chín khối tài liệu sống của màn 19: 4 tầng · 7 nguồn từ OBC · đối chiếu bắt buộc
sau mỗi lần nạp · ai là sự thật về cái gì · cạm bẫy riêng của OBC · lộ trình ·
ma trận khoá · file này nối đi đâu · cột trong từng file.

### 2.3 Không đụng tới

CSDL (không migration), `kome/pipeline.py`, 5 cổng kiểm tra,
`kome/tuoi_du_lieu.py`, `kome/config.py`, `kome/coverage.py`. Đợt này **chỉ
đổi tầng web**, cộng một module đọc mới (`kome/nhat_ky_nap.py`, §4.3).

`tinh_bang_ngay` và `tinh_bang_phu` không đổi một dòng — bảng phủ trên web và
lệnh terminal `scripts/bang_phu_du_lieu.py` phải cho ra đúng số như trước.

---

## 3. Quyết định đã chốt qua thảo luận

| Câu hỏi | Quyết định | Vì sao |
|---|---|---|
| Luồng nạp có đổi theo thiết kế (7 ô riêng) không? | **Không** — giữ một ô nhận nhiều file như hiện nay | Người làm 13:30 thả 3 file một lần; 7 ô biến 1 thao tác thành 3. Thiết kế tối ưu cho việc nhìn, không cho việc làm hằng ngày |
| Vậy làm sao biết còn thiếu file nào? | Đặt ô `_tuoi_du_lieu.html` **ngay cạnh ô thả file** | Khối đó **đã tồn tại** và đã trả lời đúng câu đó cho 3 nguồn hằng ngày, kèm mẫu tên file phải đặt. Không dựng mới |
| Bảng trạng thái hiện 3 hay 7 loại? | **3** — đúng nhịp 13:30 | `kome/coverage.py:93-100` đã ghi lý do: 4 loại master xuất vài lần mỗi năm, chiếu xuống từng ngày thì 99% ô đỏ dù không ai làm sai, và một cột đỏ thường trực dạy người đọc bỏ qua cả cột. Chúng ở lại bảng tháng |
| Ba địa chỉ cũ? | **301 về `/kho-du-lieu`** | Màn gộp không còn là một "health check" nên đặt tên `/health` là nói dối về chính nó; 301 giữ dấu trang và thói quen; một trang nên có một địa chỉ chính danh |
| Nút Hoàn tác? | **Có, kèm bước xác nhận** | `runbook.md:152` hiện bắt người không rành kỹ thuật mở terminal chạy `python scripts/hoan_tac.py` đúng lúc vừa nạp nhầm — thời điểm tệ nhất để đòi ai đó gõ Python. R1 nói "hỏng phải sửa được bằng tay" |
| Cách dựng | **Một route, một template, các khối tách thành partial** | Đợt 2b còn thêm 9 khối; tách sẵn thì 2b chỉ là thêm file, không phải mổ lại |
| Endpoint nhận file | **Giữ `POST /upload`**, chỉ đổi template nó render | Route cũ đã có test canh và runbook đã nhắc tên; đổi tên endpoint là phá hai thứ đó để đổi lấy sự gọn gàng trên giấy |

---

## 4. Kiến trúc màn hình

### 4.1 Thứ tự khối

Nguyên tắc sắp xếp: **trả lời "tôi phải làm gì ngay bây giờ" trước, rồi mới tới
"có gì sai không", cuối cùng là "sổ sách"**.

| # | Khối | Nguồn | Ẩn ở bản chỉ-đọc |
|---|---|---|---|
| 1 | Ô tuổi dữ liệu — hôm nay đã có dữ liệu chưa | `_tuoi_du_lieu.html` (đã có) | không |
| 2 | **Nạp dữ liệu** — ô thả nhiều file + kết quả lần nạp vừa rồi | tách từ `upload.html` | **có** |
| 3 | Cảnh báo sao lưu · kỳ dữ liệu · ngày làm việc bị thiếu | tách từ `health.html` | phần sao lưu tự ẩn (đã có) |
| 4 | Bảng 7 loại file — nạp lần cuối / số dòng / tổng tiền | tách từ `health.html` | không |
| 5 | **Lô nạp gần nhất + Hoàn tác** | mới | **có** |
| 6 | Bảng theo ngày — 90 ngày, 3 nguồn | `_bang_ngay.html` (đã có) | không |
| 7 | Bảng theo tháng — toàn kỳ, 7 loại | tách từ `phu_du_lieu.html` | không |

Khối 1 và 2 đứng cạnh nhau có chủ ý: khối 1 nói thiếu file nào, khối 2 là chỗ
thả file đó vào. Hôm nay hai thứ đó nằm ở hai trang khác nhau.

### 4.2 File

| File | Vai trò |
|---|---|
| `kome/web/templates/kho_du_lieu.html` | **mới** — khung màn, include 6 partial |
| `kome/web/templates/_nap.html` | **mới** — khối 2, tách từ `upload.html` |
| `kome/web/templates/_suc_khoe.html` | **mới** — khối 3+4, tách từ `health.html` |
| `kome/web/templates/_lo_nap.html` | **mới** — khối 5 |
| `kome/web/templates/_bang_thang.html` | **mới** — khối 7, tách từ `phu_du_lieu.html` |
| `kome/web/templates/_tuoi_du_lieu.html` | đã có, **không sửa** |
| `kome/web/templates/_bang_ngay.html` | đã có, **không sửa** |
| `kome/web/templates/upload.html` · `health.html` · `phu_du_lieu.html` | **xoá** |
| `kome/web/app.py` | route mới + 3 chuyển hướng + truy vấn lô nạp |

### 4.3 Dữ liệu route cần

Một lần mở màn cần bảy thứ:

```
tinh_tuoi(conn)         -> khối 1   kome/tuoi_du_lieu.py
_ky_du_lieu(conn)       -> khối 3   app.py:69, hàm riêng ở mức module
backup_status(dir)      -> khối 3   ops/backup.py, không đụng CSDL
(SQL viết thẳng trong route)  -> khối 4   xem dưới
tinh_bang_ngay(conn)    -> khối 6   kome/coverage.py
tinh_bang_phu(conn)     -> khối 7   kome/coverage.py
lo_nap_gan_nhat(conn)   -> khối 5   MỚI
```

**Khối 4 hiện không có hàm nào.** Route `/health` tự chạy một câu SQL thô trên
`meta.ingest_batch` rồi ghép với `SPECS` ngay trong thân hàm (`app.py`, khoảng
dòng 300–320). Đợt này **tách nó thành một hàm có tên** đặt cạnh
`lo_nap_gan_nhat` — không phải dọn dẹp ngoài phạm vi mà là điều kiện để route
mới không phình ra: route `/kho-du-lieu` gọi bảy thứ, nếu một trong bảy là hai
mươi dòng SQL nội tuyến thì hàm route không còn đọc trọn được nữa.

Hai hàm này đặt ở **`kome/nhat_ky_nap.py` (module mới)**, không nhét vào
`kome/coverage.py`. Lý do: docstring của `coverage.py` khai rõ nó là "MỘT nơi
duy nhất tính **bảng phủ**", đọc thẳng từ kho chứ không đếm tên file — còn hai
hàm này đọc **nhật ký nạp** (`meta.ingest_batch`: lô nào đã vào, lúc nào, bao
nhiêu dòng). Hai câu hỏi khác nhau trên hai nguồn khác nhau; gộp vào một file
làm mờ đúng ranh giới mà docstring kia dựng lên.

`trang_thai_nap` trả về **đúng shape dict mà `health.html` đang dùng**
(`name` / `last` / `rows` / `total` / `co_tien`) chứ không đổi sang dataclass —
để việc tách partial là một phép chuyển nguyên văn, không lẫn hai loại thay đổi
vào một bước.

`lo_nap_gan_nhat` đọc `meta.ingest_batch`:

```sql
SELECT batch_id, spec_name, source_file, data_date, loaded_at, row_count, total_amount
FROM meta.ingest_batch
WHERE undone_at IS NULL
ORDER BY loaded_at DESC
LIMIT 10
```

---

## 5. Route và địa chỉ

```
GET  /kho-du-lieu        màn gộp
GET  /nap                -> 301 /kho-du-lieu#nap
GET  /health             -> 301 /kho-du-lieu
GET  /phu-du-lieu        -> 301 /kho-du-lieu#theo-thang
POST /upload             giữ nguyên; render kho_du_lieu.html kèm kết quả
POST /undo/{batch_id}    giữ nguyên; đổi đích chuyển hướng /health -> /kho-du-lieu
```

**301 chứ không 302**: ba địa chỉ này biến mất vĩnh viễn, và 301 cho trình duyệt
cập nhật dấu trang. Neo `#nap` và `#theo-thang` để người bấm dấu trang cũ rơi
đúng khối họ vẫn mở, không phải cuộn đi tìm.

`/nap` trên bản chỉ-đọc: **vẫn chuyển hướng**, không trả 403. Màn đích tự ẩn khối
nạp. Trả 403 cho một dấu trang cũ là phạt người dùng vì một thay đổi họ không gây
ra.

---

## 6. Hoàn tác

Khối 5 liệt kê **10 lô nạp gần nhất chưa bị hoàn tác**, mỗi dòng: loại file · tên
file · ngày dữ liệu · nạp lúc · số dòng · tổng tiền.

Mỗi dòng có một `<details>`:

```html
<details>
  <summary>Hoàn tác</summary>
  <p>Xoá <strong>{{ row_count }} dòng</strong> đã nạp từ
     <strong>{{ source_file }}</strong>. Không thể hoàn lại.</p>
  <form method="post" action="/undo/{{ batch_id }}">
    <button type="submit">Xoá lô {{ batch_id }}</button>
  </form>
</details>
```

**Xác nhận bằng `<details>` chứ không bằng JavaScript**: đợt này không thêm JS
(lộ trình §5), `confirm()` không tạo kiểu được và bị trình duyệt chặn ở một số
cấu hình, còn `<details>` thì có sẵn, đọc được bằng trình đọc màn hình, và **bắt
người ta đọc hậu quả trước khi thấy cái nút**. Nút mang đúng số lô để người bấm
đối chiếu được với dòng mình định xoá.

Sau khi hoàn tác: chuyển hướng 303 về `/kho-du-lieu`. Người dùng thấy ngay bảng
đã đổi — đó là phản hồi, không cần thông báo riêng.

Khối này **ẩn hoàn toàn ở bản chỉ-đọc**, cùng lý do với khối nạp.

---

## 7. Tài liệu phải cập nhật cùng đợt

Sổ tay lạc hậu còn tệ hơn một địa chỉ xấu — người mở nó ra là người không rành
kỹ thuật, và họ mở đúng lúc đang hỏng.

| File | Chỗ phải sửa |
|---|---|
| `docs/runbook.md` | 6 chỗ nhắc `/health`, `/phu-du-lieu`, `/nap` (dòng 28, 81, 86, 152, 153, 154, 159, 202, 245) → đổi sang `/kho-du-lieu`. Riêng dòng 152 ("Nạp nhầm file") **viết lại**: nay hoàn tác được bằng nút trên màn, không phải `python scripts/hoan_tac.py` |
| `CLAUDE.md` | bảng "Các trang của web app": ba dòng `/nap`, `/health`, `/phu-du-lieu` gộp thành một dòng `/kho-du-lieu` |
| `docs/trien-khai-vercel.md` | dòng 99 dùng `/health` làm mục kiểm đăng nhập → đổi sang `/kho-du-lieu` |

`scripts/hoan_tac.py` **giữ nguyên, không bỏ**: nó là đường thoát khi web app
không mở được — đúng tình huống `runbook.md:159` mô tả.

---

## 8. Kiểm thử

Test hiện có phải **xanh nguyên**. Hai bộ chắc chắn bị đụng và phải đọc kỹ trước
khi sửa: `tests/test_web.py` (gọi thẳng `/health`, `/phu-du-lieu`) và
`tests/test_giao_dien.py` (hằng `TRANG` liệt kê ba địa chỉ cũ).

| Test | Chặn thảm hoạ gì |
|---|---|
| `/kho-du-lieu` trả 200 và chứa đủ 7 khối | Gộp trang làm rơi mất một khối mà không ai để ý |
| Ba địa chỉ cũ trả **301**, `Location` đúng | Dấu trang cũ gãy, người dùng tưởng hệ thống hỏng |
| Bản chỉ-đọc: màn không chứa ô thả file và không chứa nút Hoàn tác | Bản công khai mời người ta bấm một nút luôn báo lỗi |
| Bản chỉ-đọc: `/kho-du-lieu` không nhập `kome.pipeline` ở mức ngoài cùng | Trang Vercel chết khi khởi động |
| `POST /upload` render màn gộp kèm kết quả, không phải trang cũ | Nạp xong rơi vào một trang không còn tồn tại |
| `lo_nap_gan_nhat` bỏ qua lô đã có `undone_at` | Hiện nút Hoàn tác cho lô đã hoàn tác rồi |
| `POST /undo/{id}` rồi mở lại màn: lô đó biến khỏi danh sách | Hoàn tác không có tác dụng mà giao diện vẫn báo thành công |
| Số liệu từng khối khớp với số ba trang cũ đang trả trên cùng dữ liệu | Thay ba trang bằng một trang nói số khác |

---

## 9. Rủi ro & giả định

| # | Vấn đề | Ảnh hưởng | Cách xử lý |
|---|---|---|---|
| A1 | Một lần mở màn chạy 6 truy vấn thay vì 1–3 như từng trang cũ | Trung bình | **Đo sau khi dựng**, không tối ưu trước. Nếu chậm thật thì khối 7 (nặng nhất) bọc `<details>` — thiết kế đã quy ước bảng số dài mặc định đóng |
| A2 | `POST /upload` giờ phải dựng đủ dữ liệu cho 7 khối mới render được | Trung bình | Chấp nhận: nạp là việc một lần mỗi ngày, không phải đường nóng |
| A3 | Nút Hoàn tác là hành động **phá huỷ** đặt trên màn dùng hằng ngày | Cao | `<details>` che nút sau một bước đọc; nút mang số lô để đối chiếu; chỉ hiện 10 lô gần nhất; ẩn hoàn toàn ở bản chỉ-đọc |
| A4 | `runbook.md` là thứ dễ quên cập nhật nhất vì không test nào canh nó | Cao | Đưa vào §2.1 phạm vi và §10 tiêu chí hoàn thành; thêm một test grep: không file nào trong `docs/` còn trỏ tới ba địa chỉ cũ |
| A5 | Neo `#nap`, `#theo-thang` chỉ hoạt động nếu khối có đúng `id` đó | Thấp | Test khẳng định màn chứa cả hai `id` |

---

## 10. Tiêu chí hoàn thành

- [ ] `/kho-du-lieu` hiện đủ 7 khối, số liệu khớp ba trang cũ trên cùng dữ liệu
- [ ] Ba địa chỉ cũ trả 301 đúng đích
- [ ] Hoàn tác chạy được từ giao diện, có bước xác nhận, lô biến khỏi danh sách sau đó
- [ ] Bản chỉ-đọc không hiện ô thả file lẫn nút Hoàn tác
- [ ] `runbook.md`, `CLAUDE.md`, `trien-khai-vercel.md` không còn trỏ tới ba địa chỉ cũ
- [ ] `pytest -v` xanh toàn bộ
- [ ] Xem tận mắt ở cả hai chế độ sáng/tối, desktop và 375px

---

## 11. Bước tiếp theo

1. Lập kế hoạch triển khai (writing-plans)
2. Thực thi, kiểm chứng bằng mắt, merge
3. Đợt 2b — chín khối tài liệu sống, với ràng buộc "sinh ra, không chép tay" đã
   ghi ở lộ trình §7
