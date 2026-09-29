// Ngăn xếp các hộp thoại đang mở: chỉ hộp Ở TRÊN CÙNG được xử lý Esc / Tab (hộp 409 hay lịch sử mở chồng lên pop-up sửa).
let ngan: number[] = [];
let dem = 0;

/** Đẩy một hộp mới lên đỉnh, trả id của nó. */
export function dayVao(): number { const id = ++dem; ngan.push(id); return id; }
/** Gỡ hộp khỏi ngăn xếp (đúng hộp, không cần là đỉnh — đóng lệch thứ tự vẫn đúng). */
export function goRa(id: number) { ngan = ngan.filter(x => x !== id); }
export const laDinh = (id: number) => ngan.length > 0 && ngan[ngan.length - 1] === id;
export const doSau = () => ngan.length;
export function datLai() { ngan = []; }
