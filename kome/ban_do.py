"""Bản đồ khách hàng (đợt 4c, màn 24): lưới 47 ô vuông bằng nhau xếp theo hình
nước Nhật, tô màu theo chỉ số, bấm một ô mở danh bạ đã lọc theo tỉnh đó.

Như kome/khach_hang.py, kome/san_pham.py: KHÔNG định nghĩa chỉ số ở đây, không
tự mở kết nối, không tự commit. Số liệu đọc từ `core.dim_prefecture` và
`mart.khach_theo_tinh` (Task 1, migration 025) — mọi công thức (doanh thu 12
tháng, cần gọi lại) đã nằm sẵn ở đó.

Toạ độ SVG tính TỪ dữ liệu (rong/cao suy từ max hang_luoi/cot_luoi của
core.dim_prefecture), không viết cứng: sửa lưới trong CSDL (thêm/đổi ô) thì
hình vẽ phải tự đi theo mà không cần sửa module này.
"""
from dataclasses import dataclass

# Ba chỉ số có thể tô màu bản đồ, ánh xạ sang nhãn tiếng Việt hiện trên trang.
# Đây cũng là DANH SÁCH TRẮNG của tham số `chi_so` — xem _chi_so_hop_le().
CHI_SO = {
    "khach":     "Số khách",
    "doanh_thu": "Doanh thu 12 tháng",
    "can_goi":   "Cần gọi lại",
}

# Cột trên dataclass O ứng với từng khoá của CHI_SO — dùng để chọn `gia_tri`
# bằng getattr() thay vì if/elif ba nhánh giống hệt nhau.
_COT_THEO_CHI_SO = {"khach": "so_khach", "doanh_thu": "doanh_thu", "can_goi": "can_goi"}

# 8 地方 (vùng địa lý) theo đúng thứ tự bắc -> nam thật ngoài đời, KHÔNG theo
# bảng chữ cái (bảng chữ cái sẽ xếp 中国 trước 中部, sai thứ tự địa lý — 中部
# nằm giữa 関東 và 近畿, còn 中国 nằm giữa 近畿 và 四国/九州沖縄).
VUNG_THU_TU = ("北海道", "東北", "関東", "中部", "近畿", "中国", "四国", "九州沖縄")

# Kích thước một ô lưới và khe hở giữa hai ô, đơn vị SVG. Ô vuông bằng nhau
# cho MỌI tỉnh (§5.1 của đặc tả migration 025) — không có "ô lớn hơn cho
# 東京都", vì cả bốn lý do migration đó đã nêu (bấm được / tô màu đọc được /
# khớp kiến trúc SVG-từ-Python / trung thực về độ phân giải cấp tỉnh).
O_RONG = 60
O_CAO = 60
KHE = 6

# Số bậc màu cho các ô CÓ giá trị (> 0). Bậc 0 (không có khách/doanh thu/cần
# gọi) là bậc RIÊNG, không nằm trong 5 bậc này — xem _tinh_bac().
SO_BAC = 5


@dataclass(frozen=True)
class O:
    """Một ô vuông của lưới 47 tỉnh."""
    ma_jis: str
    ten: str
    ten_ngan: str
    ten_latin: str
    vung: str
    hang: int
    cot: int
    so_khach: int
    doanh_thu: int
    can_goi: int
    # can_goi / so_khach. None khi so_khach == 0 — "không biết" khác "0%"
    # (cùng luật với kome/san_pham.py::_so đối với `ton`). 45/47 ô có
    # so_khach = 0 ngay khi lọc theo một người phụ trách; một phép chia
    # thẳng trong template sẽ nổ ZeroDivisionError giữa lúc mở trang.
    ty_le_can_goi: float | None
    # Giá trị đang được tô màu (= một trong ba cột trên, theo `chi_so` đang
    # chọn) và bậc màu suy ra từ giá trị đó — xem _tinh_bac().
    gia_tri: int
    bac: int
    # Toạ độ góc trên-trái của ô trong hệ toạ độ SVG, tính từ hang/cot.
    x: int
    y: int


