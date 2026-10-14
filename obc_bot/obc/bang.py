"""Kiểm bảng Excel mà OBC vừa đẩy ra — TRƯỚC khi lưu thành file nạp.

Ô pattern và ô ngày của OBC là ô tự vẽ, UIA không đọc được (docs/obc-ui/LUONG.md), nên chương
trình không nhìn được nó đã chọn gì. Hai lớp kiểm ở đây thay cho việc nhìn:
- thiếu cột khai ở config/files.yml  → pattern lệch (ai đó đổi pattern / thứ tự danh sách);
- `売上日付` có ngày khác hôm nay    → gõ ngày trượt (đo thật: một lần xuất ra trọn ngày cũ).
`COT_CAN` / `SHEET` là BẢN CHÉP của files.yml — có test canh (tests/test_obc_bot_bang.py)."""
from datetime import date, timedelta

from obc_bot.chay import LoiObc

SHEET = {"ban": "売上明細表", "ton": "在庫一覧表", "khach": "得意先データ作成"}

COT_CAN = {
    "ban": frozenset({"伝票No.", "売上日付", "得意先コード", "担当者コード", "商品コード", "荷姿区分コード",
                      "純売上数量", "単価", "税抜純売上高", "粗利益", "粗利益率"}),
    "ton": frozenset({"商品コード", "商品名", "荷姿区分コード", "荷姿区分名", "倉庫コード", "倉庫名", "日本語", "単位",
                      "賞味期限", "売上出荷数量", "在庫残数", "在庫単価", "在庫金額"}),
    "khach": frozenset({"得意先コード", "得意先名", "郵便番号", "都道府県", "市区町村", "番地", "ビル等", "電話番号",
                        "ランクコード", "ランク名", "売上主担当者コード", "売上主担当者名", "請求締日コード", "請求締日名",
                        "支店名", "振込専用口座番号１"}),
}

# Cột ngày phải TRÙNG ngày cần lấy (mọi cột cùng tên — 売上明細表 có hai cột 売上日付).
COT_NGAY = {"ban": "売上日付"}

# Dòng GIỮ theo cột 単位 — chủ DN 2026-10-15: "cột 単位 chỉ lấy KG và ケース, còn lại xoá hết thì mới nhập lên web
# app được" (việc người ta vẫn làm tay mỗi ngày). Đo thật: các đơn vị khác (袋 / 本 / 個 / 缶 / trống) là dòng LẺ trùng
# khoá (商品コード, 倉庫コード) với dòng thùng → cổng 3 chặn cả file; file xuất tay 16/9, 24/9 chỉ có KG / ケース.
DON_VI_GIU = {"ton": frozenset({"KG", "ケース"})}

_GOC_EXCEL = date(1899, 12, 30)


def dong_bo(muc: str, gia_tri) -> list[int]:
    """Chỉ số (0 = dòng ngay dưới header) các dòng dữ liệu phải XOÁ trước khi lưu file nạp."""
    giu = DON_VI_GIU.get(muc)
    if not giu or not gia_tri:
        return []
    i = [str(h).strip() if h is not None else "" for h in gia_tri[0]].index("単位")
    return [k for k, r in enumerate(gia_tri[1:]) if (str(r[i]).strip() if r[i] is not None else "") not in giu]


def so_ngay_excel(ngay: date) -> int:
    return (ngay - _GOC_EXCEL).days


def _ngay_doc(v) -> str:
    try:
        return (_GOC_EXCEL + timedelta(days=int(v))).isoformat()
    except (TypeError, ValueError):
        return repr(v)


def kiem_bang(muc: str, gia_tri, ngay: date) -> int:
    """`gia_tri` = `UsedRange.Value2` (dòng 1 là header). Trả số dòng dữ liệu; sai → LoiObc."""
    if not gia_tri:
        raise LoiObc("kiểm cột (pattern)", "bảng Excel OBC đẩy ra rỗng")
    hdr = [str(h).strip() if h is not None else "" for h in gia_tri[0]]
    thieu = sorted(COT_CAN[muc] - set(hdr))
    if thieu:
        raise LoiObc("kiểm cột (pattern)",
                     f"thiếu cột {thieu} — pattern đang chọn không phải pattern cấu hình (danh sách đổi thứ tự?)")
    dong = list(gia_tri[1:])
    ten = COT_NGAY.get(muc)
    if ten:
        can = so_ngay_excel(ngay)
        cot = [i for i, h in enumerate(hdr) if h == ten]
        lech = sorted({_ngay_doc(r[i]) for r in dong for i in cot if r[i] != can})
        if lech:
            raise LoiObc("kiểm ngày trong file",
                         f"cần {ngay.isoformat()} mà file có {lech[:5]} — ô ngày OBC chưa nhận ngày mới")
    return len(dong)
