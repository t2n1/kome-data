"""Bộ điều phối: mọi lượt chạy kết thúc ở ĐÚNG MỘT kết cục (đặc tả §6)."""
from datetime import date
from pathlib import Path

import pytest

from obc_bot import bao_cao
from obc_bot.cau_hinh import CauHinh
from obc_bot.chay import KetCuc, LoiObc, MoiTruong, chay
from obc_bot.ten_file import ten_file
from obc_bot.web import LoiWeb

NGAY = date(2026, 10, 14)


def _ch(tmp_path, muc=("ban", "ton"), dem=0, tai_khoan="obc-bot", hoi=False):
    return CauHinh(muc=muc, web_url="https://x", tai_khoan_web=tai_khoan,
                   thu_muc_ra=tmp_path / "ra", thu_muc_bao_loi=tmp_path / "loi",
                   pattern={m: 1 for m in muc}, dem_nguoc_giay=dem, ten_may="may-b", hoi_truoc=hoi)


class WebGia:
    def __init__(self, da_co=None, la_ngay_kd=True, chan=(), loi_nap=None, loi_dang_nhap=None):
        self.da_co = {"ban": False, "ton": False, "khach": False, **(da_co or {})}
        self.la_ngay_kd, self.chan = la_ngay_kd, set(chan)
        self.loi_nap, self.loi_dang_nhap = loi_nap, loi_dang_nhap
        self.da_nap: list[Path] = []
        self.dang_nhap_voi = None

    def dang_nhap(self, ten, mk):
        if self.loi_dang_nhap:
            raise LoiWeb(self.loi_dang_nhap)
        self.dang_nhap_voi = (ten, mk)

    def hom_nay(self):
        return {"ngay": NGAY.isoformat(), "la_ngay_kd": self.la_ngay_kd, "da_co": self.da_co}

    def nap(self, files):
        if self.loi_nap:
            raise LoiWeb(self.loi_nap)
        self.da_nap += files
        return [{"ten_file": p.name, "ok": p.name not in self.chan, "skipped": False,
                 "row_count": 10, "blockers": [{"cong": 3, "loi": "dưới min_rows"}]
                 if p.name in self.chan else []} for p in files]


def _mt(khoa=False, hong=None, ghi=None, tra_loi=True):
    """`hong`: {muc: số lần xuất hỏng liên tiếp trước khi được}."""
    hong = dict(hong or {})
    ghi = ghi if ghi is not None else {"xuat": [], "khoi_dong_lai": 0, "thong_bao": [], "ngu": []}

    def xuat(muc, ngay, thu_muc, pattern):
        ghi["xuat"].append(muc)
        if hong.get(muc, 0) > 0:
            hong[muc] -= 1
            raise LoiObc("chọn pattern", "không thấy ô 出力パターン")
        thu_muc.mkdir(parents=True, exist_ok=True)
        p = thu_muc / ten_file(muc, ngay)
        p.write_bytes(b"x")
        return p

    def khoi_dong_lai():
        ghi["khoi_dong_lai"] += 1

    return MoiTruong(man_hinh_khoa=lambda: khoa, xuat=xuat, khoi_dong_lai_obc=khoi_dong_lai,
                     mat_khau=lambda ten: "mk", thong_bao=lambda t, n: ghi["thong_bao"].append(t),
                     ngu=lambda s: ghi["ngu"].append(s),
                     hoi=lambda t, n: ghi.setdefault("hoi", []).append(t) or tra_loi), ghi


def test_man_hinh_khoa_dung_ngay_khong_bam_gi(tmp_path):
    mt, ghi = _mt(khoa=True)
    kc = chay(_ch(tmp_path), WebGia(), mt)
    assert kc.loai == "man_hinh_khoa" and kc.can_bao and ghi["xuat"] == []


def test_ngay_nghi_bo_qua(tmp_path):
    mt, ghi = _mt()
    kc = chay(_ch(tmp_path), WebGia(la_ngay_kd=False), mt)
    assert kc.loai == "bo_qua" and not kc.can_bao and ghi["xuat"] == []


