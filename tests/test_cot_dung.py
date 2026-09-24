"""Màn Kho dữ liệu → "Dữ liệu đi đâu": cột OBC nào bỏ được (2026-09-24).

Sai nguy hiểm duy nhất của màn này là báo "bỏ được" cho một cột đang dùng —
người ta bỏ cột khỏi bản xuất OBC và một màn mất số vĩnh viễn. Các test dưới
đây canh phép dò (scripts/sinh_cot_dung.py) nghiêng đúng về phía "đang dùng",
và canh ảnh chụp không cũ so với migration / files.yml / mã.
"""
import sys

import pytest
from fastapi.testclient import TestClient

import kome.web.app as A
from kome import cot_dung as CD
from kome.config import GOC, SPECS
from tests.spa_kd import man, nguon

sys.path.insert(0, str(GOC / "scripts"))
import sinh_cot_dung as S  # noqa: E402


# ---- Ảnh chụp -------------------------------------------------------------

def test_anh_chup_cot_dung_khong_cu(conn):
    """[IMPORTANT] Sửa migration, files.yml hay mã kome/ mà quên chạy
    `python scripts/sinh_cot_dung.py` thì đỏ — không thì màn nói một cột
    "chưa ai dùng" trong khi màn vừa thêm đang đọc nó."""
    moi = S.van_ban(S.sinh(conn))
    assert moi == CD.ANH_CHUP.read_text(encoding="utf-8"), \
        "ảnh chụp cũ — chạy: python scripts/sinh_cot_dung.py"


@pytest.fixture(scope="module")
def anh():
    return CD.doc_anh_chup()


def _cot(anh, file, ja):
    f = next(x for x in anh["files"] if x["ten"] == file)
    return next(c for c in f["cot"] if c["ja"] == ja)


# ---- Khai báo phải đủ -------------------------------------------------------

def test_moi_cot_khai_bao_tim_duoc_cho_luu(anh):
    """[IMPORTANT] Cột hệ thống không cùng tên trong core_table và không khai ở
    LUU_RIENG → không biết loader ghi nó vào đâu → không dò được ai đọc nó."""
    for f in anh["files"]:
        for c in f["cot"]:
            if c["loai"] != "khong_nap":
                assert c["core"] != "?", f"{f['ten']}.{c['he']}: khai vào S.LUU_RIENG"


def test_moi_mo_dun_doc_mart_core_da_khai_man(anh):
    """[IMPORTANT] Mô-đun mới đọc mart/core mà chưa khai vào S.MAN thì cột nó đọc
    bị tính là "chưa dùng" — đúng lỗi nguy hiểm của màn này."""
    ma = S.quet_ma(GOC)
    thieu = [f for f, m in ma.items() if m["cau"] and f not in S.MAN and f not in S.MA_NAP
             and f not in S.BO_QUA and not f.startswith("kome/loaders/")]
    assert not thieu, f"khai các mô-đun này vào scripts/sinh_cot_dung.py::MAN: {thieu}"
    assert all(k in S.MAN_HINH for v in S.MAN.values() for k in v)


def test_mo_ta_mau_tieu_de_khop_files_yml():
    """Tiêu đề file mẫu phải chứa MỌI cột đang khai nạp — không thì file mẫu
    không phải bản xuất đang dùng (hay files.yml đã trôi khỏi OBC)."""
    import json
    td = json.loads(S.TIEU_DE.read_text(encoding="utf-8"))
    for ten, t in td.items():
        thieu = [ja for ja in SPECS[ten].columns if ja not in t["cot"]]
        assert not thieu, f"{ten}: file mẫu {t['file']} thiếu {thieu}"


# ---- Phán quyết trên dữ liệu thật (neo) -------------------------------------

def test_khoa_va_cot_doi_chieu_la_bo_nap_can(anh):
    assert _cot(anh, "uriage", "伝票No.")["loai"] == "nap"
    assert _cot(anh, "uriage", "明細行番号")["loai"] == "nap"
    assert _cot(anh, "uriage", "金額")["loai"] == "nap"          # cột tổng tiền cổng 4/5
    assert _cot(anh, "zaiko", "在庫単価")["loai"] == "nap"       # cột kiểm tích
    assert _cot(anh, "seikyu_motocho", "残高")["loai"] == "nap"  # so_cai.py đối chiếu


def test_cot_hien_tren_man_la_dang_dung(anh):
    """Những cột ai cũng thấy trên màn — dò ra "bỏ được" là phép dò hỏng."""
    for file, ja in [("uriage", "粗利益"), ("uriage", "数量"), ("uriage", "得意先コード"),
                     ("tokuisaki", "得意先名"), ("tokuisaki", "都道府県"), ("zaiko", "賞味期限"),
                     ("shohin", "商品名"), ("shohin", "食品分類名"), ("tanka", "売価No.１（税抜）")]:
        c = _cot(anh, file, ja)
        assert c["loai"] in ("nap", "man"), (file, ja, c["loai"])
    assert "khach" in _cot(anh, "tokuisaki", "都道府県")["man"]


def test_cot_khong_nap_co_trong_file_mau(anh):
    f = next(x for x in anh["files"] if x["ten"] == "tokuisaki")
    khong = [c for c in f["cot"] if c["loai"] == "khong_nap"]
    assert khong and all(c["core"] is None and c["ja"] not in SPECS["tokuisaki"].columns for c in khong)


