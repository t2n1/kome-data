# Giai đoạn 0 — Các quyết định đã ra trong lúc thực hiện

Tài liệu này ghi lại **mọi quyết định mà AI tự ra thay chủ sở hữu** khi thực hiện Giai đoạn 0,
kèm lý do và **cái giá phải trả nếu quyết định đó sai**.

Mục đích: chủ sở hữu đọc lại và sửa những chỗ quyết sai; và phiên AI hai năm sau biết vì sao
mọi thứ được làm như hiện tại, thay vì phá đi thứ nó không hiểu.

Nguồn: nhật ký thực hiện (`.superpowers/sdd/`), đã bị xoá sau khi gộp nhánh.

Đặc tả: [`../superpowers/specs/2026-09-16-kome-data-platform-design.md`](../superpowers/specs/2026-09-16-kome-data-platform-design.md)
Kế hoạch: [`../superpowers/plans/2026-09-16-giai-doan-0-nen-du-lieu.md`](../superpowers/plans/2026-09-16-giai-doan-0-nen-du-lieu.md)

---

**Ruling A: sửa kế hoạch — thay `df._append` bằng `pd.concat`.**
Vì: `DataFrame.append` đã bị bỏ ở pandas 2.0, `_append` là API riêng tư không được bảo đảm ở pandas 3.0 (bản đang cài). Test sẽ lỗi `AttributeError`.
Giá nếu sai: không có — `pd.concat` là API công khai, tương đương.

**Ruling B: sửa kế hoạch — thêm fixture `batch` vào `tests/conftest.py`.**
Vì: mọi `fact_*` và `dim_customer` có `batch_id ... REFERENCES meta.ingest_batch(batch_id)`, nhưng test của Task 7/9/10/11 truyền `batch_id=1,2,3` mà không tạo dòng nào trong `meta.ingest_batch` → vi phạm khoá ngoại, test fail toàn bộ. Bỏ khoá ngoại thì mất khả năng hoàn tác theo lô, nên giữ khoá ngoại và sửa test.
Giá nếu sai: không có — fixture chỉ thêm dữ liệu test.

**Ruling C: sửa kế hoạch — `create_app(db_url=None)` nhận URL, test truyền `DATABASE_URL_TEST`.**
Vì: test web như đang viết sẽ **kết nối vào CSDL thật**, và `conftest` thì `DROP SCHEMA ... CASCADE`. Đây là đường dẫn thẳng tới mất dữ liệu sản xuất. Không chấp nhận được ở bất kỳ mức nào.
Giá nếu sai: không có — thêm tham số tuỳ chọn, mặc định giữ nguyên hành vi cũ.

**Ruling D: giữ nguyên Task 13, ghi nhận rủi ro, không chặn.**
Vì: `CREATE ROLE` trên Supabase cần quyền cao; vai trò `postgres` của Supabase thường làm được nhưng chưa kiểm chứng. Task 13 là task cuối nên nếu hỏng cũng không chặn 12 task trước.
Giá nếu sai: Task 13 phải chuyển sang chạy tay trên SQL Editor của Supabase thay vì qua migration. Mất ~15 phút, không ảnh hưởng thiết kế.

**Ruling E: dispatch Task 1 ngay, dừng trước Task 2 để chờ `.env`.**
Vì: Task 1 không cần CSDL. Task 2 trở đi cần `DATABASE_URL_TEST` mà người dùng chưa cung cấp. Chạy tiếp mà không có sẽ fail hàng loạt và vô nghĩa.
Giá nếu sai: không có — chỉ là thứ tự thực hiện.

**Ruling F: finding 1 (`[build-system]` trong pyproject.toml) — code đứng vững, không sửa.**
Vì: chính lệnh dispatch của tôi cho phép thêm khối này nếu `pip install -e` thiếu build backend. Reviewer chỉ đọc brief nên không thấy chỉ thị đó. Đây là sai lệch tôi uỷ quyền, không phải lỗi.
Giá nếu sai: không có — setuptools.build_meta là backend chuẩn.

**Ruling G: finding 2 (`*.egg-info/` trong .gitignore) — code đứng vững, không sửa.**
Vì: lệnh dispatch cho phép append vào .gitignore. Rác build lọt vào git mới là lỗi.
Giá nếu sai: không có.

