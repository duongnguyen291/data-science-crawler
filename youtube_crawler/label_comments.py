#!/usr/bin/env python3
"""
Label YouTube comments in a CSV file using Google Gemini.

Usage:
    python youtube_crawler/label_comments.py

The script will prompt for:
    1. Path to the CSV file containing comments (see sample structure in
       `raw_comments_20251116_214218.csv`).
    2. Gemini API key (entered directly via the console input).
    3. Row range [l, r] to label (defaults to the entire file if blank).
    4. Optional output path (defaults to `<input_stem>_l<l>_r<r>_labeled.csv` if blank).

Only the columns `comment_id`, `like_count`, and `comment_text` are sent to Gemini.
Each labeled row receives a `sentiment_label` (neutral/negative/positive) and
`sentiment_score` (float 0-1). Existing values in those columns are overwritten.
You can specify a subset range of rows to label. Labeled samples are appended to
an output CSV incrementally after each batch so progress persists automatically.
"""

from __future__ import annotations

import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Tuple

try:
    import google.generativeai as genai
except ImportError as exc:  # pragma: no cover - guidance for setup issues
    print(
        "Missing dependency: google-generativeai. "
        "Install it with `pip install google-generativeai` and rerun.",
        file=sys.stderr,
    )
    raise


MODEL_NAME = "gemini-2.5-pro"
MODEL_MAX_INPUT_TOKENS = 2_000_000  # per Gemini 2.5 Pro public specs
DEFAULT_BATCH_SIZE = 100
VALID_LABELS = ("neutral", "negative", "positive")

def ask_csv_path() -> Path:
    raw_path = input("Enter the absolute path to the CSV file: ").strip()
    if not raw_path:
        print("A CSV path is required.", file=sys.stderr)
        sys.exit(1)
    path = Path(raw_path).expanduser().resolve()
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)
    if not path.is_file():
        print(f"Not a file: {path}", file=sys.stderr)
        sys.exit(1)
    return path


def ask_output_path(default_path: Path) -> Path:
    raw = input(f"Enter output path (leave blank to use {default_path}): ").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    print(f"Using default output path: {default_path}")
    return default_path


def ask_api_key() -> str:
    key = input("Enter Gemini API key: ").strip()
    if not key:
        print("An API key is required.", file=sys.stderr)
        sys.exit(1)
    return key


def ask_sample_range(total_rows: int) -> Tuple[int, int]:
    """
    Ask user for inclusive 1-based indices [l, r] to label. Defaults to all rows.
    """
    print(f"Dataset contains {total_rows} rows.")
    raw_l = input("Enter start index l (1-based, default 1): ").strip()
    raw_r = input(f"Enter end index r (1-based, default {total_rows}): ").strip()

    try:
        start = int(raw_l) if raw_l else 1
    except ValueError:
        print("Invalid start index.", file=sys.stderr)
        sys.exit(1)

    try:
        end = int(raw_r) if raw_r else total_rows
    except ValueError:
        print("Invalid end index.", file=sys.stderr)
        sys.exit(1)

    if start < 1 or end < start or end > total_rows:
        print("Invalid range. Ensure 1 ≤ l ≤ r ≤ total rows.", file=sys.stderr)
        sys.exit(1)

    return start, end


def configure_model(api_key: str):
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(MODEL_NAME)


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


def build_batch_prompt(items: List[Dict[str, Any]]) -> str:
    payload: List[Dict[str, Any]] = []
    for item in items:
        payload.append(
            {
                "row_index": item["row_index"],
                "comment_id": item["comment_id"],
                "like_count": item["like_count"],
                "comment_text": (item["comment_text"] or "").strip(),
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
    if raw_value is None or raw_value == "":
        return 0
    try:
        return int(raw_value)
    except ValueError:
        return 0


def process_csv(
    model, 
    input_path: Path, 
    output_path: Path | None = None,
    start_idx: int | None = None,
    end_idx: int | None = None,
) -> None:
    with input_path.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)
        if not reader.fieldnames:
            print("CSV file has no header row.", file=sys.stderr)
            sys.exit(1)

        rows = list(reader)

    total_rows = len(rows)
    if total_rows == 0:
        print("CSV file has no data rows.", file=sys.stderr)
        sys.exit(1)

    # If start_idx/end_idx not provided, use interactive mode
    # Check if we're in interactive mode (both None) or CLI mode with partial info
    if start_idx is None and end_idx is None:
        # Full interactive mode
        start_idx, end_idx = ask_sample_range(total_rows)
    else:
        # CLI mode: validate and set defaults
        if start_idx is None:
            start_idx = 1
        if end_idx is None:
            end_idx = total_rows
        if start_idx < 1 or end_idx < start_idx or end_idx > total_rows:
            print(f"Invalid range. Ensure 1 ≤ start_idx ≤ end_idx ≤ {total_rows}.", file=sys.stderr)
            sys.exit(1)
    
    target_indices = list(range(start_idx - 1, end_idx))
    
    # Set output path
    if output_path is None:
        if start_idx is not None and end_idx is not None:
            # CLI mode - auto-generate output path
            output_path = input_path.with_name(
                f"{input_path.stem}_l{start_idx}_r{end_idx}_labeled.csv"
            )
        else:
            # Interactive mode - ask user
            default_output = input_path.with_name(
                f"{input_path.stem}_l{start_idx}_r{end_idx}_labeled.csv"
            )
            output_path = ask_output_path(default_output)

    print(
        f"Loaded {total_rows} rows from {input_path}. "
        f"Labeling rows {start_idx}-{end_idx}. "
        f"Batch size: {DEFAULT_BATCH_SIZE}, model limit: {MODEL_MAX_INPUT_TOKENS} tokens."
    )

    output_fields = (
        "row_index",
        "comment_id",
        "like_count",
        "comment_text",
        "sentiment_label",
        "sentiment_score",
    )

    with output_path.open("w", encoding="utf-8", newline="") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=output_fields)
        writer.writeheader()

        total_target = len(target_indices)
        for offset in range(0, total_target, DEFAULT_BATCH_SIZE):
            batch_indices = target_indices[offset : offset + DEFAULT_BATCH_SIZE]
            batch_items: List[Dict[str, Any]] = []
            pending_indices: List[int] = []
            row_outputs: List[Dict[str, Any]] = []

            for global_idx in batch_indices:
                row = rows[global_idx]
                comment_text = row.get("comment_text", "")
                if not comment_text or not comment_text.strip():
                    row_outputs.append(
                        {
                            "row_index": global_idx + 1,
                            "comment_id": row.get("comment_id", ""),
                            "like_count": normalize_like_count(row.get("like_count")),
                            "comment_text": comment_text,
                            "sentiment_label": "neutral",
                            "sentiment_score": f"{0.0:.4f}",
                        }
                    )
                    continue

                batch_items.append(
                    {
                        "row_index": global_idx,
                        "comment_id": row.get("comment_id", ""),
                        "like_count": normalize_like_count(row.get("like_count")),
                        "comment_text": comment_text,
                    }
                )
                pending_indices.append(global_idx)

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

                for global_idx in pending_indices:
                    row = rows[global_idx]
                    label, score = batch_result.get(global_idx, ("neutral", 0.0))
                    row_outputs.append(
                        {
                            "row_index": global_idx + 1,
                            "comment_id": row.get("comment_id", ""),
                            "like_count": normalize_like_count(row.get("like_count")),
                            "comment_text": row.get("comment_text", ""),
                            "sentiment_label": label,
                            "sentiment_score": f"{score:.4f}",
                        }
                    )

            if row_outputs:
                # maintain ordering by original indices
                row_outputs.sort(key=lambda item: item["row_index"])
                writer.writerows(row_outputs)
                outfile.flush()

            processed = offset + len(batch_indices)
            print(f"Labeled {processed}/{total_target} target rows...")

    print(f"Saved labeled data to {output_path}")


def main() -> None:
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Label YouTube comments in a CSV file using Google Gemini"
    )
    parser.add_argument(
        "--csv-path",
        type=str,
        help="Path to the CSV file containing comments",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Gemini API key",
    )
    parser.add_argument(
        "--output-path",
        type=str,
        help="Path to save labeled output CSV (default: auto-generated)",
    )
    parser.add_argument(
        "--start-idx",
        type=int,
        help="Start index (1-based, inclusive). Defaults to 1 if not specified.",
    )
    parser.add_argument(
        "--end-idx",
        type=int,
        help="End index (1-based, inclusive). Defaults to last row if not specified.",
    )
    
    args = parser.parse_args()
    
    # Interactive mode if no arguments provided
    if args.csv_path is None:
        csv_path = ask_csv_path()
        api_key = ask_api_key()
        model = configure_model(api_key)
        process_csv(model, csv_path)
    else:
        # CLI mode
        csv_path = Path(args.csv_path).expanduser().resolve()
        if not csv_path.exists():
            print(f"File not found: {csv_path}", file=sys.stderr)
            sys.exit(1)
        
        if args.api_key is None:
            print("--api-key is required when using --csv-path", file=sys.stderr)
            sys.exit(1)
        
        api_key = args.api_key.strip()
        model = configure_model(api_key)
        
        output_path = None
        if args.output_path:
            output_path = Path(args.output_path).expanduser().resolve()
        
        # Default to full file if range not specified
        # Pass None for start_idx/end_idx if not specified to trigger full file labeling
        start_idx = args.start_idx if args.start_idx is not None else 1
        end_idx = args.end_idx  # Keep None if not specified
        
        process_csv(model, csv_path, output_path, start_idx, end_idx)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user.", file=sys.stderr)

