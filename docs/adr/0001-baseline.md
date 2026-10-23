# ADR 0001: Kiến Trúc Nền Tảng ARO Studio Baseline v1.0

* **Trạng thái:** Chấp thuận (Accepted)
* **Ngày quyết định:** 2026-10-10 (Cập nhật sửa đổi D17 & D18: 2026-10-15)
* **Tài liệu tham chiếu:** `docs/architecture/13_UNKNOWN_AND_DECISIONS.md`, `docs/architecture/01_PRODUCT_BLUEPRINT.md`

---

## 1. Bối Cảnh (Context)

ARO Studio là hệ thống phần mềm xử lý video donghua Trung Quốc: trích xuất phụ đề nguồn (từ phụ đề nhúng, file đính kèm, OCR hardsub hoặc ASR âm thanh), tổ chức bảng thuật ngữ/nhân vật, dịch sang tiếng Việt, tạo giọng đọc lồng tiếng (TTS), hòa âm và xuất video cuối cùng có phụ đề burn-in (`FINAL.mp4`).

Hệ thống cần phục vụ người dùng trên thiết bị di động (Android) kết hợp năng lực tính toán nặng của máy tính Linux/Google Colab, đồng thời không phụ thuộc vào hệ thống máy chủ trung gian đắt đỏ hoặc các giải pháp tunnel mạng thiếu ổn định.

---

## 2. Các Quyết Định Kiến Trúc Cốt Lõi (D01 – D18)

| Mã | Quyết Định | Rationale & Ý Nghĩa Kỹ Thuật |
|---|---|---|
| **D01** | **Google Drive làm tầng giao tiếp chính (Drive-first)** | Android và Python Worker trao đổi tệp và trạng thái qua Google Drive v1. Không cần máy chủ trung gian, không cần tunnel/port-forwarding. Chấp nhận độ trễ polling để đổi lại tính đơn giản và độ tin cậy. |
| **D02** | **Một Controller duy nhất & Session Fencing** | Tại mỗi thời điểm chỉ có 1 controller phát lệnh cho workspace. Worker hoạt động theo từng `worker_session_id` UUIDv4 với heartbeat định kỳ; controller gán attempt cho đúng session để triệt tiêu tình trạng xung đột ghi tệp kết quả. |
| **D03** | **Cam kết nguyên tử kiểu Manifest-Last** | Sử dụng Google Drive `files.generateIds` để đặt trước file ID. Chỉ coi dữ liệu là hoàn thành (commit) khi tệp manifest tổng chứa mã băm SHA-256 được tải lên thành công. |
| **D04** | **Danh tính Cue bất biến (UUIDv4) & Mốc thời gian nguyên** | Mỗi câu thoại có `cue_id` cố định kèm phả hệ (`parent_cue_id`, `split_from`). Thời gian được lưu dưới dạng số nguyên mili-giây (`int64`), tuyệt đối không dùng số thực `float`. |
| **D05** | **Thứ tự ưu tiên nguồn phụ đề có kiểm duyệt** | Ưu tiên phụ đề nhập tay (SRT) → phụ đề nhúng (embedded text) → OCR hardsub → ASR Whisper. Luôn có bước người dùng xác nhận trước khi dịch. |
| **D06** | **Bộ nhớ phim (Film Memory) & Ngữ cảnh ổn định** | Dịch theo từng batch độc lập có ngữ cảnh cố định và bảng thuật ngữ khóa, không đẩy toàn bộ lịch sử dịch trước đó vào prompt nhằm tránh hiện tượng sai lệch dây chuyền và tối ưu cache. |
| **D07** | **Manual Gemini Handoff là nhà cung cấp chính thức** | Cho phép người dùng sao chép prompt và dán kết quả JSON trực tiếp từ web/app Gemini mà không bắt buộc phải có API key trả phí. |
| **D08** | **Xác thực cấu trúc phản hồi nghiêm ngặt theo `cue_id`** | Kết quả dịch phải ánh xạ chính xác theo `cue_id`, không cho phép bỏ qua câu thoại hay suy luận theo chỉ mục mảng. |
| **D09** | **VieNeu TTS chính, Edge-TTS dự phòng** | VieNeu là engine TTS tiếng Việt chính theo yêu cầu sản phẩm; Edge-TTS là phương án dự phòng tường minh. |
| **D10** | **Chính sách khớp thời lượng giọng đọc (Audio Fitting)** | Tối đa 2 lần viết lại câu ngắn hơn, tốc độ phát tối đa tăng 1.2x (`atempo <= 1.2`). Nếu vẫn vượt quá thời lượng thì chuyển sang hàng đợi xem xét thủ công, không tự cắt cụt âm thanh. |
| **D11** | **Tách nhạc nền UVR tùy chọn & Hạ âm lượng nền (Ducking)** | Khi không có GPU hoặc mô hình UVR không khả dụng, hệ thống chuyển sang chế độ giảm âm lượng nền (ducking) tự động. |
| **D12** | **Phụ đề ASS theo canvas gốc & Thẩm định giải mã toàn diện** | Phụ đề ASS căn chuẩn theo độ phân giải nguồn. Video kết quả phải vượt qua kiểm định giải mã toàn bộ khung hình và độ lớn âm thanh chuẩn -16 LUFS. |
| **D13** | **Cache Content-Addressed theo SHA-256** | Khóa cache được tính toán xác định từ Canonical JSON (RFC8785) của đầu vào, tham số và phiên bản mô hình, đảm bảo tính tái lập 100%. |
| **D14** | **Chứng minh Worker Golden (G1) trước khi làm UI nâng cao** | Phải có tệp `FINAL.mp4` thực tế từ video thật trước khi đầu tư sâu vào giao diện người dùng. |
| **D15** | **Dữ liệu văn bản nguồn và phản hồi LLM không có quyền thực thi** | Không đưa nội dung phụ đề vào shell interpolation hay biến môi trường; triệt tiêu nguy cơ prompt injection làm hỏng pipeline. |
| **D16** | **Không tái sử dụng mã nguồn/tài liệu đóng cũ làm source-of-truth** | Xây dựng dự án hoàn toàn sạch (clean-room) dựa trên 14 tài liệu chuẩn tắc đã ban hành. |
| **D17** | **Cơ chế chấp thuận Golden `OWNER_ACCEPTED_WITH_QA_REVIEW`** | Cho phép người sở hữu sản phẩm phê duyệt bản dịch và video Golden sau khi đã vượt qua các công cụ QA nghiêm ngặt, không ép buộc phải có người bản ngữ Trung Quốc thẩm định. |
| **D18** | **Quy chế phát triển Android song song có kiểm soát** | Cho phép triển khai và kiểm thử các module Android trước G1 với nhãn trạng thái `IMPLEMENTED_PRE_G1`, không chặn tiến độ giao diện nhưng chỉ cấp chứng nhận `PASS` khi G1 đã hoàn thành. |

---

## 3. Hệ Quả (Consequences)

* **Tích cực:** Hệ thống tách rời rõ ràng giữa tầng hiển thị di động và tầng tính toán nặng; không phụ thuộc máy chủ lưu trữ; dữ liệu có thể khôi phục sau sự cố ngắt quãng mạng hay Colab timeout; loại bỏ hoàn toàn các lỗi sai lệch do tính toán số thực.
* **Đánh đổi:** Polling qua Google Drive có độ trễ tự nhiên (10s–30s); quy trình Manual Handoff đòi hỏi thao tác của người dùng nhiều hơn so với API tự động trực tiếp.
