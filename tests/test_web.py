import os
import time
from fastapi.testclient import TestClient
from kome.web.app import create_app

def test_trang_suc_khoe_mo_duoc(conn, test_db_url):
    client = TestClient(create_app(db_url=test_db_url))   # KHÔNG bao giờ để nó tự lấy DATABASE_URL
    r = client.get("/health")
    assert r.status_code == 200
    assert "在庫一覧" in r.text

def test_health_canh_bao_khi_sao_luu_qua_han(conn, test_db_url, tmp_path, monkeypatch):
    """Trang /health phải tự cảnh báo nếu bản sao lưu mới nhất cũ hơn 36 giờ,
    và hết cảnh báo khi có bản mới — sai phải hiện ngay lúc người ta còn ngồi đó."""
    monkeypatch.setenv("BACKUP_DIR", str(tmp_path))
    client = TestClient(create_app(db_url=test_db_url))

    z = tmp_path / "kome_20260101.zip"
    z.write_bytes(b"x")
    old = time.time() - 40 * 3600          # 40 giờ trước -> quá hạn
    os.utime(z, (old, old))

    r = client.get("/health")
    assert r.status_code == 200
    assert "Chưa sao lưu" in r.text

    new = time.time() - 1 * 3600           # 1 giờ trước -> còn mới
    os.utime(z, (new, new))

    r = client.get("/health")
    assert "Chưa sao lưu" not in r.text
    assert "Sao lưu gần nhất" in r.text

def test_upload_file_hong_tra_ve_loi_de_hieu(conn, test_db_url):
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_cat_cut.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200
    assert "nghi file xuất một phần" in r.text

def test_undo_qua_http_xoa_du_lieu_giu_lich_su(conn, test_db_url):
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_ok.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200

    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 177

    batch_id = conn.execute(
        "SELECT batch_id FROM meta.ingest_batch ORDER BY batch_id DESC LIMIT 1"
    ).fetchone()[0]

    r = client.post(f"/undo/{batch_id}")
    assert r.status_code == 200

    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 0

    rows = conn.execute(
        "SELECT undone_at FROM meta.ingest_batch WHERE batch_id = %s", (batch_id,)
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] is not None

def test_health_hien_lan_nap_GAN_NHAT_khong_phai_lon_nhat(conn, test_db_url):
    """[IMPORTANT] max(loaded_at), max(row_count), max(total_amount) là ba hàm
    độc lập lấy từ ba dòng khác nhau. uriage nạp hằng ngày ~843 dòng; đầu tháng
    nạp đối soát cả tháng ~18.000 dòng — từ đó /health LUÔN hiện 18.000, kể cả
    hôm nay OBC xuất cắt cụt còn 60 dòng. Trang duy nhất để biết hệ thống có
    hỏng không lại không phản ánh lần nạp gần nhất."""
    for digest, rows, total, tre in (("to", 18000, 400_000_000, "2 hours"),
                                     ("nho", 60, 900_000, "1 minute")):
        conn.execute(
            """INSERT INTO meta.ingest_batch
                 (spec_name, source_file, digest, archived_to, row_count,
                  total_amount, loaded_at, data_date)
               VALUES ('uriage', 'u.xlsx', %s, '/tmp/u.xlsx', %s, %s,
                       now() - %s::interval, DATE '2026-07-31')""",
            (digest, rows, total, tre),
        )
    conn.commit()

    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/health")
    assert r.status_code == 200
    # Đợt 2a (Task 4): /health giờ là màn gộp /kho-du-lieu, và màn đó thêm
    # khối "Lô nạp gần nhất" (Task 2/3) liệt kê MỖI lô riêng lẻ — khối đó
    # ĐÚNG PHẢI hiện cả 18.000 vì nó trả lời câu khác ("lịch sử nạp gồm
    # những gì"), không phải câu bảng trạng thái trả lời ("lần nạp GẦN NHẤT
    # của loại này là gì"). Cô lập đúng khối "Sức khoẻ dữ liệu" trước khi so.
    khoi = r.text.split("Sức khoẻ dữ liệu", 1)[1].split("Lô nạp gần nhất", 1)[0]
    assert "60" in khoi and "900,000" in khoi
    assert "18,000" not in khoi and "400,000,000" not in khoi


