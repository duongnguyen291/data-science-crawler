"""
Script test chạy 5 process labeling song song với 100 samples
Sử dụng để test thông luồng trước khi chạy full data
"""
import subprocess
import sys
import os
import pandas as pd
from config import API_KEYS

def create_test_data(input_file="data_features.csv", num_samples=100, output_dir="data_splits_test", num_splits=5):
    """
    Tạo test data từ num_samples đầu tiên và chia thành num_splits tập
    
    Args:
        input_file: File CSV input
        num_samples: Số samples để test
        output_dir: Thư mục chứa test data splits
        num_splits: Số tập cần chia
    """
    print(f"[TEST] Tao test data tu {num_samples} samples dau tien...")
    
    # Đọc data
    if not os.path.exists(input_file):
        print(f"[ERROR] Khong tim thay {input_file}")
        return False
    
    data = pd.read_csv(input_file)
    total_rows = len(data)
    
    if total_rows < num_samples:
        print(f"[WARNING] Data chi co {total_rows} rows, se dung het")
        num_samples = total_rows
    
    # Lấy num_samples đầu tiên
    test_data = data.iloc[:num_samples].copy()
    print(f"[OK] Da lay {len(test_data)} samples")
    
    # Tạo thư mục output
    os.makedirs(output_dir, exist_ok=True)
    
    # Tính số rows mỗi tập
    rows_per_split = len(test_data) // num_splits
    remainder = len(test_data) % num_splits
    
    print(f"[INFO] Chia thanh {num_splits} tap:")
    print(f"  - Moi tap: ~{rows_per_split} rows")
    if remainder > 0:
        print(f"  - Tap cuoi se co them {remainder} rows")
    
    # Chia và lưu
    start_idx = 0
    for i in range(num_splits):
        # Tập cuối lấy hết phần dư
        end_idx = start_idx + rows_per_split + (1 if i < remainder else 0)
        
        split_data = test_data.iloc[start_idx:end_idx].copy()
        output_file = os.path.join(output_dir, f"data_part_{i+1}.csv")
        
        split_data.to_csv(output_file, index=False)
        print(f"  [OK] Tap {i+1}: {len(split_data)} rows -> {output_file}")
        
        start_idx = end_idx
    
    print(f"[SUCCESS] Da tao test data trong thu muc '{output_dir}'")
    return True


def run_parallel_test_labeling(num_samples=100):
    """
    Chạy 5 process labeling song song với test data
    
    Args:
        num_samples: Số samples để test (mặc định 100)
    """
    data_splits_dir = "data_splits_test"
    num_parts = 5
    
    # Tạo test data nếu chưa có
    if not os.path.exists(data_splits_dir) or not any(
        os.path.exists(os.path.join(data_splits_dir, f"data_part_{i+1}.csv"))
        for i in range(num_parts)
    ):
        print(f"[TEST] Tao test data...")
        if not create_test_data(num_samples=num_samples, output_dir=data_splits_dir, num_splits=num_parts):
            return
    else:
        print(f"[INFO] Test data da ton tai trong '{data_splits_dir}'")
    
    # Kiểm tra API keys
    missing_keys = []
    for i, key in enumerate(API_KEYS, 1):
        if not key or key.strip() == "":
            missing_keys.append(i)
    
    if missing_keys:
        print(f"[WARNING] Thieu API keys cho part: {missing_keys}")
        print("[TIP] Hay set API keys trong config.py hoac environment variables:")
        print("   GEMINI_API_KEY_1, GEMINI_API_KEY_2, ..., GEMINI_API_KEY_5")
        return
    
    # Kiểm tra các file split
    processes = []
    for part_num in range(1, num_parts + 1):
        input_file = os.path.join(data_splits_dir, f"data_part_{part_num}.csv")
        
        if not os.path.exists(input_file):
            print(f"[WARNING] Khong tim thay {input_file}")
            continue
        
        api_key = API_KEYS[part_num - 1]
        
        # Tạo command
        cmd = [
            sys.executable,
            "labeler.py",
            input_file,
            api_key,
            str(part_num)
        ]
        
        # Tạo log file riêng cho test
        log_file = f"log_test_part_{part_num}.txt"
        
        print(f"[START] Khoi dong test process {part_num}...")
        print(f"   Input: {input_file}")
        print(f"   Log: {log_file}")
        
        # Chạy process
        with open(log_file, 'w', encoding='utf-8') as log:
            process = subprocess.Popen(
                cmd,
                stdout=log,
                stderr=subprocess.STDOUT,
                cwd=os.path.dirname(os.path.abspath(__file__))
            )
            processes.append((part_num, process))
    
    if not processes:
        print("[ERROR] Khong co process nao duoc khoi dong!")
        return
    
    print(f"\n[SUCCESS] Da khoi dong {len(processes)} test process")
    print(f"[INFO] Logs duoc ghi vao: log_test_part_*.txt")
    print(f"[INFO] Ket qua se duoc luu vao: labeled_output/labeled_part_*.csv")
    print(f"\n[TIP] De xem progress, chay: tail -f log_test_part_*.txt")
    print(f"[TIP] De dung tat ca: Ctrl+C hoac kill cac process\n")
    
    # Đợi tất cả process hoàn thành
    try:
        for part_num, process in processes:
            return_code = process.wait()
            if return_code == 0:
                print(f"[SUCCESS] Test part {part_num} hoan thanh!")
            else:
                print(f"[ERROR] Test part {part_num} loi voi code {return_code}")
        
        print(f"\n[TEST COMPLETE] Tat ca {len(processes)} test process da hoan thanh!")
        print(f"[INFO] Kiem tra ket qua trong: labeled_output/labeled_part_*.csv")
        
    except KeyboardInterrupt:
        print("\n[WARNING] Dang dung tat ca test process...")
        for part_num, process in processes:
            process.terminate()
        print("[OK] Da dung tat ca test process")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Test labeling system voi so luong samples nho")
    parser.add_argument(
        "--samples",
        type=int,
        default=100,
        help="So luong samples de test (default: 100)"
    )
    
    args = parser.parse_args()
    
    print("="*60)
    print("[TEST MODE] Chay test labeling voi", args.samples, "samples")
    print("="*60)
    print()
    
    run_parallel_test_labeling(num_samples=args.samples)

