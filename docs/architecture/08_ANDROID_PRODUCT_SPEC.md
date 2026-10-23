# Android Product Specification

**ARO_DESIGN_DECISION**. Kotlin + Jetpack Compose/Material3 + Room + Media3/ExoPlayer + WorkManager + Coroutines/Flow + kotlinx.serialization. minSdk26; compile/target và Gradle/Kotlin pin sau compatibility task A19. Android là controller duy nhất đang active, không host model/FFmpeg hoặc tunnel.

## 1. Kiến trúc app

Single activity, Compose navigation, unidirectional state. `Screen → ViewModel → UseCase/Repository → Room outbox + DriveStore`. UI đọc StateFlow từ Room, không gọi Drive trực tiếp trong Composable. DTO wire schemas theo 04; entities tách riêng. Dependency injection constructor với Hilt nếu lock stack chọn, không framework custom.

Modules: app, core:model, core:database, core:drive, core:sync, core:media, feature:projects, feature:setup, feature:jobs, feature:handoff, feature:editor, feature:memory, feature:voices, feature:outputs, feature:settings. Interfaces: `ProjectRepository.observeProject(id):Flow<ProjectUiState>`, `submit(revisionId):JobId`, `sendCommand(Command):Receipt`, `sync(projectId):SyncReport`, `downloadArtifact(ref):LocalUri`, `saveDraft(EditPatch):DraftRevision`.

Room tables: ProjectEntity (remote head + local draft ref), CueEntity (PK projectId,datasetRevision,cueId), ArtifactEntity (hash/remoteId/localUri/downloadState), JobEntity/StageEntity, MemoryEntity/GlossaryEntity/CharacterEntity/VoiceAssignmentEntity, OutboxCommandEntity (commandId/seq/payloadHash/status), SyncCursorEntity, UploadSessionEntity (sensitive URI encrypted), PendingHandoffEntity, EditHistoryEntity. Migrations exported/tested; không destructive migration production.

## 2. Màn hình và acceptance theo màn hình

| Screen | User action/data | Required states / done |
|---|---|---|
| Home / Projects | recent/search/create/open | loading/empty/offline/stale/active; hiện output revision và job progress riêng |
| New Project | title/source lang/profile | lưu local draft trước upload; không mất draft khi kill app |
| Video picker | SAF ACTION_OPEN_DOCUMENT hoặc Drive picker | persist URI permission, validate read access; thumbnail/duration approximate, worker probe authoritative |
| Upload/Sync | bytes sent/retry/cancel/Wi-Fi policy | resumable session; READY chỉ sau hash/manifest; quota/auth action rõ |
| Pipeline settings | source method/audio/subtitle stream/OCR ROI/model availability/audio mode | options chỉ enabled khi worker capability hoặc manual fallback phù hợp |
| Translation profile | genre/rules/provider/manual/limits | không cần API key cho manual; test provider chạy worker, keys không lên Drive |
| Glossary | add/edit/import conflict resolution | scope/locked/pronunciation; duplicate mapping conflict không silent overwrite |
| Character Bible | proposed vs confirmed, relationships có hướng | unknown được giữ; merge/unmerge có lineage/audit |
| Voice assignment | voice per character/unknown fallback, audition | actual engine available, sample do worker synth theo job artifact; preview stale labelled |
| Jobs / Progress | Run/Resume/Retry/Cancel | stages, units, heartbeat age, wait reason, affected cue links; cancel requested≠cancelled |
| Manual Gemini | batch/context preview, Share/Copy/Paste/import JSON | validate IDs/hash, show exact errors, import ACK mới coi accepted |
| Subtitle editor | source+vi+tts text/time/speaker, merge/split, locks | virtual list, undo/redo, local draft saved, conflict resolve |
| Preview | play/seek/loop cue, waveform/timeline | source overlay approximate vs worker rendered revision; download progress/error |
| Output library | accepted FINAL list, play/download/share | private download default; link is authenticated Drive file, không publicize tự động |
| Settings | account/workspace/controller role/cache/network/model status | signout clears local credentials; preserve remote projects |

Navigation deep links bằng project_id/job_id/cue_id, không local file path truyền qua intents bên ngoài. Vietnamese user copy, cue text input Unicode, accessibility content descriptions và large-font layouts.

## 3. Drive auth và sync

OAuth Google identity + Drive authorization supported SDK. MVP Android `drive.file` cho workspace/files app tạo hoặc user chọn bằng picker; không giả scope này đọc mọi file cùng tài khoản. User source chọn ngoài workspace: picker grant cho file hoặc SAF stream copy vào app-owned workspace. Colab authorize cùng tài khoản có thể phạm vi khác; worker doctor phải GET exact root/source IDs và test create/read own manifest. Live smoke là gate A03/A20: nếu folder visibility giữa clients không đủ, tái chọn/authorize từng ID bằng supported flow; nếu vẫn không đủ thì documented full-drive scope deployment riêng cần consent/review, không âm thầm mở rộng scope.

