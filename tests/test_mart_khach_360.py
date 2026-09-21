"""Chỉ số mới của Customer 360 (migration 020).

Mọi test ở đây bảo vệ một câu: **một khái niệm chỉ có một công thức**. Nhịp mua
theo mã phải tính giống hệt nhịp mua của khách (trung vị), và nhóm việc "im lặng"
phải trả về đúng tập khách mà /can-xu-ly đang trả về.
"""
from datetime import date, timedelta

import pytest

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
