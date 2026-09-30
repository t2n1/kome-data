"""Bảng dữ liệu sửa (072) — kome/bang_du_lieu.py + API + trang. Đặc tả 2026-09-30-bang-du-lieu-sua-design.md §5."""
import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from kome import bang_du_lieu as BDL
from kome.web.app import create_app
from tests.test_bang_du_lieu_mart import _gia, _hang, _khach, _ton
from tests.test_bao_mat import khach  # noqa: F401 — fixture: client có cổng đăng nhập

D2 = date(2026, 9, 8)


def _sp(conn, batch):
    _hang(conn, batch, "NT01", "Nước mắm")
    _hang(conn, batch, "NT02", "Bánh đa", ("02", "冷凍食品_VNM"))
    _gia(conn, batch, "NT01", "02", "01", 5200, 5616)
    _ton(conn, batch, "NT01", "0001", 10, "2027年03月10日")


def _dem(conn, monkeypatch):
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    return dem


def _so(conn):
    return conn.execute("""SELECT bang, khoa, cot, gia_tri, gia_tri_obc, gia_tri_truoc, bo FROM app.sua_du_lieu
                           ORDER BY id""").fetchall()


def _dong(d, k):
    return next(x for x in d["dong"] if x["k"] == k)


def test_doc_mot_luot_hoi_va_hinh_dang(conn, batch, monkeypatch):
    _sp(conn, batch)
    dem = _dem(conn, monkeypatch)
    d = BDL.doc(conn, "sp")
    assert dem["n"] == 1
    ma = [c["ma"] for c in d["cot"]]
    assert {"product_name", "gia:02|01", "ton:0001", "han:0001", "dt_12t", "ton_tong"} <= set(ma)
    c = {c["ma"]: c for c in d["cot"]}
    assert c["gia:02|01"]["nhan"] == "No.1 · ケース" and c["gia:02|01"]["kieu"] == "so" and c["gia:02|01"]["sua"]
    assert c["ton:0001"]["nhan"] == "Tồn · Kho 0001" and c["han:0001"]["kieu"] == "ngay"
    assert c["dt_12t"]["sua"] is False and c["dt_12t"]["nhom"] == "Chỉ số (chỉ xem)"
    assert ["01", "調味料_VNM"] in [list(x) for x in c["food_category_code"]["chon"]]
    assert [x["k"] for x in d["dong"]] == ["NT01", "NT02"]            # theo mã
    o = _dong(d, "NT01")["o"]
    assert o["product_name"] == "Nước mắm" and o["gia:02|01"] == "5200" and o["case_qty"] == "20.0000"
    assert o["ton:0001"] == "10.0000" and o["han:0001"] == "2027-03-10" and o["ton_tong"] == "10.0000"
    assert all(v is None or isinstance(v, str) for x in d["dong"] for v in x["o"].values())
    assert "gia:02|01" not in _dong(d, "NT02")["o"]                  # ô OBC không có = vắng (không sửa được)
    assert d["loai"] == "sp" and d["lech"] == {} and d["anh_ton"] == "2026-09-08" and d["lan_nap_gia"] == "2026-09-08"
    assert d["sua_duoc"] is True


def test_doc_khach_hang(conn, batch, monkeypatch):
    _khach(conn, batch, "000000009292", "Quán A")
    dem = _dem(conn, monkeypatch)
    d = BDL.doc(conn, "kh")
    assert dem["n"] == 1
    c = {c["ma"]: c for c in d["cot"]}
    assert len(c["prefecture"]["chon"]) == 47 and ["大阪府", "大阪府"] in [list(x) for x in c["prefecture"]["chon"]]
    assert c["rank_code"]["nhan"] == "Hạng OBC" and ["0003", "C"] in [list(x) for x in c["rank_code"]["chon"]]
    assert c["lan_cuoi"]["sua"] is False
    o = _dong(d, "000000009292")["o"]
    assert o["customer_name"] == "Quán A" and o["prefecture"] == "大阪府" and o["dt_12t"] is None


