# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | **Đinh Lê Hoàng Danh** |
| MSSV | 2A202601890 |
| Khóa/Lớp | K3 |
| Tên nhóm | ParkNoTech |
| Vai trò chính | **Source Ingestion Owner (Thành viên 1)** |
| Repository | git@github.com-acc2:dlhdwan/K3_Day10_parknotech.git |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | ---------------- | ----------------- | ---------- |
| Raw Data Ingestion | `src/ingestion/crossref.py`<br>`fetch_source_records()` | `Settings` (`source_query`, `source_filter`, `max_results`) | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Hoàn thành |
| Payload Parsing | `src/ingestion/crossref.py`<br>`parse_crossref_payload()` | Crossref API JSON Payload | `list[PaperRecord]` (Data Model chuẩn hóa) | Hoàn thành |
| Snapshot Loading | `src/ingestion/crossref.py`<br>`load_raw_records()` | Path `crossref_records.json` | `list[PaperRecord]` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Thiết kế Data Contract | `cleaning.py` (Lưu Nhân Triệu Dương) | Thống nhất cấu trúc `PaperRecord` và quy tắc đặt `paper_id` ổn định |
| Hỗ trợ luồng Repair dữ liệu | `corruption_flow.py` (Nguyễn Văn Hiếu) | Đảm bảo `load_raw_records()` cho phép reload snapshot sạch để khôi phục dữ liệu |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai thu thập dữ liệu nguồn | `src/ingestion/crossref.py`<br>`fetch_source_records()` | `data/raw/crossref_response.json` (245 KB) | Kiểm tra sự tồn tại và cấu trúc file JSON trong `data/raw/` |
| Triển khai bóc tách dữ liệu chuẩn | `src/ingestion/crossref.py`<br>`parse_crossref_payload()` | `data/raw/crossref_records.json` (61 KB) | Chạy thử nghiệm parsing 24 bản ghi thành công |
| Tái sử dụng dữ liệu offline | `src/ingestion/crossref.py`<br>`load_raw_records()` | `list[PaperRecord]` | Chạy lệnh `uv run python` load snapshot mà không cần mạng |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Là **Source Ingestion Owner**, nhiệm vụ của tôi là xây dựng cầu nối thu thập dữ liệu học thuật tự động từ external API nguồn (**Crossref REST API**), trích xuất và loại bỏ tạp chất (thẻ XML/HTML, khoảng trắng thừa), sau đó chuẩn hóa thành cấu trúc dữ liệu `PaperRecord` ổn định để cung cấp đầu vào đáng tin cậy cho toàn bộ Data Pipeline.

### Cách triển khai

1. **`parse_crossref_payload(payload: dict) -> list[PaperRecord]`**:
   - Duyệt qua danh sách bài báo `payload["message"]["items"]`.
   - Trích xuất các trường thông tin: `DOI`, `title`, `abstract`, `author`, `subject`, các mốc thời gian `published` (online/print/issued) và `updated` (indexed/deposited).
   - Sử dụng Regex `_clean_html_tags()` (`re.sub(r"<[^>]+>", " ", text)`) để làm sạch toàn bộ thẻ JATS XML (`<jats:p>`) trong `abstract` và `title`.
   - Chuẩn hóa mốc thời gian về định dạng chuẩn ISO `YYYY-MM-DD` thông qua helper `_parse_crossref_date()`.
   - Đặt `paper_id` dạng `crossref:{DOI}` giúp duy trì tính định danh duy nhất và ổn định xuyến suốt pipeline.
   - Bỏ qua các bản ghi bị lỗi hoặc không có tiêu đề.

