# Arena Build Book — từ repo trống

**ARO_DESIGN_DECISION**. Đây là taskbook để Arena triển khai sau lượt kiến trúc. Chưa task production nào đã chạy. Tên task, đường dẫn, interfaces và acceptance dưới đây là contract; không chọn lại stack hoặc lấy source đối thủ.

## Quy tắc thực thi

1. Tạo repo mới, copy đúng 14 specs vào `docs/architecture/`. Đọc01→03→04→02, rồi task đầu tiên. Không cần lịch sử chat.
2. Làm A01–A18 để có Worker Golden trước. Sau G1 PASS mới A19–A24 Android. *(Amendment A-2026-10-15b, 13 D18: A19–A24 được implement/test song song trước G1 với status `IMPLEMENTED_PRE_G1` / `PARTIAL_ACCEPTANCE`; test cần FINAL thật, G1 worker hoặc A03 live Drive ghi `PENDING_G1` / `PENDING_LIVE`; chỉ promote PASS sau khi chạy lại với evidence khi G1 PASS.)* A25 optional, A26–A28 hardening/release. Không dùng mock để qua Golden.
3. Trong mỗi task, implement contracts và failure behavior trước nối UI. Chỉ task cần runtime/API/model thật mới dùng integration credentials. Không cần xây UI rộng trước pipeline.
4. Mỗi commit task kèm evidence ở artifacts/Axx: command, exit code, actual observed result, config/source/lock hashes, issues, next task. Không commit secrets hoặc media copyrighted vào repo.
5. Test commands Python chạy trong `worker/` với `uv run`; Android chạy trong `android/` với Gradle wrapper. Test files được task chỉ rõ; bổ sung failure regression khi có lỗi thực tế, không chỉ snapshot mirror implementation.
6. Các thư mục Python package cần `__init__.py`; mỗi Android module cần `build.gradle.kts` và manifest/resources tối thiểu do A19 tạo. `FILES TO MODIFY: none` có nghĩa task tạo mới, không tìm file từ repo cũ.
7. Không cần hỏi lại quyết định routine đã được baseline chốt. Nếu model/access/video/reviewer thật thiếu, ghi BLOCKED ở đúng gate, tiếp tục phần độc lập; không bịa lock, license, benchmarks, approval hoặc PASS.

## Các mốc

A01–A05 core/Drive → A06–A09 subtitle source → A10–A11 translation → A12–A15 TTS/audio → A16–A17 render/publish → A18 G1 FINAL → A19–A22 controller/manual → A23–A24 editor/preview → A25 optional cast → A26–A27 recovery/long video → A28 release candidate.

## A01 — Khởi tạo repo và runtime reproducible

### ID

A01

### GOAL

Khởi tạo repo và runtime reproducible

### WHY

Tất cả task sau phải có cách chạy độc lập notebook.

### INPUT CONTRACT

Repo trống; 14 tài liệu ARO_MASTER; Linux x86_64; không cần credential để unit test.

### FILES TO CREATE

- `README.md`
- `AGENTS.md`
- `.gitignore`
- `Makefile`
- `worker/pyproject.toml`
- `worker/uv.lock`
- `worker/src/aro_worker/__init__.py`
- `worker/src/aro_worker/cli.py`
- `worker/src/aro_worker/core/doctor.py`
- `configs/worker.example.yaml`
- `locks/ffmpeg-manifest.json`
- `locks/runtime-profiles.json`
- `notebooks/ARO_Colab.ipynb`
- `.github/workflows/worker.yml`
- `docs/adr/0001-baseline.md`

### FILES TO MODIFY

none

### EXACT IMPLEMENTATION

Khởi tạo monorepo Python3.11 với src layout và aro console entry. Chép 14 specs vào docs/architecture. Resolve exact core dev/runtime dependencies, doctor kiểm tra disk/FFmpeg/filter/codecs và xuất JSON available/blocked. Notebook chỉ bootstrap/auth/config/worker CLI, chưa nhận job khi modules chưa xong. Make targets lint, contracts, unit, media, golden dùng commands thật; target chưa implement phải fail rõ, không echo PASS. CI chạy offline unit/contract, không cần Drive secrets. Ghi actual installed versions và ffmpeg build config theo12.

### PUBLIC INTERFACES

aro doctor --json; aro --help; runtime capability JSON gồm supported_features/blocked_reasons.

### TESTS

Fresh venv uv sync --frozen; aro doctor trên CPU host; thiếu ffmpeg phải báo unavailable có actionable reason, CLI không crash import vì model chưa cài.

### EXPECTED RESULT

Repo cài được, CLI và doctor chạy, lock tái tạo môi trường core.

### FAILURE CONDITIONS

Unpinned transitive dependency; model imports tại startup; notebook chứa pipeline logic; fake green CI.

### OUTPUT ARTIFACT

artifacts/A01/runtime-report.json + lock hashes

### NEXT TASK

A02

## A02 — Contracts và shared fixtures

### ID

A02

### GOAL

Contracts và shared fixtures

### WHY

Hai ngôn ngữ phải đồng ý cue identity/hash/wire schema.

### INPUT CONTRACT

A01; models04 và defaults aro-defaults-1.

### FILES TO CREATE

- `worker/src/aro_worker/core/models.py`
- `worker/src/aro_worker/core/config.py`
- `worker/src/aro_worker/core/errors.py`
- `worker/src/aro_worker/core/canonical.py`
- `contracts/v1/common.schema.json`
- `contracts/v1/project.schema.json`
- `contracts/v1/job.schema.json`
- `contracts/v1/cue.schema.json`
- `contracts/v1/memory.schema.json`
- `contracts/v1/handoff.schema.json`
- `contracts/v1/artifact.schema.json`
- `contracts/v1/validation.schema.json`
- `contracts/fixtures/valid.json`
- `contracts/fixtures/invalid.json`
- `configs/pipeline.default.json`
- `worker/tests/unit/test_contracts.py`
- `worker/tests/unit/test_canonical.py`

### FILES TO MODIFY

- `worker/pyproject.toml`
- `worker/uv.lock`

### EXACT IMPLEMENTATION

Implement strict Pydantic records toàn bộ04; export Draft2020-12 schemas deterministically. Implement NFC+JCS+SHA256 domain hashing, UUID validation, int ms, enums/state literals. Fixture có Unicode, null, IDs ổn định qua edits, malformed intervals, missing/extra IDs. Defaults là file versioned, loader rejects unsupported major/required feature. Unknown fields chỉ extension map như04, không silently ignore ảnh hưởng semantics.

### PUBLIC INTERFACES

load_config(path)->PipelineConfig; canonical_bytes(obj)->bytes; digest(domain,obj)->str; validate_wire(kind,bytes)->Model.

### TESTS

uv run pytest tests/unit/test_contracts.py tests/unit/test_canonical.py; schema→model roundtrip; reject float timeline/NaN/duplicate keys/unknown required_features.

### EXPECTED RESULT

Wire fixtures và hashes trở thành oracle cho Python/Kotlin.

### FAILURE CONDITIONS

cue_id tính từ start/end; defaults mutable trong active job; schemas không mirror enums.

### OUTPUT ARTIFACT

artifacts/A02/contracts-report.json

### NEXT TASK

A03

## A03 — Drive storage adapter thực

### ID

A03

### GOAL

