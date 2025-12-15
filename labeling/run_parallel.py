"""
Script chạy 5 process labeling song song
"""
import subprocess
import sys
import os
from config import API_KEYS

def run_parallel_labeling():
    """
    Chạy 5 process labeling song song, mỗi process xử lý 1 phần data
    """
    data_splits_dir = "data_splits"
    num_parts = 5
    
    # Kiểm tra data splits
    if not os.path.exists(data_splits_dir):
        print("[ERROR] Thu muc data_splits khong ton tai!")
        print("[TIP] Chay: python split_data.py truoc")
        return
    
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
        
        # Tạo log file
        log_file = f"log_part_{part_num}.txt"
        
        print(f"[START] Khoi dong process {part_num}...")
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
    
    print(f"\n[SUCCESS] Da khoi dong {len(processes)} process")
    print(f"[INFO] Logs duoc ghi vao: log_part_*.txt")
    print(f"[INFO] Ket qua se duoc luu vao: labeled_output/labeled_part_*.csv")
    print(f"\n[TIP] De xem progress, chay: tail -f log_part_*.txt")
    print(f"[TIP] De dung tat ca: Ctrl+C hoac kill cac process\n")
    
    # Đợi tất cả process hoàn thành
    try:
        for part_num, process in processes:
            return_code = process.wait()
            if return_code == 0:
                print(f"[SUCCESS] Part {part_num} hoan thanh!")
            else:
                print(f"[ERROR] Part {part_num} loi voi code {return_code}")
    except KeyboardInterrupt:
        print("\n[WARNING] Dang dung tat ca process...")
        for part_num, process in processes:
            process.terminate()
        print("[OK] Da dung tat ca process")


if __name__ == "__main__":
    run_parallel_labeling()

