"""Khách hàng: danh sách, tìm kiếm, và hồ sơ 360°.

Như kome/bao_cao.py: KHÔNG định nghĩa chỉ số ở đây, không tự mở kết nối.
Mọi công thức nằm ở schema `mart` (migration 015, 016).
"""
from dataclasses import dataclass, field
from datetime import date

MOI_TRANG = 50

# Nhãn tiếng Việt cho `mart.khach_360.trang_thai`, kèm màu để màn hình đọc được
# bằng mắt chứ không phải bằng cách tra bảng. Thứ tự ở đây LÀ thứ tự ưu tiên
# hiển thị: việc cần làm đứng trước, việc không làm gì được đứng sau.
TRANG_THAI = {
    "canh_bao":        ("Cần gọi lại", "canh"),
    "da_roi_bo":       ("Đã rời bỏ", "loi"),
    "binh_thuong":     ("Bình thường", "ok"),
    "chua_du_lich_su": ("Chưa đủ lịch sử", "nhat"),
    "ngung_giao_dich": ("Ngừng giao dịch", "nhat"),
}

# Nhãn hiển thị cho khách chưa có hồ sơ 得意先全情報 (prefecture NULL hoặc
# rỗng), và GIÁ TRỊ QUY ƯỚC mang nhãn đó đi trên URL.
#
# Vì sao phải là hai chuỗi khác nhau: đổ thẳng nhãn ra `<option value>` thì
# bấm vào nó gửi `tinh=(không rõ)`, rồi câu SQL chạy `prefecture = '(không
# rõ)'` — không dòng nào khớp. Khối "Tập trung ở đâu" nói "(không rõ): 37"
# ngay phía trên, bấm vào ra "Không có khách nào khớp": hai con số mâu thuẫn
# trên cùng một màn hình, và đúng nhóm khách CẦN dọn lại là nhóm không có
# đường nào mở ra.
KHONG_RO = "(không rõ)"
TINH_TRONG = "__trong"

# GIÁ TRỊ QUY ƯỚC cho mục "— mọi người phụ trách —" của ô lọc 担当者, cùng lý
# lẽ với TINH_TRONG ngay trên: chuỗi RỖNG đã có nghĩa khác rồi.
#
# `nv=""` nghĩa là "không chọn gì" -> trang rơi về mặc định tiện dụng của đợt
# 3 và lọc theo người ĐANG ĐĂNG NHẬP. Nên nếu mục đầu của ô chọn mang giá trị
# rỗng thì chọn nó không bỏ được lọc: ô hiện "— mọi người phụ trách —" trong
# khi danh sách vẫn chỉ có khách của mình — ô điều khiển nói một đằng, dữ
# liệu một nẻo, đúng cái mà test của ô Tỉnh được viết ra để chặn. Và vì form
# lọc chỉ mang `tat_ca` khi nó ĐÃ bật, trên bản Vercel một nhân viên không có
# đường nào từ ô đó ra xem toàn công ty.
NV_MOI_NGUOI = "__moi_nguoi"

# 荷姿区分 — hai mã thật sự có trong dữ liệu (xem CLAUDE.md). Mã lạ thì hiện
# nguyên mã chứ không đoán: một nhãn đoán sai còn tệ hơn một mã khó đọc.
QUY_CACH = {"00": "バラ (lẻ)", "02": "ケース (thùng)"}

# Cột được phép sắp xếp. Danh sách trắng, KHÔNG ghép thẳng tham số URL vào câu
# SQL — đó là đường mở cho SQL injection, và trang này sắp nằm trên Internet.
SAP_XEP = {
    "doanh_thu": "doanh_thu_thuan DESC NULLS LAST",
    "lai_gop":   "lai_gop DESC NULLS LAST",
    "ty_suat":   "ty_suat DESC NULLS LAST",
    "im_lang":   "ty_le_im_lang DESC NULLS LAST",
    "gan_nhat":  "lan_cuoi DESC NULLS LAST",
    "ten":       "ten ASC",
}


@dataclass
class Khach:
    ma: str
    ten: str
    tinh: str | None
    thanh_pho: str | None
    dien_thoai: str | None
    nguoi_phu_trach: str | None
    doanh_thu: int
    lai_gop: int
    ty_suat: float | None
    lan_cuoi: date | None
    so_ngay_im_lang: int | None
    nhip_ngay: float | None
    ty_le_im_lang: float | None
    trang_thai: str
    dau_hieu_obc: str | None

    @property
    def nhan_trang_thai(self) -> str:
        return TRANG_THAI.get(self.trang_thai, (self.trang_thai, "nhat"))[0]

    @property
    def mau(self) -> str:
        return TRANG_THAI.get(self.trang_thai, ("", "nhat"))[1]


