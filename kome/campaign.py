"""Campaign tuần (`/campaign`, migration 074) — lưu và đọc bản kế hoạch + soát do máy công ty gửi lên.

Web KHÔNG tính gì ở đây: nhóm, lý do, phán định là của script soát (raw_archive/campaign_sheet/phan_tich/), vì nguồn
của nó (Google Sheet, Cybozu) chỉ đọc được từ máy công ty. Mô-đun này chỉ kiểm HÌNH DẠNG, ghi một dòng
`app.campaign_soat`, đọc dòng mới nhất và rút mục cho chuông. Đặc tả: docs/superpowers/specs/2026-10-23-campaign-tuan-design.md.
"""
from __future__ import annotations

import json
from datetime import date, timedelta

PHIEN_BAN = 1
CO_TOI_DA = 2_000_000           # byte JSON — dưới trần 4,5 MB mỗi yêu cầu của Vercel, dư cho 5 tuần × ~160 mã
GIU_NGAY = 30
NHOM = ("uu_tien", "day_han", "thuong", "can_nhip", "loai", "nghi")
PD = ("THIẾU HÀNG", "PHỤ THUỘC LÔ CHƯA CHỐT", "?")
TUAN_TOI = 8                    # chuông: tuần đang chạy + tuần bắt đầu trong chừng này ngày
CHUONG_TOI_DA = 6


class LoiDuLieu(ValueError):
    pass


def _ngay(x, ten: str) -> date:
    try:
        return date.fromisoformat(x)
    except (TypeError, ValueError):
        raise LoiDuLieu(f"`{ten}` phải là ngày YYYY-MM-DD: {x!r}") from None


def _ds(d: dict, k: str, ten: str, kieu=dict) -> list:
    v = d.get(k)
    if not isinstance(v, list):
        raise LoiDuLieu(f"`{(ten + '.') if ten else ''}{k}` phải là danh sách.")
    if not all(isinstance(x, kieu) for x in v):
        raise LoiDuLieu(f"Mỗi phần tử của `{(ten + '.') if ten else ''}{k}` phải là "
                        f"{'đối tượng' if kieu is dict else 'chuỗi'}.")
    return v


def _chu(d: dict, k: str, ten: str, rong: bool = True) -> str:
    v = d.get(k, "")
    if not isinstance(v, str) or (not rong and not v):
        raise LoiDuLieu(f"`{(ten + '.') if ten else ''}{k}` phải là chuỗi{'' if rong else ' khác rỗng'}.")
    return v


SO_SO = ("ton", "ngay", "bien", "lai", "tuan_do", "mua")     # `so` của một mã: ô số của bảng (cùng nội dung `ly`)
SO_CHU = ("ngan", "canh")
SO_CO = ("uoc", "ngung")


