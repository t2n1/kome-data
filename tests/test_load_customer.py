from datetime import date
import pandas as pd
import pytest
from kome.loaders import customer
from kome.pipeline import undo_batch

D1 = date(2026, 9, 16)
D2 = date(2026, 9, 17)
D3 = date(2026, 9, 18)


def _nhu_reader(df: pd.DataFrame) -> pd.DataFrame:
    """Đưa DataFrame về ĐÚNG dạng kome.reader.read() trả ra cho loader: cột chữ
    dtype object, ô trống là None (pandas 3 để mặc thì cột chuỗi mang dtype
    "str" và None bị đổi thành NaN — khác với dữ liệu thật đi qua reader)."""
    for c in df.columns:
        df[c] = df[c].astype(object).where(df[c].notna(), None)
    return df


def _df(rank="0003"):
    return _nhu_reader(pd.DataFrame([{
        "customer_code": "000000009292", "customer_name": "株式会社ASIANEX",
        "branch_name": "あじさい支店", "rank_code": rank, "rank_name": "Cランク",
        "salesperson_code": "0105", "salesperson_name": "TRAN THI LAN THANH",
        "closing_day_code": "99", "closing_day_name": "代引請求",
        "postcode": "3720855", "prefecture": "群馬県", "city": "伊勢崎市",
        "address": "長沼町 615-4", "building": "橋下ビル101号", "phone": "0270-75-6396",
        "transfer_account": "0001234567",
    }]))


def test_lan_dau_tao_mot_phien_ban(conn, batch):
    r = customer.load(conn, _df(), D1, batch(1))
    assert r["inserted"] == 1
    n = conn.execute("SELECT count(*) FROM core.dim_customer WHERE is_current").fetchone()[0]
    assert n == 1


def test_khong_doi_gi_thi_khong_tao_phien_ban_moi(conn, batch):
    customer.load(conn, _df(), D1, batch(1))
    r = customer.load(conn, _df(), D2, batch(2))
    assert r["inserted"] == 0 and r["unchanged"] == 1
    n = conn.execute("SELECT count(*) FROM core.dim_customer").fetchone()[0]
    assert n == 1


def test_doi_hang_thi_tao_phien_ban_moi_va_dong_cai_cu(conn, batch):
    customer.load(conn, _df(rank="0003"), D1, batch(1))
    r = customer.load(conn, _df(rank="0001"), D2, batch(2))
    assert r["inserted"] == 1 and r["closed"] == 1
    rows = conn.execute(
        """SELECT rank_code, valid_from, valid_to, is_current FROM core.dim_customer
           WHERE customer_code = '000000009292' ORDER BY valid_from"""
    ).fetchall()
    assert len(rows) == 2
    assert rows[0][0] == "0003" and str(rows[0][2]) == "2026-09-16" and rows[0][3] is False
    assert rows[1][0] == "0001" and rows[1][3] is True


def test_khong_bao_gio_xoa_dong(conn, batch):
    customer.load(conn, _df(rank="0003"), D1, batch(1))
    customer.load(conn, _df(rank="0001"), D2, batch(2))
    customer.load(conn, _df(rank="0002"), D3, batch(3))
    n = conn.execute("SELECT count(*) FROM core.dim_customer").fetchone()[0]
    assert n == 3   # luật bất biến #6


def test_ban_xuat_mot_phan_khong_dong_khach_vang_mat(conn, batch):
    """File chỉ chứa vài khách KHÔNG được hiểu là các khách khác đã biến mất."""
    two = pd.concat([_df(), _df()], ignore_index=True)
    two.loc[1, "customer_code"] = "000000000002"
    customer.load(conn, two, D1, batch(1))
    r = customer.load(conn, _df(), D2, batch(2))  # chỉ 1 khách trong lần nạp thứ hai
    assert r["inserted"] == 0 and r["unchanged"] == 1
    n_current = conn.execute(
        "SELECT count(*) FROM core.dim_customer WHERE is_current"
    ).fetchone()[0]
    assert n_current == 2  # khách vắng mặt vẫn còn is_current=true


