"""Tầng SQL của Sản phẩm 360 (migration 051–053): các hàm mart.sp_*(mã).

Mỗi test khoá một bất biến đã ghi trong CLAUDE.md, không chỉ "chạy được"."""
from datetime import timedelta

import pytest

import pandas as pd

from tests.test_khach_hang import _ho_so_khach, _mua, _neo, HOM_NAY
from tests.test_mart_san_pham import _ban_qty, _san_pham


def _dong(conn, batch, ma_khach, ngay, ma_hang, qty=1, tien=110_000, tax=10_000, gp=30_000,
          phieu=None, dong=1, pack="02", sale="0104"):
    """Một dòng bán đầy đủ tuỳ biến (phiếu, dòng, quy cách, người phụ trách)."""
    from kome.loaders import sales
    b = batch(abs(hash((ma_khach, ngay, ma_hang, phieu, dong, qty))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": phieu or f"D{ma_khach[-4:]}{ngay:%m%d}{ma_hang}", "line_seq": dong,
        "sales_date": ngay, "customer_code": ma_khach, "product_code": ma_hang,
        "salesperson_code": sale, "pack_code": pack, "case_qty": qty, "qty": qty,
        "unit_price": 0, "unit_cost": 0, "amount": tien, "tax_amount": tax,
        "cost": tien - tax - gp, "gross_profit": gp, "paid_amount": 0, "batch_id": b,
    }]), ngay, b)
    conn.commit()


# ------------------------------------------------------------------ 051

def test_tap_trung_gop_theo_KHACH_khong_theo_nguoi_phu_trach(conn, batch):
    """Bất biến tap_trung_khach: một khách đổi người phụ trách giữa kỳ vẫn MỘT dòng."""
    _san_pham(conn, batch, "T1")
    _ho_so_khach(conn, batch, "KT01", "Quán A")
    _dong(conn, batch, "KT01", HOM_NAY - timedelta(days=40), "T1", sale="0102")
    _dong(conn, batch, "KT01", HOM_NAY - timedelta(days=5), "T1", sale="0104")
    _ho_so_khach(conn, batch, "KT02", "Quán B")
    _dong(conn, batch, "KT02", HOM_NAY - timedelta(days=5), "T1", tien=55_000, tax=5_000)
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, doanh_thu, luy_ke FROM mart.sp_tap_trung_khach('T1')").fetchall()
    assert [x[0] for x in r] == ["KT01", "KT02"]
    assert r[0][1] == 200_000
    assert abs(float(r[1][2]) - 1.0) < 1e-9


def test_theo_tinh_du_47_o_ke_ca_tinh_khong_ai_mua(conn, batch):
    """LEFT JOIN từ dim_prefecture: tỉnh không có khách mua mã này vẫn là một ô 0."""
    _san_pham(conn, batch, "T2")
    _ho_so_khach(conn, batch, "KT03", "Quán Osaka", prefecture="大阪府")
    _dong(conn, batch, "KT03", HOM_NAY - timedelta(days=3), "T2")
    _neo(conn, batch)
    r = conn.execute("SELECT ten, doanh_thu, so_khach FROM mart.sp_theo_tinh('T2')").fetchall()
    assert len(r) == 47
    d = {x[0]: (x[1], x[2]) for x in r}
    assert d["大阪府"] == (100_000, 1)
    assert d["和歌山県"] == (0, 0)


def test_theo_nguoi_giu_ma_ngoai_danh_sach_phu_trach(conn, batch):
    """Nếp FULL JOIN ngân sách: mã phụ trách '0000' không có trong dim_salesperson vẫn có dòng."""
    _san_pham(conn, batch, "T3")
    _ho_so_khach(conn, batch, "KT04", "Quán C")
    _dong(conn, batch, "KT04", HOM_NAY - timedelta(days=3), "T3", sale="0000")
    _neo(conn, batch)
    r = conn.execute("SELECT salesperson_code, ten, doanh_thu FROM mart.sp_theo_nguoi('T3')").fetchall()
    assert r == [("0000", None, 100_000)]