**Ruling H: finding 3 (.env.example thiếu dòng cảnh báo) — SỬA, một vòng fix.**
Vì: dòng đó mang cảnh báo an toàn thật ("KHÔNG commit .env"), không phải nhãn tên file. Ràng buộc toàn cục #5 nói mật khẩu không bao giờ vào git — file này tồn tại chính để nhắc điều đó.
Giá nếu sai: không có — thêm một dòng chú thích.

**Ruling I: ⚠️ RED-trước-GREEN không kiểm chứng được — bỏ qua, không phải thiếu sót.**
Vì: diff là ảnh chụp cuối, về bản chất không chứa bằng chứng thứ tự TDD. Không reviewer nào kiểm được từ diff. Không đưa vào vòng fix.
Giá nếu sai: nếu implementer bỏ bước RED thì test có thể là test giả (luôn xanh). Đã đọc test_smoke.py — nó assert thật trên `kome.__version__`, không phải test rỗng.

**Ruling J: dùng session pooler thay direct connection.**
Vì: `db.<ref>.supabase.co` chỉ có bản ghi IPv6, máy này không có IPv6 ra ngoài → timeout. `aws-0-ap-northeast-1.pooler.supabase.com:5432` có IPv4, kết nối được cả `/postgres` lẫn `/kome_test`. Cổng 6543 bị loại vì transaction pooler không chạy được migration.
Giá nếu sai: session pooler giới hạn số kết nối đồng thời thấp hơn direct. Với 3-8 người dùng thì dư.

**Ruling K: tôi tự chép sẵn fixture Excel thay vì để implementer làm.**
Vì: file gốc nằm trong OneDrive và đã gây `PermissionError` khi đọc trực tiếp (đã gặp lúc khảo sát). Implementer sẽ mất vài lượt để phát hiện. Đây là công việc chuẩn bị, không phải phần được review.
Giá nếu sai: không có — fixture là bản sao y nguyên, mã băm kiểm chứng được.

**Ruling L: Critical (fixture không được commit) — SỬA. Lỗi của tôi, không phải implementer.**
Vì: tôi thêm `*.xlsx` vào .gitignore ở Task 1 để chặn dữ liệu OBC, rồi ở Ruling K tự chép fixture vào mà không commit. Kết quả: repo không tự chạy test được. Vi phạm "nạp lại cùng file ra cùng kết quả" ở mức hạ tầng.
Cách sửa: thêm ngoại lệ HẸP `!tests/fixtures/*.xlsx` vào .gitignore, commit fixture 27KB.
Cân nhắc dữ liệu nhạy cảm: fixture chứa tồn kho thật ¥137.839.071 và tên sản phẩm. Repo là PRIVATE, và con số này vốn đã nằm trong đặc tả cũng như tiêu chí hoàn thành. Ngoại lệ chỉ mở cho `tests/fixtures/`, không mở cho toàn repo.
Giá nếu sai: nếu sau này repo chuyển sang public thì 27KB dữ liệu tồn kho lộ ra. Phải kiểm lại trước khi đổi chế độ hiển thị.

**Ruling M: Important (cột mã rỗng chưa được test) — SỬA.**
Vì: không phải lo xa. Khảo sát dữ liệu thật đã thấy `直送先` có dòng `得意先コード` để trống (ví dụ `PLE葉WALK浜北`). Nhánh `fillna("")` sẽ chạy thật ở Task 11, nhưng hiện chưa test nào chạm tới.
Giá nếu sai: nếu `fillna` xử lý sai, các dòng mã rỗng có thể gộp nhầm nhau ở bước dedup.

**Ruling N: Important (không có bằng chứng RED trước GREEN) — PARK, không sửa.**
Vì: giống Ruling I. Diff là ảnh chụp cuối, về bản chất không chứa thứ tự TDD. Đã đọc 4 test — đều assert số cụ thể (177, 137839071, 20, {0001,1002}), không có test rỗng.
Giá nếu sai: thấp — chất lượng test đã được kiểm chứng trực tiếp.