def test_gia_tri_rong_on_dinh_qua_cac_lan_nap(conn, batch):
    """Cột để trống không được coi là 'đổi' ở lần nạp sau.

    kome.reader.read() chuẩn hoá ô trống của Excel (NaN) thành None cho MỌI
    cột chữ trước khi tới loader, nên ở đây dựng dữ liệu đúng như loader nhận
    được: None, không phải NaN. (Trước đây customer.py có _norm() riêng để làm
    việc này — đã bỏ, vì chuẩn hoá ở reader thì mọi loader cùng được hưởng.)
    """
    row = _df()
    row.loc[0, "phone"] = None
    row.loc[0, "address"] = None
    r1 = customer.load(conn, row, D1, batch(1))
    assert r1["inserted"] == 1
    row2 = _df()
    row2.loc[0, "phone"] = None
    row2.loc[0, "address"] = None
    r2 = customer.load(conn, row2, D2, batch(2))
    assert r2["inserted"] == 0 and r2["unchanged"] == 1


def _batch_tokuisaki(conn, n: int) -> int:
    """Như fixture batch(), nhưng spec_name='tokuisaki' — UNDO_SCD2 tra theo
    spec_name nên test hoàn tác cần lô thật của loại file này, không dùng
    spec_name='test' mặc định của fixture batch() trong conftest.py."""
    row = conn.execute(
        """INSERT INTO meta.ingest_batch
             (spec_name, source_file, digest, archived_to, row_count, data_date)
           VALUES ('tokuisaki', 'tokuisaki_test.xlsx', %s, '/tmp/tokuisaki_test.xlsx', 0,
                   DATE '2026-01-01')
           RETURNING batch_id""",
        (f"tokuisaki-digest-{n}",),
    ).fetchone()
    conn.commit()
    return row[0]


def _two_df(rank_a="0003"):
    df = pd.concat([_df(rank=rank_a), _df()], ignore_index=True)
    df.loc[1, "customer_code"] = "000000000002"
    return df


def test_hoan_tac_lo_scd2_mo_lai_phien_ban_truoc(conn):
    """Hoàn tác lô SCD2 phải mở lại phiên bản trước đó (is_current=true,
    valid_to=NULL) — không chỉ xoá phiên bản mới, nếu không khách sẽ mất
    hẳn dòng is_current và biến mất khỏi báo cáo."""
    b1 = _batch_tokuisaki(conn, 1)
    b2 = _batch_tokuisaki(conn, 2)
    customer.load(conn, _df(rank="0003"), D1, b1)
    customer.load(conn, _df(rank="0001"), D2, b2)
    undo_batch(conn, b2)
    rows = conn.execute(
        """SELECT rank_code, is_current, valid_to FROM core.dim_customer
           WHERE customer_code = '000000009292'"""
    ).fetchall()
    assert len(rows) == 1                # phiên bản mới đã bị xoá
    assert rows[0][0] == "0003"           # quay về hạng cũ
    assert rows[0][1] is True             # đã mở lại
    assert rows[0][2] is None             # valid_to đã xoá


def test_hoan_tac_khong_lam_mat_hoac_trung_is_current(conn):
    """Một lô vừa đóng khách A (đổi hạng) vừa để khách B không đổi. Sau khi
    hoàn tác, mỗi khách phải có ĐÚNG MỘT dòng is_current=true — không khách
    nào mất phiên bản hiện hành, không khách nào có hai."""
    b1 = _batch_tokuisaki(conn, 1)
    b2 = _batch_tokuisaki(conn, 2)
    customer.load(conn, _two_df(rank_a="0003"), D1, b1)
    customer.load(conn, _two_df(rank_a="0001"), D2, b2)   # A đổi hạng, B không đổi
    undo_batch(conn, b2)
    rows = conn.execute(
        """SELECT customer_code, count(*) FROM core.dim_customer
           WHERE is_current GROUP BY customer_code ORDER BY 1"""
    ).fetchall()
    assert rows == [("000000000002", 1), ("000000009292", 1)]