Drive storage adapter thực

### WHY

Atomic visibility/idempotency cần test API thật từ đầu.

### INPUT CONTRACT

A02; Drive auth runtime do người dùng thiết lập; test folder riêng được chọn.

### FILES TO CREATE

- `worker/src/aro_worker/storage/base.py`
- `worker/src/aro_worker/storage/drive.py`
- `worker/src/aro_worker/storage/local.py`
- `worker/src/aro_worker/storage/fake_drive.py`
- `worker/src/aro_worker/storage/uploads.py`
- `worker/tests/integration/test_drive.py`
- `worker/tests/unit/test_storage_faults.py`

### FILES TO MODIFY

- `worker/src/aro_worker/cli.py`
- `worker/pyproject.toml`
- `worker/uv.lock`

### EXACT IMPLEMENTATION

Implement list pagination, exact-ID metadata/download, generateIds, immutable create, resumable8MiB, hash verify, appProperties index. LocalStore tương đương chỉ cho tests/dev. FakeDrive inject delayed listing/timeout after create/409 duplicate IDs, không pretend filename unique. Live test cả controller và Colab exact IDs với OAuth scopes; record behavior reserved IDs và checksum. Retry403 phân loại quota/permission,401 refresh once,429/5xx bounded. Không FUSE rename làm remote transaction.

### PUBLIC INTERFACES

DriveStore interfaces03; aro storage smoke --root-id ID --report PATH.

### TESTS

Fake fault matrix03; live upload/download1MiB và empty JSON; 2 pages same filenames; timeout retry không thêm file mới; verify authenticated cross-client read.

### EXPECTED RESULT

DriveStore contract có evidence live, input và manifests durable.

### FAILURE CONDITIONS

Không có authorization/access; generateIds behavior unsupported; checksum mismatch; bỏ page token. Task BLOCKED thay giả success.

### OUTPUT ARTIFACT

artifacts/A03/drive-smoke.json với file IDs/hashes, không token

### NEXT TASK

A04

## A04 — Controller, jobs và fencing

### ID

A04

### GOAL

Controller, jobs và fencing

### WHY

Chỉ active attempt được công nhận output.

### INPUT CONTRACT

A03 storage + A02 schemas; single controller invariant03.

### FILES TO CREATE

- `worker/src/aro_worker/jobs/controller.py`
- `worker/src/aro_worker/jobs/reducer.py`
- `worker/src/aro_worker/jobs/commands.py`
- `worker/src/aro_worker/jobs/lease.py`
- `worker/src/aro_worker/jobs/events.py`
- `worker/src/aro_worker/jobs/recovery.py`
- `worker/tests/unit/test_job_protocol.py`
- `worker/tests/integration/test_attempt_fencing.py`

### FILES TO MODIFY

- `worker/src/aro_worker/cli.py`

### EXACT IMPLEMENTATION

Implement durable local command outbox trước upload, monotonic seq, immutable assignment và generation. Worker session UUID mới mỗi boot; poll hello/heartbeat. State reducer theo03, duplicate command idempotent; stale result reject. CLI project create/submit/status/assign/resume/retry/cancel và controller role export/import. Cancel revoke authority ngay controller nhưng chờ worker ack cho physical stop. No auto lease lock/election bằng filenames.

### PUBLIC INTERFACES

aro project create --source FILE --root-id ID; aro job submit --project ID --config FILE; aro job assign --job ID --session ID; aro job status/resume/retry/cancel --job ID.

### TESTS

Duplicate Run replay; seq gap; crash before ack; expired heartbeat chưa đồng nghĩa dead; two sessions, old late result rejected; terminal retry creates new job.

### EXPECTED RESULT

CLI điều khiển lifecycle đúng, chưa cần ML.

### FAILURE CONDITIONS

Worker tự SUCCEEDED; cùng FINAL mutable; controller fork last-write-wins; resume cancelled job mutate terminal.

### OUTPUT ARTIFACT

artifacts/A04/protocol-trace.json

### NEXT TASK

A05

## A05 — Artifact cache và stage runner

### ID

A05

### GOAL

Artifact cache và stage runner

### WHY

Granular durable checkpoint là nền của pipeline.

### INPUT CONTRACT

A04 assignment/events; stage interface05; key rules09.

### FILES TO CREATE

- `worker/src/aro_worker/cache/keys.py`
- `worker/src/aro_worker/cache/store.py`
- `worker/src/aro_worker/cache/invalidation.py`
- `worker/src/aro_worker/cache/gc.py`
- `worker/src/aro_worker/core/stage.py`
- `worker/src/aro_worker/core/runner.py`
- `worker/src/aro_worker/core/resources.py`
- `worker/src/aro_worker/core/cancel.py`
- `worker/src/aro_worker/storage/artifacts.py`
- `worker/tests/unit/test_cache_graph.py`
- `worker/tests/integration/test_runner_recovery.py`

### FILES TO MODIFY

- `worker/src/aro_worker/cli.py`

### EXACT IMPLEMENTATION

Implement topological DAG, child-process stage execution, heartbeat cha, cache hit verification, manifest-last upload, checkpoints per unit. ResourceController disk/RAM thresholds. Fake stages chỉ trong tests, production registry rejects missing stage. Input-key params projected per table09. GC dry-run reachability, no input/output deletion. Cancel subprocess group TERM then KILL after5s; network partition stops new provider calls.

### PUBLIC INTERFACES

Stage.run/validate/input_key; ArtifactStore.commit(output)->Checkpoint; Runner.run(assignment); aro worker run --workspace-id ID.

### TESTS

SIGKILL before/after manifest, corrupt blob, style-only invalidation, key rotation unchanged, cancellation child tree; durable completed units không gọi lại.

### EXPECTED RESULT

Runner có thể execute/resume typed stages an toàn, capability advertises implemented only.

### FAILURE CONDITIONS

Cache file-exists hit; stage success trước upload commit; heartbeat blocked bởi inference.

### OUTPUT ARTIFACT

artifacts/A05/recovery-report.json

### NEXT TASK

A06

## A06 — FFmpeg wrapper, probe và audio extract

### ID

A06

### GOAL

FFmpeg wrapper, probe và audio extract

### WHY

Timeline/canvas đúng phải có trước subtitle và voice.

### INPUT CONTRACT

A05 StageContext và committed source ArtifactRef.

### FILES TO CREATE

- `worker/src/aro_worker/media/process.py`
- `worker/src/aro_worker/media/probe.py`
- `worker/src/aro_worker/media/extract.py`
- `worker/src/aro_worker/media/timeline.py`
- `worker/src/aro_worker/media/fixtures.py`
- `worker/tests/media/test_media.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`

### EXACT IMPLEMENTATION

Run ffprobe JSON/FFmpeg argv không shell, drain stderr/progress song song; timeout/cancel có cleanup. Select streams by index, rotation/SAR/VFR/start offsets. Extract16k mono cho ASR,48k stereo float mix, sample-count validation. Synthetic fixture builder text-stream/video/audio offset/no audio/rotation, không gắn Golden label. HDR reject policy explicit.

### PUBLIC INTERFACES

probe(path)->MediaProbe; extract_audio(source,index,profile)->Artifact; run_ffmpeg(argv,cancel,progress)->ProcessResult.

### TESTS

FFmpeg real fixtures5–10s; -progress time units đúng; nonzero audio start preserved; no-audio typed result; disk full reported.