def test_cot_danh_muc_DUNG_danh_sach_cot_cua_so(conn):
    """Cột sửa được của màn = đúng danh sách cột CHECK của 072 cho phép — lệch là ô sửa được mà lưu thì CSDL nổ."""
    d = conn.execute("SELECT pg_get_constraintdef(oid) FROM pg_constraint WHERE conname='sua_du_lieu_cot_check'").fetchone()[0]
    for loai in BDL.LOAI:
        for ma in BDL.COT_DANH_MUC[loai]:
            assert f"'{ma}'" in d


def test_luu_ghi_so_va_doc_lai_hieu_luc(conn, batch):
    _sp(conn, batch)
    ra = BDL.luu(conn, "sp", [
        {"k": "NT01", "cot": "product_name", "gia_tri": "  Nước mắm Phú Quốc ", "thay": "Nước mắm"},
        {"k": "NT01", "cot": "gia:02|01", "gia_tri": "5,300", "thay": "5200"},
        {"k": "NT01", "cot": "han:0001", "gia_tri": "2027-04-01", "thay": "2027-03-10"}], None, True)
    conn.commit()
    assert ra["so_o"] == 3 and [x["k"] for x in ra["dong"]] == ["NT01"]
    assert ra["dong"][0]["o"]["gia:02|01"] == "5300" and set(ra["lech"]) == {
        "NT01\tproduct_name", "NT01\tgia:02|01", "NT01\than:0001"}
    d = BDL.doc(conn, "sp")
    o = _dong(d, "NT01")["o"]
    assert (o["product_name"], o["gia:02|01"], o["han:0001"]) == ("Nước mắm Phú Quốc", "5300", "2027-04-01")
    assert d["lech"]["NT01\tgia:02|01"]["obc"] == "5200" and d["lech"]["NT01\than:0001"]["obc"] == "2027-03-10"
    assert d["lech"]["NT01\tproduct_name"]["obc"] == "Nước mắm" and d["lech"]["NT01\tproduct_name"]["luc"]
    assert _so(conn) == [
        ("san_pham", "NT01", "product_name", "Nước mắm Phú Quốc", "Nước mắm", "Nước mắm", False),
        ("gia", "NT01|02|01", "gia_chua_thue", "5300", "5200", "5200", False),
        ("ton", "NT01|0001", "best_before", "2027年04月01日", "2027年03月10日", "2027年03月10日", False)]


def test_ban_sua_qua_luu_CO_HIEU_LUC_o_ca_bon_loai_bang(conn, batch):
    """gia_tri_obc phải đúng chữ mà view so — lệch một ký tự là bản sửa lặng lẽ không bao giờ áp."""
    _khach(conn, batch, "K1", "Quán A")
    _hang(conn, batch, "P1", "Hang 1")
    _gia(conn, batch, "P1", "00", "02", 0, 5000)                       # giá OBC = 5000 / 1,08 — nhiều số lẻ
    _ton(conn, batch, "P1", "0001", 83.75, "2027年3月9日")
    BDL.luu(conn, "kh", [{"k": "K1", "cot": "customer_name", "gia_tri": "Quán A mới", "thay": "Quán A"},
                         {"k": "K1", "cot": "prefecture", "gia_tri": "京都府", "thay": "大阪府"}], None, True)
    BDL.luu(conn, "sp", [{"k": "P1", "cot": "case_qty", "gia_tri": "24", "thay": "20.0000"},
                         {"k": "P1", "cot": "gia:00|02", "gia_tri": "4700", "thay": "4630"},
                         {"k": "P1", "cot": "ton:0001", "gia_tri": "80.5", "thay": "83.7500"},
                         {"k": "P1", "cot": "han:0001", "gia_tri": "không hạn", "thay": "2027-03-09"}], None, True)
    conn.commit()
    assert conn.execute("SELECT customer_name, prefecture FROM mart.dim_customer WHERE customer_code='K1' AND is_current"
                        ).fetchone() == ("Quán A mới", "京都府")
    assert float(conn.execute("SELECT case_qty FROM mart.dim_product WHERE product_code='P1'").fetchone()[0]) == 24
    r = conn.execute("SELECT gia_chua_thue, da_sua FROM mart.bang_gia_kome WHERE product_code='P1' AND hien_hanh").fetchone()
    assert (float(r[0]), r[1]) == (4700, True)
    r = conn.execute("SELECT so_luong, best_before, loai_han FROM mart.ton_hien_tai WHERE product_code='P1'").fetchone()
    assert (float(r[0]), r[1], r[2]) == (80.5, "賞味期限なし", "khong_han")
    obc = dict(conn.execute("SELECT cot, gia_tri_obc FROM app.sua_du_lieu").fetchall())
    assert obc["case_qty"] == "20.0000" and obc["stock_qty"] == "83.7500" and obc["best_before"] == "2027年3月9日"
    assert obc["gia_chua_thue"] == conn.execute("SELECT gia_obc::text FROM mart.bang_gia_kome WHERE product_code='P1'"
                                                ).fetchone()[0] and len(obc["gia_chua_thue"]) > 10
    # về lại OBC bằng chính số đang hiện (4630 = round(4629,63…)) → dòng bo, giá về đúng số lẻ OBC
    BDL.luu(conn, "sp", [{"k": "P1", "cot": "gia:00|02", "gia_tri": "4630", "thay": "4700"}], None, True)
    conn.commit()
    r = conn.execute("SELECT gia_chua_thue, da_sua FROM mart.bang_gia_kome WHERE product_code='P1' AND hien_hanh").fetchone()
    assert (round(float(r[0]), 2), r[1]) == (4629.63, False)


