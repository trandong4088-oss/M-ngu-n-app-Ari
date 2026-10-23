# Drive Job Protocol v1

**ARO_DESIGN_DECISION**. Drive là blob store và mailbox có độ trễ; không phải POSIX filesystem, message broker hoặc distributed lock service. Không dùng rename trên Colab Drive mount làm transaction. API file ID mới là định danh; tên/path chỉ để người dùng nhìn.

## 1. Quyền ghi và giới hạn concurrency

MVP một `controller_id` đang hoạt động cho workspace: CLI trước G1, Android sau G1. Worker đọc lệnh, ghi artifacts/events của attempt được giao; không sửa project head, commands hoặc kết quả đã được controller công nhận. Không có nhiều controller tự tranh quyền. Chuyển CLI → Android chỉ sau CLI dừng phát lệnh, sync ack và export registry cho Android. Nếu thấy hai controller hoặc history fork, dừng phát lệnh với `CONTROLLER_CONFLICT`; không dùng last-write-wins.

Worker mỗi lần khởi động sinh `worker_session_id` UUID mới, quảng bá capabilities và heartbeat. Một session chỉ một process scheduler; local OS lock bảo vệ chạy trùng trên cùng máy. Controller giao attempt cho đúng session UUID. Worker khác không được claim tự động. Không dùng “check lease file không tồn tại rồi tạo” làm mutex.

Drive ACL không chặn được worker lỗi/cố ý phá dữ liệu trong cùng tài khoản; fencing dưới đây là ở protocol cho cooperative clients, không phải security boundary. Strict active-active cần transactional coordinator ngoài Drive; không thuộc MVP.

## 2. Layout logic và ownership

```text
/AroStudio/
  workspace.json                       controller: IDs/registry, schema
  controller/commands/<seq>-<id>.json  immutable, một controller
  workers/<session_id>/hello.json     worker, immutable
  workers/<session_id>/heartbeat.json worker, mutable advisory
  projects/<project_id>/
    project.json                      controller: mutable convenience head
    revisions/<revision_id>.json      controller: immutable authoritative input
    input/<source_id>/video.ext       immutable, upload verified
    jobs/<job_id>/request.json         immutable, links revision/config
    jobs/<job_id>/attempts/<attempt_id>/
      assignment.json                 controller, immutable
      state.json                      worker advisory snapshot
      events/<seq>.json               worker append-only
      checkpoints/<stage>/<key>.json  immutable commit manifests
      handoff/<batch_id>/request.json worker exports
      handoff/<batch_id>/request.txt  clean-room human prompt + JSON
      handoff/<batch_id>/responses/<response_id>.json controller imports
      result.json                     worker immutable candidate
    subtitle/<dataset_revision>/...  cues.jsonl, source.srt, vi.srt, vi.ass
    translation/<batch_key>/...      validated results, context refs
    memory/<revision_id>.json        immutable memory, glossary, cast
    tts/<key>/...                    raw.wav, fit.wav, manifest.json
    audio/<key>/...                  stems, voice.wav, master_audio.wav
    cache/<stage>/<key>/...          reusable committed blobs
    output/<job_id>/<attempt_id>/FINAL.mp4
    output/<job_id>/<attempt_id>/validation.json
    output/published/<publish_id>.json controller result acceptance
    output/FINAL.mp4                  optional Drive shortcut to accepted binary
```

`output/FINAL.mp4` là shortcut tiện dụng, không là binary dùng để validate. Binary thực có tên FINAL.mp4 trong thư mục attempt. Output library và Golden luôn giữ file ID binary + hash. Tránh hai worker ghi chung cùng một FINAL. Không bắt buộc tạo shortcut để job thành công; final binary và published manifest là bắt buộc. Tên thư mục tài liệu `Dự án Aro/ARO_MASTER` tách với runtime `/AroStudio`.

## 3. IDs, schema, timestamps

