# CHIẾN LƯỢC CRAWL YOUTUBE COMMENTS CHO SENTIMENT ANALYSIS
## Chủ đề: Phim ảnh và Âm nhạc

---

## 1. MỤC TIÊU DATA

### 1.1 Yêu cầu cơ bản
- **Số lượng tối thiểu**: 5,000 - 10,000 comments mỗi category (Film/Music)
- **Chất lượng**: Comments có nội dung thực (không spam, không quá ngắn)
- **Ngôn ngữ**: Ưu tiên tiếng Việt hoặc tiếng Anh (dễ train model)
- **Phân bố sentiment**: Cân bằng giữa positive, negative, neutral

### 1.2 Đặc điểm comments tốt cho sentiment analysis
- Độ dài: 10-200 từ (đủ ngữ cảnh, không quá dài)
- Có biểu cảm rõ ràng: "hay", "tệ", "tuyệt vời", "boring"
- Không phải bot/spam: có engagement (likes, replies)
- Thời gian gần đây: trong vòng 1-2 năm

---

## 2. CHIẾN LƯỢC CHỌN VIDEO

### 2.1 Tiêu chí chọn video

**A. Video về PHIM ẢNH:**
- **Loại video**:
  - Trailer chính thức (official trailers)
  - Review/phê bình phim
  - Phỏng vấn cast/đạo diễn
  - Cảnh phim hot/viral
  
- **Nguồn đáng tin cậy**:
  - Kênh phim chính thức (Warner Bros, Marvel, Universal)
  - Review channels lớn (CGV Vietnam, Metascore, RapReview)
  - Kênh giải trí Việt Nam (VieON, Galaxy Play)

- **Chọn phim đa dạng**:
  - Blockbuster vs phim độc lập
  - Phim Việt vs phim nước ngoài
  - Các thể loại: hành động, tâm lý, hài, kinh dị
  - Rating đa dạng: từ phim bom tấn đến phim thất bại

**B. Video về ÂM NHẠC:**
- **Loại video**:
  - MV chính thức (official music videos)
  - Live performance/concert
  - Lyric videos
  - Reaction videos (có nhiều sentiment)

- **Nguồn**:
  - Kênh nghệ sĩ chính thức
  - Kênh âm nhạc lớn (Zing MP3, NhacCuaTui)
  - Playlist top trending

- **Chọn nhạc đa dạng**:
  - Thể loại: Pop, Rock, Ballad, Rap, EDM
  - Ngôn ngữ: V-pop, K-pop, US-UK
  - Xu hướng: viral hits vs classic hits

### 2.2 Tiêu chí lọc video

**Metrics quan trọng:**
- View count: > 100,000 views (đảm bảo có comments)
- Comment count: > 500 comments (đủ data)
- Engagement rate: (likes + comments) / views > 1%
- Upload date: Trong vòng 2 năm (comments còn relevant)

**Tránh:**
- Video quá cũ (> 5 năm): ngôn ngữ, context khác biệt
- Video quá ít tương tác (< 100 comments)
- Video có tỷ lệ dislike cao bất thường (có thể bị raid/spam)

---

## 3. CHIẾN LƯỢC CRAWL COMMENTS

### 3.1 Cách lấy comments từ mỗi video

**Option 1: Lấy Top Comments (Recommended)**
```python
# Ưu tiên comments có engagement cao
order = 'relevance'  # Hoặc 'rating'
min_likes = 5        # Chỉ lấy comments có >= 5 likes
max_comments = 200   # Giới hạn mỗi video
```

**Lý do:**
- Comments có likes cao thường có nội dung chất lượng
- Tránh spam, bot
- Có sentiment rõ ràng (người khác đồng tình)

**Option 2: Lấy theo thời gian (cho phân tích temporal)**
```python
order = 'time'       # Mới nhất trước
max_comments = 300
```

**Kết hợp:** Lấy 100 top comments + 100 recent comments mỗi video

### 3.2 Xử lý Replies

**Chiến lược:**
- Lấy replies của top-level comments có > 10 likes
- Giới hạn 5 replies đầu tiên của mỗi comment
- Lý do: Replies thường chứa thảo luận sâu, có nhiều sentiment đối lập

### 3.3 Quota Management (YouTube API giới hạn)

**Giới hạn YouTube Data API:**
- Free tier: 10,000 units/day
- 1 request lấy comments: ~1 unit
- 1 request lấy video info: ~1 unit

**Tối ưu:**
- Crawl ~200 videos/day (mỗi video ~1-2 requests)
- Sử dụng pagination thông minh (chỉ lấy đủ)
- Cache video info để tránh request trùng
- Chạy crawl vào khung giờ thấp điểm

**Backup plan:** Nếu hết quota, nghỉ 24h hoặc dùng multiple API keys

---

## 4. LỌC VÀ LÀM SẠCH DATA

### 4.1 Loại bỏ comments không phù hợp

**Loại bỏ:**
- Comments spam: "First!", "Who's watching in 2024?", "👇👇👇"
- Comments quá ngắn: < 3 từ
- Comments chỉ có emoji/số
- Comments có URL quảng cáo
- Comments ngôn ngữ không xác định được

**Giữ lại:**
- Comments có từ khóa cảm xúc: "love", "hate", "amazing", "terrible"
- Comments có độ dài 10-200 từ
- Comments có cấu trúc câu hoàn chỉnh

### 4.2 Enrichment

**Thêm metadata:**
```python
{
    'comment_id': ...,
    'video_id': ...,
    'video_title': ...,
    'video_category': 'Film' | 'Music',  # Label manual hoặc auto
    'comment_text': ...,
    'like_count': ...,
    'reply_count': ...,
    'language': 'vi' | 'en',
    'text_length': ...,
    'has_emoji': True/False,
    'crawled_at': ...,
}
```

