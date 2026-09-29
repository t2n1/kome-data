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


def test_trang_lien_he_dung_4_truy_van(conn, batch, monkeypatch):
    _nen(conn, batch)
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    hn = hom_nay_o_nhat()
    ds = LH.danh_sach(conn, hn)
    LH.hoat_dong_gan_day(conn)
    LH.hen_goi_lai(conn, hn)
    LH.goi_y_va_nhan_vien(conn, [t.ma for c in ds.cot for t in c.the])
    assert dem["n"] == 4


def test_goi_y_la_hang_khach_da_mua_deu_xep_theo_so_lan(conn, batch):
    """"Nên chào" = mã CHÍNH khách đó mua ≥ 3 lần, nhiều lần nhất trước; mã mua
    < 3 lần (chưa có nhịp) không được gợi ý."""
    from tests.test_khach_hang import HOM_NAY, _mua
    _nen(conn, batch)
    for ngay_truoc in (60, 50):   # chỉ 2 lần -> không có nhịp
        _mua(conn, batch, "L0011", HOM_NAY - timedelta(days=ngay_truoc), hang="PIT01")
    gy = LH.goi_y_va_nhan_vien(conn, ["L0011", "Q0012", "X0015"])
    ma_l = [g["ma"] for g in gy["goi_y"]["L0011"]]
    assert ma_l == ["XT07"]
    assert all(g["so_lan"] >= 3 for g in gy["goi_y"]["L0011"])
    # Khách ※廃業※ không bao giờ được gợi ý.
    assert "X0015" not in gy["goi_y"]
    assert {n["ma"] for n in gy["nhan_vien"]} >= {"0104", "0102"}


def test_goi_y_toi_da_ba_ma_moi_khach(conn, batch):
    _nen(conn, batch)
    gy = LH.goi_y_va_nhan_vien(conn, ["L0011", "Q0012", "S0013"], so_ma=1)
    assert all(len(v) == 1 for v in gy["goi_y"].values())
    assert set(gy["goi_y"]) == {"L0011", "Q0012", "S0013"}


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
    assert "/can-xu-ly" not in (NGUON / "khung" / "Nav.tsx").read_text(encoding="utf-8")


# ---- Đợt 2 (063): ghi kèm thẻ `@` + giá khách kể trong MỘT giao dịch ---------------------------------

def _the(noi_dung, loai, khoa, nhan):
    """Thẻ đúng như giao diện gửi: vị trí của `nhan` trong `noi_dung`."""
    return {"loai": loai, "khoa": khoa, "vi_tri_dau": noi_dung.index(nhan), "do_dai": len(nhan)}


CAU = "Khách nói @THAK bán @Basa rẻ hơn mình"


def _nen_nhac(conn, batch):
    from tests.test_mart_doi_thu import _hang
    _ho_so_khach(conn, batch, "K0001", "Quán một")
    _hang(conn, batch)          # NT01


def _so_dong_tx(conn):
    return conn.execute("SELECT count(*) FROM app.nhat_ky_tiep_xuc").fetchone()[0]


def test_ghi_tra_id_dong_vua_them(conn, batch):
    _nen(conn, batch)
    i = LH.ghi(conn, "L0011", None, "goi", "tot", "x")
    assert i == conn.execute("SELECT max(id) FROM app.nhat_ky_tiep_xuc").fetchone()[0]


