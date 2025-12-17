"""
Script labeling chính với batch processing và checkpoint
"""
import pandas as pd
import json
import os
import time
import random
import sys
from typing import List, Dict, Optional, Tuple
import google.generativeai as genai
from config import (
    MODEL_FAST, MODEL_PRO, CONF_FAST_ACCEPT, AUDIT_RATE,
    MARGIN_THRESHOLD, WEIGHT_FAST, WEIGHT_PRO, BATCH_SIZE,
    REQUEST_DELAY, MAX_RETRIES, RETRY_DELAY,
    CHECKPOINT_INTERVAL, CHECKPOINT_DIR, OUTPUT_DIR
)

# Fix encoding cho Windows console
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except:
        pass  # Nếu không thể reconfigure, bỏ qua

# Labels
LABELS = ["positive", "neutral", "negative"]


def init_gemini(api_key: str):
    """Khởi tạo Gemini client"""
    genai.configure(api_key=api_key)
    return genai


def create_prompt(comments: List[Dict]) -> str:
    """
    Tạo prompt cho batch comments
    
    Args:
        comments: List of dict với keys: comment_text, title_youtube, source_query
    
    Returns:
        Prompt string
    """
    prompt_parts = [
        "You are a sentiment classification system for YouTube comments.",
        "Classify each comment based on the video context into one of 3 labels:",
        "- positive: positive, praising, expressing enjoyment or satisfaction",
        "- neutral: neutral, unclear, or factual statements without clear sentiment",
        "- negative: negative, complaining, expressing dissatisfaction or criticism",
        "",
        "IMPORTANT: Consider the video context (title, source_query) when classifying.",
        "The same statement can have different sentiment depending on the context.",
        "",
        "Return a JSON array, each element with format:",
        '{"label": "...", "confidence": {"positive": x, "neutral": y, "negative": z}}',
        "Where confidence values are numbers from 0.0 to 1.0, and they sum to 1.0",
        "",
        "=== COMMENTS ===",
    ]
    
    for i, comment in enumerate(comments, 1):
        prompt_parts.append(f"\n--- Comment {i} ---")
        prompt_parts.append(f"Comment: {comment['comment_text']}")
        prompt_parts.append(f"Video Title: {comment.get('title_youtube', 'N/A')}")
        prompt_parts.append(f"Context: {comment.get('source_query', 'N/A')}")
    
    prompt_parts.append("\nReturn a JSON array with results for each comment in order.")
    
    return "\n".join(prompt_parts)


def parse_model_response(response_text: str, num_comments: int) -> List[Dict]:
    """
    Parse response từ model thành list of results
    
    Returns:
        List of dict với keys: label, confidence
    """
    try:
        # Tìm JSON trong response
        response_text = response_text.strip()
        
        # Loại bỏ markdown code blocks nếu có
        if "```json" in response_text:
            response_text = response_text.split("```json")[1].split("```")[0]
        elif "```" in response_text:
            response_text = response_text.split("```")[1].split("```")[0]
        
        # Parse JSON
        results = json.loads(response_text)
        
        # Đảm bảo là list
        if not isinstance(results, list):
            results = [results]
        
        # Validate và normalize
        parsed_results = []
        for i, result in enumerate(results[:num_comments]):
            if not isinstance(result, dict):
                parsed_results.append({
                    "label": "error",
                    "confidence": {label: 0.0 for label in LABELS}
                })
                continue
            
            label = result.get("label", "").lower()
            # Convert "irrelevant" to "neutral" if model returns it
            if label == "irrelevant":
                label = "neutral"
            if label not in LABELS:
                label = "error"
            
            confidence = result.get("confidence", {})
            # Normalize confidence
            conf_dict = {}
            total = 0.0
            for lab in LABELS:
                val = float(confidence.get(lab, 0.0))
                conf_dict[lab] = val
                total += val
            
            # Normalize về tổng = 1.0
            if total > 0:
                for lab in LABELS:
                    conf_dict[lab] /= total
            else:
                # Nếu không có confidence, phân đều (3 labels)
                for lab in LABELS:
                    conf_dict[lab] = 1.0 / len(LABELS)
            
            parsed_results.append({
                "label": label,
                "confidence": conf_dict
            })
        
        # Đảm bảo đủ số lượng
        while len(parsed_results) < num_comments:
            parsed_results.append({
                "label": "error",
                "confidence": {label: 1.0 / len(LABELS) for label in LABELS}
            })
        
        return parsed_results[:num_comments]
    
    except Exception as e:
        print(f"  [WARNING] Loi parse response: {e}")
        # Trả về error results
        return [{
            "label": "error",
            "confidence": {label: 1.0 / len(LABELS) for label in LABELS}
        } for _ in range(num_comments)]


