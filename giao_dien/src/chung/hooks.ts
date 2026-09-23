import { useEffect, useRef, useState } from "react";

/** Theo dõi bề rộng thật của một phần tử — biểu đồ vẽ đúng số điểm ảnh, chữ
 *  trên trục không bị co giãn méo như viewBox cố định. */
export function useRong<T extends HTMLElement>(): [React.RefObject<T | null>, number] {
  const ref = useRef<T>(null);
  const [rong, datRong] = useState(0);
  useEffect(() => {
    if (!ref.current) return;
    const ro = new ResizeObserver(e => datRong(Math.round(e[0].contentRect.width)));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, []);
  return [ref, rong];
}