def test_ghi_kem_nhac_ghi_the_va_gia_khach_ke(conn, batch):
    _nen_nhac(conn, batch)
    nhac = [_the(CAU, "doi_thu", "THAK", "@THAK"), _the(CAU, "nhom", "ma:NT01", "@Basa")]
    gia = [{"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": "1,200", "don_vi_gia": "kg"}]
    r = LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac, gia)
    conn.commit()
    assert r["canh_bao"] == [] and isinstance(r["id"], int)
    assert conn.execute("SELECT noi_dung FROM app.nhat_ky_tiep_xuc WHERE id=%s", (r["id"],)).fetchone()[0] == CAU
    assert conn.execute("SELECT loai, khoa, vi_tri_dau, do_dai FROM app.tiep_xuc_nhac WHERE tiep_xuc_id=%s ORDER BY vi_tri_dau",
                        (r["id"],)).fetchall() == [("doi_thu", "THAK", 10, 5), ("nhom", "ma:NT01", 20, 5)]
    g = conn.execute("""SELECT ma_doi_thu, ma_hang_dt, loai_nguon, customer_code, tiep_xuc_id, nhom_khoa, gia_goc, don_vi_gia,
                               kg_moi_don_vi_gia, thue, gom_ship, ten_goc, trang_thai
                        FROM app.gia_doi_thu_tay""").fetchall()
    assert g == [("THAK", "ke:K0001:ma:NT01", "khach_ke", "K0001", r["id"], "ma:NT01", 1200, "kg", 1, "khong_ro",
                  "khong_ro", "Ca Ba sa cat khuc (500g x 20 packs)", "con")]
    assert conn.execute("SELECT loai FROM app.doi_thu_nhat_ky").fetchall() == [("gia_moi",)]


