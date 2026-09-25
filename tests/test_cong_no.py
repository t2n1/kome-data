"""Đợt 6 — sổ công nợ 請求先元帳: bộ nạp, cổng, mart (migration 038).

File mẫu dựng lại ĐÚNG cấu trúc đã đo trên file thật 2026-09-24 (5 dòng thông
tin, header dòng 6, dòng 繰越残高 / chi tiết / 伝票計 / ［ n月計］ / 【合計】) —
không dùng dữ liệu khách thật."""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from kome.pipeline import identify, ingest, undo_batch

HEADER = ['請求先コード', '請求先名', '請求締日コード', '請求締日名', '行タイトル', '日付', '伝票No.',
          '法人口座名', 'クレジット会社コード', 'クレジット会社名', '期日債権番号', '決済日付', '債権額',
          '債権調整額', '売上額', '消費税額', '入金額', '入金調整額', '残高', '摘要']
I = {h: i for i, h in enumerate(HEADER)}


def _dong(ma, ten, dk_ma, dk, tieu_de="", **o):
    r = [""] * len(HEADER)
    r[0], r[1], r[2], r[3], r[4] = ma, ten, dk_ma, dk, tieu_de
    for k, v in o.items():
        r[I[k]] = v
    return r


def ben(ma, dk, mang_sang, su_kien, ten=None, dk_ma="97", sai_tong=0):
    """Một bên nhận hoá đơn. su_kien: [("ban", ngày, số phiếu, 債権額) | ("thu", ngày, số, 入金額)
    | ("thu_khong_tru", ngày, số, 入金額)] — cái cuối mô phỏng nhóm 0090… của file thật:
    phiếu thu hiện ra mà 残高 không đổi và 【合計】.入金額 = 0."""
    ten = ten or f"KHÁCH {ma}"
    out = [_dong(ma, ten, dk_ma, dk, "繰越残高", 残高=float(mang_sang))]
    so_du, tong_no, tong_thu = mang_sang, 0, 0
    for loai, ngay, so, tien in su_kien:
        if loai == "ban":
            so_du += tien; tong_no += tien
            out.append(_dong(ma, ten, dk_ma, dk, 日付=ngay, **{"伝票No.": so}, 債権額=float(tien),
                             売上額=float(tien), 消費税額=0.0, 残高=float(so_du)))
            out.append(_dong(ma, ten, dk_ma, dk, "伝票計", 債権額=float(tien), 売上額=float(tien), 入金額=0.0))
        elif loai == "thu":
            so_du -= tien; tong_thu += tien
            out.append(_dong(ma, ten, dk_ma, dk, 日付=ngay, **{"伝票No.": so}, 法人口座名="NGÂN HÀNG",
                             入金額=float(tien), 残高=float(so_du)))
        else:
            out.append(_dong(ma, ten, dk_ma, dk, 日付=ngay, **{"伝票No.": so}, 入金額=float(tien),
                             残高=float(so_du)))
    if su_kien:
        out.append(_dong(ma, ten, dk_ma, dk, "［ 5月計］", 債権額=float(tong_no), 売上額=float(tong_no),
                         入金額=float(tong_thu)))
        out.append(_dong(ma, ten, dk_ma, dk, "【合計】", 債権額=float(tong_no + sai_tong),
                         売上額=float(tong_no), 入金額=float(tong_thu)))
    return out


def ghi_file(path: Path, dong, ky="2026年 5月 1日　～　2026年 7月31日", truc="請求先"):
    thong_tin = [["帳票名", "得意先元帳"], ["法人名", "株式会社KOME"], ["集計期間", ky],
                 ["集計軸項目", truc], ["売上伝票の表示", "伝票単位"]]
    rows = [r + [""] * (len(HEADER) - len(r)) for r in thong_tin] + [HEADER] + dong
    pd.DataFrame(rows).to_excel(path, sheet_name="得意先元帳", index=False, header=False)
    return path


def dem(n=100):
    """Các bên số dư 0 cho đủ min_rows (100 dòng sau khi bỏ tổng phụ)."""
    out = []
    for i in range(n):
        out += ben(f"8888888{i:05d}", "その都度請求", 0, [], dk_ma="00")
    return out


TEN = "請求先元帳_2026年 5月 1日　～　2026年 7月31日.xlsx"


