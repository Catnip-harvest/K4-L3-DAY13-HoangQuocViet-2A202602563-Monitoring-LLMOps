# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Evidence dẫn bằng đường dẫn tương đối trong `submission/evidence/`. Thời gian ghi theo UTC (ICT = UTC+7).

## 1. Thông tin học viên

- **Họ và tên:** Hoàng Quốc Việt
- **MSSV:** 2A202602563
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/Catnip-harvest/K4-L3-DAY13-HoangQuocViet-2A202602563-Monitoring-LLMOps
- **Commit SHA cuối:** ghi trên LMS khi nộp (commit cuối của nhánh `main`)
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602563` (Langfuse Cloud, region JP)

## 2. Evidence index

| # | Evidence | Ảnh | Output/text đi kèm |
|---|---|---|---|
| — | Baseline (trước khi sửa) | | [`evidence/baseline/`](evidence/baseline/) |
| 01 | Pytest cuối | [`01-pytest.png`](evidence/01-pytest.png) | [`01-pytest.txt`](evidence/01-pytest.txt) |
| 02 | Log validator | [`02-log-validator.png`](evidence/02-log-validator.png) | [`02-log-validator.txt`](evidence/02-log-validator.txt) |
| 03 | Dashboard validator | [`03-dashboard-validator.png`](evidence/03-dashboard-validator.png) | [`03-dashboard-validator.txt`](evidence/03-dashboard-validator.txt) |
| 04 | Structured log | [`04-structured-log.png`](evidence/04-structured-log.png) | [`04-structured-log.txt`](evidence/04-structured-log.txt) |
| 05 | PII redaction | [`05-pii-redaction.png`](evidence/05-pii-redaction.png) | [`05-pii-redaction.txt`](evidence/05-pii-redaction.txt) |
| 06 | Trace list (Langfuse) | [`06-trace-list.png`](evidence/06-trace-list.png) | [`06-trace-list.txt`](evidence/06-trace-list.txt) |
| 07 | Trace waterfall (Langfuse) | [`07-trace-waterfall.png`](evidence/07-trace-waterfall.png) | [`07-trace-waterfall.txt`](evidence/07-trace-waterfall.txt) |
| 08 | Trace metadata — generation (Langfuse) | [`08-trace-metadata.png`](evidence/08-trace-metadata.png) | |
| 09 | Prompt versions (Langfuse) | [`09-prompt-versions.png`](evidence/09-prompt-versions.png) | [`prompt-runs.txt`](evidence/prompt-runs.txt) |
| 10a | Promote `production` → v2 (Langfuse) | [`10a-production-v2.png`](evidence/10a-production-v2.png) | [`prompt-runs.txt`](evidence/prompt-runs.txt) |
| 10b | Rollback `production` → v1 (Langfuse) | [`10b-rollback-v1.png`](evidence/10b-rollback-v1.png) | [`prompt-runs.txt`](evidence/prompt-runs.txt) |
| 11 | Dashboard runtime, 60 phút | [`11-dashboard-overview.png`](evidence/11-dashboard-overview.png) | |
| 12 | Incident metric | [`12-incident-metric.png`](evidence/12-incident-metric.png) | [`12-incident-metric.txt`](evidence/12-incident-metric.txt), [`12-incident-run.txt`](evidence/12-incident-run.txt) |
| 13 | Incident log | [`13-incident-log.png`](evidence/13-incident-log.png) | [`13-incident-log.txt`](evidence/13-incident-log.txt) |
| 14 | Incident trace (Langfuse) | [`14-incident-trace.png`](evidence/14-incident-trace.png) | [`14-incident-trace.txt`](evidence/14-incident-trace.txt) |

Ảnh 06–10b và 14 chụp từ Langfuse UI của project cá nhân; dòng `scope.attributes.public_key` (Langfuse SDK tự chép public key vào metadata) đã được che đen. Ảnh 01–05 và 13 là output thật của lệnh, được `scripts/render_evidence.py` vẽ lại thành ảnh terminal; mỗi ảnh ghi lệnh và thời điểm chạy. Ảnh 11–12 do `scripts/build_dashboard.py` sinh từ `data/logs.jsonl`.

Các file `.txt` là output thật của lệnh trong repo (`scripts/export_traces.py` đọc trực tiếp từ Langfuse API của project cá nhân); public key mà Langfuse SDK tự chép vào metadata đã được lọc bỏ trước khi ghi.

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Baseline thiếu `correlation_id` (`MISSING`) và thiếu enrichment trên 20/21 dòng |
| `validate_dashboard.py` | 6/6 | 6/6 | Contract YAML đã đúng từ đầu; dashboard runtime là phần mới |
| `pytest` | 22 passed | 32 passed | Thêm test cho CCCD, thẻ, hộ chiếu, header, rò context, thứ tự processor, generation |
| Số traces hợp lệ | 0 (tracing tắt) | 99 traces trong project cá nhân (89 OK, 10 ERROR từ practice `tool_fail`) | Mỗi trace có root + retrieval + prompt-resolve + generation |
| Số PII leak | 0 | 0 | Baseline đã là 0 vì `summarize_text` scrub preview; phần mới là scrub **mọi** field (kể cả traceback, header) trước khi ghi |
| Latency P95 / TTFT P95 | 157 ms / 50 ms (không tracing) | 153 ms / 50 ms khi bình thường; 2653 ms / 50 ms trong challenge | Request đầu sau khi khởi động chậm hơn (~570 ms) do tải prompt từ Langfuse |
| Retrieval success rate | 100% | 100% bình thường; 86.5% khi practice `tool_fail` | |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `app/middleware.py` gọi `clear_contextvars()` đầu mỗi request để không rò context của request trước. Nếu client gửi `x-request-id` và giá trị chỉ gồm `[A-Za-z0-9._-]`, tối đa 64 ký tự, thì dùng lại; nếu không thì sinh `req-<8 hex>`. Kiểm tra định dạng để client không chèn xuống dòng/JSON/PII vào mọi log line. ID được bind vào structlog contextvars, lưu ở `request.state`, và trả về qua `x-request-id` cùng `x-response-time-ms`. Khi request lỗi 500, body cũng trả `correlation_id` để người dùng báo lỗi có thể tra được đúng log line.
- **Các metadata được ghi vào structured log:** `ts`, `level`, `service`, `event`, `correlation_id`, `env`, `user_id_hash` (SHA-256 cắt 12 ký tự, không lưu user ID thật), `session_id`, `feature`, `model`; `response_sent` thêm `latency_ms`, `ttft_ms`, `tokens_in/out`, `cost_usd`, `quality_score`, `tool_name`, `tool_success`; mọi log sau khi agent bắt đầu có thêm `trace_id` của Langfuse.
- **Cách bảo đảm PII được scrub trước khi ghi:** processor `scrub_event` đứng sau `format_exc_info` (để traceback đã thành chuỗi và cũng được scrub) và trước `JsonlFileProcessor`/`JSONRenderer`, nên cả file lẫn console đều không nhận dữ liệu thô. Scrubber đi đệ quy qua mọi field, không chỉ `payload`. Pattern: email, thẻ thanh toán (16 số có/không dấu cách, Amex 15 số), CCCD 12 số, điện thoại VN (`0`/`+84` + 9 số, có dấu cách/chấm/gạch), hộ chiếu VN (`[A-Z]` + 7 số). Thẻ và CCCD chạy trước điện thoại để không bị pattern điện thoại cắt mất một đoạn số.
- **Cách kiểm chứng kết quả:** `tests/test_pii.py` và `tests/test_logging_middleware.py` (gửi request thật qua ASGI có số điện thoại và thẻ, kiểm tra file log); validator 100/100 với detector độc lập của đề; `evidence/05-pii-redaction.txt` cho thấy ba query mẫu chứa email, điện thoại, thẻ đã thành `[REDACTED_*]`, và tìm chuỗi PII thô trên toàn file log trả về 0.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** mọi observation export được đều có `projectId = cmume7bpc01s5ad0d73l2qle1`, tức project `day13-k4-l3a-2A202602563` do tôi tạo; mỗi `trace_id` trong `06-trace-list.txt` khớp một dòng `response_sent`/`request_failed` trong `data/logs.jsonl`.
- **Cấu trúc root/retrieval/generation observations:** root `lab-agent-run` (agent) → `retrieval` (retriever, metadata `doc_count`, query đã scrub) → `prompt-resolve` (span) → `llm-generation` (generation: model, prompt link `day13-chat vN`, `usage_details` input/output, `cost_details` input/output/total, `completion_start_time` nên Langfuse hiển thị TTFT). Chỉ gửi preview đã scrub của prompt và câu trả lời, không gửi prompt thô. Span `prompt-resolve` được thêm sau khi thấy waterfall có khoảng trống ~400 ms không giải thích được (xem mục 8).
- **Cách nối trace với log:** hai chiều. Log → trace: `trace_id` nằm ngay trong log line. Trace → log: `correlation_id` nằm trong metadata của trace và mọi observation con.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1, labels `baseline` + `production` (template gốc của đề)
- **Version/label candidate:** v2, label `candidate` (thêm một dòng: trả lời tối đa 3 câu, chỉ dùng Docs)
- **Trace ID của mỗi version** (cùng input "Explain why metrics traces and logs work together"):
  - label `baseline` → v1: `a764ff178b2e7cf70fa2eb29eaf9e6f6` (`req-7b57dfed`), 32 input tokens
  - label `candidate` → v2: `b69c01508b837132c2263acec7b3456c` (`req-d8bd9de6`), 48 input tokens — prompt dài hơn thể hiện ngay ở token
  - `production` sau khi promote → v2: `e55b9698027411cd300341c49c23d8c6` (`req-064fa015`)
  - `production` sau khi rollback → v1: `dd0d6234e301a13fbecccfbca0b48e00` (`req-c7ca0cd5`)
- **Cách promote và rollback `production`:** `python scripts/manage_prompts.py promote --version 2` rồi `--version 1`. Một label chỉ nằm trên một version, nên gắn `production` cho version khác đồng thời gỡ nó khỏi version cũ; promote và rollback là cùng một thao tác, không cần deploy lại code. App cache prompt 60 giây, nên thay đổi có hiệu lực trong tối đa 60 giây. Trạng thái label trước/sau có timestamp trong `evidence/prompt-runs.txt`; ảnh UI ở `10a`/`10b`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `python scripts/build_dashboard.py` đọc `data/logs.jsonl` và vẽ đúng 6 panel theo `config/dashboard.yaml` (đọc tên panel, đơn vị, threshold và time range 60 phút từ chính file contract, không chép lại số): latency P50/P95/P99 + TTFT P95 (ms), traffic (request/phút), error rate + breakdown + retrieval success (%), cost theo phút + tích lũy (usd), tokens in/out (tokens), quality proxy (0–1). Mỗi panel có đường threshold/SLO màu đỏ; panel latency có thêm đường alert 2000 ms. Tiêu đề panel ghi giá trị hiện tại và OK/BREACH. Tham số `--minutes` chỉ dùng để phóng to ảnh incident.
- **SLO và lý do chọn:** `fast_successful_requests` — 99.5% request trong 28 ngày phải thành công **và** trả lời trong ≤ 3000 ms. Giữ 3000 ms bằng đúng đường latency của dashboard để biểu đồ và SLO không bao giờ lệch nhau. Baseline P95 là 157 ms trên fake LLM, nên 3000 ms rộng khoảng 19 lần một cách có chủ đích: nó mô tả lúc người dùng chat thấy "quá chậm", không phải tốc độ của model giả; model thật thường có P95 1–3 giây, siết theo baseline sẽ page vì dao động bình thường. Cảnh báo sớm là việc của alert 2000 ms.
- **Cách tính error budget:** budget = (1 − 0.995) × tổng request trong 28 ngày. Ví dụ 10.000 request → được phép 50 request xấu; 1 request/phút → 40.320 request → 201 request xấu. Burn rate = tỷ lệ request xấu trong cửa sổ / 0.005; burn rate ≥ 14.4 trong 1 giờ nghĩa là tiêu 2% budget 28 ngày chỉ trong 1 giờ và cần page ngay.
- **Ba alert và runbook tương ứng** (`config/alert_rules.yaml`, [`docs/alerts.md`](../docs/alerts.md), Slack `#day13-l3a-oncall`, owner: tôi):
  1. `slow_responses_p95` — P2 — P95 latency > 2000 ms trong 5 phút (thấp hơn đường SLO để cảnh báo trước khi đốt budget).
  2. `high_error_rate` — P1 — error rate > 2% (tối thiểu 5 request) hoặc retrieval success < 90% trong 5 phút.
  3. `cost_per_request_spike` — P2 — chi phí trung bình > 0.004 USD/request (2× baseline 0.00195) hoặc > 0.104 USD/giờ (2.5 USD/ngày ÷ 24) trong 15 phút.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort K4, file do Lab Coach gửi, đặt tại `config/challenge.json`, đã `.gitignore`, không commit).