def test_gia_khac_kg_thi_kg_null(conn, batch):
    _nen_nhac(conn, batch)
    nhac = [_the(CAU, "doi_thu", "THAK", "@THAK"), _the(CAU, "nhom", "ma:NT01", "@Basa")]
    LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac,
                    [{"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 3500, "don_vi_gia": "thung"}])
    assert conn.execute("SELECT kg_moi_don_vi_gia, don_vi_gia FROM app.gia_doi_thu_tay").fetchone() == (None, "thung")


def test_khong_the_khong_gia_van_ghi_nhu_cu(conn, batch):
    _nen_nhac(conn, batch)
    r = LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", "gọi bình thường", "", None, None)
    assert r["canh_bao"] == [] and _so_dong_tx(conn) == 1
    assert conn.execute("SELECT count(*) FROM app.tiep_xuc_nhac").fetchone()[0] == 0


@pytest.mark.parametrize("lam_hong", [
    lambda c: {**c, "vi_tri_dau": c["vi_tri_dau"] + 1},               # không trỏ vào '@'
    lambda c: {**c, "vi_tri_dau": 9999},                              # ngoài câu
    lambda c: {**c, "do_dai": 9999},                                  # đoạn tràn khỏi câu
    lambda c: {**c, "do_dai": 1},                                     # chỉ có '@'
    lambda c: {**c, "khoa": "KHONG-CO"},                              # đối thủ không tồn tại
    lambda c: {**c, "loai": "la"},
])
def test_the_sai_bi_tu_choi_va_KHONG_de_lai_dong_tiep_xuc(conn, batch, lam_hong):
    _nen_nhac(conn, batch)
    the = lam_hong(_the(CAU, "doi_thu", "THAK", "@THAK"))
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", [the], [])
    assert _so_dong_tx(conn) == 0                                     # chưa rollback tay: hàm tự thu lại


@pytest.mark.parametrize("khoa", ["ma:KHONG-CO", "n:999999", "nt01", "n:abc", "ma:", "n:", "x:NT01",
                                  "n:5\n", "ma:NT01\n", " n:5", "ma:NT01 ", "ma:NT\t01", "n:5\x00"])
def test_the_hang_khoa_sai_dinh_dang_hoac_khong_ton_tai(conn, batch, khoa):
    _nen_nhac(conn, batch)
    the = {"loai": "nhom", "khoa": khoa, "vi_tri_dau": CAU.index("@Basa"), "do_dai": 5}
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", [the], [])
    assert _so_dong_tx(conn) == 0


def test_the_nhom_co_ten_n_id_hop_le(conn, batch):
    _nen_nhac(conn, batch)
    n = conn.execute("INSERT INTO app.nhom_so_sanh (ten) VALUES ('Nhóm cá') RETURNING id").fetchone()[0]
    LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", [_the(CAU, "nhom", f"n:{n}", "@Basa")], [])
    assert conn.execute("SELECT khoa FROM app.tiep_xuc_nhac").fetchone() == (f"n:{n}",)


def test_hai_the_chong_len_nhau_bi_tu_choi(conn, batch):
    _nen_nhac(conn, batch)
    a = {"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": 10, "do_dai": 8}
    b = {"loai": "nhom", "khoa": "ma:NT01", "vi_tri_dau": 14, "do_dai": 5}
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", [a, b], [])
    assert _so_dong_tx(conn) == 0


def test_vi_tri_tinh_theo_cau_goc_ke_ca_khoang_trang_dau_va_ky_tu_ngoai_BMP(conn, batch):
    """Giao diện đếm theo JS (UTF-16) trên ô chữ CHƯA cắt khoảng trắng; máy chủ lưu câu đã cắt, vị trí theo ký tự."""
    _nen_nhac(conn, batch)
    cau = "  📞 nói @THAK rẻ"                    # 📞 = 2 đơn vị UTF-16, 1 ký tự
    js = len("  📞 nói ".encode("utf-16-le")) // 2
    the = {"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": js, "do_dai": 5}
    r = LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", cau, "", [the], [])
    luu = conn.execute("SELECT noi_dung FROM app.nhat_ky_tiep_xuc WHERE id=%s", (r["id"],)).fetchone()[0]
    pos = conn.execute("SELECT vi_tri_dau, do_dai FROM app.tiep_xuc_nhac").fetchone()
    assert luu == "📞 nói @THAK rẻ" and luu[pos[0]:pos[0] + pos[1]] == "@THAK"


def test_gia_khong_co_the_tuong_ung_bi_tu_choi(conn, batch):
    _nen_nhac(conn, batch)
    g = {"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 900, "don_vi_gia": "kg"}
    solo_dt = [_the(CAU, "doi_thu", "THAK", "@THAK")]
    solo_hang = [_the(CAU, "nhom", "ma:NT01", "@Basa")]
    for nhac in ([], solo_dt, solo_hang):
        with pytest.raises(LH.LoiNhap):
            LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac, [g])
    both = solo_dt + solo_hang
    for sai in ({**g, "ma_doi_thu": "ICHIBA"}, {**g, "nhom_khoa": "ma:KHAC"}):
        with pytest.raises(LH.LoiNhap):
            LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", both, [sai])
    assert _so_dong_tx(conn) == 0


@pytest.mark.parametrize("sai", [{"gia_goc": ""}, {"gia_goc": "abc"}, {"gia_goc": -5}, {"gia_goc": 0},
                                 {"don_vi_gia": "met"}, {"don_vi_gia": ""}])
def test_gia_sai_gia_tri_bi_tu_choi_va_khong_de_lai_gi(conn, batch, sai):
    _nen_nhac(conn, batch)
    nhac = [_the(CAU, "doi_thu", "THAK", "@THAK"), _the(CAU, "nhom", "ma:NT01", "@Basa")]
    g = {"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 900, "don_vi_gia": "kg", **sai}
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac, [g])
    assert _so_dong_tx(conn) == 0
    assert conn.execute("SELECT count(*) FROM app.gia_doi_thu_tay").fetchone()[0] == 0


def test_loi_giua_chung_thi_thu_lai_tat_ca_ke_ca_khi_nguoi_goi_van_commit(conn, batch, monkeypatch):
    """[CRITICAL] Dòng tiếp xúc, thẻ và giá cùng sống hoặc cùng chết. Người gọi bắt lỗi rồi vẫn commit
    cũng không được để lại nửa chừng."""
    from kome import doi_thu as DT
    _nen_nhac(conn, batch)
    nhac = [_the(CAU, "doi_thu", "THAK", "@THAK"), _the(CAU, "nhom", "ma:NT01", "@Basa")]
    g = {"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 900, "don_vi_gia": "kg"}

    def hong(*a, **k):
        raise RuntimeError("đứt giữa chừng")
    monkeypatch.setattr(DT, "gia_khach_ke", hong)
    with pytest.raises(RuntimeError):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac, [g])
    conn.commit()
    assert _so_dong_tx(conn) == 0
    assert conn.execute("SELECT count(*) FROM app.tiep_xuc_nhac").fetchone()[0] == 0


def test_canh_bao_khi_gia_lech_xa_trung_vi_nhom(conn, batch):
    from tests.test_mart_doi_thu import _qs
    _nen_nhac(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580)]:
        _qs(conn, batch, ben, g)
    nhac = [_the(CAU, "doi_thu", "THAK", "@THAK"), _the(CAU, "nhom", "ma:NT01", "@Basa")]
    r = LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac,
                        [{"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 1400, "don_vi_gia": "kg"}])
    assert r["canh_bao"] == ["Giá ¥1,400/kg lệch xa trung vị ¥560/kg của nhóm — kiểm lại đơn vị?"]
    ok =LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac,
                         [{"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 600, "don_vi_gia": "kg"}])
    assert ok["canh_bao"] == []


def test_canh_bao_in_DUNG_trung_vi_cua_bang_so_sanh(conn, batch):
    """Câu cảnh báo in trung vị của `mart.so_sanh_nhom` (bỏ giá bất thường) — đúng số người ta thấy ở tab
    So sánh giá. Trung vị dùng để BẮT bất thường (`trung_vi_nhom`, tính cả giá lệch) là ¥570 ở đây: in số
    đó là hai con số cùng tên "trung vị" trên hai màn."""
    from tests.test_mart_doi_thu import _qs
    _nen_nhac(conn, batch)
    for ben, g in [("A", 540), ("B", 560), ("C", 580), ("D", 1400)]:
        _qs(conn, batch, ben, g)
    tv = conn.execute("SELECT trung_vi FROM mart.so_sanh_nhom WHERE nhom_khoa = 'ma:NT01'").fetchone()[0]
    assert round(tv) == 560
    nhac = [_the(CAU, "doi_thu", "THAK", "@THAK"), _the(CAU, "nhom", "ma:NT01", "@Basa")]
    r = LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac,
                        [{"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 1400, "don_vi_gia": "kg"}])
    assert r["canh_bao"] == ["Giá ¥1,400/kg lệch xa trung vị ¥560/kg của nhóm — kiểm lại đơn vị?"]


def test_ghi_kem_nhac_dung_luot_hoi_canh_bao_MOT_cho_moi_gia(conn, batch, monkeypatch):
    _nen_nhac(conn, batch)
    cau = "@THAK @Basa và @ICHIBA @Basa"
    nhac = [_the(cau, "doi_thu", "THAK", "@THAK"), {"loai": "nhom", "khoa": "ma:NT01", "vi_tri_dau": 6, "do_dai": 5},
            {"loai": "doi_thu", "khoa": "ICHIBA", "vi_tri_dau": 15, "do_dai": 7},
            {"loai": "nhom", "khoa": "ma:NT01", "vi_tri_dau": 23, "do_dai": 5}]
    gia = [{"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 900, "don_vi_gia": "kg"},
           {"ma_doi_thu": "ICHIBA", "nhom_khoa": "ma:NT01", "gia_goc": 950, "don_vi_gia": "kg"}]
    dem = {"n": 0}
    that = conn.execute

    def demo(q, *a, **k):
        if "gia_doi_thu_hien_hanh" in str(q):
            dem["n"] += 1
        return that(q, *a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", cau, "", nhac, gia)
    assert dem["n"] == 1


# ---- Vòng sửa 1: khoá fullmatch, kiểu dữ liệu, độ dài trước ---------------------------------------------

@pytest.mark.parametrize("khoa", ["THAK\n", " THAK", "THAK ", "TH AK", "THAK\x00"])
def test_the_doi_thu_khoa_co_khoang_trang_hoac_ky_tu_dieu_khien_bi_tu_choi(conn, batch, khoa):
    _nen_nhac(conn, batch)
    the = {"loai": "doi_thu", "khoa": khoa, "vi_tri_dau": CAU.index("@THAK"), "do_dai": 5}
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", [the], [])
    assert _so_dong_tx(conn) == 0


def test_gia_khach_ke_tu_choi_khoa_bien_the_xuong_dong(conn, batch):
    from kome import doi_thu as DT
    _nen_nhac(conn, batch)
    tid = LH.ghi(conn, "K0001", None, "goi", "tot", "x")
    for nk in ("n:5\n", "ma:NT01\n", " ma:NT01"):
        with pytest.raises(DT.LoiNhap):
            DT.gia_khach_ke(conn, "THAK", nk, "K0001", tid, 900, "kg", None)
    with pytest.raises(DT.LoiNhap):
        DT.gia_khach_ke(conn, "THAK\n", "ma:NT01", "K0001", tid, 900, "kg", None)


@pytest.mark.parametrize("sai", [
    {"ma_doi_thu": ["THAK"]}, {"nhom_khoa": ["ma:NT01"]}, {"ma_doi_thu": {"a": 1}}, {"nhom_khoa": 5},
    {"ma_doi_thu": None}, {"gia_goc": [900]}, {"gia_goc": {"a": 1}}, {"don_vi_gia": ["kg"]}, {"don_vi_gia": {"a": 1}}])
def test_gia_sai_kieu_du_lieu_la_LoiNhap_khong_phai_TypeError(conn, batch, sai):
    _nen_nhac(conn, batch)
    nhac = [_the(CAU, "doi_thu", "THAK", "@THAK"), _the(CAU, "nhom", "ma:NT01", "@Basa")]
    g = {"ma_doi_thu": "THAK", "nhom_khoa": "ma:NT01", "gia_goc": 900, "don_vi_gia": "kg", **sai}
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", nhac, [g])
    assert _so_dong_tx(conn) == 0


@pytest.mark.parametrize("the", [
    {"loai": ["doi_thu"], "khoa": "THAK", "vi_tri_dau": 10, "do_dai": 5},
    {"loai": "doi_thu", "khoa": ["THAK"], "vi_tri_dau": 10, "do_dai": 5},
    {"loai": "doi_thu", "khoa": {"a": 1}, "vi_tri_dau": 10, "do_dai": 5},
    {"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": [10], "do_dai": 5},
    {"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": "10", "do_dai": 5},
    {"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": 10, "do_dai": None},
    {"loai": "doi_thu", "khoa": "THAK", "vi_tri_dau": 10.5, "do_dai": 5}])
def test_the_sai_kieu_du_lieu_la_LoiNhap(conn, batch, the):
    _nen_nhac(conn, batch)
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", CAU, "", [the], [])
    assert _so_dong_tx(conn) == 0


def test_do_dai_cau_ghi_chu_duoc_kiem_TRUOC_khi_do_the(conn, batch, monkeypatch):
    """Câu quá dài bị chặn ngay bằng lỗi độ dài — không mã hoá / dò thẻ, không hỏi CSDL về thẻ."""
    _nen_nhac(conn, batch)
    dai = "@THAK " + "x" * LH.DO_DAI_NOI_DUNG
    hong = {"loai": "doi_thu", "khoa": "KHONG-CO", "vi_tri_dau": 0, "do_dai": 5}
    goi = []
    that = LH._kiem_the
    monkeypatch.setattr(LH, "_kiem_the", lambda *a, **k: (goi.append(1), that(*a, **k))[1])
    with pytest.raises(LH.LoiNhap, match="dài quá"):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", dai, "", [hong], [])
    assert goi == [] and _so_dong_tx(conn) == 0


def test_noi_dung_co_nua_cap_UTF16_le_loi_bi_chan_bang_LoiNhap(conn, batch):
    """JSON cho phép một nửa cặp UTF-16 lẻ (U+D800) -> str Python không mã hoá UTF-8 được -> psycopg nổ (500). Chặn ở
    `doc_bieu_mau` — điểm kiểm DUY NHẤT (cả `ghi` lẫn `ghi_kem_nhac` đi qua nó), không ghi dòng nào."""
    _nen_nhac(conn, batch)
    le = "Khách nói " + chr(0xD800)
    with pytest.raises(LH.LoiNhap, match="không hợp lệ"):
        LH.doc_bieu_mau("goi", "tot", le, "")
    with pytest.raises(LH.LoiNhap):
        LH.ghi_kem_nhac(conn, "K0001", None, "goi", "tot", le, "", [], [])
    conn.commit()
    assert _so_dong_tx(conn) == 0
    LH.doc_bieu_mau("goi", "tot", "\U0001F41F cặp đủ vẫn nhận", "")     # emoji (cặp surrogate đủ) không bị chặn
