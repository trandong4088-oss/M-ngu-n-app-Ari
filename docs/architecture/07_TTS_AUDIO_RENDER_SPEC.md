# TTS, Audio và Render

**ARO_DESIGN_DECISION**. Đầu vào cue dataset tiếng Việt đã validated. Đầu ra binary FINAL.mp4 và validation/provenance. TTS primary VieNeu; Edge-TTS fallback explicit, không coi thư viện consumer endpoint là dịch vụ có SLA. Model/source/license pin theo 12.

## 1. Interfaces và audio formats

```python
class TtsEngine(Protocol):
    def voices(self) -> list[Voice]: ...
    def synthesize(self, request: SynthesisRequest, cancel: CancelToken) -> RawTtsArtifact: ...
    def fingerprint(self) -> ModelFingerprint: ...

def fit_cue(cue, raw, window, policy, rewrite_provider) -> TtsCueResult: ...
def build_voice_track(fits, duration_ms, out_path, cancel) -> Artifact: ...
def separate(audio_ref, model_manifest, window_plan, cancel) -> SeparationResult: ...
def mix_master(voice, background, config, duration_ms, cancel) -> MixResult: ...
def build_ass(cues, display_canvas, style, font_manifest) -> Artifact: ...
def render(source, master, ass, config, cancel, progress) -> RenderResult: ...
```

Native TTS có thể 16k/24k/48k; giữ native raw để không mất chất lượng. Chuẩn hóa fitted mono float32 48k, master stereo float32 48k, final AAC 48k/192k. Không giả mọi engine sinh 16k. FFmpeg/soundfile đo sample count; duration_ms=round(samples*1000/sample_rate). Giữ sample count trong artifact metadata.

## 2. Synthesis và casting

Chọn voice theo cue override → confirmed character assignment → Unknown fallback. Voice selection freeze trong config, actual engine/model/voice ghi trên mỗi cue. Không tự thay voice theo câu riêng làm nhân vật đổi giọng ngẫu nhiên: nếu primary lỗi hệ thống, fallback toàn nhóm character chưa committed; phần đã synth được đánh mixed-engine warning, cho user chọn resynth nhóm để nhất quán. Fallback policy `preserve_committed` hoặc `resynth_character`, default resynth_character khi cần publish chất lượng.

Normalize TTS text bằng quy tắc ARO cho số, đơn vị, dấu câu, abbreviation và approved pronunciation glossary. Không copy acronym dictionary đối thủ. Display text không bị sửa theo cách đọc. Mỗi raw WAV cache key = normalized text + normalization version + actual engine/model/voice + speed/style + seed nếu hỗ trợ + output profile. Cue ID không cần vào raw content key; fitted key phải có available window/placement policy.

Adapter là isolation boundary: VieNeu env riêng nếu dependency không tương thích ASR; RPC local JSON file/stdio, không notebook business logic. Edge response MP3 decode về WAV, verify speech nonempty; retry mạng tối đa 3 attempts, backoff/cancel và concurrency2. Model local concurrency1. Prewarm optional sau doctor PASS.

## 3. Timing fit hữu hạn

Cho cue i: base window [s_i,e_i). Tính `fit_end_i=min(e_i+200ms, next_required_start-50ms, video_duration)` nếu các cue không overlap; không tự mượn gap khi người dùng khóa timing. Nếu next start≤e_i (thoại chồng), không rút ngắn vô lý: đánh overlapping dialogue và dùng nhiều voice lanes sau user review. MVP single-lane Golden tránh overlap phức tạp hoặc sửa thủ công có ghi nhận. available=max(0,fit_end-s_i).

1. Synth text hiện tại; trim leading/trailing silence chỉ tối đa 100ms mỗi đầu, threshold -45dB, bảo vệ speech onset; không cắt phụ âm.
2. Nếu measured≤available, đặt onset tại s_i, giữ tốc độ1.0, pad silence phần còn lại. Không kéo chậm ép đầy cửa sổ.
3. Nếu quá dài, tối đa 2 rewrite attempts giữ tên/số/phủ định/ý chính; mỗi lần resynth và đo. Rewrite provider API hoặc manual DUB_REWRITE, không cần API key mới cho manual. Candidate chỉ adopted sau validator. Bản ngắn mất ý bị reject dù fit.
4. Sau rewrite, `tempo=measured/available`; nếu ≤1.2, atempo mức cần thiết [1.0,1.2], đo lại. Chấp nhận ≤available+20ms chỉ khi excess là silence trim được; không cắt speech cuối.
5. Vẫn dài hoặc available=0 → NEEDS_REVIEW/TIMING_OVERFLOW. Người dùng sửa text, voice/rate hoặc cue timing; job WAITING_USER. Không force arbitrarily high atempo, không keyword-only làm mất ý, không silence placeholder trong result thành công.

