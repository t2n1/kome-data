# tests/test_load_sales.py
from pathlib import Path
from datetime import date
import pandas as pd
from kome.config import load_specs
from kome.gates import check as gates_check
from kome.loaders import sales
from kome.pipeline import ingest
from kome.reader import dedup_on_keys

SPECS = load_specs(Path("config/files.yml"))


def _line(slip="079934", seq=1, amount=29167, profit=9907, qty=6, batch_id=1):
    return {
        "slip_no": slip, "line_seq": seq, "sales_date": date(2026, 5, 1),
        "slip_type": "債権計上", "customer_code": "000000009292",
        "billing_customer_code": "000000009292", "salesperson_code": "0004",
        "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": qty, "unit_price": 5250,
        "unit_cost": 3210, "amount": amount, "tax_amount": 2333, "cost": 19260,
        "gross_profit": profit, "gross_margin": 0.3397, "paid_amount": 0,
        "batch_id": batch_id,
    }


def _meisai_line(slip="090001", seq=1, amount=31500, profit=9907, batch_id=1):
    return {
        "slip_no": slip, "line_seq": seq, "sales_date": date(2026, 8, 3),
        "slip_type": "債權計上", "customer_code": "000000009292",
        "salesperson_code": "0004", "department_code": "0020",
        "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": 6,
        "unit_price": 5250, "unit_cost": 3210, "amount": amount,
        "tax_amount": 2333, "cost": 19260, "gross_profit": profit,
        "gross_margin": 0.3145, "batch_id": batch_id,
    }


def test_nap_va_cong_dung(conn, batch):
    b = batch(1)
    df = pd.DataFrame([_line(seq=1, batch_id=b), _line(seq=2, amount=37778, profit=14498, batch_id=b)])
    assert sales.load(conn, df, date(2026, 5, 1), b) == 2
    r = conn.execute("SELECT sum(amount), sum(gross_profit) FROM core.fact_sales_line").fetchone()
    assert r[0] == 66_945 and r[1] == 24_405


def test_phieu_do_so_am_duoc_giu_nguyen(conn, batch):
    b = batch(1)
    df = pd.DataFrame([
        _line(seq=1, batch_id=b),
        _line(seq=2, amount=-29167, profit=-9907, qty=-6, batch_id=b),
    ])
    sales.load(conn, df, date(2026, 5, 1), b)
    total = conn.execute("SELECT sum(amount) FROM core.fact_sales_line").fetchone()[0]
    assert total == 0          # bán rồi trả lại = 0, KHÔNG lọc bỏ dòng âm
    n = conn.execute("SELECT count(*) FROM core.fact_sales_line").fetchone()[0]
    assert n == 2


def test_nap_ba_lan_van_the(conn, batch):
    for i in range(3):
        b = batch(i + 1)
        df = pd.DataFrame([_line(batch_id=b)])
        sales.load(conn, df, date(2026, 5, 1), b)
    r = conn.execute("SELECT count(*), sum(amount) FROM core.fact_sales_line").fetchone()
    assert r[0] == 1 and r[1] == 29_167


def test_doi_soat_thang_ghi_de_phieu_da_sua(conn, batch):
    b1 = batch(1)
    sales.load(conn, pd.DataFrame([_line(amount=29167, batch_id=b1)]), date(2026, 5, 1), b1)
    b2 = batch(2)
    sales.load(conn, pd.DataFrame([_line(amount=25000, batch_id=b2)]), date(2026, 5, 1), b2)
    r = conn.execute("SELECT sum(amount), count(*) FROM core.fact_sales_line").fetchone()
    assert r[0] == 25_000 and r[1] == 1


def test_khu_trung_dong_xuat_hai_lan():
    """売上伝票データ xuất mỗi dòng nghiệp vụ HAI LẦN: một lần dưới 出荷内訳,
    một lần dưới 明細按分 — cùng 伝票No. + 明細行番号, cùng 金額/粗利益.

    Không khử trùng thì cộng thẳng ra gấp đôi doanh thu thực. Giữ dòng đầu
    tiên của mỗi khoá (slip_no, line_seq) là đủ (đã kiểm chứng trên dữ liệu
    thật: 4 cách lọc khác nhau đều cho cùng tổng 粗利益)."""
    df = pd.DataFrame([
        {"slip_no": "079934", "line_seq": 1, "amount": 31500, "gross_profit": 9907},   # 出荷内訳
        {"slip_no": "079934", "line_seq": 1, "amount": 31500, "gross_profit": 9907},   # 明細按分 (bản sao)
        {"slip_no": "079934", "line_seq": 2, "amount": 5000, "gross_profit": 1000},
        {"slip_no": "079934", "line_seq": 2, "amount": 5000, "gross_profit": 1000},
        {"slip_no": "079935", "line_seq": 1, "amount": 1200, "gross_profit": 300},
    ])
    result = dedup_on_keys(df, ["slip_no", "line_seq"])
    assert len(result) == 3
    assert result["amount"].sum() == 37_700
    assert result["gross_profit"].sum() == 11_207