@dataclass(frozen=True)
class TrangBanDo:
    o: list[O]
    # 8 vùng địa lý, mỗi vùng gộp tổng ba chỉ số của các tỉnh thuộc vùng đó
    # (bắc -> nam, xem VUNG_THU_TU).
    vung: list[dict]
    # 47 ô xếp giảm dần theo gia_tri, hoà thì theo ma_jis (thứ tự ổn định).
    bang: list[O]
    # 5 bậc màu kèm khoảng giá trị THẬT (min-max) của từng bậc — không phải
    # nhãn "thấp/cao" suông.
    chu_giai: list[dict]
    # Khách có dòng bán nhưng KHÔNG khớp tỉnh nào trong core.dim_prefecture
    # (prefecture NULL/rỗng, hoặc một chuỗi lạ không khớp OBC) — đúng 1/1.710
    # khách thật (CLAUDE.md). Phải hiện thành MỘT CON SỐ riêng, không được
    # biến mất giữa bản đồ và tổng công ty.
    khong_ro_tinh: int
    tong: dict
    # Chỉ số ĐÃ ĐƯỢC KIỂM (rơi về "khach" nếu tham số URL gõ sai) — trang đọc
    # lại để tô đúng nút đang chọn trên ô lọc chỉ số.
    chi_so: str
    rong: int
    cao: int


def _chi_so_hop_le(chi_so: str) -> str:
    """`chi_so` không nằm trong CHI_SO thì rơi về "khach".

    Bắt buộc: đây là tham số đọc thẳng từ query string URL. Một người gõ
    `?chi_so=xyz` không được làm trang nổi 500 — trang phải luôn mở được,
    chỉ là mở ra với chỉ số mặc định.
    """
    return chi_so if chi_so in CHI_SO else "khach"


def _dk_sale(sale: str | None) -> tuple[str, list]:
    """Mảnh lọc theo người phụ trách, dựng MỘT LẦN rồi dùng lại ở CẢ HAI truy
    vấn (A và B của ban_do()). Chép tay hai bản là hai bộ lọc sẽ trôi khỏi
    nhau — đúng bài học của `_vi_tu` ở kome/khach_hang.py."""
    return ("AND s.salesperson_code = %s", [sale]) if sale else ("", [])


