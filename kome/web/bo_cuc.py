"""Bố cục trang Tổng quan theo từng tài khoản (migration 034).

Theo gói thiết kế Dashboard.dc.html: lưới 3 cột, mỗi khối rộng 1–3 cột và cao
1–4 hàng (hàng tối thiểu 150px, lưới tự lấp chỗ trống), kéo để đổi chỗ, kéo
góc để đổi kích thước, ẩn/hiện từng khối. Khác gói thiết kế ở chỗ lưu: gói
ghi localStorage, ta ghi `app.nguoi_dung.bo_cuc_tong_quan` — xem chú thích
đầu migration 034.

Module này KHÔNG tin dữ liệu đến từ trình duyệt: mọi bố cục đi qua
`chuan_hoa` cả lúc GHI lẫn lúc ĐỌC. Lúc đọc là để dòng lưu từ trước khi code
thêm một khối mới vẫn dùng được — khối mới tự nối vào cuối, thay vì như gói
thiết kế (bố cục lưu thiếu một khối là vứt cả bố cục về mặc định).

Thêm một khối: thêm MỘT dòng vào KHOI (và macro cùng tên trong
tong_quan.html). Có test canh hai bên khớp nhau.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

RONG_TOI_DA = 3   # số cột của lưới — đổi là đổi cả CSS `.luoi-tq` và tong_quan.js
CAO_TOI_DA = 4

# (mã, nhãn, rộng mặc định, cao mặc định) — thứ tự là thứ tự mặc định.
KHOI = (
    ("chi_so", "Chỉ số tháng đến hôm nay", 3, 1),
    ("ngan_sach", "Tiến độ ngân sách tháng", 3, 1),
    ("xu_huong", "Xu hướng 30 ngày", 2, 2),
    ("suc_khoe", "Sức khoẻ khách hàng", 1, 2),
    ("can_goi", "Cần gọi hôm nay", 2, 2),
    ("can_han", "Hàng cận hạn", 1, 2),
)
NHAN = {k[0]: k[1] for k in KHOI}
_MAC_DINH = {k[0]: (k[2], k[3]) for k in KHOI}

# Một bố cục hợp lệ không bao giờ dài hơn vài trăm byte; chặn thân yêu cầu
# lớn để một POST rác không bắt máy chủ phân tích cả megabyte JSON.
DAI_TOI_DA = 4096


@dataclass(frozen=True)
class O:
    id: str
    rong: int
    cao: int
    an: bool = False

    @property
    def nhan(self) -> str:
        return NHAN[self.id]

    def dict(self) -> dict:
        return {"id": self.id, "rong": self.rong, "cao": self.cao, "an": self.an}


def mac_dinh() -> list[O]:
    return [O(k, r, c) for k, _, r, c in KHOI]


def _so(v, thap: int, cao: int, mac: int) -> int:
    # bool là int trong Python — `True` không được hiểu thành rộng 1.
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return mac
    return max(thap, min(cao, int(v)))


def chuan_hoa(tho) -> list[O]:
    """Bố cục bất kỳ (list/JSON/None/rác) -> bố cục hợp lệ ĐỦ mọi khối.

    - chỉ giữ mã khối đã biết, lần xuất hiện ĐẦU TIÊN (trùng thì bỏ);
    - rộng kẹp về 1..3, cao về 1..4; kiểu sai thì lấy mặc định của khối;
    - khối còn thiếu nối vào CUỐI với kích thước mặc định, đang hiện.
    Không bao giờ ném lỗi: bố cục hỏng không được làm hỏng trang chủ.
    """
    if isinstance(tho, (str, bytes)):
        try:
            tho = json.loads(tho)
        except ValueError:
            tho = None
    ds, da_co = [], set()
    for x in tho if isinstance(tho, list) else []:
        if not isinstance(x, dict):
            continue
        ma = x.get("id")
        if not isinstance(ma, str) or ma not in _MAC_DINH or ma in da_co:
            continue
        r0, c0 = _MAC_DINH[ma]
        ds.append(O(ma, _so(x.get("rong"), 1, RONG_TOI_DA, r0),
                    _so(x.get("cao"), 1, CAO_TOI_DA, c0), x.get("an") is True))
        da_co.add(ma)
    ds += [o for o in mac_dinh() if o.id not in da_co]
    return ds


def luu(conn, nguoi_dung_id: int, bo_cuc: list[O] | None) -> None:
    """Ghi bố cục (đã chuẩn hoá) của một người. None = về mặc định. Không tự
    commit — người gọi quyết định ranh giới giao dịch."""
    gia_tri = None if bo_cuc is None else json.dumps([o.dict() for o in bo_cuc])
    conn.execute("UPDATE app.nguoi_dung SET bo_cuc_tong_quan = %s WHERE id = %s",
                 (gia_tri, nguoi_dung_id))
