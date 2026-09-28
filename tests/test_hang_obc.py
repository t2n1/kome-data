"""055 — hạng khách lấy từ 得意先ランク của OBC; khách Z / ZZ / ZZZ không vào danh sách gọi.

Chủ DN chốt 2026-09-28 (đặc tả docs/superpowers/specs/2026-09-28-hang-obc-design.md).
"""
import re
from datetime import timedelta
from pathlib import Path

from kome import khach_hang as KH
from kome import lien_he as LH
from kome.tuoi_du_lieu import hom_nay_o_nhat
from tests.test_khach_hang import HOM_NAY, _ho_so_khach, _mua, _mua_deu, _neo

MIGRATION = Path("db/migrations/055_hang_obc.sql")


def test_nhan_hang_cua_ham_SQL_KHOP_THU_TU_HANG_python(conn):
    """[IMPORTANT] `KH.THU_TU_HANG` là bản chép bắt buộc của các nhãn trong
    `mart.hang_obc` — chip lọc / thứ tự sắp / khối phân bố đọc nó. Lệch một nhãn là
    khách hạng đó không có chip nào để bấm và bộ lọc `?hang=` âm thầm bỏ nó đi."""
    nhan = set(re.findall(r"THEN '([^']+)'", MIGRATION.read_text(encoding="utf-8")
                          .split("CREATE FUNCTION mart.hang_obc")[1].split("$$;")[0]))
    assert nhan == set(KH.THU_TU_HANG)
    for ma, mong in (("0001", "S"), ("0005", "D"), ("0008", "ZZZ"), ("0999", "対象外")):
        assert conn.execute("SELECT mart.hang_obc(%s, 'x')", (ma,)).fetchone()[0] == mong


def test_ma_hang_la_hien_nguyen_van_ten_trong_la_NULL(conn):
    """Mã OBC chưa biết -> nguyên văn rank_name (không đoán); không có hạng -> NULL."""
    assert conn.execute("SELECT mart.hang_obc('0042', 'Xランク')").fetchone()[0] == "Xランク"
    assert conn.execute("SELECT mart.hang_obc('', '')").fetchone()[0] is None
    assert conn.execute("SELECT mart.hang_obc(NULL, NULL)").fetchone()[0] is None


def test_danh_ba_va_ho_so_mang_hang_OBC_khong_phai_hang_tu_tinh(conn, batch):
    """[CRITICAL] Ca thật của khách 000000000179 (HA VY QUAN): OBC ZZZ, web từng
    ghi B vì tự xếp theo doanh thu. Nay web phải ghi đúng điều OBC ghi."""
    ten = "ZZZランク/電話禁止又は不要"
    _ho_so_khach(conn, batch, "000000000179", "HA VY QUAN", rank_code="0008", rank_name=ten)
    _mua(conn, batch, "000000000179", HOM_NAY, tien=900_000)
    _neo(conn, batch)
    k = next(x for x in KH.danh_ba(conn)["khach"] if x["ma"] == "000000000179")
    assert (k["hang"], k["hang_ten"], k["khong_goi"]) == ("ZZZ", ten, True)
    h = KH.ho_so(conn, "000000000179")
    assert (h.khach.hang, h.khach.hang_ten, h.khach.khong_goi) == ("ZZZ", ten, True)
    assert KH.trang_danh_sach(KH.danh_ba(conn), hang="ZZZ").tong == 1


def _bon_khach_im(conn, batch):
    """Bốn khách im lặng ≥ 4× nhịp (trang_thai 'da_roi_bo'): ba mang hạng Z/ZZ/ZZZ,
    một hạng C. Chỉ khách hạng C được gọi."""
    for ma, rc in (("GZ001", "0006"), ("GZ002", "0007"), ("GZ003", "0008"), ("GC004", "0004")):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", rank_code=rc)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=40)
    _neo(conn, batch)


def test_khach_Z_ZZ_ZZZ_KHONG_vao_bat_ky_danh_sach_goi_nao(conn, batch):
    """[CRITICAL] Mọi danh sách gọi đọc CÙNG cổng `khong_goi` (mart.dau_hieu_khach).
    Một chỗ quên cổng là nhân viên gọi đúng khách OBC ghi 電話禁止."""
    _bon_khach_im(conn, batch)
    goi = {"GC004"}
    im = {r[0] for r in conn.execute(
        "SELECT customer_code FROM mart.khach_nhom_viec WHERE nhom = 'im'").fetchall()}
    assert im == goi
    assert {k.ma for k in KH.can_xu_ly(conn)} == goi
    dem, ds = KH.dem_va_can_xu_ly(conn)
    assert {k.ma for k in ds} == goi
    assert dem["da_roi_bo"] == 4, "thanh sức khoẻ vẫn đếm mọi khách"
    dem_goi, _ = KH.dem_va_can_xu_ly(conn, chi_goi=True)
    assert dem_goi["da_roi_bo"] == 1, "ô KPI 'cần gọi' chỉ đếm khách được gọi"
    assert {r[0] for r in conn.execute(
        "SELECT customer_code FROM mart.uu_tien_lien_he").fetchall()} == goi
    ds_lh = LH.danh_sach(conn, hom_nay_o_nhat())
    assert {t.ma for c in ds_lh.cot for t in c.the} == goi
    assert conn.execute("SELECT sum(so_khach_canh_bao) FROM mart.tai_nhan_vien").fetchone()[0] == 1
    assert conn.execute("SELECT sum(can_goi) FROM mart.khach_theo_tinh").fetchone()[0] == 1
    db = KH.danh_ba(conn)
    assert {k["ma"] for k in db["khach"] if "im" in k["nhom"]} == goi
    # Nhãn cặp khách–mã và nhãn tháng: 'khong_goi' cho cả ba hạng Z.
    assert {r[0] for r in conn.execute(
        "SELECT DISTINCT customer_code FROM mart.khach_mat_hang WHERE trang_thai_cap = 'khong_goi'"
    ).fetchall()} == {"GZ001", "GZ002", "GZ003"}


def test_khach_Z_van_la_khach_that_trang_thai_khong_doi(conn, batch):
    """[IMPORTANT] Z/ZZ/ZZZ chỉ ra khỏi danh sách gọi — trạng thái KHÔNG thành
    'ngung_giao_dich' (583/604 khách ZZZ vẫn đang mua), vẫn có trong danh bạ."""
    _bon_khach_im(conn, batch)
    tt = dict(conn.execute(
        "SELECT customer_code, trang_thai FROM mart.khach_360 WHERE customer_code LIKE 'G%'").fetchall())
    assert set(tt.values()) == {"da_roi_bo"}
    assert {"GZ001", "GZ002", "GZ003"} <= {k["ma"] for k in KH.danh_ba(conn)["khach"]}


def test_nhom_tut_KHONG_bat_khach_ZZZ_hang_cao(conn, batch):
    """Nhóm 'tut' xét S/A của OBC — và cũng qua cổng khong_goi: khách OBC xếp S
    nhưng tên có ※廃業※ không được vào."""
    ma = "TZ001"
    _ho_so_khach(conn, batch, ma, "※廃業※Quán tụt", rank_code="0001")
    for i in range(3):
        _mua(conn, batch, ma, HOM_NAY - timedelta(days=40 + i * 30), tien=110_000)
    _neo(conn, batch)
    assert conn.execute(
        "SELECT count(*) FROM mart.khach_nhom_viec WHERE customer_code = %s", (ma,)).fetchone()[0] == 0
