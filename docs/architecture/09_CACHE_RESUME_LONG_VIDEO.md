# Cache, Resume và Long Video

**ARO_DESIGN_DECISION**. Cache content-addressed hai tầng: local scratch để compute, Drive manifests/blobs để survive Colab death. Cache có thể giúp tiết kiệm nhưng không là authority thay revision/required coverage.

## 1. Cache recipe

`key=SHA256("aro:<stage>:<version>\0" + JCS({inputs:[artifact_sha256...],params:effective_params,models:resolved_fingerprints,implementation_version,validator_version}))`.

Inputs ordered theo semantic contract, không hash whole project config khiến font edit invalidates ASR. Model fingerprint=upstream repo+immutable revision+file hashes+runtime/backend relevant options. Actual fallback engine/runtime phải vào recipe. Identity secret/key không vào cache; account/provider endpoint namespace public profile ID có thể vào khi behavior khác.

Blob bytes hash riêng. Hit yêu cầu manifest schema compatible, key đúng, all referenced blobs tồn tại/size/hash đúng, semantic validator compatible. Validate cheap JSON/WAV headers mỗi read; full hash lần download và khi cache corrupt suspicion. Không cache raw invalid LLM response như accepted translation.

## 2. Granularity và dependency table

| Artifact | Recipe includes | Không phụ thuộc |
|---|---|---|
| probe | source bytes, probe version | text/voice/style |
| extracted audio | source audio stream, offset, rate/channels, FFmpeg version | glossary |
| OCR observations | source/ROI/frame times/preprocess/OCR models | target language |
| ASR chunk | decoded audio hash/core/decode offsets/model/VAD/lang | font/voice |
| normalized cues | raw source result, normalization config, accepted edits | TTS voice |
| context match index | source text + memory/glossary/profile versions | font |
| translation block | exact source+timing budget+context dependencies+provider/prompt/schema | voice/font |
| polish | draft text/locks/readability thresholds/window/policy | encoder |
| raw TTS | effective spoken text, voice/engine/model/rate/normalizer | cue placement/font |
| fitted TTS | raw hash, available window/neighbor boundary/fit policy | unrelated cue text |
| separation | source audio hash + model/DSP/window plan | translation |
| voice track | ordered fitted refs, placements, D, mix profile | subtitle style |
| master mix | voice/background hashes/gains/duck/loudnorm | font |
| ASS | final display text/time + output canvas/font/style | raw TTS engine |
| render | source/master/ASS + output codec/canvas/encoder version | project title |
| final validation | rendered bytes + required coverage manifests/validator | UI sort preference |

## 3. Edit invalidation examples (normative)

| Edit | Recompute |
|---|---|
| font/color/margin | ASS → render → final validation/publish |
| encoder/quality | render → validation/publish |
| voice one character | raw/fitted TTS of assigned cues → voice/mix → render; rewrite if durations now fail |
| vi display+spoken text one cue | polish/QC cue → raw/fit cue → voice/mix + ASS → render |
| display-only punctuation with tts_text locked | subtitle QC/ASS/render, no TTS |
| source text one cue | affected anchor batches + source-context neighbor batches; proposals/index; downstream if output changes |
| cue timing | source timeline validation; affected translation duration budgets/readability; fit cue and borrowed-gap neighbor; ASS/voice/mix/render; raw TTS reuse if text same |
| source language/ASR model | affected ASR branch chunks → normalization and descendants; input audio reuse |
| ROI | OCR branch observations/cues and descendants; source bytes/probe/audio reuse |
| glossary entry updated | batches depending on entry; re-match source when new entry/alias, then affected descendants |
| character voice only | TTS assigned cues, no translation |
| character name/relation | matched context batches and descendants |
| background gain/ducking | mix/render only |
| auth key rotated | no media invalidate; provider requests continue after auth |

Pure visual edits MUST NOT invoke translation API. Upstream output bytes unchanged after revalidation: descendant key unchanged → cache hit. Cache invalidation means compute new keys, not deleting all historical files; rollback reuse possible.

## 4. Recovery algorithm