def _tinh_bac(gia_tri_theo_o: list[int]) -> list[int]:
    """Bậc màu cho từng ô, theo ĐÚNG THỨ TỰ đưa vào `gia_tri_theo_o`.

    0 -> bậc 0 (bậc RIÊNG, "không có" khác "ít"). Các giá trị > 0 được xếp
    tăng dần rồi chia `ntile(5)` BẰNG TAY (dữ liệu đã nằm sẵn trong bộ nhớ,
    không đáng một lượt hỏi CSDL riêng chỉ để gọi ntile()).

    CHIA THEO PHÂN VỊ (số Ô mỗi bậc gần bằng nhau), KHÔNG THEO KHOẢNG GIÁ TRỊ
    ĐỀU: 東京都 (290 khách, đông nhất công ty) kéo trần giá trị lên rất cao so
    với phần còn lại — chia đều khoảng [0, max] thành 5 phần sẽ dồn 40+ tỉnh
    còn lại vào đúng một bậc thấp nhất, và bản đồ thành một màu duy nhất
    (đặc tả §5.5). ntile theo phân vị đảm bảo mỗi bậc có SỐ TỈNH gần bằng
    nhau, dù giá trị của chúng cách nhau bao xa.

    [Vòng sửa 1] BẢN ĐẦU chia ntile theo VỊ TRÍ (row_number) như
    `ntile(5)` thô của Postgres — và đúng như Postgres, ranh giới bậc có thể
    CẮT NGANG một cụm giá trị bằng nhau. Người soát đo trên CSDL thật, theo
    từng người phụ trách: 4/5 sale có ít nhất một cặp tỉnh CÙNG một giá trị
    (vd cùng 1 khách) nhưng bị chia vào HAI bậc màu khác nhau — bậc 1 và bậc
    2 cùng ghi chú giải "1–1", hai ô cùng số lại khác màu, và với 東京都
    (nguyên văn người dùng): "tôi không biết màu nào là bậc nào".
    SỬA: GIÁ TRỊ BẰNG NHAU LUÔN VỀ CÙNG MỘT BẬC — đẩy cả cụm trùng giá trị về
    bậc của PHẦN TỬ ĐẦU CỤM (phần tử nhỏ nhất/đứng trước nhất trong thứ tự đã
    sắp tăng dần). Vì mảng bậc-theo-vị-trí không giảm khi vị trí tăng, phần
    tử đầu cụm luôn nhận bậc NHỎ NHẤT trong cụm — dồn cả cụm về bậc đó không
    bao giờ làm bậc giảm đi so với ntile thô, chỉ có thể gộp hai bậc liền kề
    làm một. Hệ quả tất yếu: các bậc không còn chồng khoảng giá trị lên nhau
    (chú giải không còn hai mục cùng ghi "1–1" hay "2–3"/"3–6" chồng nhau).
    """
    n = len(gia_tri_theo_o)
    bac = [0] * n
    # Vị trí (chỉ số trong gia_tri_theo_o) của các ô có giá trị > 0, sắp XẾP
    # TĂNG DẦN theo chính giá trị đó.
    vi_tri_duong = sorted((i for i in range(n) if gia_tri_theo_o[i] > 0),
                          key=lambda i: gia_tri_theo_o[i])
    so_duong = len(vi_tri_duong)
    if so_duong == 0:
        return bac
    co_ban, du = divmod(so_duong, SO_BAC)
    # Bậc THÔ theo vị trí — đúng ntile(5) chuẩn, CHƯA xử lý cụm trùng giá trị.
    bac_tho = [0] * so_duong
    con_tro = 0
    for b in range(1, SO_BAC + 1):
        kich_thuoc = co_ban + (1 if b <= du else 0)
        for _ in range(kich_thuoc):
            bac_tho[con_tro] = b
            con_tro += 1
    # Dồn cụm: mỗi GIÁ TRỊ (không phải mỗi Ô) chỉ có đúng một bậc, nhớ theo
    # lần gặp ĐẦU TIÊN — vì `vi_tri_duong` đã sắp tăng dần và `bac_tho` không
    # giảm theo vị trí, lần gặp đầu tiên của một giá trị luôn cho bậc nhỏ
    # nhất mà giá trị đó có thể nhận.
    bac_theo_gia_tri: dict[int, int] = {}
    for idx_trong_duong, i in enumerate(vi_tri_duong):
        gia_tri = gia_tri_theo_o[i]
        b = bac_theo_gia_tri.setdefault(gia_tri, bac_tho[idx_trong_duong])
        bac[i] = b
    return bac


