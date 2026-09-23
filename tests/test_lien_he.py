"""Đợt 7 — danh sách ưu tiên liên hệ (`mart.uu_tien_lien_he`) + nhật ký tiếp xúc."""
from datetime import timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import khach_hang as KH
from kome import lien_he as LH
from kome.tuoi_du_lieu import hom_nay_o_nhat
from kome.web.app import create_app
from tests.test_khach_hang import _ho_so_khach, _mua_deu, _neo


def _nen(conn, batch):
    """Bốn khách, mỗi khách một vùng của thang im lặng (nhịp 7 ngày):
    - L: im 40 ngày (~5,7×) → lâu không mua
    - Q: im 20 ngày (~2,9×) → quá hạn
    - S: im 9 ngày (~1,3×)  → sắp đến hạn (dải MỚI của đợt 7)
    - B: im 2 ngày          → bình thường, KHÔNG vào danh sách
    - X: ※廃業※, im 40 ngày → không bao giờ vào danh sách gọi lại"""
    for ma, ten, im, sale in (("L0011", "Lau", 40, "0104"), ("Q0012", "Qua", 20, "0104"),
                              ("S0013", "Sap", 9, "0102"), ("B0014", "Binh", 2, "0104"),
                              ("X0015", "※廃業※Dong", 40, "0104")):
        _ho_so_khach(conn, batch, ma, ten, salesperson_code=sale)
        _mua_deu(conn, batch, ma, nhip=7, so_lan=5, ngung_truoc=im)
    _neo(conn, batch)


def _ly_do(conn, **kw):
    ds = LH.danh_sach(conn, hom_nay_o_nhat(), **kw)
    return {t.ma: t.ly_do for c in ds.cot for t in c.the}, ds


def test_ba_ly_do_va_loai_khach_binh_thuong_va_da_dong_cua(conn, batch):
    _nen(conn, batch)
    ly_do, _ = _ly_do(conn)
    assert ly_do == {"L0011": "lau_khong_mua", "Q0012": "qua_han", "S0013": "sap_den_han"}


def test_hai_cot_dau_DUNG_BANG_nhom_viec_im(conn, batch):
    """[CRITICAL] "Khách đang rời đi" chỉ có MỘT định nghĩa: nhóm 'im' của
    mart.khach_nhom_viec. /lien-he mà nói khác /khach-hang?nhom=im là hai màn
    cãi nhau về cùng một khách."""
    _nen(conn, batch)
    ly_do, _ = _ly_do(conn)
    roi_di = {m for m, l in ly_do.items() if l in ("lau_khong_mua", "qua_han")}
    im = {r[0] for r in conn.execute(
        "SELECT customer_code FROM mart.khach_nhom_viec WHERE nhom = 'im'").fetchall()}
    assert roi_di == im
    assert roi_di == {k.ma for k in KH.can_xu_ly(conn)}


def test_loc_theo_sale(conn, batch):
    _nen(conn, batch)
    ly_do, _ = _ly_do(conn, sale="0102")
    assert set(ly_do) == {"S0013"}


def test_ghi_xong_khach_tam_an_va_van_hien_o_khoi_da_lien_he(conn, batch):
    """[IMPORTANT] Không ẩn thì khách hiện lại y nguyên hôm sau như chưa ai
    gọi; ẩn mà không nói ra thì khách biến mất lặng lẽ."""
    _nen(conn, batch)
    LH.ghi(conn, "L0011", None, "goi", "binh", "Khách hẹn tuần sau")
    conn.commit()
    ly_do, ds = _ly_do(conn)
    assert "L0011" not in ly_do
    assert [t.ma for t in ds.da_lien_he] == ["L0011"]
    assert ds.da_lien_he[0].cuoi.noi_dung == "Khách hẹn tuần sau"


def test_hen_lai_hom_nay_thi_HIEN_hen_mai_thi_AN(conn, batch):
    _nen(conn, batch)
    hom_nay = hom_nay_o_nhat()
    LH.ghi(conn, "L0011", None, "goi", "tot", "gọi lại hôm nay", hom_nay.isoformat())
    LH.ghi(conn, "Q0012", None, "chat", "tot", "gọi lại mai",
           (hom_nay + timedelta(days=1)).isoformat())
    conn.commit()
    ly_do, ds = _ly_do(conn)
    assert "L0011" in ly_do and "Q0012" not in ly_do
    assert [n.ma_khach for n in LH.hen_goi_lai(conn, hom_nay)] == ["L0011"]


