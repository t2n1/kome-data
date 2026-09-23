"""Hình học SVG (thuần Python) cho các khối phân tích của đợt 5b: sparkline,
đóng góp ngành, cây ô (treemap), bản đồ nhiệt, Pareto khách hàng.

Cùng nếp `kome.bao_cao::ve_bieu_do`/`ve_luy_ke`: không thư viện biểu đồ
JavaScript nào (CSP của Vercel chặn script ngoài, và bất biến "không có mã
màu nào ngoài kome.css" vẫn giữ) — mọi hàm ở đây chỉ TÍNH TOẠ ĐỘ, không định
nghĩa chỉ số nào; công thức nằm trong `mart` (migration 029).

Các hàm chỉ nhận dataclass/tuple đơn giản (không phải `conn`), nên test
KHÔNG cần CSDL. `kome.bao_cao` bị nhập ở đây CHỈ để lấy kiểu cho gợi ý —
không import ngược: `kome/bao_cao.py` không được nhập module này.
"""
from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from kome.bao_cao import NganhKy, NganhThang, O, TapTrung


# ---- Bậc màu tăng trưởng ---------------------------------------------------
# Dùng chung cho cây ô và bản đồ nhiệt: 5 bậc ĐỐI XỨNG quanh 0, biên như
# spec §4.2. Biên trùng khớp thuộc về bậc THẤP HƠN (ví dụ đúng -0,05 là g1,
# không phải "0") — ghi rõ ra vì đây là chỗ dễ lệch một-ký-tự nhất của cả
# module này.
def bac_tang_truong(t: float | None) -> str:
    """Bậc màu theo tăng trưởng, đối xứng quanh 0.

    `t is None` (không có cùng kỳ để so, hoặc mẫu số cùng kỳ <= 0) -> "khong".

    [Vòng soát cuối, M5] Biên: đúng -20% -> g2, đúng -5% -> g1, đúng +5% ->
    t1, đúng +20% -> t2 — nói cách khác, một giá trị NẰM ĐÚNG TRÊN biên luôn
    rơi vào bậc XA HƠN 0 (cực trị hơn) trong hai bậc kề biên đó, ở CẢ HAI
    phía. Bình luận cũ ở đây từng nói biên "thuộc bậc PHÍA ÂM/thấp hơn của
    khoảng" — đúng cho hai biên âm (-20%, -5%: bậc xa-hơn-0 tình cờ cũng là
    bậc "thấp hơn" vì phía âm càng xa 0 càng nhỏ), nhưng SAI cho hai biên
    dương (+5%, +20%): ở phía dương, bậc xa-hơn-0 (t1, t2) là bậc CAO HƠN,
    không phải thấp hơn — +5% rơi vào t1 (cao hơn "0"), không rơi vào "0".
    Hành vi (các `if`/`elif` bên dưới) không đổi — chỉ sửa lại câu chữ cho
    khớp với những gì code thật sự làm.
    """
    if t is None:
        return "khong"
    if t <= -0.20:
        return "g2"
    if t <= -0.05:
        return "g1"
    if t < 0.05:
        return "0"
    if t < 0.20:
        return "t1"
    return "t2"


# ---- Squarified treemap -----------------------------------------------------

