# kome/pipeline.py
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path
import re
from kome import archive, gates
from kome.config import SPECS, FileSpec
from kome.reader import read, ColumnMismatch
from kome.loaders import inventory, customer, sales, master, price, so_cai

# SPECS chuyển sang kome/config.py — xem ghi chú ở đó. Vẫn nhập lại tên ở
# đây vì nhiều nơi đã gọi `from kome.pipeline import SPECS`.

# shohin/shiiresaki/chokusousaki: upsert đơn giản theo khoá, không giữ lịch sử
# -> một loader chung điều khiển bằng cấu hình (kome/loaders/master.py).
# tanka (取引単価データ) KHÔNG dùng chung được: nguồn có 20 cột giá NẰM NGANG,
# bảng đích core.fact_price_list là DỌC -> cần loader riêng biết xoay trục
# (kome/loaders/price.py). Xem ghi chú trong config/files.yml.
LOADERS = {
    "zaiko": inventory.load,
    "tokuisaki": customer.load,
    "uriage": sales.load,
    "meisai": sales.load_meisai,
    "shohin": master.make_loader(
        "core.dim_product", ["product_code"],
        ["product_code", "product_name", "name_ja", "kind_code", "kind_name",
         "food_category_code", "food_category_name", "rank_code", "rank_name",
         "compete_code", "barcode", "unit", "case_qty", "shelf_code", "introduced_on"]),
    "shiiresaki": master.make_loader(
        "core.dim_supplier", ["supplier_code"], ["supplier_code", "supplier_name"]),
    "chokusousaki": master.make_loader(
        "core.dim_shipto", ["shipto_code"],
        ["shipto_code", "shipto_name", "customer_code", "postcode", "prefecture",
         "city", "address", "phone", "lead_time_code"]),
    "tanka": price.load,
    "seikyu_motocho": so_cai.load,
}

# Bảng nào cần dọn khi hoàn tác một lô, theo từng loại file.
# Thêm loader mới thì BẮT BUỘC thêm mục ở đây, nếu không hoàn tác sẽ sót bảng.
UNDO_TABLES = {
    "zaiko": ["core.fact_inventory_daily"],
    "tokuisaki": ["core.dim_customer"],
    "uriage": ["core.fact_sales_line"],
    "meisai": ["core.fact_sales_line"],
    "shohin": ["core.dim_product"],
    "shiiresaki": ["core.dim_supplier"],
    "chokusousaki": ["core.dim_shipto"],
    "tanka": ["core.fact_price_list"],
    "seikyu_motocho": ["core.fact_ar_ledger"],
}

# Bảng SCD2: hoàn tác phải mở lại phiên bản trước đó, không chỉ xoá phiên bản
# mới — nếu không, khách bị đóng valid_to ở lô đó sẽ mất hẳn is_current=true
# và biến mất khỏi mọi báo cáo. Dạng:
#   spec_name -> (tên bảng, cột khoá nghiệp vụ, các cột được hoàn nguyên)
# Cột thứ ba là danh sách cột mà loader chép vào `meta.ingest_batch.scd2_preimage`
# khi đè tại chỗ, để hoàn tác gán trả lại — phải TRÙNG với TRACKED của loader.
# Bảng nào có mặt ở đây thì undo_batch() xử lý riêng, KHÔNG xoá lại theo
# UNDO_TABLES nữa (tránh xoá hai lần) — nhưng vẫn giữ trong UNDO_TABLES để
# test lưới an toàn set(LOADERS) == set(UNDO_TABLES) còn đúng.
UNDO_SCD2 = {"tokuisaki": ("core.dim_customer", "customer_code",
                            customer.TRACKED + customer.TRACKED_CU)}

@dataclass
class IngestResult:
    ok: bool
    spec_name: str | None = None
    row_count: int = 0
    total: int = 0
    batch_id: int | None = None
    skipped: bool = False
    blockers: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    data_date: date | None = None

