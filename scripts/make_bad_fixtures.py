#!/usr/bin/env python
"""Generate test fixtures with intentional data issues for testing."""

from pathlib import Path
import shutil
from openpyxl import load_workbook

def make_zaiko_ma_rong():
    """Create zaiko_ma_rong.xlsx by blanking some warehouse_code fields."""
    source = Path("tests/fixtures/zaiko_ok.xlsx")
    target = Path("tests/fixtures/zaiko_ma_rong.xlsx")

    # Copy source to target
    shutil.copy(source, target)

    # Load and modify
    wb = load_workbook(target)
    ws = wb.active

    # Blank out warehouse_code (column E, tên cột 倉庫コード) for rows 2, 3, 5
    # Header is at row 1, so data starts at row 2
    column_idx = None
    for col_idx, cell in enumerate(ws[1], 1):
        if cell.value and "倉庫コード" in str(cell.value):
            column_idx = col_idx
            break

    if column_idx:
        # Blank out a few rows
        for row_idx in [2, 3, 5]:
            ws.cell(row=row_idx, column=column_idx).value = None

    wb.save(target)
    print(f"Created {target} with empty warehouse codes at rows 2, 3, 5")

if __name__ == "__main__":
    make_zaiko_ma_rong()