def test_hen_cu_da_tra_bang_lan_ghi_sau_thi_khong_con_hen(conn, batch):
    """Chỉ lời hẹn của lần tiếp xúc MỚI NHẤT còn hiệu lực."""
    _nen(conn, batch)
    hom_nay = hom_nay_o_nhat()
    LH.ghi(conn, "L0011", None, "goi", "binh", "hẹn", (hom_nay - timedelta(days=2)).isoformat())
    conn.execute("UPDATE app.nhat_ky_tiep_xuc SET thoi_diem = now() - interval '3 days'")
    LH.ghi(conn, "L0011", None, "goi", "tot", "đã gọi lại")
    conn.commit()
    assert LH.hen_goi_lai(conn, hom_nay) == []


def test_ghi_kiem_bieu_mau(conn, batch):
    _nen(conn, batch)
    for bad in [("fax", "tot", "x", ""), ("goi", "hay", "x", ""), ("goi", "tot", "   ", ""),
                ("goi", "tot", "x", "31/12")]:
        with pytest.raises(LH.LoiNhap):
            LH.ghi(conn, "L0011", None, *bad)
    with pytest.raises(LH.LoiNhap):
        LH.ghi(conn, "KHONG-CO", None, "goi", "tot", "x")


def test_nhat_ky_chi_them_kome_app_khong_sua_khong_xoa_duoc(conn):
    """[CRITICAL] "Chỉ thêm" là ràng buộc của CSDL: kome_app mặc định có
    UPDATE/DELETE trên mọi bảng app (009), 030 rút lại ở đúng bảng này."""
    r = conn.execute(
        """SELECT has_table_privilege('kome_app', 'app.nhat_ky_tiep_xuc', 'INSERT'),
                  has_table_privilege('kome_app', 'app.nhat_ky_tiep_xuc', 'SELECT'),
                  has_table_privilege('kome_app', 'app.nhat_ky_tiep_xuc', 'UPDATE'),
                  has_table_privilege('kome_app', 'app.nhat_ky_tiep_xuc', 'DELETE'),
                  has_table_privilege('kome_ingest', 'mart.uu_tien_lien_he', 'SELECT'),
                  has_table_privilege('kome_app', 'mart.uu_tien_lien_he', 'SELECT')""").fetchone()
    assert r == (True, True, False, False, True, True)


