"""Đợt 5b Task 4 — bảy khối phân tích mới hiển thị trên `/bao-cao`, cộng
token màu CSS mới.

Không kiểm lại công thức (đã có `tests/test_phan_tich_mart.py` và
`tests/test_bao_cao_phan_tich.py`) — chỉ kiểm trang RENDER đúng, chữ bắt
buộc hiện đúng điều kiện, và không có mã màu hex nào lọt vào giao diện.

Giai đoạn 3: màn là React (giao_dien/src/bao_cao/BaoCao.tsx) — template
bao_cao.html đã xoá. Mỗi test giữ NGUYÊN bất biến cũ nhưng kiểm theo hai
nửa: (a) dữ liệu `/api/bao-cao` sinh ra câu chữ/khối đó ĐÚNG điều kiện, và
(b) khi bất biến thuần hiển thị (một câu bắt buộc, một mục chú giải, "không
mã hex", "mọi rect dữ liệu có <title>", "bảng nhiệt là <table> có scope")
thì kiểm thẳng mã nguồn React — thứ duy nhất còn quyết định chữ trên màn.
"""
import re
from datetime import date
from pathlib import Path

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from kome.bao_cao import NganhKy, tinh_bao_cao, NGANH_TRONG, nhom_theo_nganh
from kome.ve_phan_tich import ve_cay_o, ve_dong_gop, ve_nhiet
from kome.web.app import create_app

THU_MUC_GD = (Path(__file__).resolve().parent.parent
              / "giao_dien" / "src" / "bao_cao")
NGUON = THU_MUC_GD / "BaoCao.tsx"


def _src() -> str:
    return NGUON.read_text(encoding="utf-8")


def _api(client, ky=2026) -> dict:
    """Trang /bao-cao là vỏ React; dữ liệu nằm ở /api/bao-cao."""
    r = client.get(f"/api/bao-cao?ky={ky}")
    assert r.status_code == 200, r.text
    return r.json()


@pytest.fixture
def client(conn, test_db_url):
    return TestClient(create_app(db_url=test_db_url))


def _ban(conn, batch, ngay: date, ma_hang: str, khach="000000009292",
         amount=110_000, tax=10_000, gp=30_000, sale="0104", n=1):
    """Một dòng bán thật qua loader, không SQL tay — cùng nếp
    tests/test_bao_cao_phan_tich.py."""
    from kome.loaders import sales
    b = batch(abs(hash((ngay, ma_hang, khach, amount, tax, sale, n))) % 90_000 + 1)
    sales.load(conn, pd.DataFrame([{
        "slip_no": f"S{ngay:%Y%m%d}{khach[-4:]}{ma_hang}{n}", "line_seq": 1,
        "sales_date": ngay, "customer_code": khach, "product_code": ma_hang,
        "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
        "unit_cost": 3210, "amount": amount, "tax_amount": tax,
        "cost": amount - tax - gp, "gross_profit": gp, "paid_amount": 0,
        "salesperson_code": sale, "batch_id": b,
    }]), ngay, b)
    conn.commit()


def _nganh(conn, batch, ma_hang: str, ten_nganh: str):
    b = batch(abs(hash(("nganh", ma_hang))) % 40_000 + 300_000)
    conn.execute(
        """INSERT INTO core.dim_product
             (product_code, product_name, food_category_name, batch_id)
           VALUES (%s, %s, %s, %s) ON CONFLICT (product_code) DO NOTHING""",
        (ma_hang, f"Hàng {ma_hang}", ten_nganh, b))
    conn.commit()


def _hai_nam(conn, batch, ma="AA01", ngành="Đồ khô"):
    """Hai năm dữ liệu đủ để có tháng đối chiếu — kỳ 2025 (2024-08..2025-07)
    và kỳ 2026 (2025-08..2026-07), cùng mã/ngành mỗi tháng."""
    _nganh(conn, batch, ma, ngành)
    n = 0
    for nam, thang_bd in ((2024, 8), (2025, 8)):
        for i in range(12):
            th = (thang_bd - 1 + i) % 12 + 1
            y = nam + (thang_bd - 1 + i) // 12
            n += 1
            _ban(conn, batch, date(y, th, 11), ma, amount=110_000, tax=10_000,
                 gp=30_000, n=n)


def test_kho_rong_tra_200(client, conn):
    r = client.get("/bao-cao")
    assert r.status_code == 200 and 'id="goc"' in r.text
    d = client.get("/api/bao-cao").json()
    assert d["bc"]["khong_co_du_lieu"] is True


