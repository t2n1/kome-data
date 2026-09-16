from pathlib import Path
from datetime import date
from kome.config import load_specs
from kome.reader import read
from kome.loaders import inventory

SPECS = load_specs(Path("config/files.yml"))
OK = Path("tests/fixtures/zaiko_ok.xlsx")
D = date(2026, 9, 16)

def _load(conn, batch, n=1):
    df = read(OK, SPECS["zaiko"])
    return inventory.load(conn, df, D, batch(n))   # batch() trả về batch_id thật

def test_khop_moc_doi_chieu(conn, batch):
    assert _load(conn, batch) == 177
    total, rows, whs = conn.execute(
        """SELECT sum(stock_value), count(*), count(DISTINCT warehouse_code)
           FROM core.fact_inventory_daily WHERE snapshot_date = %s""", (D,)
    ).fetchone()
    assert total == 137_839_071
    assert rows == 177
    assert whs == 2

def test_nap_ba_lan_van_the(conn, batch):
    for i in range(3):
        _load(conn, batch, n=i + 1)
    total, rows = conn.execute(
        """SELECT sum(stock_value), count(*) FROM core.fact_inventory_daily
           WHERE snapshot_date = %s""", (D,)
    ).fetchone()
    assert total == 137_839_071 and rows == 177

def test_giu_thap_phan_o_so_luong(conn, batch):
    _load(conn, batch)
    r = conn.execute(
        """SELECT count(*) FROM core.fact_inventory_daily
           WHERE snapshot_date = %s AND stock_qty <> trunc(stock_qty)""", (D,)
    ).fetchone()
    assert r[0] == 20

def test_dim_warehouse_duoc_tao(conn, batch):
    _load(conn, batch)
    rows = conn.execute("SELECT warehouse_code, warehouse_name FROM core.dim_warehouse ORDER BY 1").fetchall()
    assert rows == [("0001", "茨城第１倉庫（出荷専用）"), ("1002", "新・賞味期限用")]
