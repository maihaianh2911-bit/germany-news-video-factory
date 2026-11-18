# Bàn giao dự án (đọc trước khi làm việc với chủ kênh)

Repo này làm **video văn học Đức bằng tiếng Đức từ ảnh thật** (Shorts dọc 1080×1920: cuộc đời một nhà văn, một tác phẩm), từ 14/11/2026; trước đó là video tin tức Đức (2 video vụ án Fabian). Tên repo, nhãn `news-*` và thư mục `news/` vẫn giữ tên cũ cho máy chạy ổn định. Dây chuyền được chép từ repo `maihaianh2911-bit/japan-video-factory` (video văn học tiếng Nhật) ngày 12/11/2026 và sửa cho tiếng Đức: thư mục và nhãn đổi `lit` → `news`, phụ đề ngắt theo từ, chữ Source Sans 3 / Source Serif 4, kiểm tra giọng bằng Whisper tiếng Đức so từng từ.

## Chủ kênh

- GitHub `maihaianh2911-bit`. Nói chuyện **bằng tiếng Việt, ngắn gọn, dễ hiểu, không thuật ngữ**: chủ kênh không phải lập trình viên.
- Chỉ dùng **hạn mức gói Claude** (dùng chung với repo Nhật), không dùng Claude API trả tiền. Tiết kiệm hạn mức nhưng **không giảm chất lượng**.

## Quyết định của chủ kênh

- 12/11: **cách dựng video khác repo Nhật**: chủ kênh sẽ gửi video mẫu (thư mục `00-video-mau/` hoặc link). Khi có mẫu, làm lại `src/news/NewsV.tsx` (và `build.py` nếu cần) theo mẫu; phần giọng, tìm ảnh, phụ đề khớp giọng, các bước máy giữ nguyên.
- 14/11: chủ kênh gửi một video mẫu trong chat (video TikTok tóm tắt sách kiểu "Tủ sách hay": nền đen có sao, ảnh bìa + tên ở góc, khung ảnh ngang, phụ đề chữ có chân). Claude làm thử theo mẫu (commit `01db965`), chủ kênh xem rồi **bỏ**: *"Bỏ mẫu video mới thêm. Quay về mẫu cũ"*. Không dùng mẫu đó nữa.
- 14/11 (sau đó): **đổi nội dung kênh sang văn học Đức**: *"Đổi phần nội dung đi, kênh này sẽ làm dạng văn học đức, video mẫu đây, học cả cách viết kịch bản và cách edit của video này"*. Mẫu: video tiếng Việt về Lev Tolstoy (`00-video-mau/van-hoc-tolstoy.md`: toàn bộ lời kèm giây, khung hình, số đo). Đã làm theo mẫu:
  - **Cách dựng** (`src/news/NewsV.tsx`): mỗi lần một ảnh phủ kín khung dọc (chân dung nhà văn, tranh, ảnh chụp), đẩy vào chậm và đều, cắt thẳng, ~9 giây một ảnh; phụ đề chữ Philosopher màu gần đen trên hộp vàng, mỗi dòng một hộp, ở 78 % chiều cao, luôn có chữ; nhạc nền nhẹ; không tiêu đề, không ghi nguồn trên hình (nguồn ảnh trong `credits.txt` cho mô tả video).
  - **Cách viết** (`AGENT_NEWS.md` §1.1): mở bằng mâu thuẫn của cả cuộc đời + câu hỏi ám ảnh + cái kết kể trước; rồi kể theo thời gian từ lúc sinh (năm, nơi, cha mẹ); mỗi chặng 2–4 câu: năm + sự việc + chi tiết cụ thể + tác phẩm ra đời; câu ngắn làm bản lề ("Tính ông nóng nảy."); giọng bình thản, đúng sự thật, không kêu gọi người xem.
  - **Ai viết kịch bản**: phiếu mới (`[Văn học] …`) chỉ cần tên nhà văn hoặc tác phẩm, Claude viết kịch bản tiếng Đức theo mẫu; nếu chủ kênh dán kịch bản riêng thì giữ nguyên ý như quyết định 12/11. (Hiểu từ câu "học cả cách viết kịch bản"; nếu chủ kênh nói khác thì theo chủ kênh.)

