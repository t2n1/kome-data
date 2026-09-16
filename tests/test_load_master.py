# tests/test_load_master.py
import pandas as pd
from datetime import date
from kome.loaders.master import make_loader

def test_upsert_theo_khoa(conn, batch):
    load = make_loader("core.dim_supplier", ["supplier_code"], ["supplier_code", "supplier_name"])
    df = pd.DataFrame([{"supplier_code": "0001", "supplier_name": "BICH CHI FOOD COMPANY"}])
    assert load(conn, df, date(2026, 9, 16), batch(1)) == 1
    df2 = pd.DataFrame([{"supplier_code": "0001", "supplier_name": "BICH CHI FOOD CO., LTD"}])
    load(conn, df2, date(2026, 9, 17), batch(2))
    rows = conn.execute("SELECT supplier_code, supplier_name FROM core.dim_supplier").fetchall()
    assert rows == [("0001", "BICH CHI FOOD CO., LTD")]

def test_ma_giu_so_khong_dau(conn, batch):
    load = make_loader("core.dim_supplier", ["supplier_code"], ["supplier_code", "supplier_name"])
    load(conn, pd.DataFrame([{"supplier_code": "0001", "supplier_name": "X"}]), date(2026, 9, 16), batch(1))
    r = conn.execute("SELECT supplier_code FROM core.dim_supplier").fetchone()
    assert r[0] == "0001"
