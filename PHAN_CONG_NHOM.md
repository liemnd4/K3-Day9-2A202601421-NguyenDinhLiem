# Phân công nhóm — K3 Day 09: Multi-Agent E-commerce Dispute Resolution

Repo: `K3-Day9-2A202601421-NguyenDinhLiem`

## 0. Nguyên tắc làm việc

- **Contract trước, code sau.** File `contracts.py` (đính kèm) định nghĩa chính xác dữ liệu mỗi agent nhận vào / trả ra. Ai cũng import file này. **Không ai tự ý sửa `contracts.py` một mình** — cần đổi gì thì báo cả nhóm trước.
- **Code song song bằng mock data.** File `mock_case_data.py` (đính kèm) chứa dữ liệu giả đúng shape với `contracts.py`. Người 2 và Người 3 dùng file này để code + test ngay, không cần chờ Data Layer thật xong. Khi Data Layer xong, chỉ cần đổi 1 dòng import.
- **Mỗi người 1 file riêng**, hạn chế 2 người cùng sửa 1 file → khi merge Git ít conflict.
- Dùng branch riêng: `git checkout -b nguoiX-ten-task`, commit thường xuyên, đừng dồn đến sát giờ mới merge.

## 1. Phân công chi tiết

### Người 1 — Data Layer + Infra
**File sở hữu:** `data_loader.py`, `.env` (mẫu `.env.example`), `llm_client.py`, `metadata.json`

| Việc | Chi tiết |
|---|---|
| Load CSV | Đọc 9 file CSV trong `data/`, xử lý đúng khóa join (`orders.order_id -> order_items.order_id` v.v. — xem mục 2 README) |
| `load_case(order_id) -> CaseData` | Trả về đúng object `CaseData` trong `contracts.py`: `order`, `items`, `payments`. Nếu order không có item row → `items=[]` |
| Edge case | `order_id` không tồn tại trong CSV → trả `order=None`, để agent khác biết mà báo lỗi thay vì crash |
| LLM client | Hàm `call_llm(prompt, model="llama-3.1-8b-instant")` dùng chung cho cả nhóm, đọc key từ `.env` |
| `metadata.json` | Ghi rõ tên model, số params, framework, runtime cho từng agent |

**Test bắt buộc trước khi giao cho nhóm:** chạy `load_case()` cho **cả 50** `claimed_order_id` trong `input/EC_001.json` → `EC_050.json`. Nếu order_id nào lỗi/không tìm thấy, báo ngay cả nhóm (khả năng cao là lỗi đọc CSV chứ không phải dữ liệu thiếu thật).

---

### Người 2 — Order/Seller Agent + Delivery Agent
**File sở hữu:** `order_seller_agent.py`, `delivery_agent.py`

| Agent | Input (contracts.py) | Output (contracts.py) | Logic |
|---|---|---|---|
| Order & Seller Agent | `CaseData` | góp phần vào `DeliveryFindings` | Với mỗi item, so `order_delivered_carrier_date` với `shipping_limit_date` của item đó → seller nào vi phạm thì thêm vào `seller_violations` |
| Delivery Agent | `CaseData` | `DeliveryFindings` | So ngày giao thực tế với `order_estimated_delivery_date` → `is_delivery_late` |

**Output cuối agent này = `DeliveryFindings`**, gồm cả `root_cause_hint` (`SELLER_HANDOFF_AFTER_LIMIT` / `CARRIER_DELIVERED_AFTER_ESTIMATE` / `DELIVERY_WITHIN_ESTIMATE`) và `evidence` (dùng helper `ev_order`, `ev_item`, `ev_seller` trong `contracts.py`, đừng tự chế format).

**Test:** dùng `mock_case_data.get_mock_case_late_seller()` — phải ra `root_cause_hint = SELLER_HANDOFF_AFTER_LIMIT`. Sau đó verify tay ít nhất 5/25 case "giao trễ" thật bằng cách tự tra CSV, tránh sai logic dây chuyền.

---

### Người 3 — Payment Agent + Policy Agent
**File sở hữu:** `payment_agent.py`, `policy_agent.py`

