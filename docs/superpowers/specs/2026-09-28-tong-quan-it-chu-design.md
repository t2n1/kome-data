# Tổng quan ít chữ — nhiều hình, chi tiết trong ô nổi

Ngày: 2026-09-28 · Chủ DN duyệt thiết kế trong phiên cùng ngày (hướng 2, luật chữ C).
Kế thừa: `2026-09-23-giao-dien-react-design.md`, `2026-09-28-ky-so-sanh-toan-web-design.md`.
Phạm vi: CHỈ màn `/` (Tổng quan). Màn khác làm sau, dùng lại linh kiện chung của §3.

## 1. Vấn đề

Tổng quan hiện là một trang dài nhiều chữ: mỗi ô số có 1–2 dòng phụ, mỗi khối có dòng giải thích
ở đầu và ở cuối, và sáu khối là BẢNG (theo tháng 7 cột, tháng này chưa mua 40 dòng, khách mới 29
dòng, danh sách khách 60 dòng × 8 cột, ngành, sắp hết hạn). Người đọc phải đọc chữ mới thấy công ty
đang thế nào. Chủ DN muốn: ít chữ nhất có thể, nhiều biểu đồ hơn, chi tiết chỉ hiện khi rê chuột
(hoặc chạm, trên điện thoại).

## 2. Nguyên tắc

1. **Mỗi khối: một hình + tối đa một số lớn.** Mọi con số phụ nằm trong ô nổi của chính thứ nó
   giải thích (số lớn, thanh, chấm, điểm biểu đồ).
2. **Không bỏ số, chỉ dời chỗ.** Mọi con số đang hiện hôm nay vẫn tới được bằng một lần rê / chạm,
   hoặc qua liên kết "Mở →" của khối (danh sách đầy đủ). Không bảng nào ở lại Tổng quan (chủ DN chốt).
3. **Không đụng máy chủ.** Mọi khối dùng đúng dữ liệu `/api/tong-quan/<khối>` đang trả; không thêm
   lượt hỏi, không định nghĩa chỉ số mới. `/` vẫn ≤ 9 lượt, `NGAN_SACH_TRUY_VAN` không đổi. Nếu khi
   làm thấy thiếu một trường cho ô nổi, chỉ được THÊM trường vào kết quả của câu SQL sẵn có.
4. **Chạm cũng dùng được như chuột** (chưa rõ nhân viên có dùng điện thoại không → thiết kế cho cả hai).

## 3. Linh kiện chung (`giao_dien/src/chung/`)

### 3.1 `ONoi` — ô nổi cho mọi thứ không phải `BieuDo`
- Chuột: rê vào → hiện; rời → ẩn.
- Chạm (`pointerType === "touch"`): chạm lần 1 → hiện; chạm lần 2 cùng phần tử → đi liên kết (nếu
  có); chạm ra ngoài hoặc Esc → đóng. Chỉ một ô nổi mở tại một thời điểm.
- Bàn phím: phần tử có `tabIndex=0`; focus → hiện, Enter → đi liên kết.
- Vị trí: bám phần tử, tự lật lên/xuống, không tràn khỏi khung nhìn (điện thoại 375 px).
- Nội dung: tiêu đề đậm + các dòng `nhãn · giá trị` (cùng kiểu `.bd-noi` của `BieuDo`, dùng chung CSS).
- `role="tooltip"` + `aria-describedby` — trình đọc màn hình vẫn đọc được chi tiết.

### 3.2 `BieuDo` — sửa hành vi chạm
Hiện tại chạm một lần là vừa chọn điểm vừa gọi `onBam`. Đổi: với chạm, lần 1 chỉ chọn điểm (hiện ô
nổi), lần 2 cùng điểm mới gọi `onBam`. Chuột giữ nguyên (bấm là đi). Ô nổi đã có, không đổi nội dung.

### 3.3 `ThanhNgang` — thanh xếp hạng
Một dòng = tên ngắn (cắt `…`) · thanh · một số · (tuỳ chọn) % so kỳ. Vạch đứt kỳ so dùng lại
`VachSoSanh`. Mỗi dòng bọc `ONoi` với các dòng chi tiết do nơi gọi truyền vào; có `href` thì dòng là
liên kết. Thang: chung cho mọi dòng (max của thực tế và kỳ so). Giá trị ÂM (赤伝): thanh độ rộng 0,
số vẫn in số âm thật — không kẹp số.

### 3.4 `ThanhChong` — một thanh nhiều khúc
Nâng từ `.sk-thanh` của Sức khoẻ khách. Mỗi khúc: màu, nhãn, số đếm, `href` hoặc `onBam`; bọc
`ONoi` ("Cần gọi lại: 173 khách · 13%"). Chú giải = chấm màu + số, không câu chữ. Khúc 0 không vẽ
nhưng vẫn có trong chú giải. Tổng độ rộng = 100% của các khúc > 0.

