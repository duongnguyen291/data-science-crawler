"""
YouTube Comment Crawler - Main Application
Tổng hợp tất cả chức năng crawl, làm sạch và phân tích comments
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Optional
from youtube_crawler import YouTubeCommentCrawler
from data_cleaner import CommentDataCleaner
from logger_config import get_main_logger
import pandas as pd

# Setup logging
logger = get_main_logger()

class YouTubeCommentAnalyzer:
    """
    Class chính để phân tích comments YouTube
    """
    
    def __init__(self, api_key: str):
        """
        Khởi tạo analyzer
        
        Args:
            api_key (str): YouTube Data API v3 key
        """
        self.crawler = YouTubeCommentCrawler(api_key)
        self.cleaner = CommentDataCleaner()
        self.api_key = api_key
        
    def crawl_comments(self, video_url: str, max_comments: int = 100, 
                      order: str = 'time', min_likes: int = 0,
                      min_words: Optional[int] = None, max_words: Optional[int] = None) -> dict:
        """
        Crawl comments từ video YouTube
        
        Args:
            video_url (str): URL video YouTube
            max_comments (int): Số lượng comment tối đa
            order (str): Thứ tự sắp xếp ('time', 'relevance')
            min_likes (int): Số lượt like tối thiểu (chỉ áp dụng khi order='top')
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            dict: Kết quả crawl
        """
        logger.info(f"Starting comment crawl for: {video_url}")
        
        if min_likes > 0:
            # Lấy top comments có like cao
            result = self.crawler.get_top_comments(video_url, max_comments, min_likes, min_words, max_words)
        else:
            # Lấy comments thông thường
            result = self.crawler.crawl_video(video_url, max_comments, order, min_words, max_words)
        
        if result['success']:
            logger.info(f"Successfully crawled {result['total_comments']} comments")
        else:
            logger.error(f"Crawl failed: {result['error']}")
            
        return result
    
    def crawl_from_csv(self, csv_path: str, url_column: str = 'url', 
                      max_comments: int = 100, order: str = 'time',
                      delay: float = 0.2, limit: int = None,
                      deduplicate_urls: bool = True, min_likes: int = 0,
                      min_words: Optional[int] = None, max_words: Optional[int] = None) -> dict:
        """
        Crawl comments từ danh sách video trong CSV
        
        Args:
            csv_path (str): Đường dẫn tới file CSV chứa danh sách video
            url_column (str): Tên cột chứa URL (mặc định: 'url')
            max_comments (int): Số lượng comment tối đa mỗi video
            order (str): Thứ tự sắp xếp ('time', 'relevance')
            delay (float): Thời gian nghỉ giữa các video (giây)
            limit (int): Giới hạn số video cần crawl (None = tất cả)
            deduplicate_urls (bool): Có bỏ qua URL trùng lặp không (mặc định: True)
            min_likes (int): Số lượt like tối thiểu (0 = disabled)
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            dict: Kết quả crawl từ CSV
        """
        logger.info(f"Starting CSV crawl from: {csv_path}")
        result = self.crawler.crawl_from_csv(
            csv_path=csv_path,
            url_column=url_column,
            max_comments=max_comments,
            order=order,
            delay=delay,
            limit=limit,
            deduplicate_urls=deduplicate_urls,
            min_likes=min_likes,
            min_words=min_words,
            max_words=max_words
        )
        return result
    
    def clean_comments(self, comments: list) -> pd.DataFrame:
        """
        Làm sạch dữ liệu comments
        
        Args:
            comments (list): Danh sách comments
            
        Returns:
            pd.DataFrame: Comments đã được làm sạch
        """
        logger.info(f"Cleaning {len(comments)} comments...")
        
        df = pd.DataFrame(comments)
        cleaned_df = self.cleaner.clean_dataframe(df)
        
        stats = self.cleaner.get_cleaning_stats(cleaned_df)
        logger.info(f"Cleaning completed: {stats['valid_comments']}/{stats['total_comments']} valid comments")
        
        return cleaned_df
    
    def analyze_comments(self, video_url: str, max_comments: int = 100, 
                        order: str = 'time', min_likes: int = 0, 
                        clean_data: bool = True, save_results: bool = True,
                        min_words: Optional[int] = None, max_words: Optional[int] = None) -> dict:
        """
        Phân tích hoàn chỉnh comments từ video
        
        Args:
            video_url (str): URL video YouTube
            max_comments (int): Số lượng comment tối đa
            order (str): Thứ tự sắp xếp
            min_likes (int): Số lượt like tối thiểu
            clean_data (bool): Có làm sạch dữ liệu không
            save_results (bool): Có lưu kết quả không
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            dict: Kết quả phân tích
        """
        print(f"\n=== YOUTUBE COMMENT ANALYZER ===")
        print(f"Video: {video_url}")
        print(f"Max comments: {max_comments}")
        print(f"Order: {order}")
        if min_likes > 0:
            print(f"Min likes: {min_likes}")
        if min_words is not None:
            print(f"Min words: {min_words}")
        if max_words is not None:
            print(f"Max words: {max_words}")
        
        # Bước 1: Crawl comments
        print(f"\n1. CRAWLING COMMENTS...")
        crawl_result = self.crawl_comments(video_url, max_comments, order, min_likes, min_words, max_words)
        
        if not crawl_result['success']:
            return {'success': False, 'error': crawl_result['error']}
        
        comments = crawl_result['comments']
        video_info = crawl_result['video_info']
        
        # Hiển thị thông tin video
        print(f"\n2. VIDEO INFORMATION:")
        try:
            print(f"   Title: {video_info['title']}")
            print(f"   Channel: {video_info['channel_title']}")
        except UnicodeEncodeError:
            print(f"   Title: [Vietnamese text - see CSV file]")
            print(f"   Channel: [Vietnamese text - see CSV file]")
        
        print(f"   Views: {int(video_info['view_count']):,}")
        print(f"   Likes: {int(video_info['like_count']):,}")
        print(f"   Total Comments: {int(video_info['comment_count']):,}")
        
        # Thống kê comments
        print(f"\n3. COMMENT STATISTICS:")
        print(f"   Crawled comments: {len(comments)}")
        
        if comments:
            max_likes = max(c['like_count'] for c in comments)
            avg_likes = sum(c['like_count'] for c in comments) / len(comments)
            print(f"   Max likes: {max_likes}")
            print(f"   Average likes: {avg_likes:.1f}")
        
        # Bước 2: Làm sạch dữ liệu (nếu được yêu cầu)
        cleaned_df = None
        if clean_data:
            print(f"\n4. CLEANING DATA...")
            cleaned_df = self.clean_comments(comments)
            
            # Hiển thị thống kê sau khi làm sạch
            stats = self.cleaner.get_cleaning_stats(cleaned_df)
            print(f"   Valid comments: {stats['valid_comments']}")
            print(f"   Language distribution: {stats['language_distribution']}")
            print(f"   Average text length: {stats['avg_text_length']:.1f} characters")
        
        # Bước 3: Hiển thị comments mẫu
        print(f"\n5. SAMPLE COMMENTS:")
        for i, comment in enumerate(comments[:3], 1):
            try:
                text = comment['comment_text'][:80].replace('\n', ' ')
                author = comment['author_name']
                likes = comment['like_count']
                print(f"   {i}. {author} ({likes} likes): {text}...")
            except UnicodeEncodeError:
                print(f"   {i}. [Vietnamese comment] ({comment['like_count']} likes)")
        
        # Bước 4: Lưu kết quả (nếu được yêu cầu)
        saved_files = []
        if save_results:
            print(f"\n6. SAVING RESULTS...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Lưu raw data
            raw_file = self.crawler.save_to_csv(comments, f"raw_comments_{timestamp}.csv")
            saved_files.append(raw_file)
            print(f"   Raw data: {raw_file}")
            
            # Lưu cleaned data (nếu có)
            if cleaned_df is not None:
                cleaned_file = f"cleaned_comments_{timestamp}.csv"
                cleaned_df.to_csv(cleaned_file, index=False, encoding='utf-8')
                saved_files.append(cleaned_file)
                print(f"   Cleaned data: {cleaned_file}")
        
        print(f"\n[SUCCESS] Analysis completed!")
        if saved_files:
            print(f"Files saved: {', '.join(saved_files)}")
        
        return {
            'success': True,
            'video_info': video_info,
            'comments': comments,
            'cleaned_df': cleaned_df,
            'saved_files': saved_files,
            'total_comments': len(comments)
        }
    
    def analyze_from_csv(self, csv_path: str, url_column: str = 'url',
                        max_comments: int = 100, order: str = 'time',
                        delay: float = 0.2, limit: int = None,
                        deduplicate_urls: bool = True,
                        clean_data: bool = True, save_results: bool = True,
                        min_likes: int = 0, min_words: Optional[int] = None,
                        max_words: Optional[int] = None) -> dict:
        """
        Phân tích hoàn chỉnh comments từ danh sách video trong CSV
        
        Args:
            csv_path (str): Đường dẫn tới file CSV
            url_column (str): Tên cột chứa URL
            max_comments (int): Số lượng comment tối đa mỗi video
            order (str): Thứ tự sắp xếp
            delay (float): Thời gian nghỉ giữa các video
            limit (int): Giới hạn số video
            deduplicate_urls (bool): Có bỏ qua URL trùng lặp không
            clean_data (bool): Có làm sạch dữ liệu không
            save_results (bool): Có lưu kết quả không
            min_likes (int): Số lượt like tối thiểu (0 = disabled)
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            dict: Kết quả phân tích
        """
        print(f"\n=== YOUTUBE COMMENT ANALYZER - CSV MODE ===")
        print(f"CSV file: {csv_path}")
        print(f"Max comments per video: {max_comments}")
        print(f"Order: {order}")
        if min_likes > 0:
            print(f"Min likes: {min_likes}")
        if min_words is not None:
            print(f"Min words: {min_words}")
        if max_words is not None:
            print(f"Max words: {max_words}")
        if limit:
            print(f"Limit: {limit} videos")
        
        # Bước 1: Crawl từ CSV
        print(f"\n1. CRAWLING FROM CSV...")
        crawl_result = self.crawl_from_csv(
            csv_path=csv_path,
            url_column=url_column,
            max_comments=max_comments,
            order=order,
            delay=delay,
            limit=limit,
            deduplicate_urls=deduplicate_urls,
            min_likes=min_likes,
            min_words=min_words,
            max_words=max_words
        )
        
        if not crawl_result.get('success', False):
            if crawl_result.get('error'):
                return {'success': False, 'error': crawl_result['error']}
        
        all_comments = crawl_result.get('aggregated_comments', [])
        summary = crawl_result.get('summary', [])
        
        print(f"\n2. CRAWL SUMMARY:")
        print(f"   Total videos processed: {crawl_result.get('total_videos', 0)}")
        print(f"   Total comments crawled: {crawl_result.get('total_comments', 0)}")
        failed_count = len(crawl_result.get('failed_urls', []))
        if failed_count > 0:
            print(f"   Failed videos: {failed_count}")
        
        # Thống kê comments
        if all_comments:
            print(f"\n3. COMMENT STATISTICS:")
            max_likes = max(c['like_count'] for c in all_comments)
            avg_likes = sum(c['like_count'] for c in all_comments) / len(all_comments)
            print(f"   Total comments: {len(all_comments)}")
            print(f"   Max likes: {max_likes}")
            print(f"   Average likes: {avg_likes:.1f}")
        
        # Bước 2: Làm sạch dữ liệu
        cleaned_df = None
        if clean_data and all_comments:
            print(f"\n4. CLEANING DATA...")
            cleaned_df = self.clean_comments(all_comments)
            
            stats = self.cleaner.get_cleaning_stats(cleaned_df)
            print(f"   Valid comments: {stats['valid_comments']}")
            print(f"   Language distribution: {stats['language_distribution']}")
            print(f"   Average text length: {stats['avg_text_length']:.1f} characters")
        
        # Bước 3: Hiển thị comments mẫu
        if all_comments:
            print(f"\n5. SAMPLE COMMENTS:")
            for i, comment in enumerate(all_comments[:3], 1):
                try:
                    text = comment['comment_text'][:80].replace('\n', ' ')
                    author = comment['author_name']
                    likes = comment['like_count']
                    print(f"   {i}. {author} ({likes} likes): {text}...")
                except UnicodeEncodeError:
                    print(f"   {i}. [Vietnamese comment] ({comment['like_count']} likes)")
        
        # Bước 4: Lưu kết quả
        saved_files = []
        if save_results and all_comments:
            print(f"\n6. SAVING RESULTS...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Lưu raw data
            raw_file = self.crawler.save_to_csv(all_comments, f"raw_comments_{timestamp}.csv")
            saved_files.append(raw_file)
            print(f"   Raw data: {raw_file}")
            
            # Lưu cleaned data
            if cleaned_df is not None:
                cleaned_file = f"cleaned_comments_{timestamp}.csv"
                cleaned_df.to_csv(cleaned_file, index=False, encoding='utf-8')
                saved_files.append(cleaned_file)
                print(f"   Cleaned data: {cleaned_file}")
        
        print(f"\n[SUCCESS] CSV analysis completed!")
        if saved_files:
            print(f"Files saved: {', '.join(saved_files)}")
        
        return {
            'success': True,
            'summary': summary,
            'comments': all_comments,
            'cleaned_df': cleaned_df,
            'saved_files': saved_files,
            'total_comments': len(all_comments),
            'total_videos': crawl_result.get('total_videos', 0),
            'failed_urls': crawl_result.get('failed_urls', [])
        }

def main():
    """
    Hàm main với command line interface
    """
    parser = argparse.ArgumentParser(description='YouTube Comment Crawler & Analyzer')
    parser.add_argument('--api-key', required=True, help='YouTube Data API v3 key')
    parser.add_argument('--video-url', help='YouTube video URL (dùng cho single video)')
    parser.add_argument('--csv-path', help='Đường dẫn tới CSV file chứa danh sách video')
    parser.add_argument('--url-column', default='url', help='Tên cột URL trong CSV (mặc định: url)')
    parser.add_argument('--max-comments', type=int, default=100, help='Maximum comments to crawl')
    parser.add_argument('--order', choices=['time', 'relevance'], default='time', 
                       help='Comment ordering')
    parser.add_argument('--min-likes', type=int, default=0, 
                       help='Minimum likes for top comments (0 = disabled)')
    parser.add_argument('--min-words', type=int, 
                       help='Số từ tối thiểu của comment (None = không giới hạn)')
    parser.add_argument('--max-words', type=int, 
                       help='Số từ tối đa của comment (None = không giới hạn)')
    parser.add_argument('--delay', type=float, default=0.2, 
                       help='Thời gian nghỉ giữa các video khi crawl từ CSV (giây)')
    parser.add_argument('--limit', type=int, 
                       help='Giới hạn số video cần crawl từ CSV (None = tất cả)')
    parser.add_argument('--no-dedupe', action='store_true',
                       help='Không bỏ qua URL trùng lặp trong CSV')
    parser.add_argument('--no-clean', action='store_true', 
                       help='Skip data cleaning')
    parser.add_argument('--no-save', action='store_true', 
                       help='Skip saving results')
    
    args = parser.parse_args()
    
    # Kiểm tra có video-url hoặc csv-path không
    if not args.video_url and not args.csv_path:
        print("❌ Vui lòng cung cấp --video-url hoặc --csv-path")
        sys.exit(1)
    
    if args.video_url and args.csv_path:
        print("❌ Chỉ có thể dùng --video-url HOẶC --csv-path, không dùng cả hai")
        sys.exit(1)
    
    # Khởi tạo analyzer
    analyzer = YouTubeCommentAnalyzer(args.api_key)
    
    # Chạy phân tích
    if args.csv_path:
        # Crawl từ CSV
        result = analyzer.analyze_from_csv(
            csv_path=args.csv_path,
            url_column=args.url_column,
            max_comments=args.max_comments,
            order=args.order,
            delay=args.delay,
            limit=args.limit,
            deduplicate_urls=not args.no_dedupe,
            clean_data=not args.no_clean,
            save_results=not args.no_save,
            min_likes=args.min_likes,
            min_words=args.min_words,
            max_words=args.max_words
        )
    else:
        # Crawl từ single video
        result = analyzer.analyze_comments(
            video_url=args.video_url,
            max_comments=args.max_comments,
            order=args.order,
            min_likes=args.min_likes,
            clean_data=not args.no_clean,
            save_results=not args.no_save,
            min_words=args.min_words,
            max_words=args.max_words
        )
    
    if not result['success']:
        print(f"[ERROR] Analysis failed: {result.get('error', 'Unknown error')}")
        sys.exit(1)

def interactive_mode():
    """
    Chế độ tương tác cho người dùng
    """
    print("=== YOUTUBE COMMENT ANALYZER - INTERACTIVE MODE ===")
    
    # Nhập API key
    api_key = input("Enter YouTube API Key: ").strip()
    if not api_key:
        print("API key is required!")
        return
    
    # Khởi tạo analyzer
    analyzer = YouTubeCommentAnalyzer(api_key)
    
    while True:
        print(f"\n--- NEW ANALYSIS ---")
        
        # Chọn mode: single video hoặc CSV
        mode = input("Choose mode: (1) Single video, (2) CSV file, (q) quit: ").strip().lower()
        
        if mode == 'q' or mode == 'quit':
            break
        elif mode == '2' or mode == 'csv':
            # CSV mode
            csv_path = input("Enter CSV file path: ").strip()
            if not csv_path or not os.path.exists(csv_path):
                print("❌ CSV file not found!")
                continue
            
            try:
                max_comments = int(input("Max comments per video (default 100): ") or "100")
                order = input("Order (time/relevance, default time): ").strip() or "time"
                delay = float(input("Delay between videos in seconds (default 0.2): ") or "0.2")
                limit_input = input("Limit number of videos (press Enter for all): ").strip()
                limit = int(limit_input) if limit_input else None
                min_likes = int(input("Min likes for top comments (0=disabled, default 0): ") or "0")
                min_words_input = input("Min words per comment (press Enter for no limit): ").strip()
                min_words = int(min_words_input) if min_words_input else None
                max_words_input = input("Max words per comment (press Enter for no limit): ").strip()
                max_words = int(max_words_input) if max_words_input else None
                clean_data = input("Clean data? (y/n, default y): ").strip().lower() != 'n'
                save_results = input("Save results? (y/n, default y): ").strip().lower() != 'n'
            except ValueError:
                print("Invalid input! Using defaults.")
                max_comments = 100
                order = 'time'
                delay = 0.2
                limit = None
                min_likes = 0
                min_words = None
                max_words = None
                clean_data = True
                save_results = True
            
            result = analyzer.analyze_from_csv(
                csv_path=csv_path,
                max_comments=max_comments,
                order=order,
                delay=delay,
                limit=limit,
                min_likes=min_likes,
                min_words=min_words,
                max_words=max_words,
                clean_data=clean_data,
                save_results=save_results
            )
            
            if not result['success']:
                print(f"[ERROR] Analysis failed: {result.get('error', 'Unknown error')}")
            
        elif mode == '1' or mode == 'single' or mode == '':
            # Single video mode
            video_url = input("Enter YouTube video URL: ").strip()
            if not video_url:
                print("Video URL is required!")
                continue
            
            # Nhập các tham số
            try:
                max_comments = int(input("Max comments (default 100): ") or "100")
                order = input("Order (time/relevance, default time): ").strip() or "time"
                min_likes = int(input("Min likes for top comments (0=disabled, default 0): ") or "0")
                min_words_input = input("Min words per comment (press Enter for no limit): ").strip()
                min_words = int(min_words_input) if min_words_input else None
                max_words_input = input("Max words per comment (press Enter for no limit): ").strip()
                max_words = int(max_words_input) if max_words_input else None
                
                clean_data = input("Clean data? (y/n, default y): ").strip().lower() != 'n'
                save_results = input("Save results? (y/n, default y): ").strip().lower() != 'n'
                
            except ValueError:
                print("Invalid input! Using defaults.")
                max_comments = 100
                order = 'time'
                min_likes = 0
                min_words = None
                max_words = None
                clean_data = True
                save_results = True
            
            # Chạy phân tích
            result = analyzer.analyze_comments(
                video_url=video_url,
                max_comments=max_comments,
                order=order,
                min_likes=min_likes,
                min_words=min_words,
                max_words=max_words,
                clean_data=clean_data,
                save_results=save_results
            )
            
            if not result['success']:
                print(f"[ERROR] Analysis failed: {result.get('error', 'Unknown error')}")
        else:
            print("Invalid mode! Please choose 1, 2, or q")
            continue
        
        # Hỏi có tiếp tục không
        continue_analysis = input("\nContinue with another analysis? (y/n): ").strip().lower()
        if continue_analysis != 'y':
            break
    
    print("Goodbye!")

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Chế độ tương tác nếu không có arguments
        interactive_mode()
    else:
        # Chế độ command line
        main()
