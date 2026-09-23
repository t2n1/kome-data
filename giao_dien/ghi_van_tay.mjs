// Ghi dấu vân tay mã nguồn giao diện vào kome/web/spa/.nguon sau mỗi lần build.
// tests/test_api.py::test_ban_build_khop_ma_nguon tính lại và so: sửa giao diện
// mà quên `npm run build` (bản build được commit — máy công ty không có Node)
// thì test đỏ, thay vì máy công ty lặng lẽ chạy giao diện cũ.
// PHẢI khớp thuật toán của kome/web/spa.py::van_tay_nguon.
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";

const goc = new URL(".", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const tep = [];
const di = d => {
  for (const t of readdirSync(d).sort()) {
    const p = join(d, t);
    if (statSync(p).isDirectory()) di(p); else tep.push(p);
  }
};
di(join(goc, "src"));
for (const t of ["index.html", "vite.config.ts", "package.json", "tsconfig.json"]) tep.push(join(goc, t));
const h = createHash("sha1");
for (const p of tep.sort((a, b) => relative(goc, a).split(sep).join("/") < relative(goc, b).split(sep).join("/") ? -1 : 1)) {
  h.update(relative(goc, p).split(sep).join("/"));
  h.update(readFileSync(p).toString("utf8").replace(/\r\n/g, "\n"));
}
writeFileSync(join(goc, "..", "kome", "web", "spa", ".nguon"), h.digest("hex") + "\n");
