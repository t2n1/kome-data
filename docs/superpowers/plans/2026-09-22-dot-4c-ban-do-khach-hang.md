# Đợt 4c — Bản đồ khách hàng: Kế hoạch triển khai

> **Cho người thực thi:** BẮT BUỘC dùng sub-skill superpowers:subagent-driven-development
> để làm theo từng task. Các bước dùng cú pháp checkbox (`- [ ]`).

**Mục tiêu:** dựng `/ban-do` — bản đồ lưới 47 ô theo tỉnh, tô màu theo chỉ số, bấm vào
một ô là mở danh bạ đã lọc theo tỉnh đó.

**Kiến trúc:** một bảng tra tĩnh 47 dòng (`core.dim_prefecture`) và một view gộp
(`mart.khach_theo_tinh`) ở migration `025`; một module Python mới (`kome/ban_do.py`)
dựng sẵn toàn bộ hình học SVG; một template và một route. Không JS máy khách, không
tài nguyên ngoài — đúng nếp ba biểu đồ đang có.

**Tech stack:** PostgreSQL (Supabase) · psycopg 3 · Starlette · Jinja2 · SVG dựng sẵn
từ Python · pytest.

**Đặc tả:** `docs/superpowers/specs/2026-09-22-dot-4c-ban-do-khach-hang-design.md`

## Ràng buộc toàn cục

Áp cho MỌI task. Sao nguyên văn từ `CLAUDE.md` và đặc tả:

- OBC là sổ cái chính thức, dữ liệu CHỈ ĐỌC. Không `UPDATE`/`DELETE` trên `core`.
- Migration LUÔN chạy bằng vai trò `postgres` (`ALTER DEFAULT PRIVILEGES` không có
  `FOR ROLE`). Không sửa file migration đã chạy — chỉ thêm file mới.
- Định nghĩa chỉ số chỉ sống trong `mart/`. **Một khái niệm, một công thức.**
- Mốc thời gian là `mart.moc_thoi_gian.hom_nay`, KHÔNG BAO GIỜ `current_date`.
- Mã (`*コード`) là TEXT. Tiền luôn là số nguyên yên; số lượng có thập phân.
- Khách ※廃業※ không vào danh sách gọi lại (`mart.khach_nhom_viec` đã lo, migration 016).
- Mọi mã hoá bằng màu phải kèm một thứ ĐỌC ĐƯỢC.
- View nào bị tham chiếu nhiều hơn một lần trong CÙNG một câu lệnh thì phải vào CTE
  `AS MATERIALIZED` ghi tường minh.
- Lọc theo `salesperson_code` là mặc định tiện dụng, KHÔNG phải hàng rào bảo mật.
  Không thêm kiểm quyền.
- `kome/web/app.py` KHÔNG được nhập `kome.pipeline`/pandas ở mức ngoài cùng.
- Ngân sách: `/ban-do` **≤ 2 lượt hỏi**, đếm lúc chạy.
- Chạy test ở TIỀN CẢNH bằng `python -u -m pytest`, không pipe qua `tail`.
- Mốc test hiện tại trên `master`: **388 xanh**.

---

## Task 1: Migration `025_ban_do_tinh.sql`

**Files:**
- Tạo: `db/migrations/025_ban_do_tinh.sql`
- Test: `tests/test_ban_do.py` (mới)

**Interfaces:**
- Consumes: `mart.khach_360` (`customer_code`, `prefecture`, `salesperson_code`),
  `mart.hang_doanh_thu` (`customer_code`, `dt_12t`), `mart.khach_nhom_viec`
  (`customer_code`, `nhom`).
- Produces:
  - `core.dim_prefecture(ma_jis text PK, ten text UNIQUE, ten_latin text, ten_ngan text, vung text, hang_luoi int, cot_luoi int)`
  - `mart.khach_theo_tinh(prefecture text, salesperson_code text, so_khach bigint, doanh_thu_12t bigint, can_goi bigint)` — một dòng mỗi cặp (tỉnh, người phụ trách).

- [ ] **Bước 1: viết test đỏ trước** — `tests/test_ban_do.py`:

