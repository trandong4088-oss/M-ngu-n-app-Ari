# Golden Acceptance và Release Gates

**ARO_DESIGN_DECISION**. Đây là kế hoạch nghiệm thu, không báo cáo đã chạy. Trạng thái mọi gate tại bàn giao kiến trúc: **NOT_RUN**. Không có video test được user cung cấp trong lượt thiết kế; Arena phải chọn video donghua thật có quyền xử lý khi vào A18.

## 1. G1 bắt buộc trước UI nâng cao

Một video donghua Trung Quốc thật dài3–10 phút, có thoại≥30 cues, nhạc/nền và ít nhất2 nhân vật nếu thử casting. Không dùng video màu + sine wave làm Golden sản phẩm; synthetic chỉ integration fixture. Chọn clip có quyền sử dụng, ghi source Drive ID, SHA-256, duration, streams, rights note và timestamp đoạn gốc. Không đưa media có bản quyền vào public repo.

Production worker package + pinned models/provider thật → subtitle nguồn → dịch Việt → TTS thật → master mix → burn ASS → FINAL.mp4 → Drive. Cho phép manual Gemini đúng production contract và người dùng sửa nguồn/dịch/casting theo UI/CLI dự kiến; ghi lại interventions. Không thay stage thật bằng mock rồi gắn nhãn production.

## 2. Golden kit

Arena tạo `tests/golden/cases/donghua-001/case.json` (không chứa secrets) và private Drive artifacts: source_ref, expected_source_annotations.json, approved_memory.json, frozen config, worker/runtime lock hashes, requests/responses/provenance, final cues/SRT/ASS/TTS manifest/master_audio, result.json, validation.json, human_review.md, restart_evidence.json, logs đã redacted.

Annotations gồm tập required utterances/cue lineage được nghe/đọc kiểm tra, không lấy output ASR tự đánh mình đúng. Mỗi reference interval có source text/meaning và speaker nếu chắc. OCR chữ sign/song được phân loại; exclusions có reviewer/reason. *(Amendment A-2026-10-15, §9: annotations cũng có thể agent-derived và QA-checked dưới acceptance_basis OWNER_ACCEPTED_WITH_QA_REVIEW, ghi rõ human_reviewed=false, independent_oracle=false; reviewer/annotator ghi nhãn basis, không ghi tên người không review.)* Golden manual annotations là oracle coverage, source normalized count đơn độc không chứng minh không mất thoại.

## 3. PASS checklist

| Check ID | Pass criterion | Evidence / người thực hiện |
|---|---|---|
| G-SOURCE | ≥95% reference utterances nhận ra trước sửa; sau review100% required utterances có cue, không thiếu đoạn thoại hoàn chỉnh | source quality report và annotated timeline; reviewer hiểu Trung (HUMAN_REVIEW) **hoặc** OWNER_ACCEPTED_WITH_QA_REVIEW đủ điều kiện §9 |
| G-STRUCT | translated IDs = required_translation_ids; no missing/extra/duplicate IDs; lineage covers all required parents | validator JSON |
| G-MEANING | full review clip3–10 phút: không sai ý nghiêm trọng/phủ định/số/cảnh giới; minor fluency issues≤5% cues | bilingual human review có cue IDs (HUMAN_REVIEW) **hoặc** OWNER_ACCEPTED_WITH_QA_REVIEW đủ điều kiện §9 (owner review bản Việt cuối, cue IDs) |
| G-MEMORY |100% tên/thuật ngữ approved locked đúng; directed pronouns đúng ở cues có listener confirmed | glossary report+review |
| G-READ |≥95% cues CPS≤17,100%≤22;≤2 lines; no clipped glyph, safe margins; hiếm waived timing note không che unreadable cue | metrics + sampled frames + phone review |
| G-TTS |100% required_tts cues có speech artifact thật, đúng actual assigned voice/lang; no silence placeholders | TTS manifest + nghe toàn clip |
| G-FIT | speech onset sai≤100ms so assigned start khi không annotated exception; no unintended overlap>50ms/no cut words; atempo≤1.2 | fit metrics+listen; overlap dialogue explicit annotation |
| G-AUDIO | voice rõ, nền/SFX nghe được tại annotated sections; final -16±1LU, TP≤-1dBTP; no clipping/click/drift | loudness JSON+listen review |
| G-VIDEO | H.264/AAC/yuv420p/48k stereo; duration delta≤max100ms,2frames; moov before mdat; full decode exit0 | ffprobe/decode/atom logs |
| G-DRIVE | FINAL binary ID under project output attempt, checksum readback khớp; accepted active generation manifest | metadata+download SHA256 |
| G-RESUME | kill worker sau ít nhất1 dịch batch+5 TTS cues committed; runtime mới resume, các units đó không gọi lại; pending handoff không mất | call counters/logs/checkpoint hashes |
| G-FENCE | worker cũ hoàn tất muộn không được ACCEPT hoặc đổi output hiện tại | controlled two-session test |
| G-PUBLISH | status SUCCEEDED chỉ sau mandatory checks và controller acceptance | event/command timeline |

