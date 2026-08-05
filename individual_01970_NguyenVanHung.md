# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                          |
| --------------- | --------------------------------- |
| Họ và tên       | Nguyễn Văn Hùng                   |
| MSSV            | 2A202601970                       |
| Khóa/Lớp        | K3-AIThucChien                    |
| Vai trò chính   | Integration, Verifier & QA Engineer (Người 4) |
| Ngày hoàn thành | 2026-08-05                        |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Verifier Agent | `verifier.py` / `verify_policy_decision()` | `PolicyDecision` Object | Sanitized `PolicyDecision` & danh sách warnings | Hoàn thành |
| Workflow Coordinator | `coordinator.py` / `process_case_input()`, `process_case_file()` | Case input JSON dict / File path | `PolicyDecision`, trace dict, warnings | Hoàn thành |
| Batch Runner & Pipeline Execution | `run_all.py` / `run_all_cases()` | Folder `input/` (`EC_001.json` - `EC_050.json`) | Folder `output/` (50 JSONs) & `logging/trace.jsonl` | Hoàn thành |
| System Architecture & Metadata | `architecture.md`, `logging/metadata.json` | Khung kiến trúc & giới hạn LLM | Sơ đồ Agent, vai trò, handoff flow & metadata (Llama-3.1-8B, <=10B) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------- | ----------------------------- | ----------------------- |
| Xây dựng Contract & Helpers | Toàn bộ nhóm | Thống nhất `contracts.py` với các dataclass chuẩn, helper `to_output_json()` và `ev_*` format IDs. |
| Fallback Data & Agent Loader | Người 1, 2, 3 | Xây dựng fallback CSV loader và fallback agents trong `coordinator.py` giúp nhóm test pipeline sớm và tự động tích hợp mượt khi code chính hoàn thành. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Kiểm định Schema & Boundary | `verifier.py` | Đảm bảo 100% output tuân thủ giới hạn mảng và Regex ID | Run `python verifier.py` |
| Tự động hóa Batch Execution | `run_all.py`, `coordinator.py` | Chạy và xuất 50 file JSON dưới 4 giây với 0 warnings | Run `python run_all.py` & kiểm tra folder `output/` |
| Báo cáo Kiến trúc & Metadata | `architecture.md`, `logging/metadata.json` | Đầy đủ sơ đồ Mermaid, phân quyền dữ liệu và khai báo Model <=10B | Kiểm tra root repo & folder `logging/` |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
- Đã xây dựng bộ Verifier kiểm định độc lập và trình điều khiển `run_all.py` tự động hóa toàn bộ luồng xử lý 50 case, xuất đầy đủ 50 file `EC_001.json` &rarr; `EC_050.json` hợp lệ schema 100% và file nhật ký vết `logging/trace.jsonl`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Kiểm định độc lập kết quả đầu ra từ Policy Agent để đảm bảo không bị vi phạm giới hạn kích thước mảng (max 5 entities, 10 evidence, 3 causes, 3 parties, 5 actions), đúng định dạng Regex ID (`order:`, `item:`, `payment:`, `seller:`, `policy:`), làm tròn tài chính 2 chữ số thập phân, đồng thời điều phối luồng làm việc end-to-end giữa 4 vai trò và ghi nhật ký thực thi.

### Cách triển khai
Viết bộ lọc Regex kiểm tra các tiền tố ID. Sử dụng mảng cắt lát (list slicing) để ép số lượng phần tử không vượt quá giới hạn. Trong `coordinator.py`, kết nối tuần tự từ Data Loader $\rightarrow$ Order/Seller/Delivery Agent $\rightarrow$ Payment Agent $\rightarrow$ Policy Agent $\rightarrow$ Verifier. Trong `run_all.py`, chuyển đổi object thành JSON schema bằng `to_output_json()` và ghi nhật ký lượt chạy mới nhất vào `logging/trace.jsonl`.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | `input/EC_xxx.json` $\rightarrow$ `CaseData` $\rightarrow$ Agent findings $\rightarrow$ `PolicyDecision` |
| Output | File `output/EC_xxx.json` chuẩn schema & file `logging/trace.jsonl` |
| Module phụ thuộc | `contracts.py`, `data_loader.py`, `order_delivery/order_delivery_agent.py`, `payment_agent.py`, `policy_agent.py` |
| Module sử dụng output | Hệ thống chấm điểm tự động / nộp file output zip |
| Điều kiện lỗi cần xử lý | Order không tồn tại/thiếu item, ID sai định dạng regex, confidence ngoài [0,1], case_status bất tương thích với recommended_refund_brl |

