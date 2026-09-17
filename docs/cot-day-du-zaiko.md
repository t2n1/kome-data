# Cột đầy đủ của file 在庫一覧 (tồn kho) — cái nào đang dùng, cái nào bỏ được

Đối chiếu với bản OBC xuất ngày 2026-09-16 (sheet `在庫一覧表`, header dòng 1,
280 dòng, **71 cột**). File pipeline nạp vào CSDL chỉ dùng khai báo trong
`config/files.yml` (mục `zaiko`), tức **13/71 cột** — 58 cột còn lại có thể
xoá khi tải file OBC về để file nhẹ hơn, không ảnh hưởng gì tới nạp dữ liệu
(`reader.read()` chỉ báo lỗi khi **thiếu** cột khai báo, không quan tâm có
thừa cột hay không).

## 13 cột đang dùng (giữ lại)

| # | Cột OBC | Cột CSDL (`core.fact_inventory_daily`) |
|---|---|---|
| 1 | 商品コード | product_code |
| 2 | 商品名 | product_name |
| 3 | 荷姿区分コード | pack_code |
| 4 | 荷姿区分名 | pack_name (đọc vào nhưng không lưu — xem ghi chú) |
| 5 | 倉庫コード | warehouse_code |
| 6 | 倉庫名 | warehouse_name |
| 7 | 日本語 | name_ja |
| 8 | 単位 | unit |
| 9 | 賞味期限 | best_before |
| 10 | 売上出荷数量 | shipped_qty |
| 11 | 在庫残数 | stock_qty |
| 12 | 在庫単価 | stock_unit_cost |
| 13 | 在庫金額 | stock_value |

Nguồn: `config/files.yml` (khai báo cột) + `kome/loaders/inventory.py` (cột
nào thật sự ghi vào bảng).

## 58 cột không dùng (an toàn để xoá)

在庫回転率, 在庫回転期間, 入数, 繰越残数, 入荷数量, 出荷数量, 仕入入荷数量,
入荷調整数量, 出荷調整数量, 仮入荷数量, 仮入荷戻し数量, 仮出荷数量,
仮出荷戻り数量, 構成品生産着手数量, 構成品生産数量, 部品払出数量,
部品受入着手数量, 部品受入数量, 構成品分解数量, 倉庫振替入荷数量,
倉庫振替出荷数量, 荷姿振替入荷数量, 荷姿振替出荷数量, 他勘定振替出荷数量,
棚卸入荷数量, 棚卸出荷数量, 現品残数, 未仕入入荷残数, 販売可能残数,
未売上出荷残数, 仮入荷残数, 仮出荷残数, 仕入入荷予定残数, 売上出荷予定残数,
仮入荷予定残数, 仮出荷予定残数, 販売可能予定残数, 棚卸資産評価方法,
端数処理方法, 現品バ　ラ（小：単品）残数, 販売可能バ　ラ（小：単品）残数,
在庫バ　ラ（小：単品）残数, 販売可能予定バ　ラ（小：単品）残数,
主仕入荷姿区分コード, 主仕入荷姿区分名, 主仕入荷姿区分単位,
現品残数（主仕入荷姿区分）, 販売可能残数（主仕入荷姿区分）,
在庫残数（主仕入荷姿区分）, 預り数量, 預り品戻し数量, 預り残数, 最終出荷日,
最終入荷日, 滞留期間（日）, 滞留期間（月）, 在庫回転数量, 平均在庫残数

Đa số là các biến động số lượng theo loại nghiệp vụ (入荷/出荷/仮入荷/棚卸/構成品…)
và các số tồn quy theo 荷姿 khác — hiện không phục vụ trang nào trong web app.

## Nếu sau này cần thêm lại một cột

1. Thêm dòng vào `zaiko.columns` trong `config/files.yml` (đúng tên cột OBC ở
   trên → tên cột CSDL muốn dùng).
2. Nếu cần lưu vào bảng: thêm cột trong migration mới (`db/migrations/0xx_*.sql`
   — không sửa `005_inventory.sql` đã chạy rồi) và cập nhật
   `kome/loaders/inventory.py` để ghi cột đó.
3. Nhớ xuất lại file OBC đầy đủ (không xoá cột đó) từ lần xuất kế tiếp.

## Cách xuất từ OBC (mục 数量/金額)

Tick **「在庫管理する商品をすべて出力する」** (xuất tất cả) — 3 dòng lọc bên dưới
(`在庫残数 が 0.0001 以上`, `在庫残数 がマイナス`, `集計期間内に入出荷がある`) để mờ/mặc
định, KHÔNG dùng, vì chúng lọc mất tồn = 0 và tồn ÂM (tồn âm là tín hiệu bất
thường cần giữ, giống nguyên tắc 赤伝 không được lọc bỏ). Xem file mẫu ngày
2026-09-16, xuất kiểu này ra **2.070 dòng** (so với 280 dòng của bản xuất có
lọc theo mã sản phẩm bên dưới lần trước).

## Lọc theo nghiệp vụ (row-level, không phải cột) — do người dùng giải thích, xác nhận trên dữ liệu thật

Ba luật dưới đây là quy ước nghiệp vụ của công ty khi ĐỌC file tồn kho, không
phải do OBC tự lọc — nghĩa là **vẫn xuất đầy đủ tất cả dòng từ OBC**, việc lọc
diễn ra sau, khi dùng dữ liệu (đọc báo cáo tay hoặc tính năng CRM sau này).

| # | Luật | Ý nghĩa | Đếm trên file mẫu 2.070 dòng |
|---|---|---|---|
| 1 | `商品名` có tiền tố `※終売※` | Sản phẩm đã ngừng bán / đang ngừng bán | 651 dòng khớp |
| 2 | `単位` chỉ lấy `ケース` và `KG` | Công ty bán theo thùng — các đơn vị khác (袋 bao, 個 cái, 本 chai, 缶 lon, コンテナ container, hoặc rỗng) không dùng | 1.146 (ケース) + 29 (KG) = 1.175 dòng khớp; 895 dòng đơn vị khác bị loại |
| 3 | `商品コード` có hậu tố `_01` hoặc `_02` | Bỏ qua (biến thể mã, không phải mã chính) | 211 dòng khớp |

Áp cả 3 luật cùng lúc (có chồng lấn giữa các luật) trên file mẫu: **2.070 → 631
dòng còn lại** là dữ liệu tồn kho "sạch" thật sự cần dùng.

**Lưu ý:** đây là luật LỌC KHI DÙNG DỮ LIỆU, không phải luật để OBC xuất thiếu
— tương tự cách `mart` lọc khách `※廃業※`/`※取引停止※` sau khi đã nạp đủ dữ liệu
gốc vào `core` (xem `db/migrations/016_*.sql`, phần "Bất biến" ở
`CLAUDE.md`), KHÔNG lọc ở bước xuất/nạp. Nếu sau này xây tính năng đọc tồn
kho (report hoặc CRM), áp 3 luật này ở tầng `mart/`, không sửa
`kome/loaders/inventory.py` hay `config/files.yml` — pipeline vẫn nạp NGUYÊN
mọi dòng vào `core.fact_inventory_daily` để không mất dữ liệu gốc.
