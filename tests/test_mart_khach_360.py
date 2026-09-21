"""Chỉ số mới của Customer 360 (migration 020).

Mọi test ở đây bảo vệ một câu: **một khái niệm chỉ có một công thức**. Nhịp mua
theo mã phải tính giống hệt nhịp mua của khách (trung vị), và nhóm việc "im lặng"
phải trả về đúng tập khách mà /can-xu-ly đang trả về.
"""
from datetime import timedelta

from kome import khach_hang as KH
from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY


def test_nhip_theo_ma_dung_trung_vi_nhu_nhip_cua_khach(conn, batch):
    """[IMPORTANT] Hai công thức cho cùng một khái niệm là hai con số sẽ trôi
    khỏi nhau. `mart.nhip_mua` dùng trung vị vì một khách mua đều 7 ngày rồi
    nghỉ Tết 30 ngày có trung bình ~9 ngày — đủ lệch để báo động sai."""
    _ho_so_khach(conn, batch, "N0001", "Quán nhịp")
    for i in range(5):                       # 5 lần, cách đều 7 ngày
        _mua(conn, batch, "N0001", HOM_NAY - timedelta(days=i * 7), hang="XT07")
    _neo(conn, batch)
    r = conn.execute(
        """SELECT nhip_ngay FROM mart.khach_mat_hang
           WHERE customer_code='N0001' AND product_code='XT07'""").fetchone()
    assert float(r[0]) == 7.0


def test_ma_mua_duoi_ba_lan_thi_nhip_la_NULL(conn, batch):
    """Hai điểm dữ liệu cho ra một 'nhịp' nghe như sự thật nhưng là tiếng ồn.
    Trang phải hiện `—`, nên view phải trả NULL chứ không trả một con số."""
    _ho_so_khach(conn, batch, "N0002", "Quán hai lần")
    _mua(conn, batch, "N0002", HOM_NAY, hang="XT07")
    _mua(conn, batch, "N0002", HOM_NAY - timedelta(days=9), hang="XT07")
    _neo(conn, batch)
    r = conn.execute(
        """SELECT nhip_ngay, du_kien_lan_toi FROM mart.khach_mat_hang
           WHERE customer_code='N0002' AND product_code='XT07'""").fetchone()
    assert r[0] is None and r[1] is None


def test_tre_ngay_chi_co_nghia_khi_da_qua_han(conn, batch):
    """Mã vừa mua hôm qua không 'trễ -6 ngày' — nó chưa tới hạn. Số âm ở cột
    'trễ' sẽ bị đọc thành 'sớm', mà đó không phải điều cột này nói."""
    _ho_so_khach(conn, batch, "N0003", "Quán trễ")
    for i in range(4):
        _mua(conn, batch, "N0003", HOM_NAY - timedelta(days=60 + i * 7), hang="XT07")
    _neo(conn, batch)
    r = conn.execute(
        """SELECT nhip_ngay, tre_ngay FROM mart.khach_mat_hang
           WHERE customer_code='N0003' AND product_code='XT07'""").fetchone()
    assert float(r[0]) == 7.0
    assert r[1] > 0, "mã ngừng mua 60 ngày với nhịp 7 ngày phải trễ"


def test_tre_ngay_la_NULL_va_du_kien_lan_toi_dung_khi_chua_qua_han(conn, batch):
    """[IMPORTANT] Đây mới là lý do điều kiện `hom_nay > du_kien_lan_toi` tồn
    tại: mã còn trong hạn (mới mua cách đây ít hơn một nhịp) phải hiện `—` ở
    cột trễ, không phải một số âm. Một cài đặt trả số âm vô điều kiện vẫn qua
    được test 'chỉ trễ khi quá hạn' phía trên nếu không có ca này."""
    _ho_so_khach(conn, batch, "N0004", "Quán chưa tới hạn")
    for i in range(4):                       # 4 lần, cách đều 7 ngày, lần cuối 3 ngày trước
        _mua(conn, batch, "N0004", HOM_NAY - timedelta(days=3 + i * 7), hang="XT07")
    _neo(conn, batch)
    r = conn.execute(
        """SELECT nhip_ngay, lan_cuoi, du_kien_lan_toi, tre_ngay FROM mart.khach_mat_hang
           WHERE customer_code='N0004' AND product_code='XT07'""").fetchone()
    nhip_ngay, lan_cuoi, du_kien_lan_toi, tre_ngay = r
    assert float(nhip_ngay) == 7.0
    assert du_kien_lan_toi == lan_cuoi + timedelta(days=7), \
        "du_kien_lan_toi phải bằng đúng lan_cuoi + nhip_ngay"
    assert tre_ngay is None, "còn trong hạn (mua cách đây 3 ngày, nhịp 7 ngày) không được có số trễ"