UUIDv4 lowercase cho workspace/project/source/job/attempt/revision/controller/session/command/response/publish. `cue_id` UUIDv4 lưu một lần trong committed dataset, không sinh từ timestamps. Artifact key SHA-256 64 hex. API Drive file IDs opaque string khác domain IDs. JSON UTF-8, `schema_version: "1.0"`, UTC RFC3339 timestamps; timeline milliseconds integer signed 64-bit, không dùng wall clock làm thứ tự lệnh. Lệnh controller có `seq` tăng đơn điệu, worker event seq riêng trong attempt.

Protocol từ chối major version không hỗ trợ; minor mới chỉ được đọc khi `required_features` nằm trong capability set. Fields không biết được bảo toàn trong extension map; trường ảnh hưởng hash phải được hiểu, nếu không chặn execution.

## 4. Upload, atomic visibility và idempotency

1. Controller upload input bằng resumable API, lưu upload session URI ở local secure store. Retry tiếp offset server xác nhận; 404/410 session expired thì tạo phiên mới trên reserved file ID nếu API cho phép, hoặc artifact ID mới được ghi lại trước commit.
2. Dùng Drive `files.generateIds` để cấp ID trước cho các file binary/JSON. Ghi mapping vào local durable outbox trước request. `create` retry cùng ID: 409 → GET exact ID, kiểm tra content digest/metadata; khác bytes → `ID_COLLISION`, không ghi đè.
3. Upload blob xong: verify size + checksum Drive nếu có; SHA-256 do client tự tính và readback với artifacts quan trọng. Lưu `aro_sha256` appProperties để tra cứu, không coi appProperties là bằng chứng checksum độc lập.
4. Upload immutable manifest cuối cùng, chứa exact file IDs, sizes, sha256 và dependency keys. Manifest này là commit marker. Reader bỏ qua blob chưa được manifest hợp lệ tham chiếu. Có thể cần retry exact ID khi list chưa thấy.
5. Ghi `state.json` để UI đọc nhanh; mất/hỏng snapshot thì rebuild từ event/checkpoint commit. Không có atomic transaction đa file. Local scratch dùng temp + fsync + rename; remote dùng publish-manifest-last.
6. Mỗi command có UUID, payload hash và seq. Ack lưu event có command_id; replay cùng ID+hash không chạy effect lần hai. Cùng ID khác hash là lỗi. Provider API không hỗ trợ idempotency vẫn có thể bị gọi lại nếu crash sau response trước checkpoint; report ghi rõ at-least-once computation, không hứa exactly-once billing.

List children phải đọc hết page tokens, filter trashed=false và parent IDs. Không chọn “file đầu tiên trùng tên”. Registry biết tất cả critical IDs. Poll active exact IDs thay vì quét cả Drive. `appProperties` hỗ trợ tìm lại orphan nhưng không enforce uniqueness.

## 5. Command contract

Envelope: `schema_version, workspace_id, controller_id, command_id, seq, type, project_id, job_id?, attempt_id?, expected_revision_id?, created_at, payload, payload_sha256`.

| type | Preconditions | payload / effect |
|---|---|---|
| CREATE_JOB | revision và input manifests committed | job_id, request_file_id; job QUEUED |
| START_ATTEMPT | current job không terminal; chosen session hello hợp lệ | new attempt_id, worker_session_id, generation, request_sha256; assignment committed trước command |
| IMPORT_RESPONSE | pending batch thuộc revision/context hiện tại | batch_id, request_sha256, response_file_id/hash; worker validates, không tự trust |
| RESUME | WAITING_USER hoặc BLOCKED_RETRYABLE; dependencies vẫn hợp lệ | same attempt nếu session còn sống; session mới phải START_ATTEMPT generation mới |
| RETRY | failed stage/invalid artifact đã có issue | stage_id, keys; không bypass validators; terminal job tạo job mới có retry_of |
| CANCEL | chưa published | mark current attempt revoked ở controller log, worker stop khi thấy command |
| ACCEPT_RESULT | result từ current non-revoked attempt, validation pass, bytes verified | publish_id, result_file_id/hash, final artifact; job SUCCEEDED |

