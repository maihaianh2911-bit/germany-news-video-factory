# germany-news-video-factory

Dây chuyền làm **video tin tức tiếng Đức** khổ dọc (1080×1920) cho Shorts: ảnh thật (dùng tự do, không AI) chuyển động chậm ở trên, phụ đề chạy theo giọng đọc tiếng Đức ở dưới. Chạy trên GitHub.

## Làm một video

1. Gửi kịch bản (tiếng Việt hoặc tiếng Đức) vào một phiên chat Claude có kết nối repo này. Hoặc tự mở phiếu: **Issues → New issue → 📰 Video tin tức (ảnh thật)**, dán kịch bản → **Create**.
2. Không cần làm gì thêm. Claude chia câu (dịch sát sang tiếng Đức nếu cần, không sửa ý) → máy tạo giọng đọc, tự kiểm tra phát âm, tìm ảnh → Claude xem và chọn ảnh hợp từng câu, xem trước khung hình → máy dựng video → Claude kiểm tra lại từng cảnh. Mỗi bước báo trong phiếu.
3. Bình luận cuối có link **video**, **phụ đề** (SRT) và **nguồn ảnh** (dán vào mô tả video).
4. Muốn sửa: viết **một bình luận** gom hết yêu cầu vào phiếu, ví dụ "cảnh 3 đổi ảnh, câu 5 đọc sai".

Chỉ phiếu do chủ repo hoặc cộng tác viên mở mới chạy.

## Nhãn trên phiếu (máy tự gắn)

| Nhãn | Ý nghĩa |
|---|---|
| `news-plan` | Chờ Claude chia câu và chọn từ khóa tìm ảnh |
| `news-voice` | Máy đang tạo giọng đọc và tìm ảnh |
| `news-pick` | Chờ Claude chọn ảnh |
| `news-render` | Máy đang dựng video |
| `news-check` | Chờ Claude kiểm tra từng cảnh |
| `news-done` | Video xong (link ở bình luận cuối) |
| `news-fix` | Bạn yêu cầu sửa, Claude sẽ làm |
| `news-failed` | Máy gặp lỗi, Claude sẽ xem |

## File kết quả

Nhánh **`renders`**, thư mục `news/<số phiếu>/`: `video.mp4`, `subtitles.srt`, `credits.txt` (nguồn ảnh), `sheet.jpg` (ảnh các cảnh). Video của phiếu không hoạt động quá 14 ngày sẽ được dọn tự động, nên hãy tải về sớm.

## Cấu hình

- **Secrets** (Settings → Secrets and variables → Actions): `VN11_API_KEY` (giọng đọc 11labs, bắt buộc), `CLAUDE_TASK_URL` + `CLAUDE_TASK_TOKEN` (để GitHub gọi Claude ngay khi có việc; chép cùng giá trị như ở repo `japan-video-factory`, vì hai repo dùng chung một tác vụ Claude; thiếu thì phiếu chỉ được làm trong phiên chat hoặc khi bấm Gọi Claude ngay; không có lượt chạy mỗi giờ).
- **Giọng đọc tiếng Đức:** ghi mã giọng vào `prompts/news_voice.json`. Xem danh sách và nghe thử bằng workflow **Thử voice 11labs**.
- Mỗi video tốn khoảng 40–60 phút máy GitHub.

## Chạy tay (tab **Actions**)

| Workflow | Làm gì |
|---|---|
| **Video tin tức (ảnh thật)** | Chạy lại một bước cho một phiếu: `prepare` (giọng + ảnh), `search` (tìm thêm ảnh), `render` (dựng) |
| **Gọi Claude ngay** | Cho Claude bắt đầu ngay (dùng khi một bước đang chờ Claude, ví dụ sau khi hết hạn mức) |
| **Tìm ảnh (Wikimedia Commons)** | Tìm ảnh dùng tự do theo từ khóa |
| **Thử voice 11labs** | Số dư, danh sách giọng Đức, đọc thử một câu |
| **Dọn video cũ (nhánh renders)** | Dọn file của phiếu cũ (tự chạy mỗi tuần) |

Hướng dẫn cho Claude: [`CLAUDE.md`](CLAUDE.md), [`AGENT_NEWS.md`](AGENT_NEWS.md) (các bước làm video), [`AGENT_NIGHTLY.md`](AGENT_NIGHTLY.md) (điểm vào khi GitHub gọi Claude). Bàn giao: [`docs/HANDOVER.md`](docs/HANDOVER.md).
