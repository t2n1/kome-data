# Nhiều bảng Tổng quan có tên cho mỗi người — đặc tả

Ngày: 2026-09-28 · Trạng thái: chờ duyệt · Migration: `056_bang_tong_quan.sql`

## 1. Mục tiêu

Hôm nay mỗi tài khoản có ĐÚNG MỘT bố cục trang `/` (cột
`app.nguoi_dung.bo_cuc_tong_quan`, migration 034). Chủ DN muốn một người tạo được
NHIỀU bảng (dashboard), đặt tên, lưu lại, dùng cho từng trường hợp ("Sáng thứ Hai",
"Họp tháng", "Kho").

Chốt với chủ DN (2026-09-28):

- **Riêng từng người.** Không chia sẻ, không bảng chung công ty (làm sau nếu cần).
- **Vai trò thành mẫu.** Dải chip "XEM THEO VAI TRÒ" bỏ khỏi đầu trang; bốn vai trò
  là lựa chọn xuất phát khi tạo bảng mới.
- **Mở `/` = bảng xem gần nhất**, nhớ trên máy chủ theo người; `?bang=<id>` chọn thẳng.

Không đổi: danh mục 21 khối (`bo_cuc.KHOI`), luật "cùng khối và cùng con số cho mọi
người — bố cục là cách XẾP, không phải bộ lọc", `bo_cuc.chuan_hoa` lọc lúc ghi và
lúc đọc, dữ liệu từng khối (`/api/tong-quan/<khối>`), ảnh chụp.

## 2. Dữ liệu (migration 056)

```sql
CREATE TABLE app.bang_tong_quan (
  id            bigserial PRIMARY KEY,
  nguoi_dung_id int  NOT NULL REFERENCES app.nguoi_dung(id) ON DELETE CASCADE,
  ten           text NOT NULL CHECK (length(btrim(ten)) BETWEEN 1 AND 40),
  bo_cuc        jsonb NULL,          -- NULL = bố cục mặc định (như 034)
  thu_tu        int  NOT NULL,
  tao_luc       timestamptz NOT NULL DEFAULT now(),
  sua_luc       timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX ON app.bang_tong_quan (nguoi_dung_id, lower(btrim(ten)));
CREATE INDEX ON app.bang_tong_quan (nguoi_dung_id, thu_tu);

ALTER TABLE app.nguoi_dung
  ADD COLUMN bang_gan_nhat bigint NULL REFERENCES app.bang_tong_quan(id) ON DELETE SET NULL;
```

- **Chuyển dữ liệu cũ:** mỗi người có `bo_cuc_tong_quan IS NOT NULL` được một dòng
  `ten = 'Bảng của tôi'`, `thu_tu = 0`, `bo_cuc` = giá trị cũ, và `bang_gan_nhat` trỏ
  vào nó. Người có cột cũ NULL: KHÔNG sinh dòng (xem "bảng ảo" §3).
- **Cột `bo_cuc_tong_quan` giữ lại** (lịch sử, cùng nếp các cột cũ ở 043) nhưng
  KHÔNG còn chỗ nào đọc hay ghi. `COMMENT` ghi rõ điều đó.
- Quyền: `kome_app` nhận SELECT/INSERT/UPDATE/DELETE trên bảng mới qua `ALTER DEFAULT
  PRIVILEGES` của 009 (migration chạy bằng `postgres`) — migration vẫn GRANT tường
  minh cả bảng lẫn sequence cho chắc, và `kome_report` chỉ SELECT.
- Chạy migration: nhớ `INSERT` tên file vào `meta.schema_migration` nếu chạy tay.

## 3. Quy tắc

| Quy tắc | Ở đâu canh |
|---|---|
| Tên sau `strip()`: 1–40 ký tự | CHECK + `bang.chuan_ten` (422) |
| Tên không trùng trong bảng của CÙNG người, không phân biệt hoa thường | UNIQUE (409 "Đã có bảng tên này") |
| Tối đa **20** bảng mỗi người | `bang.TOI_DA` (409) — chặn vòng lặp lỗi phía trình duyệt |
| Luôn còn ≥ 1 bảng: không xoá được bảng cuối | 409; giao diện làm mờ mục Xoá |
| Mọi câu ghi có `AND nguoi_dung_id = %s` | bảng của người khác → **404** (không lộ là có tồn tại) |
| Mọi `bo_cuc` qua `bo_cuc.chuan_hoa` lúc ghi và đọc | như 034 |

**Bảng ảo.** Người chưa có dòng nào (tài khoản mới, hoặc cột cũ NULL) được coi như có
một bảng `{id: null, ten: "Bảng của tôi", bo_cuc: mặc định}`. Không ghi gì khi chỉ mở
trang. Lần tự lưu / đổi tên đầu tiên trên bảng ảo tạo dòng thật (máy chủ trả `id`, giao
diện thay URL bằng `?bang=<id>`).