def test_khach_moi_thang_dem_lan_DAU_mua_ma_nay(conn, batch):
    _san_pham(conn, batch, "T4")
    _ho_so_khach(conn, batch, "KT05", "Quán cũ")
    _dong(conn, batch, "KT05", HOM_NAY - timedelta(days=400), "T4")   # lần đầu từ năm trước
    _dong(conn, batch, "KT05", HOM_NAY - timedelta(days=2), "T4")
    _ho_so_khach(conn, batch, "KT06", "Quán mới")
    _dong(conn, batch, "KT06", HOM_NAY - timedelta(days=1), "T4")
    _neo(conn, batch)
    r = conn.execute("SELECT thang, khach_moi, khach_quay_lai FROM mart.sp_khach_moi_thang('T4')").fetchall()
    assert len(r) == 12 and r[-1][0] == f"{HOM_NAY:%Y-%m}"
    assert (r[-1][1], r[-1][2]) == (1, 1)


def test_ma_noi_bo_khong_vao_ham_nao_cua_051(conn, batch):
    """044: 0090…/0099… là nhân viên mua — ban_den_moc đã lọc, hàm mới không được lọt."""
    _san_pham(conn, batch, "T5")
    _dong(conn, batch, "009000000001", HOM_NAY - timedelta(days=3), "T5")
    _neo(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.sp_tap_trung_khach('T5')").fetchone()[0] == 0
    assert conn.execute("SELECT coalesce(sum(so_khach),0) FROM mart.sp_theo_tinh('T5')").fetchone()[0] == 0


# ------------------------------------------------------------------ 052

def test_theo_tuan_du_26_tuan_tuan_trong_bang_0(conn, batch):
    _san_pham(conn, batch, "T6")
    _ho_so_khach(conn, batch, "KT07", "Quán D")
    _dong(conn, batch, "KT07", HOM_NAY, "T6", qty=3)
    _neo(conn, batch)
    r = conn.execute("SELECT tuan, so_luong FROM mart.sp_theo_tuan('T6')").fetchall()
    assert len(r) == 26
    assert all(t.isoweekday() == 1 for t, _ in r)
    assert float(r[-1][1]) == 3 and float(r[0][1]) == 0


def test_co_don_dem_dong_TRA_LAI_rieng_khong_loc(conn, batch):
    """赤伝 không bị lọc: dòng âm vào nhóm 'tra_lai'."""
    _san_pham(conn, batch, "T7")
    _ho_so_khach(conn, batch, "KT08", "Quán E")
    _dong(conn, batch, "KT08", HOM_NAY - timedelta(days=9), "T7", qty=4)
    _dong(conn, batch, "KT08", HOM_NAY - timedelta(days=2), "T7", qty=-1, tien=-27_500, tax=-2_500, gp=-7_000)
    _neo(conn, batch)
    r = {(x[0], x[1]): x[3] for x in conn.execute("SELECT * FROM mart.sp_co_don('T7')").fetchall()}
    assert r[("02", "3–5")] == 1 and r[("02", "tra_lai")] == 1


def test_don_gia_la_TY_SO_CAC_TONG(conn, batch):
    """[CRITICAL] 021: trung bình tỷ số bị dòng mẫu số tí hon thổi phồng.
    Hai dòng: 10 đv / ¥100.000 thuần và 1 đv / ¥1.000 thuần.
    Tỷ số các tổng = 101.000 / 11 ≈ 9.181,8; trung bình đơn giá = (10.000 + 1.000)/2 = 5.500."""
    _san_pham(conn, batch, "T8")
    _ho_so_khach(conn, batch, "KT09", "Quán F")
    _dong(conn, batch, "KT09", HOM_NAY - timedelta(days=3), "T8", qty=10, tien=110_000, tax=10_000)
    _dong(conn, batch, "KT09", HOM_NAY - timedelta(days=2), "T8", qty=1, tien=1_100, tax=100)
    _neo(conn, batch)
    r = conn.execute("SELECT don_gia FROM mart.sp_don_gia_thang('T8') WHERE thang = %s AND pack_code = '02'",
                     (f"{HOM_NAY:%Y-%m}",)).fetchone()
    assert abs(float(r[0]) - 101_000 / 11) < 0.01


def test_don_gia_NULL_khi_tong_so_luong_khong_duong(conn, batch):
    _san_pham(conn, batch, "T9")
    _ho_so_khach(conn, batch, "KT10", "Quán G")
    _dong(conn, batch, "KT10", HOM_NAY - timedelta(days=2), "T9", qty=-2, tien=-22_000, tax=-2_000, gp=-5_000)
    _neo(conn, batch)
    r = conn.execute("SELECT don_gia FROM mart.sp_don_gia_thang('T9')").fetchall()
    assert r and r[0][0] is None


def test_khach_gia_chi_khach_DT_duong_va_it_nhat_2_lan(conn, batch):
    _san_pham(conn, batch, "T10")
    _ho_so_khach(conn, batch, "KT11", "Quán hai lần")
    _dong(conn, batch, "KT11", HOM_NAY - timedelta(days=20), "T10", qty=2)
    _dong(conn, batch, "KT11", HOM_NAY - timedelta(days=2), "T10", qty=2)
    _ho_so_khach(conn, batch, "KT12", "Quán một lần")
    _dong(conn, batch, "KT12", HOM_NAY - timedelta(days=2), "T10", qty=2)
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, so_lan, bien FROM mart.sp_khach_gia('T10')").fetchall()
    assert [x[0] for x in r] == ["KT11"]
    assert r[0][1] == 2 and abs(float(r[0][2]) - 0.3) < 1e-9


# ------------------------------------------------------------------ 053

def _sp_du(conn, batch, ma, ten="Hàng", nganh="米_VNM", kind="0", rank=None):
    """dim_product có ngành / loại / hạng — cần cho mua kèm và khách nên chào."""
    b = batch(abs(hash(("spd", ma))) % 60_000 + 1)
    conn.execute(
        """INSERT INTO core.dim_product (product_code, product_name, kind_code, kind_name,
                                         food_category_name, rank_code, batch_id)
           VALUES (%s, %s, %s, 'x', %s, %s, %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma, ten, kind, nganh, rank, b))
    conn.commit()


def test_mua_kem_bo_phi_POSM_va_hang_ngung_ban_het_ton(conn, batch):
    _sp_du(conn, batch, "M1")
    _sp_du(conn, batch, "M2", ten="Bánh")
    _sp_du(conn, batch, "PHI", ten="配送料", kind="1")
    _sp_du(conn, batch, "MKT1", ten="Poster", nganh="雑貨_VNM")
    _sp_du(conn, batch, "OLD", ten="※終売※ cũ", rank="0999")
    _ho_so_khach(conn, batch, "KM01", "Quán H")
    ngay = HOM_NAY - timedelta(days=3)
    for i, ma in enumerate(["M1", "M2", "PHI", "MKT1", "OLD"], start=1):
        _dong(conn, batch, "KM01", ngay, ma, phieu="P-KEM-1", dong=i)
    _dong(conn, batch, "KM01", ngay - timedelta(days=7), "M1", phieu="P-KEM-2", dong=1)
    _neo(conn, batch)
    r = conn.execute("SELECT product_code, so_phieu, ty_le, tong_phieu FROM mart.sp_mua_kem('M1')").fetchall()
    assert [x[0] for x in r] == ["M2"]
    assert r[0][1] == 1 and r[0][3] == 2 and abs(float(r[0][2]) - 0.5) < 1e-9


def test_khach_nen_chao_cung_nganh_chua_mua_khong_co_khach_dong_cua(conn, batch):
    _sp_du(conn, batch, "C1", nganh="米_VNM")
    _sp_du(conn, batch, "C2", nganh="米_VNM")
    _sp_du(conn, batch, "X9", nganh="麺_VNM")
    # KC01: mua đều C2 (cùng ngành), chưa mua C1 -> NÊN CHÀO
    _ho_so_khach(conn, batch, "KC01", "Quán mua gạo")
    for i in range(3):
        _dong(conn, batch, "KC01", HOM_NAY - timedelta(days=i * 7), "C2")
    # KC02: đã mua C1 -> không chào
    _ho_so_khach(conn, batch, "KC02", "Quán đã mua")
    for i in range(3):
        _dong(conn, batch, "KC02", HOM_NAY - timedelta(days=i * 7), "C2")
    _dong(conn, batch, "KC02", HOM_NAY - timedelta(days=1), "C1")
    # KC03: ※廃業※ -> nhãn 'khong_goi', không chào
    _ho_so_khach(conn, batch, "KC03", "※廃業※ Quán đóng cửa")
    for i in range(3):
        _dong(conn, batch, "KC03", HOM_NAY - timedelta(days=i * 7), "C2")
    # KC04: chỉ mua ngành khác -> không chào
    _ho_so_khach(conn, batch, "KC04", "Quán mì")
    for i in range(3):
        _dong(conn, batch, "KC04", HOM_NAY - timedelta(days=i * 7), "X9")
    _neo(conn, batch)
    r = conn.execute("SELECT customer_code, so_ma_nganh FROM mart.sp_khach_nen_chao('C1')").fetchall()
    assert r == [("KC01", 1)]


def test_khach_nen_chao_RONG_voi_ma_ngung_kinh_doanh(conn, batch):
    """050: không chào hàng đã ngừng kinh doanh — kể cả còn tồn."""
    _sp_du(conn, batch, "N1", ten="※終売※ gạo", nganh="米_VNM", rank="0999")
    _sp_du(conn, batch, "N2", nganh="米_VNM")
    _ho_so_khach(conn, batch, "KN01", "Quán I")
    for i in range(3):
        _dong(conn, batch, "KN01", HOM_NAY - timedelta(days=i * 7), "N2")
    _neo(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.sp_khach_nen_chao('N1')").fetchone()[0] == 0


# ------------------------------------------------------------------ cả 051–053

# (hàm, hậu tố mã đích, biểu thức "có gì không") — đủ MƯỜI hàm mart.sp_*. Khách nên chào nhắm
# một mã CÙNG NGÀNH mà khách chưa mua (hậu tố 3), chín hàm còn lại nhắm mã khách đã mua (1).
HAM_SP = [
    ("sp_tap_trung_khach", "1", "count(*)"),
    ("sp_theo_tinh", "1", "coalesce(sum(so_khach), 0)"),
    ("sp_theo_nguoi", "1", "count(*)"),
    ("sp_khach_moi_thang", "1", "coalesce(sum(khach_moi + khach_quay_lai), 0)"),
    ("sp_theo_tuan", "1", "coalesce(sum(abs(so_luong)), 0)"),
    ("sp_co_don", "1", "count(*)"),
    ("sp_don_gia_thang", "1", "count(*)"),
    ("sp_khach_gia", "1", "count(*)"),
    ("sp_mua_kem", "1", "count(*)"),
    ("sp_khach_nen_chao", "3", "count(*)"),
]


def _gieo_hai_khach(conn, batch):
    """Hai khách mua GIỐNG HỆT nhau trên hai bộ mã khác ngành: khách thường (KNB01, mã J*,
    ngành 麺) và NHÂN VIÊN (009000000001, mã I*, ngành 米). Mỗi tuần một phiếu có cả mã 1 và 2."""
    import pandas as pd
    from kome.loaders import sales
    for tien_to, nganh in (("I", "米_VNM"), ("J", "麺_VNM")):
        for h in "123":
            _sp_du(conn, batch, f"{tien_to}{h}", nganh=nganh)
    dong = []
    for ma_khach, tien_to in (("009000000001", "I"), ("KNB01", "J")):
        _ho_so_khach(conn, batch, ma_khach, f"Khách {ma_khach}")
        for i in range(6):
            ngay = HOM_NAY - timedelta(days=i * 7)
            for j in (1, 2):
                dong.append({"slip_no": f"NB{tien_to}{i}", "line_seq": j, "sales_date": ngay,
                             "customer_code": ma_khach, "product_code": f"{tien_to}{j}",
                             "salesperson_code": "0104", "pack_code": "02", "case_qty": 2, "qty": 2,
                             "unit_price": 0, "unit_cost": 0, "amount": 110_000, "tax_amount": 10_000,
                             "cost": 70_000, "gross_profit": 30_000, "paid_amount": 0})
    b = batch(88_123)
    df = pd.DataFrame(dong)
    df["batch_id"] = b
    sales.load(conn, df, HOM_NAY, b)
    conn.commit()
    _neo(conn, batch)


@pytest.mark.parametrize("ham, hau_to, bieu_thuc", HAM_SP, ids=[h[0] for h in HAM_SP])
def test_ma_noi_bo_khong_vao_ham_sp_NAO(conn, batch, ham, hau_to, bieu_thuc):
    """044: 0090…/0099… là nhân viên mua — ra khỏi MỌI khối của Sản phẩm 360. Đối chứng dương:
    khách thường mua y hệt thì hàm đó CÓ ra dòng (không thì test pass rỗng)."""
    _gieo_hai_khach(conn, batch)
    def _do(ma):
        return conn.execute(f"SELECT {bieu_thuc} FROM mart.{ham}(%s)", (ma,)).fetchone()[0]
    assert _do(f"J{hau_to}") > 0, f"{ham}: đối chứng khách thường phải có dữ liệu"
    assert _do(f"I{hau_to}") == 0, f"{ham}: nhân viên mua lọt vào"


D_LUI = HOM_NAY - timedelta(days=70)


def _gieo_lich_su(conn, batch):
    """Ba khách mua đều hai mã cùng ngành (thỉnh thoảng cùng phiếu) từ ~13 tháng trước tới
    HOM_NAY — MỘT lô nạp. Có dòng đúng ngày D_LUI."""
    import pandas as pd
    from kome.loaders import sales
    for h in "123":
        _sp_du(conn, batch, f"L{h}", nganh="米_VNM")
    dong = []
    for k, (ma, nhip) in enumerate((("KL01", 7), ("KL02", 10), ("KL03", 14))):
        _ho_so_khach(conn, batch, ma, f"Quán {ma}", prefecture=("東京都", "大阪府", "北海道")[k])
        i, ngay = 0, HOM_NAY   # KL01 nhịp 7 từ HOM_NAY: rơi đúng D_LUI (70 = 10 × 7)
        while ngay > HOM_NAY - timedelta(days=400):
            if not (ma == "KL02" and ngay > HOM_NAY - timedelta(days=30)):
                for j, sp in enumerate(("L1", "L2") if i % 2 == 0 else ("L1",), start=1):
                    tien = 11_000 * (1 + i % 3) * (-1 if i % 11 == 5 else 1)
                    dong.append({"slip_no": f"H{ma}{ngay:%Y%m%d}", "line_seq": j, "sales_date": ngay,
                                 "customer_code": ma, "product_code": sp, "salesperson_code": "0104",
                                 "pack_code": ("02", "00")[i % 2], "case_qty": 1 + i % 4,
                                 "qty": (1 + i % 4) * (-1 if tien < 0 else 1),
                                 "unit_price": 0, "unit_cost": 0, "amount": tien,
                                 "tax_amount": tien // 11, "cost": tien - tien // 11 - 3_000,
                                 "gross_profit": 3_000, "paid_amount": 0})
            ngay -= timedelta(days=nhip)
            i += 1
    assert any(x["sales_date"] == D_LUI for x in dong), "gieo hỏng: phải có dòng đúng D_LUI"
    b = batch(88_321)
    df = pd.DataFrame(dong)
    df["batch_id"] = b
    sales.load(conn, df, HOM_NAY, b)
    conn.commit()


def _chup_sp(conn):
    return {h: conn.execute(f"SELECT * FROM mart.{h}(%s) ORDER BY 1, 2", (f"L{t}",)).fetchall()
            for h, t, _ in HAM_SP}


def test_moc_D_cua_ham_sp_BANG_kho_chi_co_du_lieu_toi_D(conn, batch):
    """040 — đẳng thức vàng cho mười hàm mart.sp_*: đặt mốc D trong MỘT giao dịch ≡ như thể kho
    chỉ có dữ liệu bán tới D (cùng mẫu tests/test_moc_lui.py)."""
    _gieo_lich_su(conn, batch)
    conn.execute("SELECT set_config('kome.moc', %s, true)", (D_LUI.isoformat(),))
    co_moc = _chup_sp(conn)
    conn.rollback()
    assert conn.execute("SELECT hom_nay FROM mart.moc_thoi_gian").fetchone()[0] > D_LUI
    khong_moc = _chup_sp(conn)
    conn.execute("DELETE FROM core.fact_sales_line WHERE sales_date > %s", (D_LUI,))
    conn.commit()
    that = _chup_sp(conn)
    for h, _, _ in HAM_SP:
        assert co_moc[h] == that[h], f"{h} lệch khi đặt mốc {D_LUI}"
    # Không pass rỗng: bốn hàm chính có dữ liệu, và dữ liệu sau D thật sự đổi kết quả.
    for h in ("sp_tap_trung_khach", "sp_theo_tuan", "sp_don_gia_thang", "sp_mua_kem"):
        assert co_moc[h], f"{h}: phải có dữ liệu để so"
        assert co_moc[h] != khong_moc[h], f"{h}: dữ liệu sau mốc phải làm kết quả khác"


@pytest.mark.parametrize("nganh, kind", [("", "0"), ("雑貨_VNM", "0"), ("米_VNM", "1")],
                         ids=["chua_phan_loai", "hang_tang", "phi"])
def test_khach_nen_chao_RONG_voi_ma_khong_phai_hang_hoac_chua_phan_loai(conn, batch, nganh, kind):
    """Vị từ đọc mart.khong_phai_hang + nullif(ngành) — không so chuỗi nhãn ngành. Đối chứng:
    cùng khách, mã đích thường cùng ngành thì CÓ ra khách."""
    _sp_du(conn, batch, "R1", nganh=nganh, kind=kind)
    _sp_du(conn, batch, "R2", nganh=nganh, kind=kind)
    _sp_du(conn, batch, "R3", nganh="米_VNM")
    _sp_du(conn, batch, "R4", nganh="米_VNM")
    _ho_so_khach(conn, batch, "KR01", "Quán J")
    for i in range(3):
        _dong(conn, batch, "KR01", HOM_NAY - timedelta(days=i * 7), "R2")
        _dong(conn, batch, "KR01", HOM_NAY - timedelta(days=i * 7), "R4")
    _neo(conn, batch)
    assert conn.execute("SELECT count(*) FROM mart.sp_khach_nen_chao('R3')").fetchone()[0] == 1
    assert conn.execute("SELECT count(*) FROM mart.sp_khach_nen_chao('R1')").fetchone()[0] == 0


# ------------------------------------------------------------------ 054

def _gieo_nhieu_cap(conn, batch):
    """Ba khách × ba mã, nhịp khác nhau, có một khách ※廃業※ và một cặp đã ngừng — đủ để mọi nhánh
    của trang_thai_cap ('mua' / 'ngung' / 'khong_goi') và nhip_ngay NULL đều có mặt."""
    for ma in ("Z1", "Z2", "Z3"):
        _sp_du(conn, batch, ma)
    _ho_so_khach(conn, batch, "KZ01", "Quán đều")
    _ho_so_khach(conn, batch, "KZ02", "Quán đã bỏ Z2")
    _ho_so_khach(conn, batch, "KZ03", "※廃業※ Quán đóng")
    for i in range(4):
        _dong(conn, batch, "KZ01", HOM_NAY - timedelta(days=i * 7), "Z1")
        _dong(conn, batch, "KZ01", HOM_NAY - timedelta(days=i * 10), "Z2")
        _dong(conn, batch, "KZ02", HOM_NAY - timedelta(days=90 + i * 7), "Z2")
        _dong(conn, batch, "KZ03", HOM_NAY - timedelta(days=i * 7), "Z3")
    _dong(conn, batch, "KZ02", HOM_NAY - timedelta(days=3), "Z3")
    _neo(conn, batch)


def test_khach_mat_hang_cua_BANG_view_loc_theo_ma(conn, batch):
    """[CRITICAL] 054: view chỉ còn là `…_cua(NULL)`, và hàm với danh sách mã phải trả ĐÚNG các dòng
    của view cho những mã đó — lọc theo mã không được đổi cửa sổ LAG / nhịp của một cặp."""
    _gieo_nhieu_cap(conn, batch)
    view = conn.execute("""SELECT * FROM mart.khach_mat_hang
                            WHERE product_code IN ('Z1', 'Z2') ORDER BY 1, 2""").fetchall()
    ham = conn.execute("""SELECT * FROM mart.khach_mat_hang_cua(ARRAY['Z1', 'Z2']) ORDER BY 1, 2""").fetchall()
    assert view and ham == view
    nhan = {(r[0], r[1]): r[-1] for r in conn.execute("SELECT * FROM mart.khach_mat_hang_cua(NULL)")}
    assert nhan[("KZ01", "Z1")] == "mua" and nhan[("KZ02", "Z2")] == "ngung" \
        and nhan[("KZ03", "Z3")] == "khong_goi", "gieo hỏng: phải có đủ ba nhãn"
    assert conn.execute("SELECT count(*) FROM mart.khach_mat_hang").fetchone()[0] == \
        conn.execute("SELECT count(*) FROM mart.khach_mat_hang_cua(NULL)").fetchone()[0]


def test_nhip_va_khoang_cach_cua_BANG_view_loc_theo_ma(conn, batch):
    _gieo_nhieu_cap(conn, batch)
    for v in ("nhip_mat_hang", "khoang_cach_mat_hang"):
        view = conn.execute(f"SELECT * FROM mart.{v} WHERE product_code = 'Z2' ORDER BY 1, 2, 3").fetchall()
        ham = conn.execute(f"SELECT * FROM mart.{v}_cua(ARRAY['Z2']) ORDER BY 1, 2, 3").fetchall()
        assert view and ham == view, v


def test_khach_nen_chao_054_GIONG_dinh_nghia_053(conn, batch):
    """Cùng dữ liệu, kết quả của sp_khach_nen_chao (054, một lượt hàm) = định nghĩa 053 viết lại
    trực tiếp trên view (LATERAL từng mã). Chỉ đổi CÁCH đọc, không đổi định nghĩa."""
    _gieo_nhieu_cap(conn, batch)
    _sp_du(conn, batch, "Z4")          # mã đích: cùng ngành, chưa ai mua
    moi = conn.execute("SELECT customer_code, so_ma_nganh, lan_cuoi FROM mart.sp_khach_nen_chao('Z4')").fetchall()
    cu = conn.execute("""
        SELECT h.customer_code, count(*), max(h.lan_cuoi)
          FROM core.dim_product d
          CROSS JOIN LATERAL (SELECT x.customer_code, x.lan_cuoi FROM mart.khach_mat_hang x
                               WHERE x.product_code = d.product_code AND x.trang_thai_cap = 'mua') h
         WHERE d.product_code IN ('Z1', 'Z2', 'Z3')
         GROUP BY h.customer_code""").fetchall()
    assert moi and sorted(moi) == sorted(cu)
    assert "KZ03" not in {r[0] for r in moi}, "khách ※廃業※ không bao giờ vào danh sách chào"