- 18/11: **học cách làm của repo Nhật** (`maihaianh2911-bit/japan-news-video-factory`). Chủ kênh thêm repo đó vào phiên và nói *"học tập quy trình làm việc của repo mới thêm vào đi"*. Đã áp dụng những gì chủ kênh dặn bên đó mà hợp với kênh này:
  - **Cách xưng hô:** chủ kênh xưng "tao", gọi Claude là "mày"; Claude xưng "tao", gọi chủ kênh là "mày" (`CLAUDE.md`).
  - **Cách đưa kịch bản:** đưa liền một mạch, tiếng Đức một khối rồi nghĩa tiếng Việt một khối, không đánh số, không gạch đầu dòng (*"Kịch bản phải liền mạch, nói bao nhiêu lần rồi, đừng bao giờ chia đoạn ra như thế"*).
  - **Cách viết:** câu đầu (sau phần mở đầu chung) nói gọn cả câu chuyện và ý nghĩa của nó; lời kể liền mạch, câu nối bằng từ nối, không cắt vụn; kết quay lại câu mở đầu, không hỏi người xem cảm thấy thế nào; có chuyện tình, vợ chồng, mẹ con thì đưa lên trước (`AGENT_NEWS.md` §1.1).
  - **Duyệt ảnh trước khi dựng:** `preview.py` ghi `*_review.md`, mỗi ảnh kèm lời đọc lúc ảnh đó trên hình và tên ảnh gốc; ảnh nào không khớp lời, mặt bị cắt, mờ hay trùng thì chọn lại. Bình luận giao video ghi "Đã duyệt ảnh: N/N ảnh khớp lời đọc" (`AGENT_NEWS.md` §2 bước 6).
  - **Giao video:** gửi file video và file caption vào chat; chỉ gửi video đã xong, không gửi bản xem trước.
  - **Chưa làm, chờ chủ kênh quyết:**
    - Tìm ảnh kiểu mới của repo Nhật: `wiki:` (mọi ảnh về một người hay một nơi qua Wikidata), `geo:`, `web:` (ảnh trên mạng, có rủi ro bản quyền mà chủ kênh đã chấp nhận cho kênh Nhật, chưa cho kênh này), và chấm điểm ảnh theo câu tả.
    - Bốn hiệu ứng hình `fx`: nhịp máy quay, ảnh có chiều sâu, chữ hiện dần, phông chữ riêng.
    - Làm thẳng trên `main` như repo Nhật.
- 18/11: **đổi sang chuỗi "Top X"**. Chủ kênh gửi một video mẫu Top X (danh sách sát nhân, `00-video-mau/top-x.md`) kèm lời *"khả năng phải đổi cách làm video, nên làm kiểu: top x nhà văn lớn nhất của Đức"*. Claude đề xuất một video gồm Top 5, chủ kênh sửa lại: *"mỗi người 1 video đc ko? 5 người thì 5 video sẽ chung cái hook (đổi ng), còn mỗi video sẽ nói về 1 người thôi, nói về cuộc đời và phong cách văn chương"*.
  - **Một chuỗi, mỗi người một video, chung câu mở đầu:**
    - Câu 1 „Die fünf größten deutschen Schriftsteller.“: trên hình là tựa đề chữ to và chân dung tròn của cả 5 người, kèm tên.
    - Câu 2 „Platz fünf: Hermann Hesse.“: chữ to "PLATZ 5" trên ảnh người đó.
    - Sau đó là đời ông và phong cách văn chương (bắt đầu bằng câu „Und wie schrieb …?“).
    - Câu cuối gợi xem video sau. Riêng video hạng nhất thì hỏi người xem xếp ai ở hạng nhất.
  - **Không lấy từ mẫu:** hình vẽ hoạt hình và khung ngang. Phải vẽ hoặc dùng AI mới có, trái luật "ảnh thật". Vẫn giữ khung dọc, ảnh thật, phụ đề vàng, nhịp 1.2.
  - **Phần máy:** khối `"top"` trong `picks.json` (`AGENT_NEWS.md` §2.8), `build.py`, `NewsV.tsx` (TopGrid, chữ PLATZ), `preview.py` (`*_top.jpg`).
  - **Đề xuất 5 kịch bản** (Hesse, Heine, Thomas Mann, Schiller, Goethe): `docs/de-xuat/2026-11-18-top5-series.md`, chờ chủ kênh duyệt.