### Cách xác minh

```bash
python run_all.py
```

- **Kết quả mong đợi:** 50 case chạy thành công, 0 verifier warnings, đầy đủ 50 file JSON hợp lệ trong `output/`.
- **Kết quả thực tế:** Chạy thành công 50/50 case trong ~17 giây (hoặc ~3.8s với fallback), 0 verifier warnings.
- **Artifact/log:** `logging/trace.jsonl` và 50 file trong `output/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cơ chế xử lý file nhật ký vết `logging/trace.jsonl` và kiến trúc kết nối các Agent.
- **Các phương án đã cân nhắc:**  
  1. Ghi dồn (append) qua nhiều lần chạy và throw exception cứng khi thiếu module của thành viên khác.
  2. Ghi mới hoàn toàn (overwrite) ở mỗi lượt chạy batch và cung cấp cơ chế fallback mượt mà cho Coordinator.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đề bài Mục 8 ghi rõ: *"trace.jsonl: trace chạy thật của 50 case (không append, chỉ cần lượt chạy mới nhất)"*. Việc có fallback cho phép kiểm thử batch pipeline độc lập từ rất sớm trước khi các thành viên khác nộp code.
- **Bằng chứng quyết định phù hợp:** File `logging/trace.jsonl` luôn chứa chính xác 50 dòng tương ứng với 50 case của lượt chạy mới nhất.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Lỗi định dạng Evidence ID Regex loại bỏ các ID hợp lệ chứa dấu gạch ngang (`-`), gây mất bằng chứng khi kiểm tra.
- **Lệnh hoặc bước tái hiện:** Chạy `verifier.py` trên các Evidence ID thực tế có chứa dấu `-` (ví dụ: `seller:seller-id-123`).
- **Nguyên nhân gốc:** Pattern regex ban đầu `re.compile(r"^seller:[a-zA-Z0-9_]+$")` chưa bổ sung ký tự `-`.
- **Cách xử lý:** Cập nhật các pattern regex thành `re.compile(r"^seller:[a-zA-Z0-9_\-]+$")` cho tất cả loại entity ID.
- **Cách xác minh sau khi sửa:** Chạy lại `python verifier.py` và `python run_all.py`, tất cả Evidence ID chứa `-` đều hợp lệ, 0 cảnh báo false positive.
- **Điều học được:** Regex cho ID dữ liệu thực tế cần bao quát đa dạng dạng ký tự (bao gồm gạch nối).

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu khiếu nại thô từ `input/EC_xxx.json` đi qua `coordinator.py` lấy `claimed_order_id`, sau đó `data_loader.py` truy vấn 9 file CSV thô Olist để trích xuất `CaseData`.
2. `OrderDeliveryAgent` và `PaymentAgent` độc lập nhận `CaseData` để phân tích mốc thời gian (bàn giao shipper vs `shipping_limit_date`, ngày giao thực tế vs `estimated_delivery_date`) và tài chính (đối soát tổng thanh toán vs item + freight), trả về `DeliveryFindings` và `PaymentFindings`.
3. `PolicyAgent` tổng hợp kết quả, áp bảng quy tắc ưu tiên `EC_POLICY_V1` (canceled/unavailable paid -> late delivery -> valid split payment -> unsupported late claim) để tạo `PolicyDecision`.
4. `Verifier` kiểm tra độc lập các ranh giới Regex và Schema giới hạn (slicing mảng, làm tròn 2 chữ số thập phân, khớp case_status với tiền refund) trước khi ghi file JSON ra `output/` và ghi log `logging/trace.jsonl`.
5. Đánh giá chất lượng dựa trên tổng có trọng số của 6 thành phần: Primary issue (20%), Affected entities (20%), Root cause (15%), Evidence IDs (15%), Financial resolution (20%), Resolution actions (10%).

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn Hùng  
**Ngày xác nhận:** 2026-08-05
