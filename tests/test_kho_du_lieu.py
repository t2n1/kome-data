"""Test màn Kho dữ liệu — màn gộp của /nap + /health + /phu-du-lieu."""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from kome.web.app import create_app


def _lo(conn, spec_name, ten_file, ngay, row_count, digest, tong_tien=0):
    """Một dòng meta.ingest_batch, trả về batch_id."""
    return conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count,
              total_amount, data_date)
           VALUES (%s, %s, %s, 'test', %s, %s, %s)
           RETURNING batch_id""",
        (spec_name, ten_file, digest, row_count, tong_tien, ngay)).fetchone()[0]


def _ban_hang(conn, batch_id, phieu):
    """Upsert dòng bán hàng theo ĐÚNG khoá thật (slip_no, line_seq, source).

    Cùng khoá thì lô sau dán batch_id của mình lên dòng của lô trước — chính
    là cơ chế biến một lần bấm Hoàn tác thành "mất cả tháng doanh thu"."""
    for slip, seq in phieu:
        conn.execute(
            """INSERT INTO core.fact_sales_line
                 (slip_no, line_seq, sales_date, customer_code, product_code,
                  amount, batch_id, source)
               VALUES (%s, %s, '2026-09-01', 'C1', 'P1', 1000, %s, 'uriage')
               ON CONFLICT (slip_no, line_seq, source)
                 DO UPDATE SET batch_id = EXCLUDED.batch_id""",
            (slip, seq, batch_id))


def _nha_cung_cap(conn, batch_id, so_dong):
    conn.execute(
        """INSERT INTO core.dim_supplier (supplier_code, supplier_name, batch_id)
           SELECT 'S' || g, 'NCC ' || g, %s FROM generate_series(1, %s) g""",
        (batch_id, so_dong))


def _khoi_hoan_tac(html: str) -> dict[int, str]:
    """Tách từng khối <details> hoàn tác, khoá theo số lô trong form action.

    Kiểm cả trang bằng `in html` là không đủ khi có NHIỀU lô: một câu đúng
    cho lô này vẫn làm test xanh trong khi lô kia nói sai."""
    khoi = {}
    for m in re.finditer(r'<details class="hoan-tac">(.*?)</details>', html, re.S):
        khoi[int(re.search(r"/undo/(\d+)", m.group(1)).group(1))] = m.group(1)
    return khoi

# Mỗi khối một dấu hiệu nhận biết ổn định (không phải chuỗi trang trí dễ đổi).
DAU_HIEU_KHOI = {
    "tuoi du lieu": "hom-nay",
    "nap": 'id="nap"',
    "suc khoe": "Sức khoẻ dữ liệu",
    "bang 7 loai": "在庫一覧",
    "bang theo ngay": "theo-ngay",
    "bang theo thang": 'id="theo-thang"',
}


def test_man_kho_du_lieu_co_du_cac_khoi(conn, test_db_url):
    """[IMPORTANT] Gộp ba trang thành một là lúc dễ đánh rơi một khối nhất:
    trang vẫn 200, vẫn đẹp, chỉ thiếu đúng thứ ai đó cần. Test này đếm từng
    khối thay vì chỉ kiểm mã trả về."""
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/kho-du-lieu")
    assert r.status_code == 200
    for ten, dau_hieu in DAU_HIEU_KHOI.items():
        assert dau_hieu in r.text, f"thiếu khối: {ten}"


def test_man_co_hai_neo_cho_dau_trang_cu(conn, test_db_url):
    """Dấu trang cũ /nap và /phu-du-lieu sẽ được chuyển hướng kèm neo
    #nap / #theo-thang. Neo không tồn tại thì người bấm rơi lên đầu trang
    và phải cuộn đi tìm — đúng thứ chuyển hướng sinh ra để tránh."""
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert 'id="nap"' in html
    assert 'id="theo-thang"' in html


def test_ban_chi_doc_an_o_tha_file(conn, test_db_url, monkeypatch):
    """Bản công khai không nạp được. Hiện ô thả file ở đó là mời người ta
    kéo một file 100 MB vào một endpoint luôn trả 403."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert 'id="nap"' not in html
    assert "在庫一覧" in html, "khối chỉ-đọc khác vẫn phải hiện"


