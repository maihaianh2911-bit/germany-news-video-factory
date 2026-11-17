# Bàn giao dự án (đọc trước khi làm việc với chủ kênh)

Repo này làm **video tin tức tiếng Đức từ ảnh thật** (Shorts dọc 1080×1920). Dây chuyền được chép từ repo `maihaianh2911-bit/japan-video-factory` (video văn học tiếng Nhật) ngày 12/11/2026 và sửa cho tiếng Đức: thư mục và nhãn đổi `lit` → `news`, phụ đề ngắt theo từ, chữ Source Sans 3 / Source Serif 4, kiểm tra giọng bằng Whisper tiếng Đức so từng từ.

## Chủ kênh

- GitHub `maihaianh2911-bit`. Nói chuyện **bằng tiếng Việt, ngắn gọn, dễ hiểu, không thuật ngữ**: chủ kênh không phải lập trình viên.
- Chỉ dùng **hạn mức gói Claude** (dùng chung với repo Nhật), không dùng Claude API trả tiền. Tiết kiệm hạn mức nhưng **không giảm chất lượng**.

## Quyết định của chủ kênh

- 12/11: **cách dựng video khác repo Nhật**: chủ kênh sẽ gửi video mẫu (thư mục `00-video-mau/` hoặc link). Khi có mẫu, làm lại `src/news/NewsV.tsx` (và `build.py` nếu cần) theo mẫu; phần giọng, tìm ảnh, phụ đề khớp giọng, các bước máy giữ nguyên.

