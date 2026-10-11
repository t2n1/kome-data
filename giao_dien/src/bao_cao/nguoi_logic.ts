// Phép tính của MỘT thẻ "Người phụ trách" (trang Doanh thu) — thuần, không React, để test được hành vi.
// Thước: đầy thanh = ngân sách của CHÍNH người đó; có giá trị nào vượt ngân sách (đã có, dự kiến chốt, kỳ so)
// thì thước dài ra tới giá trị lớn nhất và vạch "ngân sách" đứng ở chỗ của nó — không kẹp ở mép phải
// (kẹp là nói "vượt bao nhiêu cũng bằng đúng ngân sách").

export type VaoThe = {
  tt: number;              // đã có
  mt: number | null;       // ngân sách (null = chưa đặt; 0 = đặt bằng không)
  moc: number | null;      // mức lẽ ra phải có tới mốc (máy chủ chia theo ngày làm việc)
  cs: number | null;       // dự kiến chốt (null = tháng đã khép / không dự báo)
  ss: number | null;       // kỳ so
  conNgay: boolean;        // tháng còn ngày làm việc
};

export type ThanhThe = {
  tt: number;              // % bề rộng phần đậm
  db: number | null;       // % bề rộng phần nhạt (dự báo), chỉ khi cs > tt
  ns: number | null;       // vị trí vạch ngân sách, chỉ khi thước dài hơn ngân sách
  nhip: number | null;     // vị trí vạch cam
  ss: number | null;       // vị trí vạch đứt kỳ so; kỳ so ÂM không có chỗ trên thanh (số vẫn in ở dòng chữ)
};

export type Lech = { kieu: "thieu" | "vuot" | "dung"; so: number };
export type ConLai = { kieu: "thieu" | "vuot"; so: number } | { kieu: "dat" | "ns_khong" };

export type The = { thanh: ThanhThe | null; lech: Lech | null; con: ConLai | null };

const kep = (p: number) => Math.max(0, Math.min(100, p));

export function tinhThe(v: VaoThe): The {
  const { tt, mt, moc, cs, ss, conNgay } = v;
  const coNs = mt != null && mt > 0;
  const coNhip = conNgay && moc != null && moc > 0;   // chưa qua ngày làm việc nào → mốc 0, không có nhịp để so

  let thanh: ThanhThe | null = null;
  if (coNs) {
    const thuoc = Math.max(mt, tt, cs ?? 0, ss ?? 0, coNhip ? moc : 0);
    const p = (x: number) => kep(x / thuoc * 100);
    thanh = {
      tt: p(tt),
      db: cs != null && cs > tt ? p(cs) : null,
      ns: thuoc > mt ? p(mt) : null,
      nhip: coNhip ? p(moc) : null,
      ss: ss != null && ss >= 0 ? p(ss) : null,
    };
  }

  const lech: Lech | null = coNhip
    ? { kieu: tt < moc ? "thieu" : tt > moc ? "vuot" : "dung", so: Math.abs(tt - moc) } : null;

  const con: ConLai | null = mt == null ? null
    : mt === 0 ? { kieu: "ns_khong" }        // "đã đặt bằng không" — không có gì để "đạt"
    : tt < mt ? { kieu: "thieu", so: mt - tt }
    : tt > mt ? { kieu: "vuot", so: tt - mt }
    : { kieu: "dat" };

  return { thanh, lech, con };
}
