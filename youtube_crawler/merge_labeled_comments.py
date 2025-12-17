"""
Merge sentiment labels from multiple labeled CSV files into the main CSV file.
"""

import pandas as pd
import glob
from pathlib import Path


def merge_labeled_comments(
    main_csv_path: str,
    labeled_files_pattern: str,
    output_csv_path: str
) -> None:
    """
    Merge sentiment labels from labeled CSV files into the main CSV.
    
    Args:
        main_csv_path: Path to the main CSV file (unlabeled)
        labeled_files_pattern: Glob pattern to find labeled CSV files
        output_csv_path: Path to save the merged output CSV
    """
    # Read main CSV file
    print(f"Reading main CSV file: {main_csv_path}")
    main_df = pd.read_csv(main_csv_path)
    print(f"Loaded {len(main_df)} rows from main CSV")
    
    # Find all labeled CSV files
    labeled_files = glob.glob(labeled_files_pattern)
    if not labeled_files:
        print(f"No labeled files found matching pattern: {labeled_files_pattern}")
        return
    
    print(f"Found {len(labeled_files)} labeled files:")
    for f in sorted(labeled_files):
        print(f"  - {Path(f).name}")
    
    # Read and merge all labeled files
    labeled_dfs = []
    for file_path in sorted(labeled_files):
        df = pd.read_csv(file_path)
        # Extract only comment_id, sentiment_label, sentiment_score
        df_subset = df[['comment_id', 'sentiment_label', 'sentiment_score']].copy()
        labeled_dfs.append(df_subset)
        print(f"  Loaded {len(df_subset)} rows from {Path(file_path).name}")
    
    # Concatenate all labeled data
    merged_labeled = pd.concat(labeled_dfs, ignore_index=True)
    print(f"\nTotal labeled rows before deduplication: {len(merged_labeled)}")
    
    # Remove duplicates (keep first occurrence)
    merged_labeled = merged_labeled.drop_duplicates(subset=['comment_id'], keep='first')
    print(f"Total unique labeled rows after deduplication: {len(merged_labeled)}")
    
    # Left join with main CSV to fill sentiment_label and sentiment_score
    print("\nMerging labels into main CSV...")
    
    # Store original sentiment columns if they exist (will be empty/NaN)
    has_original_labels = 'sentiment_label' in main_df.columns and 'sentiment_score' in main_df.columns
    
    # Merge with labeled data
    main_df = main_df.merge(
        merged_labeled[['comment_id', 'sentiment_label', 'sentiment_score']],
        on='comment_id',
        how='left',
        suffixes=('', '_new')
    )
    
    # Handle merged columns
    if 'sentiment_label_new' in main_df.columns:
        # Use new values from labeled files, fallback to original if exists
        if has_original_labels:
            main_df['sentiment_label'] = main_df['sentiment_label_new'].fillna(main_df['sentiment_label'])
            main_df['sentiment_score'] = main_df['sentiment_score_new'].fillna(main_df['sentiment_score'])
        else:
            main_df['sentiment_label'] = main_df['sentiment_label_new']
            main_df['sentiment_score'] = main_df['sentiment_score_new']
        
        main_df = main_df.drop(columns=['sentiment_label_new', 'sentiment_score_new'])
    
    print(f"Rows after merge: {len(main_df)}")
    print(f"Rows with labels: {main_df['sentiment_label'].notna().sum()}")
    
    # Remove rows where sentiment_label == "neutral" AND sentiment_score == 0
    print("\nFiltering out neutral comments with score 0...")
    before_filter = len(main_df)
    
    # Convert sentiment_score to numeric if it's string
    main_df['sentiment_score'] = pd.to_numeric(main_df['sentiment_score'], errors='coerce')
    
    filter_mask = ~(
        (main_df['sentiment_label'] == 'neutral') & 
        (main_df['sentiment_score'] == 0.0)
    )
    main_df = main_df[filter_mask].copy()
    
    removed = before_filter - len(main_df)
    print(f"Removed {removed} rows (neutral with score 0)")
    print(f"Final rows: {len(main_df)}")
    
    # Save output
    print(f"\nSaving merged CSV to: {output_csv_path}")
    main_df.to_csv(output_csv_path, index=False, encoding='utf-8')
    print("Done!")

if __name__ == "__main__":
    main_csv = "/Users/lucasnhandang/Study_Work/HUST/20251/Data_Science/data-science-crawler/youtube_crawler/raw_comments_20251118_115552_filtered.csv"
    labeled_pattern = "/Users/lucasnhandang/Study_Work/HUST/20251/Data_Science/data-science-crawler/youtube_crawler/raw_comments_20251118_115552_filtered_l*_r*_labeled.csv"
    output_csv = "/Users/lucasnhandang/Study_Work/HUST/20251/Data_Science/data-science-crawler/youtube_crawler/youtube_raw_comments_labeled_negative_full.csv"
    
    merge_labeled_comments(main_csv, labeled_pattern, output_csv)

'''
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Merge sentiment labels from multiple labeled CSV files into the main CSV file"
    )
    parser.add_argument(
        "--main-csv",
        type=str,
        required=True,
        help="Path to the main CSV file (unlabeled)",
    )
    parser.add_argument(
        "--labeled-pattern",
        type=str,
        required=True,
        help="Glob pattern to find labeled CSV files",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        required=True,
        help="Path to save the merged output CSV",
    )
    
    args = parser.parse_args()
    
    merge_labeled_comments(args.main_csv, args.labeled_pattern, args.output_csv)
'''