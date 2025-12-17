"""
Phân tích confidence score (sentiment_score) từ file CSV
"""

import pandas as pd
import numpy as np
from pathlib import Path

# Cấu hình
CSV_FILE = "youtube_raw_comments_labeled_full_merged.csv"

def load_data(file_path):
    """Đọc file CSV"""
    print(f"Đang đọc file: {file_path}")
    df = pd.read_csv(file_path)
    print(f"Tổng số dòng: {len(df):,}")
    print(f"Số cột: {len(df.columns)}")
    return df

def analyze_confidence_scores(df):
    """Phân tích chi tiết confidence scores"""
    
    # Làm sạch dữ liệu - loại bỏ các giá trị null hoặc không hợp lệ
    df_clean = df[df['sentiment_score'].notna()].copy()
    df_clean['sentiment_score'] = pd.to_numeric(df_clean['sentiment_score'], errors='coerce')
    df_clean = df_clean[df_clean['sentiment_score'].notna()]
    
    # Loại bỏ các sample có confidence score = 0
    initial_count = len(df_clean)
    df_clean = df_clean[df_clean['sentiment_score'] != 0].copy()
    removed_count = initial_count - len(df_clean)
    if removed_count > 0:
        print(f"\nĐã loại bỏ {removed_count:,} samples có confidence score = 0")
    
    print("\n" + "="*60)
    print("PHÂN TÍCH CONFIDENCE SCORE (SENTIMENT_SCORE)")
    print("="*60)
    print("Lưu ý: Đã loại bỏ tất cả samples có confidence score = 0")
    
    scores = df_clean['sentiment_score']
    
    # Thống kê cơ bản
    print("\n1. THỐNG KÊ CƠ BẢN:")
    print("-" * 40)
    print(f"Tổng số comments có confidence score (sau khi loại bỏ score = 0): {len(scores):,}")
    print(f"Giá trị trung bình (Mean): {scores.mean():.4f}")
    print(f"Giá trị trung vị (Median): {scores.median():.4f}")
    print(f"Độ lệch chuẩn (Std): {scores.std():.4f}")
    print(f"Giá trị nhỏ nhất (Min): {scores.min():.4f}")
    print(f"Giá trị lớn nhất (Max): {scores.max():.4f}")
    
    # Quartiles
    print("\n2. PHÂN VỊ (QUARTILES):")
    print("-" * 40)
    q25 = scores.quantile(0.25)
    q50 = scores.quantile(0.50)
    q75 = scores.quantile(0.75)
    q90 = scores.quantile(0.90)
    q95 = scores.quantile(0.95)
    q99 = scores.quantile(0.99)
    print(f"Q25 (25th percentile): {q25:.4f}")
    print(f"Q50 (50th percentile - Median): {q50:.4f}")
    print(f"Q75 (75th percentile): {q75:.4f}")
    print(f"Q90 (90th percentile): {q90:.4f}")
    print(f"Q95 (95th percentile): {q95:.4f}")
    print(f"Q99 (99th percentile): {q99:.4f}")
    
    # Phân bố theo khoảng điểm
    print("\n3. PHÂN BỐ THEO KHOẢNG ĐIỂM:")
    print("-" * 40)
    bins = [0.0, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0]
    labels = ['0.0-0.5', '0.5-0.6', '0.6-0.7', '0.7-0.8', '0.8-0.9', '0.9-0.95', '0.95-1.0']
    df_clean['score_range'] = pd.cut(scores, bins=bins, labels=labels, include_lowest=True)
    range_counts = df_clean['score_range'].value_counts().sort_index()
    for range_name, count in range_counts.items():
        percentage = (count / len(scores)) * 100
        print(f"{range_name}: {count:,} ({percentage:.2f}%)")
    
    # Phân tích theo sentiment label
    print("\n4. PHÂN TÍCH THEO SENTIMENT LABEL:")
    print("-" * 40)
    if 'sentiment_label' in df_clean.columns:
        label_stats = df_clean.groupby('sentiment_label')['sentiment_score'].agg([
            'count', 'mean', 'median', 'std', 'min', 'max'
        ]).round(4)
        print(label_stats)
    
    # Đếm số lượng các giá trị unique
    print("\n5. CÁC GIÁ TRỊ UNIQUE:")
    print("-" * 40)
    unique_scores = sorted(scores.unique())
    print(f"Số giá trị unique: {len(unique_scores)}")
    print(f"Các giá trị: {unique_scores[:20]}...")  # Hiển thị 20 giá trị đầu
    
    # Top và bottom scores
    print("\n6. TOP 10 SCORES CAO NHẤT:")
    print("-" * 40)
    top_scores = scores.value_counts().head(10)
    for score, count in top_scores.items():
        percentage = (count / len(scores)) * 100
        print(f"Score {score:.2f}: {count:,} comments ({percentage:.2f}%)")
    
    return df_clean, scores

def main():
    """Hàm chính"""
    # Đường dẫn file
    script_dir = Path(__file__).parent
    csv_path = script_dir / CSV_FILE
    
    if not csv_path.exists():
        print(f"Lỗi: Không tìm thấy file {csv_path}")
        return
    
    # Đọc dữ liệu
    df = load_data(csv_path)
    
    # Phân tích
    df_clean, scores = analyze_confidence_scores(df)
    
    print("\n" + "="*60)
    print("HOÀN TẤT PHÂN TÍCH!")
    print("="*60)

if __name__ == "__main__":
    main()

