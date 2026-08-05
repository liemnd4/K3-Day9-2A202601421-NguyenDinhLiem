# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung     |
| --------------- | ------------ |
| Họ và tên       | Nguyễn Hồng Yến |
| MSSV            | 2A202601065 |
| Khóa/Lớp        | K3 |
| Vai trò chính   | Người 3 — Payment Agent & Policy Agent |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Payment Agent | `payment_agent.py` (`analyze_payment`) | `CaseData` | `PaymentFindings` | Hoàn thành |
| Policy Agent | `policy_agent.py` (`evaluate_policy`) | `DeliveryFindings`, `PaymentFindings`, `CaseData` | `PolicyDecision` | Hoàn thành |
| Task 3 Test Suite | `test_task3.py` | Mock data cases | Unit Test Success (4/4 tests passed) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Tích hợp luồng Verifier & Coordinator | Người 4 / `verifier.py` & `run_all.py` | Khớp schema output JSON và hỗ trợ ghi log `trace.jsonl` cho 50 case |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng Payment Agent | `payment_agent.py` | Tính toán chính xác `payment_total`, `item_total`, `freight_total`, cờ `is_split_valid` và evidence `payment:` | `python3 payment_agent.py` |
| Xây dựng Policy Agent | `policy_agent.py` | Thực thi bộ 6 quy tắc ưu tiên `EC_POLICY_V1`, đưa ra `primary_issue`, `case_status`, refund BRL, actions | `python3 policy_agent.py` |
| Viết Unit test cho Task 3 | `test_task3.py` | Đảm bảo 100% test cases trôi chảy qua các kịch bản late seller, canceled paid, split payment, no item | `python3 test_task3.py` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Task 3 đóng vai trò quyết định chính của hệ thống:
1. Phân tích tài chính: Kiểm tra việc khớp tiền giữa tổng thanh toán với tổng giá trị hàng và phí vận chuyển (sai số $\le 0.10$ BRL).
2. Phán quyết chính xác: Nhận bằng chứng từ Delivery Agent và Payment Agent để áp dụng thứ tự ưu tiên tuyệt đối từ Rule 1 &rarr; Rule 6.

### Cách triển khai
- **Payment Agent:** Lặp qua `payments` và `items` trong `CaseData` để tính tổng tiền, đối soát cờ `is_split_valid` khi số dòng thanh toán $\ge 2$.
- **Policy Agent:** Đánh giá lần lượt:
  1. `canceled_order_paid` (nếu đơn hủy & đã trả tiền)
  2. `unavailable_order_paid` (nếu đơn không có hàng & đã trả tiền)
  3. `late_delivery_seller` (nếu giao muộn do seller bàn giao quá hạn)
  4. `late_delivery_logistics` (nếu giao muộn do đơn vị vận chuyển)
  5. `valid_split_payment` (nếu thanh toán chia dòng hợp lệ)
  6. `unsupported_late_claim` (nếu giao đúng hạn / không thỏa mãn quy tắc trên)

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `CaseData`, `DeliveryFindings`, `PaymentFindings` |
| Output | `PolicyDecision` (chứa `primary_issue`, `case_status`, `recommended_refund_brl`, `evidence_ids`, `resolution_actions`) |
| Module phụ thuộc | `contracts.py`, `delivery_agent.py` |
| Module sử dụng output | `verifier.py`, `run_all.py` |
| Điều kiện lỗi cần xử lý | Đơn hàng không có item row, đơn hàng bị thiếu mốc thời gian |

### Cách xác minh

```bash
python3 test_task3.py
```

- **Kết quả mong đợi:** Ran 4 tests in 0.002s — OK.
- **Kết quả thực tế:** 100% test cases passed.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần xử lý thứ tự ưu tiên khi một đơn hàng vừa có dấu hiệu trễ hạn vừa bị trạng thái `canceled` / `unavailable`.
- **Các phương án đã cân nhắc:** 
  1. Đánh giá giao hàng trễ trước.
  2. Đánh giá trạng thái hủy đơn/hết hàng trước (theo bảng ưu tiên Mục 4 README).
- **Phương án đã chọn:** Phương án 2 (Ưu tiên trạng thái hủy đơn trước).
- **Lý do:** Tuân thủ 100% quy tắc nghiệp vụ `EC_POLICY_V1`. Nếu đơn đã bị hủy mà khách đã thanh toán, khách có quyền nhận lại 100% tiền đơn (`issue_full_refund`) thay vì chỉ nhận refund phí ship.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Order không có `items` dẫn đến lỗi chia cho 0 hoặc lỗi index khi truy cập `items[0]`.
- **Lệnh hoặc bước tái hiện:** Chạy thử case `MOCK_ORDER_4` (không có item row).
- **Nguyên nhân gốc:** Đơn hàng bị hủy hoặc không sẵn có ở dữ liệu gốc Olist không tạo dòng trong file `order_items`.
- **Cách xử lý:** Thêm kiểm tra điều kiện `if case_data.items:` trước khi truy cập item, gán `item_ids = []`, `seller_ids = []`, `item_total_brl = 0.0`, `freight_total_brl = 0.0`.
- **Cách xác minh sau khi sửa:** Chạy `test_mock_case_no_item` thành công.
- **Điều học được:** Luôn chủ động xử lý edge case thiếu dữ liệu liên kết trong relational dataset.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu từ 9 file CSV Olist được `DataLoader` nạp vào bộ nhớ và chỉ mục hóa theo `order_id`.
2. `Coordinator` tiếp nhận file `EC_xxx.json` từ `input/`, lấy `claimed_order_id` để query `CaseData`.
3. `DeliveryAgent` kiểm tra thời gian giao hàng và bàn giao cho shipper.
4. `PaymentAgent` đối soát tài chính và `PolicyAgent` quyết định phương án hoàn tiền cùng bằng chứng (`evidence_ids`).
5. `VerifierAgent` kiểm tra định dạng regex và trim giới hạn entity trước khi xuất file JSON vào `output/EC_xxx.json` và lưu `trace.jsonl`.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Hồng Yến  
**Ngày xác nhận:** 2026-08-05