Tokens SDK quản lý, dữ liệu sensitive bổ sung mã hóa Android Keystore; không plaintext token/API keys trong Room, logs, Drive JSON. Provider key nhập ở Colab secret/UI runtime; app lưu provider_profile_id, model options/public capabilities. Khi auth expired, show Reconnect và giữ outbox; không gửi duplicate job sau login.

Foreground active screen coroutine poll 10s±jitter; workers idle60s. App background: WorkManager periodic sync minimum15 phút thực tế có thể bị trì hoãn, không hứa real-time. One-time foreground WorkManager với notification cho upload/download lớn; tôn trọng current Android foreground service types/quota; paused transfer resume khi app mở. Cancellation có progress/notification, không kill worker remote bằng việc đóng app.

Sync reducer: fetch controller history/known job state IDs, validate generation/seq, Room transaction apply events và ack outbox. Không ghi raw snapshot từ worker vào draft người dùng đang sửa. Outbox persisted trước HTTP. Một controller_id/token role trong workspace; thấy fork thì read-only conflict UI. CLI controller phải bàn giao role khi Android kích hoạt.

## 4. Editor và revision control

Editing local tạo draft trên base_revision_id, autosave debounce500ms + on navigation. Save tạo immutable revision và media/config references; job đang chạy giữ snapshot cũ. “Chạy bản đã sửa” hiển thị affected stages từ invalidation planner, tạo job mới; không mutate active attempt. Manual lock translations ngăn model overwrite.

Timeline time inputs ms chính xác, sliders quantize frame nếu user chọn, không ép CFR với VFR. LazyColumn stable cue_id; Room paging500 cues, search indexed text, không load toàn waveform/video vào memory. Split tại user-selected time bên trong cue, require phân chia text; merge adjacent cues yêu cầu speaker compatible hoặc explicit override; lineage cập nhật required coverage.

Undo/redo local command patches bound1000 edits (cấu hình), persisted; remote revision acceptance là action riêng, undo tạo draft revision mới. Offline edit sync conflict với newer remote head: three-way compare base/local/remote; không conflict thì merge fields, cùng cue field khác giá trị thì user resolve. Chỉ controller active publish revision; multi-device edit dự thảo có thể export/import nhưng không concurrent write protocol v1.

## 5. Preview và waveform

Media3 dùng local file sau verified download là baseline reliable. Optional authenticated range streaming qua custom DataSource/HTTP client đến Drive binary `alt=media`; refresh401 một lần, hỗ trợ seek range206 và tránh log Authorization. Không dùng `webViewLink` như direct MP4 URL. Nếu server không hỗ trợ range ổn định, tự chuyển download-first và hiển thị trạng thái. App process death giữ URI/cache mapping; hết dung lượng thì dừng trước khi download vượt budget.

Source preview overlay Vietnamese cues cho edit nhanh, label “Xem thử bố cục”. Worker render 10–20s selected range bằng chính ASS/mix/filter tạo authoritative clip, key gồm revision/time range/style/master. Clip seek offset map global ms. Waveform worker tạo min/max peaks100Hz + downsample levels10Hz/1Hz, load tiles 60s; channels thống nhất với source preview. Audio cue audition uses exact fit artifact, không fake TTS trên điện thoại.

## 6. Run controls

Run disabled khi source chưa committed, required config absent hoặc controller inactive. Resume enabled WAITING_USER sau import/resolve, hoặc BLOCKED_RETRYABLE khi problem fixed. Worker stale: UI cho Resume với new attempt assignment, cảnh báo có thể còn process cũ nhưng chỉ active generation được publish. Retry terminal tạo new job retry_of và reuse artifacts. Cancel gửi command durable, disable publish current attempt ngay ở controller; UI giữ “Đang yêu cầu dừng” tới ack hoặc revoke result.

## 7. Android tests

Contract fixtures Python/Kotlin serialize same canonical hashes; Room migration; process death trong upload/outbox; offline edit recovery; tokens expired401; duplicate names/pagination; stale worker generation ignored; no exposed credentials in logs. Instrumentation flow chọn video→Run→handoff import→FINAL play; editor edit1cue chỉ TTS cue cần thiết khi vi thay, font change render-only. Low-memory device test dataset10000 cues, waveform laziness, rotation, font scale200%, TalkBack. UI không cần exact fps benchmark trước G1; release ghi measured jank/memory/device.
