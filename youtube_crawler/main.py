"""
YouTube Comment Crawler - Main Application
Tổng hợp tất cả chức năng crawl, làm sạch và phân tích comments
"""

import os
import sys
import argparse
from datetime import datetime
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
                      order: str = 'time', min_likes: int = 0) -> dict:
        """
        Crawl comments từ video YouTube
        
        Args:
            video_url (str): URL video YouTube
            max_comments (int): Số lượng comment tối đa
            order (str): Thứ tự sắp xếp ('time', 'relevance')
            min_likes (int): Số lượt like tối thiểu (chỉ áp dụng khi order='top')
            
        Returns:
            dict: Kết quả crawl
        """
        logger.info(f"Starting comment crawl for: {video_url}")
        
        if min_likes > 0:
            # Lấy top comments có like cao
            result = self.crawler.get_top_comments(video_url, max_comments, min_likes)
        else:
            # Lấy comments thông thường
            result = self.crawler.crawl_video(video_url, max_comments, order)
        
        if result['success']:
            logger.info(f"Successfully crawled {result['total_comments']} comments")
        else:
            logger.error(f"Crawl failed: {result['error']}")
            
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
                        clean_data: bool = True, save_results: bool = True) -> dict:
        """
        Phân tích hoàn chỉnh comments từ video
        
        Args:
            video_url (str): URL video YouTube
            max_comments (int): Số lượng comment tối đa
            order (str): Thứ tự sắp xếp
            min_likes (int): Số lượt like tối thiểu
            clean_data (bool): Có làm sạch dữ liệu không
            save_results (bool): Có lưu kết quả không
            
        Returns:
            dict: Kết quả phân tích
        """
        print(f"\n=== YOUTUBE COMMENT ANALYZER ===")
        print(f"Video: {video_url}")
        print(f"Max comments: {max_comments}")
        print(f"Order: {order}")
        if min_likes > 0:
            print(f"Min likes: {min_likes}")
        
        # Bước 1: Crawl comments
        print(f"\n1. CRAWLING COMMENTS...")
        crawl_result = self.crawl_comments(video_url, max_comments, order, min_likes)
        
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

def main():
    """
    Hàm main với command line interface
    """
    parser = argparse.ArgumentParser(description='YouTube Comment Crawler & Analyzer')
    parser.add_argument('--api-key', required=True, help='YouTube Data API v3 key')
    parser.add_argument('--video-url', required=True, help='YouTube video URL')
    parser.add_argument('--max-comments', type=int, default=100, help='Maximum comments to crawl')
    parser.add_argument('--order', choices=['time', 'relevance'], default='time', 
                       help='Comment ordering')
    parser.add_argument('--min-likes', type=int, default=0, 
                       help='Minimum likes for top comments (0 = disabled)')
    parser.add_argument('--no-clean', action='store_true', 
                       help='Skip data cleaning')
    parser.add_argument('--no-save', action='store_true', 
                       help='Skip saving results')
    
    args = parser.parse_args()
    
    # Khởi tạo analyzer
    analyzer = YouTubeCommentAnalyzer(args.api_key)
    
    # Chạy phân tích
    result = analyzer.analyze_comments(
        video_url=args.video_url,
        max_comments=args.max_comments,
        order=args.order,
        min_likes=args.min_likes,
        clean_data=not args.no_clean,
        save_results=not args.no_save
    )
    
    if not result['success']:
        print(f"[ERROR] Analysis failed: {result['error']}")
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
        
        # Nhập video URL
        video_url = input("Enter YouTube video URL (or 'quit' to exit): ").strip()
        if video_url.lower() == 'quit':
            break
        
        if not video_url:
            print("Video URL is required!")
            continue
        
        # Nhập các tham số
        try:
            max_comments = int(input("Max comments (default 100): ") or "100")
            order = input("Order (time/relevance, default time): ").strip() or "time"
            min_likes = int(input("Min likes for top comments (0=disabled, default 0): ") or "0")
            
            clean_data = input("Clean data? (y/n, default y): ").strip().lower() != 'n'
            save_results = input("Save results? (y/n, default y): ").strip().lower() != 'n'
            
        except ValueError:
            print("Invalid input! Using defaults.")
            max_comments = 100
            order = 'time'
            min_likes = 0
            clean_data = True
            save_results = True
        
        # Chạy phân tích
        result = analyzer.analyze_comments(
            video_url=video_url,
            max_comments=max_comments,
            order=order,
            min_likes=min_likes,
            clean_data=clean_data,
            save_results=save_results
        )
        
        if not result['success']:
            print(f"[ERROR] Analysis failed: {result['error']}")
        
        # Hỏi có tiếp tục không
        continue_analysis = input("\nContinue with another video? (y/n): ").strip().lower()
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
