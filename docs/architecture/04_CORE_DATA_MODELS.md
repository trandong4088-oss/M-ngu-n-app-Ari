# Core Data Models v1

**ARO_DESIGN_DECISION**. Wire format là snake_case JSON UTF-8. Python Pydantic v2 strict; Kotlin kotlinx.serialization DTO tách Room entities. JSON Schema Draft 2020-12 trong `contracts/v1/` là authority. Không dùng float cho timeline, money, progress counters hoặc hash-critical config.

## 1. Scalar rules

`Id`: UUIDv4 lowercase; `Digest`: 64 lower hex; `DriveId`: opaque nonempty ≤256 chars; `Ms`: int64 ≥0; `Utc`: RFC3339 UTC. `Lang`: BCP47 (`zh-Hans`, `zh-Hant`, `vi`); Whisper adapter map zh-* → zh. `RatioMilli`: integer 1000=1.0. dB config = integer milli-dB. Optional field explicit null khi chưa biết. Không NaN/Infinity, không implicit string→number coercion.

`canonical_json`: RFC8785/JCS với domain data đã NFC-normalize, không float; bytes UTF-8. arrays giữ thứ tự. Digest theo `SHA256(domain_tag + NUL + canonical_bytes)`. Không tự normalize source video bytes; text raw giữ nguyên ở raw artifact, text normalized có version. Có cross-language fixtures cho Unicode combining marks, key order, null, emoji, int64-safe timeline. Không dùng API key/access token hoặc file path tuyệt đối trong hash.

## 2. Các record chuẩn tắc

Notation: `?` nullable; `[]` array; mọi field dưới đây required trừ `extensions` có default `{}`. Arena tạo một schema/file cho mỗi record gốc; shared definitions dùng `$defs`.

| Record | Fields / invariants |
|---|---|
| Workspace | schema_version, workspace_id, controller_id, root_drive_id, registry:map[string,DriveId], required_features: string[], created_at |
| ProjectRevision | schema_version, project_id, revision_id, parent_revision_id?, title, source:ArtifactRef, source_language, target_language=vi, cue_dataset_ref?, memory_ref?, pipeline_config_ref:ArtifactRef, created_at, author_controller_id |
| JobRequest | schema_version, job_id, project_id, revision_id, revision_ref:ArtifactRef, config:PipelineConfig, config_sha256, source_sha256, requested_output:FINAL_MP4, retry_of_job_id?, created_at |
| AttemptAssignment | schema_version, job_id, attempt_id, generation:int≥1, worker_session_id, controller_id, command_seq:int≥1, request_sha256, lease_ttl_s, created_at |
| ArtifactRef | artifact_id:Digest, drive_file_id:DriveId, name, mime_type, byte_size:int64, sha256:Digest, producer_stage, stage_version, input_key:Digest, schema_version?, duration_ms?, created_at |
| StageState | stage_id, status, stage_attempt:int≥0, completed_units:int64, total_units:int64?, unit, cache_hit:bool, started_at?, finished_at?, checkpoint_ref?, error:AroError?, wait_reason? |
| JobState | schema_version, job_id, attempt_id, generation, event_seq, observed_command_seq, status, stages:StageState[], updated_at, result_ref? |
| Checkpoint | schema_version, job_id, attempt_id, stage_id, stage_version, input_key, dependency_artifact_ids:Digest[], outputs:ArtifactRef[], validator_version, validation_ref, committed_at |
| ResultManifest | schema_version, job_id, attempt_id, generation, revision_id, request_sha256, final_video:ArtifactRef, source_cues_ref, final_cues_ref, subtitle_srt:ArtifactRef, subtitle_ass:ArtifactRef, tts_manifest:ArtifactRef, master_audio:ArtifactRef, validation:ArtifactRef, provenance:ArtifactRef, completed_at |
| PublishedResult | schema_version, publish_id, controller_id, command_id, job_id, attempt_id, generation, result_ref:ArtifactRef, final_sha256, verified_at |

ArtifactRef `artifact_id` là hash nội dung blob; `input_key` là hash recipe, khác nhau. Một input_key có thể tạo nhiều blob ở model không deterministic; manifest chọn output đã accepted, không ghi đè blob cũ. `byte_size=0` chỉ hợp lệ với loại artifact cho phép rỗng, không WAV/MP4/JSON manifest.

## 3. Cue dataset và lineage

`CueDatasetManifest`: schema_version, dataset_revision_id, project_id, source_sha256, normalizer_version, duration_ms, pages:[ArtifactRef], cue_count, required_translation_ids:[Id], required_tts_ids:[Id], exclusions:[{cue_id,reason,confirmed_by,confirmed_at}], lineage_ref?, quality_report_ref.

