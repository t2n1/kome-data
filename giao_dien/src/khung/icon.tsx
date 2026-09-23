// Icon CHÉP NGUYÊN VĂN từ object `I` của kome-nav.js (gói thiết kế). Trang trí:
// aria-hidden + focusable=false — chữ nhãn bên cạnh mới là thứ đọc được
// (bất biến đợt 4d, CLAUDE.md).
const I: Record<string, string> = {
  dashboard: '<rect x="2.5" y="2.5" width="5" height="5" rx="1"></rect><rect x="10.5" y="2.5" width="5" height="5" rx="1"></rect><rect x="2.5" y="10.5" width="5" height="5" rx="1"></rect><rect x="10.5" y="10.5" width="5" height="5" rx="1"></rect>',
  chart: '<path d="M3 14.5V8m4 6.5V4.5m4 10V10m4 4.5V6"></path>',
  team: '<path d="M6.4 6.2a2.4 2.4 0 1 0 0-.1M13 8.2a2 2 0 1 0 0-.1"></path><path d="M2.4 15c0-2.3 1.9-3.7 4-3.7s4 1.4 4 3.7M11.6 15c0-1.9.9-3.1 2.4-3.4"></path>',
  user: '<circle cx="9" cy="6" r="2.6"></circle><path d="M3.5 15c0-2.8 2.5-4.5 5.5-4.5s5.5 1.7 5.5 4.5"></path>',
  pin: '<path d="M9 16s5.2-5 5.2-8.6A5.2 5.2 0 0 0 9 2.2a5.2 5.2 0 0 0-5.2 5.2C3.8 11 9 16 9 16z"></path><circle cx="9" cy="7.3" r="1.8"></circle>',
  crm: '<path d="M2.6 5.5h12.8v9.2H2.6z"></path><path d="M6.6 5.5V4a1.6 1.6 0 0 1 1.6-1.6h1.6A1.6 1.6 0 0 1 11.4 4v1.5"></path><path d="M2.6 9.4h12.8"></path>',
  quote: '<path d="M4.4 2.6h6.2l3 3v9.8H4.4z"></path><path d="M10.4 2.6v3.2h3.2M6.6 9.4h4.8M6.6 12h3.2"></path>',
  cart: '<path d="M2.4 3.2h2l1.8 8.2h7.2l1.6-5.6H5.2"></path><circle cx="7.4" cy="14.4" r="1.1"></circle><circle cx="13" cy="14.4" r="1.1"></circle>',
  yen: '<circle cx="9" cy="9" r="6.4"></circle><path d="M6.4 5.8 9 9.4l2.6-3.6M6.6 9.8h4.8M6.6 11.8h4.8M9 9.4v3.4"></path>',
  truck: '<path d="M1.8 4.6h8.4v7.2H1.8z"></path><path d="M10.2 7.4h2.8l2.2 2.4v2h-5z"></path><circle cx="5.2" cy="13.4" r="1.4"></circle><circle cx="12.4" cy="13.4" r="1.4"></circle>',
  back: '<path d="M3 7.4h9.2a3 3 0 0 1 0 6H7.4"></path><path d="M5.8 4.2 2.8 7.4l3 3.2"></path>',
  box: '<path d="M2.6 5.4 9 2.2l6.4 3.2v7.2L9 15.8l-6.4-3.2z"></path><path d="M2.6 5.4 9 8.6l6.4-3.2M9 8.6v7.2"></path>',
  cal: '<rect x="2.6" y="4" width="12.8" height="11.4" rx="1.4"></rect><path d="M2.6 7.6h12.8M6.4 2.6v2.6M11.6 2.6v2.6"></path>',
  refill: '<path d="M14.6 9a5.6 5.6 0 1 1-1.8-4.1"></path><path d="M14.8 2.8v3.4h-3.4"></path><path d="M9 6.4v3.2l2 1.4"></path>',
  cube: '<path d="M9 2.2 15.4 5.6v6.8L9 15.8 2.6 12.4V5.6z"></path><path d="M2.6 5.6 9 9l6.4-3.4M9 9v6.8"></path>',
  target: '<circle cx="9" cy="9" r="6.4"></circle><path d="M9 2.6v12.8M2.6 9h12.8"></path>',
  bell: '<path d="M9 2.6a4.2 4.2 0 0 0-4.2 4.2c0 3.4-1.4 4.6-1.4 4.6h11.2s-1.4-1.2-1.4-4.6A4.2 4.2 0 0 0 9 2.6z"></path><path d="M7.6 14a1.6 1.6 0 0 0 2.8 0"></path>',
  db: '<ellipse cx="9" cy="4.6" rx="6" ry="2.2"></ellipse><path d="M3 4.6v8.8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V4.6"></path><path d="M3 9c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2"></path>',
  gear: '<circle cx="9" cy="9" r="2.6"></circle><path d="M14.4 11a1.2 1.2 0 0 0 .24 1.32l.04.05a1.5 1.5 0 1 1-2.12 2.12l-.05-.05a1.2 1.2 0 0 0-1.32-.24 1.2 1.2 0 0 0-.73 1.1v.13a1.5 1.5 0 1 1-3 0v-.07a1.2 1.2 0 0 0-.79-1.1 1.2 1.2 0 0 0-1.32.24l-.05.05a1.5 1.5 0 1 1-2.12-2.12l.05-.05a1.2 1.2 0 0 0 .24-1.32 1.2 1.2 0 0 0-1.1-.73H2.2a1.5 1.5 0 1 1 0-3h.07a1.2 1.2 0 0 0 1.1-.79 1.2 1.2 0 0 0-.24-1.32l-.05-.05A1.5 1.5 0 1 1 5.2 3.05l.05.05a1.2 1.2 0 0 0 1.32.24h.06a1.2 1.2 0 0 0 .73-1.1V2.2a1.5 1.5 0 1 1 3 0v.07a1.2 1.2 0 0 0 .73 1.1 1.2 1.2 0 0 0 1.32-.24l.05-.05a1.5 1.5 0 1 1 2.12 2.12l-.05.05a1.2 1.2 0 0 0-.24 1.32v.06a1.2 1.2 0 0 0 1.1.73h.13a1.5 1.5 0 1 1 0 3h-.07a1.2 1.2 0 0 0-1.1.73z"></path>',
  out: '<path d="M11.4 5.4V4a1.6 1.6 0 0 0-1.6-1.6H4.6A1.6 1.6 0 0 0 3 4v10a1.6 1.6 0 0 0 1.6 1.6h5.2a1.6 1.6 0 0 0 1.6-1.6v-1.4"></path><path d="M7.4 9h8"></path><path d="M13 6.6 15.4 9 13 11.4"></path>',
  tim: '<circle cx="8" cy="8" r="5"></circle><path d="M12 12l3.5 3.5"></path>',
};

export function Icon({ ten, co = 15 }: { ten: string; co?: number }) {
  return (
    <svg viewBox="0 0 18 18" width={co} height={co} fill="none" stroke="currentColor" strokeWidth={1.4}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false"
      style={{ flexShrink: 0, opacity: 0.9 }} dangerouslySetInnerHTML={{ __html: I[ten] ?? "" }} />
  );
}
