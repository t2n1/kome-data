"""Tổng quan theo MỘT kỳ so (đặc tả 2026-09-28-ky-so-sanh-toan-web-design.md §7 đợt 1).

Mỗi khối có phép so phải đọc ĐÚNG `so_sanh[0]` của khoảng — đổi chip "Tháng trước"
thì mọi khối cùng đổi, không khối nào lặng lẽ so năm trước. Các chuỗi theo tháng
(Theo tháng, luỹ kế dạng Kỳ, khách mới, quý) dời `lech_thang` và phải khớp đúng
số của `mart` trên tháng dời.
"""
from datetime import date

from kome import khoang_xem as KX
from kome import khoi_tong_quan as KTQ
from tests.test_phan_tich_mart import _ban

KHOI_CO_SO = ("kpi", "xu_huong", "theo_thang", "ns_thang", "so_sanh_sale", "khach_moi",
              "danh_sach_khach", "hieu_suat_nganh", "bien_loi_nhuan")


def _gieo(conn, batch):
    # Tháng 5, 6, 7/2026 + tháng 6, 7/2025 — mốc = 15/7/2026 (tháng 7 dở dang).
    for d, tien in ((date(2025, 5, 8), 11_000), (date(2025, 6, 10), 22_000), (date(2025, 7, 3), 33_000), (date(2025, 7, 20), 44_000),
                    (date(2026, 5, 12), 55_000), (date(2026, 6, 4), 66_000), (date(2026, 6, 25), 77_000),
                    (date(2026, 7, 2), 88_000), (date(2026, 7, 15), 99_000)):
        _ban(conn, batch, d, "AA01", amount=tien, tax=0, gp=tien // 5)


def _dt(conn, tu, den):
    return int(conn.execute("SELECT dt FROM mart.tong_khoang(%s, %s)", (tu, den)).fetchone()[0] or 0)


def test_moi_khoi_co_phep_so_doc_CUNG_so_sanh_0(conn, batch):
    _gieo(conn, batch)
    for ss in ("", "truoc"):
        ts = KX.doc_tham_so(ss=ss)
        ma = "thang_truoc" if ss else "nam_truoc"
        for k in KHOI_CO_SO:
            d = KTQ.KHOI[k][0](conn, None, ts)
            assert d["khoang"].so_sanh[0].ma == ma, k
            assert len(d["khoang"].so_sanh) == 1, k


def test_kpi_spark_ss_la_chuoi_ky_so(conn, batch):
    _gieo(conn, batch)
    d = KTQ.kpi(conn, None, KX.doc_tham_so(ss="truoc"))["doanh_thu"]
    assert len(d["spark"]) == len(d["spark_ss"]) and len(d["so_sanh"]) == 1
    assert sum(v or 0 for v in d["spark_ss"]) == _dt(conn, date(2026, 6, 1), date(2026, 6, 15))


def test_theo_thang_doi_dung_lech_thang(conn, batch):
    _gieo(conn, batch)
    t = {x["thang"]: x for x in KTQ.theo_thang(conn, None, KX.doc_tham_so(ss="truoc"))["thang"]}
    assert t["2026-06"]["cung_ky"] == _dt(conn, date(2026, 5, 1), date(2026, 5, 31)), "tháng trước = 5/2026"
    # Tháng 7 dở dang (tới 15/7) so CÙNG DẢI NGÀY 1 → 15/6.
    assert t["2026-07"]["cung_ky"] == _dt(conn, date(2026, 6, 1), date(2026, 6, 15))
    t = {x["thang"]: x for x in KTQ.theo_thang(conn, None, KX.doc_tham_so())["thang"]}
    assert t["2026-06"]["cung_ky"] == 22_000 and t["2026-07"]["cung_ky"] == 33_000, "năm trước, tháng 7 cắt tới 15/7"
    # Kỳ so không lệch tròn tháng -> không cột so nào (không đoán).
    ts = KX.doc_tham_so(thang="2026-07", ss_tu="2026-06-03", ss_den="2026-06-10")
    assert all(x["cung_ky"] is None for x in KTQ.theo_thang(conn, None, ts)["thang"])


def test_luy_ke_ky_so_tai_ngay_cuoi_bang_tong_dai_so(conn, batch):
    _gieo(conn, batch)
    kx = KX.giai_conn(conn, KX.doc_tham_so(ss="truoc"))
    ns = {"muc_tieu": None, "muc_tieu_lg": None, "luy_ke": []}
    d = KTQ.duong_luy_ke(conn, kx, ns)
    s = kx.so_sanh[0]
    ss = [x["ss"] for x in d["diem"] if x["ss"] is not None]
    assert d["nhan_ss"] == s.nhan
    assert len(ss) == (s.den - s.tu).days + 1 and ss[-1] == _dt(conn, s.tu, s.den)


def test_sale_co_doanh_thu_ky_so(conn, batch):
    _gieo(conn, batch)
    d = KTQ.ngan_sach(conn, None, KX.doc_tham_so(ss="truoc"))
    (n,) = [x for x in d["nguoi"] if x["ma"] == "0104"]
    assert n["dt_ss"] == _dt(conn, date(2026, 6, 1), date(2026, 6, 15))
    assert d["so_sanh"]["ma"] == "thang_truoc"


def test_quy_so_nam_truoc_va_khong_so_khi_lech_le_quy(conn, batch):
    _gieo(conn, batch)
    q = KTQ.bien_loi_nhuan(conn, None, KX.doc_tham_so())
    assert q["so_quy"] == 4
    cuoi = q["quy"][-1]                                   # quý 4 kỳ 2026 = tháng 5, 6, 7
    assert (cuoi["tu"], cuoi["den"]) == ("2026-05", "2026-07")
    assert cuoi["doanh_thu_ss"] == 11_000 + 22_000 + 33_000 + 44_000, "cùng các tháng 5–7/2025"
    assert q["quy"][0]["doanh_thu_ss"] is None, "quý dời vào trước dải dữ liệu thì không so"
    q = KTQ.bien_loi_nhuan(conn, None, KX.doc_tham_so(ss="truoc"))
    assert q["so_quy"] is None and all(x["doanh_thu_ss"] is None for x in q["quy"])
