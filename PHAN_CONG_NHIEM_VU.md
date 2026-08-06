# BẢNG PHÂN CÔNG NHIỆM VỤ NHÓM
## Dự án: Day 10 - Data Observability & RAG Pipeline

---

## 👥 Danh Sách Thành Viên & Vai Trò

| STT | Họ và tên | Vai trò | Các file mã nguồn phụ trách |
| :---: | :--- | :--- | :--- |
| 1 | **Đinh Lê Hoàng Danh** | **Source Ingestion Owner** (Thành viên 1) | `src/ingestion/crossref.py` |
| 2 | **Lưu Nhân Triệu Dương** | **Data Model & Eval Set Owner** (Thành viên 2) | `src/ingestion/cleaning.py`<br>`src/evaluation/testset.py` |
| 3 | **Đỗ Ngọc Anh** | **Data Observability Owner** (Thành viên 3) | `src/observability/quality.py`<br>`src/observability/reporting.py` |
| 4 | **Nguyễn Văn Hiếu** | **Corruption & Integration Owner** (Thành viên 4) | `src/ingestion/corruption.py`<br>`src/pipelines/phase1.py`<br>`src/pipelines/corruption_flow.py` |

---

## 📝 Chi Tiết Công Việc Từng Thành Viên

### 1. Đinh Lê Hoàng Danh — Source Ingestion Owner
* **File phụ trách:** `src/ingestion/crossref.py`
* **Nhiệm vụ chính:**
  - [x] Triển khai hàm `fetch_source_records()`: Gọi Crossref REST API (`https://api.crossref.org/works`) lấy metadata paper dựa trên query & filter từ `Settings`.
  - [x] Triển khai hàm `parse_crossref_payload()`: Duyệt qua danh sách bài báo trong payload, bóc tách các trường DOI, Title, Abstract, Authors, Subject, Published Dates, URL và chuẩn hóa thành đối tượng `PaperRecord`.
  - [x] Xử lý lưu trữ raw data: Lưu raw response vào `data/raw/crossref_response.json` và raw records vào `data/raw/crossref_records.json`.
  - [x] Triển khai hàm `load_raw_records()`: Đọc snapshot JSON raw record để tái sử dụng mà không cần fetch lại API.

### 2. Lưu Nhân Triệu Dương — Data Model & Eval Set Owner
* **File phụ trách:** `src/ingestion/cleaning.py` & `src/evaluation/testset.py`
* **Nhiệm vụ chính:**
  - [x] **Cleaning Data (`cleaning.py`)**:
    - Triển khai hàm `build_clean_dataframe()`: Chuẩn hóa title, summary, authors, categories.
    - Tính toán mốc thời gian xuất bản (`published`) và số ngày `age_days`.
    - Tạo các cột phụ trợ: `authors_joined`, `categories_joined`, `summary_chars`, và đặc biệt là `text_for_embedding` phục vụ cho Vector Store.
    - Loại bỏ các bản ghi không hợp lệ hoặc trùng lặp, lưu cleaned dataset ra `data/clean/papers_clean.csv` và `data/clean/papers_clean.json`.
  - [x] **Evaluation Set (`testset.py`)**:
    - Triển khai hàm `build_test_set()`: Lựa chọn ngẫu nhiên/đại diện các bài báo từ cleaned dataset để tạo bộ câu hỏi kiểm thử (test set).
    - Tạo đa dạng loại câu hỏi (`summary`, `authors`, `date`, `categories`) kèm `ground_truth` và `ground_truth_doc_ids`.
    - Xuất dữ liệu test set ra `data/eval/test_set.json`.

