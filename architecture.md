# Architecture — Multi-Agent E-commerce Dispute Resolution

## 1. Sơ đồ pipeline

```mermaid
flowchart TD
    A["Input<br/>input/EC_xxx.json"] --> B["Data layer<br/>Người 1 · Đọc & join CSV"]
    B --> C["Order & delivery agent<br/>Người 2 · Check giao hàng"]
    B --> D["Payment agent<br/>Người 3 · Đối soát payment"]
    C --> E["Policy agent<br/>Người 3 · Áp quy tắc ưu tiên"]
    D --> E
    E --> F["Verifier<br/>Người 4 · Check schema & giới hạn"]
    F --> G["Output<br/>output/EC_xxx.json"]
```

## 2. Vai trò từng agent

| Agent | Phụ trách | Input | Output | Quyền truy cập dữ liệu |
|---|---|---|---|---|
| **Data layer** | Người 1 | `claimed_order_id` | `CaseData` (order, items, payments) | Đọc 9 CSV trong `data/` |
| **Order & delivery agent** | Người 2 | `CaseData` | `DeliveryFindings` (seller vi phạm hạn, giao trễ hay không) | Chỉ đọc `order`, `items` từ `CaseData` |
| **Payment agent** | Người 3 | `CaseData` | `PaymentFindings` (đối soát tổng tiền, split payment) | Chỉ đọc `order`, `payments`, `items` từ `CaseData` |
| **Policy agent** | Người 3 | `DeliveryFindings` + `PaymentFindings` | `PolicyDecision` (primary issue, refund, action) | Không đọc CSV trực tiếp — chỉ nhận evidence đã tổng hợp từ 2 agent trên |
| **Verifier** | Người 4 | `PolicyDecision` | JSON đã validate, sẵn sàng ghi file | Không đọc CSV — chỉ kiểm tra format/giới hạn của `PolicyDecision` |
| **Coordinator** | Người 4 | `input/EC_xxx.json` | Điều phối toàn bộ luồng trên | Gọi tuần tự các agent, không tự suy luận nghiệp vụ |

## 3. Luồng handoff

1. **Coordinator** đọc 1 file case từ `input/`, lấy `claimed_order_id`.
2. **Data layer** tra CSV, trả về `CaseData` — dữ liệu thô, chưa có kết luận gì.
3. **Order & delivery agent** và **Payment agent** chạy song song trên cùng `CaseData`, mỗi agent chỉ phân tích domain của mình và tự sinh evidence ID theo đúng định dạng (`order:`, `item:`, `payment:`, `seller:`).
4. **Policy agent** nhận cả 2 bộ evidence, áp bảng quy tắc theo đúng thứ tự ưu tiên (`canceled_order_paid` / `unavailable_order_paid` $\rightarrow$ `late_delivery_seller` / `late_delivery_logistics` $\rightarrow$ `valid_split_payment` $\rightarrow$ `unsupported_late_claim`), tính refund, chọn action.
5. **Verifier** kiểm tra: evidence ID đúng regex và tồn tại thật trong CSV, không vượt giới hạn số lượng ($\le 5$ entity/set, $\le 10$ evidence, $\le 3$ causes, $\le 3$ parties, $\le 5$ actions), `confidence` $\in [0,1]$.
6. **Coordinator** ghi kết quả đã verify vào `output/EC_xxx.json`, đồng thời log vào `trace.jsonl`.

Điểm cốt lõi: Mỗi agent chỉ thấy đúng phần dữ liệu cần cho domain của mình (Policy agent không tự đọc CSV, Verifier không tự đọc CSV) — buộc hệ thống phải handoff bằng chứng thật giữa các agent thay vì gộp hết vào 1 prompt.

## 4. Model sử dụng

Mỗi agent sử dụng model $\le 10B$ parameters (`llama-3.1-8b-instant`), được khai báo chi tiết trong `metadata.json` và gọi qua Groq API client (`llm_client.py`).

## 5. Contract dùng chung

Toàn bộ shape dữ liệu giữa các agent (`CaseData`, `DeliveryFindings`, `PaymentFindings`, `PolicyDecision`) được định nghĩa trong `contracts.py` ở root repo, đảm bảo các thành viên phát triển song song mà không bị lệch format.