```python
"""Đợt 4c — bảng tra 47 tỉnh và view gộp theo tỉnh."""
import pytest


def test_dim_prefecture_du_47_tinh(conn):
    assert conn.execute("SELECT count(*) FROM core.dim_prefecture").fetchone()[0] == 47


def test_ma_jis_du_01_den_47_khong_thieu_khong_trung(conn):
    ma = [r[0] for r in conn.execute(
        "SELECT ma_jis FROM core.dim_prefecture ORDER BY ma_jis").fetchall()]
    assert ma == [f"{i:02d}" for i in range(1, 48)]


def test_khong_hai_tinh_cung_mot_o_luoi(conn):
    # Hai tỉnh chồng ô thì một tỉnh biến mất khỏi bản đồ mà không ai thấy —
    # trang vẫn vẽ ra bình thường, chỉ thiếu đúng một ô.
    trung = conn.execute("""
        SELECT hang_luoi, cot_luoi, count(*) FROM core.dim_prefecture
        GROUP BY 1, 2 HAVING count(*) > 1""").fetchall()
    assert trung == []


def test_moi_vung_la_mot_khoi_lien_nhau(conn):
    # Kề 8 hướng (kể cả chéo). Một vùng bị vỡ làm đôi trên lưới là lưới đặt sai,
    # và mắt người đọc bản đồ sẽ thấy trước khi test thấy.
    o = {}
    for vung, h, c in conn.execute(
            "SELECT vung, hang_luoi, cot_luoi FROM core.dim_prefecture").fetchall():
        o.setdefault(vung, set()).add((h, c))
    for vung, cells in o.items():
        dau = next(iter(cells))
        tham, hang_doi = {dau}, [dau]
        while hang_doi:
            h, c = hang_doi.pop()
            for dh in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    ke = (h + dh, c + dc)
                    if ke in cells and ke not in tham:
                        tham.add(ke)
                        hang_doi.append(ke)
        assert tham == cells, f"vùng {vung} bị vỡ thành nhiều khối rời"


def test_ten_tinh_khop_chuoi_OBC_that(conn, batch):
    # Khoá nối là chính chuỗi tên tỉnh OBC ghi. Sai một ký tự là tỉnh đó rỗng
    # vĩnh viễn trên bản đồ, và không có lỗi nào nổ ra.
    conn.execute("""
        INSERT INTO core.dim_customer
            (customer_code, customer_name, prefecture, is_current, valid_from, batch_id)
        VALUES ('BD01', 'Quan an Tokyo', '東京都', true, '2026-01-01', %s)""", (batch,))
    assert conn.execute(
        "SELECT count(*) FROM core.dim_prefecture WHERE ten = '東京都'").fetchone()[0] == 1


def test_khach_theo_tinh_khong_dem_trung_khi_khach_o_NHIEU_nhom_viec(conn, batch):
    # mart.khach_nhom_viec cho phép MỘT khách thuộc NHIỀU nhóm ('im' và 'tut'
    # cùng lúc). LEFT JOIN thẳng vào nó sẽ nhân đôi dòng khách và thổi phồng
    # `so_khach` của tỉnh. Phải dùng EXISTS — đúng nếp migration 022.
    #
    # Không gieo một khách "vừa im vừa tụt" (dựng được nhưng mong manh: nó phụ
    # thuộc hai công thức khác nhau cùng khớp). Khẳng định bất biến TỔNG, thứ
    # vỡ ngay khi có BẤT KỲ dòng nào bị nhân lên, dù vì nhóm nào.
    _ho_so_khach(conn, batch, "BD01", "Quan A", prefecture="東京都")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    tong_view = conn.execute(
        "SELECT coalesce(sum(so_khach), 0) FROM mart.khach_theo_tinh").fetchone()[0]
    tong_that = conn.execute("SELECT count(*) FROM mart.khach_360").fetchone()[0]
    assert tong_view == tong_that
```

**Ba hàm gieo dữ liệu** dùng chung cho cả ba task: chép nguyên `_ho_so_khach`, `_mua`
và hằng `HOM_NAY` từ `tests/test_khach_hang.py` (đọc file đó trước khi viết — chúng
đã có sẵn ở đầu file và đã được dùng ở ba bộ test khác). Fixture `conn`/`batch` lấy từ
`tests/conftest.py`; `batch` là một **factory nhận số hiệu lô**, không phải một giá trị.

- [ ] **Bước 2: chạy để thấy nó ĐỎ**

Chạy: `python -u -m pytest tests/test_ban_do.py -v`
Mong đợi: FAIL — `relation "core.dim_prefecture" does not exist`.