@dataclass
class TrangKhach:
    khach: list[Khach]
    tong: int
    trang: int
    so_trang: int
    tim: str
    loc: str
    sap: str
    # Mã sale đang lọc (None = đang xem tất cả) và tên người đó để trang nói
    # rõ "đang lọc theo ai".
    #
    # `dem_trang_thai` và `tong_tat_ca` KHÔNG còn ở đây — chúng đã chuyển sang
    # TongQuan, nơi chúng được lấy trong cùng một lượt hỏi với bốn khối phân
    # tích. Xem ghi chú ở tong_quan_danh_ba().
    sale: str | None = None
    ten_sale: str | None = None
    # Ba bộ lọc mới của trang danh sách (đợt 4a): nhóm việc ('im'/'tut'/'moi'),
    # hạng doanh thu ('S'..'D'), và tỉnh — trang đọc lại để giữ nguyên lựa
    # chọn qua các liên kết phân trang/sắp xếp.
    nhom: str | None = None
    hang: str | None = None
    tinh: str | None = None


@dataclass
class HoSo:
    khach: Khach
    ho_so: dict
    thang: list[dict]
    mat_hang: list[dict]
    da_ngung_mua: list[dict]
    lan_mua_gan_day: list[dict]
    # Bốn khối của đợt 4a, lấy trong ĐÚNG HAI truy vấn (xem ho_so()).
    # `bac_gia` ở đây là BẢNG GIÁ của bậc giá khách đang hưởng — khác
    # `ho_so["bac_gia"]`, vốn chỉ là MÃ bậc ('01'..'10') lấy từ dim_customer.
    chua_mua_thang: list[dict] = field(default_factory=list)
    goi_y: list[dict] = field(default_factory=list)
    bac_gia: list[dict] = field(default_factory=list)
    diem_giao: list[dict] = field(default_factory=list)


_COT = """customer_code, ten, prefecture, city, phone, salesperson_code,
          doanh_thu_thuan, lai_gop, ty_suat, lan_cuoi, so_ngay_im_lang,
          nhip_ngay, ty_le_im_lang, trang_thai, dau_hieu_obc"""

# Khối "chi tiết" của hồ sơ 360°: tên tiếng Việt cho các cột lấy thêm trong
# CÙNG câu lệnh với `_COT` (xem ho_so()). Thứ tự ở đây PHẢI khớp thứ tự cột
# trong câu lệnh đó.
_COT_CHI_TIET = ("chi_nhanh", "buu_chinh", "dia_chi", "hang", "phan_loai",
                 "ngay_chot", "bac_gia", "vang_lai", "lan_dau", "so_lan_mua",
                 "so_phieu", "gia_tri_tb")


def _khach(r) -> Khach:
    return Khach(ma=r[0], ten=r[1], tinh=r[2], thanh_pho=r[3], dien_thoai=r[4],
                 nguoi_phu_trach=r[5], doanh_thu=int(r[6] or 0),
                 lai_gop=int(r[7] or 0),
                 ty_suat=float(r[8]) if r[8] is not None else None,
                 lan_cuoi=r[9], so_ngay_im_lang=r[10],
                 nhip_ngay=float(r[11]) if r[11] is not None else None,
                 ty_le_im_lang=float(r[12]) if r[12] is not None else None,
                 trang_thai=r[13], dau_hieu_obc=r[14])