def _squarify(gia_tri: list[float], x: float, y: float, w: float, h: float
              ) -> list[tuple[float, float, float, float]]:
    """Treemap vuông hoá — thuật toán "squarified treemaps" của Bruls, Huizing
    và van Wijk (2000), *Squarified Treemaps*, Proc. Eurographics/IEEE TCVG
    Symposium on Visualization.

    `gia_tri` phải TOÀN SỐ DƯƠNG và đã xếp giảm dần (điều kiện tiên quyết của
    thuật toán để tỷ lệ khung mỗi ô gần vuông nhất). Trả về danh sách
    `(x, y, w, h)` CÙNG THỨ TỰ với `gia_tri` đầu vào, diện tích mỗi ô tỷ lệ
    thuận với giá trị của nó trong tổng diện tích khung `w * h`.

    Ý tưởng: xếp các ô thành từng "hàng" dọc theo cạnh NGẮN HƠN của phần
    khung còn trống; mỗi lần thêm một phần tử vào hàng hiện tại, so sánh tỷ
    lệ khung XẤU NHẤT (worst aspect ratio) của hàng trước/sau khi thêm — hàng
    chỉ phình ra khi thêm phần tử làm nó ĐỠ xấu hơn. Khi hàng xấu đi, chốt
    hàng hiện tại vào khung rồi bắt đầu hàng mới trên phần khung còn lại.
    """
    if not gia_tri:
        return []
    assert all(v > 0 for v in gia_tri), (
        "_squarify chỉ nhận giá trị DƯƠNG — lọc số 0/âm ở tầng gọi trước khi "
        "gọi hàm này. Một giá trị 0 lọt vào một hàng có phần tử khác 0 sẽ "
        "chia cho 0 trong công thức tỷ lệ khung xấu nhất (worst-ratio) bên "
        "dưới; assert ở đây báo lỗi ngay tại chỗ thay vì một ZeroDivisionError "
        "khó dò ở sâu bên trong vòng lặp.")
    tong = sum(gia_tri)
    if tong <= 0:
        return []
    ty_le = (w * h) / tong
    dt = [v * ty_le for v in gia_tri]

    ket_qua: list[tuple[float, float, float, float] | None] = [None] * len(dt)
    # Khung còn trống, co dần lại sau mỗi hàng đã đặt.
    cx, cy, cw, ch = x, y, w, h

    def xau_nhat(idx_hang: list[int], canh: float) -> float:
        """Tỷ lệ khung xấu nhất trong một hàng, công thức gốc của bài báo:
        worst(R, w) = max( w²·max(R) / s² , s² / (w²·min(R)) ), s = tổng R.
        `canh` là cạnh cố định (chiều dài hàng chạy dọc theo nó)."""
        s_list = [dt[i] for i in idx_hang]
        s = sum(s_list)
        if s <= 0 or canh <= 0:
            return float("inf")
        return max((canh * canh * max(s_list)) / (s * s),
                   (s * s) / (canh * canh * min(s_list)))

    def dat_hang(idx_hang: list[int]) -> None:
        nonlocal cx, cy, cw, ch
        s_list = [dt[i] for i in idx_hang]
        s = sum(s_list)
        if cw >= ch:
            # Cạnh ngắn hơn là chiều cao -> hàng chạy DỌC, mỗi ô xếp chồng
            # theo trục y trong một dải rộng `rong_hang`.
            rong_hang = s / ch if ch > 0 else 0.0
            yy = cy
            for i, v in zip(idx_hang, s_list):
                hh = v / rong_hang if rong_hang > 0 else 0.0
                ket_qua[i] = (cx, yy, rong_hang, hh)
                yy += hh
            cx += rong_hang
            cw -= rong_hang
        else:
            cao_hang = s / cw if cw > 0 else 0.0
            xx = cx
            for i, v in zip(idx_hang, s_list):
                ww = v / cao_hang if cao_hang > 0 else 0.0
                ket_qua[i] = (xx, cy, ww, cao_hang)
                xx += ww
            cy += cao_hang
            ch -= cao_hang

    hang: list[int] = []
    i = 0
    while i < len(dt):
        canh = min(cw, ch)
        if not hang:
            hang = [i]
            i += 1
            continue
        thu = hang + [i]
        if xau_nhat(hang, canh) >= xau_nhat(thu, canh):
            hang = thu
            i += 1
        else:
            dat_hang(hang)
            hang = []
    if hang:
        dat_hang(hang)

    return [o for o in ket_qua if o is not None]


# ---- Sparkline --------------------------------------------------------------

def ve_duong_nho(so: list[int | float | None], rong: int = 120, cao: int = 32) -> dict:
    """Đường nhỏ (sparkline) cho một ô chỉ số. `None` cắt đường thành đoạn
    mới — KHÔNG nối liền qua tháng thiếu dữ liệu, cùng nếp `ve_bieu_do` với
    tháng không có cùng kỳ.

    [Vòng soát 1, minor 4] Một đoạn chỉ có ĐÚNG MỘT điểm (số liệu đứng lẻ,
    kẹp giữa hai `None` hoặc ở đầu/cuối) vẫn có mặt trong `doan` (một
    `<polyline>` một điểm không vẽ được đường, template có thể bỏ qua), NHƯNG
    toạ độ của nó còn được liệt riêng trong `diem_don` (list `(x, y)`) để
    template vẽ một CHẤM tròn cho điểm đứng lẻ đó — không thì tháng duy nhất
    có số liệu giữa hai tháng thiếu dữ liệu biến mất khỏi biểu đồ hoàn toàn.
    """
    gia_tri = [v for v in so if v is not None]
    if not gia_tri:
        return {"co": False}
    le = 2
    cao_ve = cao - 2 * le
    rong_ve = rong - 2 * le
    dinh, day = max(gia_tri), min(gia_tri)
    khoang = (dinh - day) or 1
    buoc = rong_ve / max(len(so) - 1, 1)

    doan: list[str] = []
    diem_don: list[tuple[float, float]] = []
    dang_ve: list[tuple[float, float]] = []

    def flush() -> None:
        if not dang_ve:
            return
        if len(dang_ve) == 1:
            diem_don.append(dang_ve[0])
        doan.append(" ".join(f"{x},{y}" for x, y in dang_ve))
        dang_ve.clear()

    for i, v in enumerate(so):
        if v is None:
            flush()
            continue
        x = round(le + i * buoc, 1)
        y = round(le + cao_ve - cao_ve * (v - day) / khoang, 1)
        dang_ve.append((x, y))
    flush()

    return {"co": True, "rong": rong, "cao": cao, "doan": doan, "diem_don": diem_don}


# ---- Xu hướng 30 ngày (đợt 5b Task 5, dashboard `/`) -----------------------