**Ruling O: Important 1 (mã rỗng lác đác lọt qua) — SỬA, nhưng KHÔNG chặn mọi cột mã rỗng.**
Vì: reviewer chứng minh 1 dòng `product_code` rỗng lọt hoàn toàn (`.all()` chỉ bắt ca rỗng TOÀN BỘ cột). Nhưng Ruling M đã xác định `直送先.得意先コード` rỗng là HỢP LỆ trong dữ liệu thật. Nên không thể chặn mọi cột mã rỗng.
Ranh giới đúng: rỗng ở cột thuộc **khoá** (`spec.keys`) là chặn — khoá rỗng làm hỏng dedup và upsert. Rỗng ở cột mã không phải khoá thì cho qua.
Giá nếu sai: nếu một file hợp lệ có khoá rỗng thật thì sẽ bị chặn oan, người dùng phải sửa trong OBC. Chấp nhận được — khoá rỗng vốn không có nghĩa.

**Ruling P: Important 2 (ngưỡng cổng 4 là hằng số cứng) — SỬA, đưa vào cấu hình theo từng loại file.**
Vì: cổng 4 sẽ áp cùng ngưỡng cho mọi loại file tương lai, trong khi `在庫一覧` (snapshot 177 dòng, ổn định) và `売上伝票データ` (~843 dòng/ngày, tăng vọt ngày chốt sổ cuối tháng) có biên độ biến động khác hẳn nhau. Để nguyên thì hoặc kêu oan liên tục, hoặc bỏ lọt bất thường thật.
Giá nếu sai: thêm 3 khoá cấu hình phải bảo trì. Rẻ hơn nhiều so với một cổng cảnh báo mà không ai tin.

**Ruling Q: Critical (hoàn tác xong không nạp lại được) — SỬA. Lỗi thiết kế trong kế hoạch của tôi.**
Vì: reviewer tái hiện thật trên kome_test: store -> undo -> store lại = UniqueViolation. `digest UNIQUE` vô điều kiện mâu thuẫn với `already_loaded()` vốn loại trừ lô đã huỷ. Nút "Hoàn tác lần nạp" ở Task 8 sẽ hỏng: hoàn tác xong không nạp lại được file đó nữa.
Cách sửa: migration MỚI (không sửa 002 đã chạy) đổi sang partial unique index `UNIQUE (digest) WHERE undone_at IS NULL`.
Giá nếu sai: nếu partial index không đủ, hai lô đã huỷ cùng digest có thể tồn tại song song — vô hại vì chúng đã bị đánh dấu huỷ.

**Ruling R: Important (không có test cho undo) — SỬA.**
Vì: `undo` là nửa còn lại của "nạp lại vô hại", tên chính của Task 5, mà không test nào chạm tới. Có test chu trình store->undo->store thì bug Critical trên đã lộ ngay ở Step 5.
Giá nếu sai: không có.

**Ruling S: dịch số thứ tự migration của các task sau lên 1.**
Vì: bản vá Critical chiếm số 003, mà 001 và 002 đã chạy nên không được sửa. Đã cập nhật kế hoạch: dim_date 004, inventory 005, dim_customer 006, fact_sales 007, masters 008, roles 009.
Giá nếu sai: nếu quên dịch ở một task, migration chạy sai thứ tự và khoá ngoại sẽ lỗi. Đã sửa thẳng trong file kế hoạch nên brief sinh ra tự đúng.

**Ruling T: Important (/undo hard-code một bảng) — SỬA NGAY, không hoãn.**
Vì: đây là finding load-bearing. Task 9/10/11 thêm dim_customer, fact_sales_line và 4 bảng master, đều có batch_id. Route /undo hiện chỉ xoá core.fact_inventory_daily, nên hoàn tác một lô bán hàng sẽ để lại dữ liệu mồ côi mà không ai biết. Hoãn thì ba task sau xây trên nền hỏng.
Cách sửa: bảng ánh xạ `spec_name -> danh sách bảng` đặt cạnh `LOADERS` trong pipeline.py, cộng một hàm `undo_batch()` dùng chung. Task sau chỉ thêm một dòng vào bảng ánh xạ.
Giá nếu sai: nếu quên thêm mục cho loader mới, hoàn tác sẽ sót bảng đó. Giảm rủi ro bằng test khẳng định mọi spec trong LOADERS đều có mục trong bảng ánh xạ.