```json
{
  "cue_id": "54f15f76-75d2-4cf8-bfe4-0957b0189f75",
  "revision": 1,
  "start_ms": 1200,
  "end_ms": 3400,
  "source_text": "师兄，等等！",
  "translated_text": "Sư huynh, chờ đã!",
  "tts_text": "Sư huynh, chờ đã!",
  "kind": "dialogue",
  "source_method": "ocr",
  "source_confidence_milli": 930,
  "speaker_id": null,
  "listener_id": null,
  "character_id": null,
  "voice_assignment_id": null,
  "required_translation": true,
  "required_tts": true,
  "text_locked": false,
  "timing_locked": false,
  "source_evidence_ids": ["frame-00012"],
  "words": [],
  "flags": [],
  "parent_cue_ids": []
}
```

`kind`: dialogue/narration/sign/song/unknown. `source_method`: imported/embedded_text/ocr/asr/manual. `flags` là issue codes, không điều khiển pipeline thay required fields. Confidence là heuristic/model score, không xác suất dịch đúng. `words` có text/start_ms/end_ms/confidence_milli?; nằm trong source timeline. Cue interval half-open [start,end), 0≤start<end≤duration. Overlap khác speaker có thể hợp lệ; overlap không rõ → review. Sort `(start_ms,end_ms,cue_id)`; thứ tự SRT index chỉ tạo khi export.

Edit text hoặc time giữ cue_id, revision tăng. Split sinh hai UUID, cả hai parent_cue_ids=[old]; merge sinh UUID mới parents=[a,b]. Dataset mới phải có lineage coverage: mỗi required parent được thay bằng children hợp lệ hoặc exclusion do người dùng xác nhận. Không âm thầm giảm required count. Word timestamps cũ invalid nếu source text/time thay không còn map được; không dùng Chinese word timing để giả làm karaoke tiếng Việt.

## 4. Media/chunk/voices

`MediaProbe`: source_sha256, duration_ms, format_name, video_stream_index, width_encoded, height_encoded, rotation_deg∈{0,90,180,270}, display_width, display_height, sample_aspect_ratio:{num,den}, avg_frame_rate:{num,den}, time_base:{num,den}, video_start_ms, audio_streams:[{index,language?,codec,channels,sample_rate,start_ms,duration_ms?}], subtitle_streams:[{index,language?,codec,is_text,disposition}], color_transfer?, color_primaries?, hdr_detected, variable_frame_rate, ffprobe_version.

`AudioChunk`: chunk_id:Digest, core_start_ms/core_end_ms, decode_start_ms/decode_end_ms, audio_ref, sample_rate, channel_count, global_offset_ms, model_ref, config_sha256. Decode interval chứa core interval; ownership word theo midpoint nằm trong core, boundary conflict mới cần align; không drop trùng theo text toàn phim.

`VoiceAssignment`: assignment_id, character_id?, fallback_for_unknown:bool, primary:{engine_id,model_revision,voice_id}, fallback:{engine_id,voice_id}?, rate_milli=1000, enabled. Voice catalogue mỗi voice có display_name/language/style/preview_ref?/license_ref?; gender label tùy chọn do catalogue cung cấp, không danh tính thật.

`TtsCueResult`: cue_id, cue_revision, effective_text, text_sha256, requested_voice, actual_voice, raw_ref, fit_ref?, measured_ms, available_ms, tempo_milli, rewrite_attempts, status:VALID/NEEDS_REVIEW/FAILED, reason?, fit_key. Không đánh VALID cho WAV silence để thay thoại bắt buộc.

## 5. Memory

`FilmMemory`: schema_version, memory_id, revision_id, series_id?, approved_summary, summary_source_cue_ids, characters:Character[], relations:Relation[], glossary:GlossaryEntry[], proposals:MemoryProposal[], provenance.

`Character`: character_id, canonical_zh?, display_vi, aliases:string[], notes, status:PROPOSED/CONFIRMED/ARCHIVED, evidence_cue_ids:Id[]. Speaker acoustic IDs và Character IDs tách biệt; assignment record liên kết chúng do user xác nhận.

`Relation`: relation_id, from_character_id, to_character_id, self_pronoun_vi, address_pronoun_vi, valid_from_ms?, valid_to_ms?, status, evidence_cue_ids. Quan hệ có hướng. Không lấy “người nói tiếp theo” làm listener.

`GlossaryEntry`: entry_id, source_forms:string[], target_vi, category:PERSON/PLACE/SECT/REALM/SKILL/ITEM/OTHER, scope:PROJECT/SERIES, matching:EXACT/TOKEN, locked:bool, approved:bool, pronunciation_vi?, evidence_cue_ids. Hai approved mapping xung đột cùng scope → MEMORY_CONFLICT. Project override series rõ ràng, không dựa insertion order.

`MemoryProposal`: proposal_id, kind, value, evidence_cue_ids, confidence_milli?, status:PENDING/ACCEPTED/REJECTED. Model chỉ đề xuất; không đổi locked memory trực tiếp.

## 6. Translation handoff

`TranslationBatchRequest`: schema_version, batch_id:Digest, operation:TRANSLATE/POLISH/DUB_REWRITE, job_id, revision_id, dataset_revision_id, context_sha256, request_sha256, target_language, genre_profile_id, memory_revision_id, required_ids:[Id], cues:[{cue_id,source_text,draft_vi?,start_ms,end_ms,speaker_id?,listener_id?,max_graphemes?}], context:{previous_source,next_source,approved_summary,matched_glossary,matched_relations}, output_schema_id.