def identify(path: Path) -> tuple[FileSpec, date] | tuple[None, None]:
    """Cổng 1: nhận ra loại file và ngày dữ liệu từ tên file."""
    for spec in SPECS.values():
        m = re.match(spec.filename_pattern, path.name)
        if m:
            g = m.groupdict()
            if g.get("date"):
                return spec, datetime.strptime(g["date"], "%Y%m%d").date()
            # Tên gốc của OBC mang cả kỳ (sổ cái): ngày dữ liệu = ngày CUỐI kỳ.
            return spec, date(int(g["y"]), int(g["m"]), int(g["d"]))
    return None, None

def _kiem_tra_trung_nguon(conn, spec: FileSpec, df) -> list[gates.Blocker]:
    """Chặn nạp 売上伝票データ và 売上明細表 CHỒNG NGÀY nhau.

    Hai loại file này cùng ghi vào core.fact_sales_line (phân biệt bằng cột
    source) -- nếu cả hai cùng có dữ liệu một ngày thì MỌI báo cáo mart sẽ
    cộng doanh thu ngày đó hai lần mà không ai biết (mart/ chưa có logic
    chọn nguồn -- xem ghi chú "Việc cố tình để lại" trong plan triển khai
    tính năng này). Chỉ áp dụng cho hai spec này.
    """
    if spec.name not in ("uriage", "meisai"):
        return []
    nguon_khac = "meisai" if spec.name == "uriage" else "uriage"
    ngay = sorted(d for d in df["sales_date"].dropna().unique())
    if not ngay:
        return []
    rows = conn.execute(
        """SELECT DISTINCT sales_date FROM core.fact_sales_line
           WHERE source = %s AND sales_date = ANY(%s)""",
        (nguon_khac, list(ngay)),
    ).fetchall()
    if not rows:
        return []
    trung = sorted(r[0] for r in rows)
    return [gates.Blocker(
        3,
        f"Đã có dữ liệu nguồn {nguon_khac} cho {len(trung)} ngày "
        f"({trung[0]}..{trung[-1]}) — nạp thêm {spec.name} sẽ cộng doanh thu "
        f"hai lần. Hoàn tác lô {nguon_khac} trước nếu muốn đổi nguồn.")]


def _chuan_bi(conn, path: Path):
    """Năm cổng kiểm — KHÔNG ghi gì. Trả (chuẩn bị, kết quả): chuẩn bị là None
    khi file không được đi tiếp (chặn, hay đã nạp rồi)."""
    spec, data_date = identify(path)
    if spec is None:
        return None, IngestResult(ok=False, blockers=[gates.Blocker(1, f"Không nhận ra loại file: {path.name}")])

    digest = archive.sha256_of(path)
    if archive.already_loaded(conn, digest):
        return None, IngestResult(ok=True, spec_name=spec.name, skipped=True, data_date=data_date)

    try:
        df = read(path, spec)
    except ColumnMismatch as e:
        return None, IngestResult(ok=False, spec_name=spec.name, data_date=data_date,
                                  blockers=[gates.Blocker(2, str(e))])

    blockers, warnings = gates.check(path, spec, df, archive.previous_stats(conn, spec.name))
    blockers = blockers + _kiem_tra_trung_nguon(conn, spec, df)
    if blockers:
        return None, IngestResult(ok=False, spec_name=spec.name, blockers=blockers,
                                  warnings=warnings, data_date=data_date)

    # Tổng tiền đại diện: cột khai TAY trong files.yml (spec.total_column),
    # không phải money_columns[-1]. Xem ghi chú ở kome/config.py.
    total = int(df[spec.total_column].sum()) if spec.total_column else 0
    return (spec, data_date, digest, df, total), IngestResult(
        ok=True, spec_name=spec.name, row_count=len(df), total=total,
        warnings=warnings, data_date=data_date)


def kiem(conn, path: Path) -> IngestResult:
    """Bước 1 của nạp hai bước (màn Kho dữ liệu → Nạp): chạy đủ 5 cổng như
    `ingest` nhưng KHÔNG ghi một dòng nào vào `core` hay `meta` — chỉ đọc
    (lô trước để so, file đã nạp chưa, ngày trùng nguồn). Bước 2 gọi lại
    `ingest` ĐẦY ĐỦ, tức 5 cổng chạy lại trên trạng thái kho lúc xác nhận: ai
    nạp chen vào giữa hai bước thì lần kiểm thứ hai vẫn đúng."""
    return _chuan_bi(conn, path)[1]


