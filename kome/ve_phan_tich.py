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
    Biên: -20% -> g2, -5% -> g1, +5% -> t1, +20% -> t2 (biên thuộc bậc PHÍA
    ÂM/thấp hơn của khoảng, tức <= chứ không phải <).
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


# ---- Đóng góp ngành (thanh lệch hai phía) -----------------------------------

def ve_dong_gop(dong: "list[NganhKy]", rong: int = 720) -> dict:
    """Thanh lệch hai phía quanh trục giữa — ngành nào kéo doanh thu LÊN
    (chênh lệch dương) nằm bên phải trục, ngành kéo XUỐNG nằm bên trái."""
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
        thanh.append({"nganh": d.nganh, "x": round(x, 1), "w": round(w, 1),
                      "y": round(y, 1), "am": am, "chenh_lech": d.chenh_lech,
                      "tang_truong": d.tang_truong})

    return {"co": True, "rong": rong, "cao": cao, "x0": round(x0, 1),
            "cao_hang": cao_hang, "thanh": thanh}


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
        ma_ra = [{"ten": ten, "x": round(xx, 1), "y": round(yy, 1),
                  "w": round(ww, 1), "h": round(hh, 1), "doanh_thu": int(dt)}
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

def ve_nhiet(dong: "list[NganhThang]", thang: list[str]) -> dict:
    """Lưới ngành × tháng. Hàng xếp theo TỔNG doanh thu kỳ giảm dần (tính
    bằng `sorted` trên dữ liệu đã có — chỉ để SẮP XẾP HIỂN THỊ, không phải
    một chỉ số mới). Luôn đủ 12 cột kể cả tháng ngành đó không có dòng bán —
    ô thiếu KHÔNG được tô như 0%, phải có nhãn riêng "không có cùng kỳ"."""
    if not dong:
        return {"co": False}

    tra_cuu = {(d.nganh, d.thang): d for d in dong}
    tong_nganh: dict[str, int] = {}
    for d in dong:
        tong_nganh[d.nganh] = tong_nganh.get(d.nganh, 0) + (d.doanh_thu or 0)
    nganh_sap = sorted(tong_nganh, key=lambda n: tong_nganh[n], reverse=True)

    o = []
    for nganh in nganh_sap:
        for th in thang:
            d = tra_cuu.get((nganh, th))
            if d is None:
                o.append({"thang": th, "nganh": nganh, "bac": "khong_ck",
                          "tang_truong": None, "doanh_thu": 0, "co_cung_ky": False})
            elif not d.co_cung_ky:
                o.append({"thang": th, "nganh": nganh, "bac": "khong_ck",
                          "tang_truong": d.tang_truong, "doanh_thu": d.doanh_thu,
                          "co_cung_ky": False})
            elif d.tang_truong is None:
                # co_cung_ky=True nhưng tang_truong None -> mẫu số cùng kỳ <= 0.
                o.append({"thang": th, "nganh": nganh, "bac": "khong",
                          "tang_truong": None, "doanh_thu": d.doanh_thu,
                          "co_cung_ky": True})
            else:
                o.append({"thang": th, "nganh": nganh,
                          "bac": bac_tang_truong(d.tang_truong),
                          "tang_truong": d.tang_truong, "doanh_thu": d.doanh_thu,
                          "co_cung_ky": True})

    return {"co": True, "nganh": nganh_sap, "thang": thang, "o": o}


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

    cot, doan = [], []
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
    if dang_ve:
        doan.append(" ".join(dang_ve))

    return {"co": True, "rong": rong, "cao": cao, "cot": cot,
            "doan": doan, "dinh": dinh}