def test_hoan_tac_lo_sua_trong_ngay_giu_khach_va_tra_lai_gia_tri_cu(conn):
    """[IMPORTANT] Giao điểm "sửa trong ngày" × "hoàn tác" — mất dữ liệu.

    13:30 nạp 得意先全情報 (lô 1); kế toán phát hiện sai, sửa trong OBC, xuất lại,
    kéo–thả lại CÙNG NGÀY (lô 2) -> cập nhật TẠI CHỖ, chỉ còn MỘT dòng; rồi nhận
    ra file thứ hai cũng sai -> bấm Hoàn tác lô 2.

    Nếu dòng bị đè mang luôn batch_id của lô 2 mà không lưu lại giá trị cũ thì
    `DELETE ... WHERE batch_id = lô 2` xoá hẳn dòng duy nhất, bước "mở lại phiên
    bản trước" không còn gì để mở, và KHÁCH BIẾN MẤT khỏi CSDL.

    Đúng phải là: khách còn nguyên, và mang lại đúng giá trị của lô 1.
    """
    b1 = _batch_tokuisaki(conn, 1)
    b2 = _batch_tokuisaki(conn, 2)
    customer.load(conn, _df(rank="0003"), D1, b1)
    r = customer.load(conn, _df(rank="0001"), D1, b2)   # cùng ngày -> sửa tại chỗ
    assert r["updated"] == 1 and r["inserted"] == 0

    undo_batch(conn, b2)

    rows = conn.execute(
        """SELECT rank_code, valid_from, valid_to, is_current, batch_id
           FROM core.dim_customer WHERE customer_code = '000000009292'"""
    ).fetchall()
    assert len(rows) == 1                 # khách KHÔNG bị xoá
    assert rows[0][0] == "0003"           # trả về đúng giá trị của lô 1
    assert rows[0][1] == D1               # valid_from không đổi
    assert rows[0][2] is None             # không sinh khoảng âm
    assert rows[0][3] is True             # vẫn là phiên bản hiện hành
    assert rows[0][4] == b1               # dòng thuộc về lô 1 trở lại


def test_hoan_tac_lo_nap_khac_ngay_van_mo_lai_phien_ban_cu(conn):
    """Chống hồi quy cho hành vi ĐÃ CÓ, cặp đôi với test ngay trên: khi lô 2 nạp
    vào NGÀY KHÁC thì nó tạo phiên bản mới + đóng phiên bản cũ (không sửa tại
    chỗ), nên hoàn tác vẫn phải đi đường cũ — xoá phiên bản mới rồi mở lại phiên
    bản cũ — và KHÔNG được chạm vào cơ chế hoàn nguyên giá trị.
    """
    b1 = _batch_tokuisaki(conn, 1)
    b2 = _batch_tokuisaki(conn, 2)
    customer.load(conn, _df(rank="0003"), D1, b1)
    r = customer.load(conn, _df(rank="0001"), D2, b2)   # khác ngày -> phiên bản mới
    assert r["inserted"] == 1 and r["closed"] == 1 and r["updated"] == 0
    assert conn.execute(
        "SELECT scd2_preimage FROM meta.ingest_batch WHERE batch_id = %s", (b2,)
    ).fetchone()[0] is None               # khác ngày thì không lưu ảnh trước

    undo_batch(conn, b2)

    rows = conn.execute(
        """SELECT rank_code, valid_from, valid_to, is_current, batch_id
           FROM core.dim_customer WHERE customer_code = '000000009292'"""
    ).fetchall()
    assert len(rows) == 1
    assert rows[0][0] == "0003"
    assert rows[0][1] == D1
    assert rows[0][2] is None             # valid_to đã xoá khi mở lại
    assert rows[0][3] is True
    assert rows[0][4] == b1               # dòng vốn của lô 1, không ai đổi


def test_hoan_tac_nhieu_lan_sua_trong_ngay_lui_tung_buoc(conn):
    """Sửa lại BA lần trong cùng một ngày (lô 1 -> 2 -> 3). Hoàn tác lô 3 phải
    lùi về trạng thái lô 2, hoàn tác tiếp lô 2 phải lùi về trạng thái lô 1 —
    mỗi lô giữ ảnh trước của riêng nó, không chồng lấn."""
    b1, b2, b3 = (_batch_tokuisaki(conn, n) for n in (1, 2, 3))
    customer.load(conn, _df(rank="0003"), D1, b1)
    customer.load(conn, _df(rank="0002"), D1, b2)
    customer.load(conn, _df(rank="0001"), D1, b3)

    def _hien_tai():
        return conn.execute(
            """SELECT rank_code, batch_id, count(*) OVER () FROM core.dim_customer
               WHERE customer_code = '000000009292'"""
        ).fetchone()

    assert _hien_tai() == ("0001", b3, 1)
    undo_batch(conn, b3)
    assert _hien_tai() == ("0002", b2, 1)
    undo_batch(conn, b2)
    assert _hien_tai() == ("0003", b1, 1)


