"""API JSON + trang React + ảnh chụp theo phiên bản dữ liệu (đặc tả giao diện React).

Ba lời hứa được canh ở đây:
  * mọi khối Tổng quan trả JSON được trên kho thật nhỏ, và KHÔNG trả gì khi
    chưa đăng nhập (401, không phải 303 — fetch() đi theo 303 là nhận HTML);
  * ảnh chụp KHÔNG BAO GIỜ cũ hơn dữ liệu: mỗi nguồn đổi là tính lại, và kết
    quả qua ảnh chụp BẰNG kết quả tính thẳng;
  * bản build được commit KHỚP mã nguồn (máy công ty không có Node để build).
"""
import json
import re
from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome import khoi_tong_quan as KTQ
from kome.web import anh_chup, spa
from kome.web.app import create_app

GOC = Path(__file__).resolve().parents[1]
MK = "mat-khau-api-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"
NGAY = date(2026, 7, 31)


def _ban(conn, batch, ngay: date, khach="000000009292", n=1, amount=110_000):
    from kome.loaders import sales
    b = batch(abs(hash((ngay, khach, n, amount))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"A{ngay:%Y%m%d}{khach[-4:]}{n}", "line_seq": 1, "sales_date": ngay,
        "customer_code": khach, "product_code": "AA01", "pack_code": "02", "case_qty": 1, "qty": 6,
        "unit_price": 5250, "unit_cost": 3210, "amount": amount, "tax_amount": 10_000,
        "cost": 70_000, "gross_profit": 30_000, "paid_amount": 0, "salesperson_code": "0104", "batch_id": b,
    }]), ngay, b)
    conn.commit()
    return b


@pytest.fixture
def kho(conn, batch):
    for i in range(8):
        _ban(conn, batch, NGAY - timedelta(days=7 * i), n=i)
        _ban(conn, batch, NGAY - timedelta(days=365 + 7 * i), n=100 + i)
    return conn


# ---- Khối Tổng quan ---------------------------------------------------------

@pytest.mark.parametrize("khoi", sorted(KTQ.KHOI))
def test_moi_khoi_tra_json(kho, test_db_url, khoi):
    r = TestClient(create_app(db_url=test_db_url)).get(f"/api/tong-quan/{khoi}")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("application/json")
    json.loads(r.text)


def test_khoi_la_404(test_db_url):
    assert TestClient(create_app(db_url=test_db_url)).get("/api/tong-quan/xoa-het").status_code == 404


def test_thong_bao_tra_json(kho, test_db_url):
    r = TestClient(create_app(db_url=test_db_url)).get("/api/thong-bao")
    assert r.status_code == 200 and isinstance(r.json()["tb"], list)


def test_api_chua_dang_nhap_tra_401_khong_phai_303(monkeypatch, test_db_url):
    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
    c = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
    r = c.get("/api/tong-quan/kpi")
    assert r.status_code == 401 and r.json()["loi"]
    assert c.get("/api/thong-bao").status_code == 401


def test_ty_suat_theo_thang_la_ty_so_cua_cac_tong(kho, conn):
    """Bất biến tỷ suất (CLAUDE.md) áp cả ở API: lãi gộp tháng ÷ doanh thu tháng."""
    for t in KTQ.theo_thang(conn)["thang"]:
        if t["doanh_thu"]:
            assert t["ty_suat"] == pytest.approx(t["lai_gop"] / t["doanh_thu"])
    for q in KTQ.bien_loi_nhuan(conn)["quy"]:
        if q["doanh_thu"]:
            assert q["bien_gop"] == pytest.approx(q["lai_gop"] / q["doanh_thu"])


def test_theo_thang_giu_THANG_CO_NGAN_SACH_ma_khong_co_dong_ban(kho, conn):
    """Cùng bất biến FULL JOIN của mart.tien_do_ngan_sach. Sự cố thật
    2026-09-25: tháng 8/2026 có ngân sách ¥92,7M nhưng chưa nạp dữ liệu bán —
    khối LEFT JOIN từ doanh thu làm tháng đó biến mất và in "chưa đặt chỉ tiêu
    tháng nào". Ngân sách tháng SAU mốc thì không phải "kết quả" nên không vào."""
    conn.execute("""INSERT INTO app.ngan_sach_cong_ty (thang, doanh_thu, lai_gop)
                    VALUES ('2026-03-01', 5000000, 1500000), ('2026-08-01', 7000000, NULL)""")
    conn.commit()
    thang = {t["thang"]: t for t in KTQ.theo_thang(conn)["thang"]}
    assert thang["2026-03"]["ngan_sach"] == 5_000_000
    assert thang["2026-03"]["doanh_thu"] == 0 and thang["2026-03"]["thang_trong_ky"] == 8
    assert thang["2026-07"]["doanh_thu"] > 0            # tháng có bán vẫn còn nguyên
    assert "2026-08" not in thang                        # kỳ khác, và sau mốc


