"""
Cấu hình cho dự án Sentiment Analysis Crawler
"""

# YouTube Data API Configuration
YOUTUBE_API_KEY = "YOUR_API_KEY_HERE"  # Thay thế bằng API key thực của bạn

# Database Schema cho Comments
COMMENT_SCHEMA = {
    "comment_id": "VARCHAR(255) PRIMARY KEY",  # ID gốc từ YouTube hoặc hash tự tạo
    "post_id": "VARCHAR(255)",  # Video ID từ YouTube
    "platform": "VARCHAR(50)",  # "YouTube", "Facebook", "TikTok", etc.
    "author_name": "TEXT",  # Tên người bình luận
    "author_id": "VARCHAR(255)",  # Channel ID của người bình luận
    "comment_text": "TEXT",  # Nội dung comment (dữ liệu chính)
    "published_at": "TIMESTAMP",  # Thời gian comment được đăng
    "like_count": "INTEGER",  # Số lượt thích
    "reply_count": "INTEGER",  # Số lượt trả lời
    "sentiment_label": "VARCHAR(20)",  # positive, negative, neutral
    "sentiment_score": "FLOAT",  # Điểm tin cậy của mô hình (0-1)
    "crawled_at": "TIMESTAMP",  # Thời điểm crawl
    "is_reply": "BOOLEAN",  # True nếu là reply của comment khác
    "parent_comment_id": "VARCHAR(255)"  # ID của comment gốc (nếu là reply)
}

# Cấu hình crawler
CRAWLER_CONFIG = {
    "max_comments_per_video": 1000,  # Giới hạn số comment crawl mỗi video
    "max_replies_per_comment": 10,  # Giới hạn số reply crawl mỗi comment
    "delay_between_requests": 1,  # Delay giữa các request (giây)
    "retry_attempts": 3,  # Số lần thử lại khi gặp lỗi
}

# Cấu hình sentiment analysis
SENTIMENT_CONFIG = {
    "model_name": "vinai/phobert-base-v2",  # PhoBERT cho tiếng Việt
    "batch_size": 32,
    "max_length": 256,
    "confidence_threshold": 0.7,  # Ngưỡng tin cậy tối thiểu
}