Revision thay đổi không âm thầm thay request job. CREATE_JOB mới tham chiếu revision mới. Lệnh thiếu seq predecessor thì fetch predecessor và chờ; không đoán thứ tự theo modifiedTime.

## 6. State machines

Job: `QUEUED → RUNNING ↔ WAITING_USER`; `RUNNING → BLOCKED_RETRYABLE → RUNNING`; `RUNNING → VALIDATING → PUBLISH_PENDING → SUCCEEDED`. `QUEUED/RUNNING/WAITING_USER/BLOCKED_RETRYABLE/VALIDATING/PUBLISH_PENDING → CANCEL_REQUESTED → CANCELLED`. Lỗi permanent → FAILED. SUCCEEDED/FAILED/CANCELLED terminal; retry sau terminal tạo job mới, reuse artifacts.

Stage: `PENDING → RUNNING → SUCCEEDED`; `RUNNING → WAITING_USER | FAILED_RETRYABLE | FAILED_PERMANENT | CANCELLED`; retry hợp lệ → RUNNING với stage attempt counter tăng. `SKIPPED` chỉ optional stage, có reason/config hash. Cache hit vẫn SUCCEEDED với `cache_hit=true`, không SKIPPED.

Job status người dùng là reducer của controller commands + accepted worker events. Worker chỉ đề xuất state; không thể tự quyết SUCCEEDED. `WAITING_USER` có `reason` = SOURCE_REVIEW, MEMORY_CONFLICT, TRANSLATION_HANDOFF, TRANSLATION_REVIEW, TIMING_REVIEW, AUDIO_REVIEW hoặc CONFIG_REQUIRED. Cancel giữ checkpoint hợp lệ; resume job đã CANCELLED tạo job mới.

## 7. Lease, heartbeat, fencing

Assignment gồm `generation` integer tăng trong job, `attempt_id`, `worker_session_id`, `lease_ttl_s=120`. Heartbeat mỗi 30s: session, attempt, sequence, current_stage, last_checkpoint_file_id, `observed_command_seq`. UI hiển thị worker stale nếu không nhận heartbeat mới trong 120s theo monotonic elapsed tại reader, không tin hoàn toàn đồng hồ Colab.

Lease ở đây là liveness advisory, không cơ chế mutual exclusion. START_ATTEMPT giao exclusive authority bằng session/attempt cố định và controller log. Worker kiểm tra authority trước stage, trước checkpoint/result commit và mỗi 15s trong subprocess dài. Mất Drive quá TTL thì dừng tạo side effects cloud mới và dừng subprocess ở safe boundary, lưu local checkpoint chưa committed; tuyệt đối không publish từ dữ liệu authority cũ.

Controller muốn recover session stale: ghi revoke generation cũ rồi START_ATTEMPT generation mới; không tái sử dụng attempt_id. Worker cũ có thể còn chạy vì network partition, nhưng chỉ được ghi vào namespace cũ. Reader/controller từ chối result generation cũ dù nó hoàn tất muộn. Chỉ một controller tạo published manifest, nên không có stale FINAL overwrite. Các artifacts cũ chỉ reuse sau hash/validator và dependency match.

## 8. Crash/recovery theo điểm lỗi

| Điểm chết | Recovery |
|---|---|
| trước upload hoàn tất | không có manifest; resume upload hoặc discard orphan |
| sau blob, trước checkpoint manifest | blob orphan; probe hash để adopt hoặc GC sau grace period |
| sau checkpoint, trước snapshot | rebuild từ manifest; không gọi model lại |
| sau export response, trước IMPORT ack | replay response command ID; strict validation idempotent |
| giữa FFmpeg render | xóa local partial riêng attempt, render lại; reuse upstream |
| sau final upload, trước result | readback exact ID/hash, tạo result, không render lại |
| sau result, trước ACCEPT | controller verify rồi ACCEPT, không chạy lại pipeline |
| controller chết sau ACCEPT, trước shortcut | published manifest là authority, repair shortcut sau |
| Drive quota/auth mất | BLOCKED_RETRYABLE hoặc CONFIG_REQUIRED; không báo thành công |

