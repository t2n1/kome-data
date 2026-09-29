import json
from pathlib import Path
import pytest
from kome.phi_giao import tinh

CA = json.loads((Path(__file__).parent / "du_lieu" / "phi_giao_ca.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("ca", CA, ids=[c["ten"] for c in CA])
def test_phi_giao_ca_chung(ca):
    assert tinh(ca["dk"], ca["don"]) == ca["ra"]


def test_ca_du_15_khoa():
    from kome.doi_thu_giao import TRUONG_GIAO_HANG
    for c in CA:
        assert set(c["dk"]) == set(TRUONG_GIAO_HANG), c["ten"]