“Decode toàn bộ” khác “mở được trên player”. “Voice đủ” khác “có audio stream”. Nếu final derived from duck original, mark output mode DUCK_ORIGINAL; pass nền nghe được không có nghĩa đã chứng minh clean separation. Mẫu bắt buộc clean-dub cần additional stem leakage review.

## 4. Nhánh và edge cases ngoài Golden chính

| Fixture/case | Required gate |
|---|---|
| embedded zh full track + en/forced track cạnh tranh | resolver chọn đúng, absolute stream index, không dùng forced-only tự động |
| PGS bitmap subtitle, không burn trong pixels | không ffmpeg text extraction giả; yêu cầu ASR/import hoặc supported bitmap adapter |
| hardsub nhỏ, câu<500ms, ROI khác bottom | OCR4fps+refine và manual review bắt hụt, không silently drop |
| ASR chunk boundary repeated phrase | không duplicate/drop words, global offsets đúng |
| silence/music-only input | không hallucinate required dialogue; no -inf loudnorm crash |
| rotation90/SAR/VFR/nonzero audio start | canvas/ASS đúng, AV sync đầu-cuối |
| source thiếu audio nhưng imported SRT | policy explicit, no-source-audio result không giả nền có |
| text chứa braces/backslashes/emoji/dấu tổ hợp | safe ASS, glyph coverage, no injected override |
| repeated Vietnamese text khác cue_id | được giữ |
| too-long TTS / provider unavailable | WAITING_USER/fallback recorded, no success bằng silence |

## 5. Chaos/resume matrix

Inject crash trước blob commit, sau blob/trước manifest, sau manifest/trước state, sau response nhận/trước ack, giữa mix/render, sau final upload/trước result, sau ACCEPT/trước shortcut. Mỗi case ghi operation counts và expected reused units. Auth401, quota403, rate429, Drive page2 chứa target, same-name duplicate, corrupt cached bytes, stale response/hash, clock skew±5 phút. Không suy thứ tự lệnh từ wall clock; monotonic reader heartbeat và command seq phải chịu được clock skew.

## 6. G2/G3 Android acceptance

Android từ source picker đến accepted FINAL play, điện thoại không cần biết Worker URL. Kill app giữa upload và sau Run trước ack, reopen không tạo duplicate job. Background WorkManager delayed vẫn UI biết trạng thái stale khi reopen. Manual Gemini Share/Copy→Paste/import strict validation→resume không automation. Editor sửa1cue đo actual provider/TTS calls; font-only edit không gọi model. Media3 phát private Drive video qua download hoặc authenticated ranges; seek đầu/giữa/cuối. Room migration giữ draft, glossary, cue IDs, outbox.

G1 trước Android có CLI final playback/decode; G2 mới chứng minh Android preview thực, không đánh G1 đầy đủ product release.

## 7. G4 Long-video / release

Bench30/120/240 phút với D/cue_count/model/hardware cố định, decode full, AV drift cuối≤100ms, required IDs100%, disk/RAM/VRAM trong configured budget; crash resume reuse valid units. Không dùng MP4 byte equality cross-encoder/nondeterministic model làm regression oracle. Save content hashes để xác minh artifact hiện tại, compare semantic metrics để regression.

Release package: signed APK/AAB, worker wheel, verified locks/model manifests/licenses/font notices, runbook Colab/CLI, schema migration/backward compatibility note, SBOM, SHA256SUMS, doctor report, G1–G4 evidence. Telemetry default off; logs redacted; token/secret scan passed. Không publish store hoặc deploy public tự động trong taskbook.