def test_khoi_hoan_tac_hien_lo_va_giau_nut_sau_mot_buoc(conn, test_db_url):
    """[IMPORTANT] Hoàn tác XOÁ dữ liệu khỏi core và không thể hoàn lại.
    Nút không được nằm trần trên một màn người ta mở mỗi ngày: <details>
    bắt người bấm đọc hậu quả trước khi thấy cái nút."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b = _lo(conn, "shiiresaki", "仕入先_20260908.xlsx", "2026-09-08", 3, "dg1")
    _nha_cung_cap(conn, b, 3)
    conn.commit()
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text

    assert "仕入先_20260908.xlsx" in html
    assert "<details" in html and "Hoàn tác" in html
    assert "3 dòng" in _khoi_hoan_tac(html)[b], "phải nói rõ sẽ xoá bao nhiêu dòng"
    assert "Không thể hoàn lại" in html


def test_ban_chi_doc_an_khoi_hoan_tac(conn, test_db_url, monkeypatch):
    """Bản công khai không hoàn tác được (route trả 403). Hiện nút ở đó là
    mời người ta bấm một thứ chắc chắn thất bại — và là nút XOÁ."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    html = client.get("/kho-du-lieu").text
    assert "/undo/" not in html


def test_hoan_tac_master_upsert_hien_canh_bao_se_trong(conn, test_db_url):
    """[IMPORTANT] File master nạp bằng upsert theo khoá KHÔNG có ngày: mỗi
    lần nạp dán batch_id MỚI lên mọi dòng, nên hoàn tác (`DELETE WHERE
    batch_id`) quét sạch CẢ BẢNG chứ không lùi về lô trước. Sự cố thật đã xảy
    ra vì thiếu cảnh báo này: hoàn tác một lô shiiresaki 49 dòng, tưởng lùi
    về 48, thực tế core.dim_supplier còn 0.

    Cảnh báo giờ đến từ phép ĐẾM (49 dòng của lô = 49 dòng của bảng), không
    từ một danh sách loại file đoán trước."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b = _lo(conn, "shiiresaki", "仕入先_20260908.xlsx", "2026-09-08", 49, "dg2")
    _nha_cung_cap(conn, b, 49)
    conn.commit()
    client = TestClient(create_app(db_url=test_db_url))
    khoi = _khoi_hoan_tac(client.get("/kho-du-lieu").text)[b]
    assert "49 dòng" in khoi
    assert "sẽ trống hoàn toàn" in khoi
    assert "không lùi về lần nạp trước" in khoi


def test_hoan_tac_uriage_doi_soat_thang_noi_dung_so_dong_se_mat(conn, test_db_url):
    """[IMPORTANT] TEST QUAN TRỌNG NHẤT CỦA ĐỢT NÀY.

    Đối soát tháng là việc THƯỜNG KỲ (CLAUDE.md: "đầu mỗi tháng xuất lại toàn
    bộ tháng trước"). Khoá của core.fact_sales_line là (slip_no, line_seq,
    source) — KHÔNG có ngày — nên lô đối soát dán batch_id của nó lên cả
    tháng, kể cả dòng do các lô hằng ngày trước đó nạp vào. Một lần bấm Hoàn
    tác lô ấy là mất cả tháng doanh thu.

    Bản cũ của màn hình KHÔNG cảnh báo gì cho uriage và in `row_count` của
    file như thể đó là số dòng sẽ mất. Test này là thứ duy nhất chặn được
    kịch bản đó tái diễn.

    Dựng thu nhỏ: lô 1 nạp 2 phiếu, lô 2 nạp lại 3 phiếu CHỒNG lên. Màn phải
    nói lô 2 xoá 3 dòng (không phải "3 dòng file mang vào" một cách tình cờ —
    xem test cùng tên ở tests/test_nhat_ky_nap.py đo thẳng con số), phải nói
    bảng doanh thu sẽ trống, và phải nói THẲNG rằng lô 1 không còn giữ dòng
    nào thay vì hứa xoá 2 dòng nó từng nạp."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b1 = _lo(conn, "uriage", "売上伝票データ_20260901.xlsx", "2026-09-01", 2, "dg3")
    _ban_hang(conn, b1, [("A", 1), ("B", 1)])
    b2 = _lo(conn, "uriage", "売上伝票データ_20260930.xlsx", "2026-09-30", 3, "dg4")
    _ban_hang(conn, b2, [("A", 1), ("B", 1), ("C", 1)])
    conn.commit()
    client = TestClient(create_app(db_url=test_db_url))
    khoi = _khoi_hoan_tac(client.get("/kho-du-lieu").text)

    assert "3 dòng" in khoi[b2], "lô đối soát đang giữ 3 dòng, phải nói đúng 3"
    assert "doanh thu" in khoi[b2], "phải nói rõ mất dòng của BẢNG NÀO"
    assert "lô TRƯỚC nạp vào" in khoi[b2], \
        "phải nói rõ số này gồm cả dòng của lô trước bị đè lên"
    assert "sẽ trống hoàn toàn" in khoi[b2]
    assert "Không thể hoàn lại" in khoi[b2]

    assert "không còn giữ dòng nào" in khoi[b1]
    assert "2 dòng" not in khoi[b1], \
        "row_count cũ (2) là con số GÂY HIỂU NHẦM — hoàn tác lô 1 xoá 0 dòng"


