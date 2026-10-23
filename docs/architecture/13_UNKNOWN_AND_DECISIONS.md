# Unknowns, Conflicts và Architecture Decisions

Baseline ARO-1.0. Nguồn được đọc là static RE reports; không chạy hoặc tái reverse binaries trong lượt này. Không có production code, benchmark hay Golden result. “VERIFIED” trong 00 nghĩa verified-in-reference, không là independently runtime-tested by ARO.

## 1. Quyết định chốt

| ADR | ARO_DESIGN_DECISION | Lý do / consequence |
|---|---|---|
| D01 | Drive-first, Python worker/Colab, Android controller | đúng brief, không tunnel; polling có latency |
| D02 | one active controller, assigned worker session, immutable per-attempt namespace | Drive không đủ distributed lock guarantees; stale attempt không overwrite FINAL |
| D03 | manifest-last commit + checksum + reserved IDs | local rename khác remote atomicity; idempotent retry, không exactly-once billing |
| D04 | UUID cue identity + lineage, integer ms | edit timing không làm mất speaker/glossary assignments |
| D05 | source imported/embedded→OCR→ASR có review | embedded support của references UNKNOWN; đây là tính năng ARO mới |
| D06 | stable source context + approved memory, không previous translated history mặc định | consistency có thể cache/invalidate có kiểm soát, tránh cascade toàn phim |
| D07 | manual Gemini là provider chính thức | không API vẫn chạy, không automation app/web |
| D08 | strict JSON response by cue_id | không map theo index, không nuốt thiếu cue bằng fallback source |
| D09 | VieNeu primary + Edge fallback explicit | theo user brief; actual public model/license availability phải smoke |
| D10 | timing rewrite≤2, atempo≤1.2, review khi không fit | không cắt speech hoặc mất ý để tạo file “thành công” |
| D11 | separation optional, duck original mode rõ | UVR music model không bảo đảm clean dialogue removal |
| D12 | ASS bằng output canvas, loudnorm hai pass sau mix, full decode QC | subtitles đúng hình và final chất lượng kiểm chứng |
| D13 | cache SHA256, frozen actual model/runtime configs | tránh SHA1/timestamp ID cũ, cross-language schema fixtures |
| D14 | Worker Golden trước Android nâng cao | chứng minh outcome video thật trước đầu tư editor |
| D15 | native source/LLM data không executable | no shell interpolation/prompt actions; public interfaces only |
| D16 | không tái sử dụng thiết kế ARO cũ như source-of-truth | brief yêu cầu từ đầu; 14 file baseline mới độc lập |
| D17 | (Amendment A-2026-10-15, owner) Golden G-SOURCE/G-MEANING chấp nhận `OWNER_ACCEPTED_WITH_QA_REVIEW` (11 §9): không bắt buộc reviewer đọc tiếng Trung/song ngữ | bù bằng source QA không lỗi đổi nghĩa + translation strict validation + terminology/name consistency + owner review bản Việt cuối; chất lượng ngữ nghĩa không được bảo chứng bởi người song ngữ (rủi ro owner chấp nhận); không reviewer giả, waiver không phải PASS |
| D18 | (Amendment A-2026-10-15b, owner emergency schedule) A19–A24 Android có thể implement và test trước khi A18/G1 hoàn tất; A18 giữ nguyên checkpoint/run state, vẫn BLOCKED_EXTERNAL | status task `IMPLEMENTED_PRE_G1` / `PARTIAL_ACCEPTANCE`, không bao giờ PASS khi tiêu chí G1/live integration chưa đạt; giữ nguyên contracts A02/A04/A11, không tạo contract thay thế để né A18; test cần FINAL thật, G1 worker hoặc A03 live Drive ghi rõ `PENDING_G1` / `PENDING_LIVE`; khi G1 PASS chạy lại deferred integration tests và chỉ promote PASS với evidence; ưu tiên A19→A20→A21→A22→A23→A24 thiết yếu, A25 optional không được làm chậm app Android chạy được |

## 2. Unknown registry có owner và cách đóng

