# Bàn giao dự án (đọc trước khi làm việc với chủ kênh)

Repo này làm **video tin tức tiếng Đức từ ảnh thật** (Shorts dọc 1080×1920). Dây chuyền được chép từ repo `maihaianh2911-bit/japan-video-factory` (video văn học tiếng Nhật) ngày 12/11/2026 và sửa cho tiếng Đức: thư mục và nhãn đổi `lit` → `news`, phụ đề ngắt theo từ, chữ Source Sans 3 / Source Serif 4, kiểm tra giọng bằng Whisper tiếng Đức so từng từ.

## Chủ kênh

- GitHub `maihaianh2911-bit`. Nói chuyện **bằng tiếng Việt, ngắn gọn, dễ hiểu, không thuật ngữ**: chủ kênh không phải lập trình viên.
- Chỉ dùng **hạn mức gói Claude** (dùng chung với repo Nhật), không dùng Claude API trả tiền. Tiết kiệm hạn mức nhưng **không giảm chất lượng**.

## Quyết định của chủ kênh

- 12/11: *"Kịch bản sẽ do tao làm và gửi vào chat cho m, m chỉ nhận phần sau thôi"* → chủ kênh tự viết kịch bản và gửi vào chat; Claude không viết, không tìm tin, không sửa ý. Claude mở phiếu, dịch sát sang tiếng Đức nếu kịch bản là tiếng Việt, rồi làm video.
- Chưa hỏi lại, đang làm theo cách của repo Nhật: ảnh **thật** (không ảnh AI), Claude tự xem và chọn từng ảnh, xem trước khung hình trước khi dựng, kể liền mạch (không thẻ chia phần).

## Quy trình

Phiếu `[Tin tức] …` → `.github/workflows/news.yml` + `scripts/news/run.py` (máy) và `AGENT_NEWS.md` (Claude):

`news-plan` Claude viết `news/<N>/script.json` → `news-voice` máy tạo giọng (11labs.id.vn, một job mỗi câu), kiểm tra phát âm, tìm ảnh (Wikimedia Commons) → `news-pick` Claude chọn ảnh, xem trước khung hình, viết `news/<N>/picks.json` → `news-render` máy dựng (`src/news/`, Remotion) → `news-check` Claude xem bảng cảnh → `news-done`. Bình luận của chủ kênh → `news-fix`. Kết quả: nhánh `renders`, thư mục `news/<N>/`.

## Trạng thái (12/11/2026)

- Mã đã chạy thử bằng dữ liệu giả (`tests/news_smoke.py --still` và `--chapters`, kiểm tra kiểu) trên máy của phiên chat. **Chưa có video thật nào**: giọng đọc tiếng Đức, tìm ảnh và dựng trên GitHub chưa chạy lần nào ở repo này.
- Còn thiếu, theo thứ tự:
  1. Mã phải nằm trên nhánh `main` thì máy GitHub mới chạy (phiên 12/11 chỉ được đẩy lên nhánh `ccr-41fd68e7-ie4xtj`, chờ chủ kênh đồng ý).
  2. Secret `VN11_API_KEY` (chủ kênh tự thêm; cùng khóa với repo Nhật).
  3. **Giọng đọc tiếng Đức**: `prompts/news_voice.json` còn trống, bước giọng sẽ dừng và báo rõ. Chạy workflow **Thử voice 11labs** để lấy danh sách giọng Đức (ra `voices.md` trên nhánh `renders`) và đọc thử; chủ kênh nghe rồi chọn. Có thể thử cả `clone_190` (giọng của kênh Nhật) với câu tiếng Đức.
  4. Tác vụ Claude hằng giờ cho repo này + secrets `CLAUDE_TASK_URL`, `CLAUDE_TASK_TOKEN` (chưa tạo). Chưa có thì video vẫn làm được trong phiên chat.
- Sau video đầu tiên: đo lại tốc độ đọc (đang ước 14–15 ký tự/giây trong `AGENT_NEWS.md`), xem cỡ chữ phụ đề, và hỏi chủ kênh về kiểu hình (màu nền, nhạc) vì giao diện đang giống kênh văn học.

## Lưu ý kỹ thuật

- ffmpeg trên máy GitHub lấy từ gói pip `imageio-ffmpeg`, xem `scripts/news/ff.py`. Ghim `faster-whisper==1.1.1` + `av==13.1.0`.
- Lấy nhánh renders bằng `+refs/heads/renders:…`. Nhánh `renders` tự được tạo ở lần đăng kết quả đầu tiên.
- Từ hay bị giọng đọc sai ghi vào `prompts/news_readings.json`.
- Tìm ảnh: `incategory:"<tên mục Commons>"` cho người/tòa nhà/địa danh; máy bỏ ảnh < 400 px và ảnh trùng.