`request_sha256` được tính trên request bỏ chính request_sha256. `batch_id` là hash operation+cue input hashes+context+policy; không dùng nội dung mutable. Hash job_id riêng không bắt buộc vào reusable cache key.

```json
{
  "schema_version": "1.0",
  "batch_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
  "request_sha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
  "items": [
    {"cue_id": "54f15f76-75d2-4cf8-bfe4-0957b0189f75", "text_vi": "Sư huynh, chờ đã!"}
  ]
}
```

Hai digest trong ví dụ là giá trị minh họa, không là hash tính từ cue ví dụ. Response schema không có timestamps/speaker/model commands. Các key ngoài schema bị reject. `items` đúng tập required_ids, không thiếu/thừa/trùng ID; order response có thể khác, map bằng ID. Empty text bị reject với required cue. Duplicate text khác ID hợp lệ. Thông báo review dùng cue_id và issue code.

## 7. PipelineConfig defaults

| Group | Default / contract |
|---|---|
| source | method=auto; imported_ref=null; chosen_audio_index=null; chosen_subtitle_index=null; source_review_required=true |
| ocr | fps_milli=4000; roi={x:0,y:750,w:1000,h:250} permille; boundary_refine_ms=50; confidence_min_milli=800 |
| asr | engine=faster_whisper; model_ref từ lock; language=zh; chunk_target_ms=30000; chunk_max_ms=45000; overlap_ms=1000; word_timestamps=true; vad=true |
| translation | mode=manual_gemini hoặc api; provider_profile_id?; fallback_profile_ids=[]; max_cues=32; max_input_tokens=4000; max_response_tokens=4000; max_split_depth=5; context_neighbors=4; polish=rules_then_optional_model |
| genre | xianxia / wuxia / historical / transmigration / modern / neutral; default=xianxia, user xác nhận |
| readability | cps_target=17; cps_hard=22; max_lines=2; max_graphemes_per_line=42; min_display_ms=700; max_display_ms=7000 |
| tts | primary=vieneu; fallback=edge nếu allowed; max_rewrites=2; max_tempo_milli=1200; min_tempo_milli=1000; use_gap_ms≤200; mandatory_dialogue=true |
| audio | mode=separate_or_duck; fallback_allowed=true; voice_gain_mdb=0; separated_bg_gain_mdb=-6000; original_bg_gain_mdb=-12000; duck_threshold_mdb=-26000; duck_ratio_milli=4000; attack_ms=20; release_ms=250; target_lufs_milli=-16000; true_peak_mdb=-1500 |
| render | canvas=preserve_display; max_long_edge=1920; hdr_policy=reject_for_review; encoder=auto; x264_crf=20; x264_preset=medium; nvenc_preset=p4; nvenc_cq=21; pixel_format=yuv420p; audio_codec=aac; audio_bitrate=192000; audio_rate=48000 |
| runtime | gpu_concurrency=1; tts_cloud_concurrency=2; heartbeat_s=30; poll_s=10; lease_ttl_s=120; upload_chunk_bytes=8388608; max_job_cost_microunits? |

Defaults này phải có JSON fixture và version `aro-defaults-1`. Thay default không đổi job snapshot cũ. Unknown model/provider revision → preflight block, không tự dùng `latest`.

## 8. Error / validation contract

`AroError`: code, category:INPUT/AUTH/QUOTA/NETWORK/MODEL/RESOURCE/VALIDATION/CONFLICT/INTERNAL, retryable:bool, user_message_vi, stage_id?, cue_ids:Id[], diagnostic_ref?, suggested_action:RETRY/REAUTH/EDIT_CUES/IMPORT_RESPONSE/CHANGE_CONFIG/STOP.

Codes chuẩn: INPUT_NOT_COMMITTED, UNSUPPORTED_SCHEMA, CONTROLLER_CONFLICT, STALE_ATTEMPT, SOURCE_REVIEW_REQUIRED, NO_USABLE_SUBTITLE, MODEL_UNAVAILABLE, MEMORY_CONFLICT, RESPONSE_STALE, RESPONSE_ID_MISMATCH, TRANSLATION_INCOMPLETE, TTS_MISSING, TIMING_OVERFLOW, AUDIO_QC_FAILED, RENDER_DECODE_FAILED, DRIVE_AUTH_REQUIRED, DRIVE_QUOTA, DISK_PRESSURE, CHECKSUM_MISMATCH.

`ValidationReport`: schema_version, subject_artifact_id, validator_version, checks:[{check_id,status:PASS/FAIL/WARN/NOT_RUN,measured?,expected?,cue_ids,details}], passed:bool, manual_review:{reviewer?,reviewed_at?,notes?}, generated_at. NOT_RUN ở check bắt buộc = fail. Report không được tự khẳng định chất lượng ngữ nghĩa chỉ từ máy.
