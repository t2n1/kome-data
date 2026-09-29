"""Migration 059 — bảng Thị trường & đối thủ (đặc tả 2026-09-29-thi-truong-doi-thu-design.md §4)."""
import psycopg
import pytest



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


def test_064_thu_muc_nguon_chi_nhan_mung_1_va_https(conn):
    conn.execute("INSERT INTO app.thu_muc_nguon (thang, lien_ket) VALUES ('2026-08-01', 'https://drive.google.com/x')")
    conn.commit()
    for thang, lk in [("2026-08-02", "https://drive.google.com/y"), ("2026-09-01", "http://drive.google.com/y"),
                      ("2026-09-01", "javascript:alert(1)")]:
        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute("INSERT INTO app.thu_muc_nguon (thang, lien_ket) VALUES (%s, %s)", (thang, lk))
        conn.rollback()


def test_064_lien_ket_bang_chung_chi_https_va_bang_van_chi_them(conn):
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("""INSERT INTO app.gia_doi_thu_tay (ma_doi_thu, ma_hang_dt, ten_goc, trang_thai, loai_nguon,
                          lien_ket_bang_chung) VALUES ('THAK', 'ten:x|', 'x', 'het', 'chung_tu', 'ftp://a')""")
    conn.rollback()
    for quyen in ("UPDATE", "DELETE"):
        assert not conn.execute("SELECT has_table_privilege('kome_app', 'app.gia_doi_thu_tay', %s)", (quyen,)).fetchone()[0]


def test_064_nhat_ky_nhan_loai_thu_muc(conn):
    conn.execute("INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong) VALUES ('thu_muc', 'thang:2026-08')")
    conn.commit()


# ---------------------------------------------------------------- 065 (đợt 4a)

def test_065_cot_quy_cach_va_bac_tren_fact_va_bang_tay(conn):
    for bang in ("core.fact_gia_doi_thu", "app.gia_doi_thu_tay"):
        cot = {r[0]: r[1] for r in conn.execute(
            """SELECT column_name, data_type FROM information_schema.columns
               WHERE table_schema || '.' || table_name = %s""", (bang,))}
        assert cot["so_goi_thung"] == "integer", bang
        assert cot["kl_goi_g"] == "numeric", bang
        assert cot["bac"] == "jsonb", bang
    cot_tay = {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='app' AND table_name='gia_doi_thu_tay'")}
    assert {"khuyen_mai", "gia_truoc_km"} <= cot_tay


def test_065_bac_phai_la_mang_va_quy_cach_duong(conn, batch):
    b = batch(1)
    def them(**kw):
        conn.execute(
            f"""INSERT INTO core.fact_gia_doi_thu (batch_id, ma_dong, ma_doi_thu, ma_hang_dt, ngay_nguon, hinh_thuc_nguon,
                  ten_goc, trang_thai, do_chac{''.join(', ' + k for k in kw)})
                VALUES (%s, %s, 'THAK', 'ten:x', '2026-08-01', 'file', 'x', 'con', 'chac'{', %s' * len(kw)})""",
            (b, f"d{len(kw)}{list(kw.values())}", *kw.values()))
    them(bac='[{"tu": 5, "don_vi_sl": "thung", "gia": 5300, "don_vi_gia": "thung"}]', so_goi_thung=20, kl_goi_g=500)
    conn.commit()
    for xau in ({"bac": '{"tu": 5}'}, {"so_goi_thung": 0}, {"kl_goi_g": 0}, {"kl_goi_g": 30001}):
        with pytest.raises(psycopg.errors.CheckViolation):
            them(**xau)
        conn.rollback()


def test_065_so_moi_CHI_THEM_kome_app(conn):
    for bang in ("app.dinh_chinh_giao_hang", "app.dinh_chinh_dieu_kien"):
        assert _quyen(conn, "kome_app", bang, "INSERT"), bang
        assert _quyen(conn, "kome_app", bang, "SELECT"), bang
        assert not _quyen(conn, "kome_app", bang, "UPDATE"), bang
        assert not _quyen(conn, "kome_app", bang, "DELETE"), bang
    assert _quyen(conn, "kome_app", "app.giao_hang_kome", "UPDATE")          # KOME sửa được, lịch sử ở nhật ký
    assert not _quyen(conn, "kome_app", "app.giao_hang_kome", "DELETE")
    assert _quyen(conn, "kome_ingest", "core.fact_giao_hang_doi_thu", "DELETE")   # nút Hoàn tác
    assert not _quyen(conn, "kome_app", "core.fact_giao_hang_doi_thu", "INSERT")


def test_065_kome_mac_dinh_suy_tu_phieu_ban_chua_xac_nhan(conn):
    r = conn.execute("""SELECT bao_ship, phi_ship, phi_ship_theo, mien_ship_tu, phi_daibiki, daibiki_tu, daibiki_sau,
                               thue, da_xac_nhan FROM app.giao_hang_kome""").fetchall()
    assert r == [(False, 500, "don", 20000, 330, 20000, 300, "chua", False)]


def test_065_check_moi_nhan_truong_va_loai_moi(conn):
    for t in ("so_goi_thung", "kl_goi_g", "bac", "khuyen_mai", "gia_truoc_km"):
        conn.execute("INSERT INTO app.dinh_chinh_gia (fact_id, truong, gia_tri_moi) VALUES (1, %s, '1')", (t,))
    for loai in ("giao_hang", "dieu_kien"):
        conn.execute("INSERT INTO app.doi_thu_nhat_ky (loai, doi_tuong) VALUES (%s, 'x')", (loai,))
    conn.commit()
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute("INSERT INTO app.dinh_chinh_giao_hang (ma_doi_thu, truong, gia_tri_moi) VALUES ('THAK', 'khong_co', '1')")
    conn.rollback()


def test_065_dim_product_co_cot_hanh_dong_goi(conn):
    cot = {r[0] for r in conn.execute(
        "SELECT column_name FROM information_schema.columns WHERE table_schema='core' AND table_name='dim_product'")}
    assert {"pack1_code", "pack1_base_qty"} <= cot
