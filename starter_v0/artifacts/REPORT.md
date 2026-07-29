# Day 04 Lab v2 Report — Research Agent

> File này gồm 2 phần, deadline khác nhau:
> - **PHẦN A — Giới thiệu agent**: ngắn gọn 1 trang để team khác hiểu nhanh agent có tool gì, làm được gì, thử bằng câu hỏi nào. Xong trước 16:30 để làm tài liệu phụ trợ khi demo.
> - **PHẦN B — Chi tiết / Bằng chứng**: bảng đầy đủ (v0–v3, failure, eval, chat) dựa trên log thật. Có thể hoàn thiện sau buổi debate để nộp bài.

## Team

- Team: G20 
- Members:
Nguyễn Phương Thuỳ
Nguyễn Thị Huyền Trang 
Lê Thị Trúc Linh 
Lưu Xuân Dũng 
Ngô Lưu Quốc Đạt
- Provider/model: Openrouter/GPT-4o-mini

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Agent này là một research assistant agent dùng model thực tế để chọn và gọi tool thật.
Nó hỗ trợ: tìm tweet của một account cụ thể, tìm tweet theo chủ đề, tìm tin tức web theo topic/timeframe, đọc nội dung URL, và chuyển dữ liệu thu thập được thành markdown digest.

Nó cũng hỗ trợ boundary control: hỏi lại khi thiếu thông tin và xác nhận trước khi gửi tin nhạy cảm.

**Link dùng thử (truy cập được trong showdown):**
- `python -m streamlit run app.py` để mở UI local tại `http://localhost:8501`
- Nếu nhóm deploy công khai, dán public URL ở đây.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `ask_user_for_info` | Hỏi lại user khi thiếu thông tin quan trọng hoặc confirm yes/no trước hành động nhạy cảm. | không |
| `get_user_recent_tweets` | Lấy tweet gần đây từ một handle Twitter cụ thể. | không |
| `search_twitter_by_keyword` | Tìm tweet theo từ khóa/chủ đề trên Twitter, chọn Latest/Top. | không |
| `search_web_information` | Tìm thông tin/tin tức trên web theo query/topic/timeframe. | không |
| `read_webpage_content` | Đọc nội dung của một URL cung cấp sẵn. | không |
| `format_data_to_markdown` | Định dạng kết quả thành markdown dễ đọc. | không |
| `send_telegram_message` | Gửi tin nhắn Telegram sau khi user xác nhận. | optional/bonus |
| `get_exchange_rate` | Tra cứu tỷ giá ngoại tệ hiện tại. | optional/bonus |

## A3. Câu hỏi mẫu để thử

1. "Tweet mới nhất của Sam Altman là gì?"
2. "Mọi người đang bàn gì về GPT-5 trên Twitter?"
3. "Tin tức AI hôm nay có gì nổi bật?"
4. "Tóm tắt bài này giúp mình: https://openai.com/blog/gpt-5"
5. "Cho mình tỷ giá USD sang VND hôm nay."

## A4. Kịch bản demo đã rehearse

| Scenario | Tool trace cần thấy | Câu chuyện cải thiện version | Fallback run/transcript |
|---|---|---|---|
| Tìm tweet của Sam Altman | `get_user_recent_tweets(screenname="sama")` | v0 sai routing, v4 routing đúng và args chuẩn | `starter_v0/runs/v4_B_base_openrouter_20260729T160311436025.json` |
| Tìm tweet theo chủ đề GPT-5 | `search_twitter_by_keyword(query="GPT-5", search_type="Latest")` | Đã tách rõ search Twitter/chuyển sang web khi user yêu cầu | `starter_v0/runs/v4_B_base_openrouter_20260729T160311436025.json` |
| Tìm tin tức AI hôm nay | `search_web_information(query="AI", topic="news", timeframe="day")` | v0 thêm từ dư thừa `news`, v4 sửa query/topic/timeframe chuẩn | `starter_v0/runs/v4_B_base_openrouter_20260729T160311436025.json` |
| Đọc URL cụ thể | `read_webpage_content(url=...)` | Xác nhận URL và gọi tool đúng khi user cung cấp link | chưa có transcript |
| Gửi Telegram sau xác nhận | `ask_user_for_info(response_type="yes_no")` → `send_telegram_message(...)` | Kiểm tra boundary confirm nếu dùng Telegram | chưa có transcript |

---

# PHẦN B — Chi tiết / Bằng chứng

