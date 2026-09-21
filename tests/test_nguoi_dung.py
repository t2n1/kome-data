"""Tài khoản đăng nhập: băm mật khẩu, xác thực, và quyền vào Kho dữ liệu.

Mọi test ở đây bảo vệ một câu: **mật khẩu không bao giờ nằm ở dạng đọc được
trong CSDL**, và **sai mật khẩu thì không vào được**.
"""
import pytest
import psycopg

from kome.web import nguoi_dung as ND

MK = "mat-khau-cua-an-2026"


def test_tao_roi_dang_nhap_duoc(conn):
    ND.tao(conn, "an", MK, salesperson_code="0104", kho_du_lieu=True)
    conn.commit()
    n = ND.kiem_tra(conn, "an", MK)
    assert n is not None
    assert n.ten_dang_nhap == "an"
    assert n.salesperson_code == "0104"
    assert n.duoc_vao_kho_du_lieu is True
    # Tên người lấy từ core.dim_salesperson — trang khách hàng cần nó để nói
    # rõ "đang lọc theo ai", chứ không phải khoe một mã bốn chữ số.
    assert n.ten_sale == "TRAN THI LAN THANH"


def test_sai_mat_khau_va_sai_ten_deu_tra_ve_none(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert ND.kiem_tra(conn, "an", "doan-bua-mot-cai") is None
    assert ND.kiem_tra(conn, "khong-co-nguoi-nay", MK) is None
    assert ND.kiem_tra(conn, "an", "") is None


def test_mat_khau_khong_bao_gio_nam_trong_csdl_o_dang_doc_duoc(conn):
    """[CRITICAL] Ai đọc được CSDL (bản sao lưu, công cụ BI, một câu SELECT lỡ
    tay) cũng không được đọc ra mật khẩu của nhân viên."""
    ND.tao(conn, "an", MK)
    conn.commit()
    h, s = conn.execute(
        "SELECT mat_khau_hash, mat_khau_salt FROM app.nguoi_dung WHERE ten_dang_nhap='an'"
    ).fetchone()
    assert MK.encode() not in bytes(h)
    assert MK.encode() not in bytes(s)
    assert len(bytes(h)) == ND.DAI_HASH and len(bytes(s)) == ND.DAI_SALT


def test_hai_nguoi_cung_mat_khau_van_ra_hai_hash_khac_nhau(conn):
    """Salt riêng từng người. Không có nó thì nhìn bảng là biết ngay ai đang
    dùng chung mật khẩu với ai — và bẻ được một cái là bẻ được cả nhóm."""
    ND.tao(conn, "an", MK)
    ND.tao(conn, "binh", MK)
    conn.commit()
    rows = conn.execute("SELECT mat_khau_hash FROM app.nguoi_dung ORDER BY id").fetchall()
    assert rows[0][0] != rows[1][0]


def test_doi_mat_khau_thi_mat_khau_cu_het_dung_duoc(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert ND.doi_mat_khau(conn, "an", "mat-khau-moi-cua-an") is True
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK) is None
    assert ND.kiem_tra(conn, "an", "mat-khau-moi-cua-an") is not None
    assert ND.doi_mat_khau(conn, "khong-co-ai", "abc") is False


def test_dat_quyen_bat_va_tat_duoc(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is False   # mặc định
    assert ND.dat_quyen(conn, "an", True) is True
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is True
    ND.dat_quyen(conn, "an", False)
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is False
    assert ND.dat_quyen(conn, "khong-co-ai", True) is False


def test_quyen_vao_kho_du_lieu_mac_dinh_la_khong(conn):
    """[IMPORTANT] Màn Kho dữ liệu có nút xoá được cả tháng doanh thu. Quyền
    đó phải được cấp tường minh, không phải thứ ai cũng có vì người tạo tài
    khoản quên đặt."""
    ND.tao(conn, "an", MK)
    conn.commit()
    assert conn.execute(
        "SELECT duoc_vao_kho_du_lieu FROM app.nguoi_dung WHERE ten_dang_nhap='an'"
    ).fetchone()[0] is False


def test_trung_ten_dang_nhap_bi_tu_choi(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    with pytest.raises(psycopg.errors.UniqueViolation):
        ND.tao(conn, "an", "mat-khau-khac-han")
    conn.rollback()


def test_ma_sale_khong_co_that_bi_tu_choi(conn):
    """Khoá ngoại tới core.dim_salesperson: gõ nhầm mã sale phải nổ NGAY lúc
    tạo tài khoản, không phải lặng lẽ tạo một người lọc ra 0 khách."""
    with pytest.raises(psycopg.errors.ForeignKeyViolation):
        ND.tao(conn, "an", MK, salesperson_code="9999")
    conn.rollback()


def test_theo_id_tra_ve_dung_nguoi_va_none_khi_da_xoa(conn):
    """theo_id là thứ middleware gọi MỖI LƯỢT: vé còn hạn nhưng tài khoản đã
    bị xoá thì phải trả None, để người đó bị đá về trang đăng nhập ngay."""
    ma = ND.tao(conn, "an", MK, kho_du_lieu=True)
    conn.commit()
    n = ND.theo_id(conn, ma)
    assert n is not None and n.ten_dang_nhap == "an" and n.duoc_vao_kho_du_lieu
    conn.execute("DELETE FROM app.nguoi_dung WHERE id = %s", (ma,))
    conn.commit()
    assert ND.theo_id(conn, ma) is None
    assert ND.theo_id(conn, 999_999) is None


def test_liet_ke_khong_tra_ve_hash_hay_salt(conn):
    """Lệnh liệt kê của scripts/tao_nguoi_dung.py in thẳng thứ hàm này trả
    về. Không có hash/salt trong dataclass thì không có đường nào in nhầm."""
    ND.tao(conn, "an", MK, salesperson_code="0104")
    ND.tao(conn, "binh", MK, kho_du_lieu=True)
    conn.commit()
    ds = ND.liet_ke(conn)
    assert [n.ten_dang_nhap for n in ds] == ["an", "binh"]
    assert not any(hasattr(n, t) for n in ds for t in ("mat_khau_hash", "mat_khau_salt"))