## 8. Reporting rule

Report PASS chỉ khi mọi mandatory check PASS; WARN phải có disposition; NOT_RUN/unknown required=BLOCKED. `golden_report.json` includes case_id/source_sha256/config_sha256/worker_commit/runtime_lock_hash, check statuses, measurements, artifact IDs, reviewer/time, failed cue IDs. Human reviewer identity là người thực sự review, không tự điền tên giả. G-SOURCE/G-MEANING ghi `acceptance_basis` ∈ {HUMAN_REVIEW, OWNER_ACCEPTED_WITH_QA_REVIEW}; basis thứ hai chỉ PASS khi đủ mọi điều kiện §9, thiếu điều kiện → BLOCKED, có lỗi đổi nghĩa chưa sửa → FAIL. Nếu cần user review clip, Arena đưa concrete output cùng cue issues và giữ gate pending.

## 9. Amendment A-2026-10-15 — OWNER_ACCEPTED_WITH_QA_REVIEW (owner architecture decision)

Quyết định của project owner (2026-10-15): ARO Studio **không yêu cầu reviewer đọc tiếng Trung hay reviewer song ngữ** cho Golden gate. G-SOURCE và G-MEANING có hai acceptance basis hợp lệ:

1. `HUMAN_REVIEW`: như bảng §3 (reviewer thật, có tên và thời điểm).
2. `OWNER_ACCEPTED_WITH_QA_REVIEW`: check chỉ **PASS** khi đủ **tất cả** điều kiện sau:
   - a. **Source QA:** QA đối chiếu video với bảng source review.
     - Không có lỗi OCR/ASR/timing làm đổi nghĩa đáng kể khi dịch.
     - Không thiếu đoạn thoại hoàn chỉnh (`missed_required` rỗng).
     - Được phép có lỗi nhỏ (typo, sai OCR, lệch timing) nếu không đổi nghĩa.
     - Owner chấp nhận kết luận QA.
   - b. **Translation strict validation PASS:** G-STRUCT PASS (translated IDs = required IDs, không thiếu/thừa/trùng, lineage đủ) và mọi response dịch qua strict validator.
   - c. **Terminology/name consistency PASS:** G-MEMORY PASS (100% thuật ngữ/tên approved locked đúng).
   - d. **Owner review bản tiếng Việt cuối:** owner xem bản Việt của output cuối (phụ đề/thoại FINAL, hoặc bảng cue zh + vi đúng với FINAL).
     - Owner ghi kết luận, thời điểm và cue IDs có vấn đề.
     - Không còn sai ý nghiêm trọng/phủ định/số/cảnh giới chưa sửa.

**Thiếu điều kiện hoặc có lỗi:**
- Thiếu bất kỳ điều kiện nào → check **BLOCKED** (nêu điều kiện thiếu).
- Có lỗi đổi nghĩa chưa sửa → **FAIL**.
- Không có trạng thái "waiver = PASS".

**Ghi nhận:**
- `golden_report.json` lưu cho G-SOURCE/G-MEANING: `acceptance_basis`, tham chiếu quyết định owner, QA, validator/glossary report, và owner final review (kèm thời điểm).
- `confirmed_by` / `annotator` / reviewer của exclusion ghi nhãn basis, không ghi tên người không review; ghi `human_reviewed=false`.
- Annotations agent-derived không phải independent oracle. Tỉ lệ "nhận ra trước sửa" (≥95%) chỉ báo như measurement không độc lập, không chặn PASS dưới basis này.

**Không đổi:**
- G-READ phone review và listening review của G-TTS/G-FIT/G-AUDIO vẫn do người thật (owner/QA) thực hiện, ghi thời điểm.
- G-STRUCT, G-MEMORY, G-VIDEO, G-DRIVE, G-RESUME, G-FENCE, G-PUBLISH giữ nguyên tiêu chí §3; báo cáo vẫn theo §8.

**Lịch sử:** bằng chứng trước amendment (A18 ngày 2026-10-15 ghi G-SOURCE = OWNER_WAIVED) giữ nguyên, không sửa. Việc đánh giá lại theo §9 là một record mới.
