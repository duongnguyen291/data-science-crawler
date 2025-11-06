"""
🧵 THREADS SCRAPER - All-in-One
Crawl dữ liệu từ Threads by Meta với đầy đủ tính năng

HƯỚNG DẪN NHANH:
1. Cài đặt: pip install playwright jmespath nested-lookup parsel pandas openpyxl
2. Cài đặt browser: playwright install chromium
3. Chạy: python threads_scraper_complete.py

TÍNH NĂNG:
✅ Scrape thread (post) đơn lẻ với replies
✅ Scrape profile của user với threads gần đây
✅ Scrape nhiều users và so sánh
✅ Phân tích engagement chi tiết
✅ Export ra JSON, CSV, Excel
✅ Retry logic với exponential backoff
✅ Logging chi tiết

CÁCH SỬ DỤNG:
- Chạy trực tiếp: python threads_scraper_complete.py
- Import trong code: from threads_scraper_complete import ThreadsScraper
"""

import json
import time
from typing import Dict, List, Optional
from datetime import datetime
import pandas as pd

# Import thư viện
try:
    from parsel import Selector
    from playwright.sync_api import sync_playwright, Page, Browser
    from nested_lookup import nested_lookup
    import jmespath
except ImportError as e:
    print(f"❌ Thiếu thư viện: {e}")
    print("\n📦 Cài đặt bằng lệnh:")
    print("pip install playwright jmespath nested-lookup parsel pandas openpyxl")
    print("playwright install chromium")
    exit(1)

# Logging
import logging
import os

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/threads_scraper_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ============================================================================
# PARSER FUNCTIONS - Parse JSON data từ Threads
# ============================================================================

def parse_thread(data: Dict) -> Dict:
    """Parse Threads post JSON dataset"""
    result = jmespath.search(
        """{
        text: post.caption.text,
        published_on: post.taken_at,
        id: post.id,
        pk: post.pk,
        code: post.code,
        username: post.user.username,
        user_pic: post.user.profile_pic_url,
        user_verified: post.user.is_verified,
        user_pk: post.user.pk,
        user_id: post.user.id,
        has_audio: post.has_audio,
        reply_count: view_replies_cta_string,
        like_count: post.like_count,
        images: post.carousel_media[].image_versions2.candidates[1].url,
        image_count: post.carousel_media_count,
        videos: post.video_versions[].url,
        parent_post_id: post.text_post_app_info.reply_to_author.id
    }""",
        data,
    )
    
    # Xử lý text là None
    if result["text"] is None:
        result["text"] = ""
    
    result["videos"] = list(set(result["videos"] or []))
    
    # Parse reply_count an toàn
    if result["reply_count"] and type(result["reply_count"]) != int:
        try:
            # Lấy số đầu tiên từ string (vd: "15 replies" -> 15)
            reply_text = str(result["reply_count"]).split(" ")[0]
            result["reply_count"] = int(reply_text)
        except (ValueError, IndexError, AttributeError):
            # Nếu không parse được, set về 0
            result["reply_count"] = 0
    elif not result["reply_count"]:
        result["reply_count"] = 0
    
    # Xử lý like_count là None
    if result["like_count"] is None:
        result["like_count"] = 0
    
    result["url"] = f"https://www.threads.net/@{result['username']}/post/{result['code']}"
    
    return result


def parse_profile(data: Dict) -> Dict:
    """Parse Threads profile JSON dataset"""
    result = jmespath.search(
        """{
        is_private: text_post_app_is_private,
        is_verified: is_verified,
        profile_pic: hd_profile_pic_versions[-1].url,
        username: username,
        full_name: full_name,
        bio: biography,
        bio_links: bio_links[].url,
        followers: follower_count
    }""",
        data,
    )
    
    result["url"] = f"https://www.threads.net/@{result['username']}"
    
    return result


# ============================================================================
# THREADS SCRAPER CLASS - Main scraper
# ============================================================================