def test_nhan_ca_ten_goc_OBC_lan_dang_ngay_ngay_du_lieu_la_CUOI_ky():
    spec, d = identify(Path(TEN))
    assert spec.name == "seikyu_motocho" and d == date(2026, 7, 31)
    spec, d = identify(Path("請求先元帳_20260731.xlsx"))
    assert spec.name == "seikyu_motocho" and d == date(2026, 7, 31)
    # 得意先元帳 (không có 残高) CHƯA có bộ nạp — không được nhận nhầm thành sổ công nợ.
    assert identify(Path("得意先元帳_2026年 5月 1日　～　2026年 7月31日.xlsx")) == (None, None)


def _nap(conn, tmp_path, dong, ten=TEN, **kw):
    p = ghi_file(tmp_path / ten, dong, **kw)
    return ingest(conn, p, tmp_path / "archive")


def test_nap_giu_mang_sang_va_chi_tiet_bo_dong_tong_phu(conn, tmp_path):
    d = ben("000000000010", "末締/翌月10日", 380988,
            [("thu", date(2026, 5, 8), "018105", 380988), ("ban", date(2026, 5, 12), "081666", 25108)]) + dem()
    r = _nap(conn, tmp_path, d)
    assert r.ok, r.blockers
    assert r.warnings == []
    k = dict(conn.execute("""SELECT line_kind, count(*) FROM core.fact_ar_ledger
                             WHERE billing_customer_code = '000000000010' GROUP BY 1""").fetchall())
    assert k == {"mang_sang": 1, "phieu_thu": 1, "phieu_ban": 1}
    ky = conn.execute("SELECT DISTINCT period_from, period_to FROM core.fact_ar_ledger").fetchall()
    assert ky == [(date(2026, 5, 1), date(2026, 7, 31))]


def test_sai_truc_so_bi_chan_o_cong_2(conn, tmp_path):
    r = _nap(conn, tmp_path, dem(), truc="得意先")
    assert not r.ok and r.blockers[0].gate == 2
    assert "集計軸項目" in r.blockers[0].message


def test_dong_tieu_de_la_bi_chan(conn, tmp_path):
    d = dem() + [_dong("000000000099", "X", "00", "その都度請求", "小計??", 債権額=1.0)]
    r = _nap(conn, tmp_path, d)
    assert not r.ok and r.blockers[0].gate == 2


def test_tong_lech_so_du_cuoi_canh_bao_cong_5(conn, tmp_path):
    d = ben("000000000010", "末締/翌月10日", 0, [("ban", date(2026, 5, 12), "081666", 1000)], sai_tong=7) + dem()
    r = _nap(conn, tmp_path, d)
    assert r.ok
    assert [w.gate for w in r.warnings] == [5]


def test_so_du_la_cua_OBC_va_da_thu_suy_tu_dang_thuc(conn, tmp_path):
    """Nhóm 0090…: phiếu thu KHÔNG làm giảm 残高. Cộng tay 入金額 ra "đã thu 500"
    — sai; đẳng thức mang sang + nợ − số dư ra 0."""
    d = ben("009000000002", "末締/翌月10日", 1000,
            [("ban", date(2026, 6, 19), "085273", 0), ("thu_khong_tru", date(2026, 6, 19), "018318", 500)]) \
        + ben("000000000020", "末締/翌月末日", 200,
              [("ban", date(2026, 5, 3), "08001", 300), ("thu", date(2026, 6, 1), "01801", 450)]) + dem()
    assert _nap(conn, tmp_path, d).ok
    r = dict((m, (s, t)) for m, s, t in conn.execute(
        "SELECT billing_customer_code, so_du, da_thu_ky FROM mart.cong_no_ben_tra").fetchall())
    assert r["009000000002"] == (1000, 0)
    assert r["000000000020"] == (50, 450)


def test_fifo_phan_con_no_la_cua_phieu_MOI_NHAT_va_mang_sang(conn, tmp_path):
    d = ben("000000000030", "末締/翌月10日", 100,
            [("ban", date(2026, 5, 12), "A1", 50), ("thu", date(2026, 6, 10), "T1", 100),
             ("ban", date(2026, 6, 20), "A2", 40)]) \
        + ben("000000000031", "末締/翌月10日", 500, [("ban", date(2026, 7, 1), "B1", 100)]) + dem()
    assert _nap(conn, tmp_path, d).ok
    # Bên 30: số dư 90 = A2 (40) + 50 của A1 → A1 còn 50/50.
    p = {(r[0], r[1]): r[2:] for r in conn.execute(
        """SELECT billing_customer_code, coalesce(slip_no, '(trước kỳ)'), tong, con_lai, da_thu, nhom_tuoi
           FROM mart.cong_no_phieu""").fetchall()}
    assert p[("000000000030", "A2")] == (40, 40, 0, "d60")
    assert p[("000000000030", "A1")] == (50, 50, 0, "d90")
    assert ("000000000030", "(trước kỳ)") not in p
    # Bên 31: số dư 600 > phiếu trong kỳ 100 → 500 mang sang, không có số phiếu.
    assert p[("000000000031", "B1")] == (100, 100, 0, "d30")
    assert p[("000000000031", "(trước kỳ)")] == (None, 500, None, "truoc_ky")


