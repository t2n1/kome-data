from pathlib import Path
from db.migrate import apply_all


def test_report_chi_duoc_doc(fresh_conn):
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_report', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_report', 'core.fact_sales_line', 'INSERT')"""
    ).fetchone()
    assert r[0] is True and r[1] is False


def test_app_khong_duoc_ghi_vao_core(fresh_conn):
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_app', 'core.fact_sales_line', 'SELECT'),
                  has_table_privilege('kome_app', 'core.fact_sales_line', 'UPDATE')"""
    ).fetchone()
    assert r[0] is True and r[1] is False   # luật bất biến #1


def test_ingest_lam_duoc_viec_cua_no(fresh_conn):
    """Không chỉ kiểm vai trò khác BỊ CHẶN — phải kiểm vai trò nạp dữ liệu
    LÀM ĐƯỢC VIỆC của nó. 009 cấp SELECT/INSERT/UPDATE nhưng THIẾU DELETE,
    trong khi kome/pipeline.py hoàn tác bằng DELETE FROM core.… WHERE batch_id.
    Ngay khi runbook bảo đổi DATABASE_URL sang kome_ingest_user thì sự cố đầu
    bảng của runbook và route /undo/{batch_id} đều chết với permission denied.
    """
    apply_all(fresh_conn, Path("db/migrations"))
    for bang in ("core.fact_sales_line", "core.dim_customer", "core.fact_inventory_daily"):
        r = fresh_conn.execute(
            """SELECT has_table_privilege('kome_ingest', %s, 'SELECT'),
                      has_table_privilege('kome_ingest', %s, 'INSERT'),
                      has_table_privilege('kome_ingest', %s, 'UPDATE'),
                      has_table_privilege('kome_ingest', %s, 'DELETE')""",
            (bang, bang, bang, bang),
        ).fetchone()
        assert all(r), f"{bang}: kome_ingest thiếu quyền {r}"


def test_ingest_khong_xoa_duoc_nhat_ky_nap(fresh_conn):
    """meta.ingest_batch là bảng lịch sử: hoàn tác chỉ đặt undone_at, không bao
    giờ xoá dòng (luật bất biến #6). CSDL phải giữ luôn điều đó."""
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_ingest', 'meta.ingest_batch', 'INSERT'),
                  has_table_privilege('kome_ingest', 'meta.ingest_batch', 'UPDATE'),
                  has_table_privilege('kome_ingest', 'meta.ingest_batch', 'DELETE')"""
    ).fetchone()
    assert r[0] is True and r[1] is True and r[2] is False


def test_app_doc_duoc_nhat_ky_nap(fresh_conn):
    """kome_app CỐ Ý không ghi được vào core, nhưng việc nó không ĐỌC được
    meta là một khoảng trống chứ không phải chủ ý: trang chủ `/` cần
    meta.ingest_batch cho ô "hôm nay đã có dữ liệu chưa". Thiếu quyền này thì
    trang chủ của bản chạy bằng kome_app_user trả 500."""
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_app', 'meta.ingest_batch', 'SELECT'),
                  has_table_privilege('kome_app', 'meta.ingest_batch', 'INSERT'),
                  has_table_privilege('kome_app', 'meta.ingest_batch', 'UPDATE')"""
    ).fetchone()
    assert r[0] is True, "kome_app không đọc được nhật ký nạp -> trang chủ 500"
    assert r[1] is False and r[2] is False, "kome_app chỉ được ĐỌC meta"


def test_app_ghi_duoc_bang_tai_khoan(fresh_conn):
    """app.nguoi_dung thuộc schema `app` — vai trò kome_app phải đọc-ghi được,
    nếu không thì chính việc đăng nhập (và đổi mật khẩu) không chạy."""
    apply_all(fresh_conn, Path("db/migrations"))
    r = fresh_conn.execute(
        """SELECT has_table_privilege('kome_app', 'app.nguoi_dung', 'SELECT'),
                  has_table_privilege('kome_app', 'app.nguoi_dung', 'INSERT'),
                  has_table_privilege('kome_app', 'app.nguoi_dung', 'UPDATE')"""
    ).fetchone()
    assert all(r), f"kome_app thiếu quyền trên app.nguoi_dung: {r}"


def test_report_khong_doc_duoc_bam_mat_khau(fresh_conn):
    """kome_report là vai trò cho công cụ báo cáo/BI ngoài ứng dụng chính.
    ALTER DEFAULT PRIVILEGES của 009 cấp cho nó SELECT trên MỌI bảng schema
    `app` — nghĩa là bảng tài khoản vừa tạo cũng tự lọt vào tầm với của nó.
    Một công cụ vẽ biểu đồ doanh thu không có việc gì phải đọc hash mật khẩu
    của nhân viên; 019 thu lại quyền đó."""
    apply_all(fresh_conn, Path("db/migrations"))
    assert fresh_conn.execute(
        "SELECT has_table_privilege('kome_report', 'app.nguoi_dung', 'SELECT')"
    ).fetchone()[0] is False


def test_nam_nguoi_phu_trach_cua_obc_duoc_nap_san(conn):
    """5 担当者 của OBC là dữ liệu THAM CHIẾU do migration nạp — app.nguoi_dung
    trỏ khoá ngoại vào đây. Dùng fixture `conn` (không phải fresh_conn) để test
    này CŨNG canh luôn việc bảng sống sót qua TRUNCATE giữa các test."""
    rows = conn.execute(
        "SELECT salesperson_code, ten FROM core.dim_salesperson ORDER BY 1"
    ).fetchall()
    assert [r[0] for r in rows] == ["0002", "0004", "0102", "0104", "0105"]
    assert dict(rows)["0102"] == "NGUYEN PHUONG DUNG"
