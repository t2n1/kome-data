"""Campaign tuần (/campaign, migration 074) — máy công ty gửi bản kế hoạch + soát, web lưu và hiện bản mới nhất.
Đặc tả: docs/superpowers/specs/2026-10-23-campaign-tuan-design.md."""
import copy
from datetime import date
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kome import campaign as CP
from kome.web.app import create_app

_SRC = Path(__file__).resolve().parents[1] / "giao_dien" / "src"
MK = "mat-khau-cua-bot-2026"
BI_MAT = "bi-mat-phien-du-dai-2026"


def _ban(**sua):
    d = {
        "phien_ban": 1, "lap_luc": "2026-10-23T14:00", "nguon": "Tồn: 【OBC】在庫更新",
        "thu_tu_gia": ["BA07", "", "DK06"],
        "ke_hoach": [{"tu": "2026-11-27", "den": "2026-12-03", "tab": "2026/12", "tuan_so": 1, "ky": "11/27 ~ 12/3",
                      "ma": [{"ma": "BA07", "ten": "Barona", "nhom": "uu_tien", "ly": "đẩy lô cũ", "chon": True},
                             {"ma": "DK06", "ten": "Duong Kien", "nhom": "nghi", "ly": "", "chon": False}]}],
        "soat": {"lan_truoc": "2026-10-23T0830",
                 "lich_doi": [], "lo_qua_han": [], "lo_lech": [], "khong_cybozu": [], "goi_y": [],
                 "tuan": [{"tu": "2026-10-23", "den": "2026-10-29", "so_ma": 50,
                           "dong": [{"ma": "NT01", "ten": "", "pd": "PHỤ THUỘC LÔ CHƯA CHỐT", "ly": "lô 10/27", "moi": True, "off": ""},
                                    {"ma": "VF07", "ten": "", "pd": "THIẾU HÀNG", "ly": "hết 10/26", "moi": False, "off": ""}]},
                          {"tu": "2026-11-13", "den": "2026-11-19", "so_ma": 40,
                           "dong": [{"ma": "BI01", "ten": "", "pd": "THIẾU HÀNG", "ly": "xa", "moi": True, "off": ""}]}]},
    }
    d.update(sua)
    return d


@pytest.mark.parametrize("sua, chu", [
    ({"phien_ban": 2}, "phien_ban"),
    ({"lap_luc": ""}, "lap_luc"),
    ({"thu_tu_gia": ["A", 1]}, "thu_tu_gia"),
    ({"ke_hoach": {}}, "ke_hoach"),
    ({"soat": []}, "soat"),
])
def test_kiem_tu_choi_hinh_dang_sai(sua, chu):
    with pytest.raises(CP.LoiDuLieu, match=chu):
        CP.kiem(_ban(**sua))


def test_kiem_tu_choi_nhom_va_phan_dinh_la_ngay_nguoc():
    d = _ban()
    d["ke_hoach"][0]["ma"][0]["nhom"] = "la"
    with pytest.raises(CP.LoiDuLieu, match="nhom"):
        CP.kiem(d)
    d = _ban()
    d["soat"]["tuan"][0]["dong"][0]["pd"] = "OK"
    with pytest.raises(CP.LoiDuLieu, match="pd"):
        CP.kiem(d)
    d = _ban()
    d["ke_hoach"][0]["tren_sheet"] = ["BA07", 3]
    with pytest.raises(CP.LoiDuLieu, match="tren_sheet"):
        CP.kiem(d)
    d["ke_hoach"][0]["tren_sheet"] = ["BA07"]
    d["ke_hoach"][0]["ma"][0]["tren_sheet"] = True
    CP.kiem(d)                                          # trường tuỳ chọn của tuần đã có trên sheet
    d["ke_hoach"][0]["ma"][0]["tren_sheet"] = "co"
    with pytest.raises(CP.LoiDuLieu, match="tren_sheet"):
        CP.kiem(d)
    d = _ban()
    m = d["ke_hoach"][0]["ma"][0]
    m["so"] = {"ton": 89, "ngay": 15, "bien": 0.38, "lai": 10000, "uoc": False, "tuan_do": 13, "lan_loi": 10, "on_dinh": "loi", "mua": 1.5,
               "lo": {"ngay": "2026-11-12", "sl": 500, "tt": "仮登録"}, "han": {"ngay": "2027-04-15", "sl": 195},
               "canh": "phụ thuộc lô 11/02", "ngung": True, "khoa_la": [1]}
    CP.kiem(d)                                          # ô số của bảng — tuỳ chọn, khoá lạ bỏ qua
    for sai, chu in (({"ton": "89"}, "so.ton"), ({"lai": float("nan")}, "so.lai"), ({"uoc": 1}, "so.uoc"),
                     ({"lo": {"ngay": "11/12"}}, "so.lo"), ({"ngan": 3}, "so.ngan"), ({"lan_loi": "4"}, "so.lan_loi"),
                     ({"on_dinh": False}, "so.on_dinh"), ([], "so")):
        m["so"] = sai
        with pytest.raises(CP.LoiDuLieu, match=chu):
            CP.kiem(d)
    d = _ban()
    d["ke_hoach"][0]["den"] = "2026-11-01"
    with pytest.raises(CP.LoiDuLieu, match="ngày cuối"):
        CP.kiem(d)
    CP.kiem(_ban())


