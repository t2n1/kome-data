"""Khôi phục từ bản sao lưu .zip do ops.backup.dump() tạo ra, và tự kiểm tra.

⚠️ restore() XOÁ SẠCH 4 schema (core, mart, app, meta) trước khi dựng lại.
CHỈ chạy trên CSDL nháp (DATABASE_URL_TEST). Không bao giờ truyền
DATABASE_URL (CSDL thật) vào restore() hay verify() — restore() tự chặn
việc này (xem _tu_choi_neu_la_csdl_that bên dưới), nhưng đừng dựa vào đó
để bất cẩn.
"""
import json
import os
import zipfile
from pathlib import Path

import psycopg

from db.migrate import apply_all
from ops.backup import SCHEMAS


def _tu_choi_neu_la_csdl_that(target_url: str) -> None:
    """Lớp chặn an toàn: restore() xoá sạch schema, nên nếu target_url trùng
    DATABASE_URL (biến môi trường trỏ tới CSDL thật) thì từ chối chạy ngay,
    trước khi mở file zip hay mở kết nối nào."""
    real_url = os.environ.get("DATABASE_URL")
    if real_url and target_url == real_url:
        raise RuntimeError(
            "restore() sẽ XOÁ SẠCH schema. Từ chối chạy trên DATABASE_URL (CSDL thật). "
            "Chỉ dùng cơ sở dữ liệu nháp."
        )


def _reset_sequences(conn: psycopg.Connection) -> None:
    """Sau khi COPY FROM đổ dữ liệu có sẵn khoá chính (vd. customer_sk,
    batch_id), chuỗi sinh số (sequence) của mọi cột serial/bigserial bị lệch
    so với dữ liệu vừa đổ vào — lần chèn tiếp theo có thể đụng khoá chính đã
    tồn tại. Đặt lại sequence = MAX(cột) cho mọi cột serial/bigserial trong
    4 schema (bảng rỗng thì đặt về 1)."""
    cols = conn.execute(
        """SELECT table_schema, table_name, column_name
           FROM information_schema.columns
           WHERE table_schema = ANY(%s) AND column_default LIKE 'nextval(%%'
           ORDER BY 1, 2, 3""",
        (list(SCHEMAS),),
    ).fetchall()
    for schema, table, col in cols:
        conn.execute(
            f'SELECT setval(pg_get_serial_sequence(%s, %s), '
            f'(SELECT COALESCE(MAX("{col}"), 0) FROM "{schema}"."{table}") + 1, false)',
            (f"{schema}.{table}", col),
        )


def restore(zip_path: Path, target_url: str) -> dict:
    """Dựng lại cấu trúc từ migrations rồi đổ dữ liệu CSV về. Trả về số dòng từng bảng.

    KHÔNG BAO GIỜ gọi hàm này trên CSDL thật — nó xoá sạch 4 schema trước khi dựng lại.
    """
    _tu_choi_neu_la_csdl_that(target_url)
    with zipfile.ZipFile(zip_path) as z:
        manifest = json.loads(z.read("manifest.json"))
        with psycopg.connect(target_url) as conn:
            conn.execute("DROP SCHEMA IF EXISTS core, mart, app, meta CASCADE")
            conn.commit()
            apply_all(conn, Path("db/migrations"))
            # Đổ theo đúng thứ tự trong manifest để khoá ngoại không vỡ:
            # meta.ingest_batch trước, rồi dim_*, rồi fact_*
            order = sorted(manifest["tables"], key=lambda t: (
                0 if t.startswith("meta.") else 1 if ".dim_" in t else 2, t))
            for table in order:
                data = z.read(f"{table}.csv")
                # Một vài bảng (vd. core.dim_date) được apply_all() nạp sẵn dữ
                # liệu tham chiếu ngay trong migration (INSERT ... generate_series).
                # Xoá trước khi COPY FROM để không đụng khoá chính đã có sẵn —
                # bảng nào apply_all() để trống thì DELETE này là no-op.
                conn.execute(f"DELETE FROM {table}")
                if data.count(b"\n") <= 1:
                    continue                      # chỉ có dòng tiêu đề
                with conn.cursor().copy(
                    f"COPY {table} FROM STDIN WITH CSV HEADER"
                ) as cp:
                    cp.write(data)
            _reset_sequences(conn)
            conn.commit()
            return {
                t: conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                for t in manifest["tables"]
            }


def verify(zip_path: Path, scratch_url: str) -> dict:
    """Khôi phục vào CSDL nháp rồi đối chiếu số dòng với manifest. Chạy mỗi quý.

    Một bản sao lưu chưa từng được thử khôi phục thì không phải bản sao lưu.
    Trả về {"ok": bool, "mismatches": {...}, "counts": {...}}.
    """
    with zipfile.ZipFile(zip_path) as z:
        expected = json.loads(z.read("manifest.json"))["tables"]
    actual = restore(zip_path, scratch_url)
    bad = {t: (expected[t], actual.get(t)) for t in expected if expected[t] != actual.get(t)}
    return {"ok": not bad, "mismatches": bad, "counts": actual}


# --- Chạy trực tiếp: python -m ops.restore_check ------------------------------
# Kiểm tra khôi phục bản sao lưu mới nhất. CHỈ chạy trên CSDL thử nghiệm —
# restore() sẽ từ chối nếu bị trỏ vào DATABASE_URL.
if __name__ == "__main__":
    import os
    from kome.env import nap_env

    nap_env()
    thu_muc = Path(os.environ.get("BACKUP_DIR", "./backups"))
    ban = sorted(thu_muc.glob("kome_*.zip"))
    if not ban:
        raise SystemExit(f"Không có bản sao lưu nào trong {thu_muc}")
    kq = verify(ban[-1], os.environ["DATABASE_URL_TEST"])
    print(f"Bản sao lưu: {ban[-1].name}")
    print("KẾT QUẢ: KHÔI PHỤC ĐƯỢC" if kq["ok"] else f"KẾT QUẢ: LỆCH — {kq['mismatches']}")
    for bang, n in sorted(kq["counts"].items()):
        print(f"   {bang:34s} {n:>9,} dòng")