def test_da_co_du_thi_khong_chiem_chuot(tmp_path):
    mt, ghi = _mt()
    kc = chay(_ch(tmp_path), WebGia(da_co={"ban": True, "ton": True}), mt)
    assert kc.loai == "bo_qua" and ghi["xuat"] == []


def test_chi_xuat_muc_con_thieu_va_nap_vao_thu_muc_thang(tmp_path):
    mt, ghi = _mt()
    w = WebGia(da_co={"ban": True})
    kc = chay(_ch(tmp_path), w, mt)
    assert kc.loai == "xong" and ghi["xuat"] == ["ton"]
    assert w.da_nap == [tmp_path / "ra" / "2026-10" / "在庫一覧_20261014.xlsx"]
    assert w.dang_nhap_voi == ("obc-bot", "mk")


def test_khong_tai_khoan_web_thi_khong_dang_nhap(tmp_path):
    mt, _ = _mt()
    w = WebGia()
    chay(_ch(tmp_path, tai_khoan=""), w, mt)
    assert w.dang_nhap_voi is None


def test_hong_mot_lan_thi_khoi_dong_lai_va_thu_lai(tmp_path):
    mt, ghi = _mt(hong={"ban": 1})
    kc = chay(_ch(tmp_path), WebGia(), mt)
    assert kc.loai == "xong" and ghi["khoi_dong_lai"] == 1
    assert ghi["xuat"] == ["ban", "ban", "ton"]


def test_hong_hai_lan_la_loi_obc_nhung_muc_khac_van_nap(tmp_path):
    mt, ghi = _mt(hong={"ban": 2})
    w = WebGia()
    kc = chay(_ch(tmp_path), w, mt)
    assert kc.loai == "loi_obc" and kc.can_bao
    assert "chọn pattern" in kc.chi_tiet[0] and "ban" in kc.chi_tiet[0]
    assert [p.name for p in w.da_nap] == ["在庫一覧_20261014.xlsx"]


def test_cong_chan_noi_nguyen_van(tmp_path):
    mt, _ = _mt()
    kc = chay(_ch(tmp_path), WebGia(chan={"在庫一覧_20261014.xlsx"}), mt)
    assert kc.loai == "cong_chan"
    assert any("cổng 3" in d and "dưới min_rows" in d for d in kc.chi_tiet)


def test_loi_web_khi_nap_noi_cho_de_file(tmp_path):
    mt, _ = _mt()
    kc = chay(_ch(tmp_path), WebGia(loi_nap="mạng"), mt)
    assert kc.loai == "loi_web" and any(str(tmp_path / "ra") in d for d in kc.chi_tiet)


def test_sai_mat_khau_web_la_loi_web_truoc_khi_bam(tmp_path):
    mt, ghi = _mt()
    kc = chay(_ch(tmp_path), WebGia(loi_dang_nhap="sai mật khẩu"), mt)
    assert kc.loai == "loi_web" and ghi["xuat"] == []


def test_dem_nguoc_bao_truoc_roi_moi_bam(tmp_path):
    mt, ghi = _mt()
    chay(_ch(tmp_path, muc=("khach",), dem=30), WebGia(), mt)
    assert ghi["ngu"] == [30] and ghi["thong_bao"] and ghi["xuat"] == ["khach"]


def test_bao_cao_ghi_log_va_tep_loi_chi_khi_can_bao(tmp_path):
    ch = _ch(tmp_path)
    assert bao_cao.ghi(ch, KetCuc("xong", ["ok"], []), NGAY) is None
    p = bao_cao.ghi(ch, KetCuc("cong_chan", ["cổng 3: dưới min_rows"], []), NGAY)
    assert p == tmp_path / "loi" / "2026-10-14_may-b_cong_chan.txt"
    assert "dưới min_rows" in p.read_text(encoding="utf-8")
    log = (tmp_path / "ra" / "log" / "2026-10-14.log").read_text(encoding="utf-8")
    assert "xong" in log and "cong_chan" in log


