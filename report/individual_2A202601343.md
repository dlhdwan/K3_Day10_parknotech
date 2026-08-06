# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| ------------------ | -------------------------- |
| Họ và tên | **Đỗ Ngọc Anh** |
| MSSV | 2A202601343 |
| Khóa/Lớp | K3 |
| Tên nhóm | ParkNoTech |
| Vai trò chính | **Data Observability Owner (Thành viên 3)** |
| Repository | git@github.com-acc2:dlhdwan/K3_Day10_parknotech.git |
| Ngày hoàn thành | 2026-08-06 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | ---------------- | ----------------- | ---------- |
| Data Quality Checks | `src/observability/quality.py`<br>`run_data_quality_checks()` | Clean DataFrame, Settings | `baseline.json`, `corrupted.json`, `repaired.json` | Hoàn thành |
| Freshness Monitoring | `src/observability/quality.py`<br>`build_freshness_report()` | Clean DataFrame, Settings | `freshness_report.json`, `corrupted_freshness.json`, `repaired_freshness.json` | Hoàn thành |
| Markdown Reporting | `src/observability/reporting.py`<br>`generate_phase1_report()`<br>`generate_corruption_report()` | Metrics, Quality, Freshness | `phase1_report.md`, `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Kiểm thử tích hợp | `phase1.py`, `corruption_flow.py` | Xác minh Quality và Reporting hoạt động đúng khi chạy end-to-end |
| Hỗ trợ merge code | `reporting.py` | Giải quyết merge conflict sau khi đồng bộ với `origin/main` |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Triển khai Data Quality Checks | `quality.py` | `baseline.json`, `corrupted.json`, `repaired.json` | Chạy `python script/run_phase1.py` và kiểm tra `data/quality/` |
| Triển khai Freshness Report | `quality.py` | `freshness_report.json`, `corrupted_freshness.json`, `repaired_freshness.json` | Kiểm tra file JSON sinh ra trong `data/quality/` |
| Triển khai Markdown Report | `reporting.py` | `phase1_report.md`, `corruption_report.md` | Kiểm tra báo cáo trong `data/reports/` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Phần việc của tôi tập trung vào **Data Observability**, giúp theo dõi chất lượng dữ liệu sau bước Cleaning, kiểm tra độ mới của dữ liệu (Freshness) và tổng hợp toàn bộ kết quả của pipeline thành các báo cáo Markdown phục vụ đánh giá.

### Cách triển khai

- **`run_data_quality_checks()`**
  - Kiểm tra số lượng bản ghi.
  - Kiểm tra `paper_id` không bị thiếu và không trùng.
  - Kiểm tra `title` không rỗng.
  - Kiểm tra độ dài `summary`.
  - Kiểm tra số lượng bài báo quá cũ (`stale_rows`).
  - Xuất kết quả thành JSON trong `data/quality/`.

- **`build_freshness_report()`**
  - Xác định bài báo mới nhất và cũ nhất.
  - Đếm số lượng bài vượt ngưỡng `freshness_threshold_days`.
  - Sinh báo cáo Freshness dạng JSON.

- **`generate_phase1_report()`**
  - Tổng hợp Source Summary.
  - Tổng hợp Evaluation Metrics.
  - Tổng hợp Quality và Freshness.
  - Sinh báo cáo Markdown cho Baseline Pipeline.

- **`generate_corruption_report()`**
  - So sánh Baseline, Corrupted và Repaired.
  - Tổng hợp Metrics, Quality và Freshness.
  - Sinh báo cáo Markdown phục vụ đánh giá Phase 2.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Clean DataFrame, Evaluation Metrics, Settings |
| Output | Quality JSON, Freshness JSON, Markdown Reports |
| Module phụ thuộc | `cleaning.py`, `phase1.py`, `corruption_flow.py` |
| Module sử dụng output | `phase1.py`, `corruption_flow.py` |

### Cách xác minh

```bash
python script/run_phase1.py
python script/run_corruption_flow.py
```

Kết quả mong đợi:

- Sinh đầy đủ các file trong `data/quality/`
- Sinh `phase1_report.md`
- Sinh `corruption_report.md`
- Pipeline chạy hoàn chỉnh không phát sinh lỗi.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Báo cáo cần sử dụng chung dữ liệu từ nhiều module khác nhau.
- **Phương án đã chọn:** Tách phần Quality/Freshness thành JSON trước, sau đó `reporting.py` chỉ đọc các dictionary đầu vào để sinh Markdown.
- **Lý do:** Giảm phụ thuộc giữa các module, dễ tái sử dụng cho cả Baseline và Corruption Flow.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `TypeError: Object of type int64 is not JSON serializable`.
- **Nguyên nhân:** Giá trị trả về từ Pandas có kiểu `numpy.int64` và `numpy.bool_`, không thể ghi trực tiếp bằng `json.dump()`.
- **Cách xử lý:** Ép kiểu toàn bộ giá trị sang `int()` và `bool()` trước khi ghi JSON.
- **Cách xác minh:** Chạy lại `run_phase1.py`, các file JSON được ghi thành công.

Ngoài ra, tôi cũng gặp lỗi:

```
AttributeError: 'str' object has no attribute 'isoformat'
```

Nguyên nhân là trường `published` đã ở dạng chuỗi. Tôi xử lý bằng cách chỉ gọi `isoformat()` khi đối tượng hỗ trợ phương thức này (`hasattr(..., "isoformat")`), giúp Freshness Report hoạt động với cả chuỗi và kiểu datetime.

---

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu được lấy từ Crossref và chuẩn hóa thành Clean DataFrame.
2. Clean DataFrame được dùng để tạo Embedding và Chroma Index.
3. Evaluation sử dụng cùng một Test Set cho Baseline, Corrupted và Repaired.
4. Sau Evaluation, Data Quality và Freshness được kiểm tra để đánh giá tình trạng dữ liệu.
5. Cuối cùng Reporting tổng hợp toàn bộ Metrics và Quality thành báo cáo Markdown.

---

## 8. Phân tích kết quả

### Nhận xét

- Baseline đạt Quality PASS và Freshness PASS.
- Sau khi Corruption, số lượng bản ghi stale tăng lên và một số Quality Check không còn đạt.
- Sau Repair, Quality và Freshness được phục hồi về trạng thái ban đầu.
- Điều này cho thấy Data Observability có thể phát hiện chính xác ảnh hưởng của dữ liệu lỗi và xác nhận quá trình Repair thành công.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data Quality nên được kiểm tra tự động trước khi dữ liệu đi vào Vector Store.
2. Freshness là một tín hiệu quan trọng đối với các hệ thống RAG sử dụng dữ liệu thay đổi theo thời gian.
3. Báo cáo tự động giúp việc đánh giá pipeline dễ theo dõi và giảm thao tác thủ công.

### Nếu có thêm thời gian

Tôi muốn mở rộng hệ thống Observability bằng cách bổ sung thêm các chỉ số như tỷ lệ dữ liệu trùng lặp, phân phối độ dài văn bản và dashboard trực quan để theo dõi chất lượng dữ liệu theo thời gian.

---

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận đều dựa trên artifact hoặc metrics thực tế.
- [x] Báo cáo không chứa `.env`, API key hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo của thành viên khác.

**Họ và tên:** Đỗ Ngọc Anh  
**Ngày xác nhận:** 2026-08-06