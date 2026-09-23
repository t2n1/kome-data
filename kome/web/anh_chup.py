"""Ảnh chụp kết quả API theo phiên bản dữ liệu (migration 035).

Vì sao: đo thật 2026-09-23 trên CSDL thật, cả trang `/` cũ mất ~9 s ở máy chủ
— vài view của `mart` tốn 1,5–2 s MỖI lần đọc. Dữ liệu thì chỉ đổi khi nạp,
hoàn tác, sửa ngân sách, ghi tiếp xúc, hay khi có migration mới. Nên kết quả
của mỗi endpoint được lưu lại kèm PHIÊN BẢN của mọi thứ đó; lượt xem sau trả
ngay bản lưu nếu phiên bản còn khớp.

BẤT BIẾN: không bao giờ trả ảnh chụp của phiên bản cũ. Phiên bản được đọc
TRONG CÙNG câu lệnh với ảnh chụp, và một nguồn đổi là phiên bản đổi — nên số
trên màn hình không bao giờ cũ hơn dữ liệu trong kho. Thêm một nguồn dữ liệu
mới mà màn nào đó phụ thuộc (một bảng `app` mới được ghi từ web chẳng hạn) là
PHẢI thêm nó vào `_PHIEN_BAN` — quên là màn đó đứng yên sau khi người ta sửa.

Phiên bản còn gồm:
  * dấu vân tay mã nguồn `kome/` — sửa một công thức Python là ảnh chụp cũ
    hết hiệu lực, không phải chờ lô nạp kế tiếp;
  * ngày Tokyo, cho khối nào phụ thuộc đồng hồ thật (`theo_ngay=True`).

`KOME_ANH_CHUP=0` tắt hẳn (test mặc định tắt — conftest), khi đó mọi lượt gọi
tính thẳng.
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from kome.tuoi_du_lieu import hom_nay_o_nhat

_GOC = Path(__file__).resolve().parents[1]      # thư mục kome/


def _van_tay_ma() -> str:
    # CRLF -> LF: máy công ty (Windows) có thể checkout CRLF, Vercel (Linux) LF.
    # Không chuẩn hoá thì hai bên ra hai dấu vân tay, và ảnh chụp máy công ty
    # làm nóng sau 13:30 không bao giờ trúng cho người xem trên Vercel.
    h = hashlib.sha1()
    for p in sorted(_GOC.rglob("*.py"), key=lambda p: p.relative_to(_GOC).as_posix()):
        h.update(p.relative_to(_GOC).as_posix().encode())
        h.update(p.read_bytes().replace(bytes([13, 10]), bytes([10])))
    return h.hexdigest()[:12]


VAN_TAY_MA = _van_tay_ma()

# Mọi nguồn có thể làm đổi một con số trên màn hình. MỘT biểu thức, đọc cùng
# lượt hỏi với ảnh chụp (xem `lay`).
_PHIEN_BAN = """concat_ws('|',
    (SELECT max(batch_id) FROM meta.ingest_batch),
    (SELECT max(undone_at) FROM meta.ingest_batch),
    (SELECT max(id) FROM app.ngan_sach_nhat_ky),
    (SELECT max(id) FROM app.nhat_ky_tiep_xuc),
    (SELECT max(filename) FROM meta.schema_migration))"""

# Phiên bản CHỈ theo dữ liệu nạp (lô nạp, hoàn tác, migration) — cho ảnh chụp
# mà dữ liệu KHÔNG đọc bảng nào web ghi được (danh bạ khách: mart.* dựng từ
# core, không đọc app.ngan_sach hay app.nhat_ky_tiep_xuc). Dùng bản đầy đủ ở
# trên cho những ảnh chụp đó thì mỗi lần ai đó ghi một cuộc gọi, danh bạ 1.710
# khách (~6 s để dựng) lại phải tính lại — vì một thứ nó không hề đọc.
# BẤT BIẾN: chọn `chi_nap=True` NGHĨA LÀ cam đoan dữ liệu không đọc bảng `app`
# nào — sai là ảnh chụp đứng yên sau khi người ta sửa.
_PHIEN_BAN_NAP = """concat_ws('|',
    (SELECT max(batch_id) FROM meta.ingest_batch),
    (SELECT max(undone_at) FROM meta.ingest_batch),
    (SELECT max(filename) FROM meta.schema_migration))"""


# Khoá ảnh chụp danh bạ khách — api.py đọc, lam_nong làm nóng.
KHOA_DANH_BA = "khach-hang/danh-ba"


def bat() -> bool:
    return os.environ.get("KOME_ANH_CHUP", "1") != "0"


def _mac_dinh(o):
    if isinstance(o, (date, datetime)):
        return o.isoformat()
    if isinstance(o, Decimal):
        return int(o) if o == o.to_integral_value() else float(o)
    if is_dataclass(o):
        return asdict(o)
    if isinstance(o, (set, frozenset, tuple)):
        return list(o)
    raise TypeError(f"không chuyển được sang JSON: {type(o).__name__}")


def sang_json(du_lieu) -> str:
    return json.dumps(du_lieu, default=_mac_dinh, ensure_ascii=False, separators=(",", ":"))


def lay(conn, khoa: str, tinh, theo_ngay: bool = False,
        chi_nap: bool = False) -> tuple[str, str]:
    """(JSON, phiên bản) của khoá `khoa`. Trúng ảnh chụp: MỘT lượt hỏi. Trượt:
    gọi `tinh(conn)` (trả về dữ liệu chuyển được sang JSON), ghi đè ảnh chụp,
    commit. `theo_ngay`: khối phụ thuộc đồng hồ thật giờ Tokyo (hẹn gọi lại,
    tạm ẩn khách vừa liên hệ) — sang ngày mới là tính lại."""
    duoi = VAN_TAY_MA + ("|" + hom_nay_o_nhat().isoformat() if theo_ngay else "")
    if not bat():
        return sang_json(tinh(conn)), ""
    r = conn.execute(
        f"""SELECT v.pb, a.du_lieu::text
            FROM (SELECT {_PHIEN_BAN_NAP if chi_nap else _PHIEN_BAN} || '|' || %s AS pb) v
            LEFT JOIN app.anh_chup_api a ON a.khoa = %s AND a.phien_ban = v.pb""",
        (duoi, khoa)).fetchone()
    phien_ban, co_san = r[0], r[1]
    if co_san is not None:
        return co_san, phien_ban
    t = time.perf_counter()
    ra = sang_json(tinh(conn))
    ms = int((time.perf_counter() - t) * 1000)
    conn.execute(
        """INSERT INTO app.anh_chup_api (khoa, phien_ban, du_lieu, tinh_ms)
           VALUES (%s, %s, %s::jsonb, %s)
           ON CONFLICT (khoa) DO UPDATE
              SET phien_ban = EXCLUDED.phien_ban, du_lieu = EXCLUDED.du_lieu,
                  tinh_luc = now(), tinh_ms = EXCLUDED.tinh_ms""",
        (khoa, phien_ban, ra, ms))
    conn.commit()
    return ra, phien_ban


# Bản ĐÃ GIẢI MÃ của các ảnh chụp lớn (danh bạ ~940 KB) trong tiến trình này,
# theo khoá — một phần tử mỗi khoá, thay khi phiên bản đổi. Mỗi lượt lọc danh
# sách vẫn hỏi CSDL phiên bản hiện tại (không bao giờ trả bản cũ), chỉ bỏ được
# bước đọc + giải mã lại cả ảnh chụp.
_DA_GIAI_MA: dict[str, tuple[str, object]] = {}


def lay_du_lieu(conn, khoa: str, tinh, chi_nap: bool = False) -> tuple[object, str]:
    """Như `lay` nhưng trả về đối tượng Python (đã `json.loads`). Trúng ảnh
    chụp của đúng phiên bản đang nhớ thì không đọc lại thân ảnh chụp."""
    if not bat():
        return json.loads(sang_json(tinh(conn))), ""
    pb = conn.execute(
        f"SELECT {_PHIEN_BAN_NAP if chi_nap else _PHIEN_BAN} || '|' || %s",
        (VAN_TAY_MA,)).fetchone()[0]
    nho = _DA_GIAI_MA.get(khoa)
    if nho and nho[0] == pb:
        return nho[1], pb
    du_lieu, pb = lay(conn, khoa, tinh, chi_nap=chi_nap)
    obj = json.loads(du_lieu)
    _DA_GIAI_MA[khoa] = (pb, obj)
    return obj, pb


def lam_nong(open_conn) -> None:
    """Tính sẵn mọi khối Tổng quan KHÔNG phụ thuộc người xem, ngay sau nạp /
    hoàn tác — để người đầu tiên mở trang sau 13:30 không phải chờ ~10 s cho
    khối nặng nhất. Chạy trong luồng nền (app.py) và NUỐT MỌI LỖI: luồng nạp
    13:30 không bao giờ được hỏng vì bước làm nóng."""
    import threading
    from kome import khoi_tong_quan as KTQ

    def chay():
        for ma, (ham, theo_ngay, theo_sale) in KTQ.KHOI.items():
            if theo_sale:
                continue
            try:
                with open_conn() as c:
                    lay(c, f"tong-quan/{ma}", lambda cc, h=ham: h(cc, None), theo_ngay)
            except Exception as e:     # noqa: BLE001 — cố ý nuốt, xem docstring
                print(f"[anh-chup] không làm nóng được {ma}: {e!r}")
        try:
            with open_conn() as c:
                lay(c, "thong-bao", KTQ.thong_bao, theo_ngay=True)
        except Exception as e:         # noqa: BLE001
            print(f"[anh-chup] không làm nóng được thong-bao: {e!r}")
        # Danh bạ khách (giai đoạn 2) — câu nặng nhất của màn Khách hàng.
        try:
            from kome import khach_hang as KH
            with open_conn() as c:
                lay(c, KHOA_DANH_BA, KH.danh_ba, chi_nap=True)
        except Exception as e:         # noqa: BLE001
            print(f"[anh-chup] không làm nóng được danh bạ: {e!r}")

    if bat():
        threading.Thread(target=chay, name="lam-nong-anh-chup", daemon=True).start()