def test_health_liet_ke_ngay_lam_viec_bi_thieu(conn, test_db_url, batch):
    """[IMPORTANT] Không có gì khác trong hệ thống phát hiện thiếu hẳn một
    ngày: nhân viên nghỉ ốm thứ Ba, không ai kéo–thả; thứ Tư nạp bình thường,
    /health xanh hết. Ba tháng sau báo cáo thiếu một ngày và không ai truy
    được ngày nào.

    Nạp hai ngày cách nhau đúng một ngày làm việc (Hai 2026-05-11 và Tư
    2026-05-13) -> trang phải nêu đích danh thứ Ba 2026-05-12."""
    from datetime import date
    import pandas as pd
    from kome.loaders import sales

    b = batch(1)
    rows = []
    for i, d in enumerate((date(2026, 5, 11), date(2026, 5, 13))):
        rows.append({
            "slip_no": f"0799{i}", "line_seq": 1, "sales_date": d,
            "customer_code": "000000009292", "product_code": "XT07",
            "pack_code": "02", "case_qty": 1, "qty": 6, "unit_price": 5250,
            "unit_cost": 3210, "amount": 29167, "tax_amount": 2333,
            "cost": 19260, "gross_profit": 9907, "paid_amount": 0,
            "batch_id": b,
        })
    sales.load(conn, pd.DataFrame(rows), date(2026, 5, 13), b)

    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/health")
    assert r.status_code == 200
    assert "2026-05-11" in r.text and "2026-05-13" in r.text   # kỳ dữ liệu
    assert "Thiếu 1 ngày làm việc" in r.text
    assert "2026-05-12" in r.text
    # cuối tuần 2026-05-09 (Bảy) / 2026-05-10 (CN) nằm ngoài kỳ, không được kể


