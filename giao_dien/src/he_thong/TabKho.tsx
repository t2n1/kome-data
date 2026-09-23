// Dải tab của màn Kho dữ liệu: Vận hành · Sơ đồ luồng · Cột nối (đợt 2b). Tab
// đang xem mang aria-current (bất biến "màu + chữ", không chỉ đổi viền).
const TAB = [["van-hanh", "/kho-du-lieu", "Vận hành"], ["luong", "/kho-du-lieu/luong", "Sơ đồ luồng"],
  ["cot-noi", "/kho-du-lieu/cot-noi", "Cột nối"]] as const;

export function TabKho({ dang }: { dang: typeof TAB[number][0] }) {
  return (
    <nav className="loc" aria-label="Các phần của màn Kho dữ liệu">
      {TAB.map(([ma, duong, nhan]) => (
        <a key={ma} href={duong} className={dang === ma ? "dang-xem" : undefined} aria-current={dang === ma ? "page" : undefined}>{nhan}</a>))}
    </nav>
  );
}