### 3.5 `Khoi` — hai thuộc tính chữ mới, bỏ `phu` tự do
- `cach_tinh?: ReactNode` → biểu tượng **ⓘ** cạnh tiêu đề, nội dung trong `ONoi`.
- `canh_bao?: ReactNode` → một dòng màu cảnh báo cuối khối, LUÔN hiện.
- `phu` chỉ còn nhận **nhãn kỳ so** và nhãn mốc ngắn (≤ 1 dòng, không câu giải thích).
- `ChuaCoDuLieu`: khung thấp, tiêu đề + nhãn "chưa có"; `ly_do` vào ⓘ.

## 4. Luật chữ (lựa chọn C — thay một phần bất biến cũ)

| Loại chữ | Hiện thế nào |
|---|---|
| Tiêu đề khối | ≤ 4 từ (+ nhãn khoảng xem nếu có) |
| Nhãn kỳ so ("so cùng tháng năm trước") | LUÔN hiện, mờ, cạnh số % |
| Cảnh báo ngoại lệ đang xảy ra ("tháng đang chạy chưa đủ ngày", "kỳ so không lệch tròn quý", "không có dữ liệu để so", "kỳ chưa đủ 12 tháng" khi kỳ cuối thật sự thiếu) | LUÔN hiện — `Khoi.canh_bao` |
| Định nghĩa cách tính (`cach_tinh` máy chủ gửi, "Im lặng = ngày ÷ nhịp", "biên gộp = tổng ÷ tổng", "vạch đen = mốc…", "Đã thu (ước) — trả cũ trước") | ⓘ — `Khoi.cach_tinh` |
| Dòng phụ dưới số | ô nổi của con số |
| Lý do "chưa có dữ liệu" | ⓘ |

Phân biệt: câu **đổi theo dữ liệu và chỉ xuất hiện khi có chuyện** là cảnh báo; câu **luôn giống nhau**
là định nghĩa. CLAUDE.md thêm một bất biến (chủ DN chốt 2026-09-28): trên Tổng quan, câu định nghĩa
cách tính nằm sau ⓘ (vẫn là MỘT chỗ đọc `cach_tinh` của máy chủ — không chép câu vào giao diện), câu
ngoại lệ luôn hiện. Các bất biến "in câu cách tính dưới khối" (036 `khach_thang.CACH_TINH`, 044
`CACH_TINH_KHACH_MOI`, 038 `CACH_TINH["fifo"]`) được sửa chữ "in dưới khối" → "trong ⓘ của khối" ở
Tổng quan; ở màn khác giữ nguyên cho tới khi màn đó được làm lại.

## 5. Từng khối

