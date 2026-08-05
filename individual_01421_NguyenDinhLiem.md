# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                          |
| --------------- | --------------------------------- |
| Họ và tên       | Nguyễn Đình Liêm                  |
| MSSV            | 2A202601421                       |
| Khóa/Lớp        | K3-AIThucChien                    |
| Vai trò chính   | Leader / Data Layer & Preprocessing Engineer |
| Ngày hoàn thành | 2026-08-05                        |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao   | Trạng thái                            |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Data Layer Engine  | `data_loader.py` / `load_case()` | `claimed_order_id` (str) & 9 file CSV Olist | `CaseData` Object (orders, items, payments) | Hoàn thành |
| Data Contracts     | `contracts.py` | Định nghĩa schema Python Dataclasses | Các Data Contracts (`ItemInfo`, `PaymentInfo`, `DeliveryFindings`, `PolicyDecision`) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                 | Thành viên/module được hỗ trợ | Kết quả                 |
| ------------------------- | ----------------------------- | ----------------------- |
| Sắp xếp chỉ số mảng (Index Sorting) | Member 3 (`policy_agent.py`) | Sắp xếp `order_item_id` và `payment_sequential` tăng dần, giúp điểm tiêu chí *Entity liên quan* đạt 100%. |
| Tích hợp Data Contracts | Member 2 & Member 4 | Thống nhất dữ liệu truyền nhận giữa các Agent mà không bị lệch schema. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao          | Cách xác minh   |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Xây dựng Data Loader | `data_loader.py` | Nạp chính xác 50/50 đơn hàng từ 9 CSV thô | Run `python data_loader.py` |
| Thiết kế Data Contracts | `contracts.py` | 8 Dataclasses định nghĩa cấu trúc dữ liệu chuẩn | Import & type checking clean |

Nêu một output cụ thể mà phần việc của bạn tạo ra hoặc giúp xác minh:
- Đã trích xuất và đóng gói thành công 50 cấu trúc `CaseData` hoàn chỉnh, hỗ trợ các Agent bên dưới đối soát không bị thiếu hay sót dữ liệu từ các file CSV Olist.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng Tầng nạp dữ liệu (Data Layer) và Định nghĩa Hợp đồng dữ liệu (Data Contracts) giúp trích xuất thông tin từ 9 file CSV thô của Olist, đồng thời đảm bảo mảng dữ liệu trả về được sắp xếp tăng dần theo chỉ số (`order_item_id`, `payment_sequential`) để khớp vị trí mảng với Auto-Grader.

### Cách triển khai
Sử dụng thư viện `pandas` để truy vấn các dòng liên quan tới `order_id`. Áp dụng hàm `.sort_values("order_item_id")` cho bảng sản phẩm và `.sort_values("payment_sequential")` cho bảng thanh toán trước khi khởi tạo danh sách `ItemInfo` và `PaymentInfo`.

### Input, output và contract

| Thành phần              | Mô tả                                  |
| ----------------------- | -------------------------------------- |
| Input                   | `claimed_order_id` (str) từ file JSON khiếu nại |
| Output                  | `CaseData(order, items, payments)`     |
| Module phụ thuộc        | 9 file CSV thô trong `data/olist/`     |
| Module sử dụng output   | `delivery_agent.py`, `payment_agent.py`, `policy_agent.py` |
| Điều kiện lỗi cần xử lý | Xử lý trường hợp đơn hàng `unavailable` không có dòng `order_items` nào trong CSV |

### Cách xác minh

```bash
python -c "from data_loader import load_case; c = load_case('e2a03ccf5ea816036608b2d8c3ab8e60'); print(len(c.items), len(c.payments))"
```

- **Kết quả mong đợi:** In ra số lượng items và payments tương ứng của đơn hàng mà không bị lỗi KeyError.
- **Kết quả thực tế:** In ra `1 1` chính xác.
- **Artifact/log:** `data_loader.py` log execution.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi nạp danh sách `payments` từ CSV, các đợt thanh toán không được sắp xếp sẵn theo thứ tự `payment_sequential` 1, 2... làm mảng `payment_ids` sinh ra bị lộn xộn (`["...:2", "...:1"]`), bị Auto-Grader trừ điểm tiêu chí *Entity liên quan*.
- **Các phương án đã cân nhắc:**  
  1. Giữ nguyên thứ tự đọc ngẫu nhiên của `pandas`.
  2. Áp dụng sắp xếp cưỡng chế `.sort_values("payment_sequential")` ngay tại Tầng Data Loader.
- **Phương án đã chọn:** Phương án 2.
- **Lý do:** Đảm bảo tính nhất quán của dữ liệu ở mọi cấp độ, giúp toàn bộ các Agent phía sau tự động thụ hưởng mảng dữ liệu đã sắp xếp chuẩn.
- **Bằng chứng quyết định phù hợp:** Điểm tiêu chí *Entity liên quan* vọt lên mốc **100.00%** tuyệt đối.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `KeyError: 'order_item_id'` khi gọi `load_case()` cho các đơn hàng có trạng thái `unavailable`.
- **Lệnh hoặc bước tái hiện:** `python -c "from data_loader import load_case; load_case('EC_005_order_id')"`
- **Nguyên nhân gốc:** Đơn `unavailable` (như case `EC_005`) hoàn toàn không có dòng nào trong file `olist_order_items_dataset.csv`.
- **Cách xử lý:** Bổ sung kiểm tra mảng rỗng: nếu `item_rows.empty` thì gán `items = []` thay vì truy cập cột trực tiếp.
- **Cách xác minh sau khi sửa:** Chạy lại câu lệnh test với case `EC_005`, hàm trả về `items = []` không bị crash.
- **Điều học được:** Luôn phòng ngừa các trường hợp dữ liệu bị khuyết thiếu (missing rows) đối với dữ liệu thực tế.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu khiếu nại thô từ `input/EC_xxx.json` đi qua `coordinator.py` lấy `claimed_order_id`, sau đó `data_loader.py` truy vấn 9 file CSV thô để trích xuất `CaseData`.
2. `DeliveryAgent` và `PaymentAgent` độc lập nhận `CaseData` để phân tích mốc thời gian và tài chính, trả về `DeliveryFindings` và `PaymentFindings`.
3. `PolicyAgent` tổng hợp kết quả, áp bảng ưu tiên `EC_POLICY_V1` để tạo `PolicyDecision` chứa nhóm lỗi, số tiền hoàn và mảng bằng chứng đã chắt lọc.
4. `Verifier` kiểm tra độc lập các ranh giới Regex và Schema giới hạn trước khi ghi file JSON ra `output/` và ghi log `trace.jsonl`.
5. Đánh giá chất lượng dựa trên việc so sánh file nộp bài với file đáp án gốc (Golden Ground Truth) trên cả 6 tiêu chí có trọng số.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Đình Liêm  
**Ngày xác nhận:** 2026-08-05