def ve_xu_huong(ngay: "list[tuple[date, int]]", rong: int = 720, cao: int = 180) -> dict:
    """30 ngày cuối thành CỘT, 30 ngày liền trước thành ĐƯỜNG so sánh — xếp
    theo THỨ TỰ NGÀY (ngày thứ i của đường so với ngày thứ i của cột), KHÔNG
    theo "cùng thứ trong tuần": giữ đơn giản, chú giải trang phải nói rõ điều
    này để không ai đọc nhầm thành so sánh có điều chỉnh lịch.

    `ngay` là dãy (ngày, doanh_thu) LIÊN TỤC, CŨ -> MỚI (`mart.ban_theo_ngay`
    đã nối từ lịch nên ngày không bán vẫn có dòng mang số 0 — không có
    khoảng trống nào để cắt đoạn, khác `ve_duong_nho`/`ve_bieu_do`).

    Ít hơn 31 ngày dữ liệu (30 ngày để vẽ cột + tối thiểu 1 ngày liền trước để
    so) thì KHÔNG có đường — không đủ một chu kỳ trước đó để so sánh, và vẽ
    một đường từ 0 ngày sẽ trông như "sụt về không" trong khi sự thật là
    "chưa có gì để so".

    [Soát vòng 1] 31–59 ngày dữ liệu (đủ cột nhưng CHƯA đủ 30 ngày để so) thì
    số điểm của đường ÍT HƠN 30 — các điểm đó phải xếp CĂN PHẢI vào lưới 30 ô
    (dùng chung trục X với cột), không dồn về bên trái: điểm CUỐI của đường
    (ngày liền kề trước cột) luôn rơi vào Ô CUỐI, cùng vị trí với cột cuối
    cùng. Dồn trái sẽ đặt một ngày (thứ tự thời gian gần cột nhất) vào ô ĐẦU
    của lưới — trông như còn 29 ngày nữa mới tới cột, trong khi sự thật là
    hết dữ liệu ngay sau điểm đó.
    """
    if not ngay:
        return {"co": False}
    cot_ngay = ngay[-30:]
    duong_ngay = ngay[:-30][-30:]
    co_duong = len(ngay) >= 31 and bool(duong_ngay)

    le_t, le_p, le_tren, le_duoi = 8, 8, 12, 26
    cao_ve = cao - le_tren - le_duoi
    rong_ve = rong - le_t - le_p
    dinh = max([v for _, v in cot_ngay] + [v for _, v in duong_ngay], default=0) or 1
    buoc = rong_ve / len(cot_ngay)
    rong_cot = max(buoc * 0.62, 2)

    cot = []
    for i, (ng, v) in enumerate(cot_ngay):
        x = le_t + i * buoc
        h = max(cao_ve * (v / dinh), 0) if v > 0 else 0
        cot.append({"x": round(x + (buoc - rong_cot) / 2, 1),
                    "y": round(le_tren + cao_ve - h, 1),
                    "w": round(rong_cot, 1), "h": round(h, 1),
                    "ngay": ng, "gia_tri": v})

    diem = []
    if co_duong:
        # Căn phải: ô lưới cuối cùng (idx = len(cot_ngay)-1) LUÔN dành cho
        # điểm cuối của đường (ngày liền kề trước cột) — offset dịch mọi
        # điểm sang phải đúng bằng số ô còn thiếu.
        offset = len(cot_ngay) - len(duong_ngay)
        for i, (ng, v) in enumerate(duong_ngay):
            idx = offset + i
            x = le_t + idx * buoc + buoc / 2
            y = le_tren + cao_ve - (cao_ve * (v / dinh) if v > 0 else 0)
            diem.append({"x": round(x, 1), "y": round(y, 1), "ngay": ng, "gia_tri": v})

    return {"co": True, "rong": rong, "cao": cao, "cot": cot,
            "duong": " ".join(f"{p['x']},{p['y']}" for p in diem),
            "diem": diem, "dinh": dinh, "co_duong": co_duong}


# ---- Bề rộng chữ ước lượng (dùng chung nhiều khối) -------------------------
# Không đo DOM thật (không có trình duyệt ở tầng Python) — chỉ đủ để quyết
# định CẮT/DỜI chữ hay không, không phải một phép đo chính xác.

def _rong_chu(ten: str, co_chu: float) -> float:
    """1em cho ký tự "full-width" (có dấu/CJK, ord > 127 — rộng gần bằng cỡ
    chữ), 0,6em cho ký tự ASCII thường ("half-width")."""
    return sum(co_chu if ord(c) > 127 else co_chu * 0.6 for c in ten)


# ---- Đóng góp ngành (thanh lệch hai phía) -----------------------------------

_CO_CHU_DG_TIEN = 9.5
_CO_CHU_DG_TEN = 10.0
_LE_NHAN_DG = 4.0


