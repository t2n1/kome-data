"""Log ngày + tệp báo lỗi vào thư mục OneDrive dùng chung + thông báo Windows."""
import shutil
import subprocess
from datetime import date, datetime
from pathlib import Path

from obc_bot.cau_hinh import CauHinh


def ghi(ch: CauHinh, kc, ngay: date) -> Path | None:
    log = ch.thu_muc_ra / "log" / f"{ngay:%Y-%m-%d}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%H:%M:%S} {kc.loai}\n")
        for d in kc.chi_tiet:
            f.write(f"    {d}\n")
    if not kc.can_bao or ch.thu_muc_bao_loi is None:
        return None
    ch.thu_muc_bao_loi.mkdir(parents=True, exist_ok=True)
    tep = ch.thu_muc_bao_loi / f"{ngay:%Y-%m-%d}_{ch.ten_may}_{kc.loai}.txt"
    tep.write_text(f"Máy: {ch.ten_may}\nKết cục: {kc.loai}\n\n" + "\n".join(kc.chi_tiet)
                   + "\n\nNạp tay: kéo thả file vào /kho-du-lieu, hoặc "
                     "python -m obc_bot nap --cau-hinh <máy>.toml <file>\n", encoding="utf-8")
    for a in kc.anh:
        if a.exists():
            shutil.copy2(a, ch.thu_muc_bao_loi / f"{tep.stem}_{a.name}")
    return tep


# AUMID đã đăng ký của PowerShell — id lạ thì Windows 10/11 lặng lẽ bỏ thông báo.
_AUMID = r"{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe"


def thong_bao_windows(tieu_de: str, noi_dung: str) -> None:
    """Thông báo góc màn hình — cố gắng hết sức, không bao giờ làm hỏng lượt chạy."""
    ps = ("[Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, "
          "ContentType=WindowsRuntime] > $null;"
          "$x = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent(1);"
          "$t = $x.GetElementsByTagName('text');"
          f"$t.Item(0).AppendChild($x.CreateTextNode({_ps(tieu_de)})) > $null;"
          f"$t.Item(1).AppendChild($x.CreateTextNode({_ps(noi_dung)})) > $null;"
          "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier"
          f"({_ps(_AUMID)})"
          ".Show([Windows.UI.Notifications.ToastNotification]::new($x))")
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=15,
                       capture_output=True)
    except Exception:
        pass


def _ps(s: str) -> str:
    return "'" + s.replace("'", "''") + "'"