### EXPECTED RESULT

probe/audio artifacts đúng format và absolute global time.

### FAILURE CONDITIONS

Chọn attached_pic; mất offset; assume fps integer; path injection; silent fallback1920x1080.

### OUTPUT ARTIFACT

artifacts/A06/media-report.json

### NEXT TASK

A07

## A07 — Subtitle resolver, import/embedded và normalize

### ID

A07

### GOAL

Subtitle resolver, import/embedded và normalize

### WHY

Có text subtitle tốt thì không ASR/OCR vô ích.

### INPUT CONTRACT

A06 probe; source review contract05; cue lineage04.

### FILES TO CREATE

- `worker/src/aro_worker/subtitle/source.py`
- `worker/src/aro_worker/subtitle/embedded.py`
- `worker/src/aro_worker/subtitle/srt.py`
- `worker/src/aro_worker/subtitle/normalize.py`
- `worker/src/aro_worker/subtitle/lineage.py`
- `worker/tests/media/test_subtitle_sources.py`
- `worker/tests/unit/test_cue_edits.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`
- `worker/src/aro_worker/cli.py`

### EXACT IMPLEMENTATION

Implement imported SRT priority, text codec whitelist, explicit audio/subtitle selection. Forced-only/bitmap track không giả full transcript. Create raw+normalized dataset with stable cue UUIDs persisted, source evidence IDs, required kinds/exclusions. SRT strict parse, editable CLI review/import. Split/merge preserve coverage lineage. Resolver chưa có OCR/ASR phải return capability missing thay empty success.

### PUBLIC INTERFACES

resolve_source(probe,config)->SourceSelection; normalize(raw)->CueDataset; aro cues import/review --project ID --file PATH.

### TESTS

Multitrack zh/en/forced; PGS branch typed unavailable; valid SRT Unicode; bad timestamp; split/merge coverage and cue ID stability.

### EXPECTED RESULT

Embedded/import path yields validated source dataset và source review wait.

### FAILURE CONDITIONS

Auto-select first subtitle bất kể language; bitmap convert-to-SRT failure swallowed; missing cue silently dropped.

### OUTPUT ARTIFACT

artifacts/A07/source-fixtures.json

### NEXT TASK

A08

## A08 — OCR hardsub adapter và temporal reconstruction

### ID

A08

### GOAL

OCR hardsub adapter và temporal reconstruction

### WHY

Donghua thường có chữ Trung nằm trong ảnh.

### INPUT CONTRACT

A07 resolver; official model verification12/U01; OCR algorithm05.

### FILES TO CREATE

- `worker/src/aro_worker/ocr/engine.py`
- `worker/src/aro_worker/ocr/rapidocr.py`
- `worker/src/aro_worker/ocr/sampling.py`
- `worker/src/aro_worker/ocr/temporal.py`
- `worker/src/aro_worker/ocr/roi.py`
- `models/ocr.manifest.json`
- `worker/tests/media/test_ocr.py`
- `worker/tests/unit/test_ocr_temporal.py`

### FILES TO MODIFY

- `worker/src/aro_worker/subtitle/source.py`
- `worker/src/aro_worker/core/runner.py`
- `worker/pyproject.toml`
- `worker/uv.lock`

### EXACT IMPLEMENTATION

Resolve public OCR model revision/hash/license; if PP-OCRv6 not available document public supported alternative. Sample hardsub detection12 timestamps; full4fps ROI, bounded decode, pHash observation reuse with500ms inference heartbeat, edit-similarity+bbox merge,50ms boundary refine. Raw observations committed60s units. Expose ROI override and low-confidence review; retain ASCII/numbers/signs.

### PUBLIC INTERFACES

OcrEngine.recognize(frame)->Observation[]; extract_hardsub(source,roi)->RawCuePages; aro source select --method ocr --roi x,y,w,h.

### TESTS

Chinese known frames actual model; brief subtitles<500ms; same text separated gap; identical frames still extend time; watermark not blindly deleted; kill/restart per chunk.

### EXPECTED RESULT

OCR supplies source dataset + confidence/review report, public artifacts pinned.

### FAILURE CONDITIONS

Copy competitor models; claim v6 when using v4; drop tiny cues silently; lower long-video fps without policy.

### OUTPUT ARTIFACT

artifacts/A08/ocr-report.json

### NEXT TASK

A09

## A09 — ASR chunking, VAD và merge

### ID

A09

### GOAL

ASR chunking, VAD và merge

### WHY

Audio-only source cần subtitle có timestamp giữ được khi resume.

### INPUT CONTRACT

A06 audio16k; A07 normalize; faster-whisper official weights12.

### FILES TO CREATE

- `worker/src/aro_worker/asr/base.py`
- `worker/src/aro_worker/asr/whisper.py`
- `worker/src/aro_worker/asr/vad.py`
- `worker/src/aro_worker/asr/chunks.py`
- `worker/src/aro_worker/asr/stitch.py`
- `models/asr.manifest.json`
- `models/vad.manifest.json`
- `worker/tests/unit/test_asr_stitch.py`
- `worker/tests/media/test_asr.py`

### FILES TO MODIFY

- `worker/src/aro_worker/subtitle/source.py`
- `worker/src/aro_worker/core/runner.py`
- `worker/pyproject.toml`
- `worker/uv.lock`

### EXACT IMPLEMENTATION

Load one lazy Whisper engine; CUDA int8_float16/CPU int8 verified profiles. Silero VAD parameters05, target30s/max45s/core intervals+1s decode overlap, global offsets. Commit raw chunk before stitch. Word midpoint ownership plus boundary alignment preserves real repeated words. No-VAD/CPU fallback logged actual recipe; silence/no-speech hallucination flags review.

### PUBLIC INTERFACES

AsrEngine.transcribe(chunk,language)->RawWords; chunk_audio(profile)->ChunkPlan; stitch(chunks)->RawCues.

### TESTS

20s real zh speech smoke + synthetic boundary alignment fixtures; long chunk kill/restart counters; VAD failure fallback; repeat phrase at different timestamps stays.

### EXPECTED RESULT

ASR source branch complete, source reviewer can select OCR/import on poor result.

### FAILURE CONDITIONS

25min chunks unbounded model RAM; overlap double cues; confidence interpreted truth; lost global offset.

### OUTPUT ARTIFACT

artifacts/A09/asr-report.json

### NEXT TASK

A10

## A10 — Memory/glossary/genre và API translation

### ID

A10

### GOAL

Memory/glossary/genre và API translation

### WHY

Giữ tên/xưng hô và strict output contract từ batch đầu.

### INPUT CONTRACT

A07/08/09 source dataset reviewed;04 memory;06 translation spec; optional configured provider key in runtime.

### FILES TO CREATE