def test_tu_choi_khong_ly_do_van_la_cong_chan(tmp_path):
    mt, _ = _mt()
    w = WebGia()
    w.nap = lambda files: [{"ten_file": "x.xlsx", "ok": False, "skipped": False,
                            "row_count": 0, "blockers": []}]
    kc = chay(_ch(tmp_path, muc=("ton",)), w, mt)
    assert kc.loai == "cong_chan" and "web từ chối" in kc.chi_tiet[0]


def _mt_no(loi_lan):
    """xuat nổ RuntimeError `loi_lan[muc]` lần rồi mới được."""
    mt, ghi = _mt()
    goc = mt.xuat
    dem = dict(loi_lan)

    def xuat(muc, ngay, thu_muc, pattern):
        if dem.get(muc, 0) > 0:
            dem[muc] -= 1
            ghi["xuat"].append(muc)
            raise RuntimeError("timeout")
        return goc(muc, ngay, thu_muc, pattern)

    mt.xuat = xuat
    return mt, ghi


def test_loi_la_hai_lan_la_loi_obc_muc_khac_van_nap(tmp_path):
    mt, ghi = _mt_no({"ban": 2})
    w = WebGia()
    kc = chay(_ch(tmp_path), w, mt)
    assert kc.loai == "loi_obc" and "không lường trước" in kc.chi_tiet[0]
    assert [p.name for p in w.da_nap] == ["在庫一覧_20261014.xlsx"]


def test_loi_la_mot_lan_roi_thanh_cong(tmp_path):
    mt, ghi = _mt_no({"ban": 1})
    kc = chay(_ch(tmp_path), WebGia(), mt)
    assert kc.loai == "xong" and ghi["khoi_dong_lai"] == 1


def test_khoi_dong_lai_no_thi_dung_thu_lai(tmp_path):
    mt, ghi = _mt_no({"ban": 5})

    def nghe():
        raise OSError("không mở được OBC")

    mt.khoi_dong_lai_obc = nghe
    kc = chay(_ch(tmp_path, muc=("ban",)), WebGia(), mt)
    assert kc.loai == "loi_obc" and ghi["xuat"] == ["ban"]


def test_khoa_man_hinh_nhung_da_co_du_thi_bo_qua(tmp_path):
    mt, ghi = _mt(khoa=True)
    kc = chay(_ch(tmp_path), WebGia(da_co={"ban": True, "ton": True}), mt)
    assert kc.loai == "bo_qua" and ghi["xuat"] == []


def test_hom_nay_sai_dang_la_loi_web(tmp_path):
    for xau in ({}, {"ngay": "2026-10-14", "la_ngay_kd": True},
                {"ngay": "2026-10-14", "la_ngay_kd": "yes", "da_co": {"ban": False, "ton": False}},
                {"ngay": "2026-10-14", "la_ngay_kd": True, "da_co": {"ban": False}}):
        w = WebGia()
        w.hom_nay = lambda xau=xau: xau
        mt, ghi = _mt()
        kc = chay(_ch(tmp_path), w, mt)
        assert kc.loai == "loi_web" and "sai dạng" in kc.chi_tiet[0] and ghi["xuat"] == []


def test_ket_qua_nap_thieu_khoa_la_loi_web(tmp_path):
    w = WebGia()
    w.nap = lambda files: [{"ok": True}]
    mt, _ = _mt()
    kc = chay(_ch(tmp_path), w, mt)
    assert kc.loai == "loi_web" and "sai dạng" in kc.chi_tiet[0]


def test_man_hinh_khoa_nem_loi_thanh_ket_cuc_man_hinh_khoa(tmp_path):
    mt, ghi = _mt()

    def nem():
        raise OSError("không mở được desktop")
    mt.man_hinh_khoa = nem
    kc = chay(_ch(tmp_path), WebGia(), mt)
    assert kc.loai == "man_hinh_khoa" and "OSError" in kc.chi_tiet[0] and ghi["xuat"] == []


