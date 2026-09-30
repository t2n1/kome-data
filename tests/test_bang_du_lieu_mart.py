"""Bảng dữ liệu sửa (072): luật hiệu lực + view hiệu lực. Đặc tả 2026-09-30-bang-du-lieu-sua-design.md."""
from datetime import date

import psycopg
import pytest

D1, D2 = date(2026, 9, 1), date(2026, 9, 8)


def _sua(conn, bang, khoa, cot, gia_tri, obc, bo=False):
    conn.execute("""INSERT INTO app.sua_du_lieu (bang, khoa, cot, gia_tri, gia_tri_obc, bo)
                    VALUES (%s, %s, %s, %s, %s, %s)""", (bang, khoa, cot, gia_tri, obc, bo))
    conn.commit()


def _khach(conn, batch, ma, ten, ngay=D1, tinh="大阪府", hang=("0003", "C")):
    import pandas as pd
    from kome.loaders import customer
    b = batch(1, ngay)
    df = pd.DataFrame([{"customer_code": ma, "customer_name": ten, "branch_name": "", "rank_code": hang[0],
                        "rank_name": hang[1], "salesperson_code": "0002", "salesperson_name": "A",
                        "closing_day_code": "", "closing_day_name": "", "postcode": "", "prefecture": tinh,
                        "city": "", "address": "", "building": "", "phone": "", "transfer_account": ""}])
    for c in df.columns:  # đúng dạng kome.reader.read() trả ra: cột object, ô trống là None
        df[c] = df[c].astype(object).where(df[c].notna(), None)
    customer.load(conn, df, ngay, b)


def _hang(conn, batch, ma, ten, nganh=("01", "調味料_VNM")):
    b = batch(1)
    conn.execute("""INSERT INTO core.dim_product (product_code, product_name, food_category_code, food_category_name,
                      kind_code, kind_name, case_qty, batch_id) VALUES (%s, %s, %s, %s, '0', '有形', 20, %s)
                    ON CONFLICT (product_code) DO UPDATE SET product_name = EXCLUDED.product_name,
                      food_category_code = EXCLUDED.food_category_code, food_category_name = EXCLUDED.food_category_name""",
                 (ma, ten, nganh[0], nganh[1], b))
    conn.commit()


def test_ap_sua_obc_giu_nguyen_thi_sua_thang_obc_doi_thi_obc_thang(conn):
    q = "SELECT mart.ap_sua(%s, %s::jsonb, 'x'), mart.lech_obc(%s, %s::jsonb, 'x')"
    j = '{"x": ["moi", "cu"]}'
    assert conn.execute(q, ("cu", j, "cu", j)).fetchone() == ("moi", True)
    assert conn.execute(q, ("khac", j, "khac", j)).fetchone() == ("khac", False)
    assert conn.execute(q, ("cu", None, "cu", None)).fetchone() == ("cu", False)
    assert conn.execute(q, (None, '{"x": ["moi", null]}', None, '{"x": ["moi", null]}')).fetchone() == ("moi", True)
    assert conn.execute(q, ("cu", '{"x": [null, "cu"]}', "cu", '{"x": [null, "cu"]}')).fetchone() == (None, True)


def test_dim_customer_ap_ban_sua_va_nap_obc_doi_dung_cot_thi_obc_thang(conn, batch):
    _khach(conn, batch, "K1", "Quán A")
    _sua(conn, "khach", "K1", "customer_name", "Quán A (Kyoto)", "Quán A")
    ten = lambda: conn.execute("SELECT customer_name FROM mart.dim_customer WHERE customer_code='K1' AND is_current").fetchone()[0]
    assert ten() == "Quán A (Kyoto)"
    _khach(conn, batch, "K1", "Quán A", ngay=D2, tinh="京都府")      # OBC đổi CỘT KHÁC → bản sửa vẫn thắng
    assert ten() == "Quán A (Kyoto)"
    _khach(conn, batch, "K1", "Quán B", ngay=date(2026, 9, 9))        # OBC đổi đúng cột → OBC thắng
    assert ten() == "Quán B"