| Khối | Sau khi đổi |
|---|---|
| `kpi` Chỉ số | Mỗi ô: nhãn ngắn · số lớn · đường nhỏ · % kỳ so (nhãn kỳ so mờ). Dòng phụ ("98 im lặng · 30 rời bỏ", "0 hết · 0 cận hạn · 0 quá hạn", "thiếu ¥6,1M so mốc 89,5%", "n phiếu · tổng phải thu") vào `ONoi`. Ô "Phải trả 7 ngày" chưa có → ô mờ nhỏ, lý do ⓘ |
| `ns_thang` Ngân sách | Một số lớn (tiến độ %); "thiếu so mốc", "cần bán mỗi ngày" vào `ONoi` của số đó. Thanh công ty + từng người (giữ `ThanhMoc` và vạch mốc) + biểu đồ luỹ kế giữ. "Vạch đen = mốc…" → ⓘ |
| `theo_thang` Theo tháng | BỎ bảng. Ô nổi `BieuDo` thêm %NS, biên gộp, số khách. Bốn ô số → một hàng chữ nhỏ (luỹ kế · % so kỳ · tháng đạt NS · tháng cao nhất), chi tiết ("chênh", "biên gộp") vào `ONoi`. "Tháng đang chạy chưa đủ ngày…" = cảnh báo |
| `xu_huong` Xu hướng | Giữ biểu đồ; ba ô số → một hàng nhỏ trên biểu đồ |
| `viec_hom_nay` Việc hôm nay | `ThanhChong` đếm theo `tag` (bấm khúc = lọc danh sách). Dòng: ô tích · nhãn màu · TÊN khách (bỏ "Gọi … — im 53 ngày" khỏi dòng; `chu` đầy đủ + `han` vào `ONoi`). Hiện 5 dòng gấp nhất (`gap` → `canh` → `thuong`), nút "+n việc". Dấu "xong" (localStorage) giữ nguyên khoá. "Chưa gom được việc từ …" → ⓘ |
| `thang_nay_chua_mua` | Số lớn (`dem.tre`) + `ThanhNgang` top 10 (thanh = `tb_thang`, vạch = `thang_truoc`). "mua 3/3 tháng", đã mua tháng này / tháng trước cùng ngày, "+n chưa tới ngày" vào `ONoi` của số lớn / dòng. `cach_tinh` → ⓘ. Chip "Chỉ khách của tôi" giữ |
| `khach_moi` Khách mới | Số lớn + `ThanhChong` đã có đơn / chưa có đơn (`ONoi` của khúc "chưa có đơn" liệt kê tối đa 10 tên) + biểu đồ 12 tháng. BỎ bảng và chip. `cach_tinh` → ⓘ; % so kỳ cạnh số lớn |
| `suc_khoe_khach` | Số lớn + `ThanhChong` (liên kết giữ `?loc=${n}&tat_ca=1`); câu "so với nhịp của CHÍNH từng khách" → ⓘ |
| `danh_sach_khach` | `ThanhNgang` top 15 theo `thang_nay`, vạch đứt = kỳ so, màu thanh theo trạng thái (đỏ gọi ngay / cam trong tuần / xanh). `ONoi`: 12 tháng, im lặng ×, nhịp, phụ trách, việc cần làm. Bỏ bảng + sắp cột (dùng "Mở →"). "Im lặng = …" → ⓘ |
| `so_sanh_sale` Theo sale | `ThanhNgang`, giữ màu tiến độ + vạch kỳ so; câu "% là tiến độ…" → ⓘ |
| `hieu_suat_nganh` Ngành | `ThanhNgang` theo tỷ trọng + % so kỳ; doanh thu, biên gộp vào `ONoi` |
| `han_su_dung` Sắp hết hạn | Dải thời gian: trục ngang = `con_lai` (vùng quá hạn · 0–30 · 30–60 · 60+), mỗi lô một chấm, bán kính ∝ √giá trị tồn, màu theo cách xử lý hiện có. `ONoi`: tên, lô (`ten_kho`), hạn, số lượng, giá trị, cách xử lý; bấm → `/san-pham/{mã}`. Nhãn đầu khối giữ "n mã dưới 30 ngày" |
| `cong_no` Tuổi nợ | Số lớn quá hạn + `ThanhChong` 5 nhóm tuổi (liên kết `/cong-no?nhom=`); "nợ lâu nhất" vào `ONoi`. `cach_tinh` → ⓘ |
| `tuong_quan`, `tang_truong`, `bien_loi_nhuan` | Đã là biểu đồ: dòng phụ → ⓘ; "Biên RÒNG chưa có" → ⓘ; "kỳ chưa đủ 12 tháng" chỉ hiện (cảnh báo) khi kỳ cuối < 12 tháng |
| `don_hang` Nạp / phiếu | Giữ hai danh sách (chỗ đối chiếu với file); tên file vào `ONoi` |
| 5 khối chưa có dữ liệu | Khung thấp, lý do → ⓘ |

**Chiều cao mặc định** (`kome/web/bo_cuc.py::_KHOI_DAY_DU`) — lệch có chủ ý khỏi `BO_CUC_MAC_DINH`
của gói thiết kế, ghi chú thích tại chỗ: `theo_thang` 3→2, `viec_hom_nay` 3→2, `thang_nay_chua_mua`
3→2, `khach_moi` 3→2, 5 khối chưa có dữ liệu → 1. Bố cục đã lưu (`app.bang_tong_quan`) KHÔNG tự đổi;
người dùng bấm "Đặt lại bố cục" nếu muốn. Test nào ghim kích thước mặc định thì sửa cùng lúc.

## 6. Kiểm thử

- **Vitest** (`giao_dien/`): `ONoi` (chuột hiện/ẩn; chạm 1 hiện, chạm 2 đi liên kết; Esc / chạm
  ngoài đóng; chỉ một ô mở); `ThanhNgang` (tỷ lệ đúng, giá trị âm → rộng 0 nhưng in số âm);
  `ThanhChong` (Σ khúc = 100%, khúc 0 không vẽ nhưng có trong chú giải); `BieuDo` chạm 2 lần mới `onBam`.
- **Python, quét mã nguồn** (nếp `tests/test_tong_quan.py:238`): `tong_quan/khoi.tsx` không còn
  `className="phu"` và không còn `<table`; mọi `d.cach_tinh` đi qua `cach_tinh=` của `Khoi`.
- Test canh cũ phải xanh (liên kết `?loc=${n}&tat_ca=1`, `TN.cong_no && <OKpiCongNo`, ngân sách
  lượt hỏi, `test_ban_build_khop_ma_nguon`); chuỗi nào đổi thì sửa test giữ nguyên ý.
- `npm run build` + `npm test` trong `giao_dien/`, rồi `pytest` toàn bộ.
- Kiểm bằng mắt trên bản xem thử: 1440 / 768 / 375 (chế độ chạm), sáng + tối; ảnh trước / sau gửi chủ DN.

## 7. Ngoài phạm vi

Báo cáo, Khách hàng, Sản phẩm, Kho hàng, Công nợ, Dự báo… — làm sau khi chủ DN duyệt Tổng quan, dùng
lại §3. Không đổi dữ liệu, API, migration.
