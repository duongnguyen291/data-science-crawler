# Sentiment Analysis on Social Media Comments via Web Crawling

Dự án phân tích cảm xúc (sentiment analysis) trên comments từ các nền tảng mạng xã hội thông qua web crawling.

## 🎯 Mục tiêu dự án

- Crawl comments từ các nền tảng mạng xã hội (YouTube, Facebook, TikTok, Instagram)
- Tự động phân loại cảm xúc: positive, negative, neutral
- Tổng hợp kết quả để đánh giá phản ứng công chúng

## 📋 Tính năng hiện tại

### ✅ Đã hoàn thành
- [x] **YouTube Comment Crawler** - Sử dụng YouTube Data API v3
- [x] **Threads Scraper** - Crawl dữ liệu từ Threads by Meta (NEW! 🎉)
  - Scrape thread (post) với replies
  - Scrape profile với threads gần đây
  - So sánh nhiều users
  - Phân tích engagement chi tiết
  - Export JSON/CSV/Excel
- [x] **Twitter Entertainment Crawler** - Sử dụng snscrape (NEW! 🔥)
  - Scrape tweets về films và music
  - Chỉ lấy English tweets
  - Tự động phân loại film/music
  - Extract engagement metrics (likes, retweets, replies)
  - Filter by date range, keywords, users
  - Tích hợp data cleaning
  - Export CSV/JSON
- [x] **Top Comments Feature** - Lấy comments có lượt like cao nhất
- [x] **Multiple Ordering Options** - Sắp xếp theo thời gian, relevance
- [x] **Data Schema** - Cấu trúc dữ liệu chuẩn hóa
- [x] **Data Cleaning** - Làm sạch và chuẩn hóa dữ liệu
- [x] **Language Detection** - Phát hiện ngôn ngữ (Tiếng Việt/Tiếng Anh)
- [x] **Export Data** - Xuất dữ liệu CSV/JSON/Excel

### 🚧 Đang phát triển
- [ ] **Sentiment Analysis Models** - PhoBERT, BERT, etc.
- [ ] **Visualization Dashboard** - Streamlit/Flask
- [ ] **Multi-platform Support** - Facebook, TikTok, Instagram (Threads ✅)
- [ ] **Database Integration** - SQLite/PostgreSQL

## 🚀 Cài đặt

### 1. Clone repository
```bash
git clone <repository-url>
cd data-science-crawler
```

### 2. Chọn Python Version

⚠️ **Quan trọng**: `snscrape` yêu cầu **Python 3.11 hoặc thấp hơn** (không tương thích Python 3.12+)

#### **Option A: Sử dụng Python 3.11 (Khuyến nghị)**

```bash
# Kiểm tra Python 3.11 có sẵn không
python3.11 --version

# Nếu chưa có, cài Python 3.11:
# macOS (Homebrew):
brew install python@3.11

# Ubuntu/Debian:
sudo apt-get install python3.11 python3.11-venv python3.11-dev

# Sau đó chạy setup với Python 3.11:
bash setup_py311.sh
```

#### **Option B: Sử dụng Python 3.12+ với Fork**

Nếu muốn dùng Python 3.12+, cần dùng fork của snscrape:

```bash
pip install git+https://github.com/JustAnotherArchivist/snscrape.git
```

### 3. Cài đặt uv (nếu chưa có)

**uv** là package manager Python nhanh, được viết bằng Rust (optional nhưng khuyến nghị).

```bash
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Hoặc dùng pip
pip install uv

# Hoặc dùng pipx
pipx install uv

# Hoặc dùng homebrew (macOS)
brew install uv
```

### 4. Tạo virtual environment và cài dependencies

#### Cách 1: Sử dụng setup script với Python 3.11 (Khuyến nghị cho snscrape)

```bash
# macOS/Linux - Python 3.11
bash setup_py311.sh

# Hoặc setup thông thường (sẽ dùng Python hiện tại)
bash setup.sh

# Windows PowerShell
.\setup.ps1

# Windows CMD
setup.bat
```

#### Cách 2: Manual setup với Python 3.11

```bash
# Tạo virtual environment với Python 3.11
python3.11 -m venv .venv

# Hoặc dùng uv (nếu có):
uv venv --python python3.11

# Activate virtual environment
# macOS/Linux:
source .venv/bin/activate

# Windows:
# PowerShell: .\.venv\Scripts\Activate.ps1
# CMD: .venv\Scripts\activate.bat

# Verify Python version (should show 3.11.x)
python --version

# Cài dependencies
# Với uv (nhanh hơn):
uv pip install -r requirements.txt

# Hoặc với pip:
pip install --upgrade pip
pip install -r requirements.txt
```

#### Cách 3: Dùng pip (chậm hơn)

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# hoặc .venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

### 5. Cài đặt Playwright browser (cho Threads scraper)

```bash
playwright install chromium
```

### 5. Thiết lập YouTube API Key

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

## 🧵 Threads Scraper - NEW!

### Cài đặt nhanh
```bash
# Cài đặt thư viện
pip install playwright jmespath nested-lookup parsel pandas openpyxl

# Cài đặt browser
playwright install chromium
```

### Sử dụng Interactive Menu
```bash
python threads_scraper_complete.py
```

Chọn chức năng:
1. **Scrape một thread** - Lấy post và tất cả replies
2. **Scrape profile** - Lấy thông tin user và threads gần đây
3. **So sánh users** - So sánh nhiều accounts
4. **Phân tích engagement** - Phân tích metrics chi tiết

### Sử dụng trong code