def ve_dong_gop(dong: "list[NganhKy]", rong: int = 720) -> dict:
    """Thanh lệch hai phía quanh trục giữa — ngành nào kéo doanh thu LÊN
    (chênh lệch dương) nằm bên phải trục, ngành kéo XUỐNG nằm bên trái.

    [Vòng soát 1 vòng 2, N-1] Nhãn SỐ TIỀN từng đặt cứng ở "đầu mút thanh +
    4px" — thanh dài nhất (tỷ lệ 100% so với `max_abs`) chạm gần hết mép
    khung (`nua_rong = x0 - le`), nên nhãn của CHÍNH NÓ tràn khỏi viewBox mà
    không cách nào thấy được (chữ bị cắt ở x=716/720, không có lỗi nào nổ
    ra). Sửa bằng cách ước lượng bề rộng nhãn (`_rong_chu`) rồi tự CHỌN chỗ
    đặt cho từng thanh: ngoài đầu mút nếu còn đủ chỗ tới mép khung, nếu
    không thì lùi vào TRONG thân thanh (`nhan_trong=True`, template đổi màu
    chữ cho tương phản với nền thanh) — cả hai trường hợp toạ độ đều nằm
    trong `[0, rong]` theo xây dựng, vì "trong thân thanh" không bao giờ
    vượt quá đầu mút của chính thanh đó."""
    dong_loc = [d for d in dong if d.chenh_lech is not None]
    if not dong_loc:
        return {"co": False}
    dong_sap = sorted(dong_loc, key=lambda d: d.chenh_lech, reverse=True)

    le, cao_hang, khoang_cach = 8, 28, 6
    so_hang = len(dong_sap)
    cao = 2 * le + so_hang * cao_hang + (so_hang - 1) * khoang_cach
    x0 = rong / 2
    nua_rong = x0 - le
    max_abs = max(abs(d.chenh_lech) for d in dong_sap) or 1

    thanh = []
    for i, d in enumerate(dong_sap):
        y = le + i * (cao_hang + khoang_cach)
        w = nua_rong * (abs(d.chenh_lech) / max_abs)
        am = d.chenh_lech < 0
        x = (x0 - w) if am else x0

        nhan = f"¥{d.chenh_lech:+,}"
        rong_nhan = _rong_chu(nhan, _CO_CHU_DG_TIEN)
        if am:
            # Thanh kéo dài về TRÁI trục — "ngoài" là xa hơn về bên trái.
            ngoai_x = x - _LE_NHAN_DG
            if ngoai_x - rong_nhan >= 0:
                nhan_x, nhan_neo, nhan_trong = ngoai_x, "end", False
            else:
                nhan_x, nhan_neo, nhan_trong = x + _LE_NHAN_DG, "start", True
        else:
            ngoai_x = x + w + _LE_NHAN_DG
            if ngoai_x + rong_nhan <= rong:
                nhan_x, nhan_neo, nhan_trong = ngoai_x, "start", False
            else:
                nhan_x, nhan_neo, nhan_trong = x + w - _LE_NHAN_DG, "end", True

        thanh.append({"nganh": d.nganh, "x": round(x, 1), "w": round(w, 1),
                      "y": round(y, 1), "am": am, "chenh_lech": d.chenh_lech,
                      "tang_truong": d.tang_truong, "nhan": nhan,
                      "nhan_x": round(nhan_x, 1), "nhan_neo": nhan_neo,
                      "nhan_trong": nhan_trong})

    return {"co": True, "rong": rong, "cao": cao, "x0": round(x0, 1),
            "cao_hang": cao_hang, "thanh": thanh}


# ---- Nhãn cắt gọn cho ô cây ô ------------------------------------------------

_CO_CHU_TREEMAP = 11.0   # px — cỡ chữ TỐI THIỂU cho nhãn trong ô cây ô.
_LE_NHAN = 6.0           # px — chừa hai bên (padding trái phải trong ô).


def _nhan_vua_o(ten: str, w: float, h: float) -> str | None:
    """[Vòng soát 1, I-3] Nhãn đã CẮT GỌN để vừa khung `w`×`h` ở cỡ chữ
    >= `_CO_CHU_TREEMAP`px — None khi ô quá nhỏ để đặt dù một ký tự kèm dấu
    ba chấm. Trước bản sửa, template tự in `ten[:14]`/`ten[:16]` TRẦN không
    biết kích thước ô thật — nhãn dài tràn ra ngoài ô hẹp, nhãn ngắn bỏ phí
    ô rộng. Cắt ở ĐÂY (nơi biết `w`/`h` thật, tính bằng squarify) thay vì ở
    template. Dùng `_rong_chu` (đã định nghĩa ở khối "Bề rộng chữ ước
    lượng" phía trên, chung với `ve_dong_gop`)."""
    if h < _CO_CHU_TREEMAP + 4:
        return None
    kha_dung = float(w) - _LE_NHAN
    if kha_dung <= 0:
        return None
    if _rong_chu(ten, _CO_CHU_TREEMAP) <= kha_dung:
        return ten
    cat = ten
    while cat and _rong_chu(cat + "…", _CO_CHU_TREEMAP) > kha_dung:
        cat = cat[:-1]
    return f"{cat}…" if cat else None


# ---- Cây ô (treemap hai tầng) ------------------------------------------------