def call_model_batch(model_name: str, comments: List[Dict], genai_client) -> List[Dict]:
    """
    Gọi model với batch comments
    
    Args:
        model_name: Tên model
        comments: List of comments
        genai_client: Gemini client
    
    Returns:
        List of results
    """
    prompt = create_prompt(comments)
    
    for attempt in range(MAX_RETRIES):
        try:
            model = genai_client.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            response_text = response.text
            
            results = parse_model_response(response_text, len(comments))
            return results
        
        except Exception as e:
            print(f"  [WARNING] Loi request (attempt {attempt + 1}/{MAX_RETRIES}): {e}")
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY)
            else:
                # Trả về error results
                return [{
                    "label": "error",
                    "confidence": {label: 1.0 / len(LABELS) for label in LABELS}
                } for _ in range(len(comments))]


def weighted_soft_voting(fast_results: List[Dict], pro_results: List[Dict]) -> List[Tuple[str, float, str]]:
    """
    Weighted soft voting cho batch
    
    Returns:
        List of (label, margin, strategy)
    """
    final_results = []
    
    for fast_res, pro_res in zip(fast_results, pro_results):
        # Tính weighted scores
        scores = {label: 0.0 for label in LABELS}
        total_weight = 0.0
        
        # Fast model
        if fast_res["label"] != "error":
            for label in LABELS:
                scores[label] += fast_res["confidence"][label] * WEIGHT_FAST
            total_weight += WEIGHT_FAST
        
        # Pro model
        if pro_res["label"] != "error":
            for label in LABELS:
                scores[label] += pro_res["confidence"][label] * WEIGHT_PRO
            total_weight += WEIGHT_PRO
        
        # Normalize
        if total_weight > 0:
            for label in LABELS:
                scores[label] /= total_weight
        
        # Tìm max và 2nd max
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        s_max = sorted_scores[0][1]
        s_2nd = sorted_scores[1][1] if len(sorted_scores) > 1 else 0.0
        margin = s_max - s_2nd
        
        # Quyết định
        final_label = sorted_scores[0][0]
        if margin >= MARGIN_THRESHOLD:
            strategy = "soft_voting"
        else:
            strategy = "human_review"
            final_label = None  # Cần human review
        
        final_results.append((final_label, margin, strategy))
    
    return final_results


def process_batch(comments_df: pd.DataFrame, start_idx: int, api_key: str) -> List[Dict]:
    """
    Xử lý một batch comments
    
    Args:
        comments_df: DataFrame chứa comments
        start_idx: Index bắt đầu
        api_key: API key
    
    Returns:
        List of dict với kết quả labeling cho từng comment
    """
    end_idx = min(start_idx + BATCH_SIZE, len(comments_df))
    batch_df = comments_df.iloc[start_idx:end_idx].copy()
    
    # Chuẩn bị data cho prompt
    comments_data = []
    for _, row in batch_df.iterrows():
        comments_data.append({
            "comment_text": str(row["comment_text"]),
            "title_youtube": str(row.get("title_youtube", "")),
            "source_query": str(row.get("source_query", ""))
        })
    
    # Bước 1: Fast Model
    genai_client = init_gemini(api_key)
    fast_results = call_model_batch(MODEL_FAST, comments_data, genai_client)
    time.sleep(REQUEST_DELAY)
    
    # Chuẩn bị kết quả
    results = []
    need_pro_model = []
    need_pro_indices = []
    
    for i, fast_res in enumerate(fast_results):
        label = fast_res["label"]
        confidence = fast_res["confidence"].get(label, 0.0)
        
        # Check Fast Accept
        is_audit = random.random() < AUDIT_RATE
        can_fast_accept = confidence >= CONF_FAST_ACCEPT and not is_audit
        
        if can_fast_accept:
            results.append({
                "final_label": label,
                "strategy": "fast_accept",
                "margin": None
            })
            need_pro_model.append(None)
        else:
            # Cần Pro model
            need_pro_model.append(fast_res)
            need_pro_indices.append(i)
            results.append(None)  # Placeholder
    
    # Bước 2: Pro Model (nếu cần)
    if need_pro_indices:
        pro_comments = [comments_data[i] for i in need_pro_indices]
        pro_results = call_model_batch(MODEL_PRO, pro_comments, genai_client)
        time.sleep(REQUEST_DELAY)
        
        # Xử lý kết quả Pro
        pro_idx = 0
        for i in need_pro_indices:
            fast_res = need_pro_model[i]
            pro_res = pro_results[pro_idx]
            pro_idx += 1
            
            # Check Agreement
            if fast_res["label"] == pro_res["label"] and fast_res["label"] != "error":
                results[i] = {
                    "final_label": fast_res["label"],
                    "strategy": "agreement",
                    "margin": None
                }
            else:
                # Weighted Soft Voting
                voting_results = weighted_soft_voting([fast_res], [pro_res])
                final_label, margin, strategy = voting_results[0]
                
                results[i] = {
                    "final_label": final_label,
                    "strategy": strategy,
                    "margin": margin if margin is not None else None
                }
    
    return results


