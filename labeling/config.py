"""
Config file cho labeling system
"""
import os

# Model names
# Lưu ý: Cập nhật tên model chính xác theo Gemini API
# Ví dụ: "gemini-2.0-flash-exp", "gemini-2.0-flash-thinking-exp-001", etc.
# MODEL_FAST = "gemini-2.0-flash-exp"  # Gemini Flash model (rẻ, nhanh)
# MODEL_PRO = "gemini-2.0-flash-thinking-exp-001"  # Gemini Pro model (mạnh, chính xác)
MODEL_FAST = "gemini-2.5-flash"
MODEL_PRO  = "gemini-2.5-pro"
# API Keys - sẽ được set từ environment hoặc code
# Format: API_KEY_1, API_KEY_2, ..., API_KEY_5

API_KEYS = [
    "API_KET",
    "API_KET",
    "API_KET",
    "API_KET",
    "API_KET",
]

# Thresholds
CONF_FAST_ACCEPT = 0.985  # Confidence threshold để Fast Accept
AUDIT_RATE = 0.12  # 12% audit rate (10-15%)
MARGIN_THRESHOLD = 0.2  # Margin threshold cho weighted voting

# Model weights cho weighted voting
WEIGHT_FAST = 1.0
WEIGHT_PRO = 2.0

# Batch processing
BATCH_SIZE = 5  # Số comments gửi trong 1 request

# Request settings
REQUEST_DELAY = 1.0  # Delay giữa các request (giây)
MAX_RETRIES = 3  # Số lần retry khi lỗi
RETRY_DELAY = 2.0  # Delay khi retry (giây)

# Checkpoint settings
CHECKPOINT_INTERVAL = 50  # Lưu checkpoint sau mỗi N comments
CHECKPOINT_DIR = "checkpoints"

# Output settings
OUTPUT_DIR = "labeled_output"