State/event JSON tối đa 1 MiB; log chunk 256 KiB; cues chia JSONL theo page tối đa 500 cues, index manifest. Poll 10s ±20% jitter foreground; idle 60s; backoff full jitter min(60,2^attempt)s và Retry-After. 401 refresh một lần, 403 phân biệt permission/quota, 429/5xx retry tối đa 5 lần rồi block. Không blind retry permanent errors.

## 9. Bootstrap và giao quyền controller

Workspace được tạo bằng CLI hoặc Android mới, không tự chọn folder đầu tiên tên AroStudio. Controller ghi root registry, source/job/folder IDs và immutable INIT command seq1. Root reference được người dùng chọn bằng Drive picker hoặc nhập ID đã biết ở notebook. Mọi client phải đọc exact workspace_id/root_drive_id và controller_id trước phát lệnh. Workspace cùng tên khác ID là hai workspace khác nhau.

Giao quyền CLI→Android là thao tác tuần tự có kiểm soát, không election: CLI dừng submit, drain outbox/ACK, ghi immutable TRANSFER_CONTROLLER command chứa next_controller_id và last_seq; Android đọc exact transfer file/hash, tiếp tục seq=last_seq+1, cập nhật convenience workspace.json. CLI chuyển read-only vĩnh viễn trừ lần transfer mới. Nếu CLI mất trước transfer và không thể chứng minh writer đã dừng, recovery tạo workspace mới có workspace_id/controller_id mới và người dùng chọn import dữ liệu từ workspace cũ; không tự takeover theo heartbeat. Active jobs workspace cũ chỉ được xem/read/reuse artifacts đã kiểm tra, không publish vào workspace mới. Đây là giới hạn single-controller được UI hiển thị, không distributed CAS guarantee.

Commands discovery: workspace registry giữ commands_folder_id; đọc đủ pages, verify controller/seq/hash và previous command hash được lưu ở envelope extension `previous_command_sha256`. Thiếu predecessor chờ fetch/retry; hai command cùng seq khác digest là fork → CONTROLLER_CONFLICT. AppProperties chỉ index, không authority. CommandReceipt là `{command_id,seq,payload_sha256,drive_file_id,upload_state}`; receipt upload không đồng nghĩa worker đã ACK effect.

## 10. Interfaces bắt buộc

```python
class DriveStore(Protocol):
    def reserve_ids(self, count: int) -> list[str]: ...
    def list_children(self, parent_id: str, page_token: str | None) -> Page: ...
    def read_json(self, file_id: str, max_bytes: int) -> dict: ...
    def create_immutable(self, reserved_id: str, parent_id: str, name: str, data: bytes, sha256: str) -> FileRef: ...
    def upload_resumable(self, reserved_id: str, parent_id: str, local_path: Path, cancel: CancelToken) -> FileRef: ...
    def download_verified(self, artifact: ArtifactRef, local_path: Path) -> Path: ...

class JobController(Protocol):
    def submit(self, revision: ProjectRevision, config: PipelineConfig) -> JobRequest: ...
    def assign(self, job_id: str, session_id: str) -> AttemptAssignment: ...
    def command(self, command: Command) -> CommandReceipt: ...
    def accept_result(self, result: ResultManifest) -> PublishedResult: ...
```

`FakeDriveStore` phải mô phỏng pagination, duplicate names, delayed listing, read-after-timeout và crash windows. Test thật Drive phải chứng minh reserved-ID duplicate-create behavior; nếu adapter không hỗ trợ, task A03 bị chặn thay vì giả lập mutex bằng tên file. Android có equivalent suspend interfaces, cùng fixtures wire trong 04.
