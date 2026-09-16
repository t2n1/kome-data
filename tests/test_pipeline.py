from pathlib import Path
from datetime import date
import shutil
import pytest
from kome import archive
from kome.loaders import inventory
from kome.pipeline import ingest

OK = Path("tests/fixtures/zaiko_ok.xlsx")

def _staged(tmp_path):
    dest = tmp_path / "在庫一覧_20260916.xlsx"
    shutil.copy2(OK, dest)
    return dest

def test_nap_thanh_cong(conn, tmp_path):
    r = ingest(conn, _staged(tmp_path), tmp_path / "archive")
    assert r.ok and r.row_count == 177 and r.total == 137_839_071
    assert r.blockers == []

def test_nap_lai_cung_file_bi_bo_qua(conn, tmp_path):
    p = _staged(tmp_path)
    ingest(conn, p, tmp_path / "archive")
    second = ingest(conn, p, tmp_path / "archive")
    assert second.skipped is True

def test_file_cat_cut_bi_chan_va_khong_ghi_gi(conn, tmp_path):
    dest = tmp_path / "在庫一覧_20260916.xlsx"
    shutil.copy2("tests/fixtures/zaiko_cat_cut.xlsx", dest)
    r = ingest(conn, dest, tmp_path / "archive")
    assert not r.ok and any(b.gate == 3 for b in r.blockers)
    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 0

def test_moi_loader_deu_khai_bao_bang_can_don():
    from kome.pipeline import LOADERS, UNDO_TABLES
    assert set(LOADERS) == set(UNDO_TABLES), "Thêm loader mới thì phải thêm mục vào UNDO_TABLES"

def test_loader_hong_khong_de_lai_lo_mo_coi(conn, tmp_path, monkeypatch):
    """[CRITICAL] Lỗi của loader KHÔNG được để lại lô còn hiệu lực.

    archive.store() commit dòng meta.ingest_batch TRƯỚC khi loader chạy. Nếu
    loader lỗi mà lô nằm lại với undone_at IS NULL, lần sau người dùng thử lại
    ĐÚNG file đó sẽ được already_loaded() trả True -> màn hình báo XANH
    "đã nạp rồi, bỏ qua" trong khi core có 0 dòng. File bị bỏ qua vĩnh viễn.
    """
    import kome.pipeline as P

    def loader_hong(conn, df, data_date, batch_id):
        raise RuntimeError("mô phỏng loader hỏng giữa chừng")

    monkeypatch.setitem(P.LOADERS, "zaiko", loader_hong)

    p = _staged(tmp_path)
    digest = archive.sha256_of(p)
    with pytest.raises(RuntimeError):
        ingest(conn, p, tmp_path / "archive")

    # Không còn lô nào CÒN HIỆU LỰC mang digest này
    n = conn.execute(
        "SELECT count(*) FROM meta.ingest_batch WHERE digest = %s AND undone_at IS NULL",
        (digest,),
    ).fetchone()[0]
    assert n == 0
    assert archive.already_loaded(conn, digest) is False
    # File chép ra kho lưu trữ cũng phải được dọn (minor còn nợ của Task 5)
    assert list((tmp_path / "archive").rglob("*.xlsx")) == []

    # ... và nạp lại đúng file ấy phải nạp THẬT, không phải "bỏ qua"
    monkeypatch.setitem(P.LOADERS, "zaiko", inventory.load)
    r = ingest(conn, p, tmp_path / "archive")
    assert r.ok and r.skipped is False
    assert r.row_count == 177 and r.total == 137_839_071
    n = conn.execute("SELECT count(*) FROM core.fact_inventory_daily").fetchone()[0]
    assert n == 177


def test_moi_spec_trong_files_yml_deu_co_loader():
    """Lưới an toàn: thêm spec vào config/files.yml mà quên thêm vào LOADERS
    thì ingest() ném KeyError SAU archive.store() — đúng cái bẫy lô mồ côi ở
    trên. Bắt ngay tại đây thay vì để nó nổ trên máy người dùng."""
    from kome.pipeline import LOADERS, SPECS
    assert set(SPECS) == set(LOADERS), \
        "Thêm spec vào config/files.yml thì phải thêm mục vào LOADERS"


def test_tong_tien_uriage_la_sum_amount(conn, tmp_path):
    """[IMPORTANT] Tổng tiền của 売上伝票データ phải là sum(金額), không phải
    sum(入金額１) (cột CUỐI money_columns, gần như luôn 0).

    Lấy nhầm cột làm màn hình nạp và /health hiện ¥0 — và vì gates.py có điều
    kiện `if prev_total and ...` nên prev_total = 0 TẮT IM LẶNG cả nhánh cảnh
    báo lệch tiền của cổng 4 cho đúng file chở ¥1,5 tỷ/năm.
    """
    import pandas as pd
    from kome.config import load_specs

    spec = load_specs(Path("config/files.yml"))["uriage"]
    rows = []
    for i in range(60):                     # trên min_rows = 50
        rows.append({
            "slip_no": f"07{i:04d}", "line_seq": 1, "sales_date": date(2026, 5, 1),
            "billing_date": date(2026, 5, 31), "slip_type": "債権計上",
            "customer_code": "000000009292", "billing_customer_code": "000000009292",
            "salesperson_code": "0004", "department_code": "01", "shipto_code": "0001",
            "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": 6,
            "unit_price": 5250, "unit_cost": 3210, "amount": 29167 + i,
            "tax_amount": 2333, "cost": 19260, "gross_profit": 9907,
            "gross_margin": 0.3397, "tax_rate": 0.08,
            "paid_amount": 0,                       # như dữ liệu thật: 入金額１ = 0
            "payment_slip_no": "000000", "closing_day_code": "99",
        })
    df = pd.DataFrame(rows)
    mong_doi = int(df["amount"].sum())
    assert mong_doi > 0

    ja_of = {sys_col: ja for ja, sys_col in spec.columns.items()}
    df = df.rename(columns=ja_of)[list(spec.columns.keys())]
    p = tmp_path / "売上伝票データ_20260501.xlsx"
    df.to_excel(p, sheet_name=spec.sheet, index=False)

    r = ingest(conn, p, tmp_path / "archive")
    assert r.ok, r.blockers
    assert r.total == mong_doi          # KHÔNG phải 0 (sum(paid_amount))
