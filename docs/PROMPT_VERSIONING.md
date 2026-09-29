# Prompt versioning từng bước

Mục tiêu là chứng minh được một request đã dùng prompt version nào, sau đó deploy một version mới và rollback mà không sửa source code. Đây không phải bài thi viết prompt hay hoặc làm A/B testing.

## 1. Phân biệt name, version và label

- **Prompt name:** tên cố định `day13-chat`.
- **Version:** một bản nội dung không thay đổi. Lưu nội dung mới sẽ tạo v2, v3…
- **Label:** con trỏ có thể chuyển giữa các version. Bài lab dùng `baseline`, `candidate` và `production`.

Ứng dụng lấy prompt theo name và label trong `.env`:

```dotenv
LANGFUSE_PROMPT_NAME=day13-chat
LANGFUSE_PROMPT_LABEL=production
```

Ví dụ, khi `production` trỏ tới v1, app lấy v1. Chuyển `production` sang v2 thì app lấy v2 mà không cần sửa code.

## 2. Tạo version 1

Trong project Langfuse cá nhân `day13-k4-l3a-<MSSV>`, mở **Prompt Management** và tạo **Text prompt**:

- Name: `day13-chat`
- Labels: `baseline`, `production`
- Nội dung:

```text
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

Không đổi tên hoặc xóa ba biến `{{feature}}`, `{{docs}}`, `{{message}}` vì code cần chúng để điền dữ liệu lúc chạy.

## 3. Tạo version 2

Mở lại `day13-chat` và tạo version mới trong cùng prompt. Không tạo prompt name khác. Ví dụ:

```text
Answer in no more than three concise bullet points.
Feature={{feature}}
Docs={{docs}}
Question={{message}}
```

Gắn label `candidate` cho v2. Kết quả cần có:

| Version | Label | Mục đích |
|---|---|---|
| v1 | `baseline`, `production` | Bản đang chạy ban đầu |
| v2 | `candidate` | Bản mới cần kiểm tra |

Langfuse tự chuyển `latest` sang version mới; không dùng `latest` thay cho các label của bài lab.

## 4. Tạo trace cho baseline và candidate

### Baseline v1

1. Đặt `LANGFUSE_PROMPT_LABEL=baseline` trong `.env`.
2. Dừng và chạy lại API để tránh dùng prompt đã cache.
3. Chạy `python scripts/load_test.py`.
4. Mở một trace mới và kiểm tra:
   - `prompt_source=langfuse`;
   - `prompt_name=day13-chat`;
   - `prompt_label=baseline`;
   - `prompt_version=1`.
5. Ghi trace ID vào `submission/REPORT.md`.

### Candidate v2

1. Đổi thành `LANGFUSE_PROMPT_LABEL=candidate`.
2. Dừng và chạy lại API.
3. Chạy lại `python scripts/load_test.py` bằng cùng workload.
4. Mở trace mới, xác nhận `prompt_label=candidate`, `prompt_version=2`.
5. Ghi trace ID thứ hai vào report.

## 5. Promote và rollback

1. Trên Langfuse, chuyển label `production` từ v1 sang v2.
2. Đặt `.env` thành `LANGFUSE_PROMPT_LABEL=production`, restart API và chạy một request.
3. Xác nhận trace dùng `production` và version 2. Đây là **promote**.
4. Chuyển `production` từ v2 về v1, restart API và chạy lại.
5. Xác nhận trace dùng `production` và version 1. Đây là **rollback**.

## 6. Khi thấy `local-v1`

- `prompt_source=local`: app chưa nhận Langfuse key.
- `prompt_source=local-fallback`: app đã bật Langfuse nhưng fetch thất bại. Kiểm tra key thuộc đúng project, `LANGFUSE_BASE_URL`, prompt name và label.
- Nếu đổi label nhưng vẫn thấy version cũ, restart API để xóa cache trong tiến trình cũ.
- Nếu Langfuse báo thiếu biến, kiểm tra đúng ba tên `feature`, `docs`, `message` và cú pháp hai dấu ngoặc nhọn, ví dụ `{{message}}`.

App dùng prompt local để không bị dừng khi Langfuse lỗi, nhưng trace `local-v1` không được tính là evidence prompt versioning.

## 7. Evidence

- `09-prompt-versions.png`: thấy prompt `day13-chat`, v1/v2 và các label.
- Hai trace ID chứng minh `baseline` dùng v1 và `candidate` dùng v2.
- `10-prompt-rollback.png`: thấy được `production` ở v2 và trạng thái sau rollback về v1. Nếu một ảnh khó đọc, tách thành `10a-production-v2.png` và `10b-rollback-v1.png`.
- Ghi các trace ID và đường dẫn ảnh vào `submission/REPORT.md`.

Không chụp trang API Keys, không để lộ secret và không dùng trace của người khác.

## 8. Checklist hoàn thành

- [ ] Chỉ có một prompt name `day13-chat`, bên trong có v1 và v2.
- [ ] Cả hai version giữ đủ ba biến bắt buộc.
- [ ] Trace baseline ghi version 1; trace candidate ghi version 2.
- [ ] Đã chuyển `production` sang v2 và chạy kiểm tra.
- [ ] Đã rollback `production` về v1 và chạy kiểm tra lại.
- [ ] Evidence và trace ID đã được ghi trong báo cáo.