- 12/11: *"Kịch bản sẽ do tao làm và gửi vào chat cho m, m chỉ nhận phần sau thôi"* → chủ kênh tự viết kịch bản và gửi vào chat; Claude không viết, không tìm tin, không sửa ý. Claude mở phiếu, dịch sát sang tiếng Đức nếu kịch bản là tiếng Việt, rồi làm video.
- 16/11: **mỗi video phải kèm lời đăng (caption)**, để khi tải video về là có sẵn lời đăng: `caption.txt` nằm ngay cạnh `video.mp4` trên nhánh `renders` (tiếng Đức: tiêu đề ≤ 80 ký tự, 2–4 câu mô tả đúng kịch bản, 5–8 hashtag, dòng "Bildquellen: …"). Claude viết nó ở bước chọn ảnh (`AGENT_NEWS.md` §2.7); sửa caption chỉ cần đẩy lại `caption.txt`, máy không dựng lại video. Đã viết bổ sung cho các video đã có (#1, #2, #4, #5, #6; không cho #3, video thử 25 giây).
- 14/11: **Claude phải đọc từng câu rồi chọn cách edit hợp với câu đó từ một bảng có tên** ("bảng cách edit"), không tự đặt số zoom tùy ý. Bảng nằm trong `AGENT_NEWS.md` §2.5 (mã: `scripts/news/moves.py`), gồm 9 kiểu: tiến gần, soi chi tiết, lùi ra, lướt sang phải, lướt sang trái, nâng lên, hạ xuống, đứng yên, trôi nhẹ. Kênh này **chưa có video mẫu**, nên bảng dựa trên hai video đã làm và cách dựng tin tức truyền hình Đức (điềm tĩnh, không hiệu ứng); nhận xét của chủ kênh sẽ chỉnh dần bảng. Bình luận giao video kèm danh sách "Cách edit từng cảnh" (`edits.md`) để chủ kênh nói "cảnh 5 đổi sang kiểu …". Video #1 dùng số tự đặt và vẫn dựng lại y như cũ; video #2 đã được dựng lại bằng bảng này (14/11). **15/11, chỉnh bảng** (chủ kênh đồng ý): cảnh ngắn vẫn chuyển động đủ thấy (dưới khoảng 2 giây thì bản xem trước cảnh báo và gợi ý "đứng yên"); "nâng lên / hạ xuống" trên ảnh ngang tự phóng gần thêm để có chỗ di chuyển; "soi chi tiết / lùi ra" luôn giữ chủ thể trong khung và có thêm điểm `wide` để lùi ra thấy người thứ hai. Vì vậy phiếu **đã dùng `move`** (hiện chỉ #2) nếu dựng lại sẽ có chuyển động khác chút so với bản 14/11 (rõ nhất ở cảnh nâng lên); phiếu không dùng `move` không đổi.
- 13/11 (phiếu #1, vụ án Fabian): *"Dùng cách 2, che mặt bị cáo và em bé, dùng thêm cả cách 1"* → với tin có thật, được dùng **ảnh báo chí** của chính sự việc (dpa, báo Đức…) bên cạnh ảnh Commons tự do: lưu vào `news/<N>/own/`, **làm mờ mặt bị cáo và trẻ em** (không dùng ảnh nạn nhân là trẻ em), ghi nguồn đầy đủ (`Foto: <tác giả>/dpa`). Chủ kênh biết và chấp nhận rủi ro bản quyền trên YouTube.
- Chưa hỏi lại, đang làm theo cách của repo Nhật: ảnh **thật** (không ảnh AI), Claude tự xem và chọn từng ảnh, xem trước khung hình trước khi dựng, kể liền mạch (không thẻ chia phần).

## Quy trình

Phiếu `[Tin tức] …` → `.github/workflows/news.yml` + `scripts/news/run.py` (máy) và `AGENT_NEWS.md` (Claude):

`news-plan` Claude viết `news/<N>/script.json` → `news-voice` máy tạo giọng (11labs.id.vn, một job mỗi câu), kiểm tra phát âm, tìm ảnh (Wikimedia Commons) → `news-pick` Claude chọn ảnh, xem trước khung hình, viết `news/<N>/picks.json` → `news-render` máy dựng (`src/news/`, Remotion) → `news-check` Claude xem bảng cảnh → `news-done`. Bình luận của chủ kênh → `news-fix`. Kết quả: nhánh `renders`, thư mục `news/<N>/`.

## Trạng thái (14/11/2026)

- **17/11: khâu tìm ảnh được làm lại** (`scripts/find_images.py`) — **đã vào `main` ngày 17/11** (chủ kênh: "đưa tất cả các phần đã cải thiện lên nhánh chính đi"); chưa chạy trên GitHub của repo này: video đầu tiên sau ngày này là lần chạy thật đầu tiên, xem kỹ nhật ký bước tìm ảnh. Lý do: chủ kênh thấy video thiếu ảnh. Cách mới đã được làm và đo ở kênh vụ án Đức (`germany-crime-video-factory`: ảnh tìm được 102 → 139, ảnh đúng chủ đề của một từ khóa 12 → 23, thời gian 12 phút 43 giây → 6 phút 25 giây), nay đưa sang kênh này nhưng giữ nếp cũ của kênh: vẫn chỉ lấy ảnh Wikimedia Commons có giấy phép dùng được, từ khóa cũ (`incategory:"…"`, từ khóa thường) vẫn chạy như trước. Mới:
  - `wiki: <tên>` (ví dụ `wiki: Friedrich Merz`, `wiki: Bundestag`): máy tìm đúng người / cơ quan / công ty / tòa nhà / thành phố đó qua Wikidata, rồi lấy ảnh chính, ảnh trong bài Wikipedia tiếng Đức và tiếng Anh, ảnh trong thư mục Commons và ảnh chụp tại chỗ — tới 24 ảnh một từ khóa (trước đây 8). `index.json` ghi máy đã hiểu tên đó là ai/cái gì để Claude kiểm tra (tránh nhầm người trùng tên).
  - `geo: <vĩ độ>,<kinh độ> <mét>`: ảnh chụp quanh một điểm.
  - Từ khóa kèm mô tả `{"q": "Gerichtssaal", "want": "mô tả bằng tiếng Anh"}` cho ảnh minh họa: máy lấy 30 ảnh, chấm điểm từng ảnh theo mô tả (bộ chấm điểm CLIP, mã mở `open_clip`), giữ 8 ảnh khớp nhất, bỏ ảnh không khớp và ảnh không hợp để đăng. Điểm in trên bảng ảnh (`~0.31`).
  - Ảnh lấy ở cỡ chuẩn của Wikimedia (rộng tối đa 1920 px; trước là 2000 px), tải vài ảnh cùng lúc; khi Wikimedia báo quá tải (lỗi 429) máy chỉ chờ tổng cộng tối đa 90 giây cho cả lượt, không chờ lại ở từng từ khóa; tìm thấy ảnh mà không tải được thì ghi là lỗi để tìm lại, không coi là "không có ảnh".
  - `news.yml` và `find-images.yml` cài thêm bộ chấm điểm ảnh và lưu file mô hình (600 MB) giữa các lượt; cài không được thì máy vẫn tìm ảnh như cũ, chỉ không xếp hạng. `run.py` chuyển được từ khóa kèm mô tả cho khâu tìm ảnh. Quy tắc viết từ khóa và chọn ảnh mới cho Claude: `AGENT_NEWS.md` §1 và §2.
  - Thử thật một lần nhỏ trong phiên Claude (17/11, 3 từ khóa): `wiki: Friedrich Merz` → máy nhận đúng Friedrich Merz (Q566257, "deutscher Politiker (CDU), 10. Bundeskanzler"), có 30 ảnh để chọn; `incategory:"Friedrich Merz"` (cách cũ) chỉ có 3 ảnh; `Gerichtssaal` kèm mô tả → 4 ảnh phòng xử án, điểm 0,34–0,37, nhưng là phòng xử án ở Mỹ (máy không biết nước nào: Claude phải tự xem). Cũng thấy ví dụ cũ `incategory:"Reichstag building"` không ra ảnh nào (Commons không có thư mục tên đó) → đã sửa ví dụ trong `AGENT_NEWS.md`.
  - **Chưa làm / chưa kiểm:** chưa chạy trên GitHub cho kênh này (chưa đo số ảnh và thời gian thật của kênh tin tức; bước cài bộ chấm điểm trong `news.yml` chưa chạy lần nào), chưa dựng lại video nào bằng cách tìm mới. Repo `japan-video-factory` (cùng gốc file `find_images.py`) được một phiên khác sửa riêng trong cùng đợt; hai file **chưa được đối chiếu** với nhau.
- **14/11: rà soát dây chuyền và sửa** (chủ kênh đồng ý). Kết quả rà soát: 5/5 lượt máy làm video đều chạy tốt, không phiếu nào kẹt. Đã sửa các chỗ có thể gây lỗi về sau:
  - Gọi Claude: thử 3 lần; nếu vẫn không gọi được (thiếu secret, hết hạn mức) thì bình luận của máy trên phiếu nói rõ "⚠️ Chưa gọi được Claude" kèm link nút **Gọi Claude ngay**, không còn hứa "Claude sẽ…" khi chưa gọi được ai. Phiếu đang có nhãn `news-busy` mới (dưới 2 giờ) thì máy không gọi tác vụ nữa (Claude trong chat đang làm) → **nhớ gỡ `news-busy` khi dừng**.
  - Giọng đọc đã trả tiền không bị mất: câu nào đọc xong đều được giữ (thư mục `voice-partial/` trên `renders` khi một câu lỗi), lượt sau chỉ đọc câu còn thiếu; máy nghe lại (Whisper) lỗi thì chỉ cảnh báo; không lấy được nhánh `renders` thì dừng hẳn chứ không đọc lại từ đầu.
  - Bình luận "Giọng đọc xong" ghi **hạn mức giọng đọc còn lại** (13/11: còn khoảng 139.000 ký tự trong 1.002.100; một video 3 phút tốn khoảng 3.000) và cảnh báo khi dưới 20.000.
  - Xóa file cũ trong `news/` trên `main` không còn làm máy chạy; sau khi tìm thêm ảnh phiếu chỉ còn một nhãn bước (`news-pick`); máy không dựng ảnh đã chọn cũ trên ảnh vừa tìm lại (sau khi video cũ bị dọn) mà yêu cầu chọn lại; khi máy tự dừng, bình luận ghi lý do.
  - Workflow: quyền tối thiểu cho từng job; **Thử voice 11labs** để trống giọng = giọng của kênh.
  - **Không làm** (để sau, cần chủ kênh quyết): máy tự kiểm tra định kỳ phiếu bị bỏ quên; đọc nhiều câu cùng lúc cho nhanh (giọng + ảnh hiện ~12–22 phút, phần lớn là đọc từng câu một, ~21 giây/câu); khóa chống hai lượt máy chạy cùng một phiếu (GitHub chỉ giữ một lượt chờ nên dễ làm rơi lượt, xem ghi chú trong `news.yml`) → vẫn phải giữ quy tắc "một lần đẩy cho mỗi bước".
  - Quy tắc **dọn video sau 14 ngày** phiếu không hoạt động (`renders-cleanup.yml`) là chép từ repo Nhật, **chưa hỏi chủ kênh** cho kênh này; giữ nguyên, và bình luận giao video nay ghi ngày hết hạn link.

### Trạng thái trước đó (13/11/2026)

- **Đã có 2 video thật** (vụ án Fabian, làm trong chat): phiếu #1 (46 câu, 2 phút 57 giây) và phiếu #2 (22 câu, 1 phút 26 giây), kết quả ở nhánh `renders`, thư mục `news/1/` và `news/2/`. Giọng đọc tiếng Đức, tìm ảnh và dựng trên GitHub đều đã chạy được.
- Thời gian máy thật: giọng + tìm ảnh ~12 phút (22 câu) đến ~22 phút (46 câu); dựng ~6,5 phút (video 1,5 phút) đến ~19 phút (video 3 phút); tìm thêm ảnh ~2 phút.
- Đã xong: đưa lên `main` (12/11); secret `VN11_API_KEY` (12/11, lần đầu ghi sai tên `vn11-api-key`, GitHub không nhận gạch ngang); giọng tiếng Đức `clone_611` ("voice de ww40k", giọng clone tiếng Đức có sẵn trong tài khoản 11labs của chủ kênh), ghi trong `prompts/news_voice.json`. Tài khoản chỉ có 3 giọng clone (611 Đức, 190 và 461 Nhật), không có giọng Đức thường nào.
- Còn thiếu, theo thứ tự:
  1. **Tác vụ Claude chưa được gọi tự động**: lúc 13/11 10:35 UTC repo này vẫn **chưa có** hai secret `CLAUDE_TASK_URL` và `CLAUDE_TASK_TOKEN` (nhật ký máy báo "Chưa cài CLAUDE_TASK_URL/CLAUDE_TASK_TOKEN"). Không có lượt chạy mỗi giờ (chủ kênh, 13/11): Claude chỉ bắt đầu khi GitHub gọi, nên khi chưa có hai secret này phiếu chỉ được làm trong chat (hoặc bấm **Gọi Claude ngay** sau khi thêm secret). Chọn **một** trong hai cách:
     - **Dùng chung** tác vụ "japan-video-factory" của repo Nhật: chép hai secret với **cùng giá trị** như ở `japan-video-factory`. Khi đó lời nhắn (prompt) của tác vụ đó phải là lời **không giới hạn repo**, kiểu "Làm theo AGENT_NIGHTLY.md …" (tác vụ kiểm tra mọi kênh, trong đó có phiếu `news-*` của repo này). **Không** dùng lời "Làm việc đang chờ trong repo này" / "chỉ kênh văn học": với lời đó tác vụ chỉ làm kênh văn học và bỏ qua phiếu tin tức Đức.
     - **Tác vụ riêng** cho repo này (mỗi repo một chỗ Claude): tạo tác vụ mới có lời nhắn "Làm theo AGENT_NIGHTLY.md của repo maihaianh2911-bit/germany-news-video-factory." (hoặc "Làm việc đang chờ trong repo này" nếu tác vụ chỉ gắn repo này), rồi chép URL và token **của tác vụ mới** vào hai secret của repo này.
  2. Video mẫu của chủ kênh (`00-video-mau/`) **vẫn chưa có**: bố cục hiện vẫn chép kênh văn học, sẽ làm lại theo mẫu khi có.
  3. Hỏi chủ kênh về kiểu hình (màu nền, nhạc) vì giao diện đang giống kênh văn học; đo lại tốc độ đọc (đang ước 14–15 ký tự/giây trong `AGENT_NEWS.md`) và xem cỡ chữ phụ đề trên hai video đã có.

## Lưu ý kỹ thuật

- ffmpeg trên máy GitHub lấy từ gói pip `imageio-ffmpeg`, xem `scripts/news/ff.py`. Ghim `faster-whisper==1.1.1` + `av==13.1.0`.
- Lấy nhánh renders bằng `+refs/heads/renders:…`. Nhánh `renders` tự được tạo ở lần đăng kết quả đầu tiên.
- Từ hay bị giọng đọc sai ghi vào `prompts/news_readings.json` (chỉ thay nguyên từ: `US` không đổi `USA`).
- Kiểm tra mã trước khi đẩy cần `pip install numpy scipy pillow num2words==0.5.14` (nếu `num2words` không cài được vì `docopt`: `pip install docopt-ng && pip install --no-deps num2words==0.5.14`) và `npm ci`; chi tiết trong `CLAUDE.md`.
- Gọi tác vụ Claude: `scripts/wake_claude.sh` → `scripts/news/wake.py` (thử lại, kiểm tra `news-busy`, viết bình luận của bước).
- Kiểm tra giọng: số, `%`, `€`, `§` được viết thành chữ ở cả hai bên (`num2words`) nên đọc sai số sẽ bị liệt kê; từ ≤ 5 chữ cái phải khớp hẳn (ein/kein). Kiểm tra mã: `python3 tests/news_units.py`.
- GitHub không nhận file trên 100 MB: video trên 95 MB tự được nén lại một lần cho còn ~90 MB, kịch bản không phải cắt. Giọng đọc được lưu lên `renders` ngay khi đọc xong câu cuối, trước khi kiểm tra và tìm ảnh; nếu một câu lỗi thì các câu đã xong được lưu ở `voice-partial/` và dùng lại.
- Tìm ảnh: `incategory:"<tên mục Commons>"` cho người/tòa nhà/địa danh; máy bỏ ảnh < 400 px và ảnh trùng. Từ 17/11 (trên nhánh, xem mục Trạng thái): thêm `wiki:`, `geo:` và từ khóa kèm mô tả. Wikimedia giới hạn số lần hỏi (lỗi 429, kèm số giây phải chờ) và chỉ phát thoải mái ảnh ở các cỡ chuẩn (330, 960, 1280, 1920, 3840 px).
