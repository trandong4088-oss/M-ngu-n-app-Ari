# Dependency / Model Matrix

**ARO_DESIGN_DECISION + UNKNOWN**. Các version trong RE là observations của Windows bundle, không là Linux/Colab lock đã được kiểm thử. Tại bàn giao chưa cài/chạy model. Không lấy package/weights/fonts/audio samples từ bundle GenMedia/EZMaxSub. License code, weights, voice assets và service terms phải kiểm tra riêng; “open source” của engine không chứng minh weights được phép phân phối.

## 1. Runtime layout và lock policy

Core worker target Linux x86_64 Python3.11; optional isolated env TTS và diarization theo upstream requirements (3.11 hoặc3.12 sau smoke). Notebook bootstrap không `pip install -U`. `uv.lock` exact transitive resolution + model manifest immutable revisions/SHA256 + FFmpeg binary hash/build config + CUDA/cuDNN runtime fingerprint. Golden doctor lưu installed versions, không chỉ desired requirements.

Candidate seed có thể bắt đầu Python3.11.9, FFmpeg7.1.1, faster-whisper1.2.1, CTranslate2 tương thích CUDA target; đây là **proposed baseline**, không khẳng định latest hoặc đã chạy. VieNeu3.2.3/RapidOCR3.9.1/ORT1.27/CTranslate2 4.8.2 trong EZ RE phải xác minh có public distribution thật trước dùng. Package absence/version mismatch → chọn public release có license+API phù hợp, ghi ADR và pin; không download bundle đối thủ để lấp thiếu.

## 2. Python / system dependencies

| Component | Vai trò / source public | Evidence và quyết định / compatibility gate |
|---|---|---|
| CPython | python.org | core3.11, exact patch locked A01; PSF license upstream |
| uv + Pydantic v2 + jsonschema | github.com/astral-sh/uv, docs.pydantic.dev, python-jsonschema | strict models/schema generation/lock; JCS library cross-language fixture; pin resolved versions A02 |
| httpx + google-auth + google-api-python-client | public PyPI/Google repositories | Drive public API, credentials refresh and resumable upload; no custom OAuth scraping |
| FFmpeg/ffprobe + libass | ffmpeg.org, github.com/libass/libass | static/distro build with x264/AAC/loudnorm/sidechain/libass; store ffmpeg -version/-buildconf; LGPL/GPL depends build; redistribute with corresponding obligations |
| faster-whisper / CTranslate2 | github.com/SYSTRAN/faster-whisper, OpenNMT/CTranslate2 | observed in both RE; CPU int8/CUDA int8_float16 smoke; CTranslate2 CUDA/cuDNN compatibility matched actual runtime |
| RapidOCR / ONNX Runtime / OpenCV-headless | github.com/RapidAI/RapidOCR, microsoft/onnxruntime, opencv | observed engine; public OCR models gated separately; install one of ORT CPU/GPU per env, not both |
| soundfile / NumPy / soxr | public upstreams/PyPI | block PCM I/O/resample, ABI compatibility; avoid loading full timeline array |
| VieNeu Python package | upstream indicated by RE: pnnbao-ump/VieNeu-TTS | primary required by product, exact public package API/version/license UNKNOWN until A12 smoke |
| edge-tts | github.com/rany2/edge-tts | fallback required by brief, consumer network service availability UNKNOWN; inspect upstream LICENSE, do not copy RE claim “GPL-3.0” without verification |
| pyannote.audio + torch/torchaudio | github.com/pyannote/pyannote-audio, pytorch.org | optional speaker proposals; gated weight access/terms; torch/torchaudio matched pair, separate env if conflicting |
| UVR-compatible separation runner | github.com/Anjok07/ultimatevocalremovergui or public maintained adapter | reuse published open implementation, not EZ audiocpp binary; MDX preprocess exact recipe must be validated |
| public provider SDK or httpx | Google AI/OpenAI-compatible official API docs | explicit capability adapter, configured model ID, no hardcoded speculative model names from RE |
| pytest/ruff/type checker | public PyPI | dev-only, lock reproducible, relevant contract/media/fault tests |

No production dependency on Qt/MPV/Tauri/Node/Playwright/CapCut/FFmpeg-Kit. Android uses Media3; no heavy model package in APK.

## 3. Model matrix