def test_khu_trung_canh_bao_khi_gia_tri_khac_nhau():
    """Khử trùng CHỈ so khoá — nếu hai dòng cùng khoá nhưng khác 金額 thì
    dòng thứ hai sẽ bị bỏ ÂM THẦM. Phải đếm được số nhóm bất thường này để
    gates.check() cảnh báo (không tự chặn — chưa biết dòng nào đúng)."""
    df = pd.DataFrame([
        {"slip_no": "079934", "line_seq": 1, "amount": 31500, "gross_profit": 9907},
        {"slip_no": "079934", "line_seq": 1, "amount": 40000, "gross_profit": 9907},  # amount khác!
        {"slip_no": "079935", "line_seq": 1, "amount": 1200, "gross_profit": 300},
        {"slip_no": "079935", "line_seq": 1, "amount": 1200, "gross_profit": 300},    # giống hệt
    ])
    result = dedup_on_keys(df, ["slip_no", "line_seq"], ["amount", "gross_profit"])
    assert len(result) == 2
    assert result.attrs["dedup_conflicts"] == 1   # chỉ nhóm 079934 là bất thường


def test_khu_trung_khong_canh_bao_khi_gia_tri_giong_het():
    """Ca bình thường (38.882 nhóm trên dữ liệu thật): bản sao giống hệt
    nhau -> không cảnh báo."""
    df = pd.DataFrame([
        {"slip_no": "079934", "line_seq": 1, "amount": 31500, "gross_profit": 9907},
        {"slip_no": "079934", "line_seq": 1, "amount": 31500, "gross_profit": 9907},
    ])
    result = dedup_on_keys(df, ["slip_no", "line_seq"], ["amount", "gross_profit"])
    assert result.attrs["dedup_conflicts"] == 0


def test_cong_3_chan_ngay_khong_doc_duoc():
    """sales_date có khoá ngoại tới core.dim_date. Ngày rác/rỗng bị
    errors="coerce" nuốt thành None ở reader — cổng 3 phải chặn trước khi
    lô được lưu, không được để bung lỗi khoá ngoại giữa chừng."""
    df = pd.DataFrame([_line(seq=1), _line(seq=2)])
    for col in SPECS["uriage"].columns.values():   # đủ mọi cột spec khai báo
        if col not in df.columns:
            df[col] = ""
    df.loc[1, "sales_date"] = None   # mô phỏng ngày không đọc được
    blockers, _ = gates_check(
        Path("売上伝票データ_20260501.xlsx"), SPECS["uriage"], df, None
    )
    assert any(b.gate == 3 and "sales_date" in b.message for b in blockers)


def test_pipeline_chan_ngay_rac_khong_ghi_gi_va_khong_de_lo_mo_coi(conn, tmp_path):
    """Kiểm tra nguyên vẹn qua pipeline.ingest(): ngày rác bị chặn ở cổng 3
    TRƯỚC archive.store(), nên không có dòng nào trong fact_sales_line VÀ
    không có lô mồ côi nào trong meta.ingest_batch."""
    spec = SPECS["uriage"]
    ja_of = {sys_col: ja for ja, sys_col in spec.columns.items()}
    rows = []
    for r in (_line(seq=1), _line(seq=2)):
        r.pop("batch_id", None)
        rows.append(r)
    rows[1]["sales_date"] = None   # ngày rỗng/rác ở dòng thứ hai
    df = pd.DataFrame(rows)
    for col in spec.columns.values():
        if col not in df.columns:
            df[col] = None
    df = df.rename(columns=ja_of)[list(spec.columns.keys())]

    path = tmp_path / "売上伝票データ_20260501.xlsx"
    df.to_excel(path, sheet_name=spec.sheet, index=False)

    r = ingest(conn, path, tmp_path / "archive")
    assert not r.ok
    assert any(b.gate == 3 for b in r.blockers)

    n = conn.execute("SELECT count(*) FROM core.fact_sales_line").fetchone()[0]
    assert n == 0
    m = conn.execute(
        "SELECT count(*) FROM meta.ingest_batch WHERE spec_name = 'uriage'"
    ).fetchone()[0]
    assert m == 0   # không được để lại lô mồ côi


def test_canh_bao_khu_trung_di_qua_reader_read(tmp_path):
    """Cả ba test khử trùng ở trên gọi THẲNG dedup_on_keys(), nên nếu pandas
    đổi cách lan truyền df.attrs qua các phép biến đổi trong reader.read()
    (ép kiểu tiền/số lượng/ngày, reset_index), cảnh báo cổng 5 sẽ biến mất mà
    test vẫn xanh. Test này đi hết đường thật: file Excel -> read() -> check().
    """
    spec = SPECS["uriage"]
    rows = []
    for i in range(60):
        rows.append({
            "slip_no": f"07{i:04d}", "line_seq": 1, "sales_date": date(2026, 5, 1),
            "billing_date": date(2026, 5, 31), "slip_type": "債権計上",
            "customer_code": "000000009292", "billing_customer_code": "000000009292",
            "salesperson_code": "0004", "department_code": "01", "shipto_code": "0001",
            "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": 6,
            "unit_price": 5250, "unit_cost": 3210, "amount": 29167,
            "tax_amount": 2333, "cost": 19260, "gross_profit": 9907,
            "gross_margin": 0.3397, "tax_rate": 0.08, "paid_amount": 0,
            "payment_slip_no": "000000", "closing_day_code": "99",
        })
    # bản sao CÙNG khoá nhưng KHÁC 金額 -> phải đếm là 1 nhóm bất thường
    xung_dot = dict(rows[0])
    xung_dot["amount"] = 40000
    rows.append(xung_dot)

    df = pd.DataFrame(rows)
    ja_of = {sys_col: ja for ja, sys_col in spec.columns.items()}
    df = df.rename(columns=ja_of)[list(spec.columns.keys())]
    p = tmp_path / "売上伝票データ_20260501.xlsx"
    df.to_excel(p, sheet_name=spec.sheet, index=False)

    from kome.reader import read
    doc = read(p, spec)
    assert len(doc) == 60                      # bản sao đã bị khử
    assert doc.attrs.get("dedup_conflicts") == 1

    _, warnings = gates_check(p, spec, doc, None)
    assert any(w.gate == 5 and "khử trùng" in w.message for w in warnings)


def test_load_meisai_ghi_source_dung(conn, batch):
    b = batch(1)
    df = pd.DataFrame([_meisai_line(batch_id=b)])
    assert sales.load_meisai(conn, df, date(2026, 8, 3), b) == 1
    r = conn.execute(
        "SELECT source, amount FROM core.fact_sales_line"
    ).fetchone()
    assert r == ("meisai", 31500)


def test_uriage_va_meisai_khong_dung_do_khoa_ba_phan(conn, batch):
    """slip_no+line_seq CÓ THỂ trùng giữa 2 nguồn (line_seq của meisai là số
    tự sinh, không liên quan gì tới line_seq thật của uriage) -- khoá chính
    phải có thêm source để không đè nhầm dữ liệu của nhau."""
    b1 = batch(1)
    # Dùng _line (uriage data) với slip_no="090001" để mô phỏng trùng key
    uriage_data = _line(slip="090001", seq=1, amount=29167, batch_id=b1)
    sales.load(conn, pd.DataFrame([uriage_data]),
               date(2026, 5, 1), b1)   # source mặc định "uriage"
    b2 = batch(2)
    # Dùng _meisai_line với slip_no="090001", line_seq=1 (trùng key với uriage phía trên)
    sales.load_meisai(conn, pd.DataFrame([_meisai_line(slip="090001", seq=1, amount=31500, batch_id=b2)]),
                       date(2026, 8, 3), b2)
    r = conn.execute(
        "SELECT source, amount FROM core.fact_sales_line ORDER BY source"
    ).fetchall()
    assert r == [("meisai", 31500), ("uriage", 29167)]


def test_meisai_tu_file_thuc_teu_khong_co_paid_amount(conn, batch, tmp_path):
    """Hồi quy: meisai không mang paid_amount trong file gốc. Nếu không đặt
    về 0 trong load_meisai(), INSERT sẽ bị NULL constraint violation vì
    paid_amount là NOT NULL DEFAULT 0 -- DEFAULT chỉ áp khi cột OMIT, không
    khi NULL được truyền rõ ràng.

    Test này đi hết đường thật: file .xlsx -> read() -> load_meisai(),
    không như test_load_meisai_ghi_source_dung dùng hand-built dataframe.
    """
    from kome.reader import read

    # Tạo meisai-shaped .xlsx với dữ liệu thực (không có paid_amount column)
    cols = ["伝票No.", "得意先コード", "商品コード", "荷姿区分コード", "荷姿区分名",
            "売上日付", "伝票区分", "担当者コード", "部門コード",
            "入数", "純売上数量", "単価", "単位原価",
            "税込純売上高", "消費税額", "売上原価", "粗利益", "粗利益率", "消費税率",
            "荷姿区分コード", "荷姿区分名"]
    rows = [
        ["090001", "000000009292", "XT07", "02", "ケース（大：段ボール）",
         "2026-08-03", "債権計上", "0004", "0020", 1, 6, 5250, 3210,
         31500, 2333, 19260, 9907, 0.3145, 0.08, "02", "ケース（大：段ボール）"],
    ]
    df_xlsx = pd.DataFrame(rows, columns=cols)
    p = tmp_path / "売上明細表_20260803.xlsx"
    df_xlsx.to_excel(p, sheet_name="売上明細表", index=False)

    # Đọc qua reader (sẽ ko có cột paid_amount)
    doc = read(p, SPECS["meisai"])
    assert "paid_amount" not in doc.columns   # Xác nhận: real meisai ko có cột này

    # Load qua load_meisai (phải xử lý thêm paid_amount=0)
    b = batch(1)
    assert sales.load_meisai(conn, doc, date(2026, 8, 3), b) == 1

    # Kiểm chứng: dữ liệu lạch vào CSDL với source='meisai' và paid_amount=0
    r = conn.execute(
        "SELECT slip_no, source, amount, paid_amount FROM core.fact_sales_line"
    ).fetchone()
    assert r == ("090001", "meisai", 31500, 0)