`display_vi` và `tts_text` có thể khác cách diễn đạt nhưng semantic review phải xác nhận. Nếu rewrite tốt cho cả hai, user/approved rule có thể adopt display text bằng revision mới. Raw cache reuse khi đổi timing; fit cache invalidates window của cue và neighbor có liên quan.

## 4. Build voice track không O(duration RAM)

Write disk-backed float32 mono 48k theo block 10s hoặc memmap, offset_samples=round(start_ms*48). Place fit samples, sum lanes khi explicitly approved overlap, limit không clipping. Fade 5ms chỉ ở biên silence phù hợp, không dùng fade 25ms cố định cắt âm đầu. Track dài đúng video duration samples, pad cuối. Record actual speech onset/end theo detector để QC, không coi duration WAV padded là toàn bộ speech.

Với file >4GiB dùng RF64 (`-rf64 auto`) hoặc FLAC chunk/float scratch; không để WAV RIFF size overflow. Không tạo một filtergraph có hàng chục nghìn adelay inputs. Per-window mixing boundary guard 500ms và deterministic ownership tránh click; G1 được phép full streaming single FFmpeg mix.

## 5. Separation / original ducking

UVR-MDX adapter public implementation + model metadata xác minh. Model input rate/channels và STFT config lấy từ official model card/reference implementation đã kiểm thử, không đoán từ tên ONNX. Artifact stems có start offset/duration/sample count, latency compensation measured bằng fixture impulse. Chia cửa sổ60s overlap2s, overlap-add Hann crossfade với normalized sum; model receptive field có thể yêu cầu đổi overlap ở G0.

Tách nhạc không bảo đảm xóa thoại hoàn toàn hoặc giữ SFX. Kiểm tra nghe ít nhất 3 vùng lời thoại, 2 vùng nhạc/SFX; music separator có thể để lại speech hoặc mất âm hiệu ứng. Nếu model thiếu/fail/QC không đạt và policy cho phép → background=original audio, mode actual DUCK_ORIGINAL, hiển thị “Nền còn giọng Trung”. Không label CLEAN_DUB. Nếu user bắt buộc sạch thoại → AUDIO_REVIEW, không silent fallback.

No source audio và có source text: background silence với NO_SOURCE_AUDIO, QC background listenability not-applicable có lý do; Golden chuẩn phải có nền thực.

## 6. Mix và loudness chính xác

Normalize continuous voice track theo loudness đo toàn track (không từng cue), target khoảng -18 LUFS trước mix để có headroom; background gain khởi đầu -6dB separated, -12dB original. Actual mix cần listening test. Convert dB threshold sang linear amplitude: 10^(-26/20)≈0.050119; `sidechaincompress threshold` dùng linear, không truyền -26.

FFmpeg pattern tiêu chuẩn, tên path cố định trong isolated scratch, argv/filter script được builder escape:

```text
[0:a]aresample=48000,aformat=channel_layouts=stereo,volume=0.251189[bg];
[1:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[key][voice];
[bg][key]sidechaincompress=threshold=0.050119:ratio=4:attack=20:release=250:makeup=1[duck];
[duck][voice]amix=inputs=2:duration=longest:dropout_transition=0:normalize=0[mix]
```

Pattern dùng original gain -12dB; separated config đổi volume tương ứng. Input0 background, input1 voice. Cả hai đã pad/trim đúng D. Từ mix thực hiện loudnorm **hai pass** target I=-16 LUFS, LRA=11, TP=-1.5dBTP. Pass1 analyze JSON, pass2 measured_I/TP/LRA/thresh/offset, explicit resample48k sau loudnorm (filter có thể upsample). Đo lại final master và final AAC decode. Không normalize nền và voice đều -16 rồi cộng trực tiếp; không dùng limiter để che clipping quá mức.

