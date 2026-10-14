# Luồng bấm OBC (đo thật trên 商奉行クラウド, 2026-10-14)

Nguồn cho Task 7 (`obc_bot/obc/*.py`). Mỗi bước ghi: cửa sổ (title UIA) → điều khiển (tên / loại) → việc làm.
Điều khiển KHÔNG có tên chỉ được chọn khi đã ghi rõ cách nhận ra nó (giá trị đọc được, vị trí tương đối với nhãn).

## 売上明細表 (máy B, mục `ban`)

| # | Cửa sổ | Điều khiển | Việc | Nguồn |
|---|---|---|---|---|
| 1 | `奉行クラウド` | `[Button] 売上明細表` (thanh công cụ) | bấm | `01_menu.txt` |
| 2 | `売上明細表` › `売上明細表 ‐ 条件設定` | ô `パターン名` (trên cùng, nền vàng, hiện `903.売上明細表`) | màn mở ra đã chọn sẵn pattern lần trước; bấm ô → hộp thoại `売上明細表 ‐ パターン選択` (danh sách + `OK`) | ảnh chụp chủ DN 2026-10-15, `02b_ban_pattern.txt` |
| 3 | như trên | hai ô `売上日付` dạng `2026年 9月30日 ～ 2026年 9月30日` (từ ~ đến) | gõ CÙNG ngày hôm nay vào cả hai — **cách gõ phím CHƯA đo** (xem dưới) | ảnh chụp chủ DN, chủ DN: "gõ ngày 売上日付" |

**Đo thật 2026-10-15 — ô tự vẽ của OBC KHÔNG đọc được qua UIA:**
- Ô `パターン名` và danh sách trong `パターン選択`: không có tên / giá trị nào (không thấy chuỗi `903` ở bất kỳ điều khiển nào).
- Hai ô `売上日付`: chỉ lộ một `[Edit] TextBox` giá trị `2026` (phần năm); tháng / ngày không đọc được.
- Nút có tên (`データ作成(E)...`, `出力開始(E)`, `OK`, `キャンセル`) bấm theo tên được.

**Bàn phím trong ô `売上日付` (chủ DN thử tay 2026-10-15):** mỗi ô ngày là BA phần — năm → `Tab` → tháng → `Tab` → ngày
(phần năm chính là `[Edit] TextBox` đọc được `2026`). Gõ số THAY HẲN giá trị cũ của phần đó (đã thử). `Tab` sau phần ngày của ô đầu SANG phần năm của ô thứ hai (đã thử).
⇒ Chuỗi phím chốt: focus `[Edit] TextBox` (phần năm ô đầu) rồi gõ
`YYYY{TAB}MM{TAB}DD{TAB}YYYY{TAB}MM{TAB}DD` (cùng một ngày cả hai ô).

Hệ quả cho Task 7: ngày nhập bằng BÀN PHÍM (không đặt giá trị); không đọc lại được để kiểm trên màn hình, nên kiểm ở
hai lớp: (a) pattern sai → cột lệch → cổng 2 (`ColumnMismatch`) của web chặn; (b) sau khi xuất, `obc_bot` mở file Excel và
kiểm MỌI dòng `売上日付` = ngày hôm nay — lệch → `LoiObc("kiểm ngày trong file")`, không nạp.
| 4 | như trên | `[Button] データ作成(E)...` | bấm | `02_ban_dieu_kien.txt` |
| 5 | `売上明細表` › `売上明細表 - データ作成条件設定` | `[RadioButton] Excel形式のファイル` (đang chọn), `基本条件だけ出力する` (đang chọn), `罫線を付ける` / `色を付ける` (đang tick) | giữ nguyên | `03_ban_xuat.txt` |
| 6 | như trên | `[Button] 出力開始(E)` | bấm | `03_ban_xuat.txt` |
| 7 | Excel | sổ MỚI chưa lưu (`Book1`, `Path = ''`), sheet `売上明細表` | OBC KHÔNG hỏi nơi lưu — nó đẩy dữ liệu thẳng vào Excel đang mở. `obc_bot` lấy sổ qua COM (`win32com`), `SaveAs` → `thu_muc/売上明細表_YYYYMMDD.xlsx` (FileFormat 51), rồi `Close` | đo COM 2026-10-15 |

**MỖI lần xuất OBC mở một TIẾN TRÌNH Excel MỚI** (đo 2026-10-15: `Book1` ở tiến trình 22:55, `Book2` ở tiến trình 00:24).
`GetActiveObject("Excel.Application")` chỉ bám MỘT tiến trình (cái đăng ký trước) ⇒ đọc nhầm sổ cũ. Cách đúng: ghi lại các
cửa sổ `XLMAIN` có TRƯỚC khi bấm `出力開始`, chờ cửa sổ `XLMAIN` MỚI xuất hiện, lấy sổ qua chính cửa sổ đó
(`XLMAIN` › `XLDESK` › `EXCEL7`, `AccessibleObjectFromWindow(OBJID_NATIVEOM = -16)` → `Window.Parent` = Workbook), rồi
`SaveAs` + `Close` + thoát đúng tiến trình đó. Đọc giá trị bằng `UsedRange.Value2` (qua comtypes `.Value` có tham số nên
lỗi COM); ngày trả về là SỐ NGÀY Excel (46310 = 2026-10-15) — so với `(ngay - date(1899, 12, 30)).days`.
Lần thử thứ hai (đã gõ 2026/10/15): `Book2`, 221 dòng, cả hai cột `売上日付` = 46310 ⇒ chuỗi phím ngày ĐÚNG.

