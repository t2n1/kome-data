-- 074 — Campaign tuần trên web (đặc tả docs/superpowers/specs/2026-10-23-campaign-tuan-design.md).
--
-- Kế hoạch campaign + bản soát tồn / lịch hàng về được TÍNH ở máy công ty (Google Sheet + Cybozu chỉ đọc được từ đó)
-- rồi gửi lên web bằng tài khoản obc-bot (POST /api/kho-du-lieu/campaign). Web chỉ lưu và hiện bản mới nhất — không
-- tính lại, không ghi core, không ghi sheet. Mỗi lần gửi một dòng; lần gửi xoá dòng cũ hơn 30 ngày (luôn giữ dòng mới
-- nhất) nên bảng không phình. KHÔNG có trong anh_chup._PHIEN_BAN: không ảnh chụp nào đọc bảng này (chuông ghép mục
-- campaign NGOÀI ảnh chụp — kome/web/api.py::thong_bao).

CREATE TABLE app.campaign_soat (
    id       bigserial PRIMARY KEY,
    nop_luc  timestamptz NOT NULL DEFAULT now(),
    nop_boi  bigint REFERENCES app.nguoi_dung(id) ON DELETE SET NULL,
    du_lieu  jsonb NOT NULL CHECK (jsonb_typeof(du_lieu) = 'object')
);