2. **`fetch_source_records(settings: Settings) -> list[PaperRecord]`**:
   - Xây dựng HTTP request gửi tới `https://api.crossref.org/works` với các tham số từ `Settings`: `source_query`, `source_filter`, và `max_results`.
   - Thiết lập `User-Agent` chuẩn theo chính sách Polite Pool của Crossref.
   - Triển khai cơ chế **Retry với Exponential Backoff** (tối đa 3 lần) xử lý các mã lỗi ngắt quãng như HTTP `429` (Rate limit), `503`, `504`.
   - Lưu trữ nguyên văn phản hồi từ API vào `data/raw/crossref_response.json`.
   - Lưu trữ danh sách bài báo đã parse thành công ra `data/raw/crossref_records.json`.
   - Tích hợp cơ chế caching: Nếu file raw response đã tồn tại và `settings.refresh_source` là `False`, hệ thống sẽ tự động đọc từ cache thay vì gọi lại API.

3. **`load_raw_records(path: Path) -> list[PaperRecord]`**:
   - Đọc file snapshot JSON từ `data/raw/crossref_records.json` và map lại thành đối tượng `PaperRecord`, phục vụ cho công đoạn Cleaning và giai đoạn Repair dữ liệu offline.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `Settings` (`source_query`, `source_filter`, `max_results`) |