**Ruling U: Important (không có test cho route /undo) — SỬA cùng vòng.**
Vì: câu lệnh DELETE viết thẳng trong route, không test nào chạm tới. Reviewer thử tay thì đúng, nhưng sửa sai tên bảng sau này sẽ không ai phát hiện.
Giá nếu sai: không có.

**Ruling V: tự tháo chặn Task 9, không chờ file xuất hằng ngày.**
Vì: bản `得意先全情報_20260813.xlsx` trong thư mục backup đã có đủ 317 cột, và đã xác minh có mặt cả 17 cột cần dùng (gồm 請求先コード ở vị trí 109 và 請求締日コード ở 111). Cấu trúc cột của bản xuất hằng ngày sẽ giống hệt; chỉ mẫu tên file là có thể khác, mà đó là một dòng trong YAML.
Giá nếu sai: nếu bản xuất hằng ngày đặt tên khác mẫu `得意先全情報_YYYYMMDD.xlsx` thì cổng 1 sẽ từ chối. Sửa bằng cách đổi `filename_pattern`, không đụng code.

**Ruling W: fixture khách hàng phải ẩn danh trước khi vào git.**
Vì: bản thật chứa tên, địa chỉ, điện thoại, email người phụ trách của 2.080 khách — là 個人情報 theo luật Nhật, và chính đặc tả §9.7 cảnh báo không chép nguyên khối ra ngoài khi không cần. Test chỉ cần cấu trúc cột và các mã, không cần danh tính.
Đã làm: `scripts/make_tokuisaki_fixture.py` xoá 26 cột định danh, đặt tên giả `KHACH_00001`. Kiểm chứng: 2.080 dòng, 317 cột, 0 dòng còn điện thoại/địa chỉ.
Giá nếu sai: nếu một cột định danh bị bỏ sót thì dữ liệu cá nhân lọt vào git. Đã kiểm bằng truy vấn đếm, và script chạy lại được để kiểm tra lại.

**Ruling X: chuẩn hoá NaN -> "" trước khi so sánh SCD2 — GIỮ, đây là sửa đúng.**
Vì: ô Excel trống đọc ra NaN, mà NaN != NaN, nên nếu không chuẩn hoá thì mỗi lần nạp lại file thật đều sinh 2.080 phiên bản mới — vi phạm thẳng luật bất biến #2. Implementer phát hiện khi chạy với fixture 2.080 dòng thật. Sai lệch so với brief nhưng là sai lệch đúng.
Giá nếu sai: không có.

**Ruling Y: bỏ `postcode` khỏi code_columns — SAI, phải khôi phục. Lỗi của tôi.**
Vì: implementer bỏ nó vì fixture có cột đó trống toàn bộ (sẽ bị cổng 3 chặn). Nhưng cột trống là do CHÍNH TÔI xoá khi ẩn danh, không phải tính chất của dữ liệu thật. Mã bưu chính Nhật CÓ số 0 đầu (Hokkaido 0xxxxxx) nên bắt buộc phải là TEXT.
Đã sửa script ẩn danh để giữ lại mã bưu chính, sinh lại fixture: 2.080 dòng, 2.072 có mã bưu chính, 0 dòng lộ điện thoại/địa chỉ.
Giá nếu sai: nếu mã bưu chính đọc thành số thì 8+ khách Hokkaido mất số 0 đầu.

**Ruling Z: hoàn tác lô SCD2 để lại khách không có phiên bản hiện hành — SỬA, load-bearing.**
Vì: `undo_batch` hiện chỉ DELETE. Với dim_customer, một lô vừa chèn phiên bản mới vừa ĐÓNG phiên bản cũ. Xoá phiên bản mới mà không mở lại phiên bản cũ thì khách đó không còn dòng nào `is_current = true` — biến mất khỏi mọi báo cáo mà không ai biết.
Giá nếu sai: nếu logic mở lại chọn nhầm phiên bản thì lịch sử bị lệch. Giảm rủi ro bằng test khẳng định sau hoàn tác, mỗi khách có đúng 1 dòng is_current.
Task 9: fix round 1/5 (2 addressed, 0 open — postcode về code_columns, undo SCD2 mở lại phiên bản trước; commits 057c4a4..a1112da)
Task 9: complete (commits 3eeb9e0..a1112da, review clean — 46 test; 29 mã bưu chính bắt đầu bằng 0 giữ nguyên)