def ban_do(conn, sale: str | None = None, chi_so: str = "khach") -> TrangBanDo:
    """Dựng toàn bộ dữ liệu + hình học SVG của màn Bản đồ khách hàng.

    ĐÚNG HAI lượt hỏi — có test đếm LÚC CHẠY
    (tests/test_ban_do.py::test_ban_do_khong_qua_2_truy_van).

    `sale`: mặc định tiện dụng như mọi trang khác của đợt 3 (khach_hang.py,
    san_pham.py) — không phải hàng rào bảo mật, không kiểm quyền.
    """
    chi_so = _chi_so_hop_le(chi_so)
    dk_sale, tham_so_sale = _dk_sale(sale)

    # Truy vấn A (1 lượt): 47 dòng đã LEFT JOIN sẵn từ core.dim_prefecture
    # sang số liệu.
    #
    # LEFT JOIN LÀ CHỖ PHẢI CANH — KHÔNG BAO GIỜ ĐỔI THÀNH JOIN (hay để
    # dim_prefecture ở vế phải): tỉnh chưa có khách nào (hoặc chưa có khách
    # của MỘT người phụ trách cụ thể, khi lọc theo `sale`) sẽ không có dòng
    # nào trong CTE `tinh`. Một JOIN thường sẽ ĐÁNH RỚT hẳn tỉnh đó khỏi kết
    # quả — bản đồ khi đó thiếu ô mà KHÔNG NỔ LỖI NÀO, trang vẫn vẽ ra bình
    # thường với ít hơn 47 ô, và không ai để ý cho tới khi có người đếm số ô
    # trên màn hình. LEFT JOIN + coalesce(..., 0) giữ đủ 47 dòng trong mọi
    # trường hợp, kể cả lọc theo một người phụ trách chỉ có khách ở vài tỉnh.
    rows_a = conn.execute(f"""
        WITH tinh AS MATERIALIZED (
            SELECT s.prefecture, sum(s.so_khach) AS so_khach,
                   sum(s.doanh_thu_12t) AS doanh_thu, sum(s.can_goi) AS can_goi
              FROM mart.khach_theo_tinh s
             WHERE true {dk_sale}
             GROUP BY s.prefecture
        )
        SELECT p.ma_jis, p.ten, p.ten_latin, p.ten_ngan, p.vung, p.hang_luoi, p.cot_luoi,
               coalesce(t.so_khach, 0), coalesce(t.doanh_thu, 0), coalesce(t.can_goi, 0)
          FROM core.dim_prefecture p
          LEFT JOIN tinh t ON t.prefecture = p.ten
         ORDER BY p.ma_jis
    """, tham_so_sale).fetchall()

    # Truy vấn B (1 lượt): phần KHÔNG khớp tỉnh nào ("(không rõ tỉnh)") và
    # tổng toàn công ty (hoặc tổng của riêng `sale` nếu có lọc) — gộp bằng
    # UNION ALL trong ĐÚNG MỘT câu, theo nếp tong_quan_danh_ba() của
    # kome/khach_hang.py, để không tốn thêm lượt hỏi nào.
    #
    # [Vòng sửa 1] CTE `s AS MATERIALIZED`, ghi TƯỜNG MINH — BẢN ĐẦU không có
    # CTE này, và mỗi nhánh UNION ALL bên dưới tự viết `FROM
    # mart.khach_theo_tinh` riêng, tức MỖI LẦN THAM CHIẾU LÀ MỘT LẦN DỰNG LẠI
    # cả view (khach_360 + hang_doanh_thu + EXISTS vào khach_nhom_viec).
    # Cộng CTE `tinh` của truy vấn A ở trên, một lần mở trang dựng lại
    # khach_theo_tinh BA LẦN — trong khi ngân sách "<= 2 truy vấn" chỉ đếm SỐ
    # LƯỢT HỎI, không đếm sức tính, nên nó không hề bắt được lớp lỗi này
    # (đúng bài học của kome/khach_hang.py::danh_sach và
    # kome/san_pham.py::kho_hang). Lọc theo `sale` (`{dk_sale}`) nằm TRONG
    # CTE — vị từ đó vẫn đẩy xuống được, vật hoá ở đây chỉ bỏ đi hai lần dựng
    # lại thừa của cùng một tập kết quả đã lọc.
    rows_b = conn.execute(f"""
        WITH s AS MATERIALIZED (
            SELECT * FROM mart.khach_theo_tinh s WHERE true {dk_sale}
        )
        SELECT 'khong_ro'::text, coalesce(sum(so_khach),0), coalesce(sum(doanh_thu_12t),0), coalesce(sum(can_goi),0)
          FROM s
         WHERE coalesce(s.prefecture, '') NOT IN (SELECT ten FROM core.dim_prefecture)
        UNION ALL
        SELECT 'tong', coalesce(sum(so_khach),0), coalesce(sum(doanh_thu_12t),0), coalesce(sum(can_goi),0)
          FROM s
    """, tham_so_sale).fetchall()

    # ---- Từ đây trở xuống: KHÔNG còn lượt hỏi CSDL nào nữa -----------------

    tho = []
    for ma_jis, ten, ten_latin, ten_ngan, vung, hang, cot, so_khach, doanh_thu, can_goi in rows_a:
        d = {
            "ma_jis": ma_jis, "ten": ten, "ten_latin": ten_latin,
            "ten_ngan": ten_ngan, "vung": vung, "hang": hang, "cot": cot,
            "so_khach": int(so_khach), "doanh_thu": int(doanh_thu),
            "can_goi": int(can_goi),
        }
        d["gia_tri"] = d[_COT_THEO_CHI_SO[chi_so]]
        # None khi so_khach == 0 — "không biết tỷ lệ" khác "0%" (xem chú
        # thích của trường này trên dataclass O).
        d["ty_le_can_goi"] = (d["can_goi"] / d["so_khach"]) if d["so_khach"] else None
        tho.append(d)

    bac_theo_o = _tinh_bac([d["gia_tri"] for d in tho])

    max_hang = max(d["hang"] for d in tho)
    max_cot = max(d["cot"] for d in tho)
    rong = max_cot * O_RONG + (max_cot - 1) * KHE
    cao = max_hang * O_CAO + (max_hang - 1) * KHE

    cac_o = [
        O(ma_jis=d["ma_jis"], ten=d["ten"], ten_ngan=d["ten_ngan"],
          ten_latin=d["ten_latin"], vung=d["vung"], hang=d["hang"], cot=d["cot"],
          so_khach=d["so_khach"], doanh_thu=d["doanh_thu"], can_goi=d["can_goi"],
          ty_le_can_goi=d["ty_le_can_goi"], gia_tri=d["gia_tri"], bac=bac,
          x=(d["cot"] - 1) * (O_RONG + KHE), y=(d["hang"] - 1) * (O_CAO + KHE))
        for d, bac in zip(tho, bac_theo_o)
    ]

    vung_gop = [
        {
            "vung": ten_vung,
            "so_tinh": len(cua_vung),
            "so_khach": sum(o.so_khach for o in cua_vung),
            "doanh_thu": sum(o.doanh_thu for o in cua_vung),
            "can_goi": sum(o.can_goi for o in cua_vung),
            # Tổng theo ĐÚNG chi_so đang chọn — để template khỏi phải viết
            # if/elif ba nhánh (khach/doanh_thu/can_goi) mỗi lần đọc khối này.
            "gia_tri": sum(o.gia_tri for o in cua_vung),
        }
        for ten_vung in VUNG_THU_TU
        for cua_vung in [[o for o in cac_o if o.vung == ten_vung]]
    ]

    bang = sorted(cac_o, key=lambda o: (-o.gia_tri, o.ma_jis))

    # Chú giải: khoảng giá trị THẬT (min-max) của từng bậc, không phải một
    # nhãn "thấp/cao" suông — người đọc phải thấy con số đứng sau màu.
    #
    # [Vòng sửa 1] THÊM mục bậc 0 ("không có", màu RIÊNG theo §5.5) vào chính
    # chu_giai — bản đầu chỉ liệt kê bậc 1..5 nên Task 3 (template) buộc phải
    # tự viết cứng thêm một ô "0 khách" ở đâu đó ngoài danh sách này, đúng
    # loại logic không được phép nằm trong template. Bậc 0 luôn có giá trị
    # THẬT bằng 0 (đó chính là định nghĩa của bậc này), không phải None.
    gia_tri_bac_0 = [o.gia_tri for o in cac_o if o.bac == 0]
    chu_giai = [{
        "bac": 0,
        "so_tinh": len(gia_tri_bac_0),
        "tu": 0 if gia_tri_bac_0 else None,
        "den": 0 if gia_tri_bac_0 else None,
    }]
    for b in range(1, SO_BAC + 1):
        gia_tri_bac = sorted(o.gia_tri for o in cac_o if o.bac == b)
        chu_giai.append({
            "bac": b,
            "so_tinh": len(gia_tri_bac),
            "tu": gia_tri_bac[0] if gia_tri_bac else None,
            "den": gia_tri_bac[-1] if gia_tri_bac else None,
        })

    khong_ro_tinh = next((int(r[1]) for r in rows_b if r[0] == "khong_ro"), 0)
    tong_row = next((r for r in rows_b if r[0] == "tong"), None)
    tong = {
        "so_khach": int(tong_row[1]) if tong_row else 0,
        "doanh_thu": int(tong_row[2]) if tong_row else 0,
        "can_goi": int(tong_row[3]) if tong_row else 0,
    }

    return TrangBanDo(o=cac_o, vung=vung_gop, bang=bang, chu_giai=chu_giai,
                      khong_ro_tinh=khong_ro_tinh, tong=tong, chi_so=chi_so,
                      rong=rong, cao=cao)
