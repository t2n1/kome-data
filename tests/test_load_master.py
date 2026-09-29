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


def test_shohin_nap_qua_pipeline_mang_pack1_va_o_trong_la_chuoi_rong_va_NULL(conn, tmp_path):
    """荷姿１ của 商品データ qua ingest thật (5 cổng): ô trống → pack1_code '' (= không có 荷姿)
    và pack1_base_qty NULL (KHÔNG phải 0); ô có giá trị → giữ nguyên chữ / số."""
    from kome.pipeline import ingest
    dong = []
    for i in range(1, 121):
        d = {"商品コード": f"NT{i:03d}", "商品名": f"Hàng {i}", "日本語": f"品{i}", "種別コード": "0",
             "種別": "有形", "食品分類コード": "01", "食品分類名": "乾物", "商品ランク（年間）コード": "0001",
             "商品ランク（年間）名": "A", "独占or競合商品コード": "1", "バーコード": f"49000000{i:05d}",
             "単位": "袋", "入数": 20, "棚番コード": "A1", "導入日（西暦　年　月）": "2026年 1月",
             "荷姿１－荷姿区分コード": "", "荷姿１－基準単位当り荷姿区分数": ""}
        dong.append(d)
    dong[0]["荷姿１－荷姿区分コード"] = "02"
    dong[0]["荷姿１－基準単位当り荷姿区分数"] = "20"
    p = tmp_path / "商品データ_20260916.xlsx"
    pd.DataFrame(dong).to_excel(p, sheet_name="商品データ作成", index=False)
    r = ingest(conn, p, tmp_path / "archive")
    assert r.ok, r.blockers
    rows = {a: (b, c) for a, b, c in conn.execute(
        "SELECT product_code, pack1_code, pack1_base_qty FROM core.dim_product").fetchall()}
    assert rows["NT001"][0] == "02" and float(rows["NT001"][1]) == 20
    assert rows["NT002"] == ("", None)