def test_khong_doa_se_trong_khi_bang_con_dong_cua_lo_khac(conn, test_db_url):
    """Cảnh báo "sẽ trống hoàn toàn" phải IM khi nó không đúng. Dán cảnh báo
    nặng lên ca không cần dạy người đọc coi thường mọi cảnh báo — nguy hiểm
    ngang việc thiếu cảnh báo, và đó đúng là lỗi cũ với `tanka` (khoá bảng
    giá CÓ valid_from nên lô sau không đè lô trước)."""
    conn.execute("DELETE FROM meta.ingest_batch")
    b1 = _lo(conn, "uriage", "売上伝票データ_20260901.xlsx", "2026-09-01", 1, "dg5")
    _ban_hang(conn, b1, [("A", 1)])
    b2 = _lo(conn, "uriage", "売上伝票データ_20260902.xlsx", "2026-09-02", 1, "dg6")
    _ban_hang(conn, b2, [("B", 1)])
    conn.commit()
    client = TestClient(create_app(db_url=test_db_url))
    khoi = _khoi_hoan_tac(client.get("/kho-du-lieu").text)
    assert "1 dòng" in khoi[b2]
    assert "sẽ trống hoàn toàn" not in khoi[b2]
    assert "sẽ trống hoàn toàn" not in khoi[b1]


def test_ba_dia_chi_cu_chuyen_huong_301(conn, test_db_url):
    """[IMPORTANT] Ba địa chỉ này nằm trong runbook và trong dấu trang của
    người dùng. Trả 404 là phạt họ vì một thay đổi họ không gây ra.

    follow_redirects=False: TestClient mặc định ĐI THEO chuyển hướng, nên
    không tắt thì test này xanh cả khi route trả 200 mà chẳng chuyển hướng gì.
    """
    client = TestClient(create_app(db_url=test_db_url))
    mong_doi = {"/health": "/kho-du-lieu",
                "/nap": "/kho-du-lieu#nap",
                "/phu-du-lieu": "/kho-du-lieu#theo-thang"}
    for cu, moi in mong_doi.items():
        r = client.get(cu, follow_redirects=False)
        assert r.status_code == 301, f"{cu} trả {r.status_code}, phải 301"
        assert r.headers["location"] == moi, f"{cu} trỏ sai đích"


def test_nap_van_chuyen_huong_o_ban_chi_doc(conn, test_db_url, monkeypatch):
    """Dấu trang /nap cũ trên bản công khai phải rơi vào màn (tự ẩn khối
    nạp), không phải một trang 403. 403 cho một dấu trang cũ là phạt người
    dùng vì một thay đổi họ không gây ra."""
    monkeypatch.setenv("KOME_CHI_DOC", "1")
    client = TestClient(create_app(db_url=test_db_url))
    r = client.get("/nap", follow_redirects=False)
    assert r.status_code == 301


def test_upload_render_man_gop(conn, test_db_url):
    """Nạp xong phải rơi lại vào màn gộp kèm kết quả — không phải một
    template đã bị xoá."""
    client = TestClient(create_app(db_url=test_db_url))
    with open("tests/fixtures/zaiko_cat_cut.xlsx", "rb") as f:
        r = client.post("/upload", files={"files": ("在庫一覧_20260916.xlsx", f)})
    assert r.status_code == 200
    assert 'id="theo-thang"' in r.text, "phải là màn gộp, không phải trang nạp cũ"
    assert "nghi file xuất một phần" in r.text, "kết quả nạp vẫn phải hiện"