def test_hang_doanh_thu_phu_dung_100_phan_tram_khach_khong_trung_bac(conn, batch):
    """[IMPORTANT] Khách rơi ra khỏi mọi bậc là khách biến mất khỏi mọi bộ lọc
    hạng — không ai thấy họ nữa và không có gì báo."""
    for i in range(12):
        _ho_so_khach(conn, batch, f"H{i:04d}", f"Quán {i}")
        _mua(conn, batch, f"H{i:04d}", HOM_NAY - timedelta(days=5), tien=(i + 1) * 10_000)
    _neo(conn, batch)
    tong = conn.execute("SELECT count(*) FROM mart.khach_360").fetchone()[0]
    r = conn.execute(
        """SELECT count(*), count(DISTINCT customer_code), count(*) FILTER (WHERE hang IS NULL)
           FROM mart.hang_doanh_thu""").fetchone()
    assert r[0] == tong, "số dòng hạng phải bằng số khách"
    assert r[1] == tong, "không khách nào được xuất hiện hai lần"
    assert r[2] == 0, "không khách nào được thiếu hạng"
    assert {x[0] for x in conn.execute(
        "SELECT DISTINCT hang FROM mart.hang_doanh_thu").fetchall()} <= {"S", "A", "B", "C", "D"}


def test_khach_doanh_thu_cao_nhat_o_hang_S(conn, batch):
    for i in range(20):
        _ho_so_khach(conn, batch, f"H{i:04d}", f"Quán {i}")
        _mua(conn, batch, f"H{i:04d}", HOM_NAY - timedelta(days=5), tien=(i + 1) * 10_000)
    _neo(conn, batch)
    r = conn.execute(
        """SELECT hang FROM mart.hang_doanh_thu
           ORDER BY dt_12t DESC LIMIT 1""").fetchone()
    assert r[0] == "S"


def test_nhom_im_lang_trung_khop_voi_can_xu_ly(conn, batch):
    """[CRITICAL] `/can-xu-ly` và nhóm việc 'Im lặng' trả lời CÙNG một câu hỏi.
    Hai định nghĩa là hai trang nói hai điều, và người dùng không biết tin cái
    nào. Đợt 7 sẽ gộp chúng; tới lúc đó chúng phải bằng nhau."""
    for ma, nhip, ngung in (("I0001", 7, 30), ("I0002", 7, 2), ("I0003", 14, 60)):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}")
        for i in range(6):
            _mua(conn, batch, ma, HOM_NAY - timedelta(days=ngung + i * nhip))
    _neo(conn, batch)
    tu_nhom = {r[0] for r in conn.execute(
        "SELECT customer_code FROM mart.khach_nhom_viec WHERE nhom='im'").fetchall()}
    tu_trang = {k.ma for k in KH.can_xu_ly(conn)}
    assert tu_nhom == tu_trang, f"lệch: chỉ nhóm {tu_nhom - tu_trang}, chỉ trang {tu_trang - tu_nhom}"


def test_nhom_tut_bat_khach_hang_cao_dang_giam_manh(conn, batch):
    """[IMPORTANT] `tut` là đoạn SQL phức tạp nhất file (hai truy vấn con
    tương quan, cửa sổ trượt 30/90 ngày, ngưỡng 80%, cổng hạng S/A) — chưa có
    test nào canh nó trước vòng sửa này. Dựng 1 khách hạng cao (doanh thu cao
    nhất trong 5 khách -> vị trí 1/5 = 0,20 -> hạng A) có 30 ngày gần nhất tụt
    hẳn dưới 80% trung bình ba kỳ 30 ngày trước đó."""
    ma = "TU001"
    _ho_so_khach(conn, batch, ma, "Quán tụt")
    # 3 kỳ 30 ngày trước (31-120 ngày trước): đều 100.000 yên/lần -> TB 100.000/kỳ.
    for i in range(3):
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=40 + i * 30), tien=110_000)
    # 30 ngày gần nhất: chỉ 20.000 yên -> 20.000 < 0,8 * 100.000 = 80.000.
    _mua(conn, batch, ma, HOM_NAY - timedelta(days=10), tien=30_000)
    # 4 khách nền, doanh thu thấp hơn hẳn -> giữ TU001 ở vị trí cao nhất.
    for i, tien in enumerate((60_000, 50_000, 40_000, 30_000)):
        f = f"TUF{i}"
        _ho_so_khach(conn, batch, f, f"Quán nền {i}")
        _mua(conn, batch, f, HOM_NAY - timedelta(days=200), tien=tien)
    _neo(conn, batch)
    hang = conn.execute(
        "SELECT hang FROM mart.hang_doanh_thu WHERE customer_code=%s", (ma,)).fetchone()[0]
    assert hang in ("S", "A"), f"khách doanh thu cao nhất phải ở hạng cao, hạng thực={hang}"
    assert conn.execute(
        "SELECT count(*) FROM mart.khach_nhom_viec WHERE customer_code=%s AND nhom='tut'",
        (ma,)).fetchone()[0] == 1


