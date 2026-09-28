"""_squarify (Python, cây ô /bao-cao) và squarify (TS, /mua-vu) chạy CHUNG
tests/du_lieu/squarify_ca.json — sửa một bản là sửa cả hai (cùng nếp luoi_nen_ca.json)."""
import json
from pathlib import Path

import pytest

from kome.ve_phan_tich import _squarify

CA = json.loads((Path(__file__).parent / "du_lieu" / "squarify_ca.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("ca", CA, ids=[c["ten"] for c in CA])
def test_squarify_khop_file_ca(ca):
    o = _squarify(ca["gia_tri"], *ca["khung"])
    o_list = [list(x) for x in o]
    if ca["o"]:
        assert len(o_list) == len(ca["o"])
        for o_val, expected in zip(o_list, ca["o"]):
            for oval, exp in zip(o_val, expected):
                assert oval == pytest.approx(exp)
    else:
        assert o == []
