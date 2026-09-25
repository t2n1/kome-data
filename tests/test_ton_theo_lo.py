"""042 — tồn theo LÔ (mart.ton_theo_lo). Hai "kho" OBC là hai lô của MỘT kho vật
lý: 0001 = lô đang xuất, 1002 = lô chờ (hạn mới hơn), bán sau (CLAUDE.md bẫy #6)."""
from datetime import timedelta

from kome import san_pham as SP
from tests.test_khach_hang import _neo, HOM_NAY
from tests.test_mart_san_pham import _ban_qty, _san_pham, _ton


def _han(ngay_nua):
    d = HOM_NAY + timedelta(days=ngay_nua)
    return f"{d.year}年{d.month:02d}月{d.day:02d}日"


def _toc_do_10(conn, batch, ma):
    """Tốc độ theo tuổi = 10/ngày: 900 đơn vị, lần bán đầu cách mốc 89 ngày
    (tuổi 90 ngày)."""
    _ban_qty(conn, batch, "000000000001", HOM_NAY - timedelta(days=89), ma, 900)


def _lo(conn, ma):
    return {r[0]: r[1:] for r in conn.execute(
        """SELECT warehouse_code, vai_tro_lo, thu_tu_lo, bat_dau_ban_sau, ban_het_sau,
                  khong_kip_ban, sl_khong_kip, sap_chuyen_lo
             FROM mart.ton_theo_lo WHERE product_code = %s""", (ma,))}


def test_lo_dang_xuat_ban_TRUOC_ke_ca_khi_lo_cho_co_han_som_hon(conn, batch):
    """Vai trò lô theo MÃ KHO (hàng chỉ đi ra từ 0001), không suy từ hạn."""
    _san_pham(conn, batch, "L1")
    _toc_do_10(conn, batch, "L1")
    _ton(conn, batch, "L1", kho="0001", sl=100, han=_han(300))
    _ton(conn, batch, "L1", kho="1002", sl=50, han=_han(200))
    _neo(conn, batch)
    lo = _lo(conn, "L1")
    assert lo["0001"][:2] == ("dang_xuat", 1)
    assert lo["1002"][:2] == ("cho", 2)
    assert float(lo["0001"][2]) == 0 and float(lo["0001"][3]) == 10
    assert float(lo["1002"][2]) == 10 and float(lo["1002"][3]) == 15


def test_ban_het_cua_lo_CUOI_bang_du_ban_ngay_cua_ca_ma(conn, batch):
    """Một khái niệm một công thức: cộng dồn hai lô ra đúng du_ban_ngay của
    mart.san_pham_360 (cùng tốc độ toc_do_ngay_theo_tuoi)."""
    _san_pham(conn, batch, "L2")
    _toc_do_10(conn, batch, "L2")
    _ton(conn, batch, "L2", kho="0001", sl=70)
    _ton(conn, batch, "L2", kho="1002", sl=45)
    _neo(conn, batch)
    cuoi = conn.execute("""SELECT max(ban_het_sau) FROM mart.ton_theo_lo
                            WHERE product_code = 'L2'""").fetchone()[0]
    du = conn.execute("""SELECT du_ban_ngay FROM mart.san_pham_360
                          WHERE product_code = 'L2'""").fetchone()[0]
    assert float(cuoi) == float(du) == 11.5


def test_lo_cho_KHONG_KIP_BAN_truoc_han_vi_phai_doi_lo_dang_xuat(conn, batch):
    """0001 còn 100 (10 ngày), 1002 có 100 hạn còn 15 ngày: lô chờ chỉ bắt đầu
    bán từ ngày 10, tới hạn bán được 50 ⇒ dự kiến còn 50 lúc hết hạn. Riêng hạn
    của lô chờ (15 ngày) chưa đủ để thấy điều đó."""
    _san_pham(conn, batch, "L3")
    _toc_do_10(conn, batch, "L3")
    _ton(conn, batch, "L3", kho="0001", sl=100, han=_han(300))
    _ton(conn, batch, "L3", kho="1002", sl=100, han=_han(15))
    _neo(conn, batch)
    lo = _lo(conn, "L3")
    assert lo["0001"][4] is False
    assert lo["1002"][4] is True and float(lo["1002"][5]) == 50
    k = SP.kho_hang(conn)
    assert [(d["ma"], d["kho"]) for d in k.khong_kip] == [("L3", "1002")]
    assert k.khong_kip[0]["gia_tri_khong_kip"] == 50_000


def test_sap_chuyen_lo_la_cua_MA_khong_theo_bo_loc_kho(conn, batch):
    """0001 còn 50 (5 ngày < 14), 1002 còn hàng ⇒ sắp chuyển lô. Mã chỉ còn lô
    chờ (0001 không có dòng) ⇒ cần chuyển ngay. Mã đủ lâu (0001 còn 300) ⇒ không."""
    for ma in ("C1", "C2", "C3"):
        _san_pham(conn, batch, ma)
        _toc_do_10(conn, batch, ma)
    _ton(conn, batch, "C1", kho="0001", sl=50)
    _ton(conn, batch, "C1", kho="1002", sl=200)
    _ton(conn, batch, "C2", kho="1002", sl=200)
    _ton(conn, batch, "C3", kho="0001", sl=300)
    _ton(conn, batch, "C3", kho="1002", sl=200)
    _neo(conn, batch)
    k = SP.kho_hang(conn)
    assert k.kho_dang_xuat == "0001"
    assert [d["ma"] for d in k.chuyen_lo] == ["C2", "C1"]   # đã hết trước
    # Lọc lô chờ: dòng 0001 bị lọc khỏi bảng, nhưng khối chuyển lô vẫn đủ.
    assert [d["ma"] for d in SP.kho_hang(conn, kho="1002").chuyen_lo] == ["C2", "C1"]
