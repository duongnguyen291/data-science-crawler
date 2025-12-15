"""
Script chia data_features.csv thành 5 tập để chạy song song
"""
import pandas as pd
import os

def split_data(input_file="data_features.csv", num_splits=5, output_dir="data_splits"):
    """
    Chia data thành num_splits tập
    
    Args:
        input_file: File CSV input
        num_splits: Số tập cần chia
        output_dir: Thư mục chứa các tập đã chia
    """
    # Đọc data
    print(f"Đang đọc {input_file}...")
    data = pd.read_csv(input_file)
    total_rows = len(data)
    print(f"Tổng số rows: {total_rows}")
    
    # Tạo thư mục output
    os.makedirs(output_dir, exist_ok=True)
    
    # Tính số rows mỗi tập
    rows_per_split = total_rows // num_splits
    remainder = total_rows % num_splits
    
    print(f"\nChia thành {num_splits} tập:")
    print(f"- Mỗi tập: ~{rows_per_split} rows")
    if remainder > 0:
        print(f"- Tập cuối sẽ có thêm {remainder} rows")
    
    # Chia và lưu
    start_idx = 0
    for i in range(num_splits):
        # Tập cuối lấy hết phần dư
        end_idx = start_idx + rows_per_split + (1 if i < remainder else 0)
        
        split_data = data.iloc[start_idx:end_idx].copy()
        output_file = os.path.join(output_dir, f"data_part_{i+1}.csv")
        
        split_data.to_csv(output_file, index=False)
        print(f"[OK] Tap {i+1}: {len(split_data)} rows -> {output_file}")
        
        start_idx = end_idx
    
    print(f"\n[SUCCESS] Hoan thanh! Da chia thanh {num_splits} tap trong thu muc '{output_dir}'")

if __name__ == "__main__":
    split_data()

