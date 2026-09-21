"""Test hai hàm đọc nhật ký nạp (meta.ingest_batch).

Fixture `conn` và `test_db_url` nằm ở tests/conftest.py. Không test nào ở đây
dựng web app — chúng đọc CSDL trực tiếp.
"""
from kome.nhat_ky_nap import lo_nap_gan_nhat, trang_thai_nap


def _them_lo(conn, spec_name, source_file, data_date, row_count, total_amount,
             digest, undone_at=None):
    """Chèn một dòng nhật ký nạp. Không đụng bảng fact — hai hàm đang test
    chỉ đọc meta.ingest_batch."""
    conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date, undone_at)
           VALUES (%s, %s, %s, 'test', %s, %s, %s, %s)""",
        (spec_name, source_file, digest, row_count, total_amount,
         data_date, undone_at))


def test_trang_thai_nap_lay_lan_nap_gan_nhat_cua_tung_loai(conn):
    """[IMPORTANT] Phải là lần nạp GẦN NHẤT của từng loại, không phải max()
    của từng cột riêng lẻ. Sau một lần đối soát tháng ~18.000 dòng, nếu lấy
    max(row_count) thì trang LUÔN hiện 18.000 kể cả hôm nay OBC xuất cắt cụt
    còn 60 dòng — tức trang giấu đúng cái sự cố nó sinh ra để báo."""
    conn.execute("DELETE FROM meta.ingest_batch")
    _them_lo(conn, "zaiko", "在庫一覧_20260101.xlsx", "2026-01-01", 18000, 0, "d1")
    _them_lo(conn, "zaiko", "在庫一覧_20260102.xlsx", "2026-01-02", 60, 0, "d2")

    ds = {r["name"]: r for r in trang_thai_nap(conn)}
    zaiko = [r for r in ds.values() if r["rows"] in (60, 18000)]
    assert zaiko and zaiko[0]["rows"] == 60, "phải lấy lô mới nhất (60), không phải max (18000)"


def test_trang_thai_nap_liet_ke_du_moi_loai_ke_ca_loai_chua_nap(conn):
    """Loại chưa nạp lần nào vẫn phải có dòng, với last=None — bảng thiếu
    hẳn một dòng thì người đọc tưởng loại đó không tồn tại, thay vì hiểu là
    nó chưa vào kho."""
    conn.execute("DELETE FROM meta.ingest_batch")
    ds = trang_thai_nap(conn)
    assert len(ds) >= 7, f"chỉ có {len(ds)} dòng, phải đủ mọi loại khai trong SPECS"
    assert all(r["last"] is None and r["rows"] == 0 for r in ds)


def test_lo_nap_gan_nhat_bo_qua_lo_da_hoan_tac(conn):
    """[IMPORTANT] Lô đã hoàn tác KHÔNG được hiện nút Hoàn tác lần nữa —
    bấm lần hai là xoá một thứ đã không còn, và người bấm thì tưởng lần
    đầu chưa ăn."""
    conn.execute("DELETE FROM meta.ingest_batch")
    _them_lo(conn, "zaiko", "con.xlsx", "2026-01-02", 10, 0, "d3")
    _them_lo(conn, "zaiko", "da_hoan_tac.xlsx", "2026-01-01", 10, 0, "d4",
             undone_at="2026-01-03")

    ds = lo_nap_gan_nhat(conn)
    ten = [l.ten_file for l in ds]
    assert "con.xlsx" in ten
    assert "da_hoan_tac.xlsx" not in ten


def test_lo_nap_gan_nhat_sap_moi_truoc_va_ton_trong_gioi_han(conn):
    """Lô mới nhất phải đứng đầu: người vừa nạp nhầm sẽ tìm nó ở dòng một,
    không phải cuộn xuống cuối."""
    conn.execute("DELETE FROM meta.ingest_batch")
    for i in range(1, 6):
        _them_lo(conn, "zaiko", f"f{i}.xlsx", f"2026-01-0{i}", i, 0, f"g{i}")

    ds = lo_nap_gan_nhat(conn, gioi_han=3)
    assert len(ds) == 3
    assert ds[0].ten_file == "f5.xlsx"
    assert ds[0].batch_id > ds[1].batch_id


def test_lo_nap_gan_nhat_hien_ten_tieng_nhat_cua_loai_file(conn):
    """Người vận hành nhận diện file bằng tên tiếng Nhật OBC xuất ra
    (在庫一覧…), không bằng mã nội bộ `zaiko`."""
    conn.execute("DELETE FROM meta.ingest_batch")
    _them_lo(conn, "zaiko", "在庫一覧_20260101.xlsx", "2026-01-01", 10, 0, "d5")
    assert lo_nap_gan_nhat(conn)[0].loai == "在庫一覧"
