# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Khóa/Lớp | K3 |
| Tên nhóm | ParkNoTech |
| Repository | git@github.com-acc2:dlhdwan/K3_Day10_parknotech.git |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | **Đinh Lê Hoàng Danh** | MSSV-01 | Source Ingestion Owner | `src/ingestion/crossref.py` |
| 2 | **Lưu Nhân Triệu Dương** | MSSV-02 | Data Model & Eval Set Owner | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| 3 | **Đỗ Ngọc Anh** | MSSV-03 | Data Observability Owner | `src/observability/quality.py`, `src/observability/reporting.py` |
| 4 | **Nguyễn Văn Hiếu** | 2A202601831 | Corruption & Integration Owner | `src/ingestion/corruption.py`, `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm ParkNoTech đã hoàn thành trọn vẹn toàn bộ 2 pha của dự án Data Observability & RAG Pipeline. Ở Pha 1 (Baseline), hệ thống đã ingest 24 bài báo khoa học từ Crossref REST API, thực hiện làm sạch dữ liệu, xây dựng Chroma Vector Index với mô hình embedding BAAI/bge-m3 (hoặc sentence-transformers), tạo bộ kiểm thử cố định 41 câu hỏi (`test_set.json`), đạt chỉ số Retrieval Hit Rate **97.56%**, Judge Accuracy **34.15%** và Mean Judge Score **2.39/5.0**, mọi tiêu chí Data Quality và Freshness đều đạt trạng thái PASS.

Ở Pha 2 (Corruption & Repair), nhóm đã giả lập 7 dạng suy biến dữ liệu thực tế (rỗng summary, cắt ngắn tiêu đề, inject từ nhiễu, làm cũ ngày xuất bản, nhân bản dữ liệu). Kết quả ghi nhận chỉ số Retrieval Hit Rate sụt giảm nghiêm trọng xuống còn **68.29%** (giảm 29.27%), điểm Judge Accuracy sụt giảm còn **17.07%**, Mean Judge Score giảm xuống **1.66/5.0**, đồng thời Data Quality Checks lập tức báo lỗi FAIL. Khi thực hiện quy trình khôi phục (Repair) bằng cách tái dựng ETL từ Raw Snapshot JSON, toàn bộ các chỉ số đã phục hồi hoàn toàn về mức Baseline (Hit Rate **97.56%**, Judge Accuracy **31.71%**, Mean Judge Score **2.29/5.0**, Quality PASS).

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (data/raw/crossref_response.json)
    -> cleaning và data modeling (src/ingestion/cleaning.py)
    -> embedding + ChromaDB index (papers-baseline)
    -> evaluation baseline (data/results/baseline_metrics.json)
    -> quality/freshness reports (data/quality/baseline.json)
    -> corruption (src/ingestion/corruption.py)
    -> re-index và re-evaluate (papers-corrupted & corrupted_metrics.json)
    -> repair từ dữ liệu nguồn raw snapshot (papers-repaired)
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion | Crossref REST API | Fetch, retry, parse raw JSON | `data/raw/crossref_records.json` | Đinh Lê Hoàng Danh |
| Cleaning | Raw records list | Normalization, age_days, text_for_embedding | `data/clean/papers_clean.csv` | Lưu Nhân Triệu Dương |
| Embedding/index | Cleaned DataFrame | Vector store embedding & indexing | ChromaDB collection `papers-baseline` | Code hệ thống (`index.py`) |
| Evaluation | Cleaned DataFrame | Generate test set & evaluate LLM agent | `data/eval/test_set.json`, `baseline_metrics.json` | Lưu Nhân Triệu Dương |
| Observability | Cleaned DataFrame | Quality checks & freshness report | `data/quality/baseline.json`, `phase1_report.md` | Đỗ Ngọc Anh |
| Corruption/repair | Cleaned DataFrame | Corrupt 7 kịch bản & Repair từ Raw | `corruption_log.json`, `papers_clean_corrupted.csv` | Nguyễn Văn Hiếu |
| Orchestration | End-to-end config | Chạy Phase 1 & Phase 2 pipelines | `run_phase1.py`, `run_corruption_flow.py` | Nguyễn Văn Hiếu |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER` | `gemini` (hoặc `heuristic` fallback) |
| `LLM_MODEL` | `gemini-2.5-flash` / `gemini-3.5-flash-lite` |
| Embedding model | `BAAI/bge-m3` (hoặc `sentence-transformers/all-MiniLM-L6-v2`) |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 3 |
| Freshness threshold | 180 days |
| Random seed, nếu có | 42 |

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công | 2026-08-06 10:49:55 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 10:54:53 | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --------------------------- | ------------------------------------- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query="machine learning"`, `filter="has-abstract:true"` |
| Thời điểm lấy dữ liệu | 2026-08-06T10:48:00Z |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Retry 3 lần với exponential backoff khi gặp lỗi 429/503 |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | String | Có | Mã định danh duy nhất (DOI) | Bỏ qua bản ghi nếu rỗng |
| `title` | String | Có | Tiêu đề bài báo | Chuẩn hóa khoảng trắng |
| `summary` | String | Có | Tóm tắt bài báo | Bỏ qua nếu trống |
| `authors` | List[String] | Có | Danh sách tác giả | Gán "Unknown Author" nếu thiếu |
| `published` | String | Có | Ngày xuất bản YYYY-MM-DD | Đặt mặc định 2024-01-01 nếu lỗi date |
| `text_for_embedding` | String | Có | Văn bản nhãn tổng hợp để vector indexing | Rebuild từ title + categories + summary |

### Quy tắc cleaning

| Quy tắc | Quality dimension liên quan | Số record bị tác động | Cách xác minh |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại bản ghi trống title/summary | Completeness / Validity | 0 (tất cả hợp lệ) | `data/quality/baseline.json` |
| Loại bỏ paper_id trùng lặp | Uniqueness | 0 (không trùng) | `paper_id_unique: true` |

**Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:**

- `text_for_embedding`: Định dạng chuỗi tổng hợp `Title: {title}\nCategories: {categories_joined}\nSummary: {summary}` giúp mô hình embedding học trọn vẹn ngữ cảnh.
- Document ID: Chuyển DOI về dạng in thường và loại bỏ ký tự thừa.
- `age_days`: Tính bằng `(run_date - published_date).days`.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi | 41 |
| Các `question_type` | `summary`, `authors`, `date`, `categories` |
| Ground-truth document ID | Gán trực tiếp ID của bài báo sinh ra câu hỏi |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` / `BAAI/bge-m3` |
| Vector store/collection | ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`) |
| Retrieval `top_k` | 3 |
| LLM provider/model | `gemini` (`gemini-2.5-flash`) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` |

**Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:**
Việc cố định duy nhất bộ `test_set.json` cho cả 3 trạng thái đảm bảo tính nhất quán (frozen evaluation benchmark), giúp các thước đo như Hit Rate, F1, Judge Score đo lường chính xác mức sụt giảm do lỗi dữ liệu gây ra chứ không bị nhiễu do thay đổi câu hỏi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records | `data/raw/crossref_records.json` | Có | Đã lưu 24 bản ghi raw |
| Cleaned dataset | `data/clean/papers_clean.csv` | Có | 24 dòng dữ liệu sạch |
| Embedding manifest/index | `data/embeddings/embeddings_manifest.json` | Có | Đã index vào ChromaDB |
| Evaluation set | `data/eval/test_set.json` | Có | 41 mẫu kiểm thử |
| Baseline metrics | `data/results/baseline_metrics.json` | Có | Metrics baseline |
| Quality/freshness | `data/quality/baseline.json` | Có | Quality PASS |
| Baseline report | `data/reports/phase1_report.md` | Có | Markdown report |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` | **0.9756** | Truy xuất chính xác văn bản cho 97.56% câu hỏi |
| `mean_token_f1` | **0.1982** | Độ trùng khớp từ ngữ trung bình của câu trả lời |
| `judge_accuracy` | **0.3415** | Tỷ lệ câu trả lời đạt điểm tối đa từ LLM Judge |
| `mean_judge_score` | **2.3902** | Điểm số chất lượng trung bình từ LLM Judge (thang 5) |

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `paper_id_missing` | Completeness | 0 | PASS (0) | `data/quality/baseline.json` |
| `paper_id_unique` | Uniqueness | `true` | PASS (`true`) | `data/quality/baseline.json` |
| `title_missing` | Completeness | 0 | PASS (0) | `data/quality/baseline.json` |
| `short_summary` | Validity | 0 | PASS (0) | `data/quality/baseline.json` |
| `stale_rows` | Freshness | 0 | PASS (0) | `data/quality/baseline.json` |

### Freshness

| Thuộc tính | Giá trị |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cleaned DataFrame `published` date |
| Timestamp mới nhất | 2026-08-06 |
| Ngưỡng freshness | 180 days |
| Trạng thái baseline | `Fresh (0 stale)` |
| Lý do | Tất cả bài báo đều xuất bản trong vòng 180 ngày gần nhất |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| Drop latest records | Xóa 15% bài báo mới nhất | 3 | Stale rows tăng | Giảm khả năng trả lời bài mới | Khôi phục từ Raw snapshot |
| Blank summary | Xóa trống trường summary | 4 | `short_summary` FAIL | Hit rate giảm mạnh | Re-extract từ Raw abstract |
| Inject noise | Chèn từ rác `CORRUPTED_NOISE` | 4 | Text quality giảm | Nhiễu kết quả retriever | Clean lại từ Raw payload |
| Truncate title | Cắt tiêu đề ngắn <10 ký tự | 4 | Text truncated | Mất ngữ cảnh tiêu đề | Re-build từ Raw title |
| Stale date | Đặt ngày xuất bản về 2020 | 6 | `stale_rows` FAIL | Trạng thái Freshness bị FAIL | Reset date từ Raw metadata |
| Add duplicates | Nhân bản dòng ngẫu nhiên | 4 | `paper_id_unique` FAIL | Trùng lặp kết quả tìm kiếm | Deduplicate theo `paper_id` |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi nhận đầy đủ 7 thao tác biến đổi và số lượng bản ghi bị tác động.

**Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy:**
Hệ thống thực hiện Repair bằng cách đọc lại snapshot Raw JSON gốc (`crossref_records.json`) lưu tại thời điểm Ingest ban đầu và chạy lại toàn bộ quy trình ETL cleaning. Cách làm này đảm bảo tính đáng tin cậy và khôi phục 100% dữ liệu gốc mà không phụ thuộc vào kết quả biến động của API bên ngoài.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate` | **0.9756** | **0.6829** | **0.9756** | -0.2927 (-29.27%) | 100% | Lỗi làm rớt mạnh hit rate, phục hồi hoàn toàn |
| `mean_token_f1` | **0.1982** | **0.0981** | **0.1982** | -0.1001 (-10.01%) | 100% | Token F1 giảm 1 nửa khi bị nhiễu |
| `judge_accuracy` | **0.3415** | **0.1707** | **0.3171** | -0.1708 (-17.08%) | 92.8% | Điểm đánh giá giảm mạnh khi bị lỗi |
| `mean_judge_score` | **2.3902** | **1.6585** | **2.2927** | -0.7317 | 96% | Phục hồi về mức 2.29/5.0 |
| Quality checks pass/fail | Passed | Failed | Passed | Chuyển sang Failed | Passed | Cảnh báo dữ liệu hoạt động chính xác |
| Freshness status | Fresh | Stale (6) | Fresh (0) | 6 dòng bị quá hạn | Fresh | Phục hồi 0 dòng stale |