**Chọn bảng hiện** (`bang.chon(ds, tham_so, gan_nhat)`, thuần Python, không SQL):
`?bang=` hợp lệ và là của mình → bảng đó; không thì `bang_gan_nhat`; không thì bảng
đầu theo `thu_tu`; không có bảng nào → bảng ảo. `?bang=` rác / của người khác rơi
xuống bước sau, không lỗi.

**`bang_gan_nhat` chỉ ghi khi người dùng CHỦ ĐỘNG chuyển tab hoặc tạo bảng** — không
ghi lúc tải trang, nên mở `/` không phát sinh lượt ghi nào. Mở link `?bang=5` cũng
không đổi bảng gần nhất (chỉ bấm tab mới đổi).

## 4. Ngân sách truy vấn

Cổng đăng nhập vẫn MỘT lượt hỏi: câu `_CHON` của `kome/web/nguoi_dung.py` (dùng khi
dựng `request.state.nguoi`) thêm

```sql
n.bang_gan_nhat,
(SELECT json_agg(json_build_object('id', b.id, 'ten', b.ten, 'bo_cuc', b.bo_cuc)
                 ORDER BY b.thu_tu, b.id)
   FROM app.bang_tong_quan b WHERE b.nguoi_dung_id = n.id) AS bang
```

`NguoiDung.bo_cuc` đổi thành `NguoiDung.bang` (list thô, chưa tin) + `bang_gan_nhat`.
`liet_ke` (màn Cài đặt) KHÔNG cần hai cột này — nó dùng câu riêng không có truy vấn con,
để màn Cài đặt không kéo bố cục của cả công ty. `/` vẫn ≤ 9 truy vấn
(`tests/test_tong_quan.py::test_trang_chu_khong_qua_9_truy_van` không đổi).

Bố cục không phải dữ liệu của khối nào → KHÔNG vào `anh_chup._PHIEN_BAN`. Không ghi
`/nhat-ky` (cách xếp riêng của mỗi người, như 034).

## 5. Mô-đun và API

**`kome/web/bang_tong_quan.py`** (mới, cạnh `bo_cuc.py`; không nhập pandas):
`chuan_ten`, `chon`, `tao(conn, nguoi_id, ten, tu)`, `luu_bo_cuc`, `doi_ten`, `xoa`,
`mo`, `sap_thu_tu`. Không tự commit (người gọi quyết giao dịch — như `bo_cuc.luu`).
`tu` = `mac_dinh` | `chep:<id>` (phải là bảng của mình) | `vai:<mã>` (bố cục mặc định,
ẩn khối ngoài `bo_cuc.VAI_TRO[mã]` — ĐÚNG phép `apVai` hiện có, chuyển về máy chủ).
Mã vai trò lạ → 422.

Đường (chỉ JSON, cần đăng nhập — chưa có thì 403 như `POST /tong-quan/bo-cuc`; không bị
`_chi_doc` chặn, cùng lý lẽ đã ghi):

| Đường | Thân | Trả |
|---|---|---|
| `POST /tong-quan/bang` | `{ten, tu}` | 201 `{bang}`; đặt `bang_gan_nhat` |
| `POST /tong-quan/bang/{id}/bo-cuc` | bố cục | `{bo_cuc}` — `id = moi` với bảng ảo → tạo dòng, trả `{bang}` |
| `POST /tong-quan/bang/{id}/ten` | `{ten}` | `{bang}` |
| `POST /tong-quan/bang/{id}/xoa` | — | `{bang_hien}` (bảng sẽ hiện tiếp) |
| `POST /tong-quan/bang/{id}/mo` | — | 204 |
| `POST /tong-quan/bang/thu-tu` | `[id…]` (đúng tập bảng của mình) | 204; tập khác → 422 |

- `POST /tong-quan/bo-cuc` (cũ) giữ MỘT bản đời: ghi vào bảng gần nhất (hoặc tạo từ bảng
  ảo) — tab mở bản build cũ lúc triển khai không lưu hỏng. Ghi chú xoá ở đợt sau.
- `POST /tong-quan/bo-cuc/mac-dinh` (form) nhận `bang` ẩn, đặt lại ĐÚNG bảng đó về NULL.
- Thân > `bo_cuc.DAI_TOI_DA` → 413.

**`window.__KOME__`**: `bo_cuc` bỏ; thêm `bang: [{id, ten, bo_cuc}]` (MỌI bảng, mỗi
bố cục đã `chuan_hoa` — ≤ 20 × vài trăm byte, để chuyển tab tức thì không gọi máy chủ)
và `bang_hien_id` (chọn theo §3 với `?bang=` của chính yêu cầu; `null` = bảng ảo, khi
đó `bang` có đúng một phần tử `id: null`). Bảng ảo lưu qua `/tong-quan/bang/moi/bo-cuc`.

