#!/usr/bin/env python3
"""
Script để recheck labels của comments từ CSV file sử dụng text_cleaned.

Script này:
1. Đọc một CSV file và file txt chứa API keys (mỗi dòng một key)
2. Chia CSV thành n phần nhỏ (một phần cho mỗi API key)
3. Label lại mỗi phần song song sử dụng trường text_cleaned
4. Tự động merge tất cả các file đã label lại thành một CSV mới với hậu tố "_rechecked"

Usage:
    python youtube_crawler/recheck_labels.py \
        --csv-path <path_to_csv> \
        --api-keys-file <path_to_api_keys.txt>
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import google.generativeai as genai
except ImportError as exc:
    print(
        "Missing dependency: google-generativeai. "
        "Install it with `pip install google-generativeai` and rerun.",
        file=sys.stderr,
    )
    raise


MODEL_NAME = "gemini-2.5-pro"
MODEL_MAX_INPUT_TOKENS = 2_000_000
DEFAULT_BATCH_SIZE = 100
VALID_LABELS = ("neutral", "negative", "positive")

PROMPT_TEMPLATE = """
Role: You are an expert sentiment analysis specialist focused on entertainment content on social media, especially YouTube comments related to movies, music, artists, film production, and other entertainment topics. You are highly experienced in identifying subtle emotional nuances, including sarcasm, praise, and neutrality.

Goal: To accurately and consistently classify the sentiment of YouTube comments regarding the main topic (artist, product, film or music project), in order to create high-quality data labels for a Sentiment Analysis task. Ensure labels use only valid classes, with a confidence score reflecting certainty, to support effective AI model training.

Context: Comments are sourced from YouTube, focusing on movie and music topics. Comments may contain colloquial language, slang, emojis, or cultural elements related to entertainment. You need to consider the full context to avoid confusion, for example: neutral advertisements are considered "neutral", sarcasm or criticism is "negative", and excitement or praise is "positive". Only classify sentiment directed at the main topic, ignoring irrelevant parts.

Guidelines:
- Read the provided comment carefully, identify the main topic (artist, movie, song, etc.) the comment is addressing.
- Analyze the overall sentiment: Determine if it expresses positivity (praise, enjoyment), negativity (criticism, hatred, sarcasm), or neutrality (information, advertising, ambiguous).
- Only use these labels: {valid_labels}.
- Consider sarcasm or subtle criticism as "negative".
- Consider advertisements, neutral announcements, or ambiguous tones as "neutral".
- Excitement, praise, or enjoyment is "positive".
- Assess confidence: Assign a score from 0 to 1 based on the clarity of the sentiment (e.g., 1.0 for clear sentiment, 0.5 for ambiguous).
- If the comment is unclear or irrelevant to the topic, prioritize the "neutral" label with a low confidence score.
- Avoid adding any explanations outside the required format; focus on accuracy to ensure high data quality.

Batch instructions:
- You will receive a JSON array named "comments". Each item includes "row_index", "comment_id", "like_count", and "comment_text".
- Produce a JSON object with key "results" that contains an array of objects: {{"row_index": int, "sentiment_label": str, "sentiment_score": float}}.
- Maintain the same ordering as provided. Do not include any text outside the JSON object.

