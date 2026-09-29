"""068 + kome/doi_thu_giao.py — điều kiện giao hàng / điều kiện bán hiện hành (đặc tả giao diện mới §5.4)."""
from datetime import date
import pytest

from kome import doi_thu_giao as G
from kome.doi_thu import LoiNhap


@pytest.fixture
def kome_mac_dinh(conn):
    """app.giao_hang_kome sống qua TRUNCATE (GIU_LAI) — test nào sửa nó thì trả về mặc định 065 khi xong."""
    yield
    conn.rollback()
    conn.execute("""UPDATE app.giao_hang_kome SET bao_ship=false, phi_ship=500, phi_ship_theo='don', mien_ship_tu=20000,
                      mien_ship_kien=NULL, thung_moi_kien=NULL, phu_phi=NULL, phi_daibiki=330, daibiki_tu=20000,
                      daibiki_sau=300, ck_mien_daibiki=NULL, kien_toi_da_kg=NULL, ghep_kien=NULL, thue='chua',
                      cach_gui=NULL, da_xac_nhan=false""")
    conn.commit()


def _nap(conn, batch, ben, ngay=date(2026, 8, 31), **kw):
    b = batch(abs(hash((ben, ngay, str(kw)))) % 50_000 + 70_000, ngay)
    cot = ", ".join(kw)
    conn.execute(f"""INSERT INTO core.fact_giao_hang_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon{', ' + cot if kw else ''})
                     VALUES (%s, 'x', %s, %s{', %s' * len(kw)})""", (b, ben, ngay, *kw.values()))
    conn.commit()
    return b


def _hh(conn, ben):
    return conn.execute("SELECT * FROM mart.giao_hang_hien_hanh WHERE ma_doi_thu=%s", (ben,)).fetchone()


def _cot(conn, ben, cot):
    return conn.execute(f"SELECT {cot} FROM mart.giao_hang_hien_hanh WHERE ma_doi_thu=%s", (ben,)).fetchone()[0]


def test_kome_dung_dau_va_mang_nhan_suy_khi_chua_xac_nhan(conn):
    r = conn.execute("SELECT ma_doi_thu, phi_ship, suy FROM mart.giao_hang_hien_hanh").fetchall()
    assert r[0] == ("KOME", 500, True)


def test_lo_moi_nhat_cua_ben_thang_va_sua_sau_lo_thang_lo(conn, batch):
    _nap(conn, batch, "IMAI", date(2026, 7, 31), phi_ship=500)
    _nap(conn, batch, "IMAI", date(2026, 8, 31), phi_ship=605, phi_daibiki=440)
    assert _cot(conn, "IMAI", "phi_ship") == 605
    G.sua_giao_hang(conn, "IMAI", {"phi_daibiki": "400", "phu_phi": {"hokkaido": 800, "okinawa": "khong_nhan"}}, None)
    conn.commit()
    assert _cot(conn, "IMAI", "phi_daibiki") == 400
    assert _cot(conn, "IMAI", "phu_phi") == {"hokkaido": 800, "okinawa": "khong_nhan"}
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='giao_hang' AND doi_tuong='giao:IMAI'").fetchone()[0] == 1


def test_lo_nap_SAU_lan_sua_thi_lo_thang(conn, batch):
    _nap(conn, batch, "IMAI", date(2026, 8, 31), phi_ship=605)
    G.sua_giao_hang(conn, "IMAI", {"phi_ship": "600"}, None)
    conn.commit()
    conn.execute("UPDATE app.dinh_chinh_giao_hang SET luc = luc - interval '1 day'")   # sửa XONG trước lô sau
    conn.commit()
    _nap(conn, batch, "IMAI", date(2026, 9, 30), phi_ship=650)
    assert _cot(conn, "IMAI", "phi_ship") == 650


def test_xoa_ve_khong_ghi_la_NULL_khong_phai_0(conn, batch):
    _nap(conn, batch, "IMAI", phi_daibiki=440)
    G.sua_giao_hang(conn, "IMAI", {"phi_daibiki": ""}, None)
    conn.commit()
    assert _cot(conn, "IMAI", "phi_daibiki") is None


def test_ben_chua_co_lo_van_sua_duoc(conn):
    G.sua_giao_hang(conn, "JVB", {"bao_ship": True, "thue": "bao"}, None)
    conn.commit()
    assert (_cot(conn, "JVB", "bao_ship"), _cot(conn, "JVB", "thue")) == (True, "bao")


