// Build ra ../kome/web/spa (commit vào git — máy công ty không cần Node).
// Dev: `npm run dev` rồi mở http://localhost:5173, /api và /static chuyển
// sang uvicorn ở cổng 8000.
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "../kome/web/spa",
    emptyOutDir: true,
    assetsDir: "assets",
    sourcemap: false,
    target: "es2022",
  },
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/static": "http://127.0.0.1:8000",
      "/tong-quan": "http://127.0.0.1:8000",
      "/giao-dien": "http://127.0.0.1:8000",
      "/dang-xuat": "http://127.0.0.1:8000",
    },
  },
  test: { environment: "node" },
});
