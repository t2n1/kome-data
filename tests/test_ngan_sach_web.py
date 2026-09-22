"""Đợt 5a Task 3 — cổng quyền và màn nhập /ngan-sach.

Đây là đường GHI đầu tiên của app ngoài luồng nạp OBC, nên phần lớn test ở
đây canh cái CỬA chứ không canh con số.
"""
import re
from datetime import date

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome.web.app import create_app

MK = "mat-khau-cua-an-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"


@pytest.fixture
def khach(monkeypatch, test_db_url, conn):
    """Dựng app CÓ cổng đăng nhập và một tài khoản. `ngan_sach` là cờ mới."""
    from kome.web import nguoi_dung as ND

    def _tao(ngan_sach: bool = True):
        monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
        monkeypatch.delenv("VERCEL", raising=False)
        # `khach()` có thể được gọi HAI LẦN trong cùng một test (một lần cho
        # mỗi giá trị của `ngan_sach`) — tạo tài khoản "an" lần hai sẽ ném
        # UniqueViolation. `dat_quyen` (Task 3) trả False khi tài khoản chưa
        # có, nên nhánh đó vẫn tạo mới; nếu tài khoản đã có thì chỉ CẬP NHẬT
        # cờ, không tạo trùng.
        if not ND.dat_quyen(conn, "an", ngan_sach=ngan_sach):
            ND.tao(conn, "an", MK, kho_du_lieu=False, ngan_sach=ngan_sach)
        conn.commit()
        c = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
        c.post("/dang-nhap", data={"ten": "an", "mat_khau": MK})
        return c
    return _tao


def _ban(conn, batch, ngay: date = date(2026, 5, 11), sale: str = "0104"):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, sale))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{sale}", "line_seq": 1, "sales_date": ngay,
        "customer_code": "000000009292", "product_code": "XT07", "pack_code": "02",
        "case_qty": 1, "qty": 6, "unit_price": 5250, "unit_cost": 3210,
        "amount": 110_000, "tax_amount": 10_000, "cost": 70_000,
        "gross_profit": 30_000, "paid_amount": 0, "salesperson_code": sale,
        "batch_id": b,
    }]), ngay, b)
    conn.commit()


# ---- cổng quyền -----------------------------------------------------------

def test_khong_co_co_thi_403_o_CA_GET_lan_POST(khach, conn, batch):
    """[CRITICAL] Gác mỗi GET là để nguyên cửa ghi mở toang cho ai biết gõ
    `curl`. Cửa ghi phải bị chặn, và phải chặn TRƯỚC khi ghi được dòng nào."""
    _ban(conn, batch)
    c = khach(ngan_sach=False)
    assert c.get("/ngan-sach").status_code == 403
    r = c.post("/ngan-sach", data={"ky": "2026", "o-0104-2026-05": "9000000"})
    assert r.status_code == 403
    assert conn.execute("SELECT count(*) FROM app.ngan_sach").fetchone()[0] == 0


def test_403_giai_thich_chu_khong_chuyen_huong_im_lang(khach, conn, batch):
    """Người gõ thẳng địa chỉ cần biết vì sao mình không vào được, không phải
    tự hỏi trang có hỏng không."""
    _ban(conn, batch)
    r = khach(ngan_sach=False).get("/ngan-sach")
    assert r.status_code == 403
    assert "quyền" in r.text and "Ngân sách" in r.text


def test_thu_hoi_co_AN_NGAY_khong_doi_het_ve(khach, conn, batch):
    """[CRITICAL] Vé sống 12 giờ. Cờ nằm trong vé thì thu hồi quyền trên màn
    có nút ghi phải đợi tới ngày mai. Cùng bất biến đã ghi cho
    duoc_vao_kho_du_lieu: TRA app.nguoi_dung MỖI LƯỢT GỌI."""
    _ban(conn, batch)
    c = khach(ngan_sach=True)
    assert c.get("/ngan-sach").status_code == 200
    conn.execute("UPDATE app.nguoi_dung SET duoc_sua_ngan_sach = false")
    conn.commit()
    assert c.get("/ngan-sach").status_code == 403


def test_muc_ngan_sach_an_khoi_thanh_dieu_huong_khi_khong_co_co(khach, conn, batch):
    """Mời người ta bấm vào một thứ sẽ từ chối họ thì tệ hơn là không hiện."""
    _ban(conn, batch)
    assert 'href="/ngan-sach"' not in khach(ngan_sach=False).get("/bao-cao").text
    assert 'href="/ngan-sach"' in khach(ngan_sach=True).get("/bao-cao").text


def test_khong_co_cong_dang_nhap_thi_vao_duoc(conn, batch, test_db_url):
    """Máy trong công ty để trống KOME_SESSION_SECRET => không có cổng và
    không có phân quyền. Đây là CẠM BẪY đã ghi trong CLAUDE.md, không phải lỗ
    mới — nhưng test phải khẳng định đúng hành vi đó, vì nếu trang bỗng trả
    403 khi không có cổng thì máy trong công ty mất hẳn màn nhập."""
    _ban(conn, batch)
    c = TestClient(create_app(db_url=test_db_url))
    assert c.get("/ngan-sach").status_code == 200


# ---- màn nhập -------------------------------------------------------------

def test_luu_roi_tai_lai_thi_thay_dung_so_vua_nhap(khach, conn, batch):
    _ban(conn, batch)
    c = khach()
    r = c.post("/ngan-sach", data={"ky": "2026", "o-0104-2026-05": "9.000.000"})
    assert r.status_code == 303
    assert conn.execute(
        "SELECT muc_tieu FROM app.ngan_sach").fetchone()[0] == 9_000_000
    assert 'value="9.000.000"' in c.get("/ngan-sach?ky=2026").text


def test_mot_o_sai_thi_KHONG_ghi_o_nao(khach, conn, batch):
    """[CRITICAL] Ghi một nửa rồi báo lỗi là để người ta không biết nửa nào đã
    vào. Và biểu mẫu phải hiện lại ĐÚNG những gì họ vừa gõ — bắt gõ lại 60 ô
    vì một ô sai là cách chắc chắn để không ai dùng màn này lần thứ hai."""
    _ban(conn, batch)
    c = khach()
    r = c.post("/ngan-sach", data={"ky": "2026",
                                   "o-0104-2026-05": "9000000",
                                   "o-0105-2026-05": "chin trieu"})
    assert r.status_code == 400
    assert conn.execute("SELECT count(*) FROM app.ngan_sach").fetchone()[0] == 0
    assert "chin trieu" in r.text, "phải hiện lại đúng chữ người ta vừa gõ"
    assert 'value="9000000"' in r.text


@pytest.mark.parametrize("form", [
    pytest.param({"ky": "2026", "o-": "9000000"}, id="ten_o_meo"),
    pytest.param({"ky": "abc", "o-0104-2026-05": "9000000"}, id="ky_meo"),
])
def test_bieu_mau_meo_khong_no_500_tran_va_khong_ghi_dong_nao(khach, conn, batch, form):
    """[Vòng sửa 1, việc 1] Trước bản sửa, `ky = int(form.get("ky") or 0)`
    và `khoa.split("-", 1)` nằm NGOÀI mọi `try` trong `luu_ngan_sach` — HAI
    đường ném ValueError ra thẳng ngoài: một tên ô méo (`o-` không kèm gì)
    VÀ `ky` không ép được sang int (`ky=abc`). Cả hai ra thẳng "Internal
    Server Error" trần của Starlette — trên đúng màn GHI, nơi mất nửa chừng
    dễ bị hiểu nhầm thành mất dữ liệu. Route giờ phải hoặc trả về đúng
    trang lỗi tiếng Việt của app (`_loi`, 500) hoặc 400 kèm biểu mẫu —
    KHÔNG BAO GIỜ vết ngăn xếp tiếng Anh trần — và không được ghi dòng nào
    trong cả hai trường hợp.

    [Vòng sửa 2] Ca `ky_meo` là ca MỚI. Bản test vòng 1 chỉ canh
    `ten_o_meo` — đường đó giờ bị chặn bằng một phép kiểm độ dài tường minh
    (`len(phan) != 3`), không còn dựa vào ngoại lệ nào cả. Nếu sau này ai
    đó đưa RIÊNG dòng `ky = int(form.get("ky") or 0)` ra khỏi `try` một lần
    nữa, ca `ten_o_meo` vẫn xanh — chỉ `ky_meo` mới bắt được hồi quy đó."""
    _ban(conn, batch)
    c = khach()
    r = c.post("/ngan-sach", data=form)
    assert r.status_code in (400, 500), \
        f"phải là 400 (biểu mẫu) hoặc 500 (trang lỗi tiếng Việt), thấy {r.status_code}"
    assert "Internal Server Error" not in r.text
    assert conn.execute("SELECT count(*) FROM app.ngan_sach").fetchone()[0] == 0


def test_o_chua_dat_hien_TRONG_khong_hien_0(khach, conn, batch):
    """[CRITICAL] Hiện 0 cho thứ chưa biết là nói một điều sai bằng con số."""
    _ban(conn, batch)
    html = khach().get("/ngan-sach?ky=2026").text
    o = re.findall(r'name="o-0104-2026-05"[^>]*value="([^"]*)"', html)
    assert o == [""], f"ô chưa đặt phải trống, thấy {o}"


def test_ky_chua_co_doanh_thu_van_co_trong_dai_chip(khach, conn, batch):
    _ban(conn, batch)
    assert "ky=2027" in khach().get("/ngan-sach").text


def test_trang_ngan_sach_khong_qua_5_truy_van(khach, conn, batch, monkeypatch):
    """[IMPORTANT] Trang chậm dần từng đợt là cách nó chết mà không ai thấy
    ngày nào nó chết.

    NĂM chứ không phải bốn: `bang_nhap()` được cấp ngân sách 4 lượt hỏi, cộng
    một lượt của middleware tra người đăng nhập (`nguoi_dung.theo_id`) — lượt
    đó là giá của cổng quyền, có ở MỌI trang, và nó phải tra CSDL mỗi lượt
    gọi chứ không đọc từ vé (bất biến của đợt 3).

    Đo tại tầng psycopg chứ không bọc `conn` của fixture: route mở kết nối
    riêng của chính nó qua open_app_conn(), nên `conn` của fixture không hề
    được route dùng tới."""
    _ban(conn, batch)
    c = khach()
    import psycopg
    dem = {"n": 0}
    that = psycopg.Connection.execute

    def demo(self, *a, **k):
        dem["n"] += 1
        return that(self, *a, **k)

    monkeypatch.setattr(psycopg.Connection, "execute", demo)
    c.get("/ngan-sach?ky=2026")
    monkeypatch.undo()
    # Trừ lượt tra người đăng nhập của middleware (1 câu, theo_id).
    assert dem["n"] <= 5, f"/ngan-sach chạy {dem['n']} truy vấn"