- 17/11: **nhịp nhanh hơn 20 %**: duyệt 5 kịch bản mới (Heine, Struwwelpeter, Karl May, Kafka, Fontane) kèm *"Ok dựng video đi, cho nhịp nhanh lên 20% nữa nhé"* → `script.json` có `"pace": 1.2`: lúc dựng, giọng đọc nhanh hơn 20 % (giữ độ trầm bổng, không đọc lại, không tốn tiền), mọi khoảng nghỉ ngắn lại tương ứng, phụ đề và chỗ đổi ảnh theo đó (`scripts/news/build.py`). Áp dụng cho mọi video từ nay; video #1–#6 giữ nhịp cũ.
- 16/11: **hình mở đầu phải giữ chân người xem**: video Busch (#5) mở bằng một mảng tranh nét đen trắng bị cắt (bầy gà treo cành) → chủ kênh: *"Video 1 ko ổn, hình ảnh mở đầu cực kì ko ổn. Cái hình đó sẽ rất khó giữ chân người xem"*. Từ nay cảnh đầu là hình nhìn là hiểu ngay trên điện thoại: một chủ thể lớn, rõ (gương mặt, hoặc bức hình ai cũng biết của nhà văn/tác phẩm), tốt nhất có màu; không dùng tranh ngang bị cắt thành dải, tranh nét rối, trang chữ, tòa nhà, hình tối (`AGENT_NEWS.md` §2.4).
- 16/11: **viết như người Đức kể cho người Đức**: chủ kênh sửa câu "Fast jeder in Deutschland kennt diese Zeilen" (Busch): *"nên đc thay bằng: chắc hẳn mọi người đều biết câu thơ này, hãy tỏ ra là 1 ng đức chứ k phải ng nc ngoài viết về đức"* → "Diese Zeilen kennt sicher jeder."; không nói "ở Đức", "người Đức" như người ngoài nhìn vào, dùng "chúng ta" ("wir"), không giải thích điều người Đức nào cũng biết (`AGENT_NEWS.md` §1.1 mục 6). Đã sửa cả 3 kịch bản đề xuất (Grimm, Busch, Schiller: `docs/de-xuat/`).
- 16/11: **mỗi video phải kèm lời đăng (caption)**, để khi tải video về là có sẵn lời đăng: `caption.txt` nằm ngay cạnh `video.mp4` trên nhánh `renders` (tiếng Đức: tiêu đề ≤ 80 ký tự, 2–4 câu mô tả đúng kịch bản, 5–8 hashtag, dòng "Bildquellen: …"). Claude viết nó ở bước chọn ảnh (`AGENT_NEWS.md` §2.7); sửa caption chỉ cần đẩy lại `caption.txt`, máy không dựng lại video. Đã viết bổ sung cho các video đã có (#1, #2, #4, #5, #6; không cho #3, video thử 25 giây).
- 14/11: **Claude phải đọc từng câu rồi chọn cách edit hợp với câu đó từ một bảng có tên** ("bảng cách edit"), không tự đặt số zoom tùy ý. Bảng nằm trong `AGENT_NEWS.md` §2.5 (mã: `scripts/news/moves.py`), gồm 9 kiểu: tiến gần, soi chi tiết, lùi ra, lướt sang phải, lướt sang trái, nâng lên, hạ xuống, đứng yên, trôi nhẹ. Kênh này **chưa có video mẫu**, nên bảng dựa trên hai video đã làm và cách dựng tin tức truyền hình Đức (điềm tĩnh, không hiệu ứng); nhận xét của chủ kênh sẽ chỉnh dần bảng. Bình luận giao video kèm danh sách "Cách edit từng cảnh" (`edits.md`) để chủ kênh nói "cảnh 5 đổi sang kiểu …". Video #1 dùng số tự đặt và vẫn dựng lại y như cũ; video #2 đã được dựng lại bằng bảng này (14/11). **15/11, chỉnh bảng** (chủ kênh đồng ý): cảnh ngắn vẫn chuyển động đủ thấy (dưới khoảng 2 giây thì bản xem trước cảnh báo và gợi ý "đứng yên"); "nâng lên / hạ xuống" trên ảnh ngang tự phóng gần thêm để có chỗ di chuyển; "soi chi tiết / lùi ra" luôn giữ chủ thể trong khung và có thêm điểm `wide` để lùi ra thấy người thứ hai. Vì vậy phiếu **đã dùng `move`** (hiện chỉ #2) nếu dựng lại sẽ có chuyển động khác chút so với bản 14/11 (rõ nhất ở cảnh nâng lên); phiếu không dùng `move` không đổi.
  - **Áp dụng cho kênh văn học** (16/11): bảng giữ nguyên 9 kiểu, chỉ đổi khung thành toàn màn hình 1080×1920 (`moves.py`) và cách đọc "khi nào dùng" theo lời kể văn học (`AGENT_NEWS.md` §2.5). Video mẫu Tolstoy đẩy vào gần như mọi cảnh (đo được +5–20 % mỗi cảnh, 1–3 %/giây, một cảnh +35 %), nên ở kênh này "tiến gần" là kiểu thường dùng nhất; cắt thẳng giữa các cảnh như mẫu (chỉ chuyển mờ khi nhảy xa về thời gian).
- 12/11 (kênh tin tức): *"Kịch bản sẽ do tao làm và gửi vào chat cho m, m chỉ nhận phần sau thôi"* → kịch bản chủ kênh gửi thì Claude không sửa ý, chỉ dịch sát sang tiếng Đức nếu là tiếng Việt (vẫn áp dụng cho kịch bản chủ kênh tự viết; xem 14/11).
- 13/11 (phiếu #1, vụ án Fabian; chỉ cho tin tức): *"Dùng cách 2, che mặt bị cáo và em bé, dùng thêm cả cách 1"* → với tin có thật, được dùng **ảnh báo chí** của chính sự việc (dpa, báo Đức…) bên cạnh ảnh Commons tự do: lưu vào `news/<N>/own/`, **làm mờ mặt bị cáo và trẻ em** (không dùng ảnh nạn nhân là trẻ em), ghi nguồn đầy đủ (`Foto: <tác giả>/dpa`). Chủ kênh biết và chấp nhận rủi ro bản quyền trên YouTube.
- Chưa hỏi lại, đang làm theo cách của repo Nhật: ảnh **thật** (không ảnh AI), Claude tự xem và chọn từng ảnh, xem trước khung hình trước khi dựng, kể liền mạch.

## Quy trình

Phiếu `[Văn học] …` (trước đây `[Tin tức] …`) → `.github/workflows/news.yml` + `scripts/news/run.py` (máy) và `AGENT_NEWS.md` (Claude):

`news-plan` Claude viết `news/<N>/script.json` → `news-voice` máy tạo giọng (11labs.id.vn, một job mỗi câu), kiểm tra phát âm, tìm ảnh (Wikimedia Commons) → `news-pick` Claude chọn ảnh, xem trước khung hình, viết `news/<N>/picks.json` → `news-render` máy dựng (`src/news/`, Remotion) → `news-check` Claude xem bảng cảnh → `news-done`. Bình luận của chủ kênh → `news-fix`. Kết quả: nhánh `renders`, thư mục `news/<N>/`.

## Trạng thái (14/11/2026)

- **14/11: rà soát dây chuyền và sửa** (chủ kênh đồng ý). Kết quả rà soát: 5/5 lượt máy làm video đều chạy tốt, không phiếu nào kẹt. Đã sửa các chỗ có thể gây lỗi về sau:
  - Gọi Claude: thử 3 lần; nếu vẫn không gọi được (thiếu secret, hết hạn mức) thì bình luận của máy trên phiếu nói rõ "⚠️ Chưa gọi được Claude" kèm link nút **Gọi Claude ngay**, không còn hứa "Claude sẽ…" khi chưa gọi được ai. Phiếu đang có nhãn `news-busy` mới (dưới 2 giờ) thì máy không gọi tác vụ nữa (Claude trong chat đang làm) → **nhớ gỡ `news-busy` khi dừng**.
  - Giọng đọc đã trả tiền không bị mất: câu nào đọc xong đều được giữ (thư mục `voice-partial/` trên `renders` khi một câu lỗi), lượt sau chỉ đọc câu còn thiếu; máy nghe lại (Whisper) lỗi thì chỉ cảnh báo; không lấy được nhánh `renders` thì dừng hẳn chứ không đọc lại từ đầu.
  - Bình luận "Giọng đọc xong" ghi **hạn mức giọng đọc còn lại** (13/11: còn khoảng 139.000 ký tự trong 1.002.100; một video 3 phút tốn khoảng 3.000) và cảnh báo khi dưới 20.000.
  - Xóa file cũ trong `news/` trên `main` không còn làm máy chạy; sau khi tìm thêm ảnh phiếu chỉ còn một nhãn bước (`news-pick`); máy không dựng ảnh đã chọn cũ trên ảnh vừa tìm lại (sau khi video cũ bị dọn) mà yêu cầu chọn lại; khi máy tự dừng, bình luận ghi lý do.
  - Workflow: quyền tối thiểu cho từng job; **Thử voice 11labs** để trống giọng = giọng của kênh.
  - **Không làm** (để sau, cần chủ kênh quyết): máy tự kiểm tra định kỳ phiếu bị bỏ quên; đọc nhiều câu cùng lúc cho nhanh (giọng + ảnh hiện ~12–22 phút, phần lớn là đọc từng câu một, ~21 giây/câu); khóa chống hai lượt máy chạy cùng một phiếu (GitHub chỉ giữ một lượt chờ nên dễ làm rơi lượt, xem ghi chú trong `news.yml`) → vẫn phải giữ quy tắc "một lần đẩy cho mỗi bước".
  - Quy tắc **dọn video sau 14 ngày** phiếu không hoạt động (`renders-cleanup.yml`) là chép từ repo Nhật, **chưa hỏi chủ kênh** cho kênh này; giữ nguyên, và bình luận giao video nay ghi ngày hết hạn link.

### Trạng thái trước đó (13/11/2026)

- **Đã có 2 video tin tức** (kiểu cũ, trước khi đổi sang văn học; vụ án Fabian, làm trong chat): phiếu #1 (46 câu, 2 phút 57 giây) và phiếu #2 (22 câu, 1 phút 26 giây), kết quả ở nhánh `renders`, thư mục `news/1/` và `news/2/`. Giọng đọc tiếng Đức, tìm ảnh và dựng trên GitHub đều đã chạy được.
- Thời gian máy thật: giọng + tìm ảnh ~12 phút (22 câu) đến ~22 phút (46 câu); dựng ~6,5 phút (video 1,5 phút) đến ~19 phút (video 3 phút); tìm thêm ảnh ~2 phút.
- Đã xong: đưa lên `main` (12/11); secret `VN11_API_KEY` (12/11, lần đầu ghi sai tên `vn11-api-key`, GitHub không nhận gạch ngang); giọng tiếng Đức `clone_611` ("voice de ww40k", giọng clone tiếng Đức có sẵn trong tài khoản 11labs của chủ kênh), ghi trong `prompts/news_voice.json`. Tài khoản chỉ có 3 giọng clone (611 Đức, 190 và 461 Nhật), không có giọng Đức thường nào.
- Còn thiếu, theo thứ tự:
  1. **Tác vụ Claude chưa được gọi tự động**: lúc 13/11 10:35 UTC repo này vẫn **chưa có** hai secret `CLAUDE_TASK_URL` và `CLAUDE_TASK_TOKEN` (nhật ký máy báo "Chưa cài CLAUDE_TASK_URL/CLAUDE_TASK_TOKEN"). Không có lượt chạy mỗi giờ (chủ kênh, 13/11): Claude chỉ bắt đầu khi GitHub gọi, nên khi chưa có hai secret này phiếu chỉ được làm trong chat (hoặc bấm **Gọi Claude ngay** sau khi thêm secret). Chọn **một** trong hai cách:
     - **Dùng chung** tác vụ "japan-video-factory" của repo Nhật: chép hai secret với **cùng giá trị** như ở `japan-video-factory`. Khi đó lời nhắn (prompt) của tác vụ đó phải là lời **không giới hạn repo**, kiểu "Làm theo AGENT_NIGHTLY.md …" (tác vụ kiểm tra mọi kênh, trong đó có phiếu `news-*` của repo này). **Không** dùng lời "Làm việc đang chờ trong repo này" / "chỉ kênh văn học" (Nhật): với lời đó tác vụ chỉ làm kênh Nhật và bỏ qua phiếu của repo Đức này.
     - **Tác vụ riêng** cho repo này (mỗi repo một chỗ Claude): tạo tác vụ mới có lời nhắn "Làm theo AGENT_NIGHTLY.md của repo maihaianh2911-bit/germany-news-video-factory." (hoặc "Làm việc đang chờ trong repo này" nếu tác vụ chỉ gắn repo này), rồi chép URL và token **của tác vụ mới** vào hai secret của repo này.
  2. Video văn học: phiếu #3 (Goethe) — video thử 29 giây (14/11), rồi theo yêu cầu "Làm bản đầy đủ đi" bản đầy đủ 2 phút 56 giây, 48 câu, 25 cảnh có kiểu edit theo bảng (16/11), đều dựng bằng bản trên nhánh `ccr-40842142-1rxbl8` (chạy bằng tay qua workflow_dispatch với ref nhánh đó). Chủ kênh duyệt thì gộp nhánh vào `main`; tới lúc đó máy chính vẫn chạy kiểu tin tức cũ và chưa nhận phiếu `[Văn học]`. Tiếp theo (16/11): 3 kịch bản Claude đề xuất, chủ kênh duyệt ("Ok dựng đi"), dựng cùng cách: #4 Grimm (2:48, 22 cảnh), #5 Busch (2:32, 21 cảnh; dựng lại vì hình mở đầu, xem quyết định 16/11), #6 Schiller (2:55, 24 cảnh). Bản kịch bản và nghĩa tiếng Việt: `docs/de-xuat/`.
  3. Đo lại tốc độ đọc (đang ước 14–15 ký tự/giây trong `AGENT_NEWS.md`) và xem cỡ chữ phụ đề trên hai video đã có.

## Lưu ý kỹ thuật

- ffmpeg trên máy GitHub lấy từ gói pip `imageio-ffmpeg`, xem `scripts/news/ff.py`. Ghim `faster-whisper==1.1.1` + `av==13.1.0`.
- Lấy nhánh renders bằng `+refs/heads/renders:…`. Nhánh `renders` tự được tạo ở lần đăng kết quả đầu tiên.
- Từ hay bị giọng đọc sai ghi vào `prompts/news_readings.json` (chỉ thay nguyên từ: `US` không đổi `USA`).
- Kiểm tra mã trước khi đẩy cần `pip install numpy scipy pillow num2words==0.5.14` (nếu `num2words` không cài được vì `docopt`: `pip install docopt-ng && pip install --no-deps num2words==0.5.14`) và `npm ci`; chi tiết trong `CLAUDE.md`.
- Gọi tác vụ Claude: `scripts/wake_claude.sh` → `scripts/news/wake.py` (thử lại, kiểm tra `news-busy`, viết bình luận của bước).
- Kiểm tra giọng: số, `%`, `€`, `§` được viết thành chữ ở cả hai bên (`num2words`) nên đọc sai số sẽ bị liệt kê; từ ≤ 5 chữ cái phải khớp hẳn (ein/kein). Kiểm tra mã: `python3 tests/news_units.py`.
- GitHub không nhận file trên 100 MB: video trên 95 MB tự được nén lại một lần cho còn ~90 MB, kịch bản không phải cắt. Giọng đọc được lưu lên `renders` ngay khi đọc xong câu cuối, trước khi kiểm tra và tìm ảnh; nếu một câu lỗi thì các câu đã xong được lưu ở `voice-partial/` và dùng lại.
- Tìm ảnh: `incategory:"<tên mục Commons>"` cho người/tòa nhà/địa danh; máy bỏ ảnh < 400 px và ảnh trùng.