def test_nop_doc_moi_nhat_va_giu_30_ngay_nhung_khong_xoa_ban_moi_nhat(conn):
    assert CP.moi_nhat(conn)["du_lieu"] is None
    a = CP.nop(conn, _ban(lap_luc="A"), None)
    conn.execute("UPDATE app.campaign_soat SET nop_luc = now() - interval '40 days' WHERE id = %s", (a,))
    b = CP.nop(conn, _ban(lap_luc="B"), None)
    conn.commit()
    ids = [r[0] for r in conn.execute("SELECT id FROM app.campaign_soat ORDER BY id")]
    assert ids == [b]                                   # bản 40 ngày bị dọn
    conn.execute("UPDATE app.campaign_soat SET nop_luc = now() - interval '40 days'")
    conn.commit()
    m = CP.moi_nhat(conn)
    assert m["id"] == b and m["du_lieu"]["lap_luc"] == "B"   # bản cũ mà là bản duy nhất: vẫn còn
    c = CP.nop(conn, _ban(lap_luc="C"), None)
    conn.commit()
    assert [r[0] for r in conn.execute("SELECT id FROM app.campaign_soat")] == [c]


def test_nop_qua_co_thi_tu_choi(conn, monkeypatch):
    monkeypatch.setattr(CP, "CO_TOI_DA", 100)
    with pytest.raises(CP.LoiDuLieu, match="lớn quá"):
        CP.nop(conn, _ban(), None)


def test_chuong_chi_lay_tuan_dang_chay_va_sap_chay_thieu_hang_truoc():
    ban = {"id": 9, "du_lieu": _ban()}
    tb = CP.thong_bao(ban, date(2026, 10, 24))
    assert [t["ma"] for t in tb] == ["campaign-2026-10-23-VF07-THIẾU HÀNG",
                                     "campaign-2026-10-23-NT01-PHỤ THUỘC LÔ CHƯA CHỐT"]   # BI01 (tuần 11/13) quá xa
    assert tb[0]["muc"] == "gap" and tb[1]["muc"] == "canh" and tb[0]["lien_ket"] == "/campaign?tab=soat"
    ban["du_lieu"]["soat"]["lich_doi"] = [{"kieu": "ĐỔI"}]
    assert CP.thong_bao(ban, date(2026, 10, 24))[-1]["ma"] == "campaign-lich-9"
    assert CP.thong_bao({"id": None, "du_lieu": None}, date(2026, 10, 24)) == []
    assert len(CP.thong_bao(ban, date(2026, 11, 10))) == 2   # 11/10: tuần 10/23 đã qua, tuần 11/13 trong 8 ngày


def test_api_gui_doc_va_chuong(conn, test_db_url):
    c = TestClient(create_app(db_url=test_db_url))
    assert c.get("/api/campaign").json()["du_lieu"] is None
    assert c.post("/api/kho-du-lieu/campaign", content="x", headers={"content-type": "text/plain"}).status_code == 415
    r = c.post("/api/kho-du-lieu/campaign", json=_ban(phien_ban=0))
    assert r.status_code == 400 and "phien_ban" in r.json()["loi"]
    r = c.post("/api/kho-du-lieu/campaign", json=_ban())
    assert r.status_code == 200, r.text
    d = c.get("/api/campaign").json()
    assert d["id"] == r.json()["id"] and d["du_lieu"]["ke_hoach"][0]["ma"][0]["ma"] == "BA07"
    assert c.get("/campaign").status_code == 200


def test_gui_can_co_kho_du_lieu_xem_thi_ai_cung_duoc(conn, test_db_url, monkeypatch):
    from kome.web import nguoi_dung as ND
    monkeypatch.setenv("KOME_SESSION_SECRET", BI_MAT)
    ND.tao(conn, "sale", MK)
    ND.tao(conn, "obc-bot", MK, kho_du_lieu=True)
    conn.commit()
    c = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
    assert c.post("/api/kho-du-lieu/campaign", json=_ban()).status_code == 401
    c.post("/dang-nhap", data={"ten": "sale", "mat_khau": MK})
    assert c.post("/api/kho-du-lieu/campaign", json=_ban()).status_code == 403
    assert c.get("/api/campaign").status_code == 200
    b = TestClient(create_app(db_url=test_db_url), follow_redirects=False)
    b.post("/dang-nhap", data={"ten": "obc-bot", "mat_khau": MK})
    assert b.post("/api/kho-du-lieu/campaign", json=copy.deepcopy(_ban())).status_code == 200
    assert conn.execute("SELECT n.ten_dang_nhap FROM app.campaign_soat c JOIN app.nguoi_dung n ON n.id = c.nop_boi"
                        ).fetchone()[0] == "obc-bot"


def test_muc_thanh_ben_va_route_co_mat():
    muc = (_SRC / "khung" / "muc.ts").read_text(encoding="utf-8")
    assert 'url: "/campaign"' in muc
    assert '"/campaign"' in (_SRC / "main.tsx").read_text(encoding="utf-8")
    src = (_SRC / "campaign" / "ManCampaign.tsx").read_text(encoding="utf-8")
    assert "/api/campaign" in src and "toFixed(" not in src and "de-DE" not in src