def test_tai_lieu_khong_con_tro_toi_ba_dia_chi_cu():
    """[IMPORTANT] runbook.md là thứ người KHÔNG rành kỹ thuật mở ra đúng
    lúc đang hỏng. Một địa chỉ sai trong đó nguy hiểm hơn một địa chỉ sai
    trong code: code thì test bắt được, còn sổ tay thì không gì bắt —
    trừ test này."""
    canh = [Path("docs/runbook.md"), Path("CLAUDE.md"),
            Path("docs/trien-khai-vercel.md")]
    cu = ("/phu-du-lieu", "/health", "/nap")
    loi = []
    for f in canh:
        for i, dong in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            # Chỉ bắt địa chỉ dùng như ĐƯỜNG DẪN (có dấu / đứng trước),
            # không bắt chữ "nạp" tiếng Việt hay tên biến.
            if any(d in dong for d in cu):
                loi.append(f"{f}:{i}: {dong.strip()[:70]}")
    assert not loi, "tài liệu còn trỏ tới địa chỉ cũ:\n" + "\n".join(loi)


# Lời MÔ TẢ đã sai kể từ khi ba trang gộp làm một. Khác với địa chỉ cũ, những
# câu này không chứa dấu `/` nào nên test trên không thấy — mà chúng nguy hiểm
# hơn: một ô kiểm tay mô tả sai thì LUÔN XANH, kể cả khi bất biến nó canh đã
# vỡ hoàn toàn.
#
# Mỗi mẫu đi kèm danh sách MIỄN TRỪ: những chữ làm câu đó thành lời kể về quá
# khứ chứ không phải mô tả hiện tại. "Ba trang cũ nay chỉ còn 301 về
# /kho-du-lieu" (CLAUDE.md) là câu ĐÚNG và phải giữ; "Bản chạy ở máy có đủ cả
# ba trang" là câu SAI. Phân biệt bằng chữ "cũ" trên cùng dòng.
MO_TA_DA_SAI = {
    "ba trang": (
        "nạp/sức khoẻ/bảng phủ nay là MỘT màn /kho-du-lieu, không còn ba trang",
        ("cũ",)),
    "hai trang": (
        "bản Vercel mở CÙNG màn đó, chỉ ẩn hai khối — không phải 'chỉ có hai trang'",
        ("cũ",)),
    "thanh menu": (
        "ô kiểm 'thanh menu không có mục Nạp dữ liệu' nay LUÔN xanh: mục đó đã "
        "biến mất khỏi CẢ HAI bản. Phải soát trong màn: không có ô kéo–thả file "
        "và không có nút Hoàn tác",
        ()),
    "📥": (
        "biểu tượng của mục menu Nạp dữ liệu — mục đó không còn trong sidebar",
        ()),
}


def test_tai_lieu_khong_con_mo_ta_sai_cau_truc_man_hinh():
    """[IMPORTANT] Test địa chỉ cũ ở trên chỉ bắt được CHUỖI ĐƯỜNG DẪN. Câu
    "Bản chạy ở máy có đủ cả ba trang…" trong runbook không chứa đường dẫn
    nào nên nó lọt qua — mà người mở runbook lúc đang hỏng thì đọc câu đó,
    không đọc code.

    Nguy hiểm nhất là ô kiểm tay trong docs/trien-khai-vercel.md: "Thanh menu
    không có mục 📥 Nạp dữ liệu". Mục đó đã biến mất khỏi sidebar ở CẢ HAI
    bản, nên ô kiểm ấy nay xanh kể cả khi bất biến chỉ-đọc vỡ hoàn toàn — và
    nó là cổng kiểm TAY duy nhất cho bất biến đó."""
    canh = [Path("docs/runbook.md"), Path("CLAUDE.md"),
            Path("docs/trien-khai-vercel.md")]
    loi = []
    for f in canh:
        for i, dong in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            thap = dong.lower()
            for mau, (vi_sao, mien_tru) in MO_TA_DA_SAI.items():
                if mau in thap and not any(x in thap for x in mien_tru):
                    loi.append(f"{f}:{i}: “{mau}” — {vi_sao}")
    assert not loi, "tài liệu còn mô tả cấu trúc màn hình đã cũ:\n" + "\n".join(loi)