def test_luu_KHONG_tinh_chi_so_chi_xem(conn, batch, monkeypatch):
    """mart.doanh_thu_12t dựng trên khach_360 (~1,2 s trên CSDL thật) — lưu (một phần đang giữ khoá advisory) không
    được tính lại chỉ số chỉ xem. Dòng đọc lại không mang dt_12t / lan_cuoi (trình duyệt giữ giá trị đã có)."""
    _sp(conn, batch)
    _khach(conn, batch, "K1", "Quán A")
    sql = []
    that = conn.execute

    def ghi_lai(q, *a, **k):
        sql.append(str(q))
        return that(q, *a, **k)
    monkeypatch.setattr(conn, "execute", ghi_lai)
    ra = BDL.luu(conn, "kh", [{"k": "K1", "cot": "phone", "gia_tri": "06-1", "thay": None}], None, True)
    assert ra["so_o"] == 1 and "dt_12t" not in ra["dong"][0]["o"] and "lan_cuoi" not in ra["dong"][0]["o"]
    ra = BDL.luu(conn, "sp", [{"k": "NT01", "cot": "ton:0001", "gia_tri": "12", "thay": "10.0000"}], None, True)
    o = ra["dong"][0]["o"]
    assert "dt_12t" not in o and o["ton_tong"] == "12.0000" and o["ton:0001"] == "12.0000"
    assert len(sql) == 6 and not [q for q in sql if "doanh_thu_12t" in q or "ban_den_moc" in q or "lan_mua" in q]
    sql.clear()
    assert "dt_12t" in _dong(BDL.doc(conn, "kh"), "K1")["o"] and "ban_den_moc" in BDL._sql_sp(True)
    assert len(sql) == 1 and "mart.doanh_thu_12t" in sql[0]


def test_luu_bang_OBC_la_ve_OBC(conn, batch):
    _sp(conn, batch)
    BDL.luu(conn, "sp", [{"k": "NT01", "cot": "case_qty", "gia_tri": "24", "thay": "20.0000"}], None, True)
    BDL.luu(conn, "sp", [{"k": "NT01", "cot": "case_qty", "gia_tri": "20", "thay": "24.0000"}], None, True)
    conn.commit()
    assert [r[-1] for r in _so(conn)] == [False, True]
    d = BDL.doc(conn, "sp")
    assert d["lech"] == {} and _dong(d, "NT01")["o"]["case_qty"] == "20.0000"


def test_gia_tri_bang_hieu_luc_thi_bo_qua(conn, batch):
    _sp(conn, batch)
    ra = BDL.luu(conn, "sp", [{"k": "NT01", "cot": "case_qty", "gia_tri": "20", "thay": "20.0000"},
                              {"k": "NT01", "cot": "han:0001", "gia_tri": "2027-03-10", "thay": "2027-03-10"}], None, True)
    assert ra["so_o"] == 0 and _so(conn) == []