- `worker/src/aro_worker/memory/store.py`
- `worker/src/aro_worker/memory/match.py`
- `worker/src/aro_worker/memory/context.py`
- `worker/src/aro_worker/memory/proposals.py`
- `worker/src/aro_worker/translation/base.py`
- `worker/src/aro_worker/translation/batches.py`
- `worker/src/aro_worker/translation/prompts.py`
- `worker/src/aro_worker/translation/parser.py`
- `worker/src/aro_worker/translation/validator.py`
- `worker/src/aro_worker/translation/retry.py`
- `worker/src/aro_worker/translation/pipeline.py`
- `worker/src/aro_worker/translation/providers/gemini_api.py`
- `worker/src/aro_worker/translation/providers/openai_compat.py`
- `profiles/genres/xianxia.yaml`
- `profiles/genres/wuxia.yaml`
- `profiles/genres/historical.yaml`
- `profiles/genres/transmigration.yaml`
- `profiles/genres/modern.yaml`
- `profiles/genres/neutral.yaml`
- `worker/tests/unit/test_translation.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`
- `worker/src/aro_worker/cli.py`
- `worker/pyproject.toml`
- `worker/uv.lock`

### EXACT IMPLEMENTATION

Implement directed relationships/confirmed-over-proposed rules, longest glossary matching and dependency index. Freeze context and32cue stable anchors, budget including schema/context. New prompt text06, strict JSON parser rejects duplicate keys/trailing prose. API capability profiles not hardcoded imaginary models. Retry transport vs semantic separately, split depth5/global64request cap, configured fallback≤2. Preserve valid batches; no source-text fallback. CLI memory/glossary imports create revision.

### PUBLIC INTERFACES

TranslationProvider.submit; build_context; build_batches; validate_response; aro memory import --project ID --file FILE.

### TESTS

All fixtures06: IDs/memory/pronouns/numerals/CJK whitelist/repeated valid text;429 budget; split singleton bounded; public API smoke if configured, otherwise capability disabled until manual A11.

### EXPECTED RESULT

API translation path yields committed validated results hoặc actionable wait.

### FAILURE CONDITIONS

Regex guesses response mapping; overwrite locked text; auto-approved inferred relation; secrets in context/hash.

### OUTPUT ARTIFACT

artifacts/A10/translation-contract.json

### NEXT TASK

A11

## A11 — Manual Gemini và polish/readability

### ID

A11

### GOAL

Manual Gemini và polish/readability

### WHY

Golden chạy được không cần API key.

### INPUT CONTRACT

A10 provider contract;03 IMPORT_RESPONSE;04 handoff;06 manual workflow.

### FILES TO CREATE

- `worker/src/aro_worker/translation/providers/manual_gemini.py`
- `worker/src/aro_worker/translation/handoff.py`
- `worker/src/aro_worker/translation/polish.py`
- `worker/src/aro_worker/subtitle/readability.py`
- `worker/tests/integration/test_manual_handoff.py`
- `worker/tests/unit/test_readability.py`

### FILES TO MODIFY

- `worker/src/aro_worker/cli.py`
- `worker/src/aro_worker/translation/pipeline.py`
- `worker/src/aro_worker/jobs/commands.py`

### EXACT IMPLEMENTATION

Export request JSON/text≤16cues/12k bytes with operation/hash/revision, WAITING_USER durable. CLI export/import/validate response. Map IDs strictly, reject stale response and preserve pending request across restart. Rules polish wrap/CPS/graphemes; optional model polish uses same provider operation. Record voice-required vs sign-only cues; invalid semantic/readability cues review. No Gemini app automation.

### PUBLIC INTERFACES

aro handoff export --job ID --batch ID --out DIR; aro handoff import --job ID --file RESPONSE; aro job resume --job ID.

### TESTS

Manual actual export/import trace; response missing/duplicate ID/trailing prose/stale hash; restart between export/import; CPS17/22 and emoji combining marks; same text two IDs valid.

### EXPECTED RESULT

Fully translated reviewed cue dataset + vi.srt, manual no-key route usable.

### FAILURE CONDITIONS

Response accepted before ACK/validator; imports mutate old revision; manual feature a TODO until Android.

### OUTPUT ARTIFACT

artifacts/A11/manual-roundtrip.json

### NEXT TASK

A12

## A12 — VieNeu và Edge TTS adapters

### ID

A12

### GOAL

VieNeu và Edge TTS adapters

### WHY

MVP voice Việt thật, engine available có bằng chứng.

### INPUT CONTRACT

A11 translated cues; public model/codec manifests12/U02; secrets optional.

### FILES TO CREATE

- `worker/src/aro_worker/tts/base.py`
- `worker/src/aro_worker/tts/vieneu.py`
- `worker/src/aro_worker/tts/edge.py`
- `worker/src/aro_worker/tts/catalogue.py`
- `worker/src/aro_worker/tts/normalize.py`
- `worker/src/aro_worker/tts/synthesis.py`
- `models/tts.manifest.json`
- `locks/tts-environment.lock`
- `worker/tests/media/test_tts_engines.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`
- `locks/runtime-profiles.json`
- `worker/pyproject.toml`
- `worker/uv.lock`

### EXACT IMPLEMENTATION

Resolve official VieNeu/package+weights+codec+license, isolate env nếu needed. Implement local stdio adapter, catalogue actual voices, five-line VI synth including Hán-Việt/numbers. Native sample-rate kept then convert fit profile48k. Edge optional fallback policy preconfigured, MP3 decode, retries bounded. Cache raw per effective text/actual voice/model/style. No competitor voice samples/clones.

### PUBLIC INTERFACES

TtsEngine.voices/synthesize/fingerprint; SynthesisRequest->RawTtsArtifact.

### TESTS

Actual VieNeu five-line smoke with duration>0/speech detected; actual Edge1line when network enabled; auth/network fail typed; repeated cache no engine call.

### EXPECTED RESULT

Primary VieNeu verified for ARO and fallback trace, raw cues audible.

### FAILURE CONDITIONS

VieNeu unavailable yet claim MVP complete; placeholders silence; resample16k reduces all models; unknown license bundled.

### OUTPUT ARTIFACT

artifacts/A12/tts-smoke.json

### NEXT TASK

A13

## A13 — Fit duration và timing review

### ID

A13

### GOAL

Fit duration và timing review

### WHY

Không cắt lời hoặc tăng tốc vô hạn để qua pipeline.

### INPUT CONTRACT

A12 raw TTS;07 bounded fit;06 DUB_REWRITE operation.

### FILES TO CREATE

- `worker/src/aro_worker/tts/fit.py`
- `worker/src/aro_worker/tts/windows.py`
- `worker/src/aro_worker/tts/rewrite.py`
- `worker/tests/media/test_tts_fit.py`

### FILES TO MODIFY

- `worker/src/aro_worker/tts/synthesis.py`
- `worker/src/aro_worker/core/runner.py`

### EXACT IMPLEMENTATION

Available window includes≤200ms eligible gap with50ms next-start guard. Synth→measure→≤2 semantic-valid rewrites/resynth→bounded atempo≤1.2→remeasure. Trim only verified edge silence; short clips pad no slowdown. Raw reuse separate from fit key. Overflow goes WAITING_USER and emits cue IDs. Handle overlapping dialogue as review/multilane explicit, no negative window.

### PUBLIC INTERFACES

fit_cue(cue,raw,window,policy,rewrite_provider)->TtsCueResult; plan_windows(dataset)->WindowPlan.

### TESTS

Fits direct/short/1.15ratio/>1.2overflow; no speech clipping; gap neighbor invalidation; locked timing; source final cue clamp; manual rewrite resume.

### EXPECTED RESULT

Every required cue VALID fit hoặc job stopped with review, no hidden missing audio.

### FAILURE CONDITIONS

Hard truncate waveform; keyword-only rewrite changes meaning; silence marked VALID; cache ignores duration.

