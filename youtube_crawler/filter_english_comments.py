"""
Utility script to filter out non-English YouTube comments from a CSV file.
Prompts the user for required inputs via the console instead of CLI arguments.
"""

import os
from typing import Optional, Tuple

import pandas as pd

try:
    from langdetect import DetectorFactory, LangDetectException, detect_langs
except ImportError as exc:
    raise ImportError(
        "Missing dependency 'langdetect'. Install it with 'pip install langdetect'."
    ) from exc

from logger_config import get_crawler_logger

logger = get_crawler_logger()
DetectorFactory.seed = 42


def is_english_text(text: str, min_probability: float = 0.9) -> bool:
    """
    Determine whether the provided text is English based on language detection probability.

    Args:
        text (str): The text to evaluate.
        min_probability (float): Minimum probability required to classify as English.

    Returns:
        bool: True if text is detected as English, False otherwise.
    """
    if not text or not text.strip():
        return False

    try:
        detections = detect_langs(text)
    except LangDetectException:
        return False

    for detection in detections:
        if detection.lang == "en" and detection.prob >= min_probability:
            return True
    return False


def filter_english_comments(
    input_csv: str,
    output_csv: Optional[str] = None,
    text_column: str = "comment_text",
    min_probability: float = 0.9,
) -> str:
    """
    Filter a CSV file, keeping only rows where the comment text is detected as English.

    Args:
        input_csv (str): Path to the input CSV file.
        output_csv (Optional[str]): Desired path for the filtered CSV. If None,
            "_en" is appended before the file extension of the input file.
        text_column (str): Name of the column containing comment text.
        min_probability (float): Minimum probability threshold for English detection.

    Returns:
        str: Path to the saved filtered CSV file.
    """
    if not os.path.isfile(input_csv):
        raise FileNotFoundError(f"Input CSV does not exist: {input_csv}")

    df = pd.read_csv(input_csv)

    if text_column not in df.columns:
        raise ValueError(f"Column '{text_column}' not found in the CSV file.")

    logger.info(
        "Filtering comments in '%s' by English language with min_probability=%.2f",
        input_csv,
        min_probability,
    )

    english_mask = df[text_column].astype(str).apply(
        lambda text: is_english_text(text, min_probability=min_probability)
    )
    filtered_df = df[english_mask].reset_index(drop=True)

    if output_csv is None:
        base, _ = os.path.splitext(input_csv)
        output_csv = f"{base}_filtered.csv"

    filtered_df.to_csv(output_csv, index=False, encoding="utf-8")
    logger.info(
        "Saved %d English comments (from %d rows) to '%s'.",
        len(filtered_df),
        len(df),
        output_csv,
    )
    return output_csv


def summarize_filtered_data(df: pd.DataFrame, like_column: str = "like_count") -> None:
    """
    Print quick statistics about the filtered dataset without plotting charts.

    Args:
        df (pd.DataFrame): Filtered comments dataframe.
        like_column (str): Column name containing like counts.
    """
    total_samples = len(df)

    print("\n📊 Quick dataset overview:")
    print(f"   • Samples (rows): {total_samples}")

    if like_column in df.columns:
        like_series = pd.to_numeric(df[like_column], errors="coerce")
        valid_likes = like_series.dropna()
        if not valid_likes.empty:
            print("   • Likes stats:")
            print(
                f"       - Mean: {valid_likes.mean():.2f}, Median: {valid_likes.median():.2f}, "
                f"Max: {valid_likes.max():.0f}"
            )
        else:
            print(f"   • Likes stats: No numeric data found in '{like_column}'.")
    else:
        print(f"   • Likes stats: Column '{like_column}' not found.")


def prompt_user_inputs() -> Tuple[str, Optional[str], str, str, float]:
    """
    Collect required inputs from the console.

    Returns:
        Tuple containing input_csv, output_csv, text_column, like_column, min_probability.
    """
    input_csv = input("Nhập đường dẫn tới file CSV: ").strip()
    if not input_csv:
        raise ValueError("Đường dẫn file CSV không được để trống.")

    output_csv = input(
        "Nhập đường dẫn file output (Enter để tự động đặt tên): "
    ).strip()
    output_csv = output_csv or None

    text_column = (
        input("Tên cột chứa comment_text (mặc định: comment_text): ").strip()
        or "comment_text"
    )

    like_column = (
        input("Tên cột chứa like_count (mặc định: like_count): ").strip()
        or "like_count"
    )

    min_prob_input = (
        input("Ngưỡng xác suất tối thiểu cho tiếng Anh (mặc định: 0.9): ").strip()
    )
    if min_prob_input:
        try:
            min_probability = float(min_prob_input)
        except ValueError as exc:
            raise ValueError("Ngưỡng xác suất phải là số thực.") from exc
    else:
        min_probability = 0.9

    return input_csv, output_csv, text_column, like_column, min_probability


def main():
    try:
        (
            input_csv,
            output_csv,
            text_column,
            like_column,
            min_probability,
        ) = prompt_user_inputs()

        output_path = filter_english_comments(
            input_csv=input_csv,
            output_csv=output_csv,
            text_column=text_column,
            min_probability=min_probability,
        )

        filtered_df = pd.read_csv(output_path)
        summarize_filtered_data(filtered_df, like_column=like_column)

        print(f"✅ Saved filtered comments to: {output_path}")
    except Exception as exc:
        logger.exception("Failed to filter English comments.")
        print(f"❌ Error: {exc}")


if __name__ == "__main__":
    main()