def _so_that(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v == v and abs(v) != float("inf")


def _kiem_so(s, ten: str) -> None:
    """`so` (tuỳ chọn, thêm 2026-10-23 — bản không có thì màn rơi về câu `ly`): mọi khoá đều tuỳ chọn, khoá lạ bỏ qua."""
    if not isinstance(s, dict):
        raise LoiDuLieu(f"`{ten}` phải là đối tượng.")
    for k in SO_SO:
        if s.get(k) is not None and not _so_that(s[k]):
            raise LoiDuLieu(f"`{ten}.{k}` phải là số.")
    for k in SO_CHU:
        if not isinstance(s.get(k, ""), str):
            raise LoiDuLieu(f"`{ten}.{k}` phải là chuỗi.")
    for k in SO_CO:
        if not isinstance(s.get(k, False), bool):
            raise LoiDuLieu(f"`{ten}.{k}` phải là true / false.")
    for k in ("lo", "han"):
        x = s.get(k)
        if x is None:
            continue
        if not isinstance(x, dict) or not isinstance(x.get("ngay"), str) or not _so_that(x.get("sl")) \
                or not isinstance(x.get("tt", ""), str):
            raise LoiDuLieu(f"`{ten}.{k}` phải là {{ngay: chuỗi, sl: số, tt?: chuỗi}}.")


def kiem(d) -> None:
    """Kiểm HÌNH DẠNG bản gửi lên (đủ để màn vẽ không vỡ) — không kiểm nghiệp vụ. Sai → LoiDuLieu (400)."""
    if not isinstance(d, dict):
        raise LoiDuLieu("Thân yêu cầu phải là một đối tượng JSON.")
    if d.get("phien_ban") != PHIEN_BAN:
        raise LoiDuLieu(f"`phien_ban` phải là {PHIEN_BAN} (script soát và web lệch phiên bản).")
    _chu(d, "lap_luc", "", rong=False)
    _chu(d, "nguon", "")
    _ds(d, "thu_tu_gia", "", kieu=str)
    for i, t in enumerate(_ds(d, "ke_hoach", "")):
        ten = f"ke_hoach[{i}]"
        if _ngay(t.get("den"), ten + ".den") < _ngay(t.get("tu"), ten + ".tu"):
            raise LoiDuLieu(f"`{ten}`: ngày cuối trước ngày đầu.")
        for k in ("tab", "ky"):
            _chu(t, k, ten, rong=False)
        if not isinstance(t.get("tuan_so"), int):
            raise LoiDuLieu(f"`{ten}.tuan_so` phải là số nguyên.")
        if t.get("tren_sheet") is not None:          # tuần đã có trên sheet: mã đang có (tuỳ chọn)
            _ds(t, "tren_sheet", ten, kieu=str)
        for j, m in enumerate(_ds(t, "ma", ten)):
            tm = f"{ten}.ma[{j}]"
            _chu(m, "ma", tm, rong=False)
            _chu(m, "ten", tm)
            _chu(m, "ly", tm)
            if m.get("nhom") not in NHOM:
                raise LoiDuLieu(f"`{tm}.nhom` phải là một trong {', '.join(NHOM)}.")
            if not isinstance(m.get("chon"), bool) or not isinstance(m.get("tren_sheet", False), bool):
                raise LoiDuLieu(f"`{tm}.chon` / `{tm}.tren_sheet` phải là true / false.")
            if m.get("so") is not None:
                _kiem_so(m["so"], tm + ".so")
    s = d.get("soat")
    if not isinstance(s, dict):
        raise LoiDuLieu("`soat` phải là đối tượng.")
    for k in ("lich_doi", "lo_qua_han", "lo_lech", "khong_cybozu", "goi_y"):
        _ds(s, k, "soat")
    for i, t in enumerate(_ds(s, "tuan", "soat")):
        ten = f"soat.tuan[{i}]"
        _ngay(t.get("tu"), ten + ".tu")
        _ngay(t.get("den"), ten + ".den")
        for j, x in enumerate(_ds(t, "dong", ten)):
            _chu(x, "ma", f"{ten}.dong[{j}]", rong=False)
            if x.get("pd") not in PD:
                raise LoiDuLieu(f"`{ten}.dong[{j}].pd` phải là một trong {', '.join(PD)}.")


def nop(conn, d: dict, nguoi_id: int | None) -> int:
    """Kiểm + ghi một dòng; xoá dòng cũ hơn GIU_NGAY ngày (không bao giờ dòng mới nhất — chính dòng vừa ghi).
    Người gọi commit. Trả id."""
    kiem(d)
    van = json.dumps(d, ensure_ascii=False, separators=(",", ":"))
    if len(van.encode("utf-8")) > CO_TOI_DA:
        raise LoiDuLieu(f"Bản gửi lớn quá ({len(van.encode('utf-8')):,} byte > {CO_TOI_DA:,}).")
    id_ = conn.execute("INSERT INTO app.campaign_soat (nop_boi, du_lieu) VALUES (%s, %s::jsonb) RETURNING id",
                       (nguoi_id, van)).fetchone()[0]
    conn.execute("DELETE FROM app.campaign_soat WHERE nop_luc < now() - make_interval(days => %s) AND id < %s",
                 (GIU_NGAY, id_))
    return id_


def moi_nhat(conn) -> dict:
    """Bản mới nhất: {id, nop_luc, du_lieu} — chưa có thì du_lieu None. 1 lượt hỏi."""
    r = conn.execute("""SELECT id, nop_luc, du_lieu::text FROM app.campaign_soat
                        ORDER BY id DESC LIMIT 1""").fetchone()
    if r is None:
        return {"id": None, "nop_luc": None, "du_lieu": None}
    return {"id": r[0], "nop_luc": r[1].isoformat(), "du_lieu": json.loads(r[2])}


def thong_bao(ban: dict, hom_nay: date) -> list[dict]:
    """Mục chuông từ bản mới nhất (0 lượt hỏi — `ban` = `moi_nhat`): mã cần xem của tuần đang chạy và tuần bắt đầu
    trong TUAN_TOI ngày (THIẾU HÀNG trước), tối đa CHUONG_TOI_DA; một mục khi lịch hàng về đổi. Mã thông báo ổn định
    theo (tuần, mã, phán định) — người đã đọc không thấy lại tới khi phán định đổi."""
    d = ban.get("du_lieu")
    if not d:
        return []
    s = d.get("soat") or {}
    gan = []
    for t in s.get("tuan") or []:
        tu, den = date.fromisoformat(t["tu"]), date.fromisoformat(t["den"])
        if den < hom_nay or tu > hom_nay + timedelta(days=TUAN_TOI):
            continue
        for x in t.get("dong") or []:
            gan.append((x["pd"] != "THIẾU HÀNG", tu, x["ma"], x, t))
    gan.sort(key=lambda g: g[:3])
    tb = []
    for _, tu, ma, x, t in gan[:CHUONG_TOI_DA]:
        nhan = "đang chạy" if tu <= hom_nay else f"từ {tu:%m/%d}"
        tb.append({"ma": f"campaign-{t['tu']}-{ma}-{x['pd']}", "muc": "gap" if x["pd"] == "THIẾU HÀNG" else "canh",
                   "loai": "CAMPAIGN", "tieu_de": f"{ma} — {x['pd'].lower()} (tuần {nhan})",
                   "noi_dung": (x.get("ly") or "")[:140], "lien_ket": "/campaign?tab=soat"})
    doi = s.get("lich_doi") or []
    if doi:
        tb.append({"ma": f"campaign-lich-{ban['id']}", "muc": "canh", "loai": "CAMPAIGN",
                   "tieu_de": f"{len(doi)} lịch hàng về thay đổi", "noi_dung": "Cybozu 搬入スケジュール đổi từ lần soát trước.",
                   "lien_ket": "/campaign?tab=soat"})
    return tb
