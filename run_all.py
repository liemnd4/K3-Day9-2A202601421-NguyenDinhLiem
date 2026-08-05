"""
run_all.py
==========
Module thuộc sở hữu của Người 4.
Nhiệm vụ:
- Chạy batch toàn bộ 50 case trong thư mục input/ (từ EC_001.json đến EC_050.json)
- Sử dụng coordinator.py để xử lý và verifier.py để kiểm soát chất lượng
- Chuyển PolicyDecision sang JSON schema hợp lệ bằng contracts.to_output_json()
- Ghi file kết quả tương ứng vào output/EC_xxx.json
- Tạo mới file log lượt chạy gần nhất tại logging/trace.jsonl
"""

import os
import glob
import json
import time
from collections import Counter
from typing import Dict, Any

from contracts import to_output_json
from coordinator import process_case_file


def run_all_cases(input_dir: str = "input", output_dir: str = "output", trace_file: str = os.path.join("logging", "trace.jsonl")):
    start_time = time.time()
    
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.dirname(trace_file), exist_ok=True)

    # Find all input JSON files
    input_files = sorted(glob.glob(os.path.join(input_dir, "EC_*.json")))
    if not input_files:
        print(f"[!] No case files matching 'EC_*.json' found in '{input_dir}' directory.")
        return

    print(f"[*] Starting batch processing for {len(input_files)} cases...")
    
    # Overwrite trace.jsonl for the latest run
    with open(trace_file, "w", encoding="utf-8") as f_trace:
        pass

    processed_count = 0
    issue_counts = Counter()
    total_warnings = 0

    for input_file in input_files:
        filename = os.path.basename(input_file)
        try:
            decision, trace_info, warnings = process_case_file(input_file)
            
            # Format to target JSON schema
            output_dict = to_output_json(decision)
            
            # Write to output/EC_xxx.json
            output_path = os.path.join(output_dir, filename)
            with open(output_path, "w", encoding="utf-8") as f_out:
                json.dump(output_dict, f_out, ensure_ascii=False, indent=2)
                f_out.write("\n")

            # Append trace to logging/trace.jsonl
            with open(trace_file, "a", encoding="utf-8") as f_trace:
                f_trace.write(json.dumps(trace_info, ensure_ascii=False) + "\n")

            processed_count += 1
            issue_counts[decision.primary_issue] += 1
            total_warnings += len(warnings)

            if warnings:
                print(f"  [!] {filename}: {len(warnings)} verifier warning(s)")

        except Exception as e:
            print(f"  [ERROR] Failed to process {filename}: {e}")

    elapsed = time.time() - start_time
    print("\n" + "=" * 50)
    print(f"[*] Batch Run Completed in {elapsed:.2f} seconds.")
    print(f"[*] Total cases processed: {processed_count}/{len(input_files)}")
    print(f"[*] Total verifier warnings: {total_warnings}")
    print("[*] Primary Issue Breakdown:")
    for issue, count in issue_counts.items():
        print(f"    - {issue}: {count}")
    print("=" * 50)


if __name__ == "__main__":
    run_all_cases()
