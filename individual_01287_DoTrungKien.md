# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                          |
| --------------- | --------------------------------- |
| Họ và tên       | Đỗ Trung Kiên                     |
| MSSV            | 2A202601287 (5 số cuối: 01287)    |
| Khóa/Lớp        | K3-AIThucChien                    |
| Vai trò chính   | Người 2 · Order & Delivery Analysis Engineer |
| Ngày hoàn thành | 2026-08-05                        |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable     | File/hàm phụ trách                                                                                       | Input nhận vào   | Output bàn giao                                         | Trạng thái  |
| ---------------------- | -------------------------------------------------------------------------------------------------------- | ---------------- | ------------------------------------------------------- | ----------- |
| Order Seller Agent     | [order_seller_agent.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/order_seller_agent.py)   | `CaseData`       | `SellerViolation` list & vi phạm bàn giao quá hạn      | Hoàn thành  |
| Delivery Agent         | [delivery_agent.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/delivery_agent.py) / [order_delivery/](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/order_delivery/) | `CaseData`       | `DeliveryFindings` (is_delivery_late, root_cause_hint) | Hoàn thành  |
| Agent Unit Tests       | [order_delivery/test_order_delivery_agent.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/order_delivery/test_order_delivery_agent.py) | `ALL_MOCK_CASES` | 7 Unit tests passed                                     | Hoàn thành  |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                      | Thành viên/module được hỗ trợ | Kết quả                                                                                 |
| ------------------------------ | ----------------------------- | --------------------------------------------------------------------------------------- |
| Hỗ trợ trích xuất Seller vi phạm | Member 3 ([policy_agent.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/policy_agent.py)) | Cung cấp danh sách Seller ID chính xác vi phạm bàn giao quá hạn `shipping_limit_date`. |
| Tích hợp Coordinator           | Member 4 ([coordinator.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/coordinator.py))   | Đóng gói `delivery_agent.py` shim khớp 100% với luồng điều phối chính.                 |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                 | File/hàm/artifact liên quan       | Kết quả bàn giao                                              | Cách xác minh                             |
| ------------------------------------- | --------------------------------- | ------------------------------------------------------------- | ----------------------------------------- |
| Phân tích mốc thời gian giao hàng trễ | `delivery_agent.py`               | Đánh giá chuẩn xác `is_delivery_late` (True/False)            | `python order_delivery/test_order_delivery_agent.py` |
| Phân định lỗi Seller vs Logistics     | `analyze_delivery_deterministic()`| Tách biệt chính xác lỗi bàn giao Seller quá hạn `shipping_limit_date` vs lỗi Vận chuyển quá `order_estimated_delivery_date` | 7 test cases trong unit test suite |
| Thu thập bằng chứng Evidence IDs      | `ev_order`, `ev_item`, `ev_seller`| Mảng bằng chứng `evidence_ids` khớp định dạng regex          | Verification trong pipeline integration   |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
- Đã phân lập chính xác 8 case `late_delivery_seller` (Seller giao trễ quá `shipping_limit_date`) và 8 case `late_delivery_logistics` (Logistics giao trễ quá `order_estimated_delivery_date`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Trong quy trình xử lý khiếu nại thương mại điện tử, việc xác định một đơn hàng bị giao trễ do **seller bàn giao muộn cho đơn vị vận chuyển** (`SELLER_HANDOFF_AFTER_LIMIT`) hay do **đơn vị vận chuyển giao trễ cho khách** (`CARRIER_DELIVERED_AFTER_ESTIMATE`) đòi hỏi phải bóc tách mốc thời gian của từng item trong đơn (`shipping_limit_date`) so với mốc bàn giao thực tế (`order_delivered_carrier_date`) và ngày giao dự kiến (`order_estimated_delivery_date`).

### Cách triển khai

Module `order_delivery/order_delivery_agent.py` (cùng các shim [delivery_agent.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/delivery_agent.py) & [order_seller_agent.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/order_seller_agent.py)) được triển khai với kiến trúc 2 tầng (Hybrid Deterministic + Groq LLM Guardrail):
1. **Deterministic Engine (`analyze_delivery_deterministic`)**:
   - Parse chuỗi ISO timestamp bằng `parse_dt()` hỗ trợ định dạng Olist linh hoạt (`T` hoặc khoảng trắng).
   - Kiểm tra `is_delivery_late`: `order_delivered_customer_date > order_estimated_delivery_date`.
   - Lặp qua danh sách `items` trong `CaseData`: So sánh `order_delivered_carrier_date > shipping_limit_date`. Nếu trễ, tạo record `SellerViolation` chứa `seller_id`, `order_item_id`, `shipping_limit_date`, `delivered_to_carrier_date`.
   - Sinh `root_cause_hint`:
     - Đơn hủy/thiếu hàng (`canceled`/`unavailable`): `None`.
     - Giao trễ và có seller vi phạm: `"SELLER_HANDOFF_AFTER_LIMIT"`.
     - Giao trễ nhưng seller không vi phạm: `"CARRIER_DELIVERED_AFTER_ESTIMATE"`.
     - Không giao trễ: `"DELIVERY_WITHIN_ESTIMATE"`.
   - Tự động gom bằng chứng `evidence_ids` đúng định dạng (`order:<id>`, `item:<id>:<item_id>`, `seller:<id>`).
2. **Groq LLM Integration (`analyze_delivery_llm`)**:
   - Sử dụng model **`llama-3.1-8b-instant`** (đảm bảo điều kiện ≤ 10B parameters).
   - Gọi API qua thư viện chuẩn `urllib.request` (zero external dependency).
   - Nếu có lỗi API key hoặc mạng, tự động fallback mượt mà về Deterministic Engine.

### Input, output và contract

| Thành phần              | Mô tả                                                                                              |
| ----------------------- | -------------------------------------------------------------------------------------------------- |
| Input                   | `CaseData` Object từ [data_loader.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/data_loader.py) |
| Output                  | `DeliveryFindings` Object (chứa `is_delivery_late`, `seller_violations`, `root_cause_hint`, `evidence`) |
| Module phụ thuộc        | [contracts.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/contracts.py)              |
| Module sử dụng output   | [policy_agent.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/policy_agent.py) & [coordinator.py](file:///d:/VinAI_20K/K3-Day9-2A202601421-NguyenDinhLiem/coordinator.py) |
| Điều kiện lỗi cần xử lý | Xử lý các đơn hàng bị hủy/unavailable có mốc thời gian delivered bằng `None`                       |

### Cách xác minh

```bash
python order_delivery/test_order_delivery_agent.py
```

- **Kết quả mong đợi:** 7 unit test cases chạy thành công (Ran 7 tests in ~0.3s, OK).
- **Kết quả thực tế:** 7/7 tests đạt kết quả OK.
- **Artifact/log:** Không chứa `.env` hoặc API key.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn cấu trúc thư mục đóng gói riêng (`order_delivery/` + `delivery_agent.py` shim) và lựa chọn giữa việc dùng thuần LLM (Groq API) hay kết hợp thuật toán so sánh timestamp (Deterministic Engine).
- **Các phương án đã cân nhắc:**  
  1. *Chỉ đặt file lẻ ở root*: Dễ bị xung đột tên file hoặc nhầm lẫn với code của 3 thành viên khác.
  2. *Đóng gói riêng trong thư mục `order_delivery/` có `__init__.py` và `delivery_agent.py` shim*: Đảm bảo độc lập tuyệt đối, sạch sẽ, Coordinator (Người 4) có thể import trực tiếp `from delivery_agent import analyze_delivery`.
- **Phương án đã chọn:** Phương án 2 (Đóng gói riêng trong thư mục `order_delivery/` kết hợp shim).
- **Lý do:** Giúp phân định rõ ràng quyền sở hữu module của Người 2, tương thích 100% với `coordinator.py` của nhóm khi pull code mới về.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `TypeError: '>' not supported between instances of 'str' and 'NoneType'`
- **Lệnh hoặc bước tái hiện:** Chạy `delivery_agent.py` trên case đơn hàng bị hủy (`canceled`).
- **Nguyên nhân gốc:** Đơn hủy không có ngày giao khách `order_delivered_customer_date` (giá trị là `None`).
- **Cách xử lý:** Bổ sung hàm `parse_dt()` hỗ trợ chuẩn hóa chuỗi và kiểm tra `if not order.order_delivered_customer_date:` thì gán `is_delivery_late = False` trước khi so sánh.
- **Cách xác minh sau khi sửa:** Chạy kiểm thử trên toàn bộ case canceled/unavailable, không phát sinh lỗi crash.
- **Điều học được:** Cần kiểm tra điều kiện tồn tại (`None` check) cho mọi trường dữ liệu timestamp có thể bị rỗng.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu khiếu nại thô từ `input/EC_xxx.json` đi qua `coordinator.py` lấy `claimed_order_id`, sau đó `data_loader.py` truy vấn 9 file CSV thô để trích xuất `CaseData`.
2. `DeliveryAgent` (Người 2) và `PaymentAgent` (Người 3) độc lập nhận `CaseData` để phân tích mốc thời gian và tài chính, trả về `DeliveryFindings` và `PaymentFindings`.
3. `PolicyAgent` (Người 3) tổng hợp kết quả, áp bảng ưu tiên `EC_POLICY_V1` để tạo `PolicyDecision` chứa nhóm lỗi, số tiền hoàn và mảng bằng chứng đã chắt lọc.
4. `Verifier` (Người 4) kiểm tra độc lập các ranh giới Regex và Schema giới hạn trước khi ghi file JSON ra `output/` và ghi log `trace.jsonl`.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Trung Kiên  
**Ngày xác nhận:** 2026-08-05