QC: integrated loudness -16±1LU, true peak final encoded≤-1dBTP, no NaN/clipped samples. Fixture steady music + voice burst phải giảm bg RMS≥3dB trong speech và phục hồi sau release; nghe nền còn tự nhiên. Nếu silence toàn track, loudnorm đo -inf → fail TTS_MISSING với required dialogue, không đưa NaN vào pass2.

## 7. SRT → ASS và canvas

Xuất `vi.srt`, `vi.ass`; file render-ready tên `vi_final.ass` có thể là alias local của vi.ass, không thêm dataset khác. ASS PlayResX/Y bằng **canvas output sau rotation/SAR/scale/pad**, không luôn bằng encoded W/H nguồn. Preserve display aspect ratio, max long edge1920, even dimensions; fonts Noto Sans/Be Vietnam Pro từ upstream license hợp lệ. Chọn một font mặc định Noto Sans, size≈0.045*H, outline≈0.002*H (min1), safe margins5% canvas; style snapshot ghi pixel values.

SRT timestamp integer ms; ASS centiseconds: start=floor(start_ms/10), end=ceil(end_ms/10), min duration1cs, clamp duration. ASS literal escaping: không cho user text tạo override tag; sanitize braces/backslash và convert line breaks thành ASS \N qua encoder riêng đã test. Validate font glyph coverage và render bbox samples; wrap width bằng glyph measurement, 42 grapheme chỉ precheck.

Hardsub ROI do user chọn: default Việt đặt trên vùng Trung hoặc opaque box có preview; không tự mask logo hoặc crop mất hình. Source hard subtitles vẫn là pixels. Media3 text overlay preview là approximate layout; authoritative preview là Worker render clip với chính libass/font/style pipeline.

## 8. Render

FFmpeg có libass, loudnorm, sidechaincompress, amix, aresample, libx264, aac. HDR baseline block; rotation normalize once, metadata rotate=0; video time origin/audio offset theo probe. VFR preserve presentation timestamps nếu encoder/mux hỗ trợ, không đặt -r vô cớ. Explicit duration D sau pad audio; không dùng `-shortest` che audio thiếu hoặc cắt mất phần cuối.

Command conceptual cho nguồn SDR đã normalize:

```text
ffmpeg -nostdin -y -i source.mp4 -i master_audio.wav
  -filter_complex_script render.filter
  -map [vout] -map 1:a:0
  -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p
  -c:a aac -b:a 192k -ar 48000 -ac 2
  -t D_SECONDS -movflags +faststart -map_metadata -1
  -progress pipe:1 -nostats candidate.mp4
```

render.filter = orientation/display scale/pad/setsar=1 + ass filter với local safe paths. Không shell=True. Encoder auto: kiểm tra `-encoders` rồi encode thử2s (driver/VRAM có thể thiếu dù name tồn tại); NVENC `-preset p4 -cq21`, không truyền x264 preset `medium` như nghĩa tương đương. Runtime NVENC fail chỉ retry CPU một lần sau xóa partial riêng attempt; filter/invalid input/disk full không retry vô nghĩa. CPU libx264 deterministic functional behavior; không đòi binary hash giống NVENC.

## 9. Final validation và publish

Probe output codecs H264/AAC/yuv420p, positive dimensions/duration, 1 selected video+audio, expected rotation/timebase; duration error≤max(100ms,2 frames) cho Golden. `ffmpeg -v error -xerror -i candidate.mp4 -map 0:v:0 -map 0:a:0 -f null -` phải exit0, không chỉ đọc frame đầu. Verify moov trước mdat bằng MP4 atom inspection để faststart thật.

Check required translation/TTS IDs 100%, fits valid, no blocking issues, subtitle raster samples đúng Việt/font/safe region, audio nghe rõ/nền còn nghe. Validation reference đúng source/config/attempt. Upload binary FINAL.mp4 (resumable), validation và provenance; download/read hash final một lần Golden; create result manifest last. Controller active generation verify rồi ACCEPT_RESULT. Không rename partial thành FINAL trước QC.

## 10. Failure tests

TTS empty WAV; too long >1.2x; clipping; no-background-policy; offset stems; silence master; missing font; text chứa ASS tags; NVENC listed nhưng encode fail; corrupt last MP4 packets; wrong duration vì -shortest; upload killed99%; stale worker result. Mỗi lỗi phải chặn publish hoặc fallback documented, không pass từ file existence.