def test_fifo_phieu_bien_nhan_mot_phan(conn, tmp_path):
    d = ben("000000000040", "末締/翌月10日", 0,
            [("ban", date(2026, 5, 1), "C1", 100), ("ban", date(2026, 5, 2), "C2", 100),
             ("thu", date(2026, 6, 10), "T", 130)]) + dem()
    assert _nap(conn, tmp_path, d).ok
    p = dict((s, (c, t)) for s, c, t in conn.execute(
        "SELECT slip_no, con_lai, da_thu FROM mart.cong_no_phieu WHERE billing_customer_code = '000000000040'"))
    assert p == {"C2": (70, 30)}


def test_han_tra_suy_tu_ten_dieu_kien_chi_hai_mau(conn, tmp_path):
    d = ben("000000000050", "末締/翌月10日", 0, [("ban", date(2026, 5, 12), "H1", 10)]) \
        + ben("000000000051", "末締/翌月末日", 0, [("ban", date(2026, 5, 12), "H2", 10)], dk_ma="99") \
        + ben("000000000052", "代引請求", 0, [("ban", date(2026, 5, 12), "H3", 10)], dk_ma="01") + dem()
    assert _nap(conn, tmp_path, d).ok
    p = {s: (h, q) for s, h, q in conn.execute(
        "SELECT slip_no, han_tra, qua_han_ngay FROM mart.cong_no_phieu WHERE slip_no LIKE 'H%'")}
    assert p["H1"] == (date(2026, 6, 10), 51)
    assert p["H2"] == (date(2026, 6, 30), 31)
    assert p["H3"] == (None, None)          # 代引: không suy được hạn → không bao giờ "quá hạn"


def test_lo_ky_moi_nhat_thang_lo_nap_sau_ky_cu_va_hoan_tac(conn, tmp_path):
    moi = ben("000000000060", "末締/翌月10日", 0, [("ban", date(2026, 7, 1), "N", 900)]) + dem()
    cu = ben("000000000060", "末締/翌月10日", 0, [("ban", date(2026, 3, 1), "O", 300)]) + dem()
    r1 = _nap(conn, tmp_path, moi)
    r2 = _nap(conn, tmp_path, cu, ten="請求先元帳_20260430.xlsx",
              ky="2026年 2月 1日　～　2026年 4月30日")
    assert r1.ok and r2.ok
    so_du = lambda: conn.execute("""SELECT so_du FROM mart.cong_no_ben_tra
                                    WHERE billing_customer_code = '000000000060'""").fetchone()[0]
    assert so_du() == 900                    # kỳ kết thúc muộn nhất thắng, không phải lô nạp sau
    undo_batch(conn, r1.batch_id); conn.commit()
    assert so_du() == 300                    # hoàn tác → lô trước quay lại
    assert conn.execute("SELECT count(*) FROM core.fact_ar_ledger WHERE batch_id = %s",
                        (r1.batch_id,)).fetchone()[0] == 0


# ---- Màn hình / API ---------------------------------------------------------

def _mau_man(conn, tmp_path):
    d = ben("000000000070", "末締/翌月10日", 0,
            [("ban", date(2026, 5, 12), "Q1", 1000), ("ban", date(2026, 7, 20), "Q2", 500)]) \
        + ben("000000000071", "代引請求", 0, [("ban", date(2026, 7, 30), "Q3", 300)], dk_ma="01") \
        + ben("000000000072", "前払い", -200, [], dk_ma="02") + dem()
    assert _nap(conn, tmp_path, d).ok


def test_tong_hop_chi_cong_dong_view(conn, tmp_path):
    from kome import cong_no as CN
    _mau_man(conn, tmp_path)
    m = CN.man_hinh(conn)
    tq = m["tq"]
    assert m["moc"] == date(2026, 7, 31)
    assert tq["tong_phai_thu"] == 1800 and tq["so_ben_no"] == 2
    # Q1: hạn 10/6 → quá 51 ngày; Q2: hạn 10/8 → chưa tới; Q3 代引 → không suy được hạn.
    assert (tq["qua_han"], tq["so_phieu_qua_han"]) == (1000, 1)
    assert tq["khong_suy_han"] == 300
    assert (tq["tra_du"], tq["so_ben_tra_du"]) == (-200, 1)
    tuoi = {t["nhom"]: t["tien"] for t in tq["tuoi"]}
    assert tuoi == {"d30": 800, "d60": 0, "d90": 1000, "d90p": 0, "truoc_ky": 0}
    assert any("KHÁCH 000000000070" in v for v in m["viec"])


