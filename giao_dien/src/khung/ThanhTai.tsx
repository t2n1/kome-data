// Thanh tải chung: vạch mảnh trên đầu trang + nhãn "Đang tải dữ liệu · 43%".
// Số lấy từ khung/tien_do.ts. Chỉ hiện khi đợt tải kéo dài quá 200 ms — dữ
// liệu có sẵn (304 / ảnh chụp) về ngay thì không nháy thanh nào.
import { useEffect, useState, useSyncExternalStore } from "react";
import { phanTram, theoDoi } from "./tien_do";

export function ThanhTai() {
  const p = useSyncExternalStore(theoDoi, phanTram);
  const [hien, setHien] = useState(false);
  const [cuoi, setCuoi] = useState(false);  // khoảnh khắc 100% trước khi tắt

  useEffect(() => {
    if (p === null) {
      if (!hien) return;
      setCuoi(true);
      const h = setTimeout(() => { setHien(false); setCuoi(false); }, 350);
      return () => clearTimeout(h);
    }
    if (hien) return;
    const h = setTimeout(() => setHien(true), 200);
    return () => clearTimeout(h);
  }, [p === null, hien]);

  if (!hien) return null;
  const so = cuoi ? 100 : p ?? 100;
  return (
    <div className="thanh-tai" role="progressbar" aria-label="Đang tải dữ liệu"
      aria-valuemin={0} aria-valuemax={100} aria-valuenow={so}>
      <div className="thanh-tai-vach" style={{ width: `${so}%` }} />
      <div className="thanh-tai-nhan">Đang tải dữ liệu · {so}%</div>
    </div>
  );
}