def test_lenh_chay_bat_loi_cuoi_van_ghi_bao_cao_va_thong_bao(tmp_path, monkeypatch):
    import obc_bot.chay as C
    from obc_bot import __main__ as M
    ghi = []
    monkeypatch.setattr(C, "chay", lambda *a: (_ for _ in ()).throw(RuntimeError("hỏng")))
    monkeypatch.setattr(bao_cao, "thong_bao_windows", lambda t, n: ghi.append((t, n)))
    assert M.lenh_chay(_ch(tmp_path)) == 1
    tep = list((tmp_path / "loi").glob("*_loi_obc.txt"))
    assert len(tep) == 1 and "Lỗi không lường trước" in tep[0].read_text(encoding="utf-8")
    assert ghi and "loi_obc" in ghi[0][0]


# ---- Hỏi trước (chủ DN 2026-10-15: "13:30 hiện thông báo hỏi có muốn lấy dữ liệu chưa, bấm có mới chạy") ----

def test_hoi_truoc_bam_khong_thi_bo_qua_khong_bam_OBC(tmp_path):
    mt, ghi = _mt(tra_loi=False)
    kc = chay(_ch(tmp_path, hoi=True), WebGia(), mt)
    assert kc.loai == "bo_qua" and ghi["xuat"] == [] and ghi["hoi"]


def test_hoi_truoc_bam_co_thi_chay_binh_thuong(tmp_path):
    mt, ghi = _mt(tra_loi=True)
    kc = chay(_ch(tmp_path, hoi=True), WebGia(), mt)
    assert kc.loai == "xong" and ghi["xuat"] == ["ban", "ton"] and len(ghi["hoi"]) == 1


def test_khong_hoi_khi_ngay_nghi_hoac_da_co_du(tmp_path):
    for web in (WebGia(la_ngay_kd=False), WebGia(da_co={"ban": True, "ton": True})):
        mt, ghi = _mt(tra_loi=True)
        assert chay(_ch(tmp_path, hoi=True), web, mt).loai == "bo_qua"
        assert "hoi" not in ghi


def test_khong_bat_hoi_truoc_thi_khong_hoi(tmp_path):
    mt, ghi = _mt(tra_loi=False)
    assert chay(_ch(tmp_path), WebGia(), mt).loai == "xong" and "hoi" not in ghi


# ---- Làm nóng ảnh chụp sau khi nạp (2026-10-15: trang mở lần đầu sau mỗi lần nạp mất 3–6 s trên Vercel) ----

class WebNong(WebGia):
    def __init__(self, loi_nong=False, **kw):
        super().__init__(**kw)
        self.da_nong, self.loi_nong = [], loi_nong

    def lam_nong(self, duong):
        if self.loi_nong:
            raise RuntimeError("web chậm")
        self.da_nong += list(duong)
        return len(duong)


def test_nap_xong_thi_lam_nong_cac_trang_chinh(tmp_path):
    from obc_bot.web import TRANG_LAM_NONG
    mt, _ = _mt()
    w = WebNong()
    kc = chay(_ch(tmp_path), w, mt)
    assert kc.loai == "xong" and w.da_nong == list(TRANG_LAM_NONG)
    assert "/api/kho-hang" in TRANG_LAM_NONG and "/api/tong-quan/kpi" in TRANG_LAM_NONG


def test_khong_nap_gi_thi_khong_lam_nong(tmp_path):
    mt, _ = _mt()
    w = WebNong(la_ngay_kd=False)
    chay(_ch(tmp_path), w, mt)
    assert w.da_nong == []


def test_lam_nong_loi_khong_doi_ket_cuc(tmp_path):
    mt, _ = _mt()
    assert chay(_ch(tmp_path), WebNong(loi_nong=True), mt).loai == "xong"


def test_cau_hinh_doc_hoi_truoc(tmp_path):
    from obc_bot import cau_hinh as CH
    p = tmp_path / "c.toml"
    p.write_text('muc = ["ban"]\nweb_url = "https://x"\nthu_muc_ra = "C:/x"\nhoi_truoc = true\n[pattern]\nban = 1\n',
                 encoding="utf-8")
    assert CH.doc(p).hoi_truoc is True
    p.write_text(p.read_text(encoding="utf-8").replace("hoi_truoc = true", 'hoi_truoc = "co"'), encoding="utf-8")
    with pytest.raises(CH.CauHinhSai, match="hoi_truoc"):
        CH.doc(p)