def test_kho_hai_nam_tra_200_va_hien_khoi_moi(client, conn, batch):
    """Giai đoạn 3: bốn khối có DỮ LIỆU để vẽ (API) và có tiêu đề trên màn (React)."""
    _hai_nam(conn, batch)
    assert client.get("/bao-cao?ky=2026").status_code == 200
    d = _api(client)
    for khoi in ("dg", "co", "nh", "pa"):
        assert d[khoi]["co"] is True, f"khối {khoi} không có gì để vẽ"
    src = _src()
    for tieu_de in ("Ngành hàng kéo doanh thu lên/xuống",
                    "Doanh thu đến từ danh mục nào",
                    "Tăng trưởng theo tháng và ngành",
                    "Doanh thu tập trung ở khách nào"):
        assert f"<h2>{tieu_de}</h2>" in src, tieu_de


def test_co_doi_chieu_hien_dung_cau(client, conn, batch):
    """[Chữ bắt buộc, M-7 soát chặt] Ô chỉ số khi có đối chiếu: đúng NGUYÊN
    VĂN 'so cùng kỳ · {n} tháng đối chiếu ({tu} → {den})' — không đoán bừa
    bằng `or`, lấy thẳng {n}/{tu}/{den} thật từ `tinh_bao_cao`.

    Giai đoạn 3: API phải trả ĐÚNG {n}/{tu}/{den} của `tinh_bao_cao`, và
    React ghép câu từ đúng ba trường đó."""
    _hai_nam(conn, batch)
    ck = tinh_bao_cao(conn, 2026).cung_ky
    assert ck.so_thang > 0
    api = _api(client)["bc"]["cung_ky"]
    assert (api["so_thang"], api["tu"], api["den"]) == (ck.so_thang, ck.tu, ck.den)
    cau = "so cùng kỳ · {ck.so_thang} tháng đối chiếu ({ck.tu} → {ck.den})"
    assert cau in _src(), f"thiếu đúng câu: {cau!r}"


def test_khong_co_doi_chieu_hien_dung_cau(client, conn, batch):
    """[Chữ bắt buộc] Không có tháng đối chiếu: 'chưa có cùng kỳ để so'.

    Giai đoạn 3: API nói "không có đối chiếu" (so_thang 0 hoặc không có dòng
    cùng kỳ) — đúng điều kiện mà React in hai câu bắt buộc."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _ban(conn, batch, date(2026, 5, 11), "AA01")
    assert client.get("/bao-cao?ky=2026").status_code == 200
    ck = _api(client)["bc"]["cung_ky"]
    assert ck is None or ck["so_thang"] <= 0
    src = _src()
    # Ô chỉ số: nhánh `!ck || ck.so_thang <= 0` in đúng câu.
    assert re.search(r"if \(!ck \|\| ck\.so_thang <= 0\) return <>chưa có cùng kỳ để so", src)
    # Khối "Ngành hàng kéo doanh thu lên/xuống" cũng phải nói ra, KHÔNG ẩn
    # tiêu đề: tiêu đề đứng TRƯỚC (ngoài) nhánh điều kiện, câu nằm ở nhánh
    # "không có".
    # Khoảng xem: điều kiện gộp dạng Kỳ (`ck.so_thang > 0`) và dạng Tháng /
    # Khoảng (`chinh?.co`); nhánh rỗng vẫn nói ra cho CẢ HAI dạng.
    m = re.search(r"<h2>Ngành hàng kéo doanh thu lên/xuống</h2></div>\s*"
                  r"\{\(theoKy \? ck && ck\.so_thang > 0 : chinh\?\.co\) \? <>.*?</> : "
                  r'<p className="phu">\{theoKy \? "Kỳ này không có tháng nào để so cùng kỳ\." : ', src, re.S)
    assert m, "tiêu đề khối đóng góp phải ở ngoài điều kiện, và nhánh rỗng phải nói ra"


def test_ty_suat_so_bang_diem_khong_bang_phan_tram(client, conn, batch):
    """[M-7 soát chặt] Tỷ suất so cùng kỳ dùng chữ 'điểm' — kiểm NGAY TRONG
    ô chỉ số 'Tỷ suất lãi gộp', không phải bất kỳ đâu trên trang (một chữ
    'điểm' lạc ở khối khác vẫn làm test cũ xanh giả).

    Giai đoạn 3: số API đưa cho ô đó là HIỆU (`chenh_ty_suat` = tỷ suất −
    tỷ suất cùng kỳ), không phải tỷ lệ tăng; và React truyền đúng trường đó
    với đơn vị " điểm" trong CHÍNH ô 'Tỷ suất lãi gộp'."""
    _hai_nam(conn, batch)
    ck = _api(client)["bc"]["cung_ky"]
    assert ck["chenh_ty_suat"] is not None
    assert ck["chenh_ty_suat"] == pytest.approx(ck["ty_suat"] - ck["ty_suat_ck"])
    m = re.search(r'<div className="nhan">Tỷ suất lãi gộp</div>(.*?)<div className="o-kpi">',
                  _src(), re.S)
    assert m, "không tìm thấy ô chỉ số Tỷ suất lãi gộp"
    khoi = m.group(1)
    assert 'tang={ck?.chenh_ty_suat ?? null} don_vi=" điểm"' in khoi
    assert 'don_vi="%"' not in khoi, "tỷ suất phải so bằng ĐIỂM, không phải %"


def test_nganh_trong_khop_chu_view_tra_ra(conn, batch):
    """[CRITICAL] NGANH_TRONG là CHỖ THỨ HAI viết nhãn '(chưa phân loại)' —
    phải khớp TỪNG CHỮ với biểu thức của mart.ban_theo_nganh_thang (029
    §3.1). Mã hàng KHÔNG có trong core.dim_product (LEFT JOIN -> NULL) phải
    rơi vào đúng MỘT ô '(chưa phân loại)' sau khi nhom_theo_nganh gộp lại,
    không tách thành hai ô khác nhãn."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _ban(conn, batch, date(2026, 5, 11), "AA01")
    # CC01 không có dòng nào trong core.dim_product -> food_category_name NULL.
    _ban(conn, batch, date(2026, 5, 12), "CC01", khach="000000009293", n=99)

    bc = tinh_bao_cao(conn, 2026)
    dong_view = conn.execute(
        """SELECT nganh FROM mart.ban_theo_nganh_thang
           WHERE thang = '2026-05' AND nganh NOT IN ('Đồ khô')""").fetchall()
    assert dong_view, "cần có dòng cho mã CC01 không phân loại"
    assert dong_view[0][0] == NGANH_TRONG

    nganh_trong = [nk for nk in bc.nganh_ky if nk.nganh == NGANH_TRONG]
    assert len(nganh_trong) == 1, "phải gộp về đúng MỘT ngành '(chưa phân loại)'"

    nhom = nhom_theo_nganh(bc.nganh_ky, bc.hang_theo_nganh)
    dong_trong = next(t for t in nhom if t[0] == NGANH_TRONG)
    ma_trong = [ma for ma, _ten, _dt in dong_trong[3]]
    assert "CC01" in ma_trong


