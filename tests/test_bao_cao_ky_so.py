"""Báo cáo theo MỘT kỳ so (đặc tả 2026-09-28-ky-so-sanh-toan-web-design.md §7 đợt 2).

Mọi khối có phép so của /bao-cao đọc `so_sanh[0]` của khoảng — và vẫn ≤ 11 lượt
hỏi: phép so đi CHUNG câu có sẵn (người phụ trách FULL JOIN hai dải, ngành × tháng
dời `lech_thang` thay câu cũ, luỹ kế kỳ so cộng từ số đã có).
"""
from dataclasses import asdict
from datetime import date

from kome import ban_khoang as BK
from kome import bao_cao as BC
from kome import khoang_xem as KX
from kome.ve_phan_tich import ve_duong_nho
from tests.test_ban_khoang import _gieo


def _kx(conn, **ts):
    return KX.giai_conn(conn, KX.doc_tham_so(**ts))


def _dt_sale(conn, tu, den):
    return {r[0]: int(r[1]) for r in conn.execute(
        "SELECT salesperson_code, dt FROM mart.sale_khoang(%s, %s)", (tu, den)).fetchall()}


def test_nguoi_phu_trach_mang_doanh_thu_ky_so_FULL_JOIN(conn, batch):
    _gieo(conn, batch)
    kx = _kx(conn, ss="truoc")                     # 1 → 15/7/2026, so 1 → 15/6/2026
    s = kx.so_sanh[0]
    nv = {n["ma"]: n for n in BK.sale(conn, kx)}
    ss = _dt_sale(conn, s.tu, s.den)
    assert {m: n["dt_ss"] for m, n in nv.items() if n["dt_ss"]} == {m: v for m, v in ss.items() if v}
    # Năm trước (7/2025): khách của 0104 mua — người KHÔNG bán tháng này vẫn có dòng.
    kx = _kx(conn)
    nv = {n["ma"]: n for n in BK.sale(conn, kx)}
    assert set(_dt_sale(conn, kx.so_sanh[0].tu, kx.so_sanh[0].den)) <= set(nv)


def test_dang_ky_bang_nguoi_phu_trach_cung_co_ky_so(conn, batch):
    _gieo(conn, batch)
    kx = _kx(conn, ky="2026")
    s = kx.so_sanh[0]
    nv = BK.tinh_bao_cao(conn, kx).nhan_vien
    ss = _dt_sale(conn, s.tu, s.den)
    assert {n["ma"]: n["dt_ss"] for n in nv if n["dt_ss"]} == {m: v for m, v in ss.items() if v}


def test_nganh_thang_ss_lech_12_BANG_view_cung_ky(conn, batch):
    """Bản đồ nhiệt ở dạng Tháng / Khoảng đi câu mới — năm trước phải ra ĐÚNG số của
    `mart.ban_theo_nganh_thang_so_sanh` (tháng trọn)."""
    _gieo(conn, batch)
    kx = _kx(conn, thang="2026-07")               # 7/2026 so 7/2025 (có dữ liệu)
    moi = {(n.thang, n.nganh): (n.doanh_thu, n.dt_cung_ky or 0, n.tang_truong)
           for n in BK.nganh_thang_ss(conn, kx) if n.co_cung_ky}
    cu = {(n.thang, n.nganh): (n.doanh_thu, n.dt_cung_ky or 0, n.tang_truong)
          for n in BC.doc_nganh_thang(conn, kx.company_fy) if n.co_cung_ky}
    assert moi == cu and moi


def test_ban_do_nhiet_theo_thang_truoc(conn, batch):
    _gieo(conn, batch)
    kx = _kx(conn, thang="2026-07", ss="truoc")
    o = {(n.thang, n.nganh): n for n in BK.nganh_thang_ss(conn, kx)}
    a7 = o[("2026-07", "Ngành A")]
    assert a7.co_cung_ky and a7.dt_cung_ky == 60_000, "Ngành A tháng 6/2026 (dời 1 tháng)"
    # Ngành B bán 7/2026 mà 6/2026 không bán: có so (trong dải dữ liệu), cùng kỳ = 0.
    b7 = o[("2026-07", "Ngành B")]
    assert b7.co_cung_ky and b7.dt_cung_ky == 0 and b7.tang_truong is None