def test_400_gom_moi_loi_khong_ghi_gi(conn, batch):
    _sp(conn, batch)
    _khach(conn, batch, "K1", "Quán A")
    with pytest.raises(BDL.LoiO) as e:
        BDL.luu(conn, "kh", [{"k": "K1", "cot": "prefecture", "gia_tri": "大阪県", "thay": "大阪府"},
                             {"k": "K1", "cot": "dt_12t", "gia_tri": "1", "thay": None},
                             {"k": "K1", "cot": "customer_name", "gia_tri": "Quán B", "thay": "Quán A"}], None, True)
    assert set(e.value.o_loi) == {"K1\tprefecture", "K1\tdt_12t"}
    with pytest.raises(BDL.LoiO) as e:
        BDL.luu(conn, "sp", [{"k": "NT01", "cot": "gia:02|01", "gia_tri": "-5", "thay": "5200"},
                             {"k": "NT02", "cot": "gia:02|01", "gia_tri": "5000", "thay": None},
                             {"k": "NT01", "cot": "ton:0001", "gia_tri": "1.5e3x", "thay": "10.0000"},
                             {"k": "NT01", "cot": "case_qty", "gia_tri": "-1", "thay": "20.0000"},
                             {"k": "NT01", "cot": "food_category_code", "gia_tri": "99", "thay": "01"},
                             {"k": "NT01", "cot": "han:0001", "gia_tri": "2027-02-30", "thay": "2027-03-10"},
                             {"k": "NT01", "cot": "gia:02|01", "gia_tri": "5200.5", "thay": "5200"},
                             {"k": "NT01", "cot": "product_name", "gia_tri": "x" * 201, "thay": "Nước mắm"},
                             {"k": "NT01", "cot": "product_code", "gia_tri": "X", "thay": "NT01"},
                             {"k": "ZZ99", "cot": "product_name", "gia_tri": "X", "thay": None}], None, True)
    assert set(e.value.o_loi) == {"NT01\tgia:02|01", "NT02\tgia:02|01", "NT01\tton:0001", "NT01\tcase_qty",
                                  "NT01\tfood_category_code", "NT01\than:0001", "NT01\tproduct_name",
                                  "NT01\tproduct_code", "ZZ99\tproduct_name"}
    conn.rollback()
    assert _so(conn) == []


def test_400_than_sai_dang(conn):
    for loai, o in (("xx", []), ("sp", "abc"), ("sp", [{"k": "NT01"}]), ("sp", [{}] * (BDL.TOI_DA_O + 1))):
        with pytest.raises(BDL.LoiO):
            BDL.luu(conn, loai, o, None, True)


def test_tran_2000_o_cua_giao_dien_BANG_hang_so_may_chu():
    """Giao diện không gửi lô quá trần — hằng số ở logic.ts phải BẰNG BDL.TOI_DA_O (sửa một bên là sửa cả hai)."""
    import re
    from pathlib import Path
    ts = (Path(__file__).resolve().parent.parent / "giao_dien" / "src" / "bang_du_lieu" / "logic.ts").read_text(encoding="utf-8")
    m = re.search(r"export const TOI_DA_O = (\d+);", ts)
    assert m, "logic.ts thiếu `export const TOI_DA_O`"
    assert int(m.group(1)) == BDL.TOI_DA_O


def test_chuan_hoa_so(conn, batch):
    _sp(conn, batch)
    BDL.luu(conn, "sp", [{"k": "NT01", "cot": "ton:0001", "gia_tri": "1,234.56789", "thay": "10.0000"},
                         {"k": "NT01", "cot": "case_qty", "gia_tri": "-0", "thay": "20.0000"}], None, True)
    assert {r[2]: r[3] for r in _so(conn)} == {"stock_qty": "1234.5679", "case_qty": "0.0000"}


def test_409_khi_thay_khac_hien_luc(conn, batch):
    from kome.web import nguoi_dung as ND
    _sp(conn, batch)
    an = ND.tao(conn, "an", "mat-khau-cua-an-2026")
    BDL.luu(conn, "sp", [{"k": "NT01", "cot": "gia:02|01", "gia_tri": "5300", "thay": "5200"}], an, True)
    conn.commit()
    with pytest.raises(BDL.XungDotO) as e:
        BDL.luu(conn, "sp", [{"k": "NT01", "cot": "gia:02|01", "gia_tri": "5400", "thay": "5200"},
                             {"k": "NT01", "cot": "product_name", "gia_tri": "X", "thay": "Nước mắm"}], None, True)
    x = e.value.xung_dot
    assert len(x) == 1 and x[0]["k"] == "NT01" and x[0]["cot"] == "gia:02|01"
    assert x[0]["gia_tri"] == "5300" and x[0]["ai"] == "an" and x[0]["luc"]
    conn.rollback()
    assert len(_so(conn)) == 1


