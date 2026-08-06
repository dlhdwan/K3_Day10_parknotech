# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | **Nguyễn Văn Hiếu** |
| MSSV | 2A202601831 |
| Khóa/Lớp | K3 |
| Tên nhóm | ParkNoTech |
| Vai trò chính | **Corruption & Integration Owner (Thành viên 4)** |
| Repository | git@github.com-acc2:dlhdwan/K3_Day10_parknotech.git |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Data Corruption Simulator | `src/ingestion/corruption.py`<br>`corrupt_clean_dataframe()` | `clean_df` (DataFrame) | `corrupted_df`, `data/results/corruption_log.json` | Hoàn thành |
| Baseline Pipeline Integration | `src/pipelines/phase1.py`<br>`main()` | End-to-end Config | Chroma Index (`papers-baseline`), `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| Corruption Flow Integration | `src/pipelines/corruption_flow.py`<br>`main()` | Clean Dataset & Test Set | Corrupted Index, Repaired Index, `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Fix JSON serialization bug | Module Data Quality (`quality.py`) | Ép kiểu `int64`/`bool_` sang `int`/`bool` để `json.dump` không bị crash |
| Cấu hình SSH Git Account 2 | Toàn nhóm | Đổi git remote sang `github.com-acc2` và chạy fetch/push thành công |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai 7 kịch bản suy biến dữ liệu | `src/ingestion/corruption.py` | `corruption_log.json`, `papers_clean_corrupted.csv` | Kiểm tra audit log và file CSV corrupted |
| Kết nối Baseline Pipeline Phase 1 | `src/pipelines/phase1.py` | `baseline_metrics.json`, `phase1_report.md` | Lệnh `uv run python script/run_phase1.py` |
| Kết nối Corruption & Repair Flow | `src/pipelines/corruption_flow.py` | `corrupted_metrics.json`, `corruption_report.md` | Lệnh `uv run python script/run_corruption_flow.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc của tôi giải quyết vấn đề mô phỏng các dạng hỏng hóc dữ liệu thực tế (Data Corruption) và tích hợp các module đơn lẻ của từng thành viên thành một luồng thực thi end-to-end hoàn chỉnh cho cả Pha 1 (Baseline) và Pha 2 (Corruption & Repair).

### Cách triển khai

- **`corruption.py`**: Triển khai hàm `corrupt_clean_dataframe()` thực hiện 7 biến đổi: xóa 15% bài báo mới nhất, xóa rỗng summary ở 20% bản ghi, chèn từ nhiễu `CORRUPTED_NOISE`, cắt tiêu đề <10 ký tự, chuyển ngày xuất bản về 2020 (`age_days` > 180), nhân bản 20% số dòng và rebuild cột `text_for_embedding`.
- **`phase1.py`**: Tích hợp Ingest ➔ Clean ➔ Vector Indexing ➔ Testset Eval ➔ Quality Checks ➔ Export Report.
- **`corruption_flow.py`**: Quản lý luồng 3 trạng thái **Baseline vs Corrupted vs Repaired**, sử dụng cùng một bộ `test_set.json` cố định và thực hiện Repair từ Raw Snapshot JSON.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | `clean_df` (DataFrame), `Settings` config |
| Output | `corrupted_df`, `corruption_log.json`, Metrics JSON & Markdown Reports |
| Module phụ thuộc | `crossref.py`, `cleaning.py`, `testset.py`, `quality.py`, `reporting.py` |
| Module sử dụng output | `script/run_phase1.py`, `script/run_corruption_flow.py` |
| Điều kiện lỗi cần xử lý | Kiểm tra file baseline metrics tồn tại trước khi chạy Phase 2 |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả 2 script chạy thành công với Exit code 0, xuất đầy đủ metrics và báo cáo.
- **Kết quả thực tế:** Hit rate rớt từ 97.56% xuống 68.29% ở trạng thái corrupt và phục hồi 100% về 97.56% ở trạng thái repaired.
- **Artifact/log:** `data/results/corruption_log.json`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn phương pháp phục hồi dữ liệu (Repair) trong Phase 2.
- **Các phương án đã cân nhắc:**
  1. Fetch lại dữ liệu trực tiếp từ Live Crossref REST API.
  2. Tái dựng dữ liệu (Re-clean) từ Raw Snapshot JSON (`crossref_records.json`) lưu tại thời điểm Ingest ban đầu.
- **Phương án đã chọn:** Phương án 2 (Tái dựng từ Raw Snapshot JSON).
- **Lý do:** Đảm bảo tính nhất quán (reproducibility), tránh rủi ro biến động dữ liệu phía API nguồn hoặc lỗi mạng (Rate limit 429), giúp kết quả đánh giá khôi phục hoàn toàn chuẩn xác.
- **Bằng chứng quyết định phù hợp:** `repaired_metrics.json` cho kết quả Hit Rate phục hồi 100% về 97.56%.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: Object of type int64 is not JSON serializable` khi gọi `run_data_quality_checks`.
- **Lệnh hoặc bước tái hiện:** `uv run python script/run_phase1.py`.
- **Nguyên nhân gốc:** Pandas DataFrame trả về các kiểu dữ liệu `numpy.int64` và `numpy.bool_` không tương thích trực tiếp với hàm `json.dump()` tiêu chuẩn của Python.
- **Cách xử lý:** Ép kiểu thủ công các giá trị kết quả sang `int()` và `bool()` native của Python trong `src/observability/quality.py`.
- **Cách xác minh sau khi sửa:** Chạy lại `run_phase1.py` thành công 100% không còn báo lỗi.
- **Điều học được:** Cần lưu ý sự khác biệt giữa kiểu dữ liệu của Pandas/Numpy và native Python khi xuất định dạng JSON.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref API ➔ lưu Raw JSON Snapshot ➔ qua module Cleaning chuẩn hóa text & age_days ➔ tạo `text_for_embedding` ➔ tạo embedding vector ➔ index vào ChromaDB.
2. Evaluation set chứa danh sách câu hỏi kèm `ground_truth_doc_ids` đối chiếu với Top-K doc IDs truy xuất từ Retriever để đo Retrieval Hit Rate và F1/Judge scores.
3. Quality checks kiểm tra tính hợp lệ của schema (null, duplicate, short text), còn Freshness monitoring kiểm tra mốc thời gian bài báo có bị cũ quá ngưỡng `freshness_threshold_days` hay không.
4. Bắt buộc dùng chung một test set cố định cho cả 3 trạng thái để đo lường chính xác tác động của lỗi dữ liệu mà không bị biến thiên do câu hỏi khác nhau.
5. Repair được xem là thành công khi Quality Check chuyển lại sang PASS và các chỉ số RAG (Hit Rate, F1, Judge Score) phục hồi về lại mức Baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | **0.9756** | **0.6829** | **0.9756** | Lỗi làm rớt mạnh hit rate, phục hồi hoàn toàn |
| `mean_token_f1` | **0.1982** | **0.0981** | **0.1982** | Token F1 giảm 1 nửa khi bị nhiễu |
| `judge_accuracy` | **0.3415** | **0.1707** | **0.3171** | Điểm đánh giá giảm khi bị lỗi |
| `mean_judge_score` | **2.3902** | **1.6585** | **2.2927** | Phục hồi về mức 2.29/5.0 |
| Quality checks | `Passed` | `Failed` | `Passed` | Cảnh báo dữ liệu hoạt động chính xác |
| Freshness status | `Fresh` | `Stale (6)` | `Fresh (0)` | Phục hồi 0 dòng stale |