**Ruling AA: Task 10 phải KHỬ TRÙNG theo 伝票No. + 明細行番号. Kế hoạch gốc của tôi không hề nhắc tới.**
Vì: đo trên file thật, `売上伝票データ` xuất MỖI DÒNG HÀNG HAI LẦN — một lần dưới 出荷内訳, một lần dưới 明細按分, cùng 金額 cùng 粗利益. 92.824 dòng thô, chỉ 53.942 khoá riêng biệt. Cộng thẳng thì doanh thu thành ¥844.305.488, gấp 2,16 lần thực tế. Đây là lỗi sẽ làm sai MỌI báo cáo mà không ai phát hiện.
Sau khử trùng: 53.942 dòng, 粗利益 = ¥114.315.334 khớp tuyệt đối mốc độc lập từ 売上明細表.
Giá nếu sai: nếu chọn nhầm dòng giữ lại thì số liệu lệch. Đã kiểm 4 cách lọc khác nhau, cả bốn cho cùng tổng 粗利益 — nên cách đơn giản nhất (giữ dòng đầu mỗi khoá) là đủ và đúng.

**Ruling AB: KHÔNG tự tính doanh thu thuần rồi coi là chuẩn.**
Vì: `売上明細表` nói ¥390.126.850, còn `金額 − 消費税額` từ `売上伝票データ` ra ¥390.130.067 — hai bản xuất của CHÍNH OBC lệch nhau ¥3.217 do làm tròn thuế ở mức khác nhau (theo hoá đơn vs theo dòng). Tương tự `粗利益` lệch ¥6.434 so với `(金額−消費税額) − 原価`.
Quyết định: lưu nguyên `金額` và `消費税額` như OBC ghi, định nghĩa doanh thu thuần ở lớp mart. Lấy `粗利益` của OBC làm chuẩn lợi nhuận vì khớp tuyệt đối. Đã sửa tiêu chí hoàn thành cho trung thực thay vì ép số cho khớp.
Giá nếu sai: báo cáo doanh thu có thể lệch ~0,0008% so với sổ OBC. Đã ghi rõ trong kế hoạch để người đọc báo cáo biết.

**Ruling AC: Important 1 (khử trùng chỉ so khoá, không so nội dung) — SỬA.**
Vì: hiện `drop_duplicates(keep="first")` bỏ dòng trùng khoá mà không kiểm hai bản có giống nhau không. Hôm nay cả 38.882 nhóm đều đồng nhất (reviewer đã kiểm), nhưng nếu OBC đổi cách xuất thì dòng khác giá trị sẽ bị bỏ âm thầm — không blocker, không cảnh báo. Đây đúng loại lỗi mà cả hệ thống này sinh ra để chặn.
Giá nếu sai: thêm một cảnh báo có thể kêu oan nếu OBC hợp lệ xuất hai dòng khác nhau cùng khoá. Chấp nhận được — cảnh báo không chặn.

**Ruling AD: Important 3 (lỗi ép ngày bị nuốt âm thầm) — SỬA.**
Vì: `errors="coerce"` biến ngày hỏng thành NaT. `billing_date` cho phép NULL nên mất dấu vĩnh viễn; `sales_date` thì đụng khoá ngoại và bung ngoại lệ thô SAU KHI `archive.store()` đã commit, để lại lô mồ côi. Phải chặn ở cổng 3 với thông báo rõ thay vì vỡ ở tầng CSDL.
Giá nếu sai: không có.

**Ruling AE: Important 2 (thiếu test hồi quy cho dedup) — SỬA, rẻ.**
Vì: reviewer tự kiểm tay thì đúng, nhưng không có gì giữ bất biến này khi code đổi về sau.