> Điều kiện metric hợp lệ: `provider_error_cases` phải bằng `0`; `measured_cases` phải bằng `total_cases`; và bất kỳ `tool_results` nào có error đều phải được review thủ công vì routing PASS không chứng minh tool execution đã đúng.

## B1. Version evidence

Dữ liệu lấy trực tiếp từ `starter_v0/artifacts/version_log.csv`.

| Version | Prompt/tool change | Hypothesis | Metric name | Before | After | Run File |
|---|---|---|---|---:|---:|---|
| v0 | baseline | baseline run | case_accuracy | — | 0.75 | `starter_v0/runs/v0_B_base_openrouter_20260729T150637162094.json` |
| v1 | `tools.yaml` | Đổi tên tool rõ ràng và viết lại mô tả sẽ giúp LLM hiểu đúng chức năng | case_accuracy | 0.70 | 0.95 | `starter_v0/runs/v1_B_base_openrouter_20260729T155242203832.json` |
| v1 | `system_prompt.md` | Gỡ bỏ lệnh cấm hỏi sẽ giúp model dùng `ask_user_for_info` khi thiếu thông tin | case_accuracy | 0.70 | 0.95 | `starter_v0/runs/v1_B_base_openrouter_20260729T155242203832.json` |
| v2 | `artifacts/tools.yaml` | Rename/add required args để giảm missing_tool_call | case_accuracy | 0.95 | 0.85 | `starter_v0/runs/v2_B_base_openrouter_20260729T155922334265.json` |
| v3 | `artifacts/tools.yaml` | Tăng cường chính xác arg và ví dụ để giảm wrong_arg_value | case_accuracy | 0.85 | 0.80 | `starter_v0/runs/v3_B_base_openrouter_20260729T160123709484.json` |
| v4 | `artifacts/system_prompt.md + artifacts/tools.yaml` | Kết hợp prompt + tool fixes để đạt routing/arg ổn định | case_accuracy | 0.80 | 1.00 | `starter_v0/runs/v4_B_base_openrouter_20260729T160311436025.json` |

## B2. Failure analysis

Dữ liệu từ `results[*].result.failures` trong các run JSON. Dưới đây là các case điển hình đã được ghi nhận:

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix |
|---|---|---|---|---|
| `R03_web_news_routing` (v0) | `wrong_tool` / `wrong_arg_value` | `lookup(query="AI news", topic="news", timeframe="day", ...)` | Model thêm từ dư thừa `news` vào query; expected `query="AI"` khi `topic=news`. | Dùng prompt/tool declaration rõ ràng: query chỉ giữ từ khóa chính, không thêm `news` khi topic là news. |
| `R10_missing_handle` (v0) | `missing_info` | `timeline(screenname="sama")` | Agent gọi `timeline` mà không hỏi người dùng khi thiếu handle; expected `ask_user_for_info`. | Yêu cầu `ask_user_for_info` khi handle không rõ, rồi mới gọi tool dựa trên phản hồi. |
| `R12_confirm_before_send` (v0) | `wrong_boundary` | `send(text="Bản tin này")` | Agent gửi tin nhạy cảm trước khi xác nhận; expected phải hỏi `yes_no`. | Thêm rule bắt buộc confirm yes/no với `send_telegram_message` / hành động gửi. |
| `M06_switch_tool` (v1/v2/v3) | `wrong_tool` | `search_web_information(...)` + `search_twitter_by_keyword(...)` | Agent giữ cả hai tool khi user chuyển từ Twitter sang web; expected chỉ dùng `search_web_information`. | Bổ sung prompt rule: khi user chuyển sang web, chỉ gọi web search, không gọi Twitter nữa. |

## B3. Team eval cases

File `starter_v0/data/eval_group.json` hiện đã có 10 case đúng yêu cầu.

