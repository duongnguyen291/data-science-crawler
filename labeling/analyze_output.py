"""
Script phân tích output từ labeling system
"""
import pandas as pd
import os
from collections import Counter

def analyze_labeling_output(output_dir="labeled_output", num_parts=5):
    """
    Phân tích output từ các file labeled_part_*.csv
    """
    print("="*70)
    print("PHAN TICH OUTPUT LABELING SYSTEM")
    print("="*70)
    print()
    
    # Đọc tất cả các file
    all_data = []
    for part_num in range(1, num_parts + 1):
        file_path = os.path.join(output_dir, f"labeled_part_{part_num}.csv")
        if os.path.exists(file_path):
            df = pd.read_csv(file_path)
            all_data.append(df)
            print(f"[OK] Doc file part {part_num}: {len(df)} comments")
        else:
            print(f"[WARNING] Khong tim thay {file_path}")
    
    if not all_data:
        print("[ERROR] Khong co file nao de phan tich!")
        return
    
    # Gộp tất cả data
    combined_data = pd.concat(all_data, ignore_index=True)
    total_comments = len(combined_data)
    
    print(f"\n[INFO] Tong so comments: {total_comments}")
    print("="*70)
    print()
    
    # 1. Phân bố Labels
    print("1. PHAN BO LABELS")
    print("-"*70)
    label_counts = combined_data['final_label'].value_counts()
    label_percentages = (label_counts / total_comments * 100).round(2)
    
    for label, count in label_counts.items():
        pct = label_percentages[label]
        bar = "#" * int(pct / 2)
        print(f"  {label:12s}: {count:4d} ({pct:5.2f}%) {bar}")
    
    # Đếm None/empty
    none_count = combined_data['final_label'].isna().sum() + (combined_data['final_label'] == '').sum()
    if none_count > 0:
        pct = (none_count / total_comments * 100)
        bar = "#" * int(pct / 2)
        print(f"  {'None/Empty':12s}: {none_count:4d} ({pct:5.2f}%) {bar}")
    
    print()
    
    # 2. Phân bố Strategies
    print("2. PHAN BO STRATEGIES")
    print("-"*70)
    strategy_counts = combined_data['strategy'].value_counts()
    strategy_percentages = (strategy_counts / total_comments * 100).round(2)
    
    for strategy, count in strategy_counts.items():
        pct = strategy_percentages[strategy]
        bar = "#" * int(pct / 2)
        print(f"  {strategy:15s}: {count:4d} ({pct:5.2f}%) {bar}")
    
    print()
    
    # 3. Chi tiết Strategies
    print("3. CHI TIET STRATEGIES")
    print("-"*70)
    
    # Fast Accept
    fast_accept = combined_data[combined_data['strategy'] == 'fast_accept']
    if len(fast_accept) > 0:
        print(f"  Fast Accept: {len(fast_accept)} comments")
        print(f"    -> Tiet kiem: Khong can goi Pro model")
    
    # Agreement
    agreement = combined_data[combined_data['strategy'] == 'agreement']
    if len(agreement) > 0:
        print(f"  Agreement: {len(agreement)} comments")
        print(f"    -> Flash va Pro dong y -> Tin cay cao")
    
    # Soft Voting
    soft_voting = combined_data[combined_data['strategy'] == 'soft_voting']
    if len(soft_voting) > 0:
        print(f"  Soft Voting: {len(soft_voting)} comments")
        avg_margin = soft_voting['margin'].mean()
        min_margin = soft_voting['margin'].min()
        max_margin = soft_voting['margin'].max()
        print(f"    -> Margin trung binh: {avg_margin:.3f}")
        print(f"    -> Margin min: {min_margin:.3f}, max: {max_margin:.3f}")
    
    # Human Review
    human_review = combined_data[combined_data['strategy'] == 'human_review']
    if len(human_review) > 0:
        print(f"  Human Review: {len(human_review)} comments")
        print(f"    -> CAN REVIEW THU CONG!")
        if 'margin' in human_review.columns:
            avg_margin = human_review['margin'].mean()
            print(f"    -> Margin trung binh: {avg_margin:.3f}")
    
    print()
    
    # 4. Phân tích Margin
    print("4. PHAN TICH MARGIN (cho Soft Voting)")
    print("-"*70)
    margins = combined_data[combined_data['strategy'] == 'soft_voting']['margin']
    if len(margins) > 0:
        print(f"  So luong: {len(margins)}")
        print(f"  Trung binh: {margins.mean():.3f}")
        print(f"  Median: {margins.median():.3f}")
        print(f"  Min: {margins.min():.3f}")
        print(f"  Max: {margins.max():.3f}")
        print(f"  Std: {margins.std():.3f}")
        
        # Phân bố margin
        low_margin = (margins < 0.2).sum()
        medium_margin = ((margins >= 0.2) & (margins < 0.3)).sum()
        high_margin = (margins >= 0.3).sum()
        print(f"\n  Phan bo:")
        print(f"    < 0.2 (thap): {low_margin}")
        print(f"    0.2-0.3 (trung binh): {medium_margin}")
        print(f"    >= 0.3 (cao): {high_margin}")
    
    print()
    
    # 5. Comments cần Human Review
    print("5. COMMENTS CAN HUMAN REVIEW")
    print("-"*70)
    if len(human_review) > 0:
        print(f"  Tong so: {len(human_review)}")
        print(f"\n  Cac comments can review:")
        for idx, row in human_review.iterrows():
            comment_text = str(row['comment_text'])[:100] + "..." if len(str(row['comment_text'])) > 100 else str(row['comment_text'])
            # Remove emoji và ký tự đặc biệt để tránh lỗi encoding
            try:
                comment_text = comment_text.encode('ascii', 'ignore').decode('ascii')
            except:
                pass
            margin = row.get('margin', 'N/A')
            print(f"\n  [{idx}] Margin: {margin}")
            print(f"      Comment: {comment_text}")
    else:
        print("  Khong co comment nao can human review!")
    
    print()
    
    # 6. Phân tích theo Label và Strategy
    print("6. CROSS-TAB: LABEL vs STRATEGY")
    print("-"*70)
    cross_tab = pd.crosstab(combined_data['final_label'], combined_data['strategy'], margins=True)
    print(cross_tab)
    print()
    
    # 7. Đánh giá chất lượng
    print("7. DANH GIA CHAT LUONG")
    print("-"*70)
    
    # Tỷ lệ agreement (cao = tốt)
    agreement_rate = len(agreement) / total_comments * 100
    print(f"  Agreement rate: {agreement_rate:.2f}%")
    
    # Tỷ lệ human review (thấp = tốt, nhưng cần đủ để catch edge cases)
    human_review_rate = len(human_review) / total_comments * 100
    print(f"  Human review rate: {human_review_rate:.2f}%")
    
    # Tỷ lệ có label (không None)
    labeled_rate = (combined_data['final_label'].notna() & (combined_data['final_label'] != '')).sum() / total_comments * 100
    print(f"  Labeled rate: {labeled_rate:.2f}%")
    
    print()
    
    # 8. Một số ví dụ
    print("8. VI DU THEO TUNG LOAI")
    print("-"*70)
    
    def safe_print_text(text):
        """Loại bỏ emoji và ký tự đặc biệt để in an toàn"""
        try:
            return text.encode('ascii', 'ignore').decode('ascii')
        except:
            return str(text)[:50]
    
    # Positive examples
    positive_examples = combined_data[combined_data['final_label'] == 'positive'].head(3)
    if len(positive_examples) > 0:
        print("\n  Positive examples:")
        for idx, row in positive_examples.iterrows():
            text = str(row['comment_text'])[:80] + "..." if len(str(row['comment_text'])) > 80 else str(row['comment_text'])
            text = safe_print_text(text)
            print(f"    - [{row['strategy']}] {text}")
    
    # Negative examples
    negative_examples = combined_data[combined_data['final_label'] == 'negative'].head(3)
    if len(negative_examples) > 0:
        print("\n  Negative examples:")
        for idx, row in negative_examples.iterrows():
            text = str(row['comment_text'])[:80] + "..." if len(str(row['comment_text'])) > 80 else str(row['comment_text'])
            text = safe_print_text(text)
            print(f"    - [{row['strategy']}] {text}")
    
    # Note: Irrelevant label đã được bỏ, không còn hiển thị examples
    
    print()
    print("="*70)
    print("[HOAN THANH] Phan tich xong!")
    print("="*70)


if __name__ == "__main__":
    analyze_labeling_output()