def test_trang_lien_he_dung_3_truy_van(conn, batch, monkeypatch):
    _nen(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    hn = hom_nay_o_nhat()
    LH.danh_sach(conn, hn)
    LH.hoat_dong_gan_day(conn)
    LH.hen_goi_lai(conn, hn)
    assert dem["n"] == 3


def test_ho_so_mang_nhat_ky(conn, batch):
    _nen(conn, batch)
    LH.ghi(conn, "Q0012", None, "ghe", "xau", "Khách phàn nàn giao trễ")
    conn.commit()
    h = KH.ho_so(conn, "Q0012")
    assert [n.noi_dung for n in h.nhat_ky] == ["Khách phàn nàn giao trễ"]
    assert h.nhat_ky[0].nhan_kieu == "Ghé thăm" and h.nhat_ky[0].nhan_ket_qua == "Cần theo dõi"


# ---- Web -------------------------------------------------------------------

@pytest.fixture
def client(conn, test_db_url):
    return TestClient(create_app(db_url=test_db_url), follow_redirects=False)


NGUON = Path(__file__).resolve().parents[1] / "giao_dien" / "src"


def test_trang_lien_he_ve_ba_cot(client, conn, batch):
    """Giai đoạn 3: màn là React — ba cột lý do (nhãn từ LH.LY_DO) và các thẻ
    đến từ /api/lien-he; khách bình thường (B) và khách ※廃業※ (X) không nằm
    trong cột nào; hai khối "Hoạt động gần đây" / "Hẹn gọi lại hôm nay" có
    trong mã giao diện."""
    _nen(conn, batch)
    r = client.get("/lien-he")
    assert r.status_code == 200 and 'id="goc"' in r.text
    d = client.get("/api/lien-he").json()
    nhan = [c["nhan"] for c in d["ds"]["cot"]]
    for n in ("Lâu không mua", "Quá hạn mua lại", "Sắp đến hạn"):
        assert n in nhan, n
    the = {t["ten"] for c in d["ds"]["cot"] for t in c["the"]}
    assert "Sap" in the and "Binh" not in the and "※廃業※Dong" not in the
    assert "hoat_dong" in d and "hen" in d
    src = (NGUON / "lien_he" / "LienHe.tsx").read_text(encoding="utf-8")
    assert "<h2>Hoạt động gần đây</h2>" in src
    assert '<div className="nhan">Hẹn gọi lại hôm nay</div>' in src
    # Nhãn cột đọc từ API (một định nghĩa ở kome/lien_he.py), không chép tay.
    assert "{c.nhan}" in src and "Lâu không mua" not in src


def test_ghi_qua_web_roi_quay_ve_dung_trang(client, conn, batch):
    _nen(conn, batch)
    r = client.post("/khach-hang/L0011/tiep-xuc",
                    data={"kieu": "goi", "ket_qua": "tot", "noi_dung": "Đặt 3 thùng",
                          "hen_lai": "", "tiep": "/lien-he?tat_ca=1"})
    assert r.status_code == 303 and r.headers["location"] == "/lien-he?tat_ca=1"
    # Hồ sơ 360° là React (giai đoạn 2) — đọc nhật ký qua API của nó.
    nk = client.get("/api/khach-hang/L0011").json()["nhat_ky"]
    assert "Đặt 3 thùng" in [n["noi_dung"] for n in nk]


def test_tiep_ngoai_he_thong_bi_loc(client, conn, batch):
    """[CRITICAL] `tiep` đi qua bao_mat.duong_dan_an_toan — nút Thêm không được
    thành bàn đạp chuyển hướng sang site lạ."""
    _nen(conn, batch)
    for la in ("https://site-gia.example", "//site-gia.example", "/\\site-gia.example"):
        r = client.post("/khach-hang/L0011/tiep-xuc",
                        data={"kieu": "goi", "ket_qua": "tot", "noi_dung": "x", "tiep": la})
        assert r.headers["location"] == "/", la


def test_bieu_mau_sai_quay_ve_kem_loi_doc_duoc(client, conn, batch):
    from pathlib import Path
    _nen(conn, batch)
    r = client.post("/khach-hang/L0011/tiep-xuc",
                    data={"kieu": "goi", "ket_qua": "tot", "noi_dung": " ",
                          "tiep": "/khach-hang/L0011#nhat-ky"})
    loc = r.headers["location"]
    assert loc.startswith("/khach-hang/L0011?loi_tx=") and loc.endswith("#nhat-ky")
    assert "Ghi%20l%E1%BA%A1i%20n%E1%BB%99i%20dung" in loc or "Ghi lại nội dung" in loc
    assert client.get(loc.split("#")[0]).status_code == 200
    # Hồ sơ React đọc ?loi_tx= và hiện câu lỗi (giai đoạn 2).
    assert 'get("loi_tx")' in Path("giao_dien/src/khach/HoSo.tsx").read_text(encoding="utf-8")
    assert conn.execute("SELECT count(*) FROM app.nhat_ky_tiep_xuc").fetchone()[0] == 0


def test_api_ghi_tiep_xuc_chi_nhan_json_va_bao_loi_doc_duoc(client, conn, batch):
    """POST /api/khach-hang/{mã}/tiep-xuc (form của hồ sơ React): chỉ nhận
    application/json (một form trang lạ không gửi được kiểu đó nếu không qua
    preflight CORS), lỗi nhập trả 400 kèm câu tiếng Việt, không ghi dòng nào."""
    _nen(conn, batch)
    r = client.post("/api/khach-hang/L0011/tiep-xuc",
                    data={"kieu": "goi", "ket_qua": "tot", "noi_dung": "x"})
    assert r.status_code == 415
    r = client.post("/api/khach-hang/L0011/tiep-xuc", json={"kieu": "goi", "ket_qua": "tot", "noi_dung": " "})
    assert r.status_code == 400 and "Ghi lại nội dung" in r.json()["loi"]
    assert conn.execute("SELECT count(*) FROM app.nhat_ky_tiep_xuc").fetchone()[0] == 0
    r = client.post("/api/khach-hang/L0011/tiep-xuc", json={"kieu": "ghe", "ket_qua": "binh", "noi_dung": "Ghé cửa hàng"})
    assert r.status_code == 200
    assert client.get("/api/khach-hang/L0011").json()["nhat_ky"][0]["noi_dung"] == "Ghé cửa hàng"


def test_can_xu_ly_chuyen_ve_lien_he(client):
    assert client.get("/can-xu-ly").headers["location"] == "/lien-he"
    assert client.get("/can-xu-ly?tat_ca=1").headers["location"] == "/lien-he?tat_ca=1"
    assert client.get("/can-xu-ly").status_code == 301


def test_sidebar_tro_toi_lien_he(client, conn):
    """Giai đoạn 3: /lien-he là React — thanh bên React có mục "Cần liên hệ"
    trỏ /lien-he (được đánh dấu khi đang mở: Nav.tsx đặt aria-current theo
    mucDangMo), và không nơi nào còn trỏ /can-xu-ly — cả thanh bên Jinja của
    các trang còn lại."""
    assert client.get("/lien-he").status_code == 200
    muc = (NGUON / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert '{ ma: "crm", nhan: "Cần liên hệ", url: "/lien-he", icon: "crm" }' in muc
    assert "/can-xu-ly" not in muc
    assert 'aria-current={m.ma === dangMo ? "page" : undefined}' in         (NGUON / "khung" / "Nav.tsx").read_text(encoding="utf-8")
    t = client.get("/san-pham").text
    assert 'href="/lien-he"' in t and 'href="/can-xu-ly"' not in t