Load active assignment/request → download exact immutable revision → index committed checkpoints of attempts same job or allowed retry lineage → reject revoked result but inspect reusable blob/checkpoint dependencies → topological stage plan → validate matches → mark hits → start first missing unit. Any IN_PROGRESS snapshot without commit treated incomplete. Corrupt checkpoint/blobs quarantined with reason; recompute affected key, not whole project.

Durable checkpoint after every ASR/OCR chunk, translation batch, TTS cue (can pack blobs, manifests still per item) and every stage. Completed CPU result chưa upload chỉ LOCAL_PENDING, progress display separates computed vs persisted. If Drive unreachable stop compute khi uncommitted queue exceeds32 units hoặc512MiB; no claim durable resume for lost scratch. Rate-limited small-file uploads use bounded batching4 and sequential manifest commits; long-video pack completed TTS groups up to100 cues/64MiB with index of per-cue hashes, not one zip for whole project.

## 5. Disk / RAM planning

Duration D seconds. PCM s16 mono16k =32000*D bytes. Float32 stereo48k =384000*D bytes. 4h stereo master≈5.53GB decimal; không ước lượng mọi artifacts4h chỉ2–3GB. Peak disk estimate before start = input bytes + selected active PCM tracks + model download/extract peak +2*estimated output + checkpoint reserve. Add25% headroom và min2GiB free reserve. Encoder bitrate estimate uncertain → update disk forecast during render.

Default local scratch budget user-set, refuse khi free below estimated peak. RAM: decoded video queue≤8 frames; OCR queue≤32 observations; audio blocks10s; one GPU model active (evict prior model); translation concurrency2, cloud TTS2, local TTS1, upload4. Avoid ProcessPool CPU count loading N copies Whisper/GPU. ResourceController samples free disk/RAM/VRAM every5s; lower concurrency hoặc BLOCKED_RETRYABLE/DISK_PRESSURE before corruption.

Long WAV use RF64/FLAC; model cache on Drive optional compressed pinned artifacts, expanded local. Không chạy inference trên Drive FUSE random reads. Copy input needed once via API, streaming decoding local. Source must remain reachable until job result published.

## 6. Long-video stages

ASR30s core/45s max/1s overlap; OCR60s chunks/1s overlap, unchanged4fps; translation stable anchors; TTS per cue; separation60s/2s overlap; audio mixing streaming. End-to-end alignment kiểm tra đầu/giữa/cuối, offsets integer sample time tránh accumulated floating-point error.

Final render MVP một FFmpeg process streaming, không checkpoint giữa MP4; crash render chạy lại render nhưng không ASR/dịch/TTS. Long-video release chưa bắt buộc segmented video encoding vì concat codec/timebase/GOP phức tạp. Nếu thêm sau: keyframe-aligned segments cùng codec/extradata/timebase/audio strategy, subtitle timestamps local offsets và seam tests; không giới thiệu như đã hỗ trợ v1.

## 7. Garbage collection

Manifest reachability: roots=source revisions, published results, active jobs, pending handoffs, pinned cache. Only unreferenced objects eligible, grace7days; user cache quota LRU dựa usage metadata do controller ghi (Drive atime không đáng tin). GC do controller riêng, worker không xóa artifact của job khác. Dry-run list bytes/object IDs; tự động chỉ cache unreferenced đã policy cho phép, không input/output/project. Deleted remote blob cần cache miss, không failed job vĩnh viễn.

## 8. Performance/chaos acceptance

Bench30/120/240 phút ghi source hash, machine/runtime, dimensions/fps, stage wall time, peak RSS/VRAM/disk, network bytes, cost/usage, cue count, RTF. Không so sánh hash MP4 giữa hardware encoders; so semantic/media metrics và hash từng artifact trong cùng run.

Inject kill sau các checkpoint có cố định seed: assert finished ASR chunk/translation batch/TTS cue không chạy lại; unfinished unit tối đa work từ last durable commit; stale worker result ignored. Simulate timeout sau create thành công, duplicate Drive name, 2-page listing, upload failure99%, expired auth, truncated cache WAV, edited glossary during run, offline manual response. Long test decode all video, AV drift cuối≤100ms, required coverage100%, memory/disk trong configured budget, không lặng thoại để “đỗ”.
