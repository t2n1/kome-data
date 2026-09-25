// Tiến độ tải dữ liệu — MỘT bộ đếm chung cho mọi lượt `lay()` (api.ts).
//
// Phần trăm là trung bình tiến độ của các yêu cầu trong CÙNG một đợt (đợt bắt
// đầu khi không còn yêu cầu nào đang chạy). Mỗi yêu cầu có hai pha:
//  - chờ máy chủ (chưa có header): tiến dần theo thời gian tới 30% — máy chủ
//    không báo nó đã tính tới đâu, nên pha này là ước lượng;
//  - nhận thân: 30% → 100% theo byte đã nhận / Content-Length (số THẬT).
//    Không có Content-Length thì tiếp tục ước theo thời gian, dừng ở 95%.
// Con số hiển thị chỉ tăng, không lùi (thêm yêu cầu giữa đợt không kéo nó xuống).

type YeuCau = { bat_dau: number; co_header: boolean; nhan: number; tong: number | null; xong: boolean };

let dot: YeuCau[] = [];
let dang_chay = 0;
let da_hien = 0;
const nghe = new Set<() => void>();
let hen: number | undefined;

let anh: number | null = null;  // ảnh chụp cho useSyncExternalStore — chỉ đổi trong bao()

function bao() { anh = tinh(); for (const f of nghe) f(); }

function nhip() {
  // Chạy lại mỗi 120 ms khi còn yêu cầu đang chờ — để pha "chờ máy chủ" nhích lên.
  if (hen !== undefined) return;
  hen = window.setInterval(() => {
    if (dang_chay === 0) { clearInterval(hen); hen = undefined; return; }
    bao();
  }, 120);
}

function tienDo(y: YeuCau, bay_gio: number): number {
  if (y.xong) return 1;
  const t = bay_gio - y.bat_dau;
  if (!y.co_header) return 0.3 * (1 - Math.exp(-t / 1500));
  if (y.tong && y.tong > 0) return 0.3 + 0.7 * Math.min(1, y.nhan / y.tong);
  return 0.3 + 0.65 * (1 - Math.exp(-t / 2500));
}

export function phanTram(): number | null { return anh; }

function tinh(): number | null {
  if (dang_chay === 0) return null;
  const bay_gio = performance.now();
  const p = dot.reduce((s, y) => s + tienDo(y, bay_gio), 0) / dot.length;
  da_hien = Math.max(da_hien, Math.min(99, Math.floor(p * 100)));
  return da_hien;
}

export function theoDoi(f: () => void): () => void {
  nghe.add(f);
  return () => { nghe.delete(f); };
}

/** Bắt đầu một yêu cầu; trả về các hàm báo tiến độ. */
export function batDau() {
  if (dang_chay === 0) { dot = []; da_hien = 0; }
  const y: YeuCau = { bat_dau: performance.now(), co_header: false, nhan: 0, tong: null, xong: false };
  dot.push(y);
  dang_chay++;
  nhip();
  bao();
  return {
    header(tong: number | null) { y.co_header = true; y.tong = tong; bao(); },
    nhan(n: number) { y.nhan += n; bao(); },
    xong() {
      if (y.xong) return;
      y.xong = true;
      dang_chay--;
      bao();
    },
  };
}

/** Đọc thân phản hồi theo từng khúc để đếm byte, rồi parse JSON. */
export async function docJson(r: Response, td: ReturnType<typeof batDau>): Promise<unknown> {
  const dai = Number(r.headers.get("Content-Length"));
  td.header(Number.isFinite(dai) && dai > 0 ? dai : null);
  if (!r.body) return r.json();
  const doc = r.body.getReader();
  const khuc: Uint8Array[] = [];
  let tong = 0;
  for (;;) {
    const { done, value } = await doc.read();
    if (done) break;
    khuc.push(value);
    tong += value.length;
    td.nhan(value.length);
  }
  const gop = new Uint8Array(tong);
  let o = 0;
  for (const k of khuc) { gop.set(k, o); o += k.length; }
  return JSON.parse(new TextDecoder().decode(gop));
}