**Ruling AF: Important 4 (line_seq trong code_columns nhưng cột DB là integer) — chỉ ghi chú, không đổi.**
Vì: `明細行番号` là số thứ tự dòng, không phải mã nghiệp vụ, nên không có bẫy số 0 đầu. Để `integer` là đúng. Chỉ cần ghi rõ đây là ngoại lệ có chủ đích với luật #4 để người sau khỏi tưởng nhầm là sót.

**Ruling AG: số dòng bốn file master trong đặc tả SAI, thừa 1. Lỗi của tôi.**
Vì: script khảo sát ban đầu in `ws.max_row` của openpyxl, vốn TÍNH CẢ dòng tiêu đề. Thật: 商品データ 231, 仕入先 49, 直送先 1.832, 取引単価データ 395, 得意先全情報 2.080.
Implementer đo ra lệch -1 ở cả bốn file và TỪ CHỐI sửa số cho khớp, đi tìm nguyên nhân thật — đúng nguyên tắc.
Các mốc quan trọng không bị ảnh hưởng (177 tồn kho, 2.080 khách, 53.942 dòng bán) vì chúng được đếm theo dòng dữ liệu, không phải max_row. Đã sửa đặc tả.
Giá nếu sai: không có — chỉ là số liệu mô tả.

**Ruling AH: Important (không có test cho logic xoay bảng giá) — SỬA.**
Vì: `kome/loaders/price.py` là phần phức tạp nhất task này — ghép cặp 税抜/税込 theo từng mức giá. Ghép lệch một mức là sai giá toàn hệ thống, và chuỗi liên kết giá chính là nền của báo cáo "bán dưới giá" ở Giai đoạn 1. Reviewer viết test tạm thì code đúng, nhưng xoá test đi rồi — không còn gì giữ bất biến.
Giá nếu sai: không có.

**Ruling AI: Minor (lập luận chọn 単位原価 yếu) — chỉ sửa cách ghi, không đổi code.**
Vì: reviewer kiểm toàn bộ 395 dòng và thấy `単位原価` khớp `仕入原価（税抜）` ở 394/395 dòng (lệch 4 yên ở một dòng), còn `仕入原価（税込）` rỗng 100%. Nên kết luận chọn cột đúng, chỉ là ví dụ dùng để chứng minh không phân biệt được hai cột.
Giá nếu sai: không có — hai cột gần như trùng nhau.

**Ruling AJ: Task 12 bỏ `pg_dump`/`psql`, chuyển sang sao lưu thuần Python.**
Vì: máy này KHÔNG CÓ `pg_dump`, `psql`, `pg_restore` (đã kiểm). Cài PostgreSQL client chỉ để sao lưu là thêm một thứ nữa phải bảo trì cho công ty không có IT, và nó phải có mặt trên mọi máy chạy sao lưu.
Thiết kế mới: cấu trúc bảng đã nằm trong `db/migrations/*.sql` lưu git, nên chỉ sao lưu DỮ LIỆU — `COPY ... TO STDOUT WITH CSV HEADER` của psycopg 3, gom vào một file .zip kèm manifest.json (thời điểm, danh sách migration, số dòng từng bảng). Khôi phục = `apply_all()` rồi `COPY ... FROM STDIN`.
Được: không phụ thuộc chương trình ngoài, chạy trên mọi máy có Python, file nhỏ hơn.
Giá nếu sai: bản sao lưu không chứa cấu trúc, nên nếu mất cả repo git lẫn CSDL thì không dựng lại được schema. Chấp nhận được vì repo đã đẩy lên GitHub riêng tư, tức đã có hai bản ở hai nơi.
Đã sửa thẳng trong kế hoạch: interfaces, mã ops/backup.py, ops/restore_check.py, test, và lệnh chạy thử.

**Ruling AK: thêm cảnh báo sao lưu quá hạn lên trang kiểm tra sức khoẻ — SỬA.**
Vì: implementer tự nêu "sao lưu thủ công thì sẽ không ai chạy, và khi đó sao lưu không thực sự tồn tại".
Đúng, và đây là rủi ro vận hành thật với công ty không có IT. Reviewer đề xuất giải pháp hợp với
chủ trương của hệ thống: KHÔNG dựng tiến trình nền, mà hiện cảnh báo ngay trên trang /health —
trang nhân viên đã mở hằng ngày. Đây chính là nguyên tắc "sai phải thấy ngay" áp cho chính việc sao lưu.
Giá nếu sai: nếu ngưỡng 36 giờ quá chặt thì banner đỏ xuất hiện vào thứ Hai sau kỳ nghỉ dài, gây nhiễu.
Chấp nhận được — cảnh báo nhắc chứ không chặn.