def test_khong_ve_hien_dung_cau_khi_co_doanh_thu_am(client, conn, batch):
    """[Chữ bắt buộc, phán quyết controller] Ngành có TỔNG ÂM (không chỉ mã
    lẻ âm) cũng phải rơi vào 'Không vẽ' — chữ chính xác đã chốt:
    'Không vẽ: ¥{khong_ve:,} của {so_ma_khong_ve} mã (doanh thu âm hoặc
    bằng 0, hoặc thuộc ngành có tổng âm)'.

    Giai đoạn 3: API trả số tiền bị bỏ THẬT (ngành Phí −¥4.500) và số mã;
    React in đúng câu đã chốt từ hai trường đó."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _ban(conn, batch, date(2026, 5, 11), "AA01")
    _nganh(conn, batch, "PH01", "Phí")
    _ban(conn, batch, date(2026, 5, 11), "PH01", khach="000000009294",
         amount=-5_000, tax=-500, gp=-1_000, n=77)
    co = _api(client)["co"]
    assert co["khong_ve"] == -4_500 and co["so_ma_khong_ve"] == 1
    assert ("Không vẽ: {yen(d.co.khong_ve)} của {d.co.so_ma_khong_ve} mã "
            "(doanh thu âm hoặc bằng 0, hoặc thuộc ngành có tổng âm)") in _src()


def test_khong_hien_khong_ve_khi_khong_co_am(client, conn, batch):
    """Giai đoạn 3: không có doanh thu âm -> `khong_ve` = 0, và React chỉ in
    dòng "Không vẽ" khi `khong_ve !== 0`."""
    _hai_nam(conn, batch)
    assert _api(client)["co"]["khong_ve"] == 0
    assert '{d.co.khong_ve !== 0 && <p className="phu">Không vẽ:' in _src()


def test_pareto_cau_tom_tat(client, conn, batch):
    """[Chữ bắt buộc, sửa vòng soát cuối M2] '10 khách lớn nhất = {x}%
    doanh thu kỳ này, trên {so_khach} khách có phát sinh trong kỳ' — KHÔNG
    phải 'khách có doanh thu': `so_khach` đếm mọi khách có dòng trong
    `mart.dong_ban`, kể cả khách net <= 0 (赤伝 có thể làm net âm/bằng
    không), nên gọi họ "có doanh thu" là sai.

    Giai đoạn 3: API trả `luy_ke_top10` và `so_khach` = 12; React ghép câu."""
    for i in range(12):
        khach = f"00000000{9300 + i}"
        _ban(conn, batch, date(2026, 5, 11), "AA01", khach=khach,
             amount=(110_000 + i * 1_000), tax=10_000, gp=30_000, n=i)
    tt = _api(client)["bc"]["tap_trung"]
    assert tt["so_khach"] == 12 and 0 < tt["luy_ke_top10"] < 1
    src = _src()
    assert "10 khách lớn nhất = <b>{p1(bc.tap_trung.luy_ke_top10)}</b>" in src
    assert "doanh thu kỳ này, trên {so(bc.tap_trung.so_khach)} khách có phát sinh trong kỳ" in src
    assert "khách có doanh thu" not in src


def test_nhiet_chu_giai_co_khong_co_cung_ky(client, conn, batch):
    """[Chữ bắt buộc] Chú giải bản đồ nhiệt có 'không có cùng kỳ'.

    Giai đoạn 3: chú giải là mã React — kiểm nó nằm trong khối chú giải NGAY
    SAU bảng nhiệt (không phải một chữ lạc ở khối khác), cạnh đúng ô màu
    `bac-khong_ck` mà ô nhiệt bậc đó dùng."""
    _hai_nam(conn, batch)
    assert _api(client)["nh"]["co"] is True
    m = re.search(r'<table className="nhiet-bang">.*?</table>.*?<div className="chu-giai bc-cg">(.*?)</div>',
                  _src(), re.S)
    assert m, "không tìm thấy chú giải của bảng nhiệt"
    assert '<i className="mau bac-khong_ck" /> không có cùng kỳ' in m.group(1)


def test_khong_co_ma_mau_hex_trong_template():
    """Giai đoạn 3: "template" nay là mã React + CSS của màn Báo cáo — màu
    chỉ đi qua biến CSS (hai khối màu tối của kome.css), không mã hex nào."""
    tep = sorted(THU_MUC_GD.glob("*.tsx")) + sorted(THU_MUC_GD.glob("*.css"))
    assert NGUON in tep and (THU_MUC_GD / "bao_cao.css") in tep
    for f in tep:
        chu = f.read_text(encoding="utf-8")
        # Loại trừ &#... (thực thể HTML) và href="#..." (neo trong trang).
        loc = re.sub(r"&#\w+;", "", chu)
        loc = re.sub(r'href="#[^"]*"', "", loc)
        xau = re.findall(r"#[0-9a-fA-F]{3,8}\b", loc)
        assert xau == [], f"mã màu hex lọt vào {f.name}: {xau}"


def test_moi_rect_circle_du_lieu_co_title(client, conn, batch):
    """[M-7 soát chặt] Mọi <rect>/<circle> DỮ LIỆU trong các SVG (đóng góp,
    cây ô, Pareto — bản đồ nhiệt nay là <table>, xem I-2/test riêng bên
    dưới) phải có <title> ghi số thật. Bắt CẢ dạng tự đóng (`<rect .../>`,
    không thể mang <title> con) lẫn cặp mở/đóng thiếu <title> — bản trước
    chỉ bắt cặp mở/đóng, một phần tử tự đóng lọt qua hoàn toàn không bị
    phát hiện.

    Giai đoạn 3: SVG vẽ bằng React — kiểm mã nguồn của từng SVG (thêm cả
    biểu đồ 12 tháng, cũng có cột/điểm dữ liệu), và kiểm API có dữ liệu để
    các SVG đó THẬT SỰ được vẽ với bộ dữ liệu này."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    _hai_nam(conn, batch)
    _nganh(conn, batch, "PH01", "Phí")
    _ban(conn, batch, date(2026, 5, 11), "PH01", khach="000000009294",
         amount=-5_000, tax=-500, gp=-1_000, n=77)
    for i in range(12):
        khach = f"00000000{9300 + i}"
        _ban(conn, batch, date(2026, 5, 20), "AA01", khach=khach,
             amount=(50_000 + i * 1_000), tax=5_000, gp=15_000, n=200 + i)

    d = _api(client)
    assert d["bd"]["cot"] and d["dg"]["thanh"] and d["co"]["nganh"] and d["pa"]["cot"]
    src = _src()
    nhan = ("Doanh thu và tỷ suất lãi gộp theo tháng, kèm cùng kỳ năm trước",
            "Chênh lệch doanh thu theo ngành so cùng kỳ",
            "Doanh thu theo ngành hàng và mặt hàng",
            "Doanh thu và luỹ kế của 20 khách hàng lớn nhất")
    for n in nhan:
        m_svg = re.search(rf'aria-label="{re.escape(n)}">(.*?)</svg>', src, re.S)
        assert m_svg, f"không tìm thấy SVG '{n}'"
        khoi = m_svg.group(1)
        dem = 0
        for tag in ("rect", "circle"):
            # Dạng tự đóng — không thể chứa <title> con, nên CHÍNH việc tự
            # đóng đã là lỗi cho một phần tử dữ liệu.
            for m in re.finditer(rf"<{tag}\b[^>]*?/>", khoi):
                pytest.fail(f"<{tag}> tự đóng trong '{n}', không thể có "
                            f"<title>: {m.group(0)[:120]!r}")
            for m in re.finditer(rf"<{tag}\b[^>]*>((?:(?!</{tag}>).)*)</{tag}>", khoi, re.S):
                dem += 1
                assert "<title>" in m.group(1), \
                    f"<{tag}> trong '{n}' không có <title>: {m.group(0)[:120]!r}"
        assert dem, f"SVG '{n}' không có <rect>/<circle> dữ liệu nào — regex hỏng?"


