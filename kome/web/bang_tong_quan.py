"""Nhiều bảng Tổng quan có tên cho mỗi người (migration 056).

Mỗi bảng là một bố cục (kome/web/bo_cuc.py) + một tên, RIÊNG của một người
(chủ DN chốt 2026-09-28 — không chia sẻ). Mọi quy tắc sống ở đây; app.py chỉ
đọc thân yêu cầu và đổi LoiBang thành JSON. Không hàm nào tự commit.

- Mọi câu ghi có `AND nguoi_dung_id = %s`: bảng người khác -> 404, y như không
  tồn tại (không lộ là có).
- Người chưa có dòng nào có một bảng ẢO (`id=None`). Lưu bố cục lần đầu trên
  bảng ảo tạo dòng thật "Bảng của tôi" (ON CONFLICT theo tên: hai tab cùng lưu
  lần đầu vẫn ra MỘT dòng).
- `bang_gan_nhat` chỉ ghi khi người dùng CHỦ ĐỘNG chuyển tab / tạo bảng — mở
  trang hay mở link `?bang=` không ghi gì.
Đặc tả: docs/superpowers/specs/2026-09-28-nhieu-bang-tong-quan-design.md
"""
from __future__ import annotations

import json
from dataclasses import dataclass

import psycopg

from kome.web import bo_cuc as BC

TOI_DA = 20      # chặn một vòng lặp lỗi phía trình duyệt sinh hàng nghìn dòng
DAI_TEN = 40     # = CHECK của 056
TEN_MAC_DINH = "Bảng của tôi"


class LoiBang(Exception):
    """Vi phạm quy tắc — `ma` là mã HTTP trả cho trình duyệt (404/409/422)."""

    def __init__(self, ma: int, loi: str):
        super().__init__(loi)
        self.ma, self.loi = ma, loi


def _khong_thay() -> LoiBang:
    return LoiBang(404, "Không tìm thấy bảng này.")


@dataclass(frozen=True)
class Bang:
    id: int | None
    ten: str
    bo_cuc: tuple

    def dict(self) -> dict:
        return {"id": self.id, "ten": self.ten, "bo_cuc": [o.dict() for o in self.bo_cuc]}


def ao() -> Bang:
    return Bang(None, TEN_MAC_DINH, tuple(BC.mac_dinh()))


def _la_so(v) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def chuan_ten(ten) -> str:
    t = ten.strip() if isinstance(ten, str) else ""
    if not 1 <= len(t) <= DAI_TEN:
        raise LoiBang(422, f"Tên bảng phải có 1–{DAI_TEN} ký tự.")
    return t


def tu_tho(tho) -> list[Bang]:
    """JSON thô (json_agg của cổng đăng nhập) -> danh sách bảng. Không tin gì:
    phần tử thiếu id / tên thì bỏ, bố cục qua chuan_hoa. Không bao giờ ném lỗi."""
    if isinstance(tho, (str, bytes)):
        try:
            tho = json.loads(tho)
        except ValueError:
            tho = None
    ds = []
    for x in tho if isinstance(tho, list) else []:
        if isinstance(x, dict) and _la_so(x.get("id")) and isinstance(x.get("ten"), str):
            ds.append(Bang(x["id"], x["ten"], tuple(BC.chuan_hoa(x.get("bo_cuc")))))
    return ds


def chon(ds: list[Bang], tham_so: str | None, gan_nhat: int | None) -> Bang:
    """?bang= của mình > bảng gần nhất > bảng đầu > bảng ảo. Thuần Python."""
    theo_id = {b.id: b for b in ds}
    if isinstance(tham_so, str) and tham_so.isdigit() and int(tham_so) in theo_id:
        return theo_id[int(tham_so)]
    if gan_nhat in theo_id:
        return theo_id[gan_nhat]
    return ds[0] if ds else ao()


def _doc(conn, nguoi_id: int, bang_id) -> Bang:
    if not _la_so(bang_id):
        raise _khong_thay()
    r = conn.execute("SELECT id, ten, bo_cuc FROM app.bang_tong_quan WHERE id = %s AND nguoi_dung_id = %s",
                     (bang_id, nguoi_id)).fetchone()
    if r is None:
        raise _khong_thay()
    return Bang(r[0], r[1], tuple(BC.chuan_hoa(r[2])))


def _json(bo_cuc) -> str | None:
    return None if bo_cuc is None else json.dumps([o.dict() for o in bo_cuc])


def _xuat_phat(conn, nguoi_id: int, tu) -> list | None:
    """Bố cục khởi đầu của bảng mới; None = mặc định."""
    if tu == "mac_dinh":
        return None
    if isinstance(tu, str) and tu.startswith("vai:"):
        vai = {a: set(c) for a, _, c in BC.VAI_TRO}.get(tu[4:])
        if vai is None:
            raise LoiBang(422, "Không có vai trò này.")
        # ĐÚNG phép "Xem theo vai trò" cũ (apVai): bố cục mặc định, ẩn khối ngoài vai.
        return [BC.O(o.id, o.rong, o.cao, o.id not in vai) for o in BC.mac_dinh()]
    if isinstance(tu, str) and tu.startswith("chep:") and tu[5:].isdigit():
        return list(_doc(conn, nguoi_id, int(tu[5:])).bo_cuc)
    raise LoiBang(422, "Không rõ bảng mới bắt đầu từ đâu.")


