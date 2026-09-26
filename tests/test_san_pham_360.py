"""Tầng Python + API của Sản phẩm 360 (kome/san_pham_360.py)."""
from datetime import timedelta

import pytest

from kome import khach_hang as KH
from kome import ho_so_khach as HSK
from kome import san_pham as SP
from kome import san_pham_360 as SP360
from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY
from tests.test_mart_san_pham import _san_pham, _ton
from tests.test_san_pham import _dem_truy_van, _gia, _khach_web


def _gieo_mot_ma(conn, batch, ma="Q1"):
    _san_pham(conn, batch, ma, ten="Gạo thử 360")
    _ton(conn, batch, ma, sl=300)
    _ho_so_khach(conn, batch, "KQ01", "Quán đều")
    for i in range(4):
        _mua(conn, batch, "KQ01", HOM_NAY - timedelta(days=i * 7), hang=ma)
    _gia(conn, batch, ma, "03", 5250)
    _neo(conn, batch)


def test_ho_so_khong_co_ma_tra_None(conn, batch):
    _neo(conn, batch)
    assert SP360.ho_so(conn, "KHONG-CO") is None


def test_ho_so_khong_qua_5_truy_van_va_khong_rong(conn, batch, monkeypatch):
    _gieo_mot_ma(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    h = SP360.ho_so(conn, "Q1")
    assert h is not None and h["sp"].ma == "Q1"
    assert dem["n"] <= 5, f"ho_so() chạy {dem['n']} truy vấn"


def test_ho_so_dt_12t_KHOP_voi_danh_muc(conn, batch):
    """[CRITICAL — soát vòng 1] `ho_so()["dt_12t"]` phải đúng BẰNG cửa sổ 12
    tháng của danh mục (`SP.danh_muc`, `sales_date > hom_nay - 365`), không
    phải một tổng 12 THÁNG LỊCH tính lại từ `h["thang"]` ở trình duyệt — hai
    cửa sổ khác nhau (lịch vs. ngày) sẽ cho hai con số cho CÙNG một mã trên
    hai màn."""
    _gieo_mot_ma(conn, batch)
    ngay_nam_truoc = HOM_NAY - timedelta(days=365)
    _ho_so_khach(conn, batch, "KQ03", "Khách năm trước 2")
    _mua(conn, batch, "KQ03", ngay_nam_truoc, hang="Q1")
    _neo(conn, batch)

    h = SP360.ho_so(conn, "Q1")
    dm = next(m for m in SP.danh_muc(conn)["ma"] if m["ma"] == "Q1")
    assert h["dt_12t"] == dm["dt_12t"]
    assert h["lg_12t"] == dm["lg_12t"]
    assert h["dt_12t"] > 0, "gieo hỏng: phải có doanh thu 12 tháng thật để so"


def test_ho_so_24_thang_co_cot_nam_truoc(conn, batch):
    """`_gieo_mot_ma` chỉ mua trong 4 tuần gần đây, không có gì đúng 12 tháng
    trước — nếu chỉ so `dt_nam_truoc == doanh_thu`, test PASS RỖNG (0 == 0).
    Seed thêm một phiếu ở đúng tháng cách HOM_NAY 365 ngày (khách mới, không
    đụng _gieo_mot_ma) để có giá trị THẬT cần so khớp."""
    _gieo_mot_ma(conn, batch)
    ngay_nam_truoc = HOM_NAY - timedelta(days=365)
    _ho_so_khach(conn, batch, "KQ02", "Khách năm trước")
    _mua(conn, batch, "KQ02", ngay_nam_truoc, hang="Q1")
    _neo(conn, batch)

    t = SP360.ho_so(conn, "Q1")["thang"]
    assert t[-13]["thang"] == f"{ngay_nam_truoc:%Y-%m}", "seed sai tháng: không nằm đúng 12 tháng trước"
    assert len(t) == 24 and t[-1]["thang"] == f"{HOM_NAY:%Y-%m}"
    assert t[-1]["doanh_thu"] > 0
    assert t[-1]["dt_nam_truoc"] == t[-13]["doanh_thu"]
    assert t[-1]["dt_nam_truoc"] > 0


def test_mua_lai_TRUNG_TAP_voi_lich_mua_cua_ho_so_khach(conn, batch):
    """[CRITICAL] Một khái niệm hai chiều: cặp (khách, mã) nằm ở "khách đến ngày mua lại"
    của mã khi và chỉ khi mã nằm ở "Mã đến ngày mua lại" (lich_mua) của khách."""
    _gieo_mot_ma(conn, batch)
    h = SP360.ho_so(conn, "Q1")
    ma_khach = {x["ma"] for x in h["mua_lai"]}
    kh = KH.ho_so(conn, "KQ01")
    lich = HSK.lich_mua(kh.tat_ca_mat_hang, HOM_NAY)   # đúng lời gọi của ho_so_khach.py:154
    co_q1 = any(m["ma"] == "Q1" for m in lich["ma"])
    assert ("KQ01" in ma_khach) == co_q1
    assert co_q1, "gieo hỏng: KQ01 mua 4 lần nhịp 7 ngày phải có ngày dự kiến"


# ---------------------------------------------------------------------------
# Bốn tab: tab_khach, tab_thoi_gian, tab_gia, tab_ban_them
# ---------------------------------------------------------------------------

def test_tab_khach_khong_qua_3_luot(conn, batch, monkeypatch):
    _gieo_mot_ma(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    t = SP360.tab_khach(conn, "Q1")
    assert t["tap_trung"] and len(t["tinh"]["o"]) == 47
    assert [k["ma"] for k in t["dang_mua"]] == ["KQ01"]
    assert dem["n"] <= 3, dem["n"]


def test_tab_khach_bien_theo_nguoi_TU_MAY_CHU(conn, batch):
    """[Fix round 1] `bien` của mỗi người phụ trách phải tính SẴN ở máy chủ (tỷ số
    của các tổng), không để trình duyệt tự chia lai_gop/doanh_thu. Seed `_gieo_mot_ma`
    dùng `_mua` mặc định: gp=30.000, DT thuần = 110.000 - 10.000 = 100.000 mỗi dòng,
    4 dòng cùng người phụ trách → 120.000 / 400.000 = 0,3 đúng."""
    _gieo_mot_ma(conn, batch)
    nguoi = SP360.tab_khach(conn, "Q1")["nguoi"]
    assert nguoi, "gieo hỏng: phải có ít nhất một người phụ trách"
    assert nguoi[0]["doanh_thu"] == 400_000 and nguoi[0]["lai_gop"] == 120_000, \
        "seed không còn khớp giả định 4 dòng × (DT thuần 100.000, gp 30.000)"
    assert nguoi[0]["bien"] == pytest.approx(0.3)


def test_tab_khach_tinh_bac_0_la_DUNG_BANG_0(conn, batch):
    _gieo_mot_ma(conn, batch)
    o = {x["ten"]: x for x in SP360.tab_khach(conn, "Q1")["tinh"]["o"]}
    assert o["東京都"]["bac"] > 0 and o["和歌山県"]["bac"] == 0


@pytest.mark.parametrize("ham, tran", [("tab_thoi_gian", 2), ("tab_gia", 2), ("tab_ban_them", 2)])
def test_tab_con_lai_trong_tran(conn, batch, monkeypatch, ham, tran):
    _gieo_mot_ma(conn, batch)
    dem = _dem_truy_van(conn, monkeypatch)
    t = getattr(SP360, ham)(conn, "Q1")
    assert t, "đếm một hàm trả rỗng thì không đếm gì"
    assert dem["n"] <= tran, f"{ham} chạy {dem['n']} lượt"


def test_tab_thoi_gian_nhip_dem_cap_chua_du_rieng(conn, batch):
    _gieo_mot_ma(conn, batch)
    nhip = {x["nhom"]: x["so_cap"] for x in SP360.tab_thoi_gian(conn, "Q1")["nhip"]}
    assert nhip.get("≤7") == 1          # KQ01 nhịp 7 ngày
    assert nhip.get("chua_du") == 0     # khách neo 000000000999 mua XT07, không phải Q1


@pytest.mark.parametrize("duoi, tran", [("khach", 3), ("thoi-gian", 2), ("gia", 2), ("ban-them", 2), ("", 5)])
def test_ngan_sach_luot_hoi_api_360(conn, batch, test_db_url, monkeypatch, duoi, tran):
    import psycopg
    _gieo_mot_ma(conn, batch)
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)
    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    url = "/api/san-pham/Q1" + (f"/{duoi}" if duoi else "")
    r = _khach_web(test_db_url).get(url)
    assert r.status_code == 200, r.text
    assert dem["n"] <= tran, f"{url} chạy {dem['n']} lượt, trần {tran}"


def test_api_tab_ma_khong_co_tra_404(conn, batch, test_db_url):
    _neo(conn, batch)
    c = _khach_web(test_db_url)
    for duoi in ("khach", "thoi-gian", "gia", "ban-them"):
        assert c.get(f"/api/san-pham/KHONG-CO/{duoi}").status_code == 404, duoi