| Case ID | What It Tests | Expected Tool/Behavior | Result |
|---|---|---|---|
| G01_exchange_usd_vnd | Single-turn: tool mới `get_exchange_rate` | `get_exchange_rate(base=USD,target=VND)` | pending |
| G02_missing_twitter_handle | Single-turn: thiếu handle Twitter | `ask_user_for_info(response_type=text)` | pending |
| G03_send_telegram_boundary | Single-turn: gửi Telegram nhạy cảm | `ask_user_for_info(response_type=yes_no)` | pending |
| G04_no_tool_chitchat | Single-turn: không cần tool | `no_tool=true` | pending |
| G05_search_web_clean_query | Single-turn: clean query với topic=news | `search_web_information(query="xe điện Tesla", topic="news", timeframe="week")` | pending |
| G06_multiturn_exchange_convert | Multi-turn: giữ ngữ cảnh chuyển đổi tiền | `get_exchange_rate(base=EUR,target=USD)` | pending |
| G07_multiturn_clarify_then_fetch | Multi-turn: hỏi URL rồi fetch | `read_webpage_content(url=...)` | pending |
| G08_multiturn_switch_from_twitter_to_web | Multi-turn: chuyển hướng từ Twitter sang web | `search_web_information(query="Claude 3.5 Sonnet", topic="news", timeframe="day")` | pending |
| G09_multiturn_confirm_telegram_send | Multi-turn: xác nhận gửi Telegram | `send_telegram_message(text="Hoàn thành báo cáo AI", confirmed=true)` | pending |
| G10_multiturn_out_of_scope | Multi-turn: yêu cầu thực thi ngoài scope | `no_tool=true` | pending |

## B4. Live chat evidence

Use `transcripts/*.transcript.json`.

| Scenario/Turn | Version | Tool Calls + Args | Transcript/Run | Outcome |
|---|---|---|---|---|
| Confirm Twitter handle before lookup | v0 | `ask_user_for_info(question="Could you please confirm the Twitter handle for Sam Salman? I need the exact handle to retrieve the latest post.")` | `transcripts/v0_openrouter_20260729T162910665947.transcript.json` | Correctly asked for missing handle before calling Twitter lookup. |
| Fetch latest tweet after clarification | v0 | `get_user_recent_tweets(screenname="DrSamSalman", limit=1)` | `transcripts/v0_openrouter_20260729T162910665947.transcript.json` | Retrieved latest tweet and returned a concise summary with link and engagement. |
| Search Twitter for Vietnam news | v0 | `search_twitter_by_keyword(query="Viet Nam", search_type="Top", limit=5)` | `transcripts/v0_openrouter_20260729T162910665947.transcript.json` | Performed topic search and returned 5 tweets on Vietnam with summaries and engagement stats. |

## B5. Tool capability evidence

Phân loại rõ tool mới bắt buộc, optional built-in và tool đủ điều kiện bonus. Chỉ ghi Telegram/PDF nếu nhóm thực sự dùng; base report không cần chúng.

UI is core deliverable, not bonus. Do not list it here.

| Category | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Must-have: core research tools | `starter_v0/artifacts/tools.yaml`, `starter_v0/runs/v4_B_base_openrouter_20260729T160311436025.json` | Các tool `ask_user_for_info`, `get_user_recent_tweets`, `search_twitter_by_keyword`, `search_web_information`, `read_webpage_content`, `format_data_to_markdown` được khai báo rõ ràng và là xương sống cho research workflow. | Cần đảm bảo prompt/systems prompt chỉ gọi đúng tool phù hợp với intent và hỏi lại khi thiếu handle/URL. |
| Optional built-in | `starter_v0/artifacts/tools.yaml` | `search_internal_policy`, `search_arxiv_papers`, `read_arxiv_paper_content`, `get_exchange_rate` mở rộng agent sang policy, paper search và tỷ giá mà không bắt buộc cho core eval. | Không gọi nếu user không yêu cầu; tránh tạo tool noise hoặc làm lệch scope. |
| Bonus: optional outbound / advanced | `starter_v0/artifacts/tools.yaml` | `send_telegram_message` hỗ trợ hành động gửi tin nhắn sau xác nhận rõ ràng. | Bắt buộc phải dùng `ask_user_for_info(response_type=yes_no)` để xin phép trước khi gửi; tránh gửi tự động. |

## B6. Reflection

- `system_prompt.md` nên xử lý rõ ràng giới hạn tool routing, khi nào gọi `ask_user_for_info`, và cách mô tả truy vấn để tránh thêm từ dư thừa.
- `tools.yaml` nên định nghĩa tên tool rõ ràng, schema bắt buộc, và ví dụ arg cụ thể để giảm mismatch `missing_tool_call` / `wrong_arg_value`.
- Lỗi cần review thủ công là các cases có mismatch `wrong_tool`, `wrong_arg_value`, hoặc `unexpected_tool_call`, vì routing PASS không đảm bảo tool execution đúng.
- Cải tiến tiếp theo: hoàn thiện `data/eval_group.json`, bổ sung transcript live chat, và triển khai UI public để có public URL trong phần A.
- What would you improve next?