def _vi_tu(q: str, *, tim: str = "", loc: str = "", sale: str | None = None,
           nhom: str | None = None, hang: str | None = None,
           tinh: str | None = None) -> tuple[str, list]:
    """Mệnh đề WHERE lọc `mart.khach_360`, viết MỘT LẦN cho cả hai chỗ đọc.

    `q` là cách câu lệnh gọi đang gọi tên bảng: `mart.khach_360` ở
    `danh_sach()` (không bí danh), `k` ở `tong_quan_danh_ba()`.

    Vì sao dùng chung chứ không chép: bộ đếm trạng thái và chính danh sách mà
    nó mở ra phải lọc GIỐNG HỆT nhau. Hai bản chép tay là hai bộ lọc sẽ trôi
    khỏi nhau, và triệu chứng đúng bằng cái lỗi vòng review này sửa — chip
    "Tất cả (1.710)" bấm vào ra 216 khách.

    Trả về (mệnh đề WHERE đã sẵn sàng nối, danh sách tham số). Thứ tự tham số
    = thứ tự vị từ trong chính hàm này, nên chỗ gọi chỉ cần nối các danh sách
    theo đúng thứ tự VĂN BẢN mà các mảnh WHERE xuất hiện trong câu lệnh.
    """
    dieu_kien, tham_so = [], []
    if tim.strip():
        # Tìm theo tên, mã, điện thoại hoặc địa chỉ cùng lúc — nhân viên không
        # nhớ mình đang có mảnh thông tin nào trong tay.
        dieu_kien.append(f"""({q}.ten ILIKE %s OR {q}.customer_code ILIKE %s
                             OR {q}.phone ILIKE %s OR {q}.address ILIKE %s
                             OR {q}.city ILIKE %s)""")
        tham_so += [f"%{tim.strip()}%"] * 5
    if loc in TRANG_THAI:
        dieu_kien.append(f"{q}.trang_thai = %s")
        tham_so.append(loc)
    if sale:
        dieu_kien.append(f"{q}.salesperson_code = %s")
        tham_so.append(sale)
    if nhom:
        # EXISTS chứ không JOIN: một khách có thể ở nhiều nhóm, JOIN sẽ nhân
        # đôi dòng và làm `tong` đếm sai.
        dieu_kien.append(f"""EXISTS (SELECT 1 FROM mart.khach_nhom_viec v
                                     WHERE v.customer_code = {q}.customer_code
                                       AND v.nhom = %s)""")
        tham_so.append(nhom)
    if hang:
        # EXISTS định danh đầy đủ, nhất quán với nhánh `nhom` ngay trên — cùng
        # một bẫy phân giải tên (customer_code không đủ rõ nó thuộc bảng nào
        # khi có nhiều bảng cùng cột) nên dùng chung một cách viết.
        dieu_kien.append(f"""EXISTS (SELECT 1 FROM mart.hang_doanh_thu hd
                                     WHERE hd.customer_code = {q}.customer_code
                                       AND hd.hang = %s)""")
        tham_so.append(hang)
    if tinh == TINH_TRONG:
        # Nhóm "(không rõ)": khách có dòng bán nhưng chưa có hồ sơ
        # 得意先全情報. `prefecture = '(không rõ)'` không bao giờ khớp gì —
        # nhãn đó do coalesce() sinh ra lúc HIỂN THỊ, không nằm trong CSDL.
        dieu_kien.append(f"({q}.prefecture IS NULL OR {q}.prefecture = '')")
    elif tinh:
        dieu_kien.append(f"{q}.prefecture = %s")
        tham_so.append(tinh)
    return (("WHERE " + " AND ".join(dieu_kien)) if dieu_kien else ""), tham_so


