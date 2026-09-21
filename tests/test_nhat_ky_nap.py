"""Test hai hàm đọc nhật ký nạp (meta.ingest_batch).

Fixture `conn` và `test_db_url` nằm ở tests/conftest.py. Không test nào ở đây
dựng web app — chúng đọc CSDL trực tiếp.
"""
from kome.nhat_ky_nap import BANG_THEO_LOAI, lo_nap_gan_nhat, trang_thai_nap


def _them_lo(conn, spec_name, source_file, data_date, row_count, total_amount,
             digest, undone_at=None):
    """Chèn một dòng nhật ký nạp, trả về batch_id.

    Phần lớn test ở đây không đụng bảng fact — chúng chỉ đọc
    meta.ingest_batch. Những test ĐẾM DÒNG thì có, và cần batch_id thật để
    gán vào dòng fact (khoá ngoại).
    """
    return conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date, undone_at)
           VALUES (%s, %s, %s, 'test', %s, %s, %s, %s)
           RETURNING batch_id""",
        (spec_name, source_file, digest, row_count, total_amount,
         data_date, undone_at)).fetchone()[0]


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


def test_bang_theo_loai_trung_khop_undo_tables():
    """[IMPORTANT] `BANG_THEO_LOAI` là bản chép tay của
    `kome.pipeline.UNDO_TABLES` — chép vì `kome/web/app.py` nhập
    `kome.nhat_ky_nap` ở mức ngoài cùng, mà `kome.pipeline` kéo theo pandas +
    python-calamine (~120 MB) không có trong requirements.txt của Vercel.

    Hai bản trôi khỏi nhau là thảm hoạ IM LẶNG: màn hình đếm dòng trên một
    bảng, còn `undo_batch()` xoá ở bảng khác — câu xác nhận nói một con số,
    nút xoá làm một việc khác. Thêm loader mới mà quên cập nhật ở đây thì
    test này đỏ ngay, chứ không đợi ai bấm nút mới biết."""
    from kome.pipeline import UNDO_TABLES
    assert BANG_THEO_LOAI == UNDO_TABLES, (
        "BANG_THEO_LOAI (kome/nhat_ky_nap.py) đã lệch khỏi UNDO_TABLES "
        "(kome/pipeline.py) — màn hoàn tác sẽ đếm sai bảng"
    )


def _them_ban_hang(conn, batch_id, phieu):
    """Upsert vài dòng bán hàng ĐÚNG khoá thật (slip_no, line_seq, source):
    cùng khoá thì lô sau dán batch_id của mình lên dòng của lô trước — đó
    chính là cơ chế làm hoàn tác xoá cả tháng."""
    for slip, seq in phieu:
        conn.execute(
            """INSERT INTO core.fact_sales_line
                 (slip_no, line_seq, sales_date, customer_code, product_code,
                  amount, batch_id, source)
               VALUES (%s, %s, '2026-09-01', 'C1', 'P1', 1000, %s, 'uriage')
               ON CONFLICT (slip_no, line_seq, source)
                 DO UPDATE SET batch_id = EXCLUDED.batch_id""",
            (slip, seq, batch_id))


def _them_gia(conn, batch_id, valid_from, muc):
    """Vài dòng bảng giá. Khoá CÓ valid_from, nên lô ngày khác không đè nhau."""
    for m in muc:
        conn.execute(
            """INSERT INTO core.fact_price_list
                 (product_code, pack_code, price_level, valid_from,
                  price_ex_tax, price_in_tax, unit_cost, batch_id)
               VALUES ('P1', '02', %s, %s, 100, 110, 80, %s)""",
            (m, valid_from, batch_id))


def test_dem_dong_that_khong_doan_theo_loai_file(conn):
    """[IMPORTANT] Số dòng hoàn tác sẽ xoá phải ĐẾM trong bảng đích, không
    suy ra từ `row_count` của lô.

    Dựng đúng kịch bản đối soát tháng: lô 1 nạp 2 phiếu, lô 2 nạp lại 3 phiếu
    CHỒNG lên 2 phiếu đó. Upsert của `core.fact_sales_line` dán batch_id của
    lô 2 lên cả 3 dòng, nên lô 1 còn GIỮ 0 dòng còn lô 2 giữ 3 — trong khi
    `row_count` vẫn ghi 2 và 3."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b1 = _them_lo(conn, "uriage", "売上伝票データ_20260901.xlsx", "2026-09-01",
                  2, 100, "dem1")
    _them_ban_hang(conn, b1, [("A", 1), ("B", 1)])
    b2 = _them_lo(conn, "uriage", "売上伝票データ_20260930.xlsx", "2026-09-30",
                  3, 150, "dem2")
    _them_ban_hang(conn, b2, [("A", 1), ("B", 1), ("C", 1)])
    conn.commit()

    theo_lo = {l.batch_id: l for l in lo_nap_gan_nhat(conn)}
    assert theo_lo[b1].so_dong_xoa == 0, \
        "lô 1 đã bị lô 2 đè hết — hoàn tác nó không xoá dòng nào"
    assert theo_lo[b1].so_dong == 2, \
        "row_count của lô 1 vẫn là 2 — đó chính là con số GÂY HIỂU NHẦM"
    assert theo_lo[b2].so_dong_xoa == 3, \
        "lô 2 đang giữ cả 3 dòng, kể cả 2 dòng do lô 1 nạp vào"
    assert theo_lo[b2].lam_trong_bang, "xoá lô 2 là bảng doanh thu trống sạch"
    assert not theo_lo[b1].lam_trong_bang


