"""Nửa NẠP: gửi file lên web như một người dùng (tài khoản obc-bot).

Không đụng CSDL — máy chạy không giữ mật khẩu CSDL nào. Mọi file đi qua
POST /api/kho-du-lieu/nap = pipeline.ingest, 5 cổng như kéo thả tay."""
from pathlib import Path

DICH_VU_KEYRING = "kome-obc-bot"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

# Trang gọi lại ngay sau khi nạp để web tính sẵn ảnh chụp (kome/web/anh_chup.py). Mỗi lần nạp làm mọi ảnh chụp cũ hết
# hạn, mà trên Vercel `lam_nong` của web bị bỏ (luồng nền đóng băng sau khi trả lời) — đo thật 2026-10-15: lần mở đầu
# sau khi nạp /api/ban-do 5,8 s, /api/kho-hang 5,6 s, /api/san-pham 3,4 s; lần sau 0,1 s. Tham số mặc định = đúng khoá
# ảnh chụp người dùng mở (không khoảng xem).
_KHOI_TONG_QUAN = ("kpi", "ns_thang", "so_sanh_sale", "theo_thang", "xu_huong", "suc_khoe_khach", "han_su_dung",
                   "viec_hom_nay", "thang_nay_chua_mua", "cong_no", "don_hang", "danh_sach_khach", "hieu_suat_nganh",
                   "tuong_quan", "tang_truong", "khach_moi", "bien_loi_nhuan")
TRANG_LAM_NONG = (("/api/thong-bao",) + tuple(f"/api/tong-quan/{k}" for k in _KHOI_TONG_QUAN) + (
    "/api/khach-hang/ds", "/api/bao-cao", "/api/du-bao", "/api/lien-he", "/api/ban-do", "/api/san-pham",
    "/api/san-pham/khoang", "/api/kho-hang", "/api/cong-no", "/api/mua-vu", "/api/bang-gia", "/api/doi-thu/tong-quan"))


class LoiWeb(Exception):
    pass


def _loi(r) -> str:
    try:
        return r.json().get("loi") or r.text[:200]
    except Exception:
        return r.text[:200]


class KhachWeb:
    def __init__(self, base_url: str, phien=None):
        self._kw = {}
        if phien is None:
            import requests
            phien = requests.Session()
            self._kw = {"timeout": 120}
        self.base = base_url.rstrip("/")
        self.phien = phien

    def _goi(self, phuong_thuc: str, url: str, **kw):
        try:
            return getattr(self.phien, phuong_thuc)(url, **kw, **self._kw)
        except LoiWeb:
            raise
        except Exception as e:
            raise LoiWeb(f"Không kết nối được web {self.base}: {e}") from e

    def dang_nhap(self, ten: str, mat_khau: str) -> None:
        r = self._goi("post", self.base + "/dang-nhap", data={"ten": ten, "mat_khau": mat_khau})
        if r.status_code == 401:
            raise LoiWeb(f"Sai tên hoặc mật khẩu tài khoản web {ten!r}.")
        if r.status_code >= 400:
            raise LoiWeb(f"Đăng nhập web lỗi {r.status_code}: {_loi(r)}")

    def hom_nay(self) -> dict:
        return self._json(self._goi("get", self.base + "/api/kho-du-lieu/hom-nay"))

    def nap(self, files: list[Path]) -> list[dict]:
        mo = []
        try:
            for p in files:
                try:
                    mo.append(open(p, "rb"))
                except OSError as e:
                    raise LoiWeb(f"Không đọc được file {p}: {e}") from e
            r = self._goi("post", self.base + "/api/kho-du-lieu/nap",
                          files=[("files", (p.name, f, _XLSX)) for p, f in zip(files, mo)])
        finally:
            for f in mo:
                f.close()
        j = self._json(r)
        if not isinstance(j, dict) or "ket_qua" not in j:
            raise LoiWeb(f"Web trả kết quả nạp thiếu `ket_qua`: {str(j)[:200]}")
        return j["ket_qua"]

    def lam_nong(self, duong) -> int:
        """GET lần lượt `duong` (bỏ qua lỗi từng trang); trả số trang trả 200."""
        ok = 0
        for d in duong:
            try:
                ok += self._goi("get", self.base + d).status_code == 200
            except LoiWeb:
                pass
        return ok

    @staticmethod
    def _json(r) -> dict:
        if r.status_code == 401:
            raise LoiWeb("Chưa đăng nhập web (sai mật khẩu obc-bot hoặc phiên hết hạn).")
        if r.status_code == 403:
            raise LoiWeb(f"Web từ chối: {_loi(r)}")
        if r.status_code != 200:
            raise LoiWeb(f"Web lỗi {r.status_code}: {_loi(r)}")
        try:
            return r.json()
        except Exception as e:
            raise LoiWeb(f"Web trả về không phải JSON (mã 200): {r.text[:200]!r}") from e


def mat_khau_web(ten: str) -> str:
    try:
        import keyring
        mk = keyring.get_password(DICH_VU_KEYRING, ten)
    except Exception as e:
        raise LoiWeb(f"Không đọc được mật khẩu từ Windows Credential Manager: {e!r}") from e
    if not mk:
        raise LoiWeb(f"Chưa lưu mật khẩu web cho {ten!r} trên máy này — chạy: "
                     "python -m obc_bot luu-mat-khau --cau-hinh <file>.toml")
    return mk