- [ ] **Bước 3: viết migration**

Mở đầu file bằng khối chú thích nêu **vì sao lưới ô chứ không phải bản đồ theo tỷ lệ**
(đặc tả §5.1, bốn lý do) và **vì sao bảng phải đủ 47 dòng** (§5.2). Viết như các
migration trước: chú thích giải thích HẬU QUẢ nếu làm sai, không chỉ mô tả code.

```sql
CREATE TABLE core.dim_prefecture (
    ma_jis     text PRIMARY KEY,
    ten        text NOT NULL UNIQUE,
    ten_latin  text NOT NULL,
    ten_ngan   text NOT NULL,
    vung       text NOT NULL,
    hang_luoi  int  NOT NULL,
    cot_luoi   int  NOT NULL,
    UNIQUE (hang_luoi, cot_luoi)
);
```

Gieo đúng 47 dòng sau, nguyên văn (cột theo thứ tự
`ma_jis, ten, ten_latin, ten_ngan, vung, hang_luoi, cot_luoi`):

```
01 北海道     Hokkaido   北海道   北海道      1 12
02 青森県     Aomori     青森     東北        2 11
03 岩手県     Iwate      岩手     東北        3 11
04 宮城県     Miyagi     宮城     東北        4 11
05 秋田県     Akita      秋田     東北        3 10
06 山形県     Yamagata   山形     東北        4 10
07 福島県     Fukushima  福島     東北        5 11
08 茨城県     Ibaraki    茨城     関東        6 12
09 栃木県     Tochigi    栃木     関東        6 11
10 群馬県     Gunma      群馬     関東        6 10
11 埼玉県     Saitama    埼玉     関東        7 10
12 千葉県     Chiba      千葉     関東        7 12
13 東京都     Tokyo      東京     関東        7 11
14 神奈川県   Kanagawa   神奈川   関東        8 10
15 新潟県     Niigata    新潟     中部        5 10
16 富山県     Toyama     富山     中部        6  9
17 石川県     Ishikawa   石川     中部        6  8
18 福井県     Fukui      福井     中部        7  7
19 山梨県     Yamanashi  山梨     中部        8  9
20 長野県     Nagano     長野     中部        7  9
21 岐阜県     Gifu       岐阜     中部        7  8
22 静岡県     Shizuoka   静岡     中部        9  9
23 愛知県     Aichi      愛知     中部        8  8
24 三重県     Mie        三重     近畿        9  8
25 滋賀県     Shiga      滋賀     近畿        8  7
26 京都府     Kyoto      京都     近畿        8  6
27 大阪府     Osaka      大阪     近畿        9  7
28 兵庫県     Hyogo      兵庫     近畿        9  6
29 奈良県     Nara       奈良     近畿       10  6
30 和歌山県   Wakayama   和歌山   近畿       10  7
31 鳥取県     Tottori    鳥取     中国        8  5
32 島根県     Shimane    島根     中国        9  4
33 岡山県     Okayama    岡山     中国        9  5
34 広島県     Hiroshima  広島     中国       10  4
35 山口県     Yamaguchi  山口     中国       10  3
36 徳島県     Tokushima  徳島     四国       11  5
37 香川県     Kagawa     香川     四国       10  5
38 愛媛県     Ehime      愛媛     四国       11  4
39 高知県     Kochi      高知     四国       12  4
40 福岡県     Fukuoka    福岡     九州沖縄   11  2
41 佐賀県     Saga       佐賀     九州沖縄   12  2
42 長崎県     Nagasaki   長崎     九州沖縄   12  1
43 熊本県     Kumamoto   熊本     九州沖縄   12  3
44 大分県     Oita       大分     九州沖縄   11  3
45 宮崎県     Miyazaki   宮崎     九州沖縄   13  3
46 鹿児島県   Kagoshima  鹿児島   九州沖縄   13  2
47 沖縄県     Okinawa    沖縄     九州沖縄   14  1
```

Lưới là **14 hàng × 12 cột**. `ten` phải khớp CHÍNH XÁC chuỗi OBC ghi (đã đo trên CSDL
thật: cả 47 đều có hậu tố 都/道/府/県, `北海道` không có hậu tố nào thêm).

Rồi view gộp:

```sql
CREATE VIEW mart.khach_theo_tinh AS
SELECT k.prefecture,
       k.salesperson_code,
       count(*)                       AS so_khach,
       coalesce(sum(h.dt_12t), 0)::bigint AS doanh_thu_12t,
       count(*) FILTER (
           WHERE EXISTS (SELECT 1 FROM mart.khach_nhom_viec v
                          WHERE v.customer_code = k.customer_code
                            AND v.nhom = 'im')) AS can_goi
FROM mart.khach_360 k
LEFT JOIN mart.hang_doanh_thu h ON h.customer_code = k.customer_code
GROUP BY 1, 2;
```

**Ba điều BẮT BUỘC trong view này, kèm chú thích tại chỗ:**

1. `can_goi` dùng **`EXISTS`**, KHÔNG `LEFT JOIN mart.khach_nhom_viec`. Một khách có
   thể thuộc NHIỀU nhóm cùng lúc (chú thích của migration 020 nói rõ), nên JOIN sẽ
   nhân dòng khách lên và thổi phồng cả `so_khach` lẫn `doanh_thu_12t` của tỉnh. Đây
   đúng là hình mẫu migration 022.
2. Doanh thu ĐỌC `mart.hang_doanh_thu.dt_12t` — nơi "doanh thu 12 tháng" đã được định
   nghĩa một lần. KHÔNG tự viết lại `sum(...) WHERE sales_date > hom_nay - 365`, và
   KHÔNG dùng `khach_360.doanh_thu_thuan` (đó là doanh thu **toàn bộ lịch sử**, một
   con số khác hẳn mang cái tên rất dễ nhầm).
3. Khách ※廃業※ **được đếm** ở `so_khach` và `doanh_thu_12t` nhưng **không** ở
   `can_goi` — `khach_nhom_viec` đã tự loại họ (migration 016), nên không được thêm
   cổng nào nữa ở đây.

Thêm `COMMENT ON TABLE`/`COMMENT ON COLUMN` cho cả bảng lẫn view, theo nếp các
migration trước.

- [ ] **Bước 4: chạy test cho xanh**

Chạy: `python -u -m pytest tests/test_ban_do.py -v`
Mong đợi: PASS.

- [ ] **Bước 5: chạy cả bộ**

Chạy: `python -u -m pytest -q --ignore=tests/test_roles.py --ignore=tests/test_migrate.py`
rồi `python -u -m pytest -q tests/test_roles.py tests/test_migrate.py`
Mong đợi: 388 + số test mới, không test cũ nào đỏ.

- [ ] **Bước 6: commit** (thông điệp chỉ ASCII, không dấu tiếng Việt, không backtick).

---

## Task 2: `kome/ban_do.py`

**Files:**
- Tạo: `kome/ban_do.py`
- Test: `tests/test_ban_do.py` (nối thêm)

**Interfaces:**
- Consumes: `core.dim_prefecture`, `mart.khach_theo_tinh` (Task 1).
- Produces:
  - `CHI_SO: dict[str, str]` — ba khoá `"khach"` / `"doanh_thu"` / `"can_goi"` ánh xạ
    sang nhãn tiếng Việt hiện trên trang.
  - `O` — dataclass đóng băng một ô: `ma_jis, ten, ten_ngan, ten_latin, vung, hang, cot, so_khach, doanh_thu, can_goi, gia_tri, bac, x, y`.
  - `TrangBanDo` — dataclass đóng băng: `o: list[O]`, `vung: list[dict]`,
    `bang: list[O]`, `chu_giai: list[dict]`, `khong_ro_tinh: int`,
    `tong: dict`, `chi_so: str`, `rong: int`, `cao: int`.
  - `ban_do(conn, sale: str | None = None, chi_so: str = "khach") -> TrangBanDo`

- [ ] **Bước 1: viết test đỏ trước.** Bốn test, mỗi cái khoá một bất biến của đặc tả §8:

```python
from kome.ban_do import ban_do


def _hai_tinh(conn, batch):
    """Hai khách ở hai tỉnh khác nhau — nền chung của ba test dưới."""
    _ho_so_khach(conn, batch, "BD01", "Quan Tokyo", prefecture="東京都")
    _ho_so_khach(conn, batch, "BD02", "Quan Osaka", prefecture="大阪府")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    _mua(conn, batch, "BD02", HOM_NAY - timedelta(days=5))


def test_du_47_o_ke_ca_tinh_khong_co_khach(conn, batch):
    # LEFT JOIN từ dim_prefecture, KHÔNG group by trên khách. Gieo khách ở đúng
    # hai tỉnh; bản đồ vẫn phải có đủ 47 ô, 45 ô trong đó mang số 0.
    _hai_tinh(conn, batch)
    t = ban_do(conn)
    assert len(t.o) == 47
    assert sum(1 for o in t.o if o.so_khach == 0) == 45


def test_tinh_gia_tri_0_khac_bac_thap_nhat(conn, batch):
    # "Không có khách" khác "ít khách". Cùng màu là bản đồ nói dối về vùng trắng.
    _hai_tinh(conn, batch)
    t = ban_do(conn)
    o = {x.ten: x for x in t.o}
    assert o["東京都"].so_khach == 1 and o["北海道"].so_khach == 0
    assert o["北海道"].bac == 0
    assert o["東京都"].bac >= 1


def test_khach_khong_co_tinh_khong_bi_danh_roi_im_lang(conn, batch):
    # Đúng 1/1.710 khách thật rơi vào ca này. Nó phải hiện thành một con số,
    # không phải biến mất giữa bản đồ và tổng.
    _hai_tinh(conn, batch)
    _ho_so_khach(conn, batch, "BD03", "Khong ro tinh", prefecture="")
    _mua(conn, batch, "BD03", HOM_NAY - timedelta(days=5))
    t = ban_do(conn)
    assert t.khong_ro_tinh == 1
    assert sum(x.so_khach for x in t.o) + t.khong_ro_tinh == t.tong["so_khach"]


def test_ban_do_khong_qua_2_truy_van(conn, batch):
    # Đếm LÚC CHẠY, không bằng AST: một truy vấn nằm trong vòng lặp hay trong
    # một nhánh `if` thì AST đếm là một, còn trang thật chạy bốn mươi bảy lượt.
    _hai_tinh(conn, batch)
    dem = 0
    that = conn.execute

    def _dem(*a, **kw):
        nonlocal dem
        dem += 1
        return that(*a, **kw)

    conn.execute = _dem
    try:
        ban_do(conn)
    finally:
        conn.execute = that
    assert dem <= 2, f"{dem} lượt hỏi, trần là 2"
```

Cách đếm lượt hỏi ở trên phải khớp cách ba bộ test hiện có làm (`test_khach_hang.py`,
`test_san_pham.py` đều đã có test đếm) — **đọc một trong hai và dùng lại đúng cơ chế
đó**, đừng dựng cơ chế thứ hai.

- [ ] **Bước 2: chạy để thấy ĐỎ.** Mong đợi: `ModuleNotFoundError: kome.ban_do`.

- [ ] **Bước 3: viết module.**

Truy vấn A (một lượt) lấy 47 dòng đã nối sẵn:

```sql
WITH tinh AS MATERIALIZED (
    SELECT s.prefecture, sum(s.so_khach) AS so_khach,
           sum(s.doanh_thu_12t) AS doanh_thu, sum(s.can_goi) AS can_goi
      FROM mart.khach_theo_tinh s
     WHERE true {dk_sale}
     GROUP BY s.prefecture
)
SELECT p.ma_jis, p.ten, p.ten_latin, p.ten_ngan, p.vung, p.hang_luoi, p.cot_luoi,
       coalesce(t.so_khach, 0), coalesce(t.doanh_thu, 0), coalesce(t.can_goi, 0)
  FROM core.dim_prefecture p
  LEFT JOIN tinh t ON t.prefecture = p.ten
 ORDER BY p.ma_jis
```

**`LEFT JOIN` là chỗ phải canh:** đổi thành `JOIN` (hoặc để `dim_prefecture` ở vế
phải) là bốn mươi lăm tỉnh biến mất khi lọc theo một người phụ trách, và trang vẫn vẽ
ra bình thường — chỉ thiếu ô. Test §8-1 khoá đúng chỗ này.

Truy vấn B (một lượt) lấy phần KHÔNG thuộc tỉnh nào và tổng toàn công ty — gộp bằng
`UNION ALL` trong đúng một câu, theo nếp `tong_quan_danh_ba`:

```sql
SELECT 'khong_ro'::text, coalesce(sum(so_khach),0), coalesce(sum(doanh_thu_12t),0), coalesce(sum(can_goi),0)
  FROM mart.khach_theo_tinh s
 WHERE coalesce(s.prefecture, '') NOT IN (SELECT ten FROM core.dim_prefecture) {dk_sale}
UNION ALL
SELECT 'tong', coalesce(sum(so_khach),0), coalesce(sum(doanh_thu_12t),0), coalesce(sum(can_goi),0)
  FROM mart.khach_theo_tinh s WHERE true {dk_sale}
```

`dk_sale` dựng MỘT LẦN bằng một hàm nhỏ rồi dùng lại — chép tay hai bản là hai bộ lọc
sẽ trôi khỏi nhau (đúng lỗi `_vi_tu` ở `kome/khach_hang.py` né được).

Rồi trong Python:

- `gia_tri` của mỗi ô = cột ứng với `chi_so` đang chọn.
- **Bậc màu:** 0 → `bac = 0` (màu "trống", riêng). Các ô còn lại xếp tăng dần rồi chia
  `ntile(5)` bằng tay trong Python (dữ liệu đã nằm sẵn trong bộ nhớ, không cần thêm
  một lượt hỏi) → `bac` 1..5. Chú thích tại chỗ: chia theo phân vị chứ không theo
  khoảng đều, vì 東京都 kéo trần lên khiến bốn mươi tỉnh còn lại rơi hết vào bậc thấp
  nhất và bản đồ thành một màu (đặc tả §5.5).
- **Toạ độ SVG:** `x = (cot - 1) * (O_RONG + KHE)`, `y = (hang - 1) * (O_CAO + KHE)`;
  `rong`/`cao` tính từ max cột/hàng, không viết cứng — sửa lưới trong CSDL thì SVG đi
  theo.
- `chu_giai`: 5 bậc kèm khoảng giá trị THẬT của từng bậc (min–max), không phải nhãn
  "thấp/cao" suông.
- `vung`: gộp 8 vùng theo đúng thứ tự địa lý bắc→nam, không theo bảng chữ cái.
- `bang`: 47 ô xếp giảm dần theo `gia_tri`, rồi theo `ma_jis` để thứ tự ổn định khi
  bằng nhau.

`chi_so` không nằm trong `CHI_SO` thì rơi về `"khach"` — đừng nổ 500 vì một tham số URL
gõ sai; trang phải luôn mở được.

- [ ] **Bước 4: chạy test cho xanh.** `python -u -m pytest tests/test_ban_do.py -v`

- [ ] **Bước 5: chạy cả bộ** (hai lệnh như Task 1, bước 5).

- [ ] **Bước 6: commit.**

---

## Task 3: Trang `/ban-do`

**Files:**
- Tạo: `kome/web/templates/ban_do.html`
- Sửa: `kome/web/app.py` (thêm route), `kome/web/templates/_nav.html` (thêm mục)
- Test: `tests/test_ban_do.py` (nối thêm), `tests/test_giao_dien.py` (nếu có test canh
  cấu trúc điều hướng — đọc trước khi sửa `_nav.html`)

**Interfaces:**
- Consumes: `ban_do(conn, sale, chi_so)` và `TrangBanDo` (Task 2); `open_app_conn` và
  `request.state.nguoi` của `kome/web/app.py`; hằng `KH.NV_MOI_NGUOI` của
  `kome/khach_hang.py` cho ô lọc người phụ trách.
- Produces: đường dẫn `/ban-do`, tên trang `'ban-do'` cho `_nav.html`.

- [ ] **Bước 1: viết test đỏ trước.** Bốn test:

```python
import re


def _o_svg(html: str) -> list[str]:
    """Nội dung từng ô của bản đồ, cắt theo <g class="o">…</g>.

    Cắt theo Ô chứ không quét cả TRANG: đoạn văn giải thích phía trên bản đồ
    có nhắc tên tỉnh và có cả con số, nên một khẳng định quét cả trang sẽ xanh
    kể cả khi trong SVG không còn chữ nào — đúng lỗi đã bắt ở đợt 4b.
    """
    return re.findall(r'<g class="o"[^>]*>(.*?)</g>', html, re.S)


def test_moi_o_co_con_so_doc_duoc_chu_khong_chi_co_mau(conn, client, batch):
    # Bất biến _chung.html:76-77: mã hoá bằng màu phải kèm thứ đọc được.
    _hai_tinh(conn, batch)
    html = client.get("/ban-do").text
    o = _o_svg(html)
    assert len(o) == 47
    for noi_dung in o:
        assert re.search(r">\s*\d[\d.,]*\s*<", noi_dung), noi_dung


def test_bam_o_dan_toi_danh_ba_da_loc_dung_tinh(conn, client, batch):
    # Tên tỉnh là tiếng Nhật -> href phải được mã hoá URL. Quên `|urlencode`
    # thì liên kết vẫn trông đúng trên trang mà bấm vào ra danh sách rỗng.
    _hai_tinh(conn, batch)
    html = client.get("/ban-do").text
    assert "/khach-hang?tinh=%E6%9D%B1%E4%BA%AC%E9%83%BD" in html


def test_loc_nv_co_ca_ban_do_lan_bang_lan_dai_vung(conn, client, batch):
    # Một bộ lọc co bản đồ mà không co bảng là hai con số khác nhau cho cùng
    # một câu hỏi, trên cùng một màn hình.
    _ho_so_khach(conn, batch, "BD01", "Cua A", prefecture="東京都",
                 salesperson_code="0102")
    _ho_so_khach(conn, batch, "BD02", "Cua B", prefecture="大阪府",
                 salesperson_code="0104")
    _mua(conn, batch, "BD01", HOM_NAY - timedelta(days=5))
    _mua(conn, batch, "BD02", HOM_NAY - timedelta(days=5))
    html = client.get("/ban-do?nv=0102").text
    o = {t: n for t, n in re.findall(
        r'<g class="o" data-tinh="([^"]+)"[^>]*>.*?class="so">([\d.,]+)<', html, re.S)}
    assert o["東京都"] == "1" and o["大阪府"] == "0"
    # 大阪府 vẫn phải còn trên bản đồ (ô số 0), không được biến mất khi lọc —
    # `len(o) == 47` là khẳng định thật, còn `"大阪府" in html` thì không: tên
    # tỉnh nằm sẵn trong bảng 47 dòng nên chuỗi đó luôn có mặt.
    assert len(o) == 47
    # Dải vùng cũng phải co: 関東 còn 1 khách, 近畿 còn 0.
    vung = dict(re.findall(r'<li class="vung" data-vung="([^"]+)">[^<]*<b>(\d+)</b>', html))
    assert vung["関東"] == "1" and vung["近畿"] == "0"


def test_trang_ban_do_khong_qua_2_truy_van(conn, client, batch):
    # Cùng cơ chế đếm với test của tầng Python, nhưng đo TRANG: route có thể
    # lỡ thêm một lượt hỏi ngoài hàm `ban_do` (vd danh sách người phụ trách).
    ...
```

Ô SVG phải mang `data-tinh="<tên tỉnh>"` và con số nằm trong một phần tử
`class="so"` — hai móc này là thứ test bám vào; đổi chúng thì phải đổi test.

Test cuối (`_khong_qua_2_truy_van` mức trang) dựng bằng đúng cơ chế mà
`tests/test_san_pham.py` dùng cho `/kho-hang` — **đọc test đó và dùng lại**, đừng
dựng cơ chế thứ ba.

- [ ] **Bước 2: chạy để thấy ĐỎ** (404 vì chưa có route).

- [ ] **Bước 3: viết template + route + nav.**

Template dựng SVG thuần từ dữ liệu Python — **không một dòng JS, không tài nguyên
ngoài**. Đọc `kome/web/templates/san_pham_360.html` và `khach_360.html` trước để theo
đúng cách ba biểu đồ hiện có dựng SVG.

Bố cục trên xuống:
1. Tiêu đề + một đoạn nói rõ **đây là lưới ô, không phải bản đồ theo tỷ lệ**, và vì sao
   (ô bằng nhau để tỉnh đông khách nhất không thành một chấm). Người đọc phải biết mình
   đang nhìn cái gì.
2. Dải ba nút chọn chỉ số (liên kết, không phải JS).
3. Ô lọc người phụ trách + liên kết bỏ lọc, đúng nếp `/khach-hang`.
4. SVG bản đồ 47 ô. Mỗi ô là `<a href="/khach-hang?tinh=…">` bọc `<g>` chứa `<rect>` +
   tên tỉnh + con số. Ô giá trị 0 mang màu "trống" và vẫn bấm được.