### Kết luận từ số liệu

1. **Data Corruption (Blank Summary & Noise)** ➔ Quality Signal báo FAIL (`short_summary: 4`, `stale_rows: 6`) ➔ Retrieval Hit Rate giảm từ 97.56% xuống 68.29%.
2. **Repair Action (Re-ETL từ Raw Snapshot)** ➔ Quality Signal phục hồi PASS (`is_fresh: true`) ➔ Retrieval Hit Rate phục hồi 100% về 97.56%.

Kịch bản corruption ảnh hưởng rõ nhất là **Blank Summary & Truncate Title** vì nó trực tiếp phá hủy ngữ cảnh vector embedding khiến Retriever không thể tìm thấy văn bản phù hợp.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Dữ liệu chất lượng kém (rác, thiếu, rỗng) ảnh hưởng cực kỳ nghiêm trọng đến hiệu năng RAG hệ thống.
2. Bộ quan sát (Data Observability) là thành phần bắt buộc để phát hiện sớm lỗi dữ liệu trước khi đưa vào Vector Store.
3. Việc duy trì Raw Data Snapshot là giải pháp quan trọng giúp khôi phục dữ liệu an toàn và đáng tin cậy.

### Nếu có thêm thời gian

Tôi sẽ xây dựng cơ chế tự động khôi phục (Auto-healing Data Pipeline) khi Quality Check phát hiện lỗi FAIL mà không cần can thiệp thủ công.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Hiếu  
**Ngày xác nhận:** 2026-08-06
