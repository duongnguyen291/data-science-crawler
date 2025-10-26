# Sentiment Analysis on Social Media Comments via Web Crawling

Dự án phân tích cảm xúc (sentiment analysis) trên comments từ các nền tảng mạng xã hội thông qua web crawling.

## 🎯 Mục tiêu dự án

- Crawl comments từ các nền tảng mạng xã hội (YouTube, Facebook, TikTok, Instagram)
- Tự động phân loại cảm xúc: positive, negative, neutral
- Tổng hợp kết quả để đánh giá phản ứng công chúng

## 📋 Tính năng hiện tại

### ✅ Đã hoàn thành
- [x] **YouTube Comment Crawler** - Sử dụng YouTube Data API v3
- [x] **Top Comments Feature** - Lấy comments có lượt like cao nhất
- [x] **Multiple Ordering Options** - Sắp xếp theo thời gian, relevance
- [x] **Data Schema** - Cấu trúc dữ liệu chuẩn hóa
- [x] **Data Cleaning** - Làm sạch và chuẩn hóa dữ liệu
- [x] **Language Detection** - Phát hiện ngôn ngữ (Tiếng Việt/Tiếng Anh)
- [x] **Export Data** - Xuất dữ liệu CSV/JSON

### 🚧 Đang phát triển
- [ ] **Sentiment Analysis Models** - PhoBERT, BERT, etc.
- [ ] **Visualization Dashboard** - Streamlit/Flask
- [ ] **Multi-platform Support** - Facebook, TikTok, Instagram
- [ ] **Database Integration** - SQLite/PostgreSQL

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd DataScience
```

### 2. Cài đặt dependencies
```bash
pip install -r requirements.txt
```

### 3. Thiết lập YouTube API Key

#### Bước 1: Tạo Google Cloud Project
1. Truy cập [Google Cloud Console](https://console.cloud.google.com/)
2. Tạo project mới
3. Bật "YouTube Data API v3"
4. Tạo API Key

#### Bước 2: Cấu hình API Key
```python
# Trong file youtube_crawler.py hoặc test_crawler.py
API_KEY = "YOUR_API_KEY_HERE"  # Thay thế bằng API key thực
```

## 📖 Hướng dẫn sử dụng

### 1. Sử dụng chế độ tương tác (Khuyến nghị)

```bash
python main.py
```

Chương trình sẽ hướng dẫn bạn từng bước:
- Nhập YouTube API Key
- Nhập URL video YouTube
- Chọn các tùy chọn (số lượng comments, thứ tự sắp xếp, v.v.)
- Tự động crawl, làm sạch và lưu dữ liệu

### 2. Sử dụng command line

```bash
# Crawl comments cơ bản
python main.py --api-key YOUR_API_KEY --video-url "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

# Crawl top comments có lượt like cao
python main.py --api-key YOUR_API_KEY --video-url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --min-likes 10 --max-comments 50

# Crawl comments theo relevance
python main.py --api-key YOUR_API_KEY --video-url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --order relevance

# Không làm sạch dữ liệu
python main.py --api-key YOUR_API_KEY --video-url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --no-clean

# Không lưu kết quả
python main.py --api-key YOUR_API_KEY --video-url "https://www.youtube.com/watch?v=dQw4w9WgXcQ" --no-save
```

### 3. Sử dụng trong code Python

```python
from main import YouTubeCommentAnalyzer

# Khởi tạo analyzer
analyzer = YouTubeCommentAnalyzer("YOUR_API_KEY")

# Phân tích comments
result = analyzer.analyze_comments(
    video_url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    max_comments=100,
    order='time',
    min_likes=0,
    clean_data=True,
    save_results=True
)

if result['success']:
    print(f"Crawled {result['total_comments']} comments")
    print(f"Saved files: {result['saved_files']}")
```

### 4. Test các module riêng lẻ

```bash
# Test data cleaner
python data_cleaner.py

# Test logger configuration
python logger_config.py
```

## 📊 Cấu trúc dữ liệu

### Schema Comments
```python
{
    'comment_id': 'VARCHAR(255)',      # ID gốc từ YouTube
    'post_id': 'VARCHAR(255)',         # Video ID
    'platform': 'VARCHAR(50)',         # "YouTube", "Facebook", etc.
    'author_name': 'TEXT',             # Tên người bình luận
    'author_id': 'VARCHAR(255)',       # Channel ID
    'comment_text': 'TEXT',            # Nội dung comment
    'published_at': 'TIMESTAMP',       # Thời gian đăng
    'like_count': 'INTEGER',           # Số lượt thích
    'reply_count': 'INTEGER',          # Số lượt trả lời
    'sentiment_label': 'VARCHAR(20)',  # positive/negative/neutral
    'sentiment_score': 'FLOAT',        # Điểm tin cậy (0-1)
    'crawled_at': 'TIMESTAMP',         # Thời điểm crawl
    'is_reply': 'BOOLEAN',             # Có phải reply không
    'parent_comment_id': 'VARCHAR(255)' # ID comment gốc
}
```

### Dữ liệu sau khi làm sạch
```python
{
    'comment_text_clean': 'TEXT',      # Text đã làm sạch
    'language': 'VARCHAR(10)',         # 'vi' hoặc 'en'
    'text_length': 'INTEGER',          # Độ dài text
    'word_count': 'INTEGER',           # Số từ
    'is_valid': 'BOOLEAN',             # Comment hợp lệ
    'cleaned_at': 'TIMESTAMP'          # Thời điểm làm sạch
}
```

## 🔧 Cấu hình

### YouTube API Quota
- **Miễn phí**: 10,000 units/ngày
- **1 request lấy comments**: ~1 unit
- **Khuyến nghị**: Không crawl quá 1000 comments/video

### Crawler Settings
```python
CRAWLER_CONFIG = {
    "max_comments_per_video": 1000,
    "max_replies_per_comment": 10,
    "delay_between_requests": 1,  # giây
    "retry_attempts": 3,
}
```

## 📁 Cấu trúc thư mục

```
DataScience/
├── main.py                # File chính - tổng hợp tất cả chức năng
├── youtube_crawler.py     # YouTube comment crawler
├── data_cleaner.py        # Data cleaning utilities
├── logger_config.py       # Logging configuration
├── config.py             # Configuration settings
├── requirements.txt      # Python dependencies
├── README.md            # Hướng dẫn này
└── logs/                # Log files (tự tạo)
    ├── youtube_crawler.log
    ├── data_cleaner.log
    ├── main.log
    └── test.log
```

## 🚨 Lưu ý quan trọng

### YouTube API
- ✅ **Ổn định**: Sử dụng API chính thức
- ✅ **Hợp pháp**: Được YouTube cho phép
- ⚠️ **Giới hạn**: Có quota limit
- ⚠️ **Chi phí**: Có thể phát sinh phí nếu vượt quota

### Các nền tảng khác
- ❌ **Facebook/Instagram**: Cần App Review, rất khó
- ❌ **TikTok**: Không có API công khai
- ❌ **Threads**: Không có API

### Khuyến nghị
1. **Bắt đầu với YouTube** - Dễ nhất và ổn định
2. **Test với ít comments trước** - Tránh hết quota
3. **Lưu trữ dữ liệu** - Tránh crawl lại
4. **Monitor logs** - Theo dõi lỗi và quota

## 🐛 Troubleshooting

### Lỗi thường gặp

#### 1. API Quota Exceeded
```
Error: API quota exceeded
```
**Giải pháp**: Đợi 24h hoặc nâng cấp quota

#### 2. Video Not Found
```
Error: Video not found
```
**Giải pháp**: Kiểm tra URL video có đúng không

#### 3. Invalid API Key
```
Error: Invalid API key
```
**Giải pháp**: Kiểm tra API key trong Google Cloud Console

### Debug Mode
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 📈 Kế hoạch phát triển

### Phase 1: YouTube Crawler ✅
- [x] Basic YouTube comment crawling
- [x] Top comments with highest likes
- [x] Multiple ordering options (time, relevance)
- [x] Data cleaning and validation
- [x] Export to CSV/JSON
- [x] Unified main.py interface

### Phase 2: Sentiment Analysis 🚧
- [ ] PhoBERT integration for Vietnamese
- [ ] BERT/DistilBERT for English
- [ ] Batch processing
- [ ] Confidence scoring

### Phase 3: Visualization 📊
- [ ] Streamlit dashboard
- [ ] Real-time sentiment monitoring
- [ ] Export reports

### Phase 4: Multi-platform 🌐
- [ ] Facebook Graph API integration
- [ ] TikTok unofficial API
- [ ] Instagram Basic Display API

## 🤝 Đóng góp

1. Fork repository
2. Tạo feature branch
3. Commit changes
4. Push to branch
5. Tạo Pull Request

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết.

## 📞 Liên hệ

- **Email**: your-email@example.com
- **GitHub**: [your-github-username](https://github.com/your-username)

---

**Lưu ý**: Dự án này chỉ dành cho mục đích học tập và nghiên cứu. Vui lòng tuân thủ Terms of Service của các nền tảng mạng xã hội.