def test_409_do_OBC_nap_lai_thi_khong_gan_ten_nguoi_sua(conn, batch):
    """OBC đã ghi khác (bản sửa hết hiệu lực) → giá trị mới đến từ lần nạp, không phải từ người sửa cũ."""
    from kome.web import nguoi_dung as ND
    _khach(conn, batch, "K1", "Quán A")
    an = ND.tao(conn, "an", "mat-khau-cua-an-2026")
    BDL.luu(conn, "kh", [{"k": "K1", "cot": "customer_name", "gia_tri": "Quán A1", "thay": "Quán A"}], an, True)
    conn.commit()
    _khach(conn, batch, "K1", "Quán B", ngay=date(2026, 9, 9))
    with pytest.raises(BDL.XungDotO) as e:
        BDL.luu(conn, "kh", [{"k": "K1", "cot": "customer_name", "gia_tri": "Quán A2", "thay": "Quán A1"}], an, True)
    assert e.value.xung_dot == [{"k": "K1", "cot": "customer_name", "gia_tri": "Quán B", "ai": None, "luc": None}]
    conn.rollback()


def test_403_khong_co_co(conn, batch):
    _sp(conn, batch)
    with pytest.raises(BDL.KhongDuQuyen):
        BDL.luu(conn, "sp", [{"k": "NT01", "cot": "case_qty", "gia_tri": "24", "thay": "20.0000"}], None, False)
    assert _so(conn) == []


def test_han_obc_va_han_iso():
    assert BDL.han_obc("2027-03-10") == "2027年03月10日"
    assert BDL.han_obc("không hạn") == "賞味期限なし" and BDL.han_obc("") == ""
    for sai in ("2027-02-30", "2027/03/10", "10-03-2027", "abc", "2027年03月10日"):
        with pytest.raises(ValueError):
            BDL.han_obc(sai)
    assert BDL.han_iso("2027年03月10日") == "2027-03-10" and BDL.han_iso("2027年3月9日") == "2027-03-09"
    assert BDL.han_iso("賞味期限なし") == "không hạn" and BDL.han_iso(" 賞味期限なし　") == "không hạn"
    assert BDL.han_iso("") == "" and BDL.han_iso(None) == ""
    assert BDL.han_iso("2027年02月30日") == "2027年02月30日" and BDL.han_iso("不明") == "不明"
    for iso in ("2027-03-10", "không hạn", ""):
        assert BDL.han_iso(BDL.han_obc(iso)) == iso