**Ruling AL: Minor (docstring prune sai) — SỬA, một dòng.**
Vì: docstring ghi "giữ bản đầu mỗi tháng" nhưng logic thật giữ bản CUỐI tháng. Hành vi thật hợp lý hơn
(khớp chốt sổ), chỉ có lời chú thích sai. Mã này tôi viết trong brief nên là lỗi của tôi.
Task 12: fix round 1/5 (2 addressed, 0 open — cảnh báo sao lưu quá hạn trên /health, sửa docstring prune; commits d63f3e5..f0641eb)
Task 12: complete (commits e6fe7fa..f0641eb, review clean — 71 test)
  Reviewer kiểm 3 tình huống: không có file sao lưu / 40 giờ / 1 giờ — đúng cả ba; thư mục không tồn tại
  thì /health vẫn trả 200 kèm cảnh báo, không sập.
Chung: minor (deferred): bộ test giờ mất 5 phút 58 giây (71 test). Cần xử lý ở final review.
Task 13: implementer DONE (7afc8cc) — 73 test xanh, task cuối của Giai đoạn 0.

**Ruling AM: lỗi MỚI do đợt sửa đẻ ra — SỬA, dù quy trình nói không có đợt sửa thứ hai.**
Lỗi: hoàn tác lô SCD2 vừa "cập nhật tại chỗ" XOÁ HẲN khách hàng. customer.py ghi batch_id mới đè lên
dòng cũ; undo_batch DELETE theo batch_id nên xoá luôn dòng duy nhất, bước mở lại phiên bản trước không
còn gì để mở. Đã tái hiện: dim_customer rỗng.
Vì: đây là mất dữ liệu trong ĐÚNG kịch bản đầu bảng runbook (nạp nhầm file -> hoàn tác), và nó do chính
bản vá mục 4 tạo ra. Trước đợt sửa, kịch bản đó vẫn giữ được dòng cũ (kèm khoảng âm). Để nguyên thì bản
vá còn tệ hơn lỗi nó thay thế — đó là lý do tôi vượt quy tắc "chỉ một đợt sửa".
Giá nếu sai: thêm một vòng dispatch. Nhỏ hơn nhiều so với mất dữ liệu khách hàng khi người dùng làm đúng
theo sổ tay.

**Ruling AN: đưa câu kiểm CHECK vào runbook, không chỉ để trong báo cáo sửa lỗi.**
Vì: migration 010 có thể thất bại trên CSDL thật nếu ở đó đã có dòng valid_to < valid_from. Người chạy
migration đọc runbook chứ không đọc báo cáo nội bộ của agent.

---

## Sau Giai đoạn 0 — đưa trang lên mạng (2026-09-17)

**Ruling AO: Vercel chỉ chạy bản CHỈ ĐỌC; nạp dữ liệu ở lại máy trong công ty.**
Chủ sở hữu đã cân nhắc rồi quyết định giữ nguyên kiến trúc này.

Số đo thật, từ 17 tháng dữ liệu trong `core.fact_sales_line`, quy đổi kích thước file theo
`売上伝票データ_2026年5月~7月` = 101 MB / 92.824 dòng thô (OBC xuất mỗi dòng nghiệp vụ HAI lần:
`出荷内訳` + `明細按分`):

| Trường hợp | Số dòng | File ước tính | Qua giới hạn 4,5 MB của Vercel? |
|---|---:|---:|---|
| Ngày trung bình | 812 | 1,8 MB | ✅ lọt |
| Ngày bận nhất (2025-04-28) | 2.486 | 5,4 MB | ❌ |
| Ngày bận nhì (2025-07-28) | 2.344 | 5,1 MB | ❌ |
| Đối soát tháng (2025-07) | 26.369 | ~57 MB | ❌ gấp 13 lần |