def test_so_khoi_khop_ham_goc(kho, conn):
    """Khối không tự định nghĩa lại chỉ số: doanh thu tháng của ô KPI BẰNG
    mart.thang_den_hom_nay (khoảng xem mặc định = tháng hiện tại), tổng xu
    hướng BẰNG mart.ban_theo_ngay trên cùng các ngày đó."""
    dt = conn.execute("SELECT dt FROM mart.thang_den_hom_nay").fetchone()[0]
    assert KTQ.kpi(conn)["doanh_thu"]["gia_tri"] == int(dt)
    tong = conn.execute(
        """SELECT sum(b.doanh_thu_thuan) FROM mart.ban_theo_ngay b, mart.thang_den_hom_nay t
            WHERE b.ngay BETWEEN t.tu_ngay AND t.den_ngay""").fetchone()[0]
    assert sum(x[1] for x in KTQ.xu_huong(conn)["diem"]) == int(tong)


# ---- Ảnh chụp theo phiên bản dữ liệu ----------------------------------------

@pytest.fixture
def bat_anh_chup(monkeypatch):
    monkeypatch.setenv("KOME_ANH_CHUP", "1")


def test_anh_chup_trung_thi_khong_tinh_lai(kho, conn, bat_anh_chup):
    goi = []
    tinh = lambda c: goi.append(1) or {"x": 1}
    a, pb1 = anh_chup.lay(conn, "thu", tinh)
    b, pb2 = anh_chup.lay(conn, "thu", tinh)
    assert len(goi) == 1 and json.loads(a) == json.loads(b) and pb1 == pb2 and pb1


@pytest.mark.parametrize("doi", ["lo_nap", "hoan_tac", "ngan_sach", "tiep_xuc"])
def test_moi_nguon_doi_la_tinh_lai(kho, conn, batch, bat_anh_chup, doi):
    """Không bao giờ trả số cũ hơn dữ liệu: nạp, hoàn tác, sửa ngân sách, ghi
    tiếp xúc — nguồn nào đổi cũng làm phiên bản đổi."""
    goi = []
    tinh = lambda c: goi.append(1) or {"n": len(goi)}
    anh_chup.lay(conn, "thu", tinh)
    if doi == "lo_nap":
        _ban(conn, batch, NGAY, khach="000000001111", n=77)
    elif doi == "hoan_tac":
        conn.execute("UPDATE meta.ingest_batch SET undone_at = now() WHERE batch_id = (SELECT max(batch_id) FROM meta.ingest_batch)")
    elif doi == "ngan_sach":
        conn.execute("INSERT INTO core.dim_salesperson (salesperson_code, ten) VALUES ('0104', 'Lan') ON CONFLICT DO NOTHING")
        conn.execute("""INSERT INTO app.ngan_sach_nhat_ky (salesperson_code, thang, muc_tieu_cu, muc_tieu_moi)
                        VALUES ('0104', '2026-07-01', NULL, 100)""")
    else:
        conn.execute("""INSERT INTO app.nhat_ky_tiep_xuc (customer_code, kieu, ket_qua, noi_dung)
                        VALUES ('000000009292', 'goi', 'tot', 'thử')""")
    conn.commit()
    ra, _ = anh_chup.lay(conn, "thu", tinh)
    assert len(goi) == 2 and json.loads(ra) == {"n": 2}


def test_khoi_theo_ngay_tinh_lai_khi_sang_ngay_moi(kho, conn, bat_anh_chup, monkeypatch):
    goi = []
    tinh = lambda c: goi.append(1) or {}
    monkeypatch.setattr(anh_chup, "hom_nay_o_nhat", lambda: date(2026, 9, 23))
    anh_chup.lay(conn, "thu", tinh, theo_ngay=True)
    anh_chup.lay(conn, "thu", tinh, theo_ngay=True)
    monkeypatch.setattr(anh_chup, "hom_nay_o_nhat", lambda: date(2026, 9, 24))
    anh_chup.lay(conn, "thu", tinh, theo_ngay=True)
    assert len(goi) == 2


def test_qua_anh_chup_bang_tinh_thang(kho, conn, test_db_url, monkeypatch):
    c = TestClient(create_app(db_url=test_db_url))
    thang = c.get("/api/tong-quan/theo_thang").json()
    monkeypatch.setenv("KOME_ANH_CHUP", "1")
    lan1 = c.get("/api/tong-quan/theo_thang")
    lan2 = c.get("/api/tong-quan/theo_thang")
    assert lan1.json() == thang == lan2.json()


