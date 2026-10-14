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

Hệ quả cho Task 7: ngày nhập bằng BÀN PHÍM (không đặt giá trị); không đọc lại được để kiểm trên màn hình, nên kiểm ở
hai lớp: (a) pattern sai → cột lệch → cổng 2 (`ColumnMismatch`) của web chặn; (b) sau khi xuất, `obc_bot` mở file Excel và
kiểm MỌI dòng `売上日付` = ngày hôm nay — lệch → `LoiObc("kiểm ngày trong file")`, không nạp.
| 4 | như trên | `[Button] データ作成(E)...` | bấm | `02_ban_dieu_kien.txt` |
| 5 | `売上明細表` › `売上明細表 - データ作成条件設定` | `[RadioButton] Excel形式のファイル` (đang chọn), `基本条件だけ出力する` (đang chọn), `罫線を付ける` / `色を付ける` (đang tick) | giữ nguyên | `03_ban_xuat.txt` |
| 6 | như trên | `[Button] 出力開始(E)` | bấm | `03_ban_xuat.txt` |
| 7 | (hộp thoại lưu?) | — | **CHƯA đo** | — |

Không dùng ô `本日分` (nghĩa chưa chắc: có thể là "phiếu nhập/sửa hôm nay", không phải ngày bán).