| ID | UNKNOWN | Impact / owner task / exit evidence |
|---|---|---|
| U01 | PP-OCRv6 official models/API/license và accuracy donghua | OCR; A08; official manifest + frame tests, hoặc ADR chọn public alternative |
| U02 | VieNeu v3-Turbo/package3.2.3 availability/weights+codec license | core TTS; A12; official pinned compatible distribution + five-line smoke; Edge-only không đóng U02 |
| U03 | UVR model source/license/DSP và dialogue residual | optional clean audio; A14; model card+alignment+listening, otherwise duck original |
| U04 | exact default pyannote models EZ / voice classifier architecture | optional; A25; never copy proprietary classifier; manual cast resolves MVP |
| U05 | public API model choices, context/cost/rate limits | translation; A10; configured provider capability smoke, manual default nếu không có API |
| U06 | Drive conditional updates/CAS support usable cross SDK | protocol; intentionally not relied on; A03 validates reserved IDs/idempotency; active-active out of scope |
| U07 | OAuth drive.file cross-client visibility with Colab | sync blocker; A03/A20 live exact-ID access test, explicit supported consent solution |
| U08 | Colab actual CUDA/cuDNN/session/disk budgets | runtime; A01/A27; doctor current session and CPU lane, no fixed SLA |
| U09 | source donghua thật/rights/reference annotation | Golden; A18; case manifest approved and source hash; none supplied for architecture turn |
| U10 | translation semantic quality/voice MOS/OCR CER | product; A18/A27 measurements+human review (hoặc owner acceptance theo 11 §9/D17), not inferred from package names |
| U11 | Android pinned version compatibility/current target policy | app; A19/A28 exact dependency matrix build+devices |
| U12 | 4h performance/storage/network quota | hardening; A27 benchmark, no promise until run |

Unknown có safe fallback thì tiếp tục task độc lập. Unknown chặn dependency phải task BLOCKED với evidence, không thay mock vào production. Dependency pins là deliverable G0 của Arena vì cần chạy môi trường/model thật; kiến trúc này không giả đã tạo lock verified.

## 3. Conflicts phát hiện trong sources

1. EZMaxSub THREE_WAY_COMPARISON/STRENGTHS_WEAKNESSES gọi GenMedia Tkinter/VLC, không memory/diarization/local TTS. GenMedia UI_ARCHITECTURE/ASR/FILM_MEMORY/INVENTORY dẫn PySide6/MPV, film memory, sherpa diarization, VieNeu. Ưu tiên evidence chuyên biệt GenMedia; không dùng bảng so sánh làm fact.
2. GenMedia embedded subtitle support UNKNOWN ở SUBTITLE_EXTRACTION; WORKER_HTTP_PROTOCOL có prose “nhúng sẵn”. Không đủ chứng minh extractor thực tế. ARO embedded-first là D05 mới.
3. GenMedia HTTP endpoint count/token creation/health auth và synchronous response mâu thuẫn giữa NETWORK/WORKER_HTTP_PROTOCOL/EVIDENCE_INDEX. Chỉ học process isolation, không copy wire protocol private.
4. Context docs nói memory file riêng hoặc project state; deep-dive nêu project.json. Scope/fields đáng tin hơn file-path khái quát; ARO chọn immutable memory snapshots riêng.
5. EZ profile count11/12 và PROGRESS thừa nhận mới preview prompts; chỉ verify sự tồn tại genre-profile asset, không claim đã hiểu mọi proprietary prompt.
6. FFmpeg “7.1” vs avcodec62 (version mapping không nhất quán); package numbers và speculative cloud model IDs không được coi là current availability.
7. Broad license assertions (all OSS MIT/Apache, dynamic link exempt GPL, edge-tts GPL) không đủ evidence. ARO kiểm tra official LICENSE cho artifact thực, không tuyên bố pháp lý theo suy đoán.
8. Old ARO specs gợi ý VieNeu ASR, 25min chunks, hash compatibility GenMedia, Playwright, tunnel, FFmpeg-Kit, silence/force-fit. Không có runtime evidence xác nhận; không áp vào baseline này. VieNeu chỉ TTS; no reuse proprietary cache/code.
9. “Không tìm thấy HTTP server” trong EZ static strings không chứng minh không bao giờ có server. Giữ giới hạn phương pháp; app ARO không phụ thuộc kết luận phủ định đó.

## 4. Design tradeoffs chấp nhận

Single controller và manual assignment làm UI cần bước chọn worker nhưng loại bỏ race shared FINAL. Manual Gemini tăng thao tác, bù lại không đòi API. Review gates có thể dừng job, bù lại không giấu thiếu thoại. OCR4fps tốn hơn sampling thưa nhưng giữ recall; refine/cache giảm chi phí. Full render restart có thể tốn thời gian, nhưng upstream resume granular và code v1 đơn giản kiểm chứng được. Direct Drive files nhiều có overhead; packing stage được trì hoãn tới hardening sau correctness.

## 5. Handoff / change policy

Arena bắt đầu A01 trong 10 từ repo trống. Không lấy history ngoài baseline làm yêu cầu ngầm. Task output gồm files, commands/tests, observed results, artifact hashes và next task. Nếu phải đổi schema/protocol/default, ghi ADR nối tiếp D18+, cập nhật 03/04/domain/tests và compatibility. Không tự biến NOT_RUN thành PASS. Sau khi bộ 14 tài liệu được lưu và đọc lại trên Drive, công việc kiến trúc kết thúc; production implementation là lượt riêng.
