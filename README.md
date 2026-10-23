# ARO Studio

**Hệ thống xử lý video, trích xuất & dịch thuật phụ đề, tạo giọng lồng tiếng Việt và kết xuất video Donghua Trung Quốc.**

---

## 1. Tổng Quan Kiến Trúc

ARO Studio vận hành theo mô hình phân tán không cần máy chủ trung gian (serverless / tunnel-free), sử dụng **Google Drive** làm kho lưu trữ tệp lớn và kênh trao đổi lệnh/trạng thái bất đồng bộ:

```
┌─────────────────────────────────┐                 ┌─────────────────────────────────┐
│   Android Controller (Kotlin)   │                 │     Python Worker (CLI/Colab)   │
│  - Jetpack Compose, Room DB     │                 │  - Package aro_worker (CLI aro) │
│  - Media3 Preview / Editor      │                 │  - FFmpeg, Whisper, RapidOCR    │
│  - Manual Gemini Handoff UI     │                 │  - VieNeu / Edge TTS, UVR       │
└────────────────┬────────────────┘                 └────────────────▲────────────────┘
                 │ Gửi commands bất biến                             │ Poll jobs / Đọc input
                 │ Tải kết quả / trạng thái                          │ Ghi checkpoint, FINAL.mp4
                 ▼                                                   ▼
         ┌───────────────────────────────────────────────────────────────────┐
         │                    Google Drive (Blob & Mailbox)                  │
         │  /AroStudio/                                                      │
         │    ├── workspace.json & controller/commands/<seq>-<id>.json       │
         │    ├── workers/<session_id>/ (hello.json, heartbeat.json)         │
         │    └── projects/<project_id>/jobs/<job_id>/attempts/<attempt_id>/ │
         │          (assignment, state, checkpoints, output/FINAL.mp4)       │
         └───────────────────────────────────────────────────────────────────┘
```

* **Android App:** Controller duy nhất điều phối dự án, chọn tệp, biên tập phụ đề, quản lý bảng phân vai và xem trước video kết quả.
* **Python Worker (`aro_worker`):** Module xử lý tính toán nặng (trích xuất media, nhận diện OCR/ASR, dịch thuật, tổng hợp giọng nói VieNeu/Edge, hòa âm và render FFmpeg).
* **Google Drive:** Đóng vai trò blob store và asynchronous mailbox theo đặc tả `Drive Job Protocol v1`.

---

## 2. Cấu Trúc Monorepo

```
aro-studio/
├── AGENTS.md                          # Hướng dẫn quy tắc kỹ thuật và bất biến
├── Makefile                           # Các lệnh chuẩn hóa: test, lint, doctor
├── README.md                          # Tài liệu dự án tổng quan
├── configs/
│   └── worker.example.yaml            # Cấu hình worker mẫu
├── docs/
│   ├── adr/
│   │   └── 0001-baseline.md           # Ghi nhận các quyết định kiến trúc D01–D18
│   └── architecture/                  # Toàn bộ 14 tài liệu đặc tả ARO MASTER
├── locks/
│   ├── ffmpeg-manifest.json           # Khóa phiên bản và năng lực FFmpeg
│   └── runtime-profiles.json          # Cấu hình runtime GPU / CPU / Colab
├── notebooks/
│   └── ARO_Colab.ipynb                # Google Colab bootstrap notebook
└── worker/                            # Python Worker package
    ├── pyproject.toml                 # Cấu hình dependency và CLI entry
    ├── uv.lock                        # Khóa phiên bản thư viện chính xác
    └── src/
        └── aro_worker/
            ├── cli.py                 # CLI entrypoint: aro
            └── core/
                └── doctor.py          # Chẩn đoán môi trường: aro doctor
```

---

## 3. Bắt Đầu Nhanh Với Python Worker

### Yêu Cầu Hệ Thống
* Linux x86_64
* Python 3.11 (hoặc Python 3.10+)
* Quản lý gói: `uv` (khuyên dùng) hoặc `pip`
* FFmpeg 4.4+ (có `ffprobe`, hỗ trợ `libass`, `loudnorm`)

### Cài Đặt và Kiểm Tra Môi Trường

```bash
# Cài đặt worker package
make setup

# Kiểm tra phiên bản CLI
aro --version

# Chẩn đoán môi trường thực tế (CPU, GPU, FFmpeg, dung lượng ổ đĩa)
aro doctor

# Xuất kết quả chẩn đoán dạng JSON
aro doctor --json
```

---

## 4. Tài Liệu Tham Chiếu Kiến Trúc

Toàn bộ tài liệu đặc tả chuẩn tắc ARO MASTER được lưu trữ tại `docs/architecture/`:
* `01_PRODUCT_BLUEPRINT.md`: Bản thiết kế sản phẩm và 5 cổng nghiệm thu (G0 – G4).
* `03_DRIVE_JOB_PROTOCOL.md`: Giao thức phối hợp qua Google Drive v1.
* `04_CORE_DATA_MODELS.md`: Định dạng dữ liệu chuẩn tắc, JSON Schemas và Canonical JSON (RFC8785).
* `05_WORKER_PIPELINE_SPEC.md`: Đặc tả chi tiết các giai đoạn tính toán trong DAG pipeline.
* `10_ARENA_BUILD_BOOK.md`: Sổ tay hướng dẫn chi tiết từng tác vụ từ A01 đến A28.
* `11_GOLDEN_ACCEPTANCE.md`: Tiêu chuẩn nghiệm thu video thật mốc G1.