def ve_cay_o(nhom: "list[tuple[str, int, float | None, list[tuple[str, str, int]]]]",
             rong: int = 720, cao: int = 360, toi_da_ma: int = 5) -> dict:
    """Treemap hai tầng: ngành -> tối đa `toi_da_ma` mã lớn nhất + một ô
    "(khác)" cho phần còn lại. Diện tích ÂM không vẽ được — ngành/mã doanh
    thu <= 0 bị BỎ và cộng dồn vào `khong_ve` (spec §4.2: lặng lẽ bỏ là tổng
    cây ô lệch tổng ô chỉ số mà không ai biết vì sao, nên phải in ra).

    [Vòng soát 1] Đối soát tổng: `dt_nganh` (doanh thu NGÀNH, số liệu chính
    thức từ mart) và tổng các mã trong `mat_hang` là HAI nguồn khác nhau,
    không nhất thiết khớp nhau tuyệt đối. Bản đầu lấy
    `con_lai = dt_nganh - sum(mã được vẽ riêng)` làm ô "(khác)" — sai ở hai
    chỗ: (1) một mã ÂM trong danh sách đã bị cộng riêng vào `khong_ve`, rồi
    `dt_nganh` (chưa trừ mã đó) lại kéo theo đúng khoản âm đó một lần NỮA vào
    "(khác)" -> đếm hai lần; (2) nếu `dt_nganh` nhỏ hơn tổng vài mã dương nhỏ
    (dt_nganh không bao trọn hết danh sách mã), `con_lai` có thể ÂM và cả cụm
    mã nhỏ đó biến mất khỏi cây ô mà không cộng vào đâu cả.

    Sửa: diện tích của MỘT NGÀNH luôn là `doanh_thu_ve` = TỔNG CÁC MÃ DƯƠNG
    của chính ngành đó (không phải `dt_nganh`) — "(khác)" =
    `doanh_thu_ve - tổng mã được vẽ riêng`, LUÔN >= 0 theo xây dựng nên không
    còn ca mất mã. Ngành không có danh sách mã (hoặc mọi mã đều <= 0) thì vẽ
    thẳng `dt_nganh` làm diện tích (không có ô mã con nào tách ra được).
    `dt_nganh` (net, SỐ THẬT theo mart, dùng để in `<title>`) vẫn được giữ
    nguyên trong khoá `doanh_thu` của mỗi ngành; khoá MỚI `doanh_thu_ve` là
    giá trị THỰC SỰ dùng để tính diện tích — hai con số có thể khác nhau và
    ĐỀU phải hiển thị được, không được lẫn vào nhau.

    Bất biến đối soát (có test canh): với MỌI `dt_nganh` đầu vào,
    `sum(doanh_thu_ve của các ngành được vẽ) + khong_ve == sum(dt_nganh đầu
    vào)` — miễn `dt_nganh` của mỗi ngành đúng bằng tổng các mã (dương và âm)
    của chính nó, tức dữ liệu mart nhất quán giữa hai tầng.

    `so_ma_khong_ve` đếm SỐ MÃ bị bỏ — gồm cả mã nằm trong một ngành bị bỏ
    TOÀN BỘ (ngành đó không tách mã ra được nữa vì cả ngành đã biến mất khỏi
    cây ô, nhưng số mã trong danh sách gốc của nó vẫn được đếm vào đây, để
    câu "N mã doanh thu âm" trên trang không thiếu mã của những ngành đó).
    Số đếm này KHÔNG cộng dồn được thành tiền — tiền dồn hết vào `khong_ve`
    (một số nguyên yên), tách bạch "đếm mã" và "cộng tiền" là hai việc khác
    nhau.
    """
    khong_ve = 0
    so_ma_khong_ve = 0
    nganh_giu = []  # (nganh, dt_nganh, tt_nganh, doanh_thu_ve, mat_hang_duong)
    for nganh, dt_nganh, tt_nganh, mat_hang in nhom:
        if dt_nganh is None or dt_nganh <= 0:
            khong_ve += dt_nganh or 0
            so_ma_khong_ve += len(mat_hang)
            continue

        mh_duong = []
        for _ma, ten, dt in mat_hang:
            if dt is None or dt <= 0:
                khong_ve += dt or 0
                so_ma_khong_ve += 1
                continue
            mh_duong.append((ten, dt))

        doanh_thu_ve = sum(dt for _, dt in mh_duong)
        if doanh_thu_ve <= 0:
            # Không có mã nào dương để tách (danh sách rỗng, hoặc mọi mã đều
            # <= 0 dù dt_nganh > 0) -> vẽ thẳng dt_nganh, không có ô mã con.
            doanh_thu_ve = dt_nganh
            mh_duong = []

        nganh_giu.append((nganh, dt_nganh, tt_nganh, doanh_thu_ve, mh_duong))

    if not nganh_giu:
        return {"co": False, "khong_ve": int(khong_ve), "so_ma_khong_ve": so_ma_khong_ve}

    # Squarify tầng 1 theo doanh_thu_ve (giá trị THỰC SỰ vẽ), không theo
    # dt_nganh — hai con số lệch nhau khi ngành có mã âm hoặc mã không bao
    # trọn dt_nganh (xem docstring ở trên).
    nganh_sap = sorted(nganh_giu, key=lambda t: t[3], reverse=True)
    o_nganh = _squarify([t[3] for t in nganh_sap], 0, 0, rong, cao)

    ket_qua_nganh = []
    for (nganh, dt_nganh, tt_nganh, doanh_thu_ve, mh_duong), (x, y, w, h) in zip(nganh_sap, o_nganh):
        mh_sap = sorted(mh_duong, key=lambda t: t[1], reverse=True)
        ve_rieng = mh_sap[:toi_da_ma]
        con_lai = doanh_thu_ve - sum(dt for _, dt in ve_rieng)

        items = list(ve_rieng)
        if con_lai > 1e-9:
            items.append(("(khác)", con_lai))
        items_sap = sorted(items, key=lambda t: t[1], reverse=True)

        o_mh = _squarify([v for _, v in items_sap], x, y, w, h) if items_sap else []
        # [Vòng soát 1, I-3] `nhan`: nhãn ĐÃ CẮT để vừa đúng khung ô này —
        # None khi ô quá nhỏ, template khi đó bỏ hẳn <text> (không đoán bừa
        # bằng ten[:N] không biết kích thước ô thật).
        ma_ra = [{"ten": ten, "x": round(xx, 1), "y": round(yy, 1),
                  "w": round(ww, 1), "h": round(hh, 1), "doanh_thu": int(dt),
                  "nhan": _nhan_vua_o(ten, ww, hh)}
                 for (ten, dt), (xx, yy, ww, hh) in zip(items_sap, o_mh)]

        ket_qua_nganh.append({
            "nganh": nganh, "x": round(x, 1), "y": round(y, 1),
            "w": round(w, 1), "h": round(h, 1),
            "bac": bac_tang_truong(tt_nganh),
            "doanh_thu": int(dt_nganh), "doanh_thu_ve": int(doanh_thu_ve),
            "tang_truong": tt_nganh, "ma": ma_ra})

    return {"co": True, "rong": rong, "cao": cao, "nganh": ket_qua_nganh,
            "khong_ve": int(khong_ve), "so_ma_khong_ve": so_ma_khong_ve}


