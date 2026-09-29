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