def ingest(conn, path: Path, archive_dir: Path | None) -> IngestResult:
    """`archive_dir=None` = không lưu file gốc (bản Vercel, 045)."""
    chuan_bi, kq = _chuan_bi(conn, path)
    if chuan_bi is None:
        return kq
    spec, data_date, digest, df, total = chuan_bi
    warnings = kq.warnings
    batch_id = archive.store(conn, path, spec.name, digest, len(df), total,
                             archive_dir, data_date)

    # archive.store() đã COMMIT dòng meta.ingest_batch. Nếu loader lỗi sau đó
    # (mất kết nối giữa executemany, tràn bigint, spec có trong files.yml mà
    # quên thêm vào LOADERS -> KeyError, ...) thì lô nằm lại trong CSDL với
    # undone_at IS NULL, và lần sau archive.already_loaded() thấy digest đó
    # nên trả skipped=True: màn hình báo XANH "đã nạp rồi" trong khi core có
    # 0 dòng. File bị bỏ qua VĨNH VIỄN mà không ai biết.
    #
    # Vì vậy: mọi lỗi của loader đều phải huỷ lô ngay — rollback phần dở dang,
    # xoá dữ liệu đã ghi theo batch_id, đặt undone_at, xoá file đã chép vào
    # kho lưu trữ — rồi NÉM LẠI để tầng trên hiện lỗi thật, không báo xanh.
    try:
        LOADERS[spec.name](conn, df, data_date, batch_id)
    except Exception:
        _huy_lo_hong(conn, batch_id)
        raise

    return IngestResult(ok=True, spec_name=spec.name, row_count=len(df),
                        total=total, batch_id=batch_id, warnings=warnings,
                        data_date=data_date)


def _huy_lo_hong(conn, batch_id: int) -> None:
    """Dọn sạch một lô mà loader vừa làm hỏng: không để lại lô mồ côi.

    Việc này cũng đóng luôn khoảng trống của Task 5 (`archive.store()` để lại
    file mồ côi trong kho lưu trữ nếu bước sau thất bại).
    """
    try:
        conn.rollback()      # bỏ phần loader đã ghi mà chưa commit
    except Exception:
        return               # kết nối đã chết: không dọn được, cứ để lỗi nổi lên
    try:
        row = conn.execute(
            "SELECT archived_to FROM meta.ingest_batch WHERE batch_id = %s", (batch_id,)
        ).fetchone()
        undo_batch(conn, batch_id)   # xoá dữ liệu đã commit (nếu có) + đặt undone_at
        if row and row[0]:
            Path(row[0]).unlink(missing_ok=True)
    except Exception as e:
        # Lỗi gốc quan trọng hơn, đừng che nó bằng lỗi dọn dẹp — nhưng cũng
        # đừng nuốt im lặng: ghi ra nhật ký máy chủ để còn truy được.
        print(f"[KOME] KHÔNG dọn được lô hỏng {batch_id}: {type(e).__name__}: {e}")


