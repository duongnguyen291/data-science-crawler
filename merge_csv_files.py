#!/usr/bin/env python3
"""
Script để nối file CSV A vào sau file CSV B
Xử lý header tự động: giữ header của file B, bỏ qua header của file A khi nối
"""

import csv
import sys
from pathlib import Path


def merge_csv_files(file_b_path, file_a_path, output_path=None):
    """
    Nối file CSV A vào sau file CSV B
    
    Args:
        file_b_path: Đường dẫn đến file CSV B (file gốc)
        file_a_path: Đường dẫn đến file CSV A (file cần nối vào)
        output_path: Đường dẫn file output (nếu None thì tự tạo file mới)
    
    Returns:
        Tuple (số dòng đã nối vào, đường dẫn file output)
    """
    file_b = Path(file_b_path)
    file_a = Path(file_a_path)
    
    # Kiểm tra file tồn tại
    if not file_a.exists():
        raise FileNotFoundError(f"File A không tồn tại: {file_a_path}")
    if not file_b.exists():
        raise FileNotFoundError(f"File B không tồn tại: {file_b_path}")
    
    # Xác định file output
    if output_path is None:
        # Tự động tạo tên file mới: file_B.csv -> file_B_merged.csv
        stem = file_b.stem
        suffix = file_b.suffix
        output_path = file_b.parent / f"{stem}_merged{suffix}"
    else:
        output_path = Path(output_path)
    
    # Đọc header từ file B
    with open(file_b, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header_b = next(reader)
    
    # Đọc header từ file A để kiểm tra
    with open(file_a, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header_a = next(reader)
    
    # Kiểm tra header có khớp không
    if header_a != header_b:
        print(f"⚠️  Cảnh báo: Header không khớp!")
        print(f"   File B header: {header_b}")
        print(f"   File A header: {header_a}")
        print(f"   Vẫn tiếp tục nối dữ liệu...")
    
    # Đọc toàn bộ dữ liệu từ file B
    rows_b = []
    with open(file_b, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)  # Bỏ qua header
        rows_b = list(reader)
    
    # Đọc dữ liệu từ file A (bỏ qua header)
    rows_a = []
    with open(file_a, 'r', encoding='utf-8', newline='') as f:
        reader = csv.reader(f)
        next(reader)  # Bỏ qua header
        rows_a = list(reader)
    
    # Ghi file output
    rows_merged = rows_b + rows_a
    with open(output_path, 'w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(header_b)  # Ghi header từ file B
        writer.writerows(rows_merged)
    
    return len(rows_a), str(output_path)


def main():
    """Hàm main để chạy từ command line hoặc interactive mode"""
    # Nếu có đủ arguments, dùng command line mode
    if len(sys.argv) >= 3:
        file_b = sys.argv[1]
        file_a = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else None
    else:
        # Interactive mode
        print("=" * 60)
        print("  CHƯƠNG TRÌNH NỐI FILE CSV")
        print("=" * 60)
        print("\nHướng dẫn:")
        print("  - File B: File gốc (giữ header)")
        print("  - File A: File sẽ được nối vào sau file B")
        print("  - Output: Để trống sẽ tự tạo file mới (tên_file_B_merged.csv)")
        print()
        
        # Nhập file B
        while True:
            file_b = input("📁 Nhập đường dẫn file CSV B (file gốc): ").strip()
            if file_b:
                if Path(file_b).exists():
                    break
                else:
                    print(f"❌ File không tồn tại: {file_b}")
                    print("   Vui lòng nhập lại.\n")
            else:
                print("❌ Không được để trống. Vui lòng nhập lại.\n")
        
        # Nhập file A
        while True:
            file_a = input("📁 Nhập đường dẫn file CSV A (file cần nối): ").strip()
            if file_a:
                if Path(file_a).exists():
                    break
                else:
                    print(f"❌ File không tồn tại: {file_a}")
                    print("   Vui lòng nhập lại.\n")
            else:
                print("❌ Không được để trống. Vui lòng nhập lại.\n")
        
        # Nhập output (tùy chọn)
        output_input = input("📁 Nhập đường dẫn file output (Enter để tự tạo): ").strip()
        output = output_input if output_input else None
        print()
    
    try:
        rows_added, output_file = merge_csv_files(file_b, file_a, output)
        print(f"✅ Đã nối thành công!")
        print(f"   Đã thêm {rows_added} dòng từ file A")
        print(f"   File output: {output_file}")
    except Exception as e:
        print(f"❌ Lỗi: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