def _hai_nam_do_dang(conn, batch, ma="AA01", ngành="Đồ khô"):
    """Biến thể của `_hai_nam` DỰNG RIÊNG cho test dưới: đủ ba trạng thái ô
    nhiệt trong CÙNG một lần mở trang — vài tháng có tăng trưởng thật (bậc
    màu + %), một tháng THẬT SỰ không bán ở CẢ HAI năm (2026-03, "khong_ban"),
    và kỳ dừng ở 2026-05 (không bán 06/07) để có tháng "chua_toi"."""
    _nganh(conn, batch, ma, ngành)
    n = 0
    for y, th in ((2024, 8), (2024, 9), (2024, 10), (2024, 11), (2024, 12),
                  (2025, 1), (2025, 2), (2025, 4), (2025, 5), (2025, 6), (2025, 7)):
        n += 1
        _ban(conn, batch, date(y, th, 11), ma, amount=110_000, tax=10_000, gp=30_000, n=n)
    for y, th in ((2025, 8), (2025, 9), (2025, 10), (2025, 11), (2025, 12),
                  (2026, 1), (2026, 2), (2026, 4), (2026, 5)):
        n += 1
        _ban(conn, batch, date(y, th, 11), ma, amount=110_000, tax=10_000, gp=30_000, n=n)


