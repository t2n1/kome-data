"""Kiểm "mã có trong danh mục Sản phẩm 360" mà KHÔNG dựng `mart.san_pham_360` (2026-10-15).

Đo thật trên CSDL thật: `EXISTS (… FROM mart.san_pham_360 WHERE product_code = …)` mất 1,5–6,3 s (view tính tốc độ /
tỷ suất / tồn của CẢ danh mục rồi mới lọc), chiếm > 90% thời gian mỗi tab của /san-pham/{mã}; mọi câu khác của tab
≤ 0,16 s. Tập dòng của view chỉ do `FROM mart.dim_product … WHERE` quyết định (mọi JOIN khác là LEFT JOIN thêm cột),
nên `SP360.TRONG_DANH_MUC` là BẢN CHÉP của đúng mệnh đề đó — test này canh hai bản trả CÙNG một tập mã."""
from fastapi.testclient import TestClient

from kome import san_pham_360 as SP360
from kome.web.app import create_app
from tests.test_ngung_ban import HANG, NGUNG, NGUNG_TON, _du_lieu


def _them_phi_va_posm(conn, batch):
    b = batch(777_301)
    conn.execute(
        """INSERT INTO core.dim_product (product_code, product_name, kind_code, kind_name, food_category_name, batch_id)
           VALUES ('FEE1', '代引手数料', '1', '無形', '', %s),
                  ('MKT01', 'Poster', '0', '有形', '雑貨_VNM', %s)""", (b, b))
    conn.commit()


def _tap(conn, sql):
    return {r[0] for r in conn.execute(sql)}


def test_ban_chep_TRUNG_tap_ma_cua_san_pham_360(conn, batch):
    _du_lieu(conn, batch)
    _them_phi_va_posm(conn, batch)
    tat_ca = _tap(conn, "SELECT product_code FROM mart.dim_product")
    view = _tap(conn, "SELECT product_code FROM mart.san_pham_360")
    chep = {m for m in tat_ca if conn.execute(f"SELECT {SP360.TRONG_DANH_MUC}", (m,)).fetchone()[0]}
    # Dữ liệu phải phủ đủ ba lý do bị loại, không thì test không chứng minh gì.
    assert {NGUNG, "FEE1", "MKT01"} <= tat_ca - view and {HANG, NGUNG_TON} <= view
    assert chep == view


def test_tab_cua_ma_ngoai_danh_muc_van_404(conn, batch, test_db_url):
    _du_lieu(conn, batch)
    _them_phi_va_posm(conn, batch)
    assert SP360.tab_khach(conn, NGUNG) is None and SP360.tab_gia(conn, "FEE1") is None
    assert SP360.tab_thoi_gian(conn, "MKT01") is None
    assert SP360.tab_khach(conn, HANG) is not None
    c = TestClient(create_app(db_url=test_db_url))
    assert c.get(f"/api/san-pham/{NGUNG}/khach").status_code == 404
    assert c.get(f"/api/san-pham/{HANG}/khach").status_code == 200