## 6. Giao diện (`giao_dien/src/tong_quan/`)

- **`ThanhBang.tsx`** (mới) ở chỗ dải "XEM THEO VAI TRÒ": tab các bảng
  (`role="tablist"`, tab đang xem `aria-selected`), `＋ Bảng mới`. Tab đang xem có nút
  `⋯`: Đổi tên (sửa tại chỗ, Enter lưu / Esc huỷ) · Nhân bản · ← Dời trái / Dời phải →
  · Đặt lại bố cục · Xoá (hộp xác nhận ghi đúng tên; bảng cuối → mờ + lý do). Không
  kéo tab — tránh lẫn với kéo khối ngay dưới, và dùng được bằng bàn phím.
- **`BangMoi.tsx`**: ô tên + chọn xuất phát: Chép "‹bảng đang xem›" · Giám đốc ·
  Trưởng phòng KD · Kế toán · Kho & giao hàng · Đầy đủ (mặc định). Tên gợi ý theo lựa
  chọn, tự thêm " (2)" khi trùng. Lỗi máy chủ hiện ngay trong hộp.
- **Chuyển tab:** `history.pushState(giuKhoang(...?bang=id))` (bất biến Khoảng xem),
  ĐẨY NGAY lượt tự lưu 400 ms đang chờ của bảng cũ, rồi `POST …/mo` (nuốt lỗi — không
  lưu được bảng gần nhất không phải lỗi người dùng cần thấy). Dữ liệu khối dùng lại bộ
  nhớ đệm TanStack (cùng khoá) — chỉ bố cục đổi. `popstate` đọc lại `?bang=`.
- Tự lưu ghi vào `/tong-quan/bang/{id}/bo-cuc` của bảng đang xem.
- Nút "Đặt lại bố cục" của thanh bố cục giữ nguyên, tác dụng trên bảng đang xem.
- `document.title` = "Tổng quan · ‹tên bảng›".
- Máy chưa bật đăng nhập (`sap_xep_duoc = false`): một bảng tạm, `＋ Bảng mới` và `⋯`
  mờ kèm câu đang có ("Máy này chưa bật đăng nhập…").
- `TongQuan.tsx` bỏ `vaiDang`/`apVai` và dải chip; `KD.danh_muc.vai_tro` vẫn gửi xuống
  (hộp Bảng mới đọc nhãn từ đó — giao diện không tự chép danh mục).
- Sửa `giao_dien/` ⇒ `npm run build`, commit `kome/web/spa/`.

## 7. Kiểm thử (`tests/test_bang_tong_quan.py`, mới)

- Migration: bố cục cũ → "Bảng của tôi" + `bang_gan_nhat`; cột cũ NULL → không dòng.
- Sở hữu: sửa bố cục / đổi tên / xoá / `mo` / `chep:` bảng của người khác → 404, dữ
  liệu của họ không đổi.
- Giới hạn: 21 bảng → 409; trùng tên khác hoa thường / khoảng trắng → 409; tên rỗng /
  41 ký tự → 422; xoá bảng cuối → 409.
- `chon`: `?bang=` của mình > gần nhất > đầu tiên > ảo; `?bang=` rác / của người khác
  rơi xuống bước sau.
- Xoá bảng gần nhất → `bang_gan_nhat` NULL, `bang_hien` là bảng đầu.
- `vai:<mã>` → đúng tập khối đang hiện = `bo_cuc.VAI_TRO[mã]`; `chep:` chép nguyên
  thứ tự + kích thước.
- Bảng ảo: lưu bố cục lần đầu tạo đúng MỘT dòng.
- `thu-tu` với tập id khác tập bảng của mình → 422.
- Đường cũ `POST /tong-quan/bo-cuc` ghi vào bảng gần nhất.
- Cổng đăng nhập vẫn 1 lượt hỏi; `/` vẫn ≤ 9; màn Cài đặt không đọc `bang_tong_quan`.
- `kome_app` ghi được bảng mới; `kome_report` chỉ đọc.
- Sửa `tests/test_bo_cuc.py` / `tests/test_api.py` chỗ đang đọc `KD.bo_cuc` /
  `NguoiDung.bo_cuc`.

## 8. CLAUDE.md

Thêm một bất biến (056): nhiều bảng riêng từng người; `bo_cuc_tong_quan` ngừng dùng;
bảng ảo; `bang_gan_nhat` chỉ ghi khi chủ động chuyển; 404 cho bảng người khác; vai trò
là MẪU, không còn là chip áp đè. Sửa dòng `/` của bảng "Các trang". Chạy lại
`python scripts/sinh_tai_lieu.py` (sửa migration) và `scripts/sinh_cot_dung.py` nếu nó
quét `app`. **Migration 056 phải chạy TRƯỚC khi triển khai.**
