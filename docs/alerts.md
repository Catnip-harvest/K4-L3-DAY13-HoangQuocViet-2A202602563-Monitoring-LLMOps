# Alerts và Runbook

Mỗi alert dựa trên triệu chứng người dùng thấy (chậm, lỗi) hoặc triệu chứng ngân sách (chi phí), không dựa vào tên thành phần nội bộ. Rule đầy đủ nằm trong [`config/alert_rules.yaml`](../config/alert_rules.yaml); SLO nằm trong [`config/slo.yaml`](../config/slo.yaml). Cả ba alert gửi về Slack `#day13-l3a-oncall`.

Quy trình chung cho mọi alert: **Metrics → Logs → Traces**. Dashboard cho biết panel nào xấu và từ lúc nào; `data/logs.jsonl` cho biết request nào bị ảnh hưởng (`correlation_id`, `trace_id`); trace trên Langfuse cho biết span nào gây ra.

## Alert 1

- Tên: `slow_responses_p95`
- Severity: P2
- Duration: 5m
- Kênh thông báo: Slack `#day13-l3a-oncall`
- SLI/SLO liên quan: `fast_successful_requests` (99.5% request thành công và ≤ 3000 ms trong 28 ngày)
- Điều kiện và thời gian duy trì: P95 `latency_ms` của `response_sent` > 2000 ms liên tục 5 phút. Ngưỡng 2000 ms nằm dưới đường SLO 3000 ms để cảnh báo trước khi budget bị đốt; baseline P95 là 157 ms nên jitter bình thường không thể chạm tới.
- Ảnh hưởng tới người dùng: câu trả lời chậm rõ rệt; nếu tiếp tục tăng sẽ vượt SLO.
- Ba bước kiểm tra đầu tiên:
  1. Dashboard panel Latency: P95 tăng từ lúc nào; TTFT có tăng theo không (TTFT tăng → LLM chậm; TTFT giữ nguyên → chậm trước bước LLM).
  2. Lọc log: `response_sent` có `latency_ms > 2000` trong khoảng đó, lấy `correlation_id` và `trace_id`.
  3. Mở trace đó trên Langfuse, so sánh duration của `retrieval` và `llm-generation`.
- Mitigation tạm thời: nếu `retrieval` chậm, giảm top-k/timeout retrieval hoặc trả lời bằng fallback không có context; nếu `llm-generation` chậm, chuyển sang model nhỏ hơn hoặc giới hạn `max_tokens`. Tắt incident practice bằng `python scripts/inject_incident.py --scenario rag_slow --disable`.
- Owner: Hoang Quoc Viet (primary on-call)

## Alert 2

- Tên: `high_error_rate`
- Severity: P1
- Duration: 5m
- Kênh thông báo: Slack `#day13-l3a-oncall`
- SLI/SLO liên quan: `fast_successful_requests`; guardrail `error_rate_pct_max: 2` và `retrieval_success_rate_pct_min: 90`
- Điều kiện và thời gian duy trì: error rate > 2% (cần ít nhất 5 request trong cửa sổ để tránh 1/1 = 100%) hoặc retrieval success < 90%, liên tục 5 phút.
- Ảnh hưởng tới người dùng: người dùng nhận HTTP 500, không có câu trả lời; mỗi lỗi đốt trực tiếp error budget.
- Ba bước kiểm tra đầu tiên:
  1. Dashboard panel Errors: error rate và breakdown theo `error_type`; retrieval success có giảm cùng lúc không.
  2. Lọc log `request_failed`: đọc `error_type`, `tool_name`, `tool_success`, `payload.detail`, lấy `correlation_id`.
  3. Mở trace cùng `correlation_id`: observation nào có level `ERROR` và status message gì.
- Mitigation tạm thời: nếu lỗi nằm ở retrieval (vector store timeout), bật fallback trả lời không cần context thay vì 500, thêm retry có giới hạn; nếu lỗi sau deploy/prompt mới, rollback label `production` về version trước. Tắt practice bằng `python scripts/inject_incident.py --scenario tool_fail --disable`.
- Owner: Hoang Quoc Viet (primary on-call)

## Alert 3

- Tên: `cost_per_request_spike`
- Severity: P2
- Duration: 15m
- Kênh thông báo: Slack `#day13-l3a-oncall`
- SLI/SLO liên quan: guardrail `daily_cost_usd_max: 2.5`
- Điều kiện và thời gian duy trì: chi phí trung bình mỗi request > 0.004 USD (gấp 2 baseline 0.00195 USD) hoặc tổng chi phí 1 giờ > 0.104 USD (2.5 USD/ngày chia 24), liên tục 15 phút. Cửa sổ dài hơn hai alert trên vì chi phí không làm hỏng trải nghiệm ngay lập tức.
- Ảnh hưởng tới người dùng: không thấy ngay, nhưng ngân sách ngày sẽ cạn trước hạn và có thể phải chặn tính năng.
- Ba bước kiểm tra đầu tiên:
  1. Dashboard panel Cost và Tokens: chi phí tăng do `tokens_in` (prompt/context dài hơn) hay `tokens_out` (câu trả lời dài hơn).
  2. Lọc log `response_sent` có `cost_usd` cao nhất, lấy `correlation_id`, xem `feature` nào bị ảnh hưởng.
  3. Mở trace: usage và cost của `llm-generation`, prompt version nào đang được dùng.
- Mitigation tạm thời: đặt `max_tokens` cho generation, rollback prompt nếu version mới làm câu trả lời dài hơn, chuyển feature bị ảnh hưởng sang model rẻ hơn. Tắt practice bằng `python scripts/inject_incident.py --scenario cost_spike --disable`.
- Owner: Hoang Quoc Viet (primary on-call)
