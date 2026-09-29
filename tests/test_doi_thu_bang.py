"""Migration 059 — bảng Thị trường & đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4)."""


def _quyen(conn, vai, bang, q):
    return conn.execute("SELECT has_table_privilege(%s, %s, %s)", (vai, bang, q)).fetchone()[0]


def test_ba_so_CHI_THEM_kome_app_khong_sua_khong_xoa_duoc(conn):
    for bang in ("app.dinh_chinh_gia", "app.gia_doi_thu_tay", "app.doi_thu_nhat_ky"):
        assert _quyen(conn, "kome_app", bang, "INSERT"), bang
        assert _quyen(conn, "kome_app", bang, "SELECT"), bang
        assert not _quyen(conn, "kome_app", bang, "UPDATE"), bang
        assert not _quyen(conn, "kome_app", bang, "DELETE"), bang


def test_bang_nap_chi_kome_ingest_ghi_duoc(conn):
    for bang in ("core.fact_gia_doi_thu", "core.fact_dieu_kien_doi_thu"):
        assert _quyen(conn, "kome_ingest", bang, "INSERT"), bang
        assert _quyen(conn, "kome_ingest", bang, "DELETE"), bang     # nút Hoàn tác
        assert _quyen(conn, "kome_app", bang, "SELECT"), bang
        assert not _quyen(conn, "kome_app", bang, "INSERT"), bang
        assert not _quyen(conn, "kome_app", bang, "UPDATE"), bang


def test_bang_sua_duoc_cua_app(conn):
    for bang in ("app.ghep_hang", "app.nhom_so_sanh", "app.nhom_so_sanh_ma", "app.quy_cach_kome", "app.doi_thu"):
        assert _quyen(conn, "kome_app", bang, "UPDATE"), bang


def test_seed_loai_nguon_va_doi_thu(conn):
    ln = conn.execute("SELECT ma, thu_tu FROM app.loai_nguon ORDER BY thu_tu").fetchall()
    assert ln == [("bang_gia", 1), ("chung_tu", 2), ("to_roi", 3), ("khach_ke", 4), ("khac", 5)]
    ma = {r[0] for r in conn.execute("SELECT ma FROM app.doi_thu")}
    assert {"THAK", "HSC", "THAI-DUONG", "NEXT", "QUANG-KE", "VIPRO"} <= ma and len(ma) == 21


def test_dinh_chinh_chi_nhan_truong_hop_le(conn):
    import psycopg, pytest
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (1, 'xoa_het', 'x')")
    conn.rollback()


def test_gia_tay_bat_buoc_loai_nguon_co_that(conn):
    import psycopg, pytest
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        conn.execute("""INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, loai_nguon)
                        VALUES ('THAK', 'x', 'x', 'bua')""")
    conn.rollback()


def test_khong_bang_nao_bat_RLS(conn):
    """Phân quyền theo vai trò (009), không theo RLS. Bảng tạo qua SQL Editor của Supabase bị tự bật
    RLS mà không có policy → kome_app/kome_ingest thấy 0 dòng (sự cố thật 2026-09-29, migration 061)."""
    bat = [r[0] for r in conn.execute(
        """SELECT n.nspname || '.' || c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace
           WHERE n.nspname IN ('core', 'app', 'meta', 'mart') AND c.relkind = 'r' AND c.relrowsecurity""")]
    assert bat == []


def test_tiep_xuc_nhac_CHI_THEM_kome_app_khong_sua_khong_xoa_duoc(conn):
    assert _quyen(conn, "kome_app", "app.tiep_xuc_nhac", "INSERT")
    assert _quyen(conn, "kome_app", "app.tiep_xuc_nhac", "SELECT")
    assert not _quyen(conn, "kome_app", "app.tiep_xuc_nhac", "UPDATE")
    assert not _quyen(conn, "kome_app", "app.tiep_xuc_nhac", "DELETE")


def test_tiep_xuc_nhac_kiem_loai_vi_tri_va_khoa_ngoai(conn):
    import psycopg, pytest
    tx = conn.execute("""INSERT INTO app.nhat_ky_tiep_xuc (customer_code, kieu, ket_qua, noi_dung)
                         VALUES ('202601010001', 'goi', 'tot', 'nghe @THAK ban 700') RETURNING id""").fetchone()[0]
    conn.execute("INSERT INTO app.tiep_xuc_nhac (tiep_xuc_id, loai, khoa, vi_tri_dau, do_dai) VALUES (%s,'doi_thu','THAK',5,5)", (tx,))
    conn.commit()
    for sql in ("INSERT INTO app.tiep_xuc_nhac (tiep_xuc_id, loai, khoa, vi_tri_dau, do_dai) VALUES ({tx},'bua','x',0,1)",
                "INSERT INTO app.tiep_xuc_nhac (tiep_xuc_id, loai, khoa, vi_tri_dau, do_dai) VALUES ({tx},'nhom','x',-1,1)",
                "INSERT INTO app.tiep_xuc_nhac (tiep_xuc_id, loai, khoa, vi_tri_dau, do_dai) VALUES ({tx},'nhom','x',0,0)",
                "INSERT INTO app.tiep_xuc_nhac (tiep_xuc_id, loai, khoa, vi_tri_dau, do_dai) VALUES (999999,'nhom','x',0,1)"):
        with pytest.raises((psycopg.errors.CheckViolation, psycopg.errors.ForeignKeyViolation)):
            conn.execute(sql.format(tx=tx))
        conn.rollback()


def test_gia_tay_co_cot_nhom_khoa(conn):
    assert conn.execute("""SELECT count(*) FROM information_schema.columns WHERE table_schema='app'
                           AND table_name='gia_doi_thu_tay' AND column_name='nhom_khoa'""").fetchone()[0] == 1