### OUTPUT ARTIFACT

artifacts/A13/fit-report.json

### NEXT TASK

A14

## A14 — UVR separation và original fallback

### ID

A14

### GOAL

UVR separation và original fallback

### WHY

Giữ nền/SFX và phản ánh chất lượng tách thực.

### INPUT CONTRACT

A06 mix48 audio;07 separation;12 model licensing/preprocess gate.

### FILES TO CREATE

- `worker/src/aro_worker/audio/separation.py`
- `worker/src/aro_worker/audio/background.py`
- `models/separation.manifest.json`
- `worker/tests/media/test_separation.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`
- `locks/runtime-profiles.json`

### EXACT IMPLEMENTATION

Integrate public UVR-compatible implementation with pinned model/DSP recipe. Model-native rate input, stems48k aligned output,60s windows+2s overlap normalized overlap-add. Listening+latency check, cache window refs. If unavailable and policy allow, original background actual mode DUCK_ORIGINAL. Strict clean mode blocks for review; no mislabeled clean output.

### PUBLIC INTERFACES

separate(audio,model,plan,cancel)->SeparationResult; resolve_background(config,capabilities)->BackgroundArtifact.

### TESTS

Impulse alignment/length, seam energy, music/SFX speech leakage sample listen, absent model explicit fallback, strict clean disallows fallback.

### EXPECTED RESULT

Background artifact and actual mode committed, optional separation proven or disabled honestly.

### FAILURE CONDITIONS

Assume music separation removes all speech; wrong sample offsets; proprietary ONNX copied.

### OUTPUT ARTIFACT

artifacts/A14/background-report.json

### NEXT TASK

A15

## A15 — Voice timeline, ducking và loudnorm

### ID

A15

### GOAL

Voice timeline, ducking và loudnorm

### WHY

Audio rõ, không clipping và dài đúng video.

### INPUT CONTRACT

A13 fitted cues + A14 background;07 mixing profile.

### FILES TO CREATE

- `worker/src/aro_worker/audio/voice_track.py`
- `worker/src/aro_worker/audio/ducking.py`
- `worker/src/aro_worker/audio/loudness.py`
- `worker/src/aro_worker/audio/mix.py`
- `worker/tests/media/test_mix.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`

### EXACT IMPLEMENTATION

Build voice disk-backed10s blocks absolute sample placement48k, pad to D, RF64/FLAC for size>4GiB. Voice normalization continuous; background gains mode-dependent; threshold dB→linear. sidechain voice key, amix normalize0, loudnorm two-pass AFTER mix with measured stats and explicit48k resample. Encode/decode loudness QC, no -inf/NaN bypass.

### PUBLIC INTERFACES

build_voice_track; mix_master->MixResult{master,voice,measurement_refs,actual_mode}.

### TESTS

Steady BGM+speech burst duck≥3dB; release recovery; peak/loudness bounds; no-audio policy; duration and impulse offsets; memory usage bounded for sparse4h track.

### EXPECTED RESULT

master_audio.wav full duration, voice+background audible and measured.

### FAILURE CONDITIONS

Normalize stems independently -16 then add; duration max cue instead of video; in-RAM4h buffer.

### OUTPUT ARTIFACT

artifacts/A15/audio-qc.json

### NEXT TASK

A16

## A16 — ASS và video render

### ID

A16

### GOAL

ASS và video render

### WHY

Final output phải đúng hình/phụ đề và playable Android.

### INPUT CONTRACT

A11 final display cues + A15 master + A06 probe;07 render policy.

### FILES TO CREATE

- `worker/src/aro_worker/render/ass.py`
- `worker/src/aro_worker/render/fonts.py`
- `worker/src/aro_worker/render/canvas.py`
- `worker/src/aro_worker/render/filters.py`
- `worker/src/aro_worker/render/encoder.py`
- `worker/src/aro_worker/render/export.py`
- `worker/src/aro_worker/render/preview.py`
- `assets/fonts/NOTICE.txt`
- `assets/fonts/manifest.json`
- `worker/tests/media/test_render.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`

### EXACT IMPLEMENTATION

Bundle official licensed VI font, real glyph coverage. SRT→ASS output canvas PlayRes, centisecond rounding, safe literal escape. Normalize rotation/SAR/even canvas preserve display ratio. FFmpeg argv/filter script with no injection, video+master mapped explicit,D fixed. NVENC real2s probe,p4/cq21; CPU libx264 medium/crf20 fallback1; no -shortest hiding audio missing. Preview uses same pipeline on10–20s slice/global offsets.

### PUBLIC INTERFACES

build_ass; resolve_canvas; choose_encoder; render; render_preview(range)->Artifact.

### TESTS

Actual raster frame VI diacritics and styles at720/1080/portrait; ASS braces injection; rotation; NVENC advertised but driver missing; CPU decode10s; missing font blocks.

### EXPECTED RESULT

Local candidate.mp4 and authoritative preview artifacts, no success before A17.

### FAILURE CONDITIONS

Copy video while burn requested; incorrect PlayRes; x264 presets passed blindly NVENC; partial MP4 accepted.

### OUTPUT ARTIFACT

artifacts/A16/render-report.json

### NEXT TASK

A17

## A17 — Final validation và publish

### ID

A17

### GOAL

Final validation và publish

### WHY

Chỉ output đủ thoại/voice và durable được SUCCEEDED.

### INPUT CONTRACT

A16 candidate và full manifests;03 result acceptance;11 mandatory QC.

### FILES TO CREATE

- `worker/src/aro_worker/validation/coverage.py`
- `worker/src/aro_worker/validation/audio.py`
- `worker/src/aro_worker/validation/video.py`
- `worker/src/aro_worker/validation/report.py`
- `worker/src/aro_worker/jobs/publish.py`
- `worker/tests/media/test_final_validation.py`
- `worker/tests/integration/test_publish_recovery.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`
- `worker/src/aro_worker/jobs/controller.py`
- `worker/src/aro_worker/cli.py`

### EXACT IMPLEMENTATION

Validate required lineage/translation/TTS, no blocking issues, codecs/duration/master metrics, raster samples and human review refs. Full decode -xerror maps video+audio, inspect moov before mdat. Upload FINAL binary unique attempt path, verify exact ID hash, result manifest last. Controller checks active generation/request and ACCEPT_RESULT, optional shortcut as convenience only. Recover post-upload/pre-result without render again.

### PUBLIC INTERFACES

aro validate result --result FILE --report FILE; publish_candidate->ResultManifest; controller.accept_result->PublishedResult.

### TESTS

Corrupt final tail fails despite first frame playable; missing one TTS cue fails; stale generation fails; kill99% upload; candidate checksum mismatch; successful readback.

### EXPECTED RESULT

SUCCEEDED only after validated and accepted result on Drive.

### FAILURE CONDITIONS

File exists/size>0 treated success; output shortcut used checksum subject; bypass human required checks.

### OUTPUT ARTIFACT

artifacts/A17/publish-trace.json

### NEXT TASK

A18

## A18 — G1 video donghua thật và restart

### ID

A18

### GOAL

G1 video donghua thật và restart

### WHY

Chứng minh toàn pipeline trước UI nâng cao.

### INPUT CONTRACT