```python
from threads_scraper_complete import ThreadsScraper

# Khởi tạo
scraper = ThreadsScraper(headless=True)

# Scrape profile
data = scraper.scrape_user_by_username("natgeo")
print(f"Followers: {data['user']['followers']:,}")
print(f"Threads: {len(data['threads'])}")

# Phân tích engagement
analysis = scraper.analyze_engagement(data)
print(f"Engagement rate: {analysis['avg_engagement_rate']:.4f}%")

# Lưu dữ liệu
scraper.save_to_json(data, "natgeo.json")
scraper.save_to_excel(data, "natgeo.xlsx")

# Đóng browser
scraper.close()
```

### Quick Examples
```bash
# Basic usage example
python threads_scraper_complete.py 2

# Analysis example
python threads_scraper_complete.py 3
```

### Tính năng
- ✅ Scrape thread (post) với replies
- ✅ Scrape user profile với threads
- ✅ So sánh nhiều users
- ✅ Phân tích engagement (likes, engagement rate, video performance)
- ✅ Export JSON, CSV, Excel
- ✅ Retry logic với exponential backoff
- ✅ Logging chi tiết

### Use Cases
- 📊 Market research và competitor analysis
- 📈 Brand monitoring và sentiment tracking
- 🎯 Influencer analysis
- 📱 Content performance analysis
- 🔍 Social listening

## 🐦 Twitter Entertainment Crawler - NEW! 🔥

### Giới thiệu

Crawler chuyên dụng để thu thập dữ liệu Twitter/X cho bài toán **sentiment analysis trên English social media comments về entertainment (films/music)**.

### Cài đặt

```bash
# Cài đặt snscrape
pip install snscrape

# Hoặc cài tất cả dependencies
pip install -r requirements.txt
```

### Tính năng

✅ **Scrape tweets về films và music**
- Tự động tìm tweets về movies và music
- Filter chỉ English tweets
- Tự động phân loại film/music

✅ **Nhiều chế độ search**
- By keywords/hashtags
- By user
- By date range
- Film tweets riêng
- Music tweets riêng
- All entertainment tweets

✅ **Dữ liệu phù hợp cho sentiment analysis**
- Text content (cleaned)
- Engagement metrics (likes, retweets, replies)
- Metadata (hashtags, mentions, URLs)
- Entertainment category (film/music)
- User info (verified, followers)
- Language detection (English only)

✅ **Tích hợp data cleaning**
- Auto-clean text
- Remove URLs, mentions (optional)
- Language detection
- Validation

### Sử dụng Interactive Menu

```bash
python twitter_entertainment_crawler.py
```

**Menu options:**
1. Scrape Film Tweets
2. Scrape Music Tweets
3. Scrape All Entertainment (Film + Music)
4. Scrape by Keywords (Custom)
5. Scrape by User

### Sử dụng trong Python Code

```python
from twitter_entertainment_crawler import TwitterEntertainmentCrawler

crawler = TwitterEntertainmentCrawler()

# Scrape film tweets
film_tweets = crawler.scrape_film_tweets(max_tweets=500)

# Scrape music tweets
music_tweets = crawler.scrape_music_tweets(max_tweets=500)

# Scrape by keywords
tweets = crawler.scrape_by_keywords(
    keywords=['#movie', '#film', 'movie review'],
    max_tweets=1000,
    category='film'  # or 'music'
)

# Scrape from user
tweets = crawler.scrape_by_user(
    username='netflix',
    max_tweets=200,
    category='film'
)

# Clean and save
saved_files = crawler.clean_and_save(
    tweets,
    filename="film_tweets",
    clean_data=True,
    save_format='both'  # 'csv', 'json', or 'both'
)

# Get statistics
stats = crawler.get_stats(tweets)
print(f"Total tweets: {stats['total_tweets']}")
print(f"Avg likes: {stats['avg_likes']:.1f}")
```

### Data Schema

```python
{
    'comment_id': 'tweet_id',
    'post_id': 'tweet_id',
    'platform': 'Twitter',
    'author_name': 'username',
    'author_id': 'user_id',
    'comment_text': 'tweet_content',
    'published_at': 'timestamp',
    'like_count': 'integer',
    'retweet_count': 'integer',
    'reply_count': 'integer',
    'quote_count': 'integer',
    'sentiment_label': None,  # To be filled
    'sentiment_score': None,  # To be filled
    'language': 'en',
    'entertainment_category': 'film' or 'music',
    'hashtags': 'JSON array',
    'mentions': 'JSON array',
    'urls': 'JSON array',
    'media_type': 'photo' or 'video' or None,
    'is_reply': 'boolean',
    'parent_comment_id': 'parent_tweet_id',
    'user_verified': 'boolean',
    'user_followers': 'integer',
    'tweet_id': 'tweet_id',
    'crawled_at': 'timestamp'
}
```

### Quick Test

```bash
python test_twitter_crawler.py
```

### Lưu ý

⚠️ **snscrape không cần API key** - Hoạt động như Twitter search công khai

⚠️ **Rate Limiting** - Có thể bị rate limit nếu scrape quá nhanh

⚠️ **Terms of Service** - Tuân thủ Twitter Terms of Service

⚠️ **Chỉ English** - Crawler tự động filter chỉ English tweets

### Use Cases

- 📊 Sentiment analysis trên film reviews
- 🎵 Sentiment analysis trên music discussions
- 📈 Track public opinion về movies/music
- 🔍 Research entertainment industry trends
- 💬 Analyze user engagement với entertainment content

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết.

## 📞 Liên hệ

- **Email**: your-email@example.com
- **GitHub**: [your-github-username](https://github.com/your-username)

---

**Lưu ý**: Dự án này chỉ dành cho mục đích học tập và nghiên cứu. Vui lòng tuân thủ Terms of Service của các nền tảng mạng xã hội.