def undo_batch(conn, batch_id: int) -> int:
    """Xoá dữ liệu của một lô rồi đánh dấu lô đã huỷ. Trả về số dòng đã xoá.

    KHÔNG xoá dòng trong meta.ingest_batch — chỉ đặt undone_at (luật bất biến #6).

    Bảng SCD2 (UNDO_SCD2) được xử lý riêng theo 4 bước: (0) hoàn nguyên các
    dòng lô này ĐÈ TẠI CHỖ (xuất lại trong cùng ngày) về giá trị cũ đã lưu ở
    `meta.ingest_batch.scd2_preimage`, (1) lấy danh sách khoá nghiệp vụ bị đụng
    tới ở lô này, (2) xoá phiên bản mới do lô này tạo, (3) mở lại phiên bản còn
    lại mới nhất của từng khoá đó (is_current=true, valid_to=NULL) — nếu không,
    khách bị đóng ở lô này sẽ mất hẳn is_current và biến mất khỏi báo cáo mà
    không ai biết.

    Bước (0) BẮT BUỘC chạy trước (1)-(2): dòng bị đè tại chỗ mang batch_id của
    lô này, nên nếu xoá trước thì dòng DUY NHẤT của khách bị xoá hẳn và (3)
    không còn gì để mở lại — khách biến mất. Hoàn nguyên xong, batch_id của
    dòng quay về lô cũ nên (1)-(2) không đụng tới nó nữa, đúng như mong muốn:
    dòng ấy không phải do lô này tạo ra.

    Số trả về là số dòng ĐÃ XOÁ, không tính dòng được hoàn nguyên tại chỗ.
    """
    row = conn.execute(
        "SELECT spec_name FROM meta.ingest_batch WHERE batch_id = %s", (batch_id,)
    ).fetchone()
    if row is None:
        return 0
    spec_name = row[0]
    deleted = 0

    scd2 = UNDO_SCD2.get(spec_name)
    if scd2:
        table, key, cols = scd2
        _hoan_nguyen_de_tai_cho(conn, batch_id, table, key, cols)
        codes = [
            r[0] for r in conn.execute(
                f"SELECT DISTINCT {key} FROM {table} WHERE batch_id = %s", (batch_id,)
            ).fetchall()
        ]
        cur = conn.execute(f"DELETE FROM {table} WHERE batch_id = %s", (batch_id,))
        deleted += cur.rowcount
        if codes:
            conn.execute(
                f"""UPDATE {table} d SET is_current = true, valid_to = NULL
                    FROM (SELECT {key} AS k, max(valid_from) AS vf FROM {table}
                          WHERE {key} = ANY(%s) GROUP BY {key}) latest
                    WHERE d.{key} = latest.k AND d.valid_from = latest.vf""",
                (codes,),
            )

    for table in UNDO_TABLES.get(spec_name, []):
        if scd2 and table == scd2[0]:
            continue   # đã xử lý ở nhánh SCD2 phía trên
        cur = conn.execute(f"DELETE FROM {table} WHERE batch_id = %s", (batch_id,))
        deleted += cur.rowcount

    archive.undo(conn, batch_id)
    return deleted


def _hoan_nguyen_de_tai_cho(conn, batch_id: int, table: str, key: str,
                            cols: list[str]) -> int:
    """Bước (0) của hoàn tác SCD2: trả các dòng lô này đè tại chỗ về giá trị cũ.

    Điều kiện `batch_id = %s` khiến hàm này chỉ đụng đúng những dòng CÒN thuộc
    lô đang hoàn tác: gọi hoàn tác hai lần, hay hoàn tác một lô cũ sau khi đã có
    lô mới hơn đè lên, đều không ghi đè nhầm dữ liệu của người khác.
    """
    row = conn.execute(
        "SELECT scd2_preimage FROM meta.ingest_batch WHERE batch_id = %s", (batch_id,)
    ).fetchone()
    preimage = row[0] if row else None
    if not preimage:
        return 0
    # Mỗi ảnh trước chỉ gán lại ĐÚNG những cột nó đã chụp: lô nạp theo mẫu cũ chụp
    # sáu cột đã bỏ (customer.TRACKED_CU) và không có cột mới; lô mẫu mới thì ngược
    # lại. Gán NULL cho cột ảnh trước không chụp là xoá giá trị mà lô đó chưa từng đè.
    # Tên cột lấy từ `cols` (danh sách của code), không bao giờ từ khoá JSON.
    nhom: dict[tuple, list] = {}
    for e in preimage:
        cs = tuple(c for c in cols if c in e["values"])
        nhom.setdefault(cs, []).append(e)
    with conn.cursor() as cur:
        for cs, ds in nhom.items():
            sets = "".join(f"{c} = %s, " for c in cs)
            cur.executemany(
                f"""UPDATE {table} SET {sets}batch_id = %s
                    WHERE {key} = %s AND is_current AND batch_id = %s""",
                [(*(e["values"][c] for c in cs), e["batch_id"], e["code"], batch_id)
                 for e in ds],
            )
    conn.commit()
    return len(preimage)
