// "Xem thêm" dùng chung cho danh sách dài (soát 2026-10-16 — chủ DN: "nhiều thông tin quá nên hơi loạn"):
// mặc định hiện `n` dòng đầu (thứ tự danh sách giữ nguyên), nút cuối hiện phần còn lại / thu gọn.
// Chỉ CẮT HIỂN THỊ — tổng / đếm của khối vẫn tính trên CẢ danh sách ở nơi gọi.
import { useState } from "react";
import { so } from "../dinh_dang";

export const MAC_DINH_XEM = 10;

/** Thuần (có test): phần đang hiện + số dòng đang ẩn. */
export function catXem<T>(ds: readonly T[], n: number, mo: boolean): { hien: T[]; an: number } {
  if (mo || ds.length <= n) return { hien: [...ds], an: 0 };
  return { hien: ds.slice(0, n), an: ds.length - n };
}

export function useXemThem<T>(ds: readonly T[], n = MAC_DINH_XEM, don_vi = "dòng") {
  const [mo, datMo] = useState(false);
  const { hien, an } = catXem(ds, n, mo);
  const nut = ds.length <= n ? null
    : <button type="button" className="nut-xem-them" onClick={() => datMo(!mo)} aria-expanded={mo}>
        {mo ? "Thu gọn ▴" : `Xem thêm ${so(an)} ${don_vi} ▾`}</button>;
  return { hien, nut };
}