def test_ban_do_nhiet_la_bang_html_co_scope(client, conn, batch):
    """[I-1, I-2, M-7/N-4 soát chặt] Bản đồ nhiệt là <table>, không phải
    SVG — có <th scope> cho cả hàng lẫn cột. Dữ liệu dựng đủ CẢ BA trạng
    thái thật (tăng trưởng có %, không bán 2026-03, chưa tới 2026-06/07)
    trong MỘT lần mở trang — không suy luận qua chú giải hay qua lời gọi
    `ve_nhiet` rời.

    Giai đoạn 3: (a) API trả đủ ba trạng thái đó cho CÙNG một ngành; (b) mã
    React vẽ `<table className="nhiet-bang">` có `scope`, và các cụm chữ
    "không bán tháng này"/"chưa tới tháng" nằm trong hàm vẽ Ô (`ONhiet`),
    không chỉ ở chú giải (chú giải cũng có các cụm đó — kiểm cả trang là
    xanh giả). [N-4] % trong Ô và trong title đi qua CÙNG một hàm `dau`
    (một chữ số thập phân) — hai độ làm tròn khác nhau là ô và ô nổi nói
    hai con số."""
    _hai_nam_do_dang(conn, batch)
    assert client.get("/bao-cao?ky=2026").status_code == 200
    nh = _api(client)["nh"]
    o = {c["thang"]: c for h in nh["hang"] if h["nganh"] == "Đồ khô" for c in h["o"]}
    assert o["2026-03"]["bac"] == "khong_ban"
    assert o["2026-06"]["bac"] == o["2026-07"]["bac"] == "chua_toi"
    assert any(c["bac"] in ("g2", "g1", "0", "t1", "t2") and c["tang_truong"] is not None
               for c in o.values()), "cần ít nhất một ô có tăng trưởng thật"

    src = _src()
    m = re.search(r'<table className="nhiet-bang">(.*?)</table>', src, re.S)
    assert m, "không tìm thấy bảng nhiệt"
    bang = m.group(0)
    assert 'scope="col"' in bang and 'scope="row"' in bang
    assert "<ONhiet " in bang
    o_ham = re.search(r"function ONhiet\(.*?\n}\n", src, re.S)
    assert o_ham, "không tìm thấy hàm vẽ ô nhiệt"
    ham = o_ham.group(0)
    assert "không bán tháng này" in ham
    assert "chưa tới tháng" in ham
    assert re.search(r"title=\{`\$\{nhan\}: \$\{dau\(o\.tang_truong\)\}% so cùng kỳ[^`]*`\}>"
                     r"\{dau\(o\.tang_truong\)\}%</td>", ham), \
        "ô nhiệt và title phải in % bằng CÙNG một hàm làm tròn"
    assert re.search(r"const dau = .*toFixed\(1\)", src), "% phải có đúng MỘT chữ số thập phân"