**Đo thật file ra (COM, 2026-10-15):** 20 cột, header dòng 1:
`売上日付, 売上区分, 伝票No., 売上日付, 売上区分コード, 売上区分, 得意先コード, 得意先名, 担当者コード, 担当者名, 荷姿区分コード,
荷姿区分名, 商品名, 商品コード, 日本語, 単価, 税抜純売上高, 粗利益, 粗利益率, 純売上数量` (khớp bẫy #8). 618 dòng — TOÀN BỘ
`売上日付` = `2026-09-30` vì lần xuất đó chạy TRƯỚC khi người thử đổi ngày (chủ DN xác nhận) — không phải lỗi gõ phím,
nhưng cho thấy đúng loại sai lặng lẽ mà lớp kiểm (b) chặn: đọc lại file, mọi `売上日付` (cả cột 0 và cột 3) phải = ngày
cần lấy, không thì không nạp.

## 在庫一覧 (máy B, mục `ton`) — Claude tự đo trên máy chủ DN, 2026-10-15

| # | Cửa sổ | Điều khiển | Việc |
|---|---|---|---|
| 1 | `奉行クラウド` | ứng dụng THỨ HAI ở cột trái (hai `Button` không tên trong `ScrollViewer` có `LineUp`; hint `Q2`) — menu có `在庫管理`, `仕入管理` | bấm nút thứ hai |
| 2 | như trên | `[Button] 在庫一覧表` (thanh công cụ của ứng dụng thứ hai) | bấm |
| 3 | `在庫一覧表` › `在庫一覧表 ‐ パターン選択` | danh sách KHÔNG đọc được qua UIA (ảnh chụp: 12 pattern; dòng 6 = `BIG-DATA-TON-KHO`) + `[Button] OK` | chọn `BIG-DATA-TON-KHO` → `OK` |
| 4 | `在庫一覧表` › `在庫一覧表 ‐ 条件設定` | hai ô 集計期間 cùng kiểu `売上日付` (năm/tháng/ngày, `Tab` sang ô thứ hai) | gõ hôm nay ~ hôm nay |
| 5 | như trên | `[Button] データ作成(E)...` → cửa sổ `… データ作成条件設定` → `[Button] 出力開始(E)` | bấm |
| 6 | Excel | tiến trình Excel MỚI, sổ chưa lưu, sheet `在庫一覧表` | lưu qua COM như `売上明細表` |

**Chọn pattern (đo 2026-10-15):** mở lại màn thì OBC CHỌN SẴN pattern dùng lần trước (nhưng pattern là `個人利用` của
tài khoản OBC — ai dùng pattern khác trên cùng tài khoản là lần sau lệch). Bàn phím chọn được dù danh sách không đọc được:
bấm vào một dòng trong danh sách (lấy focus) → `Home` → `Down` × (vị trí − 1) → `OK`. Đã thử: `Home` + `Down 5` dừng đúng
`BIG-DATA-TON-KHO`. ⇒ cấu hình mang VỊ TRÍ dòng (1 = dòng đầu), và header của file ra là lớp kiểm (pattern lệch → cột lệch).
`売上明細表`: `903.売上明細表` là dòng 1.

**Đo thật file ra (2026-10-15, `BIG-DATA-TON-KHO`, 15/10 ~ 15/10):** sheet `在庫一覧表`, 307 dòng, 15 cột:
`食品分類コード, 食品分類名, 商品コード, 商品名, 荷姿区分コード, 荷姿区分名, 倉庫コード, 倉庫名, 日本語, 単位, 賞味期限,
売上出荷数量, 在庫残数, 在庫単価, 在庫金額` — đủ 13 cột `files.yml` khai cho `zaiko` + 2 cột `食品分類` (đã biết, bẫy #6 /
bất biến 042). File tồn KHÔNG có cột ngày ⇒ không kiểm ngày bằng nội dung được; lớp kiểm là header (pattern sai → cột lệch).

## Chạy thật `obc_bot xuat` (2026-10-15, máy chủ DN)

- `--muc ban`: tự mở 売上明細表 → pattern dòng 1 → gõ 2026/10/15 ~ 2026/10/15 → データ作成 → 出力開始 → lấy sổ Excel mới →
  kiểm → `売上明細表_20261015.xlsx`. Qua ĐỦ 5 cổng (`pipeline.kiem` trên CSDL test): 221 dòng, ¥1,839,460.
- `--muc ton`: xuất được `在庫一覧_20261015.xlsx` (307 dòng) nhưng **cổng 3 CHẶN: 84 dòng trùng khoá
  (商品コード, 倉庫コード)** — dữ liệu THẬT: cùng mã cùng kho có tồn ở CẢ `00` (lẻ) và `02` (thùng), vd `BS01`/0001: 24 lẻ +
  295 thùng. File xuất tay 16/9, 24/9 chỉ có `02` cho các mã đó. Khoá của web (`files.yml` `keys` và PK
  `core.fact_inventory_daily (snapshot_date, product_code, warehouse_code)`, 005) KHÔNG có `pack_code` ⇒ ngày nào OBC có
  tồn lẻ thì file xuất TAY cũng bị chặn y hệt. Không phải lỗi `obc_bot`; cần chủ DN quyết (thêm `pack_code` vào khoá = migration
  mới + soát mọi view đọc tồn).
- Hai lỗi đã sửa khi chạy thật: (1) Excel chưa phục vụ COM ngay → thử lại 60 s; (2) Excel tạo nhiều `XLMAIN` ẨN không chứa sổ
  → chỉ tính cửa sổ đang hiện có `XLDESK › EXCEL7`.

Không dùng ô `本日分` (nghĩa chưa chắc: có thể là "phiếu nhập/sửa hôm nay", không phải ngày bán).