Vì: đề xuất "xuất theo ngày thì file nhẹ, nạp thẳng trên Vercel được" đúng với ngày THƯỜNG nhưng
sai ở hai chỗ, và cả hai đều sai vào đúng lúc tệ nhất:
  1. Ngày đông nhất rơi vào CUỐI THÁNG (28/4, 28/7, 21/7) — tức hệ thống chạy ngon 20 ngày rồi
     hỏng đúng ngày chốt sổ, và người nạp sẽ tưởng mình thao tác sai.
  2. Đối soát tháng (~57 MB) là cái lưới DUY NHẤT bắt phiếu đỏ và phiếu bị sửa sau. Không có
     đường nào lách giới hạn cho nó.
  3. Ổ đĩa serverless là tạm → lớp `raw` (giữ nguyên file Excel gốc để đối chiếu về sau) không
     tồn tại được, bất kể file to hay nhỏ.

Lý lẽ thực tế đứng sau quyết định: file Excel SINH RA trên máy có cài OBC, và người xuất file lúc
13:30 đang ngồi ngay tại máy đó. Nạp từ xa chỉ có ích nếu muốn người khác nạp thay ở máy khác —
hiện không có nhu cầu đó.

Giá nếu sai: nếu sau này cần nạp từ xa thật, đường đi đã rõ — dựng cả ứng dụng lên VPS Vultr sẵn có
(ổ đĩa thật, không giới hạn 4,5 MB, không giới hạn thời gian chạy) rồi bỏ Vercel. Mã nguồn KHÔNG phải
sửa dòng nào: bỏ biến `VERCEL` là phần nạp tự hiện lại. Xem `docs/trien-khai-vercel.md` mục 6.

**Ruling AP: một mật khẩu chung, không phải tài khoản riêng từng người.**
Vì: mối nguy thật ở bước này là người lạ dò trúng địa chỉ, và mật khẩu chung chặn đúng mối nguy đó
mà không đẻ ra một bảng người dùng phải quản lý trong công ty không có nhân sự IT. Vé đăng nhập không
có kho phiên ở máy chủ (bắt buộc, để chạy được trên serverless), nên ĐỔI MẬT KHẨU là cách duy nhất
chặn người đã nghỉ việc — đã ghi vào `docs/runbook.md` và `docs/trien-khai-vercel.md` mục 5.
Giá nếu sai: khi cần biết AI đã xem gì (nhật ký truy cập, phân quyền theo vai trò) thì phải làm lại
phần đăng nhập. Chấp nhận được — hiện chưa ai cần.

**Ruling AQ: hồ sơ 360° hiển thị ĐẦY ĐỦ điện thoại và địa chỉ khách, kể cả trên bản công khai.**
Chủ sở hữu đã được trình bày ba phương án (giữ nguyên / che ở bản Vercel / bỏ hẳn trang Khách hàng
khỏi bản công khai) và chọn giữ nguyên.

Vì: phần lớn giá trị của công cụ này nằm ở chỗ dùng được NGOÀI THỊ TRƯỜNG — nhân viên mở trên điện
thoại khi đi thăm khách, thấy ngay số để gọi và địa chỉ để tới. Che đi thì trang vẫn "an toàn" nhưng
không còn giải quyết đúng việc người ta cần.

Điều này có nghĩa: danh bạ 2.080 khách hàng (tên, điện thoại, địa chỉ — 個人情報 theo luật Nhật) nằm
trên một địa chỉ Internet, cách nhau đúng MỘT mật khẩu chung. Hệ quả kéo theo, đã ghi vào runbook:
  * mật khẩu tối thiểu 12 ký tự là ràng buộc CỨNG trong mã (kome/web/bao_mat.py), không phải khuyến nghị
  * đổi mật khẩu mỗi khi có người nghỉ việc là bắt buộc, không phải tuỳ chọn
  * vé đăng nhập tự hết hạn sau 12 giờ

Giá nếu sai: nếu mật khẩu lọt ra ngoài thì mất cả danh bạ khách hàng, không chỉ mất số liệu tổng hợp.
Đường lùi đã rõ và rẻ: che một phần ở bản `chi_doc` (khoảng 15 phút), mã nguồn không phải đổi cấu trúc.
