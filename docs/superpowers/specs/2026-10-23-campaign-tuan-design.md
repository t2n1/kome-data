# Campaign tuần trên web (`/campaign`) — đặc tả

Người dùng: グエン (販売促進課). Chốt 2026-10-23 ("oke làm hết đi").

## Bài toán
Kế hoạch campaign tuần (Thứ Sáu → Thứ Năm, giá sale = cột セール = giá sàn của 値段管理) và việc soát tồn + lịch hàng về
mỗi ngày đang chạy bằng script trên máy công ty (`raw_archive/campaign_sheet/phan_tich/soat_ngay.py`, `lap_tuan.py`)
và ra file trên OneDrive. Người dùng muốn xem và lấy dữ liệu đó **trên kome-data.vercel.app**. Sheet
キャンペーン管理シート vẫn là bản cho sếp xem — người dùng tự dán dữ liệu vào sheet.

## Quyết định
1. **Nguồn vẫn ở máy công ty.** Google Sheet (tài khoản dịch vụ) và Cybozu (tài khoản グエン) chỉ đọc được từ máy
   công ty; khoá KHÔNG lên Vercel. Tác vụ `KOME Soat campaign` (T2–T6 8:30 + 14:00) chạy soát + lập kế hoạch rồi
   **gửi kết quả lên web** bằng tài khoản web `obc-bot` (cờ `duoc_vao_kho_du_lieu`, mật khẩu trong Windows Credential
   Manager — cùng nếp `obc_bot`).
2. **Web chỉ lưu và hiện bản mới nhất.** Bảng `app.campaign_soat` (migration 074): mỗi lần gửi một dòng
   `(id, nop_luc, nop_boi, du_lieu jsonb)`. Web không tính lại gì — số, nhóm, lý do là của script. Giữ 30 ngày (lần gửi
   xoá dòng cũ hơn, luôn giữ dòng mới nhất). Không ghi `core`, không ghi sheet.
3. **API.**
   - `POST /api/kho-du-lieu/campaign` (JSON, ≤ 2 MB): dưới `DUONG_KHO_DU_LIEU` nên middleware gác bằng
     `duoc_vao_kho_du_lieu`. Kiểm hình dạng (`kome/campaign.py::kiem`, `phien_ban = 1`) rồi INSERT. 1 giao dịch.
   - `GET /api/campaign`: dòng mới nhất (1 lượt hỏi, không qua ảnh chụp — bảng nhỏ, đọc thẳng; ETag = id).
   - Chuông (`/api/thong-bao`): ghép thêm mục campaign NGOÀI ảnh chụp (1 lượt hỏi thêm) — nên `app.campaign_soat`
     KHÔNG cần vào `anh_chup._PHIEN_BAN` (không ảnh chụp nào đọc nó; thêm vào thì 2 lần/ngày mọi ảnh chụp nặng
     phải tính lại vì một thứ chúng không đọc).
4. **Trang `/campaign` "Campaign tuần"** (nhóm HẰNG NGÀY, mọi người đăng nhập xem được):
   - Tab **Kế hoạch đề xuất** (mặc định): mỗi tuần chưa có trên 値段管理 một khối; mã chia nhóm Ưu tiên · Đẩy hạn ·
     Theo nhịp · Cân nhịp (được chọn sẵn) · Không chạy · Nghỉ nhịp (bỏ chọn). Ô tick đổi phần sẽ chép — KHÔNG lưu
     (đổi trang là về đề xuất). Ba nút chép: **cột A–B** (週目 · 期間, mỗi mã một dòng) · **cột F** (商品コード) ·
     **cột tuần của 値段管理** (đúng thứ tự dòng 3→ của 値段管理, ô trống = không chạy). Không chép cột C–E (hình /
     công thức) — dán đè là mất công thức.
   - Tab **Soát hằng ngày** (`?tab=soat`): lịch hàng về đổi · mã cần xem theo tuần (★ = mới phát sinh) · lô quá ngày
     chưa nhập kho · ngày lệch OBC ↔ Cybozu · gợi ý.
   - Đầu trang: lúc gửi; bản soát cũ hơn 1 ngày làm việc (> 36 giờ) → dải cảnh báo.
5. **Chuông:** mã cần xem (THIẾU HÀNG = gấp, còn lại = cảnh) của tuần đang chạy và tuần bắt đầu trong 8 ngày tới,
   tối đa 6, mã thông báo ổn định `campaign-<tuần>-<mã>-<phán định>` (đọc rồi thì ẩn tới khi phán định đổi); thêm một
   mục khi lịch hàng về đổi.

## Dạng dữ liệu (`phien_ban = 1`)
```
{phien_ban, lap_luc, nguon: str, thu_tu_gia: [mã | ""],
 ke_hoach: [{tu, den, tab, tuan_so, ky, ma: [{ma, ten, nhom, ly, chon}]}],
 soat: {lan_truoc, lich_doi: [{kieu, ngay, trang_thai, tieu_de, truoc, ma: [..]}],
        tuan: [{tu, den, so_ma, dong: [{ma, ten, pd, ly, moi, off}]}],
        lo_qua_han: [{ma, sl, ngay, trang_thai, cybozu}], lo_lech: [{ma, sl, ngay_obc, ngay, trang_thai, cybozu}],
        khong_cybozu: [{ma, ngay}], goi_y: [{ma, ten, ton, con_ngay, lo_ngay, lo_sl, trang_thai, cach}]}}
```
`nhom` ∈ uu_tien / day_han / thuong / can_nhip / loai / nghi; `pd` ∈ THIẾU HÀNG / PHỤ THUỘC LÔ CHƯA CHỐT / ?.

## Không làm (lần này)
- Lưu lựa chọn của người dùng trên web; ghi ngược vào sheet.
- Nạp đơn đặt hàng OBC (入荷更新) vào kho dữ liệu / tab "Hàng đang về" (dự án A riêng).
- Giá vốn theo OBC (script vẫn dùng 単価 của sheet).

## Test
`tests/test_campaign.py`: kiểm hình dạng (thiếu khoá / sai kiểu / quá cỡ → 400) · gửi cần cờ kho dữ liệu (403) ·
GET trả bản mới nhất, chưa có → `du_lieu: null` · giữ 30 ngày nhưng không xoá dòng mới nhất · chuông chỉ lấy tuần
đang chạy / sắp chạy · trang + mục thanh bên có mặt. `giao_dien/src/campaign/chep.test.ts`: ba chuỗi chép.