- **Khoảng thời gian điều tra:** 2026-09-29 09:19:02–09:19:16 UTC (16:19 ICT). Traffic bình thường chạy lúc 09:18 để làm mốc; kiểm tra phục hồi lúc 09:21.
- **Triệu chứng từ metrics:** panel Latency: P95 tăng từ 153 ms (09:18) lên **2653 ms** (09:19), 5/5 request `feature=monitoring` vượt ngưỡng 2000 ms của challenge, alert `slow_responses_p95` bắn. Các panel khác không đổi: TTFT P95 giữ 50 ms, error 0%, retrieval success 100%, token và cost bình thường. TTFT không đổi nghĩa là phần chậm nằm **trước** khi model sinh token đầu tiên. Ở phía client, request chờ 10.6–13.3 giây (`12-incident-run.txt`), lâu hơn nhiều so với 2.65 giây mà server ghi nhận.
- **Log line và correlation ID liên quan:** lọc `response_sent` trong phút 09:19 có `latency_ms > 2000` được 5 request; chọn `req-64e0fe07`: `latency_ms=2653`, `ttft_ms=50`, `tool_success=true`, `tokens 36/113`, `trace_id=ea0bf2807430d4ed9aa1316a2289698c` (`13-incident-log.txt`). Log cũng cho thấy 5 request kết thúc cách nhau đúng ~2.66 giây, dù load test gửi đồng thời 5.
- **Trace ID và span gây ảnh hưởng:** `ea0bf2807430d4ed9aa1316a2289698c`: root 2654 ms, trong đó **`retrieval` 2500 ms (94%)**, `prompt-resolve` 0 ms, `llm-generation` 152 ms (bằng mức bình thường), prompt vẫn `day13-chat` v1. Các trace bình thường lúc 09:18 có retrieval 0–2 ms (`14-incident-trace.txt`).
- **Root cause:** bước retrieval (vector store) chậm thêm ~2.5 giây mỗi lần gọi, ảnh hưởng feature `monitoring`; LLM, prompt version và chi phí không liên quan. Ba lớp bằng chứng cùng chỉ một chỗ: metric (P95 tăng, TTFT không đổi) → log (request chậm nhưng thành công, token bình thường) → trace (retrieval chiếm 94% thời gian). Có một yếu tố khuếch đại: `agent.run` là hàm đồng bộ gọi trong `async def chat`, nên event loop xử lý từng request một; 5 request đồng thời phải xếp hàng, người dùng chờ tới 13.3 giây (≈ 5 × 2.65 giây) trong khi `latency_ms` và `x-response-time-ms` chỉ đo 2.65 giây. File challenge có ghi tên incident; kết luận trên được rút ra từ evidence và khớp với nó.
- **Fix action:** khôi phục retrieval (`python scripts/inject_incident.py --disable`). Chạy lại đúng 5 query của challenge lúc 09:21: P95 về **153 ms**. Với hệ thống thật: đặt timeout cho retrieval (vd 800 ms) và trả lời fallback không có context khi quá hạn, thay vì để cả request chờ.
- **Preventive measure:** (1) giữ alert `slow_responses_p95` 2000 ms, đã bắn trong sự cố này trước khi chạm đường SLO; (2) thêm alert theo span: P95 của `retrieval` > 500 ms, để page đúng đội sở hữu vector store; (3) chạy agent trong threadpool (`run_in_threadpool`) hoặc chuyển retrieval sang async, để một dependency chậm không chặn các request khác; (4) đo latency ở đầu vào (client/load balancer), vì số đo trong app đã giấu mất ~10 giây xếp hàng.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** ghi `trace_id` vào log context ngay khi agent bắt đầu. Nhờ vậy mọi log line sau đó, kể cả `request_failed`, trỏ thẳng tới trace; khi điều tra không phải lọc trace theo metadata mà mở đúng trace từ log line. Quyết định thứ hai: scrub mọi field thay vì chỉ `payload`, vì PII có thể đi vào qua traceback, thông điệp lỗi hoặc header.
- **Một lỗi/blocker đã gặp:** (1) waterfall đầu tiên có tổng 520–670 ms nhưng retrieval + LLM chỉ ~153 ms; (2) `GET /api/public/traces` của Langfuse trả 410 `LEGACY_API_UNAVAILABLE_FOR_NEW_ORGANIZATION`; (3) key đúng nhưng trả 401 với `cloud.langfuse.com`.
- **Cách tìm nguyên nhân và xử lý:** (1) khoảng trống chỉ xuất hiện ở request đầu sau khi khởi động hoặc khi cache prompt 60 giây hết hạn → đó là lần gọi mạng lấy prompt từ Langfuse chưa có span; thêm span `prompt-resolve` để waterfall giải thích được toàn bộ thời gian. (2) đọc thông báo lỗi, chuyển `scripts/export_traces.py` sang `GET /api/public/v2/observations`. (3) tài khoản nằm ở region JP; đặt `LANGFUSE_BASE_URL=https://jp.cloud.langfuse.com`.
- **Cách hiểu luồng Metrics → Logs → Traces:** metrics trả lời "có vấn đề gì, từ lúc nào" nhưng là số tổng hợp; logs trả lời "request nào bị" và cho `correlation_id`/`trace_id`; trace của đúng request đó trả lời "bước nào gây ra". Trong challenge: metric cho biết chậm trước token đầu tiên, log cho biết request vẫn thành công với token bình thường, trace chỉ ra retrieval. Thiếu một lớp thì chỉ đoán được: metric một mình không phân biệt được retrieval chậm hay LLM chậm.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** prompt là "code" thay đổi mà không cần deploy; nếu trace không ghi version thì không biết một thay đổi chất lượng hay chi phí đến từ đâu. Ở đây v2 làm input tokens tăng từ 32 lên 48 — nhìn thấy ngay trên trace. Rollback bằng label là thao tác một dòng, có hiệu lực trong 60 giây, nhanh hơn revert code. SLO + error budget biến "hệ thống có ổn không" thành một con số, quyết định khi nào page và khi nào được phép thử nghiệm.
- **Điều quan trọng nhất đã học:** HTTP 200 không có nghĩa là ổn — toàn bộ challenge trả 200 mà người dùng chờ tới 13 giây; và số đo bên trong ứng dụng có thể giấu thời gian xếp hàng, nên cần đo cả ở đầu vào.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** không sửa lỗi chặn event loop (chỉ ghi nhận), để hành vi của challenge giữ đúng như đề; quality proxy là heuristic của starter (câu trả lời fake cố định) nên chỉ có ý nghĩa minh họa; alert mới được định nghĩa và kiểm bằng dashboard, chưa nối vào Slack thật.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