def test_nhom_tut_khong_bat_khach_hang_cao_khong_giam(conn, batch):
    """Ca ngược lại của test trên: khách hạng cao nhưng doanh thu 30 ngày gần
    nhất KHÔNG tụt (bằng đúng trung bình ba kỳ trước) thì không được vào
    nhóm 'tut'."""
    ma = "TB001"
    _ho_so_khach(conn, batch, ma, "Quán ổn định")
    for i in range(3):
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=40 + i * 30), tien=110_000)
    # 30 ngày gần nhất mua bằng đúng mức trung bình các kỳ trước -> không tụt.
    _mua(conn, batch, ma, HOM_NAY - timedelta(days=10), tien=110_000)
    for i, tien in enumerate((60_000, 50_000, 40_000, 30_000)):
        f = f"TBF{i}"
        _ho_so_khach(conn, batch, f, f"Quán nền {i}")
        _mua(conn, batch, f, HOM_NAY - timedelta(days=200), tien=tien)
    _neo(conn, batch)
    hang = conn.execute(
        "SELECT hang FROM mart.hang_doanh_thu WHERE customer_code=%s", (ma,)).fetchone()[0]
    assert hang in ("S", "A"), f"khách doanh thu cao nhất phải ở hạng cao, hạng thực={hang}"
    assert conn.execute(
        "SELECT count(*) FROM mart.khach_nhom_viec WHERE customer_code=%s AND nhom='tut'",
        (ma,)).fetchone()[0] == 0


def test_nhom_moi_bat_khach_moi_da_im_qua_1_2_lan_nhip(conn, batch):
    """[IMPORTANT] Khách mới (đơn đầu trong 90 ngày) mà đã im quá 1,2 lần nhịp
    riêng của chính họ phải vào nhóm 'moi' — im ngay từ đầu là dấu hiệu khác
    hẳn một khách cũ đang chậm lại."""
    ma = "MOI01"
    _ho_so_khach(conn, batch, ma, "Quán mới sắp rời")
    # 3 lần mua cách đều 10 ngày, lần đầu 80 ngày trước (trong 90 ngày -> "mới").
    for i in range(3):
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=80 - i * 10))
    _neo(conn, batch)
    # lan_cuoi = 60 ngày trước, nhịp 10 ngày -> tỷ lệ im lặng 60/10 = 6,0 >= 1,2.
    assert conn.execute(
        "SELECT count(*) FROM mart.khach_nhom_viec WHERE customer_code=%s AND nhom='moi'",
        (ma,)).fetchone()[0] == 1


def test_nhom_moi_khong_bat_khach_moi_van_mua_deu(conn, batch):
    """Ca ngược lại: khách mới nhưng vẫn đang mua đều (chưa im tới 1,2 lần
    nhịp) thì không được vào nhóm 'moi'."""
    ma = "MOI02"
    _ho_so_khach(conn, batch, ma, "Quán mới còn đều")
    # 4 lần mua cách đều 10 ngày, lần đầu 40 ngày trước (trong 90 ngày -> "mới").
    for i in range(4):
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=40 - i * 10))
    _neo(conn, batch)
    # lan_cuoi = 10 ngày trước, nhịp 10 ngày -> tỷ lệ im lặng 10/10 = 1,0 < 1,2.
    assert conn.execute(
        "SELECT count(*) FROM mart.khach_nhom_viec WHERE customer_code=%s AND nhom='moi'",
        (ma,)).fetchone()[0] == 0


def test_khach_ngung_giao_dich_khong_vao_nhom_viec_nao(conn, batch):
    """Doanh nghiệp đã phá sản thì im lặng là đúng, không phải bất thường —
    cùng bất biến với migration 016."""
    _ho_so_khach(conn, batch, "P0001", "Quán cũ ※廃業※")
    for i in range(6):
        _mua(conn, batch, "P0001", HOM_NAY - timedelta(days=90 + i * 7))
    _neo(conn, batch)
    assert conn.execute(
        "SELECT count(*) FROM mart.khach_nhom_viec WHERE customer_code='P0001'"
    ).fetchone()[0] == 0


def test_tai_nhan_vien_liet_ke_du_nam_nguoi_ke_ca_nguoi_khong_co_khach(conn, batch):
    """LEFT JOIN chứ không JOIN: một người phụ trách chưa có khách nào vẫn phải
    hiện với số 0, nếu không thì bảng 'tải của từng nhân viên' im lặng bỏ sót
    đúng người đang rảnh."""
    _ho_so_khach(conn, batch, "T0001", "Quán T", salesperson_code="0104")
    _mua(conn, batch, "T0001", HOM_NAY - timedelta(days=3))
    _neo(conn, batch)
    rows = {r[0]: r for r in conn.execute(
        "SELECT salesperson_code, ten, so_khach, doanh_thu FROM mart.tai_nhan_vien").fetchall()}
    assert len(rows) == 5, "phải đủ 5 担当者 của OBC"
    assert rows["0104"][2] >= 1
    assert rows["0002"][2] == 0, "người chưa có khách vẫn phải hiện với số 0"
