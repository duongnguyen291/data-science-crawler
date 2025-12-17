"""
YouTube Comment Crawler sử dụng YouTube Data API v3
"""

import os
import time
import json
import argparse
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional, Any
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging

# Thiết lập logging
from logger_config import get_crawler_logger
logger = get_crawler_logger()

class YouTubeCommentCrawler:
    def __init__(self, api_key: str):
        """
        Khởi tạo YouTube Comment Crawler
        
        Args:
            api_key (str): YouTube Data API v3 key
        """
        self.api_key = api_key
        self.youtube = build('youtube', 'v3', developerKey=api_key)
        self.comments_data = []
        
    def extract_video_id(self, url: str) -> str:
        """
        Trích xuất Video ID từ YouTube URL
        
        Args:
            url (str): YouTube URL
            
        Returns:
            str: Video ID
        """
        if 'youtube.com/watch?v=' in url:
            return url.split('v=')[1].split('&')[0]
        elif 'youtu.be/' in url:
            return url.split('youtu.be/')[1].split('?')[0]
        else:
            raise ValueError("Invalid YouTube URL format")
    
    def get_video_info(self, video_id: str) -> Dict:
        """
        Lấy thông tin cơ bản của video
        
        Args:
            video_id (str): Video ID
            
        Returns:
            Dict: Thông tin video
        """
        try:
            request = self.youtube.videos().list(
                part='snippet,statistics',
                id=video_id
            )
            response = request.execute()
            
            if response['items']:
                video = response['items'][0]
                return {
                    'video_id': video_id,
                    'title': video['snippet']['title'],
                    'channel_title': video['snippet']['channelTitle'],
                    'published_at': video['snippet']['publishedAt'],
                    'view_count': video['statistics'].get('viewCount', 0),
                    'like_count': video['statistics'].get('likeCount', 0),
                    'comment_count': video['statistics'].get('commentCount', 0)
                }
            else:
                logger.warning(f"Video {video_id} not found")
                return {}
                
        except HttpError as e:
            logger.error(f"Error getting video info: {e}")
            return {}
    
    def _count_words(self, text: str) -> int:
        """
        Đếm số từ trong text
        
        Args:
            text (str): Text cần đếm
            
        Returns:
            int: Số từ
        """
        if not text or not isinstance(text, str):
            return 0
        # Tách theo khoảng trắng và loại bỏ các phần tử rỗng
        words = [w.strip() for w in text.split() if w.strip()]
        return len(words)
    
    def _filter_by_word_count(self, comments: List[Dict], min_words: Optional[int] = None, 
                              max_words: Optional[int] = None) -> List[Dict]:
        """
        Lọc comments theo số lượng từ
        
        Args:
            comments (List[Dict]): Danh sách comments
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            List[Dict]: Danh sách comments đã được lọc
        """
        if min_words is None and max_words is None:
            return comments
        
        filtered = []
        for comment in comments:
            word_count = self._count_words(comment.get('comment_text', ''))
            
            # Kiểm tra cận dưới
            if min_words is not None and word_count < min_words:
                continue
            
            # Kiểm tra cận trên
            if max_words is not None and word_count > max_words:
                continue
            
            filtered.append(comment)
        
        return filtered
    
    def get_comments(self, video_id: str, max_comments: int = 100, order: str = 'time',
                     min_words: Optional[int] = None, max_words: Optional[int] = None) -> List[Dict]:
        """
        Lấy comments từ video YouTube
        
        Args:
            video_id (str): Video ID
            max_comments (int): Số lượng comment tối đa cần lấy
            order (str): Thứ tự sắp xếp ('time', 'relevance', 'rating')
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            List[Dict]: Danh sách comments
        """
        next_page_token = None
        
        logger.info(f"Bắt đầu crawl comments cho video: {video_id}")
        if min_words is not None or max_words is not None:
            logger.info(f"Filter comments: min_words={min_words}, max_words={max_words}")
        
        # Tăng số lượng fetch để bù cho việc filter
        # Ước tính: nếu filter thì cần fetch nhiều hơn để đủ số lượng
        fetch_multiplier = 2 if (min_words is not None or max_words is not None) else 1
        target_fetch = max_comments * fetch_multiplier
        raw_comments = []
        
        while len(raw_comments) < target_fetch:
            try:
                # Lấy comment threads (top-level comments)
                # Tính số lượng còn cần fetch, tối đa 100 mỗi request (YouTube API limit)
                remaining = target_fetch - len(raw_comments)
                request = self.youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=min(100, remaining),  # YouTube API limit: 100 per request
                    pageToken=next_page_token,
                    order=order  # Sắp xếp theo thứ tự được chỉ định
                )
                
                response = request.execute()
                
                for item in response['items']:
                    if len(raw_comments) >= target_fetch:
                        break
                        
                    # Xử lý top-level comment
                    top_comment = self._process_comment(item['snippet']['topLevelComment'], video_id)
                    raw_comments.append(top_comment)
                    
                    # Xử lý replies nếu có
                    if 'replies' in item:
                        for reply in item['replies']['comments'][:5]:  # Giới hạn 5 replies per comment
                            if len(raw_comments) >= target_fetch:
                                break
                            reply_comment = self._process_comment(reply, video_id, is_reply=True)
                            reply_comment['parent_comment_id'] = top_comment['comment_id']
                            raw_comments.append(reply_comment)
                
                # Kiểm tra có trang tiếp theo không
                next_page_token = response.get('nextPageToken')
                if not next_page_token:
                    break
                    
                # Delay để tránh rate limit
                time.sleep(0.1)
                
            except HttpError as e:
                logger.error(f"Error fetching comments: {e}")
                if e.resp.status == 403:
                    logger.error("API quota exceeded or access denied")
                    break
                time.sleep(1)
        
        # Filter comments theo số lượng từ
        comments = self._filter_by_word_count(raw_comments, min_words, max_words)
        
        # Giới hạn số lượng comments cuối cùng
        comments = comments[:max_comments]
        
        logger.info(f"Đã crawl được {len(raw_comments)} comments, sau filter còn {len(comments)} comments")
        return comments
    
    def _process_comment(self, comment_data: Dict, video_id: str, is_reply: bool = False) -> Dict:
        """
        Xử lý dữ liệu comment từ API response
        
        Args:
            comment_data (Dict): Dữ liệu comment từ API
            video_id (str): Video ID
            is_reply (bool): Có phải là reply không
            
        Returns:
            Dict: Comment đã được xử lý
        """
        snippet = comment_data['snippet']
        
        return {
            'comment_id': comment_data['id'],
            'post_id': video_id,
            'platform': 'YouTube',
            'author_name': snippet['authorDisplayName'],
            'author_id': snippet['authorChannelId']['value'] if 'authorChannelId' in snippet else None,
            'comment_text': snippet['textDisplay'],
            'published_at': snippet['publishedAt'],
            'like_count': snippet['likeCount'],
            'reply_count': snippet.get('totalReplyCount', 0),
            'sentiment_label': None,  # Sẽ được cập nhật sau
            'sentiment_score': None,  # Sẽ được cập nhật sau
            'crawled_at': datetime.now().isoformat(),
            'is_reply': is_reply,
            'parent_comment_id': None
        }
    
    def crawl_video(self, video_url: str, max_comments: int = 100, order: str = 'time',
                   min_words: Optional[int] = None, max_words: Optional[int] = None) -> Dict:
        """
        Crawl comments từ một video YouTube
        
        Args:
            video_url (str): URL của video YouTube
            max_comments (int): Số lượng comment tối đa
            order (str): Thứ tự sắp xếp ('time', 'relevance', 'rating')
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            Dict: Kết quả crawl
        """
        try:
            # Trích xuất video ID
            video_id = self.extract_video_id(video_url)
            logger.info(f"Video ID: {video_id}")
            
            # Lấy thông tin video
            video_info = self.get_video_info(video_id)
            if not video_info:
                return {'success': False, 'error': 'Video not found'}
            
            # Lấy comments
            comments = self.get_comments(video_id, max_comments, order, min_words, max_words)
            
            return {
                'success': True,
                'video_info': video_info,
                'comments': comments,
                'total_comments': len(comments)
            }
            
        except Exception as e:
            logger.error(f"Error crawling video: {e}")
            return {'success': False, 'error': str(e)}
    
    def crawl_from_csv(
        self,
        csv_path: str,
        url_column: str = 'url',
        max_comments: int = 100,
        order: str = 'time',
        delay: float = 0.2,
        limit: Optional[int] = None,
        deduplicate_urls: bool = True,
        min_likes: int = 0,
        min_words: Optional[int] = None,
        max_words: Optional[int] = None
    ) -> Dict:
        """
        Crawl comments cho danh sách video trong file CSV
        
        Args:
            csv_path (str): Đường dẫn tới file CSV chứa danh sách video
            url_column (str): Tên cột chứa URL video (mặc định: 'url')
            max_comments (int): Số lượng comment tối đa cho mỗi video
            order (str): Thứ tự sắp xếp comments
            delay (float): Thời gian nghỉ giữa mỗi video (giây)
            limit (int): Giới hạn số lượng video cần crawl (None = tất cả)
            deduplicate_urls (bool): Có bỏ qua URL trùng lặp không
            min_likes (int): Số lượt like tối thiểu (0 = disabled)
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
        
        Returns:
            Dict: Tổng hợp kết quả crawl
        """
        if not os.path.isfile(csv_path):
            logger.error(f"CSV file not found: {csv_path}")
            return {'success': False, 'error': f'CSV file not found: {csv_path}'}
        
        df = pd.read_csv(csv_path)
        
        if url_column not in df.columns:
            error_msg = f"Column '{url_column}' not found in CSV"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        context_columns = [col for col in df.columns if col != url_column]
        videos: List[Dict[str, Any]] = []
        seen_urls = set()
        
        for _, row in df.iterrows():
            raw_url = row.get(url_column)
            if pd.isna(raw_url):
                continue
            video_url = str(raw_url).strip()
            if not video_url:
                continue
            if deduplicate_urls and video_url in seen_urls:
                continue
            seen_urls.add(video_url)
            
            metadata = {}
            for col in context_columns:
                value = row.get(col)
                metadata[f"source_{col}"] = None if pd.isna(value) else value
            videos.append({'url': video_url, 'metadata': metadata})
        
        if not videos:
            error_msg = f"No valid URLs found in column '{url_column}'"
            logger.error(error_msg)
            return {'success': False, 'error': error_msg}
        
        if limit is not None and limit > 0:
            videos = videos[:limit]
        
        crawl_summary = []
        failed_urls = []
        total_comments = 0
        
        logger.info(f"Bắt đầu crawl từ CSV: {csv_path}")
        logger.info(f"Tổng số video cần crawl: {len(videos)}")
        
        for idx, video_entry in enumerate(videos, start=1):
            video_url = video_entry['url']
            metadata = video_entry['metadata']
            
            logger.info(f"[{idx}/{len(videos)}] Crawl video: {video_url}")
            # Sử dụng get_top_comments nếu min_likes > 0, ngược lại dùng crawl_video
            if min_likes > 0:
                result = self.get_top_comments(video_url, max_comments, min_likes, min_words, max_words)
            else:
                result = self.crawl_video(video_url, max_comments=max_comments, order=order, 
                                        min_words=min_words, max_words=max_words)
            
            summary_item = {
                'url': video_url,
                'metadata': metadata,
                'success': result['success'],
                'total_comments': result.get('total_comments', 0)
            }
            
            if result['success']:
                # Gắn metadata vào comments
                comments = result['comments']
                if metadata:
                    for comment in comments:
                        comment.update(metadata)
                
                self.comments_data.extend(comments)
                total_comments += len(comments)
                summary_item['video_info'] = result['video_info']
            else:
                summary_item['error'] = result.get('error', 'Unknown error')
                failed_urls.append(video_url)
            
            crawl_summary.append(summary_item)
            time.sleep(max(delay, 0))
        
        logger.info(f"Hoàn thành crawl từ CSV. Tổng số comments: {total_comments}")
        if failed_urls:
            logger.warning(f"Crawl thất bại cho {len(failed_urls)} video: {failed_urls}")
        
        return {
            'success': len(failed_urls) == 0,
            'summary': crawl_summary,
            'failed_urls': failed_urls,
            'total_videos': len(videos),
            'total_comments': total_comments,
            'aggregated_comments': self.comments_data
        }
    
    def save_to_csv(self, data: List[Dict], filename: str = None):
        """
        Lưu dữ liệu comments vào file CSV
        
        Args:
            data (List[Dict]): Dữ liệu comments
            filename (str): Tên file (tự động tạo nếu None)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_comments_{timestamp}.csv"
        
        df = pd.DataFrame(data)
        df.to_csv(filename, index=False, encoding='utf-8')
        logger.info(f"Đã lưu {len(data)} comments vào file: {filename}")
        return filename
    
    def save_to_json(self, data: List[Dict], filename: str = None):
        """
        Lưu dữ liệu comments vào file JSON
        
        Args:
            data (List[Dict]): Dữ liệu comments
            filename (str): Tên file (tự động tạo nếu None)
        """
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"youtube_comments_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"Đã lưu {len(data)} comments vào file: {filename}")
        return filename
    
    def get_top_comments(self, video_url: str, max_comments: int = 50, min_likes: int = 0,
                        min_words: Optional[int] = None, max_words: Optional[int] = None) -> Dict:
        """
        Lấy các comment có lượt like cao nhất
        
        Args:
            video_url (str): URL của video YouTube
            max_comments (int): Số lượng comment tối đa
            min_likes (int): Số lượt like tối thiểu
            min_words (Optional[int]): Số từ tối thiểu (None = không giới hạn)
            max_words (Optional[int]): Số từ tối đa (None = không giới hạn)
            
        Returns:
            Dict: Kết quả crawl với comments được sắp xếp theo like
        """
        try:
            # Trích xuất video ID
            video_id = self.extract_video_id(video_url)
            logger.info(f"Lấy top comments cho video: {video_id}")
            
            # Lấy thông tin video
            video_info = self.get_video_info(video_id)
            if not video_info:
                return {'success': False, 'error': 'Video not found'}
            
            # Lấy comments với order='relevance' để ưu tiên comments có relevance cao
            # Filter theo word count đã được xử lý trong get_comments
            comments = self.get_comments(video_id, max_comments * 2, order='relevance', 
                                        min_words=min_words, max_words=max_words)
            
            # Lọc comments có like >= min_likes
            filtered_comments = [c for c in comments if c['like_count'] >= min_likes]
            
            # Sắp xếp theo số lượt like giảm dần
            sorted_comments = sorted(filtered_comments, key=lambda x: x['like_count'], reverse=True)
            
            # Lấy top comments
            top_comments = sorted_comments[:max_comments]
            
            logger.info(f"Đã lấy {len(top_comments)} top comments (min_likes={min_likes})")
            
            return {
                'success': True,
                'video_info': video_info,
                'comments': top_comments,
                'total_comments': len(top_comments),
                'min_likes': min_likes,
                'order': 'top_liked'
            }
            
        except Exception as e:
            logger.error(f"Error getting top comments: {e}")
            return {'success': False, 'error': str(e)}


def parse_args():
    parser = argparse.ArgumentParser(description="YouTube Comment Crawler CLI")
    parser.add_argument('--api-key', help='YouTube Data API v3 key (hoặc đặt env YOUTUBE_API_KEY)')
    parser.add_argument('--video-url', help='URL video YouTube cần crawl')
    parser.add_argument('--csv-path', help='Đường dẫn tới file CSV chứa danh sách video')
    parser.add_argument('--url-column', default='url', help="Tên cột URL trong CSV (mặc định: 'url')")
    parser.add_argument('--max-comments', type=int, default=100, help='Số comment tối đa mỗi video')
    parser.add_argument('--order', choices=['time', 'relevance', 'rating'], default='time',
                        help='Thứ tự lấy comments')
    parser.add_argument('--delay', type=float, default=0.2, help='Thời gian nghỉ giữa các video (giây)')
    parser.add_argument('--limit', type=int, help='Giới hạn số video cần crawl khi dùng CSV')
    parser.add_argument('--no-dedupe', action='store_true', help='Không bỏ qua URL trùng lặp trong CSV')
    parser.add_argument('--min-words', type=int, help='Số từ tối thiểu của comment (None = không giới hạn)')
    parser.add_argument('--max-words', type=int, help='Số từ tối đa của comment (None = không giới hạn)')
    parser.add_argument('--output-csv', help='File CSV để lưu toàn bộ comments kết quả')
    parser.add_argument('--output-json', help='File JSON để lưu toàn bộ comments kết quả')
    return parser.parse_args()


def main():
    """
    CLI cho YouTube Comment Crawler.
    Hỗ trợ crawl một video hoặc crawl hàng loạt từ file CSV.
    """
    args = parse_args()
    
    api_key = args.api_key or os.getenv('YOUTUBE_API_KEY') or "YOUR_API_KEY_HERE"
    if api_key == "YOUR_API_KEY_HERE":
        print("❌ Thiếu API key. Dùng --api-key hoặc đặt biến môi trường YOUTUBE_API_KEY.")
        return
    
    if not args.video_url and not args.csv_path:
        print("❌ Vui lòng cung cấp --video-url hoặc --csv-path.")
        return
    
    crawler = YouTubeCommentCrawler(api_key)
    aggregated_comments: List[Dict] = []
    
    if args.video_url:
        print(f"Bắt đầu crawl video: {args.video_url}")
        result = crawler.crawl_video(args.video_url, max_comments=args.max_comments, order=args.order,
                                   min_words=args.min_words, max_words=args.max_words)
        if result['success']:
            aggregated_comments = result['comments']
            print(f"✅ Crawl thành công {result['total_comments']} comments.")
            print(f"📹 {result['video_info']['title']} ({result['video_info']['channel_title']})")
        else:
            print(f"❌ Crawl thất bại: {result['error']}")
            return
    
    if args.csv_path:
        csv_result = crawler.crawl_from_csv(
            csv_path=args.csv_path,
            url_column=args.url_column,
            max_comments=args.max_comments,
            order=args.order,
            delay=args.delay,
            limit=args.limit,
            deduplicate_urls=not args.no_dedupe,
            min_words=args.min_words,
            max_words=args.max_words
        )
        
        if not csv_result['success']:
            print("⚠️ Hoàn thành với một số lỗi.")
        else:
            print("✅ Đã crawl xong danh sách video.")
        
        print(f"📊 Tổng số video xử lý: {csv_result['total_videos']}")
        print(f"💬 Tổng số comments thu được: {csv_result['total_comments']}")
        if csv_result['failed_urls']:
            print(f"❗ Video lỗi: {len(csv_result['failed_urls'])}")
            for failed in csv_result['failed_urls']:
                print(f"   - {failed}")
        
        aggregated_comments = csv_result['aggregated_comments']
    
    # Lưu kết quả nếu cần
    if aggregated_comments:
        if args.output_csv:
            crawler.save_to_csv(aggregated_comments, args.output_csv)
        if args.output_json:
            crawler.save_to_json(aggregated_comments, args.output_json)
    else:
        print("ℹ️ Không có dữ liệu comment để lưu.")


if __name__ == "__main__":
    main()