"""Tên file ra — BẢN CHÉP của `filename_pattern` trong config/files.yml.

Web nhận diện loại file CHỈ theo tên (cổng 1), nên một ký tự lệch ở đây là cả
lượt chạy bị chặn. Có test canh: tests/test_obc_bot_co_ban.py chạy từng tên qua
kome.pipeline.identify, và MUC_SPEC phải bằng kome.web.app.MUC_HANG_NGAY."""
from datetime import date

MUC_SPEC = {"ban": "meisai", "ton": "zaiko", "khach": "tokuisaki"}

_TIEN_TO = {"ban": "売上明細表", "ton": "在庫一覧", "khach": "得意先全情報"}


def ten_file(muc: str, ngay: date) -> str:
    return f"{_TIEN_TO[muc]}_{ngay:%Y%m%d}.xlsx"