def test_nhiet_khong_gan_nhan_sai_thang_chua_toi_hay_khong_ban(conn, batch):
    """[CRITICAL, I-1] Kỳ ĐANG DIỄN RA (chưa đủ 12 tháng dữ liệu): tháng SAU
    ngày bán cuối cùng phải là 'chua_toi' (không phải 'khong_ck' — kỳ CHƯA
    ĐI TỚI tháng đó, không phải 'thiếu so sánh'), và một ngành có bán ở kỳ
    trước nhưng THẬT SỰ không bán gì ở một tháng đã qua của kỳ này phải là
    'khong_ban' — cả hai đều KHÁC 'khong_ck' (dành cho tháng có doanh thu
    nhưng không có dòng cùng kỳ)."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    # Kỳ 2026 (2025-08..2026-07) chỉ có MỘT tháng bán (2025-08) — kỳ dở dang.
    _ban(conn, batch, date(2025, 8, 15), "AA01")
    bc = tinh_bao_cao(conn, 2026)
    thang_cuoi = bc.ky.ngay_cuoi.strftime("%Y-%m")
    assert thang_cuoi == "2025-08"
    thang_ky = [f"2025-{t:02d}" for t in range(8, 13)] + [f"2026-{t:02d}" for t in range(1, 8)]
    nh = ve_nhiet(bc.nganh_thang, thang_ky, thang_cuoi)
    o = {c["thang"]: c for c in nh["o"] if c["nganh"] == "Đồ khô"}
    assert o["2025-08"]["bac"] not in ("chua_toi",), "tháng có bán không được là 'chưa tới'"
    assert o["2025-09"]["bac"] == "chua_toi", "tháng SAU ngày bán cuối phải là 'chưa tới'"
    assert o["2026-07"]["bac"] == "chua_toi"


def test_nhiet_khong_ban_that_su_khac_khong_co_cung_ky(conn, batch):
    """[I-1] Một ngành bán liên tục hai năm rồi NGỪNG hẳn một tháng cụ thể ở
    năm sau (0 đồng CẢ hai năm ở đúng tháng đó không đúng kịch bản này — ở
    đây ta chỉ cần MỘT tháng đã qua, trong dải kỳ, mà ngành không có dòng
    nào cả hai phía) phải mang bậc 'khong_ban', không lẫn với 'khong_ck'."""
    _nganh(conn, batch, "AA01", "Đồ khô")
    # Bán đủ 12 tháng của kỳ 2026 TRỪ tháng 2026-03 — kỳ đã đi hết
    # (ngay_cuoi = 2026-07-31) nên 2026-03 không phải "chưa tới".
    for i in range(12):
        th = (8 - 1 + i) % 12 + 1
        y = 2025 + (8 - 1 + i) // 12
        if f"{y}-{th:02d}" == "2026-03":
            continue
        _ban(conn, batch, date(y, th, 11), "AA01", n=i + 1)
    bc = tinh_bao_cao(conn, 2026)
    thang_cuoi = bc.ky.ngay_cuoi.strftime("%Y-%m")
    assert thang_cuoi == "2026-07"
    thang_ky = [f"2025-{t:02d}" for t in range(8, 13)] + [f"2026-{t:02d}" for t in range(1, 8)]
    nh = ve_nhiet(bc.nganh_thang, thang_ky, thang_cuoi)
    o = {c["thang"]: c for c in nh["o"] if c["nganh"] == "Đồ khô"}
    assert o["2026-03"]["bac"] == "khong_ban"


def test_cay_o_khong_de_nhan_nganh_len_ma_khi_co_ma_tach_rieng(conn, batch):
    """[I-3] Khi ngành tách được mã (n['ma'] không rỗng), `ve_cay_o` vẫn trả
    đủ dữ liệu để template BỎ nhãn ngành (kiểm ở mức HTML bằng cách ngành có
    mã thì mọi `<text>` bên trong ô ngành đó — nếu có — phải là nhãn MÃ, tức
    `m['nhan']`); ô quá nhỏ phải có `nhan=None` để không vẽ chữ tràn."""
    nhom = [("Gạo", 1000, 0.1, [("G1", "Gạo ST25", 900), ("G2", "Gạo Jasmine", 100)])]
    cq = ve_cay_o(nhom, rong=720, cao=360)
    n = cq["nganh"][0]
    assert n["ma"], "ngành phải tách được mã ở khung 720x360"
    for m in n["ma"]:
        assert "nhan" in m
    # Một ô quá nhỏ (khung tí hon) không được gán nhãn nào.
    cq_nho = ve_cay_o(nhom, rong=20, cao=10)
    n_nho = cq_nho["nganh"][0]
    for m in n_nho["ma"]:
        assert m["nhan"] is None, "ô quá nhỏ phải có nhan=None, không cắt bừa"


def test_hai_khoi_mau_toi_trong_css_van_xanh():
    """[CLAUDE.md] Token màu mới (--nhiet-*, --duong-ck) phải thêm vào CẢ HAI
    khối tối và giữ chúng GIỐNG HỆT nhau — chạy lại chính test canh có sẵn."""
    from tests.test_giao_dien import test_hai_khoi_mau_toi_trong_css_GIONG_HET_NHAU as t
    t()


def test_ba_khoi_ngan_sach_5a_va_bang_nhan_vien_con_nguyen(client, conn, batch):
    """Bộ test 5a hiện có phải xanh nguyên — kiểm nhanh các khối đó vẫn còn
    mặt trên trang.

    Giai đoạn 3: API có đủ dữ liệu cho ba khối ngân sách + bảng người phụ
    trách, và mã React có đủ tiêu đề. (Bảng "Kết quả theo từng nhân viên"
    của bản Jinja nay là "Tiến độ theo nhân viên" + bảng chi tiết trong
    <details> — cùng dữ liệu `td.nguoi`.)"""
    _ban(conn, batch, date(2026, 7, 31), "XT07", sale="0104")
    conn.execute(
        "INSERT INTO app.ngan_sach (salesperson_code, thang, muc_tieu) "
        "VALUES (%s, %s, %s)", ("0104", date(2026, 7, 1), 6_000_000))
    # 041: tiến độ công ty đọc ngân sách CÔNG TY nhập thẳng.
    conn.execute("INSERT INTO app.ngan_sach_cong_ty (thang, doanh_thu) VALUES ('2026-07-01', 6000000)")
    conn.commit()
    assert client.get("/bao-cao?ky=2026").status_code == 200
    d = _api(client)
    assert d["td"]["co_ngan_sach"] is True
    assert any(n["ma"] == "0104" and n["muc_tieu"] == 6_000_000 for n in d["td"]["nguoi"])
    assert d["lk"]["co"] is True
    assert any(n["ma"] == "0104" for n in d["bc"]["nhan_vien"])
    src = _src()
    for chu in ("Tiến độ ngân sách tháng", "Luỹ kế thực tế so với nhịp ngân sách",
                "Tiến độ theo nhân viên", "Bảng số chi tiết theo nhân viên",
                "Theo người phụ trách khách"):
        assert chu in src, chu


def test_bang_chi_tiet_theo_thang_dong_trong_details(client, conn, batch):
    """Giai đoạn 3: bảng chi tiết theo tháng vẫn nằm trong <details> (đóng
    sẵn), dòng lấy từ `bc.thang` của API."""
    _hai_nam(conn, batch)
    assert len(_api(client)["bc"]["thang"]) == 12
    src = _src()
    # Khoảng xem: nhãn "theo ngày / theo tháng" đổi theo chuỗi của API.
    assert re.search(r"<details[^>]*>\s*<summary>Bảng số chi tiết theo \{theoNgay \? \"ngày\" : \"tháng\"\}", src)
    assert "<details open" not in src


# ---- Vòng soát 1 vòng 2 -----------------------------------------------------

def _nk(nganh, chenh_lech, tang_truong=None):
    return NganhKy(nganh=nganh, doanh_thu=1000, lai_gop=100, dt_doi_chieu=900,
                   dt_cung_ky=900, chenh_lech=chenh_lech, tang_truong=tang_truong)


def test_dong_gop_nhan_so_tien_khong_tran_ngoai_khung_khi_thanh_dai_nhat(conn):
    """[CRITICAL, N-1] Thanh CHIẾM TRỌN nửa khung (tỷ lệ 100% so với
    max_abs) từng làm nhãn số tiền của CHÍNH NÓ tràn khỏi viewBox — đặt cứng
    'đầu mút + 4px' không chừa chỗ cho chữ. Toạ độ `nhan_x` phải luôn nằm
    trong `[0, rong]`, thử với đủ số tiền lớn (nhiều chữ số) ở CẢ hai phía."""
    dong = [_nk("Ngành dương rất dài tên", 123_456_789),
            _nk("Ngành âm cũng dài tên không kém", -98_765_432)]
    dg = ve_dong_gop(dong, rong=720)
    assert dg["co"] is True
    for t in dg["thanh"]:
        assert 0 <= t["nhan_x"] <= dg["rong"], \
            f"nhan_x={t['nhan_x']} tràn khỏi khung [0, {dg['rong']}] ở ngành {t['nganh']}"


def test_dong_gop_ten_nganh_o_phia_doi_dien_thanh():
    """[M-1] Tên ngành phải đứng ở phía ĐỐI DIỆN trục so với chính thanh
    của nó — thanh dương (kéo phải trục) thì tên bên TRÁI trục, thanh âm
    (kéo trái) thì tên bên PHẢI. Kiểm gián tiếp qua toạ độ `x` của thanh so
    với `x0`: bài test này khẳng định đúng bất biến hình học mà template
    dùng (`x0 + 4 if t.am else x0 - 4`), không phải một chuỗi cụ thể."""
    dong = [_nk("Dương", 500), _nk("Âm", -500)]
    dg = ve_dong_gop(dong)
    duong = next(t for t in dg["thanh"] if not t["am"])
    am = next(t for t in dg["thanh"] if t["am"])
    # Thanh dương nằm bên PHẢI trục (x == x0); tên của nó phải render ở toạ
    # độ x0 - 4 (bên TRÁI) theo công thức mới trong template — khẳng định
    # gián tiếp bằng cách kiểm thanh dương có x == x0 và thanh âm có x < x0,
    # tức "phía đối diện" của mỗi thanh nằm đúng bên nào.
    assert duong["x"] == dg["x0"]
    assert am["x"] < dg["x0"]


def test_pareto_truc_pct_tra_toa_do_khong_con_hang_so_cung_trong_template(conn, batch):
    """[N-3] `ve_pareto` phải tự trả toạ độ Y của ba vạch 0/50/100% — không
    còn hằng số lề 16/34 chép tay trong Jinja."""
    from kome.bao_cao import KhachTapTrung, TapTrung
    from kome.ve_phan_tich import ve_pareto
    tt = TapTrung(dong=[KhachTapTrung(ma="K1", ten="K1", doanh_thu=100,
                                      thu_hang=1, ty_trong=1.0, luy_ke=1.0)],
                  so_khach=1, luy_ke_top10=None)
    pa = ve_pareto(tt, rong=720, cao=260)
    assert len(pa["truc_pct"]) == 3
    ys = [t["y"] for t in pa["truc_pct"]]
    assert ys == sorted(ys, reverse=True), \
        "0% phải ở DƯỚI (y lớn hơn), 100% ở TRÊN (y nhỏ hơn)"
    assert pa["truc_pct"][0]["nhan"] == "0%"
    assert pa["truc_pct"][-1]["nhan"] == "100%"


def test_khong_ve_hien_du_khi_khong_co_gi_de_ve(client, conn, batch):
    """[M-3] Dòng 'Không vẽ' đứng NGOÀI điều kiện `co.co` — cả kỳ chỉ có
    ĐÚNG MỘT ngành và ngành đó ÂM (cây ô rỗng hoàn toàn, co.co=False) vẫn
    phải in ra số tiền bị bỏ, không được im lặng chỉ vì không có gì để
    VẼ.

    Giai đoạn 3: API trả co.co=False KÈM khong_ve thật; trong React dòng
    "Không vẽ" đứng SAU khi nhánh `d.co.co ? … : …` đã đóng."""
    _nganh(conn, batch, "PH01", "Phí")
    _ban(conn, batch, date(2026, 5, 11), "PH01", amount=-5_000, tax=-500, gp=-1_000)
    co = _api(client)["co"]
    assert co["co"] is False
    assert co["khong_ve"] == -4_500 and co["so_ma_khong_ve"] == 1
    assert re.search(r'\{d\.co\.co \? <svg.*?</svg> : <p className="phu">Chưa có dữ liệu để vẽ khối này\.</p>\}'
                     r'\s*\{d\.co\.khong_ve !== 0 && <p className="phu">Không vẽ:', _src(), re.S), \
        "dòng 'Không vẽ' phải nằm NGOÀI nhánh co.co"