def test_bo_ve_obc_va_dong_moi_nhat_thang(conn, batch):
    _khach(conn, batch, "K1", "Quán A")
    _sua(conn, "khach", "K1", "phone", "06-1", "")
    _sua(conn, "khach", "K1", "phone", None, "", bo=True)
    assert conn.execute("SELECT phone FROM mart.dim_customer WHERE customer_code='K1' AND is_current").fetchone()[0] == ""


def test_cot_cap_ma_ten_lay_ten_theo_ma_hieu_luc(conn, batch):
    _khach(conn, batch, "K1", "Quán A", hang=("0003", "C"))
    _khach(conn, batch, "K2", "Quán B", hang=("0001", "S"))
    _sua(conn, "khach", "K1", "rank_code", "0001", "0003")
    _sua(conn, "khach", "K1", "salesperson_code", "0004", "0002")
    r = conn.execute("""SELECT rank_code, rank_name, salesperson_code, salesperson_name FROM mart.dim_customer
                        WHERE customer_code='K1' AND is_current""").fetchone()
    ten_0004 = conn.execute("SELECT ten FROM core.dim_salesperson WHERE salesperson_code='0004'").fetchone()[0]
    assert r == ("0001", "S", "0004", ten_0004)


def test_dim_product_nganh_va_so(conn, batch):
    _hang(conn, batch, "P1", "Hang 1", ("01", "調味料_VNM"))
    _hang(conn, batch, "P2", "Hang 2", ("02", "冷凍食品_VNM"))
    _sua(conn, "san_pham", "P1", "food_category_code", "02", "01")
    _sua(conn, "san_pham", "P1", "case_qty", "24", "20.0000")
    r = conn.execute("SELECT food_category_code, food_category_name, case_qty FROM mart.dim_product WHERE product_code='P1'").fetchone()
    assert r[:2] == ("02", "冷凍食品_VNM") and float(r[2]) == 24


def test_view_hieu_luc_cung_cot_cung_kieu_voi_core(conn):
    q = """SELECT a.attname, format_type(a.atttypid, a.atttypmod) FROM pg_attribute a
           WHERE a.attrelid = %s::regclass AND a.attnum > 0 AND NOT a.attisdropped ORDER BY a.attnum"""
    for t in ("dim_customer", "dim_product"):
        assert conn.execute(q, (f"mart.{t}",)).fetchall() == conn.execute(q, (f"core.{t}",)).fetchall()


def test_so_chi_them_kome_app_khong_sua_khong_xoa(conn):
    for p in ("UPDATE", "DELETE"):
        assert conn.execute("SELECT has_table_privilege('kome_app', 'app.sua_du_lieu', %s)", (p,)).fetchone()[0] is False
    for p in ("SELECT", "INSERT"):
        assert conn.execute("SELECT has_table_privilege('kome_app', 'app.sua_du_lieu', %s)", (p,)).fetchone()[0] is True
    assert conn.execute("SELECT has_table_privilege('kome_app', 'mart.dim_customer', 'SELECT')").fetchone()[0] is True


