"""Đợt 8 — Dự báo doanh thu. Phần thuần (không CSDL) + ngân sách truy vấn + web."""
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from kome import du_bao as DB
from kome import ve_du_bao as VDB
from kome.web.app import create_app
from tests.test_khach_hang import _ho_so_khach, _mua_deu, _neo


def _lich(tu: date, den: date, hom_nay: date, dt_ngay=lambda d: 100) -> list[DB.Ngay]:
    ds, d = [], tu
    while d <= den:
        kd = d.weekday() < 5
        ds.append(DB.Ngay(d, kd, (dt_ngay(d) if kd else 0) if d <= hom_nay else None))
        d += timedelta(days=1)
    return ds


# ---- Chốt tháng ------------------------------------------------------------

def test_cong_thuc_chot_thang():
    assert DB.du_bao_chot(1000, 10, 22) == 1000 + 100 * 12
    assert DB.du_bao_chot(0, 0, 22) == 0


def test_chot_thang_giua_thang_co_khoang_tu_sai_so_that():
    """Khoảng thấp–cao là sai số THẬT của cách tính trên các tháng trước, không
    phải hệ số bịa. Bán đều mỗi ngày làm việc → mọi tháng cũ sai số đúng 1,0 →
    khoảng co lại đúng bằng dự báo cơ sở."""
    hn = date(2026, 7, 15)
    ds = _lich(date(2026, 1, 1), date(2026, 7, 31), hn)
    c = DB.chot_thang(ds, hn)
    e = sum(1 for n in ds if n.la_kd and date(2026, 7, 1) <= n.ngay <= hn)
    n = sum(1 for x in ds if x.la_kd and x.ngay.month == 7)
    assert (c.e, c.n) == (e, n) and c.da_ban == 100 * e
    assert c.co_so == 100 * n
    assert c.thap == c.cao == c.co_so
    assert len(c.kiem) == 6 and all(abs(k.lech) < 1e-9 for k in c.kiem)
    assert c.moc_kiem == e


def test_chot_thang_it_thang_cu_thi_khong_bịa_khoang():
    hn = date(2026, 3, 10)
    ds = _lich(date(2026, 1, 1), date(2026, 3, 31), hn)
    c = DB.chot_thang(ds, hn)
    assert c.thap is None and c.cao is None


def test_thang_du_ngay_thi_du_bao_bang_da_ban_va_kiem_o_giua_thang():
    hn = date(2026, 7, 31)
    ds = _lich(date(2026, 1, 1), hn, hn)
    c = DB.chot_thang(ds, hn)
    assert c.xong and c.co_so == c.da_ban == c.thap == c.cao
    assert c.moc_kiem == DB.MOC_KIEM_GIUA_THANG


def test_thang_dau_thieu_ngay_lam_viec_khong_vao_kiem():
    """Tháng đầu kho bắt đầu giữa chừng thì KHÔNG đủ để kiểm — lấy nó là so
    dự báo nửa tháng với thực tế nửa tháng."""
    hn = date(2026, 7, 15)
    ds = _lich(date(2026, 1, 14), date(2026, 7, 31), hn)
    assert "2026-01" not in [k.thang for k in DB.chot_thang(ds, hn).kiem]


# ---- 12 tháng --------------------------------------------------------------

def test_he_so_la_TY_SO_CUA_CAC_TONG_khong_phai_trung_binh_ty_so():
    """[IMPORTANT] Bất biến tỷ suất của CLAUDE.md áp cả cho hệ số tăng trưởng:
    một tháng nhỏ tăng gấp đôi không được kéo cả năm dự báo lên như một
    tháng lớn."""
    hn = date(2026, 2, 28)

    def dt(d):
        if d.year == 2025 and d.month == 1:
            return 1000
        if d.year == 2026 and d.month == 1:
            return 1100          # tháng lớn: +10%
        if d.year == 2025 and d.month == 2:
            return 10
        if d.year == 2026 and d.month == 2:
            return 20            # tháng nhỏ: ×2
        return 500
    ds = _lich(date(2025, 1, 1), date(2026, 2, 28), hn, dt)
    m = DB.muoi_hai_thang(ds, hn)
    A = {}
    for n in ds:
        A[DB.thang(n.ngay)] = A.get(DB.thang(n.ngay), 0) + (n.dt or 0)
    g_dung = (A["2026-01"] + A["2026-02"]) / (A["2025-01"] + A["2025-02"])
    assert m.doi_chieu == ["2026-01", "2026-02"]
    assert m.he_so == pytest.approx(g_dung)
    r1, r2 = A["2026-01"] / A["2025-01"], A["2026-02"] / A["2025-02"]
    assert m.he_so_thap == pytest.approx(min(r1, r2)) and m.he_so_cao == pytest.approx(max(r1, r2))
    # trung bình các tỷ số sẽ ra ~1,5 — tỷ số của các tổng thì gần tháng lớn
    assert m.he_so < 1.2 < (r1 + r2) / 2
    assert m.du_bao[0].thang == "2026-03"
    assert m.du_bao[0].co_so == round(A["2025-03"] * g_dung)
    assert m.du_bao[0].thap <= m.du_bao[0].co_so <= m.du_bao[0].cao
    # "so với năm trước" chia cho CÙNG các tháng đó năm trước, không cho 12 tháng qua
    assert m.tong_cung_ky == sum(A[DB.cong_thang(t.thang, -12)] for t in m.du_bao)