comments:
{comments_json}
"""


def read_api_keys(api_keys_file: Path) -> List[str]:
    """Read API keys from a text file (one per line)."""
    api_keys = []
    with api_keys_file.open("r", encoding="utf-8") as f:
        for line in f:
            key = line.strip()
            if key:  # Skip empty lines
                api_keys.append(key)
    
    if not api_keys:
        print(f"No API keys found in {api_keys_file}", file=sys.stderr)
        sys.exit(1)
    
    return api_keys


def configure_model(api_key: str):
    """Configure Gemini model with API key."""
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


def build_batch_prompt(items: List[Dict[str, Any]]) -> str:
    """Build prompt for batch labeling using text_cleaned."""
    payload: List[Dict[str, Any]] = []
    for item in items:
        payload.append(
            {
                "row_index": item["row_index"],
                "comment_id": item.get("comment_id", ""),
                "like_count": item.get("like_count", 0),
                "comment_text": (item.get("text_cleaned") or item.get("comment_text") or "").strip(),
            }
        )
    comments_json = json.dumps(payload, ensure_ascii=False)
    return PROMPT_TEMPLATE.format(valid_labels=VALID_LABELS, comments_json=comments_json)


def parse_batch_response(text: str) -> Dict[int, Tuple[str, float]]:
    """
    Attempt to extract {"results": [...]} JSON payload from the model's response.
    Raises ValueError if parsing fails or labels are invalid.
    """
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in response.")
    snippet = text[start : end + 1]
    data = json.loads(snippet)
    results = data.get("results")
    if not isinstance(results, list):
        raise ValueError("Response JSON missing 'results' array.")

    parsed: Dict[int, Tuple[str, float]] = {}
    for item in results:
        if not isinstance(item, dict):
            continue
        row_idx = item.get("row_index")
        if not isinstance(row_idx, int):
            continue
        label = str(item.get("sentiment_label", "")).lower()
        if label not in VALID_LABELS:
            raise ValueError(f"Invalid sentiment_label: {label}")
        score = float(item.get("sentiment_score", 0))
        score = max(0.0, min(1.0, score))
        parsed[row_idx] = (label, score)
    if not parsed:
        raise ValueError("No valid entries parsed from response.")
    return parsed


def label_batch(
    model,
    batch_items: List[Dict[str, Any]],
    max_attempts: int = 3,
) -> Dict[int, Tuple[str, float]]:
    """Label a batch of comments with retry logic."""
    prompt = build_batch_prompt(batch_items)
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = model.generate_content(prompt)
            return parse_batch_response(response.text)
        except Exception as err:
            last_error = err
            wait = 2**attempt
            print(
                f"[Attempt {attempt}/{max_attempts}] Failed to label batch: {err}. "
                f"Retrying in {wait}s...",
                file=sys.stderr,
            )
            time.sleep(wait)

    assert last_error is not None
    raise RuntimeError(f"Failed to label batch after {max_attempts} attempts.") from last_error


def normalize_like_count(raw_value: str | None) -> int:
    """Normalize like_count to integer."""
    if raw_value is None or raw_value == "":
        return 0
    try:
        return int(raw_value)
    except ValueError:
        return 0


def split_csv(
    input_csv: Path,
    num_parts: int,
    output_dir: Path | None = None,
) -> List[Path]:
    """
    Split CSV file into n parts evenly. Each part includes header.
    
    Returns list of paths to split CSV files.
    """
    if output_dir is None:
        output_dir = input_csv.parent
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Read all rows
    with input_csv.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("CSV file has no header row.", file=sys.stderr)
            sys.exit(1)
        
        rows = list(reader)
    
    total_rows = len(rows)
    if total_rows == 0:
        print("CSV file has no data rows.", file=sys.stderr)
        sys.exit(1)
    
    if num_parts < 1:
        print(f"Invalid number of parts: {num_parts}", file=sys.stderr)
        sys.exit(1)
    
    if num_parts > total_rows:
        num_parts = total_rows
        print(f"Warning: More parts than rows. Using {num_parts} parts instead.")
    
    # Calculate rows per part
    rows_per_part = total_rows // num_parts
    remainder = total_rows % num_parts
    
    split_files: List[Path] = []
    stem = input_csv.stem
    
    start_idx = 0
    for part_idx in range(num_parts):
        # Last part gets remainder
        part_size = rows_per_part + (1 if part_idx < remainder else 0)
        end_idx = start_idx + part_size
        
        if part_size == 0:
            break
        
        part_rows = rows[start_idx:end_idx]
        
        # Create output filename: <stem>_part<idx+1>.csv
        part_filename = f"{stem}_part{part_idx + 1}.csv"
        part_path = output_dir / part_filename
        
        # Write part CSV with header
        with part_path.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(part_rows)
        
        split_files.append(part_path)
        print(f"Created part {part_idx + 1}/{num_parts}: {part_path.name} ({part_size} rows)")
        
        start_idx = end_idx
    
    return split_files


def label_csv_part(
    csv_path: str,
    api_key: str,
    output_path: str,
) -> Tuple[str, bool, str]:
    """
    Label a single CSV part using text_cleaned field.
    
    Returns (csv_path, success, error_message).
    """
    try:
        csv_file = Path(csv_path)
        output_file = Path(output_path)
        
        # Read CSV
        with csv_file.open("r", encoding="utf-8", newline="") as infile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames
            if not fieldnames:
                return (csv_path, False, "CSV file has no header row.")
            
            rows = list(reader)
        
        if not rows:
            return (csv_path, False, "CSV file has no data rows.")
        
        # Check if text_cleaned column exists
        if "text_cleaned" not in fieldnames:
            return (csv_path, False, "CSV file missing 'text_cleaned' column.")
        
        # Configure model
        model = configure_model(api_key)
        
        # Prepare output fieldnames (keep all original columns, update sentiment columns)
        output_fieldnames = list(fieldnames)
        if "sentiment_label" not in output_fieldnames:
            output_fieldnames.append("sentiment_label")
        if "sentiment_score" not in output_fieldnames:
            output_fieldnames.append("sentiment_score")
        
        # Write output CSV
        with output_file.open("w", encoding="utf-8", newline="") as outfile:
            writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
            writer.writeheader()
            
            total_rows = len(rows)
            for offset in range(0, total_rows, DEFAULT_BATCH_SIZE):
                batch_indices = list(range(offset, min(offset + DEFAULT_BATCH_SIZE, total_rows)))
                batch_items: List[Dict[str, Any]] = []
                pending_indices: List[int] = []
                row_outputs: List[Dict[str, Any]] = []
                
                for idx in batch_indices:
                    row = rows[idx]
                    text_cleaned = row.get("text_cleaned", "").strip()
                    
                    if not text_cleaned:
                        # Empty text_cleaned - use neutral with low score
                        output_row = dict(row)
                        output_row["sentiment_label"] = "neutral"
                        output_row["sentiment_score"] = "0.0"
                        row_outputs.append(output_row)
                        continue
                    
                    batch_items.append(
                        {
                            "row_index": idx,
                            "comment_id": row.get("comment_id", ""),
                            "like_count": normalize_like_count(row.get("like_count")),
                            "text_cleaned": text_cleaned,
                        }
                    )
                    pending_indices.append(idx)
                
                if batch_items:
                    try:
                        batch_result = label_batch(model, batch_items)
                    except Exception as err:
                        print(
                            f"[Rows {batch_indices[0] + 1}-{batch_indices[-1] + 1}] "
                            f"Batch failed: {err}",
                            file=sys.stderr,
                        )
                        batch_result = {}
                    
                    for idx in pending_indices:
                        row = rows[idx]
                        label, score = batch_result.get(idx, ("neutral", 0.0))
                        output_row = dict(row)
                        output_row["sentiment_label"] = label
                        output_row["sentiment_score"] = f"{score:.4f}"
                        row_outputs.append(output_row)
                
                if row_outputs:
                    writer.writerows(row_outputs)
                    outfile.flush()
                
                processed = offset + len(batch_indices)
                print(f"[{csv_file.name}] Labeled {processed}/{total_rows} rows...", flush=True)
        
        return (csv_path, True, "")
    
    except Exception as e:
        return (csv_path, False, str(e))


def label_all_parts_parallel(
    split_files: List[Path],
    api_keys: List[str],
    max_workers: int | None = None,
) -> Tuple[List[Path], List[str]]:
    """
    Label all split CSV files in parallel.
    
    Returns (successful_outputs, failed_inputs).
    """
    if len(split_files) != len(api_keys):
        print(
            f"Error: Number of split files ({len(split_files)}) "
            f"must match number of API keys ({len(api_keys)})",
            file=sys.stderr,
        )
        sys.exit(1)
    
    # Prepare output paths: <input_stem>_part<idx>_labeled.csv
    output_paths = []
    for split_file in split_files:
        output_stem = split_file.stem  # Already includes _part<idx>
        output_path = split_file.parent / f"{output_stem}_labeled.csv"
        output_paths.append(output_path)
    
    print(f"\nStarting parallel labeling of {len(split_files)} files...")
    print("=" * 60)
    
    successful_outputs: List[Path] = []
    failed_inputs: List[str] = []
    
    # Use ProcessPoolExecutor for true parallelism
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_info = {
            executor.submit(
                label_csv_part,
                str(split_file),
                api_key,
                str(output_path),
            ): (split_file, output_path, api_idx)
            for (split_file, output_path, api_idx) in zip(split_files, output_paths, range(len(api_keys)))
        }
        
        # Process completed tasks
        for future in as_completed(future_to_info):
            split_file, output_path, api_idx = future_to_info[future]
            
            try:
                csv_path, success, error_msg = future.result()
                
                if success:
                    print(f"✓ Completed: {split_file.name} → {output_path.name}")
                    successful_outputs.append(output_path)
                else:
                    print(
                        f"✗ Failed: {split_file.name} - {error_msg[:100]}",
                        file=sys.stderr,
                    )
                    failed_inputs.append(str(split_file))
            
            except Exception as e:
                print(
                    f"✗ Exception processing {split_file.name}: {e}",
                    file=sys.stderr,
                )
                failed_inputs.append(str(split_file))
    
    print("=" * 60)
    print(f"\nCompleted: {len(successful_outputs)}/{len(split_files)} files labeled successfully")
    
    if failed_inputs:
        print(f"Failed files: {len(failed_inputs)}", file=sys.stderr)
        for failed in failed_inputs:
            print(f"  - {failed}", file=sys.stderr)
    
    return successful_outputs, failed_inputs


def merge_labeled_files(
    main_csv: Path,
    labeled_files: List[Path],
    output_csv: Path,
) -> None:
    """
    Merge labeled CSV files back into the main CSV structure.
    Preserves all original columns and updates sentiment_label and sentiment_score.
    Uses comment_id as key to match rows between main CSV and labeled files.
    """
    # Read main CSV to get all rows
    with main_csv.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("Main CSV file has no header row.", file=sys.stderr)
            sys.exit(1)
        
        main_rows = list(reader)
    
    # Create a mapping from comment_id to sentiment data
    sentiment_map: Dict[str, Tuple[str, float]] = {}
    
    # Read all labeled files and extract sentiment data
    for labeled_file in sorted(labeled_files):  # Sort to ensure consistent order
        if not labeled_file.exists():
            print(f"Warning: Labeled file not found: {labeled_file}", file=sys.stderr)
            continue
        
        with labeled_file.open("r", encoding="utf-8", newline="") as infile:
            reader = csv.DictReader(infile)
            for row in reader:
                comment_id = row.get("comment_id", "")
                if not comment_id:
                    continue
                sentiment_label = row.get("sentiment_label", "neutral")
                sentiment_score = float(row.get("sentiment_score", 0.0))
                sentiment_map[comment_id] = (sentiment_label, sentiment_score)
    
    # Prepare output fieldnames
    output_fieldnames = list(fieldnames)
    if "sentiment_label" not in output_fieldnames:
        output_fieldnames.append("sentiment_label")
    if "sentiment_score" not in output_fieldnames:
        output_fieldnames.append("sentiment_score")
    
    # Write merged CSV
    with output_csv.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=output_fieldnames)
        writer.writeheader()
        
        matched_count = 0
        for row in main_rows:
            output_row = dict(row)
            comment_id = row.get("comment_id", "")
            
            # Update sentiment if available in labeled files
            if comment_id and comment_id in sentiment_map:
                label, score = sentiment_map[comment_id]
                output_row["sentiment_label"] = label
                output_row["sentiment_score"] = f"{score:.4f}"
                matched_count += 1
            else:
                # Keep original values if not found
                if "sentiment_label" not in output_row:
                    output_row["sentiment_label"] = "neutral"
                if "sentiment_score" not in output_row:
                    output_row["sentiment_score"] = "0.0"
            
            writer.writerow(output_row)
    
    print(f"Merged {len(main_rows)} rows into {output_csv} (matched {matched_count} rows)")


def cleanup_temp_files(split_files: List[Path], labeled_files: List[Path]) -> None:
    """Remove temporary split and labeled CSV files."""
    all_files = split_files + labeled_files
    for temp_file in all_files:
        try:
            temp_file.unlink()
            print(f"Removed temporary file: {temp_file.name}")
        except Exception as e:
            print(f"Warning: Could not remove {temp_file.name}: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Recheck labels of comments in CSV file using text_cleaned field with parallel API keys"
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        required=True,
        help="Path to the CSV file containing comments",
    )
    parser.add_argument(
        "--api-keys-file",
        type=str,
        required=True,
        help="Path to text file containing API keys (one per line)",
    )
    parser.add_argument(
        "--keep-temp",
        action="store_true",
        help="Keep temporary split files after completion",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=None,
        help="Maximum number of parallel workers (default: number of API keys)",
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    csv_path = Path(args.csv_path).expanduser().resolve()
    api_keys_file = Path(args.api_keys_file).expanduser().resolve()
    
    # Validate inputs
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    if not api_keys_file.exists():
        print(f"Error: API keys file not found: {api_keys_file}", file=sys.stderr)
        sys.exit(1)
    
    # Generate output path with "_rechecked" suffix
    output_csv = csv_path.parent / f"{csv_path.stem}_rechecked.csv"
    
    # Ensure output file doesn't overwrite input
    if output_csv == csv_path:
        output_csv = csv_path.parent / f"{csv_path.stem}_rechecked.csv"
    
    # Read API keys
    print(f"Reading API keys from: {api_keys_file}")
    api_keys = read_api_keys(api_keys_file)
    print(f"Found {len(api_keys)} API keys")
    
    # Split CSV
    print(f"\nSplitting CSV file: {csv_path}")
    split_files = split_csv(csv_path, len(api_keys))
    
    # Label all parts in parallel
    successful_outputs, failed_inputs = label_all_parts_parallel(
        split_files,
        api_keys,
        max_workers=args.max_workers,
    )
    
    if not successful_outputs:
        print("Error: No files were labeled successfully.", file=sys.stderr)
        sys.exit(1)
    
    # Merge labeled files
    print(f"\nMerging labeled files into: {output_csv}")
    merge_labeled_files(csv_path, successful_outputs, output_csv)
    
    # Clean up temporary files
    if not args.keep_temp:
        print("\nCleaning up temporary files...")
        cleanup_temp_files(split_files, successful_outputs)
    
    print(f"\n✓ Successfully created rechecked file: {output_csv}")
    print(f"  Original file preserved: {csv_path}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)
