import { useEffect, useState, type RefCallback } from "react";

/** Nối một phần tử với `ResizeObserver`, trả về hàm dỡ (dùng trong `useEffect`).
 *  Tách khỏi `useRong` để Vitest (môi trường node, không DOM/jsdom) canh được đúng
 *  logic nối/huỷ mà không cần dựng cây React thật. */
export function noiResizeObserver(el: Element | null, datRong: (n: number) => void): () => void {
  if (!el) return () => {};
  const ro = new ResizeObserver(e => datRong(Math.round(e[0].contentRect.width)));
  ro.observe(el);
  return () => ro.disconnect();
}

/** Theo dõi bề rộng thật của một phần tử — biểu đồ vẽ đúng số điểm ảnh, chữ
 *  trên trục không bị co giãn méo như viewBox cố định.
 *
 *  CẦN một REF CALLBACK (không phải `useRef` + đọc `.current` trong
 *  `useEffect(..., [])`): hiệu ứng rỗng-dependency chỉ chạy MỘT LẦN sau lần
 *  commit ĐẦU TIÊN — nếu khối bọc phần tử đó chưa mount ở lần commit đó (vd.
 *  màn đang ở nhánh "đang tải" nên `<div ref>` chưa render), `ref.current` mãi
 *  là `null` và không có lần commit nào sau chạy lại để gắn ResizeObserver:
 *  `rong` đứng ở 0 VĨNH VIỄN, không có cách nào tự hồi phục (sự cố thật ở
 *  `/mua-vu`: `.mv-cay` không lên SVG vì đúng cảnh này). Ref callback được React
 *  gọi lại mỗi khi phần tử THẬT đổi (kể cả lần đầu nó xuất hiện muộn), nên
 *  effect luôn nối được đúng lúc. */
export function useRong<T extends HTMLElement>(): [RefCallback<T>, number] {
  const [el, datEl] = useState<T | null>(null);
  const [rong, datRong] = useState(0);
  useEffect(() => noiResizeObserver(el, datRong), [el]);
  return [datEl, rong];
}