def test_chua_nap_so_thi_man_noi_chua_co(conn):
    from kome import cong_no as CN
    assert CN.man_hinh(conn)["co_du_lieu"] is False
    assert CN.khoi_tong_quan(conn) is None
    assert CN.cua_khach(conn, "000000000070")["co_so"] is False


def test_api_cong_no_va_vo_react(conn, tmp_path, test_db_url):
    from fastapi.testclient import TestClient
    from kome.web.app import create_app
    _mau_man(conn, tmp_path)
    c = TestClient(create_app(db_url=test_db_url))
    r = c.get("/api/cong-no")
    assert r.status_code == 200, r.text
    assert r.json()["tq"]["tong_phai_thu"] == 1800
    r = c.get("/api/cong-no/khach/000000000070")
    assert r.status_code == 200 and r.json()["ben"]["so_du"] == 1500
    assert c.get("/cong-no").status_code == 200


def test_ben_tra_cua_khach_doc_tu_PHIEU_BAN_GAN_NHAT(conn, tmp_path, batch):
    """043: master 得意先全情報 không còn 請求先コード — bên nhận hoá đơn của khách
    là 請求先コード trên phiếu bán GẦN NHẤT (khách đổi bên thì theo bên mới); khách
    chưa có phiếu bán nào là bên của chính mình. Tab Công nợ của hồ sơ khách và
    `so_khach` của mart.cong_no_ben_tra đọc CÙNG view đó."""
    from kome import cong_no as CN
    from kome.loaders import sales
    _mau_man(conn, tmp_path)
    b = batch(777)
    for ma in ("000000000099", "000000000098"):
        conn.execute(
            """INSERT INTO core.dim_customer (customer_code, valid_from, is_current,
                                              customer_name, batch_id)
               VALUES (%s, '2025-01-01', true, %s, %s)""", (ma, f"KHÁCH {ma}", b))
    for i, (ngay, ben_) in enumerate([(date(2026, 5, 1), "000000000072"),
                                      (date(2026, 7, 15), "000000000071")]):
        sales.load(conn, pd.DataFrame([{
            "slip_no": f"B{i}", "line_seq": 1, "sales_date": ngay,
            "customer_code": "000000000099", "billing_customer_code": ben_,
            "product_code": "XT07", "pack_code": "02", "case_qty": 1, "qty": 1,
            "unit_price": 100, "unit_cost": 50, "amount": 110, "tax_amount": 10,
            "cost": 50, "gross_profit": 50, "paid_amount": 0, "batch_id": b}]), ngay, b)
    conn.commit()

    assert CN.cua_khach(conn, "000000000099")["ben"]["so_du"] == 300   # bên 071, không phải 072
    assert conn.execute(
        """SELECT billing_customer_code, tu_phieu_ban FROM mart.ben_tra_cua_khach
            WHERE customer_code = '000000000098'""").fetchone() == ("000000000098", False)
    so_khach = dict(conn.execute(
        "SELECT billing_customer_code, so_khach FROM mart.cong_no_ben_tra").fetchall())
    assert so_khach["000000000071"] == 1 and so_khach["000000000072"] == 0


def test_han_tra_TUNG_LAN_la_5_ngay_lam_viec_sau_ngay_xuat(conn, tmp_path):
    """044: その都度請求 trả trong 5 ngày làm việc sau ngày xuất hàng (chủ DN xác
    nhận 2026-09-25). Phiếu thứ Năm 30/7/2026 → 31/7 (T6), 3/8, 4/8, 5/8, 6/8 → hạn
    6/8; mốc sổ 31/7 nên CHƯA quá hạn. Phiếu 1/7 → hạn 8/7 → quá 23 ngày."""
    d = ben("000000000080", "その都度請求", 0,
            [("ban", date(2026, 7, 1), "T1", 400), ("ban", date(2026, 7, 30), "T2", 600)],
            dk_ma="00") + dem()
    assert _nap(conn, tmp_path, d).ok
    han = dict((r[0], (r[1], r[2])) for r in conn.execute(
        """SELECT slip_no, han_tra, qua_han_ngay FROM mart.cong_no_phieu
            WHERE billing_customer_code = '000000000080'"""))
    assert han["T2"] == (date(2026, 8, 6), -6)
    assert han["T1"] == (date(2026, 7, 8), 23)