def test_api_va_trang(conn, batch, test_db_url):
    from tests.spa_kd import man
    _sp(conn, batch)
    c = TestClient(create_app(db_url=test_db_url))                   # KHÔNG cổng (conftest xoá KOME_SESSION_SECRET)
    r = c.get("/api/kho-du-lieu/bang-du-lieu?loai=sp")
    assert r.status_code == 200 and r.headers["cache-control"] == "private, no-store"
    d = r.json()
    assert d["sua_duoc"] is True and _dong(d, "NT01")["o"]["gia:02|01"] == "5200"
    print(f"cỡ JSON loai=sp trên CSDL test: {len(r.content)} byte")
    assert c.get("/api/kho-du-lieu/bang-du-lieu?loai=xx").status_code == 400
    r = c.post("/api/kho-du-lieu/bang-du-lieu/luu", json={"loai": "sp", "o": [
        {"k": "NT01", "cot": "gia:02|01", "gia_tri": "5300", "thay": "5200"}]})
    assert r.status_code == 200 and r.json()["so_o"] == 1 and r.json()["dong"][0]["o"]["gia:02|01"] == "5300"
    assert "du_lieu" in {d["loai"] for d in man(c.get("/nhat-ky").text)["ds"]}
    r = c.post("/api/kho-du-lieu/bang-du-lieu/luu", json={"loai": "sp", "o": [
        {"k": "NT01", "cot": "gia:02|01", "gia_tri": "-1", "thay": "5300"}]})
    assert r.status_code == 400 and "NT01\tgia:02|01" in r.json()["o_loi"]
    r = c.post("/api/kho-du-lieu/bang-du-lieu/luu", json={"loai": "sp", "o": [
        {"k": "NT01", "cot": "gia:02|01", "gia_tri": "5400", "thay": "5200"}]})
    assert r.status_code == 409 and r.json()["xung_dot"][0]["gia_tri"] == "5300"
    assert man(c.get("/kho-du-lieu/bang-du-lieu").text) == {}
    r = c.post("/api/kho-du-lieu/bang-du-lieu/luu", content="loai=sp",
               headers={"content-type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415
    assert c.post("/api/kho-du-lieu/bang-du-lieu/luu", content="{x",
                  headers={"content-type": "application/json"}).status_code == 400
    assert conn.execute("SELECT count(*) FROM app.sua_du_lieu").fetchone()[0] == 1


def test_api_co_cong_can_co_sua_du_lieu(conn, batch, khach):
    from tests.test_bao_mat import _vao
    _sp(conn, batch)
    c = khach()                                                      # có cổng; "an" có duoc_vao_kho_du_lieu
    _vao(c)
    r = c.get("/api/kho-du-lieu/bang-du-lieu?loai=sp")
    assert r.status_code == 200 and r.json()["sua_duoc"] is False
    r = c.post("/api/kho-du-lieu/bang-du-lieu/luu", json={"loai": "sp", "o": [
        {"k": "NT01", "cot": "case_qty", "gia_tri": "24", "thay": "20.0000"}]})
    assert r.status_code == 403 and "Sửa dữ liệu" in r.json()["loi"]
    assert conn.execute("SELECT count(*) FROM app.sua_du_lieu").fetchone()[0] == 0
    conn.execute("UPDATE app.nguoi_dung SET duoc_sua_du_lieu = true WHERE ten_dang_nhap = 'an'")
    conn.commit()
    assert c.get("/api/kho-du-lieu/bang-du-lieu?loai=sp").json()["sua_duoc"] is True
    r = c.post("/api/kho-du-lieu/bang-du-lieu/luu", json={"loai": "sp", "o": [
        {"k": "NT01", "cot": "case_qty", "gia_tri": "24", "thay": "20.0000"}]})
    assert r.status_code == 200
    assert conn.execute("""SELECT n.ten_dang_nhap FROM app.sua_du_lieu s JOIN app.nguoi_dung n ON n.id = s.nguoi_dung_id
                        """).fetchone()[0] == "an"


def test_api_co_cong_khong_co_co_kho_du_lieu_thi_403(conn, khach):
    from tests.test_bao_mat import _vao
    c = khach(kho_du_lieu=False)
    _vao(c)
    assert c.get("/api/kho-du-lieu/bang-du-lieu?loai=sp").status_code == 403
    assert c.post("/api/kho-du-lieu/bang-du-lieu/luu", json={"loai": "sp", "o": []}).status_code == 403


def test_giao_dien_man_bang_du_lieu_noi_dung_nguon():
    """Màn React (Task 6): thanh trái có mục, main.tsx có route, màn gọi đúng API, giữ khoảng xem khi đổi ?loai=,
    hỏi trước khi rời trang còn ô chưa lưu, số qua dinh_dang.ts (không toFixed / de-DE)."""
    from tests.spa_kd import nguon
    assert "/kho-du-lieu/bang-du-lieu" in nguon("he_thong", "TabKho.tsx")
    main = nguon("main.tsx")
    assert '"/kho-du-lieu/bang-du-lieu"' in main and "ManBangDuLieu" in main
    man = nguon("bang_du_lieu", "ManBangDuLieu.tsx")
    assert "/api/kho-du-lieu/bang-du-lieu" in man and "giuKhoang(" in man and "beforeunload" in man
    for f in ("ManBangDuLieu.tsx", "BangTinh.tsx"):
        m = nguon("bang_du_lieu", f)
        assert "toFixed(" not in m and "de-DE" not in m, f
