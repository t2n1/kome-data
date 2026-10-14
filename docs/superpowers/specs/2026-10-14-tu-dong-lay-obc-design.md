# Tự động lấy dữ liệu OBC hằng ngày và nạp vào web — đặc tả

Ngày: 2026-10-14 · Trạng thái: chờ chủ DN duyệt

## 1. Vì sao, và điều này đổi gì

Hằng ngày 13:30 một người mở 商奉行クラウド, xuất 3 file Excel rồi kéo thả vào
`/kho-du-lieu`. Việc này lặp lại, dễ quên, và phụ thuộc một người có mặt.

Đặc tả gốc (`2026-09-16-kome-data-platform-design.md`, quyết định #10) đã cố ý
**không** nạp tự động: người kéo thả thấy ngay 5 cổng kiểm, và không cần máy bật
suốt ngày. Đặc tả này **đổi quyết định đó**, nên phải bù lại đúng hai điều nó bảo vệ:

- Cổng chặn file thì **phải có người biết ngay**, không được nằm im (§6).
- Máy chạy phải bật lúc chạy — đó là điều kiện vận hành có tên (§7), không giấu.

Kéo thả tay **vẫn còn nguyên** — là lối dự phòng khi chương trình hỏng.

## 2. Những gì đã chốt với chủ DN (2026-10-14)

| Câu hỏi | Chốt |
|---|---|
| OBC loại nào | **商奉行クラウド** (dữ liệu trên mây OBC, mở bằng phần mềm Windows) |
| Lấy dữ liệu bằng gì | **Bấm thay người (RPA)** trên phần mềm 奉行クラウド — KHÔNG mua bản 奉行クラウド API version |
| Chạy trên máy nào | **Hai máy**, chia theo 権限 của tài khoản OBC — quyền giữ nguyên, không gom |
| Máy B (máy riêng) | tài khoản OBC của chủ DN · `売上明細表`, `在庫一覧` |
| Máy của Long | tài khoản OBC của Long · `得意先全情報` |

## 3. Kiến trúc

```
máy B  (Task Scheduler, 13:30)              máy Long (Task Scheduler, giờ riêng §7)
  obc_bot chay --cau-hinh may_b.toml          obc_bot chay --cau-hinh may_long.toml
     │ 0. kiểm trước: màn hình không khoá,         │
     │    hôm nay là ngày làm việc, file nào       │
     │    hôm nay đã có trên web (§5.2)            │
     │ 1. mở / đánh thức 奉行クラウド             │
     │ 2. xuất 売上明細表 + 在庫一覧 → thư mục ra  │ xuất 得意先全情報
     │ 3. đăng nhập web bằng tài khoản `obc-bot`   │ (cùng bước 3–4)
     │ 4. POST /api/kho-du-lieu/nap  (JSON)        │
     ▼                                             ▼
                web app — pipeline.ingest, 5 cổng như kéo thả tay
```

- **Một chương trình, hai cấu hình.** Không có hai bản mã. Mỗi máy một file TOML.
- **Hai nửa tách nhau**: `xuat` (bấm OBC → file Excel) và `nap` (gửi file lên web,
  đọc kết quả 5 cổng). `nap` chạy được riêng: OBC đổi giao diện làm `xuat` hỏng thì
  người vẫn xuất tay rồi chạy `obc_bot nap <file>` — hoặc kéo thả như cũ.
- **Không đụng CSDL trực tiếp.** Máy B và máy Long không giữ mật khẩu CSDL nào. Mọi
  file đi qua web như một người dùng — nên 5 cổng, chặn nạp trùng theo mã băm, khoá
  `uriage`/`meisai` cùng ngày và Nhật ký thao tác ("nạp bởi obc-bot") đều giữ nguyên.
- **Đích mặc định là bản Vercel** (luôn bật, đã nạp được file hằng ngày từ 045). Đo
  thật: `在庫一覧` ~28 KB, `得意先全情報` ~2,3–2,6 MB, `売上明細表` 24 ngày ~1,2 MB —
  đều dưới trần 4 MB. Đổi sang bản máy công ty = đổi `web_url` trong cấu hình.
- **File gốc giữ trên máy chạy** (`thu_muc_ra/YYYY-MM/`), vì Vercel không lưu file gốc.

## 4. Chương trình `obc_bot`

Thư mục `obc_bot/` ở gốc repo — **tách khỏi `kome/`**: web không nhập nó, nó không
nhập `kome` (máy chạy không cần pandas / psycopg / CSDL). Thêm vào `.vercelignore`.
Gói riêng `obc_bot/requirements.txt`: `pywinauto`, `httpx`, `keyring`.

```
obc_bot/
  __main__.py      lệnh: chay · xuat · nap · do (dò cây giao diện, §8)
  cau_hinh.py      đọc TOML, kiểm hợp lệ
  ten_file.py      tên file ra ĐÚNG mẫu config/files.yml (bản chép, có test canh)
  web.py           đăng nhập, GET /api/kho-du-lieu/hom-nay, POST /api/kho-du-lieu/nap
  man_hinh.py      kiểm màn hình khoá, chụp màn hình khi lỗi
  obc/
    phien.py       tìm / mở cửa sổ 奉行クラウド, đóng hộp thoại lạ, chờ sẵn sàng
    ban.py         売上明細表  → Path
    ton.py         在庫一覧   → Path
    khach.py       得意先全情報 → Path
  bao_cao.py       ghi log, ghi tệp báo lỗi, thông báo Windows
```

Cấu hình (ví dụ máy B):

```toml
muc = ["ban", "ton"]
web_url = "https://<bản vercel>"
tai_khoan_web = "obc-bot"          # mật khẩu: Windows Credential Manager (keyring), KHÔNG nằm trong file
thu_muc_ra = "C:/KOME/obc_xuat"
thu_muc_bao_loi = "C:/Users/<…>/OneDrive - 株式会社KOME/KOME自動取込"
```

### 4.1 Tìm điều khiển theo TÊN, không theo toạ độ

`pywinauto` backend `uia`: chọn menu / nút / ô ngày theo `title` + `control_type`
(ví dụ nút `売上明細表` trên thanh công cụ trong ảnh chụp 2026-10-14). Không
`click(x, y)`. Không tìm được điều khiển trong thời hạn → lỗi có tên bước (§6), không
bấm mò. Nếu §8 cho thấy một bước nào đó UIA không thấy, CHỈ bước đó lùi về nhận diện
hình ảnh, và ghi rõ trong mã bước nào dùng hình.

### 4.2 Khoảng ngày và tên file

- `売上明細表`: **chỉ ngày hôm nay** (chủ DN, 2026-10-14) → `売上明細表_YYYYMMDD.xlsx`.
  Nạp lại cùng ngày là an toàn: bộ nạp upsert theo `(slip_no, line_seq, source)`.
- Mỗi loại file xuất theo **出力パターン đánh số** mà chủ DN đã tạo sẵn trong OBC —
  chương trình chọn pattern theo SỐ ghi trong cấu hình (`pattern_ban`, `pattern_ton`,
  `pattern_khach`), không tự đặt cột. Đổi cột xuất = sửa pattern trong OBC, và cổng 2
  vẫn chặn nếu pattern lệch `config/files.yml`.
- `在庫一覧`, `得意先全情報`: ảnh chụp hiện tại, tên `<loại>_YYYYMMDD.xlsx` theo ngày Tokyo.
- Tên ra phải khớp `filename_pattern` của `config/files.yml` — nhận diện loại file
  chỉ dựa vào tên. `ten_file.py` là bản chép; test canh chạy từng tên nó sinh qua
  `kome.pipeline.identify` và phải ra đúng spec + đúng `data_date`.

## 5. Thay đổi phía web (nhỏ)

### 5.1 `POST /api/kho-du-lieu/nap` — nạp một bước, trả JSON

Cùng việc với `POST /upload` (chạy `pipeline.ingest`, 5 cổng, `_ghi_ai`, `lam_nong`)
nhưng trả JSON thay vì vỏ React — chương trình không phải bóc HTML. Phần thân chung
tách thành MỘT hàm dùng cho cả hai route (không chép).

- Nằm dưới `/api/kho-du-lieu` ⇒ middleware tự gác: chưa đăng nhập → 401 JSON, thiếu
  `duoc_vao_kho_du_lieu` → 403 JSON. Bản chỉ-đọc → 403 JSON.
- Trả mỗi file: `ten_file, ok, skipped, spec_name, data_date, row_count, batch_id,
  blockers[{cong, loi}], warnings[]`.
- Nạp một bước (không kiểm → xác nhận): bước xác nhận chỉ có nghĩa khi có người nhìn
  5 chấm; ở đây `ingest` vẫn chạy đủ 5 cổng và vẫn chặn y như vậy.

### 5.2 `GET /api/kho-du-lieu/hom-nay` — 1 lượt hỏi

`{ngay, la_ngay_kd, da_co: {ban, ton, khach}}`. `la_ngay_kd` đọc
`mart.lich_kinh_doanh` (định nghĩa ngày làm việc DUY NHẤT — chương trình không tự giữ
lịch lễ). `da_co` đọc `meta.ingest_batch.data_date` = hôm nay theo Tokyo, cùng luật
với ô "hôm nay đã có dữ liệu chưa" (`kome/tuoi_du_lieu.py`). Chương trình dùng nó để:
không chạy ngày nghỉ, và **không chiếm chuột** khi người đã kéo thả tay rồi.

### 5.3 Tài khoản `obc-bot`

Tạo bằng `scripts/tao_nguoi_dung.py` với `--kho-du-lieu`, không cờ nào khác. Không
`salesperson_code`. Mật khẩu dài ngẫu nhiên, lưu vào Credential Manager của từng máy.
Nhật ký thao tác hiện "nạp bởi obc-bot" — phân biệt được với người nạp tay.

Rủi ro có tên: cờ `duoc_vao_kho_du_lieu` cho cả quyền **Hoàn tác**, nên ai lấy được
mật khẩu `obc-bot` trên máy B / máy Long là bấm được nút xoá lô. Chấp nhận ở đợt này
(mật khẩu nằm trong Credential Manager của người dùng Windows, không trong file; chương
trình không bao giờ gọi `/undo`). Tách một cờ "chỉ nạp" là việc riêng nếu cần.

## 6. Khi hỏng

Mọi lần chạy kết thúc ở ĐÚNG MỘT trong các kết cục, ghi vào log ngày
(`thu_muc_ra/log/YYYY-MM-DD.log`):

| Kết cục | Ví dụ | Làm gì |
|---|---|---|
| `xong` | mọi file `ok` | thông báo Windows ngắn |
| `bo_qua` | ngày nghỉ · file đã có hôm nay | chỉ log |
| `cong_chan` | cổng 3 (dưới `min_rows`), cổng 2 (`ColumnMismatch`) | **báo lỗi** — kèm nguyên văn `blockers` |
| `loi_obc` | không tìm thấy nút, hộp thoại lạ, OBC không mở, phiên bị đá | thử lại 1 lần sau khi đóng / mở lại OBC; vẫn hỏng → **báo lỗi** + ảnh chụp màn hình |
| `man_hinh_khoa` | Windows khoá / ngủ | **báo lỗi** ngay, không thử bấm |
| `loi_web` | 401 (sai mật khẩu bot), 403, mạng | **báo lỗi**; file đã xuất vẫn nằm trong `thu_muc_ra` để nạp tay |

**Báo lỗi** = (1) một tệp `YYYY-MM-DD_<máy>_<kết cục>.txt` (+ ảnh chụp) vào
`thu_muc_bao_loi` — thư mục OneDrive dùng chung nên chủ DN thấy trên mọi máy;
(2) thông báo Windows trên máy chạy. Ô 13:30 của `/kho-du-lieu` vẫn đỏ như cũ khi
thiếu dữ liệu — tức người mở web vẫn thấy, kể cả khi không ai đọc thư mục báo lỗi.

Không có gửi email / LINE ở đợt này (chưa có kênh nào cấu hình sẵn). Thêm sau nếu cần
— chỉ là một hàm thứ ba trong `bao_cao.py`.

## 7. Điều kiện vận hành (có tên, không giấu)

- **Màn hình không khoá, máy không ngủ** lúc chạy. RPA cần màn hình thật; Windows khoá
  thì không bấm được gì. Máy B: tắt khoá màn hình + chế độ ngủ, tự đăng nhập Windows.
  Máy Long: chạy lúc Long đang ở máy.
- **Task Scheduler "chỉ chạy khi người dùng đã đăng nhập"** (cần màn hình tương tác) —
  không chạy được dưới dạng dịch vụ nền.
- **Máy Long — giờ chạy đề xuất 12:05** (giờ nghỉ trưa, ít đụng chuột). Trước khi bấm,
  thông báo đếm ngược 30 giây "sắp lấy dữ liệu OBC, đừng dùng chuột". `得意先全情報` là
  danh mục (SCD2), không cần đúng 13:30.
- **Phiên OBC trùng tài khoản**: 奉行クラウド đá phiên cũ khi cùng tài khoản đăng nhập
  nơi khác. Máy B và máy Long dùng hai tài khoản khác nhau nên không đá nhau; chủ DN tự
  tránh mở OBC bằng tài khoản của mình lúc máy B chạy. Bị đá giữa chừng → thử lại 1 lần
  (§6) rồi `loi_obc` — không giành phiên qua lại.
- **OBC cập nhật giao diện** → `loi_obc` tới khi sửa `obc/*.py`. Kéo thả tay là dự phòng.

## 8. Bước đầu tiên: thử nghiệm (trước khi viết phần bấm)

Ba câu hỏi phải có câu trả lời ĐO THẬT trên máy có 奉行クラウド, trước `obc/ban.py`:

1. **UIA có thấy điều khiển của 奉行クラウド không?** `python -m obc_bot do` in cây điều
   khiển (tên + loại) của cửa sổ đang mở. Thấy được menu, nút thanh công cụ, ô ngày, nút
   xuất Excel, hộp thoại lưu file → đi tiếp §4.1. Không thấy → báo lại chủ DN trước khi
   chọn nhận diện hình ảnh cho bước nào.
2. **Khoảng ngày / mẫu xuất người ta đang dùng** cho từng loại file (§4.2) — ghi lại
   nguyên các lựa chọn trên màn xuất (出力条件, パターン).
3. **Đăng nhập trùng tài khoản** có đá phiên kia không (§7).

Kết quả ghi vào cuối đặc tả này (mục "Đo thật") rồi mới viết tiếp.

### Đo thật (chủ DN trả lời 2026-10-14)

1. UIA **thấy** điều khiển của 奉行クラウド; mỗi loại file có 出力パターン đánh số riêng.
   Vẫn chạy `obc_bot do` một lần để lấy đúng tên điều khiển trước khi viết `obc/*.py`.
2. `売上明細表`: **ngày hôm nay**.
3. Đăng nhập trùng tài khoản: **có đá phiên kia ra** — hai máy dùng hai tài khoản khác
   nhau nên không phải vấn đề (§7).

## 9. Kiểm thử

- `obc_bot` (không cần OBC): cấu hình, `ten_file` ↔ `kome.pipeline.identify` (test canh
  bản chép), máy trạng thái kết cục §6, `web.py` với máy chủ giả (401 / 403 / cổng chặn
  / `skipped`). Chạy bằng pytest như phần còn lại.
- Web: `tests/test_nap_tu_dong.py` — `/api/kho-du-lieu/nap` nạp được và trả đúng
  `blockers`; 401 chưa đăng nhập, 403 thiếu cờ, 403 bản chỉ-đọc; `/upload` cũ trả
  y như trước (cùng hàm thân); `/hom-nay` 1 lượt hỏi, `la_ngay_kd` khớp
  `mart.lich_kinh_doanh`, `da_co` khớp `tuoi_du_lieu`.
- Phần bấm OBC: KHÔNG có test tự động (không có OBC trong CI). Có danh sách kiểm tay
  `docs/runbook.md` mục mới: chạy `obc_bot xuat` từng loại, so file với file xuất tay
  cùng ngày (cùng số dòng, cùng tổng tiền), rồi `obc_bot chay` một ngày thật.

## 10. Ngoài phạm vi

- Mua / dùng 奉行クラウド API (có thể thay `obc/` sau mà không đổi `web.py` / phía web).
- File không hằng ngày (`取引単価データ`, `請求先元帳`, `商品データ`, đối soát tháng) —
  thêm sau bằng một mô-đun mới trong `obc/` + một mục trong cấu hình.
- Kênh báo lỗi email / LINE.
- Ghi bất cứ gì vào OBC (luật số một — chương trình chỉ xuất).
