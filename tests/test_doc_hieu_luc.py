"""Test canh (072): chỉ những file RAW mới được đọc danh mục OBC thô — mọi màn đọc mart.dim_* (giá trị hiệu lực)."""
import re
from pathlib import Path

GOC = Path(__file__).resolve().parents[1] / "kome"
DUOC_DOC_THO = {"loaders/customer.py", "pipeline.py", "nhat_ky_nap.py", "bang_du_lieu.py", "coverage.py", "reader.py",
                "bang_kho.py"}


def test_chi_file_RAW_doc_core_dim():
    lo = []
    for p in GOC.rglob("*.py"):
        ten = p.relative_to(GOC).as_posix()
        if ten in DUOC_DOC_THO:
            continue
        for i, dong in enumerate(p.read_text(encoding="utf-8").splitlines(), 1):
            if re.search(r"\bcore\.dim_(customer|product)\b", dong) and not dong.lstrip().startswith("#"):
                lo.append(f"{ten}:{i}: {dong.strip()}")
    assert lo == [], "\n".join(lo)
