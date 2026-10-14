"""Bấm 商奉行クラウド — mỗi bước theo đúng luồng đã đo ở docs/obc-ui/LUONG.md.

Chỉ bấm nút ĐIỀU HƯỚNG và XUẤT (tên đã đo); không bao giờ bấm 新規 / 複写 / 削除 / 登録 hay mũi tên
đổi thứ tự pattern — chương trình chỉ đọc OBC (luật số một). Nút có tên chọn theo tên; ô tự vẽ
(pattern, ngày) dùng bàn phím."""
import time
from dataclasses import dataclass
from datetime import date

from obc_bot.chay import LoiObc

CHINH = "奉行クラウド"
CHO_GIAY = 30


@dataclass(frozen=True)
class Man:
    ung_dung: int        # nút ứng dụng thứ mấy ở cột trái (0 = 商奉行, 1 = ứng dụng có 在庫管理)
    nut: str             # nút trên thanh công cụ
    cua_so: str          # tiêu đề cửa sổ báo cáo
    co_ngay: bool = True


MAN = {
    "ban": Man(0, "売上明細表", "売上明細表"),
    "ton": Man(1, "在庫一覧表", "在庫一覧表"),
}


def _desk():
    from pywinauto import Desktop
    return Desktop(backend="uia")


def _cho(dieu_kien, giay: int, buoc: str, loi: str):
    for _ in range(giay * 2):
        kq = dieu_kien()
        if kq:
            return kq
        time.sleep(0.5)
    raise LoiObc(buoc, loi)


def _nut(cua_so, ten: str):
    ds = [b for b in cua_so.descendants(control_type="Button") if b.window_text() == ten]
    if not ds:
        raise LoiObc(f"bấm {ten}", f"không thấy nút {ten!r} trong {cua_so.window_text()!r}")
    return ds[0]


def _bam(nut) -> None:
    """Bấm nút qua UIA (InvokePattern) — KHÔNG theo toạ độ: OBC hay mở hộp thoại ở màn hình thứ hai, nơi
    click_input bấm trượt (đo thật 2026-10-15, toạ độ x > 3000). Nút không hỗ trợ invoke mới dùng chuột."""
    try:
        nut.invoke()
    except Exception:
        nut.click_input()


def _con(top, chua: str):
    try:
        return next((w for w in top.children(control_type="Window") if chua in w.window_text()), None)
    except Exception:
        return None


def cua_so_chinh():
    w = _desk().window(title=CHINH, control_type="Window")
    if not w.exists(timeout=5):
        raise LoiObc("tìm 奉行クラウド", "chưa mở phần mềm 奉行クラウド (hoặc chưa đăng nhập)")
    return w


def dong_bao_cao(tieu_de: str) -> None:
    """Đưa một báo cáo đang mở dở về trạng thái đóng: キャンセル mọi hộp thoại con (キャンセル ở
    パターン選択 đóng luôn báo cáo — đã đo), rồi 閉じる."""
    top = _desk().window(title=tieu_de, control_type="Window")
    for _ in range(4):
        if not top.exists(timeout=1):
            return
        con = top.children(control_type="Window")
        if not con:
            break
        try:
            _bam(_nut(con[0], "キャンセル"))
        except LoiObc:
            break
        time.sleep(1.5)
    if top.exists(timeout=1):
        _bam(_nut(top, "閉じる"))
        time.sleep(2)


def chon_ung_dung(chinh, i: int, nut: str) -> None:
    pane = next((p for p in chinh.descendants(control_type="Pane")
                 if any(c.element_info.automation_id == "LineUp" for c in p.children())), None)
    if pane is None:
        raise LoiObc("chọn ứng dụng", "không thấy cột ứng dụng bên trái")
    nut_ud = [c for c in pane.children() if c.element_info.control_type == "Button"
              and c.element_info.class_name == "Button"]
    if len(nut_ud) <= i:
        raise LoiObc("chọn ứng dụng", f"chỉ có {len(nut_ud)} ứng dụng, cần ứng dụng thứ {i + 1}")
    nut_ud[i].click_input()
    _cho(lambda: [b for b in chinh.descendants(control_type="Button") if b.window_text() == nut],
         CHO_GIAY, "chọn ứng dụng", f"ứng dụng thứ {i + 1} không có nút {nut!r}")


def mo_bao_cao(man: Man) -> object:
    chinh = cua_so_chinh()
    chinh.set_focus()
    dong_bao_cao(man.cua_so)
    chon_ung_dung(chinh, man.ung_dung, man.nut)
    _bam(_nut(chinh, man.nut))
    top = _desk().window(title=man.cua_so, control_type="Window")
    _cho(lambda: top.exists(timeout=0) and top.children(control_type="Window"),
         CHO_GIAY, f"mở {man.nut}", f"cửa sổ {man.cua_so!r} không mở")
    return top


def chon_pattern(top, vi_tri: int) -> None:
    """Danh sách pattern không đọc được qua UIA: bấm vào danh sách lấy focus → Home → Down×(vị_trí−1)
    → OK (đã đo). Màn mở thẳng 条件設定 (không qua hộp thoại) thì giữ pattern OBC nhớ — header kiểm sau."""
    from pywinauto import mouse
    from pywinauto.keyboard import send_keys
    hop = _con(top, "パターン選択")
    if hop is None:
        return
    r = hop.rectangle()
    mouse.click(coords=(r.left + 150, r.top + 88))      # dòng đầu đang thấy (vị trí đo trên hộp thoại 550×361)
    time.sleep(0.5)
    send_keys("{HOME}" + ("{DOWN %d}" % (vi_tri - 1) if vi_tri > 1 else ""))
    time.sleep(0.5)
    _bam(_nut(hop, "OK"))
    _cho(lambda: _con(top, "条件設定"), CHO_GIAY, "chọn pattern", "bấm OK mà không tới màn 条件設定")


def go_ngay(top, ngay: date) -> None:
    from pywinauto.keyboard import send_keys
    dk = _cho(lambda: _con(top, "条件設定"), CHO_GIAY, "gõ ngày", "không thấy màn 条件設定")
    o = [e for e in dk.descendants(control_type="Edit") if e.element_info.class_name == "TextBox"]
    if not o:
        raise LoiObc("gõ ngày", "không thấy ô năm của 集計期間 / 売上日付")
    o[0].set_focus()
    mot = f"{ngay:%Y}{{TAB}}{ngay.month}{{TAB}}{ngay.day}"
    send_keys(f"{mot}{{TAB}}{mot}{{TAB}}")
    time.sleep(1)


def xuat_sang_excel(top) -> None:
    """データ作成(E)... → 出力開始(E). Hộp thoại xuất giữ lựa chọn lần trước (Excel, 基本条件だけ)."""
    dk = _con(top, "条件設定")
    if dk is None:
        raise LoiObc("データ作成", "không thấy màn 条件設定")
    _bam(_nut(dk, "データ作成(E)..."))
    hop = _cho(lambda: _con(top, "データ作成条件設定"), CHO_GIAY, "データ作成", "không mở hộp thoại データ作成条件設定")
    _bam(_nut(hop, "出力開始(E)"))