| Output | `crossref_response.json`, `crossref_records.json`, `list[PaperRecord]` |
| Module phụ thuộc | `core/config.py`, `core/utils.py` |
| Module sử dụng output | `src/ingestion/cleaning.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |

### Cách xác minh

Chạy thử nghiệm trực tiếp qua Python CLI:
```bash
uv run python -c "from core.config import load_settings; from ingestion.crossref import fetch_source_records; s = load_settings(); records = fetch_source_records(s); print('Fetched records count:', len(records))"
```

**Kết quả thực tế:**
- Thu thập thành công **24 bài báo khoa học** chất lượng cao liên quan đến RAG và LLM.
- Đã xuất thành công 2 file lưu trữ tại:
  - `data/raw/crossref_response.json` (245 KB)
  - `data/raw/crossref_records.json` (61 KB)

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Crossref API là một live public API. Kết quả trả về có thể biến động theo thời gian hoặc gặp sự cố gián đoạn mạng (HTTP 429 Rate Limit).
- **Các phương án đã cân nhắc:**
  1. Chỉ gọi API trực tiếp mỗi khi pipeline chạy (Live Fetch).
  2. Lưu trữ 2 cấp độ dữ liệu tại `data/raw/`: **Raw Response JSON** (nguyên bản từ API) và **Raw Records Snapshot JSON** (đã parse sẵn).
- **Phương án đã chọn:** Phương án 2.
- **Lý do:**
  - Đảm bảo tính tái lập 100% (Reproducibility) cho kết quả đánh giá của cả nhóm.
  - Phân tách rõ ràng giữa công đoạn lấy dữ liệu (Ingestion) và công đoạn làm sạch dữ liệu (Cleaning).
  - Cung cấp nguồn khôi phục đáng tin cậy cho bước Repair ở Phase 2 mà không phụ thuộc vào kết nối mạng.
- **Bằng chứng quyết định phù hợp:** Toàn bộ pipeline Phase 1 và Phase 2 có thể chạy offline hoàn toàn dựa trên snapshot mà vẫn đảm bảo số liệu đồng nhất.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Nội dung abstract thu thập được chứa các thẻ XML nham nhở như `<jats:p>`, `<jats:italic>`, `<jats:title>` gây nát dữ liệu văn bản.
- **Nguyên nhân gốc:** Crossref cung cấp dữ liệu tóm tắt bài báo theo chuẩn định dạng JATS XML trong các ấn phẩm xuất bản học thuật.
- **Cách xử lý:** Xây dựng hàm helper `_clean_html_tags()` ứng dụng Regex `re.sub(r"<[^>]+>", " ", text)` để bóc tách triệt để mọi thẻ XML/HTML, kết hợp hàm `normalize_whitespace()` dọn dẹp khoảng trắng thừa.
- **Cách xác minh sau khi sửa:** Kiểm tra trường `summary` trong file `data/raw/crossref_records.json`, toàn bộ các thẻ XML đã bị loại bỏ hoàn toàn, văn bản trở nên sạch sẽ và sẵn sàng cho công đoạn embedding.

---

## 7. Hiểu biết về luồng end-to-end

1. **Raw Ingestion**: Tải dữ liệu từ Crossref API, bóc tách và tạo snapshot `crossref_records.json`.
2. **Cleaning & Data Modeling**: Loại bỏ record rác, chuẩn hóa tác giả/chuyên mục, tính `age_days`, tạo cột `text_for_embedding` rồi xuất ra `papers_clean.csv`.
3. **Vector Indexing & Evaluation**: Dùng `sentence-transformers` mã hóa văn bản vào ChromaDB collection `papers-baseline`. Sinh bộ câu hỏi `test_set.json` (41 mẫu) để đánh giá RAG Agent.
4. **Data Observability**: Chạy kiểm tra Quality Checks (null, duplicate, short text) và Freshness (tuổi dữ liệu).
5. **Corruption & Repair Flow**: Giả lập 7 dạng lỗi trên cleaned data làm rớt Hit Rate từ **97.56%** xuống **68.29%**, sau đó thực hiện khôi phục (Repair) từ Raw Snapshot JSON ban đầu để đưa Hit Rate phục hồi 100% về **97.56%**.

---

## 8. Phân tích kết quả

### Metrics thu thập từ toàn luồng

| Chỉ số / Tín hiệu | Baseline (Pha 1) | Corrupted (Pha 2) | Repaired (Khôi phục) | Nhận xét cá nhân |
| :--- | :---: | :---: | :---: | :--- |
| **Retrieval Hit Rate** | **97.56%** | **68.29%** | **97.56%** | Dữ liệu thô sạch giúp khôi phục 100% hiệu năng truy xuất |
| **Mean Token F1** | **0.1982** | **0.0981** | **0.1982** | Độ chính xác từ ngữ được phục hồi hoàn toàn |
| **Judge Accuracy** | **34.15%** | **17.07%** | **31.71%** | Đánh giá LLM Judge khôi phục về mức an toàn |
| **Mean Judge Score** | **2.39 / 5.0** | **1.66 / 5.0** | **2.29 / 5.0** | Điểm số trung bình cải thiện rõ rệt |
| **Data Quality Status** | `PASSED` | `FAILED` | `PASSED` | Tín hiệu Observability cảnh báo chính xác |
| **Freshness Status** | `Fresh (0 stale)` | `Stale (6 stale)` | `Fresh (0 stale)` | Độ tươi dữ liệu được khôi phục |

### Kết luận từ số liệu

- Chất lượng dữ liệu ở bước Ingestion ban đầu quyết định trần hiệu năng (upper bound) của hệ thống RAG.
- Nếu dữ liệu thô thu thập bị thiếu trường thông tin (blank summary, missing title), Retriever sẽ chọn sai văn bản ngữ cảnh, khiến Hit Rate sụt giảm nghiêm trọng 29.27%.
- Việc duy trì lưu trữ Raw Data Snapshot là chìa khóa giúp khôi phục hệ thống (Repair) về trạng thái hoạt động tối ưu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Polite API Ingestion & Retry Mechanism**: Việc thiết lập `User-Agent` đúng quy chuẩn và xử lý retry tự động giúp hệ thống thu thập dữ liệu bền bỉ, không bị chặn IP.
2. **Text Normalization**: Loại bỏ thẻ XML/HTML ngay ở bước Ingestion giúp tránh việc "rác dữ liệu" đi sâu vào các tầng pipeline phía sau.
3. **Data Lineage & Reproducibility**: Lưu trữ dữ liệu thô nguyên bản (raw response) là điều bắt buộc để phục vụ audit và khôi phục sự cố.

### Nếu có thêm thời gian

Tôi sẽ mở rộng module Ingestion để hỗ trợ thêm các nguồn dữ liệu học thuật khác như **arXiv API** hay **Semantic Scholar API**, đồng thời xây dựng cơ chế tự động phát hiện thay đổi schema (Schema Drift) từ API nguồn.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đinh Lê Hoàng Danh  
**Ngày xác nhận:** 2026-08-06
