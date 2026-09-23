"""Test tài liệu sống (đợt 2b) — phần hàm thuần và ảnh chụp. Không cần CSDL."""
import re
import sys
from pathlib import Path

from kome import tai_lieu as T
from kome.config import GOC, SPECS

sys.path.insert(0, str(GOC / "scripts"))
import sinh_tai_lieu as S  # noqa: E402


# ---- Hai trường khai báo mới trong files.yml ------------------------------

def test_core_table_khop_undo_tables():
    """[IMPORTANT] Bảng đích khai hai nơi: pipeline.UNDO_TABLES (hoàn tác dùng)
    và files.yml (web dùng, vì web không được nhập pipeline). Trôi khỏi nhau
    là trang tài liệu nói file vào một bảng trong khi nút Hoàn tác xoá bảng khác."""
    from kome.pipeline import UNDO_TABLES
    assert set(SPECS) == set(UNDO_TABLES)
    for ten, s in SPECS.items():
        assert s.core_table == UNDO_TABLES[ten][0], ten


def test_references_hop_le():
    for ten, s in SPECS.items():
        cot = set(s.columns.values())
        for c, dich in s.references.items():
            assert c in cot, f"{ten}.{c} không có trong columns"
            assert dich in SPECS, f"{ten}.{c} trỏ vào spec lạ {dich}"
            assert len(SPECS[dich].keys) == 1, f"đích {dich} phải có đúng một khoá"


# ---- Hàm lúc chạy ---------------------------------------------------------

def test_md_dong_escape_truoc():
    """[CRITICAL] Nguồn là CLAUDE.md / đặc tả — ai cũng sửa được. Thẻ HTML lọt
    qua là một chỗ chèn script vào màn có nút xoá dữ liệu."""
    ra = str(T.md_dong("<script>x</script> **đậm** `mã`"))
    assert "<script>" not in ra and "&lt;script&gt;" in ra
    assert "<strong>đậm</strong>" in ra and "<code>mã</code>" in ra


def test_ma_tran_ky_hieu():
    mt = T.ma_tran(SPECS)
    cot = [c["vi"] for c in mt["cot"]]
    hang = {h["ten"]: dict(zip(cot, h["o"])) for h in mt["hang"]}
    assert hang["uriage"]["slip_no"] == "◆"
    assert hang["uriage"]["customer_code"] == "●"
    assert hang["tokuisaki"]["customer_code"] == "◆"
    assert hang["zaiko"]["warehouse_code"] == "◆"
    assert hang["shiiresaki"]["customer_code"] == ""
    # salesperson_code không là khoá của file nào và không có file master
    assert "salesperson_code" not in cot


def test_noi_di_dau_hai_chieu():
    n = T.noi_di_dau(SPECS, "shohin")
    assert n["tro_ra"] == []
    assert {x["nguon"] for x in n["tro_vao"]} >= {"uriage", "zaiko", "tanka"}
    ra = {x["cot"]: x["dich"] for x in T.noi_di_dau(SPECS, "uriage")["tro_ra"]}
    assert ra["billing_customer_code"] == "tokuisaki"


def test_cot_cua_du_cot_va_kieu():
    for ten, s in SPECS.items():
        assert [c["ja"] for c in T.cot_cua(SPECS, ten)] == list(s.columns)
    k = {c["vi"]: c for c in T.cot_cua(SPECS, "uriage")}
    assert k["amount"]["kieu"] == "tiền (yên)"
    assert k["customer_code"]["kieu"] == "mã (text)"
    assert k["sales_date"]["kieu"] == "ngày"
    assert k["qty"]["kieu"] == "số lượng"
    assert k["customer_code"]["noi"].startswith("得意先全情報")


def test_chon_file_la_ve_mac_dinh():
    assert T.chon_file(SPECS, "khong-co") == "uriage"
    assert T.chon_file(SPECS, None) == "uriage"
    assert T.chon_file(SPECS, "zaiko") == "zaiko"