def test_loi_ngoai_du_kien_hien_tieng_viet_khong_lo_chuoi_ngoai_le(
        conn, test_db_url, monkeypatch):
    """Nửa NHÌN THẤY ĐƯỢC của lỗi lô mồ côi: người dùng gặp trang 500 tiếng Anh
    khó hiểu rồi thử lại và được báo 'xanh'. Lỗi ngoài dự kiến phải ra thông
    báo tiếng Việt, và KHÔNG chứa nguyên văn chuỗi ngoại lệ của thư viện."""
    # Vá ở kome.pipeline chứ không ở kome.web.app: app.py CỐ Ý nhập ingest
    # bên trong thân route, để bản chỉ-đọc trên Vercel không kéo pandas
    # (~120 MB) vào gói triển khai. Xem tests/test_bao_mat.py.
    import kome.pipeline as P

    def no_tung(*a, **kw):
        raise RuntimeError("psycopg.OperationalError: connection reset by peer")

    monkeypatch.setattr(P, "ingest", no_tung)
    client = TestClient(create_app(db_url=test_db_url), raise_server_exceptions=False)
    with open("tests/fixtures/zaiko_ok.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})

    assert r.status_code == 500
    assert "Hệ thống gặp lỗi" in r.text
    assert "Dữ liệu chưa được nạp" in r.text
    assert "connection reset by peer" not in r.text
    assert "RuntimeError" not in r.text
    assert "Traceback" not in r.text


def test_trang_phu_du_lieu_mo_duoc_va_nhom_theo_ky_cong_ty(conn, test_db_url):
    """Trang /phu-du-lieu: nhóm theo kỳ kế toán CỦA CÔNG TY (1/8 → 31/7).

    Đợt 2a (Task 4): /phu-du-lieu chỉ 301 sang /kho-du-lieu#theo-thang, và
    tiêu đề trang giờ là "Kho dữ liệu" (dùng chung cho cả ba khối cũ) —
    không còn tiêu đề riêng "Bảng phủ dữ liệu". Mọi nội dung khác (kỳ kế
    toán, cột, tổng kết) vẫn nguyên vẹn, chỉ nằm trong màn gộp."""
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/phu-du-lieu")
    assert r.status_code == 200
    assert "Kho dữ liệu" in r.text
    # Trang phải gọi kỳ theo SỐ mà công ty tự dùng (Kỳ 7), không phải năm kết thúc
    assert "Kỳ 7 (2025-08 → 2026-07)" in r.text
    assert "1/8 → 31/7" in r.text
    assert "在庫一覧" in r.text and "売上伝票データ" in r.text
    # Tổng kết kỳ
    assert "Doanh thu thuần" in r.text and "Lãi gộp" in r.text
    # Tháng chốt kỳ phải được đánh dấu
    assert "chốt kỳ" in r.text
    # Ràng buộc §2.2.1 và hạn chế của dấu "không có" phải viết ra rõ ràng
    assert "2025-03-03" in r.text
    assert "ngoài phạm vi" in r.text
    assert "cổng kiểm tra chặn" in r.text


def test_phu_du_lieu_phan_biet_bang_MAU_NEN_khong_chi_bang_ky_tu(conn, test_db_url):
    """[IMPORTANT] Trang này để LIẾC MẮT là thấy. Nếu "có" và "không" chỉ khác
    nhau ở một ký tự nhỏ thì người đọc phải dò từng ô — đúng lúc cần thấy
    ngay thì lại không thấy.

    phu_du_lieu.html (đã xoá ở Task 4) mang theo một khối <style> RIÊNG định
    nghĩa lại ba lớp này — trùng với kome.css nhưng vô hại vì cùng giá trị.
    Xoá template đó bỏ luôn bản trùng, chỉ còn định nghĩa DUY NHẤT ở
    /static/kome.css (nơi _bang_ngay.html / _bang_thang.html của màn gộp đã
    dùng từ trước) — kiểm màu nền ở đúng chỗ nó còn được định nghĩa."""
    client = TestClient(create_app(db_url=test_db_url))
    css = client.get("/static/kome.css").text.replace(" ", "")
    for lop in ("o-co", "o-khong", "o-ngoai"):
        assert f"{lop}{{background:" in css, f"thiếu màu nền cho .{lop}"
    html = client.get("/phu-du-lieu").text
    assert 'class="o o-ngoai"' in html     # tháng trước 2025-03 phải là "ngoài phạm vi"


def test_phu_du_lieu_ton_trong_db_url_va_khong_lo_thong_tin_ket_noi(
        conn, test_db_url, monkeypatch):
    """[IMPORTANT] Route nào tự gọi connect() không tham số sẽ đọc CSDL THẬT
    (291.436 dòng dữ liệu công ty) trong khi test tưởng mình đang ở CSDL thử
    nghiệm. Đặt DATABASE_URL thành rác: trang vẫn phải mở được."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://khong-ton-tai/khong-ton-tai")
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/phu-du-lieu")
    assert r.status_code == 200
    # Thông tin kết nối không được lọt ra HTML — kể cả tên CSDL.
    assert "postgres" not in r.text
    assert "kome_test" not in r.text
    assert "khong-ton-tai" not in r.text


def test_ba_trang_deu_co_thanh_dieu_huong_di_qua_lai(conn, test_db_url):
    """Mọi trang phải đi lại được với nhau qua sidebar.

    Đợt 2a (Task 4): /health và /phu-du-lieu gộp vào /kho-du-lieu, nên
    sidebar giờ chỉ còn MỘT mục "Kho dữ liệu" thay vì ba mục riêng (trước
    đây từ /health không có đường nào sang bảng phủ dữ liệu — giờ cả hai
    nằm trên cùng một màn nên không cần liên kết riêng nữa). Xem thêm
    tests/test_giao_dien.py::test_sidebar_hien_du_nam_muc_va_ba_nhom."""
    client = TestClient(create_app(db_url=test_db_url))
    for duong in ("/", "/kho-du-lieu"):
        r = client.get(duong)
        assert r.status_code == 200, duong
        for link in ('href="/"', 'href="/kho-du-lieu"'):
            assert link in r.text, f"{duong} thiếu {link}"


def test_ba_trang_doc_duoc_o_che_do_toi(conn, test_db_url):
    """[IMPORTANT] Không khai màu nền/màu chữ thì máy để giao diện TỐI sẽ vẽ
    chữ sẫm trên nền sẫm — trang cảnh báo mà không đọc được thì không cảnh
    báo được gì. Đã kiểm tận mắt.

    CSS giờ nằm ở /static/kome.css (tách ra ở Task 1, xem
    tests/test_giao_dien.py) chứ không còn nằm trong HTML — nên bài kiểm
    tra soi cả CSS thật sự được phục vụ, không chỉ trang HTML trỏ tới nó."""
    client = TestClient(create_app(db_url=test_db_url))
    css = client.get("/static/kome.css").text.replace(" ", "")
    assert "prefers-color-scheme:dark" in css
    assert "body{" in css and "background:var(--nen)" in css
    assert "color:var(--chu)" in css
    for duong in ("/", "/health", "/phu-du-lieu"):
        text = client.get(duong).text
        assert 'name="color-scheme"' in text, duong
        assert "/static/kome.css" in text, duong


def test_trang_loi_cung_doc_duoc_o_che_do_toi(conn, test_db_url, monkeypatch):
    """CSS nằm ở /static/kome.css (Task 1) — trang lỗi chỉ cần trỏ tới đó,
    không còn tự mang theo biến màu TỐI trong HTML của chính nó."""
    import kome.pipeline as P

    def no_tung(*a, **kw):
        raise RuntimeError("hỏng")

    monkeypatch.setattr(P, "ingest", no_tung)
    client = TestClient(create_app(db_url=test_db_url), raise_server_exceptions=False)
    with open("tests/fixtures/zaiko_ok.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 500
    assert 'name="color-scheme"' in r.text
    assert "/static/kome.css" in r.text


def test_health_hien_gach_ngang_thay_vi_yen_0_cho_file_khong_mang_tien(
        conn, test_db_url):
    """[IMPORTANT] 商品データ / 仕入先 / 取引単価データ không mang giá trị tiền:
    total_column để trống CÓ CHỦ Ý. Hiện "¥0" ở cột Tổng tiền đúng về kỹ thuật
    nhưng người đọc tưởng hệ thống đếm hụt tiền và đi báo một lỗi không có."""
    import re

    from kome.pipeline import SPECS

    khong_tien = [s.display_name for s in SPECS.values() if s.total_column is None]
    co_tien = [s.display_name for s in SPECS.values() if s.total_column is not None]
    assert khong_tien and co_tien

    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/health")
    assert r.status_code == 200

    # Ô cuối mỗi dòng của bảng = cột "Tổng tiền".
    o_cuoi = {}
    for dong in re.findall(r"<tr>\s*(<td>.*?)</tr>", r.text, re.S):
        o = re.findall(r"<td>(.*?)</td>", dong, re.S)
        if len(o) >= 4:
            o_cuoi[o[0].strip()] = o[-1].strip()

    for ten in khong_tien:
        assert "—" in o_cuoi[ten] and "¥" not in o_cuoi[ten], \
            f"{ten}: phải hiện — chứ không phải ¥0, đã hiện {o_cuoi[ten]!r}"
    for ten in co_tien:
        assert o_cuoi[ten].startswith("¥"), f"{ten}: vẫn phải hiện số tiền"

def test_trang_chu_canh_bao_hom_nay_chua_co_du_lieu(conn, test_db_url, monkeypatch):
    """Sau 13:30 mà chưa nạp gì thì trang chủ phải nói thẳng, kèm tên 3 file cần xuất.

    Đặt ở `/` chứ không chỉ ở /health: /health là trang người ta mở khi ĐÃ
    nghi ngờ có chuyện, còn đây là chuyện phải đập vào mắt khi chưa nghi gì.
    """
    from datetime import datetime
    from kome.tuoi_du_lieu import MUI_GIO
    monkeypatch.setattr("kome.tuoi_du_lieu._bay_gio",
                        lambda: datetime(2026, 9, 17, 14, 0, tzinfo=MUI_GIO))
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/")
    assert r.status_code == 200
    assert "Chưa có dữ liệu hôm nay" in r.text
    for ten in ("在庫一覧", "得意先全情報", "売上伝票データ"):
        assert ten in r.text

def test_trang_chu_khong_bao_dong_truoc_gio_chot(conn, test_db_url, monkeypatch):
    """8 giờ sáng chưa ai xuất file là bình thường — không được đỏ."""
    from datetime import datetime
    from kome.tuoi_du_lieu import MUI_GIO
    monkeypatch.setattr("kome.tuoi_du_lieu._bay_gio",
                        lambda: datetime(2026, 9, 17, 8, 0, tzinfo=MUI_GIO))
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/")
    assert r.status_code == 200
    assert "Chưa có dữ liệu hôm nay" not in r.text
    assert "Chưa tới giờ xuất file" in r.text

def test_trang_phu_du_lieu_co_bang_theo_tung_ngay(conn, test_db_url, monkeypatch):
    """Bảng tháng không trả lời được "hôm qua có sót ngày nào không"."""
    from datetime import datetime
    from kome.tuoi_du_lieu import MUI_GIO
    monkeypatch.setattr("kome.tuoi_du_lieu._bay_gio",
                        lambda: datetime(2026, 9, 17, 14, 0, tzinfo=MUI_GIO))
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/phu-du-lieu")
    assert r.status_code == 200
    assert "90 ngày gần nhất" in r.text
    assert "2026-09-17" in r.text          # dòng đầu là hôm nay
    assert "2026-06-20" in r.text          # dòng cuối, đủ 90 ngày
