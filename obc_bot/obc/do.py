"""In cây điều khiển UIA của cửa sổ 奉行クラウド đang mở — để viết Task 7 bằng
TÊN điều khiển đo thật, không đoán. Chỉ đọc: không bấm gì."""


def do_cay(tieu_de: str = ".*奉行クラウド.*", sau: int = 12) -> str:
    from pywinauto import Desktop
    goc = Desktop(backend="uia").window(title_re=tieu_de)
    goc.wait("exists", timeout=10)
    dong: list[str] = []

    def di(e, d):
        ei = e.element_info
        dong.append("  " * d + f"[{ei.control_type}] name={ei.name!r} "
                    f"auto_id={ei.automation_id!r} class={ei.class_name!r}")
        if d < sau:
            for c in e.children():
                di(c, d + 1)

    di(goc.wrapper_object(), 0)
    return "\n".join(dong)
