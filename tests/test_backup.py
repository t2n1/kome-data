from pathlib import Path
from datetime import date, timedelta

import pytest

from ops.backup import prune


def _touch(d: Path, day: date):
    p = d / f"kome_{day:%Y%m%d}.zip"
    p.write_bytes(b"x")
    return p


def test_giu_30_ban_ngay_va_12_ban_thang(tmp_path):
    today = date(2026, 9, 16)
    for i in range(400):
        _touch(tmp_path, today - timedelta(days=i))
    kept = prune(tmp_path, keep_daily=30, keep_monthly=12)
    assert len(kept) <= 42
    assert (tmp_path / f"kome_{today:%Y%m%d}.zip") in kept


def test_sao_luu_roi_khoi_phuc_ra_dung_so_dong(conn, batch, tmp_path):
    """Nạp dữ liệu thật -> dump -> xoá sạch -> restore -> số dòng phải khớp."""
    import os, json, zipfile
    from pathlib import Path
    from datetime import date
    from kome.config import load_specs
    from kome.reader import read
    from kome.loaders import inventory
    from ops.backup import dump
    from ops.restore_check import verify

    S = load_specs(Path("config/files.yml"))
    df = read(Path("tests/fixtures/zaiko_ok.xlsx"), S["zaiko"])
    inventory.load(conn, df, date(2026, 9, 16), batch(1))

    url = os.environ["DATABASE_URL_TEST"]
    z = dump(url, tmp_path)
    with zipfile.ZipFile(z) as zf:
        m = json.loads(zf.read("manifest.json"))
    assert m["tables"]["core.fact_inventory_daily"] == 177

    result = verify(z, url)          # khôi phục vào CHÍNH CSDL thử nghiệm
    assert result["ok"], result["mismatches"]
    assert result["counts"]["core.fact_inventory_daily"] == 177


def test_khoi_phuc_dat_lai_sequence_bigserial(conn, batch, tmp_path):
    """restore() dùng COPY FROM với id có sẵn -> sequence bị lệch. Sau khi
    khôi phục, chèn thêm dòng mới (customer_sk, batch_id đều bigserial) phải
    thành công, không đụng khoá chính đã tồn tại."""
    import os
    import psycopg
    from ops.backup import dump
    from ops.restore_check import restore

    bid = batch(1)
    conn.execute(
        """INSERT INTO core.dim_customer
             (customer_code, valid_from, customer_name, batch_id)
           VALUES ('K001', current_date, 'Khach thu nghiem', %s)""",
        (bid,),
    )
    conn.commit()

    url = os.environ["DATABASE_URL_TEST"]
    z = dump(url, tmp_path)
    restore(z, url)

    with psycopg.connect(url) as c:
        new_bid = c.execute(
            """INSERT INTO meta.ingest_batch
                 (spec_name, source_file, digest, archived_to, row_count, data_date)
               VALUES ('test', 'test2.xlsx', 'digest-sau-khoi-phuc', '/tmp/t2.xlsx', 0,
                       DATE '2026-01-01')
               RETURNING batch_id"""
        ).fetchone()[0]
        c.execute(
            """INSERT INTO core.dim_customer
                 (customer_code, valid_from, customer_name, batch_id)
               VALUES ('K002', current_date, 'Khach moi sau khoi phuc', %s)""",
            (new_bid,),
        )
        c.commit()
        assert new_bid >= 1


def test_restore_tu_choi_chay_tren_database_url_that(monkeypatch):
    """Lớp chặn an toàn nhất: restore() PHẢI từ chối chạy khi target_url trùng
    DATABASE_URL (CSDL thật), vì nó xoá sạch 4 schema trước khi dựng lại.

    Không được đụng gì vào CSDL thật: dùng monkeypatch để đặt một DATABASE_URL
    giả, gọi restore() với đúng chuỗi giả đó, và khẳng định nó ném ngoại lệ
    TRƯỚC KHI mở file zip hay kết nối CSDL (zip không cần tồn tại thật)."""
    from ops.restore_check import restore

    monkeypatch.setenv("DATABASE_URL", "postgresql://fake-host/khong-that")

    with pytest.raises(RuntimeError, match="DATABASE_URL"):
        restore(Path("khong-ton-tai.zip"), "postgresql://fake-host/khong-that")