### 3. Đỗ Ngọc Anh — Data Observability Owner
* **File phụ trách:** `src/observability/quality.py` & `src/observability/reporting.py`
* **Nhiệm vụ chính:**
  - [x] **Data Quality Checks (`quality.py`)**:
    - Triển khai `run_data_quality_checks()`: Kiểm tra tổng số dòng, kiểm tra tính duy nhất & không null của `paper_id`, kiểm tra `title` không rỗng, độ dài `summary`, tính hợp lệ của `age_days`.
    - Triển khai `build_freshness_report()`: Theo dõi bài báo mới nhất, cũ nhất, số lượng bài bị cũ (stale) vượt ngưỡng `freshness_threshold_days`.
  - [x] **Automated Markdown Reporting (`reporting.py`)**:
    - Triển khai `generate_phase1_report()`: Tổng hợp kết quả Phase 1 bao gồm thông tin nguồn dữ liệu, kết quả đánh giá RAG agent (Hit rate, Token F1, Judge score), báo cáo Data Quality và Freshness ra file `data/reports/phase1_report.md`.
    - Triển khai `generate_corruption_report()`: Viết báo cáo so sánh đa chiều giữa 3 giai đoạn: **Baseline vs Corrupted vs Repaired** ra file `data/reports/corruption_report.md`.

### 4. Nguyễn Văn Hiếu — Corruption & Integration Owner
* **File phụ trách:** `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`
* **Nhiệm vụ chính:**
  - [x] **Data Corruption Simulator (`corruption.py`)**:
    - Triển khai `corrupt_clean_dataframe()`: Giả lập dữ liệu lỗi thực tế (xóa một số paper mới nhất, để trống summary, inject nhiễu vào text, truncate title, thay đổi ngày xuất bản thành quá cũ, chèn thêm các dòng trùng lặp).
    - Ghi log chi tiết các thao tác biến đổi dữ liệu vào `data/results/corruption_log.json`.
  - [x] **Baseline Pipeline Integration (`phase1.py`)**:
    - Kết nối luồng chạy end-to-end cho Phase 1: Ingest -> Clean -> Build Chroma Embedding Index -> Build/Load Test Set -> Evaluate Agent -> Run Quality Checks -> Export Phase 1 Report.
  - [x] **Corruption Flow Integration (`corruption_flow.py`)**:
    - Kết nối luồng chạy end-to-end cho Phase 2: Corrupt Clean Data -> Re-build Index & Evaluate -> Check Quality -> Repair từ Raw -> Re-evaluate Repaired Data -> Export Comparison Report.

---

## 🎯 Ma Trận Đánh Giá Theo Rubric (Score Mapping)

| Mục Rubric | Điểm tối đa | Người chịu trách nhiệm chính |
| :--- | :---: | :--- |
| **Mục 1: Code structure & project organization** | 10 | Toàn đội (Nguyễn Văn Hiếu lead) |
| **Mục 2: Raw data ingestion** | 15 | Đinh Lê Hoàng Danh |
| **Mục 3: Cleaning & data modeling** | 15 | Lưu Nhân Triệu Dương |
| **Mục 4: Embedding & vector store** | 10 | Code có sẵn (`src/retrieval/index.py`) |
| **Mục 5: Agent & multi-provider LLM** | 10 | Code có sẵn (`src/retrieval/agent.py` & `llm.py`) |
| **Mục 6: Evaluation & scoring** | 10 | Lưu Nhân Triệu Dương (`testset.py`) |
| **Mục 7: Data observability** | 10 | Đỗ Ngọc Anh |
| **Mục 8: Corruption & comparison** | 10 | Nguyễn Văn Hiếu |

---

## 🚀 Hướng Dẫn Thực Thi Dự Án

### 1. Cài đặt môi trường:
```bash
cp .env.example .env
# Chỉnh sửa file .env với LLM Provider mong muốn (Gemini, OpenAI, Ollama, v.v.)
uv sync
# Hoặc: python -m pip install -e .
```

### 2. Chạy Baseline Pipeline (Phase 1):
```bash
uv run python script/run_phase1.py
```

### 3. Chạy Corruption & Comparison Flow (Phase 2):
```bash
uv run python script/run_corruption_flow.py
```