# ---- Phép dò trên đầu vào dựng tay ------------------------------------------

def _dm(dinh_nghia, dep, cot, ham=None):
    return {"cot": cot, "loai": {k: "v" for k in dinh_nghia} | {k: "r" for k in cot if k.startswith("core.")},
            "dep": dep, "ham": ham or {}, "dinh_nghia": dinh_nghia, "khoa_ngoai": []}


def test_view_thong_suot_chi_keo_dung_cot_duoc_doc():
    dm = _dm({"mart.v": "SELECT f.a, f.b, (f.c - f.d) AS e FROM core.t f WHERE f.k > 0"},
             {"mart.v": [("core.t", x) for x in "abcdk"]},
             {"core.t": list("abcdk"), "mart.v": ["a", "b", "e"]})
    do = S.Do(dm)
    assert set(do.doc("mart.v", frozenset(["a"]))) == {("core.t", "a"), ("core.t", "k")}
    # Cột ra là biểu thức → kéo mọi cột vào có tên trong biểu thức.
    assert set(do.doc("mart.v", frozenset(["e"]))) == {("core.t", "c"), ("core.t", "d"), ("core.t", "k")}
    # Đọc cả view → mọi cột pg_depend ghi.
    assert set(do.doc("mart.v", None)) == {("core.t", x) for x in "abcdk"}


def test_view_khong_tach_duoc_tinh_ca_view():
    """WITH / UNION: không tách được → nghiêng về "đang dùng": mọi cột."""
    dm = _dm({"mart.v": "WITH x AS (SELECT a FROM core.t) SELECT a FROM x UNION SELECT b FROM core.t"},
             {"mart.v": [("core.t", "a"), ("core.t", "b")]}, {"core.t": ["a", "b", "z"], "mart.v": ["a"]})
    assert set(S.Do(dm).doc("mart.v", frozenset(["a"]))) == {("core.t", "a"), ("core.t", "b")}


def test_ham_select_sao_thong_qua_theo_ten_cot():
    """Hàm `SELECT * FROM mart.v WHERE …` (các mart.*_khoang) chuyển tiếp đúng cột."""
    dm = _dm({"mart.v": "SELECT f.a, f.b FROM core.t f"}, {"mart.v": [("core.t", "a"), ("core.t", "b")]},
             {"core.t": ["a", "b"], "mart.v": ["a", "b"], "mart.h": ["a", "b"]},
             ham={"mart.h": "SELECT * FROM mart.v WHERE a > tu"})
    assert set(S.Do(dm).doc("mart.h", frozenset(["b"]))) == {("core.t", "a"), ("core.t", "b")}


def test_sao_trong_cau_tinh_moi_cot():
    assert S.sao_cua("SELECT * FROM mart.khach_360") == {"mart.khach_360"}
    assert S.sao_cua("WITH s AS (SELECT a, b FROM mart.x) SELECT s.* FROM s") == set()
    assert S.sao_cua("SELECT k.* FROM mart.khach_360 k JOIN core.t c ON true") == {"mart.khach_360"}
    assert S.sao_cua("SELECT * FROM k") is None          # không lần được → tính tất cả


def test_chu_thich_va_docstring_khong_lam_cot_thanh_dang_dung():
    tu, chuoi = S.tu_trong_ma('"""Đọc cột_a."""\n# cột_b\nx = conn.execute("SELECT cot_c FROM core.t")\n')
    assert "cot_c" in tu and "cot_b" not in tu and "a" not in tu
    assert len(chuoi) == 1 and "SELECT cot_c FROM core.t" in chuoi[0]


def test_cau_tach_dong_la_mot_cum():
    _, chuoi = S.tu_trong_ma('q = ("SELECT * "\n     "FROM mart.v")\n')
    assert len(chuoi) == 1 and S.sao_cua(chuoi[0]) == {"mart.v"}


# ---- Màn -------------------------------------------------------------------

@pytest.fixture
def client(monkeypatch):
    def no(*a, **k):
        raise AssertionError("màn Dữ liệu đi đâu không được mở kết nối CSDL")
    monkeypatch.setattr(A, "connect", no)
    return TestClient(A.create_app(db_url="postgresql://khong-dung"))


def test_man_200_khong_truy_van_mot_file(client):
    r = client.get("/kho-du-lieu/duong-di?file=tokuisaki")
    assert r.status_code == 200
    m = man(r.text)
    assert m["chon"] == "tokuisaki" and m["file"]["ten"] == "tokuisaki"
    assert {f["ten"] for f in m["files"]} == set(SPECS)
    # Chỉ gửi chi tiết MỘT file, không cả ảnh chụp.
    assert "cot" not in m["files"][0]
    assert man(client.get("/kho-du-lieu/duong-di?file=khong-co").text)["chon"] == CD.FILE_MAC_DINH


def test_tab_moi_trong_dai_tab():
    assert '"duong-di", "/kho-du-lieu/duong-di"' in nguon("he_thong", "TabKho.tsx")
    assert '<KhungKho dang="duong-di">' in nguon("he_thong", "DuongDi.tsx")