| Agent | Input | Output | Logic |
|---|---|---|---|
| Payment Agent | `CaseData` | `PaymentFindings` | `payment_total` vs `item_total + freight_total`, sai số ≤0.10 BRL → `is_split_valid`; cờ `is_paid = payment_total > 0` |
| Policy Agent | `DeliveryFindings` + `PaymentFindings` + `order_status` | `PolicyDecision` | Áp **đúng thứ tự ưu tiên** bảng mục 4 README: canceled/unavailable (có payment) ưu tiên cao nhất, rồi mới đến late delivery, rồi split payment, cuối cùng là reject |

**Lưu ý thứ tự ưu tiên (hay bị chấm sai nhất):**
1. `canceled_order_paid` / `unavailable_order_paid` — check trước tiên
2. `late_delivery_seller` / `late_delivery_logistics`
3. `valid_split_payment`
4. `unsupported_late_claim` — chỉ khi không rơi vào các case trên

**Test:** dùng 3 hàm mock (`get_mock_case_canceled_paid`, `get_mock_case_late_seller`, `get_mock_case_split_payment`) — mỗi hàm phải ra đúng `primary_issue` tương ứng. Sau đó verify tay 16 case "đã thanh toán nhưng không hoàn tất" + 9 case "nhiều dòng thanh toán" — đây là nhóm case dễ lẫn ưu tiên nhất.

---

### Người 4 — Coordinator + Verifier + Vận hành chung
**File sở hữu:** `coordinator.py`, `verifier.py`, `run_all.py`, `architecture.md`, `trace.jsonl`

| Việc | Chi tiết |
|---|---|
| Coordinator | Đọc `input/EC_xxx.json` → gọi `data_loader.load_case()` → gọi Order/Seller + Delivery Agent → gọi Payment Agent → gọi Policy Agent → build `PolicyDecision` |
| Verifier | Check evidence ID đúng regex (`order:`, `item:`, `payment:`, `seller:`, `policy:`); check giới hạn số lượng (≤5 mỗi entity set, ≤10 evidence, ≤3 causes, ≤3 parties, ≤5 actions); `confidence` ∈ [0,1] |
| `run_all.py` | Loop 50 case → dùng `contracts.to_output_json()` → ghi `output/EC_xxx.json` + append dòng vào `trace.jsonl` (chỉ lượt chạy mới nhất, không append chồng lần cũ) |
| `architecture.md` | Sơ đồ agent, vai trò, quyền truy cập data, luồng handoff — tổng hợp từ 3 người kia |

**Test:** chạy `run_all.py` full 50 case, kiểm tra `output/` có đúng 50 file `EC_001.json` → `EC_050.json`, không file thừa.

---

## 2. Timeline đề xuất (khớp checkpoint đề bài: 9h30–12h30 competition)

| Giai đoạn | Việc |
|---|---|
| 30 phút đầu | Cả nhóm thống nhất `contracts.py` (đã có sẵn, review lại nếu cần đổi) |
| Giờ 1–2 | Code song song bằng mock data (Người 2, 3, 4) song song với Người 1 làm Data Layer thật |
| Giờ 2.5 | Tích hợp: đổi mock → data thật, chạy thử 5–10 case, review chéo |
| Giờ 3 trở đi | Chạy full 50 case, fix bug, hoàn thiện `architecture.md`, `metadata.json`, báo cáo cá nhân |
| 30 phút cuối | Verify output đủ 50 file đúng schema, zip `output/`, commit code lên repo |

## 3. Checklist nộp bài (mục 8 README)

- [ ] Commit toàn bộ source code lên repo (KHÔNG commit `.env`)
- [ ] `output/` có đúng 50 file `EC_001.json` → `EC_050.json`
- [ ] `architecture.md` ở root repo
- [ ] `individual_5SoCuoiMHV_HoVaTen.md` — mỗi người viết báo cáo cá nhân của mình, để chung trong repo
- [ ] `trace.jsonl` — lượt chạy mới nhất
- [ ] `metadata.json` — model, params, framework, runtime, khai rõ tên model trong code
- [ ] Zip **chỉ** folder `output/` để nộp (không kèm source code, `.env`)

## 4. File đính kèm

- `contracts.py` — định nghĩa data shape dùng chung
- `mock_case_data.py` — data giả để code/test song song
