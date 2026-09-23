"""Ngày lễ quốc gia Nhật (migration 032) — bộ sinh, khối VALUES, và bốn chỗ
dùng định nghĩa "ngày làm việc"."""
import re
import sys
from datetime import date

from kome.config import GOC
from kome.coverage import NGHI, tinh_bang_ngay
from kome.tuoi_du_lieu import tinh_tuoi
from tests.test_coverage import _o_ngay
from tests.test_tuoi_du_lieu import _luc

sys.path.insert(0, str(GOC / "scripts"))
import sinh_ngay_le as S  # noqa: E402

# Lịch CHÍNH THỨC của 内閣府 (đã công bố) — đối chứng độc lập với bộ sinh.
CHINH_THUC = {
    2024: ["01-01", "01-08", "02-11", "02-12", "02-23", "03-20", "04-29", "05-03", "05-04",
           "05-05", "05-06", "07-15", "08-11", "08-12", "09-16", "09-22", "09-23", "10-14",
           "11-03", "11-04", "11-23"],
    2025: ["01-01", "01-13", "02-11", "02-23", "02-24", "03-20", "04-29", "05-03", "05-04",
           "05-05", "05-06", "07-21", "08-11", "09-15", "09-23", "10-13", "11-03", "11-23",
           "11-24"],
    2026: ["01-01", "01-12", "02-11", "02-23", "03-20", "04-29", "05-03", "05-04", "05-05",
           "05-06", "07-20", "08-11", "09-21", "09-22", "09-23", "10-12", "11-03", "11-23"],
}


def test_bo_sinh_khop_lich_chinh_thuc():
    for y, ds in CHINH_THUC.items():
        assert [d.strftime("%m-%d") for d in S.ngay_le(y)] == ds, y
    assert S.ngay_le(2026)[date(2026, 9, 22)] == "国民の休日"
    assert S.ngay_le(2025)[date(2025, 5, 6)] == "振替休日"


def test_khoi_values_cua_migration_la_dung_ban_sinh():
    """[IMPORTANT] Migration viết danh sách thành CHỮ để đọc được — test canh nó
    không bị ai sửa tay lệch khỏi luật."""
    sql = (GOC / "db" / "migrations" / "032_ngay_le_nhat.sql").read_text(encoding="utf-8")
    khoi = re.search(r"FROM \(VALUES\n(.*?)\n\) AS v", sql, re.S).group(1)
    assert khoi == S.khoi_values(2024, 2035)


def test_lich_kinh_doanh_loai_ngay_le(conn):
    r = conn.execute(
        """SELECT la_ngay_kd, ngay_le FROM mart.lich_kinh_doanh WHERE ngay = '2026-05-06'""").fetchone()
    assert r == (False, "振替休日")
    # 5/2026: 21 ngày thường − 4/5, 5/5, 6/5 = 18 — ngân sách đọc cùng định nghĩa
    assert conn.execute(
        "SELECT ngay_kd FROM mart.ngay_kinh_doanh WHERE thang = '2026-05'").fetchone()[0] == 18


def test_ngay_le_thi_o_tuoi_du_lieu_im_lang(conn):
    """Ngày lễ không ai xuất file — báo đỏ là báo động giả."""
    t = tinh_tuoi(conn, _luc(2026, 9, 21, 15, 0))   # 敬老の日, thứ Hai
    assert [n.trang_thai for n in t.nguon] == ["nghi", "nghi", "nghi"]


def test_ngay_le_la_NGHI_tren_bang_phu(conn):
    bang = tinh_bang_ngay(conn, hom_nay=date(2026, 9, 25))
    assert _o_ngay(bang, date(2026, 9, 22), "ban").trang_thai == NGHI   # 国民の休日
    assert _o_ngay(bang, date(2026, 9, 23), "ban").trang_thai == NGHI   # 秋分の日