def danh_sach(conn, tim: str = "", loc: str = "", sap: str = "doanh_thu",
              trang: int = 1, sale: str | None = None,
              ten_sale: str | None = None, nhom: str | None = None,
              hang: str | None = None, tinh: str | None = None) -> TrangKhach:
    """Danh sách khách, có tìm kiếm và lọc theo trạng thái. HAI lượt hỏi.

    `sale` là MẶC ĐỊNH TIỆN DỤNG, không phải hàng rào bảo mật: công ty năm
    người, ai cũng biết khách của ai, và trang luôn có một liên kết bỏ lọc.
    Không có kiểm quyền nào ở đây, và đó là cố ý — xem đặc tả đợt 3 §5.
    """
    where, tham_so = _vi_tu("mart.khach_360", tim=tim, loc=loc, sale=sale,
                            nhom=nhom, hang=hang, tinh=tinh)

    tong = conn.execute(
        f"SELECT count(*) FROM mart.khach_360 {where}", tham_so).fetchone()[0]

    thu_tu = SAP_XEP.get(sap, SAP_XEP["doanh_thu"])
    trang = max(1, trang)
    rows = conn.execute(
        f"""SELECT {_COT} FROM mart.khach_360 {where}
            ORDER BY {thu_tu} LIMIT %s OFFSET %s""",
        tham_so + [MOI_TRANG, (trang - 1) * MOI_TRANG]).fetchall()

    return TrangKhach(
        khach=[_khach(r) for r in rows], tong=tong, trang=trang,
        so_trang=max(1, -(-tong // MOI_TRANG)), tim=tim, loc=loc, sap=sap,
        sale=sale, ten_sale=ten_sale, nhom=nhom, hang=hang, tinh=tinh)


def ho_so(conn, ma: str) -> HoSo | None:
    """Hồ sơ 360° của một khách. None nếu mã không tồn tại."""
    # MỘT lượt hỏi cho cả thẻ đầu trang lẫn khối chi tiết, chứ không hai.
    # Trước vòng sửa này đây là HAI câu `SELECT … FROM mart.khach_360 WHERE
    # customer_code = %s` giống hệt nhau về mệnh đề lọc, chỉ khác danh sách
    # cột — tức 47 ms mạng trả cho đúng một hàng đã nằm sẵn trong tay. Gộp
    # lại trả ngân sách truy vấn về 7/8, để khối tiếp theo ai đó muốn thêm
    # không phải phá bất biến mới thêm được.
    r = conn.execute(
        f"""SELECT {_COT},
                   branch_name, postcode, address, rank_code, category_code,
                   closing_day_code, price_level_code, spot_flag, lan_dau,
                   so_lan_mua, so_phieu, gia_tri_tb_moi_lan
            FROM mart.khach_360 WHERE customer_code = %s""", (ma,)).fetchone()
    if r is None:
        return None
    # `_khach` đọc 15 cột ĐẦU theo vị trí, phần đuôi cắt từ CUỐI lên theo số
    # tên trong `_COT_CHI_TIET`. Hai đầu độc lập nhau, nên thêm cột vào `_COT`
    # không làm lệch khối chi tiết (và ngược lại).
    k = _khach(r)
    ho = dict(zip(_COT_CHI_TIET, r[-len(_COT_CHI_TIET):]))

    thang = [dict(zip(("thang", "doanh_thu", "lai_gop", "so_lan"), t))
             for t in conn.execute(
        """SELECT thang, doanh_thu_thuan, lai_gop, so_lan_mua
           FROM mart.khach_theo_thang WHERE customer_code = %s
           ORDER BY thang""", (ma,)).fetchall()]

    # `nhip` là numeric từ Postgres — ép sang int khi HIỂN THỊ ở template
    # (`|int`), không ép ở đây: None phải đi qua nguyên vẹn để template hiện
    # "—" cho mã chưa đủ lịch sử để tính nhịp.
    # Cả ba cột nhịp (`nhip`, `du_kien`, `tre`) nằm sẵn trong CÙNG một view
    # mart.khach_mat_hang — lấy đủ ba ở cả hai khối bên dưới, không chỉ khối
    # đưa ra trong đặc tả gốc, vì bổ sung không tốn thêm truy vấn nào.
    mat_hang = [dict(zip(("ma", "ten", "doanh_thu", "lai_gop", "so_luong",
                          "so_lan", "lan_cuoi", "nhip", "du_kien", "tre"), h))
                for h in conn.execute(
        """SELECT product_code, ten_hang, doanh_thu_thuan, lai_gop, so_luong,
                  so_lan, lan_cuoi, nhip_ngay, du_kien_lan_toi, tre_ngay
           FROM mart.khach_mat_hang WHERE customer_code = %s
           ORDER BY doanh_thu_thuan DESC LIMIT 15""", (ma,)).fetchall()]

    # Mặt hàng khách TỪNG mua đều rồi NGỪNG hẳn. Đây là tín hiệu sớm hơn nhiều
    # so với việc khách ngừng mua toàn bộ: họ đang chuyển dần sang nhà cung cấp
    # khác, từng món một, và không ai để ý cho tới khi mất luôn khách.
    #
    # ĐỌC `ngung_mua` của mart.khach_mat_hang (migration 024), KHÔNG viết lại
    # vị từ. Trước 024 chỗ này dùng ngưỡng CHUNG (`hom_nay - lan_cuoi > 90`
    # cộng `so_lan >= 3`) còn /san-pham/{mã} dùng nhịp RIÊNG — cùng một cặp
    # (khách, mã) cho hai câu trả lời ngược nhau ở hai màn. Nay một khái niệm
    # một công thức, đúng nếp 021/022.
    #
    # `so_lan >= 3` đã bỏ vì THỪA, không phải vì nới lỏng: `nhip_ngay` chỉ có
    # giá trị khi đã có >= 2 khoảng cách, tức >= 3 lần mua (020). Để lại là
    # dựng thêm một bản sao của cùng điều kiện, ở đúng chỗ vừa dọn xong.
    da_ngung = [dict(zip(("ma", "ten", "so_lan", "lan_cuoi", "doanh_thu",
                          "nhip", "du_kien", "tre"), h))
                for h in conn.execute(
        """SELECT h.product_code, h.ten_hang, h.so_lan, h.lan_cuoi,
                  h.doanh_thu_thuan, h.nhip_ngay, h.du_kien_lan_toi, h.tre_ngay
           FROM mart.khach_mat_hang h
           WHERE h.customer_code = %s AND h.ngung_mua
           ORDER BY h.doanh_thu_thuan DESC LIMIT 10""", (ma,)).fetchall()]

    gan_day = [dict(zip(("ngay", "so_phieu", "doanh_thu", "lai_gop"), l))
               for l in conn.execute(
        """SELECT sales_date, count(*), sum(doanh_thu_thuan), sum(lai_gop)
           FROM mart.lan_mua WHERE customer_code = %s
           GROUP BY sales_date ORDER BY sales_date DESC LIMIT 12""", (ma,)).fetchall()]

    # ---- Bốn khối mới của đợt 4a, gộp thành ĐÚNG HAI truy vấn -----------
    # NGÂN SÁCH TRUY VẤN: hàm này chạy 7 lượt hỏi, và 8 là TRẦN. Đo thật
    # 2026-09-22: một round-trip rỗng tới pooler Tokyo mất 47 ms, một lượt
    # hỏi thật ~260 ms. Trang hồ sơ chậm dần từng đợt là cách nó chết mà
    # không ai thấy ngày nào nó chết. Có test canh —
    # tests/test_khach_hang.py::test_ho_so_khong_qua_8_truy_van.
    # Một chỗ trống còn lại là CỐ Ý: khối tiếp theo (đợt 4b/6) phải thêm được
    # mà không cần nới trần.
    #
    # HAI truy vấn chứ không MỘT: gộp cả bốn khối vào một UNION ALL bốn tầng
    # thì mỗi nhánh phải đệm NULL cho khớp kiểu của ba nhánh kia, và câu lệnh
    # đó khó đọc hơn đúng cái nó tiết kiệm (47 ms).
    #
    # Hai cột `chu`/`so_a` mang nghĩa KHÁC NHAU theo `khoi` — đó là cái giá
    # của việc gộp, và vòng lặp Python ngay dưới là chỗ duy nhất biết quy ước
    # đó. `xep` là khoá sắp xếp của từng nhánh (doanh thu cho 'chua', tỷ suất
    # cho 'goi_y'); ORDER BY nằm ở lớp NGOÀI vì thứ tự dòng giữa các nhánh
    # của UNION ALL không được Postgres bảo đảm.
    #
    # KHÔNG lấy `ty_suat_mat_hang.gia_cao_nhat` ra đây, dù nó có sẵn: cột đó
    # là `max(unit_price)` KHÔNG tách theo 荷姿区分 (00 = バラ lẻ, 02 = ケース
    # thùng), nên với mã bán cả hai quy cách nó LUÔN là giá thùng. Khối này
    # hứa "mã chưa từng mua, xếp theo tỷ suất" — giá không nằm trong lời hứa,
    # và đây lại là con số DUY NHẤT trên hai trang mà người bán đọc rồi nói
    # thẳng ra cho khách. Báo giá lẻ bằng giá thùng sai hơn chục lần; không
    # có số còn hơn có số sai. Bảng giá đúng (tách 荷姿) nằm ở khối "Bảng giá
    # của bậc" ngay dưới, dựng từ core.fact_price_list.
    #
    # NHÁNH 'chua' LÀ PHẦN BÙ CỦA `ngung_mua`, KHÔNG PHẢI MỘT NGƯỠNG NGÀY
    # RIÊNG. Nó là dải giữa: đã quá ngày dự kiến mua lại (`tre_ngay IS NOT
    # NULL`, tức im lặng > 1 nhịp) nhưng CHƯA tới 2 nhịp (`NOT ngung_mua`) —
    # "còn gọi kịp". Trước 024 vế thứ hai là `hom_nay - lan_cuoi <= 90`, ăn
    # khớp với ngưỡng 90 của khối "đã ngừng mua" ngay dưới nó. Đổi khối kia
    # sang nhịp riêng mà để nguyên chỗ này thì hai khối CHỒNG NHAU: một mã
    # nhịp 7 ngày im 60 ngày vừa "đã ngừng" (60 >= 2x7) vừa "chưa mua tháng
    # này" (60 <= 90) — cùng một mã, hai kết luận, trên cùng một trang.
    #
    # `NOT dh.da_ngung` (mart.dau_hieu_khach, migration 016): đây cũng là một
    # DANH SÁCH GỌI LẠI ("một cuộc điện thoại nhắc là đủ"), nên khách ※廃業※
    # không được vào. `ngung_mua` đã tự mang cổng đó, nhưng chính vì thế mà
    # `NOT ngung_mua` LUÔN đúng với khách đã đóng cửa — không chặn ở đây thì
    # toàn bộ mặt hàng quá hạn của họ dồn hết sang khối này. LEFT JOIN +
    # coalesce chứ không INNER: khách chưa có dòng 得意先全情報 vẫn phải giữ
    # được khối của mình.
    them = conn.execute("""
        SELECT khoi, ma, ten, chu, so_a FROM (
            (SELECT 'chua'::text AS khoi, h.product_code AS ma,
                    h.ten_hang AS ten, h.lan_cuoi::text AS chu,
                    h.tre_ngay::numeric AS so_a,
                    h.doanh_thu_thuan::numeric AS xep
               FROM mart.khach_mat_hang h
               LEFT JOIN mart.dau_hieu_khach dh
                      ON dh.customer_code = h.customer_code
              WHERE h.customer_code = %s
                AND h.tre_ngay IS NOT NULL AND NOT h.ngung_mua
                AND NOT coalesce(dh.da_ngung, false)
              ORDER BY h.doanh_thu_thuan DESC
              LIMIT 10)
            UNION ALL
            (SELECT 'goi_y', p.product_code,
                    coalesce(nullif(p.product_name, ''), p.product_code),
                    ''::text, t.ty_suat, t.ty_suat
               FROM core.dim_product p
               JOIN mart.ty_suat_mat_hang t ON t.product_code = p.product_code
              WHERE NOT EXISTS (SELECT 1 FROM mart.khach_mat_hang h
                                 WHERE h.customer_code = %s
                                   AND h.product_code = p.product_code)
                AND t.ty_suat IS NOT NULL
              ORDER BY t.ty_suat DESC
              LIMIT 8)
        ) u ORDER BY khoi, xep DESC
    """, (ma, ma)).fetchall()

    chua_mua, goi_y = [], []
    for khoi, ma_hang, ten_hang, chu, so_a in them:
        if khoi == "chua":
            chua_mua.append({"ma": ma_hang, "ten": ten_hang, "lan_cuoi": chu,
                             "tre": int(so_a) if so_a is not None else None})
        else:
            goi_y.append({"ma": ma_hang, "ten": ten_hang,
                          "ty_suat": float(so_a) if so_a is not None else None})

    # Truy vấn B: bảng giá của bậc giá khách đang hưởng + điểm giao thẳng.
    # `'gia'` xếp trước `'giao'` theo bảng chữ cái, nên ORDER BY khoi, ma, c2
    # giữ đúng thứ tự hai khối mà không cần thêm cột nào.
    #
    # DISTINCT ON (product_code, pack_code) ... ORDER BY valid_from DESC:
    # core.fact_price_list giữ LỊCH SỬ giá — kome/loaders/price.py ghi một
    # dòng MỚI mỗi lần nạp master, và khoá bảng có cả `pack_code`. Không lọc
    # thì sau ba lần nạp trang hiện cùng một tên hàng SÁU LẦN với sáu con số
    # khác nhau (3 lần nạp × 2 quy cách 00/02), dưới nhãn "giá đáng lẽ phải
    # bán" — trên đúng màn hình người ta nhìn TRƯỚC KHI báo giá cho khách.
    hai = conn.execute("""
        SELECT khoi, ma, ten, c1, c2, c3 FROM (
            (SELECT DISTINCT ON (pl.product_code, pl.pack_code)
                    'gia'::text AS khoi, pl.product_code AS ma,
                    coalesce(nullif(p.product_name, ''), pl.product_code) AS ten,
                    pl.price_ex_tax::text AS c1, pl.pack_code AS c2,
                    pl.valid_from::text AS c3
               FROM core.fact_price_list pl
               JOIN mart.khach_360 k ON k.customer_code = %s
                                    AND k.price_level_code = pl.price_level
               LEFT JOIN core.dim_product p ON p.product_code = pl.product_code
              ORDER BY pl.product_code, pl.pack_code, pl.valid_from DESC
              LIMIT 20)
            UNION ALL
            (SELECT 'giao', shipto_code, coalesce(nullif(shipto_name, ''), shipto_code),
                    coalesce(address, ''), '', ''
               FROM core.dim_shipto WHERE customer_code = %s)
        ) u ORDER BY khoi, ma, c2
    """, (ma, ma)).fetchall()

    bac_gia = [{"ma": r[1], "ten": r[2], "gia": int(r[3]),
                "quy_cach": QUY_CACH.get(r[4], r[4]), "tu_ngay": r[5]}
               for r in hai if r[0] == "gia"]
    diem_giao = [{"ma": r[1], "ten": r[2], "dia_chi": r[3]}
                 for r in hai if r[0] == "giao"]

    return HoSo(khach=k, ho_so=ho, thang=thang, mat_hang=mat_hang,
                da_ngung_mua=da_ngung, lan_mua_gan_day=gan_day,
                chua_mua_thang=chua_mua, goi_y=goi_y, bac_gia=bac_gia,
                diem_giao=diem_giao)


def can_xu_ly(conn, gioi_han: int = 100, sale: str | None = None) -> list[Khach]:
    """Danh sách việc cần làm: khách đang rời đi, xếp theo tiền đang mất.

    Xếp theo DOANH THU chứ không theo mức độ im lặng: gọi lại khách ¥5 triệu
    im 3 lần nhịp thì đáng hơn khách ¥50.000 im 10 lần nhịp, dù con số thứ hai
    trông đáng báo động hơn.

    `sale`: mặc định tiện dụng, như danh_sach() — không phải hàng rào.
    """
    dieu_kien = "AND salesperson_code = %s" if sale else ""
    tham_so = ([sale] if sale else []) + [gioi_han]
    return [_khach(r) for r in conn.execute(
        f"""SELECT {_COT} FROM mart.khach_360
            WHERE trang_thai IN ('canh_bao', 'da_roi_bo') {dieu_kien}
            ORDER BY doanh_thu_thuan DESC NULLS LAST LIMIT %s""",
        tham_so).fetchall()]


def ve_duong(thang: list[dict], rong: int = 640, cao: int = 120) -> dict:
    """Đường doanh thu theo tháng cho hồ sơ 360°. Tự tính toạ độ — không dùng
    thư viện JavaScript nào (xem ghi chú ở kome/bao_cao.py)."""
    if not thang:
        return {"co": False}
    le = 6
    dinh = max((t["doanh_thu"] or 0) for t in thang) or 1
    n = len(thang)
    buoc = (rong - 2 * le) / max(n - 1, 1)
    diem = [(round(le + i * buoc, 1),
             round(cao - le - (cao - 2 * le) * ((t["doanh_thu"] or 0) / dinh), 1), t)
            for i, t in enumerate(thang)]
    return {"co": True, "rong": rong, "cao": cao, "diem": diem,
            "duong": " ".join(f"{x},{y}" for x, y, _ in diem),
            "vung": f"{le},{cao-le} " + " ".join(f"{x},{y}" for x, y, _ in diem)
                    + f" {round(le + (n-1)*buoc, 1)},{cao-le}",
            "dinh": dinh}


@dataclass
class TongQuan:
    """Bốn khối phân tích + hai bộ đếm của trang danh sách, MỘT truy vấn."""
    nhom: dict[str, int]
    tong: int
    hang: list[tuple[str, int]]
    tinh: list[tuple[str, int]]
    nhan_vien: list[dict]
    # Số khách theo từng trạng thái, dùng cho dải chip "Tất cả / Cần gọi lại
    # / …". CÓ theo nhom/hang/tinh/sale, KHÔNG theo `loc` — xem docstring của
    # tong_quan_danh_ba().
    dem_trang_thai: dict[str, int] = field(default_factory=dict)
    # Tổng khách TOÀN CÔNG TY cho liên kết "Xem tất cả N khách →". Không lọc
    # gì hết, kể cả sale: chính liên kết đó bỏ mọi bộ lọc, nên con số phải là
    # con số người ta sẽ thấy sau khi bấm.
    tong_tat_ca: int = 0


# Thứ tự hiển thị của hạng. S trước D, không phải thứ tự bảng chữ cái ngẫu
# nhiên mà Postgres trả về.
THU_TU_HANG = ("S", "A", "B", "C", "D")


def tong_quan_danh_ba(conn, sale: str | None = None, nhom: str | None = None,
                      hang: str | None = None, tinh: str | None = None) -> TongQuan:
    """Bốn khối phân tích + hai bộ đếm của trang danh sách, ĐÚNG MỘT truy vấn.

    Vì sao gộp: đo thật (2026-09-22) một round-trip rỗng tới pooler Tokyo mất
    47 ms, và một lượt hỏi thật ~260 ms. Sáu khối rời nhau là sáu vòng chờ
    mạng cho một thứ người ta nhìn một lần. Con số "~10 ms" từng ghi ở đây là
    phép đo của `mart.khach_mat_hang` LỌC MỘT KHÁCH — ca có vị từ đẩy xuống
    được — nên nó KHÔNG mô tả khối này: `mart.khach_360` bị tham chiếu nhiều
    lần và không lần nào có `customer_code` để đẩy xuống. Chi phí thật chưa
    đo trên CSDL đầy; có mục KIỂM TAY riêng ở đặc tả §9, ngưỡng 500 ms.

    BỐN BỘ LỌC, HAI PHẠM VI:
      * `sale` — bốn khối phân tích và cả hai bộ đếm đều theo.
      * `nhom`/`hang`/`tinh` — CHỈ `dem_trang_thai` theo. Bốn khối phân tích
        thì KHÔNG: mỗi khối đó là ô ĐIỀU KHIỂN của chính bộ lọc mang tên nó,
        và một ô điều khiển tự lọc theo mình thì bấm vào một mục xong các con
        số khác về 0 hết, không ai quay lại được.
      * `loc` (trạng thái) — KHÔNG bộ đếm nào theo, cùng lý do ngay trên:
        `dem_trang_thai` chính là nhãn của dải chip trạng thái.

    Vì sao `dem_trang_thai` PHẢI theo ba bộ lọc mới: liên kết của từng chip
    mang theo `nhom`/`hang`/`tinh`/`nv` đang bật. Lý lẽ cũ ("bộ đếm chỉ theo
    sale") viết khi trang có MỘT bộ lọc; giờ có năm, nên chip "Tất cả
    (1.710)" bấm vào ra 216 khách — con số nói dối đúng cái danh sách mà
    chính nó mở ra.

    `tong_tat_ca` thì ngược lại: không lọc gì hết. Liên kết của nó
    (`?tat_ca=1`) bỏ MỌI bộ lọc, nên con số phải là con số sau khi bấm.
    """
    # Hai mệnh đề WHERE, cùng một hàm dựng (`_vi_tu`) nên không bao giờ trôi
    # khỏi nhau. THỨ TỰ THAM SỐ = thứ tự văn bản các mảnh WHERE bên dưới:
    # bốn lần `{dk}` (nhom, tong, hang, tinh) rồi MỘT lần `{dk_dem}`; hai
    # khối cuối ('nv', 'tat_ca') không có mảnh nào.
    dk, p = _vi_tu("k", sale=sale)
    dk_dem, p_dem = _vi_tu("k", sale=sale, nhom=nhom, hang=hang, tinh=tinh)
    # Cột thứ năm `canh_bao` (số khách cần gọi lại) chỉ có giá trị thật ở
    # khối 'nv' — các khối kia trả 0. Đây LÀ một cột riêng, không nhồi vào
    # chuỗi `khoa` như "mã|tên": nhồi chuỗi thêm một quy ước phải nhớ và một
    # chỗ nữa có thể tách sai (vd tên nhân viên lỡ chứa dấu phân cách).
    rows = conn.execute(f"""
        SELECT 'nhom' AS khoi, v.nhom AS khoa, count(*) AS so, 0::bigint AS tien,
               0::bigint AS canh_bao
          FROM mart.khach_nhom_viec v
          JOIN mart.khach_360 k ON k.customer_code = v.customer_code
          {dk}
         GROUP BY v.nhom
        UNION ALL
        SELECT 'tong', '', count(*), 0, 0 FROM mart.khach_360 k {dk}
        UNION ALL
        SELECT 'hang', h.hang, count(*), 0, 0
          FROM mart.hang_doanh_thu h
          JOIN mart.khach_360 k ON k.customer_code = h.customer_code
          {dk}
         GROUP BY h.hang
        UNION ALL
        -- Chuỗi '(không rõ)' dưới đây PHẢI khớp hằng KHONG_RO ở đầu module
        -- (trang so nhãn này để biết mục nào cần giá trị URL quy ước
        -- TINH_TRONG). Để literal chứ không truyền tham số: số placeholder
        -- của câu lệnh này đã do `_vi_tu` quyết định, thêm một cái nữa ở
        -- giữa là một chỗ rất dễ đếm lệch về sau.
        SELECT 'tinh', coalesce(nullif(k.prefecture, ''), '(không rõ)'), count(*), 0, 0
          FROM mart.khach_360 k {dk}
         GROUP BY 2
        UNION ALL
        SELECT 'nv', t.salesperson_code || '|' || t.ten, t.so_khach, t.doanh_thu,
               t.so_khach_canh_bao
          FROM mart.tai_nhan_vien t
        UNION ALL
        SELECT 'dem', k.trang_thai, count(*), 0, 0
          FROM mart.khach_360 k {dk_dem}
         GROUP BY k.trang_thai
        UNION ALL
        SELECT 'tat_ca', '', count(*), 0, 0 FROM mart.khach_360
    """, p * 4 + p_dem).fetchall()

    lay = lambda khoi: [(r[1], r[2], r[3], r[4]) for r in rows if r[0] == khoi]
    nhom = {k: n for k, n, _, _ in lay("nhom")}
    hang = dict((k, n) for k, n, _, _ in lay("hang"))
    # "(không rõ)" phải được tách ra KHỎI phép xếp hạng trước khi cắt top 8,
    # không phải trộn chung rồi cắt: công ty thật có 48 tỉnh, "(không rõ)"
    # thường chỉ vài khách nên đứng NGOÀI top 8/9 nếu xếp chung — trộn rồi
    # cắt sẽ âm thầm đánh rơi nhóm này khỏi khối "Tập trung ở đâu" đúng vào
    # lúc dữ liệu đủ lớn để thấy sự khác biệt, còn CSDL thử nghiệm nhỏ (1-2
    # tỉnh) không bao giờ lộ ra lỗi này.
    tinh_rows = lay("tinh")
    tinh_that = sorted(((t, n) for t, n, _, _ in tinh_rows if t != KHONG_RO),
                        key=lambda x: -x[1])[:8]
    khong_ro = next(((t, n) for t, n, _, _ in tinh_rows if t == KHONG_RO), None)
    tinh = tinh_that + ([khong_ro] if khong_ro else [])
    return TongQuan(
        nhom={k: nhom.get(k, 0) for k in ("im", "tut", "moi")},
        tong=next((n for _, n, _, _ in lay("tong")), 0),
        hang=[(h, hang.get(h, 0)) for h in THU_TU_HANG],
        tinh=tinh,
        # Xếp theo DOANH THU chứ không theo số khách: khối này trả lời "ai
        # đang gánh bao nhiêu tiền", không phải "ai có nhiều khách nhất" — một
        # người ít khách nhưng khách lớn vẫn đáng chú ý hơn trên bảng tải.
        nhan_vien=[{"ma": k.split("|")[0], "ten": k.split("|", 1)[1],
                    "so_khach": n, "doanh_thu": int(d), "canh_bao": int(cb)}
                   for k, n, d, cb in sorted(lay("nv"), key=lambda x: -x[2])],
        dem_trang_thai={t: n for t, n, _, _ in lay("dem")},
        tong_tat_ca=next((n for _, n, _, _ in lay("tat_ca")), 0),
    )
