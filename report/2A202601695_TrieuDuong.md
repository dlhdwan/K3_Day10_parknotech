# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| :--- | :--- |
| Họ và tên | Triệu Dương |
| MSSV | 2A202601695 |
| Khóa/Lớp | K3 |
| Tên nhóm | Bài làm Cá nhân |
| Vai trò chính | Full Pipeline Engineer & Data Observability Architect |
| Repository | [K3_Day10_parknotech](file:///c:/Users/ADMIN/Desktop/Code%20Space/K3_Day10_parknotech) |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| :--- | :--- | :--- | :--- | :--- |
| Raw Ingestion | `src/ingestion/crossref.py` | Crossref REST API | `data/raw/crossref_records.json` | Hoàn thành |
| Data Cleaning | `src/ingestion/cleaning.py` | Raw records | `data/clean/papers_clean.json` | Hoàn thành |
| Evaluation Set | `src/evaluation/testset.py` | Clean Dataframe | `data/eval/test_set.json` (18 queries) | Hoàn thành |
| Data Observability | `src/observability/quality.py` | Dataframe | `data/quality/baseline_quality.json`, `freshness_report.json` | Hoàn thành |
| Markdown Reporting | `src/observability/reporting.py` | Metrics & Quality dicts | `data/reports/phase1_report.md`, `corruption_report.md` | Hoàn thành |
| Pipeline Orchestration | `src/pipelines/phase1.py` & `corruption_flow.py` | Settings & Config | End-to-end Execution & Evaluation Comparison | Hoàn thành |

---

## 3. Giải thích phần kỹ thuật đã thực hiện

### 3.1. Vấn đề cần giải quyết
Xây dựng một quy trình dữ liệu cho hệ thống RAG có khả năng tự động ingest, clean, nhúng vector, đo lường chất lượng câu trả lời, giám sát các tiêu chuẩn Data Quality / Freshness và tự phục hồi khi dữ liệu bị lỗi.

### 3.2. Cách triển khai
1. **Ingestion**: Dùng Crossref API endpoint `/works` lọc bài báo từ tháng 02/2026 có abstract. Parse JATS XML/HTML tags bằng regex, trích xuất tác giả, ngày công bố và lưu snapshot raw response vào `data/raw/`.
2. **Cleaning**: Tính `age_days` so với ngày hiện tại, tạo cột tổng hợp `text_for_embedding` chứa toàn bộ tiêu đề, tác giả, chuyên mục và tóm tắt. Deduplicate theo DOI.
3. **Observability**: Viết các quy tắc kiểm tra tính hợp lệ (`null_paper_ids == 0`, `duplicate_paper_ids == 0`, `empty_summaries == 0`). Theo dõi độ tươi dữ liệu dựa trên ngưỡng `freshness_threshold_days = 180`.
4. **Corruption & Repair**: Giả lập 6 dạng hỏng hóc dữ liệu để đo đạc sự suy giảm chỉ số RAG Agent, sau đó khôi phục (repair) trực tiếp từ `data/raw/crossref_records.json`.

---

## 4. Phân tích kết quả thực nghiệm

### Bảng số liệu đo đạc trực tiếp từ Pipeline (Cấu hình Local Ollama llama3.2)

| Metric / Signal | Baseline (Clean) | Corrupted (Damaged) | Repaired (Restored) | Nhận xét của cá nhân |
| :--- | --: | --: | --: | :--- |
| **Retrieval Hit Rate** | **1.0000** | **0.6667** | **1.0000** | Tụt 33.3% do bị xóa mất bài báo mới và khôi phục 100% sau repair |
| **Mean Token F1** | **0.1110** | **0.0544** | **0.1110** | Giảm 51% do rỗng abstract & nhiễu text; phục hồi lại mức gốc |
| **Judge Accuracy** | **0.3333** | **0.5000** | **0.3333** | LLM Local Judge đánh giá mức độ chính xác của câu trả lời |
| **Mean Judge Score** | **2.61 / 5.0** | **3.11 / 5.0** | **2.61 / 5.0** | Điểm số đánh giá từ mô hình quantized local |
| **Data Quality Status** | **PASSED** | **FAILED** | **PASSED** | Báo FAILED chính xác khi có 2 dupes + 2 rỗng abstract |
| **Freshness Status** | **FRESH** | **FRESH** | **FRESH** | Phát hiện 2 bản ghi bị lùi ngày |

### Kết luận từ số liệu:
1. `Data Corruption` -> `Quality Check FAILED & Stale records` -> `Hit Rate giảm từ 100% xuống 66.67%, Token F1 giảm 51%`.
2. `Repair Action from Raw` -> `Quality Check PASSED` -> `Khôi phục 100% các chỉ số RAG Agent về mức Baseline`.


---

## 5. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng 100% phần việc và kết quả thực nghiệm của tôi.
- [x] Tôi nắm chắc và giải thích được luồng dữ liệu end-to-end của toàn bộ dự án.
- [x] Mọi kết luận đều có chứng minh số liệu thực tế tại `data/results/`.
- [x] Báo cáo không chứa bất kỳ secret hay API key nào.

**Họ và tên:** Triệu Dương  
**Ngày xác nhận:** 2026-08-06
