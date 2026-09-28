"""Định dạng số theo CHUẨN NHẬT (chủ DN chốt 2026-09-29): phẩy nghìn, chấm thập phân,
rút gọn 万/億. `kome/dinh_dang.py` là bản chép bắt buộc của `giao_dien/src/dinh_dang.ts`."""
import re
from pathlib import Path

import pytest

from kome import dinh_dang as DD

GOC = Path(__file__).resolve().parents[1]
SRC = GOC / "giao_dien/src"


@pytest.mark.parametrize("v, ra", [(1234567, "¥1,234,567"), (-1500, "−¥1,500"), (0, "¥0"), (None, "—")])
def test_yen_phay_ngan_nghin(v, ra):
    assert DD.yen(v) == ra


@pytest.mark.parametrize("v, ra", [
    (8_500, "¥8,500"), (98_000, "¥9.8万"), (100_000, "¥10万"), (11_700_000, "¥1,170万"),
    (99_990_000, "¥9,999万"), (120_000_000, "¥1.2億"), (100_000_000, "¥1億"),
    (1_880_000_000, "¥18.8億"), (-26_258_617, "−¥2,626万"), (None, "—")])
def test_gon_theo_man_oku(v, ra):
    assert DD.gon(v) == ra


def test_giao_dien_khong_con_kieu_cham_nghin_hay_phay_thap_phan():
    """Không chỗ nào tự in số kiểu Việt / Đức nữa — mọi số đi qua dinh_dang.ts."""
    for f in SRC.rglob("*.ts*"):
        t = f.read_text(encoding="utf-8")
        assert '"de-DE"' not in t and '"vi-VN"' not in t, f
        assert not re.search(r'replace\("\.", ","\)', t), f


def test_ts_cung_nguong_voi_python():
    t = (SRC / "dinh_dang.ts").read_text(encoding="utf-8")
    assert '"ja-JP"' in t and "1e8" in t and "1e5" in t and "1e4" in t and '"億"' in t and '"万"' in t