# ---- Bản đồ nhiệt ngành x tháng --------------------------------------------

def _lui_12_thang(th: str) -> str:
    """"YYYY-MM" của đúng 12 tháng trước `th` — so sánh chuỗi (lexicographic)
    vẫn đúng thứ tự thời gian cho định dạng này, nên không cần parse `date`."""
    return f"{int(th[:4]) - 1:04d}-{th[5:7]}"


def ve_nhiet(dong: "list[NganhThang]", thang: list[str],
             thang_cuoi_co_du_lieu: str | None = None,
             thang_dau_du_lieu: str | None = None) -> dict:
    """Lưới ngành × tháng. Hàng xếp theo TỔNG doanh thu kỳ giảm dần (tính
    bằng `sorted` trên dữ liệu đã có — chỉ để SẮP XẾP HIỂN THỊ, không phải
    một chỉ số mới). Luôn đủ 12 cột kể cả tháng ngành đó không có dòng bán —
    ô thiếu KHÔNG được tô như 0%, phải có nhãn riêng.

    [Vòng soát 1, I-1] `thang_cuoi_co_du_lieu` (chuỗi "YYYY-MM", thường là
    `bc.ky.ngay_cuoi` định dạng lại — KHÔNG hỏi CSDL thêm) tách MỘT ô thiếu
    dòng (`d is None`) thành HAI tình huống khác hẳn nhau, thứ mà bản trước
    gộp chung vào "khong_ck" (không có cùng kỳ) — sai cho cả hai:
      * tháng SAU `thang_cuoi_co_du_lieu`: kỳ CHƯA ĐI TỚI tháng đó — bậc
        "chua_toi". Tô như "không có cùng kỳ" ở đây nói dối: tháng chưa xảy
        ra không phải tháng thiếu SO SÁNH.
      * tháng <= `thang_cuoi_co_du_lieu` nhưng ngành không có dòng: ngành
        THẬT SỰ không bán gì tháng đó (và cũng không bán ở tháng cùng kỳ,
        nếu không đã có dòng qua nhánh FULL JOIN của mart) — bậc
        "khong_ban", khác "không có cùng kỳ" (bậc "khong_ck", dành cho
        trường hợp CÓ dòng doanh thu tháng này nhưng KHÔNG có dòng cùng kỳ
        năm trước, `d.co_cung_ky is False`).
    Để `None` (mặc định, ví dụ khi gọi rời khỏi `/bao-cao`) giữ NGUYÊN hành
    vi cũ — mọi ô thiếu dòng đều "khong_ck" — vì khi đó không biết ranh giới
    kỳ ở đâu để phân biệt hai tình huống trên.

    [Vòng soát 1 vòng 2] Điều kiện "tháng chưa tới" kiểm TRƯỚC TIÊN và KHÔNG
    đòi `d is None` — bản đầu chỉ gán "chua_toi" khi vừa thiếu dòng VỪA ở
    tương lai, nên một tháng tương lai mà FULL JOIN của mart (029 §3.3) lỡ
    "chiếu" dữ liệu năm trước sang (ngành có bán ở tháng cùng kỳ năm ngoái,
    dù CHƯA bán gì ở tháng đang xét) vẫn có `d` khác `None` — lọt thẳng
    xuống nhánh `co_cung_ky` phía dưới và bị tô như một tháng CÓ SỐ, đúng
    lỗi gốc mà I-1 tồn tại để sửa. Ranh giới thời gian là một SỰ THẬT VỀ
    KỲ, không phụ thuộc dòng nào có mặt trong view hay không.

    [Vòng soát cuối, I-2] `thang_dau_du_lieu` ("YYYY-MM", thường
    `bc.moi_ky[0].ngay_dau` định dạng lại — KHÔNG hỏi CSDL thêm) chặn một lỗi
    NULL≠0 đối xứng với `thang_cuoi_co_du_lieu`: tháng TRƯỚC khi công ty có
    dòng bán đầu tiên (ví dụ kỳ 6 = 2024-08..2025-07 trong khi dữ liệu chỉ
    bắt đầu 2025-03-03) không phải "ngành này không bán tháng đó" — đó là
    "kho CHƯA CÓ dữ liệu ở tháng đó", một sự thật khác hẳn. Bản trước tô cả
    dải tháng trước ngày bắt đầu bằng bậc "khong_ban" (¥0 · "không bán tháng
    này và tháng cùng kỳ năm trước cũng vậy") — sai kiểu NULL≠0 y hệt lớp lỗi
    `mart.san_pham_360.ton` đã ghi ở CLAUDE.md, chỉ khác đối tượng. Bậc mới
    "truoc_du_lieu" render giống "chua_toi" (dấu "·", không phải ¥0) vì cả
    hai đều là "không biết", không phải "biết và bằng không".

    Với ô "khong_ban" (ngành thật sự không bán gì tháng đó VÀ nằm trong
    khoảng đã có dữ liệu), câu "tháng cùng kỳ năm trước cũng vậy" chỉ đúng
    khi tháng M-12 CŨNG nằm trong khoảng có dữ liệu — nếu M-12 rơi vào trước
    `thang_dau_du_lieu`, ta không hề BIẾT tháng đó ngành có bán hay không
    (kho không lưu), nên không được khẳng định "cũng vậy". Cờ `co_the_ck`
    trên mỗi ô "khong_ban" mang đúng sự thật này cho template quyết định câu
    chữ; `thang_dau_du_lieu=None` (gọi rời khỏi `/bao-cao`, không biết ranh
    giới) giữ NGUYÊN hành vi cũ — luôn `co_the_ck=True`."""
    if not dong:
        return {"co": False}

    tra_cuu = {(d.nganh, d.thang): d for d in dong}
    tong_nganh: dict[str, int] = {}
    for d in dong:
        tong_nganh[d.nganh] = tong_nganh.get(d.nganh, 0) + (d.doanh_thu or 0)
    nganh_sap = sorted(tong_nganh, key=lambda n: tong_nganh[n], reverse=True)

    o = []
    hang = []
    for nganh in nganh_sap:
        o_hang = []
        for th in thang:
            d = tra_cuu.get((nganh, th))
            if thang_cuoi_co_du_lieu is not None and th > thang_cuoi_co_du_lieu:
                cell = {"thang": th, "nganh": nganh, "bac": "chua_toi",
                        "tang_truong": None, "doanh_thu": None, "co_cung_ky": False}
            elif thang_dau_du_lieu is not None and th < thang_dau_du_lieu:
                cell = {"thang": th, "nganh": nganh, "bac": "truoc_du_lieu",
                        "tang_truong": None, "doanh_thu": None, "co_cung_ky": False}
            elif d is None and thang_cuoi_co_du_lieu is not None:
                co_the_ck = (thang_dau_du_lieu is None
                             or _lui_12_thang(th) >= thang_dau_du_lieu)
                cell = {"thang": th, "nganh": nganh, "bac": "khong_ban",
                        "tang_truong": None, "doanh_thu": 0, "co_cung_ky": False,
                        "co_the_ck": co_the_ck}
            elif d is None:
                cell = {"thang": th, "nganh": nganh, "bac": "khong_ck",
                        "tang_truong": None, "doanh_thu": 0, "co_cung_ky": False}
            elif not d.co_cung_ky:
                cell = {"thang": th, "nganh": nganh, "bac": "khong_ck",
                        "tang_truong": d.tang_truong, "doanh_thu": d.doanh_thu,
                        "co_cung_ky": False}
            elif d.tang_truong is None:
                # co_cung_ky=True nhưng tang_truong None -> mẫu số cùng kỳ <= 0.
                cell = {"thang": th, "nganh": nganh, "bac": "khong",
                        "tang_truong": None, "doanh_thu": d.doanh_thu,
                        "co_cung_ky": True}
            else:
                cell = {"thang": th, "nganh": nganh,
                        "bac": bac_tang_truong(d.tang_truong),
                        "tang_truong": d.tang_truong, "doanh_thu": d.doanh_thu,
                        "co_cung_ky": True}
            o.append(cell)
            o_hang.append(cell)
        hang.append({"nganh": nganh, "o": o_hang})

    # `hang`: MỘT dòng = MỘT ngành, kèm sẵn 12 ô theo đúng thứ tự `thang` —
    # [Vòng soát 1, I-2] để template dựng <table> bằng một vòng lặp lồng
    # đơn giản, không cần tự chia hàng/cột bằng `loop.index0 // len(thang)`
    # (phép chia nguyên đó từng nằm trong Jinja, nay chuyển hẳn vào đây).
    # `o` (phẳng) giữ lại để không phá vỡ test cũ tham chiếu trực tiếp.
    return {"co": True, "nganh": nganh_sap, "thang": thang, "o": o, "hang": hang,
            "thang_dau_du_lieu": thang_dau_du_lieu}