def test_luy_ke_ky_so_bang_tong_dai_so(conn, batch):
    from kome.web.api import du_lieu_bao_cao
    _gieo(conn, batch)
    conn.execute("INSERT INTO app.ngan_sach_cong_ty (thang, doanh_thu, lai_gop) "
                 "VALUES ('2026-07-01', 10000000, 2000000)")
    conn.commit()
    d = du_lieu_bao_cao(conn, KX.doc_tham_so(ss="truoc"))   # 7/2026 tới 15/7, so tháng trước
    thang = [m["thang"] for m in d["td"]["luy_ke"]]
    ss = dict(zip(thang, d["_lk_ss"]))
    # Tháng 8/2025 ← 7/2025 (90.000) ... 6/2026 ← 5/2026 (0): luỹ kế 90.000;
    # tháng 7/2026 dở dang so ĐÚNG 1 → 15/6/2026 (60.000), không trọn tháng 6.
    assert ss["2025-08"] == 90_000 and ss["2026-06"] == 90_000
    assert ss["2026-07"] == 150_000
    assert d["lk"]["so_sanh"], "có đường luỹ kế kỳ so"
    # Năm trước: 8/2024 … nằm trước dữ liệu -> không vẽ (hai đường không cùng gốc).
    assert du_lieu_bao_cao(conn, KX.doc_tham_so())["_lk_ss"] is None


def test_bao_cao_ky_so_khong_qua_11_truy_van(conn, batch, monkeypatch):
    from kome.web.api import du_lieu_bao_cao
    _gieo(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    for ts in ({"ss": "truoc"}, {"thang": "2026-06", "ss": "truoc"}, {"ky": "2026", "ss": "truoc"},
               {"tu": "2026-06-01", "den": "2026-07-10", "ss": "truoc"}, {"thang": "2026-07", "ss_thang": "2026-06"}):
        dem["n"] = 0
        d = du_lieu_bao_cao(conn, KX.doc_tham_so(**ts))
        assert d["khoang"] is not None
        assert dem["n"] <= 11, f"{ts}: {dem['n']} truy vấn"


def test_duong_nho_ky_so_cung_thang():
    a = ve_duong_nho([10, 20, 30], so_sanh=[40, None, 20])
    b = ve_duong_nho([10, 20, 30])
    assert a["doan_ss"] == [] and b["doan_ss"] == [], "đoạn kỳ so một điểm không vẽ được đường"
    c = ve_duong_nho([10, 20, 30], so_sanh=[40, 30, 20])
    assert c["doan_ss"] and c["doan"] != b["doan"], "cùng thang: đỉnh kỳ so 40 kéo đường chính xuống"


def test_bieu_do_chinh_co_cot_ma_cung_thang(conn, batch):
    _gieo(conn, batch)
    bc = BK.tinh_bao_cao(conn, _kx(conn, ss="truoc"))
    bd = BC.ve_bieu_do(bc.thang)
    co_ck = [o for o in bc.thang if o.dt_cung_ky is not None]
    assert len(bd["cot_ck"]) == len(co_ck)
    # Cột ma và cột thật cùng thang: cao tỷ lệ với số.
    for c in bd["cot_ck"]:
        o = next(x for x in bd["cot"] if x["o"].thang == c["thang"])
        if o["o"].doanh_thu > 0 and c["dt"] > 0:
            assert abs(c["h"] / o["h"] - c["dt"] / o["o"].doanh_thu) < 0.05
    assert asdict(bc.thang[0]).keys() >= {"lg_cung_ky", "so_khach_cung_ky", "ty_suat_cung_ky"}
