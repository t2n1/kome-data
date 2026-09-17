# Cột đầy đủ của file 得意先全情報 (khách hàng) — cái nào đang dùng, cái nào bỏ được

Đối chiếu bản gốc `得意先全情報_20260813.xlsx` (sheet `得意先データ作成`, header dòng 1,
2.080 khách, **324 cột**) với khai báo pipeline (`config/files.yml` mục
`tokuisaki`). Pipeline chỉ dùng **17/324 cột** — 307 cột còn lại có thể bỏ khi
tải file về máy, không ảnh hưởng gì tới nạp dữ liệu (`reader.read()` chỉ báo
lỗi khi thiếu cột khai báo, không quan tâm dư cột).

## 17 cột đang dùng (giữ lại)

| # | Cột OBC | Cột CSDL (`core.dim_customer`) | Ghi chú |
|---|---|---|---|
| 1 | 得意先コード | customer_code | khoá — TEXT, có số 0 đầu |
| 2 | 得意先名 | customer_name | tên chứa nhãn `※廃業※`/`※取引停止※` (xem `db/migrations/016_*.sql`) |
| 3 | 支店名 | branch_name | |
| 4 | ランクコード | rank_code | chỉ cần MÃ, không cần `ランク名` |
| 5 | 業種・カテゴリーコード | category_code | chỉ cần MÃ |
| 6 | 注文アプリコード | order_app_code | mã app đặt hàng web — KHÁC 担当者 OBC, xem bẫy đã biết trong `CLAUDE.md` |
| 7 | 売上主担当者コード | salesperson_code | chỉ cần MÃ, không cần `売上主担当者名` |
| 8 | 売価No.コード | price_level_code | |
| 9 | 請求締日コード | closing_day_code | chỉ cần MÃ, không cần `請求締日名` |
| 10 | 請求先コード | billing_customer_code | **có thể KHÁC 得意先コード** — bên nhận hoá đơn |
| 11 | 郵便番号 | postcode | TEXT — mã bưu chính Hokkaido có số 0 đầu |
| 12 | 都道府県 | prefecture | |
| 13 | 市区町村 | city | |
| 14 | 番地 | address | |
| 15 | 電話番号 | phone | |
| 16 | インボイス登録番号 | invoice_reg_no | |
| 17 | スポット区分コード | spot_flag | |

## 307 cột không dùng (an toàn để xoá)

Không liệt kê hết vì phần lớn là cấu hình nội bộ OBC, không mang thông tin
nghiệp vụ CRM. Theo nhóm lớn:

- **法人番号, 得意先名カナ, 事業所名(カナ), 得意先略称, インデックス, 敬称** — biến
  thể tên/cách gọi, không dùng.
- **ご担当－...** (部署, 電話番号, 役職, 担当者名, 携帯番号, E-Mail) — người liên
  hệ phía khách, hiện không có màn hình nào hiển thị.
- **回収条件１/２/３－...** (~150 cột) — điều kiện & lịch thu tiền chi tiết
  (回収サイト 1-3 × phương thức, ngày lễ, ngày thu dự kiến...). Đây là khối lớn
  nhất, thuộc nghiệp vụ kế toán chi tiết của OBC, không phải dữ liệu CRM.
- **各種フォーム/差出名コード** (見積書, 納品書, 送り状, 請求書 — form + tên người gửi) —
  cấu hình in ấn chứng từ.
  - **振込専用口座番号1-10, 振込依頼人名カナ1-10** — 20 cột tài khoản chuyển khoản
  chuyên dùng, gần như luôn rỗng ở dữ liệu mẫu.
- **主販売取引コード/名 (+ 返品/値引/即時入金 các biến thể), 補助科目, 前受科目,
  非連結科目, 統一伝票...** — mã hạch toán kế toán nội bộ OBC.
- **税抜税込, 売価金額端数処理..., 値入れ元単価...** — cấu hình làm tròn/tính giá
  hiển thị trên chứng từ.

## Nếu sau này cần thêm lại một cột

1. Thêm dòng vào `tokuisaki.columns` trong `config/files.yml`.
2. Nếu cần lưu vào bảng: thêm cột migration mới + cập nhật loader tương ứng
   (không sửa migration đã chạy rồi).
3. Bản gốc đầy đủ 324 cột vẫn còn trong backup OneDrive của công ty
   (`データバックアップ/1．毎月/1.得意先データ/`) — không cần giữ bản đầy đủ ở máy
   cá nhân, cần cột nào thì mở lại bản backup để tra tên cột gốc.