def test_etag_304_khi_du_lieu_chua_doi(kho, test_db_url, bat_anh_chup):
    c = TestClient(create_app(db_url=test_db_url))
    r = c.get("/api/tong-quan/xu_huong")
    etag = r.headers["etag"]
    r2 = c.get("/api/tong-quan/xu_huong", headers={"If-None-Match": etag})
    assert r2.status_code == 304 and not r2.content


# ---- Trang React ------------------------------------------------------------

def _khoi_dau(html):
    return json.loads(re.search(r"<script>window.__KOME__=(.*?)</script>", html, re.S).group(1))


def test_trang_react_co_data_theme_tu_cookie(test_db_url):
    """Bất biến "không có khung hình sai màu": data-theme đã có trong HTML đầu tiên."""
    c = TestClient(create_app(db_url=test_db_url))
    assert '<html lang="vi" data-theme="toi"' in c.get("/", cookies={"kome_giao_dien": "toi"}).text
    html = c.get("/", cookies={"kome_giao_dien": "<script>"}).text
    assert 'data-theme="<script>"' not in html and "kome_giao_dien" not in html


def test_du_lieu_khoi_dau_khong_the_dong_the_script():
    """Tên người dùng / dữ liệu có "</script>" không được thoát khỏi thẻ script."""
    html = spa.trang(None, {"nguoi": {"ten_dang_nhap": "x</script><script>alert(1)</script>"}})
    khoi = re.search(r"<script>window.__KOME__=(.*?)</script>", html, re.S).group(1)
    assert "</script>" not in khoi and json.loads(khoi)["nguoi"]["ten_dang_nhap"].startswith("x</script>")


def test_du_lieu_khoi_dau_du_danh_muc_va_quyen(test_db_url):
    kd = _khoi_dau(TestClient(create_app(db_url=test_db_url)).get("/").text)
    assert len(kd["danh_muc"]["khoi"]) == 22 and kd["chua_co"]["dong_tien"] and "cong_no" not in kd["chua_co"]
    assert kd["nguoi"] is None and kd["hien_kho"] is True


def test_ban_build_khop_ma_nguon():
    """Sửa giao_dien/ mà quên `npm run build` -> đỏ. Máy công ty không có Node,
    nó chạy ĐÚNG bản build trong git."""
    assert spa.co_ban_build(), "chưa có kome/web/spa/index.html — chạy npm run build trong giao_dien/"
    ghi = (spa.THU_MUC / ".nguon").read_text().strip()
    assert ghi == spa.van_tay_nguon(), "bản build cũ hơn mã nguồn — chạy: cd giao_dien && npm run build"


def test_vercel_khong_day_ma_nguon_giao_dien():
    """Vercel chỉ cần bản build; thấy package.json ở giao_dien/ có thể khiến nó
    nhận nhầm dự án là Node."""
    dong = (GOC / ".vercelignore").read_text(encoding="utf-8").splitlines()
    assert "giao_dien/" in dong
    assert not (GOC / "package.json").exists()


# Ngân sách truy vấn của từng khối — đo lượt hỏi, không đo sức tính (CLAUDE.md).
# Khối nặng nhất (kpi) gom 6 nguồn cho 6 ô; mọi khối đi qua ảnh chụp nên người
# xem chỉ trả 1 lượt khi trúng. Khối theo khoảng xem (KHOI[..][3]) cộng 1 lượt
# `khoang_xem.pham_vi` (đặc tả khoảng xem §5).
NGAN_SACH_TRUY_VAN = {
    "kpi": 9, "ns_thang": 5, "so_sanh_sale": 4, "theo_thang": 2, "xu_huong": 2,
    "suc_khoe_khach": 1, "han_su_dung": 1, "viec_hom_nay": 8, "don_hang": 3,
    "danh_sach_khach": 2, "hieu_suat_nganh": 2, "tuong_quan": 2, "tang_truong": 2,
    "bien_loi_nhuan": 2, "thang_nay_chua_mua": 1, "cong_no": 2, "khach_moi": 2,
}


def test_moi_khoi_co_ngan_sach_truy_van():
    assert set(NGAN_SACH_TRUY_VAN) == set(KTQ.KHOI)


@pytest.mark.parametrize("khoi", sorted(KTQ.KHOI))
def test_khoi_khong_vuot_ngan_sach_truy_van(kho, conn, monkeypatch, khoi):
    dem = {"n": 0}
    that = conn.execute

    def demo(*a, **k):
        dem["n"] += 1
        return that(*a, **k)
    monkeypatch.setattr(conn, "execute", demo)
    KTQ.KHOI[khoi][0](conn, None)
    assert dem["n"] <= NGAN_SACH_TRUY_VAN[khoi], f"{khoi} chạy {dem['n']} truy vấn"
