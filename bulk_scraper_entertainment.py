"""
 BULK THREADS SCRAPER - Entertainment Profiles
Crawl hàng loạt profiles với chiến lược thông minh

YÊU CẦU:
- Mỗi account: 150-200 posts mới nhất
- Mỗi post: 20 comments top like (viral >1k likes: 50-100 comments)
- Mỗi comment: chính nó + 1 comment reply (nếu có)

CÁCH SỬ DỤNG:
1. Chạy: python bulk_scraper_entertainment.py
2. Chọn mode: Full auto hoặc Custom
3. Ngồi chờ và theo dõi tiến độ
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import pandas as pd
from threads_scraper_complete import ThreadsScraper
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'logs/bulk_scraper_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Danh sách profiles
ENTERTAINMENT_PROFILES = [
    "netflix",
    "disney",
    "entertainmentweekly",
    "rottentomatoes",
    "billboard",
    "rollingstone",
    "pitchfork",
    "taylorswift",
    "popbase",
    "selenagomez",
    "mariahcarey",
    "mtv",
    "bts.bighitoffficiai",
    "filmatic",
    "aboutmusicyt",
    "moviemoments",
    "buzzfeed",
]


class BulkThreadsScraper:
    """
    Scraper hàng loạt với chiến lược thông minh
    """
    
    def __init__(self, headless: bool = True):
        self.scraper = ThreadsScraper(headless=headless)
        self.results = []
        self.stats = {
            'profiles_scraped': 0,
            'total_posts': 0,
            'total_comments': 0,
            'start_time': datetime.now(),
            'errors': []
        }
        self.checkpoint_file = Path('data/entertainment_profiles/.checkpoint.json')
        self.backup_dir = Path('data/entertainment_profiles/backups')
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Load checkpoint nếu có
        self.checkpoint = self.load_checkpoint()
        
    def scrape_profile_posts(self, username: str, max_posts: int = 200) -> Dict:
        """
        Scrape profile và lấy posts (scroll để lấy nhiều posts nhất có thể)
        
        Args:
            username: Username của profile
            max_posts: Số posts tối đa (150-200), nếu profile có ít hơn thì lấy hết
            
        Returns:
            Dict chứa user info và posts
        """
        logger.info(f"{'='*70}")
        logger.info(f"Scraping profile: @{username}")
        logger.info(f"Target: {max_posts} posts (or all available)")
        
        try:
            # Scrape profile với scroll để lấy nhiều posts
            data = self.scraper.scrape_user_by_username(username, max_posts=max_posts)
            
            posts = data.get('threads', [])
            user = data.get('user', {})
            
            actual_posts = len(posts)
            logger.info(f"Found {actual_posts} posts")
            
            if actual_posts < max_posts:
                logger.info(f"Note: Profile has only {actual_posts} posts (less than target {max_posts})")
            
            logger.info(f"User: {user.get('full_name', 'N/A')}")
            logger.info(f"Followers: {user.get('followers', 0):,}")
            
            return {
                'username': username,
                'user': user,
                'posts': posts,
                'scraped_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error scraping @{username}: {str(e)}")
            self.stats['errors'].append({
                'username': username,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
            return None
    
    def scrape_post_comments(self, post_url: str, post_likes: int, 
                            target_comments: int = 20) -> List[Dict]:
        """
        Scrape comments từ một post
        
        Args:
            post_url: URL của post
            post_likes: Số likes của post
            target_comments: Số comments muốn lấy
            
        Returns:
            List comments
        """
        # Điều chỉnh số comments dựa trên viral level
        if post_likes > 1000:  # Viral post
            target_comments = min(100, target_comments * 5)  # 50-100 comments
            logger.info(f"    Viral post ({post_likes:,} likes) - Target: {target_comments} comments")
        
        try:
            comments = self.scraper.get_top_comments(
                post_url, 
                top_n=target_comments,
                sort_by='likes'
            )
            
            if comments:
                logger.info(f"    Got {len(comments)} comments")
                return comments
            else:
                logger.warning(f"    No comments found")
                return []
                
        except Exception as e:
            logger.error(f"    Error getting comments: {str(e)}")
            return []
    
    def scrape_comment_replies(self, comment_url: str, max_replies: int = 1) -> List[Dict]:
        """
        Scrape replies của một comment
        
        Args:
            comment_url: URL của comment (thread)
            max_replies: Số replies tối đa
            
        Returns:
            List replies
        """
        try:
            # Comment cũng là một thread, có thể scrape như post
            data = self.scraper.scrape_thread(comment_url)
            replies = data.get('replies', [])[:max_replies]
            
            if replies:
                logger.debug(f"      ↳ Got {len(replies)} reply")
            
            return replies
            
        except Exception as e:
            logger.debug(f"      ↳ No reply: {str(e)}")
            return []
    
    def scrape_profile_full(self, username: str, 
                           max_posts: int = 200,
                           comments_per_post: int = 20,
                           delay: float = 2.0,
                           resume: bool = False) -> Dict:
        """
        Scrape đầy đủ một profile: posts + comments + replies
        
        Args:
            username: Username
            max_posts: Số posts tối đa
            comments_per_post: Số comments mỗi post (base)
            delay: Delay giữa requests (giây)
            resume: Resume từ checkpoint
            
        Returns:
            Dict chứa toàn bộ dữ liệu
        """
        logger.info(f"\n{'='*70}")
        logger.info(f"[FULL SCRAPE] @{username}")
        logger.info(f"{'='*70}")
        
        # Check xem đã hoàn thành chưa
        if self.is_profile_completed(username):
            logger.info(f"[SKIP] Profile @{username} already completed")
            return None
        
        # 1. Scrape profile và posts
        profile_data = self.scrape_profile_posts(username, max_posts)
        
        if not profile_data:
            return None
        
        posts = profile_data['posts']
        posts_with_comments = []
        
        # Xác định điểm bắt đầu (resume hoặc từ đầu)
        start_index = 0
        if resume and self.checkpoint.get('last_profile') == username:
            start_index = self.checkpoint.get('last_post_index', 0)
            logger.info(f"Resuming from post {start_index + 1}/{len(posts)}")
        
        # 2. Scrape comments cho mỗi post
        try:
            for i in range(start_index, len(posts)):
                post = posts[i]
                logger.info(f"\nPost {i+1}/{len(posts)}: {post.get('url', 'N/A')}")
                logger.info(f"   Text: {post.get('text', '')[:60]}...")
                logger.info(f"   Likes: {post.get('like_count', 0):,}")
                
                try:
                    # Get comments
                    comments = self.scrape_post_comments(
                        post.get('url', ''),
                        post.get('like_count', 0),
                        comments_per_post
                    )
                    
                    # 3. Scrape reply cho mỗi comment (1 reply)
                    comments_with_replies = []
                    for j, comment in enumerate(comments[:10], 1):  # Limit 10 comments để lấy replies
                        logger.debug(f"   Comment {j}: @{comment.get('username', 'N/A')}")
                        
                        # Get 1 reply
                        replies = self.scrape_comment_replies(
                            comment.get('url', ''),
                            max_replies=1
                        )
                        
                        comment['replies'] = replies
                        comments_with_replies.append(comment)
                    
                    # Thêm các comments còn lại không có replies
                    for comment in comments[10:]:
                        comment['replies'] = []
                        comments_with_replies.append(comment)
                    
                    posts_with_comments.append({
                        'post': post,
                        'comments': comments_with_replies,
                        'comment_count': len(comments_with_replies)
                    })
                    
                    self.stats['total_posts'] += 1
                    self.stats['total_comments'] += len(comments_with_replies)
                    
                    # AUTO-SAVE sau mỗi 5 posts
                    if (i + 1) % 5 == 0:
                        temp_result = {
                            'username': username,
                            'user': profile_data['user'],
                            'posts_with_comments': posts_with_comments,
                            'stats': {
                                'total_posts': len(posts_with_comments),
                                'total_comments': sum(p['comment_count'] for p in posts_with_comments),
                                'scraped_at': datetime.now().isoformat(),
                                'is_complete': False,
                                'progress': f"{i+1}/{len(posts)}"
                            }
                        }
                        self.save_profile_data(temp_result, is_final=False)
                        self.backup_profile_data(temp_result, is_incremental=True)
                        logger.info(f"[AUTO-SAVE] Progress: {i+1}/{len(posts)} posts")
                    
                    # Save checkpoint sau mỗi post
                    self.save_checkpoint(username, i + 1)
                    
                    # Delay để tránh rate limit
                    time.sleep(delay)
                    
                except Exception as post_error:
                    logger.error(f"[ERROR] Processing post {i+1}: {str(post_error)}")
                    # Tiếp tục với post tiếp theo
                    continue
            
        except KeyboardInterrupt:
            logger.warning(f"\n[INTERRUPTED] at post {i+1}/{len(posts)}")
            # Save dữ liệu đã có
            if posts_with_comments:
                partial_result = {
                    'username': username,
                    'user': profile_data['user'],
                    'posts_with_comments': posts_with_comments,
                    'stats': {
                        'total_posts': len(posts_with_comments),
                        'total_comments': sum(p['comment_count'] for p in posts_with_comments),
                        'scraped_at': datetime.now().isoformat(),
                        'is_complete': False,
                        'interrupted_at': i + 1
                    }
                }
                self.save_profile_data(partial_result, is_final=False)
                logger.info(f"[SAVED] Partial data: {len(posts_with_comments)} posts")
            raise
        
        # Tổng hợp kết quả cuối cùng
        result = {
            'username': username,
            'user': profile_data['user'],
            'posts_with_comments': posts_with_comments,
            'stats': {
                'total_posts': len(posts_with_comments),
                'total_comments': sum(p['comment_count'] for p in posts_with_comments),
                'scraped_at': datetime.now().isoformat(),
                'is_complete': True
            }
        }
        
        self.stats['profiles_scraped'] += 1
        
        # FINAL SAVE sau khi hoàn thành
        self.save_profile_data(result, is_final=True)
        self.mark_profile_completed(username)
        
        logger.info(f"\n[COMPLETED] @{username}")
        logger.info(f"   Posts: {result['stats']['total_posts']}")
        logger.info(f"   Comments: {result['stats']['total_comments']}")
        
        return result
    
    def load_checkpoint(self) -> Dict:
        """Load checkpoint từ file"""
        if self.checkpoint_file.exists():
            try:
                with open(self.checkpoint_file, 'r', encoding='utf-8') as f:
                    checkpoint = json.load(f)
                logger.info(f"Loaded checkpoint: {checkpoint.get('last_profile', 'N/A')}")
                return checkpoint
            except Exception as e:
                logger.warning(f"Cannot load checkpoint: {e}")
        return {'completed_profiles': [], 'last_profile': None, 'last_post_index': 0}
    
    def save_checkpoint(self, username: str, post_index: int):
        """Lưu checkpoint"""
        self.checkpoint['last_profile'] = username
        self.checkpoint['last_post_index'] = post_index
        
        try:
            with open(self.checkpoint_file, 'w', encoding='utf-8') as f:
                json.dump(self.checkpoint, f, indent=2)
        except Exception as e:
            logger.error(f"Cannot save checkpoint: {e}")
    
    def mark_profile_completed(self, username: str):
        """Đánh dấu profile đã hoàn thành"""
        if username not in self.checkpoint.get('completed_profiles', []):
            self.checkpoint.setdefault('completed_profiles', []).append(username)
            self.checkpoint['last_profile'] = None
            self.checkpoint['last_post_index'] = 0
            self.save_checkpoint(username, 0)
    
    def is_profile_completed(self, username: str) -> bool:
        """Kiểm tra profile đã hoàn thành chưa"""
        return username in self.checkpoint.get('completed_profiles', [])
    
    def backup_profile_data(self, data: Dict, is_incremental: bool = False):
        """Backup dữ liệu profile"""
        username = data['username']
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if is_incremental:
            backup_file = self.backup_dir / f"{username}_incremental_{timestamp}.json"
        else:
            backup_file = self.backup_dir / f"{username}_backup_{timestamp}.json"
        
        try:
            with open(backup_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Backup: {backup_file.name}")
        except Exception as e:
            logger.error(f"Backup failed: {e}")
    
    def save_profile_data(self, data: Dict, is_final: bool = False):
        """Lưu dữ liệu của một profile"""
        username = data['username']
        
        # Create output dir
        output_dir = Path('data/entertainment_profiles')
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save JSON
        json_file = output_dir / f"{username}_full.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved: {json_file}")
        
        # Backup nếu là final save
        if is_final:
            self.backup_profile_data(data, is_incremental=False)
        
        # Save summary CSV
        posts_summary = []
        for item in data['posts_with_comments']:
            post = item['post']
            posts_summary.append({
                'username': username,
                'post_url': post.get('url', ''),
                'post_text': post.get('text', '')[:100],
                'likes': post.get('like_count', 0),
                'comments_count': item['comment_count']
            })
        
        if posts_summary:
            csv_file = output_dir / f"{username}_posts_summary.csv"
            df = pd.DataFrame(posts_summary)
            df.to_csv(csv_file, index=False, encoding='utf-8-sig')
            logger.info(f"Saved: {csv_file}")
    
    def scrape_all_profiles(self, profiles: List[str], 
                           max_posts: int = 200,
                           comments_per_post: int = 20,
                           delay: float = 3.0,
                           resume: bool = True):
        """
        Scrape tất cả profiles với checkpoint/resume
        
        Args:
            profiles: List usernames
            max_posts: Số posts mỗi profile
            comments_per_post: Số comments mỗi post (base)
            delay: Delay giữa profiles (giây)
            resume: Tự động resume từ checkpoint
        """
        # Filter completed profiles nếu resume
        if resume:
            profiles_to_scrape = [p for p in profiles if not self.is_profile_completed(p)]
            if len(profiles_to_scrape) < len(profiles):
                completed_count = len(profiles) - len(profiles_to_scrape)
                logger.info(f"\n[RESUME MODE] {completed_count} profile(s) already completed")
                logger.info(f"   Remaining: {len(profiles_to_scrape)} profile(s)")
        else:
            profiles_to_scrape = profiles
        
        logger.info(f"\n{'='*70}")
        logger.info(f"[BULK SCRAPING] {len(profiles_to_scrape)}/{len(profiles)} PROFILES")
        logger.info(f"{'='*70}")
        logger.info(f"Settings:")
        logger.info(f"  - Max posts per profile: {max_posts}")
        logger.info(f"  - Comments per post: {comments_per_post} (viral: 50-100)")
        logger.info(f"  - Delay between profiles: {delay}s")
        logger.info(f"  - Checkpoint: {self.checkpoint_file}")
        logger.info(f"  - Backups: {self.backup_dir}")
        logger.info(f"{'='*70}\n")
        
        try:
            for i, username in enumerate(profiles_to_scrape, 1):
                logger.info(f"\n{'#'*70}")
                logger.info(f"# PROFILE {i}/{len(profiles_to_scrape)}: @{username}")
                logger.info(f"{'#'*70}")
                
                try:
                    self.scrape_profile_full(
                        username,
                        max_posts=max_posts,
                        comments_per_post=comments_per_post,
                        delay=1.0,  # Delay giữa posts
                        resume=resume
                    )
                    
                    # Delay giữa profiles
                    if i < len(profiles_to_scrape):
                        logger.info(f"\n[COOLDOWN] Waiting {delay}s before next profile...")
                        time.sleep(delay)
                        
                except Exception as e:
                    logger.error(f"\n[ERROR] Failed to scrape @{username}: {str(e)}")
                    self.stats['errors'].append({
                        'username': username,
                        'error': str(e),
                        'timestamp': datetime.now().isoformat()
                    })
                    continue
        
        except KeyboardInterrupt:
            logger.warning(f"\n[INTERRUPTED] Bulk scrape interrupted by user")
            logger.info(f"[CHECKPOINT] Progress saved: {self.checkpoint_file}")
            logger.info(f"[BACKUP] Backups available: {self.backup_dir}")
            logger.info(f"[INFO] To resume, run the script again with resume=True")
        
        # Tổng kết
        self.print_final_stats()
        self.save_final_report()
    
    def print_final_stats(self):
        """In thống kê cuối cùng"""
        duration = datetime.now() - self.stats['start_time']
        
        logger.info(f"\n{'='*70}")
        logger.info(f"[COMPLETED] SCRAPING FINISHED!")
        logger.info(f"{'='*70}")
        logger.info(f"FINAL STATISTICS:")
        logger.info(f"   Profiles scraped: {self.stats['profiles_scraped']}")
        logger.info(f"   Total posts: {self.stats['total_posts']}")
        logger.info(f"   Total comments: {self.stats['total_comments']}")
        logger.info(f"   Duration: {duration}")
        logger.info(f"   Errors: {len(self.stats['errors'])}")
        logger.info(f"{'='*70}\n")
    
    def save_final_report(self):
        """Lưu báo cáo tổng kết"""
        # Convert datetime to string for JSON serialization
        stats_copy = self.stats.copy()
        stats_copy['start_time'] = stats_copy['start_time'].isoformat()
        
        report = {
            'summary': stats_copy,
            'duration': str(datetime.now() - self.stats['start_time']),
            'completed_at': datetime.now().isoformat()
        }
        
        report_file = Path('data/entertainment_profiles/FINAL_REPORT.json')
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"[REPORT] Final report saved: {report_file}")
    
    def close(self):
        """Đóng scraper"""
        self.scraper.close()


def main():
    """Main function"""
    print("\n" + "="*70)
    print(" BULK THREADS SCRAPER - Entertainment Profiles")
    print("="*70)
    
    print("\n PROFILES TO SCRAPE:")
    for i, username in enumerate(ENTERTAINMENT_PROFILES, 1):
        print(f"   {i:2d}. @{username}")
    
    print("\n SETTINGS:")
    print(f"   Max posts per profile: 150-200")
    print(f"   Comments per post: 20 (viral: 50-100)")
    print(f"   Replies per comment: 1")
    
    print("\n MODE:")
    print("   1. Full Auto (Tất cả profiles)")
    print("   2. Custom (Chọn profiles)")
    print("   3. Test (1 profile đầu tiên)")
    print("   0. Exit")
    
    choice = input("\nNhập lựa chọn (0-3): ").strip()
    
    if choice == "0":
        print("\n Goodbye!")
        return
    
    # Khởi tạo scraper
    headless = input("\nChạy headless mode? (y/n, default=y): ").strip().lower()
    headless = headless != 'n'
    
    scraper = BulkThreadsScraper(headless=headless)
    
    try:
        if choice == "1":
            # Full auto
            max_posts = int(input("\nSố posts mỗi profile (default=175): ").strip() or "175")
            comments = int(input("Comments mỗi post (default=20): ").strip() or "20")
            delay = float(input("Delay giữa profiles (giây, default=3): ").strip() or "3")
            
            resume = input("\nResume từ checkpoint? (y/n, default=y): ").strip().lower()
            resume = resume != 'n'
            
            confirm = input(f"\n>> Start scraping {len(ENTERTAINMENT_PROFILES)} profiles? (y/n): ")
            if confirm.lower() == 'y':
                scraper.scrape_all_profiles(
                    ENTERTAINMENT_PROFILES,
                    max_posts=max_posts,
                    comments_per_post=comments,
                    delay=delay,
                    resume=resume
                )
            
        elif choice == "2":
            # Custom
            print("\nNhập số thứ tự profiles cần scrape (vd: 1,3,5 hoặc 1-5):")
            selection = input("Lựa chọn: ").strip()
            
            # Parse selection
            selected_profiles = []
            try:
                if '-' in selection:
                    start, end = map(int, selection.split('-'))
                    selected_profiles = ENTERTAINMENT_PROFILES[start-1:end]
                else:
                    indices = [int(x.strip())-1 for x in selection.split(',')]
                    selected_profiles = [ENTERTAINMENT_PROFILES[i] for i in indices]
                
                print(f"\nSelected: {', '.join(['@'+p for p in selected_profiles])}")
                
                max_posts = int(input("\nSố posts mỗi profile (default=175): ").strip() or "175")
                comments = int(input("Comments mỗi post (default=20): ").strip() or "20")
                
                resume = input("\nResume từ checkpoint? (y/n, default=y): ").strip().lower()
                resume = resume != 'n'
                
                scraper.scrape_all_profiles(
                    selected_profiles,
                    max_posts=max_posts,
                    comments_per_post=comments,
                    resume=resume
                )
            except Exception as e:
                print(f"\n Invalid selection: {e}")
        
        elif choice == "3":
            # Test với 1 profile
            test_username = ENTERTAINMENT_PROFILES[0]
            print(f"\n Test mode: @{test_username}")
            
            result = scraper.scrape_profile_full(
                test_username,
                max_posts=10,  # Chỉ 10 posts để test
                comments_per_post=5,  # 5 comments để test
                delay=1.0,
                resume=False  # Không resume trong test mode
            )
            
            if result:
                print(f"\nTest successful!")
                print(f"   Posts: {result['stats']['total_posts']}")
                print(f"   Comments: {result['stats']['total_comments']}")
        
        else:
            print("\n Invalid choice!")
    
    except KeyboardInterrupt:
        print("\n\n Interrupted by user!")
        scraper.print_final_stats()
    except Exception as e:
        print(f"\n Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        scraper.close()
        print("\nBrowser closed")


if __name__ == "__main__":
    main()