# ---- Pareto khách hàng -------------------------------------------------------

def ve_pareto(tt: "TapTrung | None", rong: int = 720, cao: int = 260) -> dict:
    """Cột doanh thu mỗi khách (khách âm — 赤伝 của riêng họ — vẫn có cột,
    cao 0) + đường luỹ kế trên trục 0–100% bên phải. Luỹ kế bị KẸP [0, 1]
    khi vẽ (một khách âm có thể đẩy luỹ kế nhất thời > 100%); số ĐỌC ĐƯỢC
    (`KhachTapTrung.luy_ke`) giữ nguyên, không kẹp — chỉ toạ độ vẽ mới kẹp.

    [Vòng soát 1, minor 3] Trả `"doan": list[str]` (nhiều đoạn `<polyline>`),
    KHÔNG phải một `"duong"` duy nhất: `luy_ke` từng khách hàng CÓ THỂ `None`
    (chưa tính được, cùng nếp `khach_mat_hang.nhip_ngay` chưa đủ dữ liệu), và
    một chuỗi điểm duy nhất sẽ NỐI LIỀN qua đúng khách đó như thể luỹ kế của
    nó bằng khách trước — sai. Cắt đoạn tại `None`, cùng cơ chế với
    `ve_duong_nho`/`ve_bieu_do::duong_ck`."""
    if tt is None or not tt.dong:
        return {"co": False}

    le_t, le_p, le_tren, le_duoi = 8, 8, 16, 34
    cao_ve = cao - le_tren - le_duoi
    rong_ve = rong - le_t - le_p
    dinh = max((d.doanh_thu for d in tt.dong), default=0) or 1
    buoc = rong_ve / len(tt.dong)
    rong_cot = max(buoc * 0.7, 2)

    cot, doan, diem = [], [], []
    dang_ve: list[str] = []
    for i, d in enumerate(tt.dong):
        x = le_t + i * buoc
        h = max(cao_ve * (d.doanh_thu / dinh), 0) if d.doanh_thu > 0 else 0
        cot.append({"x": round(x + (buoc - rong_cot) / 2, 1),
                    "y": round(le_tren + cao_ve - h, 1),
                    "w": round(rong_cot, 1), "h": round(h, 1), "khach": d})
        if d.luy_ke is None:
            if dang_ve:
                doan.append(" ".join(dang_ve))
                dang_ve = []
            continue
        lk = max(0.0, min(d.luy_ke, 1.0))
        y = le_tren + cao_ve - cao_ve * lk
        dang_ve.append(f"{round(x + buoc / 2, 1)},{round(y, 1)}")
        # [Vòng soát 1, M-2] Chấm tròn RIÊNG tại mỗi điểm luỹ kế, kèm
        # <title> "luỹ kế X%" — polyline không tự có "tooltip" tại từng
        # điểm, chỉ vẽ được đường. `khach`/`luy_ke` giữ nguyên (không kẹp)
        # để template in đúng số đọc được, toạ độ `y` mới là giá trị kẹp.
        diem.append({"x": round(x + buoc / 2, 1), "y": round(y, 1), "khach": d})
    if dang_ve:
        doan.append(" ".join(dang_ve))

    # [Vòng soát 1 vòng 2, N-3] Vạch chia trục % (0/50/100) tính TOẠ ĐỘ Y ở
    # ĐÂY — bản trước lặp lại công thức `le_tren`/`le_duoi` (16/34) TRẦN
    # ngay trong Jinja, tách khỏi hai hằng số cục bộ của chính hàm này; đổi
    # `cao`/lề ở một trong hai chỗ mà quên chỗ kia là vạch trục vẽ sai vị
    # trí mà không lỗi nào nổ ra.
    truc_pct = [{"pct": p, "nhan": f"{int(p * 100)}%",
                 "y": round(le_tren + cao_ve * (1 - p), 1)}
                for p in (0.0, 0.5, 1.0)]

    return {"co": True, "rong": rong, "cao": cao, "cot": cot,
            "doan": doan, "diem": diem, "dinh": dinh, "truc_pct": truc_pct}