A01–A17; rights-permitted real3–10min source + reviewer (HUMAN_REVIEW) hoặc OWNER_ACCEPTED_WITH_QA_REVIEW theo 11 §9 (Amendment A-2026-10-15); checklist11.

### FILES TO CREATE

- `tests/golden/cases/donghua-001/case.json`
- `tests/golden/run_case.py`
- `tests/golden/report.schema.json`
- `docs/runbooks/golden.md`

### FILES TO MODIFY

- `Makefile`

### EXACT IMPLEMENTATION

Select/hash/upload real case, annotate independent required utterances (hoặc QA-checked agent-derived annotations dưới 11 §9), freeze config+memory/model manifests. Run production CLI with real source method/translation manual or API/VieNeu/mix/render. Review source and semantic audio/video per11. Kill runtime after translation+5TTS checkpoints; new worker session assigned, resume and compare call counts. Replay stale worker candidate. Publish FINAL and save readback hash. Record all interventions/model fallbacks, not a clean-pass fiction.

### PUBLIC INTERFACES

make golden CASE=donghua-001; CLI controls A04/A11; golden_report schema11.

### TESTS

Every G-* row11 measured PASS; unit/media suites; actual output play/decode; no mocked provider/model in Golden.

### EXPECTED RESULT

G1 PASS with Drive FINAL binary and evidence, or explicit blocked checks needing input/review.

### FAILURE CONDITIONS

Synthetic/mocked final substituted; no reviewer và không có 11 §9 owner acceptance hợp lệ / no source rights; reviewer giả hoặc waiver gắn nhãn PASS; unknown mandatory checks marked pass; no restart evidence.

### OUTPUT ARTIFACT

Private Drive Golden kit + artifacts/A18/golden_report.json

### NEXT TASK

A19

## A19 — Android scaffold và typed persistence

### ID

A19

### GOAL

Android scaffold và typed persistence

### WHY

Controller mobile dùng cùng contracts đã chứng minh.

### INPUT CONTRACT

G1 PASS; A02 shared schemas;08 app stack;12 Android version lane.

### FILES TO CREATE

- `android/settings.gradle.kts`
- `android/build.gradle.kts`
- `android/gradle/libs.versions.toml`
- `android/gradle/wrapper/gradle-wrapper.properties`
- `android/gradle/verification-metadata.xml`
- `android/app/build.gradle.kts`
- `android/app/src/main/AndroidManifest.xml`
- `android/app/src/main/java/studio/aro/MainActivity.kt`
- `android/core/model/src/main/java/studio/aro/model/WireModels.kt`
- `android/core/database/src/main/java/studio/aro/database/AroDatabase.kt`
- `android/core/database/src/main/java/studio/aro/database/Entities.kt`
- `android/core/model/src/test/java/studio/aro/model/ContractTest.kt`
- `.github/workflows/android.yml`

### FILES TO MODIFY

none

### EXACT IMPLEMENTATION

Resolve exact compatible Kotlin/AGP/Gradle/JDK17/Compose/Room/KSP stack, wrapper checksum, minSdk26/current target. Create modules08 Gradle files and package manifests; DTO serialization snake_case, Room entities independent; Room schema export/migrations. Initial navigation project empty screen and baseline StateFlow repository contracts. Add shared JSON fixtures to test resources.

### PUBLIC INTERFACES

WireModels mirror04; AroDatabase DAOs; ./gradlew :app:assembleDebug test.

### TESTS

Python/Kotlin canonical fixture hashes equal; Room roundtrip/initial migration; compile emulator API26+current target; dependency verification strict.

### EXPECTED RESULT

Installable app scaffold and database/contracts validated.

### FAILURE CONDITIONS

Generate DTO fields differently; destructive migration; unpinned versions; ship model dependencies in APK.

### OUTPUT ARTIFACT

artifacts/A19/android-build.json

### NEXT TASK

A20

## A20 — Android OAuth, picker và resumable sync

### ID

A20

### GOAL

Android OAuth, picker và resumable sync

### WHY

Điện thoại đưa input lên Drive đáng tin cậy.

### INPUT CONTRACT

A19 + live Drive visibility A03;08 scopes/offline contract.

### FILES TO CREATE

- `android/core/drive/src/main/java/studio/aro/drive/DriveAuth.kt`
- `android/core/drive/src/main/java/studio/aro/drive/DriveStore.kt`
- `android/core/sync/src/main/java/studio/aro/sync/TransferWorker.kt`
- `android/core/sync/src/main/java/studio/aro/sync/Outbox.kt`
- `android/feature/projects/src/main/java/studio/aro/projects/ProjectsScreen.kt`
- `android/feature/setup/src/main/java/studio/aro/setup/ProjectSetupScreen.kt`
- `android/core/sync/src/test/java/studio/aro/sync/TransferTest.kt`

### FILES TO MODIFY

- `android/app/src/main/AndroidManifest.xml`
- `android/core/database/src/main/java/studio/aro/database/Entities.kt`
- `android/gradle/libs.versions.toml`

### EXACT IMPLEMENTATION

Supported Google auth/Drive scope, SAF/Drive picker user-selected access, persist URI read permission. Stream input hash/upload8MiB resumable; foreground WorkManager notification and saved encrypted session URI, Wi-Fi policy. READY only after immutable input manifest. Room transaction outbox sequence allocation, replay same reserved IDs. Credential refresh, quota/permission states; keys stay worker runtime.

### PUBLIC INTERFACES

DriveAuth.authorize; DriveStore suspend operations03; TransferWorker; ProjectRepository.createDraft/upload.

### TESTS

Device→Drive→Colab exact-ID smoke; process kill mid-upload, URI revoked,401/403/429, quota insufficient, duplicate names; reopen resumes once.

### EXPECTED RESULT

Input selected from Android is committed/readable worker, projects persist offline.

### FAILURE CONDITIONS

Assume drive.file lists all account files; token in JSON/logs; upload duplicate on retry; real-time background promise.

### OUTPUT ARTIFACT

artifacts/A20/mobile-drive-report.json

### NEXT TASK

A21

## A21 — Android settings, jobs và controls

### ID

A21

### GOAL

Android settings, jobs và controls

### WHY

Người dùng chạy/resume/cancel không terminal.

### INPUT CONTRACT

A20 storage/outbox; A04 protocol;08 screen states.

### FILES TO CREATE

- `android/feature/jobs/src/main/java/studio/aro/jobs/JobViewModel.kt`
- `android/feature/jobs/src/main/java/studio/aro/jobs/JobScreen.kt`
- `android/feature/setup/src/main/java/studio/aro/setup/PipelineSettings.kt`
- `android/feature/settings/src/main/java/studio/aro/settings/SettingsScreen.kt`
- `android/core/sync/src/main/java/studio/aro/sync/JobSync.kt`
- `android/feature/jobs/src/test/java/studio/aro/jobs/JobReducerTest.kt`

### FILES TO MODIFY

- `android/app/src/main/java/studio/aro/MainActivity.kt`

### EXACT IMPLEMENTATION

Transfer controller role CLI→Android once, stop CLI writer. Screen source/profile/worker capabilities/actual mode, submit frozen revisions. Foreground poll10s + jitter, background WorkManager≥15min, heartbeat stale120s. Run/Resume/Retry/Cancel mapping03, active attempt fencing and command ACKs. UI units/progress no100% before ACCEPT; all wait/error states actionable with cue IDs.