def test_bon_cho_code_khong_con_khang_dinh_dieu_da_sai():
    """[IMPORTANT] Soát Task 4 tìm thêm bốn chỗ trong code còn trỏ tới ba
    địa chỉ đã chết như thể chúng còn sống: nhãn nút, đích mặc định sau đăng
    nhập, và comment/docstring mô tả hành vi đã sai kể từ khi gộp thành
    /kho-du-lieu. Ba định nghĩa route redirect thật (gần cuối
    kome/web/app.py, ví dụ `@app.get("/nap", ...)`) và một comment mô tả
    đúng ngay hành vi của route đó là HỢP LỆ và phải giữ nguyên — đó là nơi
    ba địa chỉ cũ còn được phép tồn tại trong code, theo nghĩa "vẫn đang là
    địa chỉ thật, chỉ 301 đi nơi khác".

    Task 5 thêm đúng MỘT chỗ hợp lệ thứ ba: hằng `DUONG_KHO_DU_LIEU` trong
    kome/web/app.py, nơi liệt kê nguyên văn ba địa chỉ cũ để CHẶN QUYỀN (một
    lý do khác hẳn — không khẳng định chúng còn là trang riêng). Miễn trừ
    này gắn vào ĐÚNG các dòng của câu lệnh gán đó bằng AST
    (`lineno..end_lineno` của node `Assign`), KHÔNG phải bằng một chuỗi
    marker rải trong `hop_le`: một marker theo chuỗi con sẽ miễn trừ VĨNH
    VIỄN mọi dòng tương lai chứa chuỗi đó ở bất cứ đâu trong file — kể cả
    một comment sai sự thật kiểu "mặc định về /nap (xem DUONG_KHO_DU_LIEU)",
    tức đúng loại khẳng định-điều-đã-sai mà chính test này sinh ra để bắt.
    AST không có lỗ hổng đó vì nó gắn miễn trừ vào một câu lệnh cụ thể, không
    gắn vào một mẩu văn bản có thể bị chép sang chỗ khác."""
    import ast

    canh = [
        Path("kome/web/templates/chi_doc.html"),
        Path("kome/web/bao_mat.py"),
        Path("kome/web/templates/kho_du_lieu.html"),
        Path("kome/web/app.py"),
    ]
    cu = ("/phu-du-lieu", "/health", "/nap")
    # Định nghĩa route redirect thật (`@app.get("/nap", ...)`) và comment mô
    # tả đúng ngay hành vi của chính route /nap đó — hai chỗ DUY NHẤT (ngoài
    # câu lệnh gán DUONG_KHO_DU_LIEU, miễn trừ riêng bằng AST ở dưới) được
    # phép nhắc địa chỉ cũ như một địa chỉ còn tồn tại.
    hop_le = ("@app.get(", "VẪN chuyển hướng ở bản chỉ-đọc")

    app_py = Path("kome/web/app.py")
    dong_app = app_py.read_text(encoding="utf-8").splitlines()
    # Miễn trừ theo KHOẢNG DÒNG của chính câu lệnh gán, không theo chuỗi
    # con: xuống dòng lại tuple này (thao tác vô hại) không được làm test ở
    # đây đỏ, và một comment tương lai nhắc tên hằng ở nơi khác thì KHÔNG
    # được ăn theo miễn trừ này. Kéo thêm lên các dòng comment đứng NGAY
    # TRÊN câu lệnh (không cách dòng trống) — comment giải thích chính hằng
    # đó cũng hợp lệ, nhưng chỉ khi nó dính liền, không phải bất cứ đâu.
    cay = ast.parse("\n".join(dong_app))
    dong_mien_tru = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "DUONG_KHO_DU_LIEU"
                for t in n.targets):
            bat_dau = n.lineno
            while bat_dau > 1 and dong_app[bat_dau - 2].strip().startswith("#"):
                bat_dau -= 1
            dong_mien_tru.update(range(bat_dau, n.end_lineno + 1))

    loi = []
    for f in canh:
        mien_tru_file = dong_mien_tru if f == app_py else set()
        for i, dong in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
            if i in mien_tru_file:
                continue
            if any(h in dong for h in hop_le):
                continue
            if any(d in dong for d in cu):
                loi.append(f"{f}:{i}: {dong.strip()[:70]}")
    assert not loi, "code còn nhắc địa chỉ cũ như thể còn sống:\n" + "\n".join(loi)