| Capability | Target | Availability/license status tại design | Fallback / task exit |
|---|---|---|---|
| OCR ZH | PP-OCRv6 det+rec via RapidOCR | VERIFIED only RE reports filenames; official upstream weights/revision/language coverage UNKNOWN | A08 find official compatible model+card; if v6 unavailable choose supported public PP-OCR release and label actual version; OCR fixture must pass |
| ASR ZH | faster-whisper large-v3-turbo CT2 | engine verified RE; exact public converted checkpoint/revision and conversion provenance must resolve | public upstream converted model or documented conversion from official Whisper; CPU smaller profile explicit, cannot silently substitute Golden |
| VAD | Silero ONNX | observed RE; pin official github.com/snakers4/silero-vad weights/code separately | no-VAD fallback warning + test silence hallucination |
| TTS VI | VieNeu target v3-Turbo | RE reports pnnbao-ump/VieNeu-TTS-v3-Turbo + MOSS tokenizer; current upstream accessibility/weights license/API UNKNOWN | pin official available VieNeu variant, test pronunciation/duration; Edge fallback can demo but VieNeu-required MVP claim remains blocked until real VieNeu test |
| Audio codec for VieNeu | model-specific tokenizer, RE mentions OpenMOSS-Team/MOSS-Audio-Tokenizer-Nano-ONNX | UNKNOWN public revision compatibility/redistribution | adapter install only verified matching revision, no mixing codec files from unrelated versions |
| Separation | UVR-MDX-NET-Inst_HQ_4 | RE observes bundle; weight license and official distribution/preprocess UNKNOWN | original duck baseline, explicit output mode; clean-dub gate blocked until listening PASS |
| Diarization | pyannote supported official segmentation/embedding pipeline | package observed; exact weights not established by RE | disabled/manual cast default until token/license/download verified |
| Voice gender/style | optional public classifier | EZ weight architecture/xvectors purpose STRONG_INFERENCE, own license UNKNOWN | omit model v1; manual voice catalogue tags and Unknown; no copying sealed weights |
| Font | Noto Sans or Be Vietnam Pro | resolve official font revision/OFL license | bundle one verified VI-complete font + notices, missing glyph blocks authoritative preview |

Model manifest record: model_id, task, upstream_url, upstream_revision, files[{path,sha256,size}], license_id/license_url/license_text_sha256, redistribution_allowed_status, runtime_profile_id, input_profile/output_profile, smoke_fixture_id, verified_at, verifier, status=VERIFIED_FOR_ARO/BLOCKED. No empty sha, mutable `main` or placeholder accepted in production config. Model download verifies hash before load, resume partial and quarantine mismatches.

## 4. Android lock matrix

Kotlin/AGP/Gradle/JDK17/Compose compiler and BOM/Room/KSP/Media3/WorkManager/Coroutines/serialization/Google identity+Drive authorization/OkHttp must resolve as a tested matrix in `libs.versions.toml` and Gradle dependency verification metadata. Candidate modern lane: Kotlin2.2.x + matching Compose compiler plugin, AGP supporting compileSdk36, compatible Gradle wrapper, Compose BOM resolved exact release. These are constraints pending A19, not fabricated certified version pins. A19 chooses exact official published patch releases, writes wrapper SHA256, compiles minimal app + Room KSP, runs emulator API26 and current target. Release targetSdk follows store policy at release date, not copied from stale RE.

## 5. G0 reproducibility procedure (Arena executable task, not done now)

1. Query official release/model card/package metadata, record URL/revision/license, do not trust name alone.
2. Resolve isolated env from seed constraints; export exact lock+hashes. If core/TTS/diarization conflict, separate env stdio adapter, not unbounded dependency downgrade.
3. Doctor test FFmpeg filters and full2s encode/decode CPU; optional NVENC actual encoding.
4. OCR10 Chinese cropped frames, ASR20s zh speech, VieNeu5 VI lines including Hán-Việt/numbers, Edge1 line if enabled, separation10s impulse/music sample and stem reconstruction/alignment. Save actual model hashes/runtime metadata and metrics.
5. Run CPU/no-GPU lane and target Colab GPU lane. Unknown capability disabled or clear block; doctor never claims all features available just because package import succeeds.
6. Commit locks/manifests/license notices to new ARO repo before Golden; notebook installs exact worker wheel+locks by SHA. Maintain task evidence in artifacts/A01 and A12 etc.

## 6. Distribution decisions

Release checks actual binary/library/model licenses and required attribution/source offer; dynamic linking alone does not automatically remove copyleft obligations. Do not reuse the legally overbroad claims from EZ dependency notes. End-user media stays private Drive. Cloud fallback sends only needed text/audio under configured policy. No keys in notebooks/Drive/job snapshots. These requirements stem from the brief's clean-room constraint and reproducibility, not a claim that any specific unknown model is prohibited.
