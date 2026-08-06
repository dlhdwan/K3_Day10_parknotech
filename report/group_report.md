# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| :--- | :--- |
| Khóa/Lớp | K3 |
| Tên nhóm | Bài làm Cá nhân (Thành viên đơn độc) |
| Repository | [K3_Day10_parknotech](file:///c:/Users/ADMIN/Desktop/Code%20Space/K3_Day10_parknotech) |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | :--- | :--- | :--- | :--- |
| 1 | Triệu Dương | 2A202601695 | End-to-End Pipeline & Data Observability Owner | Toàn bộ module `src/ingestion`, `src/evaluation`, `src/observability`, `src/pipelines` |

## 2. Tóm tắt kết quả

Bài làm đã hoàn thành trọn gói 100% các yêu cầu của bài lab trên branch `trieuduong`. Hệ thống dữ liệu được xây dựng end-to-end từ việc gọi Crossref REST API lấy 24 bài báo khoa học mới nhất, lưu vết raw artifacts (`crossref_response.json`, `crossref_records.json`), làm sạch dữ liệu thành `papers_clean.json` (24 rows), nhúng vector qua MiniLM và nạp vào ChromaDB.

Bộ test set gồm 18 câu hỏi chuẩn được dùng để đánh giá RAG Agent qua 3 trạng thái:
1. **Baseline**: Đạt `retrieval_hit_rate` = 1.0000, `mean_token_f1` = 0.2858, `judge_accuracy` = 1.0000 và `mean_judge_score` = 4.89/5.0. Data quality checks PASSED và độ tươi FRESH.
2. **Corrupted**: Sau khi giả lập rỗng abstract, inject nhiễu text, truncate tiêu đề, thêm bản ghi trùng lặp và lùi ngày công bố, chỉ số `retrieval_hit_rate` giảm xuống 0.8889, `judge_accuracy` tụt xuống 0.8333 và `mean_judge_score` giảm còn 4.11. Data Quality báo FAILED do phát hiện 2 bản ghi trùng lặp và 2 summary rỗng.
3. **Repaired**: Khi thực hiện khôi phục (repair) trực tiếp từ dữ liệu thô ban đầu (`data/raw/`), toàn bộ metrics khôi phục hoàn toàn về mức 1.0000 Hit Rate và 4.89 Judge Score.

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> raw response/raw records (data/raw/)
    -> cleaning & data modeling (data/clean/papers_clean.json)
    -> embedding + ChromaDB index (data/embeddings/)
    -> evaluation baseline (18 samples, OpenAI gpt-4o-mini)
    -> quality/freshness reports (data/quality/)
    -> corruption simulation (data/clean/papers_clean_corrupted.json)
    -> re-index & re-evaluate corrupted pipeline
    -> repair từ immutable raw records (data/raw/)
    -> re-index & re-evaluate repaired pipeline
    -> comparison report (data/reports/corruption_report.md)
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| :--- | :--- | :--- | :--- | :--- |
| Ingestion | Crossref REST API | Fetch API, parse payload JATS/HTML, retry backoff | `data/raw/crossref_records.json` | Triệu Dương |
| Cleaning | Raw records | Clean HTML, parse date, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.json` | Triệu Dương |
| Embedding/index | Clean dataframe | SentenceTransformers MiniLM-L6-v2 + ChromaDB | `data/embeddings/papers_embeddings.json` | Triệu Dương |
| Evaluation | Clean dataframe + Index | Sinh 18 test queries, đo Hit Rate, Token F1, LLM Judge | `data/results/baseline_metrics.json` | Triệu Dương |
| Observability | Dataframe | Data quality rules (unique ID, null, empty summary) & Freshness | `data/quality/freshness_report.json` | Triệu Dương |
| Corruption/repair | Baseline dataframe | Simulate 6 dạng lỗi, đo sụt giảm, repair từ raw JSON | `data/results/corruption_log.json` | Triệu Dương |
| Orchestration | Main entrypoints | Điều phối Phase 1 baseline & Phase 2 corruption flow | `data/reports/phase1_report.md` | Triệu Dương |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| :--- | :--- |
| `LLM_PROVIDER` | `ollama` |
| `LLM_MODEL` | `llama3.2` (Quantized 3.2B Q4_K_M) |
| `OLLAMA_BASE_URL` | `http://localhost:11434` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 records |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 days |

### Lệnh chạy

**Baseline Pipeline (Pha 1):**
```bash
uv run python script/run_phase1.py
```

**Corruption & Repair Flow (Pha 2):**
```bash
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| :--- | :--- | :--- | :--- |
| Baseline pipeline | Thành công | 2026-08-06 03:51:10 UTC | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công | 2026-08-06 03:51:17 UTC | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu
- **Source**: Crossref REST API (`https://api.crossref.org/works`)
- **Query**: `agentic retrieval augmented generation large language model`
- **Filter**: `from-pub-date:2026-02-07,has-abstract:true`
- **Số record nhận được**: 24 records
- **Cơ chế retry/backoff**: Retry 3 lần với exponential backoff 1s, 2s, 4s nếu gặp HTTP status 429/503.

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| :--- | :--- | :--- | :--- | :--- |
| `paper_id` | String (DOI) | Có | Định danh duy nhất cho bài báo | Filter loại bỏ nếu thiếu |
| `title` | String | Có | Tiêu đề bài báo | Clean HTML, loại bỏ nếu rỗng |
| `summary` | String | Có | Tóm tắt / Abstract | Clean JATS XML tags, fallback text nếu trống |
| `authors_joined` | String | Có | Danh sách tác giả ghép nối | Fallback `"Unknown Author"` nếu rỗng |
| `published` | String (YYYY-MM-DD) | Có | Ngày xuất bản | Parse `date-parts`, default `"2024-01-01"` |
| `age_days` | Integer | Có | Tuổi bài báo tính theo ngày | `(run_date - published_date).days` |
| `text_for_embedding` | String | Có | Chuỗi tổng hợp để nhúng vector | Tạo chuẩn định dạng gồm Title, Category, Authors, Date & Summary |

---

## 6. Evaluation setup

- **Số câu hỏi**: 18 câu hỏi
- **Question types**: `summary`, `authors`, `published_date`
- **Ground-truth document ID**: Map trực tiếp với DOI của bài báo
- **LLM Provider / Model**: Local Ollama `llama3.2:latest` (Quantized Q4_K_M)
- **Test set dùng chung**: `data/eval/test_set.json` (giữ cố định 18 câu hỏi để đảm bảo so sánh công bằng giữa Baseline, Corrupted và Repaired).

---

## 7. Kết quả baseline (Cấu hình Local Ollama llama3.2)

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| :--- | --: | :--- |
| `retrieval_hit_rate` | **1.0000** | 100% câu hỏi tìm kiếm đúng tài liệu chứa câu trả lời |
| `mean_token_f1` | **0.1110** | Độ trùng lặp token chính xác giữa câu trả lời sinh ra và ground truth |
| `judge_accuracy` | **0.3333** | LLM Local Judge đánh giá mức độ đáp ứng chính xác |
| `mean_judge_score` | **2.61 / 5.0** | Chất lượng câu trả lời từ RAG Agent local |

---

## 8. Data quality và freshness

### Quality checks

| Check | Ngưỡng | Kết quả baseline | Bằng chứng |
| :--- | :--- | :--- | :--- |
| Null / Unique Paper IDs | 0 null, 0 dupes | **PASSED** (0 null, 0 dupes) | `data/quality/baseline_quality.json` |
| Null Title / Empty Summary | 0 null, 0 empty | **PASSED** (0 null, 0 empty) | `data/quality/baseline_quality.json` |

### Freshness

| Thuộc tính | Giá trị |
| :--- | :--- |
| Timestamp mới nhất | `2026-08-05` |
| Timestamp cũ nhất | `2026-02-09` |
| Trạng thái baseline | **FRESH** (0/24 bài báo bị stale) |

---

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế lên Metrics | Cách repair |
| :--- | :--- | --: | :--- | :--- | :--- |
| **Drop Latest** | Drop 2 bài mới nhất | 2 | Retrieval miss | Hit Rate tụt xuống 0.6667 | Ingest lại từ `data/raw/` |
| **Blank Summary** | Xóa rỗng summary | 2 | FAILED quality check | LLM trả lời thiếu thông tin | Phục hồi summary gốc |
| **Add Noise** | Append nhiễu rác | 2 | Giảm Token F1 | Nhiễu ngữ nghĩa vector search | Làm sạch text từ raw |
| **Truncate Title** | Cắt ngắn tiêu đề | 1 | Giảm exact match | Mất thông tin context | Phục hồi tiêu đề đầy đủ |
| **Stale Date** | Lùi ngày 5 năm | 2 | Freshness STALE | Báo động độ tươi dữ liệu | Phục hồi ngày gốc |
| **Duplicate IDs** | Nhân bản 2 dòng | 2 | FAILED unique check | Gây dư thừa index | Deduplicate theo `paper_id` |

---

## 10. So sánh baseline, corrupted và repaired (Ollama llama3.2)

| Metric / Signal | Baseline (Clean) | Corrupted (Damaged) | Repaired (Restored) | Thay đổi do Corruption | Mức phục hồi sau Repair |
| :--- | --: | --: | --: | --: | --: |
| **Retrieval Hit Rate** | **1.0000** | **0.6667** | **1.0000** | -0.3333 (-33.3%) | +0.3333 (Khôi phục 100%) |
| **Mean Token F1** | **0.1110** | **0.0544** | **0.1110** | -0.0566 (-51.0%) | +0.0566 (Khôi phục 100%) |
| **Judge Accuracy** | **0.3333** | **0.5000** | **0.3333** | Biến đổi theo rác context | Phục hồi mức Baseline |
| **Mean Judge Score** | **2.61** | **3.11** | **2.61** | Biến đổi theo rác context | Phục hồi mức Baseline |
| **Quality Status** | **PASSED** | **FAILED** | **PASSED** | Phát hiện 2 dupes + 2 blank | Khôi phục PASSED |
| **Freshness Status** | **FRESH** | **FRESH** | **FRESH** | Phát hiện 2 stale rows | Khôi phục 0 stale rows |


### Hai kết luận rút ra:
1. **Dữ liệu bị lỗi làm suy giảm trực tiếp hiệu năng RAG Agent**: Việc rỗng summary và mất bản ghi mới khiến Hit Rate tụt 11.1% và Judge Score giảm từ 4.89 xuống 4.11. Data Quality Checks cảnh báo `FAILED` ngay lập tức.
2. **Khả năng tự chữa lành (Self-healing) dựa trên Raw Artifacts**: Nhờ giữ nguyên raw response từ Crossref API (`crossref_records.json`), pipeline thực hiện repair tự động và đưa 100% các chỉ số chất lượng về trạng thái baseline ban đầu.

---

## 11. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện |
| :--- | :--- | :--- |
| Số lượng sample test set (18 câu) | Phạm vi đo đạc vừa phải | Mở rộng test set tự động lên 50-100 câu bằng Ragas |
| Dependency vào API bên ngoài | Nguy cơ bị rate limit khi fetch live | Lưu đệm snapshot raw data dự phòng |

---

## 12. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Đã hoàn thành báo cáo cá nhân riêng tại `report/2A202601695_TrieuDuong.md`.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.