def load_checkpoint(checkpoint_file: str) -> int:
    """Load checkpoint, trả về index tiếp theo cần xử lý"""
    if os.path.exists(checkpoint_file):
        try:
            with open(checkpoint_file, 'r') as f:
                data = json.load(f)
                return data.get("last_processed_idx", 0) + 1
        except:
            return 0
    return 0


def save_checkpoint(checkpoint_file: str, last_idx: int, results_df: pd.DataFrame):
    """Lưu checkpoint"""
    os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
    
    checkpoint_data = {
        "last_processed_idx": last_idx,
        "timestamp": time.time()
    }
    
    with open(checkpoint_file, 'w') as f:
        json.dump(checkpoint_data, f)
    
    # Lưu kết quả tạm thời
    results_file = checkpoint_file.replace(".json", "_results.csv")
    results_df.to_csv(results_file, index=False)


def main(input_file: str, api_key: str, part_num: int):
    """
    Main function
    
    Args:
        input_file: File CSV input
        api_key: Gemini API key
        part_num: Số thứ tự phần (1-5)
    """
    print(f"\n{'='*60}")
    print(f"[START] Bat dau labeling - Part {part_num}")
    print(f"{'='*60}")
    
    # Đọc data
    print(f"[READ] Dang doc {input_file}...")
    data = pd.read_csv(input_file)
    print(f"[OK] Da doc {len(data)} comments")
    
    # Thêm columns cho kết quả
    if "final_label" not in data.columns:
        data["final_label"] = None
    if "strategy" not in data.columns:
        data["strategy"] = None
    if "margin" not in data.columns:
        data["margin"] = None
    
    # Checkpoint
    checkpoint_file = os.path.join(CHECKPOINT_DIR, f"checkpoint_part_{part_num}.json")
    start_idx = load_checkpoint(checkpoint_file)
    
    if start_idx > 0:
        print(f"[RESUME] Resume tu checkpoint: index {start_idx}")
    else:
        print(f"[NEW] Bat dau tu dau")
    
    # Output file
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_file = os.path.join(OUTPUT_DIR, f"labeled_part_{part_num}.csv")
    
    # Xử lý theo batch
    total_batches = (len(data) - start_idx + BATCH_SIZE - 1) // BATCH_SIZE
    
    for batch_num in range(total_batches):
        current_idx = start_idx + batch_num * BATCH_SIZE
        
        if current_idx >= len(data):
            break
        
        print(f"\n[BATCH] Batch {batch_num + 1}/{total_batches} (idx {current_idx}-{min(current_idx + BATCH_SIZE - 1, len(data) - 1)})")
        
        try:
            # Xử lý batch
            batch_results = process_batch(data, current_idx, api_key)
            
            # Cập nhật vào data
            for i, result in enumerate(batch_results):
                orig_idx = current_idx + i
                if orig_idx < len(data) and result:
                    data.iloc[orig_idx, data.columns.get_loc("final_label")] = result["final_label"]
                    data.iloc[orig_idx, data.columns.get_loc("strategy")] = result["strategy"]
                    if result["margin"] is not None:
                        data.iloc[orig_idx, data.columns.get_loc("margin")] = result["margin"]
            
            # Lưu checkpoint định kỳ
            if (batch_num + 1) % (CHECKPOINT_INTERVAL // BATCH_SIZE) == 0 or batch_num == total_batches - 1:
                save_checkpoint(checkpoint_file, current_idx + len(batch_results) - 1, data)
                data.to_csv(output_file, index=False)
                print(f"  [SAVE] Da luu checkpoint va output")
        
        except Exception as e:
            print(f"  [ERROR] Loi xu ly batch: {e}")
            # Lưu checkpoint trước khi dừng
            save_checkpoint(checkpoint_file, current_idx - 1, data)
            raise
    
    # Lưu kết quả cuối cùng
    data.to_csv(output_file, index=False)
    print(f"\n[SUCCESS] Hoan thanh! Ket qua da luu tai: {output_file}")
    
    # Xóa checkpoint khi hoàn thành
    if os.path.exists(checkpoint_file):
        os.remove(checkpoint_file)
        print(f"[CLEAN] Da xoa checkpoint")


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 4:
        print("Usage: python labeler.py <input_file> <api_key> <part_num>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    api_key = sys.argv[2]
    part_num = int(sys.argv[3])
    
    main(input_file, api_key, part_num)