def test_lo_khong_chiem_ca_bang_thi_khong_doa_se_trong(conn):
    """Cảnh báo "sẽ trống hoàn toàn" phải im khi nó không đúng. Dán cảnh báo
    nặng lên ca không cần dạy người đọc coi thường mọi cảnh báo — nguy hiểm
    ngang việc thiếu cảnh báo."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b1 = _them_lo(conn, "uriage", "売上伝票データ_20260901.xlsx", "2026-09-01",
                  1, 100, "dem3")
    _them_ban_hang(conn, b1, [("A", 1)])
    b2 = _them_lo(conn, "uriage", "売上伝票データ_20260902.xlsx", "2026-09-02",
                  1, 100, "dem4")
    _them_ban_hang(conn, b2, [("B", 1)])
    conn.commit()

    theo_lo = {l.batch_id: l for l in lo_nap_gan_nhat(conn)}
    assert theo_lo[b2].so_dong_xoa == 1
    assert not theo_lo[b2].lam_trong_bang, "bảng vẫn còn dòng của lô 1"
    assert theo_lo[b2].tong_bang == 2


def test_tanka_giu_nhieu_dong_hon_so_dong_cua_file(conn):
    """[IMPORTANT] `tanka` NỞ dòng: mỗi dòng nguồn mang 10 mức giá nằm ngang,
    thành tối đa 10 dòng dọc trong `core.fact_price_list`. Lô giữ NHIỀU dòng
    hơn `row_count`, và câu xác nhận phải giải thích chênh lệch đó — nếu
    không người đọc kết luận màn hình sai rồi bỏ qua luôn cả cảnh báo.

    Cũng đúng là loại mà bản cũ cảnh báo SAI: khoá bảng giá có `valid_from`
    nên lô sau KHÔNG đè lô trước, bảng không hề trống sau hoàn tác."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b1 = _them_lo(conn, "tanka", "取引単価データ_20260901.xlsx", "2026-09-01",
                  1, 0, "dem5")
    _them_gia(conn, b1, "2026-09-01", ["01", "02", "03"])
    b2 = _them_lo(conn, "tanka", "取引単価データ_20260902.xlsx", "2026-09-02",
                  1, 0, "dem6")
    _them_gia(conn, b2, "2026-09-02", ["01", "02"])
    conn.commit()

    theo_lo = {l.batch_id: l for l in lo_nap_gan_nhat(conn)}
    assert theo_lo[b2].so_dong_xoa == 2
    assert theo_lo[b2].nhieu_hon_luc_nap, "2 dòng đích > 1 dòng nguồn"
    assert not theo_lo[b2].lam_trong_bang, \
        "bảng giá KHÔNG trống — ba dòng của lô trước còn nguyên"
    assert theo_lo[b2].tong_bang == 5


def test_lo_scd2_bi_de_tai_cho_khong_tinh_la_dong_se_xoa(conn):
    """Dòng khách bị ĐÈ TẠI CHỖ mang batch_id của lô mới, nhưng hoàn tác
    HOÀN NGUYÊN chúng từ `scd2_preimage` chứ không xoá. Đếm thẳng
    `count(*) WHERE batch_id` sẽ thổi phồng con số — phải trừ ra."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b1 = _them_lo(conn, "tokuisaki", "得意先全情報_20260901.xlsx", "2026-09-01",
                  2, 0, "dem7")
    conn.execute(
        """INSERT INTO core.dim_customer
             (customer_code, customer_name, valid_from, is_current, batch_id)
           VALUES ('C1', 'Khách 1', '2026-09-01', true, %s),
                  ('C2', 'Khách 2', '2026-09-01', true, %s)""", (b1, b1))
    conn.execute(
        """UPDATE meta.ingest_batch
           SET scd2_preimage = '[{"code": "C1", "batch_id": 0,
                                  "values": {"customer_name": "Cũ"}}]'::jsonb
           WHERE batch_id = %s""", (b1,))
    conn.commit()

    lo = {l.batch_id: l for l in lo_nap_gan_nhat(conn)}[b1]
    assert lo.so_dong_xoa == 1, \
        "2 dòng mang lô này, nhưng 1 dòng chỉ được hoàn nguyên chứ không xoá"
    assert not lo.lam_trong_bang, "bảng khách hàng còn dòng C1 đã hoàn nguyên"


def test_loai_la_khong_con_trong_cau_hinh_thi_khong_bia_so(conn):
    """Lô cũ mang `spec_name` đã bị gỡ khỏi cấu hình: thà nói "không đếm
    được" còn hơn in một con số bịa ra ngay cạnh một nút xoá."""
    conn.execute("DELETE FROM meta.ingest_batch")
    _them_lo(conn, "loai_da_go", "gi_do.xlsx", "2026-09-01", 9, 0, "dem8")
    conn.commit()
    lo = lo_nap_gan_nhat(conn)[0]
    assert lo.so_dong_xoa is None and lo.tong_bang is None and lo.ten_bang is None