5. Chú giải 5 bậc kèm khoảng số thật của từng bậc + ô "trống (0)".
6. Dải 8 vùng.
7. Bảng 47 dòng.
8. Dòng "(không rõ tỉnh): N khách" — luôn hiện, kể cả khi N = 0.

Route đọc bằng `open_app_conn` (trang chỉ đọc → vai trò `kome_app`), lấy `sale` mặc
định từ `request.state.nguoi` như `/khach-hang`, nhận `?nv=` và `?tat_ca=1`.

`_nav.html`: thêm `<a href="/ban-do">Bản đồ</a>` vào nhóm KHÁCH HÀNG, ngay sau
"Cần xử lý".

- [ ] **Bước 4: chạy test cho xanh.**

- [ ] **Bước 5: chạy cả bộ** (hai lệnh như Task 1, bước 5).

- [ ] **Bước 6: commit.**

---

## Task 4: Tài liệu

**Files:** Sửa `CLAUDE.md`

- [ ] **Bước 1:** thêm `/ban-do` vào bảng "Các trang của web app", cột nguồn ghi
      `core.dim_prefecture`, `mart.khach_theo_tinh`.

- [ ] **Bước 2:** thêm hai bất biến:

```markdown
**Bất biến:** bản đồ tỉnh nối từ `core.dim_prefecture` **LEFT JOIN** sang số liệu
khách, KHÔNG `GROUP BY` trên khách rồi vẽ. Gom theo khách thì tỉnh không có khách nào
biến mất khỏi bản đồ — mà "chúng ta chưa có mặt ở tỉnh này" đúng là một trong những
điều một tấm bản đồ bán hàng phải nói ra. Cả 47 tỉnh hôm nay đều có khách nên lỗi này
KHÔNG lộ ra trên dữ liệu thật; nó chỉ lộ khi lọc theo một người phụ trách, và lúc đó
thì lộ ngay ở gần bốn mươi tỉnh. Có test canh.

**Bất biến:** `mart.khach_theo_tinh.can_goi` đếm bằng `EXISTS` trên
`mart.khach_nhom_viec`, KHÔNG `LEFT JOIN` nó. Một khách có thể thuộc NHIỀU nhóm việc
cùng lúc, nên JOIN nhân dòng khách lên và thổi phồng cả `so_khach` lẫn `doanh_thu_12t`
của tỉnh — một tỉnh có nhiều khách vừa `im` vừa `tut` sẽ báo nhiều khách hơn số khách
nó thật sự có. Cùng hình mẫu migration `022`.
```

- [ ] **Bước 3:** thêm vào "Bẫy đã biết" mục 7: `prefecture` của OBC là tên tỉnh chuẩn
      có hậu tố 都/道/府/県, đủ cả 47 tỉnh, và **chỉ 1 trên 1.710 khách** bỏ trống —
      cột sạch nhất đã gặp, nên khoá nối là chính chuỗi tên, không cần lớp chuẩn hoá.
      Đổi một ký tự trong `core.dim_prefecture.ten` là tỉnh đó rỗng vĩnh viễn trên bản
      đồ mà không lỗi nào nổ ra.

- [ ] **Bước 4:** chạy cả bộ, commit.

---

## Tự soát kế hoạch

| Mục đặc tả | Task |
|---|---|
| §4.1 (1) bản đồ 47 ô | 1, 2, 3 |
| §4.1 (2) ba chỉ số | 2, 3 |
| §4.1 (3) chú giải 5 bậc | 2, 3 |
| §4.1 (4) bảng 47 dòng | 2, 3 |
| §4.1 (5) dải 8 vùng | 1, 2, 3 |
| §4.1 (6) bấm ô → danh bạ | 3 |
| §4.1 (7) lọc theo người phụ trách | 2, 3 |
| §5.2 đủ 47 dòng kể cả tỉnh 0 khách | 1, 2 |
| §5.3 vị trí lưới là dữ liệu | 1 |
| §5.4 một khách một tỉnh, không đếm trùng | 1 |
| §5.5 thang màu theo phân vị | 2 |
| §5.6 ngân sách ≤ 2 lượt hỏi | 2, 3 |
| §8 bảng 11 test | 1, 2, 3 |
| §9 tài liệu | 4 |