**Hai kết luận có quan hệ nhân quả:**

1. **Lỗi rỗng Summary & Cắt Tiêu đề** ➔ Biến dạng Vector Embedding ➔ Hit Rate rớt từ 97.56% xuống 68.29% và Quality Check báo FAIL.
2. **Hành động Repair từ Raw Snapshot** ➔ Làm sạch lại toàn bộ dữ liệu ➔ Hit Rate phục hồi 100% về 97.56% và Quality Check trở lại PASS.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy `run_phase1.py` bị lỗi `TypeError: Object of type int64 is not JSON serializable`.
- **Nguyên nhân:** Lớp `run_data_quality_checks` trả về kiểu `numpy.int64` và `numpy.bool_` từ Pandas DataFrame khiến lệnh `json.dump()` của Python bị lỗi.
- **Cách xử lý:** Thực hiện ép kiểu rõ ràng sang `int()` và `bool()` native của Python trong `src/observability/quality.py`.
- **Cách xác minh:** Chạy thành công `uv run python script/run_phase1.py` và xuất file `data/quality/baseline.json`.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Số lượng bài báo nhỏ (24 bài) | Độ đa dạng ngữ cảnh chưa cao | Mở rộng ingest 500-1000 bài báo từ Crossref |
| Token F1 thấp do exact overlap | Chưa phản ánh hết ngữ nghĩa sinh ra | Tích hợp RAGAS Semantic Similarity |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
