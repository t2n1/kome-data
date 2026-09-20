"""Test của đợt 1 — nền giao diện.

Không có test nào ở đây chạm CSDL. Chúng đọc file và đọc HTML trả về.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from kome.web.app import create_app

CSS = Path("kome/web/static/kome.css")
TEMPLATES = Path("kome/web/templates")

# Mọi trang mở được mà không cần tham số. Trang hồ sơ khách và trang lỗi
# không nằm đây vì chúng cần dữ liệu hoặc một sự cố để hiện ra.
TRANG = ["/", "/khach-hang", "/bao-cao", "/can-xu-ly", "/health", "/phu-du-lieu"]


def test_css_duoc_phuc_vu(conn, test_db_url):
    """/static/kome.css phải trả về 200 và đúng kiểu nội dung.

    Chặn thảm hoạ: quên mount StaticFiles -> mọi trang mất sạch kiểu dáng
    nhưng vẫn trả 200, nên không test nào khác đỏ.
    """
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/static/kome.css")
    assert r.status_code == 200
    assert "text/css" in r.headers["content-type"]
    assert "--nen" in r.text


def test_moi_trang_deu_noi_toi_css(conn, test_db_url):
    """Chặn thảm hoạ: một trang quên include _chung.html -> trang đó trơ
    trụi trong khi bảy trang kia đẹp, và không ai để ý cho tới khi mở đúng
    trang đó."""
    client = TestClient(create_app(db_url=test_db_url))
    for duong_dan in TRANG:
        r = client.get(duong_dan)
        assert r.status_code == 200, duong_dan
        assert "/static/kome.css" in r.text, duong_dan


def test_khong_ma_mau_nao_ngoai_kome_css():
    """Mọi màu chỉ có MỘT nhà. Chặn thảm hoạ: ai đó gõ thẳng #fff vào một
    template -> trang đó trắng toát ở chế độ tối, trong khi test màu vẫn
    xanh vì nó chỉ soi kome.css."""
    for f in sorted(TEMPLATES.glob("*.html")):
        text = f.read_text(encoding="utf-8")
        assert not re.search(r"#[0-9A-Fa-f]{6}\b", text), f"{f.name} chứa mã màu"


def _bien_khai(khoi: str) -> set[str]:
    """Tên các biến được ĐỊNH NGHĨA trong một khối CSS.

    Chỉ khớp `--x:` (định nghĩa), không khớp `var(--x)` (sử dụng) — nên
    phần thân dưới file, vốn chỉ dùng biến, không lọt vào."""
    return set(re.findall(r"(--[a-z0-9-]+)\s*:", khoi))


def test_moi_bien_mau_deu_co_ban_toi():
    """Chặn thảm hoạ đã từng xảy ra: thêm một biến màu, quên bản tối ->
    chữ sẫm trên nền sẫm ở máy để giao diện tối. Trang vẫn trả 200 nên
    không test nào khác bắt được."""
    css = CSS.read_text(encoding="utf-8")
    moc = "@media (prefers-color-scheme: dark)"
    assert moc in css, "mất khối màu tối"
    sang, toi = css.split(moc, 1)
    thieu = _bien_khai(sang) - _bien_khai(toi)
    assert not thieu, f"thiếu bản tối cho: {sorted(thieu)}"


def test_co_mau_hanh_dong_chinh_va_khong_con_mau_tim():
    """Bảng màu thiết kế dùng đỏ công ty #D62C27 cho hành động chính và
    trạng thái được chọn. Màu tím --chot-* của hệ cũ không còn chỗ đứng;
    để sót lại thì hai hệ màu cùng sống trong một file."""
    css = CSS.read_text(encoding="utf-8")
    assert "--do:#D62C27" in css.replace(" ", "")
    assert "--chot-" not in css
