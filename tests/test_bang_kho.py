"""Kho dữ liệu → xem từng bảng (đợt C, 2026-09-24).

Màn đọc BẤT KỲ bảng nào theo tên trên URL — nên hai điều phải canh chặt: tên
bảng không bao giờ ghép thẳng vào SQL (chỉ quan hệ có thật của core/mart/meta,
KHÔNG `app` — nơi có băm mật khẩu), và ô tìm không bao giờ thành SQL."""
import pytest
from fastapi.testclient import TestClient

from kome import bang_kho as BK
from kome.web.app import _thuoc_kho_du_lieu, create_app
from tests.spa_kd import man


def _ban(conn, batch, phieu, ngay, tien=1000):
    conn.execute(
        """INSERT INTO core.fact_sales_line (slip_no, line_seq, sales_date, customer_code, product_code,
                                             amount, batch_id, source)
           VALUES (%s, 1, %s, 'C1', 'P1', %s, %s, 'uriage')""", (phieu, ngay, tien, batch))


@pytest.fixture
def du_lieu(conn):
    b1 = conn.execute("""INSERT INTO meta.ingest_batch (spec_name, source_file, digest, archived_to, row_count, total_amount, data_date)
                         VALUES ('uriage', 'a.xlsx', 'd1', 'x', 2, 2000, '2026-07-31') RETURNING batch_id""").fetchone()[0]
    b2 = conn.execute("""INSERT INTO meta.ingest_batch (spec_name, source_file, digest, archived_to, row_count, total_amount, data_date)
                         VALUES ('uriage', 'b.xlsx', 'd2', 'x', 1, 1000, '2026-08-31') RETURNING batch_id""").fetchone()[0]
    _ban(conn, b1, "S1", "2026-07-02")
    _ban(conn, b1, "S2", "2026-07-15")
    _ban(conn, b2, "S3", "2026-08-03")
    conn.commit()
    return b1, b2


def test_danh_sach_khong_co_schema_app(conn):
    ds = BK.danh_sach(conn)
    ten = {b["ten"] for b in ds}
    assert "core.fact_sales_line" in ten and "mart.khach_360" in ten and "meta.ingest_batch" in ten
    assert not any(t.startswith("app.") for t in ten), "schema app (tài khoản, băm mật khẩu) không được lộ"
    assert next(b for b in ds if b["ten"] == "mart.khach_360")["so_dong"] is None   # view: không có số dòng


@pytest.mark.parametrize("ten", ["app.nguoi_dung", "core.fact_sales_line; DROP TABLE x", "core.khong_co",
                                 "../etc", "CORE.fact_sales_line", "core.fact_sales_line--", "pg_catalog.pg_authid", ""])
def test_ten_bang_la_bi_tu_choi(conn, ten):
    """[IMPORTANT] Tên bảng phải là quan hệ có thật của core/mart/meta."""
    with pytest.raises(BK.KhongCoBang):
        BK.thong_tin(conn, ten)


def test_thong_tin_cot_khoa_va_lan_nap(conn, du_lieu):
    tt = BK.thong_tin(conn, "core.fact_sales_line")
    assert tt["khoa_chinh"] == ["slip_no", "line_seq", "source"]
    c = {x["ten"]: x for x in tt["cot"]}
    assert c["sales_date"]["khoa_ngoai"] == "core.dim_date.date_key"
    assert c["gross_profit"]["ja"] == "粗利益"          # tên gốc OBC lấy từ files.yml
    assert {n["spec"] for n in tt["nguon"]} == {"uriage", "meisai"}
    assert [l["batch_id"] for l in tt["lan_nap"]] == [du_lieu[1], du_lieu[0]]
    assert tt["cot_ngay"] == "sales_date" and tt["co_lo"]


def test_dong_loc_nhanh_va_tim(conn, du_lieu):
    tt = BK.thong_tin(conn, "core.fact_sales_line")
    assert BK.dong(conn, tt)["tong"] == 3
    assert BK.dong(conn, tt, chip="thang")["tong"] == 1          # tháng gần nhất = 2026-08
    assert BK.dong(conn, tt, chip="lo")["tong"] == 1             # lô mới nhất
    assert BK.dong(conn, tt, tim="S2")["tong"] == 1
    # Ô tìm là THAM SỐ, không phải SQL; % và _ là chữ thường.
    assert BK.dong(conn, tt, tim="'; DROP TABLE core.fact_sales_line; --")["tong"] == 0
    assert BK.dong(conn, tt, tim="%")["tong"] == 0
    assert BK.dong(conn, tt)["tong"] == 3                        # bảng vẫn còn nguyên


def test_view_doc_duoc_va_loc_thang_tinh_mot_lan(conn, du_lieu):
    tt = BK.thong_tin(conn, "mart.dong_ban")
    assert tt["loai"] == "view"
    assert BK.dong(conn, tt)["tong"] == 3
    assert BK.dong(conn, tt, chip="thang")["tong"] == 1
    dau, nguon, *_ = BK._cau(tt, "", "thang")
    assert "MATERIALIZED" in dau.as_string(conn)                 # bất biến CTE-trùng


def test_phan_trang(conn, du_lieu, monkeypatch):
    monkeypatch.setattr(BK, "MOI_TRANG", 2)
    tt = BK.thong_tin(conn, "core.fact_sales_line")
    t1, t2 = BK.dong(conn, tt, trang=1), BK.dong(conn, tt, trang=2)
    assert len(t1["dong"]) == 2 and len(t2["dong"]) == 1 and t1["tong"] == t2["tong"] == 3


def test_giao_dich_chi_doc(conn, du_lieu):
    """Mọi câu chạy trong giao dịch READ ONLY — lỡ có câu ghi thì CSDL từ chối."""
    BK._chi_doc(conn)
    with pytest.raises(Exception, match="read-only"):
        conn.execute("DELETE FROM core.fact_sales_line")
    conn.rollback()
    assert conn.execute("SELECT count(*) FROM core.fact_sales_line").fetchone()[0] == 3


def test_csv_co_bom_va_tieu_de(conn, du_lieu):
    tt = BK.thong_tin(conn, "core.fact_sales_line")
    van = BK.csv_van_ban(conn, tt, chip="lo")
    assert van.startswith("﻿slip_no,line_seq,")
    assert van.count("\r\n") == 2                                  # tiêu đề + 1 dòng


def test_api_va_trang(conn, du_lieu, test_db_url):
    c = TestClient(create_app(db_url=test_db_url))
    assert c.get("/api/kho-du-lieu/bang").status_code == 200
    r = c.get("/api/kho-du-lieu/bang/core.fact_sales_line/dong?chip=lo")
    assert r.status_code == 200 and r.json()["tong"] == 1
    assert c.get("/api/kho-du-lieu/bang/app.nguoi_dung").status_code == 404
    assert c.get("/api/kho-du-lieu/bang/app.nguoi_dung/dong").status_code == 404
    r = c.get("/api/kho-du-lieu/bang/core.fact_sales_line/csv")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert man(c.get("/kho-du-lieu/bang/core.fact_sales_line").text) == {"bang": "core.fact_sales_line"}


def test_api_bang_nam_sau_cong_quyen_kho_du_lieu():
    """[IMPORTANT] API đọc được MỌI bảng core — phải cùng cổng với màn có nút xoá."""
    assert _thuoc_kho_du_lieu("/api/kho-du-lieu/bang")
    assert _thuoc_kho_du_lieu("/api/kho-du-lieu/bang/core.fact_sales_line/csv")
    assert not _thuoc_kho_du_lieu("/api/khach-hang/ds")
