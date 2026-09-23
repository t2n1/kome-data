# Đợt 6 — Công nợ & thu tiền (sổ 請求先元帳)

Lộ trình §7: "đợt DUY NHẤT động vào pipeline nạp — viết bộ nạp 得意先元帳 / 請求先元帳".
Chủ doanh nghiệp: "làm tiếp tất cả" (2026-09-24).

## 1. Đo file thật trước (rủi ro L2 của lộ trình)

Đo 2026-09-24, chỉ đọc, trên máy (không gửi đi đâu):

| File | Header | Dòng | Ghi chú |
|---|---|---|---|
| `請求先元帳_2026年 5月 1日　～　2026年 7月31日.xlsx` | dòng 6 | 20.427 | 20 cột, có `残高` (số dư chạy); 215 bên nhận hoá đơn |
| `得意先元帳_…` | dòng 6 | 24.477 | 19 cột, **không có** `残高` |
| `入金伝票データ_…` | dòng 1 | 525 | phiếu thu; đã nằm trong 請求先元帳 dưới dạng dòng 入金額 |

Bẫy #4 **đúng với 元帳**: 5 dòng thông tin (帳票名 / 法人名 / 集計期間 / 集計軸項目 /
売上伝票の表示) trước header. Sheet tên `得意先元帳` ở CẢ HAI loại sổ; dòng 集計軸項目
('請求先' / '得意先') mới phân biệt được.

Loại dòng (cột 行タイトル): trống = chi tiết (phiếu bán: 債権額; phiếu thu: 入金額),
`繰越残高` = mang sang, `伝票計` / `［ n月計］` / `【合計】` = tổng phụ.

Đối chiếu: mang sang + 【合計】(債権額 + 債権調整額 − 入金額 − 入金調整額) = 残高 cuối —
**215/215 bên khớp**. Cộng tay 入金額 từng dòng thì **12 bên lệch** (nhóm mã 0090…: phiếu
thu hiện ra mà 残高 không đổi, 【合計】.入金額 = 0). ⇒ số dư LUÔN là cột 残高 của OBC.

Phân bố số dư (bản 5–7/2026): 代引請求 75 bên ≈ ¥93,9M (một mình `代引専用` ≈ ¥93,4M),
末締/翌月末日 17 bên ≈ ¥20,2M, その都度請求 34 bên ≈ ¥8,3M, 末締/翌月10日 12 bên ≈ ¥8,2M,
63 bên số dư âm.

## 2. Phạm vi

- **Nạp** `請求先元帳` (spec `seikyu_motocho`) → `core.fact_ar_ledger`. Nhận cả tên gốc
  OBC (kỳ trong tên) lẫn `_YYYYMMDD`; ngày dữ liệu = cuối kỳ.
- **Không nạp** `得意先元帳` (không có số dư — cùng nội dung) và `入金伝票データ` (đã có
  trong sổ). Cả hai ở lại danh sách "chưa có bộ nạp" với lý do.
- **Màn `/cong-no`** (Công nợ.dc.html), tab Công nợ + ô "Công nợ quá hạn" của hồ sơ
  khách, khối "Tuổi nợ phải thu" + ô "Phải thu quá hạn" của `/`.
- **Dòng tiền & phải trả** vẫn "chưa có": `仕入先元帳` chỉ có một bản 2025, không nạp đều.

## 3. Mô hình

- Mỗi lô = ảnh chụp một kỳ (`period_from/to` đọc từ 集計期間). Không đè lô cũ; mart đọc
  lô có kỳ kết thúc muộn nhất (hoà: lô sau). Hoàn tác xoá theo `batch_id`.
- `kome/so_cai.py` (gọi từ reader khi spec có `so_cai_truc`): kiểm 集計軸項目 (sai →
  cổng 2), đọc kỳ (không đọc được → cổng 2), dòng 行タイトル lạ → cổng 2, đối chiếu
  【合計】 (lệch → cảnh báo cổng 5), bỏ tổng phụ, gắn `line_kind`/`row_seq`.
- `mart.cong_no_ben_tra`: số dư = 残高 dòng cuối; đã thu kỳ = mang sang + nợ + điều
  chỉnh − số dư.
- `mart.cong_no_phieu`: chia số dư dương vào phiếu theo **trả cũ trước** (phần còn nợ
  là của phiếu mới nhất; dư ra = nợ mang sang trước kỳ). Hạn suy từ tên điều kiện, chỉ
  `末締/翌月末日` và `末締/翌月N日`; điều kiện khác → không suy được hạn, không bao giờ
  "quá hạn". Tuổi = ngày phiếu → cuối kỳ sổ (mốc dữ liệu, không phải đồng hồ).

## 4. Lệch gói thiết kế (có chủ ý, màn nói ra)

| Gói thiết kế | Ở đây | Vì sao |
|---|---|---|
| Hoá đơn INV-… | Phiếu bán của sổ | OBC không xuất số hoá đơn |
| "Đã thu" từng hoá đơn | "Đã thu (ước)" theo trả cũ trước | OBC không ghi phiếu nào được trả |
| Ghi nhận thu | Không có | Thu tiền ghi trong OBC (luật số một) |
| Gửi nhắc thu | Nút tắt kèm lý do | Chưa có kênh gửi |
| Vượt hạn mức tín dụng | Khung "chưa có dữ liệu" | OBC không xuất hạn mức |
| Số ngày thu tiền bình quân, mục tiêu thu | Bỏ | Không có định nghĩa/nguồn đo được |
| Tab "Đã thu" | Tab "Theo bên nhận hoá đơn" | Không có phiếu "đã thu" riêng |

Công nợ ghi theo **bên nhận hoá đơn**, không theo từng khách: danh sách khách không
lọc/đếm theo nợ (phân khúc "Nợ quá hạn" trỏ sang màn Công nợ); hồ sơ khách hiện số
của cả bên và nói rõ khi bên đó nhận hoá đơn cho nhiều khách.

## 5. Kiểm

`tests/test_cong_no.py` (13 test, file giả lập đúng cấu trúc đo được — không dùng dữ
liệu khách thật): nhận tên file, giữ/bỏ dòng, cổng 2/5, số dư của OBC + đẳng thức đã
thu (ca 0090…), trả cũ trước (cả phiếu biên nhận một phần và nợ mang sang), hạn hai
mẫu, lô kỳ mới nhất + hoàn tác, ô tổng, màn/API.

**Triển khai:** migration `038_so_cong_no.sql` phải chạy (vai trò `postgres`) TRƯỚC khi
đẩy mã lên Vercel — không thì màn Công nợ và khối Tuổi nợ báo lỗi.
