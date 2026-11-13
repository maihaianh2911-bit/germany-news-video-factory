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

## Trạng thái (12/11/2026)

- Mã đã chạy thử bằng dữ liệu giả (`tests/news_smoke.py --still` và `--chapters`, kiểm tra kiểu) trên máy của phiên chat. **Chưa có video thật nào**: giọng đọc tiếng Đức, tìm ảnh và dựng trên GitHub chưa chạy lần nào ở repo này.
- Còn thiếu, theo thứ tự:
  1. ~~Đưa lên `main`~~: xong 12/11, chủ kênh đồng ý.
  2. ~~Secret `VN11_API_KEY`~~: chủ kênh đã thêm 12/11 (lần đầu ghi sai tên `vn11-api-key`, GitHub không nhận gạch ngang).
  3. ~~Giọng đọc tiếng Đức~~: 12/11 chọn `clone_611` ("voice de ww40k", giọng clone tiếng Đức có sẵn trong tài khoản 11labs của chủ kênh), ghi trong `prompts/news_voice.json`. Tài khoản chỉ có 3 giọng clone (611 Đức, 190 và 461 Nhật), không có giọng Đức thường nào.
  4. Tác vụ Claude: **dùng chung** tác vụ "japan-video-factory" của repo Nhật, tác vụ đó kiểm tra cả phiếu `news-*` của repo này (xem `AGENT_NIGHTLY.md` của `japan-video-factory`). Không có lượt chạy mỗi giờ (chủ kênh, 13/11): Claude chỉ bắt đầu khi GitHub gọi, nên chủ kênh **phải** chép hai secret `CLAUDE_TASK_URL` và `CLAUDE_TASK_TOKEN` (cùng giá trị như ở `japan-video-factory`) vào repo này; chưa chép thì chỉ làm được trong chat.
  5. Video mẫu của chủ kênh (`00-video-mau/`) **vẫn chưa có**: bố cục hiện vẫn chép kênh văn học, sẽ làm lại theo mẫu khi có.
- Sau video đầu tiên: đo lại tốc độ đọc (đang ước 14–15 ký tự/giây trong `AGENT_NEWS.md`), xem cỡ chữ phụ đề, và hỏi chủ kênh về kiểu hình (màu nền, nhạc) vì giao diện đang giống kênh văn học.

## Lưu ý kỹ thuật

- ffmpeg trên máy GitHub lấy từ gói pip `imageio-ffmpeg`, xem `scripts/news/ff.py`. Ghim `faster-whisper==1.1.1` + `av==13.1.0`.
- Lấy nhánh renders bằng `+refs/heads/renders:…`. Nhánh `renders` tự được tạo ở lần đăng kết quả đầu tiên.
- Từ hay bị giọng đọc sai ghi vào `prompts/news_readings.json` (chỉ thay nguyên từ: `US` không đổi `USA`).
- Kiểm tra giọng: số, `%`, `€`, `§` được viết thành chữ ở cả hai bên (`num2words`) nên đọc sai số sẽ bị liệt kê; từ ≤ 5 chữ cái phải khớp hẳn (ein/kein). Kiểm tra mã: `python3 tests/news_units.py`.
- GitHub không nhận file trên 100 MB: video trên 95 MB tự được nén lại một lần cho còn ~90 MB, kịch bản không phải cắt. Giọng đọc được lưu lên `renders` ngay khi xong, trước khi tìm ảnh.
- Tìm ảnh: `incategory:"<tên mục Commons>"` cho người/tòa nhà/địa danh; máy bỏ ảnh < 400 px và ảnh trùng.
