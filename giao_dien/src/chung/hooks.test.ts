// Vitest chạy môi trường "node" (không jsdom/happy-dom, xem vite.config.ts), nên không
// dựng được cây React thật để canh useRong() y hệt trình duyệt. `noiResizeObserver` tách
// đúng phần LOGIC hay lỗi (nối/huỷ ResizeObserver) ra khỏi state React, nên canh được ở
// đây bằng ResizeObserver GIẢ — không cần DOM thật, không thêm phụ thuộc npm.
import { afterEach, describe, expect, it, vi } from "vitest";
import { noiResizeObserver } from "./hooks";

class ROGia {
  static dot: ROGia[] = [];
  quan_sat: unknown[] = [];
  da_huy = false;
  constructor(public cb: (e: { contentRect: { width: number } }[]) => void) { ROGia.dot.push(this); }
  observe(el: unknown) { this.quan_sat.push(el); }
  disconnect() { this.da_huy = true; }
}

describe("noiResizeObserver — logic đứng sau useRong", () => {
  afterEach(() => { ROGia.dot.length = 0; vi.unstubAllGlobals(); });

  it("phần tử null: không tạo ResizeObserver nào, hàm dỡ là no-op", () => {
    const dat = vi.fn();
    vi.stubGlobal("ResizeObserver", ROGia);
    const huy = noiResizeObserver(null, dat);
    expect(ROGia.dot.length).toBe(0);
    expect(() => huy()).not.toThrow();
    expect(dat).not.toHaveBeenCalled();
  });

  it("có phần tử: observe() đúng phần tử, đo bề rộng khi ResizeObserver bắn, huỷ khi dỡ", () => {
    vi.stubGlobal("ResizeObserver", ROGia);
    const dat = vi.fn();
    const el = {} as Element;
    const huy = noiResizeObserver(el, dat);
    expect(ROGia.dot.length).toBe(1);
    const ro = ROGia.dot[0];
    expect(ro.quan_sat).toEqual([el]);
    ro.cb([{ contentRect: { width: 123.6 } }]);
    expect(dat).toHaveBeenCalledWith(124);   // Math.round
    expect(ro.da_huy).toBe(false);
    huy();
    expect(ro.da_huy).toBe(true);
  });

  it("phần tử đổi (component re-mount muộn, đúng sự cố /mua-vu): gọi lại vẫn nối được", () => {
    // Tái hiện đúng lỗi đã sửa: nếu useRong còn dùng useRef+useEffect([]) một lần thì
    // lần "phần tử xuất hiện muộn" sẽ KHÔNG có cơ hội nối lại — ở đây ta canh rằng bản
    // thân hàm nối, gọi lại với el mới bất cứ lúc nào, luôn nối được (đúng hợp đồng mà
    // useRong dựa vào: useEffect(() => noiResizeObserver(el, datRong), [el])).
    vi.stubGlobal("ResizeObserver", ROGia);
    const dat = vi.fn();
    // Lần đầu: chưa có phần tử (nhánh "đang tải" của màn chưa render khối bọc).
    let huy = noiResizeObserver(null, dat);
    expect(ROGia.dot.length).toBe(0);
    huy();
    // Phần tử xuất hiện (dữ liệu đã tải xong, khối bọc mount) — React gọi lại effect vì
    // `el` (giá trị state, không phải ref ổn định) đã đổi.
    const el = {} as Element;
    huy = noiResizeObserver(el, dat);
    expect(ROGia.dot.length).toBe(1);
    ROGia.dot[0].cb([{ contentRect: { width: 1006 } }]);
    expect(dat).toHaveBeenCalledWith(1006);
    huy();
  });
});