### PUBLIC INTERFACES

JobRepository.submit/assign/sendCommand/observe; JobUiState sealed model; foreground lifecycle sync.

### TESTS

FakeStore reducer includes delayed/reordered snapshots, revoked worker, cancellation request vs ack; device full Run path to G1 worker and process death after submit.

### EXPECTED RESULT

Android is working controller, worker disconnect does not lose project/job.

### FAILURE CONDITIONS

Second controller active without handoff; mutable config during run; stale result overwrite; need tunnel URL.

### OUTPUT ARTIFACT

artifacts/A21/controller-device-report.json

### NEXT TASK

A22

## A22 — Android manual Gemini handoff

### ID

A22

### GOAL

Android manual Gemini handoff

### WHY

Không API vẫn có đầy đủ flow mobile.

### INPUT CONTRACT

A21 WAITING_USER; A11 pending requests;04 response contract.

### FILES TO CREATE

- `android/feature/handoff/src/main/java/studio/aro/handoff/HandoffScreen.kt`
- `android/feature/handoff/src/main/java/studio/aro/handoff/HandoffViewModel.kt`
- `android/feature/handoff/src/test/java/studio/aro/handoff/HandoffTest.kt`

### FILES TO MODIFY

- `android/app/src/main/java/studio/aro/MainActivity.kt`
- `android/core/sync/src/main/java/studio/aro/sync/JobSync.kt`

### EXACT IMPLEMENTATION

Display pending operation/batch/cue count/context and request hash. ACTION_SEND via FileProvider/text, Copy fallback; Paste/SAF JSON import size bounded. Local schema/IDs check immediate errors, upload immutable response and IMPORT command; server validation ACK controls accepted state. Stale revision response rejected with explanation and explicit manual-edit import route.

### PUBLIC INTERFACES

HandoffViewModel.export/share/import/observeValidation; no AccessibilityService or Gemini SDK automation.

### TESTS

Wrong batch/missing cue/duplicate ID/too large/Markdown fence supported exactly once; actual user-mediated Gemini roundtrip; kill app/worker between export and import then resume.

### EXPECTED RESULT

G2 manual path creates FINAL from Android without API credential.

### FAILURE CONDITIONS

App controls Gemini UI; pasted response blindly accepted; accepted before Worker ack.

### OUTPUT ARTIFACT

artifacts/A22/manual-mobile-report.json

### NEXT TASK

A23

## A23 — Subtitle editor và revision/lineage

### ID

A23

### GOAL

Subtitle editor và revision/lineage

### WHY

Sửa lỗi dịch/thời gian không mất cue identity hoặc toàn bộ cache.

### INPUT CONTRACT

A21 repository;04 cue lineage;09 invalidation;08 editor rules.

### FILES TO CREATE

- `android/feature/editor/src/main/java/studio/aro/editor/SubtitleEditor.kt`
- `android/feature/editor/src/main/java/studio/aro/editor/EditorViewModel.kt`
- `android/feature/editor/src/main/java/studio/aro/editor/EditHistory.kt`
- `android/core/sync/src/main/java/studio/aro/sync/RevisionMerge.kt`
- `android/feature/editor/src/test/java/studio/aro/editor/RevisionTest.kt`

### FILES TO MODIFY

- `android/core/database/src/main/java/studio/aro/database/Entities.kt`
- `android/app/src/main/java/studio/aro/MainActivity.kt`

### EXACT IMPLEMENTATION

LazyColumn/page500 cues stable IDs; source/display/tts fields separate, timing ms and locks. Debounced autosave500ms plus navigation, undo/redo persisted bounded1000. Split/merge requires text/time assignment+lineage. Save immutable revision based on base ID, three-way conflicts; Run edited creates new job/invalidation preview. Never mutate current job snapshot.

### PUBLIC INTERFACES

saveDraft(EditPatch); commitRevision(baseId)->Revision; planInvalidation(diff)->AffectedStages.

### TESTS

Process kill after edit/autosave; conflicting same field; split required cue coverage; edit display-only no TTS; edit one spoken cue only affected synth;10000-cue scroll memory.

### EXPECTED RESULT

Editable project revisions with reproducible minimal recomputation.

### FAILURE CONDITIONS

IDs regenerate when timing changes; edit changes active job; locked tts text overwritten by display edit.

### OUTPUT ARTIFACT

artifacts/A23/editor-report.json

### NEXT TASK

A24

## A24 — Memory/casting, timeline/waveform, preview và outputs

### ID

A24

### GOAL

Memory/casting, timeline/waveform, preview và outputs

### WHY

Đủ công cụ review bản phim và thành phẩm Android.

### INPUT CONTRACT

A23 editor + A16 preview pipeline;08 screens/media specs.

### FILES TO CREATE

- `android/feature/memory/src/main/java/studio/aro/memory/MemoryScreen.kt`
- `android/feature/voices/src/main/java/studio/aro/voices/VoiceScreen.kt`
- `android/core/media/src/main/java/studio/aro/media/PreviewPlayer.kt`
- `android/core/media/src/main/java/studio/aro/media/DriveDataSource.kt`
- `android/feature/editor/src/main/java/studio/aro/editor/Timeline.kt`
- `android/feature/outputs/src/main/java/studio/aro/outputs/OutputLibrary.kt`
- `worker/src/aro_worker/media/waveform.py`
- `worker/tests/media/test_preview_waveform.py`
- `android/core/media/src/test/java/studio/aro/media/PlaybackTest.kt`

### FILES TO MODIFY

- `android/app/src/main/java/studio/aro/MainActivity.kt`
- `worker/src/aro_worker/jobs/commands.py`
- `contracts/v1/job.schema.json`
- `contracts/fixtures/valid.json`
- `contracts/fixtures/invalid.json`
- `worker/src/aro_worker/core/models.py`
- `android/core/model/src/main/java/studio/aro/model/WireModels.kt`

### EXACT IMPLEMENTATION

Glossary/Character Bible proposed/confirmed editing and directed relations, voice assignments/catalogue and worker-generated auditions. Add PREVIEW/AUDITION auxiliary job request operation via versioned required_feature without changing main FINAL contracts; immutable inputs/artifacts same runner. Waveform peaks100/10/1Hz tiles60s, timeline seek/loop cue. Media3 download-first verified private binaries, optional range auth DataSource; authoritative worker preview vs approximate source overlay labels. Output library uses published result ID+revision, never webViewLink as media URL.

### PUBLIC INTERFACES

Auxiliary job request operation PREVIEW/AUDITION/WAVEFORM schema minor1.1 with required_features; PreviewRepository.requestClip; Media3 ArtifactDataSource.

### TESTS

Private playback/seek401refresh/download fallback; stale preview after edit; font/glyph comparisons; waveform offsets; voice sample actual assigned engine; missing glyph and clipped subtitle review.

### EXPECTED RESULT

G3 complete editor/review/output workflow and accepted FINAL plays Android.

### FAILURE CONDITIONS

Preview uses stale revision with no label; Android TTS fake audition; auxiliary schema silently incompatible.

### OUTPUT ARTIFACT

artifacts/A24/preview-device-report.json

### NEXT TASK

A25

## A25 — Optional diarization và speaker proposals

### ID

A25

### GOAL

Optional diarization và speaker proposals

### WHY

