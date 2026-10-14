"""obc_bot: tên file ra và cấu hình — không cần OBC, không cần mạng."""
from datetime import date
from pathlib import Path

import pytest

from obc_bot import cau_hinh as CH
from obc_bot.ten_file import MUC_SPEC, ten_file


@pytest.mark.parametrize("muc", sorted(MUC_SPEC))
def test_ten_file_duoc_pipeline_nhan_dung_spec_va_ngay(muc):
    """Bản chép của files.yml: tên obc_bot sinh ra phải qua cổng 1 đúng loại."""
    from kome.pipeline import identify
    spec, ngay = identify(Path(ten_file(muc, date(2026, 10, 14))))
    assert spec is not None and spec.name == MUC_SPEC[muc]
    assert ngay == date(2026, 10, 14)


def test_muc_spec_trung_ban_cua_web():
    from kome.web.app import MUC_HANG_NGAY
    assert MUC_SPEC == MUC_HANG_NGAY


def _viet(tmp_path, noi_dung: str) -> Path:
    p = tmp_path / "c.toml"
    p.write_text(noi_dung, encoding="utf-8")
    return p


HOP_LE = """
muc = ["ban", "ton"]
web_url = "https://kome.example.vercel.app/"
tai_khoan_web = "obc-bot"
thu_muc_ra = "C:/KOME/obc_xuat"
thu_muc_bao_loi = "C:/OneDrive/KOME自動取込"
ten_may = "may-b"
[pattern]
ban = 3
ton = 5
"""


def test_doc_cau_hinh_hop_le(tmp_path):
    ch = CH.doc(_viet(tmp_path, HOP_LE))
    assert ch.muc == ("ban", "ton") and ch.pattern == {"ban": 3, "ton": 5}
    assert ch.web_url == "https://kome.example.vercel.app"      # bỏ "/" cuối
    assert ch.thu_muc_ra == Path("C:/KOME/obc_xuat") and ch.dem_nguoc_giay == 0
    assert ch.ten_may == "may-b"


@pytest.mark.parametrize("sua, cau", [
    (('muc = ["ban", "ton"]', 'muc = ["ban", "la"]'), "mục lạ"),
    (('muc = ["ban", "ton"]', 'muc = []'), "ít nhất một mục"),
    (("ton = 5", ""), "pattern"),
    (("ton = 5", "ton = 0"), "pattern"),
    (('https://kome.example.vercel.app/', 'http://kome.example.com'), "https"),
])
def test_cau_hinh_sai_noi_ro_cho_sai(tmp_path, sua, cau):
    with pytest.raises(CH.CauHinhSai, match=cau):
        CH.doc(_viet(tmp_path, HOP_LE.replace(*sua)))


def test_http_chi_cho_may_noi_bo(tmp_path):
    ch = CH.doc(_viet(tmp_path, HOP_LE.replace("https://kome.example.vercel.app/",
                                               "http://127.0.0.1:8000")))
    assert ch.web_url == "http://127.0.0.1:8000"