def test_cot_la_bi_tu_choi(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO app.sua_du_lieu (bang, khoa, cot, gia_tri) VALUES ('khach', 'K1', 'customer_code', 'x')")
    conn.rollback()


def test_co_quyen_moi_va_so_quyen_nhan_co_do(conn):
    assert conn.execute("""SELECT column_default FROM information_schema.columns WHERE table_schema='app'
                           AND table_name='nguoi_dung' AND column_name='duoc_sua_du_lieu'""").fetchone()[0] == "false"
    d = conn.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='nhat_ky_quyen_co_check'").fetchone()[0]
    assert "duoc_sua_du_lieu" in d


def test_KHONG_view_ham_mart_nao_con_doc_danh_muc_OBC_tho(conn):
    """Test canh: migration sau chép thân view từ file cũ sẽ lặng lẽ đưa core.dim_* trở lại — bản sửa mất tác dụng ở màn đó."""
    v = conn.execute(r"""SELECT c.relname FROM pg_class c WHERE c.relnamespace = 'mart'::regnamespace AND c.relkind = 'v'
                         AND c.relname NOT IN ('dim_customer', 'dim_product')
                         AND pg_get_viewdef(c.oid) ~ '\mcore\.dim_(customer|product)\M'""").fetchall()
    f = conn.execute(r"""SELECT p.proname FROM pg_proc p WHERE p.pronamespace = 'mart'::regnamespace
                         AND p.prosrc ~ '\mcore\.dim_(customer|product)\M'""").fetchall()
    assert v == [] and f == []


def test_khach_360_doc_ten_da_sua(conn, batch):
    from tests.test_khach_hang import _mua
    _khach(conn, batch, "202601010001", "Quán A")
    _mua(conn, batch, "202601010001", D2)
    _sua(conn, "khach", "202601010001", "customer_name", "Quán A mới", "Quán A")
    assert conn.execute("SELECT ten FROM mart.khach_360 WHERE customer_code='202601010001'").fetchone()[0] == "Quán A mới"


def _gia(conn, batch, ma, qc, lv, ex, inc, ngay=D2):
    b = batch(abs(hash((ma, qc, lv, ex, ngay))) % 90_000, ngay)
    conn.execute("""INSERT INTO core.fact_price_list (product_code, pack_code, price_level, valid_from, price_ex_tax,
                      price_in_tax, unit_cost, batch_id) VALUES (%s, %s, %s, %s, %s, %s, 1000, %s)""",
                 (ma, qc, lv, ngay, ex, inc, b))
    conn.commit()


def test_gia_sua_thang_khi_OBC_giu_nguyen_va_thua_khi_OBC_doi(conn, batch):
    _hang(conn, batch, "P1", "Hang 1")
    _gia(conn, batch, "P1", "02", "01", 5000, 5400)
    obc = conn.execute("SELECT gia_obc::text FROM mart.bang_gia_kome WHERE product_code='P1'").fetchone()[0]
    _sua(conn, "gia", "P1|02|01", "gia_chua_thue", "5200", obc)
    r = conn.execute("SELECT gia_chua_thue, gia_obc, da_sua FROM mart.bang_gia_kome WHERE product_code='P1'").fetchone()
    assert (float(r[0]), float(r[1]), r[2]) == (5200, 5000, True)
    _gia(conn, batch, "P1", "02", "01", 5100, 5508, ngay=date(2026, 9, 20))       # lần nạp mới, OBC đổi giá
    r = conn.execute("SELECT gia_chua_thue, da_sua FROM mart.bang_gia_kome WHERE product_code='P1' AND hien_hanh").fetchone()
    assert (float(r[0]), r[1]) == (5100, False)


def _ton(conn, batch, ma, kho, sl, han, ngay=D2):
    b = batch(abs(hash((ma, kho, sl, ngay))) % 90_000, ngay)
    conn.execute("INSERT INTO core.dim_warehouse (warehouse_code, warehouse_name) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                 (kho, "Kho " + kho))
    conn.execute("""INSERT INTO core.fact_inventory_daily (snapshot_date, product_code, warehouse_code, best_before, stock_qty,
                      stock_unit_cost, stock_value, batch_id) VALUES (%s, %s, %s, %s, %s, 100, %s, %s)""",
                 (ngay, ma, kho, han, sl, int(sl * 100), b))
    conn.commit()


def test_ton_va_han_sua_di_theo_gia_tri_va_loai_han(conn, batch):
    _hang(conn, batch, "P1", "Hang 1")
    _ton(conn, batch, "P1", "0001", 10, "2027年03月10日")
    _sua(conn, "ton", "P1|0001", "stock_qty", "12", "10.0000")
    _sua(conn, "ton", "P1|0001", "best_before", "賞味期限なし", "2027年03月10日")
    r = conn.execute("""SELECT so_luong, gia_tri, best_before, loai_han, sua_so_luong, sua_han, so_luong_obc
                        FROM mart.ton_hien_tai WHERE product_code='P1'""").fetchone()
    assert (float(r[0]), r[1], r[2], r[3], r[4], r[5], float(r[6])) == (12, 1200, "賞味期限なし", "khong_han", True, True, 10)


def test_so_rong_moi_view_y_nhu_truoc(conn, batch):
    _hang(conn, batch, "P1", "Hang 1")
    _ton(conn, batch, "P1", "0001", 10, "2027年03月10日")
    r = conn.execute("SELECT so_luong, gia_tri, sua_so_luong, sua_han FROM mart.ton_hien_tai").fetchone()
    assert (float(r[0]), r[1], r[2], r[3]) == (10, 1000, False, False)
