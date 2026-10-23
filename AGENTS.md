# ARO Studio — Agent & Engineering Guidelines

Tài liệu này xác định các quy tắc bất biến, quy trình kiểm thử và nguyên tắc phát triển bắt buộc cho tất cả kỹ sư phần mềm và agent tham gia xây dựng **ARO Studio**.

---

## 1. Nguyên Tắc Tối Thượng (Non-Negotiable)

1. **Không Chức Năng Giả (Zero Fake Functionality):**
   - Tuyệt đối không dùng `TODO`, `stub`, `placeholder`, hàm rỗng hoặc kết quả hard-coded để giả vờ một tính năng đã hoàn thành.
   - Không dùng `sleep()` hay timer để mô phỏng tiến độ tính toán.
   - Không tạo ID giả, tệp giả hoặc phản hồi API giả trong luồng thực thi production.
   - Nếu một chức năng chưa sẵn sàng hoặc thiếu dependency: Phải trả về trạng thái `BLOCKED` hoặc `NOT_IMPLEMENTED` có lý do hành động rõ ràng. Mock chỉ được phép xuất hiện trong test suite có nhãn riêng, không bao giờ được đưa vào mã nguồn production.

2. **Bằng Chứng Thực Tế (Execution Over Claims):**
   - Chỉ được tuyên bố `PASS` khi lệnh kiểm thử tương ứng đã thực sự được thực thi trong môi trường và trả về kết quả đạt yêu cầu.
   - Phân biệt minh bạch 4 trạng thái:
     - `PASS`: Tiêu chí nghiệm thu đã chạy và có bằng chứng đạt yêu cầu.
     - `FAIL`: Đã chạy kiểm thử và thất bại.
     - `BLOCKED`: Thiếu điều kiện tiên quyết (ví dụ GPU, model weights, API key của người dùng).
     - `NOT_RUN`: Chưa chạy kiểm thử.

3. **Bảo Mật Thông Tin Xác Thực (Zero Secrets in Source):**
   - Tuyệt đối không lưu API key, OAuth token, mật khẩu, file credentials vào source code, logs, test fixtures hoặc Git.
   - Sử dụng biến môi trường hoặc cơ chế nạp credentials từ runtime do người dùng cấu hình tại thời điểm chạy.

4. **Kiểm Soát Chi Phí:**
   - Không tự ý kích hoạt các dịch vụ AI trả phí hoặc cloud provider nếu cấu hình job không cho phép cụ thể.

---

## 2. Thứ Tự Triển Khai Taskbook (10_ARENA_BUILD_BOOK.md)

Dự án được xây dựng tuần tự theo các cổng bàn giao nghiêm ngặt:

* **Cổng G0 (Nền tảng & Hợp đồng dữ liệu):**
  - `A01`: Khởi tạo monorepo và runtime reproducible (`aro_worker`, CLI `aro`, `aro doctor`).
  - `A02`: Schemas JSON Schema Draft 2020-12, Pydantic v2 strict models, Canonical JSON RFC8785.
  - `A03`: Google Drive Storage Adapter thực tế (generateIds, resumable upload, pagination).
  - `A04`: Controller, job lifecycle, command outbox và worker session fencing.
  - `A05`: Content-addressed Cache 2 tầng và Stage Runner.
* **Cổng G1 (Worker Pipeline & Golden Run):**
  - `A06` – `A09`: FFmpeg wrapper, Subtitle resolver, OCR Hardsub, ASR Whisper.
  - `A10` – `A15`: Memory/Glossary, Translation (Manual Gemini / API), TTS (VieNeu/Edge), Audio fitting, UVR/Ducking, Loudnorm 2-pass (-16 LUFS).
  - `A16` – `A18`: ASS render ra `FINAL.mp4`, full-decode QC validation và Golden test trên video donghua thật 3–10 phút.
* **Cổng G2 & G3 (Android Controller & Editor):**
  - `A19` – `A25`: Scaffold Android (Compose, Room, Media3), Google OAuth, File picker, Job control, Manual Gemini Handoff UI, Subtitle/Lineage editor, Preview player.
* **Cổng G4 (Gia cố & Đóng gói phát hành):**
  - `A26` – `A28`: Khôi phục lỗi mạng, benchmark video dài (30/120/240 phút), release candidate.

---

## 3. Kiến Trúc Cốt Lõi và Quy Chuẩn Kỹ Thuật

* **Phân định ranh giới:**
  - Android = Controller, Editor, Preview (Single active controller, không host ML model, không chạy FFmpeg, không mở tunnel).
  - Python Worker = Toàn bộ pipeline xử lý media nặng (CLI `aro`, chạy trên Linux x86_64 hoặc Colab).
  - Google Drive = Blob store và mailbox trao đổi trạng thái bất đối xứng (giao thức `Drive Job Protocol v1`).
* **Định dạng dữ liệu chuẩn:**
  - Định dạng trao đổi: JSON UTF-8 `snake_case`, Canonical JSON RFC8785 (JCS).
  - `cue_id`: UUIDv4 bất biến kèm phả hệ (`lineage`), không bao giờ sinh từ timestamp.
  - Mốc thời gian: Số nguyên 64-bit milliseconds (`int64`), không dùng số thực `float`.
  - Cam kết tệp kết quả: Nguyên tắc "Publish-manifest-last". Tệp `FINAL.mp4` chỉ được công nhận sau khi vượt qua bước kiểm định giải mã toàn bộ (full-decode check) và manifest tổng đã được commit.