def test_nguon_obc_tan_suat():
    n = {x["ten"]: x for x in T.nguon_obc(SPECS)}
    assert n["uriage"]["tan_suat"] == "hằng ngày 13:30"
    assert n["shohin"]["tan_suat"] == "vài lần mỗi năm"
    assert all(x["mo_ta"] for x in n.values()), "spec thiếu mô tả"


def test_anh_chup_thieu_khong_no(tmp_path):
    anh = T.doc_anh_chup(tmp_path / "khong-co.json")
    assert anh is None
    assert T.cam_bay(anh) == [] and T.cong(anh) == []
    assert [t["ma"] for t in T.bon_tang(anh, SPECS)] == ["raw", "core", "mart", "app"]


# ---- Ảnh chụp -------------------------------------------------------------

def test_anh_chup_tai_lieu_khong_cu():
    """[IMPORTANT] Sửa migration / CLAUDE.md / gates.TEN_CONG / đặc tả lộ trình
    mà quên `python scripts/sinh_tai_lieu.py` thì trang tài liệu nói sai lặng
    lẽ — đúng bệnh "bản sao thứ ba của sự thật" mà đợt 2b tồn tại để tránh."""
    da_commit = T.ANH_CHUP.read_text(encoding="utf-8")
    assert da_commit == S.van_ban(S.sinh()), \
        "ảnh chụp cũ — chạy: python scripts/sinh_tai_lieu.py"


def test_cam_bay_dem_bang_so_muc_trong_claude_md():
    van = (GOC / "CLAUDE.md").read_text(encoding="utf-8")
    muc = re.search(r"^## Bẫy đã biết\s*\n(.*?)(?=^## )", van, re.S | re.M).group(1)
    so = len(re.findall(r"^\d+\.\s", muc, re.M))
    cb = S.cam_bay(GOC / "CLAUDE.md")
    assert len(cb) == so
    # mục nhiều dòng được gộp đủ: mục 4 nói tới cả 元帳 lẫn 在庫一覧
    assert "元帳" in cb[3] and "在庫一覧" in cb[3]


def test_bon_tang_co_view_moi_nhat():
    bang = S.bang_theo_schema(GOC / "db" / "migrations")
    assert "thang_den_hom_nay" in bang["mart"]
    assert "dim_customer" in bang["core"]
    assert "ingest_batch" in bang["meta"]
    assert "ngan_sach" in bang["app"]


def test_bang_bi_drop_sau_do_khong_con(tmp_path):
    (tmp_path / "001.sql").write_text(
        "CREATE VIEW mart.cu AS SELECT 1;\n-- CREATE VIEW mart.chu_thich AS\n"
        "CREATE TABLE IF NOT EXISTS core.a (x int);", encoding="utf-8")
    (tmp_path / "002.sql").write_text(
        "DROP VIEW IF EXISTS mart.cu;\nCREATE OR REPLACE VIEW mart.moi AS SELECT 1;",
        encoding="utf-8")
    b = S.bang_theo_schema(tmp_path)
    assert b["mart"] == ["moi"] and b["core"] == ["a"]


def test_cong_du_nam_va_khop_ma_trong_gates():
    """Mọi số cổng mà check() thật sự phát ra phải có tên trong TEN_CONG."""
    import kome.gates as G
    nguon = Path(G.__file__).read_text(encoding="utf-8")
    dung = {int(n) for n in re.findall(r"(?:Blocker|Warning_)\(\s*(\d)", nguon)}
    assert dung <= set(G.TEN_CONG) == {1, 2, 3, 4, 5}
    assert [c["so"] for c in S.ten_cong()] == [1, 2, 3, 4, 5]


def test_lo_trinh_co_du_dot():
    lt = S.lo_trinh(S.LO_TRINH)
    assert lt["cot"][0] == "Đợt"
    assert any("6" in d[0] for d in lt["dong"])
