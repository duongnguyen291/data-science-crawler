#!/usr/bin/env python3
"""
Orchestrator script to label large CSV files in parallel using multiple API keys.

This script:
1. Reads a CSV file and a text file containing API keys (one per line)
2. Divides the CSV into n smaller files (one per API key)
3. Labels each file in parallel using the corresponding API key
4. Automatically merges all labeled files back into the main CSV

Usage:
    python youtube_crawler/label_comments_orchestrator.py \
        --csv-path <path_to_csv> \
        --api-keys-file <path_to_api_keys.txt> \
        --output-csv <path_to_output.csv>
"""

from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
from typing import List, Tuple


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
    Label a single CSV part using label_comments.py.
    
    Returns (csv_path, success, error_message).
    """
    script_path = Path(__file__).parent / "label_comments.py"
    
    cmd = [
        sys.executable,
        str(script_path),
        "--csv-path", csv_path,
        "--api-key", api_key,
        "--output-path", output_path,
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=None,  # No timeout for now
        )
        
        if result.returncode == 0:
            return (csv_path, True, "")
        else:
            error_msg = result.stderr or result.stdout or "Unknown error"
            return (csv_path, False, error_msg)
    
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


def cleanup_temp_files(split_files: List[Path]) -> None:
    """Remove temporary split CSV files."""
    for split_file in split_files:
        try:
            split_file.unlink()
            print(f"Removed temporary file: {split_file.name}")
        except Exception as e:
            print(f"Warning: Could not remove {split_file.name}: {e}", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Orchestrate parallel labeling of large CSV files using multiple API keys"
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
        "--output-csv",
        type=str,
        required=True,
        help="Path to save the final merged labeled CSV",
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
    output_csv = Path(args.output_csv).expanduser().resolve()
    
    # Validate inputs
    if not csv_path.exists():
        print(f"Error: CSV file not found: {csv_path}", file=sys.stderr)
        sys.exit(1)
    
    if not api_keys_file.exists():
        print(f"Error: API keys file not found: {api_keys_file}", file=sys.stderr)
        sys.exit(1)
    
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
    
    # Clean up temporary split files
    if not args.keep_temp:
        print("\nCleaning up temporary files...")
        cleanup_temp_files(split_files)
    
    # Merge labeled files
    print(f"\nMerging labeled files into: {output_csv}")
    
    # Build glob pattern for labeled files
    stem = csv_path.stem
    parent_dir = csv_path.parent
    labeled_pattern = str(parent_dir / f"{stem}_part*_labeled.csv")
    
    # Call merge script
    merge_script = Path(__file__).parent / "merge_labeled_comments.py"
    merge_cmd = [
        sys.executable,
        str(merge_script),
        "--main-csv", str(csv_path),
        "--labeled-pattern", labeled_pattern,
        "--output-csv", str(output_csv),
    ]
    
    print(f"Running: {' '.join(merge_cmd)}")
    merge_result = subprocess.run(merge_cmd, capture_output=True, text=True)
    
    if merge_result.returncode == 0:
        print(merge_result.stdout)
        print(f"\n✓ Successfully merged labeled data to: {output_csv}")
    else:
        print("Error merging labeled files:", file=sys.stderr)
        print(merge_result.stderr, file=sys.stderr)
        print(merge_result.stdout, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)
        sys.exit(1)