def _mo(conn, nguoi_id: int, bang_id: int) -> None:
    conn.execute("UPDATE app.nguoi_dung SET bang_gan_nhat = %s WHERE id = %s", (bang_id, nguoi_id))


def _trung_ten() -> LoiBang:
    return LoiBang(409, "Đã có bảng tên này.")


def tao(conn, nguoi_id: int, ten, tu) -> Bang:
    ten = chuan_ten(ten)
    bo_cuc = _xuat_phat(conn, nguoi_id, tu)
    so = conn.execute("SELECT count(*) FROM app.bang_tong_quan WHERE nguoi_dung_id = %s",
                      (nguoi_id,)).fetchone()[0]
    if so >= TOI_DA:
        raise LoiBang(409, f"Mỗi người tối đa {TOI_DA} bảng — xoá bớt một bảng trước.")
    try:
        with conn.transaction():          # savepoint: trùng tên không làm hỏng giao dịch ngoài
            bid = conn.execute(
                """INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu)
                   SELECT %s, %s, %s, coalesce(max(thu_tu) + 1, 0)
                   FROM app.bang_tong_quan WHERE nguoi_dung_id = %s
                   RETURNING id""", (nguoi_id, ten, _json(bo_cuc), nguoi_id)).fetchone()[0]
    except psycopg.errors.UniqueViolation:
        raise _trung_ten() from None
    _mo(conn, nguoi_id, bid)
    return _doc(conn, nguoi_id, bid)


def luu_bo_cuc(conn, nguoi_id: int, bang_id: int | None, bo_cuc) -> Bang:
    """Ghi bố cục (đã chuẩn hoá; None = về mặc định). `bang_id` None = bảng ảo."""
    if bang_id is None:
        bid = conn.execute(
            """INSERT INTO app.bang_tong_quan (nguoi_dung_id, ten, bo_cuc, thu_tu)
               SELECT %s, %s, %s, coalesce(max(thu_tu) + 1, 0)
               FROM app.bang_tong_quan WHERE nguoi_dung_id = %s
               ON CONFLICT (nguoi_dung_id, lower(btrim(ten)))
               DO UPDATE SET bo_cuc = EXCLUDED.bo_cuc, sua_luc = now()
               RETURNING id""", (nguoi_id, TEN_MAC_DINH, _json(bo_cuc), nguoi_id)).fetchone()[0]
        _mo(conn, nguoi_id, bid)
        return _doc(conn, nguoi_id, bid)
    if not _la_so(bang_id):
        raise _khong_thay()
    n = conn.execute("""UPDATE app.bang_tong_quan SET bo_cuc = %s, sua_luc = now()
                        WHERE id = %s AND nguoi_dung_id = %s""",
                     (_json(bo_cuc), bang_id, nguoi_id)).rowcount
    if n == 0:
        raise _khong_thay()
    return _doc(conn, nguoi_id, bang_id)


def doi_ten(conn, nguoi_id: int, bang_id: int, ten) -> Bang:
    ten = chuan_ten(ten)
    _doc(conn, nguoi_id, bang_id)
    try:
        with conn.transaction():
            conn.execute("""UPDATE app.bang_tong_quan SET ten = %s, sua_luc = now()
                            WHERE id = %s AND nguoi_dung_id = %s""", (ten, bang_id, nguoi_id))
    except psycopg.errors.UniqueViolation:
        raise _trung_ten() from None
    return _doc(conn, nguoi_id, bang_id)


def xoa(conn, nguoi_id: int, bang_id: int) -> int:
    """Xoá; trả id bảng hiện tiếp (bảng đầu còn lại). Không xoá được bảng cuối."""
    _doc(conn, nguoi_id, bang_id)
    con = [r[0] for r in conn.execute(
        "SELECT id FROM app.bang_tong_quan WHERE nguoi_dung_id = %s AND id <> %s ORDER BY thu_tu, id",
        (nguoi_id, bang_id)).fetchall()]
    if not con:
        raise LoiBang(409, "Không xoá được bảng cuối cùng.")
    conn.execute("DELETE FROM app.bang_tong_quan WHERE id = %s AND nguoi_dung_id = %s", (bang_id, nguoi_id))
    return con[0]


def mo(conn, nguoi_id: int, bang_id: int) -> None:
    _doc(conn, nguoi_id, bang_id)
    _mo(conn, nguoi_id, bang_id)


def sap_thu_tu(conn, nguoi_id: int, ids) -> None:
    co = {r[0] for r in conn.execute("SELECT id FROM app.bang_tong_quan WHERE nguoi_dung_id = %s",
                                     (nguoi_id,)).fetchall()}
    if (not isinstance(ids, list) or len(ids) != len(co)
            or not all(_la_so(i) for i in ids) or set(ids) != co):
        raise LoiBang(422, "Thứ tự phải gồm đúng các bảng của bạn.")
    for i, bid in enumerate(ids):
        conn.execute("UPDATE app.bang_tong_quan SET thu_tu = %s WHERE id = %s AND nguoi_dung_id = %s",
                     (i, bid, nguoi_id))
