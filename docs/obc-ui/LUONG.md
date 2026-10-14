# Luồng bấm OBC (đo thật trên 商奉行クラウド, 2026-10-14)

Nguồn cho Task 7 (`obc_bot/obc/*.py`). Mỗi bước ghi: cửa sổ (title UIA) → điều khiển (tên / loại) → việc làm.
Điều khiển KHÔNG có tên chỉ được chọn khi đã ghi rõ cách nhận ra nó (giá trị đọc được, vị trí tương đối với nhãn).

## 売上明細表 (máy B, mục `ban`)

| # | Cửa sổ | Điều khiển | Việc | Nguồn |
|---|---|---|---|---|
| 1 | `奉行クラウド` | `[Button] 売上明細表` (thanh công cụ) | bấm | `01_menu.txt` |
| 2 | `売上明細表` › `売上明細表 ‐ 条件設定` | ô ngày `売上日付` (ComboBox giá trị `売上日付` + `[Edit] TextBox` đang hiện `2026`) | gõ ngày hôm nay — **cách gõ chính xác (một ô hay ba ô năm/tháng/ngày, từ–đến) CHƯA đo** | `02_ban_dieu_kien.txt`, chủ DN: "gõ ngày 売上日付" |
| 3 | như trên | 出力パターン | **CHƯA biết nằm ở đâu** — không có ComboBox nào ở màn 条件設定 mang giá trị giống tên pattern | chờ chủ DN |
| 4 | như trên | `[Button] データ作成(E)...` | bấm | `02_ban_dieu_kien.txt` |
| 5 | `売上明細表` › `売上明細表 - データ作成条件設定` | `[RadioButton] Excel形式のファイル` (đang chọn), `基本条件だけ出力する` (đang chọn), `罫線を付ける` / `色を付ける` (đang tick) | giữ nguyên | `03_ban_xuat.txt` |
| 6 | như trên | `[Button] 出力開始(E)` | bấm | `03_ban_xuat.txt` |
| 7 | (hộp thoại lưu?) | — | **CHƯA đo** | — |

Không dùng ô `本日分` (nghĩa chưa chắc: có thể là "phiếu nhập/sửa hôm nay", không phải ngày bán).