Giảm công gán vai, giữ uncertainty và user confirmation.

### INPUT CONTRACT

A24 casting UI;05 diarization;12 optional gated models.

### FILES TO CREATE

- `worker/src/aro_worker/diarization/base.py`
- `worker/src/aro_worker/diarization/pyannote.py`
- `worker/src/aro_worker/diarization/assignment.py`
- `models/diarization.manifest.json`
- `locks/diarization-environment.lock`
- `worker/tests/media/test_diarization.py`

### FILES TO MODIFY

- `worker/src/aro_worker/core/runner.py`
- `worker/src/aro_worker/memory/proposals.py`
- `android/feature/memory/src/main/java/studio/aro/memory/MemoryScreen.kt`

### EXACT IMPLEMENTATION

Resolve official allowed pyannote models and token runtime; isolate env. Align turns/cues by overlap≥0.6, unknown/overlap proposals otherwise. Acoustic speaker ID separate character ID, user confirms map, no inference identity from pitch. Optional voice-style suggestion from catalogue only, classifier unverified disabled. Model absent skip optional stage with explicit reason, manual cast preserved.

### PUBLIC INTERFACES

diarize(audio)->SpeakerTurns; assign_proposals(cues,turns)->MemoryProposal[]; manual merge/unmerge retains confirmed entries.

### TESTS

Two known speakers+overlap fixture, low-confidence Unknown, repeated run manual mapping preserved, missing gated weights no crash main pipeline.

### EXPECTED RESULT

Optional feature usable with model evidence or honestly unavailable; never blocks manual MVP.

### FAILURE CONDITIONS

Auto confirmed relationships/gender identity; reuse EZ sealed weights; missing model creates fake speaker attribution.

### OUTPUT ARTIFACT

artifacts/A25/diarization-report.json

### NEXT TASK

A26

## A26 — Fault hardening và small-file packing

### ID

A26

### GOAL

Fault hardening và small-file packing

### WHY

Khả năng resume phải chịu Drive/mobile faults có kiểm soát.

### INPUT CONTRACT

A24 G2/G3 flows + A05 cache and all implemented stages;09 chaos policy.

### FILES TO CREATE

- `worker/src/aro_worker/cache/packs.py`
- `worker/tests/chaos/test_fault_matrix.py`
- `android/app/src/androidTest/java/studio/aro/RecoveryFlowTest.kt`
- `docs/runbooks/recovery.md`

### FILES TO MODIFY

- `worker/src/aro_worker/jobs/recovery.py`
- `worker/src/aro_worker/storage/artifacts.py`
- `android/core/sync/src/main/java/studio/aro/sync/JobSync.kt`

### EXACT IMPLEMENTATION

Execute full fault matrix11; repair concrete bugs with bounded changes. Pack up to100TTS/64MiB blobs with index per-cue offsets/hashes, immutable pack manifests; per-cue cache semantics unchanged. Bound uncommitted queue32units/512MiB. GC reachability/grace7days, auth reconnect/outbox consistency, schema unsupported feature path. Runtime reset after handoff/final upload tested.

### PUBLIC INTERFACES

PackStore.get_cue(ref)->verified bytes; RecoveryReport operation counters; compatibility contract retained.

### TESTS

SIGKILL all commit windows, network partition/stale worker, corrupt pack member,403quota, page2 duplicate, clock skew, Android process death+auth expiry.

### EXPECTED RESULT

Fault tests pass and recovery runbook maps issue→action, no data loss of committed units.

### FAILURE CONDITIONS

Packing makes cache whole-job only; GC deletes pending handoff/source; test disabled to get green.

### OUTPUT ARTIFACT

artifacts/A26/chaos-report.json

### NEXT TASK

A27

## A27 — 30/120/240 phút benchmark và resource budgets

### ID

A27

### GOAL

30/120/240 phút benchmark và resource budgets

### WHY

Không suy khả năng phim dài từ clip10s.

### INPUT CONTRACT

A26 stable pipeline; real/rights-permitted long cases;09 sizing and11 gates.

### FILES TO CREATE

- `tests/benchmarks/long_video.py`
- `tests/benchmarks/cases.json`
- `docs/benchmarks/long-video.md`

### FILES TO MODIFY

- `worker/src/aro_worker/core/resources.py`
- `configs/worker.example.yaml`

### EXACT IMPLEMENTATION

Run staged30→120→240min cases, record exact model/hardware/lock configs, source cues and output. Measure peak disk/RSS/VRAM/network/RTF/cost, end AV drift and full decode. Inject crash in ASR/TTS/render, prove upstream reuse. Adjust bounded concurrency/chunk/model profile only via documented config revision, rerun affected evidence. Test RF64 threshold and low-disk block. Do not promise4h PASS if runtime repeatedly ends before evidence.

### PUBLIC INTERFACES

python tests/benchmarks/long_video.py --case ID --report PATH; machine-readable BenchmarkReport.

### TESTS

All length tiers coverage100%, full decode, end drift≤100ms, budgets respected; no all-film RAM arrays; actual Colab lifecycle documented.

### EXPECTED RESULT

G4 performance portion measured, supported limits documented accurately.

### FAILURE CONDITIONS

Mock long run; estimate masquerades measurement; throughput hides dropped cues; oversized WAV corruption.

### OUTPUT ARTIFACT

artifacts/A27/benchmarks.json + Drive long outputs

### NEXT TASK

A28

## A28 — Release candidate và handoff implementation

### ID

A28

### GOAL

Release candidate và handoff implementation

### WHY

Ship reproducible artifacts với evidence và upgrade path.

### INPUT CONTRACT

G1/G2/G3/G4 PASS; actual dependency/model/font licenses verified; signing material user-controlled.

### FILES TO CREATE

- `docs/runbooks/colab.md`
- `docs/runbooks/android.md`
- `docs/runbooks/release.md`
- `LICENSE`
- `THIRD_PARTY_NOTICES.md`
- `release/manifest.schema.json`
- `scripts/package_release.py`

### FILES TO MODIFY

- `README.md`
- `worker/pyproject.toml`
- `android/app/build.gradle.kts`
- `.github/workflows/worker.yml`
- `.github/workflows/android.yml`

### EXACT IMPLEMENTATION

Package worker wheel + hashes, signed app artifact when key provided (otherwise explicit unsigned RC blocked release), model manifests/locks/notebook, notices/SBOM and schema compatibility notes. Fresh install/restart/upgrade Room test, offline local edits/auth reconnect, secret/log scanning. Validate current targetSdk/store policy. Link evidence and known limits in release manifest. Produce reviewable RC locally/Drive; no store publishing/public deployment without separate instruction.

### PUBLIC INTERFACES

make release; release manifest version/source commit/lock hashes/artifacts/gate refs.

### TESTS

Fresh machine bootstrap exact wheel/lock, current+API26 Android install, migration preserves projects, all required checks current revision, no secrets/proprietary assets in package.

### EXPECTED RESULT

Reviewable RC and clear next deployment step; no architecture-only claims of production PASS.

### FAILURE CONDITIONS

Missing actual license/weights hashes; unsigned labeled production release; old evidence after code change; automatic store publish.

### OUTPUT ARTIFACT

release/<version>/manifest.json + SHA256SUMS + handoff

### NEXT TASK

Handoff RC, STOP; deployment/store publish là yêu cầu riêng.

