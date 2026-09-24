"""Màn Nhật ký thao tác (thiết kế số 20) — ĐỌC GỘP các sổ đã có, không chép.

Năm loại thao tác, năm nguồn, mỗi nguồn đã là sổ chỉ-thêm ở nơi của nó:

| loại      | nguồn                                   | "ai"                  |
|-----------|-----------------------------------------|-----------------------|
| nap       | meta.ingest_batch.loaded_at             | nap_boi (033)         |
| huy       | meta.ingest_batch.undone_at             | huy_boi (033)         |
| ngan_sach | app.ngan_sach_nhat_ky (026)             | sua_boi               |
| quyen     | app.nhat_ky_quyen (033)                 | sua_boi               |
| tiep_xuc  | app.nhat_ky_tiep_xuc (030)              | nguoi_dung_id         |

"Ai" NULL = máy trong công ty chưa bật đăng nhập (hoặc lô nạp trước 033, hoặc
đổi quyền bằng script) — màn in rõ ra thay vì bỏ trống. Ngân sách truy vấn: 2
(dòng thời gian + tổng hợp 30 ngày).
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from kome.tuoi_du_lieu import MUI_GIO

# (icon, nhãn, lớp màu .vien.<lớp>) — icon và bố cục theo LOAI của Nhật ký.dc.html
LOAI = {
    "nap": ("⟳", "Nạp dữ liệu", "ok"),
    "huy": ("✕", "Hoàn tác lô", "loi"),
    "ngan_sach": ("¥", "Sửa ngân sách", "canh"),
    "quyen": ("⚿", "Phân quyền", "lam"),
    "tiep_xuc": ("☎", "Ghi tiếp xúc", "nhat"),
}

TEN_CO = {"duoc_vao_kho_du_lieu": "vào Kho dữ liệu (nạp + hoàn tác)",
          "duoc_sua_ngan_sach": "sửa Ngân sách",
          "duoc_quan_tri": "quản trị (đổi quyền người khác)"}

# Một khối UNION ALL, mỗi nhánh cùng bảy cột. Tên người nối MỘT LẦN ở ngoài.
_NGUON = """
    SELECT 'nap' AS loai, b.loaded_at AS luc, b.nap_boi AS ai, b.source_file AS doi_tuong,
           b.spec_name AS chi_tiet, NULL::text AS truoc, b.row_count::text AS sau
    FROM meta.ingest_batch b
    UNION ALL
    SELECT 'huy', b.undone_at, b.huy_boi, b.source_file, b.spec_name,
           b.row_count::text, NULL
    FROM meta.ingest_batch b WHERE b.undone_at IS NOT NULL
    UNION ALL
    SELECT 'ngan_sach', n.sua_luc, n.sua_boi,
           coalesce(n.salesperson_code, 'Công ty') || ' · ' || to_char(n.thang, 'YYYY-MM')
             || CASE n.chi_so WHEN 'lai_gop' THEN ' · lãi gộp' ELSE ' · doanh thu' END, NULL,
           n.muc_tieu_cu::text, n.muc_tieu_moi::text
    FROM app.ngan_sach_nhat_ky n
    UNION ALL
    SELECT 'quyen', q.sua_luc, q.sua_boi, q.ten_dang_nhap, q.co,
           q.gia_tri_cu::text, q.gia_tri_moi::text
    FROM app.nhat_ky_quyen q
    UNION ALL
    SELECT 'tiep_xuc', t.thoi_diem, t.nguoi_dung_id, t.customer_code, t.kieu,
           t.noi_dung, t.ket_qua
    FROM app.nhat_ky_tiep_xuc t"""


@dataclass
class Dong:
    loai: str
    luc: datetime
    nguoi: str | None
    doi_tuong: str
    chi_tiet: str | None
    truoc: str | None
    sau: str | None
    ten_khach: str | None = None

    @property
    def icon(self) -> str:
        return LOAI[self.loai][0]

    @property
    def nhan(self) -> str:
        return LOAI[self.loai][1]

    @property
    def mau(self) -> str:
        return LOAI[self.loai][2]

    @property
    def khi(self) -> str:
        return self.luc.astimezone(MUI_GIO).strftime("%Y-%m-%d %H:%M")

    @property
    def noi_dung(self) -> str:
        """Một câu đọc được cho từng loại — chữ ở ĐÂY, không rải trong template."""
        if self.loai == "nap":
            return f"Nạp {self.doi_tuong}"
        if self.loai == "huy":
            return f"Hoàn tác lô {self.doi_tuong} — xoá mọi dòng của lô khỏi kho"
        if self.loai == "ngan_sach":
            return f"Chỉ tiêu {self.doi_tuong}"
        if self.loai == "quyen":
            return f"Quyền {TEN_CO.get(self.chi_tiet, self.chi_tiet)} của {self.doi_tuong}"
        return f"{self.ten_khach or self.doi_tuong}: {self.truoc}"

    @property
    def truoc_sau(self) -> tuple[str, str] | None:
        """(trước, sau) như cột "trước → sau" của gói thiết kế; None nếu loại
        đó không có giá trị cũ/mới để so."""
        def yen(v):
            return f"¥{int(v):,}" if v is not None else "(chưa đặt)"
        if self.loai == "nap":
            return None if self.sau is None else ("—", f"{int(self.sau):,} dòng")
        if self.loai == "huy":
            return (f"{int(self.truoc):,} dòng", "(đã hoàn tác)")
        if self.loai == "ngan_sach":
            return (yen(self.truoc), yen(self.sau) if self.sau is not None else "(xoá chỉ tiêu)")
        if self.loai == "quyen":
            def bt(v):
                return "có" if v == "true" else "không"
            return (bt(self.truoc), bt(self.sau))
        return None


def _loc(loai: str | None, tim: str) -> tuple[str, list]:
    dk, ts = [], []
    if loai in LOAI:
        dk.append("u.loai = %s")
        ts.append(loai)
    if tim:
        dk.append("(coalesce(s.ten, nd.ten_dang_nhap, '') ILIKE %s OR u.doi_tuong ILIKE %s"
                  " OR coalesce(u.truoc, '') ILIKE %s OR coalesce(c.customer_name, '') ILIKE %s)")
        mau = f"%{tim}%"
        ts += [mau] * 4
    return (" AND ".join(dk) or "true"), ts


def dong_thoi_gian(conn, loai: str | None = None, tim: str = "",
                   gioi_han: int = 200) -> list[Dong]:
    """MỘT lượt hỏi, mới nhất trước."""
    dk, ts = _loc(loai, tim.strip())
    rows = conn.execute(
        f"""SELECT u.loai, u.luc, coalesce(s.ten, nd.ten_dang_nhap), u.doi_tuong, u.chi_tiet,
                   u.truoc, u.sau, c.customer_name
            FROM ({_NGUON}) u
            LEFT JOIN app.nguoi_dung nd ON nd.id = u.ai
            LEFT JOIN core.dim_salesperson s ON s.salesperson_code = nd.salesperson_code
            LEFT JOIN core.dim_customer c
                   ON u.loai = 'tiep_xuc' AND c.customer_code = u.doi_tuong AND c.is_current
            WHERE {dk}
            ORDER BY u.luc DESC LIMIT %s""", ts + [gioi_han]).fetchall()
    return [Dong(*r) for r in rows]


@dataclass
class TongHop:
    theo_loai: dict[str, int]
    theo_nguoi: list[tuple[str, int]]
    khong_ro_ai: int
    soat_lai: list[Dong]

    @property
    def tong(self) -> int:
        return sum(self.theo_loai.values())


def tong_hop_30_ngay(conn) -> TongHop:
    """MỘT lượt hỏi: đếm theo loại, theo người, số thao tác không rõ ai, và
    danh sách "Cần soát lại" (hoàn tác lô + đổi quyền trong 30 ngày — hai thao
    tác mà sai một lần là mất dữ liệu hoặc mở cửa màn có nút xoá).

    30 ngày tính theo ĐỒNG HỒ THẬT (`now()`): đây là sổ sự kiện ngoài đời, không
    phải chỉ số trên dữ liệu bán, nên mốc `mart.moc_thoi_gian` không áp dụng."""
    rows = conn.execute(
        f"""WITH u AS MATERIALIZED (
                SELECT u.*, coalesce(s.ten, nd.ten_dang_nhap) AS ten
                FROM ({_NGUON}) u
                LEFT JOIN app.nguoi_dung nd ON nd.id = u.ai
                LEFT JOIN core.dim_salesperson s ON s.salesperson_code = nd.salesperson_code
                WHERE u.luc > now() - interval '30 days')
            SELECT 'loai', loai, count(*)::int, NULL::timestamptz, NULL, NULL, NULL, NULL
            FROM u GROUP BY loai
            UNION ALL
            SELECT 'nguoi', ten, count(*)::int, NULL, NULL, NULL, NULL, NULL
            FROM u WHERE ten IS NOT NULL GROUP BY ten
            UNION ALL
            SELECT 'khong_ro', NULL, count(*)::int, NULL, NULL, NULL, NULL, NULL
            FROM u WHERE ai IS NULL AND loai <> 'tiep_xuc'
            UNION ALL
            SELECT 'soat', loai, 0, luc, ten, doi_tuong, chi_tiet, truoc || '|' || coalesce(sau, '')
            FROM u WHERE loai IN ('huy', 'quyen')""").fetchall()
    theo_loai = {k: 0 for k in LOAI}
    theo_nguoi, khong_ro, soat = [], 0, []
    for r in rows:
        if r[0] == "loai":
            theo_loai[r[1]] = r[2]
        elif r[0] == "nguoi":
            theo_nguoi.append((r[1], r[2]))
        elif r[0] == "khong_ro":
            khong_ro = r[2]
        else:
            truoc, _, sau = (r[7] or "|").partition("|")
            soat.append(Dong(r[1], r[3], r[4], r[5], r[6], truoc or None, sau or None))
    theo_nguoi.sort(key=lambda x: (-x[1], x[0]))
    soat.sort(key=lambda d: d.luc, reverse=True)
    return TongHop(theo_loai, theo_nguoi[:8], khong_ro, soat[:10])


def csv(dong: list[Dong]) -> str:
    """CSV cho nút "⤓ Xuất CSV" của gói thiết kế. BOM UTF-8 để Excel Nhật mở
    đúng chữ Việt + chữ Nhật thay vì đoán Shift-JIS."""
    import csv as _csv
    import io
    b = io.StringIO()
    w = _csv.writer(b)
    w.writerow(["thời điểm", "loại", "người", "nội dung", "trước", "sau"])
    for d in dong:
        ts = d.truoc_sau or ("", "")
        w.writerow([d.khi, d.nhan, d.nguoi or "(không rõ)", d.noi_dung, ts[0], ts[1]])
    return "﻿" + b.getvalue()