### 4.3 Cân bằng dataset

**Vấn đề:** Comments positive thường nhiều hơn negative (bias)

**Giải pháp:**
- Chủ động crawl video controversial (có nhiều tranh cãi)
- Crawl video có rating thấp (phim bị chê, nhạc flop)
- Oversample negative comments trong training
- Sử dụng data augmentation nếu thiếu negative samples

---

## 5. PIPELINE THỰC HIỆN

### Bước 1: Chuẩn bị danh sách video (Manual + Auto)

**Manual (khuyến nghị):**
- Tạo file `video_sources.csv`:
```csv
video_id,category,subcategory,expected_sentiment
dQw4w9WgXcQ,Music,Pop,Positive
xyz123abc,Film,Action,Mixed
```

**Auto (optional):**
- Dùng YouTube Search API: tìm video theo keyword
- Keywords: "phim hay 2024", "top MV trending", "phim review"

### Bước 2: Crawl comments

```python
# Pseudo-code
for video in video_list:
    comments = crawler.crawl_video(
        video_url=video['url'],
        max_comments=200,
        order='relevance',
        min_likes=5
    )
    
    # Lưu raw data ngay
    save_raw(comments, f"raw_{video['id']}.csv")
    
    # Rate limiting
    time.sleep(2)  # Tránh spam API
```

### Bước 3: Data cleaning

```python
cleaner = CommentDataCleaner()
cleaned_df = cleaner.clean_dataframe(raw_df)

# Lọc thêm
cleaned_df = cleaned_df[
    (cleaned_df['text_length'] >= 10) &
    (cleaned_df['text_length'] <= 1000) &
    (cleaned_df['is_valid'] == True)
]
```

### Bước 4: Labeling (cho supervised learning)

**Manual labeling (cần thiết):**
- Chọn random 1000-2000 comments
- Label sentiment: Positive (1), Negative (-1), Neutral (0)
- Tool: Label Studio, Google Sheets, hoặc custom script

**Semi-auto labeling:**
- Dùng pretrained model để label tự động
- Manual review 20% để đảm bảo chất lượng

### Bước 5: Train-Test Split

```python
from sklearn.model_selection import train_test_split

train, test = train_test_split(
    data,
    test_size=0.2,
    stratify=data['sentiment'],  # Giữ cân bằng sentiment
    random_state=42
)
```

---

## 6. KẾT QUẢ MONG ĐỢI

### Dataset cuối cùng:
- **Tổng số comments**: 10,000 - 20,000
- **Film**: 5,000 - 10,000 comments (50%)
- **Music**: 5,000 - 10,000 comments (50%)
- **Language**: 70% tiếng Việt, 30% tiếng Anh
- **Sentiment distribution**: 
  - Positive: 40-50%
  - Negative: 20-30%
  - Neutral: 20-30%

### Cấu trúc file:
```
data/youtube_sentiment/
├── raw/
│   ├── film_comments_raw.csv
│   └── music_comments_raw.csv
├── cleaned/
│   ├── film_comments_cleaned.csv
│   └── music_comments_cleaned.csv
├── labeled/
│   ├── train.csv
│   └── test.csv
└── metadata/
    └── video_sources.csv
```

---

## 7. LƯU Ý KỸ THUẬT

### 7.1 Best Practices
- **Incremental crawling**: Crawl từng đợt, lưu ngay để tránh mất data
- **Error handling**: Retry nếu API fail, log tất cả errors
- **Backup**: Lưu raw data trước khi clean
- **Version control**: Ghi timestamp, version cho mỗi dataset

### 7.2 Tránh bị ban
- Tuân thủ rate limit của YouTube API
- Delay 1-2s giữa các request
- Không crawl quá nhiều từ cùng một channel
- Sử dụng API key hợp lệ, không abuse

### 7.3 Đạo đức nghiên cứu
- Không public raw comments với username
- Anonymize author_name trước khi publish
- Chỉ dùng cho mục đích nghiên cứu
- Tuân thủ YouTube Terms of Service

---

## 8. TIMELINE ƯỚC TÍNH

**Week 1:** Setup và thu thập video sources (50-100 videos)
**Week 2-3:** Crawl comments (10,000+ comments)
**Week 4:** Data cleaning và validation
**Week 5:** Manual labeling (1000-2000 comments)
**Week 6:** Semi-auto labeling + Train-Test split

**Tổng thời gian:** 6 tuần cho dataset chất lượng

---

## 9. MỞ RỘNG (OPTIONAL)

### 9.1 Multi-platform crawling
- Kết hợp YouTube + Facebook + TikTok
- So sánh sentiment cross-platform

### 9.2 Temporal analysis
- Phân tích sentiment thay đổi theo thời gian
- VD: Sentiment trước và sau khi phim ra rạp

### 9.3 Aspect-based sentiment
- Không chỉ positive/negative
- Phân tích theo khía cạnh: diễn xuất, kịch bản, hình ảnh, âm nhạc

---

## KẾT LUẬN

Chiến lược crawl hiệu quả cần cân bằng giữa:
1. **Số lượng** (đủ data để train model)
2. **Chất lượng** (comments có sentiment rõ ràng)
3. **Đa dạng** (nhiều thể loại, sentiment)
4. **Khả thi** (tuân thủ API limit, thời gian hợp lý)

Ưu tiên chất lượng hơn số lượng. 5,000 comments chất lượng tốt hơn 50,000 comments spam.