def test_kome_sua_la_update_va_danh_dau_xac_nhan(conn, kome_mac_dinh):
    G.sua_giao_hang(conn, "KOME", {"phu_phi": {"hokkaido": 1000}, "xac_nhan": True}, None)
    conn.commit()
    assert conn.execute("SELECT phu_phi, da_xac_nhan FROM app.giao_hang_kome").fetchone() == ({"hokkaido": 1000}, True)
    assert _cot(conn, "KOME", "suy") is False


@pytest.mark.parametrize("thay", [{"khong_co": "1"}, {"phi_ship": "-1"}, {"phi_ship_theo": "tuan"}, {"thue": "co"},
                                  {"phu_phi": {"mars": 1}}, {"phu_phi": {"hokkaido": -5}}, {"mien_ship_kien": "1.5"}])
def test_kiem_dau_vao(conn, thay):
    with pytest.raises(LoiNhap):
        G.sua_giao_hang(conn, "IMAI", thay, None)


def test_bang_chung_kome_dem_tu_phieu_ban(conn):
    r = conn.execute("SELECT * FROM mart.giao_hang_kome_bang_chung").fetchone()
    assert r is not None                                    # CSDL test không có phiếu phí → đếm 0, không lỗi


def test_dieu_kien_hien_hanh_bo_ghi_chu_doc_ap_sua_va_them_tay(conn, batch):
    b = batch(5)
    for i, (loai, nd) in enumerate((("ship", "Kiện 28kg"), ("ghi_chu_doc", "chép vào ghi_chu"), ("thue", "Bao thuế"))):
        conn.execute("""INSERT INTO core.fact_dieu_kien_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon, loai, noi_dung)
                        VALUES (%s, %s, 'YUMI', '2026-08-31', %s, %s)""", (b, f"d{i}", loai, nd))
    conn.commit()
    ids = dict(conn.execute("SELECT noi_dung, id FROM core.fact_dieu_kien_doi_thu").fetchall())
    G.sua_dieu_kien(conn, fact_id=ids["Kiện 28kg"], ma_doi_thu="YUMI", loai="ship", noi_dung="Kiện 30kg", bo=False, nguoi=None)
    G.sua_dieu_kien(conn, fact_id=ids["Bao thuế"], ma_doi_thu="YUMI", loai="thue", noi_dung="Bao thuế", bo=True, nguoi=None)
    G.sua_dieu_kien(conn, fact_id=None, ma_doi_thu="YUMI", loai="thanh_toan", noi_dung="Chuyển khoản trước", bo=False, nguoi=None)
    conn.commit()
    r = sorted(conn.execute("SELECT loai, noi_dung, them_tay FROM mart.dieu_kien_hien_hanh WHERE ma_doi_thu='YUMI'").fetchall())
    assert r == [("ship", "Kiện 30kg", False), ("thanh_toan", "Chuyển khoản trước", True)]
    assert conn.execute("SELECT count(*) FROM app.doi_thu_nhat_ky WHERE loai='dieu_kien'").fetchone()[0] == 3


def test_dieu_kien_chi_lay_lo_moi_nhat_cua_ben(conn, batch):
    for ngay, nd in ((date(2026, 7, 31), "cũ"), (date(2026, 8, 31), "mới")):
        b = batch(abs(hash(nd)) % 1000 + 3000, ngay)
        conn.execute("""INSERT INTO core.fact_dieu_kien_doi_thu (batch_id, ma_dong, ma_doi_thu, ngay_nguon, loai, noi_dung)
                        VALUES (%s, 'd', 'YUMI', %s, 'ship', %s)""", (b, ngay, nd))
    conn.commit()
    assert [r[0] for r in conn.execute("SELECT noi_dung FROM mart.dieu_kien_hien_hanh WHERE ma_doi_thu='YUMI'")] == ["mới"]


def test_bo_dong_them_tay(conn):
    G.sua_dieu_kien(conn, fact_id=None, ma_doi_thu="YUMI", loai="khac", noi_dung="Nghỉ Obon", bo=False, nguoi=None)
    G.sua_dieu_kien(conn, fact_id=None, ma_doi_thu="YUMI", loai="khac", noi_dung="Nghỉ Obon", bo=True, nguoi=None)
    conn.commit()
    assert conn.execute("SELECT count(*) FROM mart.dieu_kien_hien_hanh WHERE ma_doi_thu='YUMI'").fetchone()[0] == 0