def test_chua_du_13_thang_thi_khong_du_bao_nam():
    hn = date(2026, 5, 31)
    m = DB.muoi_hai_thang(_lich(date(2026, 1, 1), hn, hn), hn)
    assert m.du_bao == [] and m.he_so is None


def test_ve_hai_bieu_do_khong_no():
    hn = date(2026, 7, 15)
    ds = _lich(date(2025, 3, 3), date(2026, 7, 31), hn)
    c = DB.chot_thang(ds, hn, ngan_sach=3000)
    g = VDB.ve_chot_thang(c)
    assert g["co"] and g["tt"] and g["cs"] and g["ns"]
    b = VDB.ve_muoi_hai_thang(DB.muoi_hai_thang(ds, hn), "cao")
    # Tháng 7/2026 chưa đủ ngày (mốc 15/7) nên không làm gốc cho 7/2027 được:
    # 11 cột dự báo chứ không bịa cột thứ 12.
    assert b["co"] and len(b["rau"]) == 11 and b["x_chia"]


# ---- CSDL ------------------------------------------------------------------

def _nen(conn, batch):
    for ma, im in (("K0021", 3), ("K0022", 20), ("K0023", 40)):
        _ho_so_khach(conn, batch, ma, f"Quan {ma}")
        _mua_deu(conn, batch, ma, nhip=7, so_lan=6, ngung_truoc=im)
    _neo(conn, batch)


def test_ca_man_dung_3_truy_van(conn, batch, monkeypatch):
    """[IMPORTANT] Một lượt hỏi qua pooler Tokyo ~260 ms; khach_360 phải vật
    hoá đúng MỘT lần (CTE MATERIALIZED trong khach())."""
    _nen(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    d = DB.du_bao(conn)
    assert dem["n"] == 3
    assert d.chot.hom_nay == date(2026, 7, 31)


def test_don_ky_vong_va_nguy_co(conn, batch):
    _nen(conn, batch)
    k = DB.du_bao(conn).kh
    # K0021 mua nhịp 7, lần cuối cách mốc 3 ngày → dự kiến sau 4 ngày
    assert [x.ma for x in k.ky_vong] == ["K0021"]
    assert k.ky_vong[0].du_kien == date(2026, 7, 31) + timedelta(days=4)
    assert k.ky_vong[0].dung_nhip == k.ky_vong[0].so_khoang == 5
    assert {x.ma for x in k.nguy_co} == {"K0022", "K0023"}
    assert k.so_nguy_co == 2


def test_lich_kinh_doanh_la_nguon_cua_ngay_kinh_doanh(conn):
    """MỘT định nghĩa "ngày làm việc": ngay_kinh_doanh (026) giờ ĐỌC
    lich_kinh_doanh (031) — thêm ngày lễ ở một chỗ là đủ."""
    r = conn.execute(
        """SELECT (SELECT ngay_kd FROM mart.ngay_kinh_doanh WHERE thang = '2026-07'),
                  (SELECT count(*) FROM mart.lich_kinh_doanh
                   WHERE la_ngay_kd AND to_char(ngay, 'YYYY-MM') = '2026-07'),
                  has_table_privilege('kome_ingest', 'mart.lich_kinh_doanh', 'SELECT')""").fetchone()
    # 7/2026: 23 ngày thường, trừ 海の日 20/7 (thứ Hai, migration 032) = 22
    assert r[0] == r[1] == 22 and r[2] is True


# ---- Web -------------------------------------------------------------------

def test_trang_du_bao(conn, batch, test_db_url):
    _nen(conn, batch)
    c = TestClient(create_app(db_url=test_db_url))
    t = c.get("/du-bao").text
    for khoi in ("Chốt tháng 07/2026", "12 tháng tới", "Đơn kỳ vọng 14 ngày tới",
                 "Nguy cơ ngừng mua", "Dự báo đã chuẩn tới đâu"):
        assert khoi in t
    assert 'href="/du-bao" class="dang-xem" aria-current="page"' in t
    assert c.get("/du-bao?kb=bay").status_code == 200


def test_trang_du_bao_kho_rong(conn, test_db_url):
    t = TestClient(create_app(db_url=test_db_url)).get("/du-bao").text
    assert "chưa có gì để dự báo" in t
