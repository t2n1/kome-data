# Cột cần giữ của file 売上伝票データ (bán hàng)

Theo khai báo pipeline thật (`config/files.yml` mục `uriage`, sheet
`売上伝票データ作成`, header dòng 1). File gốc có **271 cột** (~92.825 dòng/quý —
xem `docs/superpowers/specs/2026-09-16-kome-data-platform-design.md`), pipeline
chỉ dùng **25 cột**.

## 25 cột cần giữ

| # | Cột OBC | Cột CSDL (`core.fact_sales`) | Ghi chú |
|---|---|---|---|
| 1 | 伝票No. | slip_no | khoá cùng với line_seq |
| 2 | 明細行番号 | line_seq | số thứ tự dòng trong phiếu — ngoại lệ duy nhất KHÔNG coi là mã tra cứu chéo hệ thống dù có hậu tố コード-giống, nên lưu dạng số nguyên |
| 3 | 売上日付 | sales_date | **bắt buộc đọc được** — lỗi/rỗng phải bị chặn ở cổng 3, không để lọt xuống CSDL |
| 4 | 請求日付 | billing_date | |
| 5 | 伝票区分 | slip_type | phân biệt phiếu thường / 赤伝 (phiếu đỏ, số ÂM — KHÔNG được lọc bỏ) |
| 6 | 得意先コード | customer_code | |
| 7 | 請求先コード | billing_customer_code | có thể KHÁC 得意先コード |
| 8 | 担当者コード | salesperson_code | 5 người OBC — KHÁC 7 tài khoản web đặt hàng |
| 9 | 部門コード | department_code | |
| 10 | 直送先コード | shipto_code | |
| 11 | 商品コード | product_code | |
| 12 | 荷姿コード | pack_code | |
| 13 | 入数 | case_qty | |
| 14 | 数量 | qty | có phần thập phân (vd 83.75) |
| 15 | 単価 | unit_price | |
| 16 | 単位原価 | unit_cost | |
| 17 | 金額 | amount | **cột doanh thu thật của dòng** — đừng nhầm với 入金額１ (gần như luôn 0) |
| 18 | 消費税額 | tax_amount | |
| 19 | 原価 | cost | |
| 20 | 粗利益 | gross_profit | lấy làm chuẩn lợi nhuận (khớp tuyệt đối với 売上明細表 sau khử trùng) |
| 21 | 粗利益率 | gross_margin | |
| 22 | 消費税率 | tax_rate | |
| 23 | 入金額１ | paid_amount | |
| 24 | 入金伝票No.１ | payment_slip_no | nối được đơn bán ↔ phiếu thu — lý do chính chọn file này thay vì 売上明細表 |
| 25 | 請求締日コード | closing_day_code | |

## Bẫy khi đọc file này (khác biệt so với 2 file trước)

1. **Mỗi dòng hàng xuất HAI LẦN** trong file gốc (một lần dưới mục con `出荷内訳`,
   một lần dưới `明細按分`, cùng `伝票No.`+`明細行番号`, cùng `金額`/`粗利益`) — phải
   khử trùng theo khoá `[slip_no, line_seq]` (`dedup_on_keys: true` trong
   config, xem `kome/reader.py::dedup_on_keys`), nếu không doanh thu sẽ tính
   gấp ~2,16 lần thực tế.
2. **`sales_date`** không đọc được (rỗng/rác) phải bị chặn ngay ở cổng 3 —
   không được để lọt xuống rồi báo lỗi khoá ngoại `core.dim_date` sau khi đã
   lưu batch.
3. Cột tổng tiền dùng cho `/health` và cổng 4 là **`金額`**, không phải cột
   cuối danh sách (`入金額１`, gần như luôn 0).

## 246 cột không dùng

Không liệt kê — quá nhiều và chưa khảo sát chi tiết như 2 file trước (chưa có
file mẫu 271 cột đầy đủ trong tay). Khi có file thật, đối chiếu lại bảng 25
cột ở trên để biết cột nào bỏ được.

## Đối chiếu thật với 売上明細表 (nguồn dự phòng, Task ngày 2026-09-17)

Cùng ngày 2026-08-03, sau khử trùng `売上伝票データ` theo (slip_no, line_seq):

| | 売上伝票データ | 売上明細表 | Lệch |
|---|---|---|---|
| Số dòng | 926 | 926 | 0 |
| 消費税額 | 509.889 | 509.889 | 0 |
| 原価 | 4.260.179 | 4.260.179 | 0 |
| 粗利益 | 1.983.539 | 1.983.539 | 0 |
| 金額/税込純売上高 | 6.753.717 | 6.753.662 | 55 (0,0008%) |

Kết luận: cả hai nguồn đáng tin ở mức số liệu. `売上伝票データ` vẫn là nguồn
CHÍNH vì có `明細行番号` (khoá dòng thật) và `入金額１`/`入金伝票No.１` (nối phiếu
thu). `売上明細表` chỉ dùng khi KHÔNG lấy được `売上伝票データ` — xem
`db/migrations/017_nguon_ban_hang_thay_the.sql` và `kome/loaders/sales.py`.

## Mẫu xuất hằng ngày 20 cột (2026-09-25, migration 046)

Bản xuất 売上明細表 hằng ngày hiện chỉ có **20 cột** (bản 2026-08-03 có 117 cột;
20 cột đầu giống hệt). Tám cột bị cắt: 伝票区分, 部門コード, 入数, 単位原価,
税込純売上高, 消費税額, 売上原価, 消費税率. `config/files.yml` mục `meisai` nay chỉ
khai cột có trong bản 20 cột, nên nhận được cả bản mới lẫn bản cũ.

- `amount` của nguồn meisai = **税抜純売上高** (chưa thuế), `tax_amount` = 0 (ép
  trong `load_meisai`). Doanh thu thuần `amount - tax_amount` không đổi nghĩa —
  đo trên bản 117 cột: 税抜純売上高 = 税込 − 消費税額 ở 926/926 dòng. `amount` THÔ
  và tổng tiền lô (`meta.ingest_batch.total_amount`) của meisai là số CHƯA thuế,
  còn của uriage là số CÓ thuế.
- `case_qty`, `unit_cost`, `cost`, `slip_type`, `department_code`, `tax_rate`
  của dòng meisai là NULL (không có trong file) — không phải 0.

**Tên file khi xuất `売上明細表` để nạp qua `/nap`:** phải đặt tên đúng mẫu
`売上明細表_YYYYMMDD.xlsx` (giống mọi loại file khác) — bản test gửi trong
phiên này tên là `売上明細表.xlsx` (không có ngày), cổng 1 sẽ chặn nếu nạp
nguyên tên đó.
