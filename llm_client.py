"""
llm_client.py — Người 1 sở hữu file này.
==========================================
Hàm gọi model dùng chung cho cả nhóm (nếu agent nào cần LLM để
diễn giải case bằng ngôn ngữ tự nhiên, ví dụ tóm tắt customer_request
hoặc giải thích quyết định cho khách). Model dùng để RA QUYẾT ĐỊNH
(refund, primary_issue...) vẫn nên là rule-based trong policy_agent.py
để đảm bảo chấm điểm chính xác 100% -- LLM chỉ hỗ trợ phần diễn giải,
không quyết định số liệu.

Cài đặt trước khi dùng:
    pip install groq python-dotenv --break-system-packages

Model đề xuất (đều <=10B parameters, khai báo rõ theo yêu cầu mục 9):
    - llama-3.1-8b-instant  (8B)
    - gemma2-9b-it          (9B)
"""

import os
from dotenv import load_dotenv

load_dotenv()

MODEL_NAME = "llama-3.1-8b-instant"  # khai báo rõ trong code theo yêu cầu đề bài

_client = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError("Chưa set GROQ_API_KEY trong .env")
        _client = Groq(api_key=api_key)
    return _client


def call_llm(prompt: str, model: str = MODEL_NAME, temperature: float = 0.0) -> str:
    """Gọi model, trả về text response. temperature=0.0 để kết quả ổn định
    (quan trọng vì bài chấm điểm cần tái lập được kết quả)."""
    client = _get_client()
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        temperature=temperature,
        max_tokens=500,
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    print(call_llm("Trả lời đúng 1 câu: 2+2 bằng mấy?"))
