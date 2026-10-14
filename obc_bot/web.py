"""Nửa NẠP: gửi file lên web như một người dùng (tài khoản obc-bot).

Không đụng CSDL — máy chạy không giữ mật khẩu CSDL nào. Mọi file đi qua
POST /api/kho-du-lieu/nap = pipeline.ingest, 5 cổng như kéo thả tay."""
from pathlib import Path

DICH_VU_KEYRING = "kome-obc-bot"
_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


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
        return self._json(r)["ket_qua"]

    @staticmethod
    def _json(r) -> dict:
        if r.status_code == 401:
            raise LoiWeb("Chưa đăng nhập web (sai mật khẩu obc-bot hoặc phiên hết hạn).")
        if r.status_code == 403:
            raise LoiWeb(f"Web từ chối: {_loi(r)}")
        if r.status_code != 200:
            raise LoiWeb(f"Web lỗi {r.status_code}: {_loi(r)}")
        return r.json()


def mat_khau_web(ten: str) -> str:
    import keyring
    mk = keyring.get_password(DICH_VU_KEYRING, ten)
    if not mk:
        raise LoiWeb(f"Chưa lưu mật khẩu web cho {ten!r} trên máy này — chạy: "
                     "python -m obc_bot luu-mat-khau --cau-hinh <file>.toml")
    return mk
