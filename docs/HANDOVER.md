# Bàn giao dự án (đọc trước khi làm việc với chủ kênh)

Repo này làm **video tin tức tiếng Đức từ ảnh thật** (Shorts dọc 1080×1920). Dây chuyền được chép từ repo `maihaianh2911-bit/japan-video-factory` (video văn học tiếng Nhật) ngày 12/11/2026 và sửa cho tiếng Đức: thư mục và nhãn đổi `lit` → `news`, phụ đề ngắt theo từ, chữ Source Sans 3 / Source Serif 4, kiểm tra giọng bằng Whisper tiếng Đức so từng từ.

## Chủ kênh

- GitHub `maihaianh2911-bit`. Nói chuyện **bằng tiếng Việt, ngắn gọn, dễ hiểu, không thuật ngữ**: chủ kênh không phải lập trình viên.
- Chỉ dùng **hạn mức gói Claude** (dùng chung với repo Nhật), không dùng Claude API trả tiền. Tiết kiệm hạn mức nhưng **không giảm chất lượng**.

## Quyết định của chủ kênh

- 12/11: **cách dựng video khác repo Nhật**: chủ kênh sẽ gửi video mẫu (thư mục `00-video-mau/` hoặc link). Khi có mẫu, làm lại `src/news/NewsV.tsx` (và `build.py` nếu cần) theo mẫu; phần giọng, tìm ảnh, phụ đề khớp giọng, các bước máy giữ nguyên.

- 12/11: *"Kịch bản sẽ do tao làm và gửi vào chat cho m, m chỉ nhận phần sau thôi"* → chủ kênh tự viết kịch bản và gửi vào chat; Claude không viết, không tìm tin, không sửa ý. Claude mở phiếu, dịch sát sang tiếng Đức nếu kịch bản là tiếng Việt, rồi làm video.
- 13/11 (phiếu #1, vụ án Fabian): *"Dùng cách 2, che mặt bị cáo và em bé, dùng thêm cả cách 1"* → với tin có thật, được dùng **ảnh báo chí** của chính sự việc (dpa, báo Đức…) bên cạnh ảnh Commons tự do: lưu vào `news/<N>/own/`, **làm mờ mặt bị cáo và trẻ em** (không dùng ảnh nạn nhân là trẻ em), ghi nguồn đầy đủ (`Foto: <tác giả>/dpa`). Chủ kênh biết và chấp nhận rủi ro bản quyền trên YouTube.
- Chưa hỏi lại, đang làm theo cách của repo Nhật: ảnh **thật** (không ảnh AI), Claude tự xem và chọn từng ảnh, xem trước khung hình trước khi dựng, kể liền mạch (không thẻ chia phần).

## Quy trình

Phiếu `[Tin tức] …` → `.github/workflows/news.yml` + `scripts/news/run.py` (máy) và `AGENT_NEWS.md` (Claude):

`news-plan` Claude viết `news/<N>/script.json` → `news-voice` máy tạo giọng (11labs.id.vn, một job mỗi câu), kiểm tra phát âm, tìm ảnh (Wikimedia Commons) → `news-pick` Claude chọn ảnh, xem trước khung hình, viết `news/<N>/picks.json` → `news-render` máy dựng (`src/news/`, Remotion) → `news-check` Claude xem bảng cảnh → `news-done`. Bình luận của chủ kênh → `news-fix`. Kết quả: nhánh `renders`, thư mục `news/<N>/`.

## Trạng thái (13/11/2026)

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
- Kiểm tra giọng: số, `%`, `€`, `§` được viết thành chữ ở cả hai bên (`num2words`) nên đọc sai số sẽ bị liệt kê; từ ≤ 5 chữ cái phải khớp hẳn (ein/kein). Kiểm tra mã: `python3 tests/news_units.py`.
- GitHub không nhận file trên 100 MB: video trên 95 MB tự được nén lại một lần cho còn ~90 MB, kịch bản không phải cắt. Giọng đọc được lưu lên `renders` ngay khi xong, trước khi tìm ảnh.
- Tìm ảnh: `incategory:"<tên mục Commons>"` cho người/tòa nhà/địa danh; máy bỏ ảnh < 400 px và ảnh trùng.