class ThreadsScraper:
    """
    Threads Scraper - Crawl dữ liệu từ Threads by Meta
    
    Example:
        scraper = ThreadsScraper(headless=True)
        data = scraper.scrape_user_by_username("natgeo")
        scraper.save_to_json(data, "natgeo.json")
        scraper.close()
    """
    
    def __init__(self, headless: bool = True):
        """
        Khởi tạo scraper
        
        Args:
            headless: Chạy browser ẩn (True) hoặc hiển thị (False)
        """
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.playwright = None
        logger.info("ThreadsScraper initialized")
        
    def _start_browser(self):
        """Khởi động browser"""
        if not self.browser:
            self.playwright = sync_playwright().start()
            self.browser = self.playwright.chromium.launch(headless=self.headless)
            logger.info("Browser started")
            
    def _create_page(self) -> Page:
        """Tạo page mới với settings"""
        self._start_browser()
        context = self.browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        )
        return context.new_page()
        
    def scrape_thread(self, url: str, max_retries: int = 3) -> Dict:
        """
        Scrape một thread (post) với replies
        
        Args:
            url: URL của thread (vd: https://www.threads.net/t/C8H5FiCtESk/)
            max_retries: Số lần thử lại nếu lỗi
            
        Returns:
            Dict với keys: 'thread' (post chính), 'replies' (list replies)
        """
        logger.info(f"Scraping thread: {url}")
        
        for attempt in range(max_retries):
            try:
                page = self._create_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response and response.status == 403:
                    logger.warning(f"403 Forbidden - Retry {attempt + 1}/{max_retries}")
                    time.sleep(2 ** attempt)
                    page.close()
                    continue
                
                page.wait_for_selector("[data-pressable-container=true]", timeout=15000)
                
                # Click buttons để load tất cả replies
                try:
                    # Click "View replies" / "Show more" multiple times
                    for attempt in range(5):  # Thử click 5 lần
                        clicked = False
                        # Tìm các button có text chứa replies/more
                        selectors = [
                            'text=/View.*replies/i',
                            'text=/Show.*replies/i', 
                            'text=/View more/i',
                            'text=/Show more/i',
                            'text=/replies/i'
                        ]
                        
                        for selector in selectors:
                            try:
                                buttons = page.locator(selector).all()
                                for button in buttons:
                                    try:
                                        if button.is_visible():
                                            button.click(timeout=1000)
                                            clicked = True
                                            time.sleep(0.3)
                                    except:
                                        pass
                            except:
                                pass
                        
                        if not clicked:
                            break  # Không còn button nào để click
                        
                        time.sleep(0.5)
                    
                    logger.info(f"Finished clicking reply buttons")
                except Exception as e:
                    logger.debug(f"Click replies error: {e}")
                
                # Scroll xuống để load comments (lazy loading)
                try:
                    for _ in range(3):
                        page.evaluate("window.scrollBy(0, 1000)")
                        time.sleep(0.5)
                    # Scroll lên lại
                    page.evaluate("window.scrollTo(0, 0)")
                    time.sleep(1)
                except Exception as e:
                    logger.warning(f"Scroll error: {e}")
                
                selector = Selector(page.content())
                hidden_datasets = selector.css('script[type="application/json"][data-sjs]::text').getall()
                
                for hidden_dataset in hidden_datasets:
                    if '"ScheduledServerJS"' not in hidden_dataset or "thread_items" not in hidden_dataset:
                        continue
                        
                    data = json.loads(hidden_dataset)
                    thread_items = nested_lookup("thread_items", data)
                    
                    if not thread_items:
                        continue
                    
                    # Debug: log structure
                    logger.info(f"Found {len(thread_items)} thread_items")
                    for i, item in enumerate(thread_items):
                        logger.info(f"  thread_items[{i}] has {len(item)} threads")
                    
                    # Debug: save to file for inspection
                    if os.getenv('DEBUG_THREADS'):
                        with open('data/debug_thread_data.json', 'w', encoding='utf-8') as f:
                            json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    # Parse tất cả threads từ tất cả thread_items
                    # thread_items[0] là main post
                    # thread_items[1:] có thể là replies hoặc suggested posts
                    all_threads = []
                    main_thread = None
                    
                    for i, thread_list in enumerate(thread_items):
                        for t in thread_list:
                            parsed = parse_thread(t)
                            if i == 0:  # First item is main thread
                                main_thread = parsed
                            else:
                                all_threads.append(parsed)
                    
                    if main_thread:
                        # LẤY TẤT CẢ làm replies (trừ suggested posts rõ ràng)
                        # Vì khó phân biệt, ta sẽ lấy hết và để user filter sau
                        replies = []
                        for thread in all_threads:
                            # Bỏ qua nếu là verified account lớn (có thể là suggested)
                            # VÀ có likes cao (trending post)
                            if (thread.get('user_verified') and 
                                thread.get('like_count', 0) > 100):
                                # Có thể là suggested post, nhưng vẫn thêm vào
                                # để user có nhiều data
                                pass
                            replies.append(thread)
                        
                        page.close()
                        
                        result = {
                            "thread": main_thread,
                            "replies": replies,
                        }
                        
                        logger.info(f"Scraped thread with {len(replies)} replies")
                        logger.warning("Note: 'replies' may include suggested posts. Filter by likes/username as needed.")
                        return result
                    
                page.close()
                raise ValueError("Could not find thread data")
                
            except Exception as e:
                logger.error(f"Error (attempt {attempt + 1}): {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
                
        raise Exception(f"Failed after {max_retries} attempts")
    
    def scrape_profile(self, url: str, max_retries: int = 3, max_posts: int = 200) -> Dict:
        """
        Scrape profile của user với threads gần đây, scroll để lấy nhiều posts
        
        Args:
            url: URL profile (vd: https://www.threads.net/@natgeo)
            max_retries: Số lần thử lại
            max_posts: Số posts tối đa cần lấy (mặc định 200)
            
        Returns:
            Dict với keys: 'user' (info), 'threads' (list threads)
        """
        logger.info(f"Scraping profile: {url} (target: {max_posts} posts)")
        
        for attempt in range(max_retries):
            try:
                page = self._create_page()
                response = page.goto(url, wait_until="domcontentloaded", timeout=30000)
                
                if response and response.status == 403:
                    logger.warning(f"403 Forbidden - Retry {attempt + 1}/{max_retries}")
                    time.sleep(2 ** attempt)
                    page.close()
                    continue
                
                page.wait_for_selector("[data-pressable-container=true]", timeout=15000)
                
                # Parse initial page first
                selector = Selector(page.content())
                parsed = {"user": {}, "threads": []}
                hidden_datasets = selector.css('script[type="application/json"][data-sjs]::text').getall()
                
                for hidden_dataset in hidden_datasets:
                    if '"ScheduledServerJS"' not in hidden_dataset:
                        continue
                        
                    is_profile = 'follower_count' in hidden_dataset
                    is_threads = 'thread_items' in hidden_dataset
                    
                    if not is_profile and not is_threads:
                        continue
                    
                    data = json.loads(hidden_dataset)
                    
                    if is_profile:
                        user_data = nested_lookup('user', data)
                        if user_data:
                            parsed['user'] = parse_profile(user_data[0])
                            
                    if is_threads:
                        thread_items = nested_lookup('thread_items', data)
                        threads = [parse_thread(t) for thread in thread_items for t in thread]
                        parsed['threads'].extend(threads)
                
                logger.info(f"Initial load: {len(parsed['threads'])} posts")
                
                # Now scroll to get more posts if needed
                if len(parsed['threads']) < max_posts:
                    logger.info(f"Starting scroll to load more posts (target: {max_posts})...")
                    all_threads_ids = {t.get('id') for t in parsed['threads'] if t.get('id')}
                    no_new_posts_count = 0
                    max_no_new = 5  # Stop after 5 scrolls without new posts
                    
                    while len(all_threads_ids) < max_posts and no_new_posts_count < max_no_new:
                        selector = Selector(page.content())
                        hidden_datasets = selector.css('script[type="application/json"][data-sjs]::text').getall()
                        
                        prev_count = len(all_threads_ids)
                        
                        for hidden_dataset in hidden_datasets:
                            if '"ScheduledServerJS"' not in hidden_dataset:
                                continue
                                
                            is_profile = 'follower_count' in hidden_dataset
                            is_threads = 'thread_items' in hidden_dataset
                            
                            if not is_profile and not is_threads:
                                continue
                            
                            data = json.loads(hidden_dataset)
                            
                            if is_profile and not parsed['user']:
                                user_data = nested_lookup('user', data)
                                if user_data:
                                    parsed['user'] = parse_profile(user_data[0])
                                    
                            if is_threads:
                                thread_items = nested_lookup('thread_items', data)
                                for thread_list in thread_items:
                                    if not isinstance(thread_list, list):
                                        continue
                                    for t in thread_list:
                                        if not isinstance(t, dict):
                                            continue
                                        # Get thread ID from nested structure
                                        thread_data = t.get('thread', {})
                                        if isinstance(thread_data, dict):
                                            thread_id = thread_data.get('id')
                                        else:
                                            thread_id = t.get('id')
                                        
                                        if thread_id and thread_id not in all_threads_ids:
                                            all_threads_ids.add(thread_id)
                                            parsed['threads'].append(parse_thread(t))
                        
                        # Check if got new posts
                        new_count = len(all_threads_ids)
                        if new_count == prev_count:
                            no_new_posts_count += 1
                            logger.debug(f"No new posts found ({no_new_posts_count}/{max_no_new})")
                        else:
                            no_new_posts_count = 0
                            logger.info(f"Loaded {new_count} posts so far...")
                        
                        # Stop if reached target or no more posts
                        if new_count >= max_posts:
                            logger.info(f"Reached target: {new_count} posts")
                            break
                        
                        if no_new_posts_count >= max_no_new:
                            logger.info(f"No more posts available. Total: {new_count} posts")
                            break
                        
                        # Scroll down
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        time.sleep(2)  # Wait for content to load
                
                page.close()
                
                # Limit to max_posts
                parsed['threads'] = parsed['threads'][:max_posts]
                
                logger.info(f"Scraped profile with {len(parsed['threads'])} threads")
                return parsed
                
            except Exception as e:
                logger.error(f"Error (attempt {attempt + 1}): {str(e)}")
                if attempt == max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
                
        raise Exception(f"Failed after {max_retries} attempts")
    
    def scrape_user_by_username(self, username: str, max_retries: int = 3, max_posts: int = 200) -> Dict:
        """
        Scrape profile bằng username
        
        Args:
            username: Username (không cần @)
            max_posts: Số posts tối đa cần lấy (mặc định 200)
            
        Returns:
            Dict với user info và threads
        """
        username = username.lstrip('@')
        url = f"https://www.threads.net/@{username}"
        return self.scrape_profile(url, max_retries, max_posts)
    
    def get_top_comments(self, thread_url: str, top_n: int = 10, sort_by: str = 'likes') -> List[Dict]:
        """
        Lấy top comments (replies) từ một thread
        
        Args:
            thread_url: URL của thread
            top_n: Số lượng comments muốn lấy (default: 10)
            sort_by: Sắp xếp theo 'likes' hoặc 'time' (default: 'likes')
            
        Returns:
            List các comments được sắp xếp
            
        Example:
            scraper = ThreadsScraper()
            top_comments = scraper.get_top_comments(
                "https://www.threads.net/t/C8H5FiCtESk/",
                top_n=5,
                sort_by='likes'
            )
        """
        logger.info(f"Getting top {top_n} comments from thread")
        
        # Scrape thread với replies
        data = self.scrape_thread(thread_url)
        replies = data.get('replies', [])
        
        if not replies:
            logger.warning("No replies found")
            return []
        
        # Convert sang DataFrame để dễ xử lý
        df = pd.DataFrame(replies)
        
        # Sắp xếp theo yêu cầu
        if sort_by == 'likes':
            df = df.sort_values('like_count', ascending=False)
        elif sort_by == 'time':
            df = df.sort_values('published_on', ascending=False)
        else:
            logger.warning(f"Invalid sort_by: {sort_by}, using 'likes'")
            df = df.sort_values('like_count', ascending=False)
        
        # Lấy top N
        top_comments = df.head(top_n).to_dict('records')
        
        logger.info(f"Found {len(top_comments)} top comments")
        return top_comments
    
    def get_top_comments_from_user_posts(self, username: str, num_posts: int = 5, 
                                         top_comments_per_post: int = 5, 
                                         sort_by: str = 'likes') -> Dict:
        """
        Lấy top comments từ các posts gần đây của một user
        
        Args:
            username: Username của user
            num_posts: Số lượng posts gần đây muốn lấy (default: 5)
            top_comments_per_post: Số comments muốn lấy từ mỗi post (default: 5)
            sort_by: Sắp xếp comments theo 'likes' hoặc 'time'
            
        Returns:
            Dict chứa user info và top comments từ các posts
            
        Example:
            scraper = ThreadsScraper()
            data = scraper.get_top_comments_from_user_posts(
                "natgeo",
                num_posts=3,
                top_comments_per_post=10
            )
        """
        logger.info(f"Getting top comments from @{username}'s posts")
        
        # Scrape user profile để lấy posts gần đây
        user_data = self.scrape_user_by_username(username)
        threads = user_data.get('threads', [])[:num_posts]
        
        if not threads:
            logger.warning(f"No threads found for @{username}")
            return {
                'user': user_data.get('user', {}),
                'posts_analyzed': 0,
                'posts_with_comments': []
            }
        
        # Lấy top comments từ mỗi post
        results = {
            'user': user_data.get('user', {}),
            'posts_analyzed': len(threads),
            'posts_with_comments': []
        }
        
        for i, thread in enumerate(threads, 1):
            try:
                logger.info(f"Processing post {i}/{len(threads)}: {thread['url']}")
                
                # Lấy top comments của post này
                top_comments = self.get_top_comments(
                    thread['url'],
                    top_n=top_comments_per_post,
                    sort_by=sort_by
                )
                
                results['posts_with_comments'].append({
                    'post': {
                        'text': thread['text'][:100] + '...' if len(thread['text']) > 100 else thread['text'],
                        'url': thread['url'],
                        'likes': thread['like_count'],
                        'reply_count': thread.get('reply_count', 0)
                    },
                    'top_comments': top_comments,
                    'total_comments_found': len(top_comments)
                })
                
                # Delay để tránh rate limit
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error processing post {i}: {str(e)}")
                continue
        
        logger.info(f"Completed analysis for {len(results['posts_with_comments'])} posts")
        return results
    
    def scrape_multiple_users(self, usernames: List[str]) -> List[Dict]:
        """
        Scrape nhiều users
        
        Args:
            usernames: List các username
            
        Returns:
            List of dicts với user data
        """
        results = []
        for username in usernames:
            try:
                logger.info(f"Scraping @{username}...")
                data = self.scrape_user_by_username(username)
                results.append({
                    'username': username,
                    'success': True,
                    'data': data
                })
                time.sleep(2)  # Delay để tránh rate limit
            except Exception as e:
                logger.error(f"Failed @{username}: {str(e)}")
                results.append({
                    'username': username,
                    'success': False,
                    'error': str(e)
                })
        return results
    
    def save_to_json(self, data: Dict, filename: str = None) -> str:
        """Lưu dữ liệu ra JSON"""
        if not filename:
            filename = f"threads_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        os.makedirs("data", exist_ok=True)
        filepath = f"data/{filename}"
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved to {filepath}")
        return filepath
    
    def save_threads_to_csv(self, threads: List[Dict], filename: str = None) -> str:
        """Lưu threads ra CSV"""
        if not filename:
            filename = f"threads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        
        os.makedirs("data", exist_ok=True)
        filepath = f"data/{filename}"
        
        df = pd.DataFrame(threads)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        logger.info(f"Saved to {filepath}")
        return filepath
    
    def save_to_excel(self, data: Dict, filename: str = None) -> str:
        """Lưu dữ liệu ra Excel"""
        if not filename:
            filename = f"threads_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        
        os.makedirs("data", exist_ok=True)
        filepath = f"data/{filename}"
        
        with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
            # Sheet 1: User info
            if 'user' in data:
                user_df = pd.DataFrame([data['user']])
                user_df.to_excel(writer, sheet_name='User Info', index=False)
            
            # Sheet 2: Threads
            if 'threads' in data:
                threads_df = pd.DataFrame(data['threads'])
                threads_df.to_excel(writer, sheet_name='Threads', index=False)
        
        logger.info(f"Saved to {filepath}")
        return filepath
    
    def analyze_engagement(self, data: Dict) -> Dict:
        """
        Phân tích engagement metrics
        
        Args:
            data: Data từ scrape_profile hoặc scrape_user_by_username
            
        Returns:
            Dict chứa các metrics phân tích
        """
        if 'threads' not in data or not data['threads']:
            return {"error": "No threads data"}
        
        df = pd.DataFrame(data['threads'])
        user = data.get('user', {})
        
        analysis = {
            'user': user.get('username', 'unknown'),
            'followers': user.get('followers', 0),
            'total_threads': len(df),
            'total_likes': int(df['like_count'].sum()),
            'avg_likes': float(df['like_count'].mean()),
            'max_likes': int(df['like_count'].max()),
            'min_likes': int(df['like_count'].min()),
            'median_likes': float(df['like_count'].median()),
        }
        
        # Engagement rate
        if user.get('followers', 0) > 0:
            analysis['avg_engagement_rate'] = (analysis['avg_likes'] / user['followers']) * 100
        
        # Content analysis
        df['has_video'] = df['videos'].apply(lambda x: len(x) > 0 if x else False)
        df['has_image'] = df['images'].apply(lambda x: len(x) > 0 if x else False)
        df['text_length'] = df['text'].str.len()
        
        analysis['threads_with_video'] = int(df['has_video'].sum())
        analysis['threads_with_image'] = int(df['has_image'].sum())
        analysis['avg_text_length'] = float(df['text_length'].mean())
        
        # Video performance
        if analysis['threads_with_video'] > 0:
            video_avg = df[df['has_video']]['like_count'].mean()
            non_video_avg = df[~df['has_video']]['like_count'].mean()
            analysis['video_avg_likes'] = float(video_avg)
            analysis['non_video_avg_likes'] = float(non_video_avg)
            if non_video_avg > 0:
                analysis['video_boost_percent'] = float(((video_avg / non_video_avg) - 1) * 100)
        
        return analysis
    
    def close(self):
        """Đóng browser"""
        if self.browser:
            self.browser.close()
            logger.info("Browser closed")
        if self.playwright:
            self.playwright.stop()


# ============================================================================
# INTERACTIVE MENU - Giao diện tương tác
# ============================================================================

def print_header():
    """In header"""
    print("\n" + "="*70)
    print("🧵 THREADS SCRAPER - Complete Solution")
    print("="*70)


def show_thread_info(data: Dict):
    """Hiển thị thông tin thread"""
    thread = data['thread']
    print(f"\n📝 THREAD INFO:")
    print(f"   User: @{thread['username']} {'✓' if thread['user_verified'] else ''}")
    print(f"   Content: {thread['text'][:100]}...")
    print(f"   Likes: {thread['like_count']:,}")
    print(f"   Replies: {len(data['replies'])}")
    print(f"   URL: {thread['url']}")


def show_profile_info(data: Dict):
    """Hiển thị thông tin profile"""
    user = data['user']
    print(f"\n👤 USER INFO:")
    print(f"   @{user['username']} - {user['full_name']}")
    print(f"   Followers: {user['followers']:,}")
    print(f"   Verified: {'✓' if user['is_verified'] else '✗'}")
    print(f"   Threads: {len(data['threads'])}")
    
    if data['threads']:
        df = pd.DataFrame(data['threads'])
        print(f"\n📊 QUICK STATS:")
        print(f"   Total likes: {df['like_count'].sum():,}")
        print(f"   Avg likes: {df['like_count'].mean():.2f}")
        print(f"   Top thread: {df['like_count'].max():,} likes")


def show_comparison(results: List[Dict]):
    """Hiển thị so sánh users"""
    comparison = []
    for r in results:
        if r['success']:
            data = r['data']
            user = data['user']
            threads = data['threads']
            avg_likes = sum(t['like_count'] for t in threads) / len(threads) if threads else 0
            comparison.append({
                'Username': f"@{user['username']}",
                'Followers': user['followers'],
                'Threads': len(threads),
                'Avg Likes': round(avg_likes, 2)
            })
    
    if comparison:
        df = pd.DataFrame(comparison)
        print("\n" + "="*70)
        print(df.to_string(index=False))
        print("="*70)


def main_menu():
    """Menu chính"""
    print_header()
    
    print("\n📚 CHỌN CHỨC NĂNG:")
    print("   1. Scrape một thread (post)")
    print("   2. Scrape profile của user")
    print("   3. So sánh nhiều users")
    print("   4. Phân tích engagement chi tiết")
    print("   5. 🔥 Lấy top comments từ một post")
    print("   6. 🔥 Lấy top comments từ posts của user")
    print("   0. Thoát")
    
    choice = input("\nNhập lựa chọn (0-6): ").strip()
    
    if choice == "0":
        print("\n👋 Goodbye!")
        return
    
    scraper = ThreadsScraper(headless=True)
    
    try:
        if choice == "1":
            # Scrape thread
            url = input("\nNhập URL thread: ").strip()
            print("\n🔍 Đang scrape...")
            data = scraper.scrape_thread(url)
            show_thread_info(data)
            
            if input("\n💾 Lưu dữ liệu? (y/n): ").lower() == 'y':
                scraper.save_to_json(data)
                print("✅ Đã lưu!")
        
        elif choice == "2":
            # Scrape profile
            username = input("\nNhập username (không cần @): ").strip()
            print(f"\n🔍 Đang scrape @{username}...")
            data = scraper.scrape_user_by_username(username)
            show_profile_info(data)
            
            if input("\n💾 Lưu dữ liệu? (y/n): ").lower() == 'y':
                scraper.save_to_json(data, f"{username}_data.json")
                scraper.save_threads_to_csv(data['threads'], f"{username}_threads.csv")
                print("✅ Đã lưu JSON và CSV!")
        
        elif choice == "3":
            # So sánh users
            print("\nNhập các username, cách nhau bằng dấu phẩy")
            usernames_input = input("Ví dụ: natgeo,instagram,meta\n> ").strip()
            usernames = [u.strip().lstrip('@') for u in usernames_input.split(',')]
            
            print(f"\n🔍 Đang scrape {len(usernames)} users...")
            results = scraper.scrape_multiple_users(usernames)
            show_comparison(results)
            
            if input("\n💾 Lưu kết quả? (y/n): ").lower() == 'y':
                scraper.save_to_json(results, "comparison.json")
                print("✅ Đã lưu!")
        
        elif choice == "4":
            # Phân tích engagement
            username = input("\nNhập username để phân tích: ").strip()
            print(f"\n🔍 Đang scrape và phân tích @{username}...")
            data = scraper.scrape_user_by_username(username)
            analysis = scraper.analyze_engagement(data)
            
            print(f"\n📊 ENGAGEMENT ANALYSIS:")
            print(f"   User: @{analysis['user']}")
            print(f"   Followers: {analysis['followers']:,}")
            print(f"   Total threads: {analysis['total_threads']}")
            print(f"   Total likes: {analysis['total_likes']:,}")
            print(f"   Avg likes: {analysis['avg_likes']:.2f}")
            
            if 'avg_engagement_rate' in analysis:
                print(f"   Engagement rate: {analysis['avg_engagement_rate']:.4f}%")
            
            if 'video_boost_percent' in analysis:
                print(f"\n🎥 Video Performance:")
                print(f"   Threads with video: {analysis['threads_with_video']}")
                print(f"   Video boost: {analysis['video_boost_percent']:.1f}%")
            
            if input("\n💾 Lưu analysis? (y/n): ").lower() == 'y':
                scraper.save_to_json(analysis, f"{username}_analysis.json")
                scraper.save_to_excel(data, f"{username}_full.xlsx")
                print("✅ Đã lưu JSON và Excel!")
        
        elif choice == "5":
            # Lấy top comments từ một post
            url = input("\nNhập URL thread: ").strip()
            top_n = input("Số lượng comments muốn lấy (default 10): ").strip()
            top_n = int(top_n) if top_n.isdigit() else 10
            
            print(f"\n🔍 Đang lấy top {top_n} comments...")
            top_comments = scraper.get_top_comments(url, top_n=top_n, sort_by='likes')
            
            if top_comments:
                print(f"\n💬 TOP {len(top_comments)} COMMENTS (sorted by likes):")
                print("="*70)
                for i, comment in enumerate(top_comments, 1):
                    text = comment.get('text') or ""
                    text = text[:80] + "..." if len(text) > 80 else text
                    print(f"\n{i}. @{comment['username']}: {text}")
                    print(f"   ❤️ {comment.get('like_count', 0):,} likes")
                    if comment.get('user_verified'):
                        print(f"   ✓ Verified")
                print("="*70)
                
                if input("\n💾 Lưu top comments? (y/n): ").lower() == 'y':
                    scraper.save_to_json({
                        'thread_url': url,
                        'top_comments': top_comments,
                        'total_found': len(top_comments)
                    }, "top_comments.json")
                    
                    # Lưu ra CSV
                    df = pd.DataFrame(top_comments)
                    df.to_csv("data/top_comments.csv", index=False, encoding='utf-8-sig')
                    print("✅ Đã lưu JSON và CSV!")
            else:
                print("\n❌ Không tìm thấy comments!")
        
        elif choice == "6":
            # Lấy top comments từ posts của user
            username = input("\nNhập username: ").strip()
            num_posts = input("Số posts muốn phân tích (default 5): ").strip()
            num_posts = int(num_posts) if num_posts.isdigit() else 5
            
            top_per_post = input("Số comments muốn lấy mỗi post (default 5): ").strip()
            top_per_post = int(top_per_post) if top_per_post.isdigit() else 5
            
            print(f"\n🔍 Đang phân tích {num_posts} posts gần đây của @{username}...")
            print(f"   Lấy top {top_per_post} comments từ mỗi post...")
            
            data = scraper.get_top_comments_from_user_posts(
                username,
                num_posts=num_posts,
                top_comments_per_post=top_per_post,
                sort_by='likes'
            )
            
            print(f"\n✅ Đã phân tích {data['posts_analyzed']} posts!")
            print(f"   User: @{data['user'].get('username', 'unknown')}")
            print(f"   Followers: {data['user'].get('followers', 0):,}")
            
            # Hiển thị tổng quan
            total_comments = sum(p['total_comments_found'] for p in data['posts_with_comments'])
            print(f"\n📊 TỔNG QUAN:")
            print(f"   Total comments found: {total_comments}")
            
            # Hiển thị từng post
            for i, post_data in enumerate(data['posts_with_comments'], 1):
                print(f"\n{'='*70}")
                print(f"POST {i}: {post_data['post']['text']}")
                print(f"URL: {post_data['post']['url']}")
                print(f"❤️ {post_data['post']['likes']:,} likes | 💬 {post_data['post']['reply_count']} replies")
                
                if post_data['top_comments']:
                    print(f"\n   Top {len(post_data['top_comments'])} comments:")
                    for j, comment in enumerate(post_data['top_comments'][:3], 1):
                        text = comment.get('text') or ""
                        text = text[:60] + "..." if len(text) > 60 else text
                        print(f"   {j}. @{comment['username']}: {text}")
                        print(f"      ❤️ {comment.get('like_count', 0):,} likes")
                else:
                    print("   (Không có comments)")
            
            print("="*70)
            
            if input("\n💾 Lưu kết quả? (y/n): ").lower() == 'y':
                scraper.save_to_json(data, f"{username}_top_comments_analysis.json")
                
                # Lưu tất cả comments ra CSV
                all_comments = []
                for post_data in data['posts_with_comments']:
                    for comment in post_data['top_comments']:
                        comment['post_url'] = post_data['post']['url']
                        comment['post_text'] = post_data['post']['text'][:50]
                        all_comments.append(comment)
                
                if all_comments:
                    df = pd.DataFrame(all_comments)
                    df.to_csv(f"data/{username}_all_top_comments.csv", index=False, encoding='utf-8-sig')
                    print(f"✅ Đã lưu JSON và CSV ({len(all_comments)} comments)!")
                else:
                    print("✅ Đã lưu JSON!")
        
        else:
            print("\n❌ Lựa chọn không hợp lệ!")
    
    except Exception as e:
        print(f"\n❌ Lỗi: {str(e)}")
        logger.error(f"Error in main menu: {str(e)}", exc_info=True)
    
    finally:
        scraper.close()
        print("\n✅ Browser đã đóng")


# ============================================================================
# QUICK EXAMPLES - Ví dụ sử dụng nhanh
# ============================================================================

def example_basic_usage():
    """Ví dụ cơ bản"""
    print("\n" + "="*70)
    print("VÍ DỤ 1: SỬ DỤNG CƠ BẢN")
    print("="*70)
    
    scraper = ThreadsScraper(headless=True)
    
    try:
        # Scrape profile
        print("\n🔍 Scraping @natgeo...")
        data = scraper.scrape_user_by_username("natgeo")
        
        # Hiển thị info
        print(f"✅ User: @{data['user']['username']}")
        print(f"   Followers: {data['user']['followers']:,}")
        print(f"   Threads: {len(data['threads'])}")
        
        # Lưu dữ liệu
        scraper.save_to_json(data, "natgeo_example.json")
        print("\n✅ Đã lưu dữ liệu!")
        
    finally:
        scraper.close()


def example_analysis():
    """Ví dụ phân tích"""
    print("\n" + "="*70)
    print("VÍ DỤ 2: PHÂN TÍCH ENGAGEMENT")
    print("="*70)
    
    scraper = ThreadsScraper(headless=True)
    
    try:
        print("\n🔍 Scraping và phân tích @natgeo...")
        data = scraper.scrape_user_by_username("natgeo")
        analysis = scraper.analyze_engagement(data)
        
        print(f"\n📊 Analysis Results:")
        print(f"   Avg engagement rate: {analysis.get('avg_engagement_rate', 0):.4f}%")
        print(f"   Video boost: {analysis.get('video_boost_percent', 0):.1f}%")
        
        scraper.save_to_json(analysis, "natgeo_analysis.json")
        print("\n✅ Đã lưu analysis!")
        
    finally:
        scraper.close()


def example_top_comments():
    """Ví dụ lấy top comments"""
    print("\n" + "="*70)
    print("VÍ DỤ 3: LẤY TOP COMMENTS TỪ POSTS CỦA USER")
    print("="*70)
    
    scraper = ThreadsScraper(headless=True)
    
    try:
        print("\n🔍 Lấy top comments từ 3 posts gần đây của @natgeo...")
        data = scraper.get_top_comments_from_user_posts(
            username="natgeo",
            num_posts=3,
            top_comments_per_post=5,
            sort_by='likes'
        )
        
        print(f"\n✅ Hoàn thành!")
        print(f"   Posts analyzed: {data['posts_analyzed']}")
        total_comments = sum(p['total_comments_found'] for p in data['posts_with_comments'])
        print(f"   Total top comments: {total_comments}")
        
        # Hiển thị một số comments
        if data['posts_with_comments'] and data['posts_with_comments'][0]['top_comments']:
            top_comment = data['posts_with_comments'][0]['top_comments'][0]
            print(f"\n🔥 Top comment:")
            print(f"   @{top_comment['username']}: {top_comment['text'][:80]}...")
            print(f"   ❤️ {top_comment['like_count']:,} likes")
        
        scraper.save_to_json(data, "natgeo_top_comments.json")
        print("\n✅ Đã lưu dữ liệu!")
        
    finally:
        scraper.close()


# ============================================================================
# MAIN - Entry point
# ============================================================================

if __name__ == "__main__":
    import sys
    
    print_header()
    print("\n🎯 MODE:")
    print("   1. Interactive Menu (Khuyến nghị)")
    print("   2. Quick Example - Basic Usage")
    print("   3. Quick Example - Analysis")
    print("   4. Quick Example - Top Comments 🔥")
    
    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = input("\nChọn mode (1-4): ").strip()
    
    if mode == "1":
        main_menu()
    elif mode == "2":
        example_basic_usage()
    elif mode == "3":
        example_analysis()
    elif mode == "4":
        example_top_comments()
    else:
        print("\n📖 Sử dụng:")
        print("   python threads_scraper_complete.py        # Interactive menu")
        print("   python threads_scraper_complete.py 2      # Basic example")
        print("   python threads_scraper_complete.py 3      # Analysis example")
        print("   python threads_scraper_complete.py 4      # Top comments example")
        print("\n📚 Hoặc import trong code:")
        print("   from threads_scraper_complete import ThreadsScraper")
        print("\n🔥 NEW FEATURES:")
        print("   - Lấy top comments từ một post")
        print("   - Lấy top comments từ nhiều posts của user")
        print("   - Sắp xếp theo likes hoặc time")