def test_sua_roi_xuat_lai_trong_cung_ngay_khong_sinh_khoang_am(conn, batch):
    """[IMPORTANT] 13:30 nạp 得意先全情報; kế toán phát hiện sai hạng, sửa trong
    OBC, xuất lại, kéo–thả lại CÙNG NGÀY.

    Đóng phiên bản cũ bằng `snapshot_date - 1 ngày` khi phiên bản cũ cũng bắt
    đầu đúng ngày đó sinh ra valid_to < valid_from. Mọi truy vấn lịch sử dạng
    `valid_from <= d AND (valid_to IS NULL OR valid_to >= d)` sẽ không trả về
    ngày nào -> dòng đó biến mất khỏi lịch sử vĩnh viễn, đúng thứ mà SCD2 sinh
    ra để giữ. Cùng ngày thì phải CẬP NHẬT TẠI CHỖ.
    """
    customer.load(conn, _df(rank="01"), D1, batch(1))
    r = customer.load(conn, _df(rank="02"), D1, batch(2))   # cùng ngày D1
    assert r["inserted"] == 0 and r["closed"] == 0 and r["updated"] == 1

    rows = conn.execute(
        """SELECT rank_code, valid_from, valid_to, is_current FROM core.dim_customer
           WHERE customer_code = '000000009292'"""
    ).fetchall()
    assert len(rows) == 1                       # một dòng, không phải hai
    assert rows[0][0] == "02"                   # mang hạng MỚI
    assert rows[0][1] == D1                     # valid_from = đúng ngày đó
    assert rows[0][2] is None                   # không có khoảng âm
    assert rows[0][3] is True


def test_mau_16_cot_ghi_cot_moi_va_de_NULL_cot_da_bo(conn, batch):
    """043: năm cột mới được ghi (số tài khoản giữ số 0 đầu); sáu cột đã bỏ khỏi
    bản xuất nằm NULL ở phiên bản mới — không ai ghi giá trị đoán vào đó."""
    customer.load(conn, _df(), D1, batch(1))
    r = conn.execute(
        """SELECT building, rank_name, salesperson_name, closing_day_name, transfer_account,
                  category_code, order_app_code, price_level_code, billing_customer_code,
                  invoice_reg_no, spot_flag
             FROM core.dim_customer WHERE is_current""").fetchone()
    assert r[:5] == ("橋下ビル101号", "Cランク", "TRAN THI LAN THANH", "代引請求", "0001234567")
    assert r[5:] == (None,) * 6


def test_hoan_tac_lo_CU_voi_anh_truoc_theo_mau_cu(conn):
    """[IMPORTANT] Lô nạp theo mẫu 17 cột cũ lưu ảnh trước (`scd2_preimage`) với
    sáu cột đã bỏ và KHÔNG có cột mới. Hoàn tác lô đó sau khi đổi mẫu phải gán
    lại đúng những cột ảnh trước đã chụp — không nổ KeyError, không ghi NULL đè
    lên cột mới mà lô cũ chưa từng chạm."""
    import json
    b1 = _batch_tokuisaki(conn, 1)
    b2 = _batch_tokuisaki(conn, 2)
    customer.load(conn, _df(rank="0001"), D1, b2)
    conn.execute("UPDATE core.dim_customer SET price_level_code = '10'")
    cu = {"customer_name": "株式会社ASIANEX", "branch_name": "あじさい支店", "rank_code": "0003",
          "category_code": "0202", "order_app_code": "0001", "salesperson_code": "0105",
          "price_level_code": "03", "closing_day_code": "99",
          "billing_customer_code": "000000009292", "postcode": "3720855",
          "prefecture": "群馬県", "city": "伊勢崎市", "address": "長沼町 615-4",
          "phone": "0270-75-6396", "invoice_reg_no": "", "spot_flag": "0"}
    conn.execute("UPDATE meta.ingest_batch SET scd2_preimage = %s WHERE batch_id = %s",
                 (json.dumps([{"code": "000000009292", "batch_id": b1, "values": cu}]), b2))
    conn.commit()

    undo_batch(conn, b2)

    r = conn.execute(
        """SELECT rank_code, price_level_code, building, transfer_account, batch_id
             FROM core.dim_customer WHERE customer_code = '000000009292'""").fetchone()
    assert r == ("0003", "03", "橋下ビル101号", "0001234567", b1)


def test_csdl_chan_khoang_thoi_gian_am(conn, batch):
    """Thắt lưng thêm dây đeo: kể cả khi code lỗi, CHECK ở 010_*.sql phải chặn
    valid_to < valid_from ngay tại CSDL."""
    import psycopg
    b = batch(1)
    customer.load(conn, _df(), D2, b)
    with pytest.raises(psycopg.errors.CheckViolation):
        conn.execute(
            "UPDATE core.dim_customer SET valid_to = valid_from - 1 WHERE is_current"
        )
    conn.rollback()
