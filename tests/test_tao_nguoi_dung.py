"""Script quản lý tài khoản. Chạy bằng tay, in ra thứ cần biết.

Bất biến quan trọng nhất: **script không bao giờ in mật khẩu, hash hay salt**
— màn hình của người quản trị cũng là một nơi dữ liệu rò ra được.
"""
import pytest

from kome.web import nguoi_dung as ND
from scripts.tao_nguoi_dung import chay

MK = "mat-khau-cua-an-2026"


def _doc(*mat_khau):
    """Giả lập getpass: trả lần lượt các mật khẩu được đưa vào."""
    it = iter(mat_khau)
    return lambda: next(it)


def test_them_tai_khoan_va_dang_nhap_duoc(conn, capsys):
    assert chay(["them", "an", "--sale", "0104"], conn, _doc(MK, MK)) == 0
    conn.commit()
    n = ND.kiem_tra(conn, "an", MK)
    assert n is not None and n.salesperson_code == "0104"
    assert n.duoc_vao_kho_du_lieu is False      # không đưa --kho-du-lieu


def test_co_kho_du_lieu_thi_cap_quyen(conn):
    chay(["them", "an", "--kho-du-lieu"], conn, _doc(MK, MK))
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is True


def test_go_lai_lan_hai_khong_khop_thi_khong_tao_gi(conn):
    """Gõ nhầm mật khẩu lúc tạo tài khoản = một người không đăng nhập được và
    không ai biết vì sao. Hỏi hai lần, lệch thì dừng."""
    assert chay(["them", "an"], conn, _doc(MK, "go-nham-roi")) != 0
    conn.rollback()
    assert ND.liet_ke(conn) == []


def test_mat_khau_qua_ngan_bi_tu_choi(conn):
    assert chay(["them", "an"], conn, _doc("ngan", "ngan")) != 0
    conn.rollback()
    assert ND.liet_ke(conn) == []


def test_liet_ke_khong_in_hash_khong_in_salt_khong_in_mat_khau(conn, capsys):
    """[CRITICAL] Màn hình của người quản trị cũng là chỗ dữ liệu rò ra."""
    ND.tao(conn, "an", MK, salesperson_code="0104", kho_du_lieu=True)
    conn.commit()
    assert chay([], conn, _doc()) == 0
    ra = capsys.readouterr().out
    assert "an" in ra and "0104" in ra
    assert MK not in ra
    for cam in ("mat_khau_hash", "mat_khau_salt", "\\x", "b'"):
        assert cam not in ra


def test_doi_mat_khau(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert chay(["doi-mat-khau", "an"], conn, _doc("mat-khau-moi-2026", "mat-khau-moi-2026")) == 0
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK) is None
    assert ND.kiem_tra(conn, "an", "mat-khau-moi-2026") is not None


def test_quyen_bat_va_tat(conn):
    ND.tao(conn, "an", MK)
    conn.commit()
    assert chay(["quyen", "an", "--kho-du-lieu"], conn, _doc()) == 0
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is True
    assert chay(["quyen", "an", "--bo-kho-du-lieu"], conn, _doc()) == 0
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is False


def test_khong_co_tai_khoan_do_thi_bao_ro_chu_khong_im_lang(conn, capsys):
    """Mã thoát khác 0 VÀ nói ra tên không tìm thấy. Im lặng rồi thoát 0 là
    người quản trị tưởng đã đổi xong mật khẩu cho một người không tồn tại."""
    assert chay(["doi-mat-khau", "khong-co-ai"], conn, _doc(MK, MK)) != 0
    assert "khong-co-ai" in capsys.readouterr().out
    assert chay(["quyen", "khong-co-ai", "--kho-du-lieu"], conn, _doc()) != 0
    assert "khong-co-ai" in capsys.readouterr().out


def test_ma_sale_khong_co_that_bao_loi_de_hieu(conn, capsys):
    assert chay(["them", "an", "--sale", "9999"], conn, _doc(MK, MK)) != 0
    conn.rollback()
    ra = capsys.readouterr().out
    assert "9999" in ra


def test_hai_co_quyen_mau_thuan_thi_bao_loi_khong_doi_gi(conn):
    """Vừa --kho-du-lieu vừa --bo-kho-du-lieu là dấu hiệu người gõ không chắc
    mình muốn gì. Không được im lặng chọn nhánh cấp quyền — đó là nhánh nguy
    hiểm hơn (mở đường vào nút Hoàn tác)."""
    ND.tao(conn, "an", MK)
    conn.commit()
    assert chay(["quyen", "an", "--kho-du-lieu", "--bo-kho-du-lieu"], conn, _doc()) != 0
    conn.commit()
    assert ND.kiem_tra(conn, "an", MK).duoc_vao_kho_du_lieu is False


def test_sale_thieu_gia_tri_bao_loi_khong_tao_gi(conn):
    """Quên gõ mã sau --sale không được âm thầm tạo tài khoản không gán sale."""
    assert chay(["them", "an", "--sale"], conn, _doc(MK, MK)) != 0
    conn.rollback()
    assert ND.liet_ke(conn) == []
